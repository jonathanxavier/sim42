# Simple heater test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE
heater = Heater.Heater()
heater
cd heater
In.Fraction
In.Fraction = .25 .25 .25 .25
In.P = 101.325
In.H = -7200
In.T
In.MoleFlow = 10
InQ.Energy = 1000000
DeltaP
DeltaP.DP = 0
In
Out
InQ

#Test the profiles
cd /
heater.T
heater.P
heater.Viscosity
heater.L_Cp
heater.V_Cp
heater.Cp
heater.VapFrac
heater.NumberSegments = 10
heater.DeltaP.DP = 10.0
heater.In.H =
heater.In.VapFrac = 0.75
heater.T
heater.P
heater.Viscosity
heater.L_Cp
heater.V_Cp
heater.Cp
heater.VapFrac
heater.MassVapFrac
heater.InQ.Energy = None
heater.In.VapFrac = 0.0
heater.Out.VapFrac = 1.0
heater.VapFrac
heater.MassVapFrac


copy /heater
paste /
/heaterClone.T
/heaterClone.In