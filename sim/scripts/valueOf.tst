# Create a pre-heater, from heater.tst
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

preHeater = Heater.Heater()
preHeater
cd preHeater
In.Fraction
In.Fraction = .25 .25 .25 .25
In.P = 101.325
In.H = -7200
In.T
In.MoleFlow = 10
InQ.Energy = 1000000
DeltaP
DeltaP.DP = 0.1
In
Out
InQ
cd /

#create a mixer and splitter
mixer = Mixer.Mixer()
splitter = Split.Splitter()

#connect the pre-heater to the mixer
preHeater.Out -> mixer.In0

valueOf preHeater.In.Fraction.processValue		# composition
valueOf preHeater.compoundNames                         # compound name
valueOf preHeater.LiquidPhases.processValue		# parameter
valueOf preHeater.In.path				# port
valueOf preHeater.In.properties.key			# user dictionary
valueOf preHeater.DeltaP.properties.key                 # dictionary

valueOf preHeater.DeltaP.type
valueOf preHeater.DeltaP.DP.processValue		#DeltaP is the signal 
valueOf preHeater.InQ.Energy.processValue
valueOf preHeater.InQ.processValue
valueOf preHeater.In.MoleFlow.processValue

# everything about one Basic property
valueOf mixer.In0.P.processValue        #current process variable value
valueOf mixer.In0.P.value		#internal current value
valueOf mixer.In0.P.calcStatus
valueOf mixer.In0.P.name
valueOf mixer.In0.P.calcType
valueOf mixer.In0.P.unitType
valueOf mixer.In0.P.scaleFactor
valueOf mixer.In0.P.minValue
valueOf mixer.In0.VapFrac.maxValue

# a full material port values
valueOf preHeater.Out.T.processValue
valueOf preHeater.Out.P.processValue
valueOf preHeater.Out.molarV.processValue
valueOf preHeater.Out.H.processValue
valueOf preHeater.Out.S.processValue
valueOf preHeater.Out.VapFrac.processValue
valueOf preHeater.Out.MoleFlow.processValue
valueOf preHeater.Out.MassFlow.processValue
valueOf preHeater.Out.Energy.processValue
valueOf preHeater.Out.Fraction.processValue


