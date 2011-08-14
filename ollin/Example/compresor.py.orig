import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")

from ollin.Administrator.AdmOllin import Ollin
from ollin.Example.UOS import Stream, Valve,Heater,Flash

PR=Ollin.AddModel("PR","PR")
Ollin.Add(["METHANE","ETHANE","PROPANE","ISOBUTANE","N-BUTANE","N-PENTANE","N-HEXANE","N-HEPTANE"],"PR")
Ollin.LoadConst()
S1 = Stream(PR)
S1.X([14520,9070,7260,770,2810,950+1630,1540,3180])
##S1.FracVap(0.9)
S1.T(273.15+40)
S1.P(500)
S1.Mol(455)

V1 = Valve(PR)
V1.DP = 11030

H1 = Heater(PR)
H1.DP = 1
H1.DH = 1
 
F1 = Flash(PR) 
 
S1.Connect(F1)

##
##V1.Connect(H1)
##H1.Connect(F1)

S1.Solver()
F1.Solver()
S1.Case.CasePrint()
S1.Case.XPrint()

S1.CasePrint()
F1.Liq.CasePrint()
F1.Vap.CasePrint()

V1.Solver()
##V1.Out.CasePrint()

##H1.Solver()
##H1.Out.CasePrint()
##
##F1.Solver()
##F1.Vap.CasePrint()
