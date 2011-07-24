$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + n-HEPTANE BENZENE
# Components with names in them can be entered by using underscores instead
thermo + TRIETHYLENE_GLYCOL
thermo
units SI

lle = LiqLiqExt.LiqLiqEx()
lle
cd lle.Feed
Fraction = .5 .5 0.
T = 0
P = 101.325
MoleFlow = 10
cd /lle.Solvent
Fraction = 0 0 1
T = 0
P = 101.325
MoleFlow = 10
.
cd /lle

Extract
Raffinate
Feed
Solvent

cd /

#Test copy and paste
copy /lle
paste /
/lleClone.Extract
/lleClone.Raffinate
