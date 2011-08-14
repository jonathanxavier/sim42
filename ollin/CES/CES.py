#CUBIC ECUATION O STATE SOLVER AND OTHERS
from ollin.pvt import MixingRules
from math import sqrt
##from ollin.pvt.Fuga import CoeFugo,CoeFugM
from ollin.pvt.Flash import Flash
from ollin.pvt.eos import EOS
from ollin.pvt.Thermodinamic import Thermo
from numpy.oldnumeric import sqrt,array,power,log,exp
from ollin.tools.tools import lagrange

Equation = {}
R = 8.314 # kpa L/mol K
#############################################################################
 ############################################################################
 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
 ##################################################################################
 ##################################################################################
class RedlichKwong_simple:
    """ This try to solve the ecuation of state"""
    
    def __init__(self,PV):
        self.TagsOfConst = ["TC","PC","VC","RK_A","RK_B"]
        self.EOS = EOS(1,0)
        self.PV = PV# Presure Vapor Equation
        self.Themo = Thermo()
    
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
    
    

    def Solver(self,model,case):
        xm = case.Prop["x"]
        
        T = case.Prop["T"]
        P = case.Prop["P"]
        Ac = model["RK_A"]
        b_i = model["RK_B"]
        
        case.Prop["MolWt"] = sum( xm* model["MoleWt"] )
        
        AlphaT = 1/sqrt( T)
        
        a_i = Ac * AlphaT
        
        A_i = ( a_i * P)/ pow( R * T,2)
        B_i = ( b_i * P )/( R * T)    
    
        Zl_i= self.EOS.ZL(A_i,B_i)
        Zv_i= self.EOS.ZG(A_i,B_i)
    
        CoeFugo_v = self.FugaP(Zv_i, A_i, B_i )
        CoeFugo_l = self.FugaP(Zl_i, A_i, B_i )
        
        yf = xm
        xf = xm
        for i in range(3):

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
            
        case.Prop["Z"] =  Z
        case.Prop["Zl"] = Z_l
        case.Prop["Zv"] = Z_v
        case.Prop["Ki"] = ki
        case.Prop["FracVap"] = FrVap
        case.Prop["CoefPureLiq"] = CoeFugo_l
        case.Prop["CoefPureVap"] = CoeFugo_v
        case.Prop["CoefMixVLiq"] = CoeFugM_l
        case.Prop["CoefMixVap"] = CoeFugM_v
        case.Prop["xf"] = xf
        case.Prop["yf"] = yf
##            print "\nCV",CoeFugM_v,"\nKi",ki,"\nFracVap",FrVap,"\nXf",xf,sum(xf),"\nYf",yf,sum(yf),"\nCL",CoeFugM_l,"\nZv,Zl",Z_v,Z_l,Z
    
Equation["RedlichKwong_simple"] = RedlichKwong_simple
 
 #Other RedlichKwong
 #############################################################################
 ############################################################################
 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
 ##################################################################################
 ##################################################################################
class RedlichKwong:
    """ This try to solve the ecuation of state"""
    
    def __init__(self,PV):
        self.TagsOfConst = ["TC","PC","VC","RK_A","RK_B"]
        self.EOS = EOS(1,0)
        self.PV = PV# Presure Vapor Equation
        self.Thermo = Thermo()
        self.TagsOfConst += self.Thermo.NeedVars()
##        print self.TagsOfConst
    
    def NeedVars(self):
        return self.TagsOfConst
    
    def FugaP(self,Z,A,B):
        """ Fugacity Coefficient of Pure Substances"""
        LogFug = Z-1 - log(Z-B) - A/B*log(1+B/Z)
        Fug = exp( LogFug )
        return Fug
    
    def FugaM(self,Z,A_i,B_i,A,B):
##        print "z-b",Z,Z-B
        LogFug =  B_i/B*(Z-1) - log(Z-B) + A/B * ( B_i/B- 2*A_i/A )* log( 1 + B/Z)
        Fug = exp ( LogFug )
        return Fug
    
    def dadT(self,ac,T):
        return -ac/(2*T*sqrt(T))
    
    
    def d2adT2(self,ac,T):
        return 3*ac/(4*T*T*sqrt(T))

    def Solver(self,model,case):
        if case.Prop["T"] != None:
            if case.Prop["P"]!= None:
                self.Isotermic(model,case)
            
            elif case.Prop["FracVap"] != None:
                self.FracTemp(model,case)
##        elif case.Prop["T"]=
    

#################################################################
#Isotermic metode for solve the case
#################################################################
    def Isotermic(self,model,case):
    
        xm = case.Prop["x"]
        T = case.Prop["T"]
        P = case.Prop["P"]
        Ac = model["RK_A"]
        b_i = model["RK_B"]
        PreVap = self.PV.P(T,model)
##        print "K_I",PreVap/P
        AlphaT = 1/sqrt( T)
        case.Prop["MolWt"] = sum( xm* model["MoleWt"] )
        a_i = Ac * AlphaT
        
        A_i = ( a_i * P)/ pow( R * T,2)
        B_i = ( b_i * P )/( R * T)    
    
        Zl_i= self.EOS.ZL(A_i,B_i)
        Zv_i= self.EOS.ZG(A_i,B_i)
    
        CoeFugo_v = self.FugaP(Zv_i, A_i, B_i )
        CoeFugo_l = self.FugaP(Zl_i, A_i, B_i )
        yf = xm
        xf = xm
        
        k_i = 1
        RFrac = 2
        #Iteration to calculate the Fractio Vapor
        while k_i <=10:
    
            A_vi = MixingRules.MolarK2( yf, A_i, k=0 )
            A_li = MixingRules.MolarK2( xf, A_i,k=0)
            
            B_v = MixingRules.Molar( yf, B_i)
            A_v = MixingRules.MolarK( yf,A_i ,k=0 )
            
            B_l = MixingRules.Molar( xf, B_i)
            A_l = MixingRules.MolarK( xf,A_i,k=0) 
            
            Z_v = self.EOS.ZG(A_v,B_v)
            Z_l = self.EOS.ZL(A_l,B_l)
         
            CoeFugM_v = self.FugaM(Z_v, A_vi,B_i,A_v,B_v)
            CoeFugM_l = self.FugaM(Z_l, A_li,B_i,A_l,B_l)
            fi = P*CoeFugM_v*yf
            
            ki = CoeFugM_l/CoeFugM_v
            FrVap, xf, yf = Flash(ki, xm)
            
            Z = FrVap*Z_v + (1- FrVap)* Z_l
##            print Z
            
            if (RFrac-FrVap)<= 1e-10:
                break
                
            RFrac = FrVap
            k_i +=1 
    
        V_l = Z_l * R * T / P
        V_v = Z_v * R * T / P
        #Thermal Calcs
##        print model.keys()
        Cp,H0,S0 = self.Thermo.Calc(model["CP_A"],model["CP_B"],model["CP_C"],model["CP_D"],T,R)
        
        dadT = self.dadT( Ac,T)
        d2adT2 = self.d2adT2( Ac,T)
        
        dadT_l = MixingRules.MolarK( xf,dadT,k=0)
        d2adT2_l = MixingRules.MolarK( xf,d2adT2 ,k=0) 
        
        #Liquid 
        a_l = MixingRules.MolarK( xf, a_i, k=0 )
        b_l = MixingRules.Molar( xf, b_i)
        
        dA_l = self.EOS.dA(Z_l,a_l,b_l,B_l,R,T)
        dS_l = self.EOS.dS(Z_l,dadT_l,b_l,B_l,R,T)
        dH_l = self.EOS.dH(Z_l,dA_l,dS_l,R,T)
        
        INTd2PdT2_l = self.EOS.INTd2PdT2(Z_l,d2adT2_l,b_l,B_l)
        dCv_l= self.EOS.dCv(INTd2PdT2_l,R,T)
        
        dPdT_l = self.EOS.dPdT(dadT_l,b_l,R,T,V_l)
        dPdV_l = self.EOS.dPdV(a_l,b_l,R,T,V_l)
        dCp_l= self.EOS.dCp(dCv_l,dPdT_l,dPdV_l,T)
##        print "DAL",dA_l,dS_l
        
        # Vapor
        a_v = MixingRules.MolarK( yf, a_i, k=0 )
        b_v = MixingRules.Molar( yf, b_i)
        
        dadT_v = MixingRules.MolarK( yf,dadT,k=0)
        d2adT2_v = MixingRules.MolarK( yf,d2adT2 ,k=0)
        
        dA_v = self.EOS.dA(Z_v,a_v,b_v,B_v,R,T)
        dS_v = self.EOS.dS(Z_v,dadT_v,b_v,B_v,R,T)
        dH_v = self.EOS.dH(Z_v,dA_v,dS_v,R,T)
        
        INTd2PdT2_v = self.EOS.INTd2PdT2(Z_v,d2adT2_v,b_v,B_v)
        dCv_v= self.EOS.dCv(INTd2PdT2_v,R,T)
        
        dPdT_v = self.EOS.dPdT(dadT_v,b_v,R,T,V_v)
        dPdV_v = self.EOS.dPdV(a_v,b_v,R,T,V_v)
        dCp_v= self.EOS.dCp(dCv_v,dPdT_v,dPdV_v,T)
        
        #Mix
        HV = sum(yf*model["HV"])
        Ho_M = sum(yf*H0)
        So_M = sum(yf*S0) -R*sum(yf*log(yf))
        
        H_l = Ho_M +dH_l
        H_v = Ho_M +dH_v
        
##        print "H ",H_l,H_v,HV
##        print "V ", V_l,V_v
        
        case.Prop["Z"] =  Z
        case.Prop["Zl"] = Z_l
        case.Prop["Zv"] = Z_v
        case.Prop["Ki"] = ki
        case.Prop["FracVap"] = FrVap
        case.Prop["CoefPureLiq"] = CoeFugo_l
        case.Prop["CoefPureVap"] = CoeFugo_v
        case.Prop["CoefMixVLiq"] = CoeFugM_l
        case.Prop["CoefMixVap"] = CoeFugM_v
        case.Prop["xf"] = xf
        case.Prop["yf"] = yf
        
        case.Prop["H0"] = Ho_M
        case.Prop["S0"] = So_M
##        case.Prop["H_L"] = H_l
##        case.Prop["H_V"] = H_v
##        case.Prop["HV"] = HV
##        case.Prop
    
    def FracTemp(self,model,case):
        P_i = []
        Fra_i= []
        Fra_r =case.Prop["FracVap"]
        
        case.Prop["P"]= sum(self.PV.P(case.Prop["T"],model)*case.Prop["x"])
        self.Isotermic(model,case)
##        print case.Prop["FracVap"]
        P_i.append(case.Prop["P"])
        Fra_i.append( case.Prop["FracVap"] )
        if case.Prop["FracVap"] <=0.5:
            case.Prop["P"]= case.Prop["P"]*0.5
        else:
            case.Prop["P"]= case.Prop["P"]*1.5
        self.Isotermic(model,case)
        P_i.append(case.Prop["P"])
        Fra_i.append( case.Prop["FracVap"] )
        i = 1
        while i<=20:
            case.Prop["P"]=lagrange(Fra_i,P_i,Fra_r)
            self.Isotermic(model,case)
            P_i.append(case.Prop["P"])
##            print case.Prop["P"]
            Fra_i.append( case.Prop["FracVap"] )
            i += 1
            if abs(Fra_r-case.Prop["FracVap"])<=1e-10:
                break

Equation["RedlichKwong"] = RedlichKwong
 
 #############################################################################
 ############################################################################
 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
 ##################################################################################
 ##################################################################################
class SRK:

    def __init__(self,PV):
        self.TagsOfConst = ["TC","PC","VC","SRK_A","RK_B","OMEGA"]
        self.EOS = EOS(1,0)
        self.PV = PV# Presure Vapor Equation
    
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
        
        LogFug =  B_i/B*(Z-1) - log(Z-B) + A/B * ( B_i/B- 2*A_i/A  )* log( 1 + B/Z)
        Fug = exp ( LogFug )
        return Fug    
    
    def Solver(self,model,case):
        xm = case.Prop["x"]
        T = case.Prop["T"]
        P = case.Prop["P"]
        Ac = model["SRK_A"]
        b_i = model["RK_B"]
        W_i = model["OMEGA"]
        TC_i = model["TC"]
        
        case.Prop["MolWt"] = sum( xm* model["MoleWt"] )
        
        fwi = 0.48+0.1574*W_i-0.176*power(W_i,2)
        Tr_i = T /TC_i
        AlphaT = power(  ( 1+fwi*(1-sqrt(Tr_i) ) ),2)

        a_i = Ac * AlphaT
        
        A_i = ( a_i * P)/ pow( R * T,2)
        B_i = ( b_i * P )/( R * T)    
    
        Zl_i= self.EOS.ZL(A_i,B_i)
        Zv_i= self.EOS.ZG(A_i,B_i)
    
        CoeFugo_v = self.FugaP(Zv_i, A_i, B_i )
        CoeFugo_l = self.FugaP(Zl_i, A_i, B_i )
        
        yf = xm
        xf = xm
        
        for i in range(3):
    
            A_vi = MixingRules.MolarK2( yf, A_i, k=0.0)
            A_li = MixingRules.MolarK2( xf, A_i,k=0.0)
            
            B_v = MixingRules.Molar( yf, B_i)
            A_v = MixingRules.MolarK( yf,A_i ,k=0.0)
            
            B_l = MixingRules.Molar( xf, B_i)
            A_l = MixingRules.MolarK( xf,A_i,k=0.0) 
            
            Z_v = self.EOS.ZG(A_v,B_v)
            Z_l = self.EOS.ZL(A_l,B_l)
         
            CoeFugM_v = self.FugaM(Z_v, A_vi,B_i,A_v,B_v)
            CoeFugM_l = self.FugaM(Z_l, A_li,B_i,A_l,B_l)
            
            fi = P*CoeFugM_v*yf
            
            ki = CoeFugM_l/CoeFugM_v
            #print xm
            FrVap, xf, yf = Flash(ki, xm)
            Z = FrVap*Z_v + (1- FrVap)* Z_l
        
        case.Prop["Z"] =  Z
        case.Prop["Zl"] = Z_l
        case.Prop["Zv"] = Z_v
        case.Prop["Ki"] = ki
        case.Prop["FracVap"] = FrVap
        case.Prop["CoefPureLiq"] = CoeFugo_l
        case.Prop["CoefPureVap"] = CoeFugo_v
        case.Prop["CoefMixVLiq"] = CoeFugM_l
        case.Prop["CoefMixVap"] = CoeFugM_v
        case.Prop["xf"] = xf
        case.Prop["yf"] = yf
        
Equation["Soave"] = SRK


#############################################################################
 ############################################################################
 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
 ##################################################################################
 ##################################################################################
class PR:
    
    def __init__(self,PV):
        self.TagsOfConst = ["TC","PC","VC","PR_A","PR_B","OMEGA"]
        self.EOS = EOS(2,-1)
        self.PV = PV# Presure Vapor Equation
    
    def NeedVars(self):
        return self.TagsOfConst
    
    def NeedVars(self):
        return self.TagsOfConst
    
    def FugaP(self,Z,A,B):
        """ Fugacity Coefficient of Pure Substances"""
        L = ( 1/( 2*sqrt(2) ) ) * log( ( Z +B*(1+sqrt(2) ) ) / ( Z +B*(1-sqrt(2) ) ) )
        LogFug = Z-1 - log(Z-B) - A/B*L
        Fug = exp( LogFug )
        return Fug
    
    def FugaM(self,Z,A_i,B_i,A,B):
        L = ( 1/( 2*sqrt(2) ) ) * log( ( Z +B*(1+sqrt(2) ) ) / ( Z +B*(1-sqrt(2) ) ) )
        LogFug =  B_i/B*(Z-1) - log(Z-B) + A/B * ( B_i/B- 2*A_i/A  ) * L
        Fug = exp ( LogFug )
        return Fug
    
##    def dadT
    
    def Solver(self,model,case):
    
        xm = case.Prop["x"]
        T = case.Prop["T"]
        P = case.Prop["P"]
        Ac = model["PR_A"]
        b_i = model["PR_B"]
        W_i = model["OMEGA"]
        TC_i = model["TC"]
        
        case.Prop["MolWt"] = sum( xm* model["MoleWt"] )
        
        fwi = []
        for Wii in W_i:
            if Wii <0.5:
                fwi.append( 0.37464+1.54226*Wii-0.26992*power(Wii,2) )
            else:
                fwi.append( 0.3796+1.4850*Wii-0.1644*power(Wii,2)+0.01666*power(Wii,3) )
        
        fwi = array( fwi )
        Tr_i = T /TC_i
        AlphaT = power(  ( 1+fwi*(1-sqrt(Tr_i) ) ),2)

        a_i = Ac * AlphaT
        
        A_i = ( a_i * P)/ pow( R * T,2)
        B_i = ( b_i * P )/( R * T)    
    
        Zl_i= self.EOS.ZL(A_i,B_i)
        Zv_i= self.EOS.ZG(A_i,B_i)
    
        CoeFugo_v = self.FugaP(Zv_i, A_i, B_i )
        CoeFugo_l = self.FugaP(Zl_i, A_i, B_i )
        
        yf = xm
        xf = xm
        
        for i in range(3):
    
            A_vi = MixingRules.MolarK2( yf, A_i, k=0.0)
            A_li = MixingRules.MolarK2( xf, A_i,k=0.0)
            
            B_v = MixingRules.Molar( yf, B_i)
            A_v = MixingRules.MolarK( yf,A_i ,k=0.0)
            
            B_l = MixingRules.Molar( xf, B_i)
            A_l = MixingRules.MolarK( xf,A_i,k=0.0) 
            
            Z_v = self.EOS.ZG(A_v,B_v)
            Z_l = self.EOS.ZL(A_l,B_l)
         
            CoeFugM_v = self.FugaM(Z_v, A_vi,B_i,A_v,B_v)
            CoeFugM_l = self.FugaM(Z_l, A_li,B_i,A_l,B_l)
            
            fi = P*CoeFugM_v*yf
            
            ki = CoeFugM_l/CoeFugM_v
            #print xm
            FrVap, xf, yf = Flash(ki, xm)
            Z = FrVap*Z_v + (1- FrVap)* Z_l
        
        case.Prop["Z"] =  Z
        case.Prop["Zl"] = Z_l
        case.Prop["Zv"] = Z_v
        case.Prop["Ki"] = ki
        case.Prop["FracVap"] = FrVap
        case.Prop["CoefPureLiq"] = CoeFugo_l
        case.Prop["CoefPureVap"] = CoeFugo_v
        case.Prop["CoefMixVLiq"] = CoeFugM_l
        case.Prop["CoefMixVap"] = CoeFugM_v
        case.Prop["xf"] = xf
        case.Prop["yf"] = yf
        
Equation["Peng"] = PR
