$thermo = VirtualMaterials.SRK
/ -> $thermo
#Peng-Robinson
thermo + METHANE WATER CARBON_MONOXIDE CARBON_DIOXIDE BGS-HYDROGEN 

units SI

# A Equilibrum reactor - isothermal, no pressure drop
rxn = EquiliReactor.EquilibriumReactor()          
cd /rxn
In.P = 100
In.T = 1000 K
In.MoleFlow = 5
In.Fraction = 0.4 0.6 0 0 0
#In.Fraction = 1.95862592784202e-002 9.93197945149974e-002 0.175637702766885 3.57267224820499e-002 0.669729520957648
Out.P = 100 
Out.T = 1000 K
'OutQ = 100000

NumberRxn = 2

Rxn0.Formula = Shift:1*3+1*4-!2-1*1
Rxn1.Formula = reforming:1*2+3*4-1*1-!0  

CalculationOption = 2

In
Out
OutQ

copy /
paste /
cd /RootClone.rxn
In
Out
OutQ

