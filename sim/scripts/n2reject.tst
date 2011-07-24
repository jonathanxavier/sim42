# Nitrogen Rejection Unit (from old Hysim manual)
units Field
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + Nitrogen Methane Ethane PROPANE
thermo + ISOBUTANE n-BUTANE ISOPENTANE n-PENTANE

hp_feed = Stream.Stream_Material()
hp_ovhd = Stream.Stream_Material()
hp_btms = Stream.Stream_Material()

cd hp_feed.In
T = -215
P = 380
MoleFlow = 1000
Fraction = .5454 .4153 .0347 .0036 .0004 .0003 .0002 .0001
cd /

hp_column = Tower.Tower()
hp_column.Stage_0 + 8  # ten stages`

cd hp_column.Stage_0

l = Tower.LiquidDraw()
l.Port.P = 370

l.Port -> /hp_ovhd.In
/hp_ovhd.In.Fraction.NITROGEN = .99

l.estF = Tower.Estimate('MoleFlow')
l.estF.Value = 200

cond = Tower.EnergyFeed(0)

estReflux = Tower.Estimate('Reflux')
estReflux.Value = 3

estT = Tower.Estimate('T')
estT.Value = -250

cd ../Stage_9
f = Tower.Feed()
f.Port -> /hp_feed.Out

l = Tower.LiquidDraw()
l.Port.P = 377
l.Port -> /hp_btms.In

estT = Tower.Estimate('T')
estT.Value = -230

cd ..

TryToSolve = 1  # start calculation

cd /
hp_ovhd.Out
hp_btms.Out

# now add exchanger for overheads
e1 = Heater.HeatExchanger()
e1.DeltaPC = 0.5
e1.DeltaPH = 0.5
hp_ovhd.Out -> e1.InH
e1.OutH.T = -270

# valve
v1 = Valve.Valve()
e1.OutH -> v1.In
v1.Out.P = 29.3919

e2 = Heater.HeatExchanger()
e2.DeltaPH = .5
e2.DeltaPC = .5
hp_btms.Out -> e2.InH
e2.OutH.T = -230

# another valve
v2 = Valve.Valve()
e2.OutH -> /v2.In
v2.Out.P = 29.3919

lp_column = Tower.Tower()
lp_column.Stage_0 + 4  # six stages

cd lp_column.Stage_0
f = Tower.Feed()
f.Port -> /v1.Out

v = Tower.VapourDraw()
v.Port -> /e1.InC
v.Port.P = 29.392

cd ../Stage_3
f = Tower.Feed()
f.Port -> /v2.Out

cd ../Stage_5
reb = Tower.EnergyFeed(1)
reb.Port -> /hp_column.Stage_0.cond.Port

l = Tower.LiquidDraw()
l.Port -> /e2.InC
l.Port.P = 36.74

cd ..
TryToSolve = 1

copy /
paste /

/e1.OutC
/RootClone.e1.OutC
/e2.OutC
/RootClone.e2.OutC
