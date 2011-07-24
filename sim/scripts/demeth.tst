# Demethanizer test (from old Hysim manual)
units Field
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + Nitrogen Carbon_Dioxide Methane Ethane PROPANE
thermo + ISOBUTANE n-BUTANE ISOPENTANE n-PENTANE n-Hexane

feed = Stream.Stream_Material()
feed.In.Fraction = 
feed.In.T = -135.5506
feed.In.P = 335
feed.In.MoleFlow = 21.2984
feed.In.Fraction = .0047 .0037 .7650 .1379 .0594 .0115 .0090 .0046 .0028 .0014

demeth = Tower.Tower()
demeth.Stage_0
demeth.Stage_0 + 4  # just six stages`

cd demeth.Stage_0

f = Tower.Feed()
f.Port.T = -142.2855
f.Port.P = 330
f.Port.MoleFlow = 6.1343
f.Port.Fraction = .0034 .0051 .7886 .1678 .0310 .0025 .0013 .0003 .0001 0.0

v = Tower.VapourDraw()
v.Port.P = 330
#v.Port.MoleFlow = 21.7  # overhead flow spec
v.estF = Tower.Estimate('MoleFlow')
v.estF.Value = 22
#estT = Tower.Estimate('T')
#estT.Value = -120

cd ../Stage_1
f = Tower.Feed()
f.Port -> /feed.Out

cd ../Stage_5
l = Tower.LiquidDraw()
l.Port.P = 335
reb = Tower.EnergyFeed(1)
#reb.Port.Energy = 0.065e6
l.Port.Fraction.METHANE = 0.01

estT = Tower.Estimate('T')
estT.Value = 0

cd ..

/overhead = Stream.Stream_Material()
/overhead.In -> Stage_0.v.Port

/bottoms = Stream.Stream_Material()
/bottoms.In -> Stage_5.l.Port

TryToSolve = 1  # start calculation - turned off by default

/overhead.Out
/bottoms.Out


