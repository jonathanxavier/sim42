import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")
from ollin.Administrator.AdmOllin import Ollin
from pylab import *

RK=Ollin.AddModel("RK","RK")
S1=Ollin.AddCase("S1")
Ollin.Add(["N-BUTANE","N-PENTANE","N-HEXANE","N-HEPTANE"],"RK")
S1.SetX([1,1,1,1])
S1.T(500)

plot_x = range(5,10000,100)
plot_y0 = []
plot_y1 = []
plot_y2 = []
plot_y3 = []
Pr= []
##plot_y4 = []
##plot_y5 = []

for P in plot_x:
    
    S1.P( P ) 
    Ollin.Solve()
##    yf=S1.Get("Zvi")
    
    plot_y0.append( S1.Get("Zvi")[0])
##    plot_y1.append( S1.Get("Zli")[0] )
    plot_y2.append( S1.Get("Zvi")[1] )
    plot_y3.append( S1.Get("Zvi")[2] )
    Pr.append(P)
##    plot_y4.append( yf[4] )
##    plot_y5.append( S1.Get("FracVap") )
##    print adm.TheObj["Str"].Prop["FracVap"],adm.TheObj["Str"].Prop["T"]

plot_x = Pr
plot(plot_x,plot_y0)
##plot(plot_x,plot_y1)
plot(plot_x,plot_y2)
plot(plot_x,plot_y3)
##plot(plot_x,plot_y4)
##plot(plot_x,plot_y5)
##axis([244,300,0,1])
grid(True)
titles = RK.library
##titles.append("FracVap")
legend(titles)
title("Zv Vs P @ 500 K ")
xlabel('P (Kpa)')
ylabel('Factor de compresibilidad')
show()
