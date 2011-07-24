#splitter example
$thermo = VirtualMaterials.NRTL/Ideal/HC
/ -> $thermo
thermo + ETHANOL WATER
units SI
s = Split.Splitter()
s.In.P = 100.0
s.In.T = 25.0
s.In
s.Out0.MoleFlow = 50.0
s.Out1.MoleFlow = 50.0
s.Out1.Fraction = 1.0 1.0
s.In
cd /s
/s.Out0.MoleFlow = 
/s.FlowFraction1.Fraction = .3
Out0
/s.FlowFraction1.Fraction = 
/s.FlowFraction0.Fraction = .2
Out0
/s.FlowFraction0.Fraction = 3
In
Out0
/s.FlowFraction0.Fraction = .1
/s.Out1.MoleFlow = 
/s.In.MoleFlow = 100
Out1
cd /s.NumberStreamsOut
/s.NumberStreamsOut = 4
cd /s.FlowFraction1
cd /s
/s.Out2.MassFlow = 30
/s.FlowFraction1.Fraction = .3
FlowFraction3
Out1
cd /s.NumberStreamsOut
/s.NumberStreamsOut = 2
cd /s
/s.FlowFraction0.Fraction = 

copy /
paste /
/s.Out0
/RootClone.s.Out0