# A simple recycle test

# set up thermo - the name can be anything, I just use
# 'thermo' for convenience.  Essentially the rhs causes
# a thermo package to be created and assigned to the unit op
# owning the name thermo - in the case the base flowsheet

# Also note that for now spaces are needed around the operators (= + etc)
# A further also is that case is always significant

$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE ISOBUTANE n-BUTANE n-NONANE
units SI

# Add a stream
# for now creating a unit op requires module.class(), but this
# will be stream lined in the future
stream = Stream.Stream_Material()

# Make the stream In port current to save typing
# You can use cd (named because it is similar to change directory in
# Unix and DOS) to sub objects in this case first to the unit op stream
# and then to its port In.  This is just a typing convenience as everything
# could be done from the top level with full names i.e. stream.In.T = 360.15
cd stream.In

# Mole fractions can be enter indivually (Fraction.PROPANE = .25) or all
# together as below.
Fraction = .25 .25 .25 .25
T = 360.15 K
P = 715
MoleFlow = 3000

# Now create a recycle stream
cd /  # return to top level - only place a slash is used
recycle = Stream.Stream_Material()
cd recycle.In

# Estimate the values in the stream
# Estimates use the ~= operator in place of the normal = which
# fixes values
T ~= 460.15 K
P ~= 715
MoleFlow ~= 300
Fraction      # any object without an operator displays itself - here to get order
Fraction ~= 0 .5 0 .5
.             # a dot represents the current obj for display purposes

# add a mixer to combine the first stream with the recycle
cd /
mixer = Mixer.Mixer()

# ports are connected with the -> operator.  They would be disconnected
# by having an empty rhs.  Similarly "stream.In.T =" would remove any value
# for the stream In port Temperature
stream.Out -> mixer.In0
recycle.Out -> mixer.In1
mixer.Out

# add a separator
flash = Flash.SimpleFlash()
mixer.Out -> flash.In

# split the liquid from the flash
splitter = Split.Splitter()
flash.Liq0 -> splitter.In

# set the flow in one of the splitter outlets
splitter.Out1.MoleFlow = 200

# close the recycle
splitter.Out1 -> recycle.In

# All done - check some streams
recycle.Out
splitter.Liq0
#splitter.Liq0.Out
splitter.Out0
flash.In


#Copy and paste the recycle
sub = Flowsheet.SubFlowsheet()
innerflowsh = Flowsheet.Flowsheet()
copy /stream /recycle /mixer /flash /splitter
paste /sub
copy /stream /recycle /mixer /flash /splitter
paste /innerflowsh



#Now lets test flags for unconverged recycles that are not being re-solved
/MaxNumIterations = 4
/recycle.In.T ~= -87


#Add a second recycle
#The "annoying" flag regarding the previously unconverged recycle will keep on coming until 
#it is resolved.
c = Stream.Stream_Material()
cd c
cd /
split = Split.Splitter()
cd split
cd /split.In.Fraction
/split.In.Fraction = 1 1 1 1
/split.In.Fraction ~= 1 1 1 1
cd /split.In
T ~= 100
P = 100
MoleFlow ~= 100
cd /split
/split.FlowFraction1.Fraction = .4
/split.Out0 -> /c.In
/split.In -> /c.Out


#Only resolve split.
#It sould still flag the other recycle as unconverged
/split.Ignored = 1
/split.Ignored = None

#Only resolve recycle
#It should still flag the other recycle as unconverged
/recycle.Ignored = 1
/recycle.Ignored = None


#Do it again. Now this should have been converged and is not flagged anymore
#It should still flag the other recycle as unconverged
/recycle.Ignored = 1
/recycle.Ignored = None


#Unconverge the recycle again
/recycle.In.T ~= -87


#Delete /recycle. Nothing should break
delete /recycle

#Disconnect the other recycle. the unconv message sould go away
/split.In ->















