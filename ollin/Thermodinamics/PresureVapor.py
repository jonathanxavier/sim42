##This fuction contain the Presuse Vapor Model}
##from ollin.pvt import antoine
from numpy.oldnumeric import array,exp,log,power,absolute

Equation =  {}

class Antoine:

    def __init__(self):
        self.Name = "Antoine Equation"
        self.TagsOfConst = ["ANT_A","ANT_B","ANT_C"]
        self.Factor = 0.13332236
    
    def NeedVars(self):
        return self.TagsOfConst

    def P(self,T,m):
        logP = m["ANT_A"]-(m["ANT_B"]/ ( T + m["ANT_C"] ))
        for i in range(len(logP)):
            if logP[i]<-36:
                logP[i]= -18.420680743952367
        return array( exp( logP )*self.Factor)
    
    def T(self,P,m):
        return array( m["ANT_B"] / (m["ANT_A"] - log(P/self.Factor)) - m["ANT_C"])


Equation ["ANTOINE"] = Antoine


class Harlacher:

    def __init__(self):
        self.Name = "Harlacher Equation"
        self.TagsOfConst = ["HAR_A","HAR_B","HAR_C","HAR_D"]
        self.Factor = 0.13332236
    
    def NeedVars(self):
        return self.TagsOfConst

    def P(self,T,m):
        P_j= array( exp( m["HAR_A"]+m["HAR_B"] / T  + m["HAR_C"]*log(T) ) )
        P = []
        T1 = log(T)
        T2 = power(T,2)
##        print m["HAR_D"]
        for j in range(len(m["HAR_A"])):
            P_r = P_j[j]
            i= 1
##            print j,P_r,T2
            while i<=20:
                P_i = m["HAR_A"][j]+m["HAR_B"][j]/ T  + m["HAR_C"][j]*T1 + m["HAR_D"][j]*P_r/T2
##                print P_i
                P_i = exp(P_i)
##                print P_i*0.13332236
                i +=1
                if abs(P_i-P_r)<=1:
                    P.append(P_i)
                    break
                P_r = P_i
                
        return array(P) * self.Factor

    def T(self,P,m):
        P= P/self.Factor
        T = []
        T_j = array( m["HAR_B"] /( log(P)-m["HAR_A"] )  )
##        print m["HAR_D"]
        for j in range(len(m["HAR_A"])):
            T_r = T_j[j]
            i= 1
            while i<=20:
            
                fP_i = log(P_i) - exp( m["HAR_A"][j]+m["HAR_B"][j] / ( T_r ) + m["HAR_C"][j]*log(T_r) + m["HAR_D"][j]*P/power(T_r,2) ) 
                dP_i = m["HAR_C"][j]/T_r- m["HAR_B"][j]/power(T_r,2) - 2*m["HAR_D"][j]*P/power(T_r,3)
                i +=1
                if abs(fP_i)<=1e-3:
                    T.append(T_r)
                    break
                T = T-fP_i/dPi 
        return T
        
Equation ["HARLACHER"] = Harlacher
