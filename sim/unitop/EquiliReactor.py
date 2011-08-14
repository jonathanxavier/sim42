"""Models a Equilibrium reactor

Classes:
ReactionDisplay - For rendering reaction
EquilibriumReaction - Equilibrium reaction class
InternalEqmReactor - Internal equilibrium reactor
EquilibriumReactor - General equilibrium reactor
"""
import re, string

import UnitOperations, Balance, Heater, Sensor, Stream
from sim.solver import Flowsheet, Error
from sim.solver.Variables import *
from sim.solver.Error import SimError
from sim.unitop.ConvRxn import ConversionReaction
from sim.unitop.Pump import DataSeries, ATable, LookupTable
from sim.solver.Messages import MessageHandler

from Numeric import *
#from Numeric import array, zeros, ones, Float, Int, take, put, add, clip
#from Numeric import transpose, dot, outerproduct, matrixmultiply, absolute, identity
from LinearAlgebra import solve_linear_equations, inverse


#Common constants
from BaseForReactors import QEXOTHERMIC_ISPOS_PAR, NURXN_PAR, REACTION, COEFF
from BaseForReactors import RXNFFORMULA_PAR, RXNCONV, RXNEXTENT


#Particual constants and equations of this unit op
MAXOUTERLOOPS = 50
EQM_CONST = 'EqmConst'
CALCOPTION_PAR = 'CalculationOption'
CONSTBASIS_PAR = 'CalculationBasis'
BASISPUNIT_PAR = 'BasisPressureUnit'
RXNTABLE = 'Table'
RXNEQM = 'Eequilibrium'
EQMCNSTCOEFF = 'EqmConstCoeff'
NUMBSERIES_PAR = 'NumberSeries'
SERIESTYPE_PAR = 'SeriesType'
SERIES_OBJ = 'Series'


class RxnVariable(object):
    """ translated from VB model """
    def __init__ (self, varName, varValue):
        self.name = varName
        self.currentValue = varValue
        
    def CopyFrom(otherVar):
        self.name = otherVar.name
        self.currentValue = otherVar.currentValue

class RxnUnknowns(object):     
    """ translated from VB model """
    def __init__ (self):
        self.numberOfUnknowns = 0
        self.myVariables = []

    def AddUnknown(self, uName, uValue):
        var = RxnVariable(uName, uValue)
        self.myVariables.append(var)
        self.numberOfUnknowns = len(self.myVariables)

    def RemoveUnknown(self,uName):
        for eachVar in self.myVariables:
            if eachVar.name == uName:
                self.myVariables.remove(eachVar)
                break
        self.numberOfUnknowns = len(self.myVariables)

    def GetNumberOfUnknowns(self):
        return self.numberOfUnknowns

    def GetMyVariableValues(self):
        vars = []
        for i in range(self.numberOfUnknowns):
            vars.append(self.myVariables[i].currentValue)
        return vars
            
    def SetMyVariableValues(self, vars):
        for i in range(self.numberOfUnknowns):
            self.myVariables[i].currentValue = vars[i]

    def CleanUp(self):
        self.numberOfUnknowns = 0
        self.myVariables = []        

class NonLinearSolver(object):
    """ Non-linear solver class for EquiliReactor, translated from VB model """

    def __init__(self):
        self.converged = 0
        self.epsilon = 0.0001
    
    def Solve(self, parent, uObj, numberOfEquations, max_num_iterations):
        self.converged = 0
        self.useNumericJac = 1
        x0 = uObj.GetMyVariableValues()
        x = x0
        # Set initial deltaX to 1.0 to ensure that convergence check works
        deltaX = ones(numberOfEquations, Float)
        idex =0
        try:
            while idex < max_num_iterations:
            #for idex in range(max_num_iterations):
                stepX = parent.CalculateStep(x)
                if stepX == None: return 0
                rhs = parent.CalculateRHS(x)
                if  self.useNumericJac == 1:
                    jacobian=parent.CalculateJacobian(x)
                elif self.useNumericJac == 0:
                    try:
                        jacobian=parent.CalculateJacobian1(x)
                    except: pass
                jacobian = inverse(jacobian)
                deltaX = dot(jacobian, stepX) 
                #deltaX = self.GetSolutionSolver(numberOfEquations, jacobian, stepX)       # rhs)
                self.converged = self.CheckForConvergence(numberOfEquations, rhs, stepX, deltaX)
                if idex == max_num_iterations-1:   #show intermidiate results
                    if self.useNumericJac == 0:
                        try:
                            parentPath = parent.GetPath()
                            parent.InfoMessage('ShowIntermidiateResults', (parentPath,))
                            uObj.SetMyVariableValues(x)
                            return 2
                        except:
                            return 0
                    else:
                        self.useNumericJac = 0
                        x = x0
                        deltaX = zeros(numberOfEquations, Float)
                        idex = 0
                elif self.converged: 
                    uObj.SetMyVariableValues(x)
                    return 1
                parent.UpdateX(x, deltaX)
                idex = idex + 1
        except ArithmeticError, e:
            return 0       

        if not self.converged:
            return 0

    def CheckForConvergence(self, numberOfEquations, rhs, dItem, deltaX):
        try:
            for i in range(numberOfEquations):
                if (abs(rhs[i]) > self.epsilon)  and (abs(dItem[i]) > self.epsilon * 0.01):            #and (abs(deltaX[i]) > self.epsilon * 0.01)
                    return 0
            return 1
        except:
            return 0

class EquilibriumConstant(object):
    """ class for returning a Equilibrium reaction Constant"""
    def __init__(self, parent):
        self._parent = parent

        #newly added for EquiliReactor, some may be removed later
        self.eqmCoeffs=[]
        self.tblEqmCoeffs=[]
        self.eqmKSpecs=[]
        self.eqmConstant = None      # calculated equilibrium constant
        
        # A table lookup unit
        # with 2 series: tableTemperature, tablePressure
        self.kTable = ATable()
        self.kTable.SetSeriesCount(4)           # 4 series: TableT, tebleK, Eff, KSpec
        self.kTable.SetSeriesType(0, T_VAR)
        self.kTable.SetSeriesType(1, GENERIC_VAR)
        self.kTable.SetSeriesType(2, GENERIC_VAR)  #A,B,C,D
        self.kTable.SetSeriesType(3, GENERIC_VAR)  #K Spec
        #self.kTable.SetSeriesType(2, GENERIC_VAR)

        self.tableTemp = []
        self.tableKeq = []
        self.myUnknowns = RxnUnknowns()
        self.mySolver = NonLinearSolver()

    def CorrelateCoeffs(self):
        #clear equlibrium constant and coefficients first
        self.eqmConstant = None      # calculated equilibrium constant
        self.tblEqmCoeffs=[]
        
        tbl = self.kTable
        if not tbl: return 0
        srs0 = tbl.GetObject(SERIES_OBJ + str(0))
        srs1 = tbl.GetObject(SERIES_OBJ + str(1))
        if (not srs0) or (not srs1): return 0
        vals0 = srs0.GetValues()
        vals1= srs1.GetValues()
        self.tableTemp = vals0
        self.tableKeq = vals1
        if (len(vals0) == 0 or len(vals1) == 0 or len(vals0) != len(vals1)):
            return 0
        else:
            self.myUnknowns.CleanUp()
            if len(vals0)==1:
                self.myUnknowns.AddUnknown ("A", -10)
                nuEqu = 1
            elif len(vals0)==2:
                self.myUnknowns.AddUnknown ("A", -10)
                self.myUnknowns.AddUnknown ("B", 1)
                nuEqu = 2
            elif len(vals0)==3:
                self.myUnknowns.AddUnknown ("A", -10)
                self.myUnknowns.AddUnknown ("B", 1)
                self.myUnknowns.AddUnknown ("C", 1)
                nuEqu = 3
            else:
                self.myUnknowns.AddUnknown ("A", -10)
                self.myUnknowns.AddUnknown ("B", 1)
                self.myUnknowns.AddUnknown ("C", 1)
                self.myUnknowns.AddUnknown ("D", 0.001)
                nuEqu = 4
            if not self.mySolver.Solve (self, self.myUnknowns, nuEqu, MAXOUTERLOOPS): return 0
            self.tblEqmCoeffs = self.myUnknowns.GetMyVariableValues()
            if nuEqu < 4:
                for i in range(nuEqu, 4):
                    self.tblEqmCoeffs.append(0)
            return 1


    def GetObject(self, name):
        if name == RXNTABLE:
            return self.kTable
        else:
            return None

    def __str__(self):
        s = 'K value: ' + str(self.eqmConstant)
        s += '\nSpecified A, B, C, D: ' + str(self.eqmCoeffs)
        s += '\nRegressed A, B, C, D: ' + str(self.tblEqmCoeffs)
        
    def GetContents(self):
        result = []
        result.append(('K value', self.eqmConstant))
        result.append(('Specified A, B, C, D', self.eqmCoeffs))
        result.append(('Regressed A, B, C, D', self.tblEqmCoeffs))
        result.extend(self.kTable.GetContents())
        return result
    
    def CalculateKeq(self, temperature):
        calcOption = self._parent.parentUO.GetParameterValue(CALCOPTION_PAR)
        try:
            self.eqmConstant = None
            #self.eqmCoeffs = []
            logK = None
            if calcOption == 1:        # or calcOption == 3:
                if self.CorrelateCoeffs():
                    logK =(self.tblEqmCoeffs[0] + self.tblEqmCoeffs[1] / temperature + self.tblEqmCoeffs[2] * log(temperature) + self.tblEqmCoeffs[3] * temperature)
                else:
                    self.eqmConstant = None
            elif calcOption == 2:
                logK = self.GibbsEqmConstant(temperature)
            elif calcOption == 3:
                tbl = self.kTable
                if not tbl: return None
                srs2 = tbl.GetObject(SERIES_OBJ + str(3))
                vals2= srs2.GetValues()
                self.eqmKSpecs = vals2
                self.eqmConstant = self.eqmKSpecs[0]
                logK = None
            elif calcOption == 4:
                tbl = self.kTable
                if not tbl: return None
                srs2 = tbl.GetObject(SERIES_OBJ + str(2))
                vals2= srs2.GetValues()
                self.eqmCoeffs = vals2
                self.tblEqmCoeffs = []
                #self.eqmCoeffs = self.kTable.GetObject(SERIES_OBJ + str(2)).GetValues()
                logK=(self.eqmCoeffs[0] + self.eqmCoeffs[1] / temperature + self.eqmCoeffs[2] * log(temperature) + self.eqmCoeffs[3] * temperature)
            if logK != None:
                if logK > 300: logK = 300
                if logK < -300: logK = -300
                self.eqmConstant = exp(logK)
            return self.eqmConstant    
        except:
            return None

    def CalculateStep(self, x):
        rhs=zeros(len(x), Float)
        try:
            dum = 0
            if len(self.tableKeq) == len(self.tableTemp):
                if len(x)==1:
                    for i in range(len(self.tableTemp)):
                        dum = x[0] - log(self.tableKeq[i])
                        rhs[0] = rhs[0] + 2 * dum
                elif len(x)==2:
                    for i in range(len(self.tableTemp)):
                        dum = x[0] + x[1]/self.tableTemp[i] - log(self.tableKeq[i])
                        rhs[0] = rhs[0] + 2 * dum
                        rhs[1] = rhs[1] + 2 * dum / self.tableTemp[i]
                elif len(x)==3:
                    for i in range(len(self.tableTemp)):
                        dum = x[0] + x[1]/self.tableTemp[i] + x[2] * log(self.tableTemp[i])- log(self.tableKeq[i])
                        rhs[0] = rhs[0] + 2 * dum
                        rhs[1] = rhs[1] + 2 * dum / self.tableTemp[i]
                        rhs[2] = rhs[2] + 2 * dum * log(self.tableTemp[i])
                else:
                    for i in range(len(self.tableTemp)):
                        dum = x[0] + x[1]/self.tableTemp[i] + x[2] * log(self.tableTemp[i]) + x[3] * self.tableTemp[i] - log(self.tableKeq[i])
                        rhs[0] = rhs[0] + 2 * dum
                        rhs[1] = rhs[1] + 2 * dum / self.tableTemp[i]
                        rhs[2] = rhs[2] + 2 * dum * log(self.tableTemp[i])
                        rhs[3] = rhs[3] + 2 * dum * self.tableTemp[i]
            return rhs
        except:
            return None

    def CalculateRHS(self, x):
        try:
            sum = 0.0
            nEq = len(x)
                
            if len(self.tableKeq) == len(self.tableTemp):
                for i in range(len(self.tableTemp)):
                    denom = 1.e-20
                    if abs(log(self.tableKeq[i]))> denom: denom = log(self.tableKeq[i])
                    if nEq == 1:
                        tVal = x[0]
                    elif nEq == 2:
                        tVal = x[0] + x[1]/self.tableTemp[i]
                    elif nEq == 3:
                        tVal = x[0] + x[1]/self.tableTemp[i] + x[2] * log(self.tableTemp[i]) 
                    else:
                        tVal = x[0] + x[1]/self.tableTemp[i] + x[2] * log(self.tableTemp[i]) + x[3] * self.tableTemp[i]
                    dum = tVal - log(self.tableKeq[i])
                    sum += abs(dum/denom)
                rhs = 2*(sum)*ones(nEq, Float)    
            return rhs
        except:
            return None

    def CalculateJacobian(self, x):
        j = zeros((len(x),len(x)), Float)
        try:
            workArray1= self.CalculateStep(x)
            # Calculate Jacobian by shifting
            # unshifted RHS's
            shift = 1
            for i2 in range(len(x)):
                xOld = x[i2]
                x[i2] = x[i2] + shift
                workArray2=self.CalculateStep(x)
                for i1 in range(len(x)):
                    j[i1][i2] = (workArray2[i1]-workArray1[i1]) / shift
                x[i2] = xOld
            return j
        except:
            return j
            
    def UpdateX(self, x, deltaX):
        scaleFactor = 1
        for i in range(len(x)):
            if deltaX[i] != 0.0:
                scaleFactor1 = 100000 / abs(deltaX[i])
                if (scaleFactor1<scaleFactor): scaleFactor = scaleFactor1
        for i in range(len(x)):            
            x[i] = x[i] -deltaX[i] * scaleFactor                           

    def CompoundGibbs(self, nc, rxnT):
        try:
            parent = self._parent.parentUO
            #rxnT = parent.outPort.GetPropValue(T_VAR)
            rxnP = parent.outPort.GetPropValue(P_VAR)
            # arbitary composition
            x = zeros(nc, Float)
            x[0] = 1.0
            # check whether it returns G or g/RT
            # check whether it has mixing rule
            thCaseObj = parent.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            gibbs = thAdmin.GetArrayProperty(prov, case,
                                             (T_VAR, rxnT), (P_VAR, rxnP), VAPOUR_PHASE,
                                             x, 'IdealGasGibbs')
            return gibbs
        except:
            return None

        
    def GibbsEqmConstant(self, temperature):
        try:
            cmps = self._parent.parentUO.GetCompoundNames()
            nc = len(self._parent.parentUO.GetCompoundNames())
            gibbs = self.CompoundGibbs(nc,temperature)
            coeffs = self._parent.stoichCoeffs
            return -sum(gibbs * coeffs) /(8.31434 * temperature)
        except:
            return None

    def SetParent(self, parent):
        self._parent = parent
        
    def Clone(self):
        clone = self.__class__(None)
        
        dontClone = ['myUnknowns', 'mySolver', '_parent']
        for attrName in self.__dict__:
            if attrName in dontClone:
                continue
            attr = self.__dict__[attrName]
            
            attrClone = None
            if hasattr(attr, 'Clone'):
                attrClone = attr.Clone()
            else:
                attrClone = UnitOperations._SafeClone(attr)
            
            clone.__dict__[attrName] = attrClone
        return clone
    
        
class EquilibriumReaction(ConversionReaction):
    """ class for a equilibrium reaction """
    def __init__(self, initScript = None):
        ConversionReaction.__init__(self, initScript)
        self.eqmConstant = EquilibriumConstant(self)

    def CleanUp(self):
        self.eqmConstant = None
        super(EquilibriumReaction, self).CleanUp()
        
    def CalculateKeq(self,temperature):
        try:
            return self.eqmConstant.CalculateKeq(temperature)
        except:
            return None

    def GetObject(self, name):
        if name == EQM_CONST:
            obj = self.eqmConstant
        else:
            obj = super(EquilibriumReaction, self).GetObject(name)
        return obj

    def GetContents(self):
        result = super(EquilibriumReaction, self).GetContents()
        result.extend(self.eqmConstant.GetContents())
        return result

    def SideConstCoeff(self, sign):
        """sign = 1, reaction products side; sign = -1, reactants side.
        Equilibrium constant have a form of K = Cl*X^nl / (Cr * X^nr)
        this method returns Cl or Cr depends on the sign value. Cl or Cr counts
        for total pressure or other converstion values(e.g. if using mass fraction it
        would be 1/molarweight). If using MoleFraction to calculate equilibrium constant,
        Cl = Cr = 1"""

        calcOption = self.parentUO.GetParameterValue(CALCOPTION_PAR)
        calcBasis = self.parentUO.GetParameterValue(CONSTBASIS_PAR)

        if calcOption == 2 or calcOption == 1:  # using partial pressure to calculate reaction constant
            rxnPressure = self.parentUO.outPort.GetPropValue(P_VAR)
            nc = len(self.parentUO.GetCompoundNames())
            calcPressure = float(rxnPressure)/101.325    #assume default pressure unit for the constant table is atm
            SideCoeff = 1
            for i in range(nc):
                if (self.Coeff(i)*sign > 0):
                    SideCoeff = SideCoeff* (calcPressure **(sign * self.Coeff(i)))
            return SideCoeff
        else: 
            return 1.0
         
class InternalEqmReactor(UnitOperations.UnitOperation):
    def __init__(self, initScript = None):        
        UnitOperations.UnitOperation.__init__(self, initScript)
        self.ProductTotalMole = 0.0
        self.feedMolei = []
        self.productMolei = []
        self.productMoleFrac = []
        self.inPort = self.CreatePort(MAT|IN, IN_PORT)
        self.outPort = self.CreatePort(MAT|OUT, OUT_PORT)

        self.qPort = self.CreatePort(ENE|OUT, OUT_PORT + 'Q')
        self.dpPort = self.CreatePort(SIG, DELTAP_PORT)
        self.dpPort.SetSignalType(DELTAP_VAR)
        self.containerUnitOp = None  # used by containing op to be notified of equilibrium changes

        #newly added from VB model        
        self.myUnknowns = RxnUnknowns()
        self.mySolver = NonLinearSolver()
        self.kEqm =[]
        
        self.SetParameterValue(NURXN_PAR, 0)
        self.SetParameterValue(CALCOPTION_PAR, 1)   #use table to correlate constant
        self.SetParameterValue(CONSTBASIS_PAR, 1)   #use partial pressure to calculate constant
        self.SetParameterValue(BASISPUNIT_PAR, 'atm')   #VMG pressure unit when partial pressure as basis
        self.trace = 1.0e-10

    def CleanUp(self):
        self.inPort = self.outPort = None
        self.qPort = self.dpPort = None
        self.containerUnitOp = None
        super(InternalEqmReactor, self).CleanUp()
        
    def GetListOfReqParam(self): return (NURXN_PAR)

    def SetParameterValue(self, paramName, value):
        UnitOperations.UnitOperation.SetParameterValue(self, paramName, value)
        if paramName == NURXN_PAR:
            self.UpdateRxnCount()
        elif paramName == CALCOPTION_PAR and value == 2:
            self.SetParameterValue(CONSTBASIS_PAR, 2)
            if self.containerUnitOp:
                self.containerUnitOp.SetParameterValue(CONSTBASIS_PAR, 2)        

            
    def UpdateRxnCount(self):
        """Update the amount and names of the ports in"""      
        nuRxns = len(self.GetChildUnitOps())
        rxnIn = self.parameters[NURXN_PAR]
        for i in range(nuRxns, rxnIn, -1):
            self.DelUnitOperation(REACTION + str(i - 1))
            self.myUnknowns.RemoveUnknown(REACTION + str(i - 1))
        for i in range(nuRxns, rxnIn):
            rxn = EquilibriumReaction()
            self.AddUnitOperation(rxn, REACTION + str(i))
            self.myUnknowns.AddUnknown(REACTION + str(i), 0)
        # notify my container
        if self.containerUnitOp:
            nuRxns = len(self.GetChildUnitOps())
            self.containerUnitOp.GrabSignalPorts(nuRxns)            

    def RemoveRxn(self, name):
        self.DelUnitOperation(name)
        self.myUnknowns.RemoveUnknown(name)

    def CalculateProduct(self, finalCalc=0):
        # if finalCalc, then reset negative trcce to zero    
        rxns = self.chUODict.values()
        sumX = 0#
        for m in range(self.nc):
            dum = 0#
            for aRxn in rxns:
                dum = dum + aRxn.rxnExtent.GetValue() * aRxn.Coeff(m)

            pdt = self.feedMolei[m] + dum
            if finalCalc:
                # just to prevent round offs
                if (abs(pdt) < self.trace):
                    pdt = 0.0
                elif (pdt < 0.0):
                    if abs(pdt) > self.trace:
                        cmpName = str(self.GetCompoundNames()[m])
                        self.InfoMessage('InvalidComposition', (cmpName, pdt, self.GetPath()))
                    pdt = 0.0
            self.productMolei[m] = pdt
            
            sumX = sumX + pdt
        # normalize new moles
        self.ProductTotalMole = sumX
        self.productMoleFrac = self.productMolei / sumX

    def PropagatePressure(self):
        inPort = self.inPort
        outPort = self.outPort
        inP = inPort.GetPropValue(P_VAR)
        outP = outPort.GetPropValue(P_VAR)
        dP = self.dpPort.GetValue()

        if outP == None:
            if dP != None and inP != None:
                outPort.SetPropValue(P_VAR, inP - dP, CALCULATED_V)
        elif inP == None:
            if dP != None:
                inPort.SetPropValue(P_VAR, outP + dP, CALCULATED_V)
        else:
            self.dpPort.SetPropValue(DELTAP_VAR, inP - outP, CALCULATED_V)

    def Solve(self):
        if self.IsForgetting(): return 0
        try:
            rxns = self.chUODict.values()
            nuRxns = len(rxns)
            inPort = self.inPort
            outPort = self.outPort

            #partially solve the reaction constant if reaction temperature is known
            outT = outPort.GetPropValue(T_VAR)
                
            # propagate pressure
            self.PropagatePressure()
            inPort.Flash()

            self.kEqm = zeros(nuRxns,Float)

            regrFailed = 1
            if outT != None:
                for i in range(nuRxns):
                    ki =  rxns[i].CalculateKeq(float(outT))
                    if ki == None:
                        regrFailed = 0
                    else:
                        self.kEqm[i]=ki
            else:
                #partially solve the A,B,C,D if no other inputs were given
                calcOption = self.GetParameterValue(CALCOPTION_PAR)
                if calcOption == 1:
                    for i in range(nuRxns):
                        if not rxns[i].eqmConstant.CorrelateCoeffs(): regrFailed = 0
                    if regrFailed == 0: return 0

            xIn = inPort.GetCompositionValues()
            self.nc = len(xIn)
            #initialize the working arrays
            self.feedMolei = array(xIn)
            self.productMolei = zeros(self.nc, Float)
            self.productMoleFrac = zeros(self.nc, Float)
            self.myUnknowns.SetMyVariableValues(zeros(nuRxns, Float))

            if not self.ValidateOk(): return 0

            #check if it is a temperature or reactor heat spec
            if outT == None :
                #if self.containerUnitOp:
                    #outQ = self.containerUnitOp.GetPort(OUT_PORT + 'Q').GetPropValue(ENERGY_VAR)
                    #outQ = -1.0 * outQ
                #else:
                    #outQ = self.qPort.GetPropValue(ENERGY_VAR)
                outQ = self.qPort.GetPropValue(ENERGY_VAR)
                if outQ != None:
                    #reactor heat spec
                    if self.SolveAtDuty(outQ): return 1
                return 0
            else:
                #reactor temperature spec
                
                # Initialize rxn extents.  If inlet flow is unknown, assume 1 mole
                flow = inPort.GetPropValue(MOLEFLOW_VAR)
                if flow == None:  # and not self.IsForgetting():
                    flow = 1.0
                self.feedMolei = self.feedMolei * flow

                for i in range(nuRxns):
                    if self.kEqm[i] == None: return 0

                solveStatus = self.mySolver.Solve(self, self.myUnknowns, nuRxns, MAXOUTERLOOPS)
                if solveStatus == 1:
                    self.InfoMessage('ConvergedOp', (self.GetPath(),))
                elif solveStatus == 0:
                    self.InfoMessage('CouldNotConverge', (self.GetPath(),))
                    return 0

                convs = self.myUnknowns.GetMyVariableValues()           
                for i in range(nuRxns):            
                    rxns[i].rxnExtent.SetValue(convs[i])
                    rxns[i].localExt = convs[i]
                    
                self.CalculateProduct()
                self.UpdateOutPort()
                self.EnergyBalance()
            return 1
        except:
            return 0

    def SolveAtDuty(self, rxnQ):
        """ solve reactor when reaction heat is specified"""
        try:
            rns = self.chUODict.values()
            nuRxns = len(rns)
            rxnPressure = float(self.outPort.GetPropValue(P_VAR))
            tIn = float(self.inPort.GetPropValue(T_VAR))
            tOut = tIn
            #tOut = 298.2
            flowIn = self.inPort.GetPropValue(MOLEFLOW_VAR)
            # Cannot solve when flow is not specified 
            if (flowIn != None):
                self.feedMolei = self.feedMolei * flowIn
                hrxnIn = self.RxnEnthalpy(self.inPort)
                hin = hrxnIn*flowIn
            else:
                return 0
            tK = tOut
            tLo = 0
            tHi = 10000
            tMax = tK
            tMin = tK
            thCaseObj = self.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            phase = LIQUID_PHASE
            tolerance = self.GetTolerance()
            outerLoop = 0
            for iter in range(MAXOUTERLOOPS):
                self.kEqm = zeros(nuRxns,Float)
                regrFailed = 1
                for i in range(nuRxns):
                    ki =  rns[i].CalculateKeq(float(tK))
                    if ki == None:
                        regrFailed = 0
                    else:
                        self.kEqm[i] = ki

                if not self.mySolver.Solve(self, self.myUnknowns, nuRxns, MAXOUTERLOOPS):
                    regrFailed = 0
                if regrFailed == 0: return 0
                convs = self.myUnknowns.GetMyVariableValues()           
                for i in range(nuRxns):
                    rns[i].rxnExtent.SetValue(convs[i])
                    rns[i].localExt = convs[i]

                self.CalculateProduct()
                prodMoleEnthalpy = (hin - rxnQ * 3.6)/self.ProductTotalMole          #3.6 to convert spec unit from W(assume so) to kj/hr
                try:
                    prop1 = (P_VAR, rxnPressure)
                    prop2 = (T_VAR,tK)
                    propList = ('rxnBaseH', MOLE_WT)
                    value = thAdmin.GetProperties(prov, case, prop1, prop2, phase, self.productMoleFrac, propList)
                    moleH = prodMoleEnthalpy - value[0]
                    
                    compounds = CompoundList(None)
                    for i in range(self.nc):
                        prop = BasicProperty(FRAC_VAR)
                        prop.SetValue(self.productMoleFrac[i])
                        compounds.append(prop)
                    compounds.Normalize()
                    
                    props = MaterialPropertyDict()
                    props[H_VAR].SetValue(moleH)
                    props[P_VAR].SetValue(rxnPressure)
                    propList = (T_VAR, MOLE_WT)
                    results = thAdmin.Flash(prov, case, compounds, props, 2, (T_VAR))
                    tkProd = results.bulkProps[0]
                    dT =  float(tK) - float(tkProd)
                    scaleFactor = PropTypes[T_VAR].scaleFactor
                    sTolerance = scaleFactor * tolerance
                    if abs(dT) <= sTolerance or ((tHi-tLo) <= sTolerance and abs(dT)/tK <= 0.001): break
                    if tMax < tkProd: tMax = tkProd
                    if tMin > tkProd: tMin = tkProd
                    if dT > 0:
                        if tK < tHi: tHi = tK
                        if tLo == 0:
                            tLo = tkProd
                        elif tMin == tkProd:
                            tLo = tMin
                    else:
                        if tK > tLo: tLo = tK
                        if tHi == 10000:
                            tHi = tkProd
                        elif tMax == tkProd:
                            tHi = tMax
                    tK = 0.5 * (tLo + tHi)
                except:            #Change initial guess temperature and restart calculation
                    self.myUnknowns.SetMyVariableValues(zeros(nuRxns, Float))
                    tK = (298.2 + tK)/2
                    outerLoop += 1
                    if outerLoop > 20: return 0
            if iter > MAXOUTERLOOPS-2: return 1
            self.outPort.SetPropValue(H_VAR, moleH, CALCULATED_V)
            self.UpdateOutPort()
            return 1
        except: return 0

    def UpdateOutPort(self):
        # composition
        self.outPort.SetCompositionValues(self.productMoleFrac, CALCULATED_V)
        # molar flow
        if (self.inPort.GetPropValue(MOLEFLOW_VAR) != None):
            # inlet flow is known, assign outlet
            self.outPort.SetPropValue(MOLEFLOW_VAR, self.ProductTotalMole, CALCULATED_V)
        elif (self.outPort.GetPropValue(MOLEFLOW_VAR) != None):
            # outlet is known, calculate was done by assuming 1 mole inlet
            # proportionate the inlet flow
            inMoleFlow = self.outPort.GetPropValue(MOLEFLOW_VAR) / self.ProductTotalMole
            self.inPort.SetPropValue(MOLEFLOW_VAR, inMoleFlow, CALCULATED_V)
            self.inPort.CalcFlows()
        #flash the port
        self.outPort.Flash()                
        
    def ValidateOk(self):
        rxns = self.chUODict.values()
        # all reactions must have been defined
        if len(rxns) == 0: return 0
        for aRxn in rxns:
            if not aRxn.ValidateOk(): return 0
        # fix 020503, do not check for complete inlet stream,
        # check for inlet composiiton
        if not self.inPort.GetCompounds().AreValuesReady(): return 0

        # flow must have been known
        #inPort = self.inPort        
        #flow = inPort.GetPropValue(MOLEFLOW_VAR)
        #if flow == None: return 0
        # The In port must have been fully defined.  Probably should be OK if P is missing
        #if not inPort.AlreadyFlashed(): return 0
        return 1

    def EnergyBalance(self):
        # i need the H and flow for both the inlet and outlet
        flowIn = self.inPort.GetPropValue(MOLEFLOW_VAR)
        flowOut = self.outPort.GetPropValue(MOLEFLOW_VAR)

        if (flowIn != None and flowOut != None):
            hrxnIn = self.RxnEnthalpy(self.inPort)
            hrxnOut = self.RxnEnthalpy(self.outPort)
            if hrxnIn != None and hrxnOut != None:
                hout = (hrxnIn*flowIn - hrxnOut*flowOut) / 3.6             #convert from KJ/hr -> W (=J/s)
                self.qPort.SetPropValue(ENERGY_VAR, hout, CALCULATED_V)
       
    def RxnEnthalpy(self, aPort):
        h = aPort.GetPropValue(H_VAR)
        if (h == None): return None
        try:
            p = aPort.GetPropValue(P_VAR)
            t = aPort.GetPropValue(T_VAR)
            thCaseObj = self.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            prop1 = (P_VAR, p)
            prop2 = (T_VAR, t)
            phase = LIQUID_PHASE
            frac = aPort.GetCompositionValues()
            propList = ('rxnBaseH', MOLE_WT)
            value = thAdmin.GetProperties(prov, case, prop1, prop2, phase, frac, propList)
            hrxn = h + value[0]
            return hrxn
        except:
            return None

    def CalculateProductForReaction(self, aRxn, finalCalc=0):
        # if finalCalc, then reset negative trace to zero    
        rxns = self.chUODict.values()
        sumX = 0
        for m in range(self.nc):
            dum = aRxn.rxnExtent.GetValue() * aRxn.Coeff(m)
            pdt = self.feedMolei[m] + dum
            if finalCalc:
                # just to prevent round offs
                if (abs(pdt) < self.trace):
                    pdt = 0.0
                elif (pdt < 0.0):
                    if abs(pdt) > self.trace:
                        cmpName = str(self.GetCompoundNames()[m])
                        self.InfoMessage('InvalidComposition', (cmpName, pdt, self.GetPath()))
                    pdt = 0.0
            self.productMolei[m] = pdt
            
            sumX = sumX + pdt
        # normalize new moles
        self.ProductTotalMole = sumX
        self.productMoleFrac = self.productMolei / sumX

    def CalculateStep(self, x):
        rxns = self.chUODict.values()
        nuRxns=len(rxns)
        rhs = zeros(nuRxns, Float)
        workArray = zeros(self.nc, Float)
        sumX = 0
        for i in range(self.nc):
            dum = 0
            for j in range(nuRxns):
                dum = dum + x[j] * rxns[j].Coeff(i)
            workArray[i] = self.feedMolei[i] + dum
            sumX = sumX + workArray[i]
        # normalize new moles
        sumX = 1/sumX
        workArray = workArray * sumX
        
        # calculate the new RHS's. For those rxn's with kEqm > 1e10 RHS is Feed-extent=0.0
        for j in range(nuRxns):
            if (self.kEqm[j] > 1e10):
                xLimit = 1.e+20
                iLimit = 0
                for i in range(self.nc):
                    if (rxns[j].Coeff(i)<0):
                        if ((workArray[i]/abs(rxns[j].Coeff(i)))<xLimit):
                            iLimit = i
                            xLimit = workArray[i]/abs(rxns[j].Coeff(i))
                rhs[j]=self.feedMolei[iLimit]+x[j]*rxns[j].Coeff(iLimit)-1.e-20
            else:
                leftSide = self.kEqm[j]
                rightSide = 1
                for i in range(self.nc):
                    if (rxns[j].Coeff(i)<0):
                        leftSide = leftSide*(workArray[i])**(-rxns[j].Coeff(i))
                    else:
                        rightSide = rightSide * (workArray[i])**(rxns[j].Coeff(i))
                leftSideCoeff = rxns[j].SideConstCoeff(-1)
                rightSideCoeff = rxns[j].SideConstCoeff(1)
                rhs[j] = leftSide*leftSideCoeff - rightSide*rightSideCoeff
        return rhs

    def CalculateRHS(self, x):
        rxns = self.chUODict.values()
        nuRxns=len(rxns)
        rhs = zeros(nuRxns, Float)
        workArray = zeros(self.nc, Float)
        sumX = 0
        for i in range(self.nc):
            dum = 0
            for j in range(nuRxns):
                dum = dum + x[j] * rxns[j].Coeff(i)
            workArray[i] = self.feedMolei[i] + dum
            sumX = sumX + workArray[i]
        # normalize new moles
        sumX = 1/sumX
        workArray = workArray * sumX
        tVal = 0.0
        
        # calculate the new RHS's. For those rxn's with kEqm > 1e10 RHS is Feed-extent=0.0
        for j in range(nuRxns):
            denom = 1.e-20
            if (self.kEqm[j] > 1e10):
                xLimit = 1.e+20
                iLimit = 0
                for i in range(self.nc):
                    if (rxns[j].Coeff(i)<0):
                        if ((workArray[i]/abs(rxns[j].Coeff(i)))<xLimit):
                            iLimit = i
                            xLimit = workArray[i]/abs(rxns[j].Coeff(i))
                tVal = self.feedMolei[iLimit]+x[j]*rxns[j].Coeff(iLimit)
                rhs[j]=abs(tVal/denom -1)
            else:
                leftSide = self.kEqm[j]
                rightSide = 1
                for i in range(self.nc):
                    if (rxns[j].Coeff(i)<0):
                        leftSide = leftSide*(workArray[i])**(-rxns[j].Coeff(i))
                    else:
                        rightSide = rightSide * (workArray[i])**(rxns[j].Coeff(i))
                leftSideCoeff = rxns[j].SideConstCoeff(-1)
                rightSideCoeff = rxns[j].SideConstCoeff(1)
                tVal = rightSide*rightSideCoeff
                if tVal > denom: denom=tVal
                rhs[j] = ((leftSide*leftSideCoeff/denom) - 1)
        return rhs

   
    def CalculateJacobian(self, x):
        rxns = self.chUODict.values()
        nuRxns=len(rxns)
        lSideC = ones(nuRxns, Float)
        rSideC = ones(nuRxns, Float)
        workArray = zeros(self.nc, Float)
        jac = zeros((len(x),len(x)), Float)
        sumX = 0
        for i in range(self.nc):
            dum = 0
            for j in range(nuRxns):
                dum = dum + x[j] * rxns[j].Coeff(i)
            workArray[i] = self.feedMolei[i] + dum
            sumX = sumX + workArray[i]
        # normalize new moles
        sumX = 1/sumX
        workArray = workArray * sumX
        tVal = 0.0

        for j in range(nuRxns):
            lSideC[j] = self.kEqm[j]
            for i in range(self.nc):
                if (rxns[j].Coeff(i)<= -1):
                    lSideC[j] = lSideC[j] * (workArray[i]**(-rxns[j].Coeff(i)-1))
                elif (rxns[j].Coeff(i)< 0):
                    if workArray[i]>0:
                        lSideC[j] = lSideC[j] * (workArray[i]**(-rxns[j].Coeff(i)-1))
                elif (rxns[j].Coeff(i)>= 1):
                        rSideC[j] = rSideC[j] * (workArray[i]**(rxns[j].Coeff(i)-1))
                elif (rxns[j].Coeff(i)> 0):
                    if workArray[i]>0:
                        rSideC[j] = rSideC[j] * (workArray[i]**(rxns[j].Coeff(i)-1))

        for j in range(len(x)):
            for i in range(len(x)):
                lSum = 0.0
                rSum = 0.0
                for k in range(self.nc):
                    lItem = 1.
                    rItem = 1.
                    for m in range(self.nc):
                        if m <> k:
                            if rxns[j].Coeff(m)<0:
                                lItem = lItem*workArray[m]
                            elif rxns[j].Coeff(m)>0:
                                rItem = rItem*workArray[m]
                    if (rxns[j].Coeff(k)<0):
                        lItem = -(rxns[i].Coeff(k))*(rxns[j].Coeff(k))*lItem*sumX
                        lSum = lSum + lItem
                    elif (rxns[j].Coeff(k)>0):
                        rItem = (rxns[i].Coeff(k))*(rxns[j].Coeff(k))*rItem*sumX
                        rSum = rSum + rItem
                leftSideCoeff = rxns[j].SideConstCoeff(-1)
                rightSideCoeff = rxns[j].SideConstCoeff(1)
                jac[j][i] = leftSideCoeff*lSum*lSideC[j] - rightSideCoeff*rSum*rSideC[j]

        return jac

    def CalculateJacobian1(self,x):            #called by mysolver
        j = zeros((len(x),len(x)), Float)
        workArray1 = self.CalculateStep(x)
        # Calculate Jacobian by shifting
        # unshifted RHS's
        shift = 0.00001
        for i2 in range(len(x)):
            xOld = x[i2]
            x[i2] = x[i2] + shift
            workArray2=self.CalculateStep(x)
            for i1 in range(len(x)):
                j[i1][i2] = (workArray2[i1]-workArray1[i1]) / shift
            x[i2] = xOld
        return j

    def UpdateX(self, x, deltaX):
        rxns = self.chUODict.values()
        scaleFactor =1
        workArray = zeros(self.nc, Float)
        for i in range(self.nc):
            sumExtents = 0
            sumDeltas = 0
            iRxn = 0
            for aRxn in rxns:
                sumExtents = sumExtents + x[iRxn] * aRxn.Coeff(i)
                sumDeltas = sumDeltas + deltaX[iRxn] * aRxn.Coeff(i)
                iRxn = iRxn +1
            workArray[i] = self.feedMolei[i] + sumExtents - sumDeltas
            if (workArray[i] < 1.E-30) and (sumDeltas != 0.):
                scaleFactor1 = 0.5 * (self.feedMolei[i] + sumExtents - 1.E-30) / sumDeltas
                if (scaleFactor1 < scaleFactor): scaleFactor = scaleFactor1
            
        if (scaleFactor < 0.0001): scaleFactor = 0.0001
   
        for i in range(len(x)): x[i] = x[i] - deltaX[i] * scaleFactor
        
    def UpdateX1(self, x, deltaX):
        rxns = self.chUODict.values()
        workArray = zeros(self.nc, Float)
        for i in range(self.nc):
            sumExtents = 0
            sumDeltas = 0
            iRxn = 0
            for aRxn in rxns:
                sumExtents = sumExtents + x[iRxn] * aRxn.Coeff(i)
                sumDeltas = sumDeltas - deltaX[iRxn] * aRxn.Coeff(i)
                iRxn = iRxn+1
            workArray[i] = self.feedMolei[i] + sumExtents - sumDeltas
            while (workArray[i] < 1.E-30) and (sumDeltas != 0.):
                deltaX = 0.5 * deltaX       #(self.feedMolei[i] + sumExtents - 1.E-30) / sumDeltas
                sumDeltas = 0
                iRxn = 0
                for aRxn in rxns:
                    sumDeltas = sumDeltas - deltaX[iRxn] * aRxn.Coeff(i)
                    iRxn = iRxn+1
                workArray[i] = self.feedMolei[i] + sumExtents - sumDeltas
            
        for i in range(len(x)): x[i] = x[i] + deltaX[i]



class EquilibriumReactor(UnitOperations.UnitOperation):
    # This version do not suuport full backward calc with the following known probelms:
    #    The inlet composition cannot be calculated from the outlet composition
    #    Given OutQ and Out.T, it cannot calculate In.T
    def __init__(self, initScript = None):        
        super(EquilibriumReactor, self).__init__(initScript)
        self.itnRxn = InternalEqmReactor()
        self.AddUnitOperation(self.itnRxn, 'itnRxn')
        self.itnRxn.containerUnitOp = self
        
        self.baln = Balance.BalanceOp()
        self.AddUnitOperation(self.baln, 'EneBalance')

        self.baln.SetParameterValue(NUSTIN_PAR + Balance.S_ENE, 1)
        self.baln.SetParameterValue(Balance.BALANCETYPE_PAR, Balance.ENERGY_BALANCE)

        # to create an Energy Out port for export        
        self.balEneSensor = Sensor.EnergySensor()
        self.AddUnitOperation(self.balEneSensor, 'BalEneSensor')
        self.eneSensor = Sensor.EnergySensor()
        self.AddUnitOperation(self.eneSensor, 'EneSensor')
        self.eneStream = Stream.Stream_Energy()
        self.AddUnitOperation(self.eneStream, 'EneStream')

        # connect the child unit ops
        self.ConnectPorts('itnRxn', OUT_PORT + 'Q', 'EneBalance', IN_PORT + 'Q0')      
        self.ConnectPorts('EneSensor', OUT_PORT, 'EneStream', IN_PORT)
        self.ConnectPorts('BalEneSensor', SIG_PORT, 'EneSensor', SIG_PORT)
        
        # borrow child ports
        self.BorrowChildPort(self.eneStream.GetPort(OUT_PORT), OUT_PORT + 'Q')
        self.BorrowChildPort(self.itnRxn.GetPort(IN_PORT), IN_PORT)
        self.BorrowChildPort(self.itnRxn.GetPort(OUT_PORT), OUT_PORT)
        self.BorrowChildPort(self.itnRxn.GetPort(DELTAP_PORT), DELTAP_PORT)

        self.SetParameterValue(NURXN_PAR, 0)
        self.SetParameterValue(CALCOPTION_PAR, 1)   #use table to correlate constant
        self.SetParameterValue(CONSTBASIS_PAR, 1)   #use partial pressure to calculate constant
        self.SetParameterValue(BASISPUNIT_PAR, 'atm')   #VMG pressure unit when partial pressure as basis
        self.SetParameterValue(QEXOTHERMIC_ISPOS_PAR, 1)
        

    def CleanUp(self):
        self.itnRxn = self.baln = None
        self.balEneSensor = self.eneSensor = self.eneStream = None
        super(EquilibriumReactor, self).CleanUp()
        
    def AdjustOldCase(self, version):
        super(EquilibriumReactor, self).AdjustOldCase(version)
        if version[0] < 69:
            value = self.GetParameterValue(QEXOTHERMIC_ISPOS_PAR)
            if value != 0 or value != 1:
                #If the parameter is not there then assume that the balance is connected
                #for QEXOTHERMIC_ISPOS_PAR = 0
                #Users will have to manually change this value to make it work the other way (default)
                self.parameters[QEXOTHERMIC_ISPOS_PAR] = 0

        if version[0] < 70:
            itnRxor = self.itnRxn
            rxns = itnRxor.chUODict.values()
            nuRxns = len(rxns)
            for i in range(nuRxns):
                rxn = self.GetObject(REACTION + str(i))
                rxnConst = rxn.GetObject(EQM_CONST)
                if rxnConst:
                    rxnConst.eqmKSpecs = []
                    rxnConst.kTable.SetSeriesCount(4)             # 4 series: TableT, tebleK, Eff, KSpec
                    rxnConst.kTable.SetSeriesType(3, GENERIC_VAR)  #K Spec
               
            
    def SetParameterValue(self, paramName, value):
        super(EquilibriumReactor, self).SetParameterValue(paramName, value)
        
        if paramName == NURXN_PAR or paramName == CALCOPTION_PAR or paramName == CONSTBASIS_PAR or paramName == BASISPUNIT_PAR:
            self.itnRxn.SetParameterValue(paramName, value)

        elif paramName == QEXOTHERMIC_ISPOS_PAR:
            if value:
                self.baln.SetParameterValue(NUSTIN_PAR + Balance.S_ENE, 1)
                self.baln.SetParameterValue(NUSTOUT_PAR + Balance.S_ENE, 1)
                self.ConnectPorts('BalEneSensor', IN_PORT, 'EneBalance', OUT_PORT + 'Q0')
            else:
                self.baln.SetParameterValue(NUSTIN_PAR + Balance.S_ENE, 2)
                self.baln.SetParameterValue(NUSTOUT_PAR + Balance.S_ENE, 0)
                self.ConnectPorts('BalEneSensor', OUT_PORT, 'EneBalance', IN_PORT + 'Q1')
                
                
    def ValidateParameter(self, paramName, value):
        if not super(EquilibriumReactor, self).ValidateParameter(paramName, value):
            return False
        
        if paramName == QEXOTHERMIC_ISPOS_PAR:
            if value != 0 and value != 1:
                return False
        
        return True
            
    def DeleteObject(self, obj):
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() == QEXOTHERMIC_ISPOS_PAR:
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return
            
        super(EquilibriumReactor, self).DeleteObject(obj)
    
    def GetObject(self, name):
        obj = super(EquilibriumReactor, self).GetObject(name)
        if not obj:
            obj = self.itnRxn.GetObject(name)
        return obj

    def GrabSignalPorts(self, nuRxns):
        """
        Borrow the iso-thermal reactor conversion ports
        """
        # clear all signal port
        self.ports_sig.clear()
        # restore the delP signal port
        self.BorrowChildPort(self.itnRxn.GetPort(DELTAP_PORT), DELTAP_PORT)
        # add the conversion port
        #ports = self.itnRxn.GetPorts(SIG)
        #for port in ports:
        #    self.BorrowChildPort(port, port.GetName())
        UnitOperations.UnitOperation.SetParameterValue(self, NURXN_PAR, nuRxns)               

