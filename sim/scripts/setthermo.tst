#Test the creation of the thermo cases and preserving compounds

$thermo1 = VirtualMaterials.RK
 . -> $thermo1
/thermo1 + METHANE ETHANE PROPANE ISOBUTANE

$thermo2 = VirtualMaterials.RK
$thermo2 + ISOBUTANE PROPANE METHANE ETHANE

$thermo3 = VirtualMaterials.Advanced_Peng-Robinson
$thermo3 + PROPANE ISOBUTANE n-BUTANE ISOPENTANE n-PENTANE n-OCTANE

$thermo4 = VirtualMaterials.RK

thermo5 = VirtualMaterials.RK
$thermo5 + NITROGEN CARBON_DIOXIDE HYDROGEN_SULFIDE

/s = Stream.Stream_Material()
/s.In.T = 20
/s.In.P = 101
/s.In.MoleFlow = 10
/s.In.Fraction = 1 2 3 4
/s.In

/sep = Flash.SimpleFlash()
/sep.In -> /s.Out
copy /
paste /


/RootClone -> $thermo2
/RootClone.s.In



/RootClone -> $thermo3
/RootClone.s.In



/RootClone -> $thermo1
/RootClone.s.In



/RootClone -> $thermo5
/RootClone.s.In

/RootClone.s.In.Fraction = 1 2 3
/RootClone.s.In

/RootClone -> $thermo4
/RootClone.s.In


/RootClone -> $thermo2
/RootClone.s.In

/RootClone.s.In.Fraction = 1 2 3 4
/RootClone.s.In


/RootClone ->
/RootClone.s.In


/RootClone -> $thermo2
/RootClone.s.In


copy /s /sep
paste /RootClone
/RootClone.sClone.In



copy /
paste /RootClone
/RootClone.RootClone.s.In
/RootClone.RootClone.RootClone.s.In



