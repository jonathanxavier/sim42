# Simple distilation column test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

col = Tower.Tower()
col.Stage_0 + 20  # twenty two stages`

cd col.Stage_10
f = Tower.Feed()
f.Port.T = 30
f.Port.P = 720
f.Port.MoleFlow = 10
f.Port.Fraction = .4 .05 .4 .15
f.Port

cd ../Stage_0
l = Tower.LiquidDraw()
l.Port.P = 700

l.Port.MoleFlow = 5

cond = Tower.EnergyFeed(0)

reflux = Tower.StageSpecification('Reflux')
reflux.Value = 1

cd ../Stage_21
l = Tower.LiquidDraw()
l.Port.P = 720
reb = Tower.EnergyFeed(1)

cd ..
TryToSolve = 1  # start calculation

# since there was little output here, I will put some profile stuff here
L_MassFraction.PROPANE
V_MoleFraction.ISOBUTANE
L_MassFlow
L_Viscosity
L_StdVolFraction.PROPANE
V_StdVolFraction.PROPANE
L_VolumeFlow
L_StdLiqVolumeFlow
V_StdLiqVolumeFlow
