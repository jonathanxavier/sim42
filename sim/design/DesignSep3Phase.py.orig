""" Design procedure for Three-Phase separators based on Wayne D. Monnery & William Y. Svrcek mathematical procedures.
    Simulation design procedure by Shahrul Zainal and Izzi Alias
    ref: Succesfully Specify Three-Phase Separators
"""

import Design, DesignTools
from Design import BasicDesignParameter
from Design import STR_INFO, INT_INFO, FLT_INFO, BOOL_INFO, OPT_INFO
from Design import PORT_INFO, INLET_INFO, OUTLET_INFO, USESUNIT_INFO
from DesignTools import HNATable, GTable, FinalValue, VesselWeightAndWallThickness, Kvalue

from sim.solver.Variables import *
from sim.solver import S42Glob
from sim.unitop import Flash

import numpy.oldnumeric, math
from math import log, pi, ceil
PI = math.pi


VALID_DESIGN_OBJECTS = ['Vertical',
                        'Horizontal',
                        'HorizontalWithBoot',
                        'HorizontalWithWeir',
                        'HorizontalWithWeirAndBucket']

FIELD_UNIT_SET = 'Field'

   
# The base class for three-phase separator
class Separator3Phase(Design.DesignMain):
    def __init__(self):
        super(Separator3Phase, self).__init__()

        #Define a generic typeInfo
        genInfoType = INLET_INFO|FLT_INFO|PORT_INFO|USESUNIT_INFO
        genOutputType = OUTLET_INFO|FLT_INFO|USESUNIT_INFO

        #Load objects where input will be stored
        self._input['VapMassFlow']   = BasicDesignParameter(self, 'VapMassFlow', genInfoType, MASSFLOW_VAR, idx=0)
        self._input['LLiqMassFlow']  = BasicDesignParameter(self, 'LLiqMassFlow', genInfoType, MASSFLOW_VAR, idx=2)
        self._input['HLiqMassFlow']  = BasicDesignParameter(self, 'HLiqMassFlow', genInfoType, MASSFLOW_VAR, idx=4)
        self._input['VapDensity'] = BasicDesignParameter(self, 'VapDensity', genInfoType, MASSDEN_VAR, idx=6)
        self._input['LLiqDensity'] = BasicDesignParameter(self, 'LLiqDensity', genInfoType, MASSDEN_VAR, idx=8)
        self._input['HLiqDensity'] = BasicDesignParameter(self, 'HLiqDensity', genInfoType, MASSDEN_VAR, idx=10)
        self._input['LLiqViscosity']  = BasicDesignParameter(self, 'LLiqViscosity', genInfoType, VISCOSITY_VAR, idx=12)
        self._input['HLiqViscosity']  = BasicDesignParameter(self, 'HLiqViscosity', genInfoType, VISCOSITY_VAR, idx=14)
        self._input[P_VAR]    = BasicDesignParameter(self, P_VAR, genInfoType, P_VAR, idx=16)
        self._input['HoldupTime']   = BasicDesignParameter(self, 'HoldupTime', INLET_INFO|FLT_INFO|USESUNIT_INFO, TIME_VAR,idx=18)
        self._input['SurgeTime']   = BasicDesignParameter(self, 'SurgeTime', INLET_INFO|FLT_INFO|USESUNIT_INFO, TIME_VAR, idx=20)
        self._input['Mist'] = BasicDesignParameter(self, 'MistEliminator', INLET_INFO|BOOL_INFO, idx=22)
        self._input['Liq-LiqSepType']    = BasicDesignParameter(self, 'Liq-LiqSepType', INLET_INFO|STR_INFO|OPT_INFO, None, ['HC-Water', 'HC-Caustic', 'Other'], idx=24)
        self._input['ServiceType']    = BasicDesignParameter(self, 'ServiceType', INLET_INFO|STR_INFO|OPT_INFO, None, ['Refinery', 'PetChem', 'Other'], idx=26)
##        self._input['LLiqResidenceTime'] = BasicDesignParameter(self, 'LLiqResidenceTime', INLET_INFO|FLT_INFO|USESUNIT_INFO, TIME_VAR)
        

        #Load objects where output will be stored
        self._output['VesselLength'] = BasicDesignParameter(self, 'Length', genOutputType, LENGTH_VAR, idx=0)
        self._output['VesselDiameter'] = BasicDesignParameter(self, 'Diameter', genOutputType, LENGTH_VAR, idx=2)
        self._output['LDratio'] = BasicDesignParameter(self, 'LDratio', OUTLET_INFO|FLT_INFO, GENERIC_VAR, idx=4)
        self._output['VapDisengagementHeight'] = BasicDesignParameter(self, 'VapDisengagementHeight', genOutputType, LENGTH_VAR, idx=6)
        self._output['NormalLiqLevel'] = BasicDesignParameter(self, 'NormalLiqLevel', genOutputType, LENGTH_VAR, idx=8)
        self._output['HighLiqLevel'] = BasicDesignParameter(self, 'HighLiqLevel', genOutputType, LENGTH_VAR, idx=10)
##        self._output['LowLiqLevel'] = BasicDesignParameter(self, 'LowLiqLevel', genOutputType, LENGTH_VAR)
        self._output['VesselWeight'] = BasicDesignParameter(self, 'Weight', genOutputType, MASS_VAR, idx=12)
        self._output['VesselWallThickness'] = BasicDesignParameter(self, 'WallThickness', genOutputType, LENGTH_VAR, idx=14)


    def LoadInputFromParent(self):
        """Get the input from the parent unit operation (if any)"""
        if not self.parent: return
        vapPort = self.parent.GetPort(V_PORT)
        lliqPort = self.parent.GetPort(L_PORT + '0')
        hliqPort = self.parent.GetPort(L_PORT + '1')

        if None in (vapPort, lliqPort, hliqPort):
            self.parent.InfoMessage('WrongParentDesignObj', (self.GetPath(),))
            self._readyForSolve = False

        if not vapPort.AlreadyFlashed() or not lliqPort.AlreadyFlashed() or not hliqPort.AlreadyFlashed():
            self.parent.InfoMessage('PortNotFlashedDesignObj', (self.GetPath(),))
            self._readyForSolve = False
            

        #Load info from the vapour port
        port = vapPort
        propList = [MASSDEN_VAR]
        P = port.GetPropValue(P_VAR)
        Wv = port.GetPropValue(MASSFLOW_VAR)
        den = port.GetPropValue(MASSDEN_VAR)
        if den == None:
            H = port.GetPropValue(H_VAR)
            fracs = port.GetCompositionValues()
            vals = self.GetProperties(P, H, fracs, propList)
            if vals:
                den = vals[0]
                
        self._input[P_VAR].SetValue(P)
        self._input['VapMassFlow'].SetValue(Wv)
        self._input['VapDensity'].SetValue(den)

        
        #Load info from the lliq port
        port = lliqPort
        Wll = port.GetPropValue(MASSFLOW_VAR)
        propList = [MASSDEN_VAR, VISCOSITY_VAR]
        den = port.GetPropValue(MASSDEN_VAR)
        visc = port.GetPropValue(VISCOSITY_VAR)
        if None in (den, visc):
            H = port.GetPropValue(H_VAR)
            fracs = port.GetCompositionValues()
            vals = self.GetProperties(P, H, fracs, propList)
            if vals:
                den, visc = vals[0], vals[1]
        self._input['LLiqDensity'].SetValue(den)
        self._input['LLiqViscosity'].SetValue(visc)
        self._input['LLiqMassFlow'].SetValue(Wll)
        

        #Load info from the hliq port
        port = hliqPort
        Whl = port.GetPropValue(MASSFLOW_VAR)
        propList = [MASSDEN_VAR, VISCOSITY_VAR]
        den = port.GetPropValue(MASSDEN_VAR)
        visc = port.GetPropValue(VISCOSITY_VAR)
        if None in (den, visc):
            H = port.GetPropValue(H_VAR)
            fracs = port.GetCompositionValues()
            vals = self.GetProperties(P, H, fracs, propList)
            if vals:
                den, visc = vals[0], vals[1]
        self._input['HLiqDensity'].SetValue(den)
        self._input['HLiqViscosity'].SetValue(visc)
        self._input['HLiqMassFlow'].SetValue(Whl)

    def GetProperties(self, P, H, fracs, propList):
        """Gets the requested list of properties for the particular system"""
        if not self.parent:
            return None
        thCaseObj = self.parent.GetThermo()
        if not thCaseObj:
            return None
        
        thAdmin, prov, case = self.parent.GetThermoAdmin(), thCaseObj.provider, thCaseObj.case
        inProp1 = [P_VAR, P]
        inProp2 = [H_VAR, H]
        vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, OVERALL_PHASE, fracs, propList)        
        return vals  

    
    def GetValueInFieldUnits(self, designParam):
        """Receives an instance of a BasicDesignParameter object and returns its value in field units (if possible)"""
        val = None
        try:
            val = designParam.GetValue()
            if val != None and designParam.GetInfoType() & USESUNIT_INFO:
                unitType = designParam.GetType().unitType
                if unitType:
                    unit = S42Glob.unitSystem.GetSim42Unit(unitType)
                    val = unit.ConvertToSet(FIELD_UNIT_SET, val)
        finally:
            return val

    def SetValueFromFieldUnits(self, designParam, valueInField):
        """Receives an instance of a BasicDesignParameter object (designParam) and a value (valueInField). Converts valueInField into sim42 units and sets it into designParam"""
        val = valueInField
        try:
            if val != None and designParam.GetInfoType() & USESUNIT_INFO:
                unitType = designParam.GetType().unitType
                if unitType:
                    unit = S42Glob.unitSystem.GetSim42Unit(unitType)
                    val = unit.ConvertFromSet(FIELD_UNIT_SET, valueInField)
        finally:
            designParam.SetValue(val)
        
    def Initialize(self):
        # Get al the inputs, change units from sim42 to field if necessary
        Wv = self.GetValueInFieldUnits(self._input['VapMassFlow'])
        Wll = self.GetValueInFieldUnits(self._input['LLiqMassFlow'])
        Whl = self.GetValueInFieldUnits(self._input['HLiqMassFlow'])
        rhov = self.GetValueInFieldUnits(self._input['VapDensity'])
        rhol = self.GetValueInFieldUnits(self._input['LLiqDensity'])
        rhoh = self.GetValueInFieldUnits(self._input['HLiqDensity'])
        mul = self.GetValueInFieldUnits(self._input['LLiqViscosity'])
        muh = self.GetValueInFieldUnits(self._input['HLiqViscosity'])
        P = self.GetValueInFieldUnits(self._input[P_VAR])
        Th = self._input['HoldupTime'].GetValue()
        if Th == None:
            self._readyForSolve = False
            return None
        Th = Th/60.0      # from seconds to minutes
        
        Ts = self._input['SurgeTime'].GetValue()
        if Ts == None:
            self._readyForSolve = False
            return None
        Ts = Ts/60.0      # from seconds to minutes
        
        Mist = self._input['Mist'].GetValue()
        
        mySepType = self._input['Liq-LiqSepType'].GetValue()
        if mySepType == 'HC-Water' or mySepType == 'HC-Caustic':
            Ks = 0.333
        else:
            Ks = 0.163
        myServiceType = self._input['ServiceType'].GetValue()
        if myServiceType == 'N/A':
            Tihl = 0.0
        if myServiceType == 'Refinery':
            Tihl = 60.0
        else:
            Tihl = 12.0

        Till = 25.0
            
        # Calculate the volumetric flowrate
        Qv = Wv/(3600*rhov)
        Qll = Wll/(60*rhol)
        Qhl = Whl/(60*rhoh)

        # Find K, calculate Ut and set Uv
##        if (P-14.7) > 0.0 and (P-14.7) < 1500.0:
##            if Mist == 0:
##                K = (0.35 - 0.0001*((P-14.7) - 100))/2.0
##            else:
##                K = (0.35 - 0.0001*((P-14.7) - 100))
##        else:
        K = Kvalue(P)
            
        Ut = K*((rhol - rhov)/ rhov)**0.5
        Uv = 0.75*Ut

        # Calculate Holdup and Surge volume
        Vh = Th*Qll
        Vs = Ts*Qll

        # Initialize LD
        if P >= 14.7 and P <= 264.7:
            LD = 1.5/250.0*(P-14.7)+1.5
        elif P > 264.7 and P <= 514.7:
            LD = 1.0/250.0*(P-14.7)+2.0
        elif P > 514.7:
            LD = 5.0
        else:
            self._readyForSolve = False
            return None
##            if self.parent:
##                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
              
        
        return Wv, Wll, Whl, rhov, rhol, rhoh, mul, muh, P, Ts, Th, Mist, Ks, Qv, Qll, Qhl, K, Ut, Uv, Vh, Vs, LD, Till, Tihl

    def RecalculateLD(self, L, D):
        converged = False
        while not converged:
                LD = L / D
                if (LD < 1.5):
                    D = D - 0.5
                    converged = False
                elif (LD > 6.0):
                    D = D + 0.5
                    converged = False
                else:
                    converged = True
                    
        return D, LD


class Vertical(Separator3Phase):
    def __init__(self):
        super(Vertical, self).__init__()
           
    def Solve(self):
        #Let it do the basic steps and leave if it can not solve
        super(Vertical, self).Solve()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return

        results = self.Initialize()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return

        Wv, Wll, Whl, rhov, rhol, rhoh, mul, muh, P, Ts, Th, Mist, Ks, Qv, Qll, Qhl, K, Ut, Uv, Vh, Vs, LD, Till, Tihl = results

        Hl = 1.0       # height from liquid interface to light liquid nozzle, ft
        Hr = 12.0      # height from light liquid nozzle to baffle, inch
        Hh = 1.0       # holdup height, ft
        converged = False
        
        # Calculate vessel internal diameter
        Dvd = (4.0*Qv/(pi*Uv))**0.5
        if int(Mist) == 1:
            Dvd = Dvd + 0.4
              
        D = FinalValue(Dvd)
        
        # Calculate the setting velocity of heavy liquid
        Uhl = Ks*(rhoh-rhol)/mul
        # Calculate the setting velocity of heavy liquid
        Ulh = Ks*(rhoh-rhol)/muh
        # Calculate the setling time of the heavy liq out of the light liq and vice versa
        Thl = 12.0*Hl/Uhl
        Tlh = 12.0*Hh/Ulh
        # use Gtable to find G
        DRho = rhol - rhov
        Hlr = Hl*12.0 + Hr
        G = GTable(DRho, Hlr)
        # Calculate Ad
        Ad  = 7.48*60.0*(Qll+Qhl)/G
        # Assume the downcomer chord width, Wd = 4 inch
        
        while not converged:
            Wd = 4.0
            Wdd = Wd/(D*12.0)
            At = (pi*D**2)/4
            Y = HNATable(1, Wdd)
            Ad = Y*At
            Al = At - Ad
            # Calc. the residence time fo each phase
            Till = Hl*Al/Qll
            Ah = At
            Tihl = Hh*Ah/Qhl
            # Check for convergence
            if Till < Thl or Tihl < Tlh:
                D = D + 0.5
                converged = False
            else:
                converged = True
        
        converged = False
        
        # Calc. the height of the light liquid
        Hr = Qll*Th/Al
        # Calc. surge height
        Hs = Qll*Th/Al
        # Calc. inlet nozzle size, dN in ft
        lamda = (Qll+Qhl)/(Qll+Qhl+Qv*60.0)
        rhoLiq = (Wll/(Wll+Whl))*rhol + (Whl/(Wll+Whl))*rhoh            # use mix liquid density of light and heavy liquids
        rhoMix = rhoLiq*lamda + rhov*(1.0-lamda)
        Qm = Qv + (Qll + Qhl)/60.0
        dN = (4.0*Qm/(60.0*pi/(rhoMix**0.5)))**0.5
        dN = FinalValue(dN)

        # Calc. vessel height
        Hd1 = 0.5*D
        Hd2 = 3.0 + dN/2.0
        if int(Mist) == 1:
            Hd2 = 2.0 + dN/2.0

        Hd = Hd2
        if Hd1 > Hd2:
            Hd = Hd1
        
        Hs1 = Hs + 0.5
        if Hs1 <= 2.0:
            Hs1 = 2.0
        
        Hbn = 0.5*dN + Hs1
        Ha = 0.5    # Set
        Ht = Hh + Hl + Hr + Ha + Hbn + Hd
        if int(Mist) == 1:
            Ht = Ht + 1.5

        Htd = Ht/D
        while not converged:
            # Add 2 ft to Ht by adding 0.5 to Hr and 1.5 to Hd
            if Htd < 1.5:
                Hh = round(Hh, 0)
                Hl = round(Hh, 0)
                Hr = ceil(Hr)
                Hbn = round(Hbn, 0)
                Hd = ceil(Hd)+ 1.0
                
            Ht = Hh + Hl + Hr + Ha + Hbn + Hd
            if int(Mist) == 1:
                Ht = Ht + 1.5
                
            Htd = Ht/D      # Htd should be between 1.5 to 6.0
            if Htd < 1.5:
                Hd = Hd + 0.5
                Hbn = Hbn + 0.5
                converged = False
            else:
                converged = True
        
        converged = False
        
        # Find Normal and Maximum liquid level
        Hhll = Hh + Hl + Hr + Ha + Hs
        Hnll = Hhll - Hs

        # Calculate the vessel weight and wall thickness
        VW, VWT = VesselWeightAndWallThickness(P, D, Ht)
        
        # send the outputs
        self.SetValueFromFieldUnits(self._output['VesselLength'], Ht)
        self.SetValueFromFieldUnits(self._output['VesselDiameter'], D)
        self._output['LDratio'].SetValue(Htd)
        self.SetValueFromFieldUnits(self._output['VapDisengagementHeight'], Hd)
        self.SetValueFromFieldUnits(self._output['NormalLiqLevel'], Hnll)
        self.SetValueFromFieldUnits(self._output['HighLiqLevel'], Hhll)
        self.SetValueFromFieldUnits(self._output['VesselWeight'], VW)
        self.SetValueFromFieldUnits(self._output['VesselWallThickness'], VWT)
        
class Horizontal(Separator3Phase):

    def __init__(self):
        super(Horizontal, self).__init__()
        
    def Solve(self):
        super(Horizontal, self).Solve()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return
        
        results = self.Initialize()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return

        Wv, Wll, Whl, rhov, rhol, rhoh, mul, muh, P, Ts, Th, Mist, Ks, Qv, Qll, Qhl, K, Ut, Uv, Vh, Vs, LD, Till, Tihl = results
        
        Hll = 1.0       #lightliquid level
        Hhl = 1.0       #heavyliquid level
        converged = False
        converged1 = False
        converged2 = False
        
        D = (4.0*(Vh+Vs)/(0.5*pi*LD))**(1.0/3.0)
        if (D <= 4.0):
            D = 4.0
        while not converged:
            At = pi*(D**2)/4.0
            Hv = 0.2*D
            if int(Mist) == 1:
                if Hv <= 2.0:
                    Hv = 2.0
            else:
                if Hv <= 1.0:
                    Hv = 1.0

            X1 = Hv/D
            X2 = (Hll + Hhl)/D
            Av = HNATable(1, X1)*At
            Allh = HNATable(1, X2)*At
            # Calculate minimum length
            L = (Vh + Vs)/(At-Av-Allh)
            # Calculate liquid dropout
            Phi = Hv/Uv
            # Calculate actual vapor velocity
            Uva = Qv/Av
            # Calculate L minimum for vapor-liquid separation
            Lmin = Uva*Phi
            Li = L

            sign = -1.0
            needToIter = False

            if L < Lmin:
                Li = Lmin

            if L < (0.8*Lmin):
                sign = 1.0
                needToIter = True
                
            if L > (1.2*Lmin):
                if int(Mist) == 1 and Hv <= 2.0:
                    Hv = 2.0
                    Li = L
                elif not int(Mist) == 0 and Hv <= 1.0:
                    Hv = 1.0
                    Li = L
                else:
                    needToIter = True

            if needToIter:
                innerIter = 0
                while not converged1 and innerIter < self.maxIter:
                    innerIter += 1
                    Hv = Hv + sign*0.5
                    if int(Mist) == 1 and Hv <= 2.0:   # baru tambah Bang !
                        Hv = 2.0
                    if int(Mist) == 0 and Hv <= 1.0:   # baru tambah Bang !
                        Hv = 1.0
                    Hll = 1.0
                    Hhl = 1.0
                    X1 = Hv/D
                    X2 = (Hll + Hhl)/D
                    Y1 = HNATable(1, X1)
                    Av = Y1*At
                    Y2 = HNATable(1, X2)
                    Allh = Y2*At
                    Li = (Vh + Vs)/(At-Av-Allh)
                    Phi = Hv/Uv
                    Uva = Qv/Av
                    Lmin = Uva*Phi
                    if Li < (0.8*Lmin):
                        sign = 1.0
                        converged1 = False
                    if Li > (1.2*Lmin):
                        sign = -1.0
                        converged1 = False
                    else:
                        Li = Li
                        converged1 = True
                if not converged1 and self.parent:
                    self.parent.InfoMessage('CouldNotConvergeInner', (self.GetPath(), self.maxIter))
            converged1 = False
            L = Li
            
            # Calculate the setting velocity of heavy liquid, inch/min
            Uhl = Ks*(rhoh-rhol)/mul
            # Calculate the setting velocity of heavy liquid, inch/min
            Ulh = Ks*(rhoh-rhol)/muh
            # Calculate the setling time of the heavy liq out of the light liq and vice versa, min
            Thl = 12.0*(D-Hv-Hhl)/Uhl
            Tlh = 12.0*Hhl/Ulh
            # Calculate Ahl and All
            Ahl = HNATable(1, Hhl/D)*At
            All = Allh-Ahl
            La = Tlh*Qhl/Ahl
            Lb = Thl*Qll/(At-Av-Ahl)

            innerIter = 0
            # Calculate the residence time of the heavy liq out of the light liq and vice versa
            while not converged2 and innerIter < self.maxIter:
                innerIter += 1
                Tihl = Ahl*L/Qhl
                Till = (At-Av-Ahl)*L/Qll            
                if Tihl <= Tlh or Till < Thl:
                    if La > Lb:
                        L = La
                        converged2 = False
                    else:
                        L = Lb
                        converged2 = False
                else:
                    converged2 = True

            if not converged2 and self.parent:
                    self.parent.InfoMessage('CouldNotConvergeInner', (self.GetPath(), self.maxIter))

            # Calculate L/D
            converged2 = False
            LD = L/D

            # Check L/D
            if LD < 1.2:
                if (D <= 4.0):
                    D = D
                    converged = True
                else:
                    D = D - 0.5
                    converged = False
            elif LD > 7.2:
                D = D + 0.5
                converged = False
            else:
                converged = True

        converged = False
        
        # Calculate the vessel weight and wall thickness
        VW, VWT = VesselWeightAndWallThickness(P, D, L)
        
        # Recalculate L/D
        D, LD = self.RecalculateLD(L, D)
        
        # Calculate NLL and HLL
        Hhll = D - Hv
        Anll = (Ahl + All) + Vh / L
        
        # Obtain Hnll using table 3 by knowing the Anll/At value
        # from Anll/At to Ahl/At set HNATable = 1
        X = Anll / At
        Y = HNATable(2, X)
        Hnll = Y * D
        
        # send the outputs
        self.SetValueFromFieldUnits(self._output['VesselLength'], L)
        self.SetValueFromFieldUnits(self._output['VesselDiameter'], D)
        self._output['LDratio'].SetValue(LD)
        self.SetValueFromFieldUnits(self._output['VapDisengagementHeight'], Hv)
        self.SetValueFromFieldUnits(self._output['NormalLiqLevel'], Hnll)
        self.SetValueFromFieldUnits(self._output['HighLiqLevel'], Hhll)
        self.SetValueFromFieldUnits(self._output['VesselWeight'], VW)
        self.SetValueFromFieldUnits(self._output['VesselWallThickness'], VWT)


class HorizontalWithBoot(Separator3Phase):

    def __init__(self):
        super(HorizontalWithBoot, self).__init__()
        self._output['BootDiameter'] = BasicDesignParameter(self, 'BootDiameter', OUTLET_INFO|FLT_INFO|USESUNIT_INFO, LENGTH_VAR, idx=40)
        self._output['BootHeight'] = BasicDesignParameter(self, 'BootHeight', OUTLET_INFO|FLT_INFO|USESUNIT_INFO, LENGTH_VAR, idx=42)
        
    def Solve(self):
        super(HorizontalWithBoot, self).Solve()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return
        
        results = self.Initialize()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return

        Wv, Wll, Whl, rhov, rhol, rhoh, mul, muh, P, Ts, Th, Mist, Ks, Qv, Qll, Qhl, K, Ut, Uv, Vh, Vs, LD, Till, Tihl = results
        
        Hllv = 1.0       #lightliquid level
        Hllb = 0.5       #heavyliquid level
        converged = False
        converged1 = False
        converged2 = False

        D = (4.0*(Vh+Vs)/(0.6*pi*LD))**(1.0/3.0)
        if (D <= 4.0):
            D = 4.0
        while not converged:
            At = pi*(D**2)/4.0
            Hv = 0.2*D
            if int(Mist) == 1:
                if Hv <= 2.0:
                    Hv = 2.0
            else:
                if Hv <= 1.0:
                    Hv = 1.0

            X1 = Hv/D
            X2 = Hllv/D
            Av = HNATable(1, X1)*At
            Allv = HNATable(1, X2)*At
            # Calculate minimum length
            L = (Vh + Vs)/(At-Av-Allv)
            # Calculate liquid dropout
            Phi = Hv/Uv
            # Calculate actual vapor velocity
            Uva = Qv/Av
            # Calculate L minimum for vapor-liquid separation
            Lmin = Uva*Phi
            Li = L

            sign = -1.0
            needToIter = False

            if L < Lmin:
                Li = Lmin

            if L < (0.8*Lmin):
                sign = 1.0
                needToIter = True
                
            if L > (1.2*Lmin):
                if int(Mist) == 1 and Hv <= 2.0:
                    Hv = 2.0
                    Li = L
                elif not int(Mist) == 0 and Hv <= 1.0:
                    Hv = 1.0
                    Li = L
                else:
                    needToIter = True

            if needToIter:
                innerIter = 0
                while not converged1 and innerIter < self.maxIter:
                    innerIter += 1
                    Hv = Hv + sign*0.5
                    if int(Mist) == 1 and Hv <= 2.0:   # baru tambah Bang !
                        Hv = 2.0
                    if int(Mist) == 0 and Hv <= 1.0:   # baru tambah Bang !
                        Hv = 1.0
                    Hllv = 1.0
                    Hllb = 0.5
                    X1 = Hv/D
                    X2 = Hllv/D
                    Y1 = HNATable(1, X1)
                    Av = Y1*At
                    Y2 = HNATable(1, X2)
                    Allv = Y2*At
                    Li = (Vh + Vs)/(At-Av-Allv)
                    Phi = Hv/Uv
                    Uva = Qv/Av
                    Lmin = Uva*Phi
                    if Li < (0.8*Lmin):
                        sign = 1.0
                        converged1 = False
                    elif Li > (1.2*Lmin):
                        sign = -1.0
                        converged1 = False
                    else:
                        Li = Li
                        converged1 = True
                if not converged1 and self.parent:
                    self.parent.InfoMessage('CouldNotConvergeInner', (self.GetPath(), self.maxIter))
            converged1 = False
            L = Li
            
            # Calculate the setting velocity of heavy liquid
            Uhl = Ks*(rhoh-rhol)/mul
            # Calculate the setting velocity of heavy liquid
            Ulh = Ks*(rhoh-rhol)/muh
            # Calculate the setling time of the heavy liq out of the light liq
            Thl = 12.0*(Hllb + D - Hv)/Uhl
            if (Thl <= 0.0):
                    Hv = Hv - 0.5
            # Calculate the residence time of the light liq
            innerIter = 0
            while not converged2 and innerIter < self.maxIter:
                innerIter += 1
                Till = (At-Av)*L/Qll            
                if Till < Thl:
                    L = Thl*Qll/(At - Av)
                    converged2 = False
                else:
                    converged2 = True
                    
            if not converged2 and self.parent:
                    self.parent.InfoMessage('CouldNotConvergeInner', (self.GetPath(), self.maxIter))
                    
            converged2 = False
            
            # Calculate L/D        
            LD = L/D

            # Check L/D
            if LD < (0.8*1.5):
                if (D < 4.0):
                    D = D
                    converged = True
                else:
                    D = D - 0.5
                    converged = False
            if LD > (1.2*6.0):
                D = D + 0.5
                converged = False
            else:
                converged = True

        converged = False
            
        # Calculate the vessel weight and wall thickness
        VW, VWT = VesselWeightAndWallThickness(P, D, L)
        
        # Recalculate L/D
        D, LD = self.RecalculateLD(L, D)
        
        # Calculate NLL and HLL
        Hhll = D - Hv
        Anll = Allv + (Vh / L)
        
        # Obtain Hnll using table 3 by knowing the Anll/At value
        # from Anll/At to Ahl/At set HNATable = 1
        X = Anll / At
        Y = HNATable(2, X)
        Hnll = Y * D

        # Design the heavy liquid boot
        Hhl = 1.0
        Up = 0.75*Ulh
        # Boot diameter
        Db = (4.0*12.0*Qhl/(pi*Up))**0.5
        while not converged:
            Tlh = 12.0*Hhl/Ulh
            Tihl = pi*Hhl*(Db**2.0)/(4.0*Qhl)
            if Tihl < Tlh:
                Db = Db + 0.5
                converged = False
            else:
                converged = True

        converged = False

        Hb = Hhl + Hllb

        # send the outputs
        self.SetValueFromFieldUnits(self._output['VesselLength'], L)
        self.SetValueFromFieldUnits(self._output['VesselDiameter'], D)
        self._output['LDratio'].SetValue(LD)
        self.SetValueFromFieldUnits(self._output['VapDisengagementHeight'], Hv)
        self.SetValueFromFieldUnits(self._output['NormalLiqLevel'], Hnll)
        self.SetValueFromFieldUnits(self._output['HighLiqLevel'], Hhll)
        self.SetValueFromFieldUnits(self._output['VesselWeight'], VW)
        self.SetValueFromFieldUnits(self._output['VesselWallThickness'], VWT)
        self.SetValueFromFieldUnits(self._output['BootDiameter'], Db)
        self.SetValueFromFieldUnits(self._output['BootHeight'], Hb)
        

class HorizontalWithWeir(Separator3Phase):

    def __init__(self):
        super(HorizontalWithWeir, self).__init__()
        self._output['WeirHeight'] = BasicDesignParameter(self, 'WeirHeight', OUTLET_INFO|FLT_INFO|USESUNIT_INFO, LENGTH_VAR, idx=50)
        self._output['LengthToWeir'] = BasicDesignParameter(self, 'LengthToWeir', OUTLET_INFO|FLT_INFO|USESUNIT_INFO, LENGTH_VAR, idx=52)

        
    def Solve(self):
        super(HorizontalWithWeir, self).Solve()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return
        
        results = self.Initialize()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return

        Wv, Wll, Whl, rhov, rhol, rhoh, mul, muh, P, Ts, Th, Mist, Ks, Qv, Qll, Qhl, K, Ut, Uv, Vh, Vs, LD, Till, Tihl = results
        
        converged = False
        converged1 = False
        converged2 = False
        
        D = (16.0*(Vh+Vs)/(0.6*pi*LD))**(1.0/3.0)
        if (D <= 4.0):
            D = 4.0
        while not converged:
            At = pi*(D**2)/4.0
            Hv = 0.2*D
            if int(Mist) == 1 and Hv <= 2.0:
                Hv = 2.0
            elif not int(Mist) == 0 and Hv <= 1.0:
                Hv = 1.0

            X1 = Hv/D
            Av = HNATable(1, X1)*At
            # Calculate low liq level
            Hlll = 0.5*D + 7.0
            X2 = round(Hlll)/(D*12.0)
            Alll = HNATable(1, X2)*At
            # Calculate weir height
            Hw = D - Hv
            # Check if Hw is less than 2 ft
            while not converged2:
                if Hw < 2.0:
                    D = D + 0.5 
                At = pi*(D**2)/4.0
                Hv = 0.2*D
                if int(Mist) == 1 and Hv <= 2.0:
                    Hv = 2.0
                elif not int(Mist) == 0 and Hv <= 1.0:
                    Hv = 1.0

                X1 = Hv/D
                Av = HNATable(1, X1)*At
                # Calculate low liq level
                Hlll = 0.5*D + 7.0
                X2 = (FinalValue(Hlll))/(D*12.0)
                Alll = HNATable(1, X2)*At
                # Calculate weir height
                Hw = D - Hv
                # Check if Hw is less than 2 ft
                if Hw < 2.0:
                    converged2 = False
                else:
                    converged2 = True
                    
            converged2 = False

            # Calculate minimum length of the light liquid compartment
            L2 = (Vh + Vs)/(At-Av-Alll)
            L2 = FinalValue(L2)
            Hhl = Hw/2.0
            Hll = Hhl
            X3 = Hhl/D
            Ahl = HNATable(1, X3)*At
            All = At - Av - Ahl
            # Calculate the setting velocity of heavy liquid and light liquid
            Uhl = Ks*(rhoh-rhol)/mul
            Ulh = Ks*(rhoh-rhol)/muh
            # Calculate the setling time of the heavy liq out of the light liq
            Thl = 12.0*Hll/Uhl
            Tlh = 12.0*Hhl/Ulh
            # Calculate L1 max
            L1a = Tlh*Qhl/Ahl
            L1b = Thl*Qll/All
            if L1a > L1b:
                L1 = L1a
            else:
                L1 = L1b
            L1 = FinalValue(L1)

            # Find L
            L = L1 + L2
            # Calculate liquid dropout
            Phi = Hv/Uv
            # Calculate actual vapor velocity
            Uva = Qv/Av
            # Calculate L minimum for vapor-liquid separation
            Lmin = Uva*Phi
            Li = L

            sign = -1.0
            needToIter = False

            if L < Lmin:
                Li = Lmin

            if L < (0.8*Lmin):
                sign = 1.0
                needToIter = True
                
            if L > (1.2*Lmin):
                if int(Mist) == 1 and Hv <= 2.0:
                    Hv = 2.0
                    L = Li
                elif not int(Mist) == 0 and Hv <= 1.0:
                    Hv = 1.0
                    L = Li
                else:
                    needToIter = True

            if needToIter:
                innerIter = 0
                while not converged1 and innerIter < self.maxIter:
                    innerIter += 1
                    Hv = Hv + sign*0.5
                    if int(Mist) == 1 and Hv <= 2.0:   # baru tambah Bang !
                        Hv = 2.0
                    if int(Mist) == 0 and Hv <= 1.0:   # baru tambah Bang !
                        Hv = 1.0
                    X1 = Hv/D
                    Av = HNATable(1, X1)*At
                    Hlll = 0.5*D + 7.0
                    Hlll = FinalValue(Hlll)
                    X2 = Hlll/(D*12.0)
                    Alll = HNATable(1, X2)*At
                    # Calculate weir height
                    Hw = D - Hv
                    # Check if Hw is less than 2 ft
                    if Hw < 2.0:
                        D = D + 0.5
                        while not converged2:
                            At = pi*(D**2)/4.0
                            Hv = 0.2*D
                            if int(Mist) == 1 and Hv <= 2.0:
                                Hv = 2.0
                            elif not int(Mist) == 0 and Hv <= 1.0:
                                Hv = 1.0

                            X1 = Hv/D
                            Av = HNATable(1, X1)*At
                            # Calculate low liq level
                            Hlll = 0.5*D + 7.0
                            X2 = FinalValue(Hlll)/(D*12.0)
                            Alll = HNATable(1, X2)*At
                            # Calculate weir height
                            Hw = D - Hv
                            # Check if Hw is less than 2 ft
                            if Hw < 2.0:
                                converged2 = False
                            else:
                                converged2 = True
                    
                    converged2 = False
                    L2 = (Vh + Vs)/(At-Av-Alll)
                    L2 = FinalValue(L2)
                    Hhl = Hw/2.0
                    Hll = Hhl
                    X3 = Hhl/D
                    Ahl = HNATable(1, X3)*At
                    All = At - Av - Ahl
                    # Calculate the setting velocity of heavy liquid and light liquid
                    Uhl = Ks*(rhoh-rhol)/mul
                    Ulh = Ks*(rhoh-rhol)/muh
                    # Calculate the setling time of the heavy liq out of the light liq
                    Thl = 12.0*Hll/Uhl
                    Tlh = 12.0*Hhl/Ulh
                    # Calculate L1 max
                    L1a = Tlh*Qhl/Ahl
                    L1b = Thl*Qll/All
                    if L1a > L1b:
                        L1 = L1a
                    else:
                        L1 = L1b
                    L1 = FinalValue(L1)

                    # Find L
                    Li = L1 + L2
                    # Calculate liquid dropout
                    Phi = Hv/Uv
                    # Calculate actual vapor velocity
                    Uva = Qv/Av
                    # Calculate L minimum for vapor-liquid separation
                    Lmin = Uva*Phi
                    if Li < (0.8*Lmin):
                        sign = 1.0
                        converged1 = False
                    if Li > (1.2*Lmin):
                        sign = -1.0
                        converged1 = False
                    else:
                        Li = Li
                        converged1 = True
                if not converged1 and self.parent:
                    self.parent.InfoMessage('CouldNotConvergeInner', (self.GetPath(), self.maxIter))
            converged1 = False
            L = Li
            
            # Calculate L/D        
            LD = L/D

            # Check L/D
            if LD < 1.2:
                if (D <= 4.0):
                    D = D
                    converged = True
                else:
                    D = D - 0.5
                    converged = False
            elif LD > 7.2:
                D = D + 0.5
                converged = False
            else:
                converged = True

        converged = False
        
        # Calculate the vessel weight and wall thickness
        VW, VWT = VesselWeightAndWallThickness(P, D, L)
        
        # Recalculate L/D
        D, LD = self.RecalculateLD(L, D)
        
        # Calculate NLL and HLL
        Hhll = D - Hv
        Anll = Alll + (Vh/L)
        
        # Obtain Hnll using table 3 by knowing the Anll/At value
        # from Anll/At to Ahl/At set HNATable = 1
        X = Anll / At
        Y = HNATable(2, X)
        Hnll = Y * D
        Hlll = Hlll/12.0
 
        
        # send the outputs
        self.SetValueFromFieldUnits(self._output['VesselLength'], L)
        self.SetValueFromFieldUnits(self._output['VesselDiameter'], D)
        self._output['LDratio'].SetValue(LD)
        self.SetValueFromFieldUnits(self._output['VapDisengagementHeight'], Hv)
        self.SetValueFromFieldUnits(self._output['NormalLiqLevel'], Hnll)
        self.SetValueFromFieldUnits(self._output['HighLiqLevel'], Hhll)
        self.SetValueFromFieldUnits(self._output['VesselWeight'], VW)
        self.SetValueFromFieldUnits(self._output['VesselWallThickness'], VWT)
        self.SetValueFromFieldUnits(self._output['WeirHeight'], Hw)
        self.SetValueFromFieldUnits(self._output['LengthToWeir'], L2)
           

class HorizontalWithWeirAndBucket(Separator3Phase):

    def __init__(self):
        super(HorizontalWithWeirAndBucket, self).__init__()
        genOutputType = OUTLET_INFO|FLT_INFO|USESUNIT_INFO
        self._output['LLiqWeirHeight'] = BasicDesignParameter(self, 'LLiqWeirHeight', genOutputType, LENGTH_VAR, idx=60)
        self._output['HLiqWeirHeight'] = BasicDesignParameter(self, 'HLiqWeirHeight', genOutputType, LENGTH_VAR, idx=62)
        self._output['LengthToLLiqWeir'] = BasicDesignParameter(self, 'LengthToLLiqWeir', genOutputType, LENGTH_VAR, idx=64)
        self._output['LengthBetweenWeirs'] = BasicDesignParameter(self, 'LengthBetweenWeirs', genOutputType, LENGTH_VAR, idx=66)
        self._output['LLiqBucketLength'] = BasicDesignParameter(self, 'LLiqBucketLength', genOutputType, LENGTH_VAR, idx=68)
        self._output['HLiqBucketLength'] = BasicDesignParameter(self, 'HLiqBucketLength', genOutputType, LENGTH_VAR, idx=70)
        
        
    def Solve(self):
        super(HorizontalWithWeirAndBucket, self).Solve()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return
        
        results = self.Initialize()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return

        Wv, Wll, Whl, rhov, rhol, rhoh, mul, muh, P, Ts, Th, Mist, Ks, Qv, Qll, Qhl, K, Ut, Uv, Vh, Vs, LD, Till, Tihl = results
  
        converged = False
        converged1 = False
        converged2 = False
        
        D = (4.0*(Qll*Till+Qhl*Tihl)/(0.7*pi*LD))**(1.0/3.0)

        while not converged:
            At = pi*(D**2)/4.0
            Hv = 0.2*D
            if int(Mist) == 1:
                if Hv <= 2.0:
                    Hv = 2.0
            else:
                if Hv <= 1.0:
                    Hv = 1.0

            X1 = Hv/D
            Av = HNATable(1, X1)*At
            # Calculate minimum length
            L1 = (Qll*Till + Qhl*Tihl)/(At-Av)
            # Calculate liquid dropout
            Phi = Hv/Uv
            # Calculate actual vapor velocity
            Uva = Qv/Av
            # Calculate L minimum for vapor-liquid separation
            Lmin = Uva*Phi
            Li = L1

            sign = -1.0
            needToIter = False

            if L1 < Lmin:
                Li = Lmin

            if L1 < (0.8*Lmin):
                sign = 1.0
                needToIter = True
                
            if L1 > (1.2*Lmin):
                if int(Mist) == 1 and Hv <= 2.0:
                    Hv = 2.0
                    L = Li
                elif not int(Mist) == 0 and Hv <= 1.0:
                    Hv = 1.0
                    L = Li
                else:
                    needToIter = True

            if needToIter:
                innerIter = 0
                while not converged1 and innerIter < self.maxIter:
                    innerIter += 1
                    Hv = Hv + sign*0.5
                    if int(Mist) == 1 and Hv <= 2.0:   # baru tambah Bang !
                        Hv = 2.0
                    if int(Mist) == 0 and Hv <= 1.0:   # baru tambah Bang !
                        Hv = 1.0
                    X1 = Hv/D
                    Av = HNATable(1, X1)*At
                    L1 = (Qll*Till + Qhl*Tihl)/(At-Av)
                    Phi = Hv/Uv
                    Uva = Qv/Av
                    Lmin = Uva*Phi
                    if L1 < (0.8*Lmin):
                        sign = 1.0
                        converged1 = False
                    if L1 > (1.2*Lmin):
                        sign = -1.0
                        converged1 = False
                    else:
                        Li = L1
                        converged1 = True
                if not converged1 and self.parent:
                    self.parent.InfoMessage('CouldNotConvergeInner', (self.GetPath(), self.maxIter))
            converged1 = False
            L1 = Li

            # Calculate the light liquid layer thickness based on heavy liq settling out
            DSG = rhoh/62.3 - rhol/62.3     # Delta S.G between light and heavy liqs.
            Hll = 0.00128*Till*DSG*(89.0*0.00000328084)**2*1488.0/mul
            #Calculate diff in height between light and heavy liq weirs
            DH = Hll*(1.0 - rhol/rhoh)

            # Design the light liquid bucket
            LLw = D - Hv
            HLLl = LLw - 0.5
            Hllb = 0.125*D
            LLLl = Hllb + 0.5
            Hllw = LLw - Hllb

            X1 = HLLl/D
            Ahll = HNATable(1, X1)*At
            X2 = LLLl/D
            Alll = HNATable(1, X2)*At
            
            # Calculate L2 and L3
            L2 = (Th + Ts)*Qll/(Ahll - Alll)
            L3a = D/12.0
            if L3a < 1.0:
                L3a = 1.0
            L3 = L3a

            # Design the heavy liq compartment
            HLw = D - Hv - DH
            HLLh = HLw - 0.5
            Hvlb = 0.0*D        # from bottom of vessel
            LLLh = 0.5
            Hhlw = HLw - Hvlb
            
            X1 = HLLh/D
            Ahvll = HNATable(1, X1)*At
            X2 = LLLh/D
            Alvll = HNATable(1, X2)*At
            
            # Calculate L4
            L4 = (Th + Ts)*Qhl/(Ahvll - Alvll)
            
            # Calculate L
            L = L1 + L2 + L3 + L4
            # Calculate LD
            LD = L/D
            # Check L/D
            if LD < 1.2:
                if (D < 4.0):
                    D = D
                    converged = True
                else:
                    D = D - 0.5
                    converged = False
            elif LD > 7.2:
                D = D + 0.5
                converged = False
            else:
                converged = True

        converged = False
        # Calculate the vessel weight and wall thickness
        VW, VWT = VesselWeightAndWallThickness(P, D, L)
        
        # Recalculate L/D
        D, LD = self.RecalculateLD(L, D)
        
        # send the outputs
        self.SetValueFromFieldUnits(self._output['VesselLength'], L)
        self.SetValueFromFieldUnits(self._output['VesselDiameter'], D)
        self._output['LDratio'].SetValue(LD)
        self.SetValueFromFieldUnits(self._output['VapDisengagementHeight'], Hv)
        #self._output['NormalLiqLevel'].SetValue('NIL')
        #self._output['HighLiqLevel'].SetValue('NIL')
        self.SetValueFromFieldUnits(self._output['VesselWeight'], VW)
        self.SetValueFromFieldUnits(self._output['VesselWallThickness'], VWT)
        self.SetValueFromFieldUnits(self._output['LLiqWeirHeight'], Hllw)
        self.SetValueFromFieldUnits(self._output['HLiqWeirHeight'], Hhlw)
        self.SetValueFromFieldUnits(self._output['LengthToLLiqWeir'], L1)
        self.SetValueFromFieldUnits(self._output['LLiqBucketLength'], L2)
        self.SetValueFromFieldUnits(self._output['LengthBetweenWeirs'], L3)
        self.SetValueFromFieldUnits(self._output['HLiqBucketLength'], L4)
        

