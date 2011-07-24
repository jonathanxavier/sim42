#adiabatic mixer example
$thermo = VirtualMaterials.PSRK
/ -> $thermo
thermo + ETHANOL WATER
units SI

m = Mixer.Mixer()

m.In0.P = 1 atm
m.In0.T = 25 C
m.In0.MoleFlow = 1.0
m.In0.Fraction = 1.0 0.0

m.In1.P = 1 atm
m.In1.T = 25 C
m.In1.MoleFlow = 1.0
m.In1.Fraction = 0.0 1.0

m.Out

#Play with pressures
m.In0.P = 100
m.In1.P = 80
m.Out.P

m.In0.P = 100
m.In1.P = 110
m.Out.P

m.In0.P = 
m.In1.P = 110
m.Out.P = 100
m.In0.P

m.Out.P = 80
m.In0.P



/m.CalcPressureMode = DontCalculate
/m.In0.P = 130
/m.In0.P = 100
/m.In0.P = 70

/m.CalcPressureMode = LowestPInOutlet
/m.Out.P = 
#A problem in the solver does not clear the consistency error properly because of some
#stored results in the flash. This will be addressed later
Ignored = 1 ; Ignored = None

/m.CalcPressureMode = AllPEqual
/m.In1.P = 
/m.In0.P = 
/m.Out.P = 100
/m.Out.P = 
/m.In1.P = 120
copy /m
paste /
/m.Out
/mClone.Out

