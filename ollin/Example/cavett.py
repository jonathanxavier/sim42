from ollin.Administrator.AdmOllin import Ollin
from ollin.Example.UOS import Stream, Valve,Heater,Flash

PR=Ollin.AddModel("PR","PR")
Ollin.Add(["METHANE","ETHANE","PROPANE","ISOBUTANE","N-BUTANE","N-PENTANE","N-HEXANE","N-HEPTANE","N-OCTANE","N-NONANE","N-DECANE","N-UNDECENE"],"PR")
Ollin.LoadConst()
S1 = Stream(PR)
S1.X([2995.5,2395.5,2291,2991,1539.9,790.4,1129.9,1764.7,1844.5,1699,831.7,1214.5])
####S1.FracVap(0.6)
S1.T(322)
S1.P(1861)
S1.Mol(455)

V1 = Valve(PR)
V1.DP = 50

H1 = Heater(PR)
H1.DP = 1
H1.DT = 1
 
F1 = Flash(PR) 
 
S1.Connect(V1)
V1.Connect(F1)
H1.Connect(F1)
##
S1.Solver()
S1.CasePrint()

V1.Solver()
V1.Out.CasePrint()

##H1.Solver()
##H1.Out.CasePrint()
F1.Solver()
F1.Liq.CasePrint()

F1.Solver()
F1.Vap.CasePrint()
