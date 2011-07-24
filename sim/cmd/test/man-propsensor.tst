#Property Sensor Example
#generate a table of enthalpy versus molar fractions
$thermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $thermo
thermo + WATER TRIETHYLENE_GLYCOL

#generate WATER/TEG bubble temperature curve
units Field

s = Stream.Stream_Material()
s.In.P = 1 atm
s.In.VapFrac = 0.0

ps = Sensor.PropertySensor()
s.Out -> ps.In
ps.SignalType = H

#generate enthalpy composition curve
s.In.Fraction = 0.0 1.0
ps.Signal
s.In.Fraction = 0.1 0.9
ps.Signal
s.In.Fraction = 0.2 0.8
ps.Signal
s.In.Fraction = 0.3 0.7
ps.Signal
s.In.Fraction = 0.4 0.6
ps.Signal
s.In.Fraction = 0.5 0.5
ps.Signal
s.In.Fraction = 0.6 0.4
ps.Signal
s.In.Fraction = 0.7 0.3
ps.Signal
s.In.Fraction = 0.8 0.2
ps.Signal
s.In.Fraction = 0.9 0.1
ps.Signal
s.In.Fraction = 1.0 0.0
ps.Signal

copy /
paste /
/RootClone.ps.Signal