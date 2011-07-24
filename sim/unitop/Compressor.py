"""Models for compression/expansion equipment

Classes:
IdealCompressorExpander -- an isentropic compressor expander base class
IdealCompressor - an isentropic compressor
IdealExpander - an isentropic expander
Compressor - compressor with adiabatic efficiency
Expander - expander with adiabatic efficiency

"""

#PRESSURE DROP CALCULATION CREATED BY NORFAIZAH ON 26TH FEBRUARY 2003


import UnitOperations
import Balance, Heater, Set, Sensor, Stream, Pump
from sim.solver import Flowsheet, Error
from sim.solver.Variables import *
import math

VALID_UNIT_OPERATIONS = ['Compressor',
                         'Expander',
                         'CompressorWithCurve',
                         'ExpanderWithCurve']

ISENTROPIC_PAR = 'Isentropic'
HEAD_SERIES = 'HeadCurve'
FLOW_SERIES = 'FlowCurve'
EFFICIENCY_SERIES = 'EfficiencyCurve'
POWER_SERIES = 'Power'

HEAD_PORT = 'Head'
POLYTROPIC_EFF_PORT = 'PolytropicEff'
ADIABATIC_EFF_PORT = 'AdiabaticEff'
EFFICIENCY_PORT = "Efficiency"   #Old name. NOT USED !!



COMPRESSORCURVE_OBJ = 'CompressorCurve'
EXPANDERCURVE_OBJ = 'ExpanderCurve'
SERIES_OBJ = 'Series'
TABLE_OBJ  = 'Table'
NUMBTABLE_PAR = 'NumberTables'
NUMBSERIES_PAR = 'NumberSeries'
TABLETAGTYPE_PAR = 'TableType'
SERIESTYPE_PAR = 'SeriesType'
EXTRAPOLATE_PAR = 'Extrapolate'
SPEC_TAG_PORT = 'SpecTagValue'
TABLETAG_VAR = 'TagValue'               # Basic Object of class ATable

COMPRESSORSPEED_PORT = 'CompressorSpeed'
EXPANDERSPEED_PORT = 'ExpanderSpeed'
IGNORECURVE_PAR = 'IgnoreCurve'
EFFCURVETYPE_PAR = 'EfficiencyCurveType'
ADIABATIC_TYPE = 'Adiabatic'
POLYTROPIC_TYPE = 'Polytropic'

# defines for EquationUnit
NUMBSIG_PAR = 'NumberSignal'
TRANSFORM_EQT_PAR = 'Equation'

class IdealCompressorExpander(UnitOperations.UnitOperation):
    """Isentropic compressor/expander"""
    def __init__(self, isCompressor=1, initScript = None):
        """
        Just do balance and conserve entropy
        isCompressor determines energy flow direction
        """          
        UnitOperations.UnitOperation.__init__(self, initScript)

        self.balance = Balance.Balance(Balance.MOLE_BALANCE | Balance.ENERGY_BALANCE)
        self.lastPIn = None
        self.lastPOut = None
        
        inPort = self.CreatePort(MAT|IN, IN_PORT)
        outPort = self.CreatePort(MAT|OUT, OUT_PORT)
        
        dpPort = self.CreatePort(SIG, DELTAP_PORT)
        dpPort.SetSignalType(DELTAP_VAR)
        
        self.isCompressor = isCompressor
        
        if isCompressor:
            qPort = self.CreatePort(ENE|IN, IN_PORT + 'Q')
            self.balance.AddInput((inPort, qPort))
            self.balance.AddOutput(outPort)
        else:
            qPort = self.CreatePort(ENE|OUT, OUT_PORT + 'Q')
            self.balance.AddInput(inPort)
            self.balance.AddOutput((outPort, qPort))

    def CleanUp(self):
        self.balance.CleanUp()
        self.balance = None
        super(IdealCompressorExpander, self).CleanUp()
        
    def Solve(self):
        """Solve"""
        
        ## if not self.ValidateOk(): return None
        self.FlashAllPorts()  # make sure anything that can be flashed has been

        inport = self.GetPort(IN_PORT)
        outport = self.GetPort(OUT_PORT)
        
        inport.SharePropWith(outport, S_VAR)
                            
        self.balance.DoBalance()
        while self.FlashAllPorts():
            self.balance.DoBalance()
        self.balance.DoBalance()

        #Check if a HS flash can still be done

        propsIn = inport.GetProperties()
        propsOut = outport.GetProperties()

        P, T = propsOut[P_VAR], propsOut[T_VAR]
        if P.GetValue() == None and T.GetValue() == None:
            H, S, PIn, TIn = propsOut[H_VAR], propsOut[S_VAR], propsIn[P_VAR], propsIn[T_VAR]
            if H.GetValue() != None and S.GetValue() != None and PIn.GetValue() != None:
                unitOp, frac = self, outport.GetCompositionValues()
                knownTargetProp = (S_VAR, S.GetValue(), S.GetType().scaleFactor)
                knownFlashProp = (H_VAR, H.GetValue(), H.GetType().scaleFactor)
                iterProp = (P_VAR, PIn.GetValue(), P.GetType().scaleFactor)
                if self.isCompressor:
                    min, max = PIn.GetValue(), 10.0*PIn.GetValue()
                else:
                    min, max = PIn.GetValue()/10.0, PIn.GetValue()
                converged = 0
                try:
                    val, converged = UnitOperations.CalculateNonSupportedFlash(unitOp, frac, knownTargetProp, knownFlashProp, iterProp, self.lastPOut, min, max)
                finally:
                    if converged:
                        self.lastPOut = val
                        P.SetValue(val, CALCULATED_V)
                        self.FlashAllPorts()
                    else:
                        self.lastPOut = None
                        self.InfoMessage('CouldNotSolveNonSuppFlash', (H_VAR, str(H.GetValue()), S_VAR, str(S.GetValue()), self.GetPath()))   

                        
        P, T = propsIn[P_VAR], propsIn[T_VAR]
        if P.GetValue() == None and T.GetValue() == None:
            H, S, POut, TOut = propsIn[H_VAR], propsIn[S_VAR], propsOut[P_VAR], propsOut[T_VAR]
            if H.GetValue() != None and S.GetValue() != None and POut.GetValue() != None:
                unitOp, frac = self, inport.GetCompositionValues()
                knownTargetProp = (S_VAR, S.GetValue(), S.GetType().scaleFactor)
                knownFlashProp = (H_VAR, H.GetValue(), H.GetType().scaleFactor)
                iterProp = (P_VAR, POut.GetValue(), P.GetType().scaleFactor)
                if self.isCompressor:
                    min, max = POut.GetValue()/10.0, POut.GetValue()
                else:
                    min, max = POut.GetValue(), 10.0*POut.GetValue()
                converged = 0
                try:
                    val, converged = UnitOperations.CalculateNonSupportedFlash(unitOp, frac, knownTargetProp, knownFlashProp, iterProp, self.lastPIn, min, max)
                finally:
                    if converged:
                        self.lastPIn = val
                        P.SetValue(val, CALCULATED_V)
                        self.FlashAllPorts()
                    else:
                        self.lastPIn = None
                        self.InfoMessage('CouldNotSolveNonSuppFlash', (H_VAR, str(H.GetValue()), S_VAR, str(S.GetValue()), self.GetPath()))  

        dpPort = self.GetPort(DELTAP_PORT)
        pIn = inport.GetPropValue(P_VAR)
        pOut = outport.GetPropValue(P_VAR)
        dp = dpPort.GetValue()

        sign = 1
        if not self.isCompressor: sign = -1

        if pOut == None:
                if dp != None and pIn != None:
                        outport.SetPropValue(P_VAR, pIn + sign*dp, CALCULATED_V)
        elif pIn == None:
                if dp != None:
                        inport.SetPropValue(P_VAR, pOut - sign*dp, CALCULATED_V)               
        else:
                dpPort.SetPropValue(DELTAP_VAR, sign*(pOut - pIn), CALCULATED_V)

        return 1

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(IdealCompressorExpander,self).AdjustOldCase(version)

        #Add the isCompressor member variable
        if version[0] < 9:
            p = self.GetPort(IN_PORT + 'Q')
            if p:
                self.isCompressor = 1
            else:
                self.isCompressor = 0

        #Add the DeltaP signal
        if version[0] < 11:
            #First make sure it is not there already
            dpPort = self.GetPort(DELTAP_PORT)
            if not dpPort:
                dpPort = self.CreatePort(SIG, DELTAP_PORT)
                dpPort.SetSignalType(DELTAP_VAR)
            
            inPort, outPort = self.GetPort(IN_PORT), self.GetPort(OUT_PORT)
            pIn, pOut = inPort.GetPropValue(P_VAR), outPort.GetPropValue(P_VAR)

            sign = 1
            if not self.isCompressor: sign = -1
            
            if pIn != None and pOut != None:
                dpPort.SetPropValue(DELTAP_VAR, sign*(pOut - pIn), CALCULATED_V)


    
    def _CloneCreate(self):
        """By default just clone with the __class__ call"""
        clone = self.__class__(self.isCompressor)
        return clone
                
    
class IdealCompressor(IdealCompressorExpander):
    def __init__(self, initScript=None):
        IdealCompressorExpander.__init__(self, 1, initScript)
                
class IdealExpander(IdealCompressorExpander):
    def __init__(self, initScript=None):
        IdealCompressorExpander.__init__(self, 0, initScript)
        
class Compressor(UnitOperations.UnitOperation):
    """
    Adiabatic Compressor made from ideal compressor, set and heater
    """
    
    def __init__(self, initScript=None):
        """Init compressor - build it from IdealCompressorExpander,
        Heater and Set operations
        """
        UnitOperations.UnitOperation.__init__(self, initScript)
        
        # the isentropic compressor
        self.ideal = IdealCompressorExpander(1)
        self.AddUnitOperation(self.ideal, 'Ideal')
        
        # a heater to add the waste heat to the outlet
        self.waste = Heater.Heater()
        self.AddUnitOperation(self.waste, 'Waste')
        self.waste.GetPort(DELTAP_PORT).SetValue(0.0, FIXED_V)
        
        # connect them
        self.ConnectPorts('Ideal', OUT_PORT, 'Waste', IN_PORT)

        # energy sensors (needed for signals)
        self.idealQ = Sensor.EnergySensor()
        self.AddUnitOperation(self.idealQ, 'IdealQ')
        self.ConnectPorts('Ideal', IN_PORT + 'Q', 'IdealQ', OUT_PORT)
        
        self.wasteQ = Sensor.EnergySensor()
        self.AddUnitOperation(self.wasteQ, 'WasteQ')
        self.ConnectPorts('Waste', IN_PORT + 'Q', 'WasteQ', OUT_PORT)

        self.totalQ = Sensor.EnergySensor()
        self.AddUnitOperation(self.totalQ, 'TotalQ')
        
        # create a signal stream for the efficiency
        self.effStream = Stream.Stream_Signal()
        self.effStream.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        self.AddUnitOperation(self.effStream, 'EfficiencySig')
        
        #set relation between ideal and total Q
        self.set = Set.Set()
        self.AddUnitOperation(self.set, 'Set')
        self.set.SetParameterValue(SIGTYPE_PAR, ENERGY_VAR)
        self.set.GetPort(Set.ADD_PORT).SetValue(0.0, FIXED_V)
        self.ConnectPorts('TotalQ',SIG_PORT, 'Set', SIG_PORT + '0')
        self.ConnectPorts('IdealQ',SIG_PORT, 'Set', SIG_PORT + '1')
        self.ConnectPorts('EfficiencySig', OUT_PORT, 'Set', Set.MULT_PORT)
        
        # energy stream balance
        self.mix = Balance.BalanceOp()
        self.AddUnitOperation(self.mix, 'Mix')
        self.mix.SetParameterValue(NUSTIN_PAR + Balance.S_ENE, 1)
        self.mix.SetParameterValue(NUSTOUT_PAR + Balance.S_ENE, 2)
        self.mix.SetParameterValue(Balance.BALANCETYPE_PAR, Balance.ENERGY_BALANCE)
        
        # connect the mixer ports
        self.ConnectPorts('IdealQ',IN_PORT,'Mix',OUT_PORT + 'Q0')
        self.ConnectPorts('WasteQ',IN_PORT,'Mix',OUT_PORT + 'Q1')
        self.ConnectPorts('TotalQ',OUT_PORT,'Mix', IN_PORT + 'Q0')
        
        # export the flow ports
        self.BorrowChildPort(self.ideal.GetPort(IN_PORT), IN_PORT)
        self.BorrowChildPort(self.waste.GetPort(OUT_PORT), OUT_PORT)
        self.BorrowChildPort(self.totalQ.GetPort(IN_PORT), IN_PORT + 'Q')
        self.BorrowChildPort(self.effStream.GetPort(IN_PORT), ADIABATIC_EFF_PORT)
        self.BorrowChildPort(self.ideal.GetPort(DELTAP_PORT), DELTAP_PORT)
        
        #Change the type of the energy port such that it is in Work units and scaling
        self.totalQ.GetPort(IN_PORT).GetProperty().SetTypeByName(WORK_VAR)
        
        #Polytropic efficiency
        self.polEffPort = self.CreatePort(SIG, POLYTROPIC_EFF_PORT)
        self.polEffPort.SetSignalType(GENERIC_VAR)
        
        self.nuSolids = 0
        
    def Solve(self):
        super(Compressor, self).Solve()
        
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)
        sPort = self.ideal.GetPort(OUT_PORT)
        mf = inPort.GetPropValue(MOLEFLOW_VAR)
        
        
        self._thCaseObj = self.GetThermo()
        
        if not self._thCaseObj:
            return
        
        self.nuSolids = self.NumberSolidPhases()
        
        inFlashed = inPort.AlreadyFlashed()
        outFlashed = outPort.AlreadyFlashed()
        sFlashed = sPort.AlreadyFlashed()        
        
        if mf == None:
            if inFlashed and sFlashed:
                self.SolveForMoleFlow(inPort, outPort, sPort)
        mf = inPort.GetPropValue(MOLEFLOW_VAR)
                    
        if not inFlashed and outFlashed and mf != None:
            self.SolveForInlet(inPort, outPort, sPort)
            
                
        #Solve for polytropic eff if in and out are known
        if inFlashed and outFlashed:
            self.SolveForPolytropicEff(inPort, outPort, sPort)
            return
            
        #Solve for isentropic efficiency if isentropic port is known
        if sFlashed and inFlashed and not outFlashed:
            #Solve for efficiency
            self.SolveForIsentropicEff(inPort, outPort, sPort)
            
            
    def SolveForInlet(self, inPort, outPort, sPort):
        
        h1 = outPort.GetPropValue(H_VAR)
        p1 = outPort.GetPropValue(P_VAR)
        
        p0 = inPort.GetPropValue(P_VAR)
        mf = inPort.GetPropValue(MOLEFLOW_VAR)
        fracs = inPort.GetCompositionValues()
        
        #Which efficiency is known?
        isEff = self.GetPort(ADIABATIC_EFF_PORT).GetValue()
        usesPolytropic = 0
        if isEff == None:
            polEff = self.polEffPort.GetValue()
            if not polEff:
                return
            else:
                usesPolytropic = 1
                ps = p1
        
        if None in (h1, p1, p0, mf) or (fracs == None) or (None in fracs):
            return
        
        #Initialize h0
        h0 = h1
        maxIter = 30
        iter = 0
        converged = 0
        tolerance = 1.0E-6
        scale = 1000.0
        shift = 1.0
        maxStep = 5000.0
        while not converged and iter < maxIter:
            iter += 1
            
            s0, v0 = self.GetPropertiesPH(p0, h0, fracs, (S_VAR, molarV_VAR))
            hs, vs = self.GetPropertiesPS(p1, s0, fracs, (H_VAR, molarV_VAR))
            
            if usesPolytropic:
                isEff, status = self.FromPolyToIsenEff(polEff, p0, h0, v0, ps, vs, hs, fracs)
                if isEff == None:
                    self.InfoMessage('CouldNotConverge', self.GetPath(), status[0])
                    return
            
            err = (hs - h0) - (h1 - h0)*isEff 
            err /= scale
            
            #Leave if converged
            if abs(err) <= tolerance:
                converged = 1
                break
            
            #Calculate crude derivative
            h0Temp = h0 + shift
            s0, v0 = self.GetPropertiesPH(p0, h0Temp, fracs, (S_VAR, molarV_VAR))
            hs, vs = self.GetPropertiesPS(p1, s0, fracs, (H_VAR, molarV_VAR))
            
            if usesPolytropic:
                isEff, status = self.FromPolyToIsenEff(polEff, p0, h0, v0, ps, vs, hs, fracs)
                if isEff == None:
                    self.InfoMessage('CouldNotConverge', self.GetPath(), status[0])
                    return
            
            errTemp = (hs - h0Temp) - (h1 - h0Temp)*isEff
            errTemp /= scale
            dErr_dEff = (errTemp - err) / shift
            step = - err/dErr_dEff
            step = max(step, -maxStep)
            step = min(step, maxStep)
            h0 += step
            
        if converged:
            inPort.SetPropValue(H_VAR, h0, CALCULATED_V|PARENT_V)
        else:
            self.InfoMessage('CouldNotConverge', self.GetPath(), iter)
            
            
    def SolveForMoleFlow(self, inPort, outPort, sPort):
        """solve for mole flow"""
          
        h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
        hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
        
        if h0 == None or hs == None:
            return
        
        isEff = self.GetPort(ADIABATIC_EFF_PORT).GetValue()
        if not isEff:
            polEff = self.polEffPort.GetValue()
            if not polEff:
                return
            #See if we can get isentropic eff from the polytropic one
            mf = None
            p0 = inPort.GetPropValue(P_VAR)                 #kPa
            h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
            v0 = inPort.GetPropValue(molarV_VAR)            #m3/kmol
            fracs = inPort.GetCompositionValues()
            
            ps = p1 = sPort.GetPropValue(P_VAR)             #m3/kmol
            vs = sPort.GetPropValue(molarV_VAR)             #m3/kmol
            hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
            
            if (None in (p0, h0, v0, ps, vs, hs)) or (fracs == None) or (None in fracs):
                return
            
            isEff, status = self.FromPolyToIsenEff(polEff, p0, h0, v0, ps, vs, hs, fracs)
            if isEff == None:
                self.InfoMessage('CouldNotConverge', self.GetPath(), status[0])
                return
            else:
                self.GetPort(ADIABATIC_EFF_PORT).SetValue(isEff, CALCULATED_V|PARENT_V)
            
        if not isEff:
            return
        
        #Calculate mole flow
        h1 = (hs - h0) / isEff + h0
        outPort.SetPropValue(H_VAR, h1, CALCULATED_V|PARENT_V)
        
        #Solve for mole flow if possible
        q = self.GetPort(IN_PORT + 'Q').GetValue()     #J/s
        if q == None: return
        mf = q*3.6 / (h1 - h0)                          #kmol/h
        inPort.SetPropValue(MOLEFLOW_VAR, mf, CALCULATED_V|PARENT_V)
        

    def SolveForPolytropicEff(self, inPort, outPort, sPort):
        """Solve for hte polytropic efficiency for a given in, out and isentropic port"""
        
        isEff = self.GetPort(ADIABATIC_EFF_PORT).GetValue()
        if not isEff:
            return 
                    
        mf = inPort.GetPropValue(MOLEFLOW_VAR)          #kmol/h
        p0 = inPort.GetPropValue(P_VAR)                 #kPa
        h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
        v0 = inPort.GetPropValue(molarV_VAR)            #m3/kmol
        
        p1 = outPort.GetPropValue(P_VAR)                #kPa
        h1 = outPort.GetPropValue(H_VAR)                #kJ/kmol
        v1 = outPort.GetPropValue(molarV_VAR)           #m3/kmol
        
        vs = sPort.GetPropValue(molarV_VAR)             #m3/kmol
        hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
        
        
        if None in (mf, p0, h0, v0, p1, h1, v1, vs, hs):
            return
        
        try:
            polEff = self.CalcPolytropicEff(p0, h0, v0, p1, h1, v1, vs, hs)
            self.polEffPort.SetValue(polEff, CALCULATED_V)
        except:
            pass        
        
    def SolveForIsentropicEff(self, inPort, outPort, sPort):
        polEff = self.polEffPort.GetValue()
        if not polEff:
            return
        
        mf = inPort.GetPropValue(MOLEFLOW_VAR)          #kmol/h
        p0 = inPort.GetPropValue(P_VAR)                 #kPa
        h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
        v0 = inPort.GetPropValue(molarV_VAR)            #m3/kmol
        fracs = inPort.GetCompositionValues()
        
        ps = p1 = sPort.GetPropValue(P_VAR)             #m3/kmol
        vs = sPort.GetPropValue(molarV_VAR)             #m3/kmol
        hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
        
        if (None in (mf, p0, h0, v0, ps, vs, hs)) or (fracs == None) or (None in fracs):
            return

        isEff, status = self.FromPolyToIsenEff(polEff, p0, h0, v0, ps, vs, hs, fracs)
        if isEff == None:
            self.InfoMessage('CouldNotConverge', self.GetPath(), status[0])
        else:
            self.GetPort(ADIABATIC_EFF_PORT).SetValue(isEff, CALCULATED_V|PARENT_V)
            
            
            
    def FromPolyToIsenEff(self, *args):
        """Calcaulte for isentropic efficiency based on the polytropic efficiency and other properties"""
        
        polEff, p0, h0, v0, ps, vs, hs, fracs = args
        p1 = ps
        #Iterate on isentropic efficiency until polytropic is matched
        isEff = polEff
        dhs = hs - h0
        maxIter = 30
        iter = 0
        converged = 0
        tolerance = 1.0E-6
        shift = 0.0001
        while not converged and iter < maxIter:
            iter += 1
            
            h1 = dhs/isEff + h0
            v1 = self.GetPropertiesPH(ps, h1, fracs, (molarV_VAR, ))[0]
            iterPolEff = self.CalcPolytropicEff(p0, h0, v0, p1, h1, v1, vs, hs)
            err = iterPolEff - polEff
            
            #Leave if converged
            if abs(err) <= tolerance:
                converged = 1
                break
            
            #Calculate crude derivative
            h1 = dhs/(isEff + shift) + h0
            v1 = self.GetPropertiesPH(ps, h1, fracs, (molarV_VAR, ))[0]
            iterPolEff = self.CalcPolytropicEff(p0, h0, v0, p1, h1, v1, vs, hs)
            errTemp = iterPolEff - polEff
            dErr_dEff = (errTemp - err) / shift
            isEff = isEff - err/dErr_dEff
            
        status = (iter, )
        if not converged:
            return None, status
        else:
            return isEff, status
            
        
    def CalcPolytropicEff(self, *args):
        p0, h0, v0, p1, h1, v1, vs, hs = args
        n = math.log(p1/p0) / math.log(v0/v1)
        ns = math.log(p1/p0) / math.log(v0/vs)
        f = (hs - h0) / ( (ns/(ns-1.0)) * (p1*vs - p0*v0))
        wp = f * (n/(n-1.0)) * (p1*v1 - p0*v0)
        return wp / (h1 - h0)
    
        
    def GetPropertiesPH(self, p, h, fracs, props, phase=OVERALL_PHASE):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        if not self.nuSolids:
            inProp1 = [P_VAR, p]
            inProp2 = [H_VAR, h]
            vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, props)
        else:
            matDict = MaterialPropertyDict()
            matDict[P_VAR].SetValue(p, FIXED_V)
            matDict[H_VAR].SetValue(h, FIXED_V)
            cmps = CompoundList(None)
            for i in range(len(fracs)):
                cmps.append(BasicProperty(FRAC_VAR))
            cmps.SetValues(fracs, FIXED_V)
            liqPhases = 1
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, props, nuSolids=self.nuSolids)
            vals = results.bulkProps
        return vals
        
    def GetPropertiesPS(self, p, s, fracs, props, phase=OVERALL_PHASE):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        if not self.nuSolids:
            inProp1 = [P_VAR, p]
            inProp2 = [S_VAR, s]
            vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, props)
        else:
            matDict = MaterialPropertyDict()
            matDict[P_VAR].SetValue(p, FIXED_V)
            matDict[S_VAR].SetValue(s, FIXED_V)
            cmps = CompoundList(None)
            for i in range(len(fracs)):
                cmps.append(BasicProperty(FRAC_VAR))
            cmps.SetValues(fracs, FIXED_V)
            liqPhases = 1
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, props, nuSolids=self.nuSolids)
            vals = results.bulkProps   
        return vals
    
    def CleanUp(self):
        self.ideal = self.waste = self.idealQ = None
        self.wasteQ = self.totalQ = self.effStream = None
        self.set = self.mix = None
        super(Compressor, self).CleanUp()
        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(Compressor, self).AdjustOldCase(version)


        #Borrow DeltaP signal
        if version[0] < 11:
            #First make sure it is there
            dpPort = self.ideal.GetPort(DELTAP_PORT)
            if not dpPort:
                dpPort = self.ideal.CreatePort(SIG, DELTAP_PORT)
                dpPort.SetSignalType(DELTAP_VAR)
                
            self.BorrowChildPort(self.ideal.GetPort(DELTAP_PORT), DELTAP_PORT)
            
            
        if version[0] < 61:
            prop = self.totalQ.GetPort(IN_PORT).GetProperty()
            if prop.GetType().name == ENERGY_VAR:
                prop.SetTypeByName(WORK_VAR)
                
        if version[0] < 63:
            p = self.GetPort(POLYTROPIC_EFF_PORT)
            if p == None:
                #Polytropic efficiency
                self.polEffPort = self.CreatePort(SIG, POLYTROPIC_EFF_PORT)
                self.polEffPort.SetSignalType(GENERIC_VAR)
            
        if version[0] < 66:
            p = self.GetPort(ADIABATIC_EFF_PORT)
            if p == None:
                p = self.GetPort(EFFICIENCY_PORT)
                if p != None:
                    self.RenamePort(EFFICIENCY_PORT, ADIABATIC_EFF_PORT)
            
    def GetObject(self, name):
        #Backward compatibility
        if name == EFFICIENCY_PORT:
            name = ADIABATIC_EFF_PORT
        return super(Compressor, self).GetObject(name)
            
class Expander(UnitOperations.UnitOperation):
    """
    Adiabatic Expander made from ideal compressor, set and heater
    """
    
    def __init__(self, initScript=None):
        """Init expander - build it from IdealCompressorExpander,
        Heater and Set operations
        """
        UnitOperations.UnitOperation.__init__(self, initScript)
        
        # the isentropic expander
        self.ideal = IdealCompressorExpander(0)
        self.AddUnitOperation(self.ideal, 'Ideal')
        
        # a heater to add the waste heat to the outlet
        self.waste = Heater.Heater()
        self.AddUnitOperation(self.waste, 'Waste')
        self.waste.GetPort(DELTAP_PORT).SetValue(0.0, FIXED_V)
        
        # connect them
        self.ConnectPorts('Ideal', OUT_PORT, 'Waste', IN_PORT)

        # energy sensors (needed for signals)
        self.idealQ = Sensor.EnergySensor()
        self.AddUnitOperation(self.idealQ, 'IdealQ')
        self.ConnectPorts('Ideal', OUT_PORT + 'Q', 'IdealQ', IN_PORT)
        
        self.wasteQ = Sensor.EnergySensor()
        self.AddUnitOperation(self.wasteQ, 'WasteQ')
        self.ConnectPorts('Waste', IN_PORT + 'Q', 'WasteQ', OUT_PORT)

        self.totalQ = Sensor.EnergySensor()
        self.AddUnitOperation(self.totalQ, 'TotalQ')
        
        # create a signal stream for the efficiency
        self.effStream = Stream.Stream_Signal()
        self.effStream.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        self.AddUnitOperation(self.effStream, 'EfficiencySig')
        
        #set relation between ideal and total Q
        self.set = Set.Set()
        self.AddUnitOperation(self.set, 'Set')
        self.set.SetParameterValue(SIGTYPE_PAR, ENERGY_VAR)
        self.set.GetPort(Set.ADD_PORT).SetValue(0.0, FIXED_V)
        self.ConnectPorts('TotalQ',SIG_PORT, 'Set', SIG_PORT + '1')
        self.ConnectPorts('IdealQ',SIG_PORT, 'Set', SIG_PORT + '0')
        self.ConnectPorts('EfficiencySig', OUT_PORT, 'Set', Set.MULT_PORT)
        
        # energy stream balance
        self.mix = Balance.BalanceOp()
        self.AddUnitOperation(self.mix, 'Mix')
        self.mix.SetParameterValue(NUSTIN_PAR + Balance.S_ENE, 1)
        self.mix.SetParameterValue(NUSTOUT_PAR + Balance.S_ENE, 2)
        self.mix.SetParameterValue(Balance.BALANCETYPE_PAR, Balance.ENERGY_BALANCE)
        
        # connect the mixer ports
        self.ConnectPorts('IdealQ',OUT_PORT,'Mix',IN_PORT + 'Q0')
        self.ConnectPorts('WasteQ',IN_PORT,'Mix',OUT_PORT + 'Q1')
        self.ConnectPorts('TotalQ',IN_PORT,'Mix', OUT_PORT + 'Q0')
        
        # export the flow ports
        
        self.BorrowChildPort(self.ideal.GetPort(IN_PORT), IN_PORT)
        self.BorrowChildPort(self.waste.GetPort(OUT_PORT), OUT_PORT)
        self.BorrowChildPort(self.totalQ.GetPort(OUT_PORT), OUT_PORT + 'Q')
        self.BorrowChildPort(self.effStream.GetPort(IN_PORT), ADIABATIC_EFF_PORT)        
        self.BorrowChildPort(self.ideal.GetPort(DELTAP_PORT), DELTAP_PORT)
        
        
        #Change the type of the energy port such that it is in Work units and scaling
        self.totalQ.GetPort(OUT_PORT).GetProperty().SetTypeByName(WORK_VAR)
        
        #Polytropic efficiency
        self.polEffPort = self.CreatePort(SIG, POLYTROPIC_EFF_PORT)
        self.polEffPort.SetSignalType(GENERIC_VAR)
        
        self.nuSolids = 0
        
    def Solve(self):
        super(Expander, self).Solve()
        
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)
        sPort = self.ideal.GetPort(OUT_PORT)
        mf = inPort.GetPropValue(MOLEFLOW_VAR)
                
        self._thCaseObj = self.GetThermo()
        
        if not self._thCaseObj:
            return
        
        self.nuSolids = self.NumberSolidPhases()
        
        inFlashed = inPort.AlreadyFlashed()
        outFlashed = outPort.AlreadyFlashed()
        sFlashed = sPort.AlreadyFlashed()        
        
        if mf == None:
            if inFlashed and sFlashed:
                self.SolveForMoleFlow(inPort, outPort, sPort)
        mf = inPort.GetPropValue(MOLEFLOW_VAR)
                    
        if not inFlashed and outFlashed and mf != None:
            self.SolveForInlet(inPort, outPort, sPort)
            
                
        #Solve for polytropic eff if in and out are known
        if inFlashed and outFlashed:
            self.SolveForPolytropicEff(inPort, outPort, sPort)
            return
            
        #Solve for isentropic efficiency if isentropic port is known
        if sFlashed and inFlashed and not outFlashed:
            #Solve for efficiency
            self.SolveForIsentropicEff(inPort, outPort, sPort)
            
            
    def SolveForInlet(self, inPort, outPort, sPort):
        
        h1 = outPort.GetPropValue(H_VAR)
        p1 = outPort.GetPropValue(P_VAR)
        
        p0 = inPort.GetPropValue(P_VAR)
        mf = inPort.GetPropValue(MOLEFLOW_VAR)
        fracs = inPort.GetCompositionValues()
        
        #Which efficiency is known?
        isEff = self.GetPort(ADIABATIC_EFF_PORT).GetValue()
        usesPolytropic = 0
        if isEff == None:
            polEff = self.polEffPort.GetValue()
            if not polEff:
                return
            else:
                usesPolytropic = 1
                ps = p1
        
        if None in (h1, p1, p0, mf) or (fracs == None) or (None in fracs):
            return
        
        #Initialize h0
        h0 = h1
        maxIter = 30
        iter = 0
        converged = 0
        scale = 1000.0
        tolerance = 1.0E-6
        shift = 1.0
        maxStep = 5000.0
        while not converged and iter < maxIter:
            iter += 1
            
            s0, v0 = self.GetPropertiesPH(p0, h0, fracs, (S_VAR, molarV_VAR))
            hs, vs = self.GetPropertiesPS(p1, s0, fracs, (H_VAR, molarV_VAR))
            
            if usesPolytropic:
                isEff, status = self.FromPolyToIsenEff(polEff, p0, h0, v0, ps, vs, hs, fracs)
                if isEff == None:
                    self.InfoMessage('CouldNotConverge', self.GetPath(), status[0])
                    return
            
            err = (hs - h0) - (h1 - h0)/isEff
            err /= scale
            
            #Leave if converged
            if abs(err) <= tolerance:
                converged = 1
                break
            
            #Calculate crude derivative
            h0Temp = h0 + shift
            s0, v0 = self.GetPropertiesPH(p0, h0Temp, fracs, (S_VAR, molarV_VAR))
            hs, vs = self.GetPropertiesPS(p1, s0, fracs, (H_VAR, molarV_VAR))
            
            if usesPolytropic:
                isEff, status = self.FromPolyToIsenEff(polEff, p0, h0, v0, ps, vs, hs, fracs)
                if isEff == None:
                    self.InfoMessage('CouldNotConverge', self.GetPath(), status[0])
                    return
            
            errTemp = (hs - h0Temp) - (h1 - h0Temp)/isEff
            errTemp /= scale
            dErr_dEff = (errTemp - err) / shift
            step = - err/dErr_dEff
            step = max(step, -maxStep)
            step = min(step, maxStep)
            h0 += step
            
        if converged:
            inPort.SetPropValue(H_VAR, h0, CALCULATED_V|PARENT_V)
        else:
            self.InfoMessage('CouldNotConverge', self.GetPath(), iter)
            
            
    def SolveForMoleFlow(self, inPort, outPort, sPort):
        """solve for mole flow"""
            
        h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
        hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
        
        if h0 == None or hs == None:
            return
        
        isEff = self.GetPort(ADIABATIC_EFF_PORT).GetValue()
        if not isEff:
            polEff = self.polEffPort.GetValue()
            if not polEff:
                return
            #See if we can get isentropic eff from the polytropic one
            mf = None
            p0 = inPort.GetPropValue(P_VAR)                 #kPa
            h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
            v0 = inPort.GetPropValue(molarV_VAR)            #m3/kmol
            fracs = inPort.GetCompositionValues()
            
            ps = p1 = sPort.GetPropValue(P_VAR)             #m3/kmol
            vs = sPort.GetPropValue(molarV_VAR)             #m3/kmol
            hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
            
            if (None in (p0, h0, v0, ps, vs, hs)) or (fracs == None) or (None in fracs):
                return
            
            isEff, status = self.FromPolyToIsenEff(polEff, p0, h0, v0, ps, vs, hs, fracs)
            if isEff == None:
                self.InfoMessage('CouldNotConverge', self.GetPath(), status[0])
                return
            else:
                self.GetPort(ADIABATIC_EFF_PORT).SetValue(isEff, CALCULATED_V|PARENT_V)
            
        if not isEff:
            return
        
        #Calculate h1
        h1 = (hs - h0) * isEff + h0
        outPort.SetPropValue(H_VAR, h1, CALCULATED_V|PARENT_V)
        
        
        #Solve for mole flow if possible
        q = self.GetPort(OUT_PORT + 'Q').GetValue()     #J/s
        if q == None: return
        mf = q*3.6 / (h1 - h0)                          #kmol/h
        inPort.SetPropValue(MOLEFLOW_VAR, mf, CALCULATED_V|PARENT_V)
        
        
    def SolveForPolytropicEff(self, inPort, outPort, sPort):
        """Solve for he polytropic efficiency for a given in, out and isentropic port"""
        
        isEff = self.GetPort(ADIABATIC_EFF_PORT).GetValue()
        if not isEff:
            return 
                    
        mf = inPort.GetPropValue(MOLEFLOW_VAR)          #kmol/h
        p0 = inPort.GetPropValue(P_VAR)                 #kPa
        h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
        v0 = inPort.GetPropValue(molarV_VAR)            #m3/kmol
        
        p1 = outPort.GetPropValue(P_VAR)                #kPa
        h1 = outPort.GetPropValue(H_VAR)                #kJ/kmol
        v1 = outPort.GetPropValue(molarV_VAR)           #m3/kmol
        
        vs = sPort.GetPropValue(molarV_VAR)             #m3/kmol
        hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
        
        
        if None in (mf, p0, h0, v0, p1, h1, v1, vs, hs):
            return
        
        try:
            polEff = self.CalcPolytropicEff(p0, h0, v0, p1, h1, v1, vs, hs)
            self.polEffPort.SetValue(polEff, CALCULATED_V)
        except:
            pass
        
    def SolveForIsentropicEff(self, inPort, outPort, sPort):
        polEff = self.polEffPort.GetValue()
        if not polEff:
            return
        
        mf = inPort.GetPropValue(MOLEFLOW_VAR)          #kmol/h
        p0 = inPort.GetPropValue(P_VAR)                 #kPa
        h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
        v0 = inPort.GetPropValue(molarV_VAR)            #m3/kmol
        fracs = inPort.GetCompositionValues()
        
        ps = p1 = sPort.GetPropValue(P_VAR)             #m3/kmol
        vs = sPort.GetPropValue(molarV_VAR)             #m3/kmol
        hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
        
        if (None in (mf, p0, h0, v0, ps, vs, hs)) or (fracs == None) or (None in fracs):
            return
        
        isEff, status = self.FromPolyToIsenEff(polEff, p0, h0, v0, ps, vs, hs, fracs)
        if isEff == None:
            self.InfoMessage('CouldNotConverge', self.GetPath(), status[0])
        else:
            self.GetPort(ADIABATIC_EFF_PORT).SetValue(isEff, CALCULATED_V|PARENT_V)
            
    def FromPolyToIsenEff(self, *args):
        """Calcaulte for isentropic efficiency based on the polytropic efficiency and other properties"""
        
        polEff, p0, h0, v0, ps, vs, hs, fracs = args
        p1 = ps
        
        #Iterate on isentropic efficiency until polytropic is matched
        isEff = polEff
        dhs = hs - h0
        maxIter = 30
        iter = 0
        converged = 0
        tolerance = 1.0E-6
        shift = 0.0001
        while not converged and iter < maxIter:
            iter += 1
            
            h1 = dhs*isEff + h0
            v1 = self.GetPropertiesPH(ps, h1, fracs, (molarV_VAR, ))[0]
            iterPolEff = self.CalcPolytropicEff(p0, h0, v0, p1, h1, v1, vs, hs)
            err = iterPolEff - polEff
            
            #Leave if converged
            if abs(err) <= tolerance:
                converged = 1
                break
            
            #Calculate crude derivative
            h1 = dhs*(isEff + shift) + h0
            v1 = self.GetPropertiesPH(ps, h1, fracs, (molarV_VAR, ))[0]
            iterPolEff = self.CalcPolytropicEff(p0, h0, v0, p1, h1, v1, vs, hs)
            errTemp = iterPolEff - polEff
            dErr_dEff = (errTemp - err) / shift
            isEff = isEff - err/dErr_dEff
            
        status = (iter, )
        if not converged:
            return None, status
        else:
            return isEff, status
            
    def CalcPolytropicEff(self, *args):
        p0, h0, v0, p1, h1, v1, vs, hs = args
        n = math.log(p1/p0) / math.log(v0/v1)
        ns = math.log(p1/p0) / math.log(v0/vs)
        f = (hs - h0) / ( (ns/(ns-1.0)) * (p1*vs - p0*v0))
        wp = f * (n/(n-1.0)) * (p1*v1 - p0*v0)
        return (h1 - h0) / wp
        
    def GetPropertiesPH(self, p, h, fracs, props, phase=OVERALL_PHASE):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        if not self.nuSolids:
            inProp1 = [P_VAR, p]
            inProp2 = [H_VAR, h]
            vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, props)
        else:
            matDict = MaterialPropertyDict()
            matDict[P_VAR].SetValue(p, FIXED_V)
            matDict[H_VAR].SetValue(h, FIXED_V)
            cmps = CompoundList(None)
            for i in range(len(fracs)):
                cmps.append(BasicProperty(FRAC_VAR))
            cmps.SetValues(fracs, FIXED_V)
            liqPhases = 1
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, props, nuSolids=self.nuSolids)
            vals = results.bulkProps
        return vals
        
    def GetPropertiesPS(self, p, s, fracs, props, phase=OVERALL_PHASE):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        
        if not self.nuSolids:
            inProp1 = [P_VAR, p]
            inProp2 = [S_VAR, s]
            vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, props)
        
        else:
            matDict = MaterialPropertyDict()
            matDict[P_VAR].SetValue(p, FIXED_V)
            matDict[S_VAR].SetValue(s, FIXED_V)
            cmps = CompoundList(None)
            for i in range(len(fracs)):
                cmps.append(BasicProperty(FRAC_VAR))
            cmps.SetValues(fracs, FIXED_V)
            liqPhases = 1
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, props, nuSolids=self.nuSolids)
            vals = results.bulkProps   
            
        return vals
        
    def CleanUp(self):
        self.ideal = self.waste = self.idealQ = None
        self.wasteQ = self.totalQ = self.effStream = None
        self.set = self.mix = None
        self._thCaseObj = None
        super(Expander, self).CleanUp()

    def GetObject(self, name):
        #BAckward compatibility
        if name == EFFICIENCY_PORT:
            name = ADIABATIC_EFF_PORT
        return super(Expander, self).GetObject(name)
        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(Expander, self).AdjustOldCase(version)


        #Borrow DeltaP signal
        if version[0] < 11:
            #First make sure it is there
            dpPort = self.ideal.GetPort(DELTAP_PORT)
            if not dpPort:
                dpPort = self.ideal.CreatePort(SIG, DELTAP_PORT)
                dpPort.SetSignalType(DELTAP_VAR)
                
            self.BorrowChildPort(self.ideal.GetPort(DELTAP_PORT), DELTAP_PORT)

        if version[0] < 61:
            prop = self.totalQ.GetPort(OUT_PORT).GetProperty()
            if prop.GetType().name == ENERGY_VAR:
                prop.SetTypeByName(WORK_VAR)

        if version[0] < 64:
            p = self.GetPort(POLYTROPIC_EFF_PORT)
            if p == None:
                #Polytropic efficiency
                self.polEffPort = self.CreatePort(SIG, POLYTROPIC_EFF_PORT)
                self.polEffPort.SetSignalType(GENERIC_VAR)                
                
        if version[0] < 66:
            p = self.GetPort(ADIABATIC_EFF_PORT)
            if p == None:
                p = self.GetPort(EFFICIENCY_PORT)
                if p != None:
                    self.RenamePort(EFFICIENCY_PORT, ADIABATIC_EFF_PORT)
                
                
class CompressorWithCurve(UnitOperations.UnitOperation):

    def __init__(self, initScript=None):
        # A Compressor
        # with Compressor curves, do not preserve entropy
        super(CompressorWithCurve, self).__init__(initScript)

        compressor = self.HCompressor = Compressor()
        self.AddUnitOperation(compressor, 'IsenthalpicCompressor')
        compressor.SetParameterValue(ISENTROPIC_PAR, 0)

        # Inlet P sensor
        self.InPSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.InPSensor, 'InPSensor')
        self.InPSensor.SetParameterValue(SIGTYPE_PAR, P_VAR)

        # Outlet P sensor
        self.OutPSensor = Sensor.PropertySensor()        
        self.AddUnitOperation(self.OutPSensor, 'OutPSensor')
        self.OutPSensor.SetParameterValue(SIGTYPE_PAR, P_VAR)

        # A set to set the delP between the inlet and outlet P
        self.SetP = Set.Set()
        self.AddUnitOperation(self.SetP, 'SetP')
        self.SetP.SetParameterValue(SIGTYPE_PAR, P_VAR)
        self.SetP.GetPort(Set.MULT_PORT).SetValue(1.0, FIXED_V)

        # A table lookup unit
        lookupTable = self.LookupTable = Pump.LookupTable()
        self.AddUnitOperation(lookupTable, 'LookupTable')
        lookupTable.SetParameterValue(NUMBSERIES_PAR, 4)           # 4 series: vol flow, head, efficiency and power
        lookupTable.SetParameterValue(EXTRAPOLATE_PAR + str(2), 0) # do not extrapolate efficiency
        lookupTable.SetParameterValue(SERIESTYPE_PAR + str(0), VOLFLOW_VAR)
        lookupTable.SetParameterValue(SERIESTYPE_PAR + str(1), LENGTH_VAR)
        lookupTable.SetParameterValue(SERIESTYPE_PAR + str(3), ENERGY_VAR) # actually power
        lookupTable.SetParameterValue(TABLETAGTYPE_PAR, GENERIC_VAR)  # i do not yet have a RPM

        
        # A flow sensor
        self.FlowSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.FlowSensor, 'FlowSensor')
        self.FlowSensor.SetParameterValue(SIGTYPE_PAR, VOLFLOW_VAR)

        # An equation unit to convert the head to delP
        # delP = MW * 0.00981 * head / molarVol
        # Note cannot back out mass density from head and delta pressure
        calcDP = self.CalcDelP = Pump.EquationUnit()
        self.AddUnitOperation(calcDP, 'CalcDelP')
        calcDP.SetParameterValue(NUMBSIG_PAR, 4)
        calcDP.SetParameterValue(TRANSFORM_EQT_PAR + str(0), 'x[1]*x[3]/0.00981/x[2]')
        calcDP.SetParameterValue(TRANSFORM_EQT_PAR + str(1), 'x[0]*x[2]*0.00981/x[3]')
        # x[0] = head
        # x[1] = delta pressure
        # x[2] = molecular weight
        # x[3] = molarVol

        
        # A molarVol sensor for calculating delP from head
        self.MolarVolSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.MolarVolSensor, 'MolarVolSensor')
        self.MolarVolSensor.SetParameterValue(SIGTYPE_PAR, molarV_VAR)

        
        # A MW sensor for calculating delP from head
        self.MWSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.MWSensor, 'MWSensor')
        self.MWSensor.SetParameterValue(SIGTYPE_PAR, MOLE_WT)

        
        # An energy sensor for setting the Q from the lookup table
        self.TotalQ = Sensor.EnergySensor()
        self.AddUnitOperation(self.TotalQ, 'TotalQ')
        
        # Connect them all
        self.ConnectPorts('FlowSensor', OUT_PORT,                 'MolarVolSensor', IN_PORT)
        self.ConnectPorts('MolarVolSensor', OUT_PORT,             'MWSensor', IN_PORT)
        self.ConnectPorts('MWSensor', OUT_PORT,                   'InPSensor', IN_PORT)
        self.ConnectPorts('InPSensor', OUT_PORT,                  'IsenthalpicCompressor', IN_PORT)
        self.ConnectPorts('IsenthalpicCompressor', IN_PORT + 'Q', 'TotalQ', OUT_PORT)
        self.ConnectPorts('IsenthalpicCompressor', OUT_PORT,      'OutPSensor', IN_PORT)
        
        self.ConnectPorts('InPSensor',  SIG_PORT, 'SetP', SIG_PORT + '0')
        self.ConnectPorts('OutPSensor', SIG_PORT, 'SetP', SIG_PORT + '1')
        self.ConnectPorts('FlowSensor', SIG_PORT, 'LookupTable', SIG_PORT + '0')

        self.ConnectPorts('TotalQ',   SIG_PORT,       'LookupTable', SIG_PORT + '3')
        self.ConnectPorts('CalcDelP', SIG_PORT + '1', 'SetP', Set.ADD_PORT)
        self.ConnectPorts('CalcDelP', SIG_PORT + '2', 'MWSensor', SIG_PORT)
        self.ConnectPorts('CalcDelP', SIG_PORT + '3', 'MolarVolSensor', SIG_PORT)
        
        self.BorrowChildPort(self.TotalQ.GetPort(IN_PORT),           IN_PORT + 'Q')
        self.BorrowChildPort(self.OutPSensor.GetPort(OUT_PORT),      OUT_PORT)
        self.BorrowChildPort(self.FlowSensor.GetPort(IN_PORT),       IN_PORT)
        self.BorrowChildPort(self.HCompressor.GetPort(DELTAP_PORT),  DELTAP_PORT)
        self.BorrowChildPort(self.LookupTable.GetPort(SPEC_TAG_PORT), self.GetNameForSpeedPort())
        
        
        #Change the type of the energy port such that it is in Work units and scaling
        self.TotalQ.GetPort(IN_PORT).GetProperty().SetTypeByName(WORK_VAR)
        

        #Adaibatic efficiency signals
        #Do not connect the efficiency port to the look up table here. Let the parameter setting do it
        adEffSt = self.effStream = Stream.Stream_Signal()
        adEffSt.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        self.AddUnitOperation(adEffSt, 'EfficiencySig')
        adEffSt.AddObject(Stream.ClonePort(), 'effClone')
        adEffSt.GetPort(OUT_PORT).ConnectTo(compressor.GetPort(ADIABATIC_EFF_PORT))
        self.BorrowChildPort(adEffSt.GetPort('effClone'), ADIABATIC_EFF_PORT)
        
        
        #Polytropic efficiency signals
        #Do not connect the efficiency port to the look up table here. Let the parameter setting do it
        polEffSt = self.polEffStream = Stream.Stream_Signal()
        polEffSt.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        self.AddUnitOperation(polEffSt, 'PolytropicEffSig')
        polEffSt.AddObject(Stream.ClonePort(), 'effClone')
        polEffSt.GetPort(OUT_PORT).ConnectTo(compressor.GetPort(POLYTROPIC_EFF_PORT))
        self.BorrowChildPort(polEffSt.GetPort('effClone'), POLYTROPIC_EFF_PORT)
        
        #self.ConnectPorts('EfficiencySig', IN_PORT, 'LookupTable', SIG_PORT + '2')
        #self.ConnectPorts('EfficiencySig', OUT_PORT, 'IsenthalpicCompressor', ADIABATIC_EFF_PORT)        
        
        
        # clone and borrow the lookuptable's head port
        headStream = self.headStream = Stream.Stream_Signal()
        headStream.SetParameterValue(SIGTYPE_PAR, LENGTH_VAR)
        self.AddUnitOperation(headStream, 'HeadSig')
        headStream.AddObject(Stream.ClonePort(), 'headClone')
        headStream.GetPort(IN_PORT).ConnectTo(lookupTable.GetPort(SIG_PORT + '1'))
        headStream.GetPort(OUT_PORT).ConnectTo(calcDP.GetPort(SIG_PORT + '0'))
        self.BorrowChildPort(headStream.GetPort('headClone'), HEAD_PORT)
        
        #self.ConnectPorts('HeadSig', IN_PORT, 'LookupTable', SIG_PORT + '1')
        #self.ConnectPorts('HeadSig', OUT_PORT, 'CalcDelP', SIG_PORT + '0')        
        

        # parameters
        #default: no Compressor curve
        self.SetParameterValue(NUMBTABLE_PAR, 0)
        self.SetParameterValue(EFFCURVETYPE_PAR, ADIABATIC_TYPE)
        
        

    def CleanUp(self):
        self.HCompressor = self.InPSensor = self.OutPSensor = None
        self.SetP = self.LookupTable = self.FlowSensor = None
        self.CalcDelP = self.MolarVolSensor = self.MWSensor = None
        self.TotalQ = self.effStream = self.headStream = None
        self.polEffStream = None
        super(CompressorWithCurve, self).CleanUp()

    def GetNameForSpeedPort(self):
        """Name chosen for the speed port"""
        return COMPRESSORSPEED_PORT
        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(CompressorWithCurve,self).AdjustOldCase(version)
        
        if version[0] < 12:
            newPort = self.GetPort(DELTAP_PORT)
            if not newPort:
                # Borrow the deltaP port
                self.BorrowChildPort(self.HCompressor.GetPort(DELTAP_PORT), DELTAP_PORT)
                
            newPort = self.GetPort(EFFICIENCY_PORT)
            if not newPort:
                # insert a signal stream between the 'LookupTable.SIG_PORT2' and IsenthalpicCompressor.ADIABATIC_EFF_PORT
                # first break the old connection
                self.DisconnectPort('IsenthalpicCompressor', EFFICIENCY_PORT)
                # create the in-between signal stream and re-connect
                self.effStream = Stream.Stream_Signal()
                self.effStream.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
                self.AddUnitOperation(self.effStream, 'EfficiencySig')
                effClone = Stream.ClonePort()
                self.effStream.AddObject(effClone, 'effClone')
                self.ConnectPorts('EfficiencySig', IN_PORT, 'LookupTable', SIG_PORT + '2')
                self.ConnectPorts('EfficiencySig', OUT_PORT, 'IsenthalpicCompressor', EFFICIENCY_PORT)        
                self.BorrowChildPort(self.effStream.GetPort('effClone'), EFFICIENCY_PORT)
                
            newPort = self.GetPort(HEAD_PORT)
            if not newPort:
                # insert a signal stream between the 'CalcDelP.SIG_PORT0' and 'LookupTable.SIG_PORT1'
                # first break the old connection
                self.DisconnectPort('CalcDelP', SIG_PORT)
                # create the in-between signal stream and re-connect
                self.headStream = Stream.Stream_Signal()
                self.headStream.SetParameterValue(SIGTYPE_PAR, LENGTH_VAR)
                self.AddUnitOperation(self.headStream, 'HeadSig')
                headClone = Stream.ClonePort()
                self.headStream.AddObject(headClone, 'headClone')
                self.ConnectPorts('HeadSig', IN_PORT, 'LookupTable', SIG_PORT + '1')
                self.ConnectPorts('HeadSig', OUT_PORT, 'CalcDelP', SIG_PORT + '0')        
                self.BorrowChildPort(self.headStream.GetPort('headClone'), HEAD_PORT)
                
                
        if version[0] < 61:
            prop = self.TotalQ.GetPort(IN_PORT).GetProperty()
            if prop.GetType().name == ENERGY_VAR:
                prop.SetTypeByName(WORK_VAR)
                
        #if version[0] <63:
            #p = self.GetPort(POLYTROPIC_EFF_PORT)
            #if p == None:
                #p = self.HCompressor.GetPort(POLYTROPIC_EFF_PORT)
                #if p == None:
                    ##Polytropic efficiency
                    #self.HCompressor.polEffPort = self.CreatePort(SIG, POLYTROPIC_EFF_PORT)
                    #self.HCompressor.polEffPort.SetSignalType(GENERIC_VAR)
                #self.BorrowChildPort(self.HCompressor.GetPort(POLYTROPIC_EFF_PORT), POLYTROPIC_EFF_PORT)
                
        if version[0] < 65:
            
            #Do not add the unit op to the solve stack only because of this fix up
            stackStatus = self._stackStatus
                
            p = self.GetPort(POLYTROPIC_EFF_PORT)
            if p != None:
                #One version used to borrow the eff port from the compressor directly instead of
                #borrowing it from a signal stream
                parent = p.GetParent()
                if isinstance(parent, Compressor):
                    self.DeletePort(p)
                    
            #Make sure the child compressor has a polytropic eff port
            if p == None:
                p = self.HCompressor.GetPort(POLYTROPIC_EFF_PORT)
                if p == None:
                    #Polytropic efficiency
                    self.HCompressor.polEffPort = self.CreatePort(SIG, POLYTROPIC_EFF_PORT)
                    self.HCompressor.polEffPort.SetSignalType(GENERIC_VAR)
                    
            #Make sure there is a polytropicEffSignalStream
            polEffSt = self.GetChildUO('PolytropicEffSig')
            if polEffSt == None:
                polEffSt = self.polEffStream = Stream.Stream_Signal()
                polEffSt.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
                polEffSt.AddObject(Stream.ClonePort(), 'effClone')
                self.AddUnitOperation(polEffSt, 'PolytropicEffSig')
                polEffSt.GetPort(OUT_PORT).ConnectTo(self.HCompressor.GetPort(POLYTROPIC_EFF_PORT))
                
            else:
                self.polEffStream = polEffSt
            
            #Try obtaining the port again
            p = self.GetPort(POLYTROPIC_EFF_PORT)
            if p == None:
                self.BorrowChildPort(polEffSt.GetPort('effClone'), POLYTROPIC_EFF_PORT)
            
            type = self.GetParameterValue(EFFCURVETYPE_PAR)
            if type == None:
                type = self.SetParameterValue(EFFCURVETYPE_PAR, ADIABATIC_TYPE)
                
            ###self.ForgetAllCalculations()
            
            #Remove the unit op from the stacks in case they weren't there before
            #if not stackStatus & Flowsheet.ON_SOLVE_STACK and self._stackStatus & Flowsheet.ON_SOLVE_STACK:
                #self.RemoveOpFromSolveStack(self)
            #if not stackStatus & Flowsheet.ON_FORGET_STACK and self._stackStatus & Flowsheet.ON_FORGET_STACK:
                #self.RemoveOpFromForgetStack(self)
                
        if version[0] < 66:
            p = self.GetPort(ADIABATIC_EFF_PORT)
            if p == None:
                p = self.GetPort(EFFICIENCY_PORT)
                if p != None:
                    self.RenamePort(EFFICIENCY_PORT, ADIABATIC_EFF_PORT)
                    
                
    def GetObject(self, name):
        # shortcut to access the Compressor curves
        # CompressorWithCurve.EfficiencyCurveX vs CompressorWithCurve.LookupTable.TableX.Series2
        # where X is the curve table
        if name == EFFICIENCY_PORT:
            name = ADIABATIC_EFF_PORT
        obj = UnitOperations.UnitOperation.GetObject(self, name)
        if not obj:
            if name[:len(FLOW_SERIES)] == FLOW_SERIES:
                idx = name[len(FLOW_SERIES):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(SERIES_OBJ + str(0))
            elif name[:len(HEAD_SERIES)] == HEAD_SERIES:
                idx = name[len(HEAD_SERIES):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(SERIES_OBJ + str(1))
            elif name[:len(EFFICIENCY_SERIES)] == EFFICIENCY_SERIES:
                idx = name[len(EFFICIENCY_SERIES):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(SERIES_OBJ + str(2))
            elif name[:len(POWER_SERIES)] == POWER_SERIES:
                idx = name[len(POWER_SERIES):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(SERIES_OBJ + str(3))
            elif name[:len(self.GetNameForSpeedPort())] == self.GetNameForSpeedPort():
                idx = name[len(self.GetNameForSpeedPort()):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(TABLETAG_VAR)
        return obj

    def GetContents(self):
        result = super(CompressorWithCurve, self).GetContents()
#        result.append(('LookupTable', self.LookupTable))
        for i in range(self.LookupTable.GetTableCount()):
            tbl = self.LookupTable.GetObject(TABLE_OBJ + str(i))
            result.append(('%s%d' % (FLOW_SERIES, i), tbl.GetObject(SERIES_OBJ + str(0))))
            result.append(('%s%d' % (HEAD_SERIES, i), tbl.GetObject(SERIES_OBJ + str(1))))
            result.append(('%s%d' % (EFFICIENCY_SERIES, i), tbl.GetObject(SERIES_OBJ + str(2))))
            result.append(('%s%d' % (POWER_SERIES, i), tbl.GetObject(SERIES_OBJ + str(3))))
            result.append(('%s%d' % (self.GetNameForSpeedPort(), i), tbl.GetObject(TABLETAG_VAR)))
        return result
        
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        if paramName == NUMBTABLE_PAR:
            self.LookupTable.SetParameterValue(paramName, value)        
            super(CompressorWithCurve, self).SetParameterValue(paramName, value)
        elif paramName == IGNORECURVE_PAR:            
            #...ignore the lookuptable and remove any specifications
            if value == 'None': value = None
            self.LookupTable.SetParameterValue(IGNORED_PAR, value)
            if value:
                port = self.GetPort(HEAD_PORT)
                port.SetValue(None, FIXED_V)
        elif paramName == EFFCURVETYPE_PAR:
            if value != ADIABATIC_TYPE and value != POLYTROPIC_TYPE:
                value = ADIABATIC_TYPE
            if self.parameters.has_key(EFFCURVETYPE_PAR):
                if self.parameters[EFFCURVETYPE_PAR] == value:
                    return
            #Put the parameter in
            super(CompressorWithCurve, self).SetParameterValue(paramName, value)
            
            #Update the connection of the efficiency curve
            self.UpdateEffCurveConnection()
            
        else:
            super(CompressorWithCurve, self).SetParameterValue(paramName, value)
                
    def DeleteObject(self, obj):
        
        #Can not delete eff curve type parameter
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() == EFFCURVETYPE_PAR:
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return

        super(CompressorWithCurve, self).DeleteObject(obj)
        
        
    def UpdateEffCurveConnection(self):
        """The efficiency curves can be of adiabatic or polytropic type. therefore, the Lookuptable should
        connect to the proper port"""
        type = self.GetParameterValue(EFFCURVETYPE_PAR)
        if type != ADIABATIC_TYPE and type != POLYTROPIC_TYPE:
            self.parameters[EFFCURVETYPE_PAR] = ADIABATIC_TYPE
            type = ADIABATIC_TYPE
            
            
        if type == ADIABATIC_TYPE:
            self.effStream.GetPort(IN_PORT).ConnectTo(self.LookupTable.GetPort(SIG_PORT + '2'))
        else:
            self.polEffStream.GetPort(IN_PORT).ConnectTo(self.LookupTable.GetPort(SIG_PORT + '2'))
        
        
    def Minus(self, varName):
        # remove a Compressor curve
        if varName[:len(COMPRESSORCURVE_OBJ)] == COMPRESSORCURVE_OBJ:
            #try:
                idx = int(varName[len(COMPRESSORCURVE_OBJ):])
                if self.LookupTable.Minus(idx):
                    n = self.LookupTable.GetParameterValue(NUMBTABLE_PAR)
                    self.SetParameterValue(NUMBTABLE_PAR, n)
            #except:
                #pass
    
class ExpanderWithCurve(UnitOperations.UnitOperation):

    def __init__(self, initScript=None):
        # A Expander
        # with Expander curves, do not preserve entropy
        super(ExpanderWithCurve, self).__init__(initScript)

        expander = self.HExpander = Expander()
        self.AddUnitOperation(self.HExpander, 'IsenthalpicExpander')
        expander.SetParameterValue(ISENTROPIC_PAR, 0)

        # Inlet P sensor
        self.InPSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.InPSensor, 'InPSensor')
        self.InPSensor.SetParameterValue(SIGTYPE_PAR, P_VAR)

        # Outlet P sensor
        self.OutPSensor = Sensor.PropertySensor()        
        self.AddUnitOperation(self.OutPSensor, 'OutPSensor')
        self.OutPSensor.SetParameterValue(SIGTYPE_PAR, P_VAR)

        # A set to set the delP between the inlet and outlet P
        self.SetP = Set.Set()
        self.AddUnitOperation(self.SetP, 'SetP')
        self.SetP.SetParameterValue(SIGTYPE_PAR, P_VAR)
        self.SetP.GetPort(Set.MULT_PORT).SetValue(1.0, FIXED_V)

        # A table lookup unit
        lookupTable = self.LookupTable = Pump.LookupTable()
        self.AddUnitOperation(lookupTable, 'LookupTable')
        lookupTable.SetParameterValue(NUMBSERIES_PAR, 4)           # 4 series: vol flow, head, efficiency and power
        lookupTable.SetParameterValue(EXTRAPOLATE_PAR + str(2), 0) # do not extrapolate efficiency
        lookupTable.SetParameterValue(SERIESTYPE_PAR + str(0), VOLFLOW_VAR)
        lookupTable.SetParameterValue(SERIESTYPE_PAR + str(1), LENGTH_VAR)
        lookupTable.SetParameterValue(SERIESTYPE_PAR + str(3), ENERGY_VAR) # actually power
        lookupTable.SetParameterValue(TABLETAGTYPE_PAR, GENERIC_VAR)  # i do not yet has a RPM

        # A flow sensor
        self.FlowSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.FlowSensor, 'FlowSensor')
        self.FlowSensor.SetParameterValue(SIGTYPE_PAR, VOLFLOW_VAR)

        # An equation unit to convert the head to delP
        # delP = MW * 0.00981 * head / molarVol
        # Note cannot back out mass density from head and delta pressure
        calcDP = self.CalcDelP = Pump.EquationUnit()
        self.AddUnitOperation(calcDP, 'CalcDelP')
        calcDP.SetParameterValue(NUMBSIG_PAR, 4)
        calcDP.SetParameterValue(TRANSFORM_EQT_PAR + str(0), '-x[1]*x[3]/0.00981/x[2]')
        calcDP.SetParameterValue(TRANSFORM_EQT_PAR + str(1), '-x[0]*x[2]*0.00981/x[3]')
        # x[0] = head
        # x[1] = delta pressure
        # x[2] = molecular weight
        # x[3] = molarVol

        # A molarVol sensor for calculating delP from head
        self.MolarVolSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.MolarVolSensor, 'MolarVolSensor')
        self.MolarVolSensor.SetParameterValue(SIGTYPE_PAR, molarV_VAR)

        # A MW sensor for calculating delP from head
        self.MWSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.MWSensor, 'MWSensor')
        self.MWSensor.SetParameterValue(SIGTYPE_PAR, MOLE_WT)

        # An energy sensor for setting the Q from the lookup table
        self.TotalQ = Sensor.EnergySensor()
        self.AddUnitOperation(self.TotalQ, 'TotalQ')
        
        # Connect them all
        self.ConnectPorts('FlowSensor', OUT_PORT,             'MolarVolSensor', IN_PORT)
        self.ConnectPorts('MolarVolSensor', OUT_PORT,         'MWSensor', IN_PORT)
        self.ConnectPorts('MWSensor', OUT_PORT,               'InPSensor', IN_PORT)
        self.ConnectPorts('InPSensor', OUT_PORT,              'IsenthalpicExpander', IN_PORT)
#        self.ConnectPorts('IsenthalpicExpander', ADIABATIC_EFF_PORT, 'LookupTable', SIG_PORT + '2')
        self.ConnectPorts('IsenthalpicExpander', OUT_PORT + 'Q',   'TotalQ', IN_PORT)
        self.ConnectPorts('IsenthalpicExpander', OUT_PORT,        'OutPSensor', IN_PORT)
        
        self.ConnectPorts('InPSensor',  SIG_PORT, 'SetP', SIG_PORT + '0')
        self.ConnectPorts('OutPSensor', SIG_PORT, 'SetP', SIG_PORT + '1')
        self.ConnectPorts('FlowSensor', SIG_PORT, 'LookupTable', SIG_PORT + '0')

        self.ConnectPorts('TotalQ',   SIG_PORT,       'LookupTable', SIG_PORT + '3')
#        self.ConnectPorts('CalcDelP', SIG_PORT + '0', 'LookupTable', SIG_PORT + '1')
        self.ConnectPorts('CalcDelP', SIG_PORT + '1', 'SetP', Set.ADD_PORT)
        self.ConnectPorts('CalcDelP', SIG_PORT + '2', 'MWSensor', SIG_PORT)
        self.ConnectPorts('CalcDelP', SIG_PORT + '3', 'MolarVolSensor', SIG_PORT)

        self.BorrowChildPort(self.TotalQ.GetPort(OUT_PORT), OUT_PORT + 'Q')
        self.BorrowChildPort(self.OutPSensor.GetPort(OUT_PORT), OUT_PORT)
        self.BorrowChildPort(self.FlowSensor.GetPort(IN_PORT), IN_PORT)
        self.BorrowChildPort(self.HExpander.GetPort(DELTAP_PORT), DELTAP_PORT)
        self.BorrowChildPort(self.LookupTable.GetPort(SPEC_TAG_PORT), EXPANDERSPEED_PORT)

        #Change the type of the energy port such that it is in Work units and scaling
        self.TotalQ.GetPort(OUT_PORT).GetProperty().SetTypeByName(WORK_VAR)
        
        
        #Adiabatic efficiency signals
        #Do not connect the efficiency port to the look up table here. Let the parameter setting do it
        adEffSt = self.effStream = Stream.Stream_Signal()
        adEffSt.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        self.AddUnitOperation(adEffSt, 'EfficiencySig')
        adEffSt.AddObject(Stream.ClonePort(), 'effClone')
        adEffSt.GetPort(OUT_PORT).ConnectTo(expander.GetPort(ADIABATIC_EFF_PORT))
        self.BorrowChildPort(adEffSt.GetPort('effClone'), ADIABATIC_EFF_PORT)
        
        
        #Polytropic efficiency signals
        #Do not connect the efficiency port to the look up table here. Let the parameter setting do it
        #Connect the In port of the sginal stream to the compressor. For some reason
        #the expander does differntly and it connects the cloned port but there is nothing
        #wrong with this
        polEffSt = self.polEffStream = Stream.Stream_Signal()
        polEffSt.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        self.AddUnitOperation(polEffSt, 'PolytropicEffSig')
        polEffSt.AddObject(Stream.ClonePort(), 'effClone')
        polEffSt.GetPort(OUT_PORT).ConnectTo(expander.GetPort(POLYTROPIC_EFF_PORT))
        self.BorrowChildPort(polEffSt.GetPort('effClone'), POLYTROPIC_EFF_PORT)
        
        
        ##self.effStream = Stream.Stream_Signal()
        ##self.effStream.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        ##self.AddUnitOperation(self.effStream, 'EfficiencySig')
        ##effClone = Stream.ClonePort()
        ##self.effStream.AddObject(effClone, 'effClone')
        ##self.ConnectPorts('EfficiencySig', IN_PORT, 'LookupTable', SIG_PORT + '2')
        ##self.ConnectPorts('EfficiencySig', OUT_PORT, 'IsenthalpicExpander', ADIABATIC_EFF_PORT)        
        ##self.BorrowChildPort(self.effStream.GetPort('effClone'), ADIABATIC_EFF_PORT)
        ##self.BorrowChildPort(self.HExpander.GetPort(POLYTROPIC_EFF_PORT), POLYTROPIC_EFF_PORT)
        
        
        
        # clone and borrow the lookuptable's head port
        headStream = self.headStream = Stream.Stream_Signal()
        headStream.SetParameterValue(SIGTYPE_PAR, LENGTH_VAR)
        self.AddUnitOperation(headStream, 'HeadSig')
        headStream.AddObject(Stream.ClonePort(), 'headClone')
        headStream.GetPort(IN_PORT).ConnectTo(lookupTable.GetPort(SIG_PORT + '1'))
        headStream.GetPort(OUT_PORT).ConnectTo(calcDP.GetPort(SIG_PORT + '0'))
        self.BorrowChildPort(headStream.GetPort('headClone'), HEAD_PORT)

        # parameters
        #default: no Expander curve
        self.SetParameterValue(NUMBTABLE_PAR, 0)
        self.SetParameterValue(EFFCURVETYPE_PAR, ADIABATIC_TYPE)
        
        

    def CleanUp(self):
        self.HExpander = self.InPSensor = self.OutPSensor = None
        self.SetP = self.LookupTable = self.FlowSensor = self.CalcDelP = None
        self.MolarVolSensor = self.MWSensor = self.TotalQ = None
        self.effStream = effClone = self.headStream = None
        self.polEffStream = None
        super(ExpanderWithCurve, self).CleanUp()
        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(ExpanderWithCurve,self).AdjustOldCase(version)
        
        if version[0] < 12:
            newPort = self.GetPort(DELTAP_PORT)
            if not newPort:
                # Borrow the deltaP port
                self.BorrowChildPort(self.HExpander.GetPort(DELTAP_PORT), DELTAP_PORT)
                
            newPort = self.GetPort(EFFICIENCY_PORT)
            if not newPort:
                # insert a signal stream between the 'LookupTable.SIG_PORT2' and IsenthalpicExpander.ADIABATIC_EFF_PORT
                # first break the old connection
                self.DisconnectPort('IsenthalpicExpander', EFFICIENCY_PORT)
                # create the in-between signal stream and re-connect
                self.effStream = Stream.Stream_Signal()
                self.effStream.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
                self.AddUnitOperation(self.effStream, 'EfficiencySig')
                effClone = Stream.ClonePort()
                self.effStream.AddObject(effClone, 'effClone')
                self.ConnectPorts('EfficiencySig', IN_PORT, 'LookupTable', SIG_PORT + '2')
                self.ConnectPorts('EfficiencySig', OUT_PORT, 'IsenthalpicExpander', EFFICIENCY_PORT)        
                self.BorrowChildPort(self.effStream.GetPort('effClone'), EFFICIENCY_PORT)
                
            newPort = self.GetPort(HEAD_PORT)
            if not newPort:
                # insert a signal stream between the 'CalcDelP.SIG_PORT0' and 'LookupTable.SIG_PORT1'
                # first break the old connection
                self.DisconnectPort('CalcDelP', SIG_PORT)
                # create the in-between signal stream and re-connect
                self.headStream = Stream.Stream_Signal()
                self.headStream.SetParameterValue(SIGTYPE_PAR, LENGTH_VAR)
                self.AddUnitOperation(self.headStream, 'HeadSig')
                headClone = Stream.ClonePort()
                self.headStream.AddObject(headClone, 'headClone')
                self.ConnectPorts('HeadSig', IN_PORT, 'LookupTable', SIG_PORT + '1')
                self.ConnectPorts('HeadSig', OUT_PORT, 'CalcDelP', SIG_PORT + '0')        
                self.BorrowChildPort(self.headStream.GetPort('headClone'), HEAD_PORT)
                
        if version[0] < 61:
            prop = self.TotalQ.GetPort(OUT_PORT).GetProperty()
            if prop.GetType().name == ENERGY_VAR:
                prop.SetTypeByName(WORK_VAR)
                
        #if version[0] < 64:
            #p = self.GetPort(POLYTROPIC_EFF_PORT)
            #if p == None:
                #p = self.HExpander.GetPort(POLYTROPIC_EFF_PORT)
                #if p == None:
                    ##Polytropic efficiency
                    #self.HExpander.polEffPort = self.CreatePort(SIG, POLYTROPIC_EFF_PORT)
                    #self.HExpander.polEffPort.SetSignalType(GENERIC_VAR)
                #self.BorrowChildPort(self.HExpander.GetPort(POLYTROPIC_EFF_PORT), POLYTROPIC_EFF_PORT)


        if version[0] < 65:
            
            #Do not add the unit op to the solve stack only because of this fix up
            stackStatus = self._stackStatus
                
            p = self.GetPort(POLYTROPIC_EFF_PORT)
            if p != None:
                #One version used to borrow the eff port from the compressor directly instead of
                #borrowing it from a signal stream
                parent = p.GetParent()
                if isinstance(parent, Expander):
                    self.DeletePort(p)
                    
            #Make sure the child compressor has a polytropic eff port
            if p == None:
                p = self.HExpander.GetPort(POLYTROPIC_EFF_PORT)
                if p == None:
                    #Polytropic efficiency
                    self.HExpander.polEffPort = self.CreatePort(SIG, POLYTROPIC_EFF_PORT)
                    self.HExpander.polEffPort.SetSignalType(GENERIC_VAR)
                    
            #Make sure there is a polytropicEffSignalStream
            polEffSt = self.GetChildUO('PolytropicEffSig')
            if polEffSt == None:
                polEffSt = self.polEffStream = Stream.Stream_Signal()
                polEffSt.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
                polEffSt.AddObject(Stream.ClonePort(), 'effClone')
                self.AddUnitOperation(polEffSt, 'PolytropicEffSig')
                polEffSt.GetPort(OUT_PORT).ConnectTo(self.HExpander.GetPort(POLYTROPIC_EFF_PORT))
                
            else:
                self.polEffStream = polEffSt
            
            #Try obtaining the port again
            p = self.GetPort(POLYTROPIC_EFF_PORT)
            if p == None:
                self.BorrowChildPort(polEffSt.GetPort('effClone'), POLYTROPIC_EFF_PORT)
            
            type = self.GetParameterValue(EFFCURVETYPE_PAR)
            if type == None:
                type = self.SetParameterValue(EFFCURVETYPE_PAR, ADIABATIC_TYPE)
                
            #Remove the unit op from the stacks in case they weren't there before
            #if not stackStatus & Flowsheet.ON_SOLVE_STACK and self._stackStatus & Flowsheet.ON_SOLVE_STACK:
                #self.RemoveOpFromSolveStack(self)
            #if not stackStatus & Flowsheet.ON_FORGET_STACK and self._stackStatus & Flowsheet.ON_FORGET_STACK:
                #self.RemoveOpFromForgetStack(self)
                
                
                
        if version[0] < 66:
            p = self.GetPort(ADIABATIC_EFF_PORT)
            if p == None:
                p = self.GetPort(EFFICIENCY_PORT)
                if p != None:
                    self.RenamePort(EFFICIENCY_PORT, ADIABATIC_EFF_PORT)
                
                
    def GetObject(self, name):
        # shortcut to access the Expander curves
        # ExpanderWithCurve.EfficiencyCurveX vs ExpanderWithCurve.LookupTable.TableX.Series2
        # where X is the curve table
        if name == EFFICIENCY_PORT:
            name = ADIABATIC_EFF_PORT
        obj = UnitOperations.UnitOperation.GetObject(self, name)
        if not obj:
            if name[:len(FLOW_SERIES)] == FLOW_SERIES:
                idx = name[len(FLOW_SERIES):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(SERIES_OBJ + str(0))
            elif name[:len(HEAD_SERIES)] == HEAD_SERIES:
                idx = name[len(HEAD_SERIES):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(SERIES_OBJ + str(1))
            elif name[:len(EFFICIENCY_SERIES)] == EFFICIENCY_SERIES:
                idx = name[len(EFFICIENCY_SERIES):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(SERIES_OBJ + str(2))
            elif name[:len(POWER_SERIES)] == POWER_SERIES:
                idx = name[len(POWER_SERIES):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(SERIES_OBJ + str(3))
            elif name[:len(EXPANDERSPEED_PORT)] == EXPANDERSPEED_PORT:
                idx = name[len(EXPANDERSPEED_PORT):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(TABLETAG_VAR)
        return obj

    def GetContents(self):
        result = super(ExpanderWithCurve, self).GetContents()
#        result.append(('LookupTable', self.LookupTable))
        for i in range(self.LookupTable.GetTableCount()):
            tbl = self.LookupTable.GetObject(TABLE_OBJ + str(i))
            result.append(('%s%d' % (FLOW_SERIES, i), tbl.GetObject(SERIES_OBJ + str(0))))
            result.append(('%s%d' % (HEAD_SERIES, i), tbl.GetObject(SERIES_OBJ + str(1))))
            result.append(('%s%d' % (EFFICIENCY_SERIES, i), tbl.GetObject(SERIES_OBJ + str(2))))
            result.append(('%s%d' % (POWER_SERIES, i), tbl.GetObject(SERIES_OBJ + str(3))))
            result.append(('%s%d' % (EXPANDERSPEED_PORT, i), tbl.GetObject(TABLETAG_VAR)))
        return result
        
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        if paramName == NUMBTABLE_PAR:
            UnitOperations.UnitOperation.SetParameterValue(self, paramName, value)
            self.LookupTable.SetParameterValue(paramName, value)
            self.ForgetAllCalculations
        if paramName == IGNORECURVE_PAR:            
            #...ignore the lookuptable and remove any specifications
            if value == 'None': value = None
            self.LookupTable.SetParameterValue(IGNORED_PAR, value)
            if value:
                port = self.GetPort(HEAD_PORT)
                port.SetValue(None, FIXED_V)          
        elif paramName == EFFCURVETYPE_PAR:
            if value != ADIABATIC_TYPE and value != POLYTROPIC_TYPE:
                value = ADIABATIC_TYPE
            if self.parameters.has_key(EFFCURVETYPE_PAR):
                if self.parameters[EFFCURVETYPE_PAR] == value:
                    return
            #Put the parameter in
            super(ExpanderWithCurve, self).SetParameterValue(paramName, value)
            
            #Update the connection of the efficiency curve
            self.UpdateEffCurveConnection()
            
        else:
            super(ExpanderWithCurve, self).SetParameterValue(paramName, value)
             
    def DeleteObject(self, obj):
        
        #Can not delete eff curve type parameter
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() == EFFCURVETYPE_PAR:
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return

        super(ExpanderWithCurve, self).DeleteObject(obj)
        
        
    def UpdateEffCurveConnection(self):
        """The efficiency curves can be of adiabatic or polytropic type. therefore, the Lookuptable should
        connect to the proper port"""
        type = self.GetParameterValue(EFFCURVETYPE_PAR)
        if type != ADIABATIC_TYPE and type != POLYTROPIC_TYPE:
            self.parameters[EFFCURVETYPE_PAR] = ADIABATIC_TYPE
            type = ADIABATIC_TYPE
            
            
        if type == ADIABATIC_TYPE:
            self.effStream.GetPort(IN_PORT).ConnectTo(self.LookupTable.GetPort(SIG_PORT + '2'))
        else:
            self.polEffStream.GetPort(IN_PORT).ConnectTo(self.LookupTable.GetPort(SIG_PORT + '2'))
                    

    def Minus(self, varName):
        # remove a Expander curve
        if varName[:len(EXPANDERCURVE_OBJ)] == EXPANDERCURVE_OBJ:
            try:
                idx = int(varName[len(EXPANDERCURVE_OBJ):])
                if self.LookupTable.Minus(idx):
                    n = self.LookupTable.GetParameterValue(NUMBTABLE_PAR)
                    self.SetParameterValue(NUMBTABLE_PAR, n)
            except:
                pass
