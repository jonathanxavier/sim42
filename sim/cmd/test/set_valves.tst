units SI
/LiquidPhases = 2
/RecycleDetails = 1
displayproperties
commonproperties  VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor Cv SpeedOfSound SurfaceTension IdealGasCp  StdLiqMolarVol
displayproperties  VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor Cv SpeedOfSound SurfaceTension IdealGasCp
$VMGThermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $VMGThermo
/SolidPhases = 0
$VMGThermo + METHANE
$VMGThermo + ETHANE
$VMGThermo + PROPANE
/V1 = Valve.Valve()
'/V1.In.T' = 30
'/V1.In.P' = 3000
'/V1.In.MoleFlow' = 500
'/V1.In.Fraction' =  0.7 0.2 0.1
'/V1.Out.P' = 1000
/V2 = Valve.Valve()
'/V2.In.T' = 30
'/V2.In.P' = 3e3
'/V2.In.MoleFlow' = 500
'/V2.In.Fraction' =  0.7 0.2 0.1
'/V2.Out.T' = 15
'/V2.Out.T' =
/Set1 = Set.Set()
'/Set1.multiplier.Generic' = 1
'/Set1.addition.Generic' = -1
delete '/Set1'
'/V2.Out.T' = 15
units SI
'/V2.In.P' =
'/V2.Out.P' = 1e3
'/V2.Out.P' =
/V2Out = Stream.Stream_Material()
/V2.Out -> /V2Out.In
/V1Out = Stream.Stream_Material()
/V1.Out -> /V1Out.In
/V1in = Stream.Stream_Material()
/V1.In -> /V1in.Out
/V12In = Stream.Stream_Material()
/V2.In -> /V12In.Out
/Set1 = Set.Set()
'/Set1.multiplier.Generic' = 1
'/Set1.addition.Generic' = 0
/V2Out.T = Stream.SensorPort('T')
/V2Out.T -> /Set1.Signal0
/Set1.Signal0 ->
/V1Out.T = Stream.SensorPort('T')
/V1Out.T -> /Set1.Signal0
/V1Out.P = Stream.SensorPort('P')
/V1Out.T ->
/V1Out.P -> /Set1.Signal0
/V2Out.P = Stream.SensorPort('P')
/V2Out.P -> /Set1.Signal1
'/V2.Out.T' = 12
/V2.In
/V2.Out
/V1.In
/V1.In

copy /
paste /
/RootClone.V1.In