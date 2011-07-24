clear

$th = VirtualMaterials.Advanced_Peng-Robinson
/ -> $th
th + WATER

pipe = PipeSegment.PipeSegment()


cd /pipe.In
P = 300 kPa
T = 300.0 K
Fraction = 1.0
MoleFlow = 1000.0

cd /pipe.Out
#P = 200.0
#T = 300.0


cd /
pipe.Diameter = 0.1
pipe.Length = 20.0
pipe.Roughness = 0.0001
pipe.Elevation0 = 0.0
pipe.Elevation1 = 0.0
pipe.OutQ = 0


pipe.In
pipe.Out

#Calculate flow
pipe.In.MoleFlow =
pipe.Out.P = 280 kPa
pipe.Out

#Calculate from deltaP
pipe.Out.P =
pipe.DeltaP = 10
pipe.Out

#Back to 
pipe.In.P =
pipe.Out.P = 270
pipe.In
pipe.Out

#Negative deltaP -> Negative flow calc
pipe.DeltaP = -10
pipe.Out

#Calculate with negative flow
pipe.DeltaP.DP =
pipe.Out.P =
pipe.In.P = 300 kPa
pipe.In.MoleFlow = -5000.0
pipe.In
pipe.Out

#Play with elevation now
pipe.In.MoleFlow = 9000.0
pipe.Out
pipe.Elevation1 = 10
pipe.Out
pipe.Elevation0 = 10
pipe.Out
pipe.Elevation0 = 20
pipe.Out


#Play with roughness
pipe.Elevation1 = 0
pipe.Elevation0 = 0
pipe.Roughness = 0.0001
pipe.Out
pipe.Roughness = 0.000001
pipe.Out
pipe.Roughness = 0.0
pipe.Out


#ignore kinetic and potential energy calcs
/pipe.In.T = 
/pipe.In.P = 
/pipe.In.H = -34353.018
/pipe.In
/pipe.Out

/pipe.IgnoreKineticAndPotential = 1
#The enthalpy should be passed directly from the In to Out
/pipe.Out

#Solve
/pipe.In.P = 300


copy /pipe
paste /

/pipeClone.In
/pipeClone.Out


#Resolve
/pipe.In.H = 
/pipe.In.T = 90
/pipe.Out



#Get rid of this
IgnoreKineticAndPotential = 0


#Remove energy
/pipe.OutQ.Energy = 1.0e7
/pipe.Out
/pipe.Energy
/pipe.T


#Solve with T out as a spec
/pipe.In.MoleFlow = 
/pipe.Out.T = 38
/pipe.Out


#Did not work, solve with other numerical method
/pipe.SolutionMethod = Secant
/pipe.Out
/pipe.Energy
/pipe.T


#Worked, now try again newton raphson but don't minimize error
/pipe.SolutionMethod = NewtonRaphson
/pipe.MinimizeError = 0
/pipe.TryLastConverged = 0
/pipe.Out
/pipe.Energy
/pipe.T


#Different solve scheme
/pipe.In.T = 
/pipe.In.MoleFlow = 9000
/pipe.Out
/pipe.Out
/pipe.Energy
/pipe.T


#Flip specs around
/pipe.In.P = 
/pipe.Out.T = 
/pipe.Out.P = 150
/pipe.In.T = 90
/pipe.Out
/pipe.Energy
/pipe.T
/pipe.u


#Change energy model
/pipe.EnergyLossModel = LinearTemperature

#Didn't finish. Add iterations
/pipe.MaxNumIterations = 50
/pipe.Out
/pipe.Energy
/pipe.T


#add sections
NumberSections = 5
/pipe.Out
/pipe.Energy
/pipe.T


#all u are equal
/pipe.EnergyLossModel = EqualU
/pipe.Out
/pipe.Energy
/pipe.T
/pipe.u

#Try secant method
/pipe.SolutionMethod = Secant
/pipe.Out
/pipe.Energy
/pipe.T
/pipe.u


#Now solve for energy
/pipe.OutQ.Energy = 
/pipe.Out.T = 38
/pipe.Out
/pipe.Energy
/pipe.T
/pipe.u


#Change numerical method
/pipe.SolutionMethod = NewtonRaphson
/pipe.Out

/pipe.EnergyLossModel = LinearTemperature
/pipe.Out
/pipe.T

/pipe.EnergyLossModel = LinearEnergy
/pipe.Out
/pipe.Energy


/pipe.Out.P = 
/pipe.In.P = 300
/pipe.Out


#Now spec u and change the energy models (nothing should change since u as a spec implies all u equal)
/pipe.Out.T = 
/pipe.U.U = 4.8846261
/pipe.u
/pipe.EnergyLossModel = LinearTemperature
/pipe.u
/pipe.EnergyLossModel = LinearEnergy
/pipe.u


#Back to energy spec but change nergy models
/pipe.U.U = 
/pipe.OutQ.Energy = 9931444.4
/pipe.Out
/pipe.Energy
/pipe.T
/pipe.u


/pipe.SolutionMethod = Secant
/pipe.EnergyLossModel = LinearTemperature
/pipe.T


/pipe.EnergyLossModel = EqualU
/pipe.SolutionMethod = NewtonRaphson
/pipe.T
/pipe.u







