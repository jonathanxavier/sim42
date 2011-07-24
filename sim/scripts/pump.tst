# pump test
units SI
$thermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $thermo
thermo +  WATER

# A theoretical pump: calculate flow from delP -------------
pump = Pump.Pump()
cd pump
In.Fraction = 1.0
In.P = 101.325
In.T = 20

Out.P = 300.0
Efficiency = 0.8
In
Out

InQ = 300
In
Out
InQ

InQ = None
In.T = 
Out.T = 20.0247
In.MoleFlow = 205.10982071
In
Out
InQ

Out.T =
In.T = 20.0

cd /



# A real pump with one set of pump curves ------------------
# where head-flow-efficiency-power are restricted
realPump = Pump.PumpWithCurve()
cd realPump 

NumberTables = 1
PumpSpeed0 = 100.0
FlowCurve0 = 0.0 1000.0 2000.0 3000.0 4000.0 5000.0 6000.0 7000.0  # mass flow
HeadCurve0 = 0.0  10.0   20.0   30.0   40.0   50.0   60.0   70.0
EfficiencyCurve0 = 0.0 0.5 0.7 0.8 0.8 0.7 0.5 0.0

PumpSpeed = 30.0        # operating pump speed, not used here
In.Fraction = 1.0
In.P = 101.325
In.T = 20
In.VolumeFlow = 3600.0     # calculate delP from flow

In
Out
InQ

# calculate flow from delP
In.VolumeFlow = None
Out
Out.P = 400.0
Out
InQ


copy /pump /realPump
paste /
/pump.Out
/pumpClone.Out
/realPump.Out
/realPumpClone.Out
