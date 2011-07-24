# Two phase flash test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE WATER

flash = Flash.SimpleFlash()
flash.LiquidPhases = 2  # set the number of phases parameter
cd flash.In
Fraction = .2 .2 .2 .2 .2
T = 0
P = 101.325
MoleFlow = 10
cd ..
# dump the results
Vap   # Vapour stream
Liq0  # Liquid stream
Liq1  # Water stream
In    


#Test copy and paste
copy /flash
paste /
/flashClone.In
/flashClone.Vap
