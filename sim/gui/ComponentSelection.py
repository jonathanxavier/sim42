"""Used to filter a list of compounds

Classes:
ComponentInfo -- Defines member variables for a component
ComponentSelection -- Base class for filtering components

Functions:
SortCompInfo_name -- Function to compare instances of ComponentInfo by name
SortCompInfo_formula -- Function to compare instances of ComponentInfo by form
SortCompInfo_nuToMatch -- Function to compare instances of ComponentInfo by nTM

"""

import string

class ComponentInfo:
    """Structure definition of a component"""
    def __init__(self):
        """Init all the member variables"""
        self.name = ''
        self.formula = ''
        self.isMainName = 0
        self.bitAttributes = -1
        self.id = -1
        self.nuToMatch = 0

def SortCompInfo_name(x, y):
    """compare instances of ComponentInfo by name"""
    return cmp(x.name, y.name)

def SortCompInfo_formula(x, y):
    """compare instances of ComponentInfo by form"""
    return cmp(x.formula, y.formula)

def SortCompInfo_nuToMatch(x, y):
    """compare instances of ComponentInfo by nuToMatch"""
    return cmp(x.nuToMatch, y.nuToMatch) 

class ComponentSelection:
    """Base class for filtering components

    Basic usage:
    1) __init__
    2) Add all the components to be managed with AddComponent()
    3) To filter, pass a string to SetMatch(), and then call Sort()
    4) To know how many matches are, use GetComponentCount()
    5) To get a filtered component use GetComponent()

    """
    def __init__(self):
        """Init the list of components empty"""
        self.components = []
        self.visible = []
        self.bitAttributes = -1
        self.showSynonyms = 1
        self.useName = 1
        self.match = ''
        self.byNuToMatch = 0

    def AddComponent(self, name, isMainName = 0, formula= '',
                     bitAttributes = -1, id = -1):
        """Add a component

        name -- Name of the component
        isMainName -- Flag default=0
        formula -- Formula default=''
        bitAttribute -- Attr for filtering (could be used to filter by family)
        id -- id default=-1

        """        
        cmp = ComponentInfo()
        cmp.name = name
        cmp.isMainName = isMainName
        cmp.formula = formula
        cmp.bitAttributes = bitAttributes
        cmp.id = id
        self.components.append(cmp)

    def GetComponent(self, idx):
        """Get the info of a filtered component

        idx -- Index of the component

        returns a tuple like this:
        (success, name, isMainName, formula, bitAttributes, id)
        
        """        
        try:
            return 1, self.visible[idx].name, self.visible[idx].isMainName, \
                   self.visible[idx].formula, self.visible[idx].bitAttributes,\
                   self.visible[idx].id
        except:
            return 0, None, None, None, None, None
        
    def GetComponentCount(self):
        """Amount of visible (filtered) components"""
        return len(self.visible)

    def SetBitAttributes(self, bitAttributes):
        """Parameter to include bitAttributes in the filtering"""
        self.bitAttributes = bitAttributes

    def SetIncludeSynonyms(self, useSynonyms):
        """Doesn't do anything riht now"""
        self.showSynonyms = useSynonyms

    def SetUseNameFormula(self, useName):
        """Filter by name or by formula

        useName -- if true then filter by name, else, filter by formula

        """
        self.useName = useName
        self.__InnerSort()

    def SetMatch(self, match):
        """Sets the filtering string"""        
        self.match = match

    def Sort(self):
        """Performs the filtering

        Criteria: Selects all the components with names (or formulas) that
        begin with the same letter as match and that have the same letters and 
        in the same order as match, even if the letters in the name are not
        right after each other.

        Options: The only implemented option is, if match begins with '@', then
        match and name have to be exactly the same

        """ 
        self.visible = []
        for i in self.components:
            if self.bitAttributes == i.bitAttributes: self.visible.append(i)
        if string.strip(self.match) == '':
            self.byNuToMatch = 0
        else:
            self.byNuToMatch = 1
            idx = 0
            while idx < len(self.visible):
                if self.useName: full = self.visible[idx].name
                else: full = self.visible[idx].formula
                if self.__AbbrevCompare(self.match, full, self.visible[idx]):
                    idx += 1
                else: del self.visible[idx]
        self.__InnerSort()
                    
    def __AbbrevCompare(self, match, full, obj):
        """Decides if a component pass or not the filter"""
        match = string.upper(match)
        full = string.upper(full)
        obj.nuToMatch = 0
        if match[0] == '@': return match[1:] == full
        if match[0] != full[0]: return 0
        idx = 0
        for char in match[1:]:
            idx = string.find(full, char, idx + 1)
            if idx == -1: return 0
        obj.nuToMatch = idx
        return 1

    def __InnerSort(self):
        """Sorts the comoponents"""
        if self.byNuToMatch: self.visible.sort(SortCompInfo_nuToMatch)
        elif self.useName: self.visible.sort(SortCompInfo_name)
        else: self.visible.sort(SortCompInfo_formula)