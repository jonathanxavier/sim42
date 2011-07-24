units SI
$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + Methane Ethane Propane

Feed = Stream.Stream_Material()
Feed.In.T = 20
Feed.In.P = 3000
Feed.In.MoleFlow = 100
Feed.In.Fraction = 70 20 10

valve = Valve.Valve()
Feed.Out -> valve.In
Outlet = Stream.Stream_Material()
valve.Out -> Outlet.In

Feed.pPort = Stream.SensorPort('P')
Outlet.pPort = Stream.SensorPort('P')
Feed.flowPort = Stream.SensorPort('MoleFlow')

cv_eqn = Equation.Equation()
cd cv_eqn
Equation = '''
Signal P(pIn, pOut) MoleFlow(f)
Signal Generic(cv)

pIn-pOut = 0.05*f^2
'''

cd /
cv_eqn.pIn -> Feed.pPort
cv_eqn.pOut -> Outlet.pPort
cv_eqn.f -> Feed.flowPort
Outlet.Out
Feed.In.MoleFlow = 200
Outlet.Out.P

# now try changing the equation so that cv is a variable
cv_eqn.Equation = '''
Signal P(pIn, pOut) MoleFlow(f)
Signal Generic(cv)

pIn-pOut = cv*f^2
'''

# try back calculating cv
Outlet.Out.P = 2500
cv_eqn.cv

# change feed flow again
Feed.In.MoleFlow = 100
cv_eqn.cv

# more than one expression is allowed in an Equation op
cv_eqn.Equation = '''
Signal P(pIn, pOut) MoleFlow(f)
Signal Generic(cv) DP(deltaP)

deltaP = pIn - pOut
deltaP = cv*f^2
'''

cv_eqn.cv
Outlet.Out.P = None
cv_eqn.deltaP = 400

cv_eqn.cv
Outlet.Out.P

