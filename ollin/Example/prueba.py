import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")

from ollin.Administrator.AdmOllin import Ollin

PR=Ollin.AddModel("PR","RK","ANTOINE")
Ollin.Add(["ETHANE","PROPANE","N-BUTANE","N-PENTANE","N-HEXANE"],"PR")
S1=Ollin.AddCase("S1")

S1.SetX([0.05,0.15,0.25,0.20,0.35])
##S1.SetYf([ 0.09562319,0.25923795,0.33220682,0.16480774,0.1481243 ])
##S1.FracVap(0.01)
S1.T(378.404)#378.404 282.13
S1.P(101.325*10)

##Ollin.Solve()
Ollin.Solve()
Ollin.Resumen()
##print S1.Get("xf")
####adm.TheObj["S1"].Rx()
####print adm.TheObj["S1"].Get("x")
####print S1.Prop.keys()
##[ 0.00437689  0.04076249  0.16779372  0.23519212  0.55187479]
