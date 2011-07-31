"""Models a flowsheet, which is designed to be the parent of other uo

Classes:
Flowsheet -- Class for the flowsheet. Inherits from UnitOperation

"""

#I use this variable to print the init and end time of the solve calls
#Anything in CVS should always have it as False
REPORT_TIME = False


import time
from rexec import RExec
from sim.unitop import UnitOperations
from sim.unitop import Controller
from sim.thermo.ThermoAdmin import ThermoCase
from Messages import MessageHandler

import Ports
import Error
from Variables import *

import numpy
from numpy import array, zeros, ones, float, identity, clip
from numpy import transpose, dot, outer as outerproduct, dot as matrixmultiply, where

VERSION = (79, 'V2.0.0.0')

ON_SOLVE_STACK = 1
ON_FORGET_STACK = 2
ON_RESET_CALC_STACK = 4
ON_RESET_FIXED_STACK = 8

MAXRECYCLESTEP_VAR = 'MaxRecycleStep'
RECYCLE_DETAILS_VAR = 'RecycleDetails'

rootPathName = ''  # used for storing and recalling non python things


class Flowsheet(UnitOperations.UnitOperation):
    """Class for the flowsheet. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """Sets up stacks etc"""
        self.version = VERSION
        super(Flowsheet, self).__init__(initScript)
        
        # set up stacks and more stacks for solver
        self._solveStack = []
        self._forgetStack = []
        self._resetNewCalcStack = []
        self._resetNewFixedStack = []
        self._iterationStack = []
        self._consistencyErrorStack = []
        self._controllerSolver = None
        
        self._isForgetting = 0
        self._isSolving = 0
        self.hold = 0
        
        #Some objects so the flowsheet still knows what was unconverged or with inconsistencies
        #The need for this objects is motivated from the fact that the flowsheet
        #clears all the stack before a solve and there is no way to tell if the
        #consistency errors have been take care of.
        self.lastUnconvRecycles = UnconvRecycleDict()
        self.lastConsistErrrors = ConsistencyErrorDict()
        
        
        # set tolerance and max iterations
        self.SetParameterValue(MAXERROR_PAR, 0.0001)
        self.SetParameterValue(MAXITER_PAR, 20)
        self.SetParameterValue(MAXITERCONT_PAR, 20)
        self.SetParameterValue(MAXRECYCLESTEP_VAR, 0.05)
        
    def CleanUp(self):
        """
        remove any circular references
        """
        
        try:
            if self._controllerSolver:
                self._controllerSolver.CleanUp()
                self._controllerSolver = None
                
            self._solveStack = []
            self._forgetStack = []
            self._resetNewCalcStack = []
            self._resetNewFixedStack = []
            self._iterationStack = []
            self._consistencyErrorStack = []
            
            self.lastConsistErrrors.CleanUp()
            self.lastUnconvRecycles.CleanUp()        
        except:
            self.InfoMessage('ErrInCleanUp', (self.GetPath(),), MessageHandler.errorMessage)
            
        super(Flowsheet, self).CleanUp()
        
        
    def GetParameterValue(self, paramName):
        """
        If NULIQPH_PAR not known, use 1 as default
        (done this way to allow parent value to be used)
        """
        value = super(Flowsheet, self).GetParameterValue(paramName)
        if value != None: return value
        if paramName == NULIQPH_PAR:
            return 1
        
    def GetTolerance(self):
        return self.GetParameterValue(MAXERROR_PAR)
    
    def PushSolveOp(self, op):
        #if op.GetPath() == '/Prop1':
            #a = 1
        if not (op.IsOnStack(ON_SOLVE_STACK) or op.IsPushBlocked()):
            op.AddStackStatus(ON_SOLVE_STACK)
            self._solveStack.append(op)
        if self.parentUO:
            self.parentUO.PushSolveOp(self)
            
    def PopSolveOp(self):
        if len(self._solveStack):
            op = self._solveStack.pop()
            op.DelStackStatus(ON_SOLVE_STACK)
            return op
        else:
            return None
    

    def RemoveOpFromSolveStack(self, op):
        """remove op from solve stack, regardless of its location"""
        if self.parentUO:
            self.parentUO.RemoveOpFromSolveStack(op)
            
        if op in self._solveStack:
            i = self._solveStack.index(op)
            del self._solveStack[i]
            op.DelStackStatus(ON_SOLVE_STACK)
            
    def PushForgetOp(self, op):
        if self.parentUO:
            self.parentUO.Solver().PushForgetOp(op)
            return
        
        if not (op.IsOnStack(ON_FORGET_STACK) or op.IsPushBlocked()):
            op.AddStackStatus(ON_FORGET_STACK)
            self._forgetStack.append(op)
       
    def PopForgetOp(self):
        #if self.parentUO:
        #    return self.parentUO.Solver().PopForgetOp()
        
        if len(self._forgetStack):
            op = self._forgetStack.pop()
            op.DelStackStatus(ON_FORGET_STACK)
            return op
        else:
            return None
    
    def RemoveOpFromForgetStack(self, op):
        """remove op from forget stack, regardless of its location"""
        if self.parentUO:
            self.parentUO.RemoveOpFromForgetStack(op)
            
        if op in self._forgetStack:
            i = self._forgetStack.index(op)
            del self._forgetStack[i]
            op.DelStackStatus(ON_FORGET_STACK)
            
    def PushResetCalcPort(self, port):
        if self.parentUO:
            self.parentUO.Solver().PushResetCalcPort(port)
            return
        
        if not port.IsOnStack(ON_RESET_CALC_STACK):
            port.AddStackStatus(ON_RESET_CALC_STACK)
            self._resetNewCalcStack.append(port)

    def PopResetCalcPort(self):
        if self.parentUO:
            return self.parentUO.Solver().PopResetCalcPort()
        
        if len(self._resetNewCalcStack):
            port = self._resetNewCalcStack.pop()
            port.DelStackStatus(ON_RESET_CALC_STACK)
            return port
        else:
            return None

    def PushResetFixedPort(self, port):
        if self.parentUO:
            self.parentUO.Solver().PushResetFixedPort(port)
            return

        if not port.IsOnStack(ON_RESET_FIXED_STACK):
            port.AddStackStatus(ON_RESET_FIXED_STACK)
            self._resetNewFixedStack.append(port)

    def PopResetFixedPort(self):
        if self.parentUO:
            return self.parentUO.Solver().PopResetFixedPort()
        
        if len(self._resetNewFixedStack):
            port = self._resetNewFixedStack.pop()
            port.DelStackStatus(ON_RESET_FIXED_STACK)
            return port
        else:
            return None
        
    def PushIterationProperty(self, prop, value):
        """add BasicProperty prop to stack of estimated properties
        that have with new values available"""
        if not prop.__dict__.has_key('_newIterationValue'):
            self._iterationStack.append(prop)
        prop._newIterationValue = value

    def PopIterationProperty(self):
        """pop BasicProperty prop from stack of estimated properties
        that have with new values available
        return tuple (prop, newValue) """
        if len(self._iterationStack):
            prop = self._iterationStack.pop()
            value = prop._newIterationValue
            del prop._newIterationValue
            return (prop, value)
        else:
            return None

    def PushConsistencyError(self, prop, value):
        """add BasicProperty prop to the inconsistency list
        value is the conflicting value calculated"""
        if not prop.__dict__.has_key('_consistencyError'):
            prop._consistencyError = value
            self._consistencyErrorStack.append(prop)

    def PopConsistencyError(self):
        """pop BasicProperty (prop, value) tuple from list of
        consistency errors - value is the conflicting value for prop"""
        if len(self._consistencyErrorStack):
            prop = self._consistencyErrorStack.pop()
            value = prop._consistencyError
            del prop._consistencyError
            return (prop, value)
        else:
            return None


    def AddController(self, controller):
        """
        add controller to controllerSolver
        - make a controllerSolver if necessary
        """
        if self._controllerSolver == None:
            # if we don't have one of these, make it
            self._controllerSolver = Controller.ControllerSolver(self)
        self._controllerSolver.AddController(controller)
            
    def RemoveController(self, controller):
        """remove controller from list of controllers that as solved simultaneously"""
        if self._controllerSolver:
            self._controllerSolver.RemoveController(controller)
    
    def SolverForget(self):
        """Forget anything calculated as a result of information that is
        now changed
        """
        if self.parentUO:
            self.parentUO.Solver().SolverForget()
        
        self._isForgetting = 1
        PopForgetOp = self.PopForgetOp
        PopResetCalcPort = self.PopResetCalcPort
        PopResetFixedPort = self.PopResetFixedPort
        try:
            #op = self.PopForgetOp()
            op = PopForgetOp()
            while op:
                if not op is self:
                    op.BlockPush(1)
                    try:
                        try:
                            #self.InfoMessage('ForgettingOp', op.GetPath())
                            if op.GetParameterValue(IGNORED_PAR) == None:
                                op.Solve()
                        except (ArithmeticError, 
                                Error.SimError,
                                Error.CallBackException), e:
                            pass  # skip these errors when forgetting - may not be necessary
                        
                        for port in op.GetPorts():
                            if port.GetParentOp() == op:
                                port.UpdateConnection()
            
                        op.Forget()
                        
                        #port = self.PopResetCalcPort()
                        port = PopResetCalcPort()
                        while port:
                            port.ResetNewCalc()
                            #port = self.PopResetCalcPort()
                            port = PopResetCalcPort()
                    finally:
                        op.BlockPush(0)
                #op = self.PopForgetOp()
                op = PopForgetOp()
    
            #port = self.PopResetFixedPort()
            port = PopResetFixedPort()
            while port:
                port.ResetNewFixed()
                #port = self.PopResetFixedPort()
                port = PopResetFixedPort()
        finally:
            self._isForgetting = 0
     
    def IsForgetting(self):
        if self.parentUO:
            return self.parentUO.Solver().IsForgetting()
        return self._isForgetting
    
    def ForgetAllCalculations(self):
        self.lastConsistErrrors.CleanUp()
        self.lastUnconvRecycles.CleanUp()
        super(Flowsheet, self).ForgetAllCalculations()
    
    def IsSolving(self):
        """Indicate if it is solving, given that it is not forgetting"""
        if self.parentUO:
            return self.parentUO.Solver().IsSolving()
        
        if not self._isForgetting:
            return self._isSolving
        return 0
    
    def Solve(self):
        """Solve this flowsheet"""
        
        self._isSolving = 1
        path = self.GetPath()
        if REPORT_TIME:
            self.InfoMessage('InitSolveTime', (time.asctime(), time.time()))
        self.unitOpMessage = ('OK',)
        try:
            self.InnerSolve()
            if self.hold:
                self.unitOpMessage = ('On Hold',)
                self._isSolving = 0
                return 1
            
            if self._controllerSolver:
                if self.IsForgetting():
                    pass
                else:
                    self._controllerSolver.Solve()
                    
            if not self.IsForgetting():
                self.InfoMessage('DoneSolving',self.name)
        finally:
            self._isSolving = 0
        if REPORT_TIME:
            self.InfoMessage('InitSolveTime', (time.asctime(), time.time()))
            
        # Notify associated objects
        if not self.IsForgetting():
            for obj in self.associatedObjs:
                obj.NotifySolved(self)
            
        return 1  # nothing else needs doing
        
    def InnerSolve(self):
        """Solve this flowsheet - inside controller loops"""
        
        path = self.GetPath()
        
        tolerance    = self.GetParameterValue(MAXERROR_PAR)
        maxIter      = self.GetParameterValue(MAXITER_PAR)
        maxStep      = self.GetParameterValue(MAXRECYCLESTEP_VAR)
        recycDetails = self.GetParameterValue(RECYCLE_DETAILS_VAR)
        
        uncRecyclesDict = self.lastUnconvRecycles.GetDictionary()
        consErrorDict = self.lastConsistErrrors.GetDictionary()
        
        # clear any consistency errors left over
        PopConsistencyError = self.PopConsistencyError
        SolverForget = self.SolverForget
        PopSolveOp = self.PopSolveOp
        PopResetCalcPort = self.PopResetCalcPort
        PopIterationProperty = self.PopIterationProperty
        InfoMessage = self.InfoMessage
        
        while PopConsistencyError(): pass
        
        iter = 0
        jacobian = None
        if not maxStep:
            maxStep = .05
        while iter < maxIter:
            iter += 1
            #print iter
            SolverForget()
            if self.hold: return 1
            try:
                op = PopSolveOp()
                while op:
                    if not op is self and op.GetParameterValue(IGNORED_PAR) == None:
                        op.BlockPush(1)
                        try:
                            InfoMessage('SolvingOp', op.GetPath())
                            op.unitOpMessage = ('',)
                            op.Solve()
                            for port in op.GetPorts():
                                port.UpdateConnection()
                            for obj in op.associatedObjs:
                                obj.NotifySolved(op)
                            for obj in op.designObjects.values():
                                obj.NotifyUnitOpSolved()
                        finally:
                            op.BlockPush(0)
                            
                            #Remove the unit op if it got attempted to solve
                            if uncRecyclesDict and uncRecyclesDict.has_key(op):
                                del uncRecyclesDict[op]
                            if consErrorDict and consErrorDict.has_key(op):
                                del consErrorDict[op]
                                
                    op = PopSolveOp()
            finally:
                port = PopResetCalcPort()
                while port:
                    port.ResetNewCalc()
                    port = PopResetCalcPort()
            
            nIterationValues = len(self._iterationStack)
            if nIterationValues <= 0:
                    
                break
            
            maxError = 0.0
            maxErrProp = ''
            for i in range(nIterationValues):
                prop = self._iterationStack[i]
                if prop._myPort and recycDetails:
                    InfoMessage('RecycleErrorDetail',(prop.GetParent().GetParent().GetPath(),
                                      prop.GetType().name, prop._newIterationValue, prop._value))
                err = prop.CalculateError(prop._newIterationValue)
                if maxError < err:
                    maxError = err
                    maxErrProp = prop.GetPath()
                
            for prop in self._consistencyErrorStack:
                if prop._myPort and recycDetails:
                    InfoMessage('RecycleConsistency' ,(prop.GetParent().GetParent().GetPath(),
                                     prop.GetType().name, prop._consistencyError, prop._value))
                err = prop.CalculateError(prop._consistencyError)
                if maxError < err:
                    maxError = err
                    maxErrProp = prop.GetPath()
            
            InfoMessage('RecycleIter', (iter, maxError, maxErrProp))
            
            
            if maxError < tolerance and len(self._consistencyErrorStack) == 0:
                while PopIterationProperty(): pass
                break
                
            if iter + 1 < maxIter:
                # broyden acceleration for successive substitution
                # Solve f(x) = 0 where f(x) = g(x) - x
                # g(x) is the new value of x calculated by the flowsheet given x
                # thus g(x) will be values - the new iteration values
                # lastValues will be x
                # errors will be g(x) - x -> lastvalues - values
                # for UpdateJacobian B will be jacobian - initially identity
                # dx is newValues - lastValues
                # dF is errors - lastErrors
                
                if jacobian == None or jacobian.shape[0] != nIterationValues:
                    # use identity matrix as initial jacobian
                    values = zeros(nIterationValues, Float)
                    lastValues = zeros(nIterationValues, Float)
                    indexDict = {}
                    for i in range(nIterationValues):
                        prop = self._iterationStack[i]
                        indexDict[prop] = i
                        lastValues[i] = prop._value / prop.GetType().scaleFactor
                        values[i] = prop._newIterationValue / prop.GetType().scaleFactor
                    jacobian = identity(nIterationValues, Float)
                    newValues = values
                    errors = lastValues - values
                else:
                    for prop in self._iterationStack:
                        values[indexDict[prop]] = prop._newIterationValue / prop.GetType().scaleFactor
                    errors = lastValues - values
                    adjustment = dot(jacobian, errors)
                    largestChange = max(abs(adjustment))
                    if largestChange > maxStep:
                        adjustment *= (maxStep/largestChange)
                        
                    newValues = lastValues - adjustment
                    jacobian = self.UpdateJacobian(jacobian, dx, errors - lastErrors)

                for prop in self._iterationStack:
                    propType = prop.GetType()
                    val = newValues[indexDict[prop]]
                    if propType.name == FRAC_VAR: val = clip(val, 0.0, 1.0)
                    prop.SetValue( val * propType.scaleFactor, FIXED_V | ESTIMATED_V)
                while PopIterationProperty(): pass

                dx = newValues - lastValues
                lastErrors = array(errors)
                lastValues = array(newValues)
                    
            else:
                # this will fail on iteration overflow so just clear stack
                # without updating port so the differences can be examined
                #prop = self.PopIterationProperty()
                prop = PopIterationProperty()
                while prop:
                    #Don't let this new code stop things
                    try:
                        if prop[0].CalculateError(prop[1]) > tolerance:
                            port = prop[0].GetParent()
                            uo = port.GetParent()
                            uncRecyclesDict[uo] = (port, prop)
                            port.AddToBorrowedIn(self.lastUnconvRecycles)
                    except:
                        pass
                    prop = PopIterationProperty()
                    
            if len(self._solveStack) > 0:
                # just clear the consistency stack for next iteration
                # but don't if there is nothing left to solve
                #while self.PopConsistencyError(): pass
                while PopConsistencyError(): pass
                
                
        #Recycles that haven't been resolved. Both, new and old ones
        if uncRecyclesDict:
            #Do some last checking to make sure recycles are indeed still there
            uoLst = uncRecyclesDict.keys()
            for uo in uoLst:
                port_props = uncRecyclesDict[uo]
                if not port_props[0].GetConnection():
                    del uncRecyclesDict[uo]
            if uncRecyclesDict:        
                self.unitOpMessage = ('UnresolvedRecycles', (str(self.lastUnconvRecycles),))
                self.InfoMessage('UnresolvedRecycles', (path, str(self.lastUnconvRecycles)))
            
        if iter >= maxIter:
            self._isSolving = 0
            raise Error.SimError("MaxSolverIterExceeded", (maxIter, path))
        
        
        if len(self._consistencyErrorStack):
            # just raise first error
            self._isSolving = 0
            try:
                for prop in self._consistencyErrorStack:
                    port = prop.GetParent()
                    uo = port.GetParent()
                    consErrorDict[uo] = (port, (prop, prop._consistencyError))
                    port.AddToBorrowedIn(self.lastConsistErrrors)
            except:
                pass
                
            self.unitOpMessage = ('UnresolvedConsistencyErrors', (str(self.lastConsistErrrors),))
            self.InfoMessage('UnresolvedConsistencyErrors', (path, str(self.lastConsistErrrors)))
            raise Error.ConsistencyError(self._consistencyErrorStack[0])
        
        elif consErrorDict:
            self.unitOpMessage = ('UnresolvedConsistencyErrors', (str(self.lastConsistErrrors),))
            self.InfoMessage('UnresolvedConsistencyErrors', (path, str(self.lastConsistErrrors)))
            
        return 1
    
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
        if abs(denom) < 1.e-100:
            return B       # what else to do?
        
        return B + outerproduct((dx - dot(B, dF)), dotdxB)/denom

    def Solver(self): return self
    def ValidateOk(self):
        """True if the uo is ready to be calculated"""
        ##      Perhaps calling a method for counting degrees of freedom
        return 1
    
    def AdjustOldCase(self, version):
        """apply any necessary fixups to a recalled operation"""
        if version[0] < 20:
            if not hasattr(self, 'hold'):
                self.hold = 0
        if version[0] < 32:
            if not hasattr(self, '_isSolving'):
                self._isSolving = 0
                
        if version[0] < 40:
            if not hasattr(self, 'lastConsistErrrors'):
                self.lastConsistErrrors = ConsistencyErrorDict()
            if not hasattr(self, 'lastUnconvRecycles'):
                self.lastUnconvRecycles = UnconvRecycleDict()
                
        if not self.parameters.has_key(MAXITERCONT_PAR):
            self.parameters[MAXITERCONT_PAR] = 20
            
        super(Flowsheet, self).AdjustOldCase(version)
    
    def adjustVersion(self, revertFunction):
        """if object version different than code version due to recall"""
        
        #This call has to be made always because connections in ports get half broken
        #when pickling (__getstate__) but they can not be restored in 
        #the __setstate__ call because the order of how the port are being restored is not guaranteed
        self.walk(RestorePortConnections)
        
        if self.version[0] > VERSION[0]:
            # use revert code in newer version to fix up for this version
            # user RExec to try and protect from malicious
            self.InfoMessage('RevertingFromNewerVersion', (self.version[0], self.version[1], VERSION[0], VERSION[1]))
            r = RExec()
            r.r_exec(revertFunction)
            
            #Make sure the restricted environment can see the basics
            rmain = r.add_module('__main__')
            rmain.self = self
            rmain.VERSION = VERSION
            
            #Revert
            r.r_exec('revertToVersion(self, VERSION)')

        elif self.version[0] < VERSION[0]:
            # update object to current code
            
            #Make sure it has a place to store the message by doing fix for < version 18
            #This one can not be moved to the AdjustOldCase method and has to be done first!!
            if self.version[0] < 18:
                self.walk(CreateMsgStack)
            
            #Pass a message
            self.InfoMessage('AdjustingFromOlderVersion', (self.version[0], self.version[1], VERSION[0], VERSION[1]))
            
            if self.version[0] < 10: 
                self.walk(AdjustThermo)
            
            #Between version 18 and 23 the thermoAdmin attribute disappeared.
            if self.version[0] > 17 and self.version[0] < 23:
                if not hasattr(self, 'thermoAdmin'):
                    self.thermoAdmin = None
                #Somehow force a thAdmin to be there
                if not self.thermoAdmin:
                    if self.thCaseObj:
                        #There is one right here
                        self.SetThermoAdmin(self.thCaseObj.thermoAdmin)
                
                #Check if there are more than one thermoAdmin due to old bugs
                def LoadThermoAdmin(uo, thAdminList):
                    if uo.thCaseObj:
                        if not uo.thCaseObj.thermoAdmin in thAdminList:
                            thAdminList.append(uo.thCaseObj.thermoAdmin)
                thAdminList = []
                self.walk(LoadThermoAdmin, (thAdminList,))
                
                if thAdminList:
                    myThAdmin = thAdminList[0]
                    if not self.thermoAdmin:
                        self.SetThermoAdmin(myThAdmin)
                    #Adjust old case needed before merging
                    myThAdmin.AdjustOldCase(self.version)
                    for thAdmin in thAdminList[1:]:
                        #Adjust old case needed before merging
                        thAdmin.AdjustOldCase(self.version)
                        myThAdmin.MergeThermoAdmin(thAdmin)
                            
            #Adjust ThermoAdmin before the Generic adjust
            thermoAdmin = self.GetThermoAdmin()
            if thermoAdmin:
                thermoAdmin.AdjustOldCase(self.version)
                
            #Generic adjust
            self.AdjustOldCase(self.version)

            #Do this last. At least after AdjustOldCase!
            if self.version[0] < 20:
                self.walk(FixThCaseNames)
    
            #Set it again in case it got deleted form previous fixes
            if self.version[0] > 17 and self.version[0] < 23:
                if self.thCaseObj:
                    self.SetThermoAdmin(self.thCaseObj.thermoAdmin)                
                
            self.version = VERSION


    def Clone(self):
        if len(self._solveStack) \
           or len(self._forgetStack) or len(self._consistencyErrorStack) or len(self._iterationStack):
            self.InfoMessage('CantCloneFlowsheet', (self.GetPath(),))
            return None
        elif len(self.lastUnconvRecycles.GetDictionary()) or len(self.lastConsistErrrors.GetDictionary()):
            self.InfoMessage('CantCloneFlowsheet', (self.GetPath(),))
            return None
        return super(Flowsheet, self).Clone()
    
    
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(Flowsheet, self)._RemoveFromCloneList(clone, attrNamesToClone)
        
        dontClone = ["_solveStack", "_forgetStack", "_resetNewCalcStack", "_resetNewFixedStack", "_iterationStack",
                     "_consistencyErrorStack", "_controllerSolver", "_isForgetting", "_isSolving",
                     "hold", "lastUnconvRecycles", "lastConsistErrrors"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
            
class SubFlowsheet(UnitOperations.UnitOperation):
    """
    a sub flowsheet without a solver - relies on parent flowsheet solving
    - the normal case for a subflowsheet
    - essentially a renamed UnitOperation
    """

    
class UnconvRecycleDict(dict):
    
    def __init__(self):
        self.objDict = {}    
    
    def __str__(self):
        retVal = ''
        for uo in self.objDict.keys():
            try:
                port = self.objDict[uo][0]
                prop, iterVal = self.objDict[uo][1]
                path = uo.ShortestPortPath(port)
                retVal += '%s.%s: %g Vs %g\n' %(path, prop._type.name, iterVal, prop._value)
                #retVal += '%s\n' %(path,)
            except:
                retVal += 'ErrorDisplaying\n'
        return retVal
        
    
    def GetDictionary(self):
        return self.objDict
    
    def DeleteObject(self, port):
        """This will get called when a port is getting deleted"""
        uoLst = self.objDict.keys()
        for uo in uoLst:
            try:
                if port is self.objDict[uo][0]:
                    del self.objDict[uo]
            except:
                pass
            
    def CleanUp(self):
        #Delete everything one by one
        uoLst = self.objDict.keys()
        for uo in uoLst:
            del self.objDict[uo]
        
            
class ConsistencyErrorDict(object):
    
    def __init__(self):
        self.objDict = {}
    
    def __str__(self):
        retVal = ''
        for uo in self.objDict.keys():
            try:
                port = self.objDict[uo][0]
                prop, iterVal = self.objDict[uo][1]
                path = uo.ShortestPortPath(port)
                retVal += '%s.%s: %g Vs %g\n' %(path, prop._type.name, iterVal, prop._value)
                #retVal += '%s\n' %(path,)
            except:
                retVal += 'ErrorDisplaying\n'
        return retVal    
    
    def GetDictionary(self):
        return self.objDict
    
    def DeleteObject(self, port):
        """This will get called when a port is getting deleted"""
        uoLst = self.objDict.keys()
        for uo in uoLst:
            try:
                if port is self.objDict[uo][0]:
                    del self.objDict[uo]
            except:
                pass
            
    def CleanUp(self):
        #Delete everything one by one
        uoLst = self.objDict.keys()
        for uo in uoLst:
            del self.objDict[uo]
            
            
    
revertToVersion = '''
def revertToVersion(flowsheet, version):
    """make necessary changes in flowsheet to run version """
    flowsheet.version = version
    
    if version[0] < 36:
        def RestorePortConnections(uo):
            """Port connections are stroed as paths in order to make things easier on pickle. This method restores the connections"""
            
            #Find the top most parent
            topParent = uo.GetParent()
            while topParent:
                tempParent = topParent.GetParent()
                if not tempParent:
                    break
                topParent = tempParent
            if not topParent: topParent = uo
            
            
            for port in uo.GetPorts():
                connPath = port._connection
                if connPath:
                    if isinstance(connPath, str):
                        try:
                            if connPath[0] == '/':
                                connPath = connPath[1:]
                            splitConn = connPath.split('.')
                            parent = topParent
                            for uoname in splitConn[:-1]:
                                parent = parent.GetChildUO(uoname)
                            conn = parent.GetPort(splitConn[-1])
                            port._connection = conn
                            conn._connection = port
                        except:
                            port._connection = None
                            
                            
        flowsheet.walk(RestorePortConnections)
    
'''


def FixThCaseNames(uo):
    """Remove "." from thCase names and make the name == to the case"""
    if uo.thCaseObj:
        thAdmin = uo.thCaseObj.thermoAdmin
        caseList = []
        nameList = []
        caseObjList = []
        for name, thCaseObj in thAdmin.GetContents():
            caseList.append(thCaseObj.case)
            nameList.append(thCaseObj.name)
            caseObjList.append(thCaseObj)
            
        #Check case by case if the names are unique.
        for i in range(len(caseList)):
            name = nameList[i]
            case = caseList[i]
            if case != name:
                #First try to make the case equal to the name. This should do for most cases
                case = name
                while case in caseList:
                    case += '_'
                newThCase = re.sub('\.', '_', case)
                thAdmin.ChangeThermoCaseName(caseObjList[i].provider, caseList[i], newThCase)                    
                caseObjList[i].name = case
                caseObjList[i].case = case
                caseList[i] = case

                
def RestorePortConnections(uo):
    """Port connections are stroed as paths in order to make things easier on pickle. This method restores the connections"""
    
    #Find the top most parent
    topParent = uo.GetParent()
    while topParent:
        tempParent = topParent.GetParent()
        if not tempParent:
            break
        topParent = tempParent
    if not topParent: topParent = uo
    
    
    for port in uo.GetPorts():
        connPath = port._connection
        if connPath:
            if isinstance(connPath, str):
                try:
                    if connPath[0] == '/':
                        connPath = connPath[1:]
                    splitConn = connPath.split('.')
                    parent = topParent
                    for uoname in splitConn[:-1]:
                        parent = parent.GetChildUO(uoname)
                    conn = parent.GetPort(splitConn[-1])
                    port._connection = conn
                    conn._connection = port
                except:
                    port._connection = None
            
def CreateMsgStack(uo):
    """Creates an atribute to store info messages when there is not an infoCallBAck object available"""
    if not hasattr(uo, '_unsentMsgStack'):
        uo._unsentMsgStack = []

        
def AdjustThermo(uo):
    """Adjusts the thermo variables to comply with newest code"""

    #Perhaps could adjust thermo according to a version
    
    parent = uo.GetParent()

    #If doesn't support new variable    
    if not hasattr(uo, 'thCaseObj'):

        #If has old var created by cmd interface        
        if hasattr(uo, 'CmdThermo'):
            thermoAdmin = uo.CmdThermo.thermoAdmin
            provider = uo.CmdThermo.provider
            case = uo.CmdThermo.case
            package = uo.CmdThermo.package
            name = case.split('.')[-1]
            uo.thCaseObj = ThermoCase(thermoAdmin, provider, case, package)
            uo.thCaseObj.name = name

        #If parent already supports new variable and has same thermo
        elif hasattr(parent, 'thCaseObj'):
            uo.thCaseObj = parent.thCaseObj
            
        #Parent doesn't support new var, but has some thermo (old cases not created with cmd interface)
        elif hasattr(uo, 'thermoSelected'):
            if uo.thermoSelected and uo.thermoAdmin:
                thermoAdmin = uo.thermoAdmin
                provider = uo.thermoSelected[0]
                case = uo.thermoSelected[1]
                package = thermoAdmin.GetPropPkgString(provider, case)
                uo.thCaseObj = ThermoCase(thermoAdmin, provider, case, package)
                uo.thCaseObj.name = case.split('.')[-1]
        else:
            uo.thCaseObj = None

    else:
        if uo.thCaseObj:
            #If was done before the implementation of 'name'
            if not hasattr(uo.thCaseObj, 'name'):
                uo.thCaseObj.name = uo.thCaseObj.case.split('.')[-1]
    
    if hasattr(uo, 'thermoSelected'):
        del uo.thermoSelected
    if hasattr(uo, 'CmdThermo'):
        del uo.CmdThermo

