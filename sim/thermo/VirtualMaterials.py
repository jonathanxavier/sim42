"""Virtual Material interface for the simulator

Classes:
ThermoInterface -- Main class of the interfase

"""

import string, sys, Numeric, re
from Numeric import Float, Int, zeros, ones, array
from sim.solver.Variables import *
from sim.solver.Messages import MessageHandler
from ThermoConstants import *

import Oils
try:
    import vmg
except:
    raise AssertionError
from ThermoAdmin import FlashResults, EnvelopeResults, ThermoCase
from VMConstants import *
from Hypo import *
from vmgunits import units

from xml.dom import Node, minidom       # Node MUST be first
from xml.sax import ContentHandler, parseString

from sim.solver.Error import SimError


#Some constants to handle some special property packages
SOLID_MODELS = ['SimpleSolid']
EMPTY_MODEL = 'Unknown'

initCount = 0  # running total of number of initializations

VMG_INTERFACE_VERSION = 7.0

#Global object so not stream duplicates are done
glbVmgObjects = {}

VMGUnknown = -12321
        
class VMGStoreInfoOfThermoCase(object):
    """Groups all the information of a thermodynamic case into one single object that can be sored by pickle"""
    def __init__(self):
        self.version = VMG_INTERFACE_VERSION
        self.pkgName = ''
        self.cmps = []
        self.fshSets = None
        self.hypoDescs = None
        self.ipVals = {} #an ipval can be accessed like self.ipVals[matrName][paneName][i][j]
        self.thCaseObj = None
        self.response = ''
        self.internalData = ''
        self.oilData = ''
        
class VMGStoreInfoOfProvider(object):
    """Groups all the information of a thermodynamic provider into one single object that can be sored by pickle"""
    def __init__(self):
        self.name = None
        self.parent = None
        
        
class ThermoInterface(object):
    """Main class of the interfase"""
    def __init__(self):
        """Initializes the package"""
        global initCount
        if initCount == 0:
            vmg.InitializePkg()
        initCount += 1
        self.gPkgHandles = {} #Values are tuples with handle, proppkg creation string and the thermoCase object
        self.propHandler = vmgPropHandler()
        self.flashSettingsInfoDict = vmgFlashSettingsInfoDict()
        self.flashSettings = {} #List of values for flash settings
        self.parent = None
        self.name = 'VirtualMaterials'
        self.version = VMG_INTERFACE_VERSION

    def Clone(self, thCase, newCaseName):
        if thCase in self.gPkgHandles.keys():
            storeObj = self._CreateAStoreThCaseObj(thCase)
            storeObj.thCaseObj = None 
            # This version cannot clone oil data
            # Need to rethink whether oil data are thermo case specific or not
            # If so, need to clone also the Sim42 BasicOilObjects
            storeObj.oilData = ''
            self._CreateAVMGThCase(newCaseName, storeObj)
            return newCaseName
        
    def __getstate__(self):
        """return info to store"""
        store = {}
        for key in self.gPkgHandles.keys():
            #Wrap all the crucial information into one "pickable" object
            storeObj = self._CreateAStoreThCaseObj(key)
            store[key] = storeObj
        
        providerStoreObj = VMGStoreInfoOfProvider()
        providerStoreObj.parent = self.parent
        providerStoreObj.name = self.name
        
        return (store, self.propHandler, providerStoreObj)

    
    def __setstate__(self, oldState):
        """build packages from saved info"""
        global initCount
        if initCount == 0:
            vmg.InitializePkg()
        initCount += 1
        if len(oldState) == 2:
            (store, self.propHandler) = oldState
            self.name = 'VirtualMaterials'
            self.parent = None
        else:
            (store, self.propHandler, providerStoreObj) = oldState
            self.name = providerStoreObj.name
            self.parent = providerStoreObj.parent
            
        self.gPkgHandles = {}
        self.flashSettings = {}
        self.flashSettingsInfoDict = vmgFlashSettingsInfoDict()
        for key in store.keys():
            storeObj = store[key]
            self._CreateAVMGThCase(key, storeObj)
            
        self.version = VMG_INTERFACE_VERSION


    def _CreateAStoreThCaseObj(self, thName):
        """Returns an object with all the neccessary information to save a thermodynamic case"""
        storeObj = VMGStoreInfoOfThermoCase()
        storeObj.version = self.version
        storeObj.pkgName = self.gPkgHandles[thName][1]
        storeObj.cmps = self.GetSelectedCompoundNames(thName)
        storeObj.fshSets = self.flashSettings[thName]
        storeObj.thCaseObj = self.gPkgHandles[thName][2]

        #load cmps into a var
        cmps = storeObj.cmps
        nuCmps = len(cmps)
        
        # add Hypo handling
        descs = []
        for idx in range(nuCmps):
            family = self.GetSelectedCompoundProperties(thName, idx, 'ChemicalFamily')[0]
            
            if cmps[idx][-1] == '*' or family.lower() == 'oil':
                descs.append(self.GetSelectedCompoundProperties(thName, idx, 'CreationInfo')[0])
            else:
                descs.append('')
            
        storeObj.hypoDescs = descs

        #Now add the IP stuff
        #import time
        #print time.asctime(), time.time()
        ipVals = {}
        for ipMatrName in self.GetIPMatrixNames(thName):
            ipVals[ipMatrName] = {}
            paneNames = self.GetIPPaneNames(thName, ipMatrName)
            for paneIdx in range(len(paneNames)):
                paneName = paneNames[paneIdx]
                try:
                    ipVals[ipMatrName][paneName] = self.GetIPValues(thName, ipMatrName, paneIdx)
                except:
                    ipVals[ipMatrName][paneName] = []
                #lstOfLsts = ipVals[ipMatrName][paneName]
                ##Save the minimum amount of values (i.e. do not save ij and ji)
                #for i in range(nuCmps):
                    #lstOfLsts.append([])
                    #cmpName1 = cmps[i]
                    #for j in range(nuCmps):
                        #cmpName2 = cmps[j]
                        #val = self.GetIPValue(thName, ipMatrName, cmpName1, cmpName2, paneIdx)
                        #lstOfLsts[i].append(val)
                
        storeObj.ipVals = ipVals
        #print time.asctime(), time.time()
        hnd = self.gPkgHandles[thName][0]
        # Get any other internal property package data that need to be stored
        response = self._VMGCommand(hnd, 'GetStoreData', '')
        if response[1] != '' and response[0] == 0:
            storeObj.internalData = response[1]
            
        try:
            response = vmg.Oil(hnd, 'Store', '')
            if response[1] != '' and response[0] == 0:
                storeObj.oilData = response[1]
        except:
            pass
        #response = self._VMGCommand(hnd, 'Oil', 'SizeOfResults')
        #if response[1] != '' and response[0] == 0:    
            #pass
        
        return storeObj

    def _CreateAVMGThCase(self, thName, storeObj):
        """Any valid  storeObj can build a new thermo case"""

            
        # Earlier version doesn't store as one object and has no version number stored

        if isinstance(storeObj, tuple):
            #Old style
            # if the store contains 3 tokens, asume version 0
            if len(storeObj) == 3:
                ver = 0                
                (pkgName, cmps, fshSets) = storeObj
                descs = []
            else:
                (ver, pkgName, cmps, fshSets, descs) = storeObj

            if ver == 0:
                self.AddPkgFromName(thName, pkgName)
                for cmp in cmps:
                    try:
                        self.AddCompound(thName, cmp)
                    except:
                        # have to have this so IP errors are ignored
                        pass

            elif ver == 1.0:
                self.AddPkgFromName(thName, pkgName)
                for idx in range(len(cmps)):
                    try:
                        if descs[idx] == '':
                            self.AddCompound(thName, cmps[idx])
                        else:
                            descTuple = GetCompoundPropertyLists(cmps[idx], descs[idx])            
                            self.AddHypoCompound(thName, cmps[idx], descTuple)
                    except:
                        pass   # have to have this so IP errors are ignored
                
            for fshSet in fshSets.keys():
                self.SetFlashSetting(thName, fshSet, fshSets[fshSet])

        else:
            ver = storeObj.version
            
            if ver >= 2.0:
                pkgName = storeObj.pkgName
                cmps = storeObj.cmps
                fshSets = storeObj.fshSets
                descs = storeObj.hypoDescs
                ipVals = storeObj.ipVals

                nuCmps = len(cmps)

                #Prop pkg and compounds
                self.AddPkgFromName(thName, pkgName)
                hnd = self.gPkgHandles[thName][0]
                AddCompound = vmg.AddCompound
                AddHypoCompound = self.AddHypoCompound
                for idx in range(nuCmps):
                    try:
                        if descs[idx] == '':
                            AddCompound(hnd, cmps[idx])
                            #self.AddCompound(thName, cmps[idx])
                        else:
                            descTuple = GetCompoundPropertyLists(cmps[idx], descs[idx])            
                            AddHypoCompound(thName, cmps[idx], descTuple)
                    except:
                        pass   # have to have this so IP errors are ignored

                #Flash settings
                for fshSet in fshSets.keys():
                    self.SetFlashSetting(thName, fshSet, fshSets[fshSet])
            
            hnd = self.gPkgHandles[thName][0]
            #import time
            #print time.asctime(), time.time()
            if ver >= 3.0 and ver < 7.0:
                #IP values
                
                for ipMatrName, ipPaneDict in ipVals.items():
                    paneNames = self.GetIPPaneNames(thName, ipMatrName)
                    for paneName, lstOfLsts in ipPaneDict.items():
                        if paneName in paneNames:
                            paneIdx = paneNames.index(paneName)
                            lstOfLsts = ipVals[ipMatrName][paneName]
                            
                            vals = array(lstOfLsts, Float)
                            #print 'before'
                            vmg.SetBinaryPairValues(hnd, ipMatrName, paneIdx, vals)
                            #print 'after'
                            #for i in range(nuCmps):
                                #cmpName1 = cmps[i]
                                #for j in range(nuCmps):
                                    #cmpName2 = cmps[j]
                                    #val = lstOfLsts[i][j]
                                    #if i != j:
                                        
                                        #vmg.SetBinaryPairValue(hnd, ipMatrName, i, j, paneIdx, val)
                    vmg.ResetAijChanged(hnd)
                                        
                                        #self.SetIPValue(thName, ipMatrName, cmpName1, cmpName2, paneIdx, val)
            elif ver >= 7.0:
                #kij values loading is different as now it is done with map and it also stores i=j values
                for ipMatrName, ipPaneDict in ipVals.items():
                    paneNames = self.GetIPPaneNames(thName, ipMatrName)
                    for paneName, lstOfLsts in ipPaneDict.items():
                        if paneName in paneNames:
                            paneIdx = paneNames.index(paneName)
                            kijArray = ipVals[ipMatrName][paneName]
                            
                            if kijArray != []:
                                #Load variables that will be used by map call
                                #self._thName = thName
                                #self._nuCmps = nuCmps
                                #self._ipMatrName = ipMatrName
                                #self._paneIdx = paneIdx
                                #self._hnd = self.gPkgHandles[thName][0]
                                #self._cmpIdx1 = None
                                
                                #print 'beforenew'
                                #Load everything with map
                                vmg.SetBinaryPairValues(hnd, ipMatrName, paneIdx, kijArray)
                                
                                #map(self._SetIPValsFromList, kijArray, (range(nuCmps)))
                                #print 'afternew'
                                #Reset this
                    vmg.ResetAijChanged(hnd)
                                
                                #No real need to delete temporary member variables
                                ##del self._thName
                                ##del self._nuCmps
                                ##del self._ipMatrName
                                ##del self._paneIdx
                                ##del self._hnd
                                ##del self._cmpIdx1
            #print time.asctime(), time.time()
            if ver <= 3.0:
                self.propHandler.SetSimCommonArrayPropertyNames([])
                
            #If it stored a thCaseObj, then use it and overwrite the one that got 
            #created automatically in this method
            if hasattr(storeObj, 'thCaseObj'):
                obj = self.gPkgHandles[thName]
                if storeObj.thCaseObj:
                    self.gPkgHandles[thName] = (obj[0], obj[1], storeObj.thCaseObj)

            hnd = self.gPkgHandles[thName][0]
            # restore the property pacakge internal data
            if hasattr(storeObj, 'internalData'):
                dat = storeObj.internalData
                if dat:
                    obj = self.gPkgHandles[thName]
                    self._VMGCommand(hnd, 'RecallData', str(dat))
            
            try:
                if hasattr(storeObj, 'oilData'):
                    data = storeObj.oilData
                    if not data: 
                        data = ''
                    response = vmg.Oil(hnd, 'Recall', data)
            except:
                pass
                
    def _SetIPValsFromList(self, vals, cmpIdx1):
        """Grabs a list of values and matches it to cmpIdx1 as kij values. Useful for map calls"""
        self._cmpIdx1 = cmpIdx1
        map(self._SetIPValFromIndex, vals, range(self._nuCmps))
        
    def _SetIPValFromIndex(self, val, cmpIdx2):
        """Grabs an ip index and matches it with the active idx and sets the kij value. Useful for map calls"""
        
        vmg.SetBinaryPairValue(self._hnd, self._ipMatrName, self._cmpIdx1, cmpIdx2, self._paneIdx, val)
        #vmg.ResetAijChanged(self._hnd)
            
            
    def CleanUp(self):
        for pkg in self.gPkgHandles.values():
            pkg[2].CleanUp()
        self.gPkgHandles = {}

        global initCount
        initCount -= 1
        if initCount == 0:
            vmg.TerminatePkg()
            
        self.flashSettingsInfoDict = None
        self.propHandler = None
        self.flashSettingsInfoDict = None
        self.parent = None

        global glbVmgObjects
        glbVmgObjects = {}
        
    def SetParent(self, parent):
        """Should be a thermo admin instance but is not inforced"""
        if self.parent != parent:
            for thCaseName, obj in self.gPkgHandles.items():
                thCaseObj = ThermoCase(parent, self.name, thCaseName, obj[1])
                self.gPkgHandles[thCaseName] = (obj[0], obj[1], thCaseObj)            
            
        self.parent = parent

    def GetPath(self):
        if self.parent:
            return self.parent.GetPath() + '.' + self.name
        return None
        
    def GetParent(self):
        return self.parent
    
    def SetName(self, name):
        self.name = name
        
    def GetName(self):
        return self.name
    
    def DeleteObject(self, obj):
        if isinstance(obj, ThermoCase):
            thAdmin = obj.thermoAdmin
            thName = obj.case
            provider = obj.provider
            
            if thAdmin != self.parent:
                raise SimError('ThAdminMismatch', (str(obj),))
            
            #First get rid of the thCase from the unit ops
            unitOps = obj.GetUnitOps()
            if thName in self.gPkgHandles.keys() and provider == self.name:
                for uo in unitOps:
                    uo.thCaseObj = None
                    
                #Now delete through the thermo admin!!!!
                self.parent.DeleteThermoCase(provider, thName)
            
    
    def GetContents(self):
        results = []
        for thCaseName, myInfo in self.gPkgHandles.items():
            results.append((thCaseName, myInfo[2]))
        return results

    def GetObject(self, desc):
        """Return the thermo case if it exists"""
        if self.gPkgHandles.has_key(desc):
            return self.gPkgHandles[desc][2]

        return None         
            
    def MergeProvider(self, fProv):
        """Merge the incomming provider into this thermo provider"""
        self.gPkgHandles.update(fProv.gPkgHandles)
        self.flashSettings.update(fProv.flashSettings)
            
    def GetAvThCaseNames(self):
        """List of the avilable thermo cases for a specified provider"""
        return self.gPkgHandles.keys()
        
    def GetAvPropPkgNames(self):
        """List of avilable porperty packages for a specified provider"""
        upkgs = vmg.PkgNames()
        pkgs = []
        for i in upkgs: pkgs.append(str(i))
        return pkgs

    def AddPkgFromName(self, thName, pkgName):
        """Selects a property packages for a specified thermo case

        thName -- Name of the thermo case
        pkgName -- String with the th pkg name. If one pkg per phase,
                   then separate the th pkg names with a space. Order: Vap, liq

        """
        self.DeleteThermoCase(thName)
        pkgSplit = string.split(pkgName)

        #Once we implement polymers this string (pkgName) will have to become a dictionary
        
        #Assume this order, vap, liq, solid model.
        nuPkgs = len(pkgSplit)
        if nuPkgs <= 0:
           raise SimError('NoPkgSelected', (thName,))

        #Can not be sure of what this is, just pass it in
        if nuPkgs > 3:
            hnd = vmg.AddAggregatePkgFromName(pkgName)            
       
        #Assume it requires solid support
        elif nuPkgs == 3:
            #Insert two empties to conform to vmg model
            pkgSplit.insert(2, EMPTY_MODEL)
            pkgSplit.insert(3, EMPTY_MODEL)
            pkgName = string.join(pkgSplit, ' ')
            hnd = vmg.AddAggregatePkgFromName(pkgName)
        
        #Either vap an liq prop pkg or liq and solid prop pkg
        elif nuPkgs == 2 and pkgSplit[0] != pkgSplit[1]:
            if not pkgSplit[1] in SOLID_MODELS:
                hnd = vmg.AddAggregatePkgFromName(pkgName)
            else:
                #Duplicate the prop pkg for vap and liq and insert two empties to conform to vmg model
                pkgSplit.insert(1, str(pkgSplit[0]))
                pkgSplit.insert(2, EMPTY_MODEL)
                pkgSplit.insert(3, EMPTY_MODEL)
                pkgName = string.join(pkgSplit, ' ')
                hnd = vmg.AddAggregatePkgFromName(pkgName)
        
        #Same prop pkg for liq and vap
        else:
            hnd = vmg.AddPkgFromName(pkgSplit[0])
            
        thCaseObj = None
        if self.parent:
            thCaseObj = ThermoCase(self.parent, self.name, thName, pkgName)  
        self.gPkgHandles[thName] = (hnd, pkgName, thCaseObj)
        
        #Init flash settings with default values
        d = self.flashSettingsInfoDict
        myDict = {}
        for i in d: myDict[i] = d[i].defValue
        self.flashSettings[thName] = myDict
        
        return thCaseObj
        
    def ReplacePkgFromName(self, thName, pkgName):
        """Replaces property packages in an existing thermo case

        thName -- Name of the thermo case
        pkgName -- String with the th pkg name. If one pkg per phase,
                   then separate the th pkg names with a space. Order: Vap, liq
        """
        hnd = self.gPkgHandles[thName][0]
        thCase = self.gPkgHandles[thName][2]
        
        self.gPkgHandles[thName] = (hnd, pkgName, thCase)
        
        pkgSplit = string.split(pkgName)
        if ' ' in pkgName and (pkgSplit[0] not in pkgSplit[1:]):
            hnd = vmg.ReplaceAggregatePkgFromName(pkgName, hnd)
        else:
            hnd = vmg.ReplacePkgFromName(pkgSplit[0], hnd)
        thCase.package = pkgName
        self.gPkgHandles[thName] = (hnd, pkgName, thCase)

    def ChangeThermoCaseName(self, oldThName, newThName):
        """Change the name of a thermo case"""
        avThCases = self.GetAvThCaseNames()
        if (newThName in avThCases) or (not oldThName in avThCases):
            return
            #Should rise an error
        
        self.gPkgHandles[newThName] = self.gPkgHandles[oldThName]
        self.flashSettings[newThName] = self.flashSettings[oldThName]
        del self.gPkgHandles[oldThName]
        del self.flashSettings[oldThName]

    def DeleteThermoCase(self, thName):
        """Deletes a thermo case"""
        if self.gPkgHandles.has_key(thName):
            vmg.DeletePkg(self.gPkgHandles[thName][0])
            del self.gPkgHandles[thName]
            del self.flashSettings[thName]

    def GetPropPkgString(self, thName):
        """Retrives a string with the selected property package name/s"""  
        if self.gPkgHandles.has_key(thName): return self.gPkgHandles[thName][1]
        return None

    def CheckThermoVersion(self):
        # Check the version of the SeaPkg.dll
        minVersion = 3.85
        minBuild = 30617
        reqVer = 'This version of Sim42 requires SeaPkg v' + str(minVersion) + ' (Build ' + str(minBuild) + ') or higher.  '
        try:
            info = self._VMGCommand(-1, 'Pkg', 'Info')
        except:
            #Earlier versions of SeaPkg do not support CustomCommand
            raise SimError('ErrorValue', reqVer)
        # convert a string a=b;c=d etc. into a dictionary
        infoDict = self._ConvertStringToDict(info[1], ';')
        if 'Version' in infoDict.keys():
            delta = 0.0000000001    # to prevent round off
            thVer = 'Your SeaPkg is v' + infoDict['Version'] + '.  '
            ver = float(infoDict['Version']) + 0.5*delta
            if ver < minVersion - delta:
                # error
                raise SimError('ErrorValue', reqVer + thVer)
            elif abs(ver - minVersion) <= delta:
                if 'Build' in infoDict.keys():
                    thVer = 'Your SeaPkg is v' + infoDict['Version'] + ' (Build ' + infoDict['Build'] + ').  '
                    build = int(infoDict['Build'])
                    if build < minBuild:
                        #error
                        raise SimError('ErrorValue', reqVer + thVer)
                

##IP methods ######################################################################################
    def GetIPMatrixNames(self, thName):
        """Returns the names of the IP Matrices used by a property package"""
        ipInfo = string.strip(vmg.GetInteractionParameterMatrixNames(self.gPkgHandles[thName][0]))
        ipInfo = string.split(ipInfo, ';')
        matrixNames = []
        for i in ipInfo:
            try: matrixNames.append(string.split(i)[1])
            except: pass
        return matrixNames

    def GetNuIPPanes(self, thName, ipMatrName):
        """Returns the amount of panes for an IP matrix (aij, bij,...nij)"""
        ipInfo = string.split(vmg.GetInteractionParameterMatrixNames(self.gPkgHandles[thName][0]))
        if ipMatrName in ipInfo:
            ipMatrNameIdx = ipInfo.index(ipMatrName)
            nuIPPanes = int(ipInfo[ipMatrNameIdx+1])
        else:
            nuIPPanes = None
            
        return nuIPPanes

    def GetIPPaneNames(self, thName, ipMatrName):
        """Returns the names of the panes for an IP matrix (aij, bij,...nij)"""
        #vmg method Returns a string that looks like this
        #SeaStdPengRobinsonZFactor SeaStdAdvPengRobinson 3 kij0 kij1 kij2 ; SEAPRPenelouxMathias SeaMathiasDensity 2 aij bij ;
        ipInfo = string.split(vmg.GetInteractionParameterMatrixNames(self.gPkgHandles[thName][0]))
        # strip out the file name, incase it is identical to a kij name
        paneNames = []
        if ipMatrName in ipInfo:
            ipMatrNameIdx = ipInfo.index(ipMatrName)
            nuIPPanes = int(ipInfo[ipMatrNameIdx+1])
            for paneNameIdx in range(nuIPPanes):
                paneNames.append(ipInfo[ipMatrNameIdx+2+paneNameIdx])
                
        return paneNames
    
    def GetIPValues(self, thName, ipMatrName, pane):
        try:
            hnd = self.gPkgHandles[thName][0]
            vals = vmg.GetBinaryPairValues(hnd, ipMatrName, pane)
            return vals
        except:
            return None
    
    def GetIPValue(self, thName, ipMatrName, cmpName1, cmpName2, pane):
        """Returns the IP value of a specific pane for two compounds"""
        cmpNames = self.GetSelectedCompoundNames(thName)
        try:
            idx1 = cmpNames.index(cmpName1)
            idx2 = cmpNames.index(cmpName2)
            hnd = self.gPkgHandles[thName][0]
            val = vmg.GetBinaryPairValue(hnd, ipMatrName, idx1, idx2, pane)
            return val
        except:
            return None

    def SetIPValue(self, thName, ipMatrName, cmpName1, cmpName2, pane, value):
        """Sets the IP value of a specific pane for two compounds"""
        cmpNames = self.GetSelectedCompoundNames(thName)
        try:
            idx1 = cmpNames.index(cmpName1)
            idx2 = cmpNames.index(cmpName2)
            hnd = self.gPkgHandles[thName][0]
            vmg.SetBinaryPairValue(hnd, ipMatrName, idx1, idx2, pane, value)
            vmg.ResetAijChanged(hnd)
        except:
            try:
                self.parent.InfoMessage('CantSetIP', (value, cmpName1, cmpName2))
            except:
                pass
            return None

    def GetIPInfo(self, thName, ipMatrName, cmpName1, cmpName2):
        cmpNames = self.GetSelectedCompoundNames(thName)
        #try:
        idx1 = cmpNames.index(cmpName1)
        idx2 = cmpNames.index(cmpName2)
        hnd = self.gPkgHandles[thName][0]
        val = vmg.GetBinaryPairInformation(hnd, ipMatrName, idx1, idx2)
        return val
    
####################################################################################################

##Compound methods################################################################################
    def GetAvCompoundNames(self):
        """List of avilable compounds for a specified provider"""
        ucmps = vmg.CompoundNames()
        if len(ucmps) and ( type(ucmps[0]) is type(u'hola') ):
            return map(str, ucmps)
        return ucmps
    
    def AddCompound(self, thName, cmp):
        """Adds a compound to a  thermo case"""        
        hnd = self.gPkgHandles[thName][0]
        vmg.AddCompound(hnd, cmp)

    def AddHypoCompound(self, thName, hypoName, hypoDesc):
        """Adds a hypothetical compound to a  thermo case"""        
        # translate the property keywords
        hnd = self.gPkgHandles[thName][0]
        strDescs = CompoundPropNameFromSimToVmg('String', hypoDesc[0])
        strVals = hypoDesc[1]
        lngDescs = CompoundPropNameFromSimToVmg('Long', hypoDesc[2])
        lngVals = hypoDesc[3]
        dblDescs = CompoundPropNameFromSimToVmg('Double', hypoDesc[4])
        dblVals = hypoDesc[5]        
        vmg.AddGeneralCompound(hnd, strDescs, strVals, lngDescs, lngVals, dblDescs, dblVals)


    def EditCompound(self, thName, cmpIdx, hypoDesc):
        """Adds a hypothetical compound to a  thermo case"""        
        # translate the property keywords
        hnd = self.gPkgHandles[thName][0]
        strDescs = CompoundPropNameFromSimToVmg('String', hypoDesc[0])
        strVals = hypoDesc[1]
        lngDescs = CompoundPropNameFromSimToVmg('Long', hypoDesc[2])
        lngVals = hypoDesc[3]
        dblDescs = CompoundPropNameFromSimToVmg('Double', hypoDesc[4])
        dblVals = hypoDesc[5]
        vmg.EditGeneralCompound(hnd, cmpIdx, strDescs, strVals, lngDescs, lngVals, dblDescs, dblVals)


    def DeleteCompound(self, thName, cmp):
        """Removes a compound from a thermo case"""        
        hnd = self.gPkgHandles[thName][0]
        idx = vmg.CompoundIndexFromName(hnd, cmp)
        vmg.DeleteCompound(hnd, idx)

    def GetSelectedCompoundNames(self, thName):
        """List of selected compounds for a thermo case"""        
        hnd = self.gPkgHandles[thName][0]
        ucmps = vmg.SelectedCompoundNames(hnd)
        if len(ucmps) and type(ucmps[0]) == type(u'hola'):
            return map(str, ucmps)
        return ucmps
    
    def GetHypoteticalCompoundNames(self, thName):
        """List of hypotetical compounds"""
        cmps = self.GetSelectedCompoundNames(thName)
        hypos = []
        nuCmps = len(cmps)
        
        for idx in range(nuCmps):
            family = self.GetSelectedCompoundProperties(thName, idx, 'ChemicalFamily')[0]
            if cmps[idx][-1] == '*' or family.lower() == 'oil':
                hypos.append(cmps[idx])
                
        return hypos

    def GetCompoundPropertyNames(self, propGroup):
        propNames = []
        if propGroup & CMP_ID_GRP or propGroup == None:
            propNames.extend(self.propHandler.GetCmpSimIDPropertyNames())
        if propGroup & CMP_NO_EQDEP_GRP or propGroup == None:
            propNames.extend(self.propHandler.GetCmpSimFixedPropertyNames())
        if propGroup & CMP_EQDEP_GRP or propGroup == None:
            propNames.extend(self.propHandler.GetCmpSimEqDepPropertyNames())
        return propNames

    def GetCompoundProperties(self, thName, cmpName, propNames):
        """return property(ies) for component. String properties can only be obtained 1 by one"""
        hnd = self.gPkgHandles[thName][0]
        if type('s') == type(propNames):
            propCount = 1
            sProp = propNames
            if sProp in self.propHandler.GetCmpSimIDPropertyNames() and sProp != 'Id':
                try: return vmg.CompoundStringProperty(hnd, cmpName, sProp)
                except: return None
        else:
            propCount = len(propNames)
            sProp = ''
            for prop in propNames:
                sProp += prop + ' '
        try:
            return vmg.CompoundDoubleProperty(hnd, cmpName, sProp, propCount)
        except:
            propsOut = []
            for i in propNames:
                try: propsOut.append(vmg.CompoundDoubleProperty(hnd, cmpName, propNames[i], 1)[0])
                except: propsOut.append(None)
            return propsOut
    
    def GetSelectedCompoundProperties(self, thName, cmpNo, propNames):
        """return property(ies) for component number cmpNo"""
        hnd = self.gPkgHandles[thName][0]
        if type('s') == type(propNames):
            propCount = 1
            sProp = propNames
        else:
            propCount = len(propNames)
            sProp = ''
            for prop in propNames:
                sProp += prop + ' '
        sProp = string.strip(sProp)
        if propCount == 1 and sProp in GetSimHypoStrings():
            #get a single string property
            strProp = vmg.SelectedCompoundStringProperty(hnd, cmpNo, sProp)
            return [strProp]
        else:
            # get one or more double properties
            return vmg.SelectedCompoundDoubleProperty(hnd, cmpNo, sProp, propCount)

    def ExchangeCompound(self, thName, cmp1Name, cmp2Name):
        """ exchange the position of cmp1 and cmp2 in the property package"""
        hnd = self.gPkgHandles[thName][0]
        cmps = self.GetSelectedCompoundNames(thName)
        idx1 = cmps.Index(cmp1Name)
        idx2 = cmps.Index(cmp2Name)
        if idx1 != None and idx2 != None:
            vmg.ExchangeCompound(hnd, idx1, idx2)

    def MoveCompound(self, thName, cmp1Name, cmp2Name):
        """ move cmp1 before cmp2"""
        hnd = self.gPkgHandles[thName][0]
        cmps = self.GetSelectedCompoundNames(thName)
        idx1 = cmps.index(cmp1Name)
        if cmp2Name == '$':
            # move before last and exchange
            lng = len(cmps)
            vmg.MoveCompound(hnd, idx1, lng-1)
            vmg.ExchangeCompound(hnd, lng-1, lng-2)
        else:
            idx2 = cmps.index(cmp2Name)
            vmg.MoveCompound(hnd, idx1, idx2)
        return None
        

        
####################################################################################################


##Stream methods ######################################################################################
    def GetPropertyNames(self):
        """Returns a list of supported properties"""
        return self.propHandler.GetSimPropertyNames()

    def GetArrayPropertyNames(self):
        """Returns a list of supported array properties"""
        return self.propHandler.GetSimArrayPropertyNames()

    def SetCommonPropertyNames(self, propList):
        """Sets the common property list"""
        self.propHandler.SetSimCommonPropertyNames(propList)

    def SetCommonArrayPropertyNames(self, propList):
        """Sets the common array property list"""
        self.propHandler.SetSimCommonArrayPropertyNames(propList)

    def GetCommonPropertyNames(self):
        """Sets the common property list"""
        return self.propHandler.GetSimCommonPropertyNames()

    def GetCommonArrayPropertyNames(self):
        """Sets the common array property list"""
        return self.propHandler.GetSimCommonArrayPropertyNames()

    def GetSpecialProperty(self, thName, inputData, frac, prop, nuPoints=None):
        """
        Return a special property. 
        inputData contains any necessary info requiered to calculate the required prop
        frac is just the composition
        """
        hnd = self.gPkgHandles[thName][0]
        global glbVmgObjects
        feed = glbVmgObjects.get((hnd, 'feed'), None)
        if feed == None:
            feed = vmg.RegisterObject(hnd, 'feed')
            glbVmgObjects[(hnd, 'feed')] = feed
            
        hnd = self.gPkgHandles[thName][0]
        try:
            vmgProp = self.propHandler.SpecialPropNamesFromSimToVmg([prop])[0]
        except:
            vmgProp = prop
        
        outputData, status = None, ""
                         
        if vmgProp in ("BOILINGCURVE", "PROPERTYTABLE"):
            #These properties do not use anything extra
            inputData = inputData.upper()
            vmgProp = vmgProp + ' ' + inputData
            vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac)
            if vmgProp == "BOILINGCURVE":
                outputData, status = vmg.GetSpecialProperty(hnd, feed, vmgProp)
            else:
                outputData, status = vmg.GetPropertyTable(hnd, feed, vmgProp, nuPoints)
        
        elif vmgProp in ("hydrate3phasepressure", "hydrate3phasetemperature", "HYDRATECURVE"):
            vmgProp = "%s %s %s" %(vmgProp, 
                                   inputData, 
                                   ' '.join(map(str, frac)))
            #vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac)
            outputData, status = vmg.GetSpecialProperty(hnd, feed, vmgProp)
            
        elif vmgProp in ("hydrate3phaseformation", ):
            try:
                vmgProp = "%s %s %s" %(vmgProp, 
                                       ' '.join(map(str, inputData)), 
                                       ' '.join(map(str, frac)))
                outputData, status = vmg.GetSpecialProperty(hnd, feed, vmgProp)
            except:
                status = "Error"
            
        else:
            try:
                #Generic implementation
                if not isinstance(inputData, str):
                    try: inputData = ' '.join(map(str, inputData))
                    except: inputData = str(inputData)
                vmgProp = vmgProp + ' ' + inputData.upper()
                vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac)
                outputData, status = vmg.GetSpecialProperty(hnd, feed, vmgProp)
            except:
                pass
        return outputData, status
        
    
    
    def GetProperties(self, thName, inProp1, inProp2, phase, frac, propList):
        """
        Return a list of properties corresponding to the types in propList.
        Two intensive variables must be specified (inProp1 and inProp2). Each of
        these is a tuple with the first member being a string property type.
        The second member can be either a scalar or array variable.
        If the input variables and  phase are scalars and frac a one
        dimensional composition array, then each member of the return list will be a scalar.
        If the input variables, phase are Numeric.arrays and frac a two dimensional
        array with one composition per row, then the return value will be a 2 dim
        Numeric.array
        """
        hnd = self.gPkgHandles[thName][0]
        global glbVmgObjects
        feed = glbVmgObjects.get((hnd, 'feed'), None)
        if feed == None:
            feed = vmg.RegisterObject(hnd, 'feed')
            glbVmgObjects[(hnd, 'feed')] = feed

        vap = glbVmgObjects.get((hnd, 'vapor'), None)
        if vap == None:
            vap = vmg.RegisterObject(hnd, 'vapor')
            glbVmgObjects[(hnd, 'vapor')] = vap

        liq0 = glbVmgObjects.get((hnd, 'liquid' + str(0)), None)
        if liq0 == None:
            liq0 = vmg.RegisterObject(hnd, 'liquid' + str(0))
            glbVmgObjects[(hnd, 'liquid' + str(0))] = liq0

        liq1 = glbVmgObjects.get((hnd, 'liquid' + str(1)), None)
        if liq1 == None:
            liq1 = vmg.RegisterObject(hnd, 'liquid' + str(1))
            glbVmgObjects[(hnd, 'liquid' + str(1))] = liq1


        
        needsFlash = 0
        if phase == OVERALL_PHASE:
            needsFlash = 1
            
        phase = self.propHandler.PhaseNameFromSimToVmg(phase)
        
##        feed = vmg.RegisterObject(hnd, 'feed')
        propIDs = self.propHandler.PropNamesFromSimToVmg(propList)
        
        if (phase == OVERALL_PHASE) or \
           (not T_VAR in (inProp1[0], inProp2[0])) or \
           (not P_VAR in (inProp1[0], inProp2[0])):
            needsFlash = 1
##        if needsFlash:
##            vap = vmg.RegisterObject(hnd, 'vap')
##            liq0 = vmg.RegisterObject(hnd, 'liq0')
##            liq1 = vmg.RegisterObject(hnd, 'liq1')
            
        prop1Type, prop2Type = self.propHandler.PropNamesFromSimToVmg((inProp1[0], inProp2[0]))
        prop1 = inProp1[1]
        prop2 = inProp2[1]
        
        if type(prop1) != type(Numeric.array(())):
            vmg.SetMultipleObjectDoubleValues(hnd, feed, (prop1Type, prop2Type, seaPhaseType),
                                              (prop1, prop2, phase))

            vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac)
            if not needsFlash:
                values = vmg.GetMultipleObjectDoubleValues(hnd, feed, propIDs)
                
            else:
                #Do a flash calculation
                flType, props = self.DecideTypeOfFlash((inProp1[0], inProp2[0]), ())
                liqPhases, phasesOut, phasesFracs = 2, [vap, liq0, liq1], []
                phasesFracs = vmg.EquilibriumObjectFlash(hnd, 0, flType, liqPhases, 0, 0, feed, phasesOut, phasesFracs)
                if phase == OVERALL_PHASE:
                    values =  vmg.MultipleBulkObjectDoubleValues(hnd, liqPhases, 0, 0, feed, phasesOut, phasesFracs, propIDs, seaSeapp)
                elif phase == VAPOUR_PHASE: 
                    values = vmg.GetMultipleObjectDoubleValues(hnd, vap, propIDs)
                elif phase == LIQUID_PHASE: 
                    values = vmg.GetMultipleObjectDoubleValues(hnd, liq0, propIDs)

        else:
            valueArrays = []#zeros((len(prop1), len(propIDs)), Float)
            
            if needsFlash:
                flType, props = self.DecideTypeOfFlash((inProp1[0], inProp2[0]), ())
                liqPhases, phasesOut, phasesFracs = 2, [vap, liq0, liq1], []
            
                
            if not needsFlash:
                self._hnd = hnd
                self._feed = feed
                self._prop1Type = prop1Type
                self._prop2Type = prop2Type
                self._propIDs = propIDs
                valueArrays = map(self._PropertiesForIter, prop1, prop2, phase, frac)
            else:
                
                for i in range(len(prop1)):
                    vmg.SetMultipleObjectDoubleValues(hnd, feed, (prop1Type, prop2Type, seaPhaseType),
                                                      (prop1[i], prop2[i], phase[i]))
                    vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac[i])
                    if not needsFlash:
                        valueArrays.append(vmg.GetMultipleObjectDoubleValues(hnd, feed, propIDs))
                    else:
                        #Do a flash calculation
                        phasesFracs = vmg.EquilibriumObjectFlash(hnd, 0, flType, liqPhases, 0, 0, feed, phasesOut, phasesFracs)
                        if phase[i] == OVERALL_PHASE:
                            valueArrays.append(vmg.MultipleBulkObjectDoubleValues(hnd, liqPhases, 0, 0, feed, phasesOut, phasesFracs, propIDs, seaSeapp))
                        elif phase[i] == VAPOUR_PHASE: 
                            valueArrays.append(vmg.GetMultipleObjectDoubleValues(hnd, vap, propIDs))
                        elif phase[i] == LIQUID_PHASE: 
                            valueArrays.append(vmg.GetMultipleObjectDoubleValues(hnd, liq0, propIDs))
                
            values = Numeric.array(valueArrays)
            
        return values
        
        
        
    def GetArrayProperty(self, thName, inProp1, inProp2, phase, frac, property):
        """
        return a Numeric array containing properties of the type 'property'
        Two intensive variables must be specified (inProp1 and inProp2). Each of
        these is a tuple with the first member being a string property type.
        The second member can be either a scalar or array variable.
        If the input variables and phase are scalars, frac should be a single
        composition array and a single array of properties is returned.
        If the input variables and phase are Numeric.arrays, then they must be the same length
        and frac must be a 2d Numeric.array with the same number or rows and each row
        must be a composition.  In this case a 2d Numeric array will be returned with
        one set of results per row
        """
        hnd = self.gPkgHandles[thName][0]
        global glbVmgObjects
        feed = glbVmgObjects.get((hnd, 'feed'), None)
        if feed == None:
            feed = vmg.RegisterObject(hnd, 'feed')
            glbVmgObjects[(hnd, 'feed')] = feed
        
        propID, = self.propHandler.ArrayPropNamesFromSimToVmg((property,))

        prop1Type, prop2Type = self.propHandler.PropNamesFromSimToVmg((inProp1[0], inProp2[0]))
        prop1 = inProp1[1]
        prop2 = inProp2[1]

        if type(prop1) != type(Numeric.array(())):
            vmg.SetMultipleObjectDoubleValues(hnd, feed,
                                              (prop1Type, prop2Type, seaPhaseType),
                                              (prop1, prop2, phase))

            if propID == seaComposition:
                vmg.SetObjectDoubleArrayValues(hnd, feed, seaStdLiqVolFraction, frac)
            else:
                vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac)

            values = vmg.GetObjectDoubleArrayValues(hnd, feed, propID, 0)
        else:
            #valueArrays = []
            #if 1:
            self._hnd = hnd
            self._feed = feed
            self._prop1Type = prop1Type
            self._prop2Type = prop2Type
            self._propID = propID
            valueArrays = map(self._ArrPropertiesForIter, prop1, prop2, phase, frac)
            #else:
                #for i in range(len(prop1)):
                    #vmg.SetMultipleObjectDoubleValues(hnd, feed,
                                                      #(prop1Type, prop2Type, seaPhaseType),
                                                      #(prop1[i], prop2[i], phase[i]))
                    #vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac[i])
                    #valueArrays.append(vmg.GetObjectDoubleArrayValues(hnd, feed, propID, 0))
                
            values = Numeric.array(valueArrays)
       
        return values        
        
    def GetIdealKValues(self, thName, t, p):
        """
        return array of initial K values based on t and p
        t and p can be scalars in which case an array nComp long is returned
        if t and p are Numeric.arrays they must be the same length and a matrix
        with that many rows of nComp columns will be returned
        """

        hnd = self.gPkgHandles[thName][0]
        global glbVmgObjects
        feed = glbVmgObjects.get((hnd, 'feed'), None)
        if feed == None:
            feed = vmg.RegisterObject(hnd, 'feed')
            glbVmgObjects[(hnd, 'feed')] = feed
        
##        feed = vmg.RegisterObject(hnd, 'feed')
        
        if type(t) != type(Numeric.array(())):
            vmg.SetMultipleObjectDoubleValues(hnd, feed, (seaTemperature, seaPressure, seaPhaseType), (t, p, seaVapourPhase))
            kvalues = vmg.GetObjectDoubleArrayValues(hnd, feed, seaIdealKValue, 0)
        else:
            kArrays = []
            for i in range(len(t)):
                vmg.SetMultipleObjectDoubleValues(hnd, feed, (seaTemperature, seaPressure, seaPhaseType),
                                                  (t[i], p[i], seaVapourPhase))
                kArrays.append(vmg.GetObjectDoubleArrayValues(hnd, feed, seaIdealKValue, 0))
                
            kvalues = Numeric.array(kArrays)
       
##        vmg.UnregisterObject(hnd, feed)
        return kvalues
    
    def GetMolecularWeightValues(self, thName):
        """shortcut method to get the molecular weight vector of a thermo case"""
        
        hnd = self.gPkgHandles[thName][0]
        global glbVmgObjects
        feed = glbVmgObjects.get((hnd, 'feed'), None)
        if feed == None:
            feed = vmg.RegisterObject(hnd, 'feed')
            glbVmgObjects[(hnd, 'feed')] = feed
        try:
            return vmg.GetObjectDoubleArrayValues(hnd, feed, seaMolecularWeightArray, 0)
        except:
            return None
        
    
    #def _CmpMWForIter(self, cmpNo):
        #return vmg.SelectedCompoundDoubleProperty(self._hnd, cmpNo, 'MolecularWeight', 1)
    
    
    def _PropertiesForIter(self, prop1, prop2, phase, frac):
        feed = self._feed
        hnd = self._hnd
        vmg.SetMultipleObjectDoubleValues(hnd, feed, (self._prop1Type, self._prop2Type, seaPhaseType), (prop1, prop2, phase))
        vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac)
        return  vmg.GetMultipleObjectDoubleValues(hnd, feed, self._propIDs)
        
    def _ArrPropertiesForIter(self, prop1, prop2, phase, frac):
        feed = self._feed
        hnd = self._hnd
        vmg.SetMultipleObjectDoubleValues(hnd, feed, (self._prop1Type, self._prop2Type, seaPhaseType), (prop1, prop2, phase))
        vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, frac)
        return vmg.GetObjectDoubleArrayValues(hnd, feed, self._propID, 0)    
    
####################################################################################################


##Flash methods ####################################################################################
    def GetFlashSettingsInfo(self, thName):
        """Returns a dictionary with objects describing the flash settings"""
        return self.flashSettingsInfoDict
        
    def SetFlashSetting(self, thName, settingName, value):
        hnd = self.gPkgHandles[thName][0]
        vmgSettingName = self.flashSettingsInfoDict[settingName].localName
        myVal = value
        if vmgSettingName == seaVapFracSpec:
            myVal = self.flashSettingsInfoDict[settingName].options.index(value)
        vmg.SetFlashSetting(hnd, vmgSettingName, myVal)
        
        settingsDict = self.flashSettings[thName]
        settingsDict[settingName] = value
        
    def GetFlashSetting(self, thName, settingName):
        """Get the value of a flash setting"""
        #Should come directly form vmg
        settingsDict = self.flashSettings[thName]
        return settingsDict[settingName]
        
                            
    def GetPropNamesCapableOfFlash(self, thName):
        """Returns a tuple with prop names that can be used to calculate a flash"""
        return self.propHandler.GetFlashPropertyNames()
    
    
    def Flash(self, thName, cmps, properties, liqPhCount, 
              propList=None, thThermoAdmin=None, nuSolids=0,
              stdVolRefT=None):
        """Performs a Flash calculation

        thName -- Name of the thermo case
        cmps -- Instance of Variables.CompoundList
        properties -- Instance of Variables.MaterialPropertyDict
        liqPhCount -- Number of liquid phases

        returns a FlashResults object
        """         

        global glbVmgObjects
        
        if not cmps.AreValuesReady(): return None
        fixed = properties.GetNamesOfKnownFixedVars(CANFLASH_PROP)
        if len(fixed) > 2:
            port = properties.values()[0].GetParent()
            parentPath = ''
            if port:
                parentPath = port.GetPath()
            raise SimError ('OverspecFlash', (parentPath, len(fixed), ' '.join(fixed))) 
        calc = properties.GetNamesOfKnownCalcVars(CANFLASH_PROP)
        returnedType = self.DecideTypeOfFlash(fixed, calc)
        if returnedType == None: return None
        flType, vars = returnedType
        phasesFracs = []
  
        if VPFRAC_VAR in vars:
            flType, vars, phasesFracs = self.CheckForADiffFlash(flType, vars, phasesFracs, properties)
        vals = []
        for i in vars: vals.append(properties[i].GetValue())
        
        vmprops = self.propHandler.PropNamesFromSimToVmg(vars)
        hnd = self.gPkgHandles[thName][0]

        feed = glbVmgObjects.get((hnd, 'feed'), None)
        if feed == None:
            feed = vmg.RegisterObject(hnd, 'feed')
            glbVmgObjects[(hnd, 'feed')] = feed

        vap = glbVmgObjects.get((hnd, 'vapor'), None)
        if vap == None:
            vap = vmg.RegisterObject(hnd, 'vapor')
            glbVmgObjects[(hnd, 'vapor')] = vap

        liq1Id = glbVmgObjects.get((hnd, 'liquid' + str(0)), None)
        if liq1Id == None:
            liq1Id = vmg.RegisterObject(hnd, 'liquid' + str(0))
            glbVmgObjects[(hnd, 'liquid' + str(0))] = liq1Id

        liq2Id = glbVmgObjects.get((hnd, 'liquid' + str(1)), None)
        if liq2Id == None:
            liq2Id = vmg.RegisterObject(hnd, 'liquid' + str(1))
            glbVmgObjects[(hnd, 'liquid' + str(1))] = liq2Id

        liq3Id = glbVmgObjects.get((hnd, 'liquid' + str(2)), None)
        if liq3Id == None:
            liq3Id = vmg.RegisterObject(hnd, 'liquid' + str(2))
            glbVmgObjects[(hnd, 'liquid' + str(2))] = liq3Id

        bulkLiqId = glbVmgObjects.get((hnd, 'BulkLiq'), None)
        if bulkLiqId == None:
            bulkLiqId = vmg.RegisterObject(hnd, 'BulkLiq')
            glbVmgObjects[(hnd, 'BulkLiq')] = bulkLiqId

        solidId = glbVmgObjects.get((hnd, 'solid'), None)
        if solidId == None:
            solidId = vmg.RegisterObject(hnd, 'solid')
            glbVmgObjects[(hnd, 'solid')] = solidId

        
        liqPhases = max(liqPhCount, 2) #Minimum 2
        withSolid = min(nuSolids, 1)   #Maximum 1
        initFromInput = 0
        othersCount = 0
        phasesOut = [vap, liq1Id, liq2Id]
        if liqPhases == 3:
            phasesOut.append(liq3Id)
        #VMG uses the solid as the first phase
        if withSolid:
            phasesOut.insert(0, solidId)
            if nuSolids > 1:
                thThermoAdmin.InfoMessage('TooManySolidPhases', (nuSolids, thName))
                
        bulkComp = cmps.GetValues()
        vmg.SetObjectDoubleArrayValues(hnd, feed, seaComposition, bulkComp)
        vmg.SetMultipleObjectDoubleValues(hnd, feed, vmprops, vals)
        try:
            phasesFracs = vmg.EquilibriumObjectFlash(hnd, initFromInput, flType, liqPhases, withSolid,
                                                     othersCount, feed, phasesOut, phasesFracs)
        except vmg.VMGwarning, e:
            thThermoAdmin.InfoMessage('CMDVMGWarning', (str(e),), MessageHandler.infoMessage)
            
        #sim42 uses the solid as the last phase
        #if withSolid:
            #phasesFracs = list(phasesFracs) 
            #temp = phasesFracs.pop(0)
            #phasesFracs.append(temp)
            #temp = phasesOut.pop(0)
            #phasesOut.append(temp)
        
            
        #If propList==None get the common properties
        if not propList:
            propsNames = self.propHandler.GetVmgCommonPropertyNames()
            propsNamesOut = self.propHandler.GetSimCommonPropertyNames()    
        else:
            propsNames = self.propHandler.PropNamesFromSimToVmg(propList)
            propsNamesOut = propList
        
        #Do we need to calculate std properties ?
        origPhasesOut = list(phasesOut)
        if seaStdLiqVolume in propsNames: doStdVol = True
        else: doStdVol = False
        if seaStdLiqDensity in propsNames: doStdDen = True
        else: doStdDen = False
            
        #Array properties besides composition
        arrPropNames = self.propHandler.GetVmgCommonArrayPropertyNames()
        arrPropNamesOut = self.propHandler.GetSimCommonArrayPropertyNames()

        #Get bulk values        
        bulkProps =  vmg.MultipleBulkObjectDoubleValues(hnd, liqPhases, withSolid, othersCount, feed, phasesOut,
                                                        phasesFracs, propsNames, seaSeapp)
        
        bulkArrProps = []
        
        
        #sim42 uses the solid as the last phase
        if withSolid:
            phasesFracs = list(phasesFracs) 
            temp = phasesFracs.pop(0)
            phasesFracs.append(temp)
            temp = phasesOut.pop(0)
            phasesOut.append(temp)
            
            
        for prop in arrPropNames:
            vals = vmg.GetObjectDoubleArrayValues(hnd, feed, prop, -1)
            bulkArrProps.append(vals)

        keepValue = -1
        liqComposit = vmg.GetObjectDoubleArrayValues(hnd, liq1Id, seaComposition, keepValue)
        
        if liqPhCount == 1:
           if phasesFracs[2] != 0.0:
               # spec 1 liq, flash returns 2 liqs, lump the 2 liqs into 1
               if thThermoAdmin != None:
                   thThermoAdmin.InfoMessage('LumpLiqs', phasesFracs[2])
               # When MultipleBulkObjectDoubleValues is called, the individual phase properties
               #    should have been calculated. I can use the MixTwoObjects method to get the
               #    bulk liquid properties
       
               fr1 = phasesFracs[1] / (phasesFracs[1] + phasesFracs[2])
               vmg.MixTwoObjects(hnd, bulkLiqId, liq1Id, liq2Id, fr1, propsNames)
               # fixup phasesFracs
               phasesFracs[1] = phasesFracs[1] + phasesFracs[2]
               phasesFracs = list(phasesFracs)
               del phasesFracs[2]
               phasesFracs = array(phasesFracs, Float)
               
               # fixup phasesOut : remove the liq1 and liq2
               phasesOut.remove(liq1Id)
               phasesOut.remove(liq2Id)
               phasesOut.insert(1, bulkLiqId)
           else:
               #Just fix up the lists fro removing the second liquid so the solids are in the correct idx
               phasesFracs = list(phasesFracs)
               del phasesFracs[2]
               phasesFracs = array(phasesFracs, Float)
               phasesOut.remove(liq2Id)
               
        else:
            bulkLiqId = -1

        phasesComposit = []
        phasesArrProps = []
        phasesProps = []
        #keepValue = -1
        for i in phasesOut:
            #composition
            composit = vmg.GetObjectDoubleArrayValues(hnd, i, seaComposition, keepValue)
            phasesComposit.append(composit)

            # Array props
            # Cannot get bulk array props
            
            lstArrProps = []
            for prop in arrPropNames:
                vals = vmg.GetObjectDoubleArrayValues(hnd, i, prop, keepValue)
                lstArrProps.append(vals)
            phasesArrProps.append(lstArrProps)

            #Phase props
            props = vmg.GetMultipleObjectDoubleValues(hnd, i, propsNames)
            phasesProps.append(props)

        #Do the density stuff
        if doStdVol or doStdDen:
            if not stdVolRefT: stdVolRefT = 288.15
            vmg.SetMultipleObjectDoubleValues(hnd, liq1Id, [seaTemperature], [stdVolRefT])
            vmg.SetObjectDoubleArrayValues(hnd, liq1Id, seaComposition, bulkComp)
            stdVol, stdDen = vmg.GetMultipleObjectDoubleValues(hnd, liq1Id, [seaStdLiqVolume, seaStdLiqDensity])
            if doStdVol: 
                idxStdVol = list(propsNames).index(seaStdLiqVolume)
                bulkProps[idxStdVol] = stdVol
            if doStdDen: 
                idxStdDen = list(propsNames).index(seaStdLiqDensity)
                bulkProps[idxStdDen] = stdDen

            for i in range(len(phasesProps)):
                vmg.SetObjectDoubleArrayValues(hnd, liq1Id, seaComposition, phasesComposit[i])
                stdVol, stdDen = vmg.GetMultipleObjectDoubleValues(hnd, liq1Id, [seaStdLiqVolume, seaStdLiqDensity])
                if doStdVol: 
                    phasesProps[i][idxStdVol] = stdVol
                if doStdDen: 
                    phasesProps[i][idxStdDen] = stdDen
                

        return FlashResults(propsNamesOut, arrPropNamesOut, bulkComp, bulkProps, bulkArrProps,
                            phasesFracs, phasesComposit, phasesProps, phasesArrProps)

    def DecideTypeOfFlash(self, fixed, calc):
        """Decides which type of flash to perform depending on the info av"""
        #This function needs better ideas
        if len(fixed) == 0:
            lookin = calc #Flash with calc vars
        elif len(fixed) == 1:
            lookin = None #Flash with one fixed var and one calc var
        elif len(fixed) == 2:
            lookin = fixed #Flash with  both fixed vars
        else:
            lookin = None #Too bad :( , the thing has something wrong

        if lookin != None:
            if P_VAR in lookin and H_VAR in lookin: return seaPHFlash, (P_VAR, H_VAR)
            if T_VAR in lookin and H_VAR in lookin: return seaTHFlash, (T_VAR, H_VAR)
            if T_VAR in lookin and P_VAR in lookin: return seaPTFlash, (T_VAR, P_VAR)
            if P_VAR in lookin and VPFRAC_VAR in lookin: return seaPVFlash, (P_VAR, VPFRAC_VAR)
            if T_VAR in lookin and VPFRAC_VAR in lookin: return seaTVFlash, (T_VAR, VPFRAC_VAR)
            if P_VAR in lookin and S_VAR in lookin: return seaPSFlash, (P_VAR, S_VAR)
        if T_VAR in fixed:
            if H_VAR in calc: 
                if P_VAR in calc:
                    #Better do a PH flash with both calculated rather than using the spec T
                    return seaPHFlash, (P_VAR, H_VAR)
                return seaTHFlash, (T_VAR, H_VAR)
            if P_VAR in calc: return seaPTFlash, (T_VAR, P_VAR)
            if VPFRAC_VAR in calc: return seaTVFlash, (T_VAR, VPFRAC_VAR)
        if P_VAR in fixed:
            if H_VAR in calc: return seaPHFlash, (P_VAR, H_VAR)
            if T_VAR in calc: return seaPTFlash, (P_VAR, T_VAR)
            if VPFRAC_VAR in calc: return seaPVFlash, (P_VAR, VPFRAC_VAR)
            if S_VAR in calc: return seaPSFlash, (P_VAR, S_VAR)
        if VPFRAC_VAR in fixed:
            if T_VAR in calc: return seaTVFlash, (VPFRAC_VAR, T_VAR)
            if P_VAR in calc: return seaPVFlash, (VPFRAC_VAR, P_VAR)
        if S_VAR in fixed:
            if P_VAR in calc: return seaPSFlash, (S_VAR, P_VAR)
        if H_VAR in fixed:
            if P_VAR in calc: return seaPHFlash, (H_VAR, P_VAR)
        return None

    def CheckForADiffFlash(self, flType, vars, phasesFracs, properties):
        """If TVFlash or PVFlash = flTyp, check if DeworBub flash ispossible"""
        if flType == seaTVFlash:
            if properties[VPFRAC_VAR].GetValue() >= 0.9999999 and \
               properties[VPFRAC_VAR].GetValue() <= 1.0000001:
                flType = seaDewP
            elif properties[VPFRAC_VAR].GetValue() >= -0.0000001 and \
                 properties[VPFRAC_VAR].GetValue() <= 0.0000001:
                flType = seaBubbleP
            else:
                phasesFracs.append(properties[VPFRAC_VAR].GetValue())
            vars = (T_VAR,)
        elif flType == seaPVFlash:
            if properties[VPFRAC_VAR].GetValue() >= 0.9999999 and \
               properties[VPFRAC_VAR].GetValue() <= 1.0000001:
                flType = seaDewT
            elif properties[VPFRAC_VAR].GetValue() >= -0.0000001 and \
                 properties[VPFRAC_VAR].GetValue() <= 0.0000001:
                flType = seaBubbleT
            else:
                phasesFracs.append(properties[VPFRAC_VAR].GetValue())
            vars = (P_VAR,)
        return flType, vars, phasesFracs


    def PhaseEnvelope(self, thName, cmps, vapFraction, pressure, maxPoints, pList=None):
        hnd = self.gPkgHandles[thName][0]
        global glbVmgObjects
        feedId = glbVmgObjects.get((hnd, 'feed'), None)
        if feedId == None:
            feedId = vmg.RegisterObject(hnd, 'feed')
            glbVmgObjects[(hnd, 'feed')] = feedId
            
##        hnd = self.gPkgHandles[thName][0]
##        feedId = vmg.RegisterObject(hnd, 'feed')
        #bulkComp = cmps.GetValues()
        vmg.DefineObject(hnd, feedId, seaLiquidPhase, 298.15, pressure, cmps, seaSeapp)
        pCount = 0
        if (pList): pCount = len(pList)
        nc = len(cmps)
        try:
            results = vmg.PhaseEnvelope(hnd, feedId, pCount, pList, vapFraction, nc, maxPoints)
        except:
            # continue the calculation when failed
            pass
##        vmg.UnregisterObject(hnd, feedId)

        #return code, message, points, convert the array into an matrix
        retCode = results[0]
        msg = results[1]
        npt = results[2]
        vars = results[3]

        types = []
        pVals = []
        tVals = []
        kVals = []
        
        ret = []
        i1 = 0
        for i in range(npt):
            i2 = i1+nc+3
            types.append(vars[i1])
            pVals.append(vars[i1+1])
            tVals.append(vars[i1+2])
            kVals.append(vars[i1+3:i2])
            i1 = i2
        return EnvelopeResults(retCode, msg, npt, types, pVals, tVals, kVals)


####################################################################################################


##Extra methods ######################################################################################
    def HaveSameValues(self, seq1, seq2):
        """Order doesn't matter"""
        for i in seq1:
            if i not in seq2: return 0
        return 1

    def GetValuesInOrder(self, baseNames, destNames, valsIn):
        """Change the order of values

        baseNames -- List with names of the corresponding values in valsIn
        destName -- Order of the values out
        valsIn -- List of values in the order of baseNames

        Returns valsIn in the order of destNames assuming that valsIn is in the
        order of baseNames.
        Useful when the compounds across different things are the same,
        but in different order

        """
        size = len(baseNames)
        if size != len(destNames) or size != len(valsIn): return None
        valsOut = []
        for i in range(size):
            for j in range(size):
                if destNames[i] == baseNames[j]: valsOut.append(valsIn[j])
        return valsOut
####################################################################################################


##Save and load methods ############################################################################
    def GetThermoXMLString(self):
        """Puts the basic thermodynamic data in an xml string"""
        return self._BuildThermoXMLString(self.gPkgHandles)

    def SetThermoXMLString(self, xmlString):
        """Builds the prop pkg from an xml string"""
        self.gPkgHandles = self._BuildThermoFromXMLString(xmlString)
        
    def _BuildThermoXMLString(self, gPkgHandles):
        doc = minidom.Document()
        
        thMainNode = doc.createElement('ThermoProvider')
        thMainNode.setAttribute('Name', 'VirtualMaterials')
        thMainNode.setAttribute('Version', '3.6')
        
        #Loop for every handle (thCaseNode)
        for thCaseName in gPkgHandles.keys():
            thCaseNode = doc.createElement('ThermoCase')
            thCaseNode.setAttribute('Name', thCaseName)

            #Build property Package node
            pkgsList = string.split(gPkgHandles[thCaseName][1])
            if len(pkgsList) == 1: pkgsList.append(pkgsList[0]) #Duplicate prop pkg for liqphase
            pkgsNode = doc.createElement("PropertyPackages")
            pkgsNode.setAttribute('solidSupp', '0')
            #Vapor node to pkg node
            vapNode = doc.createElement('Vapor')
            vapVal = doc.createTextNode(pkgsList[0])
            vapNode.appendChild(vapVal)
            pkgsNode.appendChild(vapNode)
            #Liquid node to pkg node
            liqNode = doc.createElement('Liquid')
            liqVal = doc.createTextNode(pkgsList[1])
            liqNode.appendChild(liqVal)
            pkgsNode.appendChild(liqNode)

            #Build compounds node            
            cmpList = vmg.SelectedCompoundNames(gPkgHandles[thCaseName][0])
            cmpsNode = doc.createElement('Compounds')
            cmpsNode.setAttribute('NumComp', str(len(cmpList)))
            for i in cmpList:
                cmpNode = doc.createElement('Compound')
                cmpNode.setAttribute('Name', i)
                cmpsNode.appendChild(cmpNode)

            #Build main node            
            thCaseNode.appendChild(pkgsNode)
            thCaseNode.appendChild(cmpsNode)
            thMainNode.appendChild(thCaseNode)
        doc.appendChild(thMainNode)
        xmlString = doc.toxml()
    ##    xmlString = doc.toprettyxml()
        doc.unlink()
        return xmlString


    def _BuildThermoFromXMLString(self, xmlString):
        vmgContHand = self._VMGContentHandlerXML()    
        parser = parseString(xmlString, vmgContHand)

        gPkgHandles = vmgContHand.GetPkgHandles()
        vmgContHand = None
        return gPkgHandles

    class _VMGContentHandlerXML(ContentHandler):
        def __init__(self):
            vmg.TerminatePkg()
            vmg.InitializePkg()
            self.hnds = {} #List with first value = hnd and second value is the proppkg string
            self.propPkg = ''
            self.invapPkg = 0
            self.inliqPkg = 0

        def GetPkgHandles(self):
            return self.hnds
        
        def startElement(self, name, attrs):
            if name == 'ThermoProvider':
                self.name = str(normalize_whitespace(attrs.get('Name', "")))
            elif name == 'ThermoCase':
                self.temphndName = str(normalize_whitespace(attrs.get('Name', "")))
            elif name == 'PropertyPackages':
                self.solidSupp = int(attrs.get('solidSupp', ""))
                self.propPkg = ''
                self.pkgSet = 0
            elif name == 'Vapor':
                self.invapPkg = 1
                self.vapPkg = ""
            elif name == 'Liquid':
                self.inliqPkg = 1
                self.liqPkg = ""
            elif name == 'Compound':
                if self.pkgSet:
                    cmp = normalize_whitespace(attrs.get('Name', ""))
                    vmg.AddCompound(self.hnds[self.temphndName][0], cmp)
                    
        def characters(self, ch):
            if self.invapPkg: self.vapPkg = self.vapPkg + str(ch)
            elif self.inliqPkg: self.liqPkg = self.liqPkg + str(ch)
                
        def endElement(self, name):
            if name == 'PropertyPackages':
                tst = string.split(self.propPkg)
                if ' ' in self.propPkg and (tst[0] not in tst[1:]):
                    handle = vmg.AddAggregatePkgFromName(self.propPkg)
                else:
                    handle = vmg.AddPkgFromName(tst[0])
                self.hnds[self.temphndName] = handle, self.propPkg
                self.propPkg = ''
                self.pkgSet = 1
            elif name == 'Vapor':
                self.invapPkg = 0
                self.propPkg = self.vapPkg
            elif name == 'Liquid':
                self.inliqPkg = 0
                if not self.vapPkg == self.liqPkg:
                    self.propPkg = self.propPkg + ' ' + self.liqPkg
            elif name == 'ThermoCase':
                self.pkgSet = 0


####################################################################################################



##Oil Methods ######################################################################################

    def CustomCommand(self, thCase, cmd):
        # For VMG command the first token is the command key
        # incoming command tokens are separated by dot
        # returned results (retCode, result string)
        (key, remaining) = string.split(cmd, '.', 1)
        
        hnd = -1
        if thCase:
            hnd = self.gPkgHandles[thCase][0]
        
        # convert the tokens separator from '.' to to white space
        remaining = self._ConvertString(remaining)
            
        #Is this a shortcut method for interaction parameter (kij) processing ?
        if key in self.GetCustomIPCommands():
            try:
                return self.ProcessCustomIPCommand(thCase, key, remaining.split())
            except:
                return (1, '')
            
        return self._VMGCommand(hnd, key, remaining)
    

    def GetCustomIPCommands(self):
        return ['SetIPValue', 'GetIPValue', 'GetIPInfo', 
                'GetIPInfoFromCmpIdx', 'GetAllIPDataForPairCmpIdx']
    
    def ProcessCustomIPCommand(self, thCase, cmd, tokens):
        """This are shortcut methods to retrive information quick from interaction parameters"""
        
        ## DO NOT FORGET TO ADD ANY NEW METHOD TO GetCustomIPCommands !!!
        
        if cmd == 'SetIPValue':
            
            #f = open('C:\\temp.txt', 'w')
            #f.write(cmd)
            #f.write('\n')
            #f.write(str(tokens) + '\n')
            
            #Matrix name
            ipMatrName = tokens[0]
            #f.write(ipMatrName + '\n')
            
            #Pane name
            paneName = str(tokens[1])
            #f.write(paneName + '\n')
            paneNames = self.GetIPPaneNames(thCase, str(ipMatrName))
            #f.write(str(paneNames) + '\n')
            paneIdx = paneNames.index(paneName)
            #f.write(str(paneIdx) + '\n')
            
            #List compound names
            cmpNames = self.GetSelectedCompoundNames(thCase)
            
            #Compound 1 name
            cmpName1 = str(tokens[2])
            if not (cmpName1 in cmpNames) and ('_' in cmpName1):
                cmpName1 = re.sub('_', ' ', cmpName1)
            #f.write(cmpName1 + '\n')
            
            #Compound 2 name
            cmpName2 = str(tokens[3])
            if not (cmpName2 in cmpNames) and ('_' in cmpName2):
                cmpName2 = re.sub('_', ' ', cmpName2)
            #f.write(cmpName2 + '\n')
            
            #Value being set
            value = float(tokens[4])
            #f.write(str(value) + '\n\n')
            #f.close()
            
            #Process it
            self.SetIPValue(thCase, ipMatrName, cmpName1, cmpName2, paneIdx, value)
            
            #All the unit ops should resolve
            thAdmin = self.GetParent()
            if thAdmin != None:
                thAdmin.ForgetUnitOpsUsingThermo(self.GetName(), thCase)
            
            return (0, 'OK')
        
        if cmd == 'GetIPValue':
            #Matrix name
            ipMatrName = tokens[0]
            
            #Pane name
            paneName = str(tokens[1])
            paneNames = self.GetIPPaneNames(thCase, str(ipMatrName))
            paneIdx = paneNames.index(paneName)
            
            #List compound names
            cmpNames = self.GetSelectedCompoundNames(thCase)
            
            #Compound 1 name
            cmpName1 = str(tokens[2])
            if not (cmpName1 in cmpNames) and ('_' in cmpName1):
                cmpName1 = re.sub('_', ' ', cmpName1)
            
            #Compound 2 name
            cmpName2 = str(tokens[3])
            if not (cmpName2 in cmpNames) and ('_' in cmpName2):
                cmpName2 = re.sub('_', ' ', cmpName2)
            
            #Process it
            value = self.GetIPValue(thCase, ipMatrName, cmpName1, cmpName2, paneIdx)
        
            return (0, value)
        
        if cmd == 'GetIPInfo':
            tknIdx = 0
            
            #Matrix name
            ipMatrName = tokens[tknIdx]
            tknIdx += 1
            
            #Pane name
            paneName = str(tokens[tknIdx])
            paneNames = self.GetIPPaneNames(thCase, str(ipMatrName))
            if paneName in paneNames:
                #If paneName is not there, then assume that current token is the name of a compound
                paneIdx = paneNames.index(paneName)
                tknIdx += 1
            
            #List compound names
            cmpNames = self.GetSelectedCompoundNames(thCase)
            
            #Compound 1 name
            cmpName1 = str(tokens[tknIdx])
            if not (cmpName1 in cmpNames) and ('_' in cmpName1):
                cmpName1 = re.sub('_', ' ', cmpName1)
            tknIdx += 1
            
            #Compound 2 name
            cmpName2 = str(tokens[tknIdx])
            if not (cmpName2 in cmpNames) and ('_' in cmpName2):
                cmpName2 = re.sub('_', ' ', cmpName2)
            tknIdx += 1
            
            
            #Process it
            value = self.GetIPInfo(thCase, ipMatrName, cmpName1, cmpName2)
        
            return (0, value)
        
        if cmd == 'GetIPInfoFromCmpIdx':
            tknIdx = 0         
            
            #Matrix name
            ipMatrName = str(tokens[tknIdx])
            tknIdx += 1
            
            #Pane name
            paneName = str(tokens[tknIdx])
            paneNames = self.GetIPPaneNames(thCase, ipMatrName)
            if paneName in paneNames:
                #If paneName is not there, then assume that current token is the name of a compound
                paneIdx = paneNames.index(paneName)
                tknIdx += 1
            
            
            #List compound names
            cmpNames = self.GetSelectedCompoundNames(thCase)
            
            #Compound 1 name
            cmpName1 = cmpNames[int(tokens[tknIdx])]
            tknIdx += 1
            
            #Compound 2 name
            cmpName2 = cmpNames[int(tokens[tknIdx])]
            tknIdx += 1
            
            #Process it
            value = self.GetIPInfo(thCase, ipMatrName, cmpName1, cmpName2)
            
            return (0, value)
        
        
        if cmd == 'GetAllIPDataForPairCmpIdx':
            
            #List compound names
            cmpNames = self.GetSelectedCompoundNames(thCase)

            #Compound 1 name
            cmpIdx1 = int(tokens[0])
            cmpName1 = cmpNames[cmpIdx1]
            
            #Compound 2 name
            cmpIdx2 = int(tokens[1])
            cmpName2 = cmpNames[cmpIdx2]
                
            retVal = ''
            ipMatrNames = self.GetIPMatrixNames(thCase)
            ipMatrNames.sort()
            
            #Loop for k i j
            for ipMatrName in ipMatrNames:
                paneIdx = 0
                for paneName in self.GetIPPaneNames(thCase, ipMatrName):
                    value = self.GetIPValue(thCase, ipMatrName, cmpName1, cmpName2, paneIdx)
                    retVal += '%s %s %i %i %f;' %(ipMatrName, paneName, cmpIdx1, cmpIdx2, value)
                    paneIdx += 1
                    
            #Now loop for k j i
            cmpIdx1, cmpIdx2 = cmpIdx2, cmpIdx1
            cmpName1, cmpName2 = cmpName2, cmpName1
            for ipMatrName in ipMatrNames:
                paneIdx = 0
                for paneName in self.GetIPPaneNames(thCase, ipMatrName):
                    value = self.GetIPValue(thCase, ipMatrName, cmpName1, cmpName2, paneIdx)
                    retVal += '%s %s %i %i %f;' %(ipMatrName, paneName, cmpIdx1, cmpIdx2, value)
                    paneIdx += 1
                    
            #remove last character
            if retVal[-1] == ';': retVal = retVal[:-1]
            
            return (0, retVal)
        
                
    def InstallOil(self, thCase, assayObj):
        assayName = assayObj.parentObj.name + '.' + assayObj.name        
        cmd = 'Oil.InstallOil.' + assayName
        return self.CustomCommand(thCase, cmd)

    def DeletePseudos(self, thCase, assayObj):
        assayName = assayObj.parentObj.name + '.' + assayObj.name        
        cmd = 'Oil.DeletePseudos.' + assayName
        return self.CustomCommand(thCase, cmd)

    def PseudoList(self, thCase, assayObj):
        oilName = assayObj.parentObj.name
        assayName = assayObj.name        
        hnd = self.gPkgHandles[thCase][0]
        if self._AssayExists(hnd, oilName, assayName) == 1:
            cmd = 'Oil.PseudoList.' + oilName + '.' + assayName
            results = self.CustomCommand(thCase, cmd)            
            return string.split(results[1], ';')
        else:
            return None

    def UpdateOil(self, thCase, assayObj):
        assayName = assayObj.parentObj.name + '.' + assayObj.name
        cmd = 'Oil.UpdateOil.' + assayName
        return self.CustomCommand(thCase, cmd)

    def GetOilComposition(self, thCase, assayObj):
        assayName = assayObj.parentObj.name + '.' + assayObj.name        
        cmd = 'Oil.GetOilComposition.' + assayName
        result = self.CustomCommand(thCase, cmd)
        if result[0] >= 0 and result[1] != '':
            cmp = string.split(result[1], ';')
        else:
            cmp = None
        return cmp


    def BlendAssay(self, thCase, blend):
        hnd = self.gPkgHandles[thCase][0]
        nAssay = len(blend.assayNames)
        oilName = blend.parentObj.name
        cmd = 'Blend ' + blend.name + ' ' + oilName + ' ' + str(nAssay)
        # count number of assays
        for assay in blend.assays:
            cmd = cmd + ' ' + assay.name
            
        result = self._VMGCommand(hnd, 'Oil', cmd)
        if result[0] == 0:
            #ok, retrieve the blend info (light ends, curves) data
            self.UpdateAssayPropertiesFromPkg(thCase, blend)
            blend.IsUpToDate(1)
            blend.state = Oils.AssayStateCut
        return result

    def SetAssayParameterValue(self, thCase, paramObj):
        assayObj = paramObj.parentObj
        if isinstance(assayObj, Oils.Assay):
            oilName = assayObj.parentObj.name
            assayName = assayObj.name
            hnd = self.gPkgHandles[thCase][0]
            if self._AssayExists(hnd, oilName, assayName):            
                value = paramObj.GetValue()
                if value and str(value) != '':
                    cmd = 'AssayBulkValue ' + oilName + ' ' + assayName + ' ' + paramObj.name + ' ' +  str(value)
                    result = self._VMGCommand(hnd, "Oil", cmd)
                    return result                

    def CutAssay(self, thCase, assayObj):
        hnd = self.gPkgHandles[thCase][0]

        oilName = assayObj.parentObj.name
        assayName = assayObj.name
        assayPath = oilName + ' ' + assayObj.name

        # If oil do not exist, create it.
        result = self._VMGCommand(hnd, 'Oil', 'GetOilNames')
        names = string.replace(result[1], ' ', '')
        names = string.split(names, ';')
        if oilName in names:
            # Delete the existing assay, if it exists
            self._DeleteAssay(hnd, oilName, assayName)
        else:
            result = self._VMGCommand(hnd, 'Oil', 'AddOil ' + oilName)

        # Create the assay        
        result = self._VMGCommand(hnd, 'Oil', 'AddAssay ' + assayPath)

        # Assay now exists but empty
        # First set all parameters
        exptType = ''
        for key in assayObj.parameters.keys():
            value = assayObj.parameters[key].GetValue()
            if value and str(value) != '':
                if key == 'EXPERIMENT':
                    exptType = value
                cmd = "AssayBulkValue " + assayPath + " " + key + " " +  str(value)
                result = self._VMGCommand(hnd, "Oil", cmd)
                if result[0] < 0:
                    return result

        # Next, add the required distillation curve, optional MW and density curves
        #if exptType == '', the default experiment type, TBP,  shall be used
        #    return [-1, 'Experiment type not specified']
        if exptType == 'CHROMATOGRAPH':
            if assayObj.chromatograph == None:
                return [-1, 'Missing chromatograph data']
            else:
                result = self._SpecifyOilExperiment(hnd, 'AddChromoPoint ' + assayPath, assayObj.chromatograph)
        elif assayObj.distCurve == None:
            return [-1, 'Missing distillation Curve']
        else:
            result = self._SpecifyOilExperiment(hnd, 'AddDistillationCurve ' + assayPath, assayObj.distCurve)
        if result[0] < 0:
            return result
        if assayObj.MWCurve != None:
            result = self._SpecifyOilExperiment(hnd, 'AddMolecularWeightCurve ' + assayPath, assayObj.MWCurve)
            if result[0] < 0:
                return result
        if assayObj.denCurve != None:
            result = self._SpecifyOilExperiment(hnd, 'AddLiquidDensityCurve ' + assayPath, assayObj.denCurve)
            if result[0] < 0:
                return result

        # Add light ends if exists
        lightEnds = assayObj.lightEnds.lightEndDict    
        for key in lightEnds.keys():
            value = lightEnds[key].GetValue()
            if value > 0.0:
                cmd = 'AddLightEnds ' + assayPath + ' ' + key + ' ' + str(value)
                result = self._VMGCommand(hnd, "Oil", cmd)
                if result[0] < 0:
                    return result
            
        # cut the assay
        cmd = 'Cut ' + assayPath
        result = self._VMGCommand(hnd, "Oil", cmd)
        if result[0] != 0:
            raise SimError('ErrorValue', result[1])        
        return result
            
    def DeleteOilObject(self, thCase, obj):
        hnd = self.gPkgHandles[thCase][0]         
        if isinstance(obj, Oils.Assay):
            self._DeleteAssay (hnd, obj.parentObj.name, obj.name)
        elif isinstance(obj, Oils.Oil):
            self._DeleteOil (hnd, obj.name)
   
    def UndateLightEndsFromPkg(self, hnd, assayObj, path):
        cmd = 'GetInputCurve LightEnds ' + path
        response = self._VMGCommand(hnd, 'Oil', cmd)
        if response[0] == 0:
            var = string.split(response[1], ' ')
            for i in range(0, len(var), 2):
                if var and var[i] != '':
                    name = string.strip(var[i])
                    frac = float(var[i+1])
                    if frac > 0.0:
                        assayObj.lightEnds.AddObject(frac, name)
    
    def UndateExperimentFromPkg(self, exptType, hnd, assayObj, path):
        cmd = 'GetInputCurve ' + exptType + ' ' + path
        response = self._VMGCommand(hnd, 'Oil', cmd)
        if response[0] == 0:
            # create the experiment
            curve = Oils.OilExperiment(exptType)
            # give the experiment to the assay
            assayObj.AddObject(curve, exptType)
            # assign the value
            data = string.split(response[1], ' ')
            x = []
            y = []
            for i in range(0,len(data), 2):
                if data[i] and data[i] != '':
                    x.append(float(data[i]))
                    y.append(float(data[i+1]))
            curve.GetObject('Series0').SetValues(x)
            curve.GetObject('Series1').SetValues(y)

    def UpdateAssayPropertiesFromPkg(self, thCase, assayObj):
        hnd = -1
        if thCase:
            hnd = self.gPkgHandles[thCase][0]
        oilName = assayObj.parentObj.name
        assayName = assayObj.name
        path = oilName + ' ' + assayName
        # get all the assay parameters
        cmd = 'GetAssayBulkProperty ' + path
        paramStr = self._VMGCommand(hnd, 'Oil', cmd)
        params = string.split(paramStr[1], ';')
        for par in params:
            # create the oil parameters
            var = string.split(par,':')
            addData = 1
            try:
                val = float(var[1])
                if val == VMGUnknown:
                    addData = 0
            except ValueError:
                val = str(var[1])  # leave it as string
            if addData == 1:
                parName = string.strip(var[0])
                paramObj = Oils.OilParameter(GENERIC_VAR, val)
                paramObj.parentObj = assayObj
                paramObj.name = parName
                assayObj.parameters[parName] = paramObj
        # get the light ends
        self.UndateLightEndsFromPkg(hnd, assayObj, path)
        # get the density curve
        self.UndateExperimentFromPkg('DensityCurve', hnd, assayObj, path)        
        # get the MW curve
        self.UndateExperimentFromPkg('MWCurve', hnd, assayObj, path)        
        # get the distillation curve
        self.UndateExperimentFromPkg('DistillationCurve', hnd, assayObj, path)        
        return 1       
                         
            
    def _AssayExists(self, hnd, oilName, assayName):
        # Check if the oil exists
        result = self._VMGCommand(hnd, 'Oil', 'GetOilNames')
        names = string.replace(result[1], ' ', '')
        names = string.split(names, ';')
        if oilName in names:        
            #Check if the assay exists
            result = self._VMGCommand(hnd, 'Oil', 'GetAssayNames ' + oilName)
            names = string.replace(result[1], ' ', '')
            names = string.split(names, ';')
            if assayName in names:
                return 1
        return 0


    def _DeleteOil(self, hnd, oilName):
        # Delete the oil if it exists
        result = self._VMGCommand(hnd, 'Oil', 'GetOilNames')
        names = string.replace(result[1], ' ', '')
        names = string.split(names, ';')
        if oilName in names:
            self._VMGCommand(hnd, 'Oil', 'DeleteOil ' + oilName)

    def _DeleteAssay(self, hnd, oilName, assayName):
        # Delete the assay if it exists
        if self._AssayExists(hnd, oilName, assayName):
            result = self._VMGCommand(hnd, 'Oil', 'DeleteAssay ' + oilName + ' ' + assayName)            

    def _ConvertString(self, str):
        # Convert the tokens separator from '.' to to white space,
        # except those enclosed within quotes
        if string.find(str, "'") > -1:
            quote = "'"
        elif string.find(str, '"') > -1:
            quote = '"'
        else:
            return string.replace(str, '.', ' ')
    
        cmds = string.split(str, quote)
        for x in range(0, len(cmds), 2):
            cmds[x] = string.replace(cmds[x], '.', ' ')
        return string.join(cmds)
    
    def _VMGCommand(self, hnd, key, cmd):
        # command tokens are separated by white spaces
        result = vmg.CustomCommand(hnd, key, cmd)
        if result[0] != 0 and key != 'GetStoreData':
            self.GetParent().InfoMessage('ErrorValue', result[1])
        return result

    def _SpecifyOilExperiment(self, hnd, key, tbl):
        x = tbl.GetSeries(0)
        y = tbl.GetSeries(1)
        result = (0,'OK')
        if x and y:
            nx = x.GetLen()
            ny = y.GetLen()
            if nx == ny:
                for i in range(nx):
                    if y.GetDataPoint(i) != None and x.GetDataPoint(i) != None:
                        cmd = key + ' ' + str(x.GetDataPoint(i)) + ' ' + str(y.GetDataPoint(i))
                        result = self._VMGCommand(hnd, "Oil", cmd)
                        if result[0] < 0:
                            return result
        return result

    def _ConvertStringToDict(self, str, separator):
        # Convert strings of format a=b;c=d;e=f into a dictionary
        items = string.split(str, separator)
        dict = {}
        for x in items:
            try:
                entry = string.split(x, '=')
                # for entry a=b (c)
                data = string.split(entry[1])
                if string.strip(entry[0]) != '':
                    dict[string.strip(entry[0])] = string.strip(data[0])
            except:
                pass
        return dict

                
            
####################################################################################################

def normalize_whitespace(text):
    "Remove redundant whitespace from a string"
    return string.join(string.split(text), ' ')    



#import psyco
#psyco.bind(ThermoInterface.Flash)
#psyco.bind(ThermoInterface.GetIdealKValues)
#psyco.bind(ThermoInterface.GetProperties)
#psyco.bind(ThermoInterface.GetArrayProperty)
