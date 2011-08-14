import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")

##from ollin.Administrator.AdmOllin import Ollin
from ollin.Administrator.ThemoObj import ThermoObj
from numpy.oldnumeric import array,Float0

#Create the stream material for solve cases
##S1=Ollin.AddCase("S1")

class Stream:

    def __init__(self,Model=None):
        """
        define a stream of material
        """
        self.Case = ThermoObj()
        self.MassFraction = None
        self.MassFlow      = None
        self.MoleFlow       = None
        self.MassFlowi      = None
        self.MoleFlowi       = None
        self.Energy          = None
        self.Model            = Model
        self.IN = None
        self.OUT = None
        self.Solve = 0
    
    def InPort(self):
        return self
    
    def OutPort(self,Out):
        self.OUT = Out
    
    def Connect(self,port):
        self.OUT = port.InPort()
    
    def Copy(self):
        if self.OUT!= None:
            self.OUT.Case=self.Case 
            self.OUT.MassFraction=self.MassFraction 
            self.OUT.MassFlow=self.MassFlow
            self.OUT.MoleFlow=self.MoleFlow
            self.OUT.MassFlowi=self.MassFlowi
            self.OUT.MoleFlowi=self.MoleFlowi
            self.OUT.Energy=self.Energy 
            self.OUT.Solve = 1
    
    def model(self,m):
        self.Model            = m
    
    def Get(self,Var):
        if Var in self.Case.Prop.keys():
            return self.Case.Prop[Var]
        else:
            return 0

    def P(self,p):
        """
        Set Presure
        """
        self.Case.P(p)
    
    
    def T(self,t):
        """
        Set Temperature
        """
        self.Case.T(t)
    
    def FracVap(self,Frac):
        """
        Set Fraction Vapor
        """
        self.Case.FracVap(Frac)
    
    def H(self,H):
        """
        Set Hentalpy
        """
        self.Case.H(H)

    def X(self,Xt):
        """
        [xi,..] 
        """
        self.Case.SetX(Xt)
##        print self.Case.Get("x")
        xm = Xt*self.Model.Const["MoleWt"]
        self.MassFraction = xm/sum(xm)
##        print xm
        del xm
    
    def MassF(self,x):
        self.MassFraction = self.Normal(x)
        xm = Xt/self.Model.Const["MoleWt"]
        self.X(xm/sum(xm))
##        print xm
        del xm
    def Mass(self,x):
        self.MassFlow = x
        
    def Mol(self,x):
        self.MoleFlow= x
    
    def Normal(self,x):
        if type(x) == list:
            x = array(x,typecode = Float0)
        Px = sum(x)
        
        if Px == 1.000:
            return x
        else:
            xi= x/Px
        for i in range(len(x) ):
            if x[i]<1e-8:
                x[i]= 1e-8
        return x
        
    def Solver(self):
##        print "mol",self.MoleFlow
        self.Model.Solve(self.Case) 
        self.Solve = 1
        xm=(self.Model.Const["MoleWt"]*self.Get("x"))
        self.MassFraction = xm/sum(xm)
        if self.MassFlow != None:
            self.MassFlowi =  self.MassFlow*self.MassFraction
            self.MoleFlowi = self.MassFlowi/self.Model.Const["MoleWt"]
            self.MoleFlow = sum(self.MoleFlowi)
        if self.MoleFlow != None:
##            print "mol",self.MoleFlow
            self.MoleFlowi =  self.MoleFlow*self.Get("x")
            self.MassFlowi = self.MoleFlowi*self.Model.Const["MoleWt"]
            self.MassFlow = sum(self.MassFlowi)
##        print "mol",self.MoleFlow
        if self.OUT!= None:
            self.Copy()

    def CasePrint(self):
        if self.Solve == 0:
            print "firts Solve"
            return 0
    
        print "\n ..::Resumen ::..\n"
        print "FracVap      = %.4f" %self.Get("FracVap")
        print "Press  KPa   = %.3f" %self.Get("P")
        print "Temp   K     = %.3f" %self.Get("T")
        print "MoleFlow Kgmol/hr= %1.3f"%self.MoleFlow
        print "MassFlow Kg/hr= %1.3f"%self.MassFlow
        print "Enthalpy KJ/Kgmol  = ", self.Get("H")
        print "Entropy  KJ/KgmolK = ", self.Get("S")
        print "MolWt     Kg/kgmol = %0.3f" %self.Get("MolWt")
        print "Z            = %1.3f"%self.Get("Z")

class Valve:
    
    def __init__(self,Model=None):
        self.In = Stream (Model)
        self.Out = Stream(Model)
        self.DP = 0 # en Kpa
        self.Model = Model
        self.IN = None
        self.OUT = None
        self.Solve = 0
    
    def InPort(self):
        return self.In
    
    def OutPort(self,Out):
        self.OUT = Out
    
    def Connect(self,port):
        self.OUT= port.InPort()
        self.Out.Connect(port)
    
    def Solver(self):
        if self.In.Solve == 0:
            self.In.Solver()
        P1 = self.In.Get("P")
        P2 = P1-self.DP
        self.Out.P(P2)
        self.Copy()
        self.Out.Solver()
        self.Solve = 1
        if self.OUT!= None:
            self.Out.Copy()
    
    def Copy(self):
        self.Out.X(self.In.Get("x"))
        self.Out.H(self.In.Get("H"))
        self.Out.MoleFlow = self.In.MoleFlow


class Cooling:
    
    def __init__(self,Model=None):
        self.In = Stream (Model)
        self.Out = Stream(Model)
        self.DP = 0 # en Kpa
        self.DH = 0 # en kj
        self.DT = 0 # K
        self.Model = Model
        self.IN = None
        self.OUT = None
        self.Solve = 0
    
    def InPort(self):
        return self.In
    
    def OutPort(self,Out):
        self.OUT = Out
    
    def Connect(self,port):
        self.OUT= port.InPort()
        self.Out.Connect(port)
    
    def Solver(self):
        if self.In.Solve == 0:
            self.In.Solver()
        
        P1 = self.In.Get("P")
        P2 = P1-self.DP
        self.Out.P(P2)
        
        if self.DT !=0:
            T1 = self.In.Get("T")
            if T1 !=0:
                T2 = T1-self.DT
                self.Out.T(T2)
                self.Copy()
                self.Out.Solver()
                self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
                self.Solve = 1

            else:
                T2 = self.In.Get("T")
                if T2 !=0:
                    T1= T2+self.DT
                    self.In.T(T1)
                    self.Copy()
                    self.In.Solver()
                self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
                self.Solve = 1
        else:
            T1 = self.In.Get("T")
            T2 = self.Out.Get("T")
            if T1!=0 and T2!=0:
                self.Copy
                self.In.Solver()
                self.Out.Solver()
                self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
                self.DT = abs(self.In.Get("T")-self.Out.Get("T"))
                self.Solve = 1

        if self.DH !=0 and self.Solve==0:
            H1 = self.In.Get("H")
            if H1 !=0:
                H2 = H1-self.DH/self.In.MoleFlow
                self.Out.H(H2)
                self.Copy()
                self.Out.Solver()
                self.Solve = 1
                self.DT = abs(self.In.Get("T")-self.Out.Get("T"))
                self.Solve = 1
            else:
                H2 = self.In.Get("H")
                if T2 !=0:
                    H1 = H2+self.DH/self.In.MoleFlow
                    self.In.H(H1)
                    self.Copy()
                    self.In.Solver()
                self.DT = abs(self.In.Get("T")-self.Out.Get("T"))
                self.Solve = 1
        else:
            H1 = self.In.Get("H")
            H2 = self.Out.Get("H")
            if H1!=0 and H2!=0:
                self.Copy
                self.In.Solver()
                self.Out.Solver()
                self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
                self.DT = abs(self.In.Get("T")-self.Out.Get("T"))
                self.Solve = 1
    
        if self.OUT!= None:
            self.Out.Copy()
    
    def Copy(self):
        if self.In.Solve==1:
            self.Out.X(self.In.Get("x"))
            self.Out.MoleFlow = self.In.MoleFlow
        elif self.Out.Solve==1:
            self.In.X(self.Out.Get("x"))
            self.In.MoleFlow = self.Out.MoleFlow
#-_______________________________________________________________________________
class Heater:
    
    def __init__(self,Model=None):
        self.In = Stream (Model)
        self.Out = Stream(Model)
        self.DP = 0 # en Kpa
        self.DH = 0 # en kj
        self.DT = 0 # K
        self.Model = Model
        self.IN = None
        self.OUT = None
        self.Solve = 0
    
    def InPort(self):
        return self.In
    
    def OutPort(self,Out):
        self.OUT = Out
    
    def Connect(self,port):
        self.OUT= port.InPort()
        self.Out.Connect(port)
    
    def Solver(self):
        if self.In.Solve == 0:
            self.In.Solver()
        
        P1 = self.In.Get("P")
        P2 = P1-self.DP
        self.Out.P(P2)
        
        if self.DT !=0:
            T1 = self.In.Get("T")
            if T1 !=0:
                T2 = T1+self.DT
                self.Out.T(T2)
                self.Copy()
                self.Out.Solver()
                self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
                self.Solve = 1

            else:
                T2 = self.In.Get("T")
                if T2 !=0:
                    T1= T2-self.DT
                    self.In.T(T1)
                    self.Copy()
                    self.In.Solver()
                self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
                self.Solve = 1
        else:
            T1 = self.In.Get("T")
            T2 = self.Out.Get("T")
            if T1!=0 and T2!=0:
                self.Copy
                self.In.Solver()
                self.Out.Solver()
                self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
                self.DT = abs(self.In.Get("T")-self.Out.Get("T"))
                self.Solve = 1

        if self.DH !=0 and self.Solve==0:
            H1 = self.In.Get("H")
            if H1 !=0:
                H2 = H1+self.DH/self.In.MoleFlow
                self.Out.H(H2)
                self.Copy()
                self.Out.Solver()
                self.Solve = 1
                self.DT = abs(self.In.Get("T")-self.Out.Get("T"))
                self.Solve = 1
            else:
                H2 = self.In.Get("H")
                if T2 !=0:
                    H1 = H2-self.DH/self.In.MoleFlow
                    self.In.H(H1)
                    self.Copy()
                    self.In.Solver()
                self.DT = abs(self.In.Get("T")-self.Out.Get("T"))
                self.Solve = 1
        else:
            H1 = self.In.Get("H")
            H2 = self.Out.Get("H")
            if H1!=0 and H2!=0:
                self.Copy
                self.In.Solver()
                self.Out.Solver()
                self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
                self.DT = abs(self.In.Get("T")-self.Out.Get("T"))
                self.Solve = 1
    
        if self.OUT!= None:
            self.Out.Copy()
    
    def Copy(self):
        if self.In.Solve==1:
            self.Out.X(self.In.Get("x"))
            self.Out.MoleFlow = self.In.MoleFlow
        elif self.Out.Solve==1:
            self.In.X(self.Out.Get("x"))
            self.In.MoleFlow = self.Out.MoleFlow
#=======================================================================
#=======================================================================
class Flash:
    
    def __init__(self,Model=None):
        self.In = Stream (Model)
        self.Vap = Stream(Model)
        self.Liq = Stream(Model)
        self.Model = Model
        self.IN = None
        self.VAP = None
        self.LIQ = None
        self.Solve = 0
    
    def InPort(self):
        return self.In
    
    def OutPort(self,Out):
        self.OUT = Out
    
    def ConnectVap(self,port):
        self.VAP= port.InPort()
        self.Vap.Connect(port)
    
    def ConnectLiq(self,port):
        self.LIQ= port.InPort()
        self.Liq.Connect(port)
    
    def Solver(self):
        if self.In.Solve != 0:
            self.In.Solver()
        P = self.In.Get("P")
        T= self.In.Get("T")
        x= self.In.Get("xf")
        y= self.In.Get("yf")
        FV = self.In.Get("FracVap")
        F= self.In.MoleFlow
        
        V = F*FV
        L = F-V
##        print "FR",FV,L,V
        self.Vap.P(P)
        self.Vap.T(T)
        self.Vap.X(y)
        self.Vap.Mol(V)
        self.Vap.Solver()
        
        self.Liq.P(P)
        self.Liq.T(T)
        self.Liq.X(x)
        self.Liq.Mol(L)
        self.Liq.Solver()
        
        self.Solve = 1
##        if self.VAP!= None:
##            self.Vap.Copy()
##        if self.LIQ!= None:
##            self.Liq.Copy()

#===================================================================
##class HeatChanger:
##    
##    def __init__(self,Model=None):
##        self.Hot = Heater(Model)
##        self.Cool = Cooling(Model)
##        self.Hot.DP = 0 # en Kpa
##        self.Hot.DH = 0 # en kj
##        self.Hot.DT = 0 # K
##        self.Cool.DP = 0 # en Kpa
##        self.Cool.DH = 0 # en kj
##        self.cool.DT = 0 # K
##        self.Model = Model
##        self.Solve = 0
##    
##    def Solver(self):
##        
##        T= self.Hot.Out.Get("T")
##        
##        P1 = self.In.Get("P")
##        P2 = P1-self.DP
##        self.Out.P(P2)
##        
##        if self.DT !=0:
##            T1 = self.In.Get("T")
##            T2 = T1+self.DT
##            self.Out.T(T2)
##            self.Out.Solver()
##            self.Copy()
##            self.DH = abs(self.In.Get("H")-self.Out.Get("H"))*self.In.MoleFlow
##            self.Solve = 1
##
##        if self.DH !=0:
##            H1 = self.In.Get("H")
##            H2 = H1+self.DH/self.In.MoleFlow
##            self.Out.T(H2)
##            self.Copy()
##            self.Out.Solver()
##            self.Solve = 1
##    
##        if self.OUT!= None:
##            self.Out.Copy()
