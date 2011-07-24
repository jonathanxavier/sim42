#liquid-liquid extractor example
$thermo = VirtualMaterials.UNIQUAC/Ideal/HC
/ -> $thermo
thermo + ACETIC_ACID WATER DIISOPROPYL_ETHER
units SI

llex = LiqLiqExt.LiqLiqEx()

llex.NumberStages     = 8

llex.Feed.MassFraction = 30 70 0
llex.Feed.T        = 25 C
llex.Feed.P        = 1 atm
llex.Feed.MassFlow = 8000.0

llex.Solvent.MassFraction = 0.0 0.0 1.0
llex.Solvent.T        = 25 C
llex.Solvent.P        = 1 atm
llex.Solvent.MassFlow = 20000


llex.LiquidMoving = "ACETIC ACID"
llex.Extract
llex.Raffinate

