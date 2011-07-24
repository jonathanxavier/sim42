"""Module for a simple XY table
Classes:
DataSeries - an array of data
ATable - class containning multiple DataSeries

"""
from sim.solver.Variables import *
SERIES_OBJ = 'Series'
TABLETAG_VAR = 'TagValue'


class DataSeries(object):
    def __init__(self, typeName = GENERIC_VAR):
        # i do not want to trigger a solve in each series input
        # otherwise, it would be more convenient to have a list of BasicVariable

        self._myData = []
        self._myType = PropTypes.get(typeName, PropTypes[GENERIC_VAR])
        self.unitOpParent = None
        self.name = ''
        
    def CleanUp(self):
        self.unitOpParent = None

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        s = '%s = %s; %s' % (self.name, t, self._myType)
        for i in self._myData:
            s += ' ' + str(i)
        return s

    def GetContents(self):
        return [('UnitType', self._myType.unitType), ('Values', self._myData)]
                  
    def Initialize(self, unitOpObj, name):
        self.unitOpParent = unitOpObj
        self.name = name
        
    def SetParent(self, parent):
        self.unitOpParent = parent
        
    def SetValues(self, vals, dummy=None):
        """the dummy is just to make it match the BasicProperty call"""
        self._myData = []
        if vals != None:
            for i in range(len(vals)):
                if vals[i] == 'None':
                    self._myData.append(None)
                else:
                    try:
                        self._myData.append(float(vals[i]))
                    except:
                        # string data support
                        self._myData.append(vals[i])
        if self.unitOpParent:
            self.unitOpParent.ForgetAllCalculations()

    def GetValues(self):
        vals = []
        for i in range(len(self._myData)): vals.append(self._myData[i])
        return vals

    def GetType(self):
        return self._myType

    def SetType(self, typeName):
        self._myType = PropTypes.get(typeName, PropTypes[GENERIC_VAR])
        if self.name == '':
            self.name = typeName

    def GetLen(self):
        return len(self._myData)

    def GetDataValue(self, idx, allowExtrap = 1):
        # idx can be any real number
        #linear interpolation
        n = len(self._myData)
        if (n == 0):
            return None
        elif (n == 1):
            return self._myData[0]        
        else:
            if (idx <= 0):
                idx1 = 0
                if ( not allowExtrap): return self._myData[0]
            elif (idx >= n-1):
                idx1 = n-2
                if (not allowExtrap): return self._myData[n-1]
            else:
                idx1 = long(idx)
            return self._myData[idx1] + (self._myData[idx1+1] - self._myData[idx1]) * (idx - idx1)

    def GetDataIndex(self, val):
        n = len(self._myData)
        if (n == 0):
            return None
        elif (n == 1):
            return 0
        for i in range(n-1):
            factor = (val - self._myData[i]) * (self._myData[i+1] - val)
            if (factor >= 0 and self._myData[i+1] != self._myData[i]):
                return i + (val - self._myData[i]) / (self._myData[i+1] - self._myData[i])
        # value out of bound, returns the end point
        if ((self._myData[n-1] - self._myData[0]) * (self._myData[0] - val)) >= 0.0:
            return 0
        else:
            return n-1

    def GetDataPoint(self, idx):
        if idx >= 0 and idx < len(self._myData):
            return self._myData[idx]


    def Clone(self):
        clone = self.__class__(self._myType.name)
        clone.name = self.name
        clone._myData = copy.deepcopy(self._myData)
        return clone
        
class ATable(object):
    def __init__(self, typeName = GENERIC_VAR):
        self._TagValue = 0.0
        self._Series = {}
        self._Tag = BasicProperty(typeName)

    def CleanUp(self):
        for s in self._Series.values():
            s.CleanUp()
        self._Series.clear()
    def GetObject(self, name):
        if (name == TABLETAG_VAR):        
            return self._Tag
        elif self._Series.has_key(name):
            return self._Series[name]
        else:
            for i in range(nSeries):
                if self._Series[SERIES_OBJ + str(i)].name == name:
                    return self._Series[SERIES_OBJ + str(i)]
            

    def GetLen(self):
        maxLen = 0
        nSeries = len(self._Series)
        for i in range(nSeries):
            n = self._Series[SERIES_OBJ + str(i)].GetLen()
            if n > maxLen:
                maxLen = n
        return maxLen        

    def GetContents(self):
        result = [(TABLETAG_VAR, self._Tag)]
        for key in self._Series:
            result.append((key, self._Series[key]))
        return result
            
    def SetSeriesCount(self, n):
        nSeries = len(self._Series)
        for i in range(nSeries, n, -1):
            del self._Series[SERIES_OBJ + str(i-1)]
        for i in range(nSeries, n):
            self._Series[SERIES_OBJ + str(i)] = DataSeries()

    def SetTagType(self, typeName):
        # if i switch data type, erase existing data
        if typeName != self._Tag.GetName():
            self._Tag = None
            self._Tag = BasicProperty(typeName)

    def TagValue(self):
        return self._Tag.GetValue()

    def SetSeriesType(self, seriesIdx, typeName):
        seriesName = SERIES_OBJ + str(seriesIdx)
        if (self._Series.has_key(seriesName)):
            self._Series[seriesName].SetType(typeName)

    def GetSeries(self, idx):
        if idx < len(self._Series):
            return self._Series[SERIES_OBJ + str(idx)]
        else:
            return None
        
    def Clone(self):
        clone = self.__class__(self._Tag._type.name)
        
        for key, value in self._Series.items():
            clone._Series[key] = value.Clone()
        clone._Tag = self._Tag.Clone()
            
        return clone