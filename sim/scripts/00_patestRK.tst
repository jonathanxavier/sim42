# Depeopanizer test (from old Hysim manual)
units SI
$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + propane isobutane n-butane isopentane n-pentane
thermo + n-hexane n-heptane n-octane
thermo + n-nonane n-decane

stab = Tower.Tower()
stab.Stage_0 + 10  # twelve stages
stab.LiquidPhases = 2

cd stab.Stage_0

l = Tower.LiquidDraw()
l.Port.P = 1000

cond = Tower.EnergyFeed(0)

estT = Tower.Estimate('T')
estT.Value = 25

reflux = Tower.StageSpecification('Reflux')
reflux.Value = 2

cd ../Stage_5
f = Tower.Feed()
f.Port.T = 50
f.Port.P = 2000
f.Port.MoleFlow = 1000
f.Port.Fraction = .1702 .1473 .1132 .1166 .1066 .0963 .0829 .0694 .0558 .0417
f.Port

cd ../Stage_11
l = Tower.LiquidDraw()
l.Port.P = 1100
l.Port.Fraction.n-BUTANE = .02

reb = Tower.EnergyFeed(1)
estT = Tower.Estimate('T')
estT.Value = 100

cd ../Stage_9
pa_source = Tower.VapourDraw()
pa_source.Port.MoleFlow = 200

cd ../Stage_7
pa_dest = Tower.Feed()

cd ..
Stage_9.pa_source.Port -> Stage_7.pa_dest.Port

/overhead = Stream.Stream_Material()
/overhead.In -> Stage_0.l.Port

/bottoms = Stream.Stream_Material()
/bottoms.In -> Stage_11.l.Port



TryToSolve = 1  # start calculation

/overhead.Out
/bottoms.Out
L
V
T

# remove feed and draw and install VapourPumpAround object
TryToSolve = 0
delete Stage_9.pa_source
delete Stage_7.pa_dest

Stage_9.pa = Tower.VapourPumpAround(7)
Stage_7.pa_paR.Port.MoleFlow = 200
Stage_7.pa_paQ.Port.Energy = 0
TryToSolve = 1

/overhead.Out
/bottoms.Out
Stage_7.pa_paR.Port
L
V
T

# delete the pump around
delete Stage_9.pa

# add liquid pump down
Stage_7.pd = Tower.LiquidPumpAround(10)
Stage_7.pd.Port.MoleFlow = 300
Stage_10.pd_paQ.Port.Energy = 1000000
/overhead.Out
/bottoms.Out
Stage_10.pd_paR.Port
L
V
T

