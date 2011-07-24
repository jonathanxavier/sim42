# Heat exchanger test
units SI

$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + WATER


# lets have some streams for this test
hotInlet = Stream.Stream_Material()
coldInlet = Stream.Stream_Material()
hotOutlet = Stream.Stream_Material()
coldOutlet = Stream.Stream_Material()
hotInlet2 = Stream.Stream_Material()
hotOutlet2 = Stream.Stream_Material()

cd /hotInlet.In
Fraction = 1.0
P = 101
MoleFlow = 800

cd /hotInlet2.In
Fraction = 1.0
P = 101
MoleFlow = 300

cd /coldInlet.In
Fraction = 1.0
#VapFrac = 0
P = 101
MoleFlow = 1000

cd /
exch = Heater.MultiSidedHeatExchangerOp()
exch.NumberSides = 3

cd exch
DeltaP0 = 0.0
DeltaP1 = 0.0
DeltaP2 = 0.0


cd /
coldInlet.Out -> exch.In0
exch.Out0 -> coldOutlet.In
hotInlet.Out -> exch.In1
exch.Out1 -> hotOutlet.In
hotInlet2.Out -> exch.In2
exch.Out2 -> hotOutlet2.In

exch.IsCounterCurrent1 = 0
exch.IsCounterCurrent2 = 1


#spec UA and coldInlet.T
exch.UA0_1 = 8288.42280702 #Cold with the first hot side
exch.UA0_2 = 5000.42280702  #Cold with the second hot side
exch.UA1_2 = 0.0           #Ignore heat transfer between both hot sides
hotInlet.In.T = 573.15 K
hotInlet2.In.T = 500 K
coldInlet.In.T = 413.15 K

units sim42
coldInlet.In
coldOutlet.In
hotInlet.In
hotOutlet.In
hotInlet2.In
hotOutlet2.In
exch.UA0_1


copy /
paste /
cd /RootClone
coldInlet.In
coldOutlet.In
hotInlet.In
hotOutlet.In
hotInlet2.In
hotOutlet2.In
exch.UA0_1


