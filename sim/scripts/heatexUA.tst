# Heat exchanger test
units SI

$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE ISOBUTANE n-BUTANE n-PENTANE

# lets have some streams for this test
hotInlet = Stream.Stream_Material()
coldInlet = Stream.Stream_Material()
hotOutlet = Stream.Stream_Material()
coldOutlet = Stream.Stream_Material()

cd hotInlet.In
Fraction = .25 .25 .25 .25
T = 375 K
P = 500
MoleFlow = 800

cd /coldInlet.In
Fraction
Fraction = .95 0 .05 0
P = 300
MoleFlow = 1000

cd /
exch = Heater.HeatExchangerUA()
exch
cd exch
DeltaP1 = 10
DeltaP0 = 50


cd /
coldInlet.Out -> exch.In1
exch.Out1 -> coldOutlet.In
hotInlet.Out -> exch.In0
exch.Out0 -> hotOutlet.In


#spec UA and coldInlet.T
exch.UA0_1 = 52710.6781154
coldInlet.In.T = -8 C

coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.UA0_1


###See if it forgets
exch.UA0_1.UA =
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out


#Spec UA again nowspect coldOutlet.T
exch.UA0_1 = 52710.6781154
coldInlet.In.T =
coldOutlet.In.T = 80 C
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.UA0_1







