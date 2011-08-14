#Themo objetc
from numpy.oldnumeric import array,Float0,power

class ThermoObj:

    def __init__(self):
        
        self.library = [] #lists of componets
        self.Vars = ("P","T","Mol_WT","FracVap","Z","Zv","Zl","CpG","CpL","H","Hv","CoeFugOl","CoeFugOv","CoeFugOl","CoeFugMl","CoeFugMl","yf","xf","Pvi","Ki","fi","Zi","Zli","Zvi")
        self.EOSVars = {}
        self.Prop = {}
        self.ExtProp = {}
        self.Prop["P"] = None
        self.IdP = 0
        self.Prop["T"] = None
        self.IdT = 0
        self.Prop["Mol_WT"] = None
        self.Prop["H"] = None
        self.IdH = 0
        self.Prop["FracVap"] = None
        self.IdF = 0
        self.Solve = 0
        self.Model=None
        self.Prop["x"] = None
        self.Prop["xf"] = None
        self.Prop["yf"] = None
##        self.Name = str(self)
    
    def P(self,p):
        """
        Set Presure
        """
        self.IdP = 1
        if self.Prop["P"] != p:
            self.Prop["P"] = p
            self.reset()
            self.Solve = 0
    
    
    def T(self,t):
        """
        Set Temperature
        """
        self.IdT = 1
        if self.Prop["T"] != t:
            self.Prop["T"] = t
            self.reset()
            self.Solve = 0
    
    def FracVap(self,Frac):
        """
        Set Fraction Vapor
        """
        self.IdF = 1
        if self.Prop["FracVap"] != Frac:
            self.Prop["FracVap"] = Frac
            self.reset()
            self.Solve = 0
    
    def H(self,H):
        """
        Set Hentalpy
        """
        self.IdH = 1
        if self.Prop["H"] != H:
            self.Prop["H"] = H
            self.reset()
            self.Solve = 0


    def SetX(self,Xt):
        """
        [xi,..] 
        """
        #minimun concentration = 1e-8
        self.Prop["x"]= self.Normal(Xt)
    
    def SetXf(self,Xt):
        """
        [xi,..]
        """
        #minimun concentration = 1e-8
        self.Prop["xf"]= self.Normal(Xt)

    
    def SetYf(self,Xt):
        """
        [xi,..]
        """
        #minimun concentration = 1e-8
        self.Prop["yf"]= self.Normal(Xt)
    
    def Rx(self):
        self.Prop["x"]=self.Prop["xf"]*self.Prop["FracVap"]+self.Prop["yf"]*self.Prop["FracVap"]
        
    def Get(self,Var):
        if Var in self.Prop.keys():
            return self.Prop[Var]
        else:
            return 0
    
    def reset(self):
    
        if self.IdH == 0:
            self.Prop["H"] = None
        if self.IdT == 0:
            self.Prop["T"] = None
        if self.IdP == 0:
            self.Prop["P"] = None
        if self.IdF == 0:
            self.Prop["FracVap"] = None
    
    def Normal(self,x):
        if type(x) == list:
            x = array(x,typecode = Float0)
        Px = sum(x)
        
        if Px == 1.000:
            return x
        else:
            xi= x/Px
        for i in range(len(x) ):
            if xi[i]<1e-8:
                xi[i]= 1e-8
        return xi

    def CasePrint(self):
        if self.Solve == 0:
            print "firts Solve"
            return 0
    
        print "\n ..::Resumen ::..\n"
        print "FracVap      = %.4f" %self.Prop["FracVap"]
        print "Press  KPa   = %.3f" %self.Prop["P"]
        print "Temp   K     = %.3f" %self.Prop["T"]
        print "Z L          = %1.3f"%self.Prop["Zl"]
        print "Z V          = %1.3f"%self.Prop["Zv"]
        print "Z            = %1.3f"%self.Prop["Z"]
        print "Enthalpy KJ/Kgmol  = ", self.Prop["H"]
        print "Entropy  KJ/KgmolK = ", self.Prop["S"]
        print "MolWt     Kg/kgmol = %0.3f" %self.Prop["MolWt"]
        print "MolWt L  Kg/kgmol  = %0.3f" %self.Prop["MolWt_l"]
        print "MolWt V  Kg/kgmol  = %0.3f" %self.Prop["MolWt_v"]
        
    
    def XPrint(self):
        if self.Solve == 0:
            print "firts Solve"
            return 0
        """Print Fraction of components"""
        print "..::Component::..      << Liq Fraction >>   << Vap Fraction >>"
        for i in range( len(self.library) ):
            print "%-20s %-3s %12.4f %4s %12.4f"%(self.library[i],"==>",self.Prop["xf"][i],"         |____|",self.Prop["yf"][i])
