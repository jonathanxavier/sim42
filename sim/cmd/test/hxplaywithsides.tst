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


cd hotInlet.In
Fraction = 1.0
T = 300 C
P = 101
MoleFlow = 800


cd /coldInlet.In
Fraction
Fraction = 1.0
#VapFrac = 0
P = 101
MoleFlow = 1000

cd /
exch = Heater.MultiSidedHeatExchangerOp()
exch

cd exch
DeltaP0 = 0.0
DeltaP1 = 0.0

cd /
coldInlet.Out -> exch.In1
exch.Out1 -> coldOutlet.In
hotInlet.Out -> exch.In0
exch.Out0 -> hotOutlet.In


#spec UA and coldInlet.T
exch.UA0_1 = 8288.42280702
coldInlet.In.T = 413.15 K

units sim42
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.UA0_1

exch.IsCounterCurrent1 = 0

coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.UA0_1

#This should not be accepted
exch.IsCounterCurrent0 = 1
exch.IsCounterCurrent0
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out

exch.ReferenceSide = 1
exch.ReferenceSide
exch.IsCounterCurrent0
exch.IsCounterCurrent1

exch.IsCounterCurrent0 = 1
exch.IsCounterCurrent0
exch.IsCounterCurrent1

exch.ReferenceSide = 0
exch.ReferenceSide
exch.IsCounterCurrent0
exch.IsCounterCurrent1

exch.NumberSides = 5
exch.ReferenceSide = 4
exch.ReferenceSide
exch.IsCounterCurrent0
exch.IsCounterCurrent1
exch.IsCounterCurrent2
exch.IsCounterCurrent3
exch.IsCounterCurrent4

exch.IsCounterCurrent0 = 1
exch.IsCounterCurrent3 = 1
exch.IsCounterCurrent0
exch.IsCounterCurrent1
exch.IsCounterCurrent2
exch.IsCounterCurrent3
exch.IsCounterCurrent4


exch.NumberSides = 3
exch.ReferenceSide
exch.IsCounterCurrent0
exch.IsCounterCurrent1
exch.IsCounterCurrent2
exch.IsCounterCurrent3
exch.IsCounterCurrent4

hold
#Reconnect to different sides
coldInlet.Out -> exch.In0
exch.Out0 -> coldOutlet.In
hotInlet.Out -> exch.In1
exch.Out1 -> hotOutlet.In
go

coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.UA0_1


exch.NumberSegments = 3
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.UA0_1

exch.NumberSides = 2
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.UA0_1

copy /
paste /
cd /Rootclone
coldInlet.Out
coldOutlet.Out
hotInlet.Out
hotOutlet.Out
exch.UA0_1
