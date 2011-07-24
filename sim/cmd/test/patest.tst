# Depeopanizer test (from old Hysim manual)
units SI
$thermo = VirtualMaterials.Peng-Robinson
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

#Create some pump around variables
cd /stab.Stage_7.pd
PADeltaT = Tower.PumpAroundDTSpec()
cd PADeltaT
cd /stab.Stage_7.pd
PAReturnT = Tower.PumpAroundReturnTSpec()
cd PAReturnT
cd /stab.Stage_7.pd
PAReturnCv = Tower.PumpAroundReturnPropSpec("Cv")
cd PAReturnCv
cd /stab
TryToSolve = 0
TryToRestart = 0
/stab.EnergyFeed_10_pd_paQ.Energy = 
TryToSolve = 1
/stab.Variable_7_PAReturnT.T = 54.53
L
V
T
/stab.Variable_7_PAReturnT.T = 
/stab.Variable_7_PADeltaT.DT = 60
L
V
T
/stab.Variable_7_PADeltaT.DT = 
/stab.Stage_10.pd_paQ.Port.Energy = 1000000


#lets see if it balances when using efficiencies
/bal = Balance.BalanceOp()
/bal.NumberStreamsInMat = 1
/bal.NumberStreamsOutMat = 3
/bal.BalanceType = 2


cd /
feed = Stream.Stream_Material()
cd feed
/feed.Out -> /stab.Feed_5_f
CloneOut = Stream.ClonePort(0)
/feed.CloneOut -> /bal.In0


cd /overhead
CloneIn = Stream.ClonePort()
/overhead.CloneIn -> /bal.Out0

cd /bottoms
CloneIn = Stream.ClonePort()
/bottoms.CloneIn -> /bal.Out1

/bal.Out2

/stab.TryLastConverged = 1
/stab.Efficiencies = 0.9
/bal.Out2

/stab.Efficiencies = 0.8
/bal.Out2

/stab.Efficiencies = 1.0
/stab.TryLastConverged = 0


#Now play with vol fracs
/stab.TryToRestart = 1
cd /stab.Stage_11.l
VolFracs = Tower.VolFractionSpec()
cd VolFracs
. +  n-HEPTANE n-OCTANE n-NONANE
cd /stab

cd /stab.Stage_11.l
StdLiqVolFlows = Tower.ComponentStdVolFlowSpec()
cd StdLiqVolFlows
. +  n-HEXANE n-HEPTANE n-OCTANE n-NONANE
cd /stab.Stage_11.l
StdLiqVolRecovery = Tower.StdVolRecoverySpec()
cd StdLiqVolRecovery
. +  n-PENTANE n-HEXANE n-HEPTANE n-OCTANE n-NONANE
. -  n-PENTANE n-HEXANE n-HEPTANE n-OCTANE n-NONANE
. +  n-PENTANE n-HEXANE n-HEPTANE
. -  n-PENTANE n-HEXANE n-HEPTANE


cd /stab.Stage_11.l
StdLiqVolRatio = Tower.StdVolRatioSpec()
cd StdLiqVolRatio
. +  n-BUTANE ISOPENTANE n-PENTANE n-HEXANE /  n-PENTANE n-HEXANE n-HEPTANE n-OCTANE
. -  n-BUTANE ISOPENTANE n-PENTANE n-HEXANE / n-PENTANE n-HEXANE n-HEPTANE n-OCTANE / 
. +  n-BUTANE ISOPENTANE n-PENTANE n-HEXANE / 
. -  n-BUTANE ISOPENTANE n-PENTANE n-HEXANE / n-HEXANE n-HEPTANE n-OCTANE / 
. +  n-BUTANE ISOPENTANE n-PENTANE n-HEXANE /  n-HEXANE n-HEPTANE n-OCTANE

cd /stab
/stab.Variable_0_reflux.Generic = 
/stab.Variable_11_StdLiqVolRatio.Fraction = 0.986
TryToRestart = 0
L
V
T
/stab.Variable_11_StdLiqVolRatio.Fraction = 
/stab.Variable_0_reflux.Generic = 2
L
V
T



#Now delete try deleting the stages with the pump around

#The following should not work
#A stage with a feed from a pump around can not be deleted
/stab.Stage_9 - 1
/stab.Stage_7 - 3

#Finally do it right
/stab.Stage_6 - 4


copy /
paste /
/RootClone.stab.L
/RootClone.stab.V
/RootClone.stab.T
