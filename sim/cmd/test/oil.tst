#..... VMG Oil Test
units Field
$thermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

#..... Create a crude stream
lightCrude = Stream.Stream_Material()

#..... Create an oil case
thermo.thOilCase = Oils.OilCase()
cd thermo.thOilCase

#..... Create an oil
Watkins55 = Oils.Oil()

#..... Add several assays
Watkins55.Light_Naphtha = Oils.Assay()
Watkins55.Heavy_Naphtha = Oils.Assay()
Watkins55.Light_Distillate = Oils.Assay()
Watkins55.Heavy_Distillate = Oils.Assay()
Watkins55.Light = Oils.Assay()

#..... Add some bulk properties
Watkins55.Light_Naphtha.MW = Oils.OilParameter('MolecularWeight', 96.0)
Watkins55.Heavy_Naphtha.MW = Oils.OilParameter('MolecularWeight', 132.0)
Watkins55.Light_Distillate.MW = Oils.OilParameter('MolecularWeight', 190.0)
Watkins55.Heavy_Distillate.MW = Oils.OilParameter('MolecularWeight', 254.0)
Watkins55.Light.MW = Oils.OilParameter('MolecularWeight', 96.0)

Watkins55.Light_Naphtha.LD60 = Oils.OilParameter('MassDensity')
Watkins55.Heavy_Naphtha.LD60 = Oils.OilParameter('MassDensity')
Watkins55.Light_Distillate.LD60 = Oils.OilParameter('MassDensity')
Watkins55.Heavy_Distillate.LD60 = Oils.OilParameter('MassDensity')
Watkins55.Light.LD60 = Oils.OilParameter('MassDensity')

#..... Set the density values using the field units
Watkins55.Light_Naphtha.LD60 = 44.4
Watkins55.Heavy_Naphtha.LD60 = 48.3
Watkins55.Light_Distillate.LD60 = 51.4
Watkins55.Heavy_Distillate.LD60 = 53.5
Watkins55.Light.LD60 = 44.4

#..... Add the distillation curves to the assay
Watkins55.Light_Naphtha.EXPERIMENT = Oils.OilParameter('Generic','TBP')
Watkins55.Light_Naphtha.distCurve = Oils.OilExperiment('DistillationCurve')
Watkins55.Light_Naphtha.distCurve.Series0 = 0    10   30   50   70   90   100. 
Watkins55.Light_Naphtha.distCurve.Series1 = 183. 291. 327. 352. 372. 395. 416.5 K

Watkins55.Heavy_Naphtha.D86 = Oils.OilExperiment('D86')
Watkins55.Heavy_Naphtha.EXPERIMENT = Oils.OilParameter('Generic','D86')
Watkins55.Heavy_Naphtha.D86.Series0 = 0    10   30   50   70   90   100. 
Watkins55.Heavy_Naphtha.D86.Series1 = 404. 413. 422. 729. 437. 452. 467. K

Watkins55.Light_Distillate.D86 = Oils.OilExperiment('D86')
Watkins55.Light_Distillate.EXPERIMENT = Oils.OilParameter('Generic','D86')
Watkins55.Light_Distillate.D86.Series0 = 0    10   30   50   70   90   100. 
Watkins55.Light_Distillate.D86.Series1 = 470. 482. 495. 507. 520. 544. 567. K

Watkins55.Heavy_Distillate.EFV = Oils.OilExperiment('EFV')
Watkins55.Heavy_Distillate.EXPERIMENT = Oils.OilParameter('Generic','EFV')
Watkins55.Heavy_Distillate.EFV.Series0 = 0    10   30   50   70   90   100.
Watkins55.Heavy_Distillate.EFV.Series1 = 583. 586. 593. 597. 600. 606. 610. K

Watkins55.Light.distCurve = Oils.OilExperiment('DistillationCurve')
Watkins55.Light.EXPERIMENT = Oils.OilParameter('Generic','TBP')
Watkins55.Light.distCurve.Series0 = 0    10   30   50   70   90   100. 
Watkins55.Light.distCurve.Series1 = 183. 291. 327. 352. 372. 395. 416.5 K

#..... Add the light ends to the assay
Watkins55.Light.TBBASIS = Oils.OilParameter('Generic','VOLUMEPCT')
Watkins55.Light.LIGHTENDS = Oils.OilParameter('Generic','YES')
Watkins55.Light.LIGHTENDSBASIS = Oils.OilParameter('Generic','MOLEPCT')
Watkins55.Light.LightEndComp.CO2 = 3.0
Watkins55.Light.LightEndComp.METHANE = 0.1
Watkins55.Light.LightEndComp.ETHANE = 0.5
Watkins55.Light.LightEndComp.PROPANE = 1.0
Watkins55.Light.LightEndComp.n-BUTANE = 1.5
Watkins55.Light.LightEndComp.n-PENTANE = 2.0

#..... Test get settings
/thermo.thOilCase.CustomCommand + GetBulkPropertyUnitTypes
/thermo.thOilCase.CustomCommand + GetList.EXPERIMENT
/thermo.thOilCase.CustomCommand + GetAssayDefaults

#..... Cut and install the assay, Light_Naphtha, use 5 hypo's
Watkins55.Light_Naphtha.PREFIX = Oils.OilParameter('Generic','LN')
Watkins55.Light_Naphtha.SUFFIX = Oils.OilParameter('Generic','F')
Watkins55.Light_Naphtha.SLICESTYLE = Oils.OilParameter('Generic','FIXEDCUTS')
Watkins55.Light_Naphtha.NUMBEROFCUTS = Oils.OilParameter('Generic',5)

Watkins55.Light_Naphtha.CustomCommand + Cut
Watkins55.Light_Naphtha.CustomCommand + InstallOil
Watkins55.Light_Naphtha.CustomCommand + GetOilComposition
/lightCrude.In

#..... Cut and install another assay, Heavy_Distillate
Watkins55.Heavy_Distillate.PREFIX = Oils.OilParameter('Generic','HD')
Watkins55.Heavy_Distillate.SUFFIX = Oils.OilParameter('Generic','F')
Watkins55.Heavy_Distillate.CustomCommand + Cut
Watkins55.Heavy_Distillate.CustomCommand + InstallOil
Watkins55.Heavy_Distillate.CustomCommand + GetOilComposition
/lightCrude.In

#..... Cut and install another assay, Light
Watkins55.Light.PREFIX = Oils.OilParameter('Generic','LT')
Watkins55.Light.SUFFIX = Oils.OilParameter('Generic','F')
Watkins55.Light.CustomCommand + Cut
Watkins55.Light.CustomCommand + InstallOil
Watkins55.Light.CustomCommand + GetOilComposition
/lightCrude.In

#..... Assign the composition of the assay 'Light' to a stream 'lightCrude'
cd /
lightCrude.In.Fraction = /thermo.thOilCase.Watkins55.Light
lightCrude.In.T = 60 F
lightCrude.In.P = 14.7 psia
lightCrude.In


copy /
paste /
/RootClone.lightCrude.In

clear

#now create a unit operation before doing the oil

units SI
/LiquidPhases = 2
$VMGThermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $VMGThermo
$VMGThermo + WATER
$VMGThermo + HYDROGEN_SULFIDE
$VMGThermo + CARBON_DIOXIDE
/CSP1 = ComponentSplitter.ComponentSplitter()
/VMGThermo.thOilCase = Oils.OilCase()
/VMGThermo.thOilCase.test = Oils.Oil()
/VMGThermo.thOilCase.test.testt = Oils.Assay()
/VMGThermo.thOilCase.test.testt.DistillationCurve = Oils.OilExperiment('DistillationCurve')
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series0 = 0
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series0 = 0 20
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series0 = 0 20 40
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series0 = 0 20 40 60
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series0 = 0 20 40 60 80
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series0 = 0 20 40 60 80 100
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series1 = 80 None None None None None
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series1 = 80 None None None None 200
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series1 = 80 140 None None None 200
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series1 = 80 140 None None 195 200
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series1 = 80 140 None 185 195 200
/VMGThermo.thOilCase.test.testt.DistillationCurve.Series1 = 80 140 165 185 195 200
/VMGThermo.thOilCase.test.testt.CustomCommand + Cut
/VMGThermo.thOilCase.test.testt.CustomCommand + InstallOil
/VMGThermo.thOilCase.test.testt.CustomCommand + GetOilComposition


