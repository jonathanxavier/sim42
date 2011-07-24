#valve example
$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + METHANE
units SI

v = Valve.Valve()
v.In.T = 50
v.In.P = 7000.0
v.In.MoleFlow = 100.0
v.In.Fraction = 1.0

v.Out
v.Out.P = 500.0
v.Out
