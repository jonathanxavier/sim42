$thermo = VirtualMaterials.NRTL/Ideal/HC
/ -> $thermo
$thermo + HYDROGEN METHANE PROPANE WATER

units SI

V101 = Flash.SimpleFlash()
V101.LiquidPhases = 1

sep101.In.T = 45
sep101.In.P = 165 psia
sep101.In.MassFlow = 852143
sep101.In.Fraction =  2 2 2 1 

sep101.Vap
sep101.Liq0

sep101.Vertical  = DesignSep2Phase.Vertical()
sep101.Horizontal  = DesignSep2Phase.Horizontal()
# can try: Vertical or Horizontal

sep101.Vertical.Input.HoldupTime = 1500
sep101.Vertical.Input.SurgeTime = 300
sep101.Vertical.Input.Mist = 1		# boolean 1 or 0
sep101.Vertical.Input.Liq-LiqSepType = 'HC-Water'	# 'HC-Caustic', 'Others'

sep101.Horizontal.Input.HoldupTime = 1400
sep101.Horizontal.Input.SurgeTime = 500
sep101.Horizontal.Input.Mist = 0		# boolean 1 or 0
sep101.Horizontal.Input.Liq-LiqSepType = 'HC-Caustic'	# 'HC-Caustic', 'Others'

sep101.TryToSolveDesign = 1	# boolean 1 or 0


# common results
sep101.Vertical.Input
sep101.Vertical.Output

sep101.Horizontal.Input
sep101.Horizontal.Output
