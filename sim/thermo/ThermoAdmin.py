"""Thermo administrator for the simulator

Classes:
ThermoDict -- Dictionary of thermo providers
ThermoAdmin -- Thermo administrator

Remarks:
This module provides a class with a standar interfase to available thermo
providers. 

"""

import os, re
from UserDict import *
from sim.solver.Variables import *
from sim.solver.Error import SimError
from ThermoConstants import *
from Hypo import *
from sim.solver.Messages import MessageHandler
import numpy.oldnumeric
from numpy.oldnumeric import array, ones, zeros, Float, Int, sum


VMModName = 'VirtualMaterials'
VMClassName = 'ThermoInterface'

IPINFO = 'IPInfo'
LINKED_OPS_KEY = 'LinkedOps'

class ThermoDict(UserDict):
    """Dictionary implemented to handle the thermo interfases classes

    keys -- Name of the provider (Name of the file with the class)
    values -- Instance of the thermo interfase of the provider

    """
    def __init__(self, dict=None):
        """Init an empty dictionary"""          
        UserDict.__init__(self, dict)        

##A simulation should not get an instance of a thermo provider class and 
## operate on it. The way to do things, is to call methods to the ThermoAdmin 
##class passing a valid thermo provider name.
##It is not any thermo provider's duty to do extensive properties calculations
class ThermoAdmin(object):
    """Thermo administrator"""
    def __init__(self):
        """Supports Virtual Materials by default"""
        self.thDict = ThermoDict()
        self._linkedUOs = []    #Instance of uos that use this thermoadmin
        self.saveInfo = []
        self._unsentMsgStack = []    #Top most unit op stacks messages while an infoCallBack is not available
        err = self.SetNewThermoProvider(VMModName, VMClassName)
        self.currTypeOfCmpID = 'VMName' #Could be VM Id, CASN, DIPPR ID, etc.

    def CleanUp(self):
        for i in self.thDict.values(): i.CleanUp()
        self._linkedUOs = []
        self._unsentMsgStack = []
        self.saveInfo = []

    def AdjustOldCase(self, version):
        """apply any necessary fixups to a recalled case"""
        if version[0] < 19:
            for provName, prov in self.thDict.items():
                prov.SetName(provName)  #Set the name before setting the parent
                prov.SetParent(self)
            for thName, thCase in self.GetContents():
                if isinstance(thCase, ThermoCase):
                    if not hasattr(thCase, 'linkedUnitOps'):
                        thCase.linkedUnitOps = []
                    if hasattr(thCase, 'unitop'):
                        del thCase.unitop
        if version[0] < 22:
            if not hasattr(self, '_unsentMsgStack'):
                self._unsentMsgStack = []
                
        for thName, thCase in self.GetContents():
            if isinstance(thCase, ThermoCase):
                thCase.AdjustOldCase(version)
            
##Methods for usage with the CLI ###############################################

    def GetPath(self):
        from sim.unitop.UnitOperations import TH_ADMIN_KEYWORD
        return TH_ADMIN_KEYWORD

    def GetObject(self, desc):
        """Bypass the thermo provider and assume desc is a thCaseName"""
        obj = None
        for prov in self.thDict.values():
            obj = prov.GetObject(desc)
            if obj:
                return obj
        return obj

    def GetContents(self):
        """Pass the contents of all the providers. Bypass the Thermo providers"""
        results = []
        for prov in self.thDict.values():
            results.extend(prov.GetContents())
        return results

    def DeleteObject(self, obj):
        """Delete thCaseobjects directly"""
        #Bypass the provider and delete directly a thermocase
        if isinstance(obj, ThermoCase):
            provider = self.GetThermoProvider(obj.provider)
            provider.DeleteObject(obj)

    
    
################################################################################

##Methods not implemented by thermo providers ###############################################

    def LinkUO(self, uo):
        """Adds a link from the ThermoAdmin to a uo that uses it"""
        if self._unsentMsgStack:
            for msg, args, msgType in self._unsentMsgStack:
                uo.InfoMessage(msg, args, msgType)
            self._unsentMsgStack = []
        
        if not uo in self._linkedUOs:
            self._linkedUOs.append(uo)
            
            
    def UnlinkUO(self, uo):
        """Deletes a link between the ThermoAdmin and a uo"""
        if uo in self._linkedUOs:
            self._linkedUOs.remove(uo)
            
            
    def GetMsgStack(self):
        return self._unsentMsgStack
    
    def ForgetUnitOpsUsingThermo(self, provider, thName):
        """Dedicated method to forget the unit operations that use a specific thermo"""
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if thCaseObj:
                if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    uo.ForgetAllCalculations()
    
    def InfoMessage(self, message=None, args=None, msgType=MessageHandler.infoMessage):
        """use first linked uo for info message"""
        if len(self._linkedUOs):
            self._linkedUOs[0].InfoMessage(message, args, msgType)
        else:
            self._unsentMsgStack.append((message, args, msgType))
            
    def SetNewThermoProvider(self, modName, className, args = ()):
        """Adds a new thermo provider to the thermo admin

        modName -- Name of the module where the provider class is defined
        className -- Name of the class with the interfase to the thermo
        args -- (Optional) Tuple with necessary arguments to create className 

        """
        module = self.__ImportModule(modName)
        if not module:
            self.InfoMessage('CouldNotLoadProvider', modName)
            return 0
        #The provider name and the module name are the same
        self.thDict[modName] = apply(module.__dict__[className], args)
        
        #Make sure it know who the parent is
        self.thDict[modName].SetParent(self)
        self.thDict[modName].SetName(modName)

        #Small functions for filtering the required properties that are not supported
        def myFilter(prop):
            if prop not in suppProps: return 1  #1 if is not supported
            return 0

        #By default, set as common properties the required properties from the simulator
        #Check for required properties
        reqProps = GetReqIntensivePropertyNames()
        suppProps = self.thDict[modName].GetPropertyNames()
        suppProps.append(VPFRAC_VAR)
        notSupp = filter(myFilter, reqProps)
        if len(notSupp) > 0:
            self.thDict[modName].CleanUp()
            del self.thDict[modName]
            raise SimError('NoSupportForReqProps', (modName, str(notSupp)))
            return 0
        self.thDict[modName].SetCommonPropertyNames(reqProps)

        #Check for required array properties
        reqProps = GetReqArrayPropertyNames()
        suppProps = self.thDict[modName].GetArrayPropertyNames()
        notSupp = filter(myFilter, reqProps)
        if len(notSupp) > 0:
            self.thDict[modName].CleanUp()
            del self.thDict[modName]
            raise SimError('NoSupportForReqArrProps', (modName, str(notSupp)))
            return 0
        self.thDict[modName].SetCommonArrayPropertyNames(reqProps)

        return 1

    def __ImportModule(self, modName):
        """Imports a module and returns its instance or None if error"""
        module = None
        try: module = __import__(modName, globals())
        finally: return module

    def SupportsProvider(self, provider):
        """True if provider is a valid thermo provider name

        provider -- Name of the thermo provider

        """
        return self.thDict.has_key(provider)
    
    def GetThermoProvider(self, provider):
        """Provides the instance of the class of the thermo provider

        provider -- Name of the thermo provider        

        """        
        return self.thDict.get(provider)
    
    def GetAvThermoProviderNames(self):
        """List of the names of the available thermo providers"""
        return self.thDict.keys()

    def SetSameCompoundsForAll(self):
        """Not Implemented.

        Makes sure all the providers have the same cmps in every thCase

        """
        pass
####################################################################################################


    def GetAvThCaseNames(self, provider):
        """List of the avilable thermo cases for a specified provider"""
        return self.thDict[provider].GetAvThCaseNames()
    
    def GetAvPropPkgNames(self, provider):
        """List of avilable porperty packages for a specified provider"""
        return self.thDict[provider].GetAvPropPkgNames()
    
    def AddPkgFromName(self, provider, thName, pkgName):
        """Selects a property packages for a specified thermo case

        provider -- Name of the thermo provider
        thName -- Name of the thermo case
        pkgName -- String with the th pkg name. If one pkg per phase,
                   then separate the th pkg names with a space. Order: Vap, liq
        """
        #Add pkg
        thCaseObj = self.thDict[provider].AddPkgFromName(thName, pkgName)
        return thCaseObj

        ##If it was added succesfully, return a ThermoCase obj
        #if thName in self.thDict[provider].GetAvThCaseNames():
            #return ThermoCase(self, provider, thName, pkgName)
        #else:
            #return None

    def ReplacePkgFromName(self, provider, thName, pkgName):
        """Replaces property packages for a specified thermo case
        (the case must already have had property packages assigned

        provider -- Name of the thermo provider
        thName -- Name of the thermo case
        pkgName -- String with the th pkg name. If one pkg per phase,
                   then separate the th pkg names with a space. Order: Vap, liq
        """
        #Add pkg
        self.thDict[provider].ReplacePkgFromName(thName, pkgName)
        self.ForgetUnitOpsUsingThermo(provider, thName)
        #for uo in self._linkedUOs:
            #thCaseObj = uo.GetThermo()
            #if thCaseObj:
                #if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    #uo.ForgetAllCalculations()

    def ChangeThermoCaseName(self, provider, oldThName, newThName):
        """Changes the name of a thermo case"""
        avThCases = self.thDict[provider].GetAvThCaseNames()
        if (newThName in avThCases) or (not oldThName in avThCases):
            return
            #Should raise an error

        self.thDict[provider].ChangeThermoCaseName(oldThName, newThName)
        
        '''
        Watch out!  ThermoAdmin has no access to thermoCase objects, hence the 
        thCase.name and thCase.case are not updated if thCase is not linked to 
        any unit op's.
        '''
        
        for uo in self._linkedUOs:
            if hasattr(uo, 'thCaseObj'):
                thCaseObj = uo.GetThermo()
                if thCaseObj:
                    if (thCaseObj.provider, thCaseObj.case) == (provider, oldThName):
                        uo.thCaseObj.case = newThName
                        uo.thCaseObj.name = newThName
    
    def DeleteThermoCase(self, provider, thName, cleaningUp=0):
        """Deletes a thermo case"""
        if not thName in self.GetAvThCaseNames(provider):
            return   # probably already deleted
        
        if not cleaningUp:
            selCmps = self.GetSelectedCompoundNames(provider, thName)
            for cmp in selCmps:
                self.DeleteCompound(provider, thName, cmp)
                
        self.thDict[provider].DeleteThermoCase(thName)
        
    def GetPropPkgString(self, provider, thName):
        """Retrives a string with the selected property package name/s"""
        return self.thDict[provider].GetPropPkgString(thName)

    def GetUnitOps(self, thCase):
        """Returns a list of the unit ops using this thermo case"""
        uoList = []
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if (thCaseObj is thCase):
                uoList.append(uo)
        return uoList
                    
    def GetUnitOpPaths(self, thCase):
        """Returns a list of the paths of the unit ops using this thermo case"""
        uoList = []
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if (thCaseObj == thCase):
                uoList.append(uo.GetPath())
        return uoList
                            
    def CheckThermoVersion(self):
        for provider in self.thDict.keys():
            self.thDict[provider].CheckThermoVersion()

##IP methods ######################################################################################
    def GetIPMatrixNames(self, provider, thName):
        """Returns the names of the IP Matrices used by a property package"""
        return self.thDict[provider].GetIPMatrixNames(thName)

    def GetNuIPPanes(self, provider, thName, ipMatrName):
        """Returns the amount of panes for an IP matrix (aij, bij,...nij)"""
        return self.thDict[provider].GetNuIPPanes(thName, ipMatrName)

    def GetIPPaneNames(self, provider, thName, ipMatrName): 
        """Returns the names of the panes for an IP matrix (aij, bij,...nij)"""
        return self.thDict[provider].GetIPPaneNames(thName, ipMatrName)
    
    def GetIPValues(self, provider, thName, ipMatrName, pane):
        """Gets all the ip values of one pane in one call"""
        return self.thDict[provider].GetIPValues(thName, ipMatrName, pane)
        
        
    def GetIPValue(self, provider, thName, ipMatrName, cmpName1, cmpName2, pane):
        """Returns the IP value of a specific pane for two compounds"""
        return self.thDict[provider].GetIPValue(thName, ipMatrName, cmpName1, cmpName2, pane)

    def GetIPInfo(self, provider, thName, ipMatrName, cmpName1, cmpName2):
        """Returns the IP value of a specific pane for two compounds"""
        return self.thDict[provider].GetIPInfo(thName, ipMatrName, cmpName1, cmpName2)

    def SetIPValue(self, provider, thName, ipMatrName, cmpName1,
                   cmpName2,pane, value):
        """Sets the IP value of a specific pane for two compounds"""
        self.thDict[provider].SetIPValue(thName, ipMatrName, cmpName1, cmpName2, pane, value)
        self.ForgetUnitOpsUsingThermo(provider, thName)
        #for uo in self._linkedUOs:
            #thCaseObj = uo.GetThermo()
            #if thCaseObj:
                #if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    #uo.ForgetAllCalculations()


##Oil methods ######################################################################################

    def CustomCommand(self, provider, thCase, cmd):
        try:
            return self.thDict[provider].CustomCommand(thCase, cmd)
        except SimError, e:
            return e.extraData
        except:
            raise SimError('ErrorValue', cmd + ' failed.') 
 
    def InstallOil(self, provider, thCase, assayObj):
        # First delete the pseudo's associated with this installed assay
        self.DeletePseudos(provider, thCase, assayObj)
        # count the number of existing compounds
        cmpOld = self.GetSelectedCompoundNames(provider, thCase)
        # Install the oil        
        result = self.thDict[provider].InstallOil(thCase, assayObj)
        # Count the number of new compounds
        cmpNew = self.GetSelectedCompoundNames(provider, thCase)
        # Calculate the number of compounds that need to be added
        nuCmpOld = len(cmpOld)
        nc = len(cmpNew) - nuCmpOld
        if nc < 0:
            nc = 0
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if thCaseObj:
                if (thCaseObj.provider, thCaseObj.case) == (provider, thCase):
                    cmpCount = nuCmpOld
                    for i in range(nc):
                        try:
                            uo.AppendCompound(cmpCount)
                            cmpCount += 1
                        except:
                            self.InfoMessage('ErrNotifyChangeCmp', (uo.GetPath(),), MessageHandler.errorMessage)
        return result

    def DeletePseudos(self, provider, thCase, assayObj):
        # Get the pseudo list
        pesudoList = self.thDict[provider].PseudoList(thCase, assayObj)
        if pesudoList:
            for cmp in pesudoList:
                self.DeleteCompound(provider, thCase, cmp)

    def UpdateOil(self, provider, thCase, assayObj):
        return self.thDict[provider].UpdateOil(thCase, assayObj)

    def CutAssay(self, provider, thCase, assayObj):
        return self.thDict[provider].CutAssay(thCase, assayObj)

    def BlendAssay(self, provider, thCase, blend):
        return self.thDict[provider].BlendAssay(thCase, blend)
    
    def SetAssayParameterValue(self, provider, thCase, paramObj):
        return self.thDict[provider].SetAssayParameterValue(thCase, paramObj)

    def DeleteOilObject(self, provider, thCase, obj):
        return self.thDict[provider].DeleteOilObject(thCase, obj)

    def GetOilComposition(self, provider, thCase, obj):
        return self.thDict[provider].GetOilComposition(thCase, obj)
        
####################################################################################################


##Compound methods################################################################################
    def GetAvCompoundNames(self, provider):
        """List of avilable compounds for a specified provider"""
        return self.thDict[provider].GetAvCompoundNames()
    
    def AddCompound(self, provider, thName, cmp):
        """Adds a compound to a  thermo case"""
        selCmps = self.GetSelectedCompoundNames(provider, thName)
        if cmp in selCmps: return
        self.thDict[provider].AddCompound(thName, cmp)
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if thCaseObj:
                if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    try:
                        uo.AppendCompound()
                    except:
                        self.InfoMessage('ErrNotifyChangeCmp', (uo.GetPath(),), MessageHandler.errorMessage)
                        

    def AddHypoCompound(self, provider, thName, hypoName, hypoDesc):
        selCmps = self.GetSelectedCompoundNames(provider, thName)
        if cmp in selCmps: return
        self.thDict[provider].AddHypoCompound(thName, hypoName, hypoDesc)
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if thCaseObj:
                if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    try:
                        uo.AppendCompound()
                    except:
                        self.InfoMessage('ErrNotifyChangeCmp', (uo.GetPath(),), MessageHandler.errorMessage)

    def EditCompound(self, provider, thName, hypoName, hypoDesc):
        cmpIdx = self.CompoundIndexFromName(provider, thName, hypoName)
        self.thDict[provider].EditCompound(thName, cmpIdx, hypoDesc)
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if thCaseObj:
                if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    try:
                        uo.ForgetAllCalculations()
                    except:
                        self.InfoMessage('ErrNotifyEditCmp', (uo.GetPath(),), MessageHandler.errorMessage)

    def MoveCompound(self, provider, thName, cmp1Name, cmp2Name):
        #cmp1Name = re.sub('_', ' ', cmp1Name)
        #cmp2Name = re.sub('_', ' ', cmp2Name)
        #cmps = self.thDict[provider].GetSelectedCompoundNames(thName)
        #idx1 = cmps.index(cmp1Name)
        #if cmp2Name == '$':
        #    idx2 = len(cmps)
        #else:
        #    idx2 = cmps.index(cmp2Name)
        #idx1 = self.CompoundIndexFromName(provider, thName, cmp1Name)
        #idx2 = self.CompoundIndexFromName(provider, thName, cmp2Name)
        cmps = self.thDict[provider].GetSelectedCompoundNames(thName)
        try:
            if cmp1Name == '$':
                idx1 = len(cmps)
            else:
                idx1 = cmps.index(cmp1Name)
        except:
            cmp1Name = re.sub('_', ' ', cmp1Name)
            idx1 = cmps.index(cmp1Name)
            
        try:
            if cmp2Name == '$':
                idx2 = len(cmps)
            else:
                idx2 = cmps.index(cmp2Name)
        except:
            cmp2Name = re.sub('_', ' ', cmp2Name)
            idx2 = cmps.index(cmp2Name)
            
        self.thDict[provider].MoveCompound(thName, cmp1Name, cmp2Name)        
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if thCaseObj:
                if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    try:
                        uo.MoveCompound(idx1, idx2)
                    except:
                        self.InfoMessage('ErrNotifyChangeCmp', (uo.GetPath(),), MessageHandler.errorMessage)    
        
    def CompoundIndexFromName(self, provider, thName, cmpName):
        cmps = self.thDict[provider].GetSelectedCompoundNames(thName)
        if cmpName == '$':
            idx = len(cmps)
        else:
            try:
                idx = cmps.index(cmpName)
            except:
                cmpName = re.sub('_', ' ', cmpName)
                idx = cmps.index(cmpName)
        return idx
            
    def DeleteCompound(self, provider, thName, cmp):
        """Removes a compound from a thermo case"""
        selCmps = self.GetSelectedCompoundNames(provider, thName)
        if not cmp in selCmps:
            cmp = re.sub(' ', '_', cmp)
            if not cmp in selCmps:
                return
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if thCaseObj:
                if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    try:
                        uo.DeleteCompound(cmp)
                    except:
                        self.InfoMessage('ErrNotifyChangeCmp', (uo.GetPath(),), MessageHandler.errorMessage)                   
        self.thDict[provider].DeleteCompound(thName, cmp)
        for uo in self._linkedUOs:
            thCaseObj = uo.GetThermo()
            if thCaseObj:
                if (thCaseObj.provider, thCaseObj.case) == (provider, thName):
                    try:
                        uo.AfterCompoundDeleted(cmp)
                    except:
                        self.InfoMessage('ErrNotifyChangeCmp', (uo.GetPath(),), MessageHandler.errorMessage)                   
        
    def GetSelectedCompoundNames(self, provider, thName):
        """List of selected compounds for a thermo case"""
        return self.thDict[provider].GetSelectedCompoundNames(thName)
    
    def GetHypoteticalCompoundNames(self, provider, thName):
        """List of selected compounds for a thermo case"""
        return self.thDict[provider].GetHypoteticalCompoundNames(thName)
    
    def GetCompoundPropertyNames(self, provider, propGroup=None):
        """Get the names of the supported properties (of certain groups if desired)"""
        return self.thDict[provider].GetCompoundPropertyNames(propGroup)

    def GetCompoundProperties(self, provider, thName, cmp, propNames):
        """Property of a compound"""
        return self.thDict[provider].GetCompoundProperties(thName, cmp, propNames)
        
    def GetSelectedCompoundProperties(self, provider, thName, cmpNo, propNames):
        """return property(ies) for component number cmpNo"""
        return self.thDict[provider].GetSelectedCompoundProperties(thName, cmpNo, propNames)
    
####################################################################################################


##Stream methods ######################################################################################
    def GetPropertyNames(self, provider):
        """Returns a list of supported properties"""
        return self.thDict[provider].GetPropertyNames()

    def GetArrayPropertyNames(self):
        """Returns a list of supported array properties"""
        return self.thDict[provider].GetArrayPropertyNames()

    def SetCommonPropertyNames(self, provider, propList):
        """Sets the common property list"""
        if not ZFACTOR_VAR in propList:
            raise SimError('MissigZInCommonProps', (str(propList),))
        #Make sure there are no duplicates
        finalList = []
        for prop in propList:
            if prop not in finalList:
                finalList.append(prop)
                
        self.thDict[provider].SetCommonPropertyNames(finalList)

    def SetCommonArrayPropertyNames(self, provider, propList):
        """Sets the common array property list"""
        self.thDict[provider].SetCommonArrayPropertyNames(propList)

    def GetCommonPropertyNames(self, provider):
        """Gets the common property list"""
        return self.thDict[provider].GetCommonPropertyNames()

    def GetCommonArrayPropertyNames(self, provider):
        """Gets the common array property list"""
        return self.thDict[provider].GetCommonArrayPropertyName()

    def GetSpecialProperty(self, provider, thName, inputData, frac, prop, nuPoints=None):
        """
        Return a special property. 
        inputData contains any necessary info requiered to calculate the required prop
        frac is just the composition
        """
        return self.thDict[provider].GetSpecialProperty(thName, inputData, frac, prop, nuPoints)
    
    def GetProperties(self, provider, thName, prop1, prop2, phase, frac, propList):
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
        return self.thDict[provider].GetProperties(thName, prop1, prop2, phase, frac, propList)

    def GetArrayProperty(self, provider, thName, prop1, prop2, phase, frac, property):
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
        return self.thDict[provider].GetArrayProperty(thName, prop1, prop2, phase, frac, property)
    
    def GetIdealKValues(self, provider, thName, temperature, pressure):
        """return array of estimated K values based on just temperature and pressure"""
        return self.thDict[provider].GetIdealKValues(thName, temperature, pressure)
    
    def GetMolecularWeightValues(self, provider, thName):
        """shortcut method to get the molecular weigt vector of a thermo case"""
        return self.thDict[provider].GetMolecularWeightValues(thName)
        
####################################################################################################


##Flash methods ####################################################################################
    def GetFlashSettingsInfo(self, provider, thName):
        """Returns a dictionary with objects describing the flash settings"""
        return self.thDict[provider].GetFlashSettingsInfo(thName)
        
    def SetFlashSetting(self, provider, thName, settingName, value):
        return self.thDict[provider].SetFlashSetting(thName, settingName, value)
        
    def GetFlashSetting(self, provider, thName, settingName):
        """Get the value of a flash setting"""
        return self.thDict[provider].GetFlashSetting(thName, settingName)

    def GetPropNamesCapableOfFlash(self, provider, thName):
        """Returns a tuple with prop names that can be used to calculate a flash"""
        return self.thDict[provider].GetPropNamesCapableOfFlash(thName)

    
    def Flash(self, provider, thName, cmps, properties, liqPhases, 
              propList=None, nuSolids=0, stdVolRefT=None):
        """Performs a Flash calculation

        provider -- Name of the thermo provider that will do the calculation
        thName -- Name of the thermo case
        cmps -- Instance of Variables.CompoundList
        properties -- Instance of Variables.MaterialPropertyDict
        liqPhases -- Number of liquid phases
        propList -- Optional list of properties to calculate.
                    If propList==None, then the common properties are calculated
        nuSolids -- Number of solid phases

        return results object
        """        
        return self.thDict[provider].Flash(thName, cmps, properties, liqPhases, propList, self, nuSolids, stdVolRefT)
####################################################################################################


##Save and load methods ############################################################################
    def UpdateSaveInfo(self):
        #Call this before saving, so pickle saves the xml string
        """Temporary scheme for saving the prop pkg as a tuple in the list self.saveInfo """
        for th in self.thDict.items():
            info = (th[0], th[1].GetThermoXMLString())
            self.saveInfo.append(info)
        
    def UpdateFromSaveInfo(self):
        #Call this after loading from pickle so the prop pkgs get built
        """Temporary scheme for loading the prop pkg from the tuples in the list self.saveInfo """
        for info in self.saveInfo:
            #For now, let's hope the provider info[0] is already in thDict
            self.thDict[info[0]].SetThermoXMLString(info[1])

    def GetSaveInfo(self):
        return self.saveInfo
####################################################################################################



    def PhaseEnvelope(self, provider, thName, cmps, vapFraction, initP, maxPoints, pList=None):
        """Calculate a 2 phase VL PT envelope

        provider -- Name of the thermo provider that will do the calculation
        thName -- Name of the thermo case
        cmps -- composiiton list
        vapFraction -- quality line specification (0 = bubble point)
        initP -- starting pressure
        maxPoints -- maximum allowable points in the envelope
        pList -- optional list of pressure set points.
                    If propList==None, no pressure points are interpolated

        return tuple containing (retCode, retMessage, actual Number of points, result matrix
        """        
        return self.thDict[provider].PhaseEnvelope(thName, cmps, vapFraction, initP, maxPoints, pList)
    
    def MergeThermoAdmin(self, fThAdmin):
        """Changes the thermoadmin of uo for this thermoadmin"""
        #f stands for foreign
        #l stands for local
        
        lThAdmin = self
        lProvNames = lThAdmin.thDict.keys()
        lProv = lThAdmin.thDict.values()

        lCaseNames = []
        lCaseObjs = []
        for caseName, caseObj in lThAdmin.GetContents():
            lCaseNames.append(caseName)
            lCaseObjs.append(caseObj)
            
        fCaseNames = []
        fCaseObjs = []
        for caseName, caseObj in fThAdmin.GetContents():
            fCaseNames.append(caseName)
            fCaseObjs.append(caseObj)
            
        for i in range(len(fCaseNames)):
            #If the name of the thermo case is already there, then attempt
            #to fix based on the path of the first linked unit op
            if fCaseNames[i] in lCaseNames:
                newName = fCaseObjs[i].name
                linkedOps = fCaseObjs[i].GetLinkedUnitOps()
                if linkedOps:
                    uo = linkedOps[0]
                    path = uo.GetPath()
                    if path[0] == '/':
                        path = path[1:]
                    newName = path + '.' + newName
                    newName = re.sub('\.', '_', newName)
                    
                #That should had work, but to make sure loop until it becomes unique
                while newName in lCaseNames:
                    newName += '_'
                fThAdmin.ChangeThermoCaseName(fCaseObjs[i].provider, fCaseNames[i], newName)
                fCaseObjs[i].name = newName
                fCaseObjs[i].case = newName
            
                lCaseNames.append(newName) #As if the newly fixed case was already here
            else:
                lCaseNames.append(fCaseNames[i])
            
                
            
        ##Fix names so providers can be merged       
        #def FixThCaseName(chUOp, thFixed, thAdmin):
            #thCaseObj = chUOp.thCaseObj
            #if thCaseObj:
                #if not thCaseObj in thFixed:
                    #path = chUOp.GetPath()
                    #oldName = thCaseObj.case
                    #newName = path + '.' + thCaseObj.name  #Use this as the new name
                    #newName = re.sub('\.', '_', newName)
                    #thCaseObj.thermoAdmin.ChangeThermoCaseName(thCaseObj.provider, oldName, newName)
                    #thCaseObj.thermoAdmin = thAdmin
                    #thFixed.append(thCaseObj)
                #chUOp.thermoAdmin = thAdmin
                #self.LinkUO(chUOp)
        #uo.walk(FixThCaseName, ([], self))
        
        
        #Lets iterate in every foreign provider
        for fProvName, fProv in fThAdmin.thDict.items():
            #Pass the providers from the foreign to the local
            if fProvName in lProvNames:
                if fProv.__class__ != lThAdmin.thDict[fProvName].__class__:
                    #Error!!
                    #The name of the provider is the same but the type of class is not the same
                    pass
                else:
                    lThAdmin.thDict[fProvName].MergeProvider(fProv)
            else:
                lThAdmin.thDict[fProvName] = fProv

    
        for caseObj in fCaseObjs:
            caseObj.thermoAdmin = lThAdmin
            
        #At the end, the ops from the foreign admin should be included to the local admin
        for uo in fThAdmin._linkedUOs:
            lThAdmin.LinkUO(uo)

    def AddObject(self, rhsObj, createName):
        if isinstance(rhsObj, ThermoCase):
            # clone a thermo case
            thCase = rhsObj.case
            if thCase != createName:
                return self.thDict[rhsObj.provider].Clone(thCase, createName)

##The following are wrapper objects to interact with the CLI ########################################
    
            
class ThermoProvider(object):
    """Just wraps up thermo provider"""
    def __init__(self, unitOp, thermoAdmin, case, provider, pkgName):
        """description is provider.pkgname"""
        self.thermoAdmin = thermoAdmin
        unitOp.SetThermoAdmin(thermoAdmin)
        thermoAdmin.AddPkgFromName(provider, case, pkgName)
        unitOp.SetThermoProvider(provider, case)
        unitOp.CmdThermo = self
        self.provider = provider
        self.case = case
        self.package = pkgName

    def CleanUp(self):
        self.thermoAdmin.DeleteThermoCase(self.provider, self.case)
        self.thermoAdmin = None
        self.provider = None
        if self.case:
            self.case.CleanUp()
        self.case = None
        
    def Add(self, cmpNames):
        """adds component"""
        # replace all spaces within quotes by underscore
        cmps = re.findall(r'"[^"]+"|\'[^\']+\'', cmpNames)
        for token in cmps:
            # strip out the quote
            cmp = token[1:-1]
            # underscore represent space
            cmp = re.sub(' ', '_', cmp)
            try:
                cmpNames = cmpNames.replace(token, cmp)
            except:
                pass

        cmps = re.split(r'[\s]', cmpNames)

        response = ''
        for cmp in cmps:
            if cmp:
                cmp = re.sub('_', ' ', cmp)  # let underscores stand for spaces
                try:
                    self.thermoAdmin.AddCompound(self.provider, self.case, cmp)
                    response = response + cmp + ' '
                except Exception, e:
                    self.thermoAdmin.InfoMessage('AddCompoundError', str(e))
        return response

    def AddHypo(self, hypoName, hypoDesc, unitSystem):
        try:
            #hypo names must end with '*'
            if hypoName[-1] != '*':
                hypoName = hypoName + '*'            
            # descTupple = (hypoStrDescs, hypoStrVals, hypoLongDescs, hypoLongVals, hypoDblDescs, hypoDblVals)
            descTupple = GetCompoundPropertyLists(hypoName, hypoDesc, unitSystem)            
            self.thermoAdmin.AddHypoCompound(self.provider, self.case, hypoName, descTupple)
            return hypoName
        except Exception, e:
            self.thermoAdmin.InfoMessage('AddHypoCompoundError', str(e))
            return None

    def MoveCompound(self, cmp1Name, cmp2Name):
        """Move compound cmp1 before compound cmp2"""
        #cmp1 = re.sub('_', ' ', cmp1Name)  # let underscores stand for spaces
        #cmp2 = re.sub('_', ' ', cmp2Name)  # let underscores stand for spaces        
        return self.thermoAdmin.MoveCompound(self.provider, self.case, cmp1, cmp2)
            
                
    def Minus(self, cmpNames):
        """adds component"""
        cmps = re.split(r'[\s,]', cmpNames)
        for cmp in cmps:
            if cmp:
                cmp = re.sub('_', ' ', cmp)  # let underscores stand for spaces
                self.thermoAdmin.DeleteCompound(self.provider, self.case, cmp)

    def GetObject(self, desc):
        '''
        return whatever desc option
        '''
        if desc == 'CommonProperties':
            return self.thermoAdmin.GetCommonPropertyNames(self.provider)

            
class ThermoCase(object):
    """Just wraps up a thermo case"""
    
    def __init__(self, thermoAdmin, provider, case, pkgName):
        """Load some vars into member vars"""
        self.thermoAdmin = thermoAdmin
        self.provider = provider
        self.case = case
        self.package = pkgName
        self.linkedUnitOps = []

        #By default, the name of the ThermoCase is the name of the case        
        self.name = case    

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return '%s = %s; Uses --> %s.%s' % (self.name, t, self.provider, self.package)

    def GetContents(self):
        results = [('Provider', self.provider), ('Package', self.package), (LINKED_OPS_KEY, self.linkedUnitOps)]
        if hasattr(self, 'oilCase'):
            if self.oilCase:
                results.append(('oilCase', self.oilCase))
        return results
        
    def CleanUp(self):
        """Delete the thcase"""
        cleaningUp = 1
        self.thermoAdmin.DeleteThermoCase(self.provider, self.case, cleaningUp)
        self.thermoAdmin = None
        self.provider = None
        self.case = None
        if hasattr(self, 'oilCase'):
            if self.oilCase:
                self.oilCase.CleanUp()
            del self.oilCase
        self.linkedUnitOps = None
        
    def AdjustOldCase(self, version):
        if hasattr(self, 'oilCase'):
            self.oilCase.AdjustOldCase(version)

    def GetLinkedUnitOps(self):
        return self.linkedUnitOps
        
    def LinkUnitOp(self, unitop):
        """
        Adds a unit op to the list of directly linked unit ops
        """
        if not unitop in self.linkedUnitOps:
            self.linkedUnitOps.append(unitop)
        
    def UnLinkUnitOp(self, unitop):
        """
        Removes the unit op from the list of attached unitops
        """
        if unitop in self.linkedUnitOps:
            self.linkedUnitOps.remove(unitop)
        
    def GetName(self):
        return self.name
    
    def GetPath(self):
        """
        The creating path is encoded in the case name
        """
        if not hasattr(self,'linkedUnitOps'):
            self.linkedUnitOps = []
            
        if not self.linkedUnitOps:
            from sim.unitop.UnitOperations import TH_ADMIN_KEYWORD
            
            return TH_ADMIN_KEYWORD + self.case
        else:
            #Pick the first unit op as the source for the path
            from sim.unitop.UnitOperations import TH_CASE_KEYWORD
            uoPath = self.linkedUnitOps[0].GetPath()
            if uoPath == '/':
                return uoPath + self.case
            return uoPath + '.' + self.case

    def GetParent(self):
        """
        Either the thermo admin or the first unit op
        """
        if self.linkedUnitOps:
            return self.linkedUnitOps[0]
        else:
            return self.thermoAdmin

    def AddObject(self, obj, name):
        """
        generic add object routine
        used to change property package
        """
        
        if name.lower() == 'package':
            self.ReplacePropertyPackage(obj)
            self.package = obj
            self.description = obj
        elif name.lower() == 'description':
            self.description = obj
        elif name == 'NewName':
            newName = str(obj)
            newName = re.sub(' ', '_', newName)
            oldName = self.name
            #Let the thermo admin coordinate the changes
            self.thermoAdmin.ChangeThermoCaseName(self.provider, oldName, newName)
            self.name = newName
            self.case = newName
            
        elif isinstance(obj, Oils.OilCase):
            self.oilCase = obj
            if obj:
                obj.SetThermoCase(self)
                obj.SetName(name)
        elif name == 'NewName':
            newName = str(obj)
            newName = re.sub(' ', '_', newName)
            oldName = self.name
            
            #Let the thermo admin coordinate the changes
            self.thermoAdmin.ChangeThermoCaseName(self.provider, oldName, newName)
            
        else:
            raise SimError('CantAddObject', (name, self.name))

    def Add(self, cmpNames):
        """adds component"""
        # replace all spaces within quotes by underscore
        self.ResetKijPaneValues()
                
        cmps = re.findall(r'"[^"]+"|\'[^\']+\'', cmpNames)
        for token in cmps:
            # strip out the quote
            cmp = token[1:-1]
            # underscore represent space
            cmp = re.sub(' ', '_', cmp)
            try:
                cmpNames = cmpNames.replace(token, cmp)
            except:
                pass

        cmps = re.split(r'[\s]', cmpNames)

        response = ''
        for cmp in cmps:
            if cmp:
                cmp = re.sub('_', ' ', cmp)  # let underscores stand for spaces
                try:
                    self.thermoAdmin.AddCompound(self.provider, self.case, cmp)
                    response = response + cmp + ' '
                except Exception, e:
                    self.thermoAdmin.InfoMessage('AddCompoundError', str(e))
        return response

    def AddHypo(self, hypoName, hypoDesc, unitSystem):
        try:
            self.ResetKijPaneValues()
            #hypo names must end with '*'
            if hypoName[-1] != '*':
                hypoName = hypoName + '*'            
            # descTupple = (hypoStrDescs, hypoStrVals, hypoLongDescs, hypoLongVals, hypoDblDescs, hypoDblVals)
            descTupple = GetCompoundPropertyLists(hypoName, hypoDesc, unitSystem)            
            self.thermoAdmin.AddHypoCompound(self.provider, self.case, hypoName, descTupple)
            return hypoName
        except Exception, e:
            self.thermoAdmin.InfoMessage('AddHypoCompoundError', str(e))
            return None

    def EditCompound(self, hypoName, hypoDesc, unitSystem):
        try:
            descTupple = GetCompoundPropertyLists(hypoName, hypoDesc, unitSystem)            
            self.thermoAdmin.EditCompound(self.provider, self.case, hypoName, descTupple)
            return hypoName
        except Exception, e:
            self.thermoAdmin.InfoMessage('EditCompoundError', str(e))
            return None
        
        
    def MoveCompound(self, cmp1Name, cmp2Name):
        """Move compound cmp1 before compound cmp2"""
#        cmp1 = re.sub('_', ' ', cmp1Name)  # let underscores stand for spaces
#        cmp2 = re.sub('_', ' ', cmp2Name)  # let underscores stand for spaces        
#        return self.thermoAdmin.MoveCompound(self.provider, self.case, cmp1, cmp2)
        self.ResetKijPaneValues()
        return self.thermoAdmin.MoveCompound(self.provider, self.case, cmp1Name, cmp2Name)

    def ReplacePropertyPackage(self, pkgName):
        """
        replace the property packages
        pkgName -- String with the th pkg name. If one pkg per phase,
                   then separate the th pkg names with a space. Order: Vap, liq
        """
        self.ResetKijPaneValues()
        self.thermoAdmin.ReplacePkgFromName(self.provider, self.case, pkgName)
    
    def Minus(self, cmpNames):
        """adds component"""
        self.ResetKijPaneValues()
        cmps = re.split(r'[\s]', cmpNames)
        for cmp in cmps:
            if cmp:
                cmp = re.sub('_', ' ', cmp)  # let underscores stand for spaces
                self.thermoAdmin.DeleteCompound(self.provider, self.case, cmp)

    def GetObject(self, desc):
        '''
        return whatever desc option
        '''
        if desc == 'CommonProperties':
            return self.thermoAdmin.GetCommonPropertyNames(self.provider)
        elif desc == 'Package':
            return PropPackage(self)
        elif hasattr(self, 'oilCase') and desc == self.oilCase.name:
            return self.oilCase
        elif desc == 'OilCase':
            if hasattr(self, 'oilCase'):
                return self.oilCase
        elif desc == 'CustomCommand':
            return CustomCommandObject(self)
        elif desc == LINKED_OPS_KEY:
            return self.linkedUnitOps
 
    def GetUnitOpPaths(self):
        """Method to return a list of paths of the unit ops using me"""
        return self.thermoAdmin.GetUnitOpPaths(self)

    def GetUnitOps(self):
        """Method to return a list of unit ops using me"""
        return self.thermoAdmin.GetUnitOps(self)
    
    def GetLinkedUnitOpPaths(self):
        """Method to return a list of paths of the unit ops that linked directly to me"""
        return map(lambda uo:uo.GetPath(), self.linkedUnitOps)

    
    def CustomCommand(self, cmd):
        # commands are redirected to the thermoAdmin
        return self.thermoAdmin.CustomCommand(self.provider, self.case, cmd)

    def GetDescription(self):
        # If I have a description returns it; otherwise returns the pkg name
        if hasattr(self, 'description'):
            return self.description
        else:
            return self.package
        
    def GetKijPaneValues(self, ipMatrName, paneIdx):
        if not hasattr(self, storedKijVals):
            self.storedKijVals = {}
        if self.storedKijVals.has_key((ipMatrName, paneIdx)):
            return self.storedKijVals[(ipMatrName, paneIdx)]
        
    def RemoveKijPaneValues(self, ipMatrName, paneIdx):
        if not hasattr(self, storedKijVals):
            self.storedKijVals = {}
        if self.storedKijVals.has_key((ipMatrName, paneIdx)):
            del self.storedKijVals[(ipMatrName, paneIdx)]
        
    def ResetKijPaneValues(self):
        self.storedKijVals = {}
                
    def SetKijPaneValues(self, ipMatrName, paneIdx, values):
        if not hasattr(self, storedKijVals):
            self.storedKijVals = {}
        self.storedKijVals[(ipMatrName, paneIdx)] = values
            
                
    def GetSelectedCompoundNames(self):
        """List of selected compounds for a thermo case"""
        return self.thermoAdmin.GetSelectedCompoundNames(self.provider, self.case)
        
class EnvelopeResults(object):
    def __init__(self, retCode, retMessage, pointCount, types, pVals, tVals, kVals, type='PT'):
        # Quality curves: P, T, Kvalues
        # TH curves: P, T, H
        self.returnCode = retCode
        self.returnMessage = retMessage
        self.pointCount = pointCount
        self.pointTypes =  types
        self.pValues = pVals
        self.tValues = tVals
        self.kValues = kVals
        self.type = type
        self.SetCritical()

    def SetCritical(self):
        # point type 2: critical point
        #            3: cricondenbar
        #            4: crocondentherm
        self.criticalPoint = (None, None)
        self.cricondenbar = (None, None)
        self.cricondentherm = (None, None)
        if self.type == 'PT':
            for i in range(self.pointCount):
                if self.pointTypes[i] == 2 and self.criticalPoint[0] == None:
                    self.criticalPoint = (self.pValues[i], self.tValues[i])
                elif self.pointTypes[i] == 3 and self.cricondenbar[0] == None:
                    self.cricondenbar = (self.pValues[i], self.tValues[i])
                elif self.pointTypes[i] == 4 and self.cricondentherm[0] == None:
                    self.cricondentherm = (self.pValues[i], self.tValues[i])

    def GetContents(self):
        results = [('ReturnCode', self.returnCode), ('Message', self.returnMessage),
                   ('CurveTypes', self.type),
                   ('NumberPoints', self.pointCount), ('PointType', self.pointTypes),
                   ('Pressure',self.pValues), ('Temperature', self.tValues)]
        if self.type == 'TH' or self.type == 'PH':
            results.append(('Enthalpy', self.kValues))
        return results                
    
        
class FlashResults(object):
    """wraps up the results of a flash calculation"""
    def __init__(self, propNames, arrPropNames, bulkComp, bulkProps, bulkArrProps,
                 phasesFracs, phasesComp, phasesProps, phasesArrProps):
        self.propNames = propNames
        self.arrPropNames = arrPropNames
        self.bulkComposition = bulkComp
        self.bulkProps = bulkProps
        self.bulkArrProps = bulkArrProps
        self.phaseFractions = phasesFracs
        self.phaseComposition = phasesComp
        self.phaseProps = phasesProps
        self.phaseArrProps = phasesArrProps
        
    def __str__(self):
        """return attribute names as string"""
        result = ''
        for a in self.__dict__:
            result += a + ' '
        return result
    
    def GetObject(self, description):
        """return object corresponding to description"""
        if hasattr(self, description):
            return self.__dict__[description]
        else:
            return None
        
    def ResultsForPhase(self, phaseNo):
        """return FlashResults representing phase number phaseNo"""
        
        phaseFrac = [0.0] * len(self.phaseFractions)
        phaseFrac[phaseNo] = 1.0
        return FlashResults(
                self.propNames,
                self.arrPropNames,
                self.phaseComposition[phaseNo],
                self.phaseProps[phaseNo],
                self.phaseArrProps[phaseNo],
                phaseFrac,
                self.phaseComposition,
                self.phaseProps,
                self.phaseArrProps
                )
    def Clone(self):
        from sim.unitop import UnitOperations
        
        f = UnitOperations._SafeClone
        clone = self.__class__(f(self.propNames), f(self.arrPropNames), f(self.bulkComposition), f(self.bulkProps),
                               f(self.bulkArrProps), f(self.phaseFractions), f(self.phaseComposition),
                               f(self.phaseProps), f(self.phaseArrProps))
        return clone

class PropPackage(object):
    """Wraps a property package"""
    def __init__(self, thCase):
        self.thCase = thCase
        self.name = "Package"

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return '%s = %s' % (self.name, t)

    def GetParent(self):
        """The parent is the thermo case"""
        return self.thCase

    def GetPath(self):
        """Path is the path of the thCase plus the name of the package"""
        return self.thCase.GetPath() + '.' + self.name

    def GetContents(self):
        """Return list of compounds"""
        thCase = self.thCase
        thAdmin = thCase.thermoAdmin
        selCmps = thAdmin.GetSelectedCompoundNames(thCase.provider, thCase.case)
        results = []
        for cmp in selCmps:            
            name = re.sub(' ', '_', cmp)
            results.append(name)
        results = [('Compounds', results)]
        ip = IPMatrices(self)
        results.append((ip.name, ip))        
        return results
           

    def GetObject(self, desc):
        """Returns a wrapper obj of a pure selected compound"""
        thCase = self.thCase
        thAdmin = thCase.thermoAdmin
        selCmps = thAdmin.GetSelectedCompoundNames(thCase.provider, thCase.case)
        desc = re.sub('_', ' ', desc)
        if desc == 'IPMatrices':
            return IPMatrices(self)
        
        for cmp in selCmps:
            if cmp == desc:
                name = re.sub(' ', '_', cmp)
                return PureSelectedCompound(self, name)            
            
class PureSelectedCompound(object):
    """Wraps a pure selected compound"""
    def __init__(self, propPkgObj, name):
        self.propPkgObj = propPkgObj
        self.name = name

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return '%s = %s' % (self.name, t)

    def GetParent(self):
        """Parent is the property package"""
        return self.propPkgObj

    def GetPath(self):
        """Path"""
        return self.propPkgObj.GetPath() + '.' + self.name

    def GetContents(self):
        """Selected compound properties"""
        thKey = GetSimHypoStrings()
        thKey.extend(GetSimHypoDoubles())
        results = []
        for k in thKey:
            results.append((k, PureCompoundProperty(self, k)))
        return results

    def GetObject(self, desc):
        thKey = GetSimHypoStrings()
        thKey.extend(GetSimHypoDoubles())
        if desc in thKey:
            return PureCompoundProperty(self, desc)

        

class PureCompoundProperty(object):
    """Wraps a pure compound property"""
    def __init__(self, pureCmpObj, name):
        self.pureCmpObj = pureCmpObj
        self.name = name

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return '%s = %s' % (self.name, t)      

    def GetParent(self):
        """Parent"""
        return self.pureCmpObj

    def GetPath(self):
        """Path"""
        return self.pureCmpObj.GetPath() + '.' + self.name

    def GetValue(self):
        """Vale of a pure property"""
        cmpName = re.sub(' ', '_', self.pureCmpObj.name)
        thCase = self.pureCmpObj.GetParent().thCase
        thAdmin = thCase.thermoAdmin
        selCmps = thAdmin.GetSelectedCompoundNames(thCase.provider, thCase.case)
        try:
            idx = selCmps.index(cmpName)
            thProp = self.name
            thVal = thAdmin.GetSelectedCompoundProperties(thCase.provider, thCase.case, idx, thProp)[0]
        except:
            thVal = None
        return thVal
        

def SubSpaceForUnder(cmp):
    return re.sub(' ', '_', cmp)

class IPMatrices(object):
    """Dummy object to wrap IPMatrix objects"""
    def __init__(self, propPkgObj):
        
        self.propPkgObj = propPkgObj
        self.name = 'IPMatrices'
        self.thCase = thCase = propPkgObj.thCase
        self.ipMatrNames = thCase.thermoAdmin.GetIPMatrixNames(thCase.provider, thCase.case)
        self.cmpNames = thCase.thermoAdmin.GetSelectedCompoundNames(self.thCase.provider, self.thCase.case)
        self.cmpNamesFixed = map(SubSpaceForUnder, self.cmpNames)
        self.ipMatrNames.sort()
                
    def __str__(self):
        t = str(self.ipMatrNames)
        return '%s = %s' % (self.name, t)      

    def GetCompoundNames(self):
        """list of compound names"""
        return self.cmpNames
    
    def GetCompoundNamesFixed(self):
        """Names with underscore for spaces"""
        return self.cmpNamesFixed    
        
    def GetThermo(self):
        return self.thCase
        
    def GetParent(self):
        """Parent"""
        return self.propPkgObj

    def GetPath(self):
        """Path"""
        return self.GetParent().GetPath() + '.' + self.name

    def GetContents(self):
        result = []
        if self.ipMatrNames:
            for ipMatrName in self.ipMatrNames:
                result.append((ipMatrName, IPMatrix(self, ipMatrName)))
        return result    

    def GetObject(self, desc):
        """Just the value for the given key (desc)"""
        if desc in self.ipMatrNames:
            return IPMatrix(self, desc)
        return None

    def GetMatricesNames(self):
        t = str(self.ipMatrNames)
        return t    
        
    

        
class IPMatrix(object):
    """Wraps an object with the ip matrices"""
    def __init__(self, ipMatrices, name):
        self.ipMatrices = ipMatrices
        self.name = name
        thCase = self.GetThermo()
        thAdmin = thCase.thermoAdmin
        self.paneNames = thAdmin.GetIPPaneNames(thCase.provider, thCase.case, name)
        
    
        ###Lets not load all the kij info for now. 
        
        

    def __str__(self):
        t = str(self.paneNames)
        return '%s = %s' % (self.name, t)

    def GetAllIPInfoForCmp(self, cmpName1):
        """returns a list of all the matching kij info for all compunds with this compound. This is useful or map calls"""
        self.cmpName1 = cmpName1
        return map(self.GetIPInfoActiveCmp, self.cmpNames)
    
    def GetIPInfoActiveCmp(self, cmpName2):
        """Return the kij info for a compound based on an active compound. This is useful or map calls"""
        thCase = self.thCase
        return thCase.thermoAdmin.GetIPInfo(thCase.provider, thCase.case, self.name, self.cmpName1, cmpName2)
    
    def GetIPInfo(self):
        """Returns nested lists of kij info for pairs of compounds"""
        """Load the ip info when needed"""
        #The infor per kij depends only on matrix, not per pane. Load all of that right here and let
        #each pane come and get it from here
        self.thCase = self.GetThermo()
        self.cmpNames = self.GetCompoundNames()
        ipInfo = map(self.GetAllIPInfoForCmp, self.cmpNames)
        del self.thCase
        del self.cmpNames
        
        return ipInfo
    
    def GetCompoundNames(self):
        return self.GetParent().GetCompoundNames()
        
    def GetCompoundNamesFixed(self):
        return self.GetParent().GetCompoundNamesFixed()
            
    def GetThermo(self):
        #Get it from the parent
        return self.GetParent().GetThermo()

    def GetParent(self):
        """Parent"""
        return self.ipMatrices

    def GetPath(self):
        """Path"""
        return self.GetParent().GetPath() + '.' + self.name


    def GetContents(self):
        result = []
        if self.paneNames:
            paneIdx = 0
            for paneName in self.paneNames:
                paneObj = IPPane(self, paneName, paneIdx)
                result.append((paneName, paneObj.GetValues()))
                paneIdx += 1
                
            ## Do not include the info.
            #paneObj = IPPane(self, IPINFO, 0)
            #result.append((IPINFO, paneObj.GetValues()))
            
        return result


    def GetObject(self, desc):
        """Just the value for the given key (desc)"""
        if desc in self.paneNames:
            return IPPane(self, desc, self.paneNames.index(desc))
        if desc == IPINFO:
            return IPPane(self, IPINFO, 0)
        return None


class IPPane(object):
    """Wraps an IP pane"""
    def __init__(self, ipMatrix, name, paneIdx):
        self.ipMatrix = ipMatrix
        self.name = name
        self.idx = paneIdx
        
        #Load the kij values right here
        thCase = self.GetThermo()
        thAdmin = thCase.thermoAdmin
        if name == IPINFO:
            #Info is the same for each pane, so just grab from matrix
            #This should not be getting created very often as it is very time consuming
            self.ipVals = ipMatrix.GetIPInfo()
        else:
            self.ipVals =  thAdmin.GetIPValues(thCase.provider, thCase.case, ipMatrix.name, paneIdx)


    def __str__(self):
        t = ''
        for cmp in self.GetCompoundNamesFixed():
            t += '%s = {%s}\n' %(cmp, str(IPValues(self, cmp)))
        return t

    def GetThermo(self):
        #Get it from the parent
        return self.GetParent().GetThermo()
        
    def GetCompoundNames(self):
        return self.GetParent().GetCompoundNames()
        
    def GetCompoundNamesFixed(self):
        return self.GetParent().GetCompoundNamesFixed()
        
    def GetParent(self):
        """Parent"""
        return self.ipMatrix


    def GetPath(self):
        """Path"""
        return self.GetParent().GetPath() + '.' + self.name
    
    def GetContents(self):
        result = []
        for cmp in self.GetCompoundNamesFixed():
            ipValsObj = IPValues(self, cmp)
            result.append((str(cmp), ipValsObj.GetValues()))
        return result
    
    def GetObject(self, desc):
        """Just the value for the given key (desc)"""
        try:
            return IPValues(self, desc)
        except:
            return None
    
    def GetValues(self):
        """Load information from nested dictionaries into nested lists"""
        if self.name != IPINFO:
        #return self.ipVals
            return map(list, self.ipVals)
        else:
            return self.ipVals
    
class IPValues(object):
    def __init__(self, ipPane, name):
        self.ipPane = ipPane
        self.name = name
        self.cmpName1 = name
    
        ipMatr = ipPane.GetParent()
        
        cmpNames = self.GetCompoundNamesFixed()
        cmpIdx = cmpNames.index(name)
        if ipPane.name == IPINFO:
            self.vals = ipPane.ipVals[cmpIdx]
        else:
            self.vals = array(ipPane.ipVals[cmpIdx, :], Float)
            
    def __str__(self):
        t = ''
        cmpNames = self.GetCompoundNamesFixed()
        vals = self.vals
        for i in range(len(cmpNames)):
            t += '%s = %s; ' %(cmpNames[i], str(vals[i]))
        return t

    def GetThermo(self):
        #Get it from the parent
        return self.GetParent().GetThermo()
        
    def GetCompoundNames(self):
        return self.GetParent().GetCompoundNames()
        
    def GetCompoundNamesFixed(self):
        return self.GetParent().GetCompoundNamesFixed()    
        
    def GetParent(self):
        """Parent"""
        return self.ipPane

    def GetPath(self):
        """Path"""
        return self.GetParent().GetPath() + '.' + self.name

    def GetContents(self):
        result = []
        cmpNames = self.GetCompoundNamesFixed()
        vals = self.vals
        for i in range(len(cmpNames)):
            ipValObj = IPValue(self, cmpNames[i], vals[i])
            result.extend(ipValObj.GetContents())
        return result    
    
    
    def GetObject(self, desc):
        """Just the value for the given key (desc)"""
        cmpNames = self.GetParent().GetCompoundNamesFixed()
        cmpName = re.sub(' ', '_', desc)
        if cmpName in cmpNames:
            idx = cmpNames.index(cmpName)
            return IPValue(self, cmpNames[idx], self.vals[idx])
    
    def SetValues(self, vals, status=None):
        """Sets each value in the child object. Status is just a dummy for conformity with CLI"""
        
        cmpNames = self.GetCompoundNamesFixed()
        if len(cmpNames) != len(vals):
            return
    
        #Make sure they are all numbers and let an error be raised otherwise
        self.vals = array(vals, Float)
        vals = self.vals
    
        i = 0
        for cmp in cmpNames:
            ipValObj = IPValue(self, cmpNames[i], vals[i])
            ipValObj.SetValue(vals[i])
            i+=1
    
    def GetValues(self):
        """Return the stuff from the dictionary"""
        return self.vals

    
    
class IPValue(object):
    """Just wrap a value"""
    def __init__(self, ipValues, name, value):
        self.ipValues = ipValues
        self.name = name
        self.value = value

    def __str__(self):
        t = str(self.GetValue())
        return '%s = %s' % (self.name, t)

    def GetContents(self):
        return [(self.name, self.GetValue())]
            
    def GetThermo(self):
        #Get it from the parent
        return self.GetParent().GetThermo()
        
    def GetCompoundNames(self):
        return self.GetParent().GetCompoundNames()
        
    def GetCompoundNamesFixed(self):
        return self.GetParent().GetCompoundNamesFixed()    

    def GetParent(self):
        """Parent"""
        return self.ipValues

    def GetPath(self):
        """Path"""
        return self.GetParent().GetPath() + '.' + self.name
    
    def GetValue(self):
        """Return the value"""
        return self.value
    
    def SetValue(self, value, status=None):
        """Sets an IP value"""
        ipValuesObj = self.GetParent()
        ipPaneObj = ipValuesObj.GetParent()
        ipMatrixObj = ipPaneObj.GetParent()        

        # cannot set kij info
        if ipPaneObj.name == IPINFO:
            return
        
        try: value = float(value)
        except: return
        thCase = self.GetThermo()
        thAdmin = thCase.thermoAdmin
        ipMatrName = ipMatrixObj.name
        cmpName1 = ipValuesObj.name
        cmpName2 = self.name
        paneIdx = ipPaneObj.idx

        #Use the real internal names to set values
        cmpNames = self.GetCompoundNames()
        if not cmpName1 in cmpNames:
            cmpName1 = re.sub('_', ' ', cmpName1)
        if not cmpName2 in cmpNames:
            cmpName2 = re.sub('_', ' ', cmpName2)
        thAdmin.SetIPValue(thCase.provider, thCase.case, ipMatrName, cmpName1, cmpName2, paneIdx, value)
        
####################################################################################################

class CustomCommandObject(object):
    """wrapper for CustomCommand so they can be referenced as objects"""
    def __init__(self, parentObj):
        self.parent = parentObj

    def SetValue(self, cmd, dummy=None):
        return self.parent.CustomCommand(cmd)

    def Add(self, cmd):
        return self.parent.CustomCommand(cmd)
    

import Oils



