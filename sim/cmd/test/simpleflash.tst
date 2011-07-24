# Simple flash test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

flash = Flash.SimpleFlash()
cd flash.In
Fraction = .25 .25 .25 .25
T = 0 C
P = 101.325
MoleFlow = 10
cd ..
# dump the results
Vap   # Vapour stream
Liq0  # Liquid stream
In

cd /

#Add a test here to make sure that estimates do not back propagate values
s = Stream.Stream_Material()
s.Out -> flash.In

#We should have values in s.Out as passed (backpropagated)
s.Out
flash.In

#Now estimate one of the values in flash.In
flash.In.T ~= 0 C

#Nothing should be in s.Out
s.Out

#Disconnect and reconnect
s.Out ->
s.Out
s.Out -> flash.In
s.Out


#Now re specify the value
flash.In.State = 0 #Make it a normal port
flash.In.T = 0 C
s.Out

#Now estimate P and Fraction
flash.In.P ~= 101.325 kPa
flash.In.Fraction ~= .25 .25 .25 .25
s.Out

#Un estimate only P
flash.In.P = 101.325 kPa
s.Out

#Remove composition altogether
flash.In.Fraction = 
flash.In.State = 0
s.Out

#Make it solve again
flash.In.Fraction = .25 .25 .25 .25
flash.In


#Test copy and paste
copy /flash /s
paste /
/flashClone.In
/sClone.Out
