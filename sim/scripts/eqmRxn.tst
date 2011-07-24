$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + BGS-HYDROGEN BGS-WATER BGS-CARBON_MONOXIDE BGS-CARBON_DIOXIDE 
thermo + BGS-METHANE BGS-OXYGEN BGS-NITROGEN AMMONIA BGS-ETHANE BGS-PROPANE

units SI

# A Equilibrum reactor - isothermal, no pressure drop
#rxn = EquiliReactor.IsothermalEquiliReactor()           #IsothermalEqmReactor()
rxn = EquiliReactor.EquilibriumReactor()          
cd /rxn
In.P = 100 
In.T = 80 
In.MoleFlow = 8 lbmole/h
In.Fraction = 1 1 1 1 1 1 1 1 0 0 
DeltaP = 10 

# Test 1 : Testing Outlet T spec  ----------------------------------

NumberRxn = 2
Rxn0.Formula = Reforming:3*0+1*2-1*1-!4
Rxn1.Formula =  Shift:1*3+1*0-!2-1*1
Rxn0.EqmConst.Table.Series0  =  366.5 533.15 699.8 810.9 866.5 922.04 977.6 1033.15 1199.8 1310.9 1477.6 K
Rxn0.EqmConst.Table.Series1  =  7.81e-19 2.17e-9 0.000266 0.049 0.4098 2.679 14.26 63.43 2464 17010 178400
Rxn1.EqmConst.Table.Series0  =  366.5 422.04 477.6 505.4 588.7 616.5 727.6 838.7 1088.7 1227.6 1477.6 K
Rxn1.EqmConst.Table.Series1  =  4523 783.6 206.8 119 31.44 22 7.05 3.13 0.9813 0.647 0.3843
CalculationOption = 1
Out.T = 80 

In
Out
OutQ

# Test 2 : Testing Outlet Q spec  ----------------------------------
Out.T = None
OutQ = 10000 
Out
OutQ

# Test 3 Negative K value in K table, Should not solve -------------------------------------------
Rxn0.EqmConst.Table.Series0  =  366.5 533.15 699.8 810.9 866.5 922.04 977.6 1033.15 1199.8 1310.9 1477.6 K
Rxn0.EqmConst.Table.Series1  =  -7.81e-19 -2.17e-9 -0.000266 -0.049 -0.4098 -2.679 -14.26 -63.43 -2464 -17010 -178400
#Rxn1.EqmConst.Table.Series0  =  366.5 422.04 477.6 505.4 588.7 616.5 727.6 838.7 1088.7 1227.6 1477.6 K
#Rxn1.EqmConst.Table.Series1  =  -4523 -783.6 -206.8 -119 -31.44 -22 -7.05 -3.13 -0.9813 -0.647 -0.3843
Ignored = 1
Ignored = None
Out
OutQ


# Test 4 : Given No Flow at Temperature spec. Should partially solve ----------------------------------
Rxn0.EqmConst.Table.Series0  =  366.5 533.15 699.8 810.9 866.5 922.04 977.6 1033.15 1199.8 1310.9 1477.6 K
Rxn0.EqmConst.Table.Series1  =  7.81e-19 2.17e-9 0.000266 0.049 0.4098 2.679 14.26 63.43 2464 17010 178400
In.MoleFlow = None
OutQ = None
Out.T = 80
Out
OutQ

# Test 5 : Given No Flow at Reaction Heat spec. Should not solve ----------------------------------
Out.T = None
OutQ = -10000
Out
OutQ

# Test 6 : Given Inlet and Outlet Pressures ----------------------------------
OutQ = -5150 
In.P = None
In.MoleFlow = 8 lbmole/h
Out.P = 90
Out
OutQ


#Due to an old mistake in the sign of Q, now we have to support the following parameter
QExothermicIsPositive = 0
Out
OutQ

QExothermicIsPositive = 1
OutQ = 5150
Out

copy /rxn
paste /
/rxnClone.Out