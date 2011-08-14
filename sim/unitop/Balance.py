"""Heat and material (mole or mass) balance class(es)"""

from sim.solver import Ports, Error
from sim.solver.Variables import *
import numpy.oldnumeric
from numpy.oldnumeric import array, Float, Int, ones, zeros, matrixmultiply
from LinearAlgebra import solve_linear_equations, determinant
import UnitOperations

MASS_BALANCE = 1
MOLE_BALANCE = 2
ENERGY_BALANCE = 4

S_MAT = 'Mat'
S_ENE = 'Ene'
BALANCETYPE_PAR = 'BalanceType'

class Balance:
    def __init__(self, type):
        self.type = type
        self._eneIn = []
        self._eneOut = []
        self._matIn = []
        self._matOut = []

    def CleanUp(self):
        self._eneIn = []
        self._eneOut = []
        self._matIn = []
        self._matOut = []
        
    def _AddInputByType(self, port):
        """use isinstance to determine what input list to add port to"""
        if isinstance(port, Ports.Port_Energy):
            self._eneIn.append(port)
        elif isinstance(port, Ports.Port_Material):
            self._matIn.append(port)
        else:
            raise Errors.SimError("BalanceInvalidPort")

    def _AddOutputByType(self, port):
        """use isinstance to determine what output list to add port to"""
        if isinstance(port, Ports.Port_Energy):
            self._eneOut.append(port)
        elif isinstance(port, Ports.Port_Material):
            self._matOut.append(port)
        else:
            raise Errors.SimError("BalanceInvalidPort")
        
    def AddInput(self, ports):
        """add material or energy ports to input list.
        ports can either be a single port or a sequence of ports"""
        if isinstance(ports, Ports.Port):
            # just a single value
            self._AddInputByType(ports)
        elif ports != None:
            for port in ports:
                self._AddInputByType(port)

    def AddOutput(self, ports):
        """add material or energy ports to output list.
        ports can either be a single port or a sequence of ports"""
        if isinstance(ports, Ports.Port):
            # just a single value
            self._AddOutputByType(ports)
        elif ports != None:
            for port in ports:
                self._AddOutputByType(port)
   
    def DoBalance(self, calcStatus=CALCULATED_V):
        """perform the actual balance.
        Use calcStatus as the status flag for set value calls"""
       
        if self.type & MASS_BALANCE:
            self.DoMassBalance(calcStatus)

        if self.type & ENERGY_BALANCE:
            self.DoEnergyBalance(calcStatus)
            
        if self.type & MOLE_BALANCE:
            self.DoMassBalance(calcStatus)  # if it mole balances, it must mass balance
            molBal = self.DoMoleBalance(self.type & ENERGY_BALANCE, calcStatus)
            if self.type & ENERGY_BALANCE:
                self.DoEnergyBalance(calcStatus)
            
            if not molBal:
                try:
                    #Attempt a voluma balance
                    volBal = self.DoVolBalance(calcStatus)
                    if volBal:
                        self.DoEnergyBalance(calcStatus)
                except:
                    pass
                
    def DoMassBalance(self, calcStatus=CALCULATED_V):
        """perform mass balance 
        composition is not necessarily preserved.
        """
        balanced = 0
        
        if len(self._matIn): aPort = self._matIn[0]
        elif len(self._matOut): aPort = self._matOut[0]
        else: 
            balanced = 1
            return balanced

        missing = None
        sum = 0.0

        # do inlets
        for port in self._matIn:
            flow = port.GetLocalValue(MASSFLOW_VAR)
            if flow == None:
                if missing != None:
                    return balanced # don't know enough to do anything
                missing = port
                missingInlet = 1
            else:
                sum += flow
                
        # now the outlets
        for port in self._matOut:
            flow = port.GetLocalValue(MASSFLOW_VAR)
            if flow == None:
                if missing != None:
                    return balanced # don't know enough to do anything
                missing = port
                missingInlet = 0
            else:
                sum -= flow
                
        if missing:
            if missingInlet:
                sum = -sum
            missing.SetPropValue(MASSFLOW_VAR, sum, calcStatus)
            missing.CalcFlows()
        elif aPort:
            scaleFactor = PropTypes[MASSFLOW_VAR].scaleFactor
            if scaleFactor:
                tolerance = aPort.GetParentOp().GetTolerance()
                if abs(sum)/scaleFactor > tolerance:
                    prop = aPort.GetProperty(MASSFLOW_VAR)
                    aPort.GetParentOp().PushConsistencyError(prop, sum)

        #If it made it all the way here, then  it must be balanced
        balanced = 1
        return balanced
                    
    def DoEnergyBalance(self, calcStatus=CALCULATED_V):
        """
        perform energy balance
        """
        
        missing = None
        sum = 0.0
        inlets = self._matIn + self._eneIn
        outlets = self._matOut + self._eneOut
        balanced = 0
        
        if len(inlets): aPort = inlets[0]
        elif len(outlets): aPort = outlets[0]
        else: 
            balanced = 1
            return balanced

        # do inlets
        for port in inlets:
            flow = port.GetLocalValue(ENERGY_VAR)
            if flow == None:
                if missing != None:
                    return balanced # don't know enough to do anything
                missing = port
                missingInlet = 1
            else:
                sum += flow
                
        # now the outlets
        for port in outlets:
            flow = port.GetLocalValue(ENERGY_VAR)
            if flow == None:
                if missing != None:
                    return balanced # don't know enough to do anything
                missing = port
                missingInlet = 0
            else:
                sum -= flow
                
        if missing:
            if missingInlet:
                sum = -sum
            missing.SetPropValue(ENERGY_VAR, sum, calcStatus)
        elif aPort:
            scaleFactor = PropTypes[ENERGY_VAR].scaleFactor
            if scaleFactor:
                tolerance = aPort.GetParentOp().GetTolerance()
                if abs(sum)/scaleFactor > tolerance:
                    prop = aPort.GetProperty(ENERGY_VAR)
                    aPort.GetParentOp().PushConsistencyError(prop, sum)
                    
        #If it made it all the way here, then  it must be balanced
        balanced = 1
        return balanced
                    
                    
    def DoMoleBalance(self, canUseEnth, calcStatus):
        """do a balance on the stream components.
        If canUseEnth is true enthalpy balances may be used to try and
        determine mole flows
        """
        missing = []   # port missing port array (port, inletFlag)
        sum = 0.0
        nuPortsIn = len(self._matIn)
        nuPortsOut = len(self._matOut)
        totPorts = nuPortsIn + nuPortsOut
        balanced = 0
        
        if totPorts == 1: 
            balanced = 1
            return balanced
        
        if nuPortsIn: aPort = self._matIn[0]
        elif nuPortsOut: aPort = self._matOut[0]
        else: 
            balanced = 1
            return balanced

        scaleFactor = PropTypes[MOLEFLOW_VAR].scaleFactor
        tolerance = aPort.GetParentOp().GetTolerance()
        
        # do outlets
        allMatOutAreZero = 1
        for port in self._matOut:
            flow = port.GetPropValue(MOLEFLOW_VAR)
            if flow == None:
                missing.append((port,0))
                allMatOutAreZero = 0
            else:
                sum -= flow
                if allMatOutAreZero:
                    if abs(flow)/scaleFactor >= tolerance:
                        allMatOutAreZero = 0
                        #This makes sure that aPort is not a zero flow
                        aPort = port
        
        # do inlets
        allMatInAreZero = 1
        for port in self._matIn:
            flow = port.GetPropValue(MOLEFLOW_VAR)
            if flow == None:
                missing.append((port,1))
                allMatInAreZero = 0
            else:
                sum += flow
                if allMatInAreZero:
                    if abs(flow)/scaleFactor >= tolerance:
                        allMatInAreZero = 0
                        #This makes sure that aPort is not a zero flow
                        aPort = port               
                

        #Mmmhh, Always check if H and composition can be shared
        if totPorts == 2:
            myPortLst = self._matIn + self._matOut
            for i in range(len(myPortLst)-1):
                myPortLst[i].ShareComposition(myPortLst[i+1])
                
            if canUseEnth:
                allEneAreZero = 1
                eneScaleFactor = PropTypes[ENERGY_VAR].scaleFactor
                for eneP in self._eneIn + self._eneOut:
                    eneFlow = eneP.GetPropValue(ENERGY_VAR)
                    if eneFlow == None or eneFlow != 0.0:
                        allEneAreZero = 0
                        break
                if allEneAreZero:
                    for i in range(len(myPortLst)-1):
                        myPortLst[i].SharePropWith(myPortLst[i+1], H_VAR)

        nuMissing = len(missing)
        if nuMissing == 0:
            # all flows known, but do consistency check
            if aPort:
                if scaleFactor:
                    if abs(sum)/scaleFactor > tolerance:
                        prop = aPort.GetProperty(MOLEFLOW_VAR)
                        aPort.GetParentOp().PushConsistencyError(prop, sum)
                        
        elif nuMissing == 1:
            if missing[0][1]:
                sum = -sum
            missing[0][0].SetPropValue(MOLEFLOW_VAR, sum, calcStatus)
            missing[0][0].CalcFlows()
        else:  
            # more than 1 unknown
                
            # see if we can find as many knowns as unknowns
            # start with overall mole flow
            row = []
            a = [] # hold matrix
            b = [] # hold rhs
            for i in missing:
                if i[1]: row.append(1.0)
                else: row.append(-1.0)
            a.append(row)
            b.append(-sum)
            
            if canUseEnth:
                # see if all missing ports have enthalpies
                row = []
                for i in missing:
                    (port, isIn) = i
                    h = port.GetPropValue(H_VAR)
                    if h == None:
                        break  # need them all
                    if isIn: row.append(h)
                    else: row.append(-h)
                    
                if len(row) == nuMissing:
                    # see if we can get the nonmissing total
                    sumq = 0.0
                    nuMissingQ = 0
                    for port in self._matIn:
                        q = port.GetPropValue(ENERGY_VAR)
                        if q == None:
                            nuMissingQ += 1
                        else:
                            sumq -= q
                                
                    for port in self._matOut:
                        q = port.GetPropValue(ENERGY_VAR)
                        if q == None:
                            nuMissingQ += 1
                        else:
                            sumq += q
                            
                    for port in self._eneIn:
                        q = port.GetPropValue(ENERGY_VAR)
                        if q == None:
                            nuMissingQ += 1
                        else:
                            sumq -= q

                    for port in self._eneOut:
                        q = port.GetPropValue(ENERGY_VAR)
                        if q == None:
                            nuMissingQ += 1
                        else:
                            sumq += q
                            
                    if nuMissingQ == nuMissing:
                        # note conversion to W from KJ/hr and vice versa
                        b.append(sumq * 3.6)
                        a.append(row)
                        
            # look for mole fractions to use
            for cmpNo in range(len(aPort.GetCompounds())):
                if len(a) == nuMissing:
                    break  # have enough equations
                
                # see if all missing ports have mole fractions
                row = []
                for i in missing:
                    (port, isIn) = i
                    x = port.GetCompounds()[cmpNo].GetValue()
                    if x == None:
                        break  # need them all
                    if isIn: row.append(x)
                    else: row.append(-x)
                
                if len(row) != nuMissing:
                    continue
                sumN = 0.0
                nuMissingN = 0
                for port in self._matIn:
                    flow = port.GetPropValue(MOLEFLOW_VAR)
                    x = port.GetCompounds()[cmpNo].GetValue()
                    if flow == None or x == None:
                        nuMissingN += 1
                    else:
                        sumN -= x * flow
                            
                for port in self._matOut:
                    flow = port.GetPropValue(MOLEFLOW_VAR)
                    x = port.GetCompounds()[cmpNo].GetValue()
                    if flow == None or x == None:
                        nuMissingN += 1
                    else:
                        sumN += x * flow
                       
                if nuMissingN == nuMissing:
                    b.append(sumN)
                    a.append(row)
                        
                        
            if len(a) != nuMissing:
                return balanced # not enough info
            
            try:
                if abs(determinant(array(a))) < 0.0001:
                    return balanced
                
                flows = solve_linear_equations(array(a),array(b))
            except:
                return balanced
            
            for i in range(nuMissing):
                missing[i][0].SetPropValue(MOLEFLOW_VAR, flows[i], calcStatus)
                missing[i][0].CalcFlows()
                
        # flows are now known - do components
        cmps = aPort.GetCompounds()
        
        #iterate through components
        missing = None
        for cmpNo in range(len(cmps)):
            sum = 0.0
            # inlets
            for port in self._matIn:
                flow = port.GetPropValue(MOLEFLOW_VAR)
                if flow == None:
                    return balanced          # should not happen
                if flow != 0.0:
                    x = port.GetCompounds()[cmpNo].GetValue()
                    if x != None:
                        if missing and missing is port:
                            return  balanced # all components must be missing
                        sum += x * flow
                    elif missing and not port is missing:
                        return balanced      # all missing compositions must be in same port
                    else:
                        missing = port
                        missingInlet = 1

            # outlets
            for port in self._matOut:
                flow = port.GetPropValue(MOLEFLOW_VAR)
                if flow == None:
                    return balanced          # shouldn't happen

                if flow != 0.0:                    
                    x = port.GetCompounds()[cmpNo].GetValue()
                    if x != None:
                        if missing and missing is port:
                            return  balanced # all components must be missing
                        sum -= x * flow
                    elif missing and not port is missing:
                        return  balanced # all missing compositions must be in same port
                    else:
                        missing = port
                        missingInlet = 0
                   
            #It balanced
            if missing:
                flow = missing.GetPropValue(MOLEFLOW_VAR)
                if flow == 0:
                    return balanced
                if missingInlet:
                    sum = -sum
                missing.GetCompounds()[cmpNo].SetValue(sum/flow, calcStatus)
                missing.CalcFlows()
            else:
                flow = aPort.GetPropValue(MOLEFLOW_VAR)
                if flow == 0:
                    flow = 1000.0   # arbitrary scaling
                x = abs(sum)/flow
                
                scaleFactor = PropTypes[FRAC_VAR].scaleFactor
                if scaleFactor:
                    tolerance = aPort.GetParentOp().GetTolerance()
                    if x/scaleFactor > tolerance:
                        prop = aPort.GetCompounds()[cmpNo]
                        aPort.GetParentOp().PushConsistencyError(prop, x)
                
        #If it made it all the way here, then  it must be balanced
        balanced = 1
        return balanced
    
    def DoVolBalance(self, calcStatus=CALCULATED_V):
        """performs a volume or stdliqvolume balance 
        """
        balanced = 0
        
        if len(self._matIn): aPort = self._matIn[0]
        elif len(self._matOut): aPort = self._matOut[0]
        else: 
            balanced = 1
            return balanced

        #Keep track of std vol and vol and see which one can be solved for
        missingStdVol = None
        missingxStdVol = None
        sumStdVol = 0.0
        canDoStdVol = True
        
        missingVol = None
        missingxVol = None
        sumVol = 0.0
        canDoVol = True
        
        #Put all the mole flows in vectors
        moleFlows = []
        compositions = []
        signs = []
        enthalpies = []
        mode = None

        # do inlets
        for port in self._matIn:
            moleFlows.append(port.GetLocalValue(MOLEFLOW_VAR))
            enthalpies.append(port.GetLocalValue(H_VAR))
            x = port.GetCompositionValues()
            compositions.append(x)
            signs.append(1.0)
            if canDoStdVol:
                stdVolFlow = port.GetLocalValue(STDVOLFLOW_VAR)
                if stdVolFlow == None:
                    if missingStdVol != None:
                        # don't know enough to do anything
                        canDoStdVol = False
                    else:
                        #Must know composition in unknown stdvol
                        if x == None or None in x:
                            canDoStdVol = False
                    missingStdVol = port
                    missingInletStdVol = 1
                else:
                    sumStdVol += stdVolFlow
                    
                    #Keep track of which port is missing composition
                    if x == None or None in x:
                        if missingxStdVol:
                            #Can not be missing composition in more than one port
                            canDoStdVol = False
                        else:
                            missingxStdVol = port
                
            if canDoVol:
                volFlow = port.GetLocalValue(VOLFLOW_VAR)
                if volFlow == None:
                    if missingVol != None:
                        # don't know enough to do anything
                        canDoVol = False
                    else:
                        #Must know composition in unknown stdvol
                        if x == None or None in x:
                            canDoVol = False
                    missingVol = port
                    missingInletVol = 1
                else:
                    sumVol += volFlow
                    
                    #Keep track of which port is missing composition
                    if x == None or None in x:
                        if missingxVol:
                            #Can not be missing composition in more than one port
                            canDoVol = False
                        else:
                            missingxVol = port
                    
            if not canDoStdVol and not canDoVol:
                return balanced #Nothing can be done
            
        # now the outlets
        for port in self._matOut:
            moleFlows.append(port.GetLocalValue(MOLEFLOW_VAR))
            enthalpies.append(port.GetLocalValue(H_VAR))
            x = port.GetCompositionValues()
            compositions.append(x)
            signs.append(-1.0)
            if canDoStdVol:
                stdVolFlow = port.GetLocalValue(STDVOLFLOW_VAR)
                if stdVolFlow == None:
                    if missingStdVol != None:
                        # don't know enough to do anything
                        canDoStdVol = False
                    else:
                        #Must know composition in unknown stdvol
                        if x == None or None in x:
                            canDoStdVol = False
                    missingStdVol = port
                    missingInletStdVol = 0
                else:
                    sumStdVol -= stdVolFlow
                    #Keep track of which port is missing composition
                    if x == None or None in x:
                        if missingxStdVol:
                            #Can not be missing composition in more than one port
                            canDoStdVol = False
                        else:
                            missingxStdVol = port
                    
            if canDoVol:
                volFlow = port.GetLocalValue(VOLFLOW_VAR)
                if volFlow == None:
                    if missingVol != None:
                        # don't know enough to do anything
                        canDoVol = False
                    else:
                        #Must know composition in unknown stdvol
                        if x == None or None in x:
                            canDoVol = False
                    missingVol = port
                    missingInletVol = 0
                else:
                    sumVol -= volFlow
                    #Keep track of which port is missing composition
                    if x == None or None in x:
                        if missingxVol:
                            #Can not be missing composition in more than one port
                            canDoVol = False
                        else:
                            missingxVol = port
                    
            if not canDoStdVol and not canDoVol:
                return balanced #Nothing can be done
                
                
        #Decide which balance can be done
        ##!!
        ##Starting here, the prefix vol will be used for vol and stdvol depending on the selected mode
        ##Use v to refer to the port that is missing the volume flow
        ##Use x to refer to the port that is missing the composition
        vPort = None
        xPort = None
        
        if canDoStdVol:
            mode = STDVOLFLOW_VAR
            vPort = missingStdVol
            vInlet = missingInletStdVol
            xPort = missingxStdVol
            sum = sumStdVol
            vMolVol = vPort.GetPropValue(STDLIQVOL_VAR)
            xVolFlow = xPort.GetPropValue(STDVOLFLOW_VAR)
        elif canDoVol:
            mode = VOLFLOW_VAR
            vPort = missingVol
            vInlet = missingInletVol
            xPort = missingxVol
            sum = sumVol
            vMolVol = vPort.GetPropValue(MOLARV_VAR)
            xVolFlow = xPort.GetPropValue(VOLFLOW_VAR)
        else:
            return balanced
        
        #Don't solve if already fully specified. Let the other balances
        #check for consistency errors
        if vPort == None or xPort == None:
            balanced = 1
            return balanced
        
        #Find the indexes of the ports with the missing info
        vIdx = None
        xIdx = None
        cnt = 0
        for port in self._matIn + self._matOut:
            if port is vPort:
                vIdx = cnt
            if port is xPort:
                xIdx = cnt
            cnt += 1
        if vIdx == None or xIdx == None:
            return balanced
        
        #Get some thermo info
        parentOp = xPort._parentOp
        if parentOp == None: return balanced
        thCaseObj = parentOp.GetThermo()
        if thCaseObj == None: return balanced
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        refT = parentOp.GetStdVolRefT()
                
        #Rearange the information in vectors
        if vMolVol == None:
            if mode == STDVOLFLOW_VAR:
                vMolVol = thAdmin.GetArrayProperty(prov, case, (P_VAR, 101.325), (T_VAR, refT), 
                                                   LIQUID_PHASE, array(compositions[vIdx], Float), 
                                                   STDLIQMOLVOLPERCMP_VAR)
                if vMolVol == None: return balanced
                vMolVol = Numeric.sum(array(compositions[vIdx], Float)*vMolVol)
            if vMolVol == None: 
                return balanced
        
        #Remove info from port with missing composition
        xH = enthalpies[xIdx]
        vH = enthalpies[vIdx]
        xT = None
        xSign = signs[xIdx]
        del moleFlows[xIdx]
        del compositions[xIdx]
        del signs[xIdx]
        del enthalpies[xIdx]
        if vIdx > xIdx:
            vIdx -= 1
            
        #Estimate a mole flow and convert arrays to Numeric array
        if vInlet:
            sum = -sum
        vVolFlow = sum
        vMoleFlow = vVolFlow / vMolVol
        moleFlows[vIdx] = vMoleFlow
        try:
            moleFlows = array(moleFlows, Float)
        except:
            return balanced
        compositions = array(compositions, Float)
        signs = array(signs, Float)
        
        if mode == VOLFLOW_VAR:
            xP = xPort.GetPropValue(P_VAR)
            if xP == None: return balanced
            nuSolids = parentOp.NumberSolidPhases()
            propsDict = MaterialPropertyDict()
            xList = CompoundList(None)
            for val in compositions[0]:
                xList.append(BasicProperty(FRAC_VAR))
            if vH == None:
                #If enthalpy here is not known, then we should either know T or H in the port
                #that is missing the composition
                if xH == None:
                    xT = xPort.GetPropValue(T_VAR)
                    if xT == None:
                        return balanced
            else:
                enthalpies = array(enthalpies, Float)
        
        #Preapre to iterate
        maxIter = 20
        iter = 0
        converged = False
        scaleFactor = PropTypes[MOLEFLOW_VAR].scaleFactor
        tolerance = 1.0E-6
        errorOld = None
        while not converged and iter < maxIter:
            iter += 1
            moleFlows[vIdx] = vMoleFlow
            
            xMoleFlows = matrixmultiply(moleFlows*signs, compositions)
            if xSign > 0.0:
                xMoleFlows *= -1.0
            xMoleFlow = Numeric.sum(xMoleFlows)
            x = xMoleFlows/xMoleFlow
            
            if mode == STDVOLFLOW_VAR:
                xMolVol = thAdmin.GetArrayProperty(prov, case, (P_VAR, 101.325), (T_VAR, refT), LIQUID_PHASE, x, STDLIQMOLVOLPERCMP_VAR)
                if xMolVol == None: return balanced
                xMolVol = Numeric.sum(x*xMolVol)
            else:
                propsDict[P_VAR].SetValue(xP, FIXED_V)
                if xT != None:
                    #Use the T if known
                    propsDict[T_VAR].SetValue(xT, FIXED_V)
                else:
                    #Do energy balance and backcalculate xH
                    xH = Numeric.sum(moleFlows * signs * enthalpies) / xMoleFlow
                    if xSign > 0.0:
                        xH *= -1.0
                    propsDict[H_VAR].SetValue(xH, FIXED_V)
                for i in range(len(x)):
                    xList[i].SetValue(x[i], FIXED_V)
                results = thAdmin.Flash(prov, case, xList, propsDict, 2, (MOLARV_VAR,), nuSolids=nuSolids)
                xMolVol = results.bulkProps[0] 
                
            xMoleFlowTest = xVolFlow / xMolVol
            error = abs(xMoleFlow - xMoleFlowTest) / scaleFactor
            if error < tolerance:
                converged = True
                break
            
            #Do a regula falsi
            if errorOld == None:
                #Make up a reasonable step
                vMoleFlowNew = vMoleFlow + (xMoleFlow - xMoleFlowTest)*0.5
            else:
                #Update
                dy_dx = (error - errorOld) / (vMoleFlow - vMoleFlowOld)
                vMoleFlowNew = vMoleFlow - error/dy_dx
            #Keep track of old values
            vMoleFlowOld = vMoleFlow
            vMoleFlow = vMoleFlowNew
            errorOld = error
            
        if converged:
            vPort.SetPropValue(MOLEFLOW_VAR, vMoleFlow, calcStatus)
            xPort.SetPropValue(MOLEFLOW_VAR, xMoleFlow, calcStatus)
            xPort.SetCompositionValues(x, calcStatus)
            if xT == None:
                xPort.SetPropValue(H_VAR, xH, calcStatus)
            vPort.CalcFlows()
            xPort.CalcFlows()
        return converged
                    
        
        
        
class BalanceOp(UnitOperations.UnitOperation):
    """Class for the balance unit op. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """Init the balance

        Init Info:
        nuStreamsInMat = 0
        nuStreamsOutMat = 0
        nuStreamsInEne = 0
        nuStreamsOutEne = 0
        BalanceType = MOLE_BALANCE|ENERGY_BALANCE

        """          
        super(BalanceOp, self).__init__(initScript)
        self.SetParameterValue(NUSTIN_PAR + S_MAT, 0)
        self.SetParameterValue(NUSTOUT_PAR + S_MAT, 0)
        self.SetParameterValue(NUSTIN_PAR + S_ENE, 0)
        self.SetParameterValue(NUSTOUT_PAR + S_ENE, 0)
        self.SetParameterValue(BALANCETYPE_PAR, MOLE_BALANCE|ENERGY_BALANCE)
        self._balance = None
        
        
        
    def CleanUp(self):
        if self._balance:
            self._balance.CleanUp()
            self._balance = None
        super(BalanceOp, self).CleanUp()

    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        super(BalanceOp, self).SetParameterValue(paramName, value)
        self.UpdatePorts()
           
    def UpdatePorts(self):
        """Update the amount and names of the ports"""        
        # first inlet material ports
        nuPorts = self.GetNumberPorts(MAT|IN)
        nuStIn = self.GetParameterValue(NUSTIN_PAR + S_MAT)
        
        for i in range(nuPorts, nuStIn, -1):
            self.DeletePortNamed(IN_PORT + str(i - 1))
        for i in range(nuPorts, nuStIn):
            self.CreatePort(IN|MAT, IN_PORT + str(i))

        # now outlet material ports
        nuPorts = self.GetNumberPorts(MAT|OUT)
        nuStOut = self.GetParameterValue(NUSTOUT_PAR + S_MAT)
        if nuStOut == None: return
        
        for i in range(nuPorts, nuStOut, -1):
            self.DeletePortNamed(OUT_PORT + str(i - 1))
        for i in range(nuPorts, nuStOut):
            self.CreatePort(OUT|MAT, OUT_PORT + str(i))

        # inlet energy ports
        nuPorts = self.GetNumberPorts(ENE|IN)
        nuStIn = self.GetParameterValue(NUSTIN_PAR + S_ENE)
        if nuStIn == None: return
        
        for i in range(nuPorts, nuStIn, -1):
            self.DeletePortNamed(IN_PORT + 'Q' + str(i - 1))
        for i in range(nuPorts, nuStIn):
            self.CreatePort(IN|ENE, IN_PORT + 'Q' + str(i))

        # outlet energy ports
        nuPorts = self.GetNumberPorts(ENE|OUT)
        nuStOut = self.GetParameterValue(NUSTOUT_PAR + S_ENE)
        if nuStOut == None: return
        
        for i in range(nuPorts, nuStOut, -1):
            self.DeletePortNamed(OUT_PORT + 'Q' + str(i - 1))
        for i in range(nuPorts, nuStOut):
            self.CreatePort(OUT|ENE, OUT_PORT + 'Q' + str(i))

        # now create the balance
        balanceType = self.GetParameterValue(BALANCETYPE_PAR)
        if balanceType == None: return
        self._balance = Balance(balanceType)
        for port in self.GetPorts(MAT|ENE|IN|OUT):
            if port.GetPortType() & IN:
                self._balance.AddInput(port)
            else:
                self._balance.AddOutput(port)

    def Solve(self):
        self.FlashAllPorts()
        if self._balance:
            self._balance.DoBalance()
        if self.FlashAllPorts() and self._balance:
            self._balance.DoBalance()

    def _CloneParameters(self, clone, attrNamesToClone):
        """Update the number of ports and balance obj right here"""
        attrNamesToClone = super(BalanceOp, self)._CloneParameters(clone, attrNamesToClone)
            
        #Remove these attributes from the clone list
        dontClone = ["_balance"]
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
    