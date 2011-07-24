import string, re
#from ThermoAdmin import *
from vmgunits import units

#supported hypo string definitions
def GetSimHypoStrings():
    _hypoStrings = ['Name',
                    'Formula',
                    'CASN',
                    'ChemicalFamily',
                    'UNIFACStructure',
                    'PhysicalState',
                    'EnthalpyOfCombustionState',
                    'SolubilityStatus',
                    'AutoIgnitionTemperatureStatus',
                    'FlashPointStatus',
                    'SolubilityInWaterStatus',
                    'ExplosionLimitStatus',
                    'SolubilityInWaterWithNaClStatus',
                    'Alias',
                    'Notes',
                    'Owner',
                    'CreationInfo']
    return _hypoStrings

def GetSimHypoLongs():
    _hypoLongs = ['ElectricCharge',
                  'GammaNormalization',
                  'LiquidThermalConductivityEqType']
    return _hypoLongs

def GetSimHypoDoubles():
    _hypoDoubles = ['AcentricFactor',
                    'AdsorptionAt10ppm(vol)',
                    'AdsorptionInActivatedCarbonA',
                    'AdsorptionInActivatedCarbonB',
                    'AdsorptionInActivatedCarbonC',
                    'Antoine5LogA',
                    'Antoine5LogB',
                    'Antoine5LogC',
                    'Antoine5LogD',
                    'Antoine5LogE',
                    'Antoine5LogTmax',
                    'Antoine5LogTmin',
                    'AutoIgnitionTemperature',
                    'ConcentrationInGas@298And1AtmMax',
                    'ConcentrationInGas@298And1AtmMin',
                    'CriticalCompressibility',
                    'CriticalPressure',
                    'CriticalTemperature',
                    'CriticalVolume',
                    'DiffusionCoefficientInAirA',
                    'DiffusionCoefficientInAirB',
                    'DiffusionCoefficientInAirC',
                    'DiffusionCoefficientInAirTmax',
                    'DiffusionCoefficientInAirTmin',
                    'DiffusionCoefficientInWaterA',
                    'DiffusionCoefficientInWaterB',
                    'DiffusionCoefficientInWaterTmax',
                    'DiffusionCoefficientInWaterTmin',
                    'DipoleMoment',
                    'EnthalpyOfCombustionAt298',
                    'EnthalpyOfFusion',
                    'EnthalpyOfVapourizationA',
                    'EnthalpyOfVapourizationB',
                    'EnthalpyOfVapourizationN',
                    'EnthalpyOfVapourizationTmax',
                    'EnthalpyOfVapourizationTmin',
                    'FlashPointTemperature',
                    'FreezingPoint',
                    'GasThermalConductivityA',
                    'GasThermalConductivityB',
                    'GasThermalConductivityC',
                    'GasThermalConductivityTmax',
                    'GasThermalConductivityTmin',
                    'GasViscosityA',
                    'GasViscosityB',
                    'GasViscosityC',
                    'GasViscosityTmax',
                    'GasViscosityTmin',
                    'HaydenOConnell',
                    'HenryConstantInWaterTemperature',
                    'HTIdealGasHeatCapacityA',
                    'HTIdealGasHeatCapacityB',
                    'HTIdealGasHeatCapacityC',
                    'HTIdealGasHeatCapacityD',
                    'HTIdealGasHeatCapacityTmax',
                    'HTIdealGasHeatCapacityTmin',
                    'IdealGasEnthalpyOfFormation@298',
                    'IdealGasEnthalpyOfFormationA',
                    'IdealGasEnthalpyOfFormationB',
                    'IdealGasEnthalpyOfFormationC',
                    'IdealGasEnthalpyOfFormationTmax',
                    'IdealGasEnthalpyOfFormationTmin',
                    'IdealGasGibbsFreeEnergyOfFormation@298',
                    'IdealGasGibbsFreeEnergyOfFormationA',
                    'IdealGasGibbsFreeEnergyOfFormationB',
                    'IdealGasGibbsFreeEnergyOfFormationC',
                    'IdealGasGibbsFreeEnergyOfFormationTmax',
                    'IdealGasGibbsFreeEnergyOfFormationTmin',
                    'ImmediatelyDangerousToLifeHealthmgm3',
                    'ImmediatelyDangerousToLifeHealthppm',
                    'LiquidDensity@298',
                    'LiquidHeatCapacityA',
                    'LiquidHeatCapacityB',
                    'LiquidHeatCapacityC',
                    'LiquidHeatCapacityD',
                    'LiquidHeatCapacityTmax',
                    'LiquidHeatCapacityTmin',
                    'LiquidThemalExpansionTc',
                    'LiquidThermalConductivityA',
                    'LiquidThermalConductivityB',
                    'LiquidThermalConductivityC',
                    'LiquidThermalConductivityTmax',
                    'LiquidThermalConductivityTmin',
                    'LiquidThermalExpansion@298',
                    'LiquidThermalExpansionA',
                    'LiquidThermalExpansionM',
                    'LiquidThermalExpansionTmax',
                    'LiquidThermalExpansionTmin',
                    'LiquidViscosityA',
                    'LiquidViscosityB',
                    'LiquidViscosityC',
                    'LiquidViscosityD',
                    'LiquidViscosityTmax',
                    'LiquidViscosityTmin',
                    'Log10KOW',
                    'LowerExplosionLimitVol',
                    'MaxP',
                    'MaxT',
                    'MinP',
                    'MinT',
                    'MolecularWeight',
                    'NormalBoilingPoint',
                    'PermissibleExposureLimitOSHAmgm3',
                    'PermissibleExposureLimitOSHAppm',
                    'Poly5IdealGasCpA',
                    'Poly5IdealGasCpB',
                    'Poly5IdealGasCpC',
                    'Poly5IdealGasCpD',
                    'Poly5IdealGasCpE',
                    'Poly5IdealGasCpTmax',
                    'Poly5IdealGasCpTmin',
                    'RackettLiquidDensityA',
                    'RackettLiquidDensityB',
                    'RackettLiquidDensityN',
                    'RackettLiquidDensityTc',
                    'RackettLiquidDensityTmax',
                    'RackettLiquidDensityTmin',
                    'RadiusOfGyration',
                    'RecommendedExposureLimitNIOSHmgm3',
                    'RecommendedExposureLimitNIOSHppm',
                    'RefractiveIndex',
                    'SolidDensity',
                    'SolidDensityTemperature',
                    'SolidHeatCapacityA',
                    'SolidHeatCapacityB',
                    'SolidHeatCapacityC',
                    'SolidHeatCapacityTmax',
                    'SolidHeatCapacityTmin',
                    'SolidThermalConductivityA',
                    'SolidThermalConductivityB',
                    'SolidThermalConductivityC',
                    'SolidThermalConductivityTmax',
                    'SolidThermalConductivityTmin',
                    'SolubilityInWater@298',
                    'SolubilityInWaterA',
                    'SolubilityInWaterB',
                    'SolubilityInWaterC',
                    'SolubilityInwaterInMass',
                    'SolubilityInWaterInMol',
                    'SolubilityInWaterTemperature',
                    'SolubilityInWaterTmax',
                    'SolubilityInWaterTmin',
                    'SolubilityInWaterWithNaClA',
                    'SolubilityInWaterWithNaClB',
                    'SolubilityInWaterWithNaClC',
                    'SolubilityInWaterWithNaClXmax',
                    'SolubilityInWaterWithNaClXmin',
                    'SolubilityParameter',
                    'StandardAbsoluteEntropyOfFormation',
                    'StandardEnthalpyOfFormation',
                    'StandardEntropyofFormation',
                    'StandardGibbsFreeEnergyOfFormation',
                    'StandardHelmholtzEnergyOfFormation',
                    'StandardInternalEnergyOfFormation',
                    'SurfaceTensionA',
                    'SurfaceTensionB',
                    'SurfaceTensionN',
                    'SurfaceTensionTmax',
                    'SurfaceTensionTmin',
                    'UpperExplosionLimitVol',
                    'vanderWaalsVolume']
    return _hypoDoubles

def GetSimHypoDoubleUnitTypes():
    _hypoDoubleUnits = ['',     #  AcentricFactor',
                        '',     #  AdsorptionAt10ppm(vol)',
                        '',     #  AdsorptionInActivatedCarbonA',
                        '',     #  AdsorptionInActivatedCarbonB',
                        '',     #  AdsorptionInActivatedCarbonC',
                        '',     #  Antoine5LogA',
                        '',     #  Antoine5LogB',
                        '',     #  Antoine5LogC',
                        '',     #  Antoine5LogD',
                        '',     #  Antoine5LogE',
                        'Temperature',     #  Antoine5LogTmax',
                        'Temperature',     #  Antoine5LogTmin',
                        'Temperature',     #  AutoIgnitionTemperature',
                        'Fraction',     #  ConcentrationInGas@298And1AtmMax',
                        'Fraction',     #  ConcentrationInGas@298And1AtmMin',
                        '',     #  CriticalCompressibility',
                        'Pressure',     #  CriticalPressure',
                        'Temperature',     #  CriticalTemperature',
                        'MolarVolume',     #  CriticalVolume',
                        '',     #  DiffusionCoefficientInAirA',
                        '',     #  DiffusionCoefficientInAirB',
                        '',     #  DiffusionCoefficientInAirC',
                        'Temperature',     #  DiffusionCoefficientInAirTmax',
                        'Temperature',     #  DiffusionCoefficientInAirTmin',
                        '',     #  DiffusionCoefficientInWaterA',
                        '',     #  DiffusionCoefficientInWaterB',
                        'Temperature',     #  DiffusionCoefficientInWaterTmax',
                        'Temperature',     #  DiffusionCoefficientInWaterTmin',
                        'DipoleMoment',     #  DipoleMoment',
                        'MolarEnthalpy',     #  EnthalpyOfCombustionAt298',
                        'MolarEnthalpy',     #  EnthalpyOfFusion',
                        '',     #  EnthalpyOfVapourizationA',
                        '',     #  EnthalpyOfVapourizationB',
                        '',     #  EnthalpyOfVapourizationN',
                        'Temperature',     #  EnthalpyOfVapourizationTmax',
                        'Temperature',     #  EnthalpyOfVapourizationTmin',
                        'Temperature',     #  FlashPointTemperature',
                        'Temperature',     #  FreezingPoint',
                        '',     #  GasThermalConductivityA',
                        '',     #  GasThermalConductivityB',
                        '',     #  GasThermalConductivityC',
                        'Temperature',     #  GasThermalConductivityTmax',
                        'Temperature',     #  GasThermalConductivityTmin',
                        '',     #  GasViscosityA',
                        '',     #  GasViscosityB',
                        '',     #  GasViscosityC',
                        'Temperature',     #  GasViscosityTmax',
                        'Temperature',     #  GasViscosityTmin',
                        '',     #  HaydenOConnell',
                        'Temperature',     #  HenryConstantInWaterTemperature',
                        '',     #  HTIdealGasHeatCapacityA',
                        '',     #  HTIdealGasHeatCapacityB',
                        '',     #  HTIdealGasHeatCapacityC',
                        '',     #  HTIdealGasHeatCapacityD',
                        'Temperature',     #  HTIdealGasHeatCapacityTmax',
                        'Temperature',     #  HTIdealGasHeatCapacityTmin',
                        'MolarEnthalpy',     #  IdealGasEnthalpyOfFormation@298',
                        '',     #  IdealGasEnthalpyOfFormationA',
                        '',     #  IdealGasEnthalpyOfFormationB',
                        '',     #  IdealGasEnthalpyOfFormationC',
                        'Temperature',     #  IdealGasEnthalpyOfFormationTmax',
                        'Temperature',     #  IdealGasEnthalpyOfFormationTmin',
                        'MolarEnthalpy',     #  IdealGasGibbsFreeEnergyOfFormation@298',
                        '',     #  IdealGasGibbsFreeEnergyOfFormationA',
                        '',     #  IdealGasGibbsFreeEnergyOfFormationB',
                        '',     #  IdealGasGibbsFreeEnergyOfFormationC',
                        'Temperature',     #  IdealGasGibbsFreeEnergyOfFormationTmax',
                        'Temperature',     #  IdealGasGibbsFreeEnergyOfFormationTmin',
                        'Fraction',     #  ImmediatelyDangerousToLifeHealthmgm3',
                        'Fraction',     #  ImmediatelyDangerousToLifeHealthppm',
                        'Density',     #  LiquidDensity@298',
                        '',     #  LiquidHeatCapacityA',
                        '',     #  LiquidHeatCapacityB',
                        '',     #  LiquidHeatCapacityC',
                        '',     #  LiquidHeatCapacityD',
                        'Temperature',     #  LiquidHeatCapacityTmax',
                        'Temperature',     #  LiquidHeatCapacityTmin',
                        '',     #  LiquidThemalExpansionTc',
                        '',     #  LiquidThermalConductivityA',
                        '',     #  LiquidThermalConductivityB',
                        '',     #  LiquidThermalConductivityC',
                        'Temperature',     #  LiquidThermalConductivityTmax',
                        'Temperature',     #  LiquidThermalConductivityTmin',
                        'ThermalExpansion',     #  LiquidThermalExpansion@298',
                        '',     #  LiquidThermalExpansionA',
                        '',     #  LiquidThermalExpansionM',
                        'Temperature',     #  LiquidThermalExpansionTmax',
                        'Temperature',     #  LiquidThermalExpansionTmin',
                        '',     #  LiquidViscosityA',
                        '',     #  LiquidViscosityB',
                        '',     #  LiquidViscosityC',
                        '',     #  LiquidViscosityD',
                        'Temperature',     #  LiquidViscosityTmax',
                        'Temperature',     #  LiquidViscosityTmin',
                        '',     #  Log10KOW',
                        'Fraction',     #  LowerExplosionLimitVol',
                        'Pressure',     #  MaxP',
                        'Temperature',     #  MaxT',
                        'Pressure',     #  MinP',
                        'Temperature',     #  MinT',
                        '',     #  MolecularWeight',
                        'Temperature',     #  NormalBoilingPoint',
                        'Fraction',     #  PermissibleExposureLimitOSHAmgm3',
                        'Fraction',     #  PermissibleExposureLimitOSHAppm',
                        '',     #  Poly5IdealGasCpA',
                        '',     #  Poly5IdealGasCpB',
                        '',     #  Poly5IdealGasCpC',
                        '',     #  Poly5IdealGasCpD',
                        '',     #  Poly5IdealGasCpE',
                        'Temperature',     #  Poly5IdealGasCpTmax',
                        'Temperature',     #  Poly5IdealGasCpTmin',
                        '',     #  RackettLiquidDensityA',
                        '',     #  RackettLiquidDensityB',
                        '',     #  RackettLiquidDensityN',
                        '',     #  RackettLiquidDensityTc',
                        'Temperature',     #  RackettLiquidDensityTmax',
                        'Temperature',     #  RackettLiquidDensityTmin',
                        'Length',     #  RadiusOfGyration',
                        'Fraction',     #  RecommendedExposureLimitNIOSHmgm3',
                        'Fraction',     #  RecommendedExposureLimitNIOSHppm',
                        '',     #  RefractiveIndex',
                        'Density',     #  SolidDensity',
                        'Temperature',     #  SolidDensityTemperature',
                        '',     #  SolidHeatCapacityA',
                        '',     #  SolidHeatCapacityB',
                        '',     #  SolidHeatCapacityC',
                        'Temperature',     #  SolidHeatCapacityTmax',
                        'Temperature',     #  SolidHeatCapacityTmin',
                        '',     #  SolidThermalConductivityA',
                        '',     #  SolidThermalConductivityB',
                        '',     #  SolidThermalConductivityC',
                        'Temperature',     #  SolidThermalConductivityTmax',
                        'Temperature',     #  SolidThermalConductivityTmin',
                        'Fraction',     #  SolubilityInWater@298',
                        '',     #  SolubilityInWaterA',
                        '',     #  SolubilityInWaterB',
                        '',     #  SolubilityInWaterC',
                        'Fraction',     #  SolubilityInwaterInMass',
                        'Fraction',     #  SolubilityInWaterInMol',
                        'Temperature',     #  SolubilityInWaterTemperature',
                        'Temperature',     #  SolubilityInWaterTmax',
                        'Temperature',     #  SolubilityInWaterTmin',
                        '',     #  SolubilityInWaterWithNaClA',
                        '',     #  SolubilityInWaterWithNaClB',
                        '',     #  SolubilityInWaterWithNaClC',
                        'Fraction',     #  SolubilityInWaterWithNaClXmax',
                        'Fraction',     #  SolubilityInWaterWithNaClXmin',
                        'SolubilityParameter',     #  SolubilityParameter',
                        'MolarSpecificHeat',     #  StandardAbsoluteEntropyOfFormation',
                        'MolarEnthalpy',     #  StandardEnthalpyOfFormation',
                        'MolarSpecificHeat',     #  StandardEntropyofFormation',
                        'MolarEnthalpy',     #  StandardGibbsFreeEnergyOfFormation',
                        'MolarEnthalpy',     #  StandardHelmholtzEnergyOfFormation',
                        'MolarEnthalpy',     #  StandardInternalEnergyOfFormation',
                        '',     #  SurfaceTensionA',
                        '',     #  SurfaceTensionB',
                        '',     #  SurfaceTensionN',
                        'Temperature',     #  SurfaceTensionTmax',
                        'Temperature',     #  SurfaceTensionTmin',
                        'Fraction',     #  UpperExplosionLimitVol',
                        'MolarVolume']     #  vanderWaalsVolume',                    
    return _hypoDoubleUnits

# Assuming Vmg keywords = Sim keywords, modify later
def _GetVmgHypoStrings():
    return GetSimHypoStrings()
def _GetVmgHypoLongs():
    return GetSimHypoLongs()
def _GetVmgHypoDoubles():
    return GetSimHypoDoubles()

def CompoundPropNameFromSimToVmg(propType, hypoProps):
    outProps = []
    if propType == 'String':
        simProps = GetSimHypoStrings()
        vmgProps = _GetVmgHypoStrings()
    elif propType == 'Long':
        simProps = GetSimHypoLongs()
        vmgProps = _GetVmgHypoLongs()
    elif propType == 'Double':
        simProps = GetSimHypoDoubles()
        vmgProps = _GetVmgHypoDoubles()
    else:
        simProps = None
    if simProps:
        for prop in hypoProps:
            idx = simProps.index(prop)
            outProps.append(vmgProps[idx])
        return outProps
    else:
        return None
           
def GetCompoundPropertyLists(hypoName, hypoDescs, unitSystem = None):
    # get the suppored compound keywords
    # called from commandinterface to build the 6 compound property lists
    hypoStrings = GetSimHypoStrings()
    hypoLongs = GetSimHypoLongs()
    hypoDoubles = GetSimHypoDoubles()
    hypoDoubleUnitTypes = GetSimHypoDoubleUnitTypes()
    # initialize the return lists
    hypoStringDescs = []
    hypoStringValues = []

    hypoLongDescs = []
    hypoLongValues = []
    
    hypoDoubleDescs = []
    hypoDoubleValues = []
    
    # split the hypoDescriptions
    lines = re.split(r'[\n,]+', hypoDescs)
    # expecting a = value [unit]
    # convertedHypoDescs is the same as hypoDescs but with no unit info and all
    #    the doubles converted
    convertedHypoDescs = ''
    for line in lines:
        tokens = re.split(r'\s+', string.strip(line), 2)
        if len(tokens) == 3 and tokens[1] == '=':
            if tokens[0] in hypoDoubles:
                # Note that unit conversion is done only if a unit string
                #    is present irrespective of the current unit
                vals = re.split(r'\s+', string.strip(tokens[2]), 1)
                if len(vals) == 2 and unitSystem:
                    idx = hypoDoubles.index(tokens[0])
                    unitType = hypoDoubleUnitTypes[idx]
                    unitTypeId = unitSystem.GetTypeID(unitType)
                    if unitType != '':
                        # get all units that matches the unit string
                        units = unitSystem.UnitsByPartialName(vals[1], unitTypeId)
                        # expecting a single match
                        if len(units) == 1:
                            tokens[2] = units[0].ConvertToSim42(float(vals[0]))
                hypoDoubleDescs.append(tokens[0])
                hypoDoubleValues.append(float(tokens[2]))
                convertedHypoDescs += '\n' + tokens[0] + ' = ' + str(tokens[2])

            elif tokens[0] in hypoStrings:
                hypoStringDescs.append(tokens[0])
                hypoStringValues.append(tokens[2])
                convertedHypoDescs += '\n' + string.strip(line)
            elif tokens[0] in hypoLongs:
                hypoLongDescs.append(tokens[0])
                hypoLongValues.append(long(tokens[2]))
                convertedHypoDescs += '\n' + string.strip(line)
    # if not defined explicitly, set the hypo name
    if not 'Name' in hypoStringDescs:
        hypoStringDescs.append('Name')
        hypoStringValues.append(hypoName)
    # store the creation string as Note
    if not 'CreationInfo' in hypoStringDescs:
        hypoStringDescs.append('CreationInfo')
        hypoStringValues.append(convertedHypoDescs)
    else:
        # store the converted hypo descs in 'CreationInfo'
        # so that i could re-create the jupo after recall
        idx = hypoStringDescs.index('CreationInfo')
        hypoStringValues[idx] = convertedHypoDescs
        
    return (hypoStringDescs, hypoStringValues, hypoLongDescs, hypoLongValues, hypoDoubleDescs, hypoDoubleValues)

                
                
            
                
        
    
    
