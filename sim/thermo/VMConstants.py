
from sim.solver.Variables import *
from sim.solver import S42Glob

# from enum SeaFlashSettingEnum
seaCheckStability = 5
seaIgnoreComp = 0
seaIsRetrograde = 10
seaMaxIter = 2
seaMaxLiquids = 12
seaMaxPkpa = 9
seaMaxTk = 7
seaMinPkpa = 8
seaMinTk = 6
seaRestartAccel = 4
seaStartAcceleration = 3
seaTolerance = 1
seaVapFracSpec = 11

# from enum SeaFlashTypeEnum
seaPTFlash = 0
seaPVFlash = 1
seaBubbleT = 2
seaDewT = 3
seaPHFlash = 4
seaTVFlash = 5
seaBubbleP = 6
seaDewP = 7
seaHVolFlash = 8
seaPSFlash = 9
seaRxPTFlash = 10
seaRxBubbleP = 11
seaDynPHFlash = 12
seaRxPTnFlash = 13
seaFrozenPHFlash = 14
seaFrozenPSFlash = 15
seaTHFlash = 16
seaLastFlashType = 17

# from enum SeaMiscFlagEnum
seaLiquidPhase = 1
seaOverallPhase = 6
seaSolidPhase = 4
seaSplitKvalue = 1
seaSplitMoleFrac = 0
seaVapourPhase = 0

# from enum SeaPropertyEnum
seaComposition = -4
seaPhaseType = -3
seaTemperature = -2
seaPressure = -1
seaMolecularWeight = 0
seaZFactor = 1
seaVolume = 2
seaMassDensity = 3
seaLnFugacityCoefficient = 4
seaLnActivityCoefficient = 5
seaLnStandardStateFugacity = 6
seaLnFugacity = 7
seaEnthalpy = 8
seaEntropy = 9
seaCp = 10
seaCv = 11
seaIdealGasEnthalpy = 12
seaIdealGasEntropy = 13
seaIdealGasCp = 14
seaResidualEnthalpy = 15
seaResidualEntropy = 16
seaResidualCp = 17
seaResidualCv = 18
seaViscosity = 19
seaThermalConductivity = 20
seaSurfaceTension = 21
seaSpeedOfSound = 22
seaIsothermalCompressibility = 23
seadPdVt = 24
seaPhaseIdentity = 25
seaIdealGasFormation = 26
seaIdealGasGibbs = 27
seaMechanicalZFactor = 28
seadVdTp = 29
seaLnPoynting = 30
seaLnSatFugacity = 31
seaLnVaporPressure = 32
seaMassFraction = 33                    # mass fraction array
seaIdealVolumeFraction = 34             # ideal volume fraction array
seaGibbsFreeEnergy = 35                 # Gibbs free energy 
seaHelmholtzEnergy = 36                 # Helmholtz energy
seaInternalEnergy = 37                  # Internal energy
seaIdealKValue = 38                     # ideal k value
seapH = 39                              # pH
seaStdLiqDensity = 40                   # standard liquid density
seaActualPhaseComposition = 41          # phase actual composition
seaExcessEnthalpy = 42                  # phase execss enthalpy
seaExcessEntropy = 43                   # phase excess entropy
seaExcessCp = 44                        # phase excess heat capacity
seaExcessCv = 45                        # phase excess heat capacity, isochoric
seaExcessGibbs = 46                     # phase excess Gibbs free energy
seaExcessHelmholtz = 47                 # phase excess Helpholtz energy
seaExcessInternalEnergy = 48            # phase excess Internal energy
seaExcessVolume = 49                    # phase excess volume
seaStdLiqVolume = 50                    # standard liquid volume
seaRxnBasisOffset = 51                  # reaction basis offset, kJ/kmol
seaKinematicViscosity = 52              # kinematic viscosity
seaLowHeatingValue = 53                 # low heating value kJ/kmol
seaHighHeatingValue = 54                # high heating value kJ/kmol
seaLowWobbeIndex = 55                   # low Wobbe index kJ/kmol
seaHighWobbeIndex = 56                  # high Wobbe index kJ/kmol
seaRONClear = 57                        # RON clear
seaMONClear = 58                        # MON clear
seaJT       = 59                        # Joule Thomson coefficient
seaLnSolidFugacityCoefficient = 60      # solid fugacity coefficients
seaStdLiqVolFraction          = 61      # liquid volume fraction array
seaStdLiqVolumePerCmp         = 62      # liquid molar volume per component
seaPseudoTc                   = 63      # pseudo critical temperature
seaPseudoPc                   = 64      # pseudo critical pressure
seaPseudoVc                   = 65      # pseudo critical volume
seaEnvelopeCmp                = 66      #    
seaMolecularWeightArray       = 67      #Molecular weight as an array
seaMassCp                     = 68
seaMassCv                     = 69
seaMassEnthalpy               = 70
seaMassEntropy                = 71


#from enum SeaUnitSetEnum
seaBritish = 6
seaDippr = 5
seaField = 2
seaPureSI = 7
seaSI = 1
seaSeapp = 3
seaYaws = 4


#sim speciality prop
_simSpecialProps = [BUBBLEPOINT_VAR,
                    DEWPOINT_VAR,
                    WATERDEWPOINT_VAR,
                    BUBBLEPRESSURE_VAR,
                    RVPD323_VAR,
                    RVPD1267_VAR,
                    FLASHPOINT_VAR,
                    POURPOINT_VAR,
                    LIQUIDVISCOSITY_VAR,
                    PNA_VAR,
                    BOILINGCURVE_VEC,
                    CETANENUMBER_VAR,
                    RON_VAR,
                    MON_VAR,
                    GHV_VAR,
                    NHV_VAR,
                    PH_VAR,
                    HYDRATETEMPERATURE_VAR,
                    RI_VAR,
                    CO2VSE_VAR,
                    CO2LSE_VAR,
                    PROPERTYTABLE_MATRIX,
                    LOWWOBBE_VAR,
                    HIGHWOBBE_VAR,
                    CUTTEMPERATURE_VAR,
                    PSEUDOTC_VAR,
                    PSEUDOPC_VAR,
                    PSEUDOVC_VAR,
                    JT_VAR,
                    NHVMASS_VAR,
                    GHVMASS_VAR,
                    HVAPCTEP_VAR,
                    HVAPCTET_VAR,
                    GAPTEMPERATURE_VAR]

_vmgSpecialProps = ["BUBBLEPOINT",
                    "DEWPOINT",
                    "WATERDEWPOINT",
                    "BUBBLEPRESSURE",
                    "RVP-D323",
                    "RVP-D1267",
                    "FLASHPOINT",
                    "POURPOINT",
                    "LIQUIDVISCOSITY",
                    "PNA",
                    "BOILINGCURVE",
                    "CETANENUMBER",
                    "RON",
                    "MON",
                    "GHV",
                    "NHV",
                    "PH",
                    "HYDRATETEMPERATURE",
                    "RI",
                    "CO2VSE",
                    "CO2LSE",
                    "PROPERTYTABLE",
                    "LOWWOBBE",
                    "HIGHWOBBE",
                    "CUTTEMPERATURE",
                    "PSEUDOTC",
                    "PSEUDOPC",
                    "PSEUDOVC",
                    "JT",
                    "NHVMASS",
                    "GHVMASS",
                    "HVAPCTEP",
                    "HVAPCTET",
                    "GAPTEMPERATURE"]


#Bulk properties of a stream (T, P, etc) as seen in the simulator
_simProps =[T_VAR,
            P_VAR,
            MOLEWT_VAR,
            ZFACTOR_VAR,
            MOLARV_VAR,
            MASSDEN_VAR,
            H_VAR,            
            S_VAR,
            CP_VAR,
            CV_VAR,
            GIBBSFREEENERGY_VAR,
            HELMHOLTZENERGY_VAR,
            IDEALGASENTHALPY_VAR,
            IDEALGASENTROPY_VAR,
            IDEALGASCP_VAR,
            RESIDUALENTHALPY_VAR,
            RESIDUALENTROPY_VAR,
            RESIDUALCP_VAR,
            RESIDUALCV_VAR,
            VISCOSITY_VAR,
            THERMOCONDUCTIVITY_VAR,
            SURFACETENSION_VAR,     
            SPEEDOFSOUND_VAR,
            ISOTHERMALCOMPRESSIBILITY_VAR,
            DPDVT_VAR,
            IDEALGASFORMATION_VAR,
            IDEALGASGIBBS_VAR,
            MECHANICALZFACTOR_VAR,
            INTERNALENERGY_VAR,
            PH_VAR,
            RXNBASEH_VAR,
            STDLIQVOL_VAR,
            STDLIQDEN_VAR,
            PSEUDOTC_VAR,
            PSEUDOPC_VAR,
            PSEUDOVC_VAR,
            JT_VAR,
            CPMASS_VAR,
            CVMASS_VAR,
            HMASS_VAR,
            SMASS_VAR]

#Bulk properties of a stream (T, P, etc) as seen in vmg
_vmgProps =[seaTemperature,
            seaPressure,
            seaMolecularWeight,
            seaZFactor,
            seaVolume,
            seaMassDensity,
            seaEnthalpy,
            seaEntropy,
            seaCp,
            seaCv,
            seaGibbsFreeEnergy,
            seaHelmholtzEnergy,
            seaIdealGasEnthalpy,
            seaIdealGasEntropy,
            seaIdealGasCp,
            seaResidualEnthalpy,
            seaResidualEntropy,
            seaResidualCp,
            seaResidualCv,
            seaViscosity,
            seaThermalConductivity,
            seaSurfaceTension,
            seaSpeedOfSound,
            seaIsothermalCompressibility,
            seadPdVt,
            seaIdealGasFormation,
            seaIdealGasGibbs,
            seaMechanicalZFactor,
            seaInternalEnergy,
            seapH,
            seaRxnBasisOffset,
            seaStdLiqVolume,
            seaStdLiqDensity,
            seaPseudoTc,
            seaPseudoPc,
            seaPseudoVc,
            seaJT,
            seaMassCp,
            seaMassCv,
            seaMassEnthalpy,
            seaMassEntropy]


#Array properties of a stream (lnFugacity, etc) as seen in the simulator
_simArrayProps =["Composition",
                 "LnFugacityCoefficient",
                 "LnActivityCoefficient",
                 "LnStandardStateFugacity",
                 "LnFugacity",
                 "IdealKValue",
                 "LnSatFugacity",
                 "MassFraction",
                 "IdealVolumeFraction",
                 "IdealGasGibbs",
                 "StdVolFraction",
                 "StdLiqMolVolPerCmp",
                 "EnvelopeCmp",
                 "MolecularWeightArray"]

#Array properties of a stream (lnFugacity, etc) as seen in vmg
_vmgArrayProps =[seaComposition,
                 seaLnFugacityCoefficient,
                 seaLnActivityCoefficient,
                 seaLnStandardStateFugacity,
                 seaLnFugacity,
                 seaIdealKValue,
                 seaLnSatFugacity,
                 seaMassFraction,
                 seaIdealVolumeFraction,
                 seaIdealGasGibbs,
                 seaStdLiqVolFraction,
                 seaStdLiqVolumePerCmp,
                 seaEnvelopeCmp,
                 seaMolecularWeightArray]


#ID properties of a compound as seen in the simulator
#Implemented as a method to avoid keeping the tuple in memory
def _GetCmpSimIDProps():
    _cmpSimIDProps =['Id',
                    'Formula',
                    'Name',
                    'CASN',
                    'ChemicalAbstractsServiceNumber',
                    'ComponentCASN',
                    'MainChemicalFamily',
                    'SecondaryChemicalFamily',
                    'ChemicalFamily']
    return _cmpSimIDProps

def _GetCmpVmgIDProps():
    _cmpVmgIDProps =['Id',
                    'Formula',
                    'Name',
                    'CASN',
                    'ChemicalAbstractsServiceNumber',
                    'ComponentCASN',
                    'MainChemicalFamily',
                    'SecondaryChemicalFamily',
                    'ChemicalFamily']
    return _cmpVmgIDProps

def _GetCmpSimFixedProps():    
    _cmpSimFixedProps =['MolecularWeight',
                    'FreezingPoint',
                    'NormalBoilingPoint',
                    'CriticalTemperature',
                    'CriticalPressure',
                    'CriticalVolume',
                    'CriticalDensity',
                    'CriticalCompressibility',
                    'AcentricFactor',
                    'IdealGasEnthalpyOfFormation@298',
                    'IdealGasGibbsFreeEnergyOfFormation@298',
                    'SolidDensity',
                    'SolidDensityTemperature',
                    'StandardEnthalpyOfFormation',
                    'StandardInternalEnergyOfFormation',
                    'StandardEntropyofFormation',
                    'StandardGibbsFreeEnergyOfFormation',
                    'StandardHelmholtzEnergyOfFormation',
                    'StandardAbsoluteEntropyOfFormation',
                    'PhysicalState',
                    'SolubilityInWaterTemperature',
                    'SolubilityInwaterInMass',
                    'SolubilityInWaterInMol',
                    'SolubilityInWaterStatus',
                    'SolubilityInWater@298',
                    'SolubilityStatus',
                    'LiquidDensity@298',
                    'LowerExplosionLimitVol',
                    'UpperExplosionLimitVol',
                    'ExplosionLimitStatus',
                    'FlashPointTemperature',
                    'AutoIgnitionTemperature',
                    'FlashPointStatus',
                    'AutoIgnitionTemperatureStatus',
                    'PermissibleExposureLimitOSHAppm',
                    'PermissibleExposureLimitOSHAmgm3',
                    'RecommendedExposureLimitNIOSHppm',
                    'RecommendedExposureLimitNIOSHmgm3',
                    'ImmediatelyDangerousToLifeHealthppm',
                    'ImmediatelyDangerousToLifeHealthmgm3',
                    'EnthalpyOfCombustionAt298',
                    'EnthalpyOfCombustionState',
                    'ConcentrationInGas@298And1AtmMin',
                    'ConcentrationInGas@298And1AtmMax',
                    'AdsorptionAt10ppm(vol)',
                    'RadiusOfGyration',
                    'SolubilityParameter',
                    'DipoleMoment',
                    'vanderWaalsVolume',
                    'vanderWaalsArea',
                    'RefractiveIndex']
    return _cmpSimFixedProps

def _GetCmpVmgFixedProps():
    _cmpVmgFixedProps =['MolecularWeight',
                    'FreezingPoint',
                    'NormalBoilingPoint',
                    'CriticalTemperature',
                    'CriticalPressure',
                    'CriticalVolume',
                    'CriticalDensity',
                    'CriticalCompressibility',
                    'AcentricFactor',
                    'IdealGasEnthalpyOfFormation@298',
                    'IdealGasGibbsFreeEnergyOfFormation@298',
                    'SolidDensity',
                    'SolidDensityTemperature',
                    'StandardEnthalpyOfFormation',
                    'StandardInternalEnergyOfFormation',
                    'StandardEntropyofFormation',
                    'StandardGibbsFreeEnergyOfFormation',
                    'StandardHelmholtzEnergyOfFormation',
                    'StandardAbsoluteEntropyOfFormation',
                    'PhysicalState',
                    'SolubilityInWaterTemperature',
                    'SolubilityInwaterInMass',
                    'SolubilityInWaterInMol',
                    'SolubilityInWaterStatus',
                    'SolubilityInWater@298',
                    'SolubilityStatus',
                    'LiquidDensity@298',
                    'LowerExplosionLimitVol',
                    'UpperExplosionLimitVol',
                    'ExplosionLimitStatus',
                    'FlashPointTemperature',
                    'AutoIgnitionTemperature',
                    'FlashPointStatus',
                    'AutoIgnitionTemperatureStatus',
                    'PermissibleExposureLimitOSHAppm',
                    'PermissibleExposureLimitOSHAmgm3',
                    'RecommendedExposureLimitNIOSHppm',
                    'RecommendedExposureLimitNIOSHmgm3',
                    'ImmediatelyDangerousToLifeHealthppm',
                    'ImmediatelyDangerousToLifeHealthmgm3',
                    'EnthalpyOfCombustionAt298',
                    'EnthalpyOfCombustionState',
                    'ConcentrationInGas@298And1AtmMin',
                    'ConcentrationInGas@298And1AtmMax',
                    'AdsorptionAt10ppm(vol)',
                    'RadiusOfGyration',
                    'SolubilityParameter',
                    'DipoleMoment',
                    'vanderWaalsVolume',
                    'vanderWaalsArea',
                    'RefractiveIndex']
    return _cmpVmgFixedProps

def _GetCmpSimEqDepProps():
    _cmpSimEqDepProps =['AdsorptionCapacity',
                        'IdealGasHeatCapacity',
                        'LiquidHeatCapacity',
                        'RackettLiquidDensity',
                        'AntoineVapourPressure',
                        'SurfaceTension',
                        'IdealGasEnthalpyOfFormation',
                        'IdealGasGibbsFreeEnergyOfFormation',
                        'HTIdealGasHeatCapacity',
                        'SolidHeatCapacity',
                        'EnthalpyOfFusion',
                        'LiquidViscosity',
                        'GasViscosity',
                        'LiquidThermalConductivity',
                        'GasThermalConductivity',
                        'SolidThermalCondictivity',
                        'SolubilityInWater',
                        'SolubilityInWaterWithNaCl',
                        'DiffusionCoefficientInAir',
                        'DiffusionCoefficientInWater',
                        'LiquidThermalExpansion']
    return _cmpSimEqDepProps

def _GetCmpVmgEqDepProps():
    _cmpVmgEqDepProps =['AdsorptionCapacity',
                        'IdealGasHeatCapacity',
                        'LiquidHeatCapacity',
                        'RackettLiquidDensity',
                        'AntoineVapourPressure',
                        'SurfaceTension',
                        'IdealGasEnthalpyOfFormation',
                        'IdealGasGibbsFreeEnergyOfFormation',
                        'HTIdealGasHeatCapacity',
                        'SolidHeatCapacity',
                        'EnthalpyOfFusion',
                        'LiquidViscosity',
                        'GasViscosity',
                        'LiquidThermalConductivity',
                        'GasThermalConductivity',
                        'SolidThermalCondictivity',
                        'SolubilityInWater',
                        'SolubilityInWaterWithNaCl',
                        'DiffusionCoefficientInAir',
                        'DiffusionCoefficientInWater',
                        'LiquidThermalExpansion']
    return _cmpVmgEqDepProps

class vmgPropHandler(object):
    """Property handler"""
    def __init__(self):
 
        self._cmpSimCommonIDProps = []
        self._cmpSimCommonFixedProps = []
        self._cmpSimCommonEqDepProps = []
        self._simCommonProps = tuple(_simProps)
        self._simCommonArrayProps = tuple(_simArrayProps)

        self._cmpVmgCommonIDProps = []
        self._cmpVmgCommonFixedProps = []
        self._cmpVmgCommonEqDepProps = []
        self._vmgCommonProps = tuple(_vmgProps)
        self._vmgCommonArrayProps = tuple(_vmgArrayProps)


    def GetFlashPropertyNames(self):
        """Simulator  names of the properties that can perform a flash"""
        return (T_VAR, P_VAR, H_VAR, S_VAR, VPFRAC_VAR)



#Methods for compound properties

    def GetCmpSimIDPropertyNames(self): return _GetCmpSimIDProps() 
    def GetCmpVmgIDPropertyNames(self): return _GetCmpVmgIDProps() 
    def GetCmpSimFixedPropertyNames(self): return _GetCmpSimFixedProps() 
    def GetCmpVmgFixedPropertyNames(self): return _GetCmpVmgFixedProps() 
    def GetCmpSimEqDepPropertyNames(self): return _GetCmpSimEqDepProps() 
    def GetCmpVmgEqDepPropertyNames(self): return _GetCmpVmgEqDepProps() 


    
#Methods for special properties

    def ContainsSpecialProperty(self, simNamesIn):
        for prop in simNamesIn:
            if prop in _simSpecialProps:
                return True
        return False
    
    def SpecialPropNamesFromSimToVmg(self, simNamesIn):
        vmgSpecialNamesOut = []
        for i in simNamesIn:
            idx = _simSpecialProps.index(i)
            vmgSpecialNamesOut.append(_vmgSpecialProps[idx])

        return vmgSpecialNamesOut

    

#Methods for stream properties
    
    def GetSimPropertyNames(self): return list(_simProps)  #Send a copy, not the original one
    def GetVmgPropertyNames(self): return list(_vmgProps)  #Send a copy, not the original one

    def PropNamesFromSimToVmg(self, simNamesIn):
        """Translate a sequence of simulator property names to vmg names"""
        vmgNamesOut = []
        for i in simNamesIn:
            idx = _simProps.index(i)
            vmgNamesOut.append(_vmgProps[idx])
        return vmgNamesOut

    def PropNamesFromVmgToSim(self, vmgNamesIn):
        """Translate a sequence of vmg property names to simulator names"""
        simNamesOut = []
        for i in vmgNamesIn:
            idx = _vmgProps.index(i)
            simNamesOut.append(_simProps[idx])
        return simNamesOut

    def GetVmgCommonPropertyNames(self):
        """Returns the tuple of vmgCommonProperty Names"""
        return self._vmgCommonProps

    def GetSimCommonPropertyNames(self):
        """Returns the tuple of simCommonProperty Names"""
        return self._simCommonProps
        
    def SetVmgCommonPropertyNames(self, vmgNamesIn):
        """Sets a new list of common properties by passing a list of vmg properties"""
        vmgPropList = []
        for i in vmgNamesIn:
            if i in _vmgProps: vmgPropList.append(i)
        simPropList = self.PropNamesFromVmgToSim(vmgPropList)
        self._vmgCommonProps = tuple(vmgPropList)
        self._simCommonProps = tuple(simPropList)

    def SetSimCommonPropertyNames(self, simNamesIn):
        """Sets a new list of common properties by passing a list of sim properties"""
        simPropList = []
        for i in simNamesIn:
            if i in _simProps: simPropList.append(i)        
        vmgPropList = self.PropNamesFromSimToVmg(simPropList)
        self._vmgCommonProps = tuple(vmgPropList)
        self._simCommonProps = tuple(simPropList)

#Methods for array properties

    def GetSimArrayPropertyNames(self): return list(_simArrayProps)
    def GetVmgArrayPropertyNames(self): return list(_vmgArrayProps)

    def ArrayPropNamesFromSimToVmg(self, simNamesIn):
        """Translate a sequence of simulator property names to vmg names"""
        vmgNamesOut = []
        for i in simNamesIn:
            idx = _simArrayProps.index(i)
            vmgNamesOut.append(_vmgArrayProps[idx])
        return vmgNamesOut

    def ArrayPropNamesFromVmgToSim(self, vmgNamesIn):
        """Translate a sequence of vmg property names to simulator names"""
        simNamesOut = []
        for i in vmgNamesIn:
            idx = _vmgArrayProps.index(i)
            simNamesOut.append(_simArrayProps[idx])
        return simNamesOut

    def GetVmgCommonArrayPropertyNames(self):
        """Returns the tuple of vmgCommonProperty Names"""
        return self._vmgCommonArrayProps

    def GetSimCommonArrayPropertyNames(self):
        """Returns the tuple of simCommonProperty Names"""
        return self._simCommonArrayProps
        
    def SetVmgCommonArrayPropertyNames(self, vmgNamesIn):
        """Sets a new list of common properties by passing a list of vmg properties"""
        vmgPropList = []
        for i in vmgNamesIn:
            if i in _vmgArrayProps: vmgPropList.append(i)
        simPropList = self.ArrayPropNamesFromVmgToSim(vmgPropList)
        self._vmgCommonArrayProps = tuple(vmgPropList)
        self._simCommonArrayProps = tuple(simPropList)

    def SetSimCommonArrayPropertyNames(self, simNamesIn):
        """Sets a new list of common properties by passing a list of sim properties"""
        simPropList = []
        for i in simNamesIn:
            if i in _simArrayProps: simPropList.append(i)        
        vmgPropList = self.ArrayPropNamesFromSimToVmg(simPropList)
        self._vmgCommonArrayProps = tuple(vmgPropList)
        self._simCommonArrayProps = tuple(simPropList)

    def PhaseNameFromSimToVmg(self, simPhaseName):
        return simPhaseName

    def PhaseNameFromVmgToSim(self, vmgPhaseName):
        return vmgPhaseName

class vmgFlashSettingsInfoDict(dict):
    """Dictionary with stuff describing flash settings"""
    def __init__(self):
        dict.__init__(self)
        
        vapFracOpts = ["Mol fraction", "Vol fraction", "Mass fraction"]
        TTypeID = S42Glob.unitSystem.GetTypeID("Temperature")
        PTypeID = S42Glob.unitSystem.GetTypeID("Pressure")
        unitSet = S42Glob.unitSystem.GetUnitSet('VMG')
        TUnit = S42Glob.unitSystem.GetUnit(unitSet, TTypeID)
        PUnit = S42Glob.unitSystem.GetUnit(unitSet, PTypeID)

        self["Minimum mole fraction"] = FlashSettingInfo(seaIgnoreComp, "Minimum mole fraction", 1.0e-10)
        self["Flash conv tolerance"] = FlashSettingInfo(seaTolerance, "Flash conv tolerance", 1.0e-14)
        self["Maximum number of iterations"] = FlashSettingInfo(seaMaxIter, "Maximum number of iterations", 200)
        self["Start acceleration"] = FlashSettingInfo(seaStartAcceleration, "Start acceleration", 2)
        self["Restart acceleration"] = FlashSettingInfo(seaRestartAccel, "Restart acceleration", 5)
        self["Minumum temperature"] = FlashSettingInfo(seaMinTk, "Minumum temperature", 10.0, unit=TUnit)
        self["Maximum temperature"] = FlashSettingInfo(seaMaxTk, "Maximum temperature", 1.0e5, unit=TUnit)
        self["Minimum pressure"] = FlashSettingInfo(seaMinPkpa, "Minimum pressure", 0.0001, unit=PUnit)
        self["Maximum pressure"] = FlashSettingInfo(seaMaxPkpa, "Maximum pressure", 1.0e5, unit=PUnit)
        self["Maximum number of liquid phases"] = FlashSettingInfo(seaMaxLiquids, "Maximum number of liquid phases", 4)
        self["Check Stability"] = FlashSettingInfo(seaCheckStability, "Check Stability", 1, options=[0, 1])
        self["Retrograde calculations"] = FlashSettingInfo(seaIsRetrograde, "Retrograde calculations", 0, options=[0, 1])
        self["Vapor frac spec"] = FlashSettingInfo(seaVapFracSpec, "Vapor frac spec",  vapFracOpts[0], options=vapFracOpts)
        
class FlashSettingInfo(object):
    def __init__(self, localName, simName, defValue=None, unit=None, options=None):
        self.localName = localName
        self.simName = simName
        self.defValue = defValue
        self.unit = unit
        self.options = options

#Prop pkg related point props
NUTIMESYAWS_PRP = 'NuTimesCmpInYawsTables'
HENCTINH2OT_PRP = 'HenryConstantInWaterTemperature'
HENCTINH2OMOLEFRAC_PRP = 'HenryConstantInWaterInMoleFraction'
HENCTINH2OVOLFRAC_PRP = 'HenryConstantInWaterInVolumeFraction'
NUUNIFACGRPS_PRP = 'NumberOfUNIFACAtomicGroups'
SUBGRPNU1_PRP = 'SubGroupNumber1'
NUSUBGRPS1_PRP = 'NumberOfSubGroups1'
SUBGRPNU2_PRP = 'SubGroupNumber2'
NUSUBGRPS2_PRP = 'NumberOfSubGroups2'
SUBGRPNU3_PRP = 'SubGroupNumber3'
NUSUBGRPS3_PRP = 'NumberOfSubGroups3'
SUBGRPNU4_PRP = 'SubGroupNumber4'
NUSUBGRPS4_PRP = 'NumberOfSubGroups4'
SUBGRPNU5_PRP = 'SubGroupNumber5'
NUSUBGRPS5_PRP = 'NumberOfSubGroups5'
SUBGRPNU6_PRP = 'SubGroupNumber6'
NUSUBGRPS6_PRP = 'NumberOfSubGroups6'
SUBGRPNU7_PRP = 'SubGroupNumber7'
NUSUBGRPS7_PRP = 'NumberOfSubGroups7'
