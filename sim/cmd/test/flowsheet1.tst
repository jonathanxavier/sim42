# A simple flowsheet
units SI

# set up thermo
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE ISOBUTANE n-BUTANE n-PENTANE

# Add a couple of streams
stream1 = Stream.Stream_Material()
stream2 = Stream.Stream_Material()

# Make the stream1 In port current to save typing
cd stream1.In
Fraction  # print fractions to figure out order
Fraction = .5 0 0 .5  # assign mole fractions
T = 187
P = 715
MoleFlow = 3000

# Make the other stream In port current
cd /stream2.In
Fraction = 0 .5 .5 0
T = -73
P = 715
MoleFlow = 3000
cd /  # return to top level flowsheet

# now mix the streams
mixer = Mixer.Mixer()   # add a mixer op
stream1.Out -> mixer.In0 # connect the streams to it
stream2.Out -> mixer.In1
mixer.Out  # have a look at the combined outlet

# add a flash drum
flash = Flash.SimpleFlash()
mixer.Out -> flash.In

# have a look at the flash outlets
flash.Vap
flash.Liq0

#Test copy and paste
#The whole thing
copy /stream1 /stream2 /mixer /flash
paste /
/stream2Clone.In
/mixerClone.Out0
/flashClone.Vap


#copy part of it
copy  /stream2 /mixer /flash
paste /
/stream2Clone_1.In
/mixerClone_1.Out0
/flashClone_1.Vap


#copy part of it again but
copy  /stream2 /flash
paste /
/stream2Clone_2.In
/flashClone_2.Vap


#Now copy the whole flowsheet
copy /
paste /


#Now copy into a subflowsheet
cd /
sub = Flowsheet.SubFlowsheet()
copy /stream1 /stream2 /mixer /flash
paste /sub

#Now clone the subflowsheet
copy /sub
paste /

#Now test cut and paste
sub2 = Flowsheet.SubFlowsheet()
cut /stream1Clone /stream2Clone /mixerClone /flashClone
paste sub2


