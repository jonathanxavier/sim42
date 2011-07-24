# tests multivariable balance solution
units SI
$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + PROPANE n-BUTANE
balance = Balance.BalanceOp()
balance

# set number of balance streams
balance.NumberStreamsInMat = 2
balance.NumberStreamsOutMat = 2

# make it a mole balance (not that it matters in this case)
balance.BalanceType = 2

# set compositions
cd balance
In0.Fraction
In0.Fraction = .3 .7
In1.Fraction = .4 .6
Out0.Fraction = .6 .4
Out1.Fraction = .8 .2

# give two flows - other two should be calculated
In0.MoleFlow = 1000
Out0.MoleFlow = 1500

# and they are
In1.MoleFlow
Out1.MoleFlow
