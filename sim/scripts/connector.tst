# Cross connecter thermo test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE ISOBUTANE n-BUTANE n-PENTANE WATER
# lets have some streams for this test
coldInlet = Stream.Stream_Material()
hotInlet = Stream.Stream_Material()

cd hotInlet.In
T = 200
P = 150
Fraction = .01 .02 .01 0 1
MoleFlow = 500

cd /
cd /coldInlet.In
Fraction
Fraction = .75 15 .08 .02 0
VapFrac = 0
P = 300
T =
MoleFlow = 1000
cd /

coldOutlet = Stream.Stream_Material()

exch = Heater.HeatExchanger()
exch
cd exch
DeltaPC = 10
DeltaPH = 50
DeltaTHO = 5 K
cd /

# hot side will use steam property package
$thermo1 = VirtualMaterials.Steam95
exch.HotSide -> $thermo1
exch.HotSide.thermo1 + water

# create hot outlet and assign the hot inlet thermo
hotOutlet = Stream.Stream_Material()
hotOutlet -> $thermo1

# create CrossConnector
xc = CrossConnector.CrossConnector()
hotInlet.Out -> xc.In
xc.In
xc.Out

#connect things
coldInlet.Out -> exch.InC
exch.OutC -> coldOutlet.In
xc.Out -> exch.InH
exch.OutH.T
exch.OutH -> hotOutlet.In

# results
coldInlet
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.ColdSide.InQ

# one more stream and connector
hotOut2 = Stream.Stream_Material()
xc2 = CrossConnector.CrossConnector()
xc2.Out -> hotOut2.In
hotOut2.In

copy /
paste /
cd /RootClone
coldInlet
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.ColdSide.InQ

