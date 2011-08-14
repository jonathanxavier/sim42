#thermo case
from numpy.oldnumeric import array,Float0
import ollin.Thermodinamics.PresureVapor as PresureVapor
import ollin.CES
import sys, imp, re

class ThermoCase:
    """
    Beta termo case Edit
    """
    def __init__(self,EOS="RedlichKwong",PV="Antoine"):

        self.library = [] #lists of componets
        self.NamePresureVap = PV #Presure Vapor Equation
        self.NameEOS = EOS # Ecuation of state
        self.PresureVap = None
        self.EOS = None
        self.PublicVars=["MoleWt","LIQDEN",]
        self.LoadPresureModel(PV)
        self.LoadEOSModel(ollin.CES,EOS)
        self.Const = {}
        self.Cases=[]
        self.Load = 0 #Var to determinate if is necesary load data base
        
        


    def Comp(self):
        """ print current componets in case"""
        print "<<Numero>> <<Clave>> <<Nombre>>"
        print "_______________________________"
        for x in self.library.keys():
            print "%-10d>> %-8d >> %-10s"%(x,self.library[x][1],self.library[x][0])
        del x

    def LoadPresureModel(self, model):
        """
        load the class of Presure Vapor Model
        """
        if model in PresureVapor.Equation.keys():
            self.PresureVap = PresureVapor.Equation[model]()
            self.PublicVars += self.PresureVap.NeedVars()
        else:
            print "The model is no aviable!"



    def LoadEOSModel(self,module,model):
        """
        load the class of Presure Vapor Model
        """
        modpath = module.__path__
        fullName = module.__name__ + '.' + model
##        print fullName
##        print sys.modules
        if fullName in sys.modules:
            lang = sys.modules[fullName]
            
        else:
                file, path, description = imp.find_module(model, modpath)
                try: lang = imp.load_module(model ,file,path,description)
                finally: file.close()
        
        self.EOS = lang.Model(self.PresureVap)
        self.PublicVars += self.EOS.NeedVars()
##        else:
##            print "The model is no aviable!"
    def Get(self,Var):
        if Var in self.Const.keys():
            return self.Const[Var]
        else:
            return 0
    
    def Solve(self,case):
        case.library = self.library
        self.EOS.Solver(self.Const,case)

