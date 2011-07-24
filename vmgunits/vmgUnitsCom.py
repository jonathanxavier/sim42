"""implements a COM version of the unit system"""

import sys, os
import units
from pythoncom import CLSCTX_LOCAL_SERVER, CLSCTX_INPROC

class PyUnitsCom:
    """COM accessible version of CommandInterface"""  
    _reg_clsid_ = "{BE460C2B-3ED2-4855-B0EA-AB7D8CC52FD0}"
    _reg_desc_  = "VMG Unit System COM component"
    _reg_progid_ = "VMGSim.units"
    _reg_clsctx_ = CLSCTX_INPROC
    _public_methods_ = [
            'BaseDataPath',
            'GetSetNames',
            'GetUnits',
            'GetUnitIDs',
            'UnitsByType',
            'UnitsByPartialName',
            'SetDefaultSet',
            'GetTypeID',
            'GetTypeIDs',
            'GetTypeName',
            'GetUnit',
            'GetUnitWithID',
            'GetCurrentUnit',
            'GetSim42Unit',
            'GetUserDir',
            'SetUserDir',
            'ActiveListLength',
            'ActiveUnitFromList',
            'ConvertFromBase',
            'ConvertToBase',
            'ConvertToSim42',
            'ConvertFromSim42',
            'RenderConversion',
            'ActiveUnitItem',
            'ConvertToDefault',
            'ConvertFromDefaultToBase',
            'ConvertToSim42b',
            'ConvertFromSim42b',
            'ValueList'
        ]
    _public_attrs_ = []
    _readonly_attrs_ = []
    
    def __init__(self):
        self.myActiveUnitItem = None
        self.myActiveUnitList = None
        self.myUnitSystem = units.UnitSystem()

    def BaseDataPath(self):
        return self.myUnitSystem.baseDataPath

    #---------------------------------------------------
    def SetActiveUnitList(self, unitItemList):
        self.myActiveUnitList = unitItemList
        names = []
        for i in unitItemList:
            names.append(i.name)
        return names

    def SetActiveUnitItem(self, ui):
        self.myActiveUnitItem = ui
        if ui:
            return ui.name
        else:
            return ''
    #---------------------------------------------------
        
    def GetSetNames(self):
        return self.myUnitSystem.GetSetNames()

    def GetUnits(self):
        ui = self.myUnitSystem.GetUnits()
        result = self.SetActiveUnitList(ui)
        return result

    def GetUnitIDs(self):
        return self.myUnitSystem.GetUnitIDs()

    def UnitsByType(self, typeID):
        """return list units with type typeID"""
        itemList = self.myUnitSystem.UnitsByType(typeID)
        return self.SetActiveUnitList(itemList)
    
    def UnitsByPartialName(self, name, typeID=None):
        """return list of units that match name and typeID (if it is not None)"""
        return self.SetActiveUnitList(self.myUnitSystem.UnitsByPartialName(str(name), typeID))
    
    def SetDefaultSet(self, setName):
        self.myUnitSystem.SetDefaultSet(str(setName))
        return setName

    def GetTypeID(self, typeName):
        """returns type id from a name"""
        return self.myUnitSystem.GetTypeID(str(typeName))
    
    def GetTypeIDs(self):
        """return list of type ids"""
        return self.myUnitSystem.GetTypeIDs()
    
    def GetTypeName(self, typeID):
        """returns name of type with id typeID"""
        return self.myUnitSystem.GetTypeName(typeID)
    
    def GetUnit(self, unitSetName, typeID):
        """returns the unit in unitSet set for typeID"""
        us = self.myUnitSystem.GetUnitSet(unitSetName)
        return self.SetActiveUnitItem(self.myUnitSystem.GetUnit(us, typeID))
    
    def GetUnitWithID(self, id):
        return self.SetActiveUnitItem(self.myUnitSystem.GetUnitWithID(id))
    
    def GetCurrentUnit(self, typeID):
        """returns unit in default unit set with type typeID"""
        return self.SetActiveUnitItem(self.myUnitSystem.GetCurrentUnit(typeID))
    
    def GetSim42Unit(self, typeID):
        """returns the Sim42 property package unit with type typeID"""
        return self.SetActiveUnitItem(self.myUnitSystem.GetSim42Unit(typeID))
    
    def GetUserDir(self):
        """return the current user directory"""
        return self.myUnitSystem.GetUserDir()
    
    def SetUserDir(self, path):
        """set the userDataPath to path"""
        self.myUnitSystem.SetUserDir(str(path))
        return self.myUnitSystem.GetUserDir()

#-----------------------------------------------------------------
    def ActiveListLength(self):
        return len(self.myActiveUnitList)
    
    def ActiveUnitFromList(self, idx):
        return self.SetActiveUnitItem(self.myActiveUnitList[idx])

    def ActiveUnitItem(self):
        result = []
        if (self.myActiveUnitItem != None):
            result.append(self.myActiveUnitItem.name)
            result.append(self.myActiveUnitItem.id)
            result.append(self.myActiveUnitItem.typeID)
            result.append(self.myActiveUnitItem.scale)
            result.append(self.myActiveUnitItem.offset)
            result.append(self.myActiveUnitItem.operation)
            result.append(self.myActiveUnitItem.notes)
        return result

    def ConvertFromBase(self, value):
        return self.myActiveUnitItem.ConvertFromBase(value)
            
    def ConvertToBase(self, value):
        return self.myActiveUnitItem.ConvertToBase(value)
    
    def ConvertToSim42(self, value):
        ui = self.myActiveUnitItem      
        return ui.ConvertToSim42(value)
    
    def ConvertFromSim42(self, value):
        return self.myActiveUnitItem.ConvertFromSim42(value)

    def RenderConversion(self):
        result = self.myActiveUnitItem.RenderOperation()
        items = self.myUnitSystem.UnitsByType(self.myActiveUnitItem.typeID)
        for i in items:
            if (i.scale == 1.0 and i.offset == 0.0):
                result = result.replace('Base', i.name)
                break
        return result

    def ConvertToDefault(self, typeId, itemName, value):
        items = filter(lambda u, n=itemName, id=typeId: u.typeID == id and u.name == n,
                     self.myUnitSystem.units.values())        
        id = items[0].id        
        id2 = self.myUnitSystem.defaultSet[typeId]
        if (id != None and id != id2):
            baseValue = items[0].ConvertToBase(value)
            value = self.myUnitSystem.units[id2].ConvertFromBase(baseValue)
        return value

    def ConvertFromDefaultToBase(self, typeId, value):
        id = self.myUnitSystem.defaultSet[typeId]
        if (id != None):
            value = self.myUnitSystem.units[id].ConvertToBase(value)
        return value


    def ConvertToSim42b(self, typeId, itemName, value):
        items = filter(lambda u, n=itemName, id=typeId: u.typeID == id and u.name == n,
                     self.myUnitSystem.units.values())        
        id = items[0].id        
        if (id != None):
            value = items[0].ConvertToSim42(value)
        return value

    def ConvertFromSim42b(self, typeId, itemName, value):
        # if itemName = '' signifies value in current unitset
        if itemName == '':
            value = self.myUnitSystem.GetCurrentUnit(typeId).ConvertFromSim42(value)
        else:
            items = filter(lambda u, n=itemName, id=typeId: u.typeID == id and u.name == n,
                     self.myUnitSystem.units.values())        
            id = items[0].id        
            if (id != None):
                value = items[0].ConvertFromSim42(value)
        return value

    def ValueList(self, typeId, value):
        # Given a numberic value in the default unit, returns a list
        # containing the same values in all different units
        baseValue = self.ConvertFromDefaultToBase(typeId, value)
        results = []
        units = []
        for unitSetName in self.myUnitSystem.GetSetNames():
            us = self.myUnitSystem.GetUnitSet(unitSetName)
            unitItem = self.myUnitSystem.GetUnit(us, typeId)
            if not unitItem.name in units:
                units.append(unitItem.name)
                results.append(unitItem.ConvertFromBase(baseValue))
        return [results, units]



        
#  def GetUnitSet(self, setName):
#  def GetType(self, typeID):
#  def GetTypes(self): 

def Test():
    units = PyUnitsCom()
    result = units.ValueList(2, 100.0)
    
    for unit in units.UnitsByType(2):
        print unit       
    for unit in units.UnitsByPartialName('k', 32):
        print unit
    id = units.GetTypeID('MoleFlow')
    print 'Type ID for MoleFlow', id

    item = units.GetUnit("Field", 1)
    print item
    desc = units.RenderConversion()
    print desc
    val = units.ConvertToSim42(400.0)
    print val
    val = units.ConvertFromDefaultToBase(3, 100.0)
    print val
    
    val = units.SetDefaultSet("Field")
    print val
    val = units.ConvertToDefault(2, "C", 100.0)
    print val
    val = units.ConvertToDefault(2, "K", 100.0)
    print val
    val = units.ConvertToDefault(2, "R", 100.0)
    print val

    val = units.ConvertFromSim42b(1,"psia",101.325)
    print val
    val = units.ConvertToSim42b(1, "psia", 14.696)
    print val

    val = units.ConvertFromSim42b(1, "", 101.325)
    print val


if __name__ == '__main__':
        import win32com.server.register
        import _winreg
        if len(sys.argv) > 1 and sys.argv[1] == 'unregister':
            win32com.server.register.UnregisterClasses(PyUnitsCom)
            software_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE')
            vmg_key = _winreg.OpenKey(software_key, 'VMG')
            _winreg.DeleteKey(vmg_key, 'vmgsimdll')
            _winreg.CloseKey(vmg_key)
            _winreg.CloseKey(software_key)
        else:
            #import wingdbstub
            win32com.server.register.UseCommandLine(PyUnitsCom)
            software_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE')
            vmg_key = _winreg.CreateKey(software_key, 'VMG')
            _winreg.SetValue(vmg_key, 'vmgsimdll', _winreg.REG_SZ, os.path.abspath(os.curdir))
            _winreg.CloseKey(vmg_key)
            _winreg.CloseKey(software_key)
            #Test()

    

    
