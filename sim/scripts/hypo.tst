$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + methane water 'Carbon dioxide'

thermo.hypo1 = HypoCompound '''
NormalBoilingPoint = 100 C
MolecularWeight =  108.0
LiquidDensity@298 = 880.0 kg/m3
'''
thermo.hypo2 = HypoCompound '''
NormalBoilingPoint = 373.15
MolecularWeight =  18
LiquidDensity@298 = 980.0
'''
thermo.hypo1*

strm = Stream.Stream_Material()
strm.In.Fraction = 0.1 0.2 0.3 0.4 0.0 
strm.In.P = 100
strm.In.T = 300
strm.In

# move methane last
thermo.METHANE >> $
strm.In

# move hypo1 first
thermo.hypo1* >> WATER
strm.In

copy /strm
paste /
/strmClone.Out