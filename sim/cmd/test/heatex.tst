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
VapFrac = 0
P = 300
T
MoleFlow = 1000
cd /
exch = Heater.HeatExchanger()
exch
cd exch
DeltaPC = 10
DeltaPH = 50
DeltaTHO = 5 K
cd /
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

cd /
copy /exch /hotInlet /coldInlet /hotOutlet /coldOutlet
sub = Flowsheet.SubFlowsheet()
paste /sub
cd /sub

coldInlet
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.ColdSide.InQ