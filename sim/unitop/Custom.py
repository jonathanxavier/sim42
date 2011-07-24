from sim.solver.Variables import SimInfoDict
from UnitOperations import SIMINFO

class CustomSolveMethod(object):
    
    def __init__(self):
        self.info = SimInfoDict(SIMINFO, self)
    
    def __str__(self):
        return "Custom solve method for unit operation %s" % self.parent.GetPath()
    
    def Initialize(self, parent, name):
        self.parent = parent
        self.name = name
        
    def CleanUp(self):
        self.info.CleanUp()
        self.parent = None
        self.info = None
    
    def GetPath(self):
        return self.parent.GetPath() + "." + self.name
        
    def SetParent(self, parent):
        self.parent = parent
    
    def GetParent(self):
        return self.parent
    
    def GetName(self):
        return self.name
    
    def GetObject(self, name):
        if name == SIMINFO:
            if hasattr(self, 'info'):
                obj = self.info
                return obj
            
    def Solve(self):
        return
    
    def Clone(self):
        clone = self.__class__()
        clone.name = self.name
        return clone
    
    def GetStoreInfo(self):
        """Return information (as native python objects) that needs to be saved as part of the case """
        #Nothing for now
        return None
            
    def SetStoreInfo(self, storeInfo):
        """Recreate an instance of this object from information that got stored in file"""
        #Nothing for now
        pass
    
    
