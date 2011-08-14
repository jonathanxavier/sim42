# This class defin the cubic eos
import numpy
from numpy.oldnumeric import sqrt,array,power,log,exp,absolute
from ollin.Thermodinamics.Thermodinamic import Thermo
from ollin.Thermodinamics.Constans import R

class EOS:

    def __init__(self,u,w):
        """
        This help to develovep the server
        EOS(u,w)-> class"""
        
        self.u = u
        self.w = w
        self.delta = sqrt( power(u , 2) - 4*w )
        self.Thermo = Thermo()
        self.name = str(self)

# Fuction to calculate Z factor
    def ZL(self,A,B):

        if type(A) == int or type(A) == float or type(A) == numpy.float64:
            A = list((A,))
            B = list((B,))
        numE = len (A) 
        u = self.u
        w = self.w
        list_temp = []

        for j  in range(numE) :
            Ai = A[j]
            Bi = B[j]
            i = 0
            Fz = 1
            a = (1 + Bi - pow(u*Bi,2))
            b = (Ai + pow(w*Bi,2) - u*Bi - pow(u*Bi,2))
            c = Ai*Bi
            d = pow(w*Bi,2)
            e = pow(w*Bi,3)
            
            Z1,Z2 = self.Zo(a,b)
            Fz1  = pow(Z1,3) - a*pow(Z1,2) + b*Z1 - c -d -e
##            print "ZZ",Z1,Z2
            if Fz1 < 0:
                Z = Z2*1.1
                ID = 1
            elif Z1 <=0:
                Z = Z2*1.1
                ID = 2
            else:
                Z = Z1*0.9
                ID = 3

            while i<=50:
                Fz  = pow(Z,3) - a*pow(Z,2) + b*Z - c -d -e
                dFz = 3*pow(Z,2) - 2*a*Z + b
##                print Z,Fz,dFz
                if abs(Fz)<=1e-12:
                    if Z>0:
                        break
                    elif ID==3:
                        Z = Z1*1.1
                        ID = 2
                        i = 1
                    elif  ID==2 :
                        Z = Z2*1.1
                        ID = 1
                        i = 1
                
                Zz = Fz/dFz    
                Z=Z-Zz
                if (Z <-0.1):
                    if ID==3:
                        Z = Z2*1.1
                        ID = 2
                    if ID==2:
                        Z = Z2*1.1
                        ID = 1
                i +=1
##            if Z>1.5:
##                Z= 0.99999
            list_temp.append(Z)
        if numE == 1:
##            print list_temp[0],i
            return list_temp[0]
##        print "Zl",list_temp
        return array(list_temp)
    


    def ZG(self,A,B):

        if type(A) == int or type(A) == float or type(A) == numpy.float64:
            A = list((A,))
            B = list((B,))
        numE = len (A) 
        u = self.u
        w = self.w
        list_temp = []

        for j  in range(numE) :
            Ai = A[j]
            Bi = B[j]
            i = 1
            Fz = 1
            a = (1 + Bi - pow(u*Bi,2))
            b = (Ai + pow(w*Bi,2) - u*Bi - pow(u*Bi,2))
            c = Ai*Bi
            d = pow(w*Bi,2)
            e = pow(w*Bi,3)
            Z1,Z2 = self.Zo(a,b)
            Fz2  = pow(Z2,3) - a*pow(Z2,2) + b*Z2 - c -d -e

            if Fz2 >0:
                Z = Z1*0.9
            else:
                Z = Z2*1.1
##            print "Zg", Z,Z2,Fz2
            while i<=50:
                Fz  = pow(Z,3) - a*pow(Z,2) + b*Z - c -d -e
                dFz = 3*pow(Z,2) - 2*a*Z + b
                if abs(Fz)<=1e-15:
                    break
##                print i, Z,Fz,dFz,Z
                Zz = Fz/dFz        
                Z=Z-Zz
                i +=1
            list_temp.append(Z)
        if numE == 1:
            return list_temp[0]
##        print "Zg",list_temp
        return array(list_temp)

    def Zo(self,a,b):

        a = 2*a
        c =pow(a,2) - 12 *b
##        print "cuadra",a,b,c
##        print c
        if c <0:
            return (0.05,1.0)
        else:
            x1 = (a - sqrt( c ))/6
            x2 = (a + sqrt( c))/6
            if x1<0:
                x1 = 1.0
            if x2<0:
                x2= 0.05
            return (x1,x2)
        

    def dA(self,Z,a,b,B,R,T):
        """ This calculate the residual helmozt energy 
        (Z,a,b,B,R,T)->dA)"""
        u = self.u
        w = self.w
        L = log( ( 2*Z - B*( u-sqrt( u*u-4*w )  ) ) / ( 2*Z +B*( u-sqrt(u*u-4*w)  ) ) )
        return a/( b * sqrt( u*u-4*w ) )*L - R*T*log( Z-B )

    def dS(self,Z,dadT,b,B,R,T):
        """ This calculate the residual Entropy
        (Z,dadT,b,B,R,T)->dA)"""
        u = self.u
        w = self.w
        L = log( ( 2*Z - B*( u-sqrt( u*u-4*w )  ) ) / ( 2*Z +B*( u-sqrt(u*u-4*w)  ) ) )
        return R*log( Z-B )-dadT/( b * sqrt( u*u-4*w ) )*L
        
    
    def dH(self,Z,dA,dS,R,T):
        """ This calculate the residual Enthalpy
        (Z,a,b,B,R,T)->dA)"""
        return dA +T*dS + R*T*(Z-1)
    
    def dCv(self,INTd2PdT2,R,T):
        return T*INTd2PdT2 - R
        
    
    def dCp(self,dCv,dPdT,dpdV,T):
        return dCv - T*dPdT*dPdT/dpdV
    
    def dPdT(self,dadT,b,R,T,V):
    
        u = self.u
        w = self.w
        return R*T / (V-b) - dadT/( V*V + u*b*V +w*b*b)
    
    def dPdV(self,a,b,R,T,V):
        
        u = self.u
        w = self.w
        return -R*T / power( (V-b),2) - ( 2*a*( V+b) )/power( ( V*V + u*b*V +w*b*b), 2)
    
    def INTd2PdT2(self,Z,d2adT2,b,B):
        
        u = self.u
        w = self.w
        L = log( ( 2*Z - B*( u-sqrt( u*u-4*w )  ) ) / ( 2*Z +B*( u-sqrt(u*u-4*w)  ) ) )
        return d2adT2/( b * sqrt( u*u-4*w ) )*L
        
#################################################################
#Thermal calcs of streams(for example)
#################################################################
    def Thermal(self,model,case):
     #Thermal Calcs
##        Ac = model["RK_A"]
        T = case.Prop["T"]
        P = case.Prop["P"]
        a = case.Prop["a"]
        xf = case.Prop["xf"]
        yf = case.Prop["yf"]
        A = case.Prop["A"]
        B = case.Prop["B"]
        Zli = case.Prop["Zli"]
        Zvi = case.Prop["Zvi"]
        V_li = case.Prop["Vli"]
        V_vi = case.Prop["Vvi"]
        x = case.Prop["x"]
        
        ac = model["RK_A"]
        b = model["RK_B"]
        
        Cp,H0,S0 = self.Thermo.Calc(model["CP_A"],model["CP_B"],model["CP_C"],model["CP_D"],T,R)
    
        dadT=case.Prop["dadT"] 
        d2adT2=case.Prop["d2adT2"] 
        
        #Liquid 
        dA_L = self.dA(Zli, a, b, B, R,T)
        dS_L = self.dS(Zli, dadT, b, B, R, T)
        dH_L= self.dH(Zli, dA_L, dS_L, R, T)
        
        INTd2PdT2_L = self.INTd2PdT2(Zli , d2adT2 , b ,B)
        dCv_L= self.dCv(INTd2PdT2_L ,R,T)
        
        dPdT_L = self.dPdT(dadT,b,R,T,V_li)
        dPdV_L = self.dPdV(a ,b ,R,T,V_li)
        dCp_L = self.dCp(dCv_L ,dPdT_L ,dPdV_L ,T)
        # Vapor
        dA_V = self.dA(Zvi,a,b,B,R,T)
        dS_V = self.dS(Zvi,dadT,b,B,R,T)
        dH_V = self.dH(Zvi,dA_V,dS_V,R,T)
        
        INTd2PdT2_V = self.INTd2PdT2(Zvi ,d2adT2 ,b,B)
        dCv_V = self.dCv(INTd2PdT2_V,R,T)
        
        dPdT_V = self.dPdT(dadT,b,R,T,V_vi)
        dPdV_V = self.dPdV(a,b,R,T,V_vi)
        dCp_V = self.dCp(dCv_V,dPdT_V,dPdV_V,T)
        
        #Mix
        HV_i = model["HV"]*power( absolute( ( T-model["TC"] ) / (model["TB"]-model["TC"]) ) , 0.38)
        model["HV_T"] = HV_i
        Ho_M_v = sum(yf* ( H0-dH_V) )
        Ho_M_l = sum(xf* (H0-dH_L) )
        So_M_v = sum(yf*( S0-dS_V) )-R*sum(yf*log(yf))
        So_M_l = sum(xf*( S0-dS_L )) -R*sum(xf*log(xf))
        
        H_v = Ho_M_v
        H_l = Ho_M_l-sum(xf*HV_i)
        
        HV = H_v-H_l
        SV = HV/T
        
        S_v = So_M_v
        S_l = So_M_l-SV
        #Cp and Cv : Cp-Cv=R,Cv=Cp-R
        Cv_v = Cp-R
        case.Prop["Cp_v"]= Cp - dCp_V
        case.Prop["Cv_v"]= Cv_v - dCv_V
        #Save result in the case Hentalpy
        case.Prop["H"] = H_v*(case.Prop["FracVap"])+H_l*(1-case.Prop["FracVap"])
        case.Prop["H_l"] = H_l
        case.Prop["H_v"] = H_v
        case.Prop["HV"] = HV
        #Save result in the case Emtropy
        case.Prop["S"] = S_v*(case.Prop["FracVap"])+S_l*(1-case.Prop["FracVap"])
        case.Prop["S_l"] = S_l
        case.Prop["S_v"] = S_v
        
        G_l = H_l - T*S_l
        G_v = H_v - T*S_v
        
        #Save result in the case Free 
        case.Prop["G"] = G_v*(case.Prop["FracVap"])+G_l*(1-case.Prop["FracVap"])
        case.Prop["G_l"] = G_l
        case.Prop["G_v"] = G_v
        
        U_l = H_l - sum(xf*P*V_li)
        U_v = H_v - sum(yf*P*V_vi)
        
        #Save result in the case Free 
        case.Prop["U"] = U_v*(case.Prop["FracVap"])+U_l*(1-case.Prop["FracVap"])
        case.Prop["U_l"] = U_l
        case.Prop["U_v"] = U_v
        
        A_l = U_l - T*S_l
        A_v = U_v - T*S_v
        
        #Save result in the case Free 
        case.Prop["AFree"] = U_v*(case.Prop["FracVap"])+U_l*(1-case.Prop["FracVap"])
        case.Prop["AFree_l"] = A_l
        case.Prop["AFree_v"] = A_v
        
        #Hentapy and gibbs formation Energy
        case.Prop["HF"] =  sum(model["DELHF"]*x)
        case.Prop["GF"] =  sum(model["DELGF"]*x)
