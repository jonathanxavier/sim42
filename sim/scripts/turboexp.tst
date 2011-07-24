# turboexpander test (from old Hysim manual)
units Field
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + Nitrogen Carbon_Dioxide Methane Ethane PROPANE
thermo + ISOBUTANE n-BUTANE ISOPENTANE n-PENTANE n-Hexane

# define plant feed
feed = Stream.Stream_Material()
feed.In.T = 60
feed.In.P = 600
feed.In.MoleFlow = 100
feed.In.Fraction = 1.49 .2 91.22 4.96 1.48 .26 .2 .1 .06 .03

# define feed cooler
cooler = Heater.Cooler()
feed.Out -> cooler.In
cooler.Out.T = -105
cooler.DeltaP = 15

# high pressure separator
hp-sep = Flash.SimpleFlash()
cooler.Out -> hp-sep.In

# turbo expander
expander = Compressor.Expander()
expander.Efficiency = .75
expander.Out.P = 330

hp-sep.Vap -> expander.In

# low pressure separator
lp-sep = Flash.SimpleFlash()
expander.Out -> lp-sep.In

# valve
valve = Valve.Valve()
hp-sep.Liq0 -> valve.In
valve.Out.P = 335

demeth = Tower.Tower()
demeth.Stage_0
demeth.Stage_0 + 4  # just six stages`

cd demeth.Stage_0

f = Tower.Feed()
/lp-sep.Liq0 -> f.Port
v = Tower.VapourDraw()
v.Port.P = 330
#v.Port.MoleFlow = 21.7  # overhead flow spec
v.estF = Tower.Estimate('MoleFlow')
v.estF.Value = 22
#estT = Tower.Estimate('T')
#estT.Value = -120

cd ../Stage_1
f = Tower.Feed()
f.Port -> /valve.Out

cd ../Stage_5
l = Tower.LiquidDraw()
l.Port.P = 335
reb = Tower.EnergyFeed(1)
#reb.Port.Energy = 0.065e6
l.Port.Fraction.METHANE = 0.01

estT = Tower.Estimate('T')
estT.Value = 0

cd ..

/overhead = Stream.Stream_Material()
/overhead.In -> Stage_0.v.Port

/bottoms = Stream.Stream_Material()
/bottoms.In -> Stage_5.l.Port

TryToSolve = 1  # start calculation - turned off by default

/overhead.Out
/bottoms.Out

copy /
paste /
/bottoms.In
/RootClone.bottoms.In
