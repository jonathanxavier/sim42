# Simple flash test
units SI
$thermo = VirtualMaterials.Peng-Robinson SimpleSolid
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE WATER INERTSOLID
flash = Flash.SimpleFlash()
LiquidPhases = 2
SolidPhases = 1
cd flash.In
Fraction = .25 .25 .25 .25 .25 .25
T = 0 C
P = 101.325
MoleFlow = 10
cd ..
# dump the results
In
Vap   # Vapour stream
Liq0  # Liquid stream
Liq1
Solid0

#Lets play with phase arragement
KeyCmp_Liq0 = WATER 0.5
In
Vap   # Vapour stream
Liq0  # Liquid stream
Liq1
Solid0

KeyCmp_Liq1 = WATER 0.5
In
Vap   # Vapour stream
Liq0  # Liquid stream
Liq1
Solid0

KeyCmp_Liq0 = WATER 0.5
KeyCmp_Liq1 = INERTSOLID 0.5
In
Vap   # Vapour stream
Liq0  # Liquid stream
Liq1
Solid0

KeyCmp_Liq0 = None
KeyCmp_Liq1 = INERTSOLID 0.5
In
Vap   # Vapour stream
Liq0  # Liquid stream
Liq1
Solid0

KeyCmp_Liq1 = None
KeyCmp_Solid0 = INERTSOLID 0.5
In
Vap   # Vapour stream
Liq0  # Liquid stream
Liq1
Solid0

#Finally lets make the solid phases = to 0
SolidPhases = 0

cd ..
#To clear the error, delete the solid compound
thermo - INERTSOLID

cd flash
In
Vap   # Vapour stream
Liq0  # Liquid stream
Liq1
Solid0

copy /flash
paste /
/flashClone.Solid0
/flashClone.Vap
/flashClone.Liq0




