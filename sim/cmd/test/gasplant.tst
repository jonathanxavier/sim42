# hysim 1.5 tutorial problem
units Field
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + Methane Ethane Propane
thermo + isoButane n-Butane isoPentane n-Pentane n-Hexane
thermo + n-Heptane n-Octane

Feed = Stream.Stream_Material()
Feed.In.T = 60
Feed.In.P = 600
Feed.In.MoleFlow = 144
Feed.In.Fraction = 70 20 10 9 8 7 6 7 4 3 

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

# create a nested Flowsheet for the LTS and dewpoint calc
# this prevents the controller solver from resolving everything during
# its iterations

ContFS = Flowsheet.Flowsheet()
cd ContFS

LTS = Flash.SimpleFlash()

#LTS-Feed = Sensor.PropertySensor()
#LTS-Feed.SignalType = T
LTS-Feed = Stream.Stream_Material()
LTS-Feed.Signal = Stream.SensorPort('T')

LTS-Vap = Stream.Stream_Material()
LTS-Vap.DPFeed = Stream.ClonePort(0)   # outgoing clone for dew point

/Chiller.OutH -> LTS-Feed.In
LTS-Feed.Out -> LTS.In

LTS.Vap -> LTS-Vap.In
LTS-Vap.Out -> /Gas-Gas.InC

# dew point check - use mole balance to copy material of the sales gas
DP = Balance.BalanceOp()
cd DP
NumberStreamsInMat = 1
NumberStreamsOutMat = 1
BalanceType = 2 # Mole balance
cd ..

LTS-Vap.DPFeed -> DP.In0
DP.Out0.P = 815
DP.Out0.VapFrac = 1.
DewPoint = Sensor.PropertySensor()
DewPoint.SignalType = T
DP.Out0 -> DewPoint.In

DPControl = Controller.Controller()
DPControl.In -> DewPoint.Signal
DPControl.Out -> LTS-Feed.Signal
DPControl.Out = 0
DPControl.Target = 15
DPControl.StepSize = 10

# return to root flowsheet
cd /

# mix flash liquid streams
Mixer = Mixer.Mixer()
Sep.Liq0 -> Mixer.In0
ContFS.LTS.Liq0 -> Mixer.In1

deprop = Tower.Tower()
deprop.Stage_0 + 10  # twelve stages`

cd deprop.Stage_0
v = Tower.VapourDraw()
v.Port.P = 200
reflux = Tower.RefluxRatioSpec()
reflux.Port = 1.0

cond = Tower.EnergyFeed(0)
estT = Tower.Estimate('T')
estT.Value = 40

cd ../Stage_5
f = Tower.Feed()
/Mixer.Out -> f.Port

cd ../Stage_11
l = Tower.LiquidDraw()
l.Port.P = 205
l.Port.Fraction.PROPANE = .02

reb = Tower.EnergyFeed(1)
estT = Tower.Estimate('T')
estT.Value = 200

cd ..

/overhead = Stream.Stream_Material()
/overhead.In -> Stage_0.v.Port

/bottoms = Stream.Stream_Material()
/bottoms.In -> Stage_11.l.Port



TryToSolve = 1  # start calculation

/overhead.Out
/bottoms.Out


# add refrigeration
# fix the chiller cold outlet as boiling refrigerant
cd /Chiller.OutC
VapFrac = 1
Fraction = 0 0 1 0 0 0 0 0 0 0
cd /
Chiller.DeltaTHI = 30

# add valve
V-100 = Valve.Valve()
V-100.Out -> Chiller.InC

# add condensor
E-103 = Heater.Cooler()
E-103.Out -> V-100.In

# Condensor outlet is bubble point liquid at air cooler kind of T
E-103.Out.T = 120
E-103.Out.VapFrac = 0
E-103.DeltaP = 5

V-100.Out

# compressor isn't needed to calculate flows, but add it for completeness
K-100 = Compressor.Compressor()
K-100.Efficiency = .75

Chiller.OutC -> K-100.In

K-100.Out -> E-103.In
K-100.Out
E-103.OutQ


# try making some changes
cd /
Feed.In.T = 55
bottoms.Out
ContFS.DewPoint.In.T

ContFS.DPControl.Target = 10
ContFS.DewPoint.In.T
bottoms.Out



copy /
paste /
cd /RootClone
ContFS.DewPoint.In.T
bottoms.Out
#Feed.In.T = 55
#bottoms.Out
#ContFS.DewPoint.In.T
cd /



