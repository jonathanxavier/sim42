units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

flash = Flash.MixAndFlash()
flash.In0.T = 460.15 K
cd flash.In0
Fraction = .5 .5 0 0
P = 700.325
MoleFlow = 10
cd ..
cd In1
T = 200.15 K
P = 700.325
MoleFlow = 10
Fraction = 0 0 .5 .5
cd /flash
# The vapour and liq outlet ports should now be known
Vap
Liq0
# As well as the inlets
In1
In0

#Test copy and paste
copy /flash
paste /
/flashClone.In0
/flashClone.Vap