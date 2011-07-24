# Ammonia Refrigeration Loop - no streams
# Sim42 Tutorial

 
$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + Ammonia
 

Chiller    = Heater.Heater()
Compressor = Compressor.Compressor()
Condenser  = Heater.Cooler()
JT         = Valve.Valve()
 

Chiller.Out.T        = 253.15 K
Chiller.Out.VapFrac  = 1
Chiller.Out.Fraction = 1
Chiller.DeltaP = 20

Chiller.InQ   = 10000
 

Condenser.Out.T        = 333.15 K
Condenser.Out.VapFrac  = 0
Condenser.Out.Fraction = 1
Condenser.DeltaP = 20

Compressor.Efficiency = 0.75

Chiller.Out    -> Compressor.In
Compressor.Out -> Condenser.In
Condenser.Out  -> JT.In
JT.Out         -> Chiller.In


Chiller.Out
Compressor.Out
Condenser.Out
JT.Out
