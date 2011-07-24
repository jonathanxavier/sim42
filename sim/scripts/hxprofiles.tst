hx = Heater.HeatExchangerUA()
cd /
$thermo = VirtualMaterials.Advanced_Peng-Robinson
 . -> $thermo
cd thermo
/thermo + WATER HYDROGEN_SULFIDE METHANE ETHANE PROPANE VALERIC_ACID
cd /hx
/hx.side1.In.T = 200
/hx.side1.In.P = 1000
/hx.side1.In.MoleFlow = 500
cd /hx.side1.In.Fraction
/hx.side1.In.Fraction = 0.0 0.0 1 1 1 0.0
cd /hx
/hx.side0.Out.T = 105
/hx.side0.Out.P = 100
/hx.side0.Out.MoleFlow = 1000
cd /hx.side0.Out.Fraction
/hx.side0.Out.Fraction = 1 0.0 0.0 0.0 0.0 0.0
cd /hx
/hx.side0.DeltaP.DP = 0
/hx.side1.DeltaP.DP = 0
/hx.side1.Out.T = 150.0
/hx.heatTransfer0_1.Energy
/hx.heatTransfer0_1.Energy_Acum
/hx.heatTransfer0_1.LMTD
/hx.side0.T
/hx.side1.T

/hx.NumberSegments = 7
/hx.heatTransfer0_1.Energy
/hx.heatTransfer0_1.Energy_Acum
/hx.heatTransfer0_1.LMTD
/hx.side0.T
/hx.side1.T

copy /hx
paste /
/hxClone.side0.T