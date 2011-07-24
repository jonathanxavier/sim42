# A few additions to flowsheet1
units SI

# set up thermo
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

# Add a couple of streams
stream1 = Stream.Stream_Material()
stream2 = Stream.Stream_Material()

# Make the stream1 In port current to save typing
cd stream1.In
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
# now lets add a couple of components
thermo + n-HEXANE n-DODECANE
# pretty much everything will have been forgotten
stream1.Out
# let's delete a component
thermo - n-Pentane
stream1.In.Fraction
stream1.In.Fraction.n-Hexane = .25
# Whoops, caps count, even in components - try again
stream1.In.Fraction.n-HEXANE = .25
stream1.In.Fraction.n-DODECANE = .25
# Whoops again - the composition is not normalized when
# individual component fractions are specified
stream1.In.Fraction = .25 0 0 .25 .25 .25

# stream1 should now be known
stream1.Out

# Now fix stream2 as well
stream2.In.Fraction = 0 .25 .25 0 .3 .2

# Now everything should be known again
flash.Vap
flash.Liq0
