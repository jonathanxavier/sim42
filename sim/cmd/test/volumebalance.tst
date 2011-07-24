$thermo = VirtualMaterials.Advanced_Peng-Robinson
 . -> $thermo
cd thermo
cd $
cd /thermo
/thermo + METHANE ETHANE PROPANE n-HEXANE n-HEPTANE n-OCTANE n-NONANE
cd /
mixer1 = Mixer.Mixer()
cd mixer1
NumberStreamsIn = 3
/mixer1.In0.P = 100
/mixer1.In1.P = 110
/mixer1.In2.P = 105
cd /mixer1.In0.Fraction
/mixer1.In0.Fraction = 0 0 0 1 1 1 1
cd /mixer1
/mixer1.In0.T = 30
cd /mixer1.In1.Fraction
/mixer1.In1.Fraction = 0.0 0.0 0.0 2 3 1 2
cd /mixer1
/mixer1.In1.T = 20
cd /mixer1.In2.Fraction
/mixer1.In2.Fraction = 0.0 0.0 0.0 5 6 3 5
cd /mixer1
/mixer1.Out.T = 40
/mixer1.In0.VolumeFlow = 20
/mixer1.In1.VolumeFlow = 40
/mixer1.Out.VolumeFlow = 150
/mixer1.Out.T = 

#Solve for vol in In2 and composition in Out
/mixer1.In2.T = 40
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out


#Solve for vol in Out and composition in In2
/mixer1.In2.T = 
/mixer1.Out.VolumeFlow = 
cd /mixer1.In2.Fraction
/mixer1.In2.Fraction = None
cd /mixer1
cd /mixer1.Out.Fraction
/mixer1.Out.Fraction = 0.0 0.0 0.0 0.25784 0.32313 0.16119 0.25784
cd /mixer1
/mixer1.In2.VolumeFlow = 90.016371
/mixer1.Out.T = 33.347474
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out


#Solve for vol in In1 and composition in In2
/mixer1.In1.VolumeFlow = 
/mixer1.Out.VolumeFlow = 150
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out


#Solve for vol in In0 and composition in In2
/mixer1.In0.VolumeFlow = 
/mixer1.In1.VolumeFlow = 40
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out



#Solve for vol in In0 and composition in In1
/mixer1.In1.VolumeFlow = 
/mixer1.In1.Fraction = None
/mixer1.In2.Fraction = 0.0 0.0 0.0 0.26316 0.31579 0.15789 0.26316
/mixer1.In1.T = 
/mixer1.In2.T = 40
/mixer1.In0.VolumeFlow = 20
/mixer1.In0.VolumeFlow = 
/mixer1.In1.VolumeFlow = 40
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out


#Solve for vol in In2 and composition in In1
/mixer1.In2.VolumeFlow = 
/mixer1.In0.VolumeFlow = 20
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out


#Now change specs to std vol flow
/mixer1.Out.VolumeFlow = 
/mixer1.Out.StdLiqVolumeFlow = 150
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out



/mixer1.In1.VolumeFlow = 
/mixer1.In1.StdLiqVolumeFlow = 40
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out


/mixer1.In0.VolumeFlow = 
/mixer1.In0.StdLiqVolumeFlow = 20
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out


#Deleting temperatures should still be able to balance moles
/mixer1.Out.T = 
/mixer1.In2.T = 
/mixer1.In0.T = 
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out


#Changing specs should work
/mixer1.In0.StdLiqVolumeFlow = 
/mixer1.In2.StdLiqVolumeFlow = 90
/mixer1.Out.StdLiqVolumeFlow = 
/mixer1.In0.StdLiqVolumeFlow = 20
/mixer1.In0
/mixer1.In1
/mixer1.In2
/mixer1.Out









