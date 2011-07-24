# Heat exchanger test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE ISOBUTANE n-BUTANE n-PENTANE WATER

# lets have some streams for this test
coldInlet = Stream.Stream_Material()
hotInlet = Stream.Stream_Material()

# hot side will use steam property package
hotInlet.thermo = VirtualMaterials.Steam95
hotInlet.thermo + water

# create hot outlet and assign the hot inlet thermo
hotOutlet = Stream.Stream_Material()
hotOutlet.thermo = hotInlet.thermo
cd hotInlet.In
T = 200
P = 150
Fraction = 1
MoleFlow = 500

cd /
coldOutlet = Stream.Stream_Material()
cd /coldInlet.In
Fraction
Fraction = .75 15 .08 .02 0
VapFrac = 0
P = 300
T =
MoleFlow = 1000
cd /
exch = Heater.HeatExchanger()
exch
cd exch
DeltaPC = 10
DeltaPH = 50
DeltaTHO = 5 K
cd /

# the hot side subunit of exchanger has to have the steam thermo
exch.HotSide.thermo = hotInlet.thermo

#connect things
coldInlet.Out -> exch.InC
exch.OutC -> coldOutlet.In
hotInlet.Out -> exch.InH
exch.OutH.T
exch.OutH -> hotOutlet.In

# results
coldInlet
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.ColdSide.InQ
