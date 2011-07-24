#ethanol distillation
$thermo = VirtualMaterials.PSRK
/ -> $thermo
thermo + Ethanol Water

units SI

Feed = Stream.Stream_Material()
Feed.In.MoleFlow = 34.43
Feed.In.Fraction = 0.3 0.7
Feed.In.VapFrac = 0.0
Feed.In.P = 101.325
Feed.In

Steam = Stream.Stream_Material()
Steam.In.P = 24.7 psia
Steam.In.Fraction = 0 1
Steam.In.MoleFlow = 51.1
Steam.In.VapFrac = 1.0
Steam.In

dist = Tower.Tower()
dist.MaxOuterLoops = 40
dist.Stage_0 + 12
cd dist.Stage_0
l = Tower.LiquidDraw()
l.Port.P = 101.325
l.Port.MoleFlow = 12.91
#reflux = Tower.RefluxRatioSpec()
#reflux.Port = 3.0
cond = Tower.EnergyFeed(0)
estT = Tower.Estimate('T')
estT.Value = 78

cd ../Stage_11
f = Tower.Feed()
/Feed.Out -> f.Port

cd ../Stage_13
l = Tower.LiquidDraw()
l.Port.P = 101.325
f = Tower.Feed()
/Steam.Out -> f.Port
estT = Tower.Estimate('T')
estT.Value = 100

cd ..
/distillate = Stream.Stream_Material()
/stillage   = Stream.Stream_Material()
/distillate.In -> Stage_0.l.Port
/stillage.In -> Stage_13.l.Port

TryToSolve = 1

copy /
paste /
cd /RootClone
dist.Stage_0.l.Port