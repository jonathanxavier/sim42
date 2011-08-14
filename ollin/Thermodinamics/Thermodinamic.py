from numpy.oldnumeric import log
from ollin.Thermodinamics.Constans import T_ref

class Thermo:

    def __init__(self):
         self.TagsOfConst = ["CP_A","CP_B","CP_C","CP_D","HV","TB","DELHF","DELGF"]

    def NeedVars(self):
        return self.TagsOfConst
    
    def CpG(self,a,b,c,d,T):
        """
        This Module Calc
        Cp for Gas"""
        Cp_temp = a + b*T + c*pow( T,2 )+ d*pow( T,3 )
        return Cp_temp
        
    
    def Enthalpy(self,a,b,c,d,T):
        H0 = a*T + b*pow( T,2 )/2 + c*pow( T,3 )/3 +d*pow( T,4 )/4
##        H_std = a*T_ref + b*pow( T_ref,2 )/2 + c*pow( T_ref,3 )/3 +d*pow( T_ref,4 )/4
        return H0
    
    def Entropy(self,a,b,c,d,T):
        S0 = a*log(T) + b*(T-1) + c* ( pow( T,2 )-1 )/2 +d*( pow( T,3 )-1 )/3
##        S_std = a*log(T_ref) + b*(T_ref ) + c* ( pow( T_ref,2 ) )/2 +d*( pow( T_ref,3 ) )/3
        return S0
    
    def Calc(self,a,b,c,d,T,R):
        
        Cp = self.CpG(a,b,c,d,T)
        H = self.Enthalpy(a,b,c,d,T)
        S = self.Entropy(a,b,c,d,T)
        
        return (Cp, H, S)
