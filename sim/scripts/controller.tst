# hysim 1.5 tutorial problem
units Field
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + Methane Ethane Propane
thermo + isoButane n-Butane isoPentane n-Pentane n-Hexane
thermo + n-Heptane n-Octane

Feed = Sensor.PropertySensor()
Feed.SignalType = T
Feed.In.T = 60
Feed.In.P = 600
Feed.In.MoleFlow = 144
Feed.In.Fraction = 70 20 10 9 8 7 6 5 4 3 

# Inlet separator
Sep = Flash.SimpleFlash()
Feed.Out -> Sep.In

Gas-Gas = Heater.HeatExchanger()
cd Gas-Gas
DeltaPH = 10
DeltaPC = 10
DeltaTHI = 10
cd ..

Sep.Vap -> Gas-Gas.InH

Chiller = Heater.HeatExchanger()
cd Chiller
DeltaPH = 10
DeltaPC = .1
DeltaTCI = 5  # 5 degree approach on the hot end
cd ..

Gas-Gas.OutH -> Chiller.InH

LTS = Flash.SimpleFlash()

LTS-Feed = Sensor.PropertySensor()
LTS-Feed.SignalType = T
LTS-Feed.In.T = 0

Chiller.OutH -> LTS-Feed.In
LTS-Feed.Out -> LTS.In

LTS.Vap -> Gas-Gas.InC

# dew point check - use mole balance to copy material of the sales gas
DP = Balance.BalanceOp()
cd DP
NumberStreamsInMat = 1
NumberStreamsOutMat = 1
BalanceType = 2 # Mole balance
cd ..

Gas-Gas.OutC -> DP.In0
DP.Out0.P = 815
DP.Out0.VapFrac = 1.
DewPoint = Sensor.PropertySensor()
DewPoint.SignalType = T
DP.Out0 -> DewPoint.In

# mix flash liquid streams
Mixer = Mixer.Mixer()
Sep.Liq0 -> Mixer.In0
LTS.Liq0 -> Mixer.In1

Tower_Feed = Sensor.PropertySensor()
Tower_Feed.SignalType = T
Mixer.Out -> Tower_Feed.In

Mixer.Out
DewPoint.Out
LTS-Feed.In.T
Feed.In.T

hold  # keep things in limbo while controllers are set up

#remove previous fixed values
LTS-Feed.In.T = None
Feed.In.T = None

DPControl = Controller.Controller()
DPControl.In -> DewPoint.Signal
DPControl.Out -> LTS-Feed.Signal
DPControl.Out = 0
DPControl.Target = 15
DPControl.StepSize = 10

TLiqCont = Controller.Controller()
TLiqCont.In -> Tower_Feed.Signal
TLiqCont.Out -> Feed.Signal
TLiqCont.Out = 60
TLiqCont.Target = 50
TLiqCont.StepSize = 10

go

copy /
paste /

Mixer.Out.T
DewPoint.Out.T
LTS-Feed.In.T
Feed.In.T
Tower_Feed.In.T

cd /RootClone
Mixer.Out.T
DewPoint.Out.T
LTS-Feed.In.T
Feed.In.T
Tower_Feed.In.T

cd /

# now let's make it fail
TLiqCont.Minimum = 53
TLiqCont.Out = 60
hold  # so it doesn't try and solve on each command

Feed.In.T
DewPoint.In.T
Tower_Feed.In.T

#Make sure disconnecting doesn't screw things up
#TLiqCont.In ->
#Tower_Feed.Signal =  10.0
