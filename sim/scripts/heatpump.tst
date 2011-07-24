# Depeopanizer test (from old Hysim manual)
units Field
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + Propane ISOBUTANE n-BUTANE ISOPENTANE

Feed = Stream.Stream_Material()
Feed.In.T = 90
Feed.In.P = 55
Feed.In.MoleFlow = 3000
Feed.In.Fraction = 2.5 39 58 .5

c4split = Tower.Tower()
c4split.Stage_0 + 38  # forty stages`

cd c4split.Stage_0

l = Tower.LiquidDraw()
l.Port.P = 60
l.nC4spec = Tower.VolFractionSpec()
l.nC4spec + n-BUTANE
l.nC4spec.Port = .05

reflux = Tower.RefluxRatioSpec()
reflux.Port = 7

cond = Tower.EnergyFeed(0)
estT = Tower.Estimate('T')
estT.Port = 100

cd ../Stage_1
vap = Tower.InternalVapourClone()
/to_comp = Stream.Stream_Material()
vap.Port -> /to_comp.In

cd ../Stage_29
f = Tower.Feed()
f.Port -> /Feed.Out

cd ../Stage_39
l = Tower.LiquidDraw()
l.Port.P = 68

reb = Tower.EnergyFeed(1)

estT = Tower.Estimate('T')
estT.Port = 120

cd ..

/liq_prod = Stream.Stream_Material()
/liq_prod.clone = Stream.ClonePort(1) 
/liq_prod.In -> Stage_0.l.Port

/btm_prod = Stream.Stream_Material()
/btm_prod.In -> Stage_39.l.Port

TryToSolve = 1  # start calculation

/liq_prod.Out
/btm_prod.Out

cd /
K-100 = Compressor.Compressor()
K-100.Efficiency = .75
K-100.Out.P = 235.1787

c4split.Stage_1.vap.Port -> K-100.In

E-100 = Heater.Cooler()
E-100.DeltaP = 5 

K-100.Out -> E-100.In
E-100.OutQ -> c4split.Stage_39.reb.Port

E-101 = Heater.Cooler()
E-101.DeltaP = 5 
E-100.Out -> E-101.In

CV-100 = Valve.Valve()
E-101.Out -> CV-100.In

V-100 = Flash.SimpleFlash()
CV-100.Out -> V-100.In

split = Split.Splitter()
V-100.Liq0 -> split.In
split.Out0 -> liq_prod.clone

copy /
paste /

/btm_prod.In
/RootClone.btm_prod.In