"""Class and constant definitions for variables within the simulator

Group of constants:
Properties -- written as XXX_VAR
Parameters -- written as XXX_PAR
Types Of Properties -- written as XXX_PROP
Status Of Properties -- written as XXX_V
Names For Ports -- written as XXX_PORT
Types Of Ports -- these are used so often they are just IN, OUT, MAT, ENE, SIG ...

Classes:
BasicProperty -- A property handler
MaterialPropertyDict -- Dict with material properties
MaterialArrayPropertyDict -- Dict with material properties
EnergyPropertyDict -- Dict with energy properties
ParameterDict -- Dict with parameters
CompoundList -- List with compounds

"""

#There are more imports at the end of the file!!!
import re, os, sys, copy
from Error import ConsistencyError
from vmgunits import units
import numpy
from numpy import float, int, array, zeros, ones, sum
import S42Glob

#Redefine them as integers
True = 1
False = 0

#The cli will be setting this global variable for misc purposes
#Only create once and do not change with further imports
mod = sys.modules['sim.solver.Variables']
if not mod.__dict__.has_key('SIMGLOBALPATH'):
    SIMGLOBALPATH = os.getcwd()
SETCURRENTPATH = False

TINIEST_FLOW = 1.0E-40

##IMPORTANT !!
##THE STRING NAME OF THE VARIABLES MUST NOT CONTAIN A _ IN ITS NAME !!

T_VAR = 'T'                         #Temperature
P_VAR = 'P'                         #Pressure
H_VAR = 'H'                         #Enthalpy
HMASS_VAR = 'HMass'                 #Enthalpy in mass basis
MOLARV_VAR = 'molarV'               #MolarVolume
molarV_VAR = MOLARV_VAR             # to avoid breaking old code
S_VAR = 'S'                         #Entropy
VPFRAC_VAR = 'VapFrac'              #Vapour fraction
MASSVPFRAC_VAR = 'MassVapFrac'      #Mass vapour fraction
MASSFLOW_VAR = 'MassFlow'           #Mass flow
MOLEFLOW_VAR = 'MoleFlow'           #Mole flow
VOLFLOW_VAR = 'VolumeFlow'          #Actual volume flow
STDVOLFLOW_VAR = 'StdLiqVolumeFlow' #Standard volume flow
STDLIQDEN_VAR = 'StdLiqMassDensity' #In mass basis
STDLIQVOL_VAR = 'StdLiqMolarVol'    #
ENERGY_VAR = 'Energy'               #Energy Flow - actually Power
ZFACTOR_VAR = 'ZFactor'             # Note this is used as a flash done flag as well
MOLEWT_VAR = 'MolecularWeight'
MOLE_WT = MOLEWT_VAR                # to avoid breaking old code
DELTAT_VAR = 'DT'                   # delta T variable
DELTAP_VAR = 'DP'                   # delta P variable
GENERIC_VAR = 'Generic'
LENGTH_VAR = 'Length'
UA_VAR = 'UA'                       #Heat transfer coefficient multiplied by area
VOL_VAR = 'Volume'
TIME_VAR = 'Time'
MASS_VAR = 'Mass'
U_VAR = 'U'                         #Heat transfer coefficient
CONCENTRATION_VAR = 'Concentration'
RATERXNVOL_VAR = 'ReactionRateVol'
RATERXNCAT_VAR = 'ReactionRateCat'
HUMIDITY_VAR = 'Humidity'

# alias types
STDGASVOLFLOW_VAR = 'StdGasVolumeFlow' #Standard gas volume flow
WORK_VAR          = 'Work'             # Power equivalent

# other fluid property variables
CP_VAR     = 'Cp'
CV_VAR     = 'Cv'
CPMASS_VAR = 'CpMass'
CVMASS_VAR = 'CvMass'
HMASS_VAR  = 'HMass'
SMASS_VAR  = 'SMass'
            
DPDVT_VAR = 'dPdVt'

GIBBSFREEENERGY_VAR = 'GibbsFreeEnergy'
HELMHOLTZENERGY_VAR = 'HelmholtzEnergy'

IDEALGASCP_VAR        = 'IdealGasCp'
IDEALGASENTHALPY_VAR  = 'IdealGasEnthalpy'
IDEALGASENTROPY_VAR   = 'IdealGasEntropy'
IDEALGASFORMATION_VAR = 'IdealGasFormation'
IDEALGASGIBBS_VAR     = 'IdealGasGibbs'

INTERNALENERGY_VAR            = 'InternalEnergy'
ISOTHERMALCOMPRESSIBILITY_VAR = 'IsothermalCompressibility'

RESIDUALCP_VAR       = 'ResidualCp'
RESIDUALCV_VAR       = 'ResidualCv'
RESIDUALENTHALPY_VAR = 'ResidualEnthalpy'
RESIDUALENTROPY_VAR  = 'ResidualEntropy'

RXNBASEH_VAR           = 'rxnBaseH'

MASSDEN_VAR            = 'MassDensity'
MECHANICALZFACTOR_VAR  = 'MechanicalZFactor'
SURFACETENSION_VAR     = 'SurfaceTension'
SPEEDOFSOUND_VAR       = 'SpeedOfSound'
THERMOCONDUCTIVITY_VAR = 'ThermalConductivity'
VISCOSITY_VAR          = 'Viscosity'
KINEMATICVISCOSITY_VAR = 'KinematicViscosity'

AREA_VAR     = 'Area'
VELOCITY_VAR = 'Velocity'


#Properties that are also special properties
PH_VAR       = 'pH'
PSEUDOTC_VAR = 'PseudoTc'
PSEUDOPC_VAR = 'PseudoPc'
PSEUDOVC_VAR = 'PseudoVc'
JT_VAR       = 'JTCoefficient'


#Special property variables
BUBBLEPOINT_VAR     = "BubblePoint"
DEWPOINT_VAR        = "DewPoint"
WATERDEWPOINT_VAR   = "WaterDewPoint"
BUBBLEPRESSURE_VAR  = "BubblePressure"
RVPD323_VAR         = "ReidVaporPressure_D323"
RVPD1267_VAR        = "ReidVaporPressure_D1267"
FLASHPOINT_VAR      = "FlashPoint"
POURPOINT_VAR       = "PourPoint"
LIQUIDVISCOSITY_VAR = "LiquidViscosity"
PNA_VAR             = "PNA"
BOILINGCURVE_VAR    = "BoilingCurve"
CETANENUMBER_VAR    = "CetaneNumber"
RON_VAR             = "ResearchOctaneNumber"
MON_VAR             = "MotorOctaneNumber"
GHV_VAR             = "GHV"
NHV_VAR             = "NHV"
NHVMASS_VAR         = 'NHVMass'
GHVMASS_VAR         = 'GHVMass'
RI_VAR              = "RefractiveIndex"
CO2VSE_VAR          = "CO2VSEFreezing"
CO2LSE_VAR          = "CO2LSEFreezing"
LOWWOBBE_VAR        = "LowerWobbeIdx"
HIGHWOBBE_VAR       = "HigherWobbeIdx"
CUTTEMPERATURE_VAR  = "CutTemperature"
HVAPCTEP_VAR        = 'HVapConstP'
HVAPCTET_VAR        = 'HVapConstT'
HYDRATETEMPERATURE_VAR = "HydrateTemperature"
GAPTEMPERATURE_VAR  = "GapTemperature"

#Some array props
BOILINGCURVE_VEC       = 'BoilingCurve'
PROPERTYTABLE_MATRIX   = 'PropertyTable'
LNFUG_VAR              = 'LnFugacity'
CMPIDEALG_VAR          = 'IdealGasGibbs'
STDLIQMOLVOLPERCMP_VAR = 'StdLiqMolVolPerCmp'

#Compositions
FRAC_VAR        = 'Fraction'       #Mole fraction
CMPMOLEFRAC_VAR = 'MoleFraction'   #A mistake in design. FRAC_VAR for mole fractions in MAT ports and CMPMOLEFRAC_VAR for SIG ports
MASSFRAC_VAR    = 'MassFraction'
STDVOLFRAC_VAR  = 'StdVolFraction'


#Backward compatibility
CMPMASSFRAC_VAR = MASSFRAC_VAR

#Constants for parameters used commonly.   
NULIQPH_PAR     = 'LiquidPhases'
NUSOLPH_PAR     = 'SolidPhases'
NUTRAYS_PAR     = 'Trays'
NUSTAGES_PAR    = 'NumberStages'
NUSTIN_PAR      = 'NumberStreamsIn'
NUSTOUT_PAR     = 'NumberStreamsOut'
LIQ_MOV         = 'LiquidMoving' #For a liq-liq extraction only
MAXITER_PAR     = 'MaxNumIterations'
MAXITERCONT_PAR = 'MaxControllerIter'
MAXERROR_PAR    = 'MaxError'
MAXABSERROR_PAR = 'MaxAbsoluteError'
R_PAR           = 'RefluxRatio'
SIGTYPE_PAR     = 'SignalType'
IGNORED_PAR     = 'Ignored'
NUSECTIONS_PAR  = 'NumberSections'
STDVOLREFT_PAR  = 'StdLiqVolRefT'



#Constants for types of properties
INTENSIVE_PROP = 1
EXTENSIVE_PROP = 2
CANFLASH_PROP  = 4  # means this property can be used as intensive prop for a flash calc

#Constants for property values status - bit values
UNKNOWN_V    = 1
FIXED_V      = 2
CALCULATED_V = 4
PASSED_V     = 8
NEW_V        = 16
ESTIMATED_V  = 32
PARENT_V     = 64

#Common names for ports
IN_PORT     = 'In'
OUT_PORT    = 'Out'
SIG_PORT    = 'Signal'
V_PORT      = 'Vap'
L_PORT      = 'Liq'
S_PORT      = 'Solid'
FEED_PORT   = 'Feed'
SOLV_PORT   = 'Solvent'
EXTR_PORT   = 'Extract'
RAFF_PORT   = 'Raffinate'
DELTAP_PORT = 'DeltaP'
DELTAT_PORT = 'DeltaT'
U_PORT      = 'U'
UA_PORT     = 'UA'

#Constants for port types
IN  = 1
OUT = 2
MAT = 4
ENE = 8
SIG = 16

#Phase definitions
LIQUID_PHASE  = 1
OVERALL_PHASE = 6
SOLID_PHASE   = 4
VAPOUR_PHASE  = 0

#set up units
#unitSystem = units.UnitSystem()

##check python extensions versions
##To be implemented
##def AreVersionsCorrect():
##    """This method checks that the installed extensions are the same on which this version of sim42 was developed"""
##    suppPythonVer = (2, 2, 2)
##    suppNumericVer = '23.0'
##    suppVmgVer = '3.82'
##    suppwxVer = (2, 3, 3)
##
##    msg = ''
##    out = True
##
##    try:
##        import sys
##        pythonVer = sys.version_info[0:3]
##        if suppPythonVer != pythonVer:
##            msg  = msg + 'Python: Difference found!.\nSupported Version: ' + suppPythonVer + '\nInstalled Version: ' + pythonVer + '\n\n'
##            out = False
##        else:
##            msg = msg + 'Python: Equal\n\n'
##
##    except:
##        msg = msg + 'Python: Error while attempting to check version\n\n'
##        out = False
##
##    try:
##        import numeric_version
##        numericVer = numeric_version.version
##        if suppNumericVer != numericVer:
##            msg  = msg + 'Numeric: Difference found!.\nSupported Version: ' + suppNumericVer + '\nInstalled Version: ' + numericVer + '\n\n'
##            out = False
##        else:
##            msg = msg + 'Numeric: Equal\n\n'
##
##    except:
##        msg = msg + 'Numeric: Error while attempting to check version\n\n'
##        out = False
##
##    try:
##        from wxPython import wx
##        wxVer = wx.wxVERSION
##        if suppwxVer != wxVer:
##            msg  = msg + 'wxPython: Difference found!.\nSupported Version: ' + suppwxVer + '\nInstalled Version: ' + wxVer + '\n\n'
##            out = False
##        else:
##            msg = msg + 'wxPython: Equal\n\n'
##
##    except:
##        msg = msg + 'wxPython: Error while attempting to check version\n\n'
##        out = False
##
##    return (out, msg)


_reqExtProps = (MOLEFLOW_VAR, MASSFLOW_VAR, ENERGY_VAR, VOLFLOW_VAR)
_reqIntProps = (T_VAR, P_VAR, H_VAR, S_VAR, VPFRAC_VAR, molarV_VAR, ZFACTOR_VAR, MOLE_WT, STDLIQVOL_VAR)
_reqArrayProps = ()

def GetReqExtensivePropertyNames():
    """List of required extensive properties within the simulator"""
    global _reqExtProps
    return _reqExtProps

def GetReqIntensivePropertyNames():
    """List of required intensive properties within the simulator"""
    global _reqIntProps
    return _reqIntProps

def GetReqArrayPropertyNames():
    """List of required array properties within the simulator"""
    global _reqArrayProps
    return _reqArrayProps

def SetReqIntensivePropertyNames(propList):
    """Sets the list of requiered intensive properties"""
    global _reqIntProps
    try: _reqIntProps = tuple(propList)
    except: pass
        
def SetReqExtensivePropertyNames(propList):
    """Sets the list of requiered intensive properties"""
    global _reqExtProps
    try: _reqExtProps = tuple(propList)
    except: pass

def SetReqArrayPropertyNames(propList):
    """Sets the list of requiered intensive properties"""
    global _reqArrayProps
    try: _reqArrayProps = tuple(propList)
    except: pass

class PropertyType(object):
    """information concerning the type of variable"""
    def __init__(self, name, calcType=INTENSIVE_PROP, unitType=None, scaleFactor=None,
               minValue=None, maxValue=None):
        """
        name = descriptive name key - should be unique
        calcType = INTENSIVE_PROP intensive variable,
                   EXTENSIVE_PROP extensive variable
                   CANFLASH_PROP variable can be used to do flash (t, p, h etc)
                   These are bit values and can be or'd together
                   CANFLASH_PROP should only occur with INTENSIVE_PROP
        unit = a unit conversion object
        scaleFactor = factor for consistency and convergence tolerences.
             should scale any errors to a base of one - i.e. a fraction
             would have scale of 1, but an temperature value might have
             a scale factor of 1000 reflecting K in the hundred.
             If scaleFactor is None, no error checking is done
        minValue = smallest allowable value
        maxValue = largert allowable
        """
      
        self.name = name
        self.calcType = calcType
        if unitType:
            unitType = S42Glob.unitSystem.GetTypeID(unitType)
        self.unitType = unitType
        self.scaleFactor = scaleFactor  #Negative, 0.0 or None are ignored in consistency calcs
        self.minValue = minValue
        self.maxValue = maxValue
    
    def __str__(self):
        return self.name
    
    def SetValues(self, values, calcStatus):
        """
        set the scaleFactor, minValue and maxValue from values
        if not all values are supplied, the missing ones are not changed
        calcstatus is ignored
        """
        try:
            if values[0]: self.scaleFactor = float(values[0])
            if values[1] != None and values[1] != 'None': self.minValue = float(values[1])
            if values[2] != None and values[2] != 'None': self.maxValue = float(values[2])
        except IndexError:
            pass
        
    def GetObject(self, name):
        """
        for name = Values return scaleFactor, minValue, maxValue
        """
        if name == 'Values':
            return [self.scaleFactor, self.minValue, self.maxValue]
        
#Constants for properties used commonly.
## need to fill in Units

PropTypes = {}

def InitPropTypes(t):
    """
    add default property types to t
    """
    t[T_VAR] = PropertyType(T_VAR, calcType=INTENSIVE_PROP|CANFLASH_PROP, unitType='Temperature',
                         scaleFactor=100.0, minValue=0.0)  #Temperature

    t[P_VAR] = PropertyType(P_VAR, calcType=INTENSIVE_PROP|CANFLASH_PROP, unitType='Pressure',
                         scaleFactor=1000.0, minValue=0.0) #Pressure

    t[H_VAR] = PropertyType(H_VAR, calcType=INTENSIVE_PROP|CANFLASH_PROP, unitType='MolarEnthalpy', 
                            scaleFactor=10000.0)              #Enthalpy
    
    t[HMASS_VAR] = PropertyType(HMASS_VAR, calcType=INTENSIVE_PROP, unitType='MassEnthalpy',
                                scaleFactor=10000.0)              #Enthalpy mass basis
    
    t[MOLARV_VAR] = PropertyType(MOLARV_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarVolume',
                         scaleFactor=10.0, minValue=0.0)    #MolarVolume
    
    t[STDLIQVOL_VAR] = PropertyType(STDLIQVOL_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarVolume',
                         scaleFactor=10.0, minValue=0.0)    #StdLiqMolarVolume

    t[STDLIQDEN_VAR] = PropertyType(STDLIQDEN_VAR, calcType=INTENSIVE_PROP, unitType='Density',
                         scaleFactor=50000.0, minValue=0.0)    #StdLiqMassDensity
    
    t[S_VAR] = PropertyType(S_VAR, calcType=INTENSIVE_PROP, unitType='MolarSpecificHeat',
                         scaleFactor=1000.0)               #Entropy

    t[VPFRAC_VAR] = PropertyType(VPFRAC_VAR, calcType=INTENSIVE_PROP,
                         scaleFactor=1.0,
                         minValue=0.0, maxValue=1.0) #Vapor fraction

    t[MASSFLOW_VAR] = PropertyType(MASSFLOW_VAR, calcType=EXTENSIVE_PROP,
                         unitType='MassFlow',
                         scaleFactor=50000.0)               #Mass Flow

    t[STDVOLFLOW_VAR] = PropertyType(STDVOLFLOW_VAR, calcType=EXTENSIVE_PROP,
                         unitType='VolumetricFlow',
                         scaleFactor=10000.0)               #standard liquid volumetric Flow

    t[VOLFLOW_VAR] = PropertyType(VOLFLOW_VAR, calcType=EXTENSIVE_PROP,
                         unitType='VolumetricFlow',
                         scaleFactor=10000.0)               #actual volumetric Flow    
    
    t[MOLEFLOW_VAR] = PropertyType(MOLEFLOW_VAR, calcType=EXTENSIVE_PROP,
                         unitType='MoleFlow',
                         scaleFactor=1000.0)               #Mole Flow

    t[ENERGY_VAR] = PropertyType(ENERGY_VAR, calcType=EXTENSIVE_PROP,
                              unitType='Power',
                               scaleFactor=1000000.0)        #Energy

    t[FRAC_VAR] = PropertyType(FRAC_VAR, calcType=INTENSIVE_PROP,
                         scaleFactor = 1.0,
                         minValue=0.0, maxValue=1.0)           #Fraction

    t[ZFACTOR_VAR] = PropertyType(ZFACTOR_VAR, calcType=INTENSIVE_PROP,
                         scaleFactor=1.0)         
    t[MOLEWT_VAR] = PropertyType(MOLE_WT, calcType=INTENSIVE_PROP,
                         scaleFactor=100.0)
    t[DELTAT_VAR] = PropertyType(DELTAT_VAR, calcType=INTENSIVE_PROP, unitType='DeltaT',
                         scaleFactor=100.0, minValue=0.0)  #Temperature difference


    t[DELTAP_VAR] = PropertyType(DELTAP_VAR, calcType=INTENSIVE_PROP, unitType='DeltaP',
                         scaleFactor=1000.0, minValue=0.0) #Pressure difference

    t[LENGTH_VAR] = PropertyType(LENGTH_VAR, unitType='Length', scaleFactor=10.0)
    t[CMPMOLEFRAC_VAR] = PropertyType(CMPMOLEFRAC_VAR, calcType=INTENSIVE_PROP,
                         scaleFactor = 1.0,
                         minValue=0.0, maxValue=1.0)           #Used for accessing single mole fraction
             
    t[CMPMASSFRAC_VAR] = PropertyType(CMPMASSFRAC_VAR, calcType=INTENSIVE_PROP,
                         scaleFactor = 1.0,
                         minValue=0.0, maxValue=1.0)           #Used for accessing single mass fraction
             
    t[STDVOLFRAC_VAR] = PropertyType(STDVOLFRAC_VAR, calcType=INTENSIVE_PROP,
                         scaleFactor = 1.0,
                         minValue=0.0, maxValue=1.0)           #Used for accessing single vol fraction
             
    
    t[CP_VAR] = PropertyType(CP_VAR, calcType=INTENSIVE_PROP,unitType='MolarSpecificHeat',
                         scaleFactor=500.0, minValue=0.0)

    t[CV_VAR] = PropertyType(CV_VAR, calcType=INTENSIVE_PROP,unitType='MolarSpecificHeat',
                         scaleFactor=500.0, minValue=0.0)

    t[DPDVT_VAR] = PropertyType(DPDVT_VAR, calcType=INTENSIVE_PROP,unitType='Pressure/MolarVolume',
                         scaleFactor=1.0e6)

    t[GIBBSFREEENERGY_VAR] = PropertyType(GIBBSFREEENERGY_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarEnthalpy',
                         scaleFactor=1.0e5)

    t[HELMHOLTZENERGY_VAR] = PropertyType(HELMHOLTZENERGY_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarEnthalpy', scaleFactor=1.0e5)

    t[IDEALGASCP_VAR] = PropertyType(IDEALGASCP_VAR, calcType=INTENSIVE_PROP,unitType='MolarSpecificHeat',
                         scaleFactor=500.0, minValue=0.0)

    t[IDEALGASENTHALPY_VAR] = PropertyType(IDEALGASENTHALPY_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarEnthalpy', scaleFactor=10000.0)
             
    t[IDEALGASENTROPY_VAR] = PropertyType(IDEALGASENTROPY_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarSpecificHeat', scaleFactor=1000.0)
             
    t[IDEALGASFORMATION_VAR] = PropertyType(IDEALGASFORMATION_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarEnthalpy', scaleFactor=100000.0)
             
    t[IDEALGASGIBBS_VAR] = PropertyType(IDEALGASGIBBS_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarEnthalpy', scaleFactor=100000.0)
             
    t[INTERNALENERGY_VAR] = PropertyType(INTERNALENERGY_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarEnthalpy', scaleFactor=100000.0)
             
    t[ISOTHERMALCOMPRESSIBILITY_VAR] = PropertyType(ISOTHERMALCOMPRESSIBILITY_VAR,
                         calcType=INTENSIVE_PROP, scaleFactor=1.0)         

    t[MASSDEN_VAR] = PropertyType(MASSDEN_VAR, calcType=INTENSIVE_PROP,unitType='Density',
                         scaleFactor = 50000.0, minValue=0.0)

    t[MECHANICALZFACTOR_VAR] = PropertyType(MECHANICALZFACTOR_VAR,
                         calcType=INTENSIVE_PROP, scaleFactor=1.0)

    t[PH_VAR] = PropertyType(PH_VAR, calcType=INTENSIVE_PROP, scaleFactor=10.0)

    t[RESIDUALCP_VAR] = PropertyType(RESIDUALCP_VAR, calcType=INTENSIVE_PROP,unitType='MolarSpecificHeat',
                         scaleFactor=500.0, minValue=0.0)

    t[RESIDUALCV_VAR] = PropertyType(RESIDUALCV_VAR, calcType=INTENSIVE_PROP,unitType='MolarSpecificHeat',
                         scaleFactor=500.0, minValue=0.0)

    t[RESIDUALENTHALPY_VAR] = PropertyType(RESIDUALENTHALPY_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarEnthalpy', scaleFactor=10000.0)
             
    t[RESIDUALENTROPY_VAR] = PropertyType(RESIDUALENTROPY_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarSpecificHeat', scaleFactor=1000.0)
             
    t[RXNBASEH_VAR] = PropertyType(RXNBASEH_VAR, calcType=INTENSIVE_PROP,
                         unitType='MolarEnthalpy', scaleFactor=100000.0)
             
    t[SURFACETENSION_VAR] = PropertyType(SURFACETENSION_VAR, calcType=INTENSIVE_PROP,
                         unitType='SurfaceTension', scaleFactor=-1.0)

    t[SPEEDOFSOUND_VAR] = PropertyType(SPEEDOFSOUND_VAR, calcType=INTENSIVE_PROP,
                         unitType='Velocity',
                         scaleFactor=-1.0, minValue=0.0)

    t[THERMOCONDUCTIVITY_VAR] = PropertyType(THERMOCONDUCTIVITY_VAR, calcType=INTENSIVE_PROP,unitType='ThermalConductivity',
                         scaleFactor=-1.0, minValue=0.0)

    t[VISCOSITY_VAR] = PropertyType(VISCOSITY_VAR, calcType=INTENSIVE_PROP,unitType='Viscosity',
                         scaleFactor=-1.0, minValue=0.0)

    t[KINEMATICVISCOSITY_VAR] = PropertyType(KINEMATICVISCOSITY_VAR, calcType=INTENSIVE_PROP,unitType='KinematicViscosity',
                         scaleFactor=1.0, minValue=0.0)

    t[UA_VAR] = PropertyType(UA_VAR, calcType=EXTENSIVE_PROP, unitType='UA', scaleFactor=100000.0, minValue=0.0)

    t[U_VAR] = PropertyType(U_VAR, calcType=EXTENSIVE_PROP, unitType='HeatTransferCoeff', scaleFactor=10.0, minValue=0.0)    
    
    t[AREA_VAR] = PropertyType(AREA_VAR, calcType=EXTENSIVE_PROP, unitType='Area', scaleFactor=10.0)

    t[TIME_VAR] = PropertyType(TIME_VAR, calcType=EXTENSIVE_PROP, unitType='Time', scaleFactor=10.0)
    
    t[MASS_VAR] = PropertyType(MASS_VAR, calcType=EXTENSIVE_PROP, unitType='Mass', scaleFactor=100.0)

    t[VOL_VAR] = PropertyType(VOL_VAR, calcType=EXTENSIVE_PROP, unitType='Volume', scaleFactor=10.0)
        
    t[CONCENTRATION_VAR] = PropertyType(CONCENTRATION_VAR, calcType=EXTENSIVE_PROP, 
                                        unitType='MolarConcentration', scaleFactor=10.0)
    
    t[RATERXNVOL_VAR] = PropertyType(RATERXNVOL_VAR, calcType=INTENSIVE_PROP, 
                                     unitType=RATERXNVOL_VAR, scaleFactor=1.0)  
    
    t[RATERXNCAT_VAR] = PropertyType(RATERXNCAT_VAR, calcType=INTENSIVE_PROP, 
                                     unitType=RATERXNCAT_VAR, scaleFactor=1.0)

    t['GasConstant'] = PropertyType('GasConstant', calcType=EXTENSIVE_PROP, 
                                        unitType='GasConstant', scaleFactor=1.0)
    
    t[GENERIC_VAR] = PropertyType(GENERIC_VAR, scaleFactor=1.0)       #unknown type

    t[VELOCITY_VAR] = PropertyType(VELOCITY_VAR, calcType=INTENSIVE_PROP,
                         unitType='Velocity', scaleFactor=1000.0)

    t[NHVMASS_VAR] = PropertyType(NHVMASS_VAR, calcType=INTENSIVE_PROP, unitType='MassEnthalpy',
                                  scaleFactor=10000.0)              #NHV mass basis
    
    t[GHVMASS_VAR] = PropertyType(GHVMASS_VAR, calcType=INTENSIVE_PROP, unitType='MassEnthalpy',
                                  scaleFactor=10000.0)              #GHV mass basis
    
    t[HVAPCTEP_VAR] = PropertyType(HVAPCTEP_VAR, calcType=INTENSIVE_PROP, unitType='MolarEnthalpy', 
                                   scaleFactor=10000.0)              #Enthalpy 
    
    t[HVAPCTET_VAR] = PropertyType(HVAPCTET_VAR, calcType=INTENSIVE_PROP, unitType='MolarEnthalpy', 
                                   scaleFactor=10000.0)              #Enthalpy 
    
    t[PSEUDOTC_VAR] = PropertyType(PSEUDOTC_VAR, calcType=INTENSIVE_PROP, unitType='Temperature',
                                   scaleFactor=100.0, minValue=0.0)  #Temperature

    t[PSEUDOPC_VAR] = PropertyType(PSEUDOPC_VAR, calcType=INTENSIVE_PROP, unitType='Pressure',
                                   scaleFactor=1000.0, minValue=0.0) #Pressure
    
    t[PSEUDOVC_VAR] = PropertyType(PSEUDOVC_VAR, calcType=INTENSIVE_PROP, unitType='MolarVolume',
                                   scaleFactor=10.0, minValue=0.0)    #MolarVolume
    
    t[JT_VAR] = PropertyType(JT_VAR, calcType=INTENSIVE_PROP, unitType='JouleThomson',
                                   scaleFactor=1.0)    #JouleThomson coefficient
    
    t[HUMIDITY_VAR] = PropertyType(HUMIDITY_VAR, calcType=INTENSIVE_PROP, unitType='Humidity', scaleFactor=10000.0)

    t[WORK_VAR] = PropertyType(WORK_VAR, calcType=EXTENSIVE_PROP, unitType='Work', scaleFactor=1000000.0)

    t[STDGASVOLFLOW_VAR] = PropertyType(STDGASVOLFLOW_VAR, calcType=EXTENSIVE_PROP,
                         unitType='StdGasVolumeFlow', scaleFactor=10000.0)
    
    t[HMASS_VAR] = PropertyType(HMASS_VAR, calcType=INTENSIVE_PROP, unitType='MassEnthalpy',
                                  scaleFactor=10000.0)
    t[CPMASS_VAR] = PropertyType(CPMASS_VAR, calcType=INTENSIVE_PROP, unitType='MassSpecificHeat',
                                  scaleFactor=500.0)
    t[CVMASS_VAR] = PropertyType(CVMASS_VAR, calcType=INTENSIVE_PROP, unitType='MassSpecificHeat',
                                  scaleFactor=500.0)
    t[SMASS_VAR] = PropertyType(SMASS_VAR, calcType=INTENSIVE_PROP, unitType='MassSpecificHeat',
                                  scaleFactor=1000.0)
  
    
    
InitPropTypes(PropTypes)

class BasicProperty(object):
    """Class definition for properties that the user interacts with"""
    def __init__(self, typeName, port=None):
        """Init a property with everything as None or unknown
        typeName is the string indicating the type of variable (T_VAR, P_VAR etc)
        port is the port to which the property will belong
        """
        self._value = None
        self._calcStatus = UNKNOWN_V
        self._type = PropTypes.get(typeName, PropTypes[GENERIC_VAR])
        self._myPort = port

    def __str__(self):
        """very basic representation"""
        return 'BasicProperty ' + self._type.name
    
    def Clone(self):
        clone = self.__class__(self._type.name)
        
        if self._calcStatus & FIXED_V:
            #Only keep values if they are fixed
            clone._value = self._value
            clone._calcStatus = self._calcStatus
            
        return clone
            
    def CleanUp(self):
        """
        clean up before deleting
        """
        self._myPort = None
        self._type = None
        
    def SetValue(self, value, calcStatus=CALCULATED_V):
        """used to assign a value to the property"""
        port = self._myPort
        
        if not port:
            self._value = value
            self._calcStatus = calcStatus
            return
     
        if calcStatus & FIXED_V:
            
            estimateAll = False
            #For now, estimating anything will flip the state of the port
            if calcStatus & ESTIMATED_V:
                if port.state != Ports.ESTIMATEALL_STATE:
                    port.SetState(Ports.ESTIMATEALL_STATE)
                    estimateAll = True
                
            if port.state == Ports.ESTIMATEALL_STATE:
                #Every spec will be forced as estimate
                calcStatus |= ESTIMATED_V
            elif port.state == Ports.FIXALL_STATE:
                #Every spec is forced to be a spec
                calcStatus &= ~ESTIMATED_V
                
            #Make sure it is a number
            if value == None: calcStatus = UNKNOWN_V
            else: value = float(value)
            
            #Same status, same value, just leave
            if self._calcStatus == calcStatus and value == self._value:
                return
            
            #If an estimate, then notify the port or else, clear the ESTIMATED_V bit
            if calcStatus & ESTIMATED_V:
                port.SetEstimated()
            elif self._calcStatus & ESTIMATED_V:
                self._calcStatus = self._calcStatus & ~ ESTIMATED_V
                port.CheckEstimated()
                
            #Dirty hack for zero flow
            if value == 0.0:
                if self._type.name in (MOLEFLOW_VAR, MASSFLOW_VAR, VOLFLOW_VAR, STDVOLFLOW_VAR, STDGASVOLFLOW_VAR):
                    value = TINIEST_FLOW
                    
            #Flag it as new
            self._calcStatus = calcStatus | NEW_V
            self._value = value
            port.PropertyModified(self, calcStatus)
            
            if estimateAll:
                port.AllPropsAsEstimates()
            
        elif calcStatus == UNKNOWN_V:
            if value != None:
                raise SimError('SetValueUnknownNotNone')
            if self._calcStatus & UNKNOWN_V:
                return  # already unknown
            
            self._calcStatus = UNKNOWN_V | NEW_V
            self._value = None
            port.PropertyModified(self, UNKNOWN_V)

        elif calcStatus & (CALCULATED_V | PASSED_V):
            # ignore attempts to calculate or pass unknown values
            if value == None: return
            # is there already a value? GetValue won't return new fixed values
            isNew =  self._calcStatus & NEW_V
            isFixed = self._calcStatus & FIXED_V
            if self.GetValue() != None or (isNew and isFixed):
                # is this a forget call?
                if not self._myPort.GetParentOp().IsForgetting():
                    self.CheckTolerance(value)
                    # Just keep old value
            else:
                self._calcStatus = NEW_V | calcStatus
                if value == 0.0:
                    if self._type.name in (MOLEFLOW_VAR, MASSFLOW_VAR, VOLFLOW_VAR, STDVOLFLOW_VAR, STDGASVOLFLOW_VAR):
                        value = TINIEST_FLOW
                self._value = value
                port.PropertyModified(self, calcStatus)
            
        else:
            raise SimError('InvalidCalcStatusInSet')
 
    def CheckTolerance(self, value):
        """check to see if value is tolerably equal to the current value
        If not place on parent flowsheet consistency error list
        """
        tolerance = self._myPort.GetParentOp().GetTolerance()
        error = self.CalculateError(value)
        if error > tolerance:
            self._myPort.GetParentOp().PushConsistencyError(self, value)

    def CalculateError(self, value):
        """Calculate a scaled error value between value and the 
        current value"""
        scaleFactor = self._type.scaleFactor
        if scaleFactor == None or self._value == None or scaleFactor <= 0.0:
            return 0.0        
        else:
            return abs(self._value - value)/scaleFactor
        
    def GetValue(self):
        """return value of property subject to current solver state"""
        # if no port then not part of normal solver - just return value
        if not self._myPort:
            return self._value

        # if not doing a forget, just return the value
        if not self._myPort.GetParentOp().IsForgetting():
            return self._value
        
        calcStatus = self._calcStatus
        
        # Newly fixed values must look unknown while forgetting
        newValue = calcStatus & NEW_V
        fixedValue = calcStatus & FIXED_V
        if newValue and fixedValue:
            return None
        
        ##Is this really needed??
        # Hide passed vapour fractions while forgetting because they could calculate
        # unexpected bubble or dew points
        #if calcStatus & PASSED_V and self._type.name == VPFRAC_VAR:
            #return None
        
        # other than calculated and new fixed values are valid
        if not (calcStatus & CALCULATED_V):
            return self._value
        
        # new calculated values are also okay
        if newValue:
            return self._value
            
        # old values calculated by parent op are hidden when forgetting
        return None

    def GetObject(self, description):
        """just return value description unless description is GlobalType"""
        if description == 'GlobalType':
            return self._type
        else:
            return self.GetValue()
    
    def GetCalcStatus(self):
        return self._calcStatus
    
    def ResetNewFixed(self):
        if self._calcStatus & FIXED_V:
            self._calcStatus &= ~NEW_V
        
    def ResetNewCalc(self):
        if not (self._calcStatus & FIXED_V):
            self._calcStatus &= ~NEW_V
            
    def Forget(self, connProp, skipStatus=0):
        """
        forget value if it has been calculated, but is not a new value
        connProp is a BasicProperty connected to this one or None
        if skipStatus is not 0 then variable will only be skipped if _calcStatus
        has one of the skipStatus bits set
        """
        if skipStatus and not(skipStatus & self._calcStatus):
            return
        
        if ((self._calcStatus & CALCULATED_V) and
              not (self._calcStatus & NEW_V)):
            fromParent = self._calcStatus & PARENT_V
            self._calcStatus = UNKNOWN_V
            self._value = None
            if connProp and (connProp._calcStatus & PASSED_V):
                connProp._calcStatus = UNKNOWN_V
                connProp._value = None
                if connProp._myPort:
                    connProp._myPort.PropertyModified(connProp, UNKNOWN_V)
            if self._myPort:
                self._myPort.PropertyModified(self, UNKNOWN_V | fromParent)
    
    def ForgetForStatus(self, calcStatus):
        """forget any value that has any status bit in common with calcStatus"""
        if self._calcStatus & calcStatus:
            self._calcStatus = UNKNOWN_V
            self._value = None
            if self._myPort:
                self._myPort.PropertyModified(self, UNKNOWN_V)

    def GetType(self):
        return self._type

    def SetTypeByName(self, typeName):
        """Change the type of a property, but only if it is of an equivalent unit type"""
        if S42Glob.unitSystem.IsEquivalentType(self._type.unitType, PropTypes[typeName].unitType):
            self._type = PropTypes[typeName]
        
    
    def GetCalcType(self):
        return self._type.calcType
    
    def SetCalcType(self, calcType):
        #Don't change anything if type is wrong
        if (calcType == EXTENSIVE_PROP or calcType == INTENSIVE_PROP or calcType == INTENSIVE_PROP | CANFLASH_PROP):
            self._type.calcType = calcType
    
    ##def __cmp__(self, prop):
        ##if isinstance(prop, BasicProperty):
            ##return cmp(self._value, prop._value)
        ##else: return cmp(self._value, prop)

    def GetName(self):
        return self._type.name

    def GetPath(self):
        if self._myPort:
            path = self._myPort.GetPath() + '.' + self._type.name
            if self._type.name == FRAC_VAR:
                if isinstance(self._myPort, Ports.Port_Material):
                    cmps = self._myPort.GetCompounds()
                    cmpIdx = None
                    for i in range(len(cmps)):
                        if cmps[i] is self:
                            cmpIdx = i
                            break
                    if cmpIdx != None:
                        cmpName = self._myPort.GetCompoundNames()[cmpIdx]
                    else:
                        return self._type.name
                    path += '.' + cmpName
            return path
        else:
            return self._type.name

    def GetParent(self):
        """return parent port"""
        return self._myPort

    def GetContents(self):
        result = [('Value', self._value), ('Status', self._calcStatus), ('Name', self._type.name),
                    ('UnitType', self._type.unitType)]
        return result
        
        
class BasicArrayProperty(object):
    """Base object to create arrays recognized by sim42"""
    
    #Eventually could implement some forget behavior
    
    def __init__(self, typeNames, parent=None, name="Profile"):
        
        #Always keep type in a list even if there is only one of them
        #Make it a list if it came as a single string
        if isinstance(typeNames, str):
            typeNames = [typeNames]
        self._type = map(lambda typeName: PropTypes.get(typeName, PropTypes[GENERIC_VAR]), typeNames)
        self.parent = None
        self.name = name
        self._value = None
        
    def __str__(self):
        return "%s\n%s" % (self.name, str(self._value))
        
    def Clone(self):
        clone = self.__class__([])
        clone._type = list(self._type)
        clone._value = self.GetValue()
        return clone
    
    def GetName(self):
        return self.name
    
    def SetName(self, name):
        self.name = name
    
    def GetParent(self):
        return self.parent
    
    def SetParent(self, parent):
        self.parent = parent
    
    def GetPath(self):
        if not self.parent: return self.name
        return "%s.%s" %(self.parent.GetPath(), self.name)
    
    def SetValue(self, value):
        self._value = value
        
    def GetValue(self):
        """Return a copy of the values"""

        if isinstance(self._value, type(Numeric.array([0]))):
            return Numeric.array(self._value)
        elif self._value == None:
            return None
        else:
            return copy.deepcopy(self._value)
        
    def GetShape(self):
        """Return the shape of the value/s"""
        if self._value == None:
            return None
        else:
            retShape = None
            try: 
                myShape = Numeric.shape(self._value)
                if len(myShape) == 0:
                    retShape = (0, 0)
                elif len(myShape) == 1:
                    retShape = (myShape[0], 0)
                else:
                    retShape = myShape
                
            finally: 
                return retShape
        
    def GetRank(self):
        """Return how many dimensions the value has (scalar, vector, or array)"""
        if self._value == None:
            return None
        else:
            return Numeric.rank(self._value)
        
    def GetType(self):
        """Get the list of types. Returns a list even for a scalar"""
        return self._type
        
        
class MaterialPropertyDict(dict):
    """Dictionary of material properties. Inherits from dict

    keys -- Name of the property
    values -- Instance of BasicProperty

    """
    def __init__(self, dict=None, port=None):
        """Init dictionary with basic and common properties."""
        dict.__init__(self, dict)
        
        for i in GetReqIntensivePropertyNames():
            self[i] = BasicProperty(i, port)
        for i in GetReqExtensivePropertyNames():
            self[i] = BasicProperty(i, port)

    def __setitem__(self, key, item):
        """Only BasicProperties"""
        if not isinstance(item, BasicProperty): return
        dict.__setitem__(self, key, item)

    def NumericItems(self):
        """Returns all the numeric values of properties

        Works like the items() method in a dictionary, but in this case
        the tuple is (key, valueOfTheProperty)

        """
        numItems = []
        for i in self .items(): numItems.append((i[0], i[1].value))
        return numItems

    def GetNamesOfKnownFixedVars(self, type=None):
        """Returns names of props with self.GetCalcStatus()==FIXED_V"""
        vars = []
        for i in self.items():
            if(i[1].GetCalcStatus() & FIXED_V and
                   i[1].GetValue() != None):
                if type == None or i[1].GetType().calcType & type:
                    vars.append(i[0])
        return vars

    def GetNamesOfKnownCalcVars(self, type=None):
        """Returns names of props with self.GetCalcStatus()==CALCULATED_V"""
        vars = []
        for i in self.items():
            if(i[1].GetCalcStatus() & (CALCULATED_V | PASSED_V) and
                    i[1].GetValue() != None):
                if type == None or i[1].GetType().calcType & type:
                    vars.append(i[0])
        return vars

    def GetNamesOfKnownVars(self, type=None):
        """Returns names of props with self.GetCalcStatus()=!= UNKNOWN_V.
        
        type -- filters by type if desired(i.e. intensive or extensive)

        """
        vars = []
        for i in self.items():
            if i[1].GetCalcStatus() != UNKNOWN_V:
                if type == None or i[1].GetType().calcType & type:
                    vars.append(i[0])
        return vars


class MaterialArrayPropertyDict(dict):
    """Dictionary of material properties. Inherits from UserDict

    keys -- Name of the property
    values -- List of BasicProperties

    """
    def __init__(self, dict=None, port=None):
        """Init dictionary with required properties."""
        dict.__init__(self, dict)
        self._port = port

        for i in GetReqArrayPropertyNames():
            self[i] = []
        
    def CleanUp(self):
        """
        clean up prior to delete
        """
        self._port = None


class EnergyPropertyDict(dict):
    """Dictionary of energy properties. Inherits from UserDict

    keys -- Name of the property
    values -- Instance of BasicProperty

    """
    def __init__(self, dict=None, port=None, varTypeName=ENERGY_VAR):
        """The only value of the dictionary is varTypeName"""
        dict.__init__(self, dict)
        
        self[varTypeName] = BasicProperty(varTypeName, port)

    def __setitem__(self, key, item):
        """Only BasicProperties"""
        if not isinstance(item, BasicProperty): return
        dict.__setitem__(self, key, item)

class ParameterDict(dict):
    """ Dictionary of unit operation parameters. Inherits from UserDict

    keys -- Name of the property
    values -- Value of the parameter

    """
    def __init__(self):
        """Init an empty dictionary"""        
        dict.__init__(self)

class CompoundList(list):
    """slightly enhanced list of BasicProperties representing composition"""

    def __init__(self, parent):
        """
        just set parent
        """
        list.__init__(self)
        self._parent = parent
        
    def CleanUp(self):
        """
        clean up prior to delete
        """
        self._parent = None
        
    def SetValues(self, vals, calcStatus):
        """Set the compositions for all the compounds

        vals -- Composition values        

        """
        if vals == None:
            for i in self:
                i.SetValue(None, calcStatus)
            return
        
        if len(vals) != len(self):
            return
        
        try:
            #Can we do everything in arrays?
            #vals can be a list with strings, therefore a map call is needed first
            vals = array(map(float, vals), Float)
            total = sum(vals)
            vals = vals/total #normalize
            for i in range(len(vals)):
                self[i].SetValue(vals[i], calcStatus)
                
        except:
            try:
                for i in range(len(vals)):
                    try: val = float(vals[i])
                    except: val = None
                    self[i].SetValue(val, calcStatus)
            except:
                pass
            self.Normalize()
            

    def GetValues(self):
        """Vals are in the order of the compounds"""
        return map(_GetValueFromProperty, self)
        #vals = []
        #for cmp in self:
            #if cmp.GetCalcStatus() & UNKNOWN_V: vals.append(None)
            #else: vals.append(cmp.GetValue())
        #return vals
        
    def AreValuesReady(self):
        """True if all the compositions hava a valid value"""
        if (len(self) == 0):
            return 0
        try:
            #If I can do this, then it is ready
            values = array(self.GetValues(), Float)
            return 1
        except:
            return 0
        
        #for i in self:
            #if i.GetValue() == None: return 0
        #return 1
        
    def GetName(self):
        """return the name used by material ports to refer to this"""
        return FRAC_VAR
    def GetPath(self):
        """path to this object"""
        return self._parent.GetPath() + '.' + self.GetName()

    def GetParent(self):
        return self._parent
    
    def GetContents(self):
        """
        return all BasicVariables this contains as list of tuples of
        (description, obj)
        """
        #result = []
        #i = 0
        names = self.GetCompoundNames()
        return map(None, names, self)
    
        #for cmp in self:
            #result.append((names[i],cmp))
            #i += 1
        #return result
     
    def GetCompoundNames(self):
        """
        return compound names
        """
        if self._parent:
            return self._parent.GetCompoundNames()
        
    def GetObject(self, name):
        """ return object (compound) matching number or name"""
        try:
            # if it is a number, use that
            return self[int(name)]
        except:
            try:
                return(self[self._parent.GetCompoundNumber(name)])
            except:
                if name == 'Names':
                    return self._parent.GetCompoundNames()
                return None

    def DeleteObject(self, cmp):
        """
        just set the value of the cmp to unknown
        """
        cmp.SetValue(None, FIXED_V)


    def SumFractions(self):
        """
        return the sum of the fractions or None if any unknown
        """
        try: 
            return sum(array(self.GetValues(), Float))
        except:
            return None
    
    def Normalize(self):
        """
        Normalize the composition

        Note that this call by itself does not notify the solver of any change
        """
        
        vals = self.GetValues()
        try:
            vals = array(vals, Float)
            total = sum(vals)
            if total == 0:
                # all components cannot be zero - set unknown
                for i in self:
                    i.SetValue(None, FIXED_V)
            else:
                vals = vals / total
                map(_SetValuesToAttribute, self, vals)
        except:
            pass
        

    def MoveCompound(self, idx1, idx2):
        cmp1 = self.GetObject(idx1)
        if idx1 < idx2:
            # moving a compound down, insert first
            self.insert(idx2, cmp1)
            del self[idx1]
        elif idx1 > idx2:
            # moving a compound up, delete first
            del self[idx1]
            self.insert(idx2, cmp1)

    def SetLocalCompValues(self, vals):
        # Load CompoundList with a list of floats, already normalized
        # Typical use is to create a local CompoundList for internal flash calcualtions
        # i am exoecting len(self) = 0 and self._parent = None
        n = len(vals)
        n0 = len(self)
        for i in range(n):
            if i >= n0:
                self.append(BasicProperty(FRAC_VAR))
            self[i].SetValue(vals[i], FIXED_V)
        for i in range(i,n0):
            del self[i]
            
        
        
        
        
class MassCompoundList(object):
    def __init__(self, cmpList):
        self._cmpList = cmpList
        self.MW = None

    def GetName(self):
        """return the name used by material ports to refer to this"""
        return MASSFRAC_VAR

    def GetPath(self):
        """path to this object"""
        return self._cmpList.GetParent().GetPath() + '.' + self.GetName()

    def GetObject(self, name):
        """ return object (compound) matching number or name"""
        try:
            # if it is a number, use that
            idx = int(name)
            vals = self.GetValues()
            return vals[idx]
        except:
            try:
                idx = self._cmpList.GetParent().GetCompoundNumber(name)
                vals = self.GetValues()
                return vals[idx]
            except:
                return None
            
    def SetValues(self, values, calcStatus=CALCULATED_V):
        if values == None:
            for i in self._cmpList:
                i.SetValue(None, calcStatus)
            return

        try:
            # first get the unit operation pointer
            unitOp = self._cmpList.GetParent().GetParent()
            
            # assign the mole fraction as mass fraction/ MW for each compound
            # with the same calc status
            thCaseObj = unitOp.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            mw = thAdmin.GetMolecularWeightValues(prov, case)
            try: 
                values = values/mw
            except:
                #Came as a list instaed of an array?
                values = array(map(float, values), Float) / mw
                
            #normalize right here
            values = values / sum(values)
            
            #Make status an array
            _calcStatus = ones(len(values), Int) * calcStatus
            
            #Put the values in
            map(_SetValuesToProperty, self._cmpList, values, _calcStatus)
                
        except:
            pass

    def GetValues(self):
        """Mass fractions are available only when the entire slate of
           mole fractions are available.
           Vals are in the order of the compounds"""
        vals = self._cmpList.GetValues()
        if vals == None: return None
        
        try:
            try:
                #Change to numeric array
                vals = array(vals, Float)
                unitOp = self._cmpList.GetParent().GetParent()
                thCaseObj = unitOp.GetThermo()
                thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
                mw = thAdmin.GetMolecularWeightValues(prov, case)
                vals = vals * mw
                vals = vals / sum(vals)
            except:
                #If fails, means that at least one value was None, return a list of Nones
                vals = list(vals) #back to a list
                for i in range(len(vals)):
                   vals[i] = None
                
        except: 
            return None
        
        return vals

    def __str__(self):
        result = ''
        cmpNames = self._cmpList.GetParent().GetParent().GetCompoundNames()
        vals = self.GetValues()
        if vals == None: return "None"
        for i in range(len(self._cmpList)):
            cmp = cmpNames[i]
            result += cmp
            pad = max(28 - len(cmp), 1)
            result += ' ' * pad + '= ' + str(vals[i]) + '\n'
        return result
    def GetParent(self):
        return self._cmpList.GetParent()
    def GetCompoundNames(self):
        return self._cmpList.GetCompoundNames()
    
class StdVolCompoundList(object):
    def __init__(self, cmpList):
        self._cmpList = cmpList
        self.molarVol = None

    def GetName(self):
        """return the name used by material ports to refer to this"""
        return STDVOLFRAC_VAR

    def GetPath(self):
        """path to this object"""
        return self._cmpList.GetParent().GetPath() + '.' + self.GetName()

        
    def GetObject(self, name):
        """ return object (compound) matching number or name"""
        try:
            # if it is a number, use that
            idx = int(name)
            vals = self.GetValues()
            return vals[idx]
        except:
            try:
                idx = self._cmpList.GetParent().GetCompoundNumber(name)
                vals = self.GetValues()
                return vals[idx]
            except:
                return None    
    
    def SetValues(self, values, calcStatus=CALCULATED_V):
        if values == None:
            for i in self._cmpList:
                i.SetValue(None, calcStatus)
            return

        
        try:
            # first get the unit operation pointer
            unitOp = self._cmpList.GetParent().GetParent()
            
            # assign the mole fraction for each compound
            # with the same calc status
            thCaseObj = unitOp.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            values = array(map(float, values), Float)
            values = values/sum(values)
            refT = unitOp.GetStdVolRefT()
            molVol = thAdmin.GetArrayProperty(prov, case, (P_VAR, 101.325), (T_VAR, refT), LIQUID_PHASE, values, STDLIQMOLVOLPERCMP_VAR)
            values = values/molVol
            
            #normalize right here
            values = values / sum(values)
            
            #Make status an array
            _calcStatus = ones(len(values), Int) * calcStatus
            
            #Put the values in
            map(_SetValuesToProperty, self._cmpList, values, _calcStatus)
                
        except:
            pass
        

    def GetValues(self):
        """Vol fractions are available only when the entire slate of
           mole fractions are available.
           Vals are in the order of the compounds"""
        vals = self._cmpList.GetValues()
        if vals == None: return None
        
        try:
            try:
                #Change to numeric array
                vals = array(vals, Float)
                
                #Get objects
                unitOp = self._cmpList.GetParent().GetParent()
                thCaseObj = unitOp.GetThermo()
                thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
                
                #Get properties
                refT = unitOp.GetStdVolRefT()
                vals = thAdmin.GetArrayProperty(prov, case, (P_VAR, 101.325), (T_VAR, refT), LIQUID_PHASE, vals, STDVOLFRAC_VAR)
                
                return vals
            
            except:
                #If fails, means that at least one value was None, return a list of Nones
                vals = list(vals)         #back to a list
                for i in range(len(vals)):
                   vals[i] = None
                
        except: 
            return None
            
        return vals

    def __str__(self):
        result = ''
        cmpNames = self._cmpList.GetParent().GetParent().GetCompoundNames()
        vals = self.GetValues()
        if vals == None: return "None"
        for i in range(len(self._cmpList)):
            cmp = cmpNames[i]
            result += cmp
            pad = max(28 - len(cmp), 1)
            result += ' ' * pad + '= ' + str(vals[i]) + '\n'
        return result
    def GetParent(self):
        return self._cmpList.GetParent()
    def GetCompoundNames(self):
        return self._cmpList.GetCompoundNames()

class SimInfoDict(dict):
    """
    info dictionary for Unit Ops
    """
    def __init__(self, name, parent):
        """
        save the name and parent for path functions
        """
        self.name = name
        self.parent = parent
        super(SimInfoDict, self).__init__()
        
    def Clone(self):
        clone = self.__class__(self.name, None)
        for name in self.keys():
            if isinstance(self[name], SimInfoDict):
                clone[name] = self[name].Clone()
                clone[name].SetParent(clone)
            else:
                clone[name] = copy.deepcopy(self[name])
                
        return clone
        
    def CleanUp(self):
        for o in self.values():
            if isinstance(o, SimInfoDict):
                o.CleanUp()
        
        self.parent = None

    def SetParent(self, parent):
        self.parent = parent
        
    def GetPath(self):
        return self.parent.GetPath() + '.' + self.name
    
    def GetName(self):
        return self.name

    def GetParent(self):
        return self.parent
    
    def GetObject(self, name):
        try:
            return self[name]
        except:
            return None
        
    def AddObject(self, obj, name):
        if obj == '{}':
            obj = SimInfoDict(name, self)
        elif obj == 'None':
            if name in self.keys():
                del self[name]
            return
        self[name] = obj

    def DeleteObject(self, obj):
        for item in self.items():
            if item[1] == obj:
                del self[item[0]]

def _GetValueFromProperty(obj):
    """Useful for map calls when a value is required"""
    if obj._calcStatus & UNKNOWN_V: return None
    else: return obj.GetValue()
    
def _SetValuesToProperty(obj, value, calcStatus):
    """Useful for map calls """
    obj.SetValue(value, calcStatus)

def _SetValuesToAttribute(obj, value):
    """Useful for map calls """
    obj._value = value
                
                
import Ports
#import psyco
#psyco.bind(BasicProperty.SetValue)
#psyco.bind(BasicProperty.Forget)
