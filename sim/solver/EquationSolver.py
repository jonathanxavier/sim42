
import numpy, math, time
from numpy.oldnumeric import array, zeros, ones, Float, Int, take, put, add, clip
from numpy.oldnumeric import transpose, dot, outerproduct, matrixmultiply, absolute, identity
from numpy.linalg import solve as solve_linear_equations, inv as inverse
from math import sqrt, pow


from sim.unitop import UnitOperations
from sim.unitop.Tower import DAMPINGFACTOR_PAR, FREQ_JAC_MSG_PAR

from sim.solver.Variables import *
from sim.solver.Messages import MessageHandler
from sim.solver.Error import SimError

SOLVE_METH_PAR = 'SolutionMethod'
AV_SOLVE_METH_PAR = 'AvSolutionMethods'
MINIMERR_PAR = 'MinimizeError'
TRYTOSOLVE_PAR = 'TryToSolve'
TRYTORESTART_PAR = 'TryToRestart'
TRYLASTCONVERGED_PAR = 'TryLastConverged'
MONITCONV_PAR = 'MonitorConvergence'
ODEMAXSTEPS_PAR = 'ODEMaxSteps'

#Simoultaneous
SECANT = 'Secant'
NR = 'NewtonRaphson'
BROYDEN = 'Broyden'

#Integrals
RK4 = 'RungeKutta4'
EULER = 'Euler'
EULER_IMPL = 'EulerImplicit'


TINYESTVALUE = 1.0E-100
LARGESTVALUE = 1.0E100

NUM_METH_SETTINGS = 'LocalSolverSettings'

class NumericMethodSettings(object):
    """Place holder for settings of a numerical method"""
    def __init__(self, parent):
        self.maxIter = 20
        self.tolerance = 0.00001
        self.dampingFactor = 1.0
        self.stayThreshold = 0.1 #Stick to the last converged solution if its err is less than this
        self.maxStep = None
        self.solveMethod = NR
        self.parent = parent
        self.minimizeErr = True
        self.tryToRestart = False
        self.tryLastConverged = True #TryToRestart overrides TryLastConverged 
        self.init = 0.0
        self.end = 10.0
        self.step = 1.0
        self.monitorConv = False
        self.freqJacMsg = 10
        
        #Try to load some default method calls
        #if hasattr(parent, 'CalculateRHS'): self.methodForSolvingRHS = parent.CalculateRHS
        #else: self.methodForSolvingRHS = None
        
        #if hasattr(parent, 'CalculateJacobian'): self.methodForJacobian = parent.CalculateJacobian
        #else: self.methodForJacobian = None
        
        #if hasattr(parent, 'CalculateDerivatives'): self.methodForDerivatives = parent.CalculateDerivatives
        #else: self.methodForDerivatives = None
        

    def GetPath(self):
        return self.parent.GetPath() + '.' + NUM_METH_SETTINGS
    
    def GetParent(self):
        return self.parent
    

        
class EquationBasedOp(UnitOperations.UnitOperation):
    """Base class of a unit operation that solves equations simulataneously"""
    def __init__(self, initScript=None):
        super(EquationBasedOp, self).__init__(initScript)

        self._unknowns = Unknowns()
        self._lastConvergedX = None
        self._lastX = None
        self._lastJacobian = None
        self._lastConvergedJac = None
        self._numMethodSetings = NumericMethodSettings(self)
        self._thCaseObj = None
        self.overSpecIdxVec = []
        
        self.parameters[AV_SOLVE_METH_PAR] = '%s %s %s' %(NR, SECANT, BROYDEN)
        self.SetParameterValue(MAXITER_PAR, 20)
        self.SetParameterValue(MAXERROR_PAR, 0.00001)
        self.SetParameterValue(DAMPINGFACTOR_PAR, 1.0)
        self.SetParameterValue(SOLVE_METH_PAR, NR)
        self.SetParameterValue(MINIMERR_PAR, True)
        self.SetParameterValue(TRYTORESTART_PAR, False)
        self.SetParameterValue(TRYLASTCONVERGED_PAR, True)
        self.SetParameterValue(MONITCONV_PAR, False)
        self.SetParameterValue(FREQ_JAC_MSG_PAR, 10)
        
    def CleanUp(self):
        self._numMethodSetings = None
        super(EquationBasedOp, self).CleanUp()
        
    def UpdateStructure(self):
        """Used to update the overall structure of the underlying objects when structure changed in the parent"""
        #Uncomment later
        #tolerance = self.GetParameterValue(MAXERROR_PAR)
        #maxIter = self.GetParameterValue(MAXITER_PAR)
        #damp = self.GetParameterValue(DAMPINGFACTOR_PAR)
        
        #if maxIter != None:
            #self._numMethodSetings.maxIter = maxIter
        #if tolerance != None:
            #self._numMethodSetings.tolerance = tolerance
        #if damp != None:
            #self._numMethodSetings.dampingFactor = damp

            
    
    def Solve(self):
        """Generic solve procedure"""
        
        self.FlashAllPorts()
        if isinstance(self.GetParent(), EquationBasedOp):
            #Let the parent do the solving
            return

        u = self._unknowns
        u.__init__()

        #In case there is something to be done before getting to business
        #Also used to solve stuff that can be solved already even if the whole system of equations is not ready
        if not self.PrepareForSolve(): return

        #Check for zero flow. Use this method to whatever there is to solve when there is zero flow
        if self.IsZeroFlow(): return

        #Do not solve if forgetting
        if self.IsForgetting():
            return
        
        #self.InfoMessage('5', (time.asctime(),))
        #Load known and unknown values. Estimate and initialize the unknowns
        #Return False if can not solve yet
        if not self.LoadUnknowns(u): return
        
        #self.InfoMessage('6', (time.asctime(),))
        #Make sure it is not overspecified
        nuSpecsNeeded = self.GetNuSpecsNeeded()
        self.CheckForOverSpec(nuSpecsNeeded)     
        
        #self.InfoMessage('7', (time.asctime(),))
        #Call the solver        
        s = self._numMethodSetings
        lConvX = self._lastConvergedX
        lX = self._lastX
        lJac = self._lastJacobian
        lConvJac = self._lastConvergedJac
        x, rhs, converged, jacobian = SolveNonLinearEquations(self, u, s, lConvX, lX, lJac, lConvJac)
        
        #self.InfoMessage('8', (time.asctime(),))
        self.converged = converged
        self._lastX = Numeric.array(x)
        self._lastJacobian = Numeric.array(jacobian)
        if converged:
            self._lastConvergedX = Numeric.array(x)
            self._lastConvergedJac = Numeric.array(jacobian)
            self.AssignResults(x)
        else:
            pass #Should it clear the last converged sol'n ??
        
        #self.InfoMessage('9', (time.asctime(),))
        self.FlashAllPorts()
        
        #self.InfoMessage('10', (time.asctime(),))
        
    def IsZeroFlow(self):
        return False
        
    def ParameterChanged(self, paramName, value):
        super(EquationBasedOp, self).ParameterChanged(paramName, value)
        if paramName == MAXITER_PAR:
            self._numMethodSetings.maxIter = value
        elif paramName == MAXERROR_PAR:
            self._numMethodSetings.tolerance = value
        elif paramName == DAMPINGFACTOR_PAR:
            self._numMethodSetings.dampingFactor = value
        elif paramName == SOLVE_METH_PAR:
            self._numMethodSetings.solveMethod = value
        elif paramName == MINIMERR_PAR:
            self._numMethodSetings.minimizeErr = value
        elif paramName == TRYTORESTART_PAR:
            self._numMethodSetings.tryToRestart = value
        elif paramName == TRYLASTCONVERGED_PAR:
            self._numMethodSetings.tryLastConverged = value
        elif paramName == MONITCONV_PAR:
            self._numMethodSetings.monitorConv = value    
        elif paramName == FREQ_JAC_MSG_PAR:
            self._numMethodSetings.freqJacMsg = value        
        elif paramName == ODEMAXSTEPS_PAR:
            self._numMethodSetings.odeMaxSteps = value  
            
    def ValidateParameter(self, paramName, value):
        if not super(EquationBasedOp, self).ValidateParameter(paramName, value):
            return False
        if paramName in (MAXITER_PAR, MAXERROR_PAR, DAMPINGFACTOR_PAR):
            if value <= 0:
                return False
        if paramName == FREQ_JAC_MSG_PAR and int(value) < 0:
            return False
        if paramName == ODEMAXSTEPS_PAR and int(value) < 0:
            return False
        return True
        
    def DeleteObject(self, obj):
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() in (MAXITER_PAR, MAXERROR_PAR, 
                                 DAMPINGFACTOR_PAR, MINIMERR_PAR,
                                 SOLVE_METH_PAR, AV_SOLVE_METH_PAR,
                                 TRYTORESTART_PAR, TRYLASTCONVERGED_PAR, 
                                 MONITCONV_PAR, FREQ_JAC_MSG_PAR):
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return

        super(EquationBasedOp, self).DeleteObject(obj)
            
                
    def GetNuSpecsNeeded(self):
        return 0
        
    def PrepareForSolve(self):
        """Make sure everything is in place"""
        return True
    
    def LoadUnknowns(self, u):
        """load all the unknowns"""
        return True
    
    def CheckForOverSpec(self, nuSpecsNeeded):
        """Check it is not overspec before solving"""
        self.overSpecIdxVec = []
        u = self._unknowns
        isSpecVec = u.GetIsFixed()
        nuSpecs = 0
        for i in range(len(isSpecVec)):
            if isSpecVec[i]:
                nuSpecs += 1
                if nuSpecs > nuSpecsNeeded:
                    u._unkIsSpec[i] = False
                    self.overSpecIdxVec.append(i)

    def AssignResults(self, vals):
        """Put results in the corresponding ports"""
        pass
        
    def ConvertToMKS(self, vals):
        """Converto all the units to m, kg, s units. It expects the std units from sim42"""
        return vals
        
    def ConvertFromMKS(self, vals):
        """Converto all the units to m, kg, s units. It expects the std units from sim42"""
        return vals

    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        """Calculates the right hand side of the design equations. Returns the next avilable index for a new equation"""
        return eqnNo
    
    def AdjustOldCase(self, version):
        super(EquationBasedOp, self).AdjustOldCase(version)
        if version[0] < 23:

            if not hasattr(self._numMethodSetings, 'minimizeErr'):
                self._numMethodSetings.minimizeErr = True
            
            if not self.parameters.has_key(MAXITER_PAR):
                self.SetParameterValue(MAXITER_PAR, 20)
            if not self.parameters.has_key(MAXERROR_PAR):
                self.SetParameterValue(MAXERROR_PAR, 0.00001)
            if not self.parameters.has_key(DAMPINGFACTOR_PAR):
                self.SetParameterValue(DAMPINGFACTOR_PAR, 1.0)
            if not self.parameters.has_key(AV_SOLVE_METH_PAR):
                self.parameters[AV_SOLVE_METH_PAR] = '%s %s %s' %(NR, SECANT, BROYDEN)                
            if not self.parameters.has_key(SOLVE_METH_PAR):
                self.SetParameterValue(SOLVE_METH_PAR, NR)
            if not self.parameters.has_key(MINIMERR_PAR):
                self.SetParameterValue(MINIMERR_PAR, True)
        if version[0] < 24:
            if not self.parameters.has_key(TRYTORESTART_PAR):
                self.SetParameterValue(TRYTORESTART_PAR, False)
        if version[0] < 25:
            if not self.parameters.has_key(TRYLASTCONVERGED_PAR):
                self.SetParameterValue(TRYLASTCONVERGED_PAR, True)                
            if not hasattr(self, '_lastX'):
                self._lastX = None
            if not hasattr(self, '_lastJacobian'):
                self._lastJacobian = None
        if version[0] < 39:
            if not self.parameters.has_key(MONITCONV_PAR):
                self.SetParameterValue(MONITCONV_PAR, False)
        if version[0] < 41:
            if not hasattr(self, '_lastConvergedJac'):
                self._lastConvergedJac = None
        if version[0] < 46:
            if not self.parameters.has_key(FREQ_JAC_MSG_PAR):
                #Do it driectly not to trigger a resolve of the whole thing
                self.parameters[FREQ_JAC_MSG_PAR] = 10
                self._numMethodSetings.freqJacMsg = 10  #value
                
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(EquationBasedOp, self)._RemoveFromCloneList(clone, attrNamesToClone)
        
        dontClone = ["_numMethodSetings"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone

def SolveNonLinearEquations(parent, u, numMethSettings, lastConvX, lastX, lastJac, lastConvJac=None):

    #parent.InfoMessage('In:', (time.asctime(), time.time()))
    #Load numerical method settings
    maxIter = numMethSettings.maxIter
    damp = numMethSettings.dampingFactor
    stayThreshold = numMethSettings.stayThreshold
    tolerance = numMethSettings.tolerance
    maxStep = numMethSettings.maxStep
    minimErr = numMethSettings.minimizeErr
    tryToRestart = numMethSettings.tryToRestart
    tryLastConverged = numMethSettings.tryLastConverged
    if hasattr(numMethSettings, 'solveMethod'):
        solveMethod = numMethSettings.solveMethod
    else:
        if hasattr(parent, 'CalculateJacobian'):
            solveMethod = NR
        else:
            solveMethod = SECANT
    if hasattr(numMethSettings, 'monitorConv'): monitorConv = numMethSettings.monitorConv
    else: monitorConv = False
    if hasattr(numMethSettings, 'freqJacMsg'): freqJacMsg = numMethSettings.freqJacMsg
    else: freqJacMsg = 10
    
    #Load stuff from the unknowns
    nuEquations = u.GetNumberOfUnknowns()
    x = u.GetValues()
    isFix = u.GetIsFixed()
    initx = u.GetInitValues()
    scaleFactors = u.GetScaleFactors()
    lowBounds = u.GetLowBounds()
    highBounds = u.GetHighBounds()
    
    #Init arrays
    jacobian = zeros((nuEquations, nuEquations), Float)
    deltaX = ones(nuEquations, Float) #Set initial deltaX to 1.0 to ensure that convergence check works
    rhs = zeros(nuEquations, Float)
    oldRhs = zeros(nuEquations, Float)

    #Init some vars
    iter = 0
    converged = False
    needsAFirstCalculation = True
    maxError = None
    parentPath = parent.GetPath()
    
    #Start from last vals? 
    if tryToRestart:
        if lastX and len(lastX) == nuEquations:
            #Should it really waste the time checking on the specs?
            for i in range(nuEquations):
                if not isFix[i]:
                    x[i] = lastX[i]
                    
    #Use last converged?
    elif tryLastConverged:
        if lastConvX and len(lastConvX) == nuEquations:
            try:
                #Keep the specs:
                for i in range(nuEquations):
                    if isFix[i]:
                        lastConvX[i] = x[i]
                parent.CalculateRHS(lastConvX, oldRhs, isFix, initx)
                maxErr = max(abs(oldRhs))
                if maxErr < stayThreshold:
                    x = Numeric.array(lastConvX)
                    initx = Numeric.array(lastConvX)
                    u.SetInitValues(lastConvX)
                    rhs[:] = oldRhs[:]
                    needsAFirstCalculation = False
            except:
                pass
    
            
    #Lets do stuff for the first iteration
    if needsAFirstCalculation:
        #print 'FirstCalcIn:', time.asctime()
        try:
            parent.CalculateRHS(x, rhs, isFix, initx)
            #Check to see if the previous solution is better
            if not tryToRestart and maxError != None and maxError < max(abs(rhs)):
                x = Numeric.array(lastConvX)
                initx = Numeric.array(lastConvX)
                u.SetInitValues(lastConvX)
                rhs[:] = oldRhs[:]  #OldRhs was used to store rhs for the last converged solution
        except:
            parent.InfoMessage('CouldNotInitialize', (parentPath,))
            return x, rhs, converged, jacobian
        
    try:
        converged = CheckForConvergence(rhs, scaleFactors, tolerance)
        if converged: 
            parent.InfoMessage('Converged', (parentPath, iter))
            return x, rhs, converged, lastConvJac
        
        #parent.InfoMessage('FirstJacobianIn:', (time.asctime(), time.time()))
        
        doCrudeDiff = True
        parent.InfoMessage('TowerCalcJacobian', (parentPath,))
        if solveMethod == NR and hasattr(parent, 'CalculateJacobian'):
            parent.CalculateJacobian(x, jacobian, isFix, initx)
            jacobian = inverse(jacobian)
            doCrudeDiff = False
            
        elif solveMethod == BROYDEN:
            if tryToRestart and lastX and len(lastX) == nuEquations:
                if lastJac:
                    jacobian[:] = lastJac[:]
                    doCrudeDiff = False
            elif tryLastConverged and lastConvX and len(lastConvX) == nuEquations:
                if lastConvJac:
                    jacobian[:] = lastConvJac[:]
                    doCrudeDiff = False
            elif hasattr(parent, 'CalculateJacobian'):
                parent.CalculateJacobian(x, jacobian, isFix, initx)
                jacobian = inverse(jacobian)
                doCrudeDiff = False
        
        if doCrudeDiff:
            xForJac = array(x, Float)
            rhsForJac = array(rhs, Float)
            shift = 0.0001
            
            #Pass a message every x calculations, so the solver doesn't look dead
            distCnt = 0
            msgEvery = freqJacMsg
            for j in range(nuEquations):
                distCnt +=1
                if distCnt == msgEvery:
                    parent.InfoMessage('CalcDisturbance', (j+1, nuEquations, parentPath))
                    distCnt = 0   
                    
                old = xForJac[j]
                xForJac[j] = xForJac[j] + shift * scaleFactors[j]
                parent.CalculateRHS(xForJac, rhsForJac, isFix, initx)
                jacobian[:, j] = (rhsForJac - rhs)/(shift * scaleFactors[j])
                xForJac[j] = old
            jacobian = inverse(jacobian)
        deltaX = -dot(jacobian, rhs) 
        #parent.InfoMessage('FirstJacobianOut:', (time.asctime(), time.time()))
    except:
        #Bye
        parent.InfoMessage('CouldNotInvertJacobian', (parentPath,))
        return x, rhs, converged, jacobian

    maxStep = None
    errHistory = []
    currMaxErr = max(abs(rhs))
    while iter <= maxIter:
        iter += 1
        oldRhs[:] = rhs[:]
        stepLength = 1.0*damp
        currx = Numeric.array(x)
        maxErr = currMaxErr
        
        #Make sure the step is not too large
        if maxStep != None:
            for i in range(len(deltaX)):
                if deltaX[i]/scaleFactors[i] > maxStep:
                    deltaX[i] = maxStep*scaleFactors[i]
                elif deltaX[i]/scaleFactors[i] < -maxStep:
                    deltaX[i] = -maxStep*scaleFactors[i]
                    
        cntHere = 0
        #Loop until max error (max rhs) decreases
        while 1:
            actualDeltaX = stepLength*deltaX
            
            x = UpdateX(currx, actualDeltaX, lowBounds, highBounds)
            if hasattr(parent, 'SanityCheck'):
                parent.SanityCheck(x, initx)
                
            try:
                parent.CalculateRHS(x, rhs, isFix, initx)
                converged = CheckForConvergence(rhs, scaleFactors, tolerance)
                if converged: 
                    parent.InfoMessage('Converged', (parentPath, iter))
                    #parent.InfoMessage('Out:', (time.asctime(), time.time()))
                    return x, rhs, converged, jacobian
                
                currMaxErr = max(abs(rhs))
                if minimErr and currMaxErr > maxErr:
                    stepLength *= 0.25
                    cntHere += 1
                else:
                    break

            except:
                stepLength *= 0.25
                
            if stepLength < 0.0000001:
                parent.InfoMessage('CouldNotConverge', (parentPath, iter))
                return x, rhs, False, jacobian
        
        parent.InfoMessage('EqnBasedUOpError', (parentPath, iter, currMaxErr))
        
        if monitorConv:
            #Monitor if it is not converging and it is just wasting time
            if cntHere > 4 and currMaxErr > 1000.0*tolerance:
                errHistory.append(currMaxErr)
                
                #It needed to reduce the error 7 times more than 4 times in a row.
                #Indicator there could be something wrong
                if len(errHistory) > 4:
                    parent.InfoMessage('NotConverging', (parentPath,))
                    return x, rhs, converged, jacobian
            else:
                errHistory = []
            
            
        try:
            #parent.InfoMessage('JacobianIn:', (time.asctime(), time.time()))
            parent.InfoMessage('TowerCalcJacobian', (parentPath,))
            if solveMethod == NR and hasattr(parent, 'CalculateJacobian'):
                jacobian = zeros((nuEquations, nuEquations), Float)
                parent.CalculateJacobian(x, jacobian, isFix, initx)
                jacobian = inverse(jacobian) 
            
            elif solveMethod == BROYDEN:
                xLastBr = array(x)
                rhsLastBr = array(rhs)
                usedBr = True
                dF = rhs - oldRhs 
                dotdxB = dot(actualDeltaX, jacobian)
                denom = dot(dotdxB, dF)
                if not abs(denom) < TINYESTVALUE:
                    jacobian = jacobian + outerproduct((actualDeltaX - dot(jacobian, dF)), dotdxB)/denom

            else: #Do Secant
                xForJac = array(x, Float)
                rhsForJac = array(rhs, Float)
                shift = 0.0001
                
                #Pass a message every x calculations, so the solver doesn't look dead
                distCnt = 0
                msgEvery = freqJacMsg
                for j in range(nuEquations):
                    distCnt +=1
                    if distCnt == msgEvery:
                        parent.InfoMessage('CalcDisturbance', (j+1, nuEquations, parentPath))
                        distCnt = 0
                        
                    old = xForJac[j]
                    xForJac[j] = xForJac[j] + shift * scaleFactors[j]
                    parent.CalculateRHS(xForJac, rhsForJac, isFix, initx)
                    jacobian[:, j] = (rhsForJac - rhs)/(shift * scaleFactors[j])
                    xForJac[j] = old
           
                jacobian = inverse(jacobian)
                
            deltaX = -dot(jacobian, rhs)
            #parent.InfoMessage('JacobianOut:', (time.asctime(), time.time()))
            
        except:
            parent.InfoMessage('CouldNotInvertJacobian', (parentPath,))
            break
    
    parent.InfoMessage('CouldNotConverge', (parentPath, iter))
    return x, rhs, converged, jacobian


class SolverVariable(object):
    """Defines a variable that is unerstood by the solver routines"""
    def __init__(self, name=None, value=None, initValue=None, isSpec=None, scaleFactor=None, lowBound=-LARGESTVALUE, highBound=LARGESTVALUE):
        self.name = name
        self.value = value
        self.initValue = initValue
        self.isSpec = isSpec
        self.scaleFactor = scaleFactor
        self.lowBound = lowBound
        self.highBound = highBound


class Unknowns(object):
    """Object used to manipulate a sequence of unknwon variables"""
    def __init__(self):
        """Keeps a list of SolverVariable objects"""

        self._lstUnknowns = []
        self._unkNames = []
        self._unkVals = []
        self._unkInitVals = []
        self._unkIsSpec = []
        self._unkScaleFacts = []
        self._unkLowBounds = []
        self._unkHighBounds = []

    def AddUnknown(self, solverVar):
        """Append an unknown at the end"""
        
        self._unkNames.append(solverVar.name)
        self._unkVals.append(solverVar.value)
        self._unkInitVals.append(solverVar.initValue)
        self._unkIsSpec.append(solverVar.isSpec)
        self._unkScaleFacts.append(solverVar.scaleFactor)
        self._unkLowBounds.append(solverVar.lowBound)
        self._unkHighBounds.append(solverVar.highBound)        

        lastIdx = len(self._unkVals) - 1
        
        return lastIdx
        
            
    def RemoveUnknwon(self, idx):
        """Remove an unknown by index"""
        if idx >= len(self._unkVals):
            return
        
        del self._unkNames[idx]
        del self._unkVals[idx]
        del self._unkInitVals[idx]
        del self._unkIsSpec[idx]
        del self._unkScaleFacts[idx]
        del self._unkLowBounds[idx]
        del self._unkHighBounds[idx]

    def GetNumberOfUnknowns(self):
        """Number of unknown variables"""
        return len(self._unkVals)

    def GetNames(self):
        """Get the names in a list"""
        return self._unkNames

    def SetNames(self, vector):
        """Sets the names for the variables. vector is any sequence of names"""
        self._unkNames = list(vector)
    
    def GetValues(self):
        """Get the values in a Numeric vector"""
        return array(self._unkVals, Float)

    def SetValues(self, vector):
        """Sets the values for the variables. vector is any sequence of values"""
        self._unkVals = array(vector, Float)

    def GetInitValues(self):
        """Get the values in a Numeric vector"""
        return array(self._unkInitVals, Float)

    def SetInitValues(self, vector):
        """Sets the values for the variables. vector is any sequence of values"""
        self._unkInitVals = array(vector, Float)

    def GetIsFixed(self):
        """Get the values in a Numeric vector"""
        return array(self._unkIsSpec, Int)

    def SetIsFixed(self, vector):
        """Sets the values for the variables. vector is any sequence of values"""
        self._unkIsSpec = array(vector, Int)

    def GetScaleFactors(self):
        """Get the values in a Numeric vector"""
        return array(self._unkScaleFacts, Float)

    def SetScaleFactors(self, vector):
        """Sets the values for the variables. vector is any sequence of values"""
        self._unkScaleFacts = array(vector, Float)

    def GetLowBounds(self):
        if self._unkLowBounds:
            return array(self._unkLowBounds, Float)
        else:
            return -LARGESTVALUE*ones(len(self._unkVals), Float)

    def SetLowBounds(self, vector):
        self._unkLowBounds = array(vector, Float)
        
    def GetHighBounds(self):
        if self._unkHighBounds:
            return array(self._unkHighBounds, Float)
        else:
            return LARGESTVALUE*ones(len(self._unkVals), Float)
        
    def SetHighBounds(self, vector):
        self._unkHighBounds = array(vector, Float)
        

def CheckForConvergence(rhs, scaleFactors, epsilon=0.000001):
    """Checks for convergence"""
    #Don't use scaleFactors as they are already scaled equations!!
    if max(Numeric.absolute(rhs)) > epsilon:
        return False
    else:
        return True

    
def UpdateX(x, deltaX, lowBound=None, highBound=None):

    x = x + deltaX
    
    if lowBound != None and highBound != None:
        x = clip(x, lowBound, highBound)
    elif lowBound != None:
        x = Numeric.maximum(x, lowBound)
    elif highBound != None:
        x = Numeric.minimum(x, highBound)

    return x

def CreateLinearDistArray(nuVals, bound1, bound2):
    """Create a Numeric array of values distributed linearly

    nuVals -- Number of values desired
    bound1 -- Boundary 1. Can be a numeric array
    bound2 -- Boundary 2. Can be a numeric array

    """
    if hasattr(bound1, 'shape'):
        #A bit convoluted but all it does it putting in a list something like this
        #nuVals =5, shape = (3, 4) -> (5, 3, 4)
        dim = [nuVals]
        dim.extend(list(bound1.shape)) 
        vals = zeros(dim, Float)
    else:
        vals = zeros(nuVals, Float)
        
    delta = (bound2 - bound1) / (nuVals - 1)
    for i in range(nuVals): vals[i] = delta * i + bound1

    return vals
    

###Integrals###########################################################


class Integrator(object):
    def __init__(self):
        self.name = None
        self.parent = None
        
    def __str__(self):
        return "Integrator"
    
    def Initialize(self, parent, name):
        self.name = name
        self.parent = parent
        
    def SetName(self, name):
        self.name = name
        
    def GetName(self):
        return self.name
    
    def SetParent(self, parent):
        self.parent = parent
        
    def GetParent(self):
        return self.parent
    
    def GetPath(self):
        return "%s.%s" %(self.parent.GetPath(), self.name)
    
    def InfoMessage(self, message=None, args=None, msgType=MessageHandler.infoMessage):
        """Support for info messages just to make like easier. Just pass them directly to the parent"""
        self.parent.InfoMessage(message, args, msgType)
        
    def CleanUp(self):
        self.parent = None
        
    def GetAvailableMethods(self):
        return [EULER, EULER_IMPL, RK4]
    
    def Integrate(self, yInit, numMethSettings, yMin=None, yMax=None, yScale=None):
        """Integrate"""
        
        method = numMethSettings.solveMethod
        retVal = False
        parent = self.parent
        
        if method == EULER:
            retVal = EulerExplicit(parent, yInit, numMethSettings, yMin, yMax, yScale)
            
        elif method == RK4:
            retVal = RungeKutta4(parent, yInit, numMethSettings, yMin, yMax, yScale)
            
        elif method == EULER_IMPL:
            retVal = EulerImplicit(parent, yInit, numMethSettings, yMin, yMax, yScale)
            
        else:
            parent.InfoMessage('NumMethodNotValid', (parent.GetPath(), method))
            
        return retVal
    def Clone(self):
        clone = self.__class__()
        clone.name = self.name
        return clone
    
        
def Integrate(parent, yInit, numMethSettings, yMin=None, yMax=None, yScale=None):
    """Integrate"""
    method = numMethSettings.solveMethod
    retVal = False

    if method == EULER:
        retVal = EulerExplicit(parent, yInit, numMethSettings, yMin, yMax, yScale)
        
    elif method == RK4:
        retVal = RungeKutta4(parent, yInit, numMethSettings, yMin, yMax, yScale)
        
    elif method == EULER_IMPL:
        retVal = EulerImplicit(parent, yInit, numMethSettings, yMin, yMax, yScale)
        
    else:
        #See if the parent can go and find it
        if hasattr(parent, 'GetCustomIntegrator'):
            Integrator = parent.GetCustomIntegrator(method)
            if not method:
                parent.InfoMessage('NumMethodNotValid', (parent.GetPath(), method))
            else:
                retVal = Integrator(parent, yInit, numMethSettings, yMin, yMax, yScale)
    return retVal
        

def RungeKutta4(parent, yInit, odeSettings, yMin=None, yMax=None, yScale=None):
    """Integrage with RK"""
    
    MAXTRY = 40
    if hasattr(odeSettings, 'odeMaxSteps'): LARGEVALITER = odeSettings.odeMaxSteps
    else: LARGEVALITER = 1000  #Do not calculate more than this many steps
    
    h = odeSettings.step
    xEnd = odeSettings.end
    xInit = odeSettings.init
    CalcDerivativesMethod = parent.CalculateDerivatives
    
    #Did scale values came in?
    autoScale = False
    if yScale == None:
        autoScale = True
    
    #Iterate along the whole distance
    h = Numeric.sign(xEnd-xInit) * abs(h) #Make sure the sign of h makes sense
    hBase = h                             #Original value of h
    hNext = h                             #Initialize hNext as h
    hMin = TINYESTVALUE                   #Always positive
    x = xInit
    y = array(yInit)
    stepCnt = 0
    converged = False
    loadResults = True
    path = parent.GetPath()
    xNextStore = xInit
    while stepCnt < LARGEVALITER and ((x-xEnd)*(xEnd-xInit) < 0.0):
        stepCnt += 1
        
        #Calculate derivatives right where we are 
        parent.InfoMessage('CalculatingStep', (stepCnt, path, x, xInit, xEnd))
        if ( hBase > 0.0 and x >= xNextStore ) or ( hBase < 0.0 and x <= xNextStore ): 
            loadResults = True
            xNextStore += hBase
        else:
            loadResults = False
        dy_dx = CalcDerivativesMethod(x, y, loadResults)
        
        #Set h as the estimated next h
        h = hNext
        
        #Make sure it won't go over
        if (x + h - xEnd) *  (x + h - xInit) > 0.0: h = xEnd - x
        
        #Iterate until a proper step size is found
        innerCnt = 0
        ySave = array(y, Float)
        while innerCnt <= MAXTRY:
            innerCnt += 1
            try:
                k1 = h * dy_dx
                k2 = h * CalcDerivativesMethod(x+h*0.5, ySave+k1*0.5)
                k3 = h * CalcDerivativesMethod(x+h*0.5, ySave+k2*0.5)
                k4 = h * CalcDerivativesMethod(x+h, ySave+k3)
                y = ySave + k1/6.0 + (k2 + k3)/3.0 + k4/6.0
                
                if yMin != None and min(y-yMin) < 0.0:
                    #If it crossed limits then reduce step by half
                    h = 0.5*h
                elif yMax != None and min(yMax - y) < 0.0:
                    #If it crossed limits then reduce step by half
                    h = 0.5*h
                else:
                    if h >= 0.0: hNext = min(hBase, h*2.0)
                    else: hNext = max(hBase, h*2.0)
                    break
                if abs(h) <= hMin or innerCnt >= MAXTRY:
                    raise SimError('StepSizeTooSmall', (path, h))
            except:
                h = 0.5*h
                if abs(h) <= hMin or innerCnt >= MAXTRY:
                    raise SimError('StepSizeTooSmall', (path, h))
                
        x += h
                
        ##Decide if we keep on iterating####################################################
        if ((x-xEnd)*(xEnd-xInit) >= 0.0):
            #Calculate derivatives yet again just so final results are loaded.
            #Not the best way to do things but good enough for now
            loadResults = True
            dy_dx = CalcDerivativesMethod(xEnd, y, loadResults)
            converged = True
            break
                
        ####################################################################################
                
    if not converged:
        parent.InfoMessage('ODEMaxSteps', (stepCnt, path))        
        
    return converged


def EulerExplicit(parent, yInit, odeSettings, yMin=None, yMax=None, yScale=None):
    """Integrate with Euler"""
    
    MAXTRY = 40
    if hasattr(odeSettings, 'odeMaxSteps'): LARGEVALITER = odeSettings.odeMaxSteps
    else: LARGEVALITER = 1000  #Do not calculate more than this many steps
    
    h = odeSettings.step
    xEnd = odeSettings.end
    xInit = odeSettings.init
    CalcDerivativesMethod = parent.CalculateDerivatives
    
    #Did scale values came in?
    autoScale = False
    if yScale == None:
        autoScale = True
    
    #Iterate along the whole distance
    h = Numeric.sign(xEnd-xInit) * abs(h) #Make sure the sign of h makes sense
    hBase = h                             #Original value of h
    hNext = h                             #Initialize hNext as h
    hMin = TINYESTVALUE                   #Always positive
    x = xInit
    y = array(yInit)
    stepCnt = 0
    converged = False
    loadResults = True
    path = parent.GetPath()
    xNextStore = xInit
    while stepCnt < LARGEVALITER and ((x-xEnd)*(xEnd-xInit) < 0.0):
        stepCnt += 1
        
        #Calculate derivatives right where we are 
        parent.InfoMessage('CalculatingStep', (stepCnt, path, x, xInit, xEnd))
        if ( hBase > 0.0 and x >= xNextStore ) or ( hBase < 0.0 and x <= xNextStore ): 
            loadResults = True
            xNextStore += hBase
        else:
            loadResults = False
        dy_dx = CalcDerivativesMethod(x, y, loadResults)
        
        #Set h as the estimated next h
        h = hNext
        
        #Make sure it won't go over
        if (x + h - xEnd) *  (x + h - xInit) > 0.0: h = xEnd - x
        
        #Iterate until a proper step size is found
        innerCnt = 0
        ySave = array(y, Float)
        while innerCnt <= MAXTRY:
            innerCnt += 1
            #Do the explicit calculation
            y = ySave + h*dy_dx
            
            #See if it crossed boundaries
            if yMin != None and min(y-yMin) < 0.0:
                #Step has begun to be reduced many times. See
                #if it is a round off problem.
                if hasattr(parent, 'RoundValues'):
                    y = parent.RoundValues(y, yMin, yMax, yScale)
                    if min(y-yMin) >= 0.0:
                        break
                
                #Reduce step by half
                h = 0.5*h
            elif yMax != None and min(yMax - y) < 0.0:
                #If it crossed limits then reduce step by half
                h = 0.5*h
                
            else:
                if h >= 0.0: hNext = min(hBase, h*2.0)
                else: hNext = max(hBase, h*2.0)
                break
            if abs(h) <= hMin or innerCnt >= MAXTRY:
                raise SimError('StepSizeTooSmall', (path, h))
            
        x += h
                
        ##Decide if we keep on iterating####################################################
        if ((x-xEnd)*(xEnd-xInit) >= 0.0):
            #Calculate derivatives yet again just so final results are loaded.
            #Not the best way to do things but good enough for now
            loadResults = True
            dy_dx = CalcDerivativesMethod(xEnd, y, loadResults)
            converged = True
            break
                
        ####################################################################################
                
    if not converged:
        parent.InfoMessage('ODEMaxSteps', (stepCnt, path))
        
    return converged


def EulerImplicit(parent, yInit, odeSettings, yMin=None, yMax=None, yScale=None):
    """Integrate with Euler explicit"""
    
    MAXTRY = 40
    LARGEVALITER = 1000
    
    #Settings for implicit iteration
    #Default are fairly loose settings
    if hasattr(odeSettings, 'maxIter'): maxIter = odeSettings.maxIter
    else: maxIter = 15
    if hasattr(odeSettings, 'dampingFactor'): damping = odeSettings.dampingFactor
    else: damping = 1.0
    damping = 1.0
    if hasattr(odeSettings, 'tolerance'): tol = odeSettings.tolerance
    else: tol = 1.0E-3
    h = odeSettings.step
    xEnd = odeSettings.end
    xInit = odeSettings.init
    CalcDerivativesMethod = parent.CalculateDerivatives
    Validate = None
    if hasattr(parent, 'ValidateStepResults'): Validate = parent.ValidateStepResults
    nuEquations = len(yInit)
    jacobian = zeros((nuEquations, nuEquations), Float)
    
    
    #Did scale values came in?
    autoScale = False
    if yScale == None:
        autoScale = True
    
    #Iterate along the whole distance
    h = Numeric.sign(xEnd-xInit) * abs(h) #Make sure the sign of h makes sense
    hBase = h                             #Original value of h
    hNext = h                             #Initialize hNext as h
    hMin = TINYESTVALUE                   #Always positive
    x = xInit
    y = array(yInit)
    stepCnt = 0
    converged = False
    loadResults = True
    path = parent.GetPath()
    xNextStore = xInit
    while stepCnt < LARGEVALITER and ((x-xEnd)*(xEnd-xInit) < 0.0):
        stepCnt += 1
        
        #Calculate derivatives right where we are 
        parent.InfoMessage('CalculatingStep', (stepCnt, path, x, xInit, xEnd))
        if ( hBase > 0.0 and x >= xNextStore ) or ( hBase < 0.0 and x <= xNextStore ): 
            loadResults = True
            xNextStore += hBase
        else:
            loadResults = False
            
        if yMin != None and min(y-yMin) < 0.0:
            #See if it is a round off problem.
            if hasattr(parent, 'RoundValues'):
                y = parent.RoundValues(y, yMin, yMax, yScale)
            
        dy_dx = CalcDerivativesMethod(x, y, loadResults) 
        
        #Set h as the estimated next h
        h = hNext
        
        #Make sure it won't go over
        if (x + h - xEnd) *  (x + h - xInit) > 0.0: h = xEnd - x
        
        #Scale values
        if autoScale: 
            C = ones(len(y), Float)
            yScale = Numeric.maximum(C, absolute(y))
            
        #Iterate until a proper step size is found
        innerCnt = 0
        ySave = array(y, Float)
        
        #The implicit algorithm implies that the derivatives are evaluated at h
        #but sometimes it is necessary to evaluate the derivatives at h-epsilon
        #to avoid convergence problems.
        #In this case hEval = h-epsilon
        hEval = h
        doImplicit = 1
        while innerCnt <= MAXTRY:
            innerCnt += 1
            try:
                #Initial guess of yNext as explicit Euler
                yNext = ySave + h*dy_dx
                
                #Make sure it is
                yNext = parent.StepToBoundaries(x+h, yNext, h)
                yNext = Numeric.clip(yNext, yMin, yMax)
                #Iterate in the implicit step with quasi Newton Raphson
                #with approximate Jacobian
                iter = 0
                convImplicit = False
                while iter < maxIter:
                    iter += 1
                    yNextNew = ySave + h*CalcDerivativesMethod(x + hEval, yNext)
                    yNextNew = parent.StepToBoundaries(x+h, yNextNew, h)
                    #if Validate: yNextNew = Validate(x+h, yNextNew)
                    rhs = yNextNew - yNext
                    rhs /= yScale
                    if max(Numeric.absolute(rhs)) < tol:
                        convImplicit = True
                        y = Numeric.clip(yNextNew, yMin, yMax)
                        break
                    
                    #Calculate Jacobian with crude differentials
                    yNextForJac = array(yNext, Float)
                    rhsForJac = array(rhs, Float)
                    shift = 0.0001
                    shift = shift * yScale
                    for j in xrange(nuEquations):
                        old = yNextForJac[j]
                        yNextForJac[j] = yNextForJac[j] + shift[j]
                        yNextNewForJac = ySave + h*CalcDerivativesMethod(x+hEval, yNextForJac)
                        rhsForJac = (yNextNewForJac - yNextForJac) / yScale
                        for k in xrange(nuEquations):
                            jacobian[k][j] = (rhsForJac[k] - rhs[k])/(shift[j])
                        yNextForJac[j] = old
                        
                    #Invert Jacobian and get the new estimate for y
                    jacobian = inverse(jacobian)
                    deltaX = -dot(jacobian, rhs)*damping
                    yNext = UpdateX(yNext, deltaX)
                    yNext = parent.StepToBoundaries(x+h, yNext, h)
                    yNext = Numeric.clip(yNext, yMin, yMax)
                
                if convImplicit:
                    if h >= 0.0: hNext = min(hBase, h*4.0)
                    else: hNext = max(hBase, h*4.0)
                    y = yNext
                    break 
                else:
                    #Reduce the step
                    h *= 0.25
                    if abs(h) <= hMin:
                        raise SimError('StepSizeTooSmall', (path, h))
            except:
                #Reduce the step
                h *= 0.25
                if abs(h) <= hMin:
                    raise SimError('StepSizeTooSmall', (path, h))
                    
                    
        if not convImplicit:
            raise SimError('StepSizeTooSmall', (path, h))
            
        x += h
                
        ##Decide if we keep on iterating####################################################
        if ((x-xEnd)*(xEnd-xInit) >= 0.0):
            #Calculate derivatives yet again just so final results are loaded.
            #Not the best way to do things but good enough for now
            loadResults = True
            dy_dx = CalcDerivativesMethod(xEnd, y, loadResults)
            converged = True
            break
                
        ####################################################################################
                
    if not converged:
        parent.InfoMessage('ODEMaxSteps', (stepCnt, path))
        
    return converged
