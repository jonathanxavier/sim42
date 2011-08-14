import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")

from ollin.Administrator.AdmOllin import Ollin
from ollin.Example.UOS import Stream, Valve,Heater,Flash

PR=Ollin.AddModel("PR","PR")
Ollin.Add(["METHANE","ETHANE","PROPANE","ISOBUTANE","N-BUTANE","N-PENTANE","N-HEXANE"],"PR")
Ollin.LoadConst()
S1 = Stream(PR)
S1.X([85.92,7.73,2.45,0.36,0.56,0.47,1.12])
##S1.FracVap(0.6)
S1.T(66+273.15)
S1.P(24820)
S1.Mol(455)

V1 = Valve(PR)
V1.DP = 11030

H1 = Heater(PR)
H1.DP = 1
H1.DH = 1
 
F1 = Flash(PR) 
 
S1.Connect(V1)
V1.Connect(H1)
##H1.Connect(F1)

S1.Solver()
S1.CasePrint()

V1.Solver()
V1.Out.CasePrint()

H1.Solver()
H1.Out.CasePrint()
##
##F1.Solver()
##F1.Vap.CasePrint()
