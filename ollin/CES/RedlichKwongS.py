from ollin.Tools import MixingRules
from ollin.Flash.Flash import Flash
from ollin.EOS.eos import EOS
from numpy.oldnumeric import sqrt,array,power,log,exp,absolute
from ollin.Tools.tools import lagrange
from ollin.Thermodinamics.Constans import R

class Model:
    """ This try to solve the ecuation of state"""
    
    def __init__(self,PV):
        self.TagsOfConst = ["TC","PC","VC","RK_A","RK_B","CP_A","CP_B","CP_C","CP_D","HV","TB","DELHF","DELGF"]
        self.EOS = EOS(1,0)
        self.PV = PV# Presure Vapor Equation
##        self.Thermo = Thermo()
##        self.TagsOfConst += self.Thermo.NeedVars()
    
    def NeedVars(self):
        return self.TagsOfConst
    
    def NeedVars(self):
        return self.TagsOfConst
    
    def FugaP(self,Z,A,B):
        """ Fugacity Coefficient of Pure Substances"""
        LogFug = Z-1 - log(Z-B) - A/B*log(1+B/Z)
        Fug = exp( LogFug )
        return Fug
    
    def FugaM(self,Z,A_i,B_i,A,B):
        
        LogFug =  B_i/B*(Z-1) - log(Z-B) + A/B * ( B_i/B- 2*sqrt( A_i/A ) )* log( 1 + B/Z)
        Fug = exp ( LogFug )
        return Fug
    
    def dadT(self,ac,T):
        return -ac/(2*T*sqrt(T))
    
    
    def d2adT2(self,ac,T):
        return 3*ac/(4*T*T*sqrt(T))

    def Solver(self,model,case):
##        self.Isotermicx(model,case)
        """Case with  defined temperature"""
        if case.Prop["T"] != None and  case.Solve!=1:
            print "Defined Temperature"
            if case.Prop["P"]!= None:
                print "...Defined Presure"
                self.Isotermic(model,case)
                self.EOS.Thermal(model,case)
                case.Solve = 1
            
            elif case.Prop["FracVap"] != None:
                print "...Defined FracVap"
                self.FracTemp(model,case)
                self.EOS.Thermal(model,case)
                case.Solve = 1
                
            elif case.Prop["H"] != None:
                print "...Defined Hentalpy"
                self.HenTemp(model,case)
                case.Solve = 1

        """Case with defines Presure"""
        if case.Prop["P"] != None and  case.Solve!=1:
            print "Defined Presure"
            if case.Prop["FracVap"] != None:
                print "...Defined FracVap"
                self.FracPre(model,case)
                self.EOS.Thermal(model,case)
                case.Solve = 1
                
            elif case.Prop["H"] != None:
                print "...Defined Hentalpy"
                self.HenPre(model,case)
                case.Solve = 1
   

#################################################################
#Isotermic metode for solve the case
#################################################################
    def Isotermic(self,model,case):
        xm = case.Prop["x"]
        
        T = case.Prop["T"]
        P = case.Prop["P"]
        Ac = model["RK_A"]
        b_i = model["RK_B"]
        case.Prop["dadT"] = self.dadT( Ac,T)
        case.Prop["d2adT2"] = self.d2adT2( Ac,T)
        case.Prop["MolWt"] = sum( xm* model["MoleWt"] )
        
        PreVap = self.PV.P(T,model)
        case.Prop["PreVap"]=PreVap
        
        AlphaT = 1/sqrt( T)
        case.Prop["AlphaT"] = AlphaT
        
        a_i = Ac * AlphaT
        case.Prop["a"] =  a_i
        
        A_i = ( a_i * P)/ pow( R * T,2)
        B_i = ( b_i * P )/( R * T)    
        case.Prop["A"] = A_i
        case.Prop["B"] = B_i
        
        Zl_i= self.EOS.ZL(A_i,B_i)
        Zv_i= self.EOS.ZG(A_i,B_i)
        case.Prop["Zli"] = Zl_i
        case.Prop["Zvi"] = Zv_i
    
        case.Prop["Vli"] = Zl_i* R * T / P
        case.Prop["Vvi"] = Zv_i* R * T / P
    
        CoeFugo_v = self.FugaP(Zv_i, A_i, B_i )
        CoeFugo_l = self.FugaP(Zl_i, A_i, B_i )
        yf = xm
        xf = xm
        
        k_i = 1
        RFrac = 2
        FrVap, xf, yf =  Flash(case.Prop["PreVap"]/P,xm)
               
        #Iteration to calculate the Fractio Vapor
        while k_i <=10:
            B_v = MixingRules.Molar( yf, B_i)
            A_v = power( sum( yf* sqrt(A_i)  ),2 )
            
            B_l = MixingRules.Molar( xf, B_i)
            A_l = power( sum( xf* sqrt(A_i)  ),2 )

            Z_v = self.EOS.ZG(A_v,B_v)
            Z_l = self.EOS.ZL(A_l,B_l)
         
            CoeFugM_v = self.FugaM(Z_v, A_i,B_i,A_v,B_v)
            CoeFugM_l = self.FugaM(Z_l, A_i,B_i,A_l,B_l)
            
            fi = P*CoeFugM_v*yf
            
            ki = CoeFugM_l/CoeFugM_v
            FrVap, xf, yf = Flash(ki, xm)
            
            Z = FrVap*Z_v + (1- FrVap)* Z_l
            
            if abs(RFrac-FrVap)<= 1e-10:
                case.Solve = 1
                break
                
            RFrac = FrVap
            k_i +=1 
    
        V_l = Z_l * R * T / P
        V_v = Z_v * R * T / P
            
        case.Prop["Z"] =  Z
        case.Prop["Zl"] = Z_l
        case.Prop["Zv"] = Z_v
        case.Prop["Ki"] = ki
        case.Prop["FracVap"] = FrVap
        case.Prop["CoefPureLiq"] = CoeFugo_l
        case.Prop["CoefPureVap"] = CoeFugo_v
        case.Prop["CoefMixVLiq"] = CoeFugM_l
        case.Prop["CoefMixVap"] = CoeFugM_v
        case.Prop["ActivityVap"] = CoeFugM_v/CoeFugo_v
        case.Prop["ActivityLiq"] = CoeFugM_l/CoeFugo_l
        case.Prop["xf"] = xf
        case.Prop["yf"] = yf
        case.Prop["Vl"] = V_l
        case.Prop["Vv"] = V_v
        case.Prop["MolWt_l"] = sum( xf* model["MoleWt"] )
        case.Prop["MolWt_v"] = sum( yf* model["MoleWt"] )
        case.Prop["LiqDen"] = sum( xf* model["LIQDEN"] )
        
#################################################################
#Case that Tempererature and Fraction Vapor are defined
#################################################################
    def FracTemp(self,model,case):
    
        P_i = []
        Fra_i= []
        Fra_r =case.Prop["FracVap"]
        
        case.Prop["P"]= sum(self.PV.P(case.Prop["T"],model)*case.Prop["x"])
        self.Isotermic(model,case)
        P_i.append(case.Prop["P"])
        Fra_i.append( case.Prop["FracVap"] )
        
        if case.Prop["FracVap"] <=0.5:
            case.Prop["P"]= case.Prop["P"]*0.5
            self.Isotermic(model,case)
            while case.Prop["FracVap"] <=0.05:
                case.Prop["P"]= case.Prop["P"]*0.5
                self.Isotermic(model,case)
        else:
            case.Prop["P"]= case.Prop["P"]*1.5
            self.Isotermic(model,case)
            while case.Prop["FracVap"] >=0.95:
                case.Prop["P"]= case.Prop["P"]*1.5
                self.Isotermic(model,case)
        
##        self.Isotermic( model,case )
        P_i.append( case.Prop["P"] )
        Fra_i.append( case.Prop["FracVap"] )
        
        case.Prop["P"]= sum(P_i)/2
        self.Isotermic( model,case )
        P_i.append( case.Prop["P"] )
        Fra_i.append( case.Prop["FracVap"] )
        
        i = 1
        while i<=20:
            case.Prop["P"]=lagrange( Fra_i, P_i, Fra_r )
            self.Isotermic( model, case )
            P_i.append( case.Prop["P"] )
            Fra_i.append( case.Prop["FracVap"] )
            i += 1
            if abs(Fra_r-case.Prop["FracVap"])<=1e-10:
                break


#################################################################
#Case that Tempererature and Hentalpy are defined
#################################################################
    def HenTemp(self,model,case):
        P_i = []
        H_i= []
        H_r =case.Prop["H"]
        case.Prop["P"]= sum(self.PV.P(case.Prop["T"],model)*case.Prop["x"])
        self.Isotermic(model,case)
        self.EOS.Thermal(model,case)
        
        P_i.append(case.Prop["P"])
        H_i.append( case.Prop["H"] )
        
        if case.Prop["H"] <=0.5*H_r:
            case.Prop["P"]= case.Prop["P"]*0.5
        else:
            case.Prop["P"]= case.Prop["P"]*1.5
    
        self.Isotermic(model,case)
        self.EOS.Thermal(model,case)
        P_i.append(case.Prop["P"])
        H_i.append( case.Prop["H"] )
        
        case.Prop["P"]= sum(P_i)/2
        self.Isotermic(model,case)
        self.EOS.Thermal(model,case)
        P_i.append(case.Prop["P"])
        H_i.append( case.Prop["H"] )
        
        i = 1
        
        while i<=20:
            case.Prop["P"]=lagrange(H_i,P_i,H_r)
            self.Isotermic(model,case)
            self.EOS.Thermal(model,case)
            P_i.append(case.Prop["P"])
            H_i.append( case.Prop["H"] )
            i += 1

            if abs(H_r-case.Prop["H"])<=1e-10:
                break

#################################################################
#Case that Presure and Fraction Vapor are defined
#################################################################
    def FracPre(self,model,case):
    
        T_i = []
        Fra_i= []
        Fra_r =case.Prop["FracVap"]
        
        case.Prop["T"]= sum(self.PV.T(case.Prop["P"],model)*case.Prop["x"])
        
        self.Isotermic(model,case)
        
        T_i.append(case.Prop["T"])
        Fra_i.append( case.Prop["FracVap"] )
##        print case.Prop["FracVap"],case.Prop["T"]
        
        if case.Prop["FracVap"] <=0.5:
            case.Prop["T"]= case.Prop["T"]*1.05
            self.Isotermic(model,case)
            while case.Prop["FracVap"] <=0.05:
                case.Prop["T"]= case.Prop["T"]*1.05
                self.Isotermic(model,case)
        else:
            case.Prop["T"]= case.Prop["T"]*0.95
            self.Isotermic(model,case)
            while case.Prop["FracVap"] >=0.95:
                case.Prop["T"]= case.Prop["T"]*0.95
                self.Isotermic(model,case)
        
        self.Isotermic(model,case)
        T_i.append(case.Prop["T"])
        Fra_i.append( case.Prop["FracVap"] )
        
        case.Prop["T"]= sum(T_i)/2
        self.Isotermic( model,case )
        T_i.append( case.Prop["T"] )
        Fra_i.append( case.Prop["FracVap"] )
##        print case.Prop["FracVap"],case.Prop["T"]
        
        i = 1
        while i<=20:
            case.Prop["T"]=lagrange(Fra_i,T_i,Fra_r)
##            print case.Prop["FracVap"],case.Prop["T"]
            self.Isotermic(model,case)
            T_i.append(case.Prop["T"])
            Fra_i.append( case.Prop["FracVap"] )
            i += 1
            if abs(Fra_r-case.Prop["FracVap"])<=1e-10:
                break

#################################################################
#Case that Presure and Hentalpy are defined
#################################################################
    def HenPre(self,model,case):
        T_i = []
        H_i= []
        H_r =case.Prop["H"]
        case.Prop["T"]= sum(self.PV.T(case.Prop["P"],model)*case.Prop["x"])
        self.Isotermic(model,case)
        self.EOS.Thermal(model,case)
        T_i.append(case.Prop["T"])
        H_i.append( case.Prop["H"] )
        
        if case.Prop["FracVap"] <=0.5:
            case.Prop["T"]= case.Prop["T"]*1.1
            self.Isotermic(model,case)
            while case.Prop["FracVap"] <=0.05:
                case.Prop["T"]= case.Prop["T"]*1.1
                self.Isotermic(model,case)
        else:
            case.Prop["T"]= case.Prop["T"]*0.9
            self.Isotermic(model,case)
            while case.Prop["FracVap"] >=0.95:
                case.Prop["T"]= case.Prop["T"]*0.9
                self.Isotermic(model,case)
                
        self.Isotermic(model,case)
        self.EOS.Thermal(model,case)
        T_i.append(case.Prop["T"])
        H_i.append( case.Prop["H"] )
        
        case.Prop["T"]= sum(T_i)/2
        self.Isotermic(model,case)
        self.EOS.Thermal(model,case)
        T_i.append(case.Prop["T"])
        H_i.append( case.Prop["H"] )
        
        i = 1
        while i<=20:
            case.Prop["T"]=lagrange(H_i,T_i,H_r)
            self.Isotermic(model,case)
            self.EOS.Thermal(model,case)
            T_i.append(case.Prop["T"])
            H_i.append( case.Prop["H"] )
            i += 1
            if abs(H_r-case.Prop["H"])<=1e-10:
                break

#################################################################
#Case that Fraction Vapor  and Hentalpy are defined
#################################################################
##    def HenFrac(self,model,case):
##        T_i = []
##        P_i = []
##        H_i= []
##        H_r =case.Prop["H"]
##        case.Prop["T"]= sum(self.PV.T(case.Prop["P"],model)*case.Prop["x"])
##        self.Isotermic(model,case)
##        self.Thermal(model,case)
##        T_i.append(case.Prop["T"])
##        H_i.append( case.Prop["H"] )
##        
##        if case.Prop["FracVap"] <=0.5:
##            case.Prop["T"]= case.Prop["T"]*1.1
##            self.Isotermic(model,case)
##            while case.Prop["FracVap"] <=0.05:
##                case.Prop["T"]= case.Prop["T"]*1.1
##                self.Isotermic(model,case)
##        else:
##            case.Prop["T"]= case.Prop["T"]*0.9
##            self.Isotermic(model,case)
##            while case.Prop["FracVap"] >=0.95:
##                case.Prop["T"]= case.Prop["T"]*0.9
##                self.Isotermic(model,case)
##                
##        self.Isotermic(model,case)
##        self.Thermal(model,case)
##        T_i.append(case.Prop["T"])
##        H_i.append( case.Prop["H"] )
##        i = 1
##        while i<=20:
##            case.Prop["T"]=lagrange(H_i,T_i,H_r)
##            self.Isotermic(model,case)
##            self.Thermal(model,case)
##            T_i.append(case.Prop["T"])
##            H_i.append( case.Prop["H"] )
##            i += 1
##            if abs(H_r-case.Prop["H"])<=1e-10:
##                break                
    def Isotermicx(self,model,case):
        yf = case.Prop["yf"]
        
        T = case.Prop["T"]
        P = case.Prop["P"]
        Ac = model["RK_A"]
        b_i = model["RK_B"]
        case.Prop["dadT"] = self.dadT( Ac,T)
        case.Prop["d2adT2"] = self.d2adT2( Ac,T)
##        case.Prop["MolWt"] = sum( xm* model["MoleWt"] )
        PreVap = self.PV.P(T,model)
        case.Prop["PreVap"]=PreVap
        AlphaT = 1/sqrt( T)
        case.Prop["AlphaT"] = AlphaT
        
        a_i = Ac * AlphaT
        case.Prop["a"] =  a_i
        
        A_i = ( a_i * P)/ pow( R * T,2)
        B_i = ( b_i * P )/( R * T)    
        case.Prop["A"] = A_i
        case.Prop["B"] = B_i
        
        Zl_i= self.EOS.ZL(A_i,B_i)
        Zv_i= self.EOS.ZG(A_i,B_i)
        case.Prop["Zli"] = Zl_i
        case.Prop["Zvi"] = Zv_i
    
        case.Prop["Vli"] = Zl_i* R * T / P
        case.Prop["Vvi"] = Zv_i* R * T / P
    
        CoeFugo_v = self.FugaP(Zv_i, A_i, B_i )
        CoeFugo_l = self.FugaP(Zl_i, A_i, B_i )
##        yf = xm
        xf = yf/(PreVap/P)
        sk = sum(PreVap/P)
        
        B_v = MixingRules.Molar( yf, B_i)
        A_v = power( sum( yf* sqrt(A_i)  ),2 )
        Z_v = self.EOS.ZG(A_v,B_v)
        CoeFugM_v = self.FugaM(Z_v, A_i,B_i,A_v,B_v)
        k_i = 1
        RFrac = 2
##        FrVap, xf, yf =  Flash(PreVap/P,xm)
               
        #Iteration to calculate the Fractio Vapor
        while k_i <=10:
            B_l = MixingRules.Molar( xf, B_i)
            A_l = power( sum( xf* sqrt(A_i)  ),2 )
            Z_l = self.EOS.ZL(A_l,B_l)
            CoeFugM_l = self.FugaM(Z_l, A_i,B_i,A_l,B_l)
            
            fi = P*CoeFugM_v*yf
            
            ki = CoeFugM_l/CoeFugM_v
            
##            Z = FrVap*Z_v + (1- FrVap)* Z_l
            
            if abs(sk-sum(ki))<= 1e-8:
                print xf
##                case.Solve = 1
                break
            xf = yf/ki
            sk = sum(ki)
            k_i +=1 
        FrVap,xm = Flash(ki,x=xf,y=yf)
        print "Frac",FrVap
        Z = FrVap*Z_v + (1- FrVap)* Z_l
        V_l = Z_l * R * T / P
        V_v = Z_v * R * T / P
##            
##        case.Prop["Z"] =  Z
##        case.Prop["Zl"] = Z_l
##        case.Prop["Zv"] = Z_v
##        case.Prop["Ki"] = ki
##        case.Prop["FracVap"] = FrVap
##        case.Prop["CoefPureLiq"] = CoeFugo_l
##        case.Prop["CoefPureVap"] = CoeFugo_v
##        case.Prop["CoefMixVLiq"] = CoeFugM_l
##        case.Prop["CoefMixVap"] = CoeFugM_v
##        case.Prop["ActivityVap"] = CoeFugM_v/CoeFugo_v
##        case.Prop["ActivityLiq"] = CoeFugM_l/CoeFugo_l
##        case.Prop["xf"] = xf
##        case.Prop["yf"] = yf
##        case.Prop["Vl"] = V_l
##        case.Prop["Vv"] = V_v
##        case.Prop["MolWt_l"] = sum( xf* model["MoleWt"] )
##        case.Prop["MolWt_v"] = sum( yf* model["MoleWt"] )
##        case.Prop["LiqDen"] = sum( xf* model["LIQDEN"] )
