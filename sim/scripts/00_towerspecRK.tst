# Depeopanizer test (from old Hysim manual)
units Field
$thermo = VirtualMaterials.RK
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
l.Port.P = 205
l.spec = Tower.MoleRecoverySpec()
l.spec + PROPANE
l.spec.Port.Fraction = .1

reb = Tower.EnergyFeed(1)
estT = Tower.Estimate('T')
estT.Value = 250

cd ..

/overhead = Stream.Stream_Material()
/overhead.In -> Stage_0.v.Port

/bottoms = Stream.Stream_Material()
/bottoms.In -> Stage_19.l.Port


TryToRestart = 0 # so each test starts from scratch
TryToSolve = 1  # start calculation

/overhead.Out
/bottoms.Out

cd Stage_19.l
delete spec
spec = Tower.ComponentMoleFlowSpec()
spec + PROPANE
spec.Port.MoleFlow = 10
/bottoms.Out

delete spec
Port.MassFlow = 43000
/bottoms.Out

Port.MassFlow = None
spec = Tower.ComponentMassFlowSpec()
spec + PROPANE
spec.Port.MassFlow = 450
/bottoms.Out

delete spec
spec = Tower.MassRecoverySpec()
spec + PROPANE ETHANE
spec.Port.Fraction = .1
/bottoms.Out

delete spec
spec = Tower.MoleRatioSpec()
spec + ETHANE PROPANE / ISOBUTANE n-BUTANE
spec.Port.Fraction = 0.05
/bottoms.Out

delete spec
spec = Tower.MassRatioSpec()
spec + ETHANE PROPANE / ISOBUTANE n-BUTANE
spec.Port.Fraction = 0.05
/bottoms.Out

delete spec
cd ..
spec = Tower.ReboilRatioSpec()
spec.Port = 2
/bottoms.Out
