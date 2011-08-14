"""
Controller module
    provides class to manipulate an output signal port
    until the value of an input signal port is equal to
    a target signal port

Classes:
    Controller -- Inherits from UnitOperation
    has special relationship with Flowsheet
"""

import UnitOperations
from sim.solver import Error
from sim.solver.Variables import *
from sim.solver.Ports import SIGNAL_TYPE_NONE

import numpy, math
from numpy.oldnumeric import array, zeros, ones, Float, take, put, add, clip
from numpy.oldnumeric import transpose, dot, outerproduct, matrixmultiply, where
from numpy.linalg import solve as solve_linear_equations, inv as inverse

TARGET_PORT = 'Target'
STEPSIZE_PORT = 'StepSize'
TOLERANCE_PORT = 'Tolerance'
MINIMUM_PORT = 'Minimum'
MAXIMUM_PORT = 'Maximum'

SOLUTION_METH_PAR = 'SolutionMethod'
SECANT_METH = 'Secant'
BROYDEN_METH = 'Broyden'
BISECTION_METH = 'Bisection'
SIMULTANEOUS = 'Simultaneous'

tiniestValue = 1.0e-100
largestValue = 1.0e100

class ControllerObject(object):
    pass

class AbsoluteTolerance(object):
    """Wrapper for the absolute tolerance"""
    def __init__(self, parent, name=MAXABSERROR_PAR):
        self.parent = parent
        self.name = name
        
    def __str__(self):
        retVal = "Maximum absolute error %.5g" %(self.GetValue())
        return retVal
    
    def GetParent(self):
        return self.parent
    
    def GetPath(self):
        return self.parent.GetPath() + '.' + self.GetName()
    
    def GetValue(self):
        return self.parent.GetAbsoluteTolerance()
    
    def SetValue(self, value, status=None):
        self.parent.SetAbsoluteTolerance(value)
        
    def GetType(self):
        inPort = self.parent.monitoredPort
        type = inPort.GetType()
        if type == None:
            type = PropTypes[GENERIC_VAR]
        if type.name == T_VAR:
            type = PropTypes[DELTAT_VAR]
        if type.name == P_VAR:
            type = PropTypes[DELTAP_VAR]
            
        return type
    
    def GetObject(self, desc):
        if desc == 'Value':
            return self.GetValue()
        elif desc == 'Type':
            return self.GetType()

    
class Controller(UnitOperations.UnitOperation):
    """
    manipulates an output signal port until the value of an
    input signal port is equal to a target signal port
    
    Has the following signal values:
        IN_PORT - the monitored variable
        OUT_PORT - the controlled variable
        TARGET_PORT - the desired value for the monitored variable
        STEPSIZE_PORT - the largest allowable single step for the controlled variable
        MINIMUM_PORT  - smallest allowable value for the controlled variable
        MAXIMUM_PORT  - largest allowable value for the controlled variable
    """
    def __init__(self, initScript = None):
        """Init the controller"""          
        super(Controller, self).__init__(initScript)

        self.monitoredPort  = self.CreatePort(SIG, IN_PORT)
        self.controlledPort = self.CreatePort(SIG, OUT_PORT)
        self.targetPort     = self.CreatePort(SIG, TARGET_PORT)
        self.stepsizePort   = self.CreatePort(SIG, STEPSIZE_PORT)
        self.minPort        = self.CreatePort(SIG, MINIMUM_PORT)
        self.maxPort        = self.CreatePort(SIG, MAXIMUM_PORT)
        self.haveAdded = 0   # can't add myself to parent yet, but need to know I haven't
        # lock all ports
        self.monitoredPort.SetLocked(True)
        self.controlledPort.SetLocked(True)
        self.targetPort.SetLocked(True)
        self.stepsizePort.SetLocked(True)
        self.minPort.SetLocked(True)
        self.maxPort.SetLocked(True)
        
        self.SetParameterValue(SOLUTION_METH_PAR, BROYDEN_METH)

    def GetAbsoluteTolerance(self):
        """Get the maximum error based on the active scaling factor"""
        tol = self.GetTolerance()
        try:
            scaleFactor = self.monitoredPort.GetType().scaleFactor
            if scaleFactor == -1.0: scaleFactor = 1.0
        except:
            scaleFactor = 1.0
        return tol*scaleFactor
    
    def SetAbsoluteTolerance(self, value):
        """Get the maximum error based on the active scaling factor"""
        
        try:
            scaleFactor = self.monitoredPort.GetType().scaleFactor
            if scaleFactor == -1.0: scaleFactor = 1.0
        except:
            scaleFactor = 1.0
        self.SetParameterValue(MAXERROR_PAR, value / scaleFactor)
    
    
    def NotifyControlledPortChange(self, msgKey, other):
        if other:
            portPath = self.ShortestPortPath(self.controlledPort)
            otherPath = other.GetParentOp().ShortestPortPath(other)
            self.InfoMessage (msgKey, (portPath, otherPath))
        
    def GetObject(self, desc):
        obj = super(Controller, self).GetObject(desc)
        if obj != None: return obj
        
        if desc == MAXABSERROR_PAR:
            obj = AbsoluteTolerance(self)
            
        return obj
        
    def CleanUp(self):
        self.Solver().RemoveController(self)
        super(Controller, self).CleanUp()
        # notify controller delete
        self.NotifyControlledPortChange ('ControllerDelete', self.controlledPort.IsPortConnected())
        
    def Solve(self):
        """everything is done by the solvers ControllerSolver object"""
        if not self.haveAdded:
            self.Solver().AddController(self)
            self.haveAdded = 1
        self.PropagateSignalTypes()

    def PropagateSignalTypes(self):
        # in and target should all be the same type of port
        # out, stepSize, min and max should all be the same
        inports = (self.monitoredPort, self.targetPort)
        outports = (self.controlledPort, self.minPort, self.maxPort, self.stepsizePort)
        for port in inports:
            portType = port.GetSignalType()
            if portType != SIGNAL_TYPE_NONE:
                break
            
        if portType != SIGNAL_TYPE_NONE:
            for port in inports:
                if port.GetSignalType() == SIGNAL_TYPE_NONE:
                    port.CreateProperty(portType)
                    port._varType = portType
            
                    
        for port in outports:
            portType = port.GetSignalType()
            if portType != SIGNAL_TYPE_NONE:
                break
            
        if portType != SIGNAL_TYPE_NONE:
            if portType == T_VAR:
                port = self.GetPort(STEPSIZE_PORT)
                port.CreateProperty(DELTAT_VAR)
                port._varType = portType
                
            elif portType == P_VAR:
                port = self.GetPort(STEPSIZE_PORT)
                port.CreateProperty(DELTAP_VAR)
                port._varType = portType
            for port in outports:
                if port.GetSignalType() == SIGNAL_TYPE_NONE:
                    port.CreateProperty(portType)
                    port._varType = portType
                    
    def Error(self):
        """
        return the scaled error between the monitored and target variables
        """
        inPort = self.monitoredPort
        dependent = inPort.GetValue()
        if dependent == None:
            return None
        
        target = self.targetPort.GetValue()
        if target == None:
            return None
        
        # use the inPort type - presumably target should be the same, but
        # we won't enforce it.
        scaleFactor = inPort.GetType().scaleFactor
        if not scaleFactor:
            return None
        if scaleFactor < 0.0: scaleFactor = 1.0
        
        err = (dependent - target)/scaleFactor
        self.unitOpMessage = ('ErrorValue', str(err))
        return err
    
    def SaveBase(self):
        """
        save the controlled variable and stepsize and use then
        in the SetOutput routine
        return 0 if either is None, 1 if both known
        """
        # first check if step size is known - if not return None
        
        self._base = self.GetPort(OUT_PORT).GetValue()
        self._stepSize = self.GetPort(STEPSIZE_PORT).GetValue()
        return self._base != None and self._stepSize != None
    
    def GetScaledMinimum(self):
        """
        return the minimum scaled appropriately
        """
        minV = self.minPort.GetValue()
        if minV == None: minV = -largestValue
        
        return (minV - self._base)/self._stepSize
    
    def GetScaledMaximum(self):
        """
        return the maximum scaled appropriately
        """
        maxV = self.maxPort.GetValue()
        if maxV == None: maxV = largestValue
        
        return (maxV - self._base)/self._stepSize
    
    def SetOutput(self, scaledValue):
        """
        fix the output value as a function of scaledValue, the step size
        and the stored base value
        """
        output = self._base + scaledValue * self._stepSize
        self.controlledPort.SetValue(output, FIXED_V)
        
    def MakingPortConnection(self, myPort, otherPort):
        if otherPort == None:
            # disconnecting, reset the signal types of the associated ports to None
            # otherwise i shall not be able to re-connect to a different signals
            cleanIn = 0
            cleanOut = 0
            inports = (self.monitoredPort, self.targetPort)
            outports = (self.controlledPort, self.minPort, self.maxPort, self.stepsizePort)
            
            if myPort == self.monitoredPort:
                if not self.targetPort.IsPortConnected(): cleanIn = 1
            elif myPort == self.targetPort:
                if not self.monitoredPort.IsPortConnected(): cleanIn = 1
            else:
                if myPort == self.controlledPort:
                    self.NotifyControlledPortChange ('BeforeControllerDisconnect', myPort.IsPortConnected())
                cleanOut = 1
                for port in outports:
                    if port != myPort and port.IsPortConnected():
                        cleanOut = 0
                        break
                    
            #Hack to make it look as if it is already disconnected
            #because SetSignalPort affects the connected port creating problems
            tempConn = myPort._connection
            myPort._connection = None
            if cleanIn:
                for port in inports:
                    port.SetSignalType(SIGNAL_TYPE_NONE)
            elif cleanOut:
                for port in outports:
                    port.SetSignalType(SIGNAL_TYPE_NONE)
            myPort._connection = tempConn
        else:
            if myPort == self.controlledPort:
                self.NotifyControlledPortChange ('ControllerConnect', otherPort)
            
        self.PropagateSignalTypes()
                    
        
    def ValidateParameter(self, paramName, value):
        super(Controller, self).ValidateParameter(paramName, value)
        if paramName == SOLUTION_METH_PAR:
            if not value in (BROYDEN_METH,):
                return False

        return True
        
        
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        dontClone = ["haveAdded"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
    
class ControllerSolver(object):
    """used by flowsheet solver to solve the controllers it contains"""

    def __init__(self, flowsheet):
        """
        flowsheet is the solver that owns this
        """
        self.flowsheet = flowsheet
        self.controllerList = []
        self.jacobian = None

    def CleanUp(self):
        """
        call to break circular references
        """
        self.flowsheet = self.controllerList = self.jacobian = None
        
    def AddController(self, controller):
        """add controller to list of controllers"""
        if not controller in self.controllerList:
            self.controllerList.append(controller)
            
    def RemoveController(self, controller):
        """remove controller from list of controllers"""
        try:
            if self.controllerList:
                self.controllerList.remove(controller)
        except ValueError:
            pass

    def Solve(self):
        """solve for controllers in controllerList"""
        from sim.solver import Flowsheet
        
        flowsheet = self.flowsheet
        flPath = flowsheet.GetPath()
        details = flowsheet.GetParameterValue(Flowsheet.RECYCLE_DETAILS_VAR)
        
        # solve the controllers
        self.activeControllers = []
        self.activeControllersBisect = []
        for cont in self.controllerList:
            error = cont.Error()
            if error != None and cont.SaveBase() and cont.GetParameterValue(IGNORED_PAR) == None:
                #solMeth = cont.GetParameterValue(SOLUTION_METH_PAR)
                solMeth = BROYDEN_METH
                if solMeth == BROYDEN_METH or solMeth == None:
                    self.activeControllers.append(cont)
                    
                elif solMeth == BISECTION_METH:
                    self.activeControllersBisect.append(cont)
        
        #For broyden
        numA = self.numberActive = len(self.activeControllers)
        
        #For bisection
        numABisect = self.numberActiveBisect = len(self.activeControllersBisect)
        
        if self.numberActive + self.numberActiveBisect == 0: return

        #For broyden
        maxErr1 = 0.0
        totalError = 0.0
        if numA > 0:
            self.errors = self.GetErrors(BROYDEN_METH)
            tolerances = self.GetTolerances(BROYDEN_METH)
            maxErr1 = max(Numeric.absolute(self.errors)/tolerances)
            totalError = Numeric.sum(Numeric.absolute(self.errors))

        #For bisection
        maxErr2 = 0.0
        totalErrorBisect = 0.0
        if numABisect > 0:
            self.errorsBisect = self.GetErrors(BISECTION_METH)
            tolerancesBisect = self.GetTolerances(BISECTION_METH)
            maxErr2 = max(Numeric.absolute(self.errorsBisect)/tolerancesBisect)
            totalErrorBisect = Numeric.sum(Numeric.absolute(self.errorsBisect))
            
        if max(maxErr1, maxErr2) <= 1.0:
            return
        
        if numA > 0:
            # calculate a jacobian if necessary
            newJacobian = 0
            if self.jacobian == None or self.jacobian.shape[0] != numA:
                self.CalcJacobian()
                newJacobian = 1

                
        #For broyden
        if numA > 0:
            oldErrors = zeros(self.numberActive, Float)
            oldVars = zeros(self.numberActive, Float)
            vars = zeros(self.numberActive, Float)  # using scaled variables so base is 0
            minV = self.GetMinimums(BROYDEN_METH)
            maxV = self.GetMaximums(BROYDEN_METH)
        
        #For bisection
        if numABisect > 0:
            oldErrorsBisect = zeros(numABisect, Float)        
            oldVarsBisect = zeros(numABisect, Float)
            
            varsBisect = zeros(numABisect, Float)  # using scaled variables so base is 0
            lowBound = self.GetMinimums(BISECTION_METH)
            upBound = self.GetMaximums(BISECTION_METH)        
        
        minStepSize = 0.0001

        #Initialize boundaries
        if numABisect > 0:
            sign = 1.0
            #We already have errors @ varsBisect, lets get errors in upBound
            # adjust the output
            self.SetOutput(upBound, BISECTION_METH)
            
            # recalculate flowsheet
            self.flowsheet.InnerSolve()
            
            changeInSign = self.GetErrors(BISECTION_METH)*self.errorsBisect
            for i in range(numABisect):
                #Didn't change sign
                if sign*changeInSign[i] > 0.0:
                    upBound[i] = varsBisect[i]
                    sign = 1.0
                #sign changed
                else:
                    lowBound[i] = varsBisect[i]
                    sign = -1.0
                    
        iter = 0
        maxIter = flowsheet.GetParameterValue(MAXITERCONT_PAR)
        if not maxIter: maxIter = 1E10 #A very large number
        while iter < maxIter:   #main loop
            converged = 0
            iter += 1
            
            #First bisect
            if numABisect > 0:
                oldErrorsBisect[:] = self.errorsBisect[:]
                oldTotalErrorBisect = totalErrorBisect
                
                varsBisect[:] = lowBound + (upBound-lowBound)/2.0
                
                # adjust the output
                self.SetOutput(varsBisect, BISECTION_METH)
                
                # recalculate flowsheet
                flowsheet.InnerSolve()
                
                self.errorsBisect = self.GetErrors(BISECTION_METH)
                changeInSign = self.errorsBisect*oldErrorsBisect
                for i in range(numABisect):
                    #Didn't change sign
                    if sign*changeInSign[i] > 0.0:
                        upBound[i] = varsBisect[i]
                        sign = 1.0
                        
                    #sign changed
                    else:
                        lowBound[i] = varsBisect[i]
                        sign = -1.0

                maxGap = max(upBound - lowBound)
                if maxGap < minStepSize:
                    # step size too small - bail
                    break
                        
                totalErrorBisect = Numeric.sum(Numeric.absolute(self.errorsBisect))
                
                
            #Do broyden
            if numA > 0:
                oldErrors[:] = self.errors[:]
                oldTotalError = totalError
                oldVars[:] = vars[:]
                adjustment = -dot(self.jacobian, self.errors)
                
                # initial step length limited so no controller exceeds its max step
                maxAdjustment = max(Numeric.absolute(adjustment))
                if maxAdjustment > 1.0:
                    stepLength = 1.0 / maxAdjustment
                else:
                    stepLength = 1.0
                
                adj = stepLength * adjustment
                newvars = vars + adj
                minlimit = min(where(newvars < minV, (minV - vars)/adj, 1.0))
                maxlimit = min(where(newvars > maxV, (maxV - vars)/adj, 1.0))
                stepLength *= min(minlimit, maxlimit)
    
                # loop until reduction in errors or step length become too small
                while 1:
                    actualAdjustment = stepLength * adjustment
                    vars += actualAdjustment
    
                    # adjust the output
                    self.SetOutput(vars)
                    
                    # recalculate flowsheet
                    flowsheet.InnerSolve()
                    
                    # check errors
                    self.errors = self.GetErrors()
                    totalError = Numeric.sum(Numeric.absolute(self.errors))
                    
                    if totalError < oldTotalError:
                        break
                    
                    # errors did not go down - back down step size
                    vars[:] = oldVars[:]
                    if stepLength < minStepSize:
                        # step size too small - bail
                        break
    
                    stepLength /= 4
            
            if details:
                try:
                    for cont in self.activeControllers + self.activeControllersBisect:
                        target = cont.targetPort.GetValue()
                        current = cont.monitoredPort.GetValue()
                        flowsheet.InfoMessage('RecycleErrorDetail',(cont.GetPath(), cont.targetPort.GetType().name, current, target))
                except:
                    pass
            flowsheet.InfoMessage('ControllerTotalError', (flPath, totalError+totalErrorBisect))
            
            
            #Broyden
            if numA > 0:
                maxErr1 = max(Numeric.absolute(self.errors)/tolerances)
            #Bisect
            if numABisect > 0:
                maxErr2 = max(Numeric.absolute(self.errorsBisect)/tolerancesBisect)
                
            if max(maxErr1, maxErr2) <= 1.0:
                converged = 1
                break
            
            if numA > 0:
                if totalError >= oldTotalError:
                    # smallest step didn't work
                    # if already has new jacobian, exit
                    if newJacobian:
                        break
                    else:
                        # other wise try a fresh one
                        self.CalcJacobian()
                        newJacobian = 1
                        minV = self.GetMinimums()
                        maxV = self.GetMaximums()
                else:
                    # update jacobian        
                    self.jacobian = self.UpdateJacobian(self.jacobian, actualAdjustment,
                                                       (self.errors - oldErrors))
                    newJacobian = 0
            
        if not converged:            
            flowsheet.InfoMessage('ControllerConvergeFail', flPath)
            
    def GetErrors(self, solMeth=BROYDEN_METH):
        """
        return an array _numberActive long of errors
        """
        
        #Where to pull info from
        if solMeth == BROYDEN_METH:
            numAct = self.numberActive
            conts = self.activeControllers
        elif solMeth == BISECTION_METH:
            numAct = self.numberActiveBisect
            conts = self.activeControllersBisect
            
        #Get the info
        errors = zeros(numAct, Float)
        i = 0
        for cont in conts:
            errors[i] = cont.Error()
            i += 1

            
        return errors

    def GetTolerances(self, solMeth=BROYDEN_METH):
        """
        return an array _numberActive long of controller tolerances
        """

        #Where to pull info from
        if solMeth == BROYDEN_METH:
            numAct = self.numberActive
            conts = self.activeControllers
        elif solMeth == BISECTION_METH:
            numAct = self.numberActiveBisect
            conts = self.activeControllersBisect
            
        #Get the info    
        t = zeros(numAct, Float)
        i = 0
        for cont in conts:
            t[i] = cont.GetTolerance()
            i += 1
            
        return t

    def SetOutput(self, vars, solMeth=BROYDEN_METH):
        """
        set the output variables
        """
        
        #Where to pull info from
        if solMeth == BROYDEN_METH:
            numAct = self.numberActive
            conts = self.activeControllers
        elif solMeth == BISECTION_METH:
            numAct = self.numberActiveBisect
            conts = self.activeControllersBisect
        
        for i in range(numAct):
            cont = conts[i]
            cont.SetOutput(vars[i])

    def GetMinimums(self, solMeth=BROYDEN_METH):
        """
        return an array _numberActive long of the minimum variables
        """
        
        #Where to pull info from
        if solMeth == BROYDEN_METH:
            numAct = self.numberActive
            conts = self.activeControllers
        elif solMeth == BISECTION_METH:
            numAct = self.numberActiveBisect
            conts = self.activeControllersBisect        
        
        
        minV = zeros(numAct, Float)
        i = 0
        for cont in conts:
            minV[i] = cont.GetScaledMinimum()
            i += 1
            
        return minV
            
    def GetMaximums(self, solMeth=BROYDEN_METH):
        """
        return an array _numberActive long of the maximum variables
        """
        
        #Where to pull info from
        if solMeth == BROYDEN_METH:
            numAct = self.numberActive
            conts = self.activeControllers
        elif solMeth == BISECTION_METH:
            numAct = self.numberActiveBisect
            conts = self.activeControllersBisect        
        
        maxV = zeros(numAct, Float)
        i = 0
        for cont in conts:
            maxV[i] = cont.GetScaledMaximum()
            i += 1
        return maxV
        
    
    def CalcJacobian(self):
        """
        Use crude numerical differences to approximate Jacobian
        return inverse
        """
        jacobian = zeros((self.numberActive, self.numberActive), Float)
        for cont in self.activeControllers:
            cont.SaveBase()
        self.errors = self.GetErrors()
            
        delta = 0.1
        for i in range(self.numberActive):
            self.flowsheet.InfoMessage('ContDerivCalc', (self.flowsheet.GetPath(), i))
            cont = self.activeControllers[i]
            cont.SetOutput(delta)
            self.flowsheet.InnerSolve()
            jacobian[:,i] = (self.GetErrors() - self.errors)/delta
            cont.SetOutput(0.0)
            
        self.flowsheet.InnerSolve()
        
        try:
            self.jacobian = inverse(jacobian)
        except:
            raise Error.SimError('CouldNotInvertJacobian', self.flowsheet.GetPath())

    def UpdateJacobian(self, B, dx, dF):
        """
        Use Broyden method (following Numerical Recipes in C, 9.7)
        to update inverse Jacobian
        B is previous inverse Jacobian (n x n)
        dx is delta x for last step (n)
        dF is delta errors for last step (n)
        """
        
        dotdxB = dot(dx, B)
        denom = dot(dotdxB, dF)
        if abs(denom) < tiniestValue:
            return B       # what else to do?
        
        return B + outerproduct((dx - dot(B, dF)), dotdxB)/denom
            
        