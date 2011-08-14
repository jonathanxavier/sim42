from ollin.pvt import MixingRules
from numpy.oldnumeric import sqrt,power
from ollin.pvt.rkzf import RKZ
from ollin.pvt.zfi import ZFI
from ollin.pvt.Fuga import CoeFugo,CoeFugM
from ollin.pvt.Flash import Flash

from ollin.pvt.eos import RK

def SRK(model,case):

    R = 0.08206 ##
    xm = case.ExtProp["x"]
    yf = case.ExtProp["yf"]
    xf = case.ExtProp["xf"]
    pv = case.ExtProp["pv"]
    FrVap = case.ExtProp["FracVap"]
    
    T = case.ExtProp["T"]
    P = case.ExtProp["P"]
    Ac = model.Const["SRK_A"]
    b_i = model.Const["RK_B"]
    W_i = model.Const["OMEGA"]
    TC_i = model.Const["TC"]
    
##    print "Ac",Ac,b_i
    
    fwi = 0.48+0.1574*W_i-0.176*power(W_i,2)
    Tr_i = T /TC_i
    
##    print Tr_i
    AlphaT = power(  ( 1+fwi*(1-sqrt(Tr_i) ) ),2)

    a_i = Ac * AlphaT
    
    A_i = ( a_i * P)/ pow( R * T,2)
    B_i = ( b_i * P )/( R * T)    
##    print "AiBi",A_i,B_i

    Zl_i = SRK.ZL(A_i,B_i)
    Zv_i = SRK.ZG(A_i,B_i)


    print "z", Zl_i, Zv_i

    CoeFugo_v = CoeFugo(Zv_i, A_i, B_i )
    CoeFugo_l = CoeFugo(Zl_i, A_i, B_i )

    #print CoeFugo_v/CoeFugo_l
    
    for i in range(3):

        A_vi = MixingRules.MolarK2( yf, A_i, k=0.5)
        B_vi = MixingRules.Molar( yf, B_i) 
            
        A_li = MixingRules.MolarK2( xf, A_i,k=0.5)
        B_li = MixingRules.Molar( xf,B_i) 
        
        B_v = MixingRules.Molar( yf, B_i)
        A_v = MixingRules.MolarK( yf, A_i, k=0.5)
        
        B_l = MixingRules.Molar( xf, B_i)
        A_l = MixingRules.MolarK( xf, A_i, k=0.5)


        Z_v = SRK.ZG(A_v,B_v)
        Z_l = SRK.ZL(A_l,B_l)
     
        CoeFugM_v = SRK.FugMix(Z_v, A_i,B_i,A_v,B_v)
        CoeFugM_l = SRK.FugMix(Z_l, A_i,B_i,A_l,B_l)

        fi = P*CoeFugM_v*yf
        
        ki = CoeFugM_l/CoeFugM_v
        #print xm
        FrVap, xf, yf = Flash(ki, xm)
        Z = FrVap*Z_v + (1- FrVap)* Z_l
        print CoeFugM_v,"\n",ki,"\n",FrVap,"\n",xf,"\n",yf,"\n",CoeFugM_l,"\n",Z_v,Z_l
