#conversion reactor example
#calculation of propane adiabatic flame temperature
$thermo = VirtualMaterials.SRK
/ -> $thermo
thermo + PROPANE OXYGEN NITROGEN CARBON_DIOXIDE WATER

units SI

#create reactor
r = ConvRxn.ConvReactor()
cd /r
In.P = 1 atm
In.T = 25 C
In.MoleFlow = 1
In.Fraction = 1 6 24 0 0
DeltaP = 0
OutQ = 0

#create reaction
NumberRxn = 1
Rxn0.Formula = PropaneAFT:4*WATER+3*"CARBON DIOXIDE"-!PROPANE-5*OXYGEN

Out

copy /r
paste /
/rClone.Out