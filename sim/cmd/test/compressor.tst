# Simple compressor test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + METHANE ETHANE PROPANE n-BUTANE
comp = Compressor.Compressor()
comp
cd comp
In.Fraction = .4 .3 .2 .1
In.P = 101.325
In.T = 20
In.MoleFlow = 100
Out.P = 400
Efficiency = .8
In
Out
InQ
Efficiency = .5
Out
InQ
# ideal efficiency
Efficiency = 1.
Out
InQ

# add expander
cd /
expander = Compressor.Expander()
comp.Out -> expander.In
expander.Efficiency = 1.
expander.Out.P = 101.325
expander.OutQ
expander.Out
comp.Efficiency = .75
expander.Efficiency = .75
comp.InQ
comp.Out
expander.OutQ
expander.Out
