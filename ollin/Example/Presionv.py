from ollin.Administrator.AdmOllin import Ollin
from ollin.Tools.tools import lagrange
from pylab import *

RK=Ollin.AddModel("RK","PR")
S1=Ollin.AddCase("S1")
Ollin.Add(["N-HEPTANE"],"RK")

Ti = range(300,450,10)
S1.SetX([1,])
Ppi=[]
Ppv=[]
for T in Ti:
    df=[]
    P= []
    S1.P(101.325)
    S1.T(T)
    Ollin.Solve()
    Pvi=S1.Get("PreVap")[0]
    Ppi.append(Pvi)
    fl=S1.Get("fl_i")[0]
    fv=S1.Get("fv_i")[0]
    P.append(S1.Get("P"))
    df.append(fl-fv)
    
    S1.P(Pvi)
    Ollin.Solve()
    fl=S1.Get("fl_i")[0]
    fv=S1.Get("fv_i")[0]
    P.append(S1.Get("P"))
    df.append(fl-fv)
    E = fl-fv
    while abs(E)>1e-3: 
        Pi = lagrange(df,P,0)
        print Pi
        S1.P(Pi)
        Ollin.Solve()
        fl=S1.Get("fl_i")[0]
        fv=S1.Get("fv_i")[0]
        P.append(S1.Get("P"))
        E = fl-fv
        df.append(E)
    
    Ppv.append(Pi)



plot(Ti,Ppi)
plot(Ti,Ppv)
grid(True)
titles = ["Antoine","Peng-Robinson"]
legend(titles)
title("Presion de vapor de N-Heptano")
ylabel('P (Kpa)')
xlabel('Temperatura (K)')
show()
