optimizecode 1
maxversions 0
units Field
/LiquidPhases = 2
/StdLiqVolRefT = 288.15 
 /StdLiqVolRefT = 60 F
/RecycleDetails = 1
displayproperties
displayproperties VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow StdGasVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor
commonproperties
commonproperties + ZFactor P T MolecularWeight MassDensity StdLiqMolarVolVapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow StdGasVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + METHANE ETHANE PROPANE n-BUTANE
realcomp = Compressor.CompressorWithCurve()
cd realcomp
NumberTables = 1
CompressorSpeed0 = 1800.0
FlowCurve0 = 0.0 1000.0 2000.0 3000.0 4000.0 5000.0 6000.0 7000.0
HeadCurve0 = 700.0  600.0   500.0   400.0   300.0   200.0   100.0   0.0
EfficiencyCurve0 = 0.0 0.5 0.7 0.8 0.8 0.7 0.5 0.0
CompressorSpeed = 1800
In.Fraction = .4 .3 .2 .1
In.P = 101.325
In.T = 30
Out.P = 106
Out
InQ
/realcomp.EfficiencyCurveType = Polytropic
Out
AdiabaticEff
PolytropicEff
/realcomp.EfficiencyCurveType = Adiabatic
AdiabaticEff
PolytropicEff
'/realcomp.Out.P' =
'/realcomp.In.VolumeFlow' =  2500
AdiabaticEff
PolytropicEff
cd /

copy /
paste /
/RootClone.realcomp.Out