#dehydration plant
$thermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $thermo
thermo + WATER NITROGEN CARBON_DIOXIDE METHANE ETHANE PROPANE ISOBUTANE N-BUTANE ISOPENTANE
thermo + N-PENTANE N-HEXANE N-OCTANE BENZENE TOLUENE ETHYLBENZENE O-XYLENE TRIETHYLENE_GLYCOL

units Field

#define feed to dehydration plant
Feed = Stream.Stream_Material()
Feed.In.MoleFlow = 100
Feed.In.Fraction = 0.0022 0.0041 0.0186 0.8954 0.0469 0.0161 0.0043 0.0053 0.0021 0.0016 0.0022 .0016 0.000256 0.00018 0.000100 0.000095 0.0

Feed.In.T = 120
Feed.In.P = 1000
Feed.In

Lean = Stream.Stream_Material()
Lean.In.T = 130.0022
Lean.In.P = 1000
Lean.In.MoleFlow = 5
Lean.In.Fraction = 0.14 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.86
Lean.In

dehy = Tower.Tower()
dehy.Stage_0 + 10

cd dehy.Stage_0
v = Tower.VapourDraw()
v.Port.P = 995
estT = Tower.Estimate('T')
estT.Value = 130
lFeed = Tower.Feed()
/Lean.Out -> lFeed.Port

cd ../Stage_11
l = Tower.LiquidDraw()
l.Port.P = 1000
estT = Tower.Estimate('T')
estT.Value = 120
vFeed = Tower.Feed()
/Feed.Out -> vFeed.Port

cd ..
/dryGas = Stream.Stream_Material()
/Rich = Stream.Stream_Material()

/dryGas.In -> Stage_0.V.Port
/Rich.In -> Stage_11.L.Port

InitKPower = 0  # says to use combined feed composition and est T and P on each stage to get initial Ks
TryToSolve = 1

Stage_0.v.Port
Stage_11.l.Port

copy /
paste /
cd /RootClone.dehy
Stage_0.v.Port
Stage_11.l.Port

