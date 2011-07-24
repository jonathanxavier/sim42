# Component Splitter test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE
f = Stream.Stream_Material()
cd f.In
Fraction = .4 .3 .2 .1
T = 0 C
P = 101.325
MoleFlow = 10
cd /

s = ComponentSplitter.SimpleComponentSplitter()
s.Splits = 1.0 .8 .3 0.0
s.Splits

f.Out -> s.In
s.Out0
s.Out1

f.Out ->
s.Out0 -> f.In
s.In   # doesn't work because fo the zero split
s.Splits = 1.0 .8 .3 .01
s.In

f.In ->
s.Out1 -> f.In
s.In # now the problem is the 1.0
s.Splits.PROPANE_Split = .99
s.In
s

thermo + n-Hexane
s.In
f.In.Fraction = .4 .3 .15 .1 .05
s.Splits.n-HEXANE_Split = .03

s.In

delete s
s = ComponentSplitter.ComponentSplitter()
s.Splits = .99 .8 .5 .3 .1
f.Out -> s.In0
s.Out0

s.Out0.VapFrac = 1
s.Out0.P = 400

s.Out1.VapFrac = 0
s.Out1.P = 400

s.InQ0

thermo - n-HEXANE
s.In0
s.Out1
s.InQ0



copy /f /s
paste /
sClone.In0
sClone.Out1
sClone.InQ0