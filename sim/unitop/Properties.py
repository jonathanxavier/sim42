"""Models Cold Properties and Refinery Properties

Class:
ColdProp -- Class for cold properties
RefineryProp -- Class for refinery properties

"""

from sim.solver.Variables import *
from sim.solver import S42Glob
from sim.unitop import UnitOperations
import numpy.oldnumeric
from numpy.oldnumeric import array, Float, zeros

#Keywords used in the PropertyPackge

EMPTY_VAL = -12321

KINEMATICVISCOSITY_VAR = 'KinematicViscosity'
DYNAMICVISCOSITY_VAR = 'DynamicViscosity'
PARAFFIN_VAR = 'ParaffinMolPercent'
NAPHTHENE_VAR = 'NaphthaleneMolPercent'
AROMATIC_VAR = 'AromaticMolPercent'

#For backward compatibility in this typo
NAPHTHENE_VAR_WRONG = 'NapthleneMolPercent'

#Some options for curves
TBP_OPT = 'TBP'
D86_OPT = 'D86'
D2887_OPT = 'D2887'
EFV_OPT = 'EFV'
D1160_OPT = 'D1160'

#This last one is only used in CUTTEMPERATURE
D1160Vac_OPT = 'D1160Vac'

SPECIAL_PROPS = [BUBBLEPOINT_VAR,
                 DEWPOINT_VAR,
                 WATERDEWPOINT_VAR,
                 BUBBLEPRESSURE_VAR,
                 RVPD323_VAR,
                 RVPD1267_VAR,
                 FLASHPOINT_VAR,
                 POURPOINT_VAR,
                 KINEMATICVISCOSITY_VAR,
                 DYNAMICVISCOSITY_VAR,
                 PARAFFIN_VAR,
                 NAPHTHENE_VAR,
                 AROMATIC_VAR,
                 CETANENUMBER_VAR,
                 RON_VAR,
                 MON_VAR,
                 GHV_VAR,
                 GHVMASS_VAR,
                 NHV_VAR,
                 NHVMASS_VAR,
                 PH_VAR,
                 HYDRATETEMPERATURE_VAR,
                 RI_VAR,
                 CO2VSE_VAR,
                 CO2LSE_VAR,
                 LOWWOBBE_VAR,
                 HIGHWOBBE_VAR,
                 JT_VAR,
                 PSEUDOTC_VAR,
                 PSEUDOPC_VAR,
                 PSEUDOVC_VAR,
                 HVAPCTEP_VAR,
                 HVAPCTET_VAR]

COLD_PROPS =    (BUBBLEPOINT_VAR,
                 DEWPOINT_VAR,
                 WATERDEWPOINT_VAR,
                 BUBBLEPRESSURE_VAR,
                 GHV_VAR,
                 GHVMASS_VAR,
                 NHV_VAR,
                 NHVMASS_VAR,
                 PH_VAR,
                 HYDRATETEMPERATURE_VAR,
                 CO2VSE_VAR,
                 CO2LSE_VAR,
                 LOWWOBBE_VAR,
                 HIGHWOBBE_VAR,
                 JT_VAR,
                 PSEUDOTC_VAR,
                 PSEUDOPC_VAR,
                 PSEUDOVC_VAR,
                 HVAPCTEP_VAR,
                 HVAPCTET_VAR)


COLD_PROPS = ' '.join(COLD_PROPS)

REFINERY_PROPS =    (RVPD323_VAR,
                     RVPD1267_VAR,
                     FLASHPOINT_VAR,
                     POURPOINT_VAR,
                     KINEMATICVISCOSITY_VAR,
                     DYNAMICVISCOSITY_VAR,
                     PARAFFIN_VAR,
                     NAPHTHENE_VAR,
                     AROMATIC_VAR,
                     CETANENUMBER_VAR,
                     RON_VAR,
                     MON_VAR,
                     RI_VAR)
REFINERY_PROPS = ' '.join(REFINERY_PROPS)

SPECIAL_PROP_TYPES = [T_VAR,
                      T_VAR,
                      T_VAR,
                      P_VAR,
                      P_VAR,
                      P_VAR,
                      T_VAR,
                      T_VAR,
                      KINEMATICVISCOSITY_VAR,
                      VISCOSITY_VAR,
                      FRAC_VAR,
                      FRAC_VAR,
                      FRAC_VAR,
                      GENERIC_VAR,
                      GENERIC_VAR,
                      GENERIC_VAR,
                      H_VAR,
                      GHVMASS_VAR,
                      H_VAR,
                      NHVMASS_VAR,
                      PH_VAR,
                      T_VAR,
                      GENERIC_VAR,
                      T_VAR,
                      T_VAR,
                      H_VAR,
                      H_VAR,
                      JT_VAR,
                      PSEUDOTC_VAR,
                      PSEUDOPC_VAR,
                      PSEUDOVC_VAR,
                      HVAPCTEP_VAR,
                      HVAPCTET_VAR]

ACTIVE_KEY = "_Active"
AVAICOLDPROPS_PAR = 'AvailableColdProps'
AVAIREFINERYPROPS_PAR = 'AvailableRefineryProps'

class SpecialProps(UnitOperations.UnitOperation):
    """Class for cold & refinery properties. Inherits from UnitOperations"""
    def __init__(self, initScript = None):
        super(SpecialProps, self).__init__(initScript)
        self.portOut = self.CreatePort(MAT|OUT, OUT_PORT)
        self.portOut.SetLocked(True)
        self.portIn = self.CreatePort(MAT|IN, IN_PORT)
        self.portIn.SetLocked(True)

        for prop in SPECIAL_PROPS:
            self.SetParameterValue(prop + ACTIVE_KEY, False)

        #Set the parameters directly so they are not Validated
        self.parameters[AVAICOLDPROPS_PAR] = COLD_PROPS
        self.parameters[AVAIREFINERYPROPS_PAR] = REFINERY_PROPS

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(SpecialProps, self).AdjustOldCase(version)
        
        if version[0] < 33:
            port = self.GetPort(KINEMATICVISCOSITY_VAR)
            if port:
                varType = port.GetSignalType()
                if varType != KINEMATICVISCOSITY_VAR:
                    conn = port.GetConnection()
                    if conn:
                        #What else to do?
                        port.Disconnect()
                    port.SetSignalType(KINEMATICVISCOSITY_VAR)
                    self.ForgetAllCalculations()
        if version[0] < 50:
            port = self.GetPort(GHV_VAR) #NHV_VAR
            if port:
                varType = port.GetSignalType()
                if varType != H_VAR:
                    conn = port.GetConnection()
                    if conn:
                        conn.Disconnect()
                    port.SetSignalType(H_VAR)
            port = self.GetPort(NHV_VAR) #NHV_VAR
            if port:
                varType = port.GetSignalType()
                if varType != H_VAR:
                    conn = port.GetConnection()
                    if conn:
                        conn.Disconnect()
                    port.SetSignalType(H_VAR)
                    
        if self.parameters.get(AVAICOLDPROPS_PAR, None) != COLD_PROPS:
            self.parameters[AVAICOLDPROPS_PAR] = COLD_PROPS
            
        if self.parameters.get(AVAIREFINERYPROPS_PAR, None) != REFINERY_PROPS:
            self.parameters[AVAIREFINERYPROPS_PAR] = REFINERY_PROPS
            
        #Use this loop as a generic looop for any newer version that adds new properties
        if version[0] < 57:
            for propName in SPECIAL_PROPS:
                if self.parameters.get(propName + ACTIVE_KEY, None) == None:
                    self.parameters[propName + ACTIVE_KEY] = False
                
        
        if version[0] < 74:
            #Correct this typo
            self.parameters[AVAIREFINERYPROPS_PAR] = REFINERY_PROPS
            
            val = self.parameters.get(NAPHTHENE_VAR_WRONG + ACTIVE_KEY, None)
            if val != None:
                self.parameters[NAPHTHENE_VAR + ACTIVE_KEY] = val
                
            port = self.GetPort(NAPHTHENE_VAR_WRONG)
            if port != None:
                self.RenamePort(NAPHTHENE_VAR_WRONG, NAPHTHENE_VAR)
            
            
    def SetParameterValue(self, paramName, value):
        super(SpecialProps, self).SetParameterValue(paramName, value)

        if paramName[-len(ACTIVE_KEY):] == ACTIVE_KEY:
            propName = paramName[0:-len(ACTIVE_KEY)]
            if propName == NAPHTHENE_VAR_WRONG:
                propName = NAPHTHENE_VAR
            if propName in SPECIAL_PROPS:
                if value and not self.GetPort(propName): 
                    p = self.CreatePort(SIG, propName)
                    idx = SPECIAL_PROPS.index(propName)
                    p.SetSignalType(SPECIAL_PROP_TYPES[idx])

                elif not value and self.GetPort(propName):
                    self.DeletePort(self.GetPort(propName))
                        
    def ValidateParameter(self, paramName, value):
        super(SpecialProps, self).ValidateParameter(paramName, value)

        if not super(SpecialProps, self).ValidateParameter(paramName, value):
            return False

        #if paramName == AVAICOLDPROPS_PAR:
            #return False
            
        #if paramName == AVAIREFINERYPROPS_PAR:
            #return False
        
        return True
        
    def SolvePorts(self):
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)

        # share between in and out
        self.FlashAllPorts()
        inPort.ShareWith(outPort)
        self.FlashAllPorts()
        inPort.ShareWith(outPort)
        

    def Solve(self):
        
        self.SolvePorts()
        self.unitOpMessage = ('NoMessage', )
        if self.IsForgetting(): return
        
        #Get thermo
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: return 
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case

        portIn = self.portIn
        P = portIn.GetPropValue(P_VAR)
        fracs = portIn.GetCompositionValues()
        if None in fracs: return
        
        statusOut = ''
        for port in self.GetPorts(SIG):
            name = port.GetName()
            
            #Properties that need pressure and composition
            if name in (BUBBLEPOINT_VAR, DEWPOINT_VAR, WATERDEWPOINT_VAR, CO2VSE_VAR, CO2LSE_VAR, HVAPCTEP_VAR):
                if P != None:
                    value, status = thAdmin.GetSpecialProperty(prov, case, P, fracs, name)
                    try:
                        value = float(value)
                        if value != EMPTY_VAL: port.SetValue(value, CALCULATED_V)
                        if status[0:2] != 'OK':
                            statusOut += '%s: %s;\n' %(name, status)
                    except:
                        statusOut += '%s: %s;\n' %(name, status)
                        
            #Properties that need temperature and composition
            elif name in (BUBBLEPRESSURE_VAR, HVAPCTET_VAR):
                T = portIn.GetPropValue(T_VAR)
                if T != None:
                    value, status = thAdmin.GetSpecialProperty(prov, case, T, fracs, name)
                    try:
                        value = float(value)
                        if value != EMPTY_VAL: port.SetValue(value, CALCULATED_V)
                        if status[0:2] != 'OK':
                            statusOut += '%s: %s;\n' %(name, status)
                    except:
                        statusOut += '%s: %s;\n' %(name, status)
                        
            #Special treatmente for viscosities
            elif name in (KINEMATICVISCOSITY_VAR, DYNAMICVISCOSITY_VAR):
                propName = LIQUIDVISCOSITY_VAR
                T = self.portIn.GetPropValue(T_VAR)
                if T != None:
                    value, status = thAdmin.GetSpecialProperty(prov, case, T, fracs, propName)
                    try:
                        values = value.split()
                        value0, value1 = float(values[0]), float(values[1])
                        if name == KINEMATICVISCOSITY_VAR:
                            if value0 != EMPTY_VAL: port.SetValue(value0, CALCULATED_V)
                        else:
                            if value1 != EMPTY_VAL: port.SetValue(value1, CALCULATED_V)
                        if status[0:2] != 'OK':
                            statusOut += '%s: %s;\n' %(name, status)
                    except:
                        statusOut += '%s: %s;\n' %(name, status)
                        
            #Special treatment for PNA
            elif name in (PARAFFIN_VAR, NAPHTHENE_VAR, AROMATIC_VAR):
                propName = PNA_VAR
                value, status = thAdmin.GetSpecialProperty(prov, case, "", fracs, propName)
                try:
                    values = value.split()
                    value0, value1, value2 = float(values[0]), float(values[1]), float(values[2])
                    if name == PARAFFIN_VAR:
                        if value0 != EMPTY_VAL: port.SetValue(value0, CALCULATED_V)
                    elif name == NAPHTHENE_VAR:
                        if value1 != EMPTY_VAL: port.SetValue(value1, CALCULATED_V)
                    else:
                        if value2 != EMPTY_VAL: port.SetValue(value2, CALCULATED_V)
                    if status[0:2] != 'OK':
                        statusOut += '%s: %s;\n' %(name, status)
                except:
                    statusOut += '%s: %s;\n' %(name, status)
                    
            #Properties that require composition
            elif name in (RVPD323_VAR, RVPD1267_VAR, FLASHPOINT_VAR, POURPOINT_VAR, 
                          CETANENUMBER_VAR, RON_VAR, MON_VAR, GHV_VAR, NHV_VAR, PH_VAR, 
                          HYDRATETEMPERATURE_VAR, RI_VAR, LOWWOBBE_VAR, HIGHWOBBE_VAR,
                          NHVMASS_VAR, GHVMASS_VAR, PSEUDOTC_VAR, PSEUDOPC_VAR, PSEUDOVC_VAR):
                value, status = thAdmin.GetSpecialProperty(prov, case, "", fracs, name)
                try:
                    value = float(value)
                    if value != EMPTY_VAL: port.SetValue(value, CALCULATED_V)
                    if status[0:2] != 'OK':
                        statusOut += '%s: %s;\n' %(name, status)
                except:
                    statusOut += '%s: %s;\n' %(name, status)
            
            #Properties that require P, T and composition
            elif name == JT_VAR:
                T = portIn.GetPropValue(T_VAR)
                if T != None and P != None:
                    value, status = thAdmin.GetSpecialProperty(prov, case, (T, P), fracs, name)
                    try:
                        value = float(value)
                        if value != EMPTY_VAL: port.SetValue(value, CALCULATED_V)
                        if status[0:2] != 'OK':
                            statusOut += '%s: %s;\n' %(name, status)
                    except:
                        statusOut += '%s: %s;\n' %(name, status)
                        
        if not statusOut:
            statusOut = 'OK'
            self.unitOpMessage = ('ThermoProviderMsg', (statusOut,))
        else:
            self.unitOpMessage = ('ThermoProviderMsg', (statusOut,))
            if not self.IsForgetting():
                self.InfoMessage('ThermoProviderMsg', (self.GetPath(), statusOut))
        

VECTOR_PROPS = [BOILINGCURVE_VEC + "_" + TBP_OPT,
                BOILINGCURVE_VEC + "_" + D86_OPT,
                BOILINGCURVE_VEC + "_" + D2887_OPT,
                BOILINGCURVE_VEC + "_" + EFV_OPT,
                BOILINGCURVE_VEC + "_" + D1160_OPT]

VECTOR_PROP_TYPES = [(GENERIC_VAR, T_VAR),
                     (GENERIC_VAR, T_VAR),
                     (GENERIC_VAR, T_VAR),
                     (GENERIC_VAR, T_VAR),
                     (GENERIC_VAR, T_VAR)]

AVAIVECTOR_PROPS =  (BOILINGCURVE_VEC + "_" + TBP_OPT,
                    BOILINGCURVE_VEC + "_" + D86_OPT,
                    BOILINGCURVE_VEC + "_" + D2887_OPT,
                    BOILINGCURVE_VEC + "_" + EFV_OPT,
                    BOILINGCURVE_VEC + "_" + D1160_OPT)
AVAIVECTOR_PROPS = '%s %s %s %s %s' %AVAIVECTOR_PROPS

AVAIVECTORPROPS_PAR = 'AvailableBoilingCurve'

class VectorProps(UnitOperations.UnitOperation):
    def __init__(self, initScript = None):
        super(VectorProps, self).__init__(initScript)
        self.portOut = self.CreatePort(MAT|OUT, OUT_PORT)
        self.portOut.SetLocked(True)
        self.portIn = self.CreatePort(MAT|IN, IN_PORT)
        self.portIn.SetLocked(True)

        self.results = {}

        self.parameters[AVAIVECTORPROPS_PAR] = self.GetAvVectorPropsString()       

        for prop in self.GetAvVectorPropsList():
            self.SetParameterValue(prop + ACTIVE_KEY, False)

    def GetAvVectorPropsString(self):
        return AVAIVECTOR_PROPS  
    
    def GetAvVectorPropsList(self):
        return VECTOR_PROPS            
            
    def SetParameterValue(self, paramName, value):
        super(VectorProps, self).SetParameterValue(paramName, value)

        if paramName[-len(ACTIVE_KEY):] == ACTIVE_KEY:
            propName = paramName[0:-len(ACTIVE_KEY)]
            if propName in self.GetAvVectorPropsList():
                if value: 
                    self.results[propName] = None
                
                elif not value and propName in self.results.keys():
                    del self.results[propName]       

    def GetContents(self):
        # Will inherit the basic parameters in the Unitoperations and whatever in the self
        contents = super(VectorProps, self).GetContents()
        contents.extend(self.results.items())
        return contents

    def GetObject(self, desc):
        # Will inherit the basic parameters in the Unitoperations and whatever in the self
        object = super(VectorProps, self).GetObject(desc)
        if object:
            return object
        
        if desc in self.results.keys():
            return self.results[desc]

        return None
        
    def SolvePorts(self):
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)

        # share between in and out
        self.FlashAllPorts()
        inPort.ShareWith(outPort)
        self.FlashAllPorts()
        inPort.ShareWith(outPort)

    def Solve(self):
        self.SolvePorts()
        if self.IsForgetting(): return
        
        #Clear results
        for key in self.results.keys():
            self.results[key] = None
            
        #Get thermo
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: return 
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        fracs = self.portIn.GetCompositionValues()
        if None in fracs: return
        for propName in self.results.keys():
            if propName[:len(BOILINGCURVE_VEC)] == BOILINGCURVE_VEC:
                option = propName[len(BOILINGCURVE_VEC) + 1:]
                value, status = thAdmin.GetSpecialProperty(prov, case, option, fracs, BOILINGCURVE_VEC)
                try:
                    valsList = value.split()
                    rows, cols = len(valsList)/2, 2
                    vals = zeros((rows, cols), Float)
                    
                    count = 0
                    for i in range(rows):
                        vals[i][0] = float(valsList[count])
                        count += 1
                        vals[i][1] = float(valsList[count])
                        count += 1
                    
                    self.results[propName] = vals
                except:
                    self.results[propName] = None



#Independent props options
P_OPT = 'PRESSURE'
T_OPT = 'TEMPERATURE'
H_OPT = 'ENTHALPY'
S_OPT = 'ENTROPY'
VPFRAC_OPT = 'VF'

#Dependent props options
MASSDEN_OPT = 'MASSDENSITY'
VIS_OPT = 'VISCOSITY'
SPEEDSOUND_OPT = 'SPEEDOFSOUND'
MW_OPT = 'MOLECULARWEIGHT'
ZFAC_OPT = 'ZFACTOR'
VOL_OPT = 'VOLUME'
ENTHALPY_OPT = 'ENTHALPY'
ENTROPY_OPT = 'ENTROPY'
CP_OPT = 'CP'
CV_OPT = 'CV'
IGENTHALPY_OPT = 'IGENTHALPY'
IGENTROPY_OPT = 'IGENTROPY'
IGCP_OPT = 'IGCP'
RESIDUALENTHALPY_OPT = 'RESIDUALENTHALPY'
RESIDUALENTROPY_OPT = 'RESIDUALENTROPY'
RESIDUALCP_OPT = 'RESIDUALCP'
RESIDUALCV_OPT = 'RESIDUALCV'
THERMALCONDUCTIVITY_OPT = 'THERMALCONDUCTIVITY'
SURFACETENSION_OPT = 'SURFACETENSION'
ISOCOMPRESSIBILITY_OPT = 'ISOCOMPRESSIBILITY'
DPDVT_OPT = 'DPDVT'
IGFORMATION_OPT = 'IGFORMATION'
IGGIBBS_OPT = 'IGGIBBS'
MECHANICALZ_OPT = 'MECHANICALZ'
DVDTP_OPT = 'DVDTP'
PH_OPT = 'PH'
STDLIQDENSITY_OPT = 'STDLIQDENSITY'
STDLIQVOLUME_OPT = 'STDLIQVOLUME'
KINEMATICVISCOSITY_OPT = 'KINEMATICVISCOSITY'

#Phase options
BULK_OPT = 'FEED'
L_OPT = 'LIQUID'
V_OPT = 'VAPOR'
L2_OPT = 'LIQUID2'

#Independent props

XAXIS_PROPS = [P_OPT, T_OPT, H_OPT, S_OPT, VPFRAC_OPT]
XAXIS_PROP_TYPES = [P_VAR, T_VAR, H_VAR, S_VAR, VPFRAC_VAR]

YAXIS_PROPS = [P_OPT, T_OPT, H_OPT, S_OPT, VPFRAC_OPT]
YAXIS_PROP_TYPES = [P_VAR, T_VAR, H_VAR, S_VAR, VPFRAC_VAR]

#Dependent props
ZAXIS_PROPS =  [MASSDEN_OPT,
                VIS_OPT,
                SPEEDSOUND_OPT,
                MW_OPT,
                ZFAC_OPT,
                VOL_OPT,
                P_OPT, 
                T_OPT,
                VPFRAC_OPT,
                ENTHALPY_OPT,
                ENTROPY_OPT,
                CP_OPT,
                CV_OPT,
                IGENTHALPY_OPT,
                IGENTROPY_OPT,
                IGCP_OPT,
                RESIDUALENTHALPY_OPT,
                RESIDUALENTROPY_OPT,
                RESIDUALCP_OPT,
                RESIDUALCV_OPT,
                THERMALCONDUCTIVITY_OPT,
                SURFACETENSION_OPT,
                ISOCOMPRESSIBILITY_OPT,
                DPDVT_OPT,
                IGFORMATION_OPT,
                IGGIBBS_OPT,
                MECHANICALZ_OPT,
                DVDTP_OPT,
                PH_OPT,
                STDLIQDENSITY_OPT,
                STDLIQVOLUME_OPT,
                KINEMATICVISCOSITY_OPT]
ZAXIS_PROP_TYPES =  ['Density',
                     'Viscosity',
                     'Velocity',
                     None,
                     None,
                     'Volume',
                     'Pressure', 
                     'Temperature',
                     None,
                     'MolarEnthalpy',
                     'MolarSpecificHeat',
                     'MolarSpecificHeat',
                     'MolarSpecificHeat',
                     'MolarEnthalpy',
                     'MolarSpecificHeat',
                     'MolarSpecificHeat',
                     'MolarEnthalpy',
                     'MolarSpecificHeat',
                     'MolarSpecificHeat',
                     'MolarSpecificHeat',
                     'ThermalConductivity',
                     'SurfaceTension',
                     None,
                     'Pressure/MolarVolume',
                     'MolarEnthalpy',
                     'MolarEnthalpy',
                     None,
                     'ThermalExpansion', # This is a DVDTP property and the units are 1/K
                     None,
                     'Density',
                     'Volume',
                     'KinematicViscosity']

#Available parameters
AVAIXAXIS_PROPS = (P_OPT, T_OPT, H_OPT, S_OPT, VPFRAC_OPT)
AVAIXAXIS_PROPS = ' '.join(AVAIXAXIS_PROPS)

AVAIYAXIS_PROPS = (P_OPT, T_OPT, H_OPT, S_OPT, VPFRAC_OPT)
AVAIYAXIS_PROPS = ' '.join(AVAIYAXIS_PROPS)


AVAIZAXIS_PROPS =  (CP_OPT,
                    CV_OPT,
                    DPDVT_OPT,
                    DVDTP_OPT,
                    ENTHALPY_OPT,
                    ENTROPY_OPT,
                    IGCP_OPT,
                    IGENTHALPY_OPT,
                    IGENTROPY_OPT,
                    IGFORMATION_OPT,
                    IGGIBBS_OPT,
                    ISOCOMPRESSIBILITY_OPT,
                    KINEMATICVISCOSITY_OPT,
                    MASSDEN_OPT,
                    MECHANICALZ_OPT,
                    MW_OPT,
                    P_OPT,
                    PH_OPT,
                    RESIDUALCP_OPT,
                    RESIDUALCV_OPT,
                    RESIDUALENTHALPY_OPT,
                    RESIDUALENTROPY_OPT,
                    SPEEDSOUND_OPT,
                    STDLIQDENSITY_OPT,
                    STDLIQVOLUME_OPT,
                    SURFACETENSION_OPT,
                    T_OPT,
                    THERMALCONDUCTIVITY_OPT,
                    VIS_OPT,
                    VOL_OPT,
                    VPFRAC_OPT,
                    ZFAC_OPT)
AVAIZAXIS_PROPS = ' '.join(AVAIZAXIS_PROPS)

AVAIPHASE_STATUS = (BULK_OPT, L_OPT, V_OPT, L2_OPT)
AVAIPHASE_STATUS = ' '.join(AVAIPHASE_STATUS)


#Parameters
AVAIXAXISPROPS_PAR = 'AvailableXAxisProps'
AVAIYAXISPROPS_PAR = 'AvailableYAxisProps'
AVAIZAXISPROPS_PAR = 'AvailableZAxisProps'
AVAIPHASESTATUS_PAR = 'DependentPropPhaseStatus'
POINTSX_PAR = 'XPoints'
POINTSY_PAR = 'YPoints'
XPROP_PAR = 'XProperty'
YPROP_PAR = 'YProperty'
ZPROP_PAR = 'ZProperty'
PHASE_PAR = 'Phase'

#Ports
MINVX_PORT = 'XMin'
MAXVX_PORT = 'XMax'
MINVY_PORT = 'YMin'
MAXVY_PORT = 'YMax'

#Keys for extra objects
TABLEXY_KEY = 'TableXY'
TABLEXYZ_KEY = 'TableXYZ'
XUNIT_KEY = 'XUnit'
YUNIT_KEY = 'YUnit'
ZUNIT_KEY = 'ZUnit'

class PropertyTable(UnitOperations.UnitOperation):
    def __init__(self, initScript = None):
        super(PropertyTable, self).__init__(initScript)
        self.portOut = self.CreatePort(MAT|OUT, OUT_PORT)
        self.portOut.SetLocked(True)
        self.portIn = self.CreatePort(MAT|IN, IN_PORT)
        self.portIn.SetLocked(True)

        self.results = None
        self.xResults = None
        self.yResults = None
        self.zResults = None
        
        #set parameters yhis way so they do not get validated
        self.parameters[AVAIXAXISPROPS_PAR] = AVAIXAXIS_PROPS
        self.parameters[AVAIYAXISPROPS_PAR] = AVAIYAXIS_PROPS
        self.parameters[AVAIZAXISPROPS_PAR] = AVAIZAXIS_PROPS
        self.parameters[AVAIPHASESTATUS_PAR] = AVAIPHASE_STATUS

        #Create 2 signal ports for the X-Axis
        self.xMin = self.CreatePort(SIG, MINVX_PORT)
        self.xMax = self.CreatePort(SIG, MAXVX_PORT)

        #Create 2 signal ports for the Y-Axis
        self.yMin = self.CreatePort(SIG, MINVY_PORT)
        self.yMax = self.CreatePort(SIG, MAXVY_PORT)

        #keep the z type
        self.zTypes = None

        value = None       
        self.SetParameterValue(XPROP_PAR, value)
        self.SetParameterValue(POINTSX_PAR, value)
        self.SetParameterValue(YPROP_PAR, value)
        self.SetParameterValue(POINTSY_PAR, value)
        self.SetParameterValue(PHASE_PAR, value)
        self.SetParameterValue(ZPROP_PAR, value)
        
        self.tableXY = None
        self.tableXYZ = None
        
       

    def SetParameterValue(self, paramName, value):
        super(PropertyTable, self).SetParameterValue(paramName, value)

        if paramName == XPROP_PAR:
            if value in XAXIS_PROPS:
                type = XAXIS_PROP_TYPES[XAXIS_PROPS.index(value)]
                self.xMin.SetSignalType(type)
                self.xMax.SetSignalType(type)
            else:
                self.xMin.SetSignalType(GENERIC_VAR)
                self.xMax.SetSignalType(GENERIC_VAR)

        elif paramName == YPROP_PAR:
            if value in YAXIS_PROPS:
                type = YAXIS_PROP_TYPES[YAXIS_PROPS.index(value)]
                self.yMin.SetSignalType(type)
                self.yMax.SetSignalType(type)
            else:
                self.yMin.SetSignalType(GENERIC_VAR)
                self.yMax.SetSignalType(GENERIC_VAR)

        elif paramName == ZPROP_PAR:
            zTypes = []
            if value != None:
                values = value.split()    
                for value in values:
                    if value in ZAXIS_PROPS:
                        type = ZAXIS_PROP_TYPES[ZAXIS_PROPS.index(value)]
                        zTypes.append(S42Glob.unitSystem.GetTypeID(type))
                        #self.zType = S42Glob.unitSystem.GetTypeID(type)
                    else:
                        zTypes.append(None)
                        #self.zType = None
            self.zTypes = zTypes
            
    def ValidateParameter(self, paramName, value):
        super(PropertyTable, self).ValidateParameter(paramName, value)

        if not super(PropertyTable, self).ValidateParameter(paramName, value):
            return False

        #if paramName == AVAIXAXISPROPS_PAR:
            #return False
            
        #if paramName == AVAIYAXISPROPS_PAR:
            #return False

        #if paramName == AVAIZAXISPROPS_PAR:
            #return False
            
        #if paramName == AVAIPHASESTATUS_PAR:
            #return False

        if paramName == POINTSX_PAR or paramName == POINTSY_PAR:
            if value <= 0 and value >= 500:
                return False

        if paramName == XPROP_PAR or paramName == YPROP_PAR:
            if value not in XAXIS_PROPS and value != None:
                return False
        
        return True                

    def GetContents(self):
        # Will inherit the basic parameters in the Unitoperations and whatever in the self
        contents = super(PropertyTable, self).GetContents()
        
        #TABLE_KEY is an object 'you' created
        contents.append((TABLEXY_KEY, self.tableXY))
        contents.append((TABLEXYZ_KEY, self.tableXYZ))

        return contents

    def GetObject(self, desc):
        # Will inherit the basic parameters in the Unitoperations and whatever in the self
        object = super(PropertyTable, self).GetObject(desc)
        if object:
            return object
        
        if desc == TABLEXY_KEY:
            return self.tableXY

        if desc == TABLEXYZ_KEY:
            try:
                #Return the first one for backward compatibility
                return self.tableXYZ[0]
            except:
                return None
            
        if desc[0:len(TABLEXYZ_KEY)]:
            try:
                #Requested by index
                idx = int(desc[len(TABLEXYZ_KEY):])
                return self.tableXYZ[idx]
            except:
                try:
                    #Requested by prop name 
                    zPropName = desc[len(TABLEXYZ_KEY):].strip()
                    zPropNames = self.GetParameterValue(ZPROP_PAR)
                    zPropNames = zPropNames.split()
                    if zPropName in zPropNames:
                        idx = zPropNames.index(zPropName)
                        return self.tableXYZ[idx]
                        
                except:
                    return None
        
        
        return None
                    
    def SolvePorts(self):
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)

        # share between in and out
        self.FlashAllPorts()
        inPort.ShareWith(outPort)
        self.FlashAllPorts()
        inPort.ShareWith(outPort)


    def Solve(self):
        self.SolvePorts()
        self.unitOpMessage = ('NoMessage', )
        if self.IsForgetting(): return
        
        self.fullArray = None
        self.tableXY = None
        self.tableXYZ = None
        
        
        #Get thermo
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: return 
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        fracs = self.portIn.GetCompositionValues()
        if None in fracs: return
        propX = self.GetParameterValue(XPROP_PAR)
        propY = self.GetParameterValue(YPROP_PAR)
        propZ = self.GetParameterValue(ZPROP_PAR)
        if not propZ: return
        propZLst = propZ.split()
        nuZProps = len(propZLst)
        
        phase = self.GetParameterValue(PHASE_PAR)
        pointX = self.GetParameterValue(POINTSX_PAR)
        pointY = self.GetParameterValue(POINTSY_PAR)
        
        xMin = self.xMin.GetValue()
        xMax = self.xMax.GetValue()
        yMax = self.yMax.GetValue()
        yMin = self.yMin.GetValue()
        
        if None in (propX, propY, propZ, phase, pointX, pointY, xMin, xMax, yMax, yMin):
            return
        
        if propX in propZLst or propY in propZLst:
            statusOut = "This version can not have X-Variable or Y-Variable repeated in the list of Z-Variables"
            self.unitOpMessage = ('ThermoProviderMsg', (statusOut,))
            self.InfoMessage('ThermoProviderMsg', (self.GetPath(), statusOut))
            self.fullArray = None
            self.tableXY = None
            self.tableXYZ = None
            return
            
        option = "%s %s %s END %s GRID %s %s %s %s %s %s DEFAULT XY" %(propX, propY, propZ, phase, str(xMin), str(xMax), str(pointX), str(yMin), str(yMax), str(pointY))
        #Pass the number of points so the string buffer can be dinamically created
        nuPoints = (5 + nuZProps) * (pointX * pointY)
        value, status = thAdmin.GetSpecialProperty(prov, case, option, fracs, PROPERTYTABLE_MATRIX, nuPoints)
        statusOut = ''
        try:
            valsList = value.split()
            valsList = map(float, valsList)
            fullArray = Numeric.reshape(valsList, (len(valsList)/(5+nuZProps), (5+nuZProps)))
            
            #Full array now looks like this:
            #X0 Y0 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #X0 Y1 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #X0 Y2 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #...
            #X0 YpointY Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            
            #X1 Y0 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #X1 Y1 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #X1 Y2 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #...
            #X1 YpointY Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            
            #...
            
            #XpointX Y0 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #XpointX Y1 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #XpointX Y2 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            #...
            #XpointX YpointY Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
            
            self.fullArray = fullArray
            self.tableXY = TableXY(self, TABLEXY_KEY, fullArray, pointX, pointY, nuZProps)
            self.tableXYZ = []
            for i in range(nuZProps):
                self.tableXYZ.append(TableXYZ(self, TABLEXYZ_KEY, fullArray, pointX, pointY, i))
                #self.tableXYZ = TableXYZ(self, TABLEXYZ_KEY, fullArray, pointX, pointY, nuZProps)
            if status[0:2] != 'OK':
                statusOut += status

        except:
            self.fullArray = None
            self.tableXY = None
            self.tableXYZ = None
            
        if not statusOut:
            statusOut = 'OK'
            self.unitOpMessage = ('ThermoProviderMsg', (statusOut,))
        else:
            self.unitOpMessage = ('ThermoProviderMsg', (statusOut,))
            self.InfoMessage('ThermoProviderMsg', (self.GetPath(), statusOut))

    def AdjustOldCase(self, version):
        
        super(PropertyTable, self).AdjustOldCase(version)
        
        
        if version[0] < 62:
            if not hasattr(self, 'zTypes'):
                self.zTypes = None
            if hasattr(self, 'zType'):
                if self.zType != None:
                    self.zTypes = [self.zType]
                del self.zType
        if version[0] < 63:
            if not hasattr(self, 'tableXYZ'):
                self.tableXYZ = None
            if self.tableXYZ != None and not isinstance(self.tableXYZ, list):
                self.tableXYZ = [self.tableXYZ]
        try:
            if self.tableXY:
                self.tableXY.AdjustOldCase(version)
            if self.tableXYZ:
                for t in self.tableXYZ:
                    t.AdjustOldCase(version)
            
        except:
            pass
    def CleanUp(self):
        try:
            if self.tableXY != None:
                self.tableXY.CleanUp()
            if self.tableXYZ != None:
                for table in self.tableXYZ:
                    table.CleanUp()
            self.tableXY = None
            self.tableXYZ = None
        except:
            pass
        
        super(PropertyTable, self).CleanUp()
        

    def DeleteObject(self, obj):
        super(PropertyTable, self).DeleteObject(obj)
        paramName = obj.name
        if paramName == XPROP_PAR or paramName == YPROP_PAR or paramName == ZPROP_PAR:
            self.ForgetAllCalculations()
        
        
class Table(object):
    def __init__(self, parent, name, table, pointX, pointY, nuZProps):
        self.parent = parent
        self.name = name
        self.table = table
        self.xUnit = None
        self.yUnit = None
        self.zUnits = None
        self.pointX = pointX
        self.pointY = pointY
        self.nuZProps = nuZProps
            
    def CleanUp(self):
        self.parent = None
        
    def AdjustOldCase(self, version):
        if version[0] < 62:
            if not hasattr(self, 'zUnit'):
                self.zUnits = [self.zUnit]
            if not hasattr(self, 'nuZProps'):
                self.nuZProps = 1
                
    def GetParent(self):
        return self.parent

    def GetPath(self):
        return self.parent.GetPath() + "." + self.name

    def GetContents(self):
        results = []
        results.append((XUNIT_KEY, self.xUnit))
        results.append((YUNIT_KEY, self.yUnit))
        cnt = 0
        for unit in self.zUnits:
            results.append((ZUNIT_KEY + str(cnt), self.zUnits[cnt]))
            cnt += 1
        return results

    def GetObject(self, desc):
        if desc == XUNIT_KEY: return self.xUnit
        elif desc == YUNIT_KEY: return self.yUnit
        elif desc[:len(ZUNIT_KEY)] == ZUNIT_KEY:
            idx = int(desc[len(ZUNIT_KEY):])
            return self.zUnits[idx]

    def GetValues(self):
        return self.table
            
    def GetArrayRepresentation(self):
        return self.table

    def GetConvertedArrayRepresentation(self, unitSystem):
        xType = self.parent.xMin.GetType().unitType
        unit = unitSystem.GetCurrentUnit(xType)
        if unit:
            x = array(map(unit.ConvertFromSim42, self.x))
            self.xUnit = unit.name
        else:
            x = self.x
            self.xUnit = None
        
        yType = self.parent.yMin.GetType().unitType
        unit = unitSystem.GetCurrentUnit(yType)
        if unit:
            y = array(map(unit.ConvertFromSim42, self.y))
            self.yUnit = unit.name
        else:
            y = self.y
            self.yUnit = None
            
        nuZProps = self.nuZProps
        self.zUnits = []
        for i in range(nuZProps):
            
            zType = self.parent.zTypes[i]
            unit = unitSystem.GetCurrentUnit(zType)
            if unit:
                z = array(map(unit.ConvertFromSim42, self.z[:, i]))
                self.zUnits.append(unit.name)
            else:
                z = self.z[:, i]
                self.zUnits.append(None)
            self.convTable[:,2+i] = z[:]
            
        self.convTable[:,0] = x
        self.convTable[:,1] = y

        return self.convTable        

    def SetParent(self, parent):
        self.parent = parent
        
    def Clone(self):
        f = UnitOperations._SafeClone
        clone = self.__class__(None, self.name, f(self.table), f(self.pointX), f(self.pointY), f(self.nuZProps))
        return clone
    
                              
class TableXY(Table):
    def __init__(self, parent, name, table, pointX, pointY, nuZProps):
        super(TableXY, self).__init__(parent, name, table, pointX, pointY, nuZProps)
        self.convTable = array(table, Float)
        
        #Keep direct references to x, y and z for unit conversions
        self.x = table[:,0]
        self.y = table[:,1]
        self.z = table[:,2:2+nuZProps]
        
        #self.x, self.y and self.z keep this format
        #Full array now looks like this:
        #X0 Y0 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #X0 Y1 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #X0 Y2 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #...
        #X0 YpointY Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        
        #X1 Y0 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #X1 Y1 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #X1 Y2 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #...
        #X1 YpointY Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        
        #...
        
        #XpointX Y0 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #XpointX Y1 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #XpointX Y2 Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac
        #...
        #XpointX YpointY Z0 Z1 ... ZnuZProps VapFrac Liq0Frac Liq1Frac        
        
    def AdjustOldCase(self, version):
        super(TableXY, self).AdjustOldCase(version)
        if version[0] < 64:
            self.z = self.table[:,2:2+self.nuZProps]

                        
class TableXYZ(Table):
    def __init__(self, parent, name, table, pointX, pointY, zPropIdx):
        super(TableXYZ, self).__init__(parent, name, table, pointX, pointY, 1)
        self.convTable = zeros((pointX+1, pointY+1), Float)
        self.zPropIdx = zPropIdx
        
        #Keep direct references to x, y and z for unit conversions
        self.x = table[0::pointY, 0]
        self.y = table[0:pointY, 1]
        self.z = table[:,zPropIdx+2]
        
        #x and y are only the vectors of their different values
        #self.x = X0 X1 X2 ... XpointX
        #self.y = Y0 Y1 Y2 ... ypointY
        
        #z is the matrix of all the values
        
    def AdjustOldCase(self, version):
        super(TableXYZ, self).AdjustOldCase(version)
        if version[0] < 63:
            if not hasattr(self, 'zPropIdx'):
                self.zPropIdx = 0
            
    def GetConvertedArrayRepresentation(self, unitSystem):
        xType = self.parent.xMin.GetType().unitType
        unit = unitSystem.GetCurrentUnit(xType)
        if unit:
            x = array(map(unit.ConvertFromSim42, self.x))
            self.xUnit = unit.name
        else:
            x = self.x
            self.xUnit = None
        
        yType = self.parent.yMin.GetType().unitType
        unit = unitSystem.GetCurrentUnit(yType)
        if unit:
            y = array(map(unit.ConvertFromSim42, self.y))
            self.yUnit = unit.name
        else:
            y = self.y
            self.yUnit = None
            
        self.zUnits = []
        zPropIdx = self.zPropIdx
        zType = self.parent.zTypes[zPropIdx]
        unit = unitSystem.GetCurrentUnit(zType)
        if unit:
            z = array(map(unit.ConvertFromSim42, self.z))
            self.zUnits.append(unit.name)
        else:
            z = self.z
            self.zUnits.append(None)
            
        self.convTable[1:,1:] = Numeric.reshape(z, (self.pointX, self.pointY))
        self.convTable[0,1:] = y
        self.convTable[1:,0] = x

        return self.convTable
    
    def Clone(self):
        f = UnitOperations._SafeClone
        clone = self.__class__(None, self.name, f(self.table), f(self.pointX), f(self.pointY), f(self.zPropIdx))
        return clone
