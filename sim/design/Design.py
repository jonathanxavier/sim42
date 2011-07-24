'''Main class for unit operations design
'''

import re
from sim.solver.Variables import *

TRY_SOLVE_DESIGN_PAR = 'TryToSolveDesign'


#Constants for the basic design parameter
STR_INFO = 1            #String
INT_INFO = 2            #Integer
FLT_INFO = 4            #Float
BOOL_INFO = 8           #Boolean
OPT_INFO = 16           #Options
PORT_INFO = 32          #Comes from a port
INLET_INFO = 64         #Is inlet
OUTLET_INFO = 128       #Is outlet
USESUNIT_INFO = 256     #Uses unit conversion

INPUT_KEYWORD = 'Input'
OUTPUT_KEYWORD = 'Output'
VALUE_KEYWORD = 'Value'
INFO_TYPE_KEYWORD = 'InfoType'
OPTIONS_KEYWORD = 'Options'
DISP_NAME_KEYWORD = 'DisplayName'

                
class BasicDesignParameter(object):
    """This class defines the container of information for each parameter in the design object"""
    def __init__(self, parent, name, infoType, propTypeName=None, options=[], dispName='', idx=0):
        self.parent = parent
        self.name = name
        self.infoType = infoType
        if propTypeName:
            self.propType = PropTypes.get(propTypeName, PropTypes[GENERIC_VAR])
        else:
            self.propType = None
        self.options = options
        self.value = None
        if not dispName:
            self.dispName = name
        else:
            self.dispName = dispName
        self.idx = idx

    def __str__(self):
        return '%s = %s' % (self.name, str(self.GetValue()))
    
    def GetPath(self):
        return self.parent.GetPath() + '.' + self.name

    def GetParent(self):
        return self.parent

    def GetContents(self):
        results = []
        results.append((VALUE_KEYWORD, self.value))
        results.append((INFO_TYPE_KEYWORD, self.infoType))
        results.append((OPTIONS_KEYWORD, self.options))
        results.append((DISP_NAME_KEYWORD, self.dispName))
        return results

    def GetObject(self, desc):
        obj = None
        if desc == VALUE_KEYWORD:
            obj = self.value
        elif desc == INFO_TYPE_KEYWORD:
            obj = self.infoType
        elif desc == OPTIONS_KEYWORD:
            obj = self.options
        elif desc == DISP_NAME_KEYWORD:
            obj = self.dispName
        return obj

    def SetValue(self, value, calcType=None):
        """Sets the value. calcType is just a dummy so it looks like other calls in sim42"""
        #if self.infoType & PORT_INFO:
            #Can not set port values this way
            #return
        self.value = value

    def GetValue(self):
        return self.value

    def GetInfoType(self):
        return self.infoType

    #HAd to pick this name for the method for consistency
    def GetType(self):
        """Get the type of property"""
        return self.propType    
    
    def GetOptions(self):
        """Returns the options if it has any"""
        return self.options


class DesignMain(object):
    def __init__(self):
        self.parent = None
        self.name = ''
        self._input = {}
        self._output = {}
        self._readyForSolve = False

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return '%s = %s' % (self.name, t)

    def CleanUp(self):
        pass

    def SetName(self, name):
        self.name = name

    def GetName(self):
        return self.name

    def SetParent(self, parent):
        self.parent = parent

    def GetParent(self):
        return self.parent
    
    def GetPath(self):
        if self.parent:
            return self.parent.GetPath() + '.' + self.name
        else:
            return self.name

    def GetContents(self):
        """Retruns a list of tuples with the contents"""
        results = []
        results.append((INPUT_KEYWORD, DesignInfoWrapper(self._input, self.parent, INPUT_KEYWORD)))
        results.append((OUTPUT_KEYWORD, DesignInfoWrapper(self._output, self.parent, OUTPUT_KEYWORD)))
        return results

    def GetObject(self, desc):
        """desc can be Input or Output"""
        if desc == INPUT_KEYWORD:
            obj = DesignInfoWrapper(self._input, self.parent, INPUT_KEYWORD)
        elif desc == OUTPUT_KEYWORD:
            obj = DesignInfoWrapper(self._output, self.parent, OUTPUT_KEYWORD)
        else:
            obj = None
        return obj

    def GetInput(self):
        return self._input

    def SetInput(self, input):
        self._input = input
        
    def GetOutput(self):    
        return self._output
    
    def SetOutput(self, output):
        self._output = output

    def LoadInputFromParent(self):
        """Get the input from the parent unit operation (if any)"""
        pass

    def ClearInput(self):
        for obj in self._input.values():
            obj.SetValue(None)
            
    def ClearOutput(self):
        for obj in self._output.values():
            obj.SetValue(None)
            
    def Solve(self):
        self._readyForSolve = True
##        self.ClearInput()
        self.ClearOutput()
        self.LoadInputFromParent()
        self.PrepareForSolve()
        if self.parent:
            self.maxIter = self.parent.GetParameterValue(MAXITER_PAR)
        if not self.maxIter:
            self.maxIter = 50

            
    def PrepareForSolve(self):
        '''Does all prelimenary calculations. Return False if it cannot solve'''
        if self._input == None:
            self._readyForSolve = False

    def NotifyUnitOpSolved(self):
        pass
    
NAME_COL = 0
VALUE_COL = 1
INFOTYPE_COL = 2
OPTIONS_COL = 3
UNIT_COL = 4 
            
class DesignInfoWrapper(object):
    """Wraps the input or the output dictionary from a design object"""
    def __init__(self, obj, parent, name):
        self.obj = obj
        self.parent = parent
        self.name = name
    
    def __str__(self):
        contents = self.GetContents()
        s = '%s. Contains\n' %self.name
        for name, desParam in contents:
            s += '%s\t= %s\n' %(name, str(desParam.value))
        return s
    
    def GetPath(self):
        return self.parent.GetPath() + '.' + self.name
    
    def GetParent(self):
        return self.parent
        
    def GetContents(self):
        myList = []
        results = []
        
        #Sort by the index
        for key_val in self.obj.items():
            myList.append((key_val[1].idx, key_val))
        myList.sort()
        for idx, result in myList:
            results.append(result)
        
        return results
        
    def GetObject(self, desc):
        return self.obj.get(desc, None)
        
    
    def GetArrayRepresentation(self):
        """Returns all the information in an array"""
        contents = self.GetContents()
        rows = len(contents)
        cols = 4
        
        
        #Dimension the list initally rather than appending
        #results = [[None]*rows]*cols
        results = [[], [], [], []]
        for row in range(rows):
            obj = contents[row][1]
            results[NAME_COL].append(obj.name)
            results[VALUE_COL].append(obj.value)
            results[INFOTYPE_COL].append(obj.infoType)
            results[OPTIONS_COL].append(obj.options)
            
        return results
        
    def GetConvertedArrayRepresentation(self, unitSystem):
        """Returns the information in the current units of the unitSystem"""
        contents = self.GetContents()
        rows = len(contents)
        cols = 5
        
        
        #Dimension the list initally rather than appending
        #results = [[None]*rows]*cols
        results = [[], [], [], [], []]
        for row in range(rows):
            obj = contents[row][1]
            results[NAME_COL].append(obj.name)
            results[VALUE_COL].append(obj.value)
            results[INFOTYPE_COL].append(obj.infoType)
            results[OPTIONS_COL].append(obj.options)
            results[UNIT_COL].append('')
            propType = obj.propType
            if propType:
                value = results[VALUE_COL][row]
                unit = unitSystem.GetCurrentUnit(propType.unitType)
                if unit: 
                    value = unit.ConvertFromSim42(value)
                    results[VALUE_COL][row] = value
                    results[UNIT_COL][row] = unit.name            

        return results
        
