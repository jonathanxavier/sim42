optimizecode 1
maxversions 0
units SI
/LiquidPhases = 2
/StdLiqVolRefT = 288.15 
 /StdLiqVolRefT = 60 F
/RecycleDetails = 1
displayproperties
displayproperties VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow StdGasVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor S
commonproperties
commonproperties + ZFactor P T MolecularWeight MassDensity StdLiqMolarVolVapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow StdGasVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor S
$VMGThermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $VMGThermo
/SolidPhases = 0

$VMGThermo + WATER
$VMGThermo + METHANE
$VMGThermo + ETHANE
$VMGThermo + PROPANE
$VMGThermo + n-BUTANE
$VMGThermo + ISOPENTANE

/CP1 = Compressor.CompressorWithCurve("IgnoreCurve = 1")
'/CP1.In.Fraction' =   .003690036900369  .3690036900369  .3690036900369  .18450184501845  .03690036900369  .03690036900369
'/CP1.In.T' =  80
'/CP1.In.P' =  100
'/CP1.In.MoleFlow' =  100
'/CP1.Out.P' =  300
'/CP1.AdiabaticEff.Generic' =  .8
/CP1.In
/CP1.Out
/CP1.AdiabaticEff
/CP1.PolytropicEff
/CP1.TotalQ.In

'/CP1.AdiabaticEff.Generic' =
'/CP1.PolytropicEff.Generic' =  .8
/CP1.In
/CP1.Out
/CP1.AdiabaticEff
/CP1.PolytropicEff
/CP1.TotalQ.In

/CP1.FlowSensor.In.MoleFlow = 
/CP1.In
/CP1.Out
/CP1.AdiabaticEff
/CP1.PolytropicEff
/CP1.TotalQ.In

/CP1.TotalQ.In.Work = 121861.34
/CP1.In
/CP1.Out
/CP1.AdiabaticEff
/CP1.PolytropicEff
/CP1.TotalQ.In

/CP1.TotalQ.In.Work = 
/CP1.FlowSensor.In.MoleFlow = 100
/CP1.FlowSensor.In.T = 
/CP1.OutPSensor.Out.T = 148.12996
/CP1.In
/CP1.Out
/CP1.AdiabaticEff
/CP1.PolytropicEff
/CP1.TotalQ.In


/CP1.PolytropicEffSig.effClone.Generic = 
/CP1.EfficiencySig.effClone.Generic = 0.78619833
/CP1.In
/CP1.Out
/CP1.AdiabaticEff
/CP1.PolytropicEff
/CP1.TotalQ.In

/CP1.OutPSensor.Out.T = 
/CP1.FlowSensor.In.T = 80


EXP1 = Compressor.ExpanderWithCurve()
/EXP1.FlowSensor.In -> /CP1.OutPSensor.Out
/EXP1.PolytropicEffSig.effClone.Generic = .8
/EXP1.OutPSensor.Out.P = 100
/EXP1.In
/EXP1.Out
/EXP1.AdiabaticEff
/EXP1.PolytropicEff
/EXP1.TotalQ.Out


/EXP1.PolytropicEffSig.effClone.Generic = 
/EXP1.EfficiencySig.effClone.Generic = 	0.81140616
/EXP1.In
/EXP1.Out
/EXP1.AdiabaticEff
/EXP1.PolytropicEff
/EXP1.TotalQ.Out


/EXP1.EfficiencySig.effClone.Generic = 
/EXP1.PolytropicEffSig.effClone.Generic = .8
/EXP1.FlowSensor.In -> 
/EXP1.OutPSensor.Out.T = 103.7
/EXP1.FlowSensor.In.P = 300
/EXP1.In.Fraction = 0.00369003690037 0.369003690037 0.369003690037 0.184501845018 0.0369003690037 0.0369003690037
/EXP1.FlowSensor.In.MoleFlow = 100
/EXP1.In
/EXP1.Out
/EXP1.AdiabaticEff
/EXP1.PolytropicEff
/EXP1.TotalQ.Out


/EXP1.OutPSensor.Out.T = 
/EXP1.FlowSensor.In.T = 148.15736
/EXP1.In
/EXP1.Out
/EXP1.AdiabaticEff
/EXP1.PolytropicEff
/EXP1.TotalQ.Out

/EXP1.FlowSensor.In.MoleFlow = 
/EXP1.In
/EXP1.Out
/EXP1.AdiabaticEff
/EXP1.PolytropicEff
/EXP1.TotalQ.Out

/EXP1.TotalQ.Out.Work = 80541.524
/EXP1.In
/EXP1.Out
/EXP1.AdiabaticEff
/EXP1.PolytropicEff
/EXP1.TotalQ.Out


copy /CP1 /EXP1
paste /
/CP1.Out
/EXP1.Out
/CP1Clone.Out
/EXP1Clone.Out