import re
#import ThermoAdmin
from sim.solver.Variables import *
from ThermoAdmin import ThermoCase, ThermoAdmin, CustomCommandObject
from sim.unitop.XYTable import *
from sim.solver.Error import SimError

OILARAM_NAME = 'Name'
OILARAM_VALUE = 'Value'
OILARAM_TYPE = 'Type'
LIGHTENDSNAME = 'LightEndComp'

EXPERIMENT_DIST = 'DistillationCurve'
EXPERIMENT_MW = 'MWCurve'
EXPERIMENT_DEN = 'DensityCurve'
EXPERIMENT_PARAM = 'EXPERIMENT'
EXPERIMENT_CHROMATOGRAPH = 'Chromatograph'

# Assay state
AssayStateBuilding = 0
AssayStateCut = 1
AssayStateInstalled = 2

class OilParameter(object):
    def __init__(self, typeName, value=None, parentObj=None, name=''):
        self.parentObj = parentObj
        self.name = name
        self._type = PropTypes.get(typeName, PropTypes[GENERIC_VAR])
        self._value = value
        if parentObj:
            self.parentObj.IsUpToDate(0)

    def __str__(self):
        return 'OilParameter ' + self.name

    def CleanUp(self):
        self.parentObj = None
        self._type = None

    def GetContents(self):
        """return list of (description, obj) tuples of contained objects"""
        return [(OILARAM_NAME, self.name), (OILARAM_VALUE, self._value), (OILARAM_TYPE, self._type)]        
        
    def GetValue(self):
        return self._value

    def SetValue(self, value, calcStatus):
        # calcStatus is not used
        self._value = value
        self.parentObj.IsUpToDate(0)
        
    def GetType(self):
        return self._type

    def GetPath(self):
        if self.parentObj:
            path = self.parentObj.Getpath()
            return path + '.' + self.name
        else:
            return self.name

    def GetName(self):
        return self.name

    def GetParent(self):
        return self.parentObj
    

class OilExperiment(ATable):
    def __init__(self, exptType):
        ATable.__init__(self, GENERIC_VAR)
        self.name = ''
        self.exptType = exptType
        self.SetSeriesType(0, VPFRAC_VAR)
        self.SetSeriesCount(2)
        if exptType == EXPERIMENT_MW:
            self.SetSeriesType(1, MOLEWT_VAR)
        elif exptType == EXPERIMENT_DEN:
            self.SetSeriesType(1, MASSDEN_VAR)
        elif exptType != EXPERIMENT_CHROMATOGRAPH:
            self.SetSeriesType(1, T_VAR)
                
    def CleanUp(self):
        self.parentObj = None
        super(OilExperiment, self).CleanUp()

    def IsUpToDate(self, val):
        self.parentObj.IsUpToDate(val)

    def Initialize(self, obj):
        # set motifications
        self.GetSeries(0).Initialize(obj, 'X')
        self.GetSeries(1).Initialize(obj, self.exptType)
        
    def GetInputCurve(self):
        # returns the property package values
        assay = self.parentObj
        oil = assay.parentObj
        thCase = oil.GetThermoCase()
        if thCase:
            response = thCase.CustomCommand('Oil.GetInputCurve.' + self.exptType + '.' + oil.name + '.' + assay.name)
            if response[0] >= 0:
                return response[1]
        return ''
        
        
        
    
class OilDict(dict):
    """Dictionary of oilObjects. Inherits from UserDict"""
    def __init__(self, allowedType):
        """Init an empty dictionary"""        
        dict.__init__(self)
        self._allowedType = allowedType

    def __setitem__(self, key, item):
        """Only specified types, no repetitions of values"""
        if not isinstance(item, self._allowedType): return
        if self.has_key(key): return
        if item in self.values(): return
        dict.__setitem__(self, key, item)

    def GetType(self):
        return self._allowedType
    

class LightEnds(object):
    '''Use a dictionary to hold OilParameters.  Each parameter holds a light end fraction'''
    def __init__(self, parentObj, name):
        self.parentObj = parentObj
        self.name = name
        self.lightEndDict = {}
        
    def __str__(self):
        return 'LightEnds ' + self.name

    def CleanUp(self):
        self.parentObj = None
        for key in self.lightEndDict.keys():
            self.lightEndDict[key].CleanUp()
        self.lightEndDict.clear()

    def GetContents(self):
        """return list of (description, obj) tuples of contained objects"""
        result = []
        for key in self.lightEndDict.keys():
            result.append((key, self.lightEndDict[key]))
        return result

    def GetPath(self):
        path = self.parentObj.Getpath()
        return path + '.' + self.name

    def GetName(self):
        return self.name

    def GetParent(self):
        return self.parentObj

    def AddObject(self, fraction, name):
        le = OilParameter(GENERIC_VAR, fraction, self, name)
        self.lightEndDict[name] = le
        self.IsUpToDate(0)
        
    def DeleteObject(self, obj):
        if self.lightEndDict.has_key(obj.name):
            del self.lightEndDict[obj.name]
            self.IsUpToDate(0)
        obj.CleanUp()

    def GetObject(self, name):
        if self.lightEndDict.has_key(name):
            return self.lightEndDict[name]
        return None

    def IsUpToDate(self, val):
        self.parentObj.IsUpToDate(val)
        

class BasicOilObject(object):
    """Base class for oil objects: case, oil, assay"""
    def __init__(self, name='', parentObj=None):
        self.name = name
        self.parentObj = parentObj
        self.parameters = OilDict(OilParameter)
        self.childDict = None
        self.childType = None
        self.isUpTodate = 1
        self.customCommandObj = CustomCommandObject(self) 

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return '%s = %s' % (self.name, t)

    def CleanUp(self):
        for key in self.parameters.keys():
            self.parameters[key].CleanUp()
        self.parameters.clear()
        
        if self.childDict:            
            for key in self.childDict.keys():
                self.childDict[key].CleanUp()
            self.childDict.clear()
        self.customCommandObj = None
        self.parentObj = None
   
    def GetContents(self):
        """return list of (description, obj) tuples of contained objects"""
        result = []
        params = self.parameters.keys()
        params.sort()
        for key in params:
            result.append((key, self.parameters[key]))
        if self.childDict:
            children = self.childDict.keys()
            children.sort()
            for key in children:
                result.append((key, self.childDict[key]))
        return result    

    def SetParameterValue(self, paramName, typeName, value=None):
        """Set the value of a parameter"""
        param = OilParameter(self, paramName, typeName, value)
        self.parameters[paramName] = param

    def GetThermoCase(self):
        if hasattr(self, 'thCaseObj'):
            return self.thCaseObj
        elif self.parentObj:
            return self.parentObj.GetThermoCase()
        else:
            return None

    def GetPath(self):
        if self.parentObj:
            path = self.parentObj.GetPath()
            return path + '.' + self.name
        else:
            return self.name

    def GetName(self):
        return self.name

    def SetName(self, name):
        self.name = name

    def GetParent(self):
        return self.parentObj

    def SetChildDictType(self, type):
        self.childType = type
        self.childDict = OilDict(type)

    def AddObject(self, obj, name):
        # Try to add unknown objects as parameter
        if isinstance(obj, OilParameter):
            obj.parentObj = self
            obj.name = name
            self.parameters[name] = obj
            self.isUpTodate = 0
            #Notify the property package
            thCase = self.GetThermoCase()            
            if thCase:
                thCase.thermoAdmin.SetAssayParameterValue(thCase.provider, thCase.case, obj)            
            
        elif isinstance(obj, self.childType):
            obj.parentObj = self
            obj.name = name
            self.childDict[name] = obj
            self.isUpTodate = 0
        
        elif name == 'NewName':
            # rename object
            if not self.parentObj.childDict.has_key(obj):
                del self.parentObj.childDict[self.name]
                self.name = obj
                self.parentObj.childDict[obj] = self
                if thCase:                
                    thCase.thermoAdmin.DeleteOilObject(thCase.provider, thCase.case, self)

        elif isinstance(obj, str):
            # try adding it as a parameter
            # see if it can be a number
            try:
                val = int(obj)
            except ValueError:
                try:
                    val = float(obj)
                except ValueError:
                    val = str(obj)  # leave it as string
                
            # Create a generic OilParameter
            obj = OilParameter(GENERIC_VAR, val)
            self.AddObject(obj, name)
        else:
            return

    def DeleteObject(self, obj):
        if isinstance(obj, OilParameter):
            if self.parameters.has_key(obj.name):
                del self.parameters[obj.name]
                self.isUpTodate = 0
            
        elif isinstance(obj, self.childType):
            if self.childDict.has_key(obj.name):
                thCase = self.GetThermoCase()
                if thCase:                
                    thCase.thermoAdmin.DeleteOilObject(thCase.provider, thCase.case, obj)
                if isinstance(obj, OilExperiment):
                    obj.Initialize(None)
                del self.childDict[obj.name]
                self.isUpTodate = 0
        obj.CleanUp()

                
    def GetObject(self, name):
        if self.parameters.has_key(name):
            return self.parameters[name]
        elif self.childDict.has_key(name):
            return self.childDict[name]
        elif hasattr(self, 'thCaseObj') and self.thCaseObj.name == name:
            return self.thCaseObj
        elif name == 'CustomCommand':
            return self.customCommandObj       
        return None

    def CustomCommand(self, cmd):
        # Any commands are redirected to the thermo case
        thCase = self.GetThermoCase()
        if thCase:
            try:
                result = thCase.CustomCommand('Oil.' + cmd)
            except SimError, e:
                result = e.extraData
            except:
                raise SimError('ErrorValue', cmd + ' failed.')                 
            return result

    def GetCompoundNames(self):        
        thCase = self.GetThermoCase()
        result = None
        if thCase:
            if thCase.thermoAdmin:
                result = thCase.thermoAdmin.GetSelectedCompoundNames(thCase.provider, thCase.case)
        return result
        
    def IsUpToDate(self, val):
        self.isUpTodate = val


class OilCase(BasicOilObject):
    def __init__(self, thermoCase=None):
        BasicOilObject.__init__(self, 'OilCase')
        self.thCaseObj = thermoCase
        self.parentObj = thermoCase   # to make Getpath happy
        # OilCases contains a dictionary of 'Oil'
        self.SetChildDictType (Oil)

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return '%s = %s' % (self.name, t)

    def SetThermoCase(self, thCase):
        self.thCaseObj = thCase
        self.parentObj = thCase

    def CleanUp(self):
        self.thCaseObj = None
        super(OilCase, self).CleanUp()
        
    def AdjustOldCase(self, version):
        if version[0] < 62:
            for oil in self.childDict.values():
                for assay in oil.childDict.values():
                    if not hasattr(assay, '_attachedPort'):
                        assay._attachedPort = []
        

class Oil(BasicOilObject):
    def __init__(self):
        BasicOilObject.__init__(self)
        # Oil contains a dictionary of 'Assay'
        self.SetChildDictType (Assay)
        self.autoCutBeforeBlend = 0


    def AddObject(self, obj, name):
        if isinstance(obj, Blend):
            thCase = self.GetThermoCase()            
            if thCase == None: return
            try:
                obj.name = name
                obj.parentObj = self              
                # convert assay names to objects
                obj.assays = []
                for a in obj.assayNames:
                    # cut the assay first
                    assay = self.childDict[a.strip()]
                    if self.autoCutBeforeBlend:
                        try:
                            assay.CustomCommand('Cut')
                        except:
                            raise SimError('ErrorValue', 'Failed to cut ' + assay.name + ' before blending') 
                    obj.assays.append(assay)

                response = thCase.thermoAdmin.BlendAssay(thCase.provider, thCase.case, obj)
                # add the blend if successful
                if response[0] >= 0:
                    self.childDict[name] = obj
                    self.isUpTodate = 0
            except:
                raise SimError('ErrorValue', 'Blend failed')             
        else:
            return super(Oil, self).AddObject(obj, name)
        
        
        
        
class Assay(BasicOilObject):
    def __init__(self):
        BasicOilObject.__init__(self)
        # Assay contains a dictionary of oil experiments
        # Typically, it contains 3 xy curves: distilaltion curve, MW curve and density curve
        self.SetChildDictType (OilExperiment)
        # assay contains a dictionary of lightend
        self.lightEnds = LightEnds(self, LIGHTENDSNAME)
        self.distCurve = None
        self.MWCurve = None
        self.denCurve = None
        self.chromatograph = None
        # parameters
        self.state = AssayStateBuilding
        # attached port
        self._attachedPort = []
                

    def CleanUp(self):
        self.lightEnds.CleanUp()
        self.lightEnds = None
        if self.distCurve:
            self.distCurve.CleanUp()
            self.distCurve = None
        if self.MWCurve:
            self.MWCurve.CleanUp()
            self.MWCurve = None
        if self.denCurve:
            self.denCurve.CleanUp()
            self.denCurve = None
        if self.chromatograph:
            self.chromatograph.CleanUp()
            self.chromatograph = None
        for port in self._attachedPort:
            port.RemoveFromBorrowedIn(self)
        self._attachedPort = []
        super(Assay, self).CleanUp()
 
    def DistillationCurveName(self):
        if self.distCurve:
            return self.distCurve.name
        else:
            return ''

    def MWCurveName(self):
        if self.MWCurve:
            return self.MWCurve.name
        else:
            return ''

    def DensityCurveName(self):
        if self.denCurve:
            return self.denCurve.name
        else:
            return ''

    def ChromatographName(self):
        if self.chromatograph:
            return self.chromatograph.name
        else:
            return ''

    def GetObject(self, name):
        if name == LIGHTENDSNAME:
            return self.lightEnds
        
        elif name == EXPERIMENT_DIST:            #'DistillationCurve'
            return self.distCurve
        elif name == EXPERIMENT_MW:              #'MWCurve'
            return self.MWCurve
        elif name == EXPERIMENT_DEN:             #'DensityCurve'
            return self.denCurve
        elif name == EXPERIMENT_CHROMATOGRAPH:   #'Chromatograph'
            return self.chromatograph
        
        else:
            return super(Assay, self).GetObject(name)
                    
    def GetContents(self):
        result = super(Assay, self).GetContents()
        result.append((LIGHTENDSNAME, self.lightEnds))
        return result
        
    def AddObject(self, obj, name):
        # Allow only one distillation curve, one MW curve and one density curve
        if isinstance(obj, OilExperiment):
            if obj.exptType == EXPERIMENT_MW:
                if self.MWCurve:
                     self.DeleteObject(self.MWCurve)
                self.MWCurve = obj
            elif obj.exptType == EXPERIMENT_DEN:
                if self.denCurve:
                    self.DeleteObject(self.denCurve)
                self.denCurve = obj
            elif obj.exptType == EXPERIMENT_CHROMATOGRAPH:
                if self.chromatograph:
                    self.DeleteObject(self.chromatograph)
                self.chromatograph = obj
            else:
                if self.distCurve:
                    self.DeleteObject(self.distCurve)
                self.distCurve = obj
            # set notifications
            obj.Initialize(self)            
        return super(Assay, self).AddObject(obj, name)

    def CustomCommand(self, cmd):
        try:
            thCase = self.GetThermoCase()            
            if thCase == None:
                return None
            if cmd == 'Cut':                
                result = thCase.thermoAdmin.CutAssay(thCase.provider, thCase.case, self)
                if self.state >= AssayStateInstalled:
                    # recut after install
                    self.state = AssayStateCut + AssayStateInstalled
                else:
                    self.state = AssayStateCut
                self.isUpTodate = 1
            elif cmd == 'InstallOil':
                result = thCase.thermoAdmin.InstallOil(thCase.provider, thCase.case, self)
                self.state = AssayStateInstalled
                self.isUpTodate = 1
                
                # update attached port composition using a working copy
                vals = self.GetFraction()
                workList = self._attachedPort[:]
                for port in workList:
                    port.GetCompounds().SetValues(vals, FIXED_V)
                    # SetValues will disconnect, re-attach with the new object
                    port.AttachToObject(self)
                
            elif cmd == 'UpdateOil':                
                result = thCase.thermoAdmin.UpdateOil(thCase.provider, thCase.case, self)
                self.state = AssayStateInstalled
                self.isUpTodate = 1
            elif cmd == 'DeletePseudos':
                result = thCase.thermoAdmin.DeleteOilObject(thCase.provider, thCase.case, self)
                self.state = self.state - AssayStateInstalled # Note that i can be Cut or building
                # No change in isUpTodate flag
            elif cmd == 'GetOilComposition':
                result = thCase.thermoAdmin.GetOilComposition(thCase.provider, thCase.case, self)
            else:
                result = super(Assay, self).CustomCommand(cmd)
            
        except SimError, e:
            result = e.extraData
        except:
            raise SimError('ErrorValue', cmd + ' failed in Oils.py.') 
        return result

    def AssayState(self):
        return self.state

    def AssayUpToDate(self):
        return self.isUpTodate
        
    def ForgetAllCalculations(self):
        # Called by the DataSeries on data change
        self.isUpTodate = 0
 
    def GetFraction(self):
        # Method to get the fraction of installed oil        
        try:
            cmps = self.CustomCommand('GetOilComposition')
            return cmps
        except:
            return None
        
    def AttachToPort(self, port):
        if not port in self._attachedPort:
            self._attachedPort.append(port)
        
    def DeleteObject(self, obj):
        # The attached port is being deleted
        if obj in self._attachedPort:
            idx = self._attachedPort.index(obj)
            del self._attachedPort[idx]
            
            
class Blend(Assay):
    def __init__(self, *args):
        Assay.__init__(self)
        self.assayNames = args
        self.oilObject = None
        
        
    def CleanUp(self):
        self.assays = []
        super(Blend, self).CleanUp()

