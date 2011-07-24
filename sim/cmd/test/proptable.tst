optimizecode 1
maxversions 0
units Field
/LiquidPhases = 2
/StdLiqVolRefT = 288.15 
 /StdLiqVolRefT = 60 F
/RecycleDetails = 1
displayproperties
displayproperties VapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow StdGasVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor
commonproperties
commonproperties + ZFactor P T MolecularWeight MassDensity StdLiqMolarVolVapFrac T P MoleFlow MassFlow VolumeFlow StdLiqVolumeFlow StdGasVolumeFlow Energy H S MolecularWeight MassDensity Cp ThermalConductivity Viscosity molarV ZFactor
$VMGThermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $VMGThermo
/SolidPhases = 0
$VMGThermo + METHANE
$VMGThermo + ETHANE
$VMGThermo + PROPANE
$VMGThermo + n-BUTANE
$VMGThermo + n-PENTANE
$VMGThermo + n-HEXANE
$VMGThermo + n-HEPTANE
$VMGThermo + WATER
$VMGThermo + CARBON_DIOXIDE
/PT1 = Properties.PropertyTable()
'/PT1.In.Fraction' =   .1  .1  .2  .1  .1  .1  .1  .1  .1
/PT1.XProperty = PRESSURE
/PT1.XMin =  10
/PT1.XMax =  20
/PT1.XPoints = 4
/PT1.YProperty = TEMPERATURE
/PT1.YMin =  60
/PT1.YMax =  100
/PT1.YPoints = 3
/PT1.Phase = FEED

#One property
/PT1.ZProperty = CP
valueOf /PT1.TableXYZCP.convertedArrayRep

#More than one property
/PT1.ZProperty = CP CV ENTHALPY ENTROPY ZFACTOR
valueOf /PT1.TableXYZCP.convertedArrayRep
valueOf /PT1.TableXYZCV.convertedArrayRep
valueOf /PT1.TableXYZENTHALPY.convertedArrayRep
valueOf /PT1.TableXYZENTROPY.convertedArrayRep
valueOf /PT1.TableXYZZFACTOR.convertedArrayRep

#Change phases
/PT1.Phase = LIQUID
valueOf /PT1.TableXYZCP.convertedArrayRep
valueOf /PT1.TableXYZCV.convertedArrayRep
valueOf /PT1.TableXYZENTHALPY.convertedArrayRep
valueOf /PT1.TableXYZENTROPY.convertedArrayRep
valueOf /PT1.TableXYZZFACTOR.convertedArrayRep


/PT1.Phase = VAPOR
valueOf /PT1.TableXYZCP.convertedArrayRep
valueOf /PT1.TableXYZCV.convertedArrayRep
valueOf /PT1.TableXYZENTHALPY.convertedArrayRep
valueOf /PT1.TableXYZENTROPY.convertedArrayRep
valueOf /PT1.TableXYZZFACTOR.convertedArrayRep


/PT1.Phase = LIQUID2
valueOf /PT1.TableXYZCP.convertedArrayRep
valueOf /PT1.TableXYZCV.convertedArrayRep
valueOf /PT1.TableXYZENTHALPY.convertedArrayRep
valueOf /PT1.TableXYZENTROPY.convertedArrayRep
valueOf /PT1.TableXYZZFACTOR.convertedArrayRep


/PT1.Phase = FEED
valueOf /PT1.TableXYZCP.convertedArrayRep
valueOf /PT1.TableXYZCV.convertedArrayRep
valueOf /PT1.TableXYZENTHALPY.convertedArrayRep
valueOf /PT1.TableXYZENTROPY.convertedArrayRep
valueOf /PT1.TableXYZZFACTOR.convertedArrayRep


#With VF at the end BULK
/PT1.ZProperty = CP CV ENTHALPY ENTROPY ZFACTOR VF
valueOf /PT1.TableXYZCP.convertedArrayRep
valueOf /PT1.TableXYZCV.convertedArrayRep
valueOf /PT1.TableXYZENTHALPY.convertedArrayRep
valueOf /PT1.TableXYZENTROPY.convertedArrayRep
valueOf /PT1.TableXYZZFACTOR.convertedArrayRep
valueOf /PT1.TableXYZVF.convertedArrayRep


#With VF in the middle BULK
/PT1.ZProperty = CP CV ENTHALPY ENTROPY ZFACTOR VF VISCOSITY
valueOf /PT1.TableXYZCP.convertedArrayRep
valueOf /PT1.TableXYZCV.convertedArrayRep
valueOf /PT1.TableXYZENTHALPY.convertedArrayRep
valueOf /PT1.TableXYZENTROPY.convertedArrayRep
valueOf /PT1.TableXYZZFACTOR.convertedArrayRep
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep



#With VF at the beginning BULK
/PT1.ZProperty = VF VISCOSITY
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep


#Now only VF in all phases
/PT1.ZProperty = VF
/PT1.Phase = VAPOR
valueOf /PT1.TableXYZVF.convertedArrayRep

/PT1.Phase = LIQUID
valueOf /PT1.TableXYZVF.convertedArrayRep

/PT1.Phase = LIQUID2
valueOf /PT1.TableXYZVF.convertedArrayRep

/PT1.Phase = VAPOR
valueOf /PT1.TableXYZVF.convertedArrayRep


#With VF at the beginning all phases
/PT1.ZProperty = VF VISCOSITY
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep

/PT1.Phase = LIQUID
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep

/PT1.Phase = LIQUID2
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep


#With VF in the middle all phases
/PT1.ZProperty = ENTHALPY VF VISCOSITY
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep

/PT1.Phase = LIQUID
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep

/PT1.Phase = LIQUID2
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep

#With VF at the end all phases
/PT1.ZProperty = VISCOSITY VF
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep

/PT1.Phase = LIQUID
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep

/PT1.Phase = LIQUID2
valueOf /PT1.TableXYZVF.convertedArrayRep
valueOf /PT1.TableXYZVISCOSITY.convertedArrayRep

copy /PT1
paste /
valueOf /PT1Clone.TableXYZVISCOSITY.convertedArrayRep