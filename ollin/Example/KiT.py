import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")
from ollin.Administrator.AdmOllin import Ollin
from pylab import *

RK=Ollin.AddModel("RK","RK")
S1=Ollin.AddCase("S1")
Ollin.Add(["ETHANE","PROPANE","N-BUTANE","N-PENTANE","N-HEXANE"],"RK")
S1.SetX([0.05,0.15,0.25,0.20,0.35])
S1.P(101.325*2.5)

plot_x = range(220,425,2)
plot_y0 = []
plot_y1 = []
plot_y2 = []
plot_y3 = []
plot_y4 = []
##plot_y5 = []
Tr = []
print plot_x
for T in plot_x:
    
    S1.T( T ) 
    Ollin.Solve()
    yf=S1.Get("Ki")
    
    plot_y0.append( yf[0] )
    plot_y1.append( yf[1] )
    plot_y2.append( yf[2] )
    plot_y3.append( yf[3] )
    plot_y4.append( yf[4] )
##    plot_y5.append( S1.Get("FracVap") )
    Tr.append(T)

##    print adm.TheObj["Str"].Prop["FracVap"],adm.TheObj["Str"].Prop["T"]
plot(Tr,plot_y0)
plot(Tr,plot_y1)
plot(Tr,plot_y2)
plot(Tr,plot_y3)
plot(Tr,plot_y4)
##plot(Tr,plot_y5)
##axis([244,300,0,1])
grid(True)
titles = RK.library
titles.append("FracVap")
legend(titles)
title("Ki Vs Tr @ 253.31")
xlabel('T (K)')
ylabel('Ki')
show()
