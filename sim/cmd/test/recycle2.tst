# A recycle test with information flowing both ways
# through the recycle

units SI
# set up thermo
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-NONANE

# Add a stream
stream = Stream.Stream_Material()

# Make the stream In port current to save typing
cd stream.In
Fraction = .25 .25 .25 .25
T = 360.15 K
P = 715
# Note that flow is not known for the feed stream

# Now create a recycle stream 
cd /
recycle = Stream.Stream_Material()

# add a mixer to combine the first stream with the recycle
cd /
mixer = Mixer.Mixer()
stream.Out -> mixer.In0
recycle.Out ->mixer.In1
recycle.Out -> mixer.In1
mixer.Out

# add a separator
flash = Flash.SimpleFlash()
mixer.Out -> flash.In

# instead of estimating the recycle stream, I will estimate
# the inlet port of the flash for everything but flow
# I will just use the same values as the feed stream
cd flash.In
# Note use of ~= to mean estimate
Fraction ~= .25 .25 .25 .25
T ~= 360.15 K
cd /

# fix the flow of the vapour from the flash
flash.Vap.MoleFlow = 1652.682

# split the liquid from the flash
splitter = Split.Splitter()
flash.Liq0 -> splitter.In

# set the flow in one of the splitter outlets
splitter.Out1.MoleFlow = 200
splitter.Out1.P = 715

# close the recycle
splitter.Out1 -> recycle.In

# still needs balance to figure out flow
balance = Balance.BalanceOp()
# just need a mole balance
balance.BalanceType = 2

#set number of balance streams
balance.NumberStreamsInMat = 2
balance.NumberStreamsOutMat = 1

# connect the dangling ends of the streams to the balance
stream.In -> balance.Out0
flash.Vap -> balance.In1
splitter.Out0 -> balance.In0

# All done - check some streams
recycle.Out
splitter.Liq0
splitter.Liq0.Out
splitter.Out0
flash.In
stream.Out

# reset the temperature
stream.In.T = 400 K

# check streams again
recycle.Out
splitter.Liq0
splitter.Liq0.Out
splitter.Out0
flash.In
stream.Out

#Copy the whole flowsheet
copy /
paste /
copy /
paste /

/flash.In.State = 0
/flash.In
/flash.In.State = 1
/flash.In


