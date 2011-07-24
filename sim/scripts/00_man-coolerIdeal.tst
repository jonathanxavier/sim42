
thermo = VirtualMaterials.IdealLiquid/Ideal/HC
thermo + ETHANOL WATER
topVap = Stream.Stream_Material()
topVap.In.P = 101.325
topVap.In.T = 78
topVap.In.MoleFlow = 100
topVap.In.Fraction = 0.85 0.15

cond = Heater.Cooler()
topVap.Out -> cond.In
cond.DeltaP = 0
cond.Out.T = 25

cond.OutQ

