##import sys
##sys.path.append("/Users/jonathanxavier/Developer/sim42")
from ollin.DataBase.DataBase import DataBase
from ollin.Administrator.ThermoCase import ThermoCase
from ollin.Administrator.ThemoObj import ThermoObj
from numpy.oldnumeric import array

class AdmOllin:
    """
    Beta termo server administrator
    """
    def __init__(self):
        """
        cargar base de datos
        """
        self.TheCase = {}
        self.TheObj = {}
        self.Model = {}
        self.cur = DataBase()
        print "OllinTS has been loaded\n"


    def Add(self,items,case):
        """
        add components in tha case
        """
##        print type(items)
        if type(items) == str:
            items = [items,]
        
##        print items
        
        for item in items:
##            print item
            if self.TheCase[case].library.count(item) != 0:
                print "The component %s has been add"
                return 0
            temp = self.cur.Dates("IdKey",item)
            if temp == (None or []):
                print "Isn,t the compound in databse %s"%(item)
            else:
                print "component %d  %s was add to %s"%(temp[0][0],item,self.TheCase[case].NameEOS)
                self.TheCase[case].library.append(item)
                self.TheCase[case].Load = 0
    
    def Remove(self,items,case):
        """
        remove components in tha case
        """
##        print type(items)
        if type(items) == str:
            items = [items,]
        
##        print items
        
        for item in items:
            if self.TheCase[case].library.count(item) != 0:
                self.TheCase[case].library.remove[item]
                print "The component %s has been removed"
                self.TheCase[case].Load = 0

    def AddModel(self,Name,case="SRK",PV="ANTOINE"):
        ModelKeys={}
        ModelKeys["RKS"]= "RedlichKwongS"
        ModelKeys["RK"]= "RedlichKwong"
        ModelKeys["PR"]= "PengRobinson"
        ModelKeys["SRK"]= "SoaveRK"

        if not  case in ModelKeys:
            print "The model %s isnt aviable"%case
            return 0
        
        if not Name in self.TheCase.keys(): 
            self.TheCase[Name] = ThermoCase( ModelKeys[case] ,PV)
            case_i = self.TheObj.keys()
            if case_i != [] and len(self.TheCase.keys())==1:
                self.TheCase[Name].Cases += case_i
                for i in case_i:
                    self.TheObj[i].Model = Name
            return self.TheCase[Name]
        else:
            print "%s has yet added"%Name
    
    def AddCase (self,Name,Model=None):
    
        if not Name in self.TheObj.keys(): 
            self.TheObj[Name] = ThermoObj()
            case_i = self.TheCase.keys()
##                print case_i
            if case_i != []:
                self.TheCase[ case_i[0] ].Cases += Name
                self.TheObj[Name].Model = case_i[0]
            return self.TheObj[Name]

    def LoadConst(self,case=None):
        """
        Load information from data base
        for the Model (case)
        """
        
        if case == None:
            for case in self.TheCase.keys():
                if self.TheCase[case].Load !=1: 
                    comp = self.TheCase[case].library
                    for Var in self.TheCase[case].PublicVars:
                        self.TheCase[case].Const[Var] = array( self.cur.Dates( Var, comp)[0] )   
                    self.TheCase[case].Load = 1
        else:
            if self.TheCase[case].Load !=1: 
                comp = self.TheCase[case].library
                for Var in self.TheCase[case].PublicVars:
                    self.TheCase[case].Const[Var] = array( self.cur.Dates( Var, comp)[0] )
                self.TheCase[case].Load = 1
    
    def Connect(self,Model,Case):
        if Case in self.TheObj.keys() and Model in self.TheCase.keys():
            self.TheObj[Case].Model = Model
        else:
            return 0
        

    def Solve(self,case=None):
    
        if self.TheObj !=None and self.TheCase !=None:
            if case!=None:
                print "Solving %s..."%case
                model = self.TheObj[case].Model
                if self.TheCase[model].Load == 0:
                    self.LoadConst()
                self.TheCase[model].Solve( self.TheObj[case] )
            else:
                for case in self.TheObj.keys():
                    print "Solving %s..."%case
                    model = self.TheObj[case].Model
                    
                    if self.TheCase[model].Load == 0:
                        self.LoadConst()
                    
                    self.TheCase[model].Solve( self.TheObj[case] )
        else:
            return 0
    
    def Resumen(self,case=None):
        """Print resumen of the case"""
        if case == None:
            for case in self.TheObj.keys():
                self.TheObj[case].CasePrint()
                self.TheObj[case].XPrint()
        else:
                self.TheObj[case].CasePrint()
                self.TheObj[case].XPrint()

Ollin = AdmOllin()
