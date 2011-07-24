# Depropanizer test (from old Hysim manual)
units SI
thermo = VirtualMaterials.Peng-Robinson
thermo + propane isobutane n-butane isopentane n-pentane
thermo + n-hexane n-heptane n-octane
thermo + n-nonane n-decane
thermo + water

stab = Tower.Tower()
stab.Stage_0 + 10  # twelve stages
stab.LiquidPhases = 2

cd stab.Stage_0

l = Tower.LiquidDraw()
l.Port.P = 1000

cond = Tower.EnergyFeed(0)

wd = Tower.WaterDraw()

estT = Tower.Estimate('T')
estT.Value = 25

reflux = Tower.StageSpecification('Reflux')
reflux.Value = 2

cd ../Stage_5
f = Tower.Feed()
f.Port.T = 50
f.Port.P = 2000
f.Port.MoleFlow = 1000
f.Port.Fraction = .1702 .1473 .1132 .1166 .1066 .0963 .0829 .0694 .0558 .0417 .005
f.Port

cd ../Stage_11
l = Tower.LiquidDraw()
l.Port.P = 1100
l.Port.Fraction.n-BUTANE = .02

reb = Tower.EnergyFeed(1)
estT = Tower.Estimate('T')
estT.Value = 100

cd ..

/overhead = Stream.Stream_Material()
/overhead.In -> Stage_0.l.Port

/bottoms = Stream.Stream_Material()
/bottoms.In -> Stage_11.l.Port


/stab.MaxOuterLoops = 40
TryToSolve = 1  # start calculation

/overhead.Out
/bottoms.Out

copy /stab /overhead /bottoms
paste /
/overheadClone.Out
/bottomsClone.Out

