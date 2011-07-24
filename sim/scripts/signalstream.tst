
#Test signal stream
s1 = Stream.Stream_Signal()

#Should not be accepted. Type not set yet
s1.In = 100.0

#Set type
s1.SignalType = P


#set a value
s1.In = 100.0
s1.In
s1.Out


#Set thermo below
$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + WATER


#Add a clone
s1.pPort = Stream.ClonePort(0)
s1.pPort


#Clear value
s1.In = None
s1.In
s1.Out
s1.pPort


#Put a value to the clone
s1.pPort = 90
s1.In
s1.Out
s1.pPort

#Delete the clone
delete s1.pPort

#Try deleting the in and out ports
delete s1.In
delete s1.Out

#The In and Out ports are still there
s1.In
s1.Out
s1.pPort


#Create a new signal with an init script
s2 = Stream.Stream_Signal("SignalType = T")
s2.tPort = Stream.ClonePort(1)
s2.tPort = 230.0
s2.tPort
s2.In
s2.Out

#A new clone
s2.tPort2 = Stream.ClonePort(1)
s2.tPort
s2.tPort2
s2.In
s2.Out

#Delete the new clone
delete s2.tPort2
s2.tPort
s2.tPort2
s2.In
s2.Out


#Now lets propagate the types
h = Heater.Heater()
s3 = Stream.Stream_Signal("c = Stream.ClonePort(0)
ctrl = Controller.Controller()

h.DeltaP
s3.In
s3.c
s3.Out
ctrl.In


#Get the deltap type from the heater by connecting
h.DeltaP -> s3.In
h.DeltaP
s3.In
s3.c
s3.Out
ctrl.In

#Connect to the controller.
#Right now the type does not get propagated all the way to the controller
#which is a bug
s3.Out -> ctrl.In
h.DeltaP
s3.In
s3.c
s3.Out
ctrl.In


#Put a value in s3.Out. This fails. is it a bug ??
s3.Out = 10.0
h.DeltaP
s3.In
s3.c
s3.Out
ctrl.In


#Now set it in the in port
s3.In = 10.0
h.DeltaP
s3.In
s3.c
s3.Out
ctrl.In


#Clear it
s3.In = None
h.DeltaP
s3.In
s3.c
s3.Out
ctrl.In


#Set in hx
h.DeltaP = 5.0
h.DeltaP
s3.In
s3.c
s3.Out
ctrl.In


#Disconnect
h.DeltaP ->
h.DeltaP
s3.In
s3.c
s3.Out
ctrl.In

#The types remained... what to do??












