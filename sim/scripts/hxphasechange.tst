units SI
/LiquidPhases = 2
/RecycleDetails = 1
displayproperties
commonproperties  VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor SurfaceTension  StdLiqMolarVol
displayproperties  VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor SurfaceTension
$VMGThermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $VMGThermo
$VMGThermo + WATER
$VMGThermo + NITROGEN
$VMGThermo + CARBON_DIOXIDE
$VMGThermo + METHANE
$VMGThermo + ETHANE
$VMGThermo + PROPANE
$VMGThermo + ISOBUTANE
$VMGThermo + n-BUTANE
$VMGThermo + ISOPENTANE
$VMGThermo + n-PENTANE
$VMGThermo + n-HEXANE
/Hx1 = Heater.HeatExchangerUA()
'/Hx1.DeltaP0.DP' = 20
'/Hx1.DeltaP1.DP' = 5
'/Hx1.In0.T' = 150
'/Hx1.In0.P' = 200
'/Hx1.In0.MassFlow' = 80
'/Hx1.In0.Fraction' =  0 1.56701856206534E-02 3.10201631060189E-04 5.52959423625356E-02 0.622104367839095 0.255756241557012 3.45624656026417E-02 1.38289888427478E-02 1.2508130284685E-03 9.10591884725071E-04 3.10201631060189E-04
'/Hx1.In1.T' = 90
'/Hx1.In1.P' = 200
'/Hx1.UA0_1.UA' = 45
'/Hx1.In1.Fraction' =  1 0 0 0 0 0 0 0 0 0 0
'/Hx1.Out0.T' = 130
/Hx1.NumberSegments = 5
cd /


#Now play with segments and phase change tracking
/Hx1.UA0_1.UA = None
/Hx1.Out1.T = 125
/Hx1.UA0_1.UA

#As the number of segments increases, the ua converges to a single
#ua but the hx becomes slower
/Hx1.NumberSegments = 10
/Hx1.UA0_1.UA
/Hx1.NumberSegments = 50
/Hx1.UA0_1.UA


#Now back to 5 segments
/Hx1.NumberSegments = 5
/Hx1.UA0_1.UA

#Track phase change
#The UA is already the converged one with 100 segments
/Hx1.TrackPhaseChange = 1
/Hx1.UA0_1.UA
/Hx1.NumberSegments = 3
/Hx1.UA0_1.UA
/Hx1.NumberSegments = 10
/Hx1.UA0_1.UA

#Lets get a bunch of profiles
/Hx1.side0.T
/Hx1.side0.EnergyAcum
/Hx1.side0.L_Cp
/Hx1.side0.L_Viscosity
/Hx1.side0.V_Viscosity
/Hx1.side0.Viscosity

/Hx1.side1.T
/Hx1.side1.EnergyAcum
/Hx1.side1.L_Cp
/Hx1.side1.L_Viscosity
/Hx1.side1.V_Viscosity
/Hx1.side1.Viscosity

#Now unspec T and spec ua
#Unfortunately, the track phase change thing does not work for rating mode :(
/Hx1.Out1.T = None
/Hx1.TryLastConverged = 0
/Hx1.UA0_1.UA = 49.9
/Hx1.Out1.T

#Test vap frac profiles
/Hx1.side1.VapFrac
/Hx1.side1.MassVapFrac

copy /
paste /
/RootClone.Hx1.side1.VapFrac




