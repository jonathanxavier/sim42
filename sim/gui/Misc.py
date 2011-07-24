"""Miscellaneous Objects and Functions"""

import string, sys, os, StringIO

from sim.solver.Variables import *
from sim.solver import S42Glob
from sim.unitop import *
from sim.solver import *

from wxPython.wx import *
from wxPython.grid import *

class BaseInterpreterParent(object):
    def __init__(self, wxParent, thAdmin, parentFlowsh, autoSolve=1):
        self.wxParent = wxParent
        self.thAdmin = thAdmin
        self.parentFlowsh = parentFlowsh
        self.autoSolve = autoSolve

        self.locals = {'thAdmin': thAdmin, 'parentFlowsh': parentFlowsh}

    def CloseFrameNotify(self, frame):
        """Notify the interpreter parent that 'frame' is being close"""
        pass
    
    def SendAndExecCode(self, code):
        """Execute code and do any neccessary manipulations to it"""
        self.locals['thAdmin'] = self.thAdmin
        self.locals['parentFlowsh'] = self.parentFlowsh
        exec(code, globals(), self.locals)
        
        if self.GetAutoSolveStatus(): code = 'parentFlowsh.Solve()'
        else: code = 'parentFlowsh.SolverForget()'
        exec(code, globals(), self.locals)
        
        if hasattr(self.wxParent, 'UpdateView'):
            self.wxParent.UpdateView()
                
    def GetParentFlowsh(self):
        return self.parentFlowsh
    
    def GetThAdmin(self):
        return self.thAdmin
    
    def GetAutoSolveStatus(self):
        return self.autoSolve
    
    def SetAutoSolveStatus(self, autoSolve):
        self.autoSolve = autoSolve

class BaseObjectFrame(wxFrame):
    def __init__(self, parent, log, interpParent=None, obj=None):
        wxFrame.__init__(self, parent, -1, "Base Object Frame", style=wxDEFAULT_FRAME_STYLE)
##                          style=wxDEFAULT_DIALOG_STYLE|wxDIALOG_MODAL|wxRESIZE_BORDER)
        EVT_CLOSE(self, self.OnCloseWindow)

        self.inObj = obj
        self.panels = []

        if not self.inObj: #Create a sample simulation
            (self.thAdmin, self.parentFlowsh) = RunSimTest(1)
            
        if not interpParent:
            interpParent = BaseInterpreterParent(self, self.thAdmin, self.parentFlowsh, true)
            
        self.interpParent = interpParent

    def GetSimObject(self):
        return self.inObj
        
    def OnCloseWindow(self, event):
        self.interpParent.CloseFrameNotify(self)
        if not self.inObj: #If everything was created here, do a CleanUp
            self.thAdmin.CleanUp()
            self.parentFlowsh.CleanUp()
        self.CleanUp()
        self.Destroy()
            
    def CleanUp(self):
        """Clean up"""
        del self.inObj
        for panel in self.panels: 
            if hasattr(panel, "CleanUp"): panel.CleanUp()
        del self.panels

    def UpdateView(self):
        for panel in self.panels: 
            if hasattr(panel, "UpdateView"): panel.UpdateView()


def RunSimTest(testNo=1):
    from sim.thermo import ThermoAdmin
    from sim.solver import Flowsheet
    from sim.unitop import Flash

    if testNo == 1:
        #Do a basic simulation
        thCase = "TestCase1"
        thAdmin = ThermoAdmin.ThermoAdmin()
        parentFlowsh = Flowsheet.Flowsheet()
        parentFlowsh.SetThermoAdmin(thAdmin)
        parentFlowsh.name = '/'
        thCaseObj = thAdmin.AddPkgFromName("VirtualMaterials", thCase, "RK")
        parentFlowsh.SetThermo(thCaseObj)
        thAdmin.AddCompound("VirtualMaterials", thCase, "METHANE")
        thAdmin.AddCompound("VirtualMaterials", thCase, "PROPANE")
        thAdmin.AddCompound("VirtualMaterials", thCase, "n-HEXANE")
        uOp = Flash.SimpleFlash()
        parentFlowsh.AddUnitOperation(uOp, "FlashTestCase1")
        port = uOp.GetPort('In')
        port.SetCompositionValues((0.33, 0.33, 0.34), FIXED_V)
    elif testNo == 2:
        from sim.cmd.CommandInterface import CommandInterface
        thAdmin = ThermoAdmin.ThermoAdmin()
        parentFlowsh = Flowsheet.Flowsheet()
        parentFlowsh.SetThermoAdmin(thAdmin)
        parentFlowsh.name = '/'
        cmdproc = CommandInterface(parentFlowsh)
        GUI_PATH = os.getcwd()
        fPath = os.path.join(os.path.split(GUI_PATH)[0], 'cmd', 'test', 'gasplant.tst')
        f = open(fPath, 'r')
        s = f.read()
        inString = StringIO.StringIO(s)
        outString = StringIO.StringIO()
        cmdproc.ProcessCommandStream(inString, outString, outString)
    elif testNo == 3:
        from sim.cmd.CommandInterface import CommandInterface
        thAdmin = ThermoAdmin.ThermoAdmin()
        parentFlowsh = Flowsheet.Flowsheet()
        parentFlowsh.name = '/'
        parentFlowsh.SetThermoAdmin(thAdmin)
        cmdproc = CommandInterface(parentFlowsh)
        GUI_PATH = os.getcwd()
        fPath = os.path.join(os.path.split(GUI_PATH)[0], 'cmd', 'test', 'flowsheet1.tst')
        f = open(fPath, 'r')
        s = f.read()
        inString = StringIO.StringIO(s)
        outString = StringIO.StringIO()
        cmdproc.ProcessCommandStream(inString, outString, outString)
    elif testNo == 4:
        from sim.cmd.CommandInterface import CommandInterface
        thAdmin = ThermoAdmin.ThermoAdmin()
        parentFlowsh = Flowsheet.Flowsheet()
        parentFlowsh.name = '/'
        parentFlowsh.SetThermoAdmin(thAdmin)
        cmdproc = CommandInterface(parentFlowsh)
        GUI_PATH = os.getcwd()
        fPath = os.path.join(os.path.split(GUI_PATH)[0], 'cmd', 'test', 'aheatex.tst')
        f = open(fPath, 'r')
        s = f.read()
        inString = StringIO.StringIO(s)
        outString = StringIO.StringIO()
        cmdproc.ProcessCommandStream(inString, outString, outString)
        
    else:
        #Do a basic simulation
        thCase = "TestCase1"
        thAdmin = ThermoAdmin.ThermoAdmin()
        parentFlowsh = Flowsheet.Flowsheet()
        parentFlowsh.SetThermoAdmin(thAdmin)
        parentFlowsh.name = '/'
        thCaseObj = thAdmin.AddPkgFromName("VirtualMaterials", thCase, "RK")
        parentFlowsh.SetThermo(thCaseObj)
        thAdmin.AddCompound("VirtualMaterials", thCase, "METHANE")
        thAdmin.AddCompound("VirtualMaterials", thCase, "PROPANE")
        thAdmin.AddCompound("VirtualMaterials", thCase, "n-HEXANE")
        uOp = Flash.SimpleFlash()
        parentFlowsh.AddUnitOperation(uOp, "FlashTestCase1")
        port = uOp.GetPort('In')
        port.SetCompositionValues((0.33, 0.33, 0.34), FIXED_V)
        port.SetPropValue(T_VAR, 273.15, FIXED_V)
        port.SetPropValue(P_VAR, 101, FIXED_V)

    return (thAdmin, parentFlowsh)


class PortDisplayInfo(object):
    """Holds the basic info to display the info of a port"""
    def __init__(self, propList=None):
        """Init with the required properties"""
        self._props = []
        self._units = []
        if not propList:
            for i in GetReqExtensivePropertyNames(): self.AddProp(i)
            for i in GetReqIntensivePropertyNames(): self.AddProp(i)
        else:
            for i in propList: self.AddProp(i)

    def _GetUnitItem(self, propName, unit=None):
        """Get a unitItem for a given propName depending on the value of unit"""
        if not unit:
            unitType = PropTypes.get(propName, PropTypes[GENERIC_VAR]).unitType
            unit = S42Glob.unitSystem.GetCurrentUnit(unitType)
        elif isinstance(unit, str) or isinstance(unit, unicode):
            unitType = PropTypes.get(propName, PropTypes[GENERIC_VAR]).unitType
            units = S42Glob.unitSystem.UnitsByPartialName(unit, unitType)
            if not len(units): unit = None
            else: unit = units[0]
        elif not isinstance(unit, vmgunits.units.UnitItem):
            raise TypeError, "The parameter unit must be None, a string or a UnitItem"
        return unit

    def GetPropList(self):
        return list(self._props)

    def GetUnitList(self):
        return list(self._units)

    def AddProp(self, propName, unit=None):
        """Add a property along with units. If units==None, get current units"""
        unit = self._GetUnitItem(propName, unit)
        self._props.append(propName)
        self._units.append(unit)

    def SetProp(self, idx, propName, unit=None):
        """Set a property in a specific place"""
        if idx+1 == len(self._props):
            self.AddProp(propName, unit)
        else:
            unit = self._GetUnitItem(propName, unit)
            self._props[idx] = propName
            self._units[idx] = unit

    def InsertProp(self, idx, propName, unit=None):
        """Insert a property in a specific place"""
        if idx+1 == len(self._props):
            self.AddProp(propName)
            self.AddProp(propName, unit)
        else:
            unit = self._GetUnitItem(propName, unit)
            self._props.insert(idx, propName)
            self._units.insert(idx, unit)

    def DelProp(self, idx):
        """Delete a property"""
        if idx >= 0 and idx < len(self._props):
            del self._props[idx]
            del self._units[idx]

    def SetUnit(self, idx, unit):
        """Sets a different unit for an existing prop"""
        propName = self._props[idx]
        self._units[idx] = self._GetUnitItem(propName, unit)

    def GetProp(self, idx):
        return self._props[idx]

    def GetUnit(self, idx):
        return self._units[idx]

    def GetPropUnitTuple(self, idx):
        """Get a tuple (propName, UnitItem)"""
        try: myTuple = (self._props[idx], self._units[idx])
        except: myTuple = (None, None)
        return myTuple
    
