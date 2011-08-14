import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")
from ollin.Administrator.AdmOllin import Ollin
from pylab import *

RK=Ollin.AddModel("RK","RK")
S1=Ollin.AddCase("S1")
Ollin.Add(["N-BUTANE","N-PENTANE","N-HEXANE"],"RK")
S1.SetX([1,1,1])
S1.T(322)

plot_x = range(10,1000,10)
plot_y0 = []
plot_y1 = []
plot_y2 = []
plot_y3 = []
plot_y4 = []
##plot_y5 = []
Pr = []
print plot_x
for P in plot_x:
    
    S1.P( P ) 
    Ollin.Solve()
    yf=S1.Get("Ki")
    
    plot_y0.append( yf[0] )
    plot_y1.append( yf[1] )
    plot_y2.append( yf[2] )
##    plot_y3.append( yf[3] )
##    plot_y4.append( yf[4] )
##    plot_y5.append( S1.Get("FracVap") )
    Pr.append(P)

##    print adm.TheObj["Str"].Prop["FracVap"],adm.TheObj["Str"].Prop["T"]
##print "PC",S1.Get("PC")
##print Pr
plot(Pr,plot_y0)
plot(Pr,plot_y1)
plot(Pr,plot_y2)
##plot(Pr,plot_y3)
##plot(Pr,plot_y4)
##plot(Tr,plot_y5)
##axis([244,300,0,1])
grid(True)
titles = RK.library
##titles.append("FracVap")
legend(titles)
title("Ki Vs P @ 322 K")
xlabel('P (Kpa)')
ylabel('Ki')
show()
