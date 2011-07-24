units VMG
/LiquidPhases = 2
$thermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $thermo
commonproperties VapFrac T P MoleFlow MassFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor
displayproperties VapFrac T P MoleFlow MassFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor
/thermo + METHANE
S1 = Stream.Stream_Material()
'/S1.In.T' = 300
'/S1.In.P' = 100
'/S1.In.MoleFlow' = 1
'/S1.In.Fraction' =  1
CP1 = Compressor.Compressor()
/S1.Out -> /CP1.In
S2 = Stream.Stream_Material()
/CP1.Out -> /S2.In
cd /CP1.Efficiency
'/CP1.Efficiency.Generic' = .75
cd /

/CP1.InQ.Energy = 10000
CP1.Out

#Small change, 
/CP1.InQ.Energy = 10010
CP1.Out

#Large change
/CP1.InQ.Energy = 1000
CP1.Out


#Now spec outside
'/S1.In.T' =
'/S1.In.P' =
'/S2.In.T' = 400
'/S2.In.P' = 270
CP1.In

