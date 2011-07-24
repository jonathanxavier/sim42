$thermo = VirtualMaterials.NRTL/Ideal/HC
/ -> $thermo
$thermo + HYDROGEN METHANE PROPANE N-PENTANE WATER

units SI

V101 = Flash.SimpleFlash()
V101.LiquidPhases = 2

V101.In.T = 45
V101.In.P = 165 psia
V101.In.MassFlow = 852143
V101.In.Fraction =  2 2 1 1 1

V101.Vap
V101.Liq0
V101.Liq1

V101.Vertical = DesignSep3Phase.Vertical()
V101.Horizontal = DesignSep3Phase.Horizontal()
V101.HorizontalWithBoot = DesignSep3Phase.HorizontalWithBoot()
V101.HorizontalWithWeir = DesignSep3Phase.HorizontalWithWeir()
V101.HorizontalWithWeirAndBucket = DesignSep3Phase.HorizontalWithWeirAndBucket()
# can try: Horizontal, Horizontal, HorizontalWithBoot, HorizontalWithWeir, HorizontalWithWeirAndBucket

V101.TryToSolveDesign = 1

V101.Horizontal.Input.HoldupTime = 1500
V101.Horizontal.Input.SurgeTime = 300
V101.Horizontal.Input.Mist = 1		# boolean 1 or 0
V101.Horizontal.Input.Liq-LiqSepType = 'HC-Water'	# 'HC-Caustic', 'Others'
V101.Horizontal.Input.ServiceType = 'Refinery'	# support 'PetChem', 'Others'

V101.Vertical.Input.HoldupTime = 1500
V101.Vertical.Input.SurgeTime = 300
V101.Vertical.Input.Mist = 1		# boolean 1 or 0
V101.Vertical.Input.Liq-LiqSepType = 'HC-Water'	# 'HC-Caustic', 'Others'
V101.Vertical.Input.ServiceType = 'Refinery'	# support 'PetChem', 'Others'

V101.HorizontalWithWeirAndBucket.Input.HoldupTime = 1500
V101.HorizontalWithWeirAndBucket.Input.SurgeTime = 300
V101.HorizontalWithWeirAndBucket.Input.Mist = 1		# boolean 1 or 0
V101.HorizontalWithWeirAndBucket.Input.Liq-LiqSepType = 'HC-Water'	# 'HC-Caustic', 'Others'
V101.HorizontalWithWeirAndBucket.Input.ServiceType = 'Refinery'	# support 'PetChem', 'Others'

V101.HorizontalWithBoot.Input.HoldupTime = 1500
V101.HorizontalWithBoot.Input.SurgeTime = 300
V101.HorizontalWithBoot.Input.Mist = 1		# boolean 1 or 0
V101.HorizontalWithBoot.Input.Liq-LiqSepType = 'HC-Water'	# 'HC-Caustic', 'Others'
V101.HorizontalWithBoot.Input.ServiceType = 'Refinery'	# support 'PetChem', 'Others'

V101.HorizontalWithWeir.Input.HoldupTime = 1500
V101.HorizontalWithWeir.Input.SurgeTime = 300
V101.HorizontalWithWeir.Input.Mist = 1		# boolean 1 or 0
V101.HorizontalWithWeir.Input.Liq-LiqSepType = 'HC-Water'	# 'HC-Caustic', 'Others'
V101.HorizontalWithWeir.Input.ServiceType = 'Refinery'	# support 'PetChem', 'Others'

V101.TryToSolveDesign = 1
V101.TryToSolveDesign = 1
V101.TryToSolveDesign = 1
V101.TryToSolveDesign = 1	# boolean 1 or 0


# common results
V101.Horizontal.Input
V101.Horizontal.Output

V101.HorizontalWithWeirAndBucket.Input
V101.HorizontalWithWeirAndBucket.Output

V101.HorizontalWithWeir.Input
V101.HorizontalWithWeir.Output

V101.HorizontalWithBoot.Input
V101.HorizontalWithBoot.Output

V101.Vertical.Input
V101.Vertical.Output



