from ollin.Tools import MixingRules
from math import sqrt
from ollin.Flash.Flash import Flash
from ollin.EOS.eos import EOS
from ollin.Thermodinamics.Thermodinamic import Thermo
from numpy.oldnumeric import sqrt,array,power,log,exp,absolute
from ollin.Tools.tools import lagrange
from ollin.Thermodinamics.Constans import R

class Model:

    def __init__(self,PV):
        self.TagsOfConst = ["TC","PC","VC","SRK_A","RK_B","OMEGA","CP_A","CP_B","CP_C","CP_D","HV","TB","DELHF","DELGF"]
        self.EOS = EOS(1,0)
        self.PV = PV# Presure Vapor Equation
##        self.Thermo = Thermo()
##        self.TagsOfConst += self.Thermo.NeedVars()
##    
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

    def dadT(self,ac,fw,Tr,Tc):
        return ac*fw*( fw*sqrt(Tr)-fw-1 )/( Tc*sqrt(Tr) )
    
    def d2adT2(self,ac,fw,T,Tr,Tc):
        return fw*( fw+1 )/( 2*Tc*T*sqrt(Tr) )
    
    
    def Solver(self,model,case):
        model["RK_A"]= model["SRK_A"]
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
        Ac = model["SRK_A"]
        b_i = model["RK_B"]
        W_i = model["OMEGA"]
        TC_i = model["TC"]
    
    
        PreVap = self.PV.P(T,model)
        case.Prop["PreVap"]=PreVap
##        print "PV", PreVap
        
        fwi = 0.48+0.1574*W_i-0.176*power(W_i,2)
        case.Prop["fw"]=fwi
        Tr_i = T /TC_i
        case.Prop["Tr"]=Tr_i
        AlphaT = power(  ( 1+fwi*(1-sqrt(Tr_i) ) ),2)
        case.Prop["AlphaT"] = AlphaT
        case.Prop["MolWt"] = sum( xm* model["MoleWt"] )
        case.Prop["dadT"]= self.dadT( Ac,fwi,Tr_i,TC_i)
        case.Prop["d2adT2"]= self.d2adT2( Ac,fwi,T,Tr_i,TC_i)
        
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
##        xf = xm/2
        
        k_i = 1
        RFrac = 2
        
        FrVap, xf, yf =  Flash(case.Prop["PreVap"]/P,xm)
        
        #Iteration to calculate the Fractio Vapor
        while k_i <=20:
##            print k_i 
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
            
##            if RFrac==FrVap:
##                print "hola"
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
        
        case.Prop["T"]= sum( self.PV.T( case.Prop["P"], model ) * case.Prop["x"] )
        
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



###################################################################
###Thermal calcs of streams(for example)
###################################################################
##    def Thermal(self,model,case):
##     #Thermal Calcs
####        Ac = model["RK_A"]
##        T = case.Prop["T"]
##        P = case.Prop["P"]
##        a = case.Prop["a"]
##        xf = case.Prop["xf"]
##        yf = case.Prop["yf"]
##        A = case.Prop["A"]
##        B = case.Prop["B"]
##        Zli = case.Prop["Zli"]
##        Zvi = case.Prop["Zvi"]
##        V_li = case.Prop["Vli"]
##        V_vi = case.Prop["Vvi"]
##        x = case.Prop["x"]
##        fw = case.Prop["fw"]
##        Tr = case.Prop["Tr"]
##        
##        ac = model["SRK_A"]
##        b = model["RK_B"]
##        Tc= model["TC"]
##        
##        Cp,H0,S0 = self.Thermo.Calc(model["CP_A"],model["CP_B"],model["CP_C"],model["CP_D"],T,R)
##        
##        
##        #Liquid 
##        dA_L = self.EOS.dA(Zli, a, b, B, R,T)
##        dS_L = self.EOS.dS(Zli, dadT, b, B, R, T)
##        dH_L= self.EOS.dH(Zli, dA_L, dS_L, R, T)
##        
##        INTd2PdT2_L = self.EOS.INTd2PdT2(Zli , d2adT2 , b ,B)
##        dCv_L= self.EOS.dCv(INTd2PdT2_L ,R,T)
##        
##        dPdT_L = self.EOS.dPdT(dadT,b,R,T,V_li)
##        dPdV_L = self.EOS.dPdV(a ,b ,R,T,V_li)
##        dCp_L = self.EOS.dCp(dCv_L ,dPdT_L ,dPdV_L ,T)
##        
##        # Vapor
##        dA_V = self.EOS.dA(Zvi,a,b,B,R,T)
##        dS_V = self.EOS.dS(Zvi,dadT,b,B,R,T)
##        dH_V = self.EOS.dH(Zvi,dA_V,dS_V,R,T)
##        
##        INTd2PdT2_V = self.EOS.INTd2PdT2(Zvi ,d2adT2 ,b,B)
##        dCv_V = self.EOS.dCv(INTd2PdT2_V,R,T)
##        
##        dPdT_V = self.EOS.dPdT(dadT,b,R,T,V_vi)
##        dPdV_V = self.EOS.dPdV(a,b,R,T,V_vi)
##        dCp_V = self.EOS.dCp(dCv_V,dPdT_V,dPdV_V,T)
##        
##        #Mix
##        HV_i = model["HV"]*power( absolute( ( T-model["TC"] ) / (model["TB"]-model["TC"]) ) , 0.38 )
##        model["HV_T"] = HV_i
##        
##        Ho_M_v = sum(yf* ( H0-dH_V) )
##        Ho_M_l = sum(xf* (H0-dH_L) )
##        
##        So_M_v = sum(yf*( S0-dS_V) )-R*sum(yf*log(yf))
##        So_M_l = sum(xf*( S0-dS_L )) -R*sum(xf*log(xf))
##        
##        H_v = Ho_M_v
##        H_l = Ho_M_l-sum(xf*HV_i)
##        
##        HV = H_v-H_l
##        SV = HV/T
##        
##        S_v = So_M_l
##        S_l = So_M_l-SV
##        #Cp and Cv : Cp-Cv=R,Cv=Cp-R
##        Cv_v = Cp-R
##        case.Prop["Cp_v"]= Cp - dCp_V
##        case.Prop["Cv_v"]= Cv_v - dCv_V 
##        #Save result in the case Hentalpy
##        case.Prop["H"] = H_v*(case.Prop["FracVap"])+H_l*(1-case.Prop["FracVap"])
##        case.Prop["H_l"] = H_l
##        case.Prop["H_v"] = H_v
##        case.Prop["HV"] = HV
##        #Save result in the case Emtropy
##        case.Prop["S"] = S_v*(case.Prop["FracVap"])+S_l*(1-case.Prop["FracVap"])
##        case.Prop["S_l"] = S_l
##        case.Prop["S_v"] = S_v
##        
##        G_l = H_l - T*S_l
##        G_v = H_v - T*S_v
##        
##        #Save result in the case Free 
##        case.Prop["G"] = G_v*(case.Prop["FracVap"])+G_l*(1-case.Prop["FracVap"])
##        case.Prop["G_l"] = G_l
##        case.Prop["G_v"] = G_v
##        
##        U_l = H_l - sum(xf*P*V_li)
##        U_v = H_v - sum(yf*P*V_vi)
##        
##        #Save result in the case Free 
##        case.Prop["U"] = U_v*(case.Prop["FracVap"])+U_l*(1-case.Prop["FracVap"])
##        case.Prop["U_l"] = U_l
##        case.Prop["U_v"] = U_v
##        
##        A_l = U_l - T*S_l
##        A_v = U_v - T*S_v
##        
##        #Save result in the case Free 
##        case.Prop["AFree"] = U_v*(case.Prop["FracVap"])+U_l*(1-case.Prop["FracVap"])
##        case.Prop["AFree_l"] = A_l
##        case.Prop["AFree_v"] = A_v
##        
##        #Hentapy and gibbs formation Energy
##        case.Prop["HF"] =  sum(model["DELHF"]*x)
##        case.Prop["GF"] =  sum(model["DELGF"]*x)
