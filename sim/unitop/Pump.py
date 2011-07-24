"""Models for compression/expansion equipment

Classes:
IdealPump - an Isenthalpic Pump
Pump - Pump with adiabatic efficiency

"""

#PRESSURE DROP CALCULATION CREATED BY NORFAIZAH ON 27TH FEBRUARY 2003


import UnitOperations
import Balance, Heater, Set, Sensor, Stream
from sim.solver import Flowsheet, Error
from sim.solver.Variables import *
from XYTable import *

VALID_UNIT_OPERATIONS = ['EquationUnit',
                         'LookupTable',
                         'IdealPump',
                         'Pump',
                         'IsenthalpicPump',
                         'PumpWithCurve']

ISENTROPIC_PAR = 'Isentropic'
HEAD_SERIES = 'HeadCurve'
FLOW_SERIES = 'FlowCurve'
EFFICIENCY_SERIES = 'EfficiencyCurve'
POWER_SERIES = 'Power'

EFFICIENCY_PORT = 'Efficiency'
HEAD_PORT = 'Head'

PUMPCURVE_OBJ = 'PumpCurve'
TABLE_OBJ  = 'Table'
NUMBTABLE_PAR = 'NumberTables'
NUMBSERIES_PAR = 'NumberSeries'
TABLETAGTYPE_PAR = 'TableType'
SERIESTYPE_PAR = 'SeriesType'
EXTRAPOLATE_PAR = 'Extrapolate'
SPEC_TAG_PORT = 'SpecTagValue'

PUMPSPEED_PORT = 'PumpSpeed'
IGNORECURVE_PAR = 'IgnoreCurve'

# defines for EquationUnit
NUMBSIG_PAR = 'NumberSignal'
TRANSFORM_EQT_PAR = 'Equation'



class EquationUnit(UnitOperations.UnitOperation):
    def __init__(self, initScript=None):
        super(EquationUnit, self).__init__(initScript)
        self._FuncExpression = None #This shouldn't be here
        self._Funcs = {}
        self._FuncsDefs = {}
        self.SetParameterValue(NUMBSIG_PAR, 0)

        
    def __getstate__(self):
        """return info to store"""
        try: 
            state = self.__dict__.copy()
            del state['_Funcs']
            return state
        except: 
            return self.__dict__
        
    def __setstate__(self, oldState):
        """build packages from saved info"""
        
        self.__dict__ = oldState
        if self.__dict__.has_key('_FuncsDefs'):
            if self._FuncsDefs:
                self._Funcs = {}
                for k, v in self._FuncsDefs.items():
                    if v != None:
                        self._Funcs[k] = compile(v, '', 'eval')
                    else:
                        self._Funcs[k] = v

            
    def SetParameterValue(self, paramName, value):
        super(EquationUnit, self).SetParameterValue(paramName, value)
        if (paramName == NUMBSIG_PAR):
            n = self.GetParameterValue(NUMBSIG_PAR)
            inPorts = self.GetNumberPorts(SIG)
            for i  in range(inPorts, n, -1):
                #Delete ports that are not needed
                self.DeletePortNamed(SIG_PORT + str(i-1))
                if self._Funcs.get(TRANSFORM_EQT_PAR + str(i-1), None) != None:
                    del self._Funcs[TRANSFORM_EQT_PAR + str(i-1)]
                if self._FuncsDefs.get(TRANSFORM_EQT_PAR + str(i-1), None) != None:
                    del self._FuncsDefs[TRANSFORM_EQT_PAR + str(i-1)]
                    
            for i in range(inPorts, n):
                sigPort = self.CreatePort(SIG, SIG_PORT + str(i))
                # do not set the signal type, so that i can be connected to
                # any signal port without generating a type mismatch error.
                self._Funcs[TRANSFORM_EQT_PAR + str(i)] = None
                self._FuncsDefs[TRANSFORM_EQT_PAR + str(i)] = None
                
        elif (paramName[:len(TRANSFORM_EQT_PAR)] == TRANSFORM_EQT_PAR):
            # compile for speed            
            # Equation0 corresponds to x0 = func(...)
            # Equation1 corresponds to x1 = func(...)
            #   etc.
            # They are the transformation of the same equation, allowing backward calcs.
            eqnStr = self.GetParameterValue(paramName)
            if (self._Funcs.has_key(paramName) and eqnStr != ''):
                self._Funcs[paramName] = compile(eqnStr, '', 'eval')    
                self._FuncsDefs[paramName] = eqnStr 

    def Solve(self):
        # solve if only one unknown variable
        # if variable X is unknown, use EquationX andput reaults in port SignalX
        try:
            # assemble the variables
            x = []
            inPorts = self.GetNumberPorts(SIG)
            if (inPorts == 0): return

            iVar = -1            
            for i in range(inPorts):
                port = self.GetPort(SIG_PORT + str(i))
                val = port.GetValue()
                if (val == None):
                    if iVar >= 0: return
                    iVar = i
                    x.append(0.0)   # value not used, set to zero so that x can be eval()
                else:
                    x.append(float(val))            
            result = eval(self._Funcs[TRANSFORM_EQT_PAR + str(iVar)])
            self.GetPort(SIG_PORT + str(iVar)).SetValue(result, CALCULATED_V)
        except:
            pass

        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(EquationUnit,self).AdjustOldCase(version)
        
        if version[0] < 10:
            if self.__dict__.has_key('_Funcs') and not self.__dict__.has_key('_FuncsDefs'):
                self._FuncsDefs = {}
                for k in self._Funcs.keys():
                    self._FuncsDefs[k] = self.GetParameterValue(k)
            
            
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(EquationUnit, self)._RemoveFromCloneList(clone, attrNamesToClone)
  
        dontClone = ["_Funcs", "_FuncsDefs"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone


class LookupTable(UnitOperations.UnitOperation):
    def __init__(self, initScript = None):
        super(LookupTable, self).__init__(initScript)
        # Signal port for table tag specifications
        # e.g. the pump speed
        extPort = self.CreatePort(SIG, SPEC_TAG_PORT)
        extPort.SetSignalType(GENERIC_VAR)        

        self._Tables = {}
        self.SetParameterValue(TABLETAGTYPE_PAR, GENERIC_VAR)
        self.SetParameterValue(NUMBSERIES_PAR, 0)
        self.SetParameterValue(NUMBTABLE_PAR, 0)
        
    def CleanUp(self):
        for t in self._Tables.values():
            t.CleanUp()
        self._Tables.clear()
        super(LookupTable, self).CleanUp()

    def GetObject(self, name):
        obj = UnitOperations.UnitOperation.GetObject(self, name)
        if not obj and self._Tables.has_key(name):
            obj = self._Tables[name]
        return obj

    def GetContents(self):
        result = super(LookupTable, self).GetContents()
        for key in self._Tables:
            result.append((key, self._Tables[key]))
        return result
    
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        super(LookupTable, self).SetParameterValue(paramName, value)
        if paramName == NUMBTABLE_PAR:
            self.SetTableCount()
        elif paramName == NUMBSERIES_PAR:
            self.SetSeriesCount()
        elif paramName == TABLETAGTYPE_PAR:
            self.SetTableTagType()
        elif paramName[:len(SERIESTYPE_PAR)] == SERIESTYPE_PAR:
            idx = long(paramName[len(SERIESTYPE_PAR):])
            self.SetSeriesTypes(idx)        

    def SetTableCount(self):
        n = self.GetParameterValue(NUMBTABLE_PAR)
        nTble = len(self._Tables)
        for i in range(nTble, n, -1):
            del self._Tables[TABLE_OBJ + str(i-1)]
        nSeries = self.GetParameterValue(NUMBSERIES_PAR)
        tagType = self.GetParameterValue(TABLETAGTYPE_PAR)
        typeName = self.GetParameterValue(TABLETAGTYPE_PAR)
        
        for i in range(nTble, n):
            self._Tables[TABLE_OBJ + str(i)] = ATable(typeName)
            self._Tables[TABLE_OBJ + str(i)].SetSeriesCount(nSeries)
            for idx in range(nSeries):
                typeName = self.GetParameterValue(SERIESTYPE_PAR + str(idx))                
                self._Tables[TABLE_OBJ + str(i)].SetSeriesType(idx, typeName)

    def Minus(self, idx):
        # remove table idx
        n = self.GetParameterValue(NUMBTABLE_PAR)
        if idx >= 0 and idx < n:
            delTbl = self._Tables[TABLE_OBJ + str(idx)]
            for i in range(idx, n-1):
                self._Tables[TABLE_OBJ + str(i)] = self._Tables[TABLE_OBJ + str(i+1)]
            self._Tables[TABLE_OBJ + str(n-1)] = delTbl
            self.SetParameterValue(NUMBTABLE_PAR, n-1)
            return 1
        else:
            return 0

    def GetTableCount(self): return len(self._Tables)
    
    def SetSeriesCount(self):
        nSeries = self.GetParameterValue(NUMBSERIES_PAR)
        # Notify all my tables
        for tblName in self._Tables.keys():
            tbl = self._Tables[tblName]
            tbl.SetSeriesCount(nSeries)

        # update series-count-dependent ports and parameters
        # For each series, there is a matching signal port (SignalN)
        # and two matching parameters (ExtrapolateN and SeriesTypeN)
        inPorts = self.GetNumberPorts(SIG)
        #if (inPorts > 0):
            #inPorts = (inPorts - 1) / 2
        inPorts -= 1 #one port is for the tag
        for i in range(inPorts, nSeries, -1):
            self.DeletePortNamed(SIG_PORT + str(i-1))
            if self.parameters.get(EXTRAPOLATE_PAR + str(i-1), None) != None:
                del self.parameters[EXTRAPOLATE_PAR + str(i-1)]
            if self.parameters.get(SERIESTYPE_PAR + str(i-1), None) != None:
                del self.parameters[SERIESTYPE_PAR + str(i-1)]
            
        for i in range(inPorts, nSeries):
            if self.GetPort(SIG_PORT + str(i)) == None:
                sigPort = self.CreatePort(SIG, SIG_PORT + str(i))
            # default is to allow extrapolation
            self.SetParameterValue(EXTRAPOLATE_PAR + str(i), 1.0)
            self.SetParameterValue(SERIESTYPE_PAR + str(i), GENERIC_VAR)
 
    def SetSeriesTypes(self, idx):
        nSeries = self.GetParameterValue(NUMBSERIES_PAR)
        typeName = self.GetParameterValue(SERIESTYPE_PAR + str(idx))
        if (typeName == None): return
        # set the signal type of my signal port (required for inconsistency check)
        self.GetPort(SIG_PORT + str(idx)).SetSignalType(typeName)
        # tha series themself also keep the datatype for unit conversion
        for tblName in self._Tables.keys():
            self._Tables[tblName].SetSeriesType(idx, typeName)    

    def SetTableTagType(self):
        typeName = self.GetParameterValue(TABLETAGTYPE_PAR)
        for tblName in self._Tables.keys():
            tbl = self._Tables[tblName]
            tbl.SetTagType(typeName)

    def LookupFromTable(self, tble0, tble1 = None, factor = 0.0):
        # Factor is to faciltate interpolation between tables
        # it is the factor between the existing value and the new value
        nSeries = self.GetParameterValue(NUMBSERIES_PAR)
        if (tble0 == None): return

        # search for first availeble value for lookup
        # search for the last lookup value first
        fromIdx = None
        rSeries = range(nSeries)
        iSeries = self.lookupFromPort
        if iSeries and iSeries < nSeries:
            rSeries[0] = iSeries
            rSeries[iSeries] = 0
        
        for i in rSeries:
            port = self.GetPort(SIG_PORT + str(i))
            if (port != None):
                val = port.GetValue()
                if (val != None):
                    iSeries = i
                    fromIdx = tble0._Series[SERIES_OBJ + str(i)].GetDataIndex(val)
                    # When the series is missing, fromIdx = None
                    if (fromIdx != None):
                        if (tble1 != None):
                            fromIdx1 = tble1._Series[SERIES_OBJ + str(i)].GetDataIndex(val)
                        break;
        if (fromIdx == None): return

        # lookup the table
        self.lookupFromPort = iSeries
        for i in range(nSeries):
            if i == iSeries: continue
            allowExtrap = self.GetParameterValue(EXTRAPOLATE_PAR + str(i))
            val = tble0._Series[SERIES_OBJ + str(i)].GetDataValue(fromIdx, allowExtrap)
            if tble1 != None and factor != 0.0:                
                val1 = tble1._Series[SERIES_OBJ + str(i)].GetDataValue(fromIdx1, allowExtrap)
                if val != None and val1 != None:
                    val = (1.0 - factor) * val + factor * val1
            # When the series is missing, val = None
            if val != None:
                self.GetPort(SIG_PORT + str(i)).SetValue(val, CALCULATED_V)

    def Solve(self):
        if self.IsForgetting():
            self.lookupFromPort = None
            return
        n = self.GetParameterValue(NUMBTABLE_PAR)
        tagSpec = self.GetPort(SPEC_TAG_PORT).GetValue()
        if (n <= 0):
            return
        elif (tagSpec == None):
            # if i have more than one table, the tag value must be specified
            return
        elif (n == 1):
            tbl0 = self._Tables[TABLE_OBJ + '0']
            self.LookupFromTable(tbl0)
        else:
            # locate the 2 tables where their tag brackets the spec tag
            tbl0 = None
            tbl1 = None
            for tblName in self._Tables.keys():
                tbl = self._Tables[tblName]
                #ignore tables with no series
                if tbl.GetLen() > 0:
                    diff = tbl.TagValue() - tagSpec
                    if (diff <= 0):
                        if (tbl0 == None or diff  > tbl0.TagValue() - tagSpec):
                            tbl0 = tbl
                    if (diff >= 0):
                        if (tbl1 == None or diff < tbl1.TagValue() - tagSpec):
                            tbl1 = tbl
            if (tbl1 == None):
                self.LookupFromTable(tbl0)
            elif (tbl0 == None):
                self.LookupFromTable(tbl1)
            elif (tbl1 == tbl0):
                self.LookupFromTable(tbl1)
            else:
                factor = (tagSpec - tbl0.TagValue()) / (tbl1.TagValue() - tbl0.TagValue())
                self.LookupFromTable(tbl0, tbl1, factor)
                 
                
    #def _CloneParameters(self, clone, attrNamesToClone):
        ##Clone parameters
        #for paramName in self.parameters:
            ##Do a copy just in case
            
            #if paramName == NUMBTABLE_PAR or paramName[:len(EXTRAPOLATE_PAR)] == EXTRAPOLATE_PAR or\
               #paramName[:len(SERIESTYPE_PAR)] == SERIESTYPE_PAR:
                ##Don't set these parameters, just make sure their values are identical
                #clone.parameters[paramName] = self.parameters[paramName]
            #else:
                #clone.SetParameterValue(paramName, copy.deepcopy(self.parameters[paramName]))
            
        #for paramName in self.parameterPropertyTypes:
            ##Can safely point to the same thing as they are global types
            #clone.parameterPropertyTypes[paramName] = self.parameterPropertyTypes[paramName]
            
        #if "parameters" in attrNamesToClone: attrNamesToClone.remove("parameters")
        #if "parameterPropertyTypes" in attrNamesToClone: attrNamesToClone.remove("parameterPropertyTypes") 
        
        #return attrNamesToClone
    

class IdealPump(UnitOperations.UnitOperation):
    """Isentropic pump"""
    def __init__(self, initScript = None):
        """
        Just do balance and conserve entropy
        isCompressor determines energy flow direction
        """          
        super(IdealPump, self).__init__(initScript)

        self.balance = Balance.Balance(Balance.MOLE_BALANCE | Balance.ENERGY_BALANCE)
        self.lastPIn = None
        self.lastPOut = None
        
        inPort = self.CreatePort(MAT|IN, IN_PORT)
        outPort = self.CreatePort(MAT|OUT, OUT_PORT)

        dpPort = self.CreatePort(SIG, DELTAP_PORT)
        dpPort.SetSignalType(DELTAP_VAR)        
                
        qPort = self.CreatePort(ENE|IN, IN_PORT + 'Q')
        self.balance.AddInput((inPort, qPort))
        self.balance.AddOutput(outPort)

        self.SetParameterValue(ISENTROPIC_PAR, 1)
        
    def CleanUp(self):
        self.balance.CleanUp()
        super(IdealPump, self).CleanUp()

    def GetListOfReqParam(self): return (ISENTROPIC_PAR,)
    
    def Solve(self):
        """Solve"""
        
        ## if not self.ValidateOk(): return None
        self.FlashAllPorts()  # make sure anything that can be flashed has been

        inport = self.GetPort(IN_PORT)
        outport = self.GetPort(OUT_PORT)

        #Only do the sharing for flows different to 0
        if inport.GetPropValue(MOLEFLOW_VAR) != 0.0 and outport.GetPropValue(MOLEFLOW_VAR) != 0.0:
            if self.GetParameterValue(ISENTROPIC_PAR) == 1:        
                inport.SharePropWith(outport, S_VAR)
            elif self.GetParameterValue(ISENTROPIC_PAR) == -1:
                inport.SharePropWith(outport, H_VAR)
                            
        self.balance.DoBalance()
        while self.FlashAllPorts():
            self.balance.DoBalance()

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
                min, max = PIn.GetValue(), 10.0*PIn.GetValue()
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
                min, max = POut.GetValue()/10.0, POut.GetValue()
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

        if pOut == None:
                if dp != None and pIn != None:
                        outport.SetPropValue(P_VAR, pIn + dp, CALCULATED_V)
        elif pIn == None:
                if dp != None:
                        inport.SetPropValue(P_VAR, pOut - dp, CALCULATED_V)               
        else:
                dpPort.SetPropValue(DELTAP_VAR, pOut - pIn, CALCULATED_V)

        return 1

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(IdealPump,self).AdjustOldCase(version)
        
        if version[0] < 11:
            #First make sure it is not there already
            dpPort = self.GetPort(DELTAP_PORT)
            if not dpPort:
                dpPort = self.CreatePort(SIG, DELTAP_PORT)
                dpPort.SetSignalType(DELTAP_VAR)
            
            inPort, outPort = self.GetPort(IN_PORT), self.GetPort(OUT_PORT)
            pIn, pOut = inPort.GetPropValue(P_VAR), outPort.GetPropValue(P_VAR)
            
            if pIn != None and pOut != None:
                dpPort.SetPropValue(DELTAP_VAR, (pOut - pIn), CALCULATED_V)



class Pump(UnitOperations.UnitOperation):
    """
    Adiabatic pump made from ideal pump, set and heater
    """
    
    def __init__(self, initScript=None):
        """Init pump - build it from Idealpump,
        Heater and Set operations
        """
        super(Pump, self).__init__(initScript)
        
        # the isentropic compressor
        self.ideal = IdealPump()
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
        self.BorrowChildPort(self.effStream.GetPort(IN_PORT), EFFICIENCY_PORT)
        self.BorrowChildPort(self.ideal.GetPort(DELTAP_PORT), DELTAP_PORT)
        
        #Change the type of the energy port such that it is in Work units and scaling
        self.totalQ.GetPort(IN_PORT).GetProperty().SetTypeByName(WORK_VAR)

    def CleanUp(self):
        # the isentropic compressor
        self.ideal = self.waste = self.idealQ = None
        self.wasteQ = self.totalQ = self.effStream = None
        self.set = self.mix = None
        super(Pump, self).CleanUp()

    def GetListOfReqParam(self): return (ISENTROPIC_PAR,)

    def Solve(self):
        super(Pump, self).Solve()
        
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)
        sPort = self.ideal.GetPort(OUT_PORT)
        mf = inPort.GetPropValue(MOLEFLOW_VAR)
        
        
        self._thCaseObj = self.GetThermo()
        
        if not self._thCaseObj:
            return
        
        inFlashed = inPort.AlreadyFlashed()
        outFlashed = outPort.AlreadyFlashed()
        sFlashed = sPort.AlreadyFlashed()        
        
        if mf == None:
            if inFlashed and sFlashed:
                self.SolveForMoleFlow(inPort, outPort, sPort)
                
        if not inFlashed and outFlashed:
            self.SolveForInlet(inPort, outPort, sPort)
            
            
    def SolveForInlet(self, inPort, outPort, sPort):
        
        h1 = outPort.GetPropValue(H_VAR)
        p1 = outPort.GetPropValue(P_VAR)
        
        p0 = inPort.GetPropValue(P_VAR)
        mf = inPort.GetPropValue(MOLEFLOW_VAR)
        fracs = inPort.GetCompositionValues()
        
        isEff = self.GetPort(EFFICIENCY_PORT).GetValue()
        
        if None in (h1, p1, p0, mf, isEff) or (fracs == None) or (None in fracs):
            return
        
        #Initialize h0
        h0 = h1
        
        dhTerm = (h1 - h0)*isEff
        maxIter = 30
        iter = 0
        converged = 0
        scale = 1000.0
        tolerance = 1.0E-6
        shift = 1.0
        maxStep = 5000.0
        while not converged and iter < maxIter:
            iter += 1
            
            s0 = self.GetPropertiesPH(p0, h0, fracs, (S_VAR,))[0]
            hs = self.GetPropertiesPS(p1, s0, fracs, (H_VAR,))[0]
            
            err = hs - ((h1 - h0)*isEff + h0)
            err /= scale
            
            #Leave if converged
            if abs(err) <= tolerance:
                converged = 1
                break
            
            #Calculate crude derivative
            h0Temp = h0 + shift
            s0 = self.GetPropertiesPH(p0, h0Temp, fracs, (S_VAR,))[0]
            hs = self.GetPropertiesPS(p1, s0, fracs, (H_VAR,))[0]
            
            errTemp = hs - ((h1 - h0Temp)*isEff + h0Temp)
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
            
            
            
    def GetPropertiesPH(self, p, h, fracs, props, phase=OVERALL_PHASE):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        nuSolids = self.NumberSolidPhases()
        if not nuSolids:
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
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, props, nuSolids=nuSolids)
            vals = results.bulkProps
            
        return vals
            
    def GetPropertiesPS(self, p, s, fracs, props, phase=OVERALL_PHASE):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        nuSolids = self.NumberSolidPhases()
        if not nuSolids:
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
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, props, nuSolids=nuSolids)
            vals = results.bulkProps    
        return vals
    
    def SolveForMoleFlow(self, inPort, outPort, sPort):
        """solve for mole flow"""
          
        h0 = inPort.GetPropValue(H_VAR)                 #kJ/kmol
        hs = sPort.GetPropValue(H_VAR)                  #kJ/kmol
        
        if h0 == None or hs == None:
            return
        
        isEff = self.GetPort(EFFICIENCY_PORT).GetValue()
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
        
        
                
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        UnitOperations.UnitOperation.SetParameterValue(self, paramName, value)
        if paramName == ISENTROPIC_PAR:
            if (self.ideal != None):
                self.ideal.SetParameterValue(paramName, value)


    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(Pump, self).AdjustOldCase(version)


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
            

class IsenthalpicPump(Pump):
    """ Basic building block for pumpWithCurve """
    def __init__(self, initScript=None):
        super(IsenthalpicPump, self).__init__(initScript)
        self.SetParameterValue(ISENTROPIC_PAR, -1)
        

class PumpWithCurve(UnitOperations.UnitOperation):

    def __init__(self, initScript=None):
        # A pump
        # with pump curves, do not preserve entropy
        super(PumpWithCurve, self).__init__(initScript)

        self.HPump = Pump()
        self.HPump.SetParameterValue(ISENTROPIC_PAR, 1)
        self.AddUnitOperation(self.HPump, 'IsenthalpicPump')

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
        # with 3 series: mass flow, head, efficiency
        self.LookupTable = LookupTable()
        self.AddUnitOperation(self.LookupTable, 'LookupTable')
        self.LookupTable.SetParameterValue(NUMBSERIES_PAR, 4)           # 4 series: mass flow, head, efficiency and power
        self.LookupTable.SetParameterValue(EXTRAPOLATE_PAR + str(2), 0) # do not extrapolate efficiency
        self.LookupTable.SetParameterValue(SERIESTYPE_PAR + str(0), VOLFLOW_VAR)
        self.LookupTable.SetParameterValue(SERIESTYPE_PAR + str(1), LENGTH_VAR)
        self.LookupTable.SetParameterValue(SERIESTYPE_PAR + str(3), ENERGY_VAR) # actually power
        
        self.LookupTable.SetParameterValue(TABLETAGTYPE_PAR, GENERIC_VAR)  # i do not yet has a RPM

        # A flow sensor
        self.FlowSensor = Sensor.PropertySensor()
        self.AddUnitOperation(self.FlowSensor, 'FlowSensor')
        self.FlowSensor.SetParameterValue(SIGTYPE_PAR, VOLFLOW_VAR)

        # An equation unit to convert the head to delP
        # delP = MW * 0.00981 * head / molarVol
        # Note cannot back out mass density from head and delta pressure
        self.CalcDelP = EquationUnit()
        self.AddUnitOperation(self.CalcDelP, 'CalcDelP')
        self.CalcDelP.SetParameterValue(NUMBSIG_PAR, 4)
        self.CalcDelP.SetParameterValue(TRANSFORM_EQT_PAR + str(0), 'x[1]*x[3]/0.00981/x[2]')
        self.CalcDelP.SetParameterValue(TRANSFORM_EQT_PAR + str(1), 'x[0]*x[2]*0.00981/x[3]')
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
        self.ConnectPorts('InPSensor', OUT_PORT,              'IsenthalpicPump', IN_PORT)
#        self.ConnectPorts('IsenthalpicPump', EFFICIENCY_PORT, 'LookupTable', SIG_PORT + '2')
        self.ConnectPorts('IsenthalpicPump', IN_PORT + 'Q',   'TotalQ', OUT_PORT)
        self.ConnectPorts('IsenthalpicPump', OUT_PORT,        'OutPSensor', IN_PORT)
        
        self.ConnectPorts('InPSensor',  SIG_PORT, 'SetP', SIG_PORT + '0')
        self.ConnectPorts('OutPSensor', SIG_PORT, 'SetP', SIG_PORT + '1')
        self.ConnectPorts('FlowSensor', SIG_PORT, 'LookupTable', SIG_PORT + '0')

        self.ConnectPorts('TotalQ',   SIG_PORT,       'LookupTable', SIG_PORT + '3')
#        self.ConnectPorts('CalcDelP', SIG_PORT + '0', 'LookupTable', SIG_PORT + '1')
        self.ConnectPorts('CalcDelP', SIG_PORT + '1', 'SetP', Set.ADD_PORT)
        self.ConnectPorts('CalcDelP', SIG_PORT + '2', 'MWSensor', SIG_PORT)
        self.ConnectPorts('CalcDelP', SIG_PORT + '3', 'MolarVolSensor', SIG_PORT)

        self.BorrowChildPort(self.TotalQ.GetPort(IN_PORT), IN_PORT + 'Q')
        self.BorrowChildPort(self.OutPSensor.GetPort(OUT_PORT), OUT_PORT)
        self.BorrowChildPort(self.FlowSensor.GetPort(IN_PORT), IN_PORT)
        self.BorrowChildPort(self.LookupTable.GetPort(SPEC_TAG_PORT), PUMPSPEED_PORT)
        self.BorrowChildPort(self.HPump.GetPort(DELTAP_PORT), DELTAP_PORT)
        
        #Change the type of the energy port such that it is in Work units and scaling
        self.TotalQ.GetPort(IN_PORT).GetProperty().SetTypeByName(WORK_VAR)

        # clone and borrow the lookuptable's efficiency port
        self.effStream = Stream.Stream_Signal()
        self.effStream.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        self.AddUnitOperation(self.effStream, 'EfficiencySig')
        effClone = Stream.ClonePort()
        self.effStream.AddObject(effClone, 'effClone')
        self.ConnectPorts('EfficiencySig', IN_PORT, 'LookupTable', SIG_PORT + '2')
        self.ConnectPorts('EfficiencySig', OUT_PORT, 'IsenthalpicPump', EFFICIENCY_PORT)        
        self.BorrowChildPort(self.effStream.GetPort('effClone'), EFFICIENCY_PORT)
        
        # clone and borrow the lookuptable's head port
        self.headStream = Stream.Stream_Signal()
        self.headStream.SetParameterValue(SIGTYPE_PAR, LENGTH_VAR)
        self.AddUnitOperation(self.headStream, 'HeadSig')
        headClone = Stream.ClonePort()
        self.headStream.AddObject(headClone, 'headClone')
        self.ConnectPorts('HeadSig', IN_PORT, 'LookupTable', SIG_PORT + '1')
        self.ConnectPorts('HeadSig', OUT_PORT, 'CalcDelP', SIG_PORT + '0')        
        self.BorrowChildPort(self.headStream.GetPort('headClone'), HEAD_PORT)

        # parameters
        #default: no pump curve
        self.SetParameterValue(NUMBTABLE_PAR, 0)
        
    def CleanUp(self):
        self.HPump = self.InPSensor = self.OutPSensor = None        
        self.SetP = self.LookupTable = self.FlowSensor = None
        self.CalcDelP = self.MolarVolSensor = self.MWSensor = None
        self.TotalQ = self.effStream = self.headStream = None
        super(PumpWithCurve, self).CleanUp()

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(PumpWithCurve,self).AdjustOldCase(version)
        
        if version[0] < 12:
            newPort = self.GetPort(DELTAP_PORT)
            if not newPort:
                # Borrow the deltaP port
                self.BorrowChildPort(self.HPump.GetPort(DELTAP_PORT), DELTAP_PORT)
                
            newPort = self.GetPort(EFFICIENCY_PORT)
            if not newPort:
                # insert a signal stream between the 'LookupTable.SIG_PORT2' and IsenthalpicPump.EFFICIENCY_PORT
                # first break the old connection
                self.DisconnectPort('IsenthalpicPump', EFFICIENCY_PORT)
                # create the in-between signal stream and re-connect
                self.effStream = Stream.Stream_Signal()
                self.effStream.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
                self.AddUnitOperation(self.effStream, 'EfficiencySig')
                effClone = Stream.ClonePort()
                self.effStream.AddObject(effClone, 'effClone')
                self.ConnectPorts('EfficiencySig', IN_PORT, 'LookupTable', SIG_PORT + '2')
                self.ConnectPorts('EfficiencySig', OUT_PORT, 'IsenthalpicPump', EFFICIENCY_PORT)        
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
                
    def GetObject(self, name):
        # shortcut to access the pump curves
        # pumpWithCurve.EfficiencyCurveX vs pumpWithCurve.LookupTable.TableX.Series2
        # where X is the curve table
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
            elif name[:len(PUMPSPEED_PORT)] == PUMPSPEED_PORT:
                idx = name[len(PUMPSPEED_PORT):]
                tbl = self.LookupTable.GetObject(TABLE_OBJ + idx)
                if tbl:
                    obj = tbl.GetObject(TABLETAG_VAR)
        return obj

    def GetContents(self):
        result = super(PumpWithCurve, self).GetContents()
        #result.append(('LookupTable', self.LookupTable))
        for i in range(self.LookupTable.GetTableCount()):
            tbl = self.LookupTable.GetObject(TABLE_OBJ + str(i))
            result.append(('%s%d' % (FLOW_SERIES, i), tbl.GetObject(SERIES_OBJ + str(0))))
            result.append(('%s%d' % (HEAD_SERIES, i), tbl.GetObject(SERIES_OBJ + str(1))))
            result.append(('%s%d' % (EFFICIENCY_SERIES, i), tbl.GetObject(SERIES_OBJ + str(2))))
            result.append(('%s%d' % (POWER_SERIES, i), tbl.GetObject(SERIES_OBJ + str(3))))
            result.append(('%s%d' % (PUMPSPEED_PORT, i), tbl.GetObject(TABLETAG_VAR)))
        return result
        
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        if paramName == NUMBTABLE_PAR:
            UnitOperations.UnitOperation.SetParameterValue(self, paramName, value)
            self.LookupTable.SetParameterValue(paramName, value)

        if paramName == IGNORECURVE_PAR:            
            #...ignore the lookuptable and remove any specifications
            if value == 'None': value = None
            self.LookupTable.SetParameterValue(IGNORED_PAR, value)
            if value:
                port = self.GetPort(HEAD_PORT)
                port.SetValue(None, FIXED_V)               
        else:
            UnitOperations.UnitOperation.SetParameterValue(self, paramName, value)
        
            
             

    def Minus(self, varName):
        # remove a pump curve
        if varName[:len(PUMPCURVE_OBJ)] == PUMPCURVE_OBJ:
            try:
                idx = int(varName[len(PUMPCURVE_OBJ):])
                if self.LookupTable.Minus(idx):
                    n = self.LookupTable.GetParameterValue(NUMBTABLE_PAR)
                    self.SetParameterValue(NUMBTABLE_PAR, n)
            except:
                pass
        
        
        
    
