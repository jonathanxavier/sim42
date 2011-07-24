$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + HYDROGEN WATER CARBON_MONOXIDE CARBON_DIOXIDE 
thermo + METHANE OXYGEN NITROGEN AMMONIA ETHANE PROPANE

units SI

# A conversion reactor - isothermal, no pressure drop
rxn = ConvRxn.ConvReactor()
cd /rxn
In.P = 0.0 psig
In.T = 70.08 F
In.MoleFlow = 21.1497
In.Fraction = 0. 0. 0. 0. 1.0 4.0 5.0 0. 0. 0.
DeltaP = 0
Out.T = 70.08 F

# Test 1 : Single reaction, complete reaction----------------------------------
# The default is 100 % conversion
NumberRxn = 1
# Note the use of quotes around CO2
Rxn0.Formula = CH4-Combustion:2*WATER+"CARBON DIOXIDE"-!METHANE-2*OXYGEN
# review reaction and results
Rxn0
Rxn0.Coeff
valueOf Rxn0.Coeff.GetValues
In
Out
OutQ

# Test 2  : Single reaction, 25% conversion-------------------------------------
Rxn0.Conversion = 0.25
Out

# Test 3  : Single reaction, in-sufficient O2 for complete reaction-------------
Rxn0.Conversion = 1.0
In.Fraction = 0. 0. 0. 0. 5.0 2.0 3.0 0. 0. 0.
Out

# test 4 : Multiple reactions, in-sufficient O2 for complete reaction--------------
IsoRxn.NumberRxn = 5
Rxn1.Formula = H2_Combustion:2*WATER-2*!HYDROGEN-OXYGEN
Rxn2.Formula = CO_Combustion:2*CARBON_DIOXIDE-2*!CARBON_MONOXIDE-OXYGEN
Rxn3.Formula = C2_Combustion:3*WATER+2*CARBON_DIOXIDE-!ETHANE-3.5*OXYGEN
# test5 : Alternative formula input
# 4*WATER+3*CARBON_DIOXIDE-!PROPANE-5*OXYGEN
Rxn4.Formula = C3_Combustion:4*1+3*3-!9-5*5
Rxn4.Coeff
In.Fraction = .1 .1 .1 .1 .1 .1 .1 .1 .1 .1
In.MoleFlow = 10.0
Out
OutQ

# test 5 : adibatic reaction-----------------------------------------------------
Out.T =
OutQ = 0.0
Out

# test 6 : Compae with literature result-----------------------------------------
# burns 1 mole of C3 with 28 moles of air adibatically 
# literature outlet T = 1878.8 C
In.Fraction = 0 0 0 0 0 0.202759 0.7628 0 0 0.034482
In.P = 1 atm
In.T = 25 C
OutQ = 0.0
In.MoleFlow = 29
In
IsoRxn.Out
IsoRxn.OutQ
Out

# test 7 : partial spec----------------------------------------------------------
# specify inlet composition, should be able to calculate outlet composition
In.P =
In.T =
In.MoleFlow =
OutQ.Energy =
Out

# test 8 : backward calc---------------------------------------------------------
Out.P = 101.325
Out.T = 2000 C
Out.MoleFlow = 30
In.T = 29 C
DeltaP = 5 psi
In
Out
OutQ

