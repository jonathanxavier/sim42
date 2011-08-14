"""Models a Kinetic Reactor
"""

import UnitOperations, BaseForReactors
from sim.solver.Variables import *
from sim.solver import S42Glob
from sim.solver import EquationSolver, Flowsheet
from sim.solver.Messages import MessageHandler

import numpy
from numpy.oldnumeric import array, Float, Int, ones, zeros, matrixmultiply, absolute, where
import math, string, copy, re, operator
PI = math.pi


from sim.unitop import PipeSegment  #Import this just to have the same constants
from sim.unitop import Stream

#Generic reactor constants
from BaseForReactors import QEXOTHERMIC_ISPOS_PAR, REACTION, NURXN_PAR, RXNORDER_PAR
from BaseForReactors import ReactorObject


#Specific constants for this unit ops
VOL_PORT = 'Volume'
RXN_RATE_EQ_PAR = 'ReactionRateEq'
CUSTOM_EQ_UNITSET_PAR = 'CustomEquationUnitSet'
RXNPHASE_PAR = 'ReactionPhase'
AV_SYSTEMPHASE_PAR = 'AvSystemPhases'
SYSTEMPHASE_PAR = 'SystemPhase'
R = 8.314  #Constant
ADVKINETIC_PAR = 'AdvancedKinetics'
FWDA_PAR = 'FwdA'
FWDE_PAR = 'FwdE'
REVA_PAR = 'RevA'
REVE_PAR = 'RevE'
RXNNOTES_PAR = 'Notes'
FWDORDER_PAR = 'FwdOrder_'
REVORDER_PAR = 'RevOrder_'


INTEGRATOR_OBJ = 'Integrator' #Name of object that will contain the integration algorithms


_mathFuncs = filter(lambda x: not '_' in x, math.__dict__.keys())
_operators = ['=', '==', '+', '-', '*', '/', '\\', '**', '^']
_reservedWords = ['glbX', 'glbUnitOp']
_validStrings = ['Path']
_validStrings.extend(_mathFuncs)
_validStrings.extend(_operators)
_validStrings.extend(['for', 'in', 'break', 'range', 'len', 'if', 'elif', 'else', 'pass', 
                      'R', 'T', 'P', 'H', 'MoleFlow', 'MassFlow', 'VolumeFlow', 
                      'Concentration', 'Fraction', 'MassFraction', 'rxnCmp'])

#_reStripAndCommentOut = re.compile(r'(^\s*)|(\s*#.*)')   #Find left and right spaces and comments out
_reCommentOut = re.compile(r'#.*')
_reTokenizeEqn = re.compile(r'[=*/+\-^]{1,2}|[\w.]+')

glbUnitOp = None
glbX = None

USES_Q = 0
USES_U = 1
USES_UEQN = 2

class CompoundInfo(object):
    """dummy holder of info for a compound"""
    def __init__(self, name):
        name = re.sub(' ', '_', name)
        self.Name = name
        self.Fraction = None
        self.MassFraction = None
        self.Concentration = None
        self.P = None
        
    def Clone(self):
        clone = self.__class__(self.Name)
        for key in self.__dict__:
            clone.__dict__[key] = UnitOperations._SafeClone(self.__dict__[key])
        return clone

def Path(path):
    """Returns a value depending on a path. The output depends on the namespace under which the method is ran"""
    global glbUnitOp
    global glbX
    global R
    
    nuCmps = glbUnitOp._nuCmps
    value = None
    
    #Return the iteration value, rather than the current port value
    splitPath = path.split('.')
    nuTokens = len(splitPath)
    
    #Likely a property
    if nuTokens == 2:
        prop = splitPath[1]
        
        #From the inlet port
        if splitPath[0] == IN_PORT:
            
            #Iteration properties
            if prop == T_VAR:
                return glbX[glbUnitOp._T0Idx]
            elif prop == P_VAR:
                return glbUnitOp._P0
            elif prop == MOLEFLOW_VAR:
                flows = glbX[glbUnitOp._1stFCmp0Idx:glbUnitOp._1stFCmp0Idx+nuCmps]
                return Numeric.sum(flows)
            
            #Extensive variables
            elif prop == MASSFLOW_VAR:
                flows = glbX[glbUnitOp._1stFCmp0Idx:glbUnitOp._1stFCmp0Idx+nuCmps]
                massFlow = Numeric.sum(flows * glbUnitOp._pureCmpMW)
                return massFlow
            elif prop == VOLFLOW_VAR:
                P, T = glbX[glbUnitOp._T0Idx], glbUnitOp._P0
                flows = glbX[glbUnitOp._1stFCmp0Idx:glbUnitOp._1stFCmp0Idx+nuCmps]
                molarFlow = Numeric.sum(flows)
                fracs = flows/molarFlow
                propList = [MOLARV_VAR]
                molarVol = glbUnitOp.GetProperties(P, T, fracs, propList)[0]
                return molarFlow*molarVol
            
            #Intensive variables
            else:
                try:
                    P, T = glbX[glbUnitOp._T0Idx], glbUnitOp._P0
                    flows = glbX[glbUnitOp._1stFCmp0Idx:glbUnitOp._1stFCmp0Idx+nuCmps]
                    fracs = flows/Numeric.sum(flows)
                    propList = [prop]
                    vals = glbUnitOp.GetProperties(P, T, fracs, propList)
                    return vals[0]
                except:
                    pass
                
        #From the outlet port
        elif splitPath[0] == OUT_PORT:
            if prop == T_VAR:
                return glbX[glbUnitOp._TIdx]
            elif prop == P_VAR:
                return glbUnitOp._P
            elif prop == MOLEFLOW_VAR:
                flows = glbX[glbUnitOp._1stFCmpIdx:glbUnitOp._1stFCmpIdx+nuCmps]
                return Numeric.sum(flows)
            
            #Extensive variables
            elif prop == MASSFLOW_VAR:
                flows = glbX[glbUnitOp._1stFCmpIdx:glbUnitOp._1stFCmpIdx+nuCmps]
                massFlow = Numeric.sum(flows * glbUnitOp._pureCmpMW)
                return massFlow
            elif prop == VOLFLOW_VAR:
                P, T = glbX[glbUnitOp._TIdx], glbUnitOp._P
                flows = glbX[glbUnitOp._1stFCmpIdx:glbUnitOp._1stFCmpIdx+nuCmps]
                molarFlow = Numeric.sum(flows)
                fracs = flows/molarFlow
                propList = [MOLARV_VAR]
                molarVol = glbUnitOp.GetProperties(P, T, fracs, propList)[0]
                return molarFlow*molarVol
            
            #Intensive variables
            else:
                try:
                    P, T = glbX[glbUnitOp._TIdx], glbUnitOp._P
                    flows = glbX[glbUnitOp._1stFCmpIdx:glbUnitOp._1stFCmpIdx+nuCmps]
                    fracs = flows/Numeric.sum(flows)
                    propList = [prop]
                    vals = glbUnitOp.GetProperties(P, T, fracs, propList)
                    return vals[0]
                except:
                    pass

    #Likely a property of a specific compound
    elif nuTokens == 3:
        prop, cmpName = splitPath[1], splitPath[2]
        cmpName = re.sub('_', ' ', cmpName)
        cmpIdx = -1
        cmpNames = glbUnitOp.inPort.GetCompoundNames()
        try: cmpIdx = cmpNames.index(cmpName)
        except: pass
        #From the inlet port
        if splitPath[0] == IN_PORT and cmpIdx >= 0:
            flows = glbX[glbUnitOp._1stFCmp0Idx:glbUnitOp._1stFCmp0Idx+nuCmps]
            if prop == FRAC_VAR:
                fracs = flows/Numeric.sum(flows)
                return fracs[cmpIdx]
            elif prop == MASSFRAC_VAR:
                massFlows = flows * glbUnitOp._pureCmpMW
                massFracs = massFlows/Numeric.sum(massFlows)
                return massFracs[cmpIdx]
            elif prop == LNFUG_VAR or prop == "LnFugacityCoefficient" or prop == "LnActivityCoefficient":
                try:
                    P, T = glbX[glbUnitOp._T0Idx], glbUnitOp._P0
                    fracs = flows/Numeric.sum(flows)
                    vals = glbUnitOp.GetArrayProperty(P, T, fracs, prop)
                    return vals[cmpIdx]
                except:
                    pass
                
        #From the outlet port
        elif splitPath[0] == OUT_PORT and cmpIdx >= 0:
            flows = glbX[glbUnitOp._1stFCmpIdx:glbUnitOp._1stFCmpIdx+nuCmps]
            if prop == FRAC_VAR:
                fracs = flows/Numeric.sum(flows)
                return fracs[cmpIdx]
            elif prop == MASSFRAC_VAR:
                massFlows = flows * glbUnitOp._pureCmpMW
                massFracs = massFlows/Numeric.sum(massFlows)
                return massFracs[cmpIdx]
            elif prop == LNFUG_VAR or prop == "LnFugacityCoefficient" or prop == "LnActivityCoefficient":
                try:
                    P, T = glbX[glbUnitOp._TIdx], glbUnitOp._P
                    fracs = flows/Numeric.sum(flows)
                    vals = glbUnitOp.GetArrayProperty(P, T, fracs, prop)
                    return vals[cmpIdx]
                except:
                    pass

    #Reactor volume
    elif path == VOL_PORT:
        return glbX[glbUnitOp._VIdx]
    
    #Energy port
    elif path == '%sQ' %OUT_PORT:
        return glbX[glbUnitOp._QIdx]
        
    #Generic implementation
    tokens = path.split('.')
    obj = glbUnitOp
    for token in tokens:
        obj = obj.GetObject(token)
        value = obj.GetValue()
    
    return value
    
        
class KineticReaction(BaseForReactors.Reaction):
    def __init__(self, initScript=None):
        super(KineticReaction, self).__init__(initScript)
        self.InitKinetics()

    def InitKinetics(self):
        self.SetParameterValue(ADVKINETIC_PAR, 0)
        self.SetParameterValue(FWDA_PAR, None)
        self.SetParameterValue(FWDE_PAR, None)
        self.SetParameterValue(REVA_PAR, None)
        self.SetParameterValue(REVE_PAR, None)
        self.SetParameterValue(RXNNOTES_PAR, '')
        self.SetParameterValue(CUSTOM_EQ_UNITSET_PAR, None)   # None = Use the unit set from the reactor

    def AdjustOldCase(self, version):
        #Note that there is no adjustments for compound reaction orders
        super(KineticReaction, self).AdjustOldCase(version)
        if not self.parameters.has_key(ADVKINETIC_PAR):
            self.InitKinetics()
            #all previous cases have the kinetics equation defined
            self.SetParameterValue(ADVKINETIC_PAR, 1)
            
        
    def AddedToParent(self, parentUO, name):
        """Add a sample rate equation"""
        super(KineticReaction, self).AddedToParent(parentUO, name)
        defaultRxn = """
r = 0
"""     
        self.SetParameterValue(RXN_RATE_EQ_PAR, defaultRxn)
        
    def SetParameterValue(self, paramName, value):
        super(KineticReaction, self).SetParameterValue(paramName, value)
        if paramName == RXN_RATE_EQ_PAR:
            self.GetParent().ForgetAllCalculations()

            self.parameters[RXN_RATE_EQ_PAR] = value
            if '^' in value:
                value = value.replace('^', '**')
                self.parameters[RXN_RATE_EQ_PAR] = value
                self.InfoMessage('Changed^For**',  (self.GetPath(), '\n' + value))
            if '\r' in value:
                value = value.replace('\r', '')
                self.parameters[RXN_RATE_EQ_PAR] = value
            # switch to advance kinetics when equation is supplied
            self.parameters[ADVKINETIC_PAR] = 1
        #delete parameter if order = 0
        elif paramName.find(FWDORDER_PAR) == 0 or paramName.find(REVORDER_PAR) == 0:
            if value == 0 and self.parameters.has_key(paramName):
                del self.parameters[paramName]
            
    def DeleteCompound(self, cmpName):
        """Deletes a compound from the reaction"""
        super(KineticReaction, self).DeleteCompound(cmpName)
        # remove the reaction order parameters
        cmp = re.sub('_', ' ', cmpName)
        if self.parameters.has_key(FWDORDER_PAR + cmp):
            del self.parameters[FWDORDER_PAR + cmp]
        if self.parameters.has_key(REVORDER_PAR + cmp):
            del self.parameters[REVORDER_PAR + cmp]       

                
    def ValidateParameter(self, paramName, value):
        if not super(KineticReaction, self).ValidateParameter(paramName, value):
            return False
        if paramName == RXN_RATE_EQ_PAR:
            #Validate the equation such that it can be used in an eval statement
            lines = re.split(r'\n', value)
            allValidStrings = []
            allValidStrings.extend(_validStrings)
            cmpNames = self.GetCompoundNames()
            cmpNames = map(lambda cmpName: re.sub(' ', '_', cmpName), cmpNames)
            allValidStrings.extend(cmpNames)
            for line in lines:
                line = string.strip(line)
                if not line or line[0] == '#': 
                    pass #Is a comment or empty line. Ignore
                else:
                    
                    #Divide the line in words (tokens)
                    #Those words must belong to the list of accepted strings or be assignments of new variables
                    line = _reCommentOut.sub('', line)
                    tokens = _reTokenizeEqn.findall(line)
                    nuTokens = len(tokens)
                    for i in range(nuTokens):
                        token = tokens[i]
                        valid = False
                        if token in _reservedWords:
                            self.InfoMessage('ReservedTokenInEq', (self.GetPath(), token))
                            return False
                        if not token in allValidStrings:
                            #Lets see if it is a number
                            try: 
                                if token[-1] == 'E' or token[-1] == 'e':
                                    float(token[:-1])
                                    valid = True
                                else:
                                    float(token)
                                    valid = True
                            except:
                                pass
                            
                            #See if it is a new assignment
                            if not valid and i+1 < nuTokens:
                                if tokens[i+1] == '=' and not '.' in token: #Second comparison perhaps not needed
                                    allValidStrings.insert(0, token)
                                    valid = True
                            
                            #See if it is a path
                            if not valid and i > 0 and nuTokens > 1:
                                if tokens[i-1] == 'Path':
                                    valid = True
                                    break
                                
                            #See if it is a comopund prop like rxnCmp['ETHANE'].Fraction
                            if not valid and i > 0 and nuTokens > 1:
                                if tokens[i-1] == 'rxnCmp':
                                    valid = True
                                    break
                                
                            #See if it is a compound like OXYGEN.Fraction
                            if '.' in token:
                                tokenSplit = token.split('.')
                                if len(tokenSplit) == 2 and tokenSplit[1] in allValidStrings:
                                    valid = True
                                    allValidStrings.insert(0, token)
                                
                        else:
                            valid = True
                            #Skip the whole line if it is a compound prop like rxnCmp['ETHANE'].Fraction
                            if token == 'rxnCmp':
                                break
                            
                        if not valid:
                            #There is something wrong in the equation
                            self.InfoMessage('InvalidTokenInEq', (self.GetPath(), token))
                            return False

        return True
        
        
        
class CSTR(EquationSolver.EquationBasedOp):
    """CSTR"""

    def __init__(self, initScript=None):
        """
        create the ports and init the balance
        """
        
        super(CSTR, self).__init__(initScript)
        
        self._numMethodSetings.solveMethod = EquationSolver.SECANT
        
        #An inlet and aoutlet material port
        self.inPort = self.CreatePort(IN|MAT, IN_PORT)
        self.inPort.SetLocked(True)
        self.outPort = self.CreatePort(OUT|MAT, OUT_PORT)
        self.outPort.SetLocked(True)
        
        #an outlet energy port
        self.enePort = self.CreatePort(OUT|ENE, OUT_PORT + 'Q')
        self.enePort.SetLocked(True)
        
        #delta p port
        self.dpPort = self.CreatePort(SIG, DELTAP_PORT)
        self.dpPort.SetSignalType(DELTAP_VAR)
        self.dpPort.SetLocked(True)

        #volume port
        self.volPort = self.CreatePort(SIG, VOL_PORT)
        self.volPort.SetSignalType(VOL_VAR)
        self.volPort.SetLocked(True)
        
        self.SetParameterValue(NURXN_PAR, 0)
        self.SetParameterValue(CUSTOM_EQ_UNITSET_PAR, 'sim42')
        self.SetParameterValue(RXNPHASE_PAR, OVERALL_PHASE)
        
        self.myGlobals = {'Path':Path}
        self.myGlobals.update(math.__dict__)
        
        self.activeSpecs = []
        self.inactiveSpecs = []
        self.signals = {}
        self.estimates = {}
        
   
    def __getstate__(self):
        """return info to store"""
        try: 
            state = self.__dict__.copy()
            del state['myGlobals']
            return state
        except: 
            return self.__dict__
        
    def __setstate__(self, oldState):
        """build packages from saved info"""
        self.__dict__ = oldState
        self.myGlobals = {'Path':Path}
        self.myGlobals.update(math.__dict__)
        
    def CleanUp(self):
        self._cmpInfoHolders = []
        self.myGlobals = {}
        self._thCaseObj = None
        for signal in self.signals.values():
            signal.CleanUp()
            
        for signal in self.estimates.values():
            signal.CleanUp()
        super(CSTR, self).CleanUp()
        
        
    def AdjustOldCase(self, version):
        super(CSTR, self).AdjustOldCase(version)
        if version[0] < 28:
            if not self.GetParameterValue(CUSTOM_EQ_UNITSET_PAR):
                self.SetParameterValue(CUSTOM_EQ_UNITSET_PAR, 'sim42')
                
        if version[0] < 70:
            if not hasattr(self, 'estimates'):
                self.estimates = {}
            if not hasattr(self, 'signals'):
                self.signals = {}
            if not hasattr(self, 'activeSpecs'):
                self.activeSpecs = []
            if not hasattr(self, 'inactiveSpecs'):
                self.inactiveSpecs = []
        
    def GetListOfReqParam(self): 
        return (NURXN_PAR,)

    def ParameterChanged(self, paramName, value):
        super(CSTR, self).ParameterChanged(paramName, value)
        if paramName == NURXN_PAR: 
            self.UpdateRxnCount()
            
    def ValidateParameter(self, paramName, value):
        if not super(CSTR, self).ValidateParameter(paramName, value):
            return False
        
        if paramName == CUSTOM_EQ_UNITSET_PAR:
            if not value in S42Glob.unitSystem.GetSetNames():
                return False
            
        if paramName == RXNPHASE_PAR:
            if not value in (LIQUID_PHASE, VAPOUR_PHASE, OVERALL_PHASE, None):
                return False
        return True
            
    def UpdateRxnCount(self):
        """Update the amount and names of the ports in"""      
        nuRxns = len(self.GetChildUnitOps())
        rxnIn = self.parameters[NURXN_PAR]
        
        for i in range(nuRxns, rxnIn, -1):
            self.DelUnitOperation(REACTION + str(i - 1))

        for i in range(nuRxns, rxnIn):
            rxn = KineticReaction()
            rxn.SetParameterValue(RXNORDER_PAR, i+1)
            self.AddUnitOperation(rxn, REACTION + str(i))
           
    def RemoveRxn(self, name):
        self.DelUnitOperation(name)

        
    def AssignResults(self, vals):
        """Assign the results into the appropriate ports"""
        
        isFix = self._unknowns.GetIsFixed()
        
        if not isFix[self._1stFCmp0Idx]:
            z0 = vals[self._1stFCmp0Idx:self._1stFCmp0Idx+self._nuCmps]
            F0 = Numeric.sum(z0)
            z0 = z0/F0
            self.inPort.SetPropValue(MOLEFLOW_VAR, F0, CALCULATED_V)
            self.inPort.SetCompositionValues(z0, CALCULATED_V)        

        if not isFix[self._1stFCmpIdx]:
            z = vals[self._1stFCmpIdx:self._1stFCmpIdx+self._nuCmps]
            F = Numeric.sum(z)
            z = z/F
            self.outPort.SetPropValue(MOLEFLOW_VAR, F, CALCULATED_V)
            self.outPort.SetCompositionValues(z, CALCULATED_V)                
            
        if not isFix[self._VIdx]:
            self.volPort.SetValue(vals[self._VIdx], CALCULATED_V)
            
        if not isFix[self._T0Idx]:
            self.inPort.SetPropValue(T_VAR, vals[self._T0Idx], CALCULATED_V)            

        if not isFix[self._TIdx]:
            self.outPort.SetPropValue(T_VAR, vals[self._TIdx], CALCULATED_V)  

        if not isFix[self._QIdx]:
            self.enePort.SetValue(vals[self._QIdx], CALCULATED_V)
          
        ##No needed to flash all ports. It is done by the main Solve method         
                        

    def Solve(self):
        """Add a mass balance check"""
        
        #Put this stuff here rather than in LoadUnknowns so it always gets done
        activeSpecs = self.activeSpecs = []
        inactiveSpecs = self.inactiveSpecs = []
        for signal in self.signals.values():
            signal.Reset()
            if signal.value != None:
                activeSpecs.append(signal)
            else:
                inactiveSpecs.append(signal)   
        self.converged = 0
        super(CSTR, self).Solve()
        
        #Mass balance check for inconsistencies
        massFlow = self.inPort.GetPropValue(MASSFLOW_VAR)
        if massFlow != None:
            self.outPort.SetPropValue(MASSFLOW_VAR, massFlow, CALCULATED_V)
            
        if self.converged:
            for signal in self.signals.values():
                signal.AssignResultsToPort()
        else:
            try:
                if not self.IsForgetting():
                    for signal in self.inactiveSpecs:
                        if hasattr(signal, 'SolveFromPortValues'):
                            signal.SolveFromPortValues()
            except:
                pass
            
            
    def GetNuSpecsNeeded(self):
        #Number of specs needed is just a substractions on unknwons - nu equations
        nuCmps = len(self.inPort.GetCompounds())
        nuUnk = 4 + 2*nuCmps
        nuEqns = 1 + nuCmps
        return nuUnk - nuEqns
    
    def SolveForPressure(self):
        """Calculate for any known from PIn, POut, dP"""
        PIn = self.inPort.GetPropValue(P_VAR)
        POut = self.outPort.GetPropValue(P_VAR)
        dP = self.dpPort.GetValue()
        if PIn != None and POut != None:
            self.dpPort.SetValue(PIn - POut, CALCULATED_V)
        elif PIn != None and dP != None:
            self.outPort.SetPropValue(P_VAR, PIn-dP, CALCULATED_V)
        elif POut != None and dP != None:
            self.inPort.SetPropValue(P_VAR, POut+dP, CALCULATED_V)
        
            
    def PrepareForSolve(self):
        """Solve what can be solved; load variables used in simultaneous solution and return False if not ready for simultaneous solution"""
        
        ready = True

        #Get thermo
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: return False
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        
        #scale factors
        p = self.inPort
        self.scaleFactorF = p.GetProperty(MOLEFLOW_VAR).GetType().scaleFactor        #In kmol/h
        self.scaleFactorP = p.GetProperty(P_VAR).GetType().scaleFactor               #In kPa
        self.scaleFactorT = p.GetProperty(T_VAR).GetType().scaleFactor               #In K  
        self.scaleFactorQ = p.GetProperty(ENERGY_VAR).GetType().scaleFactor          #In J/s
        self.scaleFactorV = self.volPort.GetType().scaleFactor

        self.solids = self.GetParameterValue(NUSOLPH_PAR)
        if self.solids == None:
            self.solids = 0
        
        self.SolveForPressure()
        self.FlashAllPorts()

        self._P0 = self.inPort.GetPropValue(P_VAR)
        self._P = self.outPort.GetPropValue(P_VAR)
        self._nuCmps = len(self.inPort.GetCompounds())
        self._nuRxn = self.parameters.get(NURXN_PAR, None)
        if not self._P0 or not  self._P or not self._nuCmps or not self._nuRxn:
            ready = False
        
        self._stoichCoeffsArray = self.GetStoichCoeffsArray()
        if not self._stoichCoeffsArray:
            ready = False
            
        #Get molecular weights and load reaction rate expressions if it is ready to solve
        if ready:
            self._pureCmpMW = zeros(self._nuCmps, Float)
            for i in range(self._nuCmps):
                #Note: cmpMwt is an array with only one element because only one prop (Mwt) was requested
                self._pureCmpMW[i] = thAdmin.GetSelectedCompoundProperties(prov, case, i, 'MolecularWeight')[0]

            self._unitSet = []
            self._rateExpressions = []
            allSetsEqual = True
            for i in range(self._nuRxn):
                rxn = self.GetChildUO(REACTION + str(i))
                rateExp = rxn.GetParameterValue(RXN_RATE_EQ_PAR)
                if not rateExp:
                    self.InfoMessage('MissingRateExpression', (rxn.GetPath(), ))
                    ready = False
                self._rateExpressions.append(rateExp)
                unitSet = S42Glob.unitSystem.GetUnitSet(rxn.GetParameterValue(CUSTOM_EQ_UNITSET_PAR))
                if i == 0 and allSetsEqual: firstSet = unitSet
                elif firstSet != unitSet: allSetsEqual = True
                self._unitSet.append(unitSet)
            if allSetsEqual and self._nuRxn:
                self._unitSet = self._unitSet[0]
        
        if ready:
            self._cmpInfoHolders = []
            for name in self.GetCompoundNames():
                self._cmpInfoHolders.append(CompoundInfo(name))
            
            self._rxnPhase = self.GetParameterValue(RXNPHASE_PAR)
            if self._rxnPhase == None:
                self._rxnPhase = OVERALL_PHASE
                
        return ready
        
    def GetStoichCoeffsArray(self):
        """Builds a Numeric array with the stoich coeffs of all the reactions. Returns None if not ready"""
        
        #Make sure it can solve
        nuRxn = self.parameters.get(NURXN_PAR, None)
        if not nuRxn: return None
        
        cmps = self.inPort.GetCompounds()
        if not cmps: return None
        nuCmps = len(cmps)
        
        
        #Dimension variables
        coeffsArr = zeros((nuCmps, nuRxn), Float)
        
        #Load variables
        for j in range(nuRxn):
            rxn = self.GetChildUO(REACTION + str(j))
            if not rxn: return None
            if not rxn.stoichCoeffs: return None
            coeffsArr[:, j] = rxn.stoichCoeffs
                
        return coeffsArr
        
    
    def LoadUnknowns(self, u):

        pIn = self.inPort
        pOut = self.outPort
        
        #Request necessary variables
        F0 = pIn.GetPropValue(MOLEFLOW_VAR)
        T0 = pIn.GetPropValue(T_VAR)
        z0 = pIn.GetCompositionValues()
        F = pOut.GetPropValue(MOLEFLOW_VAR)
        T = pOut.GetPropValue(T_VAR)
        z = pOut.GetCompositionValues()
        Q = self.enePort.GetValue()
        V = self.volPort.GetValue()
        
        #Check if inlet flows are known
        missingInlet = False
        if None != F0 and not None in z0:
            FCmp0 = F0 * Numeric.array(z0, Float)
            if F0:
                self.scaleFactorF = F0/self._nuCmps
        else:
            missingInlet = True
            
        #Check if outlet flows are known
        missingOutlet = False
        if None != F and not None in z:
            FCmp = F * Numeric.array(z, Float)
            if F:
                self.scaleFactorF = F/self._nuCmps
        elif missingInlet:
            #Can not solve if an inlet or an outlet composition are not known
            return False
        else:
            missingOutlet = True

        #Initialize by copying each other
        if missingInlet:
            FCmp0 = array(FCmp, Float)
        elif missingOutlet:
            FCmp = array(FCmp0, Float)
        
        #Load inlet as unknowns
        isSpec = not missingInlet
        for i in range(self._nuCmps):
            name = 'InletFlowCmp_%d' % i
            tempUnkVar = EquationSolver.SolverVariable(name, FCmp0[i], FCmp0[i], isSpec, self.scaleFactorF, 0.0)
            unkIdx = u.AddUnknown(tempUnkVar) #Returns the index where the unk was put
            if i == 0: self._1stFCmp0Idx = unkIdx
        
        
        #Load outlet as unknowns
        isSpec = not missingOutlet
        usedSpec = False
        for i in range(self._nuCmps):
            name = 'OutletFlowCmp_%d' % i
            if not missingOutlet and not missingInlet:
                #in this case only use up to one flow as spec
                if not usedSpec and not 0 in self._stoichCoeffsArray[i, :]:
                    usedSpec = True
                else:
                    isSpec = False
            tempUnkVar = EquationSolver.SolverVariable(name, FCmp[i], FCmp[i], isSpec, self.scaleFactorF, 0.0)
            unkIdx = u.AddUnknown(tempUnkVar) #Returns the index where the unk was put
            if i == 0: self._1stFCmpIdx = unkIdx                

            
        #Can not solve
        if T0 == None and T == None:
            return False

        
        #Now load temperatures
        isSpec = True
        if T0 == None:
            isSpec = False
            T0 = T
        name = 'T0'
        tempUnkVar = EquationSolver.SolverVariable(name, T0, T0, isSpec, self.scaleFactorT, 0.0)
        self._T0Idx = u.AddUnknown(tempUnkVar) #Returns the index where the unk was put           
        
        isSpec = True
        if T == None:
            isSpec = False
            T = T0
        name = 'T'
        tempUnkVar = EquationSolver.SolverVariable(name, T, T, isSpec, self.scaleFactorT, 0.0)
        self._TIdx = u.AddUnknown(tempUnkVar) #Returns the index where the unk was put

        
        #Finally do Volume and Energy flow
        isSpec = True
        if V == None:
            isSpec = False
            V = 1.0 #What to do??
        name = 'V'
        tempUnkVar = EquationSolver.SolverVariable(name, V, V, isSpec, self.scaleFactorV, 0.0)
        self._VIdx = u.AddUnknown(tempUnkVar) #Returns the index where the unk was put     

        isSpec = True
        if Q == None:
            isSpec = False
            Q = 0.0 #What to do??
        name = 'Q'
        tempUnkVar = EquationSolver.SolverVariable(name, Q, Q, isSpec, self.scaleFactorQ)
        self._QIdx = u.AddUnknown(tempUnkVar) #Returns the index where the unk was put     
                
        #Check if it has enough specs
        nuSpecsNeeded = self.GetNuSpecsNeeded()
        isSpecVec = u.GetIsFixed()
        nuSpecs = Numeric.sum(isSpecVec)
        nuSpecs += len(self.activeSpecs)
        self.nuSpecs = nuSpecs
        if nuSpecs < nuSpecsNeeded:
            missSpecs = nuSpecsNeeded - nuSpecs
            self.unitOpMessage = ('Missing %i Specs' %missSpecs, )
            return False
        elif nuSpecs > nuSpecsNeeded:
            overSpecs = nuSpecs - nuSpecsNeeded
            self.unitOpMessage = ('Over Specified by %i' %overSpecs, )
            self.InfoMessage('TooManyTowerSpecs', (nuSpecs, nuSpecsNeeded, self.GetPath()))
            return False
        
        return True
    
    
    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        """Calculates the right hand side of the design equations"""

        #In this code,
        #F -> Molar flow
        #0 -> Used to designate a feed. If it is not there, then it implies a product
        #Cmp -> Used to designate something per compound
        #V -> Reactor volume
        #z -> Composition
        #C -> Concentration
        #T, P, H -> Temperature, Pressure, Enthalpy
        
        #Make self and the vector x available to the reate expression methods
        global glbUnitOp
        global glbX
        global R
        glbUnitOp = self
        glbX = x
        
        #The following variables should had been updated in the PrepareForSolve call
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        nuCmps = self._nuCmps
        nuRxn = self._nuRxn
        stoichCoeffsArray = self._stoichCoeffsArray
        rateRxn = zeros(nuRxn, Float)
        P0 = self._P0
        P = self._P
        
        #Load x into variables
        FCmp0 = x[self._1stFCmp0Idx:self._1stFCmp0Idx+nuCmps]
        FCmp = x[self._1stFCmpIdx:self._1stFCmpIdx+nuCmps]
        V = x[self._VIdx]
        T0 = x[self._T0Idx]
        T = x[self._TIdx]
        Q = x[self._QIdx]
        
        
        #Calculate some convenient variables
        F0 = Numeric.sum(FCmp0)
        F = Numeric.sum(FCmp)
        z0 = FCmp0/F0
        z = FCmp/F
        
        #Keep track of these values
        self._T0 = T0
        self._T = T
        self._z0 = z0
        self._z = z
        self._fCmp0 = FCmp0
        self._fCmp = FCmp
        
        
        #Do a flash to get some extra info
        propList = [H_VAR, 'rxnBaseH']
        H0, HBase0 = self.GetProperties(P0, T0, z0, propList, self._rxnPhase)
        
        propList = [H_VAR, 'rxnBaseH', MOLARV_VAR, MOLEWT_VAR]
        H, HBase, molarV, MW = self.GetProperties(P, T, z, propList, self._rxnPhase)
        massFlow = F*MW
        volFlow = F*molarV
        
        #Update the rate of reactions
        self.myGlobals.update({'glbUnitOp': glbUnitOp, 'glbX': glbX})
        oneSetForAll = not isinstance(self._unitSet, list)
        
        #Run the rate of reaction expression as Python code
        for i in range(self._nuRxn):
            if i == 0 or not oneSetForAll:
                #Do unit conversions for using in the custom rxn rate equation according to the
                #selected unit set
                if oneSetForAll: unitSet = self._unitSet
                else: unitSet = self._unitSet[i]

                if not unitSet: unitSet = 'sim42'
                rUnit = S42Glob.unitSystem.GetUnit(unitSet, PropTypes[RATERXNVOL_VAR].unitType)
                if unitSet != 'sim42':
                    unit = S42Glob.unitSystem.GetUnit(unitSet, S42Glob.unitSystem.GetTypeID('GasConstant'))
                    passR = unit.ConvertFromSim42(R)            
                    
                    unit = S42Glob.unitSystem.GetUnit(unitSet, PropTypes[T_VAR].unitType)
                    passT = unit.ConvertFromSim42(T)
                    
                    unit = S42Glob.unitSystem.GetUnit(unitSet, PropTypes[P_VAR].unitType)
                    passP = unit.ConvertFromSim42(P)
                    
                    unit = S42Glob.unitSystem.GetUnit(unitSet, PropTypes[H_VAR].unitType)
                    passH = unit.ConvertFromSim42(H)
                    
                    unit = S42Glob.unitSystem.GetUnit(unitSet, PropTypes[MOLEFLOW_VAR].unitType)
                    passF = unit.ConvertFromSim42(F)
                    
                    passMassFlow = passF*MW
                    
                    unit = S42Glob.unitSystem.GetUnit(unitSet, PropTypes[VOLFLOW_VAR].unitType)
                    passVolFlow = unit.ConvertFromSim42(volFlow)            
                else:
                    passR, passT, passP, passH = R, T, P, H
                    passF, passMassFlow, passVolFlow = F, massFlow, volFlow
                    
                baseLocals = {'R': passR, 'T': passT, 'P': passP, 'H': passH, 
                              'MoleFlow': passF, 'MassFlow': passMassFlow, 'VolumeFlow': passVolFlow}
                    
                #Load some info of compounds
                rxnCmp = {}
                concUnit = S42Glob.unitSystem.GetUnit(unitSet, PropTypes[CONCENTRATION_VAR].unitType)
                for c in range(self._nuCmps):
                    cmpInfo = self._cmpInfoHolders[c]
                    cmpInfo.Fraction = z[c]
                    cmpInfo.Concentration = concUnit.ConvertFromSim42(FCmp[c]/(volFlow)) 
                    cmpInfo.MoleFlow = z[c]*passF
                    cmpInfo.P = z[c]*passP
                    rxnCmp[cmpInfo.Name] = cmpInfo
                baseLocals['rxnCmp'] = rxnCmp
                
            myLocals = {}
            myLocals.update(baseLocals)
            rateExp = self._rateExpressions[i]
            exec(rateExp, self.myGlobals, myLocals)
            r = myLocals.get('r', None)
            rateRxn[i] = rUnit.ConvertToSim42(r) 
                
        #Calculate rhs 
        #Mole balance (in kmol/h)
        rhs[eqnNo:eqnNo+nuCmps] = (FCmp0 - FCmp + (V * matrixmultiply(stoichCoeffsArray, rateRxn))*3600.0)/self.scaleFactorF
        eqnNo = eqnNo+nuCmps
        
        #Energy balance in J/s
        rhs[eqnNo] = ((F0*(H0+HBase0) - F*(H+HBase))/3.6 - Q)/self.scaleFactorQ
        eqnNo +=1

        #Eqn's for known vars
        for idx in range(len(x)):
            if isFix[idx]:
                rhs[eqnNo] = (x[idx] - initx[idx]) / self._unknowns._unkScaleFacts[idx]
                eqnNo += 1

        for spec in self.activeSpecs:
            rhs[eqnNo] = spec.Error()
            eqnNo += 1
                
        return eqnNo
        
    def GetProperties(self, P, T, fracs, propList, phase):
        """Gets a list of properties for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        if not self.solids:
            inProp1 = [P_VAR, P]
            inProp2 = [T_VAR, T]
            vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, propList)  #OVERALL_PHASE      
        else:
            matDict = MaterialPropertyDict()
            matDict[P_VAR].SetValue(P, FIXED_V)
            matDict[T_VAR].SetValue(T, FIXED_V)
            cmps = CompoundList(None)
            for i in range(len(fracs)):
                cmps.append(BasicProperty(FRAC_VAR))
            cmps.SetValues(fracs, FIXED_V)
            liqPhases = 1
            solPhases = self.solids
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, propList, solPhases)
            vals = results.bulkProps
        return vals      
        
    def GetArrayProperty(self, P, T, fracs, prop):
        """Gets an array property in the gas phase for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        inProp1 = [P_VAR, P]
        inProp2 = [T_VAR, T]
        vals = thAdmin.GetArrayProperties(prov, case, inProp1, inProp2, VAPOUR_PHASE, fracs, prop)        
        return vals
    
    
    def AddObject(self, obj, name):
        """adds an object to the appropriate container, based on its type"""
        
        if isinstance(obj, ReactorObject):
            prevObj = self.GetObject(name)
            if prevObj:
                raise SimError('CantAddObject', (name, self.GetPath()))
    
            self.LinkToObject(obj, name)
            try:
                obj.Initialize(self, name)
            except:
                obj.UnlinkObject(self, obj)
                raise
            
        else:
            super(CSTR, self).AddObject(obj, name)
            
    def GetObject(self, name):
        obj = super(CSTR, self).GetObject(name)
        if obj != None: return obj
        
        obj = self.signals.get(name, None)
        if obj != None: return obj
        
        obj = self.estimates.get(name, None)
        if obj != None: return obj
        
        return None
            
    def GetContents(self):
        results = super(CSTR, self).GetContents()
        for k, v in self.signals.items():
            results.append((k, v))
        for k, v in self.estimates.items():
            results.append((k, v))
        return results
        
    def DeleteObject(self, obj):
        """
        check that we aren't deleting a port
        """
        if isinstance(obj, Ports.Port) and self is obj.GetParent():
            #All the ports that are created and owned in this unit op are administerd by objects.
            #Do not allow direct deletion of those objects.
            #The rest of the many ports that are displayed by this unit op are all borrowed from child unit ops
            #The deletion of those ports should be processed normally
            raise SimError('CantDelPortDirectly', (obj.GetPath(), self.GetPath()))
        elif isinstance(obj, ReactorObject):
            try:
                locked = obj.locked
            except AttributeError:
                locked = False
                
            if locked:
                raise SimError('CannotRemoveLockedObject', obj.GetPath())
            else:
                self.UnlinkObject(obj)
                obj.CleanUp()
                
        else:
            super(CSTR, self).DeleteObject(obj)
        
    def LinkToObject(self, obj, name):
        """
        add object to the appropriate dictionary using name
        """
        
        if isinstance(obj, ReactorObject):
            if 0:#isinstance(obj, EstimatePerSide):
                ###Redundant check, but just in case
                ##if self.estimates.get(name, None) != None:
                    ##raise SimError('CantAddObject', (name, self.GetPath()))
                ##self.estimates[name] = obj
                pass
            else:
                #Redundant check, but just in case
                if self.signals.get(name, None) != None:
                    raise SimError('CantAddObject', (name, self.GetPath()))
                self.signals[name] = obj
            
        #Lets not unconverge or resolve for now.
        
    def UnlinkObject(self, obj):
        """remove obj from the appropriate list"""
        if self.signals.has_key(obj.name):
            del self.signals[obj.name]
            if obj in self.activeSpecs:
                idx = self.activeSpecs.index(obj)
                del self.activeSpecs[idx]
            if obj in self.inactiveSpecs:
                idx = self.inactiveSpecs.index(obj)
                del self.inactiveSpecs[idx]
        if self.estimates.has_key(obj.name):
            del self.estimates[obj.name]
    def ChangeObjectName(self, fromName, toName):
        if fromName in self.signals.keys():
            self.signals[toName] = self.signals[fromName]
            self.signals[toName].name = toName
            del self.signals[fromName]
        elif fromName in self.estimates.keys():
            self.estimates[toName] = self.estimates[fromName]
            self.estimates[toName].name = toName
            del self.estimates[fromName]
    
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(CSTR, self)._RemoveFromCloneList(clone, attrNamesToClone)
        
        dontClone = ["activeSpecs", "inactiveSpecs", "myGlobals"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
            
class PFR(EquationSolver.EquationBasedOp):
    def __init__(self, initScript=None):
        """
        create the ports and init the balance
        """
        
        super(PFR, self).__init__(initScript)
        
        self.usesHTEqn = False
        self.usesDPEqn = False

        #Generic call for creating ports
        self.CreatePorts()
        self.SetParameterValue(NUSECTIONS_PAR, 10)
        self.SetParameterValue(NURXN_PAR, 0)
        self.SetParameterValue(CUSTOM_EQ_UNITSET_PAR, 'sim42')
        self.SetParameterValue(SYSTEMPHASE_PAR, 'Overall')
        self.parameters[AV_SYSTEMPHASE_PAR] = 'Overall Vapour Liquid'
        
        self.myGlobals = {'Path':Path}
        self.myGlobals.update(math.__dict__)
        
        self.activeSpecs = []
        self.inactiveSpecs = []
        self.signals = {}
        self.estimates = {}
        
        self.integrator = None
        self.AddObject(EquationSolver.Integrator(), INTEGRATOR_OBJ)
        self.SetParameterValue(EquationSolver.SOLVE_METH_PAR, EquationSolver.EULER_IMPL)
        
    def __getstate__(self):
        """return info to store"""
        try: 
            state = self.__dict__.copy()
            del state['myGlobals']
        
            if state['integrator']:
                #Don't store the integrator object
                #as it could be custom made
                try:
                    #The str(type(state['integrator'])) call returns something like this:
                    #"<class 'EquationSolver.Integrator'>"
                    #Change it to something like this:
                    #'Integrator'
                    s = str(type(state['integrator'])).split(' ', 1)[1][1:-2]
                    state['integrator'] = s
                except:
                    pass
            return state
        
        
        except: 
            return self.__dict__
        
    def __setstate__(self, oldState):
        """build packages from saved info"""
        self.__dict__ = oldState
        self.myGlobals = {'Path':Path}
        self.myGlobals.update(math.__dict__)
        
        if self.__dict__.has_key('integrator'):
            if self.integrator:
                try:
                    #The integrator object was stored as a string. 
                    #Try to recreate it as an a object
                    lstMods = self.integrator.split('.', 1)
                    if len(lstMods) > 1:
                        exec('import %s' %lstMods[0])
                    integrator = eval('%s()' %self.integrator)
                    self.integrator = None
                    self.AddObject(integrator, INTEGRATOR_OBJ)
                except:
                    #self.InfoMessage('CouldNotRestorePlugIn', (str(self.integrator), ))
                    integrator = EquationSolver.Integrator()
                    self.integrator = None
                    self.AddObject(integrator, INTEGRATOR_OBJ)
        
    def CleanUp(self):
        self._cmpInfoHolders = []
        self.myGlobals = {}
        self._thCaseObj = None
        try:
            self.integrator.CleanUp()
            self.integrator = None
        except:
            pass
        super(PFR, self).CleanUp()
        
    def AdjustOldCase(self, version):
        super(PFR, self).AdjustOldCase(version)
        if version[0] < 55:
            self.parameters[EquationSolver.AV_SOLVE_METH_PAR] = '%s %s %s' %(EquationSolver.EULER_IMPL,
                                                                                   EquationSolver.EULER,
                                                                                   EquationSolver.RK4)
            self.parameters[AV_SYSTEMPHASE_PAR] = 'Overall Vapour Liquid'
            self.parameters[SYSTEMPHASE_PAR] = 'Overall'
            self.CreateHeatTransferPorts()
            
        if version[0] < 68:
            if not hasattr(self, 'integrator'):
                self.integrator = None
                self.AddObject(EquationSolver.Integrator(), INTEGRATOR_OBJ)
        if version[0] < 71:
            if not hasattr(self, 'estimates'):
                self.estimates = {}
            if not hasattr(self, 'signals'):
                self.signals = {}
            if not hasattr(self, 'activeSpecs'):
                self.activeSpecs = []
            if not hasattr(self, 'inactiveSpecs'):
                self.inactiveSpecs = []

                
    def CreatePorts(self):
        """This method can be used to manipulate creation of ports with methods and facilitate inheritance"""
        self.CreateBasicPorts()
        self.CreatePipePorts()
        self.CreateHeatTransferPorts()
        #self.CreateDeltaPCalcPorts()
        
        #volume port
        self.volPort = self.CreatePort(SIG, VOL_PORT)
        self.volPort.SetSignalType(VOL_VAR)
        self.volPort.SetLocked(True)        
        
    def CreateBasicPorts(self):
        """Common ports that are generally used by unit operations"""
        self.inPort = self.CreatePort(IN|MAT, IN_PORT)
        self.inPort.SetLocked(True)
        self.outPort = self.CreatePort(OUT|MAT, OUT_PORT)
        self.outPort.SetLocked(True)

        self.enePort = self.CreatePort(OUT|ENE, OUT_PORT + 'Q')
        self.enePort.SetLocked(True)

        self.dpPort = self.CreatePort(SIG, DELTAP_PORT)
        self.dpPort.SetSignalType(DELTAP_VAR)
        self.dpPort.SetLocked(True)
        
        
    def CreateHeatTransferPorts(self):
        """Ports that are used by heat transfer calculations"""
        if not self.GetPort(U_PORT):
            self.uPort = self.CreatePort(SIG, U_PORT)
            self.uPort.SetSignalType(U_VAR)
            self.uPort.SetLocked(True)
        
        if not self.GetPort(PipeSegment.EXT_T_PORT):
            self.ambTPort = self.CreatePort(SIG, PipeSegment.EXT_T_PORT)
            self.ambTPort.SetSignalType(T_VAR)
            self.ambTPort.SetLocked(True)
            self.ambTPort.SetValue(298.15, FIXED_V)
        
    def CreatePipePorts(self):
        """Ports that are commonly used by a pipe"""
        self.lenPort = self.CreatePort(SIG, PipeSegment.LENGTH_PORT)
        self.lenPort.SetSignalType(LENGTH_VAR)
        self.lenPort.SetLocked(True)
        
        self.diamPort = self.CreatePort(SIG, PipeSegment.DIAM_PORT)
        self.diamPort.SetSignalType(LENGTH_VAR)
        self.diamPort.SetLocked(True)
        
    def CreateDeltaPCalcPorts(self):
        """Ports that are commonly used for pressure drop calculations in pipes"""
        if not self.GetPort(ROUGH_PORT):
            self.roughPort = self.CreatePort(SIG, PipeSegment.ROUGH_PORT)
            self.roughPort.SetSignalType(LENGTH_VAR)        
            self.roughPort.SetLocked(True)
        
        if not self.GetPort(ELEVATION_PORT + '0'):
            self.z0Port = self.CreatePort(SIG, PipeSegment.ELEVATION_PORT + '0')
            self.z0Port.SetSignalType(LENGTH_VAR)        
            self.z0Port.SetLocked(True)
        
        if not self.GetPort(ELEVATION_PORT + '1'):
            self.z1Port = self.CreatePort(SIG, PipeSegment.ELEVATION_PORT + '1')
            self.z1Port.SetSignalType(LENGTH_VAR)        
            self.z1Port.SetLocked(True)

        
    def ParameterChanged(self, paramName, value):
        super(PFR, self).ParameterChanged(paramName, value)
        if paramName == NUSECTIONS_PAR:
            nuSections = self._nuSections = value
            #Dimension variables
            self.P = zeros(nuSections+1, Float)
            self.H = zeros(nuSections+1, Float)
            self.Q = zeros(nuSections, Float)
            self.U = zeros(nuSections, Float)
            
            self._PIdx = zeros(nuSections+1, Int)
            self._HIdx = zeros(nuSections+1, Int)
            self._QIdx = zeros(nuSections, Int)
            self._UIdx = zeros(nuSections, Int)
            
            self._nuEqns = nuSections*3
            self._nuUnk = nuSections*4 + 3
            
        elif paramName == NURXN_PAR: 
            self.UpdateRxnCount()
            

    def GetStoichCoeffsArray(self):
        """Builds a Numeric array with the stoich coeffs of all the reactions. Returns None if not ready"""
        
        #Make sure it can solve
        nuRxn = self.parameters.get(NURXN_PAR, None)
        if not nuRxn: return None
        
        cmps = self.inPort.GetCompounds()
        if not cmps: return None
        nuCmps = len(cmps)
        
        
        #Dimension variables
        coeffsArr = zeros((nuCmps, nuRxn), Float)
        
        #Load variables
        for j in range(nuRxn):
            rxn = self.GetChildUO(REACTION + str(j))
            if not rxn: return None
            if not rxn.stoichCoeffs: return None
            coeffsArr[:, j] = rxn.stoichCoeffs
                
        return coeffsArr
    
            
    def ValidateParameter(self, paramName, value):
        
        
        if not super(PFR, self).ValidateParameter(paramName, value):
            return False
        
        if paramName == NUSECTIONS_PAR:
            if value < 1:
                return False
        
        if paramName == CUSTOM_EQ_UNITSET_PAR:
            if not value in S42Glob.unitSystem.GetSetNames():
                return False
            
        if paramName == SYSTEMPHASE_PAR:
            validVals = self.parameters.get(AV_SYSTEMPHASE_PAR, None)
            if validVals:
                validVals = validVals.split()
                if value not in validVals:
                    return False
                
        #if paramName == AV_SYSTEMPHASE_PAR:
            #return False
                
        return True
            
    def UpdateRxnCount(self):
        """Update the amount and names of the ports in"""      
        nuRxns = len(self.GetChildUnitOps())
        rxnIn = self.parameters[NURXN_PAR]
        
        for i in range(nuRxns, rxnIn, -1):
            self.DelUnitOperation(REACTION + str(i - 1))

        for i in range(nuRxns, rxnIn):
            rxn = KineticReaction()
            rxn.SetParameterValue(RXNORDER_PAR, i+1)
            self.AddUnitOperation(rxn, REACTION + str(i))
           
    def RemoveRxn(self, name):
        self.DelUnitOperation(name)
        
    def AssignResultsFromIntegrator(self):
        if self.P:
            self.outPort.SetPropValue(P_VAR, self.P[self.stepCount-1], CALCULATED_V)
            self.P = self.P[:self.stepCount]
        if self.T:
            self.outPort.SetPropValue(T_VAR, self.T[self.stepCount-1], CALCULATED_V)
            self.T = self.T[:self.stepCount]
        if self.F:
            self.outPort.SetPropValue(MOLEFLOW_VAR, self.F[self.stepCount-1], CALCULATED_V)
            self.F = self.F[:self.stepCount]
        if self.f:
            z = self.f[self.stepCount-1, :]/Numeric.sum(self.f[self.stepCount-1, :])
            self.outPort.SetCompositionValues(z, CALCULATED_V)
            self.f = self.f[:self.stepCount, :]
        if self.Q:
            self.Q = self.Q[:self.stepCount]
        if self.r:
            self.r = self.r[:self.stepCount, :]
        if self.C:
            self.C = self.C[:self.stepCount, :]
            
            
    def IsZeroFlow(self):
        flow = self.inPort.GetPropValue(MOLEFLOW_VAR)
        if flow == 0.0: 
            self.outPort.SetPropValue(MOLEFLOW_VAR, 0.0, CALCULATED_V)
            return True
        
        flow = self.outPort.GetPropValue(MOLEFLOW_VAR)
        if flow == 0.0: 
            self.inPort.SetPropValue(MOLEFLOW_VAR, 0.0, CALCULATED_V)        
            return True
        
        return False
        
        
    def Solve(self):
        """Decide if integrate or solve simoultaneous"""
        method = self._numMethodSetings.solveMethod
        
        self.LoadPhase()
        
        #Integrate
        
        ready = self.PrepareForSolve()
        if not ready: return
        
        if self.IsZeroFlow(): return
        
        if self.IsForgetting(): return
        
        self.y0, yMin, yMax, yScale = self.GetInitValsForIntegrator()
        if not self.y0: return
        
        #Dimension arrays
        nuSections = self._nuSections
        self.ClearArrays()
        self.DimensionArrays(nuSections+1)
        
        #Find the enthalpy in the inlet with reactive basis added
        port = self.inPort
        z0 = port.GetCompositionValues()
        h0 = port.GetPropValue(H_VAR)
        mf0 = port. GetPropValue(MOLEFLOW_VAR)
        h0Base = self.GetPropertiesFromPT(0.0, 0.0, z0, ['rxnBaseH'], LIQUID_PHASE)[0]
        self.absQ0 = (h0 + h0Base) * mf0
        
        
        self.stepCount = 0
        init = self._numMethodSetings.init = 0.0
        end = self._numMethodSetings.end = self._len
        self._numMethodSetings.step = (end-init)/(float(nuSections))
        if self.integrator == None:
            self.AddObject(EquationSolver.Integrator(), INTEGRATOR_OBJ)
            
        #Initialize these variables
        activeSpecs = self.activeSpecs = []
        inactiveSpecs = self.inactiveSpecs = []
        for signal in self.signals.values():
            signal.Reset()
            if signal.value != None:
                activeSpecs.append(signal)
            else:
                inactiveSpecs.append(signal)
                
        self._P0 = None
        self._P = None
        self._T0 = None
        self._T = None
        self._z0 = None
        self._z = None
        self._fCmp0 = None
        self._fCmp = None
        
        #Can not solve for signals as specs yet
        
        if self.solveMode == "DirectIntegration":
            converged = self.integrator.Integrate(self.y0, self._numMethodSetings, yMin, yMax, yScale)
            
        elif self.solveMode == "TOutSpecIterOnQ":
            
            #Load some variables
            maxIter = 30
            converged = 0
            iter = 0
            Integrate = self.integrator.Integrate
            y0 = self.y0
            nms = self._numMethodSetings
            tIn = self._inT
            tOut = self.tOut
            maxStep = 1.0E5
            scale = 100.0
            tolerance = nms.tolerance
            
            #Do a first try
            qIter = 0.0
            self._totQ = qIter
            self.stepCount = 0
            Integrate(y0, nms, yMin, yMax, yScale)
            t = self.T[self.stepCount-1]
            err = tOut - t
            if abs(err)/scale < tolerance:
                converged = 1
                
            #Prepare for the iterations
            errOld = err
            qOld = qIter
            qIter = qIter + 1.0E3
            while not converged and iter <= maxIter:
                iter += 1
                self._totQ = qIter
                self.stepCount = 0
                Integrate(y0, nms, yMin, yMax, yScale)
                t = self.T[self.stepCount-1]
                err = tOut - t
                if abs(err)/scale < tolerance:
                    converged = 1
                    break
                
                #Update based on last error
                dErr_dQ = (err - errOld) / (qIter - qOld)
                dQ = -err / dErr_dQ
                dQ = min(max(-maxStep, dQ), maxStep)
                
                #Update variables
                errOld = err
                qOld = qIter
                qIter = dQ + qOld
                
                
        #Redimension arrays to the exact number of steps taken
        self.DimensionArrays(self.stepCount)
        if converged:
            self.AssignResultsFromIntegrator()
            self.FlashAllPorts()
            self.enePort.SetValue(-self.Q[self.stepCount-1]/3.6, CALCULATED_V)
            
            #Finally, input u if necessary:
            if self.eneMode == USES_Q and self.tAmb:
                avgVal = Numeric.sum(self.U)/len(self.U)
                self.uPort.SetValue(avgVal, CALCULATED_V)      #W/cm2K
                
        else:
            self.unitOpMessage = ('CouldNotSolve', ())
            
        
        #Mass balance check for inconsistencies
        massFlow = self.inPort.GetPropValue(MASSFLOW_VAR)
        if massFlow != None:
            self.outPort.SetPropValue(MASSFLOW_VAR, massFlow, CALCULATED_V)
            
            
        #Load some variables such that the signals can picke them up
        inPort = self.inPort
        outPort = self.outPort
        self._P0 = inPort.GetPropValue(P_VAR)
        self._P = outPort.GetPropValue(P_VAR)
        self._T0 = inPort.GetPropValue(T_VAR)
        self._T = outPort.GetPropValue(T_VAR)
        self._z0 = inPort.GetCompositionValues()
        self._z = outPort.GetCompositionValues()
        mf0 = inPort.GetPropValue(MOLEFLOW_VAR)
        if mf0 != None and self._z0 != None and not None in self._z0:
            self._z0 = array(self._z0, Float)
            self._fCmp0 = mf0 * self._z0
        mf = outPort.GetPropValue(MOLEFLOW_VAR)
        if mf != None and self._z != None and not None in self._z:
            self._z = array(self._z, Float)
            self._fCmp = mf * self._z
            
        for signal in self.signals.values():
            signal.AssignResultsToPort()
            
            
    def LoadPhase(self):
        """Load the phase into the member variable"""
        self.phase = OVERALL_PHASE
        phase = self.GetParameterValue(SYSTEMPHASE_PAR)
        if phase:
            if phase == 'Vapour' or phase == VAPOUR_PHASE or phase == 'Vapor':
                self.phase = VAPOUR_PHASE
            elif phase == 'Liquid' or phase == LIQUID_PHASE:
                self.phase = LIQUID_PHASE
        
        
    def ClearArrays(self):
        """Clear all the arrays"""
        self.F = None
        self.T = None
        self.P = None
        self.Q = None
        self.H = None
        self.x = None
        self.r = None
        self.f = None
        self.C = None
        self.U = None
        
            
    def DimensionArrays(self, length):
        """Used to dimension arrays for the first time or to redimension to a new size without losing old vals"""
        if self.F == None: 
            self.F = zeros(length, Float)
        else:
            oldLen = len(self.F)
            if oldLen >= length:
                self.F = self.F[:length]
            else:
                temp = array(self.F, Float)
                self.F = zeros(length, Float)
                self.F[:oldLen] = temp
                
        if self.T == None: 
            self.T = zeros(length, Float)
        else:
            oldLen = len(self.T)
            if oldLen >= length:
                self.T = self.T[:length]
            else:
                temp = array(self.T, Float)
                self.T = zeros(length, Float)
                self.T[:oldLen] = temp
                
        if self.P == None: 
            self.P = zeros(length, Float)
        else:
            oldLen = len(self.P)
            if oldLen >= length:
                self.P = self.P[:length]
            else:
                temp = array(self.P, Float)
                self.P = zeros(length, Float)
                self.P[:oldLen] = temp
        
        if self.Q == None: 
            self.Q = zeros(length, Float)
        else:
            oldLen = len(self.Q)
            if oldLen >= length:
                self.Q = self.Q[:length]
            else:
                temp = array(self.Q, Float)
                self.Q = zeros(length, Float)
                self.Q[:oldLen] = temp
        
        if self.U == None: 
            self.U = zeros(length, Float)
        else:
            oldLen = len(self.U)
            if oldLen >= length:
                self.U = self.U[:length]
            else:
                temp = array(self.U, Float)
                self.U = zeros(length, Float)
                self.U[:oldLen] = temp
                
        if self.H == None: 
            self.H = zeros(length, Float)
        else:
            oldLen = len(self.H)
            if oldLen >= length:
                self.H = self.H[:length]
            else:
                temp = array(self.H, Float)
                self.H = zeros(length, Float)
                self.H[:oldLen] = temp
                
        if self.x == None: 
            self.x = zeros(length, Float)
        else:
            oldLen = len(self.x)
            if oldLen >= length:
                self.x = self.x[:length]
            else:
                temp = array(self.x, Float)
                self.x = zeros(length, Float)
                self.x[:oldLen] = temp
                
        if self.r == None: 
            self.r = zeros((length, self._nuRxn), Float)
        else:
            oldLen = len(self.r)
            if oldLen >= length:
                self.r = self.r[:length, :]
            else:
                temp = array(self.r, Float)
                self.r = zeros((length, self._nuRxn), Float)
                self.r[:oldLen, :] = temp
        
        if self.f == None: 
            self.f = zeros((length, self._nuCmps), Float)
        else:
            oldLen = len(self.f)
            if oldLen >= length:
                self.f = self.f[:length, :]
            else:
                temp = array(self.f, Float)
                self.f = zeros((length, self._nuCmps), Float)
                self.f[:oldLen, :] = temp
                
        if self.C == None: 
            self.C = zeros((length, self._nuCmps), Float)
        else:
            oldLen = len(self.C)
            if oldLen >= length:
                self.C = self.C[:length, :]
            else:
                temp = array(self.C, Float)
                self.C = zeros((length, self._nuCmps), Float)
                self.C[:oldLen, :] = temp
                
                
        
    def GetNuSpecsNeeded(self):
        #Number of specs needed is just a substractions on unknwons - nu equations
        return self._nuUnk - self._nuEqns
    
    
    def GetInitValsForIntegrator(self):
        """The inlet has to be fully defined in order to integrate"""
        self.solveMode = "DirectIntegration"
        
        F = self.inPort.GetPropValue(MOLEFLOW_VAR)
        if F == None: return None, None, None, None
        
        self._inP = self.inPort.GetPropValue(P_VAR)
        if self._inP == None: return None, None, None, None
        
        self._inT = self.inPort.GetPropValue(T_VAR)
        if self._inT == None: return None, None, None, None
        
        self._inH = self.inPort.GetPropValue(H_VAR)
        if self._inH == None: return None, None, None, None    
        
        self._totQ = self.enePort.GetValue()   #W
        self.tAmb = self.ambTPort.GetValue()   #K
        self.u = self.uPort.GetValue()         #W/(cm2*K)
        if self.u != None and self.tAmb != None:
            self.eneMode = USES_U
        elif self._totQ != None:
            self.eneMode = USES_Q
        else:
            self.tOut = self.outPort.GetPropValue(T_VAR)
            if self.tOut == None:
                return None, None, None, None
            self.eneMode = USES_Q
            self.solveMode = "TOutSpecIterOnQ"
            
        if not self.usesDPEqn:
            self._outP = self.outPort.GetPropValue(P_VAR)
            if self._outP == None:
                return None, None, None, None
            
        #Dimension
        nuCmps = self._nuCmps
        otherVars = 2 #Q and P
        yInit = zeros(nuCmps+otherVars, Float)
        yMin = -1.0E40*ones(nuCmps+otherVars, Float)
        yMax = 1.0E40*ones(nuCmps+otherVars, Float)
        yScale = ones(nuCmps+otherVars, Float)
        
        
        #Quick way to find a max flow
        coeffs = self._stoichCoeffsArray
        zReactants = Numeric.clip(coeffs, -1E100, 0.0)
        zProducts = Numeric.clip(coeffs, 0.0, 1E100)
        zReactants = Numeric.sum(zReactants)
        zProducts = Numeric.sum(zProducts)
        tempVal1 = Numeric.sum(zProducts)
        tempVal2 = -1.0*Numeric.sum(zReactants)
        tempVal = 1.0
        if type(tempVal1) == type(array(())):
            for i in range(len(tempVal1)):
                if tempVal1[i] > tempVal2[i]:
                    tempVal *= tempVal1[i] / tempVal2[i]
                else:
                    tempVal *= tempVal2[i] / tempVal1[i]
        else:
            if tempVal1 > tempVal2:
                tempVal *= tempVal1 / tempVal2
            else:
                tempVal *= tempVal2 / tempVal1
        maxF = tempVal * F
        
        #Flows
        yInit[:nuCmps] = array(self._fracs)*F
        yMin[:nuCmps] *= 0.0
        yMax[:nuCmps] = maxF
        yScale[:nuCmps] = max((1.0, max(absolute(yInit[:nuCmps]))))
        
        #Q
        yInit[nuCmps] = 0.0
        yScale[nuCmps] = 10000.0
        yMax[nuCmps] = 1.0E10
        yMin[nuCmps] = -1.0E10
        
        #Pressure
        yInit[nuCmps+1] = self._inP
        yMin[nuCmps+1] = 1.0E-8
        yScale[nuCmps+1] = self._inP
        
        return yInit, yMin, yMax, yScale
    
        
    def CalculateDerivatives(self, x, y, loadResults=False):
        """This method gets called by the integrator and receives a vector y and returns a vector dy
           if loadResults is true, then it means that it is time to load info to the profiles
        """
        
        #Make self and the vector x available to the reate expression methods
        global glbUnitOp
        global glbX
        global R
        glbUnitOp = self
        glbX = x
        
        stoichCoeffsArray = self._stoichCoeffsArray
        nuRxn = self._nuRxn
        nuCmps = self._nuCmps
        diam = self._diam
        crossArea = self._area
        
        rateRxn = zeros(nuRxn, Float)
        hRxn = zeros(nuRxn, Float)
        
        f = y[:nuCmps]         #kmol/h
        Q = y[nuCmps]          #kJ/(h)
        P = y[nuCmps+1]        #kPa
        F = Numeric.sum(f)     #kmol/h
        z = f/F
                
        
        #We have P and composition. We are missing H which will be obtained from a balance
        HBase = self.GetPropertiesFromPT(0.0, 0.0, z, ['rxnBaseH'], LIQUID_PHASE)[0]
        H = (Q + self.absQ0) / F - HBase
        propList = [T_VAR, MOLARV_VAR, MOLEWT_VAR, CP_VAR]
        T, molarV, MW, cp = self.GetProperties(P, H, z, propList, self.phase) #K, m3/kmol, -, kJ/(kmol-K)
        
        #Flows
        massFlow = F*MW                                       #kg/h
        volFlow = F*molarV                                    #m3/h
        
        #Update the rate of reactions
        self.myGlobals.update({'glbUnitOp': glbUnitOp, 'glbX': glbX})
        oneSetForAll = not isinstance(self._unitSet, list)
        
        GetUnit = S42Glob.unitSystem.GetUnit
        for i in range(nuRxn):
            if i == 0 or not oneSetForAll:
                #Do unit conversions for using in the custom equation according to the
                #selected unit set
                if oneSetForAll: unitSet = self._unitSet
                else: unitSet = self._unitSet[i]
                
                if not unitSet: unitSet = 'sim42'
                rUnit = GetUnit(unitSet, PropTypes[RATERXNVOL_VAR].unitType)
                if unitSet != 'sim42':
                    unit = GetUnit(unitSet, S42Glob.unitSystem.GetTypeID('GasConstant'))
                    passR = unit.ConvertFromSim42(R)            
                    
                    unit = GetUnit(unitSet, PropTypes[T_VAR].unitType)
                    passT = unit.ConvertFromSim42(T)
                    
                    unit = GetUnit(unitSet, PropTypes[P_VAR].unitType)
                    passP = unit.ConvertFromSim42(P)
                    
                    unit = GetUnit(unitSet, PropTypes[H_VAR].unitType)
                    passH = unit.ConvertFromSim42(H)
                    
                    unit = GetUnit(unitSet, PropTypes[MOLEFLOW_VAR].unitType)
                    passF = unit.ConvertFromSim42(F)
                    
                    passMassFlow = passF*MW
                    
                    unit = GetUnit(unitSet, PropTypes[VOLFLOW_VAR].unitType)
                    passVolFlow = unit.ConvertFromSim42(volFlow)
                else:
                    passR, passT, passP, passH = R, T, P, H
                    passF, passMassFlow, passVolFlow = F, massFlow, volFlow
                    
                #Update the rate of reactions
                #Run the rate of reaction expression as Python code

                baseLocals = {'R': passR, 'T': passT, 'P': passP, 'H': passH, 
                              'MoleFlow': passF, 'MassFlow': passMassFlow, 'VolumeFlow': passVolFlow}
                
                #Load some info of compounds
                rxnCmp = {}
                concUnit = GetUnit(unitSet, PropTypes[CONCENTRATION_VAR].unitType)
                for c in range(self._nuCmps):
                    cmpInfo = self._cmpInfoHolders[c]
                    cmpInfo.Fraction = z[c]
                    cmpInfo.Concentration = concUnit.ConvertFromSim42(f[c]/(volFlow)) 
                    cmpInfo.MoleFlow = z[c]*passF
                    cmpInfo.P = z[c]*passP
                    rxnCmp[cmpInfo.Name] = cmpInfo
                baseLocals['rxnCmp'] = rxnCmp
        
            
            myLocals = {}
            myLocals.update(baseLocals)
            rateExp = self._rateExpressions[i]
            exec(rateExp, self.myGlobals, myLocals)
            r = myLocals.get('r', None)
            rateRxn[i] = rUnit.ConvertToSim42(r) 
        
            coeffs = stoichCoeffsArray[:, i]
            
        self.lastRateRxn = rateRxn
        
        
        #Mole balance (in kmol/h). 
        #Change in flow of each cmp per unit of length is the matrix product of stoich*rateRxn
        dF_dLen = self._area * matrixmultiply(stoichCoeffsArray, rateRxn) * 3600.0
        
        #Energy balance
        if self.eneMode == USES_Q:
            qFlow = 3.6*self._totQ/self._len                         #((s*kJ)/(h*J)) * W / m -> kJ/(m*h)
            dQ_dLen = -qFlow                                         #kJ/(m*h)
            
        elif self.eneMode == USES_U:
            u = self.u * (100.0**2)                                  #W/(cm2*K) -> W/(m2*K)
            qFlow = u * PI * diam * (T-self.tAmb) * 3.6              #W/(m2*K) * (m) * (K) * ((s*kJ)/(h*J))-> kJ/(m*h)
            dQ_dLen = -qFlow                                         #kJ/(m*h)
            
        ##elif self.eneMode == USES_UEQN:
            ##u = self.CalcU()
            ##qFlow = u * PI * diam * (T-tAmb) * 3.6                   #W/(m2*K) * (m) * (K) * ((s*kJ)/(h*J))-> kJ/(m*h)
            ##qRxn = -crossArea * Numeric.sum(hRxn*rateRxn) * 3600.0   #(m2) * (kJ/kmol) * (kmol/(s*m3) * (s/h) -> kJ/(m*h)
            ##dT_dLen = (qRxn  - qFlow) / (F*cp)
            
        #Momentum balance
        if not self.usesDPEqn:
            dP_dLen = ((self._outP - self._inP)/self._len)
        else:
            dP_dLen = ((self._outP - self._inP)/self._len)

        
        dy = zeros(len(y), Float)
        dy[:self._nuCmps] = dF_dLen
        dy[self._nuCmps] = dQ_dLen
        dy[self._nuCmps+1] = dP_dLen

        if loadResults:
            length = len(self.P)-1
            if length < self.stepCount: self.DimensionArrays(length + 31)
            self.P[self.stepCount] = P
            self.T[self.stepCount] = T
            self.H[self.stepCount] = H
            self.r[self.stepCount, :] = rateRxn
            self.F[self.stepCount] = F
            self.f[self.stepCount, :] = f
            self.C[self.stepCount, :] = f/(volFlow)
            self.x[self.stepCount] = x
            self.Q[self.stepCount] = Q
            if self.eneMode == USES_U:
                self.U[self.stepCount] = self.u
            elif self.eneMode == USES_Q and self.tAmb:
                u = qFlow / (PI * diam * (T-self.tAmb) * 3.6)  #W/(m2*K)
                self.U[self.stepCount] = u / (100.0**2)        #W/(m2*K) -> W/(cm2*K)
            else:
                self.U[self.stepCount] = 0.0
            self.stepCount +=1        
        
        return dy
    
                

    def RoundValues(self, y, yMin, yMax, yScale):
        """Make negative traces of flow = 0 and negative trace temperatures = to their min value"""
        
        minAllowedFlow = 1.0E-10
        
        nuCmps = self._nuCmps
        f = y[:nuCmps]         #kmol/h
        
        minf = min(f)
        
        if min(f) < minAllowedFlow:
            #Which values are lower that the smallest allowed flow?
            valsToModif = map(operator.ge, absolute(f), minAllowedFlow*ones(nuCmps, Float))
            
            #Round to 0.0
            f = where(valsToModif, f, 0.0)
        
            
        y[:nuCmps] = f        #kmol/h
        
        return y
    
        
    def StepToBoundaries(self, x, y, h):
        """Force the variables to hit their boundaries. This is used for very stiff reactions
        that are very close to 0.0 flow in reactants but the integrator is having troubles reaching that value.
        x = Current step
        y = vector with state variable values that went over boundaries
        h = Step size taken from x.
        the return value is a vector with the values of y as if they reached their boundaries going from
        x to x+h
        """
        
        nuCmps = self._nuCmps
        f = y[:nuCmps]         #kmol/h
        F = Numeric.sum(f)     #kmol/h
        z = f/F
        
        #Looking good. Just leave
        if min(z) >= 0.0: return y
        
        Q = y[nuCmps]          #K
        P = y[nuCmps+1]        #kPa
        
        #Need to drive reactions to 0.0 instead of negative flows
        #To do this use an equation of the type deltaf/deltax = a*stoich*r  
        #deltaf is a vector per cmp of changes in flow from previous step to the next step
        #deltax is a length
        #a is an area
        #stoich is a matrix with stoich coefficients per reaction
        #r is a vector of reaction rates
        #the * stands for a matrix multiplication.
        #The proposed equation keeps everything under stoichiometry and keeps the reaction rate proportional
        #The algorithm is... (j stands for a compound idx and i is used for rxn idx and * is always a matrix multiplication where possible)
        #1) Find a compound that goes below zero and make deltaf_j = 0.0 - lastf_j
        #2) Find deltax as deltax = deltaf_j / (a*stoich_j*r)
        #3) Backcalculate deltaf = deltax*a*stoich*r
        #4) If none value in newf < 0.0 where newf = deltaf + lastf then go to (5) else go to (1)
        #5) Use newf as the new values for flows and back calculate an enthalpy
        
        #Get info from last step
        r = self.lastRateRxn
        lastf = self.f[self.stepCount-1, :]
        
        epsilon = 1.0E-15
        stoich = self._stoichCoeffsArray
        a = self._area
        deltaxVec = zeros(nuCmps, Float)
        success = False
        mindeltax = None
        for j in range(nuCmps):
            if f[j] < 0.0:
                #a and the unit conversion are not really needed for this purpose, but they
                #provide a meaningful deltax which could be used later on for a reasonable estimate of where
                #the reactions stop occuring
                deltaf_j = epsilon - lastf[j]
                deltax = deltaf_j /( a * matrixmultiply(stoich[j], r) * 3600.0 )
                if mindeltax == None: mindeltax = deltax
                if deltax <= mindeltax:
                    mindeltax = deltax
                else:
                    continue
                deltaf = deltax * a * matrixmultiply(stoich, r) * 3600.0 
                newf = deltaf + lastf
                if min(newf) >= 0.0:
                    success = True
                    break
        while not success:
            mindeltax = mindeltax * 0.5
            deltaf = mindeltax * a * matrixmultiply(stoich, r) * 3600.0 
            newf = deltaf + lastf
            if min(newf) >= 0.0:
                success = True
                break
                
        yNew = array(y, Float)
        yNew[:nuCmps] = newf
        
        return yNew
    
    def SolveForPressure(self):
        """Calculate for any known from PIn, POut, dP"""
        PIn = self.inPort.GetPropValue(P_VAR)
        POut = self.outPort.GetPropValue(P_VAR)
        dP = self.dpPort.GetValue()
        if PIn != None and POut != None:
            self.dpPort.SetValue(PIn - POut, CALCULATED_V)
        elif PIn != None and dP != None:
            self.outPort.SetPropValue(P_VAR, PIn-dP, CALCULATED_V)
        elif POut != None and dP != None:
            self.inPort.SetPropValue(P_VAR, POut+dP, CALCULATED_V)
        
    def SolveForVolume(self):
        """Solve for volume from D and len"""
        diam = self.diamPort.GetValue()
        len = self.lenPort.GetValue()
        vol = self.volPort.GetValue()
        if diam != None and len != None:
            self.volPort.SetValue(len * PI*(diam/2.0)**2, CALCULATED_V)
        elif diam != None and vol != None:
            self.lenPort.SetValue(vol / (PI*(diam/2.0)**2), CALCULATED_V)
        elif len != None and vol != None:
            self.diamPort.SetValue(2.0 * math.sqrt(vol/(len*PI)), CALCULATED_V)
    
    def PrepareForSolve(self):
        """Solve what can before going into numerical method"""
        
        ready = True

        #Get thermo
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: return False
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        
        self._nuRxn = self.GetParameterValue(NURXN_PAR)
        self._fracs = self.inPort.GetCompositionValues()
        self._nuCmps = nuCmps = len(self.inPort.GetCompounds())
        self.solids = self.GetParameterValue(NUSOLPH_PAR)
        if self.solids == None:
            self.solids = 0

        if not self._fracs or None in self._fracs:
            ready = False
        else:
            self._MW = self.inPort.GetPropValue(MOLEWT_VAR)
            if not self._MW:
                MWLst = []
                for i in range(nuCmps):
                    #Note: cmpMwt is an array with only one element because only one prop (Mwt) was requested
                    MWLst.append(thAdmin.GetSelectedCompoundProperties(prov, case, i, 'MolecularWeight')[0])
                self._MW = Numeric.sum(array(MWLst, Float) * array(self._fracs, Float))

            self._unitSet = []
            self._rateExpressions = []
            allSetsEqual = True
            self._rateExpressions = []
            for i in range(self._nuRxn):
                rxn = self.GetChildUO(REACTION + str(i))
                rateExp = rxn.GetParameterValue(RXN_RATE_EQ_PAR)
                if not rateExp:
                    self.InfoMessage('MissingRateExpression', (rxn.GetPath(), ))
                    ready = False
                self._rateExpressions.append(rateExp)
                unitSet = S42Glob.unitSystem.GetUnitSet(rxn.GetParameterValue(CUSTOM_EQ_UNITSET_PAR))
                if i == 0 and allSetsEqual: firstSet = unitSet
                elif firstSet != unitSet: allSetsEqual = True
                self._unitSet.append(unitSet)
            if allSetsEqual and self._nuRxn:
                self._unitSet = self._unitSet[0]
                
                
        self._stoichCoeffsArray = self.GetStoichCoeffsArray()
        if not self._stoichCoeffsArray:
            ready = False
                    
        self.SolveForPressure()
        self.SolveForVolume()
        self.FlashAllPorts()

        self._diam = self.diamPort.GetValue()
        self._len = self.lenPort.GetValue()
        if None in (self._diam, self._len):
            ready = False
        else:
            self._area = PI * (self._diam / 2.0)**2       #Cross sectional
            self._surfArea = PI * self._diam * self._len  #Surface area
            
        if self.usesDPEqn:
            self._z0 = self.z0Port.GetValue()
            self._z1 = self.z1Port.GetValue()
            self._rough = self.roughPort.GetValue()
            if None in (self._diam, self._len, self._z0, self._z1, self._rough):
                ready = False
            else:
                self._relRough = self._rough/self._diam
        
        self.tAmb = self.ambTPort.GetValue()
        
                
        #scale factors
        p = self.inPort
        self.scaleFactorW = p.GetProperty(MASSFLOW_VAR).GetType().scaleFactor/3600.0 #In kg/s
        self.scaleFactorP = p.GetProperty(P_VAR).GetType().scaleFactor * 1000.0 #In Pa
        self.scaleFactorH = p.GetProperty(H_VAR).GetType().scaleFactor * 1000.0 #In J/kg  
        self.scaleFactorPD = self.scaleFactorP / 1000.0
        self.scaleFactorQ = self.enePort.GetType().scaleFactor
        #self.scaleFactorU = self.uPort.GetType().scaleFactor * (100.0**2) 
        
        self._nuSections = self.GetParameterValue(NUSECTIONS_PAR)
        if not self._nuSections:
            self._nuSections = 1
            self.SetParameterValue(NUSECTIONS_PAR, self._nuSections)
        
        if ready:
            self._cmpInfoHolders = []
            for name in self.GetCompoundNames():
                self._cmpInfoHolders.append(CompoundInfo(name))
                
            self._rxnPhase = self.GetParameterValue(RXNPHASE_PAR)
            if self._rxnPhase == None:
                self._rxnPhase = OVERALL_PHASE
                
        return ready
        
    
    def FricLoss(self, den0, den1, v0, v1, visc0, visc1):
        """Calculate friction loss"""
        v = 0.5 * (v0 + v1)
        den = 0.5 * (den0 + den1)
        visc = 0.5 * (visc0 + visc1)
        
        Re = den * self._diam * v / visc
        fricIsNeg = False
        if Re < 0.0:
            fricIsNeg = True
            Re = -1.0*Re
        
        #Calc friction Factor using Churchill's formula which is good for both turbulent and laminar flow
        A = (2.457 * math.log(1.0 / ((7.0/Re) ** 0.9 + (0.27 * self._relRough)))) ** 16
        B = (37530.0 / Re) ** 16
        ff = 8.0 * ((8.0 / Re) ** 12 + 1.0 / (A + B) ** 1.5) ** (1.0 / 12.0)
        ff = ff / 4.0    # 'Conver to Fanning friction factor
        val = ff * (self._len/self._nuSections) / self._diam * v * v * 0.5    
        
        if fricIsNeg:
            val = -1.0*val
            
        return val       
        
        
    def GetProperties(self, P, H, fracs, propList, phase):
        """Gets density for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        if not self.solids:
            inProp1 = [P_VAR, P]
            inProp2 = [H_VAR, H]
            vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, propList)
        else:
            matDict = MaterialPropertyDict()
            matDict[P_VAR].SetValue(P, FIXED_V)
            matDict[H_VAR].SetValue(H, FIXED_V)
            cmps = CompoundList(None)
            for i in range(len(fracs)):
                cmps.append(BasicProperty(FRAC_VAR))
            cmps.SetValues(fracs, FIXED_V)
            liqPhases = 1
            solPhases = self.solids
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, propList, solPhases)
            vals = results.bulkProps
        return vals
    
    def GetPropertiesFromPT(self, P, T, fracs, propList, phase):
        """Gets properties for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        if not self.solids or propList == ['rxnBaseH'] or propList == ('rxnBaseH',):
            inProp1 = [P_VAR, P]
            inProp2 = [T_VAR, T]
            vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, propList)
        else:
            matDict = MaterialPropertyDict()
            matDict[P_VAR].SetValue(P, FIXED_V)
            matDict[T_VAR].SetValue(T, FIXED_V)
            cmps = CompoundList(None)
            for i in range(len(fracs)):
                cmps.append(BasicProperty(FRAC_VAR))
            cmps.SetValues(fracs, FIXED_V)
            liqPhases = 1
            solPhases = self.solids
            results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, propList, solPhases)
            vals = results.bulkProps
        return vals      

    def GetPropertyVecs(self, P, H, fracs, propList, phase):
        """Gets density for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        inProp1 = [P_VAR, P]
        inProp2 = [H_VAR, H]
        phase = phase*ones(len(P), Int)
        fracs = fracs*ones((len(P), len(fracs)), Float)
        vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, propList)
        return vals  
    
        
        
    def AddObject(self, obj, name):
        """adds an object to the appropriate container, based on its type"""
        
        if isinstance(obj, EquationSolver.Integrator):
            if name != INTEGRATOR_OBJ:
                self.InfoMessage('CantChangeName', (INTEGRATOR_OBJ,), MessageHandler.errorMessage)
                #Should it really raise an error ??
                raise SimError ('CantChangeName', (INTEGRATOR_OBJ,))
            if self.integrator:
                self.DeleteObject(self.integrator)
            self.integrator = obj
            obj.Initialize(self, INTEGRATOR_OBJ)
            
            self.parameters[EquationSolver.AV_SOLVE_METH_PAR] = ' '.join(obj.GetAvailableMethods())
        
        elif isinstance(obj, ReactorObject):
            prevObj = self.GetObject(name)
            if prevObj:
                raise SimError('CantAddObject', (name, self.GetPath()))
    
            self.LinkToObject(obj, name)
            try:
                obj.Initialize(self, name)
            except:
                obj.UnlinkObject(self, obj)
                raise
            
        else:
            super(PFR, self).AddObject(obj, name)
            
    def GetObject(self, name):
        
        obj = super(PFR, self).GetObject(name)
        if obj != None: return obj
        
        if name == INTEGRATOR_OBJ:
            return self.integrator
        
        if name == T_VAR:
            obj = BasicArrayProperty([T_VAR], self, T_VAR)
            obj.SetValue(self.T)
            return obj
        if name == H_VAR:
            obj = BasicArrayProperty([H_VAR], self, H_VAR)
            obj.SetValue(self.H)
            return obj        
        if name == P_VAR:
            obj =  BasicArrayProperty([P_VAR], self, P_VAR)
            obj.SetValue(self.P)
            return obj        
        if name == MOLEFLOW_VAR:
            obj =  BasicArrayProperty([MOLEFLOW_VAR], self, MOLEFLOW_VAR)
            obj.SetValue(self.F)
            return obj        
        if name == CONCENTRATION_VAR:
            obj =  BasicArrayProperty([CONCENTRATION_VAR], self, CONCENTRATION_VAR)
            obj.SetValue(self.C)
            return obj        
        if name == ENERGY_VAR:
            obj =  BasicArrayProperty([ENERGY_VAR], self, ENERGY_VAR)
            obj.SetValue(self.Q)
            return obj        
        if name == 'r':
            obj =  BasicArrayProperty([RATERXNVOL_VAR], self, 'r')
            obj.SetValue(self.r)
            return obj        
        if name == 'f':
            obj =  BasicArrayProperty([MOLEFLOW_VAR], self, 'f')
            obj.SetValue(self.f)
            return obj        
        if name == 'x':
            obj = BasicArrayProperty([LENGTH_VAR], self, 'x')
            obj.SetValue(self.x)
            return obj
        if name == 'u':
            obj = BasicArrayProperty([U_VAR], self, 'u')
            obj.SetValue(self.U)
            return obj
        
        obj = self.signals.get(name, None)
        if obj != None: return obj
        
        obj = self.estimates.get(name, None)
        if obj != None: return obj
        
        return None
            
    def GetContents(self):
        results = super(PFR, self).GetContents()
        for k, v in self.signals.items():
            results.append((k, v))
        for k, v in self.estimates.items():
            results.append((k, v))
        return results
        
    def DeleteObject(self, obj):
        """
        check that we aren't deleting a port
        """
        
        #Can not remove these parameters
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() == NUSECTIONS_PAR:
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return
            if obj.GetName() == AV_SYSTEMPHASE_PAR:
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return
            if obj.GetName() == NURXN_PAR:
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return
            
        elif isinstance(obj, EquationSolver.Integrator) and self.integrator is obj:
            if hasattr(self.integrator, 'CleanUp'):
                self.integrator.CleanUp()
            self.integrator = None
            return
        elif isinstance(obj, Ports.Port) and self is obj.GetParent():
            #All the ports that are created and owned in this unit op are administerd by objects.
            #Do not allow direct deletion of those objects.
            #The rest of the many ports that are displayed by this unit op are all borrowed from child unit ops
            #The deletion of those ports should be processed normally
            raise SimError('CantDelPortDirectly', (obj.GetPath(), self.GetPath()))
        
        elif isinstance(obj, ReactorObject):
            try:
                locked = obj.locked
            except AttributeError:
                locked = False
                
            if locked:
                raise SimError('CannotRemoveLockedObject', obj.GetPath())
            else:
                self.UnlinkObject(obj)
                obj.CleanUp()
                
        super(PFR, self).DeleteObject(obj)  
        
        
    def LinkToObject(self, obj, name):
        """
        add object to the appropriate dictionary using name
        """
        
        if isinstance(obj, ReactorObject):
            if 0:#isinstance(obj, EstimatePerSide):
                ###Redundant check, but just in case
                ##if self.estimates.get(name, None) != None:
                    ##raise SimError('CantAddObject', (name, self.GetPath()))
                ##self.estimates[name] = obj
                pass
            else:
                #Redundant check, but just in case
                if self.signals.get(name, None) != None:
                    raise SimError('CantAddObject', (name, self.GetPath()))
                self.signals[name] = obj
            
        #Lets not unconverge or resolve for now.
        
    def UnlinkObject(self, obj):
        """remove obj from the appropriate list"""
        if self.signals.has_key(obj.name):
            del self.signals[obj.name]
            if obj in self.activeSpecs:
                idx = self.activeSpecs.index(obj)
                del self.activeSpecs[idx]
            if obj in self.inactiveSpecs:
                idx = self.inactiveSpecs.index(obj)
                del self.inactiveSpecs[idx]
        if self.estimates.has_key(obj.name):
            del self.estimates[obj.name]
            
    def ChangeObjectName(self, fromName, toName):
        if fromName in self.signals.keys():
            self.signals[toName] = self.signals[fromName]
            self.signals[toName].name = toName
            del self.signals[fromName]
        elif fromName in self.estimates.keys():
            self.estimates[toName] = self.estimates[fromName]
            self.estimates[toName].name = toName
            del self.estimates[fromName]
        
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(PFR, self)._RemoveFromCloneList(clone, attrNamesToClone)
        
        dontClone = ["activeSpecs", "inactiveSpecs", "myGlobals"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
        