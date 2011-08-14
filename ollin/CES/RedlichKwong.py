from ollin.Tools import MixingRules
from math import sqrt
from ollin.Flash.Flash import Flash
from ollin.EOS.eos import EOS
from numpy.oldnumeric import sqrt,array,power,log,exp,absolute
from ollin.Tools.tools import lagrange,lagrangeL,lagrangeLL
from ollin.Thermodinamics.Constans import R
from ollin.Thermodinamics.Thermodinamic import Thermo

class Model:
    """ This try to solve the ecuation of state"""
    
    def __init__(self,PV):
        self.TagsOfConst = ["TC","PC","VC","OMEGA","RK_A","RK_B","CP_A","CP_B","CP_C","CP_D","HV","TB","DELHF","DELGF"]
        self.EOS = EOS(1,0)
        self.PV = PV# Presure Vapor Equation
##        self.Thermo = Thermo()
##        self.TagsOfConst += self.Thermo.NeedVars()

    def NeedVars(self):
        return self.TagsOfConst
    
    def FugaP(self,Z,A,B):
        """ Fugacity Coefficient of Pure Substances"""
        LogFug = Z-1 - log(Z-B) - A/B*log(1+B/Z)
        Fug = exp( LogFug )
        return Fug
    
    def FugaM(self,Z,A_i,B_i,A,B):
    
        LogFug =  B_i/B*(Z-1) - log(Z-B) + A/B * ( B_i/B- 2*A_i/A )* log( 1 + B/Z)
        Fug = exp ( LogFug )
        return Fug
    
    def dadT(self,ac,T):
        return -ac/(2*T*sqrt(T))
    
    
    def d2adT2(self,ac,T):
        return 3*ac/(4*T*T*sqrt(T))

    def Solver(self,model,case):
        
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
        W_i = model["OMEGA"]
        TC_i = model["TC"]
        PC_i = model["PC"]
        VC_i = model["VC"]
        xm = case.Prop["x"]
        
##        print xm
        TC = sum( xm* TC_i )
        PC = sum( xm* PC_i )
        VC = sum( xm* VC_i )
##        print "PC",PC_i
##        print "TC",TC_i
##        print TC,PC
        case.Prop["ZC"]=PC*VC/(R*TC)
        case.Prop["PC"]=PC
        case.Prop["TC"]=TC
        case.Prop["VC"]=VC
        case.Prop["Pr"]=P/PC
        case.Prop["Tr"]=T/TC
        
        PreVap = self.PV.P(T,model)
        case.Prop["PreVap"]=PreVap
##        print "PV", PreVap
        
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
        
        case.Prop["CoefPureLiq"] = CoeFugo_l
        case.Prop["CoefPureVap"] = CoeFugo_v
        
        k_i = 1
        RFrac = 2
        ki=PreVap/P
##        print "sum",xf,yf,FrVap
##        print "K",PreVap/P,exp(lnk)
        #Iteration to calculate the Fractio Vapor
        Fr_i = []
        Fu_i= []
        yf_i = []
        xf_i = []
        fl_i =[]
        MinFuga = 1e10
        while k_i <=10:
            
            FrVap, xf, yf =  Flash(ki,xm)
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
            
            f_l = P*CoeFugM_l*xf
            f_v = P*CoeFugM_v*yf
            
            dFuga = sum(f_l-f_v) 
##            print "fuga",sum(f_l),sum(f_v),dFuga,FrVap
            if abs(dFuga) <MinFuga:
##                print "min",dFuga
                MinFuga = abs(dFuga)
                ymin= yf
                xmin= xf
                Frmin = FrVap
           
            ki = CoeFugM_l/CoeFugM_v
            
##            print "\n\n fraction",FrVap,ki#,CoeFugM_l
            
##            print "x",xf
##            print "y",yf,"\n"
            
            if k_i <=3:
                if not FrVap in Fr_i:
##                    print "Yes"
                    Fr_i.append(FrVap)
                    Fu_i.append( f_l/f_v)
                    xf_i.append(xf)
                    yf_i.append(yf)
                    fl_i.append(f_l)
##                    print "FRACTION",Fr_i[0]

            Z = FrVap*Z_v + (1- FrVap)* Z_l
            
            if abs(RFrac-FrVap)<= 1e-8:
##                print "a"
                case.Solve = 1
                break
            if (dFuga)<=1e-3 and (dFuga)>=-3:
##                print "b"
                case.Solve = 1
                break
            RFrac = FrVap
            k_i +=1 
##        print "ki",  ki
        
        
        case.Prop["Fr_i"] =  Fr_i
        case.Prop["Fu_i"] =Fu_i
        case.Prop["xf_i"] =xf_i
        case.Prop["yf_i"] =yf_i
        case.Prop["fl_i"] =fl_i
        case.Prop["MinFuga"] =MinFuga
        case.Prop["xmin"] =xmin
        case.Prop["ymin"] =ymin
        case.Prop["Frmin"] =Frmin
##        print len(Fr_i)
        if abs( sum(f_v-f_l) )>=1 and len(Fr_i)>1:
##            print "YES"
            self.IsotermicL(model,case)
            return 1
        
        
        V_l = Z_l * R * T / P
        V_v = Z_v * R * T / P
        
        case.Prop["Z"] =  Z
        case.Prop["Zl"] = Z_l
        case.Prop["Zv"] = Z_v
        case.Prop["Ki"] = ki
        case.Prop["FracVap"] = FrVap
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
        case.Prop["fl_i"] =f_l
        case.Prop["fv_i"] =f_v
        return 1

#################################################################
#Isotermic metode for solve the case
#################################################################
    def IsotermicL(self,model,case):
    
        xm = case.Prop["x"]
        T = case.Prop["T"]
        P = case.Prop["P"]
        A_i = case.Prop["A"] 
        B_i =case.Prop["B"]
        Fr_i = case.Prop["Fr_i"]
        Fu_i=case.Prop["Fu_i"]
        xf_i=case.Prop["xf_i"] 
        yf_i=case.Prop["yf_i"] 
        fl_i=case.Prop["fl_i"] 
##        FrVap= case.Prop["Frmin"] 
        
        k_i=1
##        print "Free",Fr_i
        xf= lagrangeL(Fu_i,xf_i,1)
        yf = lagrangeL(Fu_i,yf_i,1)
        
        for i in range(len(xf)):
            if xf[i]<=0:
                xf[i]=1e-8
            if yf[i]<=0:
                yf[i]=1e-8
        yf = case.Normal(yf)
        xf = case.Normal(xf)
        ki=yf/xf
        while k_i <=1:
        
            FrVap, xf, yf =  Flash(ki,xm)
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

            f_l = P*CoeFugM_l*xf
            f_v = P*CoeFugM_v*yf
            ki = CoeFugM_l/CoeFugM_v
            
    
##            print "fugaFree",sum(f_l),sum(f_v),f_l/f_v
##            print "x",xfff
##            print "xx",xff
##            print "y",yff,"\n"
##            print "ki",  ki,FrVap
##            print "x",xff,sum(xf)
##            print "y",yff,sum(yf),"\n"
            dFuga =  sum(f_l-f_v)
            if case.Prop["MinFuga"] <abs(dFuga):
                
                xf=case.Prop["xmin"] 
                yf=case.Prop["ymin"] 
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
                
                f_l = P*CoeFugM_l*xf
                f_v = P*CoeFugM_v*yf
                ki = CoeFugM_l/CoeFugM_v
                FrVap=case.Prop["Frmin"]
                dFuga = abs( sum(f_l-f_v) )
##                print "FugaFree2",dFuga,FrVap
            Z = FrVap*Z_v + (1- FrVap)* Z_l
            
            k_i +=1 
##        print "ki",  ki
        V_l = Z_l * R * T / P
        V_v = Z_v * R * T / P
        
        case.Prop["Z"] =  Z
        case.Prop["Zl"] = Z_l
        case.Prop["Zv"] = Z_v
        case.Prop["Ki"] = ki
        case.Prop["FracVap"] = FrVap
        case.Prop["CoefMixVLiq"] = CoeFugM_l
        case.Prop["CoefMixVap"] = CoeFugM_v
        case.Prop["ActivityVap"] = CoeFugM_v/case.Prop["CoefPureVap"]
        case.Prop["ActivityLiq"] = CoeFugM_l/case.Prop["CoefPureLiq"]
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
##        print "TI",T_i
        i = 1
        while i<=20:
##            print "TI",T_i
##            print "TI",Fra_i,case.Prop["T"]
            case.Prop["T"]=lagrange(Fra_i,T_i,Fra_r)
            
            if case.Prop["T"]>=case.Prop["TC"]:
                case.Prop["T"]=case.Prop["TC"]-50
                
##            print case.Prop["T"],Fra_r
##            print case.Prop["FracVap"],case.Prop["T"]
            self.Isotermic(model,case)
##            print case.Prop["T"],Fra_r,case.Prop["FracVap"]
            
            if case.Prop["FracVap"]<=0.01:
            
                while case.Prop["FracVap"]<0.01:
                    case.Prop["T"]= case.Prop["T"]+3
                    print "TII",case.Prop["T"]
                    self.Isotermic( model,case )
            
            elif case.Prop["FracVap"]>=0.99:
            
                while case.Prop["FracVap"]>0.99:
                    case.Prop["T"]= case.Prop["T"]-3
                    print "TII",case.Prop["T"]
                    self.Isotermic( model,case )
                
            T_i.append(case.Prop["T"])
            Fra_i.append( case.Prop["FracVap"] )
##            print min(Fra_i)
##            for m in range(len(T_i)):
##            
##                if abs(min(Fra_i)-case.Prop["FracVap"])<=1e-8:
##                    n=Fra_i.index(min(Fra_i))
##                    T_i[n]=case.Prop["T"]
##                
##                if abs(max(Fra_i)-case.Prop["FracVap"])<=1e-8:
##                    n=Fra_i.index(case.Prop["FracVap"])
##                    T_i[n]=case.Prop["T"]
##
##            else:
                
            
            
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
        
        case.Prop["P"]= sum(T_i)/2
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
##        
##        x = case.Prop["x"]
##        
##        ac = model["RK_A"]
##        b = model["RK_B"]
##        
##        Cp,H0,S0 = self.Thermo.Calc(model["CP_A"],model["CP_B"],model["CP_C"],model["CP_D"],T,R)
##    
##        
##        dadT = self.dadT( ac,T)
##        d2adT2 = self.d2adT2( ac,T)
##
##        case.Prop["dadT"]= dadT
##        case.Prop["d2adT2"]= d2adT2
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
##        HV_i = model["HV"]*power( absolute( ( T-model["TC"] ) / (model["TB"]-model["TC"]) ) , 0.38)
##        model["HV_T"] = HV_i
##        Ho_M_v = sum(yf* ( H0-dH_V) )
##        Ho_M_l = sum(xf* (H0-dH_L) )
##        So_M_v = sum(yf*( S0-dS_V) )-R*sum(yf*log(yf))
##        So_M_l = sum(xf*( S0-dS_L )) -R*sum(xf*log(xf))
##        
##        H_v = Ho_M_v
##        H_l = Ho_M_l-sum(xf*HV_i)
##        
##        HV = H_v-H_l
##        SV = HV/T
##        
##        S_v = So_M_v
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
