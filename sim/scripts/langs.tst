language Spanish
$thermo = VirtualMaterials.Advanced_Peng-Robinson
 . -> $thermo
cd thermo
/thermo + PROPANE ISOBUTANE n-BUTANE
language Portuguese
/thermo - ISOBUTANE n-BUTANE
/thermo + ETHANE ISOBUTANE
language French
/thermo + n-BUTANE ISOPENTANE
cd $
cd $
thermo2 = VirtualMaterials.RK
cd thermo2
$thermo2 + PROPANE ISOBUTANE n-BUTANE
language Malay
$thermo2 - ISOBUTANE
cd /
language Spanish
stream = Stream.Stream_Material()
cd stream
language Malay
/stream.In.T = 20
/stream.In.P = 101
cd /stream.In.Fraction
/stream.In.Fraction = 0.0 2 3 0.0 0.0
cd /
language Portuguese
mix = Mixer.Mixer()
cd mix
/mix.In0 -> /stream.Out
language English
