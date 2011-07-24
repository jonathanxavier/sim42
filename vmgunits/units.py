#!/usr/bin/python

""" Units module - contains classes and methods for doing unit conversions. 
Inspired by the Virtual Materials Group unit system"""

import sys, os, imp, re, string
EMPTY_VAL = -12321
IniternalUnitItemOffset = 10000

ConvertToBaseOps = [
                    lambda value, scale, offset: scale * value + offset,
                    lambda value, scale, offset: scale / value + offset,
                    lambda value, scale, offset: scale * value * value + offset,
                    lambda value, scale, offset: scale / value / value + offset,
                    lambda value, scale, offset: offset,
                    lambda value, scale, offset: scale / (value + offset)
                    ]

ConvertFromBaseOps = [
                    lambda value, scale, offset: (value - offset) / scale,
                    lambda value, scale, offset: scale / (value - offset),
                    lambda value, scale, offset: Math.sqrt((value - offset) / scale),
                    lambda value, scale, offset: Math.sqrt(scale / (value - offset)),
                    lambda value, scale, offset: offset,
                    lambda value, scale, offset: (scale / value) - offset
                    ]

OperationRenderings = [
                    '%f * (%s) + %f',
                    '%f / (%s) + %f',
                    '%f * (%s)^2 + %f',
                    '%f / (%s)^2 + %f',
                    '%f * (%s) + %f',
                    '%f / (%s + %f)'
                    ]

OperationsScaleOnly = [
                    '%f * (%s)',
                    '%f / (%s)',
                    '%f * (%s)^2',
                    '%f / (%s)^2',
                    '%f',
                    '%f * (%s)'
                    ]

# this global variable can be externally set to indicate where the unit
# data files are kept - particularly useful for frozen apps.
globalBasePath = None

class UnitItem:
    """Basic unit in unit system"""
    def __init__(self, unitSystem):
        """initialize attributes"""
        self.unitSystem = unitSystem
        self.id = 0
        self.typeID = 0
        self.name = 'Unknown'
        self.scale = 1.0
        self.offset = 0.0
        self.operation = 1
        self.notes = 'Unknown'

    def CleanUp(self):
        self.unitSystem = None
        
    def ReadFile(self, f):
        """
        read a line from a tab separated file to initialize values
        return the type id if successful or None if not
        """
        line = f.readline()
        if not line: return None

        fields = re.split(r'\t', string.strip(line))
        
        if fields[0] == 'ID':  # check for header line
            line = f.readline()
            if not line: return None
            fields = re.split(r'\t', string.strip(line))

        self.id = int(fields[0])
        self.typeID = int(fields[1])
        self.name = fields[2]
        self.scale = float(fields[3])
        self.offset = float(fields[4])
        self.operation = int(fields[5])
        try:
            self.notes = fields[6]
        except:
            self.notes = ''
        return self.id
    
    def WriteFile(self, f):
        """
        write a line to a tab separated file
        """
        f.write('%d\t%d\t%s\t%e\t%e\t%d\t%s\n' % (
            self.id, self.typeID, self.name, self.scale, self.offset,
            self.operation, self.notes ))
    
    def ConvertFromBase(self, value):
        if value == None: return None
        return ConvertFromBaseOps[self.operation - 1](value, self.scale, self.offset)
    
    def ConvertToBase(self, value):
        if value == None: return None
        return ConvertToBaseOps[self.operation - 1](value, self.scale, self.offset)

    def ConvertToSim42(self, value):
        baseValue = self.ConvertToBase(value)
        sim42Unit = self.unitSystem.GetSim42Unit(self.typeID)
        return sim42Unit.ConvertFromBase(baseValue)
    
    def ConvertFromSim42(self, value):
        if value == EMPTY_VAL:
            return EMPTY_VAL
        sim42Unit = self.unitSystem.GetSim42Unit(self.typeID)
        baseValue = sim42Unit.ConvertToBase(value)
        return self.ConvertFromBase(baseValue)
    
    def ConvertToSet(self, setName, value):
        baseValue = self.ConvertToBase(value)
        unit = self.unitSystem.GetUnit(self.unitSystem.GetUnitSet(setName), self.typeID)
        return unit.ConvertFromBase(baseValue)
    
    def ConvertFromSet(self, setName, value):
        unit = self.unitSystem.GetUnit(self.unitSystem.GetUnitSet(setName), self.typeID)
        baseValue = unit.ConvertToBase(value)
        return self.ConvertFromBase(baseValue)

    def RenderOperation(self):
        """return a string representing the operation"""
        s = 'Base = '
        if self.offset == 0.0:
            s += OperationsScaleOnly[self.operation - 1] % (self.scale, self.name)
        elif self.operation == 5:
            s += '%f' % self.offset
        else:
            s += OperationRenderings[self.operation - 1] % (self.scale, self.name, self.offset)
        return s
    
    def Clone(self, standard=0):
        """ return a clone of self """
        clone = UnitItem(self.unitSystem)
        clone.id = 0     # dummy until added to list
        clone.typeID = self.typeID
        clone.name = '%s-clone' % self.name
        clone.scale = self.scale
        clone.offset = self.offset
        clone.operation = self.operation
        clone.notes = self.notes
        return clone
    
class UnitType:
    """type of unit"""
    def __init__(self):
        """initialize attributes"""
        self.id = 0
        self.name = 'Unknown'
        self.equivalentType = None
        
    def ReadFile(self, f):
        """
        read a line from a tab separated file to initialize values
        return the type id if successful or None if not
        """
        line = f.readline()
        if not line: return None

        fields = re.split(r'\t', string.strip(line))
        if fields[0] == 'ID':  # check for header line
            line = f.readline()
            if not line: return None
            fields = re.split(r'\t', string.strip(line))

        self.id = int(fields[0])
        self.name = fields[1]
        self.equivalentType = self.id
        return self.id

    def WriteFile(self, f):
        """
        write a line to a tab separated file
        """
        f.write('%d\t%s\n' % (self.id, self.name))
        

class UnitSet(dict):
    """
    Dictionary of unit ids stored by type key that represent the 
    default units for the set
    """
    def __init__(self, isMaster=0):
        """
        The isMaster flag indicates whether this is one of the
        distributed master sets or a user set
        """
        dict.__init__(self)
        self.isMaster = isMaster
    
class UnitSystem:
    """base class for containing the units and unit sets"""

    def __init__(self, userDir=None):
        """
        read in the unit system information and set things up
        userDir is the path to the directory containing user data, if any
        """

        if globalBasePath:  # allow path to be set externally
            self.baseDataPath = globalBasePath
        else:
            # get the module path for this module
            try:
                module = sys.modules['vmgunits']
                modpath = module.__path__
                (f, moduleDir, d) = imp.find_module('units', modpath)
                if f:
                    f.close()
                    moduleDir = os.path.dirname(moduleDir)
            except:
                moduleDir = ''
                if sys.platform == 'win32':
                    try:
                        import _winreg
                        software_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE')
                        vmg_key = _winreg.CreateKey(software_key, 'VMG')
                        (moduleDir, type) = _winreg.QueryValueEx(vmg_key, 'vmgsimdll',)
                        _winreg.CloseKey(vmg_key)
                        _winreg.CloseKey(software_key)
                        # check if the folder exists, in case an older version was deleted without un-install
                        if not os.path.exists(os.path.abspath(moduleDir) + os.sep + 'data'):
                            moduleDir = os.curdir                            
                    except:
                        pass   # this will fail during registration as the reg key is not yet set
                
            if not os.sep in moduleDir:
                moduleDir = os.curdir + os.sep + moduleDir
 
            self.baseDataPath = os.path.abspath(moduleDir) + os.sep + 'data'

        #f = open('\\junk.txt', 'a')
        #f.write('baseDataPath = %s\n' % self.baseDataPath)
        #f.close()

        # get user unit dir
        if not userDir:
            if os.environ.has_key('VMGUNITSDIR'):
                userDir = os.environ['VMGUNITDIR']
            else:
                userDir = '.vmgunits'
                if os.environ.has_key('HOME'):
                    homeDir = os.environ['HOME']
                elif os.environ.has_key('HOMEPATH'):
                    homeDir = os.environ['HOMEPATH']
                else:
                    homeDir = os.sep  # just use root I guess
                if homeDir[-1] != os.sep:
                    homeDir += os.sep
                userDir = homeDir + userDir
        self.userDataPath = userDir
        
        # read in types
        self.types = {}
        # first base types
        fileName = self.baseDataPath + os.sep + 'UnitType.txt'
        f = open(fileName)
        while 1:
            unitType = UnitType()
            id = unitType.ReadFile(f)
            if id == None: break
            self.types[id] = unitType            
        f.close()
        
        # check if user types exist
        fileName = self.userDataPath + os.sep + 'UnitType.txt'
        if os.path.exists(fileName):
            f = open(fileName)
            while 1:
                unitType = UnitType()
                id = unitType.ReadFile(f)
                if id == None: break
                self.types[id] = unitType    # it is up to user to ensure unique ids
            f.close()

        # read in unit items
        self.units = {}
        fileName = self.baseDataPath + os.sep + 'UnitItem.txt'
        f = open(fileName)
        while 1:
            unit = UnitItem(self)
            id = unit.ReadFile(f)
            if id == None: break
            self.units[id] = unit            
        f.close()
        
        # check if user items exist
        fileName = self.userDataPath + os.sep + 'UnitItem.txt'
        if os.path.exists(fileName):
            f = open(fileName)
            while 1:
                unit = UnitItem(self)
                id = unit.ReadFile(f)
                if id == None: break
                self.units[id] = unit    # it is up to user to ensure unique ids
            f.close()
            
        # create cross reference for quick look up by name
        self.nameIndex = {}
        for unit in self.units.values():
            self.nameIndex[unit.name] = unit.id
            
        # read standard unit sets
        self.unitSets = {}
        self.ReadSets(self.baseDataPath, 1)
        self.ReadSets(self.userDataPath, 0)

        # see if there is a current default unit set
        defaultName = self.userDataPath + os.sep + 'default'
        if os.path.exists(defaultName):
            f = open(defaultName)
            setName = f.readline()
            f.close()
            setName = string.strip(setName)
            self.defaultSet = self.unitSets[setName]
        else:
            self.defaultSet = self.unitSets['SI']

        self.sim42Set = self.unitSets.get('sim42',None)

        # fix up equivalent unit types after creation of nameIndex
        self.FixEquivalentTypes()
        
    def CleanUp(self):
        [u.CleanUp() for u in self.units.values()]
        self.unitSets = {}
        self.units = {}

    def ReadSets(self, dirName, isMaster):
        """
        read in unit sets from dirName
        The isMaster flag indicates whether these are the
        distributed master sets or a user sets
        """
        if not os.path.exists(dirName): return
        files = os.listdir(dirName)
        sets = filter(lambda file: re.search(r'\.set$', file), files)
        for set in sets:
            setName = re.sub(r'\.set$', '', set)
            self.unitSets[setName] = self.ReadSet(dirName + os.sep + set, isMaster)        
        
    def ReadSet(self, fileName, isMaster):
        """
        read in unit set from file described by fileName
        return the new set which is a dictionary where the key is
        the typeID and the value is the unitID
        The isMaster flag indicates whether this is one of the
        distributed master sets or a user set
        """
        f = open(fileName)
        set = UnitSet(isMaster)
        while 1:
            line = f.readline()
            if not line: break
            fields = re.split('\t', string.strip(line))
            set[int(fields[0])] = int(fields[1])
        f.close()
            
        return set
    
    def WriteSets(self, dirName, isMaster):
        """
        write out unit sets from dirName
        The isMaster flag indicates whether these are the
        distributed master sets or a user sets
        """
        if not os.path.exists(dirName): return
        # remove files for deleted sets
        files = os.listdir(dirName)
        sets = filter(lambda file: re.search(r'\.set$', file), files)
        for set in sets:
            setName = re.sub(r'\.set$', '', set)
            if not setName in self.unitSets.keys():
                os.remove(dirName + os.sep + set)
        
        keys = self.unitSets.keys()
        keys.sort()
        for setName in keys:
            set = self.unitSets[setName]
            if set.isMaster == isMaster:
                self.WriteSet(dirName + os.sep + setName + '.set' , set)        
        
    def WriteSet(self, fileName, set):
        """
        write out unit set to fileName
        """
        f = open(fileName, 'w')
        keys = set.keys()
        keys.sort()
        for typeID in keys:
            f.write('%d\t%d\n' % (typeID, set[typeID]))
        f.close()
    

    def Write(self, master=0):
        """
        write out information back to their files
        if master is true, then write to master files
        otherwise user files
        """
        if master:
            basePath = self.baseDataPath
        else:
            basePath = self.userDataPath
            if not os.path.exists(basePath):
                os.mkdir(basePath)
                
        unitPath = basePath + os.sep + 'UnitItem.txt'
        typePath = basePath + os.sep + 'UnitType.txt'

        f = open(unitPath, 'w')
        f.write('ID\tUnitTypeID\tItemName\tScale\tOffset\tOperationID\tNotes\n')
        keys = self.units.keys()
        keys.sort()
        for key in keys:
            unit = self.units[key]
            if master and (unit.id > 0):
                unit.WriteFile(f)
            elif (unit.id < 0) and not master:
                unit.WriteFile(f)
        f.close()
        
        f = open(typePath, 'w')
        f.write('ID\tTypeName\n')
        keys = self.types.keys()
        keys.sort()
        for key in keys:
            type = self.types[key]
            if master and (type.id > 0):
                type.WriteFile(f)
            elif (type.id < 0) and not master:
                type.WriteFile(f)
        f.close()
        
        if master:
            self.WriteSets(self.baseDataPath, 1)
        else:
            self.WriteSets(self.userDataPath, 0)            
        
    def AddSet(self, setName, set):
        """add set to set collection using setName as key"""
        self.unitSets[setName] = set
        
    def DeleteSet(self, setName):
        """delete set references by setName from the set collection"""
        del self.unitSets[setName]
        
    def GetSetNames(self):
        """return the available unit sets as a list of names"""
        return self.unitSets.keys()
    
    def GetBaseSetNames(self):
        """return the names of the sets that are always there"""
        return ['PureSI', 'VMG', 'Yaws', 'Hysys', 'British', 'DIPPR', 'Field', 'SI', 'sim42']
    
    def GetUnits(self):
        """return a list of all units"""
        return self.units.values()
    
    def GetUnitIDs(self):
        return self.units.keys()
    

    def IsEquivalentType(self, typeID1, typeID2):
        """
        Test whether unit type 1 and unit type 2 are of identical types.
        Types are identical if their corresponding unit items are equal in the Sim42.set
        e.g. Power and Work are identical unit types
        """
        try:
            id1 = self.units[self.sim42Set[typeID1]].id
            id2 = self.units[self.sim42Set[typeID2]].id
            if (id1 == id2):
                return 1
            else:
                return 0
        except:
            return None #None indicates error
        
    def FixEquivalentTypes(self):
        '''
        Some unit types share the same list of unit items, duplicate these items for simplicity
        Offset their ID's by a large number to avoid conflicts
        '''
        for typeId in self.types.keys():
            # test each unit type
            items = self.UnitsByType(typeId)
            eqType = typeId
            if len(items) == 0:
                # has no unit items of this type, find the equivalent id
                s42UnitItemId = self.sim42Set[typeId]
                
                ui = self.units[s42UnitItemId]
                equivalentTypeID = ui.typeID
                # get all the unit items of the equivalent type
                items = filter(lambda ui, t=equivalentTypeID: ui.typeID == t, self.units.values())
                # get these unit items
                for ui in items:
                    unit = ui.Clone()
                    unit.id = ui.id + IniternalUnitItemOffset
                    unit.typeID = typeId
                    unit.name = ui.name
                    # add the clone to the unit item dictionary
                    self.units[unit.id] = unit
                
                # add an equivalent type Id to the unit type    
                # Search the Sim42 unit set for another unit type having the same unit item ID
                for t in self.sim42Set.keys():
                    if t != typeId:
                        if self.sim42Set[t] == s42UnitItemId:
                            eqType = t
                            break
            self.types[typeId].equivalentType = eqType
            items = self.UnitsByType(typeId)
            pass
    
    def UnitsByType(self, typeID):
        """return list units with type typeID"""
        if typeID > 0:
            typeID = self.types[typeID].equivalentType
        return filter(lambda unit, t=typeID: unit.typeID == t, self.units.values())
    
    def UnitsByPartialName(self, name, typeID=None):
        """return list of units that match name and typeID (if it is not None)"""
        name = string.replace(name, "(", "\\(")
        name = string.replace(name, ")", "\\)")
        if typeID:
            if typeID > 0:
                typeID = self.types[typeID].equivalentType            
            return filter(lambda u, n=name, t=typeID: u.typeID == t and re.match(n, u.name, re.I),
                self.units.values())
        else:
            return filter(lambda u, n=name: re.match(n, u.name, re.I), self.units.values())

    def GetUnitSet(self, setName):
        return self.unitSets[setName]
    
    def SetDefaultSet(self, setName):
        """Set the default unit set"""
        try:
            set = self.unitSets[setName]
            self.defaultSet = set
            return 1
        except:
            return 0

    def GetDefaultSet(self):
        """Gets the default unit set name"""
        uDef = None
        try:
            for name, set in self.unitSets.items():
                if self.defaultSet == set:
                    uDef = name
                    break
            return uDef
        except:
            return None
    
    def GetType(self, typeID):
        """return the type corresponding to typeID"""
        return self.types[typeID]

    def GetTypeID(self, typeName):
        """returns type id from a name"""
        typeIDs = filter(lambda t, n=typeName: t.name == n, self.types.values())
        # to get around the simcom installation problem
        #    when installing a new version with a new unit type
        if typeIDs and len(typeIDs) > 0:
            return typeIDs[0].id
        else:
            return None

    def GetTypes(self):
        """return list of all types"""
        return self.types.values()
    
    def GetTypeIDs(self):
        """return list of type ids"""
        return self.types.keys()
    
    def GetTypeName(self, typeID):
        """returns name of type with id typeID"""
        return self.types[typeID].name
    def DeleteType(self, typeID):
        """deletes type associated with type ID and all the units that have that type"""
        units = self.UnitsByType(typeID)
        for unit in units:
            self.DeleteUnit(unit.id)
        del self.types[typeID]
        for set in self.unitSets.values():
            del set[typeID]

    def GetUnit(self, unitSet, typeID):
        """returns the unit in unitSet set for typeID. If not available, then return sim42 unit"""
        if typeID == None: return None
        try: unitID = unitSet[typeID]
        except: unitID = self.sim42Set[typeID]
        try: return self.units[unitID]
        except: return None
    
    def GetUnitWithID(self, id):
        return self.units[id]
    
    def GetCurrentUnit(self, typeID):
        """returns unit in default unit set with type typeID. If unit is missing then return sim42 unit"""
        if typeID == None or self.defaultSet == None: return None
        try: 
            unitID = self.defaultSet[typeID]
        except: 
            try:
                unitID = self.sim42Set[typeID]
            except:
                return None
        return self.units[unitID]

    def GetSim42Unit(self, typeID):
        """returns the sim42 property package unit with type typeID"""
        if typeID == None or self.sim42Set == None: return None
        return self.units[self.sim42Set[typeID]]
    
    def GetUserDir(self):
        """return the current user directory"""
        return self.userDataPath
    def SetUserDir(self, path):
        """set the userDataPath to path"""
        self.userDataPath = path
        # reread unit sets
        self.unitSets = {}
        self.ReadSets(self.baseDataPath, 1)
        self.ReadSets(self.userDataPath, 0)
        
    def AddUserType(self, newType):
        """add a new user unit type to the self.types - create negative id"""
        id = min(self.types.keys()) - 1
        id = min(id, -1)  # in case there were no other user types
        newType.id = id
        self.types[id] = newType
        
        firstUnit = UnitItem(self)
        firstUnit.typeID = id
        unitID = self.AddUserUnit(firstUnit)
        for set in self.unitSets.values():
            if not set.isMaster:
                set[id] = unitID
        return id
        
    def AddMasterType(self, newType):
        """add a new master unit type to the self.types - create positive id"""
        id = max(self.types.keys()) + 1
        id = max(id, 1)  # in case there were no other types
        newType.id = id
        self.types[id] = newType
        firstUnit = UnitItem(self)
        firstUnit.typeID = id
        unitID = self.AddMasterUnit(firstUnit)
        for set in self.unitSets.values():
            if set.isMaster:
                set[id] = unitID
        return id

    def AddUserUnit(self, unit):
        """add a new user unit to the self.units - create negative id"""
        id = min(self.units.keys()) - 1
        id = min(id, -1)  # in case there were no other user units
        unit.id = id
        self.units[id] = unit
        return id
        
    def AddMasterUnit(self, unit):
        """add a new master unit to the self.units - create positive id"""
        id = max(self.units.keys()) + 1
        id = max(id, 1)  # in case there were no other units
        unit.id = id
        self.units[id] = unit
        return id

    def ReplaceUnit(self, unit):
        """use the id of unit as key for unit"""
        self.units[unit.id] = unit
        
    def DeleteUnit(self, unitID):
        """delete the unit with id unitID"""
        del self.units[unitID]
        
def ConvertSets(baseDir='.'):
    """read the sets export file from access and create individual files"""
    inFileName = baseDir + os.sep + 'UnitSet.txt'
    f = open(inFileName)
    # read headers
    line = string.strip(f.readline())
    
    headerFields = re.split(r'\t', line)
    
    #create set files and type file
    fout = []
    for i in range(3, len(headerFields)):
        fout.append(open(baseDir + os.sep + headerFields[i] + '.set', 'w'))
        
    # write the files
    while 1:
        line = f.readline()
        if not line: break
        fields = re.split(r'\t', string.strip(line))
        typeID = fields[2]
        for i in range(3, len(headerFields)):
            fout[i-3].write(typeID + '\t'+ fields[i] + '\n')
        
    f.close()
    for f in fout:
        f.close()
        
if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '-c':
        ConvertSets(sys.argv[2])
        sys.exit(0)
        
    units = UnitSystem()
    for i in units.types.values():
        print i.name, i.id

    #print 'Units'
    #for unit in units.units.values():
    #    print unit.GetName(), unit.scale, unit.offset, unit.operation, unit.notes
    
    for i in units.GetSetNames():
        print i
    
    for unit in units.UnitsByType(9):
        print unit.name, unit.scale, unit.notes
    
    for unit in units.UnitsByPartialName('k', 32):
        print unit.name, unit.typeID, unit.scale, unit.notes
        base = unit.ConvertToBase(1.0)
        print base, unit.ConvertFromBase(base)
    
    print 'Type ID for MoleFlow', units.GetTypeID('MoleFlow')
    typeID = units.GetTypeID('Temperature')
    fieldSet = units.GetUnitSet('Field')
    print 'Field unit for Temperature', units.GetUnit(fieldSet, typeID).name
    pass



