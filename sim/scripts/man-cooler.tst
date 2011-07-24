#Cooler Example - Distillation Tower Condenser Duty
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

cond.OutQ

