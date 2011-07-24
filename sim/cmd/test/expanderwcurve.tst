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
realExpander = Compressor.ExpanderWithCurve()
cd realExpander
NumberTables = 1
ExpanderSpeed0 = 1800.0
FlowCurve0 = 0.0 1000.0 2000.0 3000.0 4000.0 5000.0 6000.0 7000.0
HeadCurve0 = 0.0  5637.0   11273.0   16910.0   22546.0   28184.0   33821.0   39457.0
EfficiencyCurve0 = 0.0 0.5 0.7 0.78 0.8 0.7 0.6 0.55
ExpanderSpeed = 1800
In.Fraction = .4 .3 .2 .1
In.P = 206
In.T = 30
In.MassFlow = 1000
In
Out
OutQ
'/realExpander.In.MassFlow' =
'/realExpander.In.VolumeFlow' =  1000
AdiabaticEff
PolytropicEff
/realExpander.EfficiencyCurveType = Polytropic
AdiabaticEff
PolytropicEff
/realExpander.EfficiencyCurveType = Adiabatic
AdiabaticEff
PolytropicEff

copy /
paste /
/RootClone.realExpander.Out