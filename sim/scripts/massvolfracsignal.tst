units SI
/LiquidPhases = 2

displayproperties
commonproperties  VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor  StdLiqMolarVol
displayproperties  VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor
$VMGThermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $VMGThermo
$VMGThermo + METHANE
$VMGThermo + ETHANE
$VMGThermo + PROPANE

/S1 = Stream.Stream_Material()

'/S1.In.T' = 30
'/S1.In.P' = 100
'/S1.In.MoleFlow' = 100

'/S1.In.Fraction' =  0.2 0.5 0.3
/S1.In.MassFraction


#Play with mass fraction signals
/S1.MassFrac_C1 = Stream.SensorPort('MassFraction_METHANE')
/S1.MassFrac_C1
'/S1.In.T' = 40
/S1.MassFrac_C1
'/S1.In.Fraction' =  1 2 3
/S1.MassFrac_C1
/S1.In.MassFraction

/S1.MassFrac_C1_Copy = Stream.SensorPort('MassFraction_METHANE')
/S1.MassFrac_C1_Copy
/S1.MassFrac_C1
'/S1.In.T' = 30


/S1.MassFrac_C2 = Stream.SensorPort('MassFraction_ETHANE')
/S1.MassFrac_C2
'/S1.In.Fraction' =  3 2 1
/S1.In.MassFraction
/S1.MassFrac_C2



#Now with volume fractions
/S1.VolFracOfEthane = Stream.SensorPort('StdVolFraction_ETHANE')
/S1.StdVolFraction
/S1.VolFracOfEthane
'/S1.In.T' = 40
/S1.VolFracOfEthane
'/S1.In.Fraction' =  1 2 3
/S1.VolFracOfEthane
/S1.In.StdVolFraction


#now attemt setting values. It should fail !
'/S1.In.Fraction' =  None
/S1.MassFrac_C1_Copy = .1
/S1.VolFracOfEthane = .3
/S1.VolFracOfEthane

'/S1.In.Fraction' =  1 2 3
/S1.VolFracOfEthane
/S1.MassFrac_C1_Copy
/S1.VolFracOfEthane = None
/S1.MassFrac_C1_Copy = None


copy /S1
paste /
/S1Clone.Out.StdVolFraction
/S1Clone.VolFracOfEthane
/S1Clone.MassFrac_C2





