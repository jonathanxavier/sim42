#material stream example
$thermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $thermo
thermo + WATER TRIETHYLENE_GLYCOL

#generate WATER/TEG bubble temperature curve
units Field

s = Stream.Stream_Material()
s.In.P = 1 atm
s.In.VapFrac = 0.0
s.In.Fraction = 0.0 1.0
s.Out.T
s.In.Fraction = 0.1 0.9
s.Out.T
s.In.Fraction = 0.2 0.8
s.Out.T
s.In.Fraction = 0.3 0.7
s.Out.T
s.In.Fraction = 0.4 0.6
s.Out.T
s.In.Fraction = 0.5 0.5
s.Out.T
s.In.Fraction = 0.6 0.4
s.Out.T
s.In.Fraction = 0.7 0.3
s.Out.T
s.In.Fraction = 0.8 0.2
s.Out.T
s.In.Fraction = 0.9 0.1
s.Out.T
s.In.Fraction = 1.0 0.0
s.Out.T