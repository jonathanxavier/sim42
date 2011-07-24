#Heater example
#distillation tower condenser is used to preheat distillation tower feed

$thermo = VirtualMaterials.NRTL/Ideal/HC
/ -> $thermo
thermo + ETHANOL WATER

topVap = Stream.Stream_Material()
topVap.In.P = 101.325
topVap.In.VapFrac = 1
topVap.In.MoleFlow = 100
topVap.In.Fraction = 0.85 0.15

cond = Heater.Cooler()
topVap.Out -> cond.In
cond.DeltaP = 0
cond.Out.VapFrac = 0

heater = Heater.Heater()
heater.In.P = 130.0
heater.In.T = 25.0
heater.In.MoleFlow = 1000.0
heater.In.Fraction = 0.1 0.9
heater.DeltaP = 0.0
cond.OutQ -> heater.InQ
heater.Out
		
