""" Design procedure for Two-Phase separators based on Wayne D. Monnery & William Y. Svrcek mathematical procedures.
    Simulation design procedure by Shahrul Zainal and Izzi Alias
    ref: Design Two-Phase Separators Within the Right Limits, Chemical Engineering Progress Oct,1993
"""

import Design, DesignTools, DesignSep3Phase
from Design import BasicDesignParameter
from Design import STR_INFO, INT_INFO, FLT_INFO, BOOL_INFO, OPT_INFO
from Design import PORT_INFO, INLET_INFO, OUTLET_INFO, USESUNIT_INFO
from DesignTools import HNATable, GTable, FinalValue, VesselWeightAndWallThickness, Kvalue


from sim.solver.Variables import *
from sim.unitop import Flash

import numpy.oldnumeric, math
from math import log, pi, ceil
PI = math.pi


VALID_DESIGN_OBJECTS = ['Vertical',
                        'Horizontal']                        

FIELD_UNIT_SET = 'Field'


class Separator2Phase(DesignSep3Phase.Separator3Phase):
    def __init__(self):
        super(Separator2Phase, self).__init__()

        #Define a generic typeInfo
        genOutputType = OUTLET_INFO|FLT_INFO|USESUNIT_INFO
        
        del self._input['HLiqMassFlow']
        del self._input['HLiqDensity']
        del self._input['HLiqViscosity']
        del self._input['ServiceType']
        self._output['LowLiqLevel'] = BasicDesignParameter(self, 'LowLiqLevel', genOutputType, LENGTH_VAR, idx=11)
       

    def LoadInputFromParent(self):
        """Get the input from the parent unit operation (if any)"""
        if not self.parent: return
        vapPort = self.parent.GetPort(V_PORT)
        liqPort = self.parent.GetPort(L_PORT + '0')

        if None in (vapPort, liqPort):
            self.parent.InfoMessage('WrongParentDesignObj', (self.GetPath(),))
            self._readyForSolve = False

        if not vapPort.AlreadyFlashed() or not liqPort.AlreadyFlashed():
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

        
        #Load info from the liq port
        port = liqPort
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
    

    def Initialize(self):
        Wv = self.GetValueInFieldUnits(self._input['VapMassFlow'])
        Wll = self.GetValueInFieldUnits(self._input['LLiqMassFlow'])
        rhov = self.GetValueInFieldUnits(self._input['VapDensity'])
        rhol = self.GetValueInFieldUnits(self._input['LLiqDensity'])
        mul = self.GetValueInFieldUnits(self._input['LLiqViscosity'])
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
        Ts = Ts/60.0
        
        Mist = self._input['Mist'].GetValue()
        mySepType = self._input['Liq-LiqSepType'].GetValue()
        if mySepType == 'HC-Water' or mySepType == 'HC-Caustic':
            Ks = 0.333
        else:
            Ks = 0.163

        # Calculate the volumetric flowrate
        Qv = Wv/(3600*rhov)
        Qll = Wll/(60*rhol)

        # Calculate Ut and set Uv
        K = Kvalue(P)
        
        Ut = K*((rhol - rhov)/ rhov)**0.5
        Uv = 0.75*Ut

        # Calculate Holdup and Surge volume
        Vh = Th*Qll
        Vs = Ts*Qll

        return Wv, Wll, rhov, rhol, P, Th, Ts, Mist, Ks, Qv, Qll, Ut, Uv, Vh, Vs


  
class Vertical(Separator2Phase):

    def __init__(self):
        super(Vertical, self).__init__()

    def Solve(self):
        super(Vertical, self).Solve()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return
        
        converged = False

        results = self.Initialize()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return
        
        Wv, Wll, rhov, rhol, P, Th, Ts, Mist, Ks, Qv, Qll, Ut, Uv, Vh, Vs = results

        # Calculate internal diameter, Dvd
        Dvd = (4.0*Qv/(pi*Uv))**0.5
        if int(Mist) == 1:
            D = FinalValue(Dvd + 0.4)
        else:
            D = FinalValue(Dvd)

        # Obtaining low liquid level height, Hlll
        Hlll = 0.5
        if P < 300:
            Hlll = 1.25
            
        # Calculate the height from Hlll to  Normal liq level, Hnll
        Hh = Vh/(pi/4.0*Dvd**2)
        if Hh < 1.0:
            Hh = 1.0
        Hh = FinalValue(Hh)
        
        # Calculate the height from Hnll to  High liq level, Hhll
        Hs = Vs/(pi/4.0*Dvd**2)
        if Hs < 0.5:
            Hs = 0.5
        Hs = FinalValue(Hs)
        
        # Calculate dN
        Qm = Qll + Qv
        lamda = Qll/Qm
        rhoM = rhol*lamda + rhov*(1-lamda)
        dN = (4*Qm/(pi*60.0/(rhoM**0.5)))**0.5
        dN = FinalValue(dN)

        # Calculate Hlin, assume with inlet diverter
        Hlin = 1.0 + dN

        # Calculate the vapor disengagement height
        Hv = 0.5*Dvd
        if int(Mist) == 1:
            Hv2 = 2.0 + dN/2.0
        else:
            Hv2 = 3.0 + dN/2.0
                    
        if Hv2 < Hv:
            Hv = Hv2
        Hv = ceil(Hv)

        # Calculate total height, Ht
        Hme = 0.0
        if int(Mist) == 1:
            Hme = 1.5
        Ht = Hlll + Hh + Hs + Hlin + Hv + Hme
        Ht = FinalValue(Ht)
        
        # Calculate Vessel weight and wall thickness
        VW, VWT = VesselWeightAndWallThickness(P, D, Ht)

        # Check if LD is between 1.5 and 6.0
        while not converged:
            LD = Ht/D
            if (LD < 1.5):
                D = D - 0.5
                converged = False
            elif (LD > 6.0):
                D = D + 0.5
                converged = False
            else:
                converged = True
                    
        converged = False

        LD = Ht/D
        
        # Find maximum and normal liquid level
        Hhll = Hs + Hh + Hlll
        Hnll = Hh + Hlll
        
        # send the outputs
        self.SetValueFromFieldUnits(self._output['VesselLength'], Ht)
        self.SetValueFromFieldUnits(self._output['VesselDiameter'], D)
        self._output['LDratio'].SetValue(LD)
        self.SetValueFromFieldUnits(self._output['VapDisengagementHeight'], Hv)
        self.SetValueFromFieldUnits(self._output['HighLiqLevel'], Hhll)
        self.SetValueFromFieldUnits(self._output['NormalLiqLevel'], Hnll)
        self.SetValueFromFieldUnits(self._output['LowLiqLevel'], Hlll)
        self.SetValueFromFieldUnits(self._output['VesselWeight'], VW)
        self.SetValueFromFieldUnits(self._output['VesselWallThickness'], VWT)
        
       
class Horizontal(Separator2Phase):

    def __init__(self):
        super(Horizontal, self).__init__()
        
    def Solve(self):
        super(Horizontal, self).Solve()
        
        converged = False
        converged1 = False
        
        results = self.Initialize()
        if not self._readyForSolve:
            if self.parent:
                self.parent.InfoMessage('DesignObjNotReady', (self.GetPath(),))
            return
        
        Wv, Wll, rhov, rhol, P, Th, Ts, Mist, Ks, Qv, Qll, Ut, Uv, Vh, Vs = results

        # Initialize LD
        if P > 14.7 and P <= 264.7:
            LD = 1.5/250.0*(P-14.7)+1.5
        elif P > 264.7 and P <= 514.7:
            LD = 1.0/250.0*(P-14.7)+2.0
        elif P > 514.7:
            LD = 5.0
           
        D = (4.0*(Vh+Vs)/(0.6*pi*LD))**(1.0/3.0)
        D = round(D)
        if D <= 4.0:
            D = 4.0

        outerIter = 0    
        while not converged and outerIter < self.maxIter:
            outerIter += 1
            At = pi*(D**2)/4.0

            # Calculate Low Liq. Area
            Hlll = round(0.5*D + 7.0)      # D is in ft but Hlll is in inches
            Hlll = Hlll/12.0
            X = Hlll/D
            Y = HNATable(1, X)
            Alll = Y*At

            # Calculate the Vap. disengagement area, Av
            Hv = 0.2*D
            if int(Mist) == 1 and Hv <= 2.0:
                Hv = 2.0
            else:
                if Hv <= 1.0:
                    Hv = 1.0
            X = Hv/D
            Y = HNATable(1, X)
            Av = Y*At
            
            # Calculate minimum length fo surge and holdup
            L = (Vh + Vs)/(At - Av - Alll)
            # Calculate liquid dropout
            Phi = Hv/Uv
            # Calculate actual vapor velocity
            Uva = Qv/Av
            # Calculate minimum length for vapor disengagement
            Lmin = Uva*Phi
            Li = L

            sign = -1.0
            needToIter = False
            
            if L < Lmin:
                Li = Lmin

            if L < 0.8*Lmin:
                sign = 1.0
                needToIter = True

            elif L > 1.2*Lmin:
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
                    X = Hv/D
                    Y = HNATable(1, X)
                    Av = Y*At

                    X = Hlll/D
                    Y = HNATable(1, X)
                    Alll = Y*At
                    
                    Li = (Vh + Vs)/(At - Av - Alll)
                    Phi = Hv/Uv
                    Uva = Qv/Av
                    Lmin = Uva*Phi
                    if Li < 0.8*Lmin:
                        sign = 1.0
                        converged1 = False
                    elif Li > 1.2*Lmin:
                        sign = -1.0
                        converged1 = False
                    else:
                        Li = Li
                        converged1 = True
                if not converged1 and self.parent:
                    self.parent.InfoMessage('CouldNotConvergeInner', (self.GetPath(), self.maxIter))
            converged1 = False
            L = Li
            LD = L/D
            # Check LD
            if LD < (0.8*1.5):
                if D <= 4.0:
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
            if not converged and self.parent:
                self.parent.InfoMessage('CouldNotConvergeOuter', (self.GetPath(), self.maxIter))

        converged = False
        # Calculate vessel weight and wall thickness
        VW, VWT = VesselWeightAndWallThickness(P, D, L)

        # to check minimum Hv value
        if int(Mist) == 1 and Hv <= 2.0:
            Hv = 2.0
        if int(Mist) == 0 and Hv <= 1.0:
            Hv = 1.0
        
        
        # Recalculate LD so it lies between 1.5 - 6.0
        
        while not converged:
            LD = L / D
            if (LD < 1.5) and D <= 4.0:
                L = L + 0.5
                
                converged = False
            elif LD < 1.5:
                D = D - 0.5
                converged = False
            elif (LD > 6.0):
                D = D + 0.5
                converged = False
            else:
                converged = True

        converged = False
        # Calculate normal liquid level and High liquid level
        Hhll = D - Hv
        if (Hhll < 0.0):
            Hhll = 0.0
        Anll = Alll + Vh/L
        X = Anll/At
        Y = HNATable(2, X)
        Hnll = Y*D

        # Send all outputs
        self.SetValueFromFieldUnits(self._output['VesselLength'], L)
        self.SetValueFromFieldUnits(self._output['VesselDiameter'], D)
        self._output['LDratio'].SetValue(LD)
        self.SetValueFromFieldUnits(self._output['VapDisengagementHeight'], Hv)
        self.SetValueFromFieldUnits(self._output['HighLiqLevel'], Hhll)
        self.SetValueFromFieldUnits(self._output['NormalLiqLevel'], Hnll)
        self.SetValueFromFieldUnits(self._output['LowLiqLevel'], Hlll)
        self.SetValueFromFieldUnits(self._output['VesselWeight'], VW)
        self.SetValueFromFieldUnits(self._output['VesselWallThickness'], VWT)

