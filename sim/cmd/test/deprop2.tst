# Depeopanizer test with some changes
units Field
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + Methane Ethane PROPANE
thermo + ISOBUTANE n-BUTANE ISOPENTANE n-PENTANE n-Hexane
thermo + n-Heptane n-Octane

deprop = Tower.Tower()
deprop.Stage_0 + 18  # twenty stages`

cd deprop.Stage_0

v = Tower.VapourDraw()
v.Port.P = 200
v.Port.Fraction.ISOBUTANE = .01

cond = Tower.EnergyFeed(0)
estT = Tower.Estimate('T')
estT.Value = 25

cd ../Stage_9
f = Tower.Feed()
f.Port.T = 50
f.Port.P = 480
f.Port.MoleFlow = 1000
f.Port.Fraction = .1702 .1473 .1132 .1166 .1066 .0963 .0829 .0694 .0558 .0417
f.Port

cd ../Stage_19
l = Tower.LiquidDraw()

l.c3flow = Tower.ComponentMoleFlowSpec()
l.c3flow + PROPANE 
l.c3flow.Port = 12

reb = Tower.EnergyFeed(1)
#reb.Port.Energy = 8.42e6
estT = Tower.Estimate('T')
estT.Value = 250

cd ..

/overhead = Stream.Stream_Material()
/overhead.In -> Stage_0.v.Port

/bottoms = Stream.Stream_Material()
/bottoms.In -> Stage_19.l.Port



TryToSolve = 1  # start calculation

/overhead.Out
/bottoms.Out

cd Stage_19
delete l.c3flow

c = Tower.InternalLiquidClone()
c.Port.T = 255

/overhead.Out
/bottoms.Out

c.Port.T = None
c.c3spec = Tower.MassFractionSpec()
c.c3spec + PROPANE
c.c3spec.Port = .02

/overhead.Out
/bottoms.Out

#Now test TriggerSolve
cd /
deprop.TriggerSolve = 1
deprop.TryToSolve = 0


#Lets trigger a solve
deprop.TriggerSolve = 1
deprop.TriggerSolve
deprop.TryToSolve


#Lets change a spec
deprop.Stage_19.c.c3spec.Port = 0.01

#Everything is forgotten. trigger a solve
deprop.TriggerSolve = 1
deprop.Stage_19.c.c3spec.Port = None
deprop.TriggerSolve = 1
deprop.Stage_19.c.c3spec.Port = 0.02
deprop.TryToSolve = 1









