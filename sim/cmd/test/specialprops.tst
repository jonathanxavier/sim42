units SI
LiquidPhases = 2

Prop-101 = Properties.SpecialProps()
$ThermoCase = VirtualMaterials.Advanced_Peng-Robinson
/ -> $ThermoCase
ThermoCase + METHANE
ThermoCase + ETHANE
ThermoCase + PROPANE
ThermoCase + n-BUTANE
ThermoCase + ISOBUTANE
ThermoCase + n-PENTANE
ThermoCase + ISOPENTANE
ThermoCase + WATER
Prop-101.In.T = 300
Prop-101.In.P = 200
Prop-101.In.MoleFlow = 10
Prop-101.In.Fraction =  4.54545454545455E-02 9.09090909090909E-02 0.136363636363636 0.181818181818182 0.136363636363636 0.136363636363636 0.136363636363636 0.136363636363636

Prop-101.BubblePoint_Active = 1
Prop-101.FlashPoint_Active = 1
Prop-101.PourPoint_Active = 1
Prop-101.KinematicViscosity_Active = 1
Prop-101.DynamicViscosity_Active = 1
Prop-101.ParaffinMolPercent_Active = 1
Prop-101.NapthleneMolPercent_Active = 1
Prop-101.AromaticMolPercent_Active = 1
Prop-101.pH_Active = 1

Prop-101.BubblePoint
Prop-101.FlashPoint
Prop-101.PourPoint
Prop-101.KinematicViscosity
Prop-101.DynamicViscosity
Prop-101.ParaffinMolPercent
Prop-101.NapthleneMolPercent
Prop-101.AromaticMolPercent
Prop-101.pH

copy /Prop-101
paste /
/Prop-101Clone.BubblePoint
/Prop-101Clone.FlashPoint
/Prop-101Clone.PourPoint
/Prop-101Clone.KinematicViscosity
/Prop-101Clone.DynamicViscosity
/Prop-101Clone.ParaffinMolPercent
/Prop-101Clone.NapthleneMolPercent
/Prop-101Clone.AromaticMolPercent
/Prop-101Clone.pH


#$thermo2 = VirtualMaterials.Advanced_Peng-Robinson
#/ -> $thermo2
#thermo + METHANE ETHANE PROPANE n-BUTANE n-PENTANE n-OCTANE n-NONANE n-TETRADECANE n-PENTADECANE n-OCTADECANE ETHYLENE CYCLOPROPANE BENZENE WATER CARBON_DIOXIDE HYDROGEN_SULFIDE
#Prop-101.In.Fraction = None
#Prop-101.In.Fraction = .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625  .0625