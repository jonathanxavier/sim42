"""Class definitions for the ports used by uos in the simulator

Classes:
PortDict -- Dict of ports
Port -- Base class for a port
Port_Material -- Material port. Inherits from Port
Port_Energy -- Energy port. Inherits from Port
Port_Signal -- Signal port. Inherits from Port

"""

from Variables import *
import S42Glob
from Error import SimError
import re, string
import Numeric
from Numeric import array, Float, Int, zeros, ones


ENERGY_PORT = 'Ene'
MATERIAL_PORT = 'Mat'
SIGNAL_PORT = 'Sig'
SIGNAL_TYPE_NONE = 'None'

PORT_STATE = 'State'
FIXALL_STATE = 0
ESTIMATEALL_STATE = 1
NONE_STATE = 2

class PortDict(dict):
    """Dictionary of ports. Inherits from dict

    keys -- Name of the port
    values -- Instance of Port

    """    
    def __init__(self):
        """Init an empty dictionary"""          
        dict.__init__(self)

    def __setitem__(self, key, item):
        """Only ports, no repetitions of values"""
        if not isinstance(item, Port): return
        if item in self.values(): return
        dict.__setitem__(self, key, item)

class Port(object):
    """Base class for specific ports"""
    def __init__(self, portType, parentOp, name=''):
        """Init basic info
        parent_op - the UnitOperation the port is part of
        """
        self._properties =  {} # dummy dictionary
        self._name = name
        self._parentOp = parentOp
        self._connection = None # if known it must be another port (of same type?)
        self._stackStatus = 0
        self._type = portType
        self._estimated = 0
        self._locked = False
        
        #The following list is used for:
        #keep track of objects other than the parent where instances 
        #of the port exist and clear from there in case of clean ups or deletions
        self._borrowedIn = []
        
        #Flag to see if all the specs into a port should be froced as estimates
        #self.forceEstimates = 0
        self.state = FIXALL_STATE
        
        
    def __getstate__(self):
        """return info to store"""
        try: 
            #Change the instance of the connection for a path
            #because pickle could run into infinite loops for complex simulations
            state = self.__dict__.copy()
            connPort = state.get('_connection', None)
            if connPort:
                state['_connection'] = state['_connection'].GetPath()
            return state
        except: 
            return self.__dict__
        
    def __setstate__(self, oldState):
        """build packages from saved info"""
        self.__dict__ = oldState
        

    def CloneContents(self, clone):
        
        #Only preserve these attributes
        clone._estimated = self._estimated
        clone._locked = self._locked
        clone.state = self.state
        
        #Now clone the properties
        props = self._properties
        propsClone = clone._properties
        for propName in props:
            prop = props[propName]
            if propName in propsClone:
                #Delete if already there. Clone through clone method !
                propsClone[propName].CleanUp()
                del propsClone[propName]
                
            #Cloning of properties do not assign parents
            propsClone[propName] = prop.Clone()
            propsClone[propName]._myPort = clone

        
    def Clone(self):
        """Clone with no parent, no connection, no passed values and no list of borrowed In"""
        clone = self.__class__(self._type, None, self._name)
        
        self.CloneContents(clone)
        
        return clone
        
    def SetLocked(self, lock):
        """if lock = true then the port can't be deleted"""
        self._locked = bool(lock)

    def GetLocked(self):
        """True if the port is locked for deletion"""
        return self._locked
        
    def CleanUp(self):
        """Necessary clean up in order to get rid of a port"""
        self.Disconnect()
        
        #Delete myself from all the places where I'm being borrowed or used
        for obj in self._borrowedIn:
            obj.DeleteObject(self)
            
        self._properties = {}
        self._parentOp = None
        self._name = None
        self._borrowedIn = []

        
    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return t

    def GetBorrowedIn(self):
        """Get the list with all the unit operations where the port is borrowed"""
        return self._borrowedIn

    def AddToBorrowedIn(self, obj):
        """Adds a unit operations to the list that keeps track of where the port is being borrowed"""
        if not hasattr(obj, 'DeleteObject'):
            errMsg = """The port %s can not keep track of the obj %s\n
Error raised when calling the 'AddToBorrowedIn' method because the obj %s does not support
the method 'DeleteObj'
"""%(self.GetPath(), str(obj), str(obj))
            raise AssertionError(errMsg)
        if not obj in self._borrowedIn:
            self._borrowedIn.append(obj)

    def RemoveFromBorrowedIn(self, obj):
        """Removes a unit operations to the list that keeps track of where the port is being borrowed"""
        if obj in self._borrowedIn:
            idx = self._borrowedIn.index(obj)
            del self._borrowedIn[idx]


    def IsPortConnected(self): return self._connection
    def GetPortType(self): return self._type
    def GetParentOp(self): return self._parentOp
    def GetParent(self): return self._parentOp   # preferred more generically named version of GetParentOp
    def Rename(self, name): self._name = name
    def SetState(self, state):
        """Sets the state of a port (all fixed, all estimated, etc)"""
        if self.state == state: return
        op = self.GetParent()
        if op: 
            op.InfoMessage('ChangedPortState', (op.ShortestPortPath(self), state))
        self.state = state
        if state == ESTIMATEALL_STATE:
            self._estimated = 1
        elif state == FIXALL_STATE:
            self._estimated = 0
            self._parentOp.PushForgetOp(self._parentOp.GetParent())
            self._parentOp.PushSolveOp(self._parentOp.GetParent())
        
        if self._connection and self._estimated:
            # estimated ports don't pass information
            # make sure there is no passed value left
            for prop in self._connection._properties.values():
                if prop.GetCalcStatus() & PASSED_V:
                    prop.SetValue(None, UNKNOWN_V)
            return   
            
    def IsOnStack(self, flag):
        return self._stackStatus & flag
    
    def PropertyModified(self, property, calcStatus):
        """
        called when any property contained by this port is modified.
        """
        if calcStatus & FIXED_V:
            self._parentOp.PushSolveOp(self._parentOp)
            self._parentOp.PushResetFixedPort(self)
            self._parentOp.PushForgetOp(self._parentOp)
        elif calcStatus == (UNKNOWN_V|PARENT_V):
            self._parentOp.PushForgetOp(self._parentOp.GetParent())
            self._parentOp.PushSolveOp(self._parentOp.GetParent())
        elif calcStatus & (PASSED_V|PARENT_V):
            self._parentOp.PushSolveOp(self._parentOp)
            self._parentOp.PushResetCalcPort(self)
        elif calcStatus & CALCULATED_V:
            self._parentOp.PushResetCalcPort(self)
        elif calcStatus & UNKNOWN_V:
            self._parentOp.PushForgetOp(self._parentOp)
            self._parentOp.PushSolveOp(self._parentOp)
        #self.UpdateConnection()
        
    def AddStackStatus(self, flag):
        self._stackStatus |= flag
    def DelStackStatus(self, flag):
        self._stackStatus &= ~flag
    def ConnectTo(self, otherPort, internalCall=False):
        """create a connection between this port and otherPort
        always returns 1 to satisfy older error checks"""
        assert(isinstance(otherPort, Port))
        
        if self._connection is otherPort:
            return 1
        
        parentOp = self._parentOp
        
        if self._connection != None:
            #Disconnect first if already connected
            self.Disconnect(True)
            
            
        if self._type == otherPort._type and not self._type & SIG:
            raise SimError('ConnectSameTypePorts', self._parentOp.GetPath())
        
        
        #let parent op know what is happening
        parentOp.MakingPortConnection(self, otherPort)
        self._connection = otherPort
        otherPort.ConnectTo(self, True)
        self.UpdateConnection()
                
        if not internalCall and not parentOp.IsSolving():
            #We need to keep track of the consistency errors so they get notifed to the user
            solver = parentOp.Solver()
            if solver and len(solver._consistencyErrorStack):
                if not parentOp in solver._solveStack and not otherPort._parentOp in solver._solveStack:
                    if not self._estimated and not otherPort._estimated:
                        parentOp.ForgetAllCalculations()
        
        return 1

    def Disconnect(self, internalCall=False):
        """break connection to other port"""
        if not self._connection: return
        
        parentOp = self._parentOp
        
        #Remove the unit op from the dict of last consistency errors
        if not parentOp.IsSolving():
            solver = parentOp.Solver()
            if solver:
                consErrorDict = solver.lastConsistErrrors.GetDictionary()
                if consErrorDict and consErrorDict.has_key(parentOp):
                    #Can not delete blindly. Force a resolve ??
                    #del consErrorDict[parentOp]
                    parentOp.ForgetAllCalculations()
                

        other = self._connection
        portPath = parentOp.ShortestPortPath(self)
        otherpath = other._parentOp.ShortestPortPath(other)
        
        parentOp.InfoMessage ('BeforePortDisconnect', (portPath, otherpath))        
        
        #let parent op know what is happening
        parentOp.MakingPortConnection(self, None)
        
        self._connection = None
        #self.UpdateConnection()
        
        other.Disconnect(True)
        self.UpdateConnection()
        parentOp.InfoMessage ('AfterPortDisconnect', (portPath, otherpath))
        
        if not internalCall and not parentOp.IsSolving():
            #We need to keep track of the consistency errors so they get notifed to the user
            solver = parentOp.Solver()
            if solver and len(solver._consistencyErrorStack):
                parentOp.ForgetAllCalculations()
                #if not parentOp in solver._solveStack:
                    #try:
                        #consErrorDict = solver.lastConsistErrrors.GetDictionary()
                        #for prop in solver._consistencyErrorStack:
                            #port = prop.GetParent()
                            #uo = port.GetParent()
                            #consErrorDict[uo] = (port, (prop, prop._consistencyError))
                            #port.AddToBorrowedIn(solver.lastConsistErrrors)
                    #except:
                        #pass
                    
                #Do not raise errors for now
                #raise Error.ConsistencyError(solver._consistencyErrorStack[0])
        
        
    def Forget(self, skipStatus=0):
        """
        forget (if necessary) variable values
        if skipStatus is not 0 then variable will only be skipped if calcStatus
        has one of the skipStatus bits set
        """
        if self._connection:
            connProps = self._connection._properties
        else:
            connProps = None
        for propName in self._properties.keys():
            prop = self._properties[propName]
            if connProps and connProps.has_key(propName):
                connProp = connProps[propName]
            else:
                connProp = None
                
            prop.Forget(connProp, skipStatus)
            
    def ForgetAllCalculations(self):
         for prop in self._properties.values():
             prop.ForgetForStatus(CALCULATED_V)
         if self._connection != None:
             self._connection.ForgetAllPassed()
    def ForgetAllPassed(self):
         for prop in self._properties.values():
             prop.ForgetForStatus(PASSED_V)
             
    def IsEstimated(self):
        """Returns true if the port is estimated"""
        return self._estimated
    
    def SetEstimated(self):
        """
        sets flag indicating that one of this ports properties
        has been estimated
        """
        self._estimated = 1
        
    def CheckEstimated(self):
        """
        A property that was estimated is no longer
        Check to see if any others still are and if not clear
        the estimated flag.
        """
        self._estimated = 0  # clear flag to start
        if self.state == ESTIMATEALL_STATE:
            #State overrides the behaviour. keep as recycle even if no other are estimates
            self._estimated = 1
        elif self.state == FIXALL_STATE:
            self._estimated = 0
        else:
            for prop in self._properties.values():
                if prop.GetCalcStatus() & ESTIMATED_V:
                    self._estimated = 1
                    return
        solver = self.Solver()
            
            
    def Solver(self):
        p = self.GetParent()
        if p != None:
            return p.Solver()
            
    def AllPropsAsEstimates(self):
        """Make sure that every spec is an estimate"""
        conn = self._connection
        
        #Needs to clear the connected port ?
        needClearConn = 0
        if not self._estimated:
            needClearConn = 1
            
        for prop in self._properties.values():
            if (prop._calcStatus & FIXED_V) and not (prop._calcStatus & ESTIMATED_V):
                #Estimate all the fixed props
                prop._calcStatus |= ESTIMATED_V
                self._estimated = 1
                if needClearConn and conn:
                    # estimated ports don't pass information
                    # make sure there is no passed value left
                    for connProp in conn._properties.values():
                        if connProp._calcStatus & PASSED_V:
                            connProp.SetValue(None, UNKNOWN_V)
                    needClearConn = 0
                    
        
    def AllPropsAsNonEstimates(self):
        """Make sure that every estimate is only a spec"""
        conn = self._connection
        
        #Needs to clear the connected port ?
        needUpdateConn = 0
        if self._estimated:
            needUpdateConn = 1
            
        for prop in self._properties.values():
            if (prop._calcStatus & FIXED_V) and (prop._calcStatus & ESTIMATED_V):
                #Estimate all the fixed props
                prop._calcStatus &= ~ESTIMATED_V
        self._estimated = 0
        if needUpdateConn: self.UpdateConnection()
        
            
    def UpdateConnection(self):
        """passes any information available through the connection
        always returns 1 to satisfy older error checks
        """
        conn = self._connection
        if not conn:
            for prop in self._properties.values():
                if prop.GetCalcStatus() & PASSED_V:
                    prop.SetValue(None, UNKNOWN_V)
            return 1

        if self._estimated:
            # estimated ports don't pass information
            # make sure there is no passed value left
            for prop in conn._properties.values():
                if prop.GetCalcStatus() & PASSED_V:
                    prop.SetValue(None, UNKNOWN_V)
            return   
        
        isForgetting = self._parentOp.IsForgetting()
        connProps = conn._properties
        connPropNames = connProps.keys()
        myProps = self._properties
        connParent = conn._parentOp
        for i in myProps.keys():
            myProp = myProps[i]
            if not i in connPropNames:
                connProps[i] = BasicProperty( myProp.GetType().name, conn)
            connProp = connProps[i]
            myStatus = myProp.GetCalcStatus()
            connStatus = connProp.GetCalcStatus()
            
            if connStatus & ESTIMATED_V:
                # the connection was an estimate
                # if I have known value and we aren't forgetting
                # add connection port to iteration stack
                myValue = myProp.GetValue()
                if not isForgetting and myValue != None:
                    connParent.PushIterationProperty(connProp, myValue)
                    
            elif isForgetting:
                # if calculated value was not recalculated during forget solve
                # (i.e. not NEW_V) then forget the connected value                
                if connStatus & PASSED_V:
                    isNew = myStatus & NEW_V
                    isCalc = myStatus & CALCULATED_V
                    if((myStatus & UNKNOWN_V) or
                       (isNew and not isCalc) or
                       (isCalc and not isNew) or
                       myProp.GetValue() != connProp.GetValue()):
                        connProp.SetValue(None, UNKNOWN_V)
            else:
                # normal calculation update from connection as appropriate
                myValue = myProp.GetValue()
                connValue = connProp.GetValue()
                if myValue != None and not (myStatus & PASSED_V):
                    connProp.SetValue(myValue, PASSED_V)
                    
        return 1
    
    def UpdateInternalConnection(self):
        pass
        
    def ResetNewFixed(self):
        """Reset NEW_V for all properties of the port"""
        for i in self._properties.values():
            i.ResetNewFixed()
    
    def ResetNewCalc(self):
        """Reset NEW_V for all properties of the port"""
        for i in self._properties.values():
            i.ResetNewCalc()
    
    def GetNuKnownProps(self, type=None):
        """Number of properties with calcStatus != UNKNOWN_V"""
        nu = 0
        for i in self._properties.values():
            if i.GetValue() != None:
                if type == None or i.GetType().calcType & type: nu += 1
        return nu

    def GetKnownProps(self, type=None):
        """List of instances of properties with calcStatus != UNKNOWN_V"""
        props = []
        for i in self._properties.keys():
            prop = self._properties[i]
            if prop.GetValue() != None and (type == None or
                            prop.GetType().calcType & type):
                props.append(i)
        return props
    
    def GetProperties(self):
        return self._properties
    def GetProperty(self, propName):
        return self._properties.get(propName, None)  ## perhaps some error checking?
    
    def GetObject(self, description):
        """return object corresponding to description"""
        if self._properties.has_key(description):
            return self._properties[description]
        elif hasattr(self, description):
            return self.__dict__[description]
        #elif description == 'ForceEstimates':
            #return ForceEstimatesObj(self)
        elif description == PORT_STATE:
            return PortStateObj(self)
        else:
            return None

    def GetContents(self):
        """
        return the properties of this Port
        """
        result = []
        for i in self._properties.keys():
            result.append((i, self._properties[i]))
        return result
    
    def GetPropNames(self):
        return self._properties.keys()
  
    def GetPropInfo(self, propName=None):
        """Order of info: propName, value, calcStatus, type """
        propInfo = []
        portProps = self._properties
        if propName:
            if portProps.has_key(propName):
                propInfo.append((propName, portProps[propName].GetValue(),
                                 portProps[propName].GetCalcStatus(),
                                 portProps[propName].GetType().calcType))
        else:
            for i in portProps.keys():
                propInfo.append((i, portProps[i].GetValue(),
                                 portProps[i].GetCalcStatus(),
                                 portProps[i].GetType().calcType))
        return propInfo

    def GetPropValue(self, propName):
        prop = self.GetObject(propName)
        if prop:
            return prop.GetValue()
        return None

    def SetPropValue(self, propName, value, calcStatus):

        prop = self.GetObject(propName)
        if prop:
            prop.SetValue(value, calcStatus)
        else:
            var = string.split(propName, '_',1)
            if var[0] == CMPMASSFRAC_VAR or var[0] == STDVOLFRAC_VAR:
                raise SimError('CantSetSingleFrac', (propName, self.GetPath()))

            if not self._properties.has_key(propName):
                prop = self._properties[propName] = BasicProperty(propName, self)
                prop.SetValue(value, calcStatus)

    def GetLocalValue(self, propName, isForgetting=None):
        """return value for property with propName, but return None
        if that value was passed from outside and this is forget pass.
        The isForgetting flag can be passed if something already obtained that info
        Allowing this flag to be passed in was made in order to reduce the amout of times this gets called
        since the profiler said that this was time consuming call in a simulation"""
        try:
            prop = self._properties[propName]
            calcStatus = prop._calcStatus #GetCalcStatus()
            if isForgetting == None:
                isForgetting = self._parentOp.IsForgetting()
            if calcStatus & UNKNOWN_V:
                return None
            if isForgetting and calcStatus & PASSED_V:
                return None
            return prop.GetValue()
        except LookupError:
            return None
        
    def DelPropValue(self, propName):
        self._properties[propName].SetValue(None, UNKNOWN_V)
    def ShareWith(self, port, propType=None, calcStatus=CALCULATED_V):
        """shares bidirectionally all values with port
        (of PropertyType.calcType = propType if propType not None)
        """
        assert(type(port) == type(self))
        
        #Get this flag and pass it to GetLocalValue
        
        isForgetting = self._parentOp.IsForgetting()
        GetLocalValue = self.GetLocalValue
        SetPropValue = port.SetPropValue
        props = self._properties
        for i in props.keys():
            prop = props[i]
            if propType == None or prop._type.calcType & propType:
                SetPropValue(i, GetLocalValue(i, isForgetting), calcStatus)
            
        GetLocalValue = port.GetLocalValue
        SetPropValue = self.SetPropValue
        props = port._properties
        for i in props.keys():
            prop = props[i]
            if propType == None or prop._type.calcType & propType:
                SetPropValue(i, GetLocalValue(i, isForgetting), calcStatus)

    def SharePropWith(self, port, varType):
        """shares bidirectionally value of varType with port
        """
        assert(type(port) == type(self))
        port.SetPropValue(varType, self.GetLocalValue(varType), CALCULATED_V)
        self.SetPropValue(varType, port.GetLocalValue(varType), CALCULATED_V)

    def GetName(self):
        return self._name
    
    def GetPath(self):
        if self._parentOp:
            return self._parentOp.GetPath() + '.' + self._name
        else:
            return self._name
    def GetConnection(self):
        """just return connection port"""
        return self._connection

    def DeleteObject(self, prop):
        """
        just set the value of the prop to unknown
        """
        prop.SetValue(None, FIXED_V)
        
class Port_Material(Port):
    """Material port"""
    def __init__(self, portType, parentOp, name=''):
        """Inits a material port with two member variables
        parent_op - the UnitOperation the port is part of

        Member variables:
        _properties = Instance of MaterialPropertyDict()
        _arrProperties = Array properites Dict
        _compounds = Instance of CompoundList()
        _flashResults = Object with the flash results

        """        
        Port.__init__(self, portType, parentOp, name)
        self._properties =  MaterialPropertyDict(port=self)
        self._arrProperties = MaterialArrayPropertyDict(port=self)
        self._compounds = CompoundList(self)  # list which will contain BasicProperties
        self._flashResults = None
        self._attachedObj = None
    
    def CloneContents(self, clone):
        super(Port_Material, self).CloneContents(clone)
        
        #Now clone the properties
        cmps = self._compounds
        cmpsClone = clone._compounds
        for i in range(len(cmps)):
            cmp = cmps[i]
            #Cloning of properties do not assign parents
            cmpsClone.append(cmp.Clone())
            cmpsClone[-1]._myPort = clone
        
        for arrPropName in self._arrProperties:
            arrProp = self._arrProperties[arrPropName]
            clone._arrProperties[arrPropName] = []
            for i in range(len(arrProp)):
                prop = arrProp[i]
                #Cloning of properties do not assign parents
                clone._arrProperties[arrPropName].append(prop.Clone())
                clone._arrProperties[arrPropName][-1]._myPort = clone
        
    def Clone(self):
        clone = super(Port_Material, self).Clone()
            
        return clone
            
    def CleanUp(self):
        """
        clean up before deleting
        """
        super(Port_Material, self).CleanUp()
        self._compounds.CleanUp()
        self._arrProperties.CleanUp()
        self._compounds = None
        self._arrProperties = None
        self._flashResults = None
        
    def Forget(self, skipStatus=0):
        """
        forget (if necessary) variable values
        if skipStatus is not 0 then variable will only be skipped if calcStatus
        has one of the skipStatus bits set
        """
        
        #In reality, the safest way to know when to get rid of the flash
        #results would be by keeping track of the Z_FACTOR directly
        #The not (skipStatus & PARENT_V) was added because it was found in
        #lle.tst that one of the feed ports would be fully flashed but without
        #flash results.
        if not self.AlreadyFlashed() and not (skipStatus & PARENT_V):
            self._flashResults = None
            
        Port.Forget(self, skipStatus)
        if self._connection:
            connCompounds = self._connection._compounds
        else:
            connCompounds = None
        
        for i in range(len(self._compounds)):
            if connCompounds:
                connCompound = connCompounds[i]
            else:
                connCompound = None
            self._compounds[i].Forget(connCompound, skipStatus)

        #arrProperties
        for prop in self._arrProperties.keys():
            if self._connection:
                connCompounds = self._arrProperties[prop]
            else:
                connCompounds = None
            
            for i in range(len(self._arrProperties[prop])):
                if connCompounds:
                    connCompound = connCompounds[i]
                else:
                    connCompound = None
                self._arrProperties[prop][i].Forget(connCompound, skipStatus)
                
    def ForgetAllCalculations(self):
        Port.ForgetAllCalculations(self)
        self._flashResults = None
        for cmp in self._compounds:
            cmp.ForgetForStatus(CALCULATED_V)
        #arrProperties
        for prop in self._arrProperties.values():
            for cmp in prop:
                cmp.ForgetForStatus(CALCULATED_V)
                
    def ForgetAllPassed(self):
        Port.ForgetAllPassed(self)
        for cmp in self._compounds:
            cmp.ForgetForStatus(PASSED_V)            
        #arrProperties
        for prop in self._arrProperties.values():
            for cmp in prop:
                cmp.ForgetForStatus(PASSED_V)
                
    def CheckEstimated(self):
        """
        A property that was estimated is no longer
        Check to see if any others still are and if not clear
        the estimated flag.
        """
        Port.CheckEstimated(self)
        if self._estimated:
            return # parent already found estimate - no need to check

        for prop in self._compounds:
            if prop.GetCalcStatus() & ESTIMATED_V:
                self._estimated = 1
                return
        #arrProperties
        for prop in self._arrProperties.values():
            for cmp in prop:
                if cmp.GetCalcStatus() & ESTIMATED_V:
                    self._estimated = 1
                    return

    def SetState(self, state):
        """Sets the state of a port (all fixed, all estimated, etc)"""
        super(Port_Material, self).SetState(state)
        if self._connection and self._estimated:
            # estimated ports don't pass information
            # make sure there is no passed value left
            for prop in self._connection._compounds:
                if prop.GetCalcStatus() & PASSED_V:
                    prop.SetValue(None, UNKNOWN_V)
        
        
    def UpdateConnection(self):
        """passes any information available through the connection
        returns None on error, otherwise 1 
        """
        if not Port.UpdateConnection(self): 
            if self._estimated:
                # estimated ports don't pass information
                # make sure there is no passed value left
                for prop in self._connection._compounds:
                    if prop.GetCalcStatus() & PASSED_V:
                        prop.SetValue(None, UNKNOWN_V)
            return None
        
        if not self._connection:
            for prop in self._compounds:
                if prop.GetCalcStatus() & PASSED_V:
                    prop.SetValue(None, UNKNOWN_V)
            return 1

        if self._parentOp.GetThermo() != self._connection._parentOp.GetThermo():
            from sim.unitop import CrossConnector
            #Check if it is not a cross connector
            if isinstance(self._parentOp, CrossConnector.ConnectorNode):
                #As if it was reconnecting
                self._parentOp.MakingPortConnection(self, self._connection)
            elif isinstance(self._connection._parentOp, CrossConnector.ConnectorNode):
                #As if it was reconnecting
                self._connection._parentOp.MakingPortConnection(self._connection, self)
            elif self._parentOp.GetCompoundNames() != self._connection._parentOp.GetCompoundNames():
                #If the compounds are the same and have the same order then keep on going.
                self._parentOp.InfoMessage('DiffThCaseInConn', (self.GetPath(), self._connection.GetPath()), addToUnitOpMsg=1)
                self._connection._parentOp.unitOpMessage = ('DiffThCaseInConn', (self._connection.GetPath(), self._connection.GetPath()))
                return 0
        
        if self._estimated:
            # estimated ports don't pass information
            # make sure there is no passed value left
            for prop in self._connection._compounds:
                if prop.GetCalcStatus() & PASSED_V:
                    prop.SetValue(None, UNKNOWN_V)
            return
            
        
        #For compositions
        connCmps = self._connection._compounds
        myCmps = self._compounds
        self.UpdateArrPropConnection(myCmps, connCmps)

        #Now for arrProps
        for prop in self._arrProperties.keys():
            myCmps = self._arrProperties[prop]
            #Create property if necessary
            if not self._connection._arrProperties.has_key(prop):
                self._connection._arrProperties[prop] = []
                for i in range(len(myCmps)):
                    self._connection._arrProperties[prop].append(BasicProperty(prop, self._connection))
            connCmps = self._connection._arrProperties[prop]
            self.UpdateArrPropConnection(myCmps, connCmps)

        return 1

    def UpdateArrPropConnection(self, myCmps, connCmps):
        """Update all the properties of an array"""
        
        self._isForgetting = self._parentOp.IsForgetting()
        map(self._UpdateCmpPropConnection, myCmps, connCmps)
        del self._isForgetting
                    
        
    def _UpdateCmpPropConnection(self, myCmp, connCmp):
        """Updates the connection in a specific property of a compound. Useful for map calls"""
        isForgetting = self._isForgetting
        myStatus = myCmp.GetCalcStatus()
        connStatus = connCmp.GetCalcStatus()
        if connStatus & ESTIMATED_V:
            # the connection was an estimate
            # if I have known value and we aren't forgetting
            # add connection port to iteration stack
            myValue = myCmp.GetValue()
            if not isForgetting and myValue != None:
                self._parentOp.PushIterationProperty(connCmp, myValue)
                
        elif isForgetting:
            # if calculated value was not recalculated during forget solve
            # (i.e. not NEW_V) then forget the connected value
            if connStatus & PASSED_V:
                isNew = myStatus & NEW_V
                isCalc = myStatus & CALCULATED_V
                if((myStatus & UNKNOWN_V) or
                   (isNew and not isCalc) or
                   (isCalc and not isNew)):
                    connCmp.SetValue(None, UNKNOWN_V)
        else:
            # normal calculation update from connection as appropriate
            myValue = myCmp.GetValue()
            connValue = connCmp.GetValue()
            if myValue != None and not (myStatus & PASSED_V):
                connCmp.SetValue(myValue, PASSED_V)    
        
        
    
    def ResetNewFixed(self):
        """Reset NEW_V status on all port properties"""
        Port.ResetNewFixed(self)
        for i in self._compounds:
            i.ResetNewFixed()
        #arrProperties
        for prop in self._arrProperties.values():
            for cmp in prop:
                cmp.ResetNewFixed()
                
    def ResetNewCalc(self):
        """Reset NEW_V status on all port properties"""
        Port.ResetNewCalc(self)
        for i in self._compounds:
            i.ResetNewCalc()
        #arrProperties
        for prop in self._arrProperties.values():
            for cmp in prop:
                cmp.ResetNewCalc()
                
                
    def AllPropsAsEstimates(self):
        """Make sure that every spec is an estimate"""
        super(Port_Material, self).AllPropsAsEstimates()
        conn = self._connection
        
        #Needs to clear the connected port ?
        needClearConn = 1
            
        for prop in self._compounds:
            if (prop._calcStatus & FIXED_V) and not (prop._calcStatus & ESTIMATED_V):
                #Estimate all the fixed props
                prop._calcStatus |= ESTIMATED_V
                self._estimated = 1
                if needClearConn and conn:
                    # estimated ports don't pass information
                    # make sure there is no passed value left
                    for connProp in conn._compounds:
                        if connProp._calcStatus & PASSED_V:
                            connProp.SetValue(None, UNKNOWN_V)
                    needClearConn = 0
                    
        
    def AllPropsAsNonEstimates(self):
        """Make sure that every estimate is only a spec"""
        
        conn = self._connection
            
        for prop in self._compounds:
            if (prop._calcStatus & FIXED_V) and (prop._calcStatus & ESTIMATED_V):
                #Unestimate all the fixed props
                prop._calcStatus  &= ~ESTIMATED_V
                
        super(Port_Material, self).AllPropsAsNonEstimates()
                
    def GetCompounds(self):
        return self._compounds
    
    def GetCompoundNumber(self, cmpName):
        """
        return the position index for compound with name cmpName
        """
        try:
            cmpNames = self._parentOp.GetCompoundNames()
            return cmpNames.index(cmpName)
        except:
            try:
                cmpNameX = re.sub('_', ' ', cmpName)
                return cmpNames.index(cmpNameX)            
            except:
                return None
           
    def GetCompound(self, cmpName):
        """
        return compound with name cmpName - inefficient lookup!
        """
        return self._compounds[self.GetCompoundNumber(cmpName)]

    def GetCompoundNames(self):
        """
        return compound names
        """
        if self._parentOp:
            return self._parentOp.GetCompoundNames()
        
    def GetObject(self, description):
        """return object matching description"""
        if description == FRAC_VAR:
            return self.GetCompounds()
        elif description == MASSFRAC_VAR:
            massFracObj = MassCompoundList(self.GetCompounds())
            return massFracObj
        elif description == STDVOLFRAC_VAR:
            stdVolFracObj = StdVolCompoundList(self.GetCompounds())
            return stdVolFracObj
        elif self._arrProperties.has_key(description):
            ##This key could be MASSFRAC
            return self._arrProperties[description]
        elif description == 'FlashResults':
            return self._flashResults
        else:
            var = string.split(description, '_',1)
            if len(var) == 2:
                if  var[0] == CMPMOLEFRAC_VAR:
                    return self.GetCompound(var[1])
                
                #Can not return a single mass or vol frac as an object
                elif var[0] == CMPMASSFRAC_VAR:
                    return None
                elif var[0] == STDVOLFRAC_VAR:
                    return None

            else:
                return super(Port_Material, self).GetObject(description)
    
    def GetContents(self):
        """
        return all BasicVariables this contains as list of tuples of
        (description, obj)
        """
        result = super(Port_Material, self).GetContents()
        result.append((self._compounds.GetName(), self._compounds))
        #i = 0
        #names = self.GetCompoundNames()
        #for cmp in self._compounds:
        #    result.append((names[i],cmp))
        #    i += 1
        return result

    def GetArrPropNames(self):
        """Names of the array properties available"""
        return self._arrProperties.keys()

    def GetArrPropValue(self, propName):
        """List of values of propName"""
        try:
            vals = []
            for prop in self._arrProperties[propName]:
                vals.append(prop.GetValue())
            return vals
        except LookupError:
            return None

    def SetArrPropValue(self, propName, vals, calcStatus):
        """Sets a list of values for the desired array property"""
        if not self._arrProperties.has_key(propName):
            self._arrProperties[propName] = []
            for i in range(len(vals)):
                self._arrProperties[propName].append(BasicProperty(propName, self))
        for i in range(len(vals)):
            arrProp = self._arrProperties[propName]
            arrProp[i].SetValue(vals[i], calcStatus)
        pass
        
    def DelArrPropValue(self, propName):
        """To be implemented"""
        pass

    def AppendCompound(self, cmpIdx=-1):
        """Add a compound to the port"""
        self.AppendCompounds(1, cmpIdx)
        
        ### get the status of the current composition
        ##nc = len(self._compounds)
        ##zeroNewCmp = 0
        ##if nc > 0:
            ##st0 = self._compounds[0].GetCalcStatus()
            ##if st0 & ESTIMATED_V or st0 & FIXED_V:
                ##zeroNewCmp = 1           
                ##for cmp in self._compounds[1:]:
                    ##st = cmp.GetCalcStatus()
                    ##if st & NEW_V:
                        ###When adding more then 1 compounds, the earlier ones will be new & fixed
                        ##st = st - NEW_V                    
                    ##if st != st0:
                        ##zeroNewCmp = 0
                    ##elif cmp.GetValue() == None:
                        ##zeroNewCmp = 0
     
        ##self._compounds.append(BasicProperty(FRAC_VAR, self))

        ### If all composition is fixed or estimated, zero the new compound.
        ##if zeroNewCmp:
            ##self._compounds[nc].SetValue(0.0, st0)
        
        ###arrProperties
        ##for name, prop in self._arrProperties.items():
            ##prop.append(BasicProperty(name, self))
        ##self._flashResults = None
        
    def AppendCompounds(self, nuAddCmps, cmpIdx=-1):
        """ append nuCmps in one shot"""
        
        # get the status of the current composition
        nc = len(self._compounds)
        zeroNewCmp = 0
        if nc > 0:
            st0 = self._compounds[0].GetCalcStatus()
            if st0 & ESTIMATED_V or st0 & FIXED_V:
                zeroNewCmp = 1           
                for cmp in self._compounds[1:]:
                    st = cmp.GetCalcStatus()
                    if st & NEW_V:
                        #When adding more then 1 compounds, the earlier ones will be new & fixed
                        st = st - NEW_V                    
                    if st != st0:
                        zeroNewCmp = 0
                    elif cmp.GetValue() == None:
                        zeroNewCmp = 0
                        
        for i in range(nuAddCmps):
            self._compounds.append(BasicProperty(FRAC_VAR, self))

        # If all composition is fixed or estimated, zero the new compound.
        if zeroNewCmp:
            for i in range(nc, nc+nuAddCmps):
                self._compounds[i].SetValue(0.0, st0)
        
        #arrProperties
        for name, prop in self._arrProperties.items():
            for i in range(nuAddCmps):
                prop.append(BasicProperty(name, self))
                
        self._flashResults = None
    
        
    def MoveCompound(self, cmp1Idx, cmp2Idx):
        """Move a compound cmp1 before cmp2"""
        self._compounds.MoveCompound(cmp1Idx, cmp2Idx)
        # to prevent inconsistency in composition
        self._flashResults = None

    def DeleteCompound(self, cmpName):
        """Deletes a compound from the port"""
        cmpNo = self.GetCompoundNumber(cmpName)
        self.DeleteCompoundNumber(cmpNo)

    def DeleteCompoundNumber(self, cmpNo):
        """Delete a compound based on position in list"""
        del self._compounds[cmpNo]
        self._compounds.Normalize()
        #arrProperties
        for prop in self._arrProperties.values():
            del prop[cmpNo]
        self._flashResults = None
        
    def DeleteCompounds(self, nuDelCmps, startIdx):
        """Delete nuDelCmps starting at index startIdx"""
        del self._compounds[startIdx:startIdx+nuDelCmps]
        self._compounds.Normalize()
        #arrProperties
        for prop in self._arrProperties.values():
            del prop[startIdx:startIdx+nuDelCmps]
        self._flashResults = None
        
    def SetCompositionValues(self, vals, calcStatus):
        """Assumes vals is in the correct order

        vals -- List of numeric values of composition
        calcStatus -- Status of all the values (FIXED_V, UNKNOWN_V, etc)
        
        """
        for i in range(len(vals)):
            self._compounds[i].SetValue(vals[i], calcStatus)

    def GetCompositionValues(self):
        """Vals are in the order of the compounds"""
        return self._compounds.GetValues()

    def SetCompositionValue( self, cmpName, val, calcStatus):
        """assign value by name - ineffiecient lookup"""
        cmp = self.GetCompound(cmpName)
        if cmp:
            cmp.SetValue(val, calcStatus)

    def GetCompositionValue( self, cmpName):
        """
        return mole fraction for cmpName
        """
        cmp - self.GetCompound(cmpName)
        if cmp:
            return cmp.GetValue()
        
    def GetPropValue(self, propName):
        prop = self.GetObject(propName)
        if prop:
            return prop.GetValue()

        # failed - see if it might be mass fraction
        var = propName.split('_', 1)
        if len(var) == 2:
            cmpIdx = self.GetCompoundNumber(var[1])
            if cmpIdx == None: return None
            
            if var[0] == CMPMASSFRAC_VAR:
                massCmps = MassCompoundList(self._compounds)
                return massCmps.GetValues()[cmpIdx]
            elif var[0] == STDVOLFRAC_VAR:
                volCmps = StdVolCompoundList(self._compounds)
                return volCmps.GetValues()[cmpIdx]
            elif var[0] == MOLEFLOW_VAR:
                flow = self.GetPropValue(MOLEFLOW_VAR)
                if flow != None:
                    frac = self._compounds.GetValues()[cmpIdx]
                    if frac != None: return frac * flow
            elif var[0] == MASSFLOW_VAR:
                flow = self.GetPropValue(MASSFLOW_VAR)
                if flow != None:
                    massCmps = MassCompoundList(self._compounds)
                    frac = massCmps.GetValues()[cmpIdx]
                    if frac != None: return frac * flow
            elif var[0] == STDVOLFLOW_VAR:
                flow = self.GetPropValue(STDVOLFLOW_VAR)
                if flow != None:
                    volCmps = StdVolCompoundList(self._compounds)
                    frac = volCmps.GetValues()[cmpIdx]
                    if frac != None: return frac * flow
            else:
                #Just return the proportional value based on mole fraction
                value = self.GetPropValue(var[0])
                if value != None:
                    frac = self._compounds.GetValues()[cmpIdx]
                    if frac != None: return frac * value
                    
        return None
        
    def HasSameCompounds(self, port):
        """check that port has the same compound list as this port"""
        
        if self._parent and port._parent:
            return self._parent.GetThermo() == port._parent.GetThermo()
        else:
            return 0
    
    def ShareWith(self, port, propType=None, calcStatus=CALCULATED_V):
        """shares bidirectionally all values with port
        """
        Port.ShareWith(self, port, propType, calcStatus)
        if propType == None or propType & CANFLASH_PROP or propType & INTENSIVE_PROP:
            self.ShareComposition(port, calcStatus)
            if self._flashResults: port._flashResults = self._flashResults
            elif port._flashResults: self._flashResults = port._flashResults
        
    def ShareComposition(self, port, calcStatus=CALCULATED_V):
        """sets all composition values equal to ports and vice versa"""

        myCmps = self._compounds
        otherCmps = port._compounds
        isForgetting = self._parentOp.IsForgetting()
        for cmpNo in range(len(myCmps)):
            if isForgetting and myCmps[cmpNo].GetCalcStatus() & PASSED_V:
                continue
                
            x = myCmps[cmpNo].GetValue()
            if x != None:
                otherCmps[cmpNo].SetValue(x, calcStatus)
            else:
                x = otherCmps[cmpNo].GetValue()
                if x != None:
                    myCmps[cmpNo].SetValue(x, calcStatus)       

    def SetAsFlashProps(self, flashProps):
        flashProps = list(flashProps)
        for i in self._properties.keys():
            if i in flashProps:
                self._properties[i].SetCalcType(INTENSIVE_PROP|CANFLASH_PROP)
                flashProps.remove(i)
                
            #Only add but don't delete because the CalcType is global to the whole simulation
            #else:
            #    self._properties[i].SetCalcType(self._properties[i].GetCalcType() &~ CANFLASH_PROP)

        #Create is necessary
        for i in flashProps:
            self._properties[i] = BasicProperty(i, self)
            self._properties[i].SetCalcType(INTENSIVE_PROP|CANFLASH_PROP)
                    
    def ReadyToFlash(self):
        """check to see if flash is needed. If there is insufficient 
        information or if flash results are already available, return 0
        otherwise 1"""
        
        if self.GetNuKnownProps(CANFLASH_PROP) < 2:
            return 0  # not enough info
        
        cmps = self._compounds
        sumFracs = cmps.SumFractions()
        if not sumFracs: return 0

        parentOp = self._parentOp
        
        # check for unnormalized composition
        fracType = cmps[0].GetType()
        error = abs(1.0 - sumFracs)/fracType.scaleFactor
        if error > parentOp.GetTolerance():
            self.GetParentOp().InfoMessage('CompNotNormalized', (self.GetPath(), sumFracs))
        
        if not parentOp.GetThermo():
            return 0
        
        return 1

    def AlreadyFlashed(self):
        """
        return true if flashed results are already available
        """
        try:
            return self._properties[ZFACTOR_VAR].GetValue() != None
        except:
            return 0
        
                
    def Flash(self, calcStatus=CALCULATED_V, skipCalcFlows=0):
        """ if flash need, call the thermo to do so
        returns 1 if a flash was done, 0 if not"""
        if not skipCalcFlows: self.CalcFlows(calcStatus)  # just in case this can get H

        readyToFlash = self.ReadyToFlash()
        alreadyFlashed = self.AlreadyFlashed()
        if readyToFlash and self._flashResults:
            self.AssignFlashResults(self._flashResults)
            return not alreadyFlashed
        
        if alreadyFlashed or self._parentOp.IsForgetting():
            return 0

        uo = self._parentOp
        if readyToFlash:
            # use cached results on forget pass
            thCaseObj = uo.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            try:
                self._flashResults = thAdmin.Flash(prov, case, 
                                                   self._compounds, self._properties,
                                                   uo.NumberLiqPhases(),
                                                   nuSolids=uo.NumberSolidPhases(),
                                                   stdVolRefT=uo.GetParameterValue(STDVOLREFT_PAR))
            except Exception, e:
                #Let the error be raised but wrap it as a SimError that notifies of the port that failed
                raise SimError ('FlashFailure', (self.GetPath(), str(e)))
            
            if self._flashResults == None: return 0
            self.AssignFlashResults(self._flashResults, calcStatus)            
            self.CalcFlows(calcStatus)
            return 1
        else:
            #self.CalcFlows(calcStatus)
            return 0

    def AssignFlashResults(self, flashResults, calcStatus=CALCULATED_V):
        """assign the cached flash results to the appropriate variables"""
        #calcStatus = CALCULATED_V|PARENT_V
        if flashResults:
            self._flashResults = flashResults
            for i in range(len(flashResults.propNames)):
                self.SetPropValue(flashResults.propNames[i], flashResults.bulkProps[i], calcStatus)
            self.SetPropValue(VPFRAC_VAR, flashResults.phaseFractions[0], calcStatus)
            self.SetCompositionValues(flashResults.bulkComposition, calcStatus)
            for i in range(len(flashResults.arrPropNames)):
                self.SetArrPropValue(flashResults.arrPropNames[i], flashResults.bulkArrProps[i], calcStatus)
            self.CalcFlows(calcStatus)


    def GetLocalMoleWt(self, isForgetting=None):
        """
        Calculate Mole Wt, but not if compositions were passed and this is forget pass
        """
        #mwt = 0.0
        #x = []
        #sum = 0.0
        
        compounds = self._compounds
        nuCmps = len(compounds)
        if not nuCmps: return None
        
        parentOp = self._parentOp
        if isForgetting == None:
            isForgetting = parentOp.IsForgetting()
        x = zeros(nuCmps, Float)
        
        thCaseObj = parentOp.GetThermo()
        if thCaseObj == None: return None
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        cmpMwt = thAdmin.GetMolecularWeightValues(prov, case)
        if cmpMwt == None: return None
        
        for i in range(nuCmps):
            cmp = compounds[i]
            calcStatus = cmp.GetCalcStatus()
            if calcStatus & UNKNOWN_V: 
                return None
            if  isForgetting and calcStatus & PASSED_V: 
                return None
            frac = cmp.GetValue()
            if frac == None: 
                return None
            x[i] = frac
            #sum += frac
            
        total = Numeric.sum(x)
        if not total: return None
        x = x/total
        
        return Numeric.sum(x * cmpMwt)
    
    
        #for i in range(len(self._compounds)):
            ##Note: cmpMwt is an array with only one element because only one prop (Mwt) was requested
            #cmpMwt = thAdmin.GetSelectedCompoundProperties(prov, case, i, 'MolecularWeight')
            #mwt += x[i]*cmpMwt[0]/sum
        #return mwt
        
    def GetLocalStdMolVol(self, isForgetting=None):
        """
        Calculate StdMolVol, but not if compositions were passed and this is forget pass
        """
        
        compounds = self._compounds
        nuCmps = len(compounds)
        if not nuCmps: return None
        x = zeros(nuCmps, Float)
        
        parentOp = self._parentOp
        if isForgetting == None:
            isForgetting = parentOp.IsForgetting()
            
        thCaseObj = parentOp.GetThermo()
        if thCaseObj == None: return None
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        
        for i in range(nuCmps):
            cmp = compounds[i]
            calcStatus = cmp.GetCalcStatus()
            if calcStatus & UNKNOWN_V: 
                return None
            if  isForgetting and calcStatus & PASSED_V: 
                return None
            frac = cmp.GetValue()
            if frac == None: 
                return None
            x[i] = frac
        
        refT = parentOp.GetStdVolRefT()
        ##molVol = thAdmin.GetArrayProperty(prov, case, (P_VAR, 101.325), (T_VAR, refT), LIQUID_PHASE, x, STDLIQMOLVOLPERCMP_VAR)
        ##if molVol == None: return None
        ##molVol = sum(x*molVol)
        molVol = thAdmin.GetProperties(prov, case, (P_VAR, 101.325), (T_VAR, refT), LIQUID_PHASE, x, [STDLIQVOL_VAR])[0]
        
        return molVol
        
        
    def CalcFlows(self, calcStatus=CALCULATED_V):
        """perform mass/mole/energy flow cross calculations"""

        #Grab isForgetting flag right here. 
        #The only reason to do this is because the profiler indicated that this is one of the most
        #time consuming calls because of the amount of times it gets done
        isForgetting = self._parentOp.IsForgetting()
        
        #First, check for 0.0 flows
        moles = self.GetLocalValue(MOLEFLOW_VAR, isForgetting)
        massFlow = self.GetLocalValue(MASSFLOW_VAR, isForgetting)
        volFlow = self.GetLocalValue(VOLFLOW_VAR, isForgetting)
        stdVolFlow = self.GetLocalValue(STDVOLFLOW_VAR, isForgetting)
        stdGasVolFlow = self.GetLocalValue(STDGASVOLFLOW_VAR, isForgetting)
        q = self.GetLocalValue(ENERGY_VAR, isForgetting)
        if 0 in (moles, massFlow, volFlow, stdVolFlow, q, stdGasVolFlow):
            if moles == None: self.SetPropValue(MOLEFLOW_VAR, 0.0, calcStatus)
            if massFlow == None: self.SetPropValue(MASSFLOW_VAR, 0.0, calcStatus)
            if volFlow == None: self.SetPropValue(VOLFLOW_VAR, 0.0, calcStatus)
            if stdVolFlow == None: self.SetPropValue(STDVOLFLOW_VAR, 0.0, calcStatus)
            if q == None: self.SetPropValue(ENERGY_VAR, 0.0, calcStatus)
            if stdGasVolFlow == None: self.SetPropValue(STDGASVOLFLOW_VAR, 0.0, calcStatus)
            return #Done!
        
        if moles == None and stdGasVolFlow != None:
            moles = stdGasVolFlow
            self.SetPropValue(MOLEFLOW_VAR, moles, calcStatus)
        elif moles != None and stdGasVolFlow == None:
            stdGasVolFlow = moles
            self.SetPropValue(STDGASVOLFLOW_VAR, stdGasVolFlow, calcStatus)
        elif moles != None and stdGasVolFlow != None:
            self.SetPropValue(STDGASVOLFLOW_VAR, moles, calcStatus)

        mwt = self.GetLocalValue(MOLE_WT)
        molVol = self.GetLocalValue(MOLARV_VAR)
        stdMolVol = self.GetLocalValue(STDLIQVOL_VAR)
        
        if mwt == None and (moles != None or massFlow != None or stdVolFlow != None):
            mwt = self.GetLocalMoleWt(isForgetting)

        if mwt != None:
            if moles != None:
                massFlow = moles * mwt
                self.SetPropValue(MASSFLOW_VAR, massFlow, calcStatus)
            else:
                if massFlow != None:
                    moles = massFlow / mwt
                    self.SetPropValue(MOLEFLOW_VAR, moles, calcStatus)

        #Use this "if" for stdVol as well
        if molVol != None:
            # Calculate the volume flow and possibly the std vol flow
            moles = self.GetLocalValue(MOLEFLOW_VAR, isForgetting)
            massFlow = self.GetLocalValue(MASSFLOW_VAR, isForgetting)
            volFlow = self.GetLocalValue(VOLFLOW_VAR, isForgetting)
            if moles != None:
                # if mole flow is available, mass flow has already been calculated if possible
                #Set the values regardless if they are there already or not for consistency checks
                ##if volFlow == None:
                volFlow = moles * molVol
                self.SetPropValue(VOLFLOW_VAR, volFlow, calcStatus)
                ##if stdVolFlow == None and stdMolVol != None:
                if stdMolVol != None:
                    stdVolFlow = moles * stdMolVol
                    self.SetPropValue(STDVOLFLOW_VAR, stdVolFlow, calcStatus)
            elif volFlow != None:
                moles = volFlow / molVol
                self.SetPropValue(MOLEFLOW_VAR, moles, calcStatus)
                stdGasVolFlow = moles
                self.SetPropValue(STDGASVOLFLOW_VAR, stdGasVolFlow, calcStatus)
                if mwt != None and massFlow == None:
                    massFlow = moles * mwt
                    self.SetPropValue(MASSFLOW_VAR, massFlow, calcStatus)
                if stdVolFlow == None and stdMolVol != None:
                    stdVolFlow = moles * stdMolVol
                    self.SetPropValue(STDVOLFLOW_VAR, stdVolFlow, calcStatus)
            elif stdVolFlow != None and stdMolVol != None:
                moles = stdVolFlow / stdMolVol
                self.SetPropValue(MOLEFLOW_VAR, moles, calcStatus)
                stdGasVolFlow = moles
                self.SetPropValue(STDGASVOLFLOW_VAR, stdGasVolFlow, calcStatus)
                if mwt != None and massFlow == None:
                    massFlow = moles * mwt
                    self.SetPropValue(MASSFLOW_VAR, massFlow, calcStatus)
                if volFlow == None:
                    volFlow = moles * molVol
                    self.SetPropValue(VOLFLOW_VAR, volFlow, calcStatus)                
                    
        elif moles == None and stdVolFlow != None and mwt != None:
            stdMolVol = self.GetLocalStdMolVol(isForgetting)
            if stdMolVol != None:
                moles = stdVolFlow / stdMolVol
                self.SetPropValue(MOLEFLOW_VAR, moles, calcStatus)
                
                stdGasVolFlow = moles
                self.SetPropValue(STDGASVOLFLOW_VAR, stdGasVolFlow, calcStatus)
                
                if massFlow == None:
                    massFlow = moles * mwt
                    self.SetPropValue(MASSFLOW_VAR, massFlow, calcStatus)
        elif moles != None and stdVolFlow == None and mwt != None:
            stdMolVol = self.GetLocalStdMolVol(isForgetting)
            if stdMolVol != None:
                stdVolFlow = moles * stdMolVol
                self.SetPropValue(STDVOLFLOW_VAR, stdVolFlow, calcStatus)
            

        h = self.GetLocalValue(H_VAR, isForgetting)
        # note conversion to W from KJ/hr and vice versa
        if h != None:
            moles = self.GetLocalValue(MOLEFLOW_VAR, isForgetting)
            if moles != None:
                q = moles * h / 3.6
                self.SetPropValue(ENERGY_VAR, q, calcStatus)
            else:
                q = self.GetLocalValue(ENERGY_VAR, isForgetting)
                if q != None and h != 0.0:
                    moles = 3.6*q/h
                    self.SetPropValue(MOLEFLOW_VAR, moles, calcStatus)
                    # since this can only be reached when moles is none
                    # it is safe to call recursively to fill in mass
                    # as long as moles is actually known
                    if self.GetLocalValue(MOLEFLOW_VAR, isForgetting) != None:
                    #if moles != None
                        self.CalcFlows()
        else:
            #moles = self.GetLocalValue(MOLEFLOW_VAR)
            q = self.GetLocalValue(ENERGY_VAR, isForgetting)
            if moles != None and q != None and moles != 0:
                self.SetPropValue(H_VAR, 3.6*q/moles, calcStatus)
                # should be safe to recurse if h now known
                if self.GetLocalValue(H_VAR, isForgetting) != None:
                    self.CalcFlows()
            elif moles == 0:
                q = 0.0
                self.SetPropValue(ENERGY_VAR, q, calcStatus)


    def DeleteObject(self, obj):
        """
        if obj is a CompoundList, set its values to None
        otherwise call super method
        """
        if isinstance(obj, CompoundList):
            for i in range(len(obj)):
                obj[i].SetValue(None, FIXED_V)
        else:
            Port.DeleteObject(self, obj)        

    def CompListChanged(self, compList):
        # disconnect from the assay upon composition changes
        if self._attachedObj:
            self.RemoveFromBorrowedIn(self._attachedObj)
            self._attachedObj.DeleteObject(self)
            self._attachedObj = None

    def AttachToObject(self, obj):
        if hasattr(obj, 'AttachToPort'):
            if self._attachedObj:
                # disconnect existing connection
                if obj == self._attachedObj: return
                self.RemoveFromBorrowedIn(self._attachedObj)
                self._attachedObj.DeleteObject(self)
            # connect to object
            obj.AttachToPort(self)
            self._attachedObj = obj
            self.AddToBorrowedIn(self._attachedObj)
            
            
            
class Port_Energy(Port):
    """Energy port"""    
    def __init__(self, portType, parentOp, name, varTypeName=ENERGY_VAR):
        """Inits an energy port with one member variables
        parent_op - the UnitOperation the port is part of
        
        Member variables:
        properties = Instance of EnergyPropertyDict()

        """         
        Port.__init__(self, portType, parentOp, name)
        self._properties =  EnergyPropertyDict(port=self, varTypeName=varTypeName)
        self._varType = varTypeName
        self._prop = self._properties[varTypeName]

    def CloneContents(self, clone):
        super(Port_Energy, self).CloneContents(clone)
        clone._varType = str(self._varType)
        try:
            clone._prop = clone._properties.values()[0]
        except:
            pass
        
        
    def CleanUp(self):
        self._prop = None
        self._varType = None
        super(Port_Energy, self).CleanUp()        
        
    def GetObject(self, description):
        """Get object. Hack to make ENERGY_VAR equivalent to WORK_VAR)"""
        obj = super(Port_Energy, self).GetObject(description)
        if obj != None: return obj
        
        if description == WORK_VAR:
            return self.GetObject(ENERGY_VAR)
        
        
    def GetValue(self):
        """get the value from the signal property"""
        return self._prop.GetValue()

    def SetValue(self, value, calcStatus):
        self._prop.SetValue(value, calcStatus)

    def SetPropValue(self, name, value, calcStatus):
        """
        for conformity with super class - do nothing if wrong type
        so added variables aren't created
        """
        name = name.split('_', 1)[0]  #In case if wrongly passed a name of a compound appended to name
        if name == self._varType:
            self.SetValue(value, calcStatus)
            
    def GetType(self):
        """returns property type"""
        return self._prop.GetType()

    def GetSignalType(self):
        """
        bit of a ruse so energy streams can 'ShareWith' signal streams
        """
        return self._varType
    
    def ShareWith(self, port, propType=None, calcStatus=CALCULATED_V):
        """
        if port is signal, then let it's ShareWith try, otherwise just
        call super method
        """
        if isinstance(port, Port_Signal):
            #Let the signal take care of it for type matching
            port.ShareWith(self, propType, calcStatus)
            
        elif isinstance(port, Port_Material):
            #Get and set stuff in the material port as an ENERGY_VAR
            prop = self._prop
            val = self.GetLocalValue()
            if prop and (propType == None or prop.GetType().calcType & propType):
                port.SetPropValue(ENERGY_VAR, val, calcStatus)
            
            prop = port.GetLocalValue(ENERGY_VAR)
            if prop and (propType == None or prop.GetType().calcType & propType):
                self.SetValue(val, calcStatus)
                
        else:
            #Blindly trust that the other energy port is of an equivalent type
            #Put my value into the other port
            prop = self._prop
            val = self.GetLocalValue()
            if prop and (propType == None or prop.GetType().calcType & propType):
                port.SetValue(val, calcStatus)
            
                
            #Put the value from the other port into myself
            prop = port._prop
            val = port.GetLocalValue()
            if prop and (propType == None or prop.GetType().calcType & propType):
                self.SetValue(val, calcStatus)

    def GetLocalValue(self, propName=None):
        """return value for property with propName, but return None
        if that value was passed from outside and this is forget pass"""
        if propName:
            return super(Port_Energy, self).GetLocalValue(propName)
        
        
        try:
            if not self._prop: 
                return None
            calcStatus = self._prop.GetCalcStatus()
            if calcStatus & UNKNOWN_V:
                return None
            if  self._parentOp.IsForgetting() and calcStatus & PASSED_V:
                return None
            return self._prop.GetValue()
        except LookupError:
            return None
        
        #try:
            #calcStatus = self._properties[ENERGY_VAR].GetCalcStatus()
            #if calcStatus & UNKNOWN_V:
                #return None
            #if  self._parentOp.IsForgetting() and calcStatus & PASSED_V:
                #return None
            #return self._properties[ENERGY_VAR].GetValue()
        #except LookupError:
            #return None
            
    def GetProperty(self, propName=None):
        if propName == None:
            return self._prop
        else:
            return super(Port_Energy, self).GetProperty(propName)
        
    def UpdateConnection(self):
        """Update the only property available"""
        conn = self._connection
        myProp = self._prop
        
        if not conn:
            if myProp != None:
                if myProp.GetCalcStatus() & PASSED_V:
                    myProp.SetValue(None, UNKNOWN_V)
            return 1

        connProp = conn._prop
        
        if self._estimated:
            # estimated ports don't pass information
            # make sure there is no passed value left
            if connProp != None:
                if connProp.GetCalcStatus() & PASSED_V:
                    connProp.SetValue(None, UNKNOWN_V)
            return   
        
        isForgetting = self._parentOp.IsForgetting()
        
        
        if myProp == None and connProp == None:
            return
        
        #this should never happen but lets code for it anyway
        if myProp == None and connProp != None:
            self.SetSignalType(conn.GetSignalType())
            myProp = self._prop
        elif connProp == None and myProp != None:
            conn.SetSignalType(self.GetSignalType())
            connProp = conn._prop
        
        
        myStatus = myProp.GetCalcStatus()
        connStatus = connProp.GetCalcStatus()
        
        if connStatus & ESTIMATED_V:
            # the connection was an estimate
            # if I have known value and we aren't forgetting
            # add connection port to iteration stack
            myValue = myProp.GetValue()
            if not isForgetting and myValue != None:
                conn._parentOp.PushIterationProperty(connProp, myValue)
                
        elif isForgetting:
            # if calculated value was not recalculated during forget solve
            # (i.e. not NEW_V) then forget the connected value                
            if connStatus & PASSED_V:
                isNew = myStatus & NEW_V
                isCalc = myStatus & CALCULATED_V
                if((myStatus & UNKNOWN_V) or
                   (isNew and not isCalc) or
                   (isCalc and not isNew) or
                   myProp.GetValue() != connProp.GetValue()):
                    connProp.SetValue(None, UNKNOWN_V)
        else:
            # normal calculation update from connection as appropriate
            myValue = myProp.GetValue()
            connValue = connProp.GetValue()
            if myValue != None and not (myStatus & PASSED_V):
                connProp.SetValue(myValue, PASSED_V)
                    
        return 1        
    
    
class Port_Signal(Port):
    """Signal port. Inherits from Port."""
    def __init__(self, portType, parentOp, name=''):
        """parent_op - the UnitOperation the port is part of"""
        Port.__init__(self, portType, parentOp, name)
        self._prop = None  # short cut to the signal property - set when type set
        self._varType = None # keep track of explicitly set type
        self._cmpName = None
        
    def CloneContents(self, clone):
        super(Port_Signal, self).CloneContents(clone)
        clone._varType = self._varType
        clone._cmpName = self._cmpName
        try:
            clone._prop = clone._properties.values()[0]
        except:
            pass
        
        
    def CleanUp(self):
        self._prop = None
        self._varType = None
        super(Port_Signal, self).CleanUp()
        
        
    def ConnectTo(self, otherPort, internalCall=False):
        """create a connection between this port and otherPort"""
        if not isinstance(otherPort, Port_Signal):
            raise SimError("ConnectSigToNonSig", self._name)
        
        if self._connection is otherPort:
            return 1
        
        if self._connection != None:
            #Disconnect first if already connected
            self.Disconnect(True)
            
            
        # for signal ports, notify parent first, may need to fix up signal type
        self.GetParent().MakingPortConnection(self, otherPort)
        otherPort.GetParent().MakingPortConnection(otherPort, self)
        
        
        #Get the type objects
        myType, otherType = self.GetType(), otherPort.GetType()
        
        
        # this calls bring the type as a name with the name of the compund
        # appended to the end
        mySignalType, otherSignalType = self.GetSignalType(), otherPort.GetSignalType()
        
        
        #Compare generic types. Do not check on compounds
        equivalent = True
        try:
            if myType.unitType != otherType.unitType:
                equivalent = S42Glob.unitSystem.IsEquivalentType(myType.unitType, otherType.unitType)
        except:
            #if it failed comparing, then assume they are equivalent
            pass
        
        if myType != None and otherType != None and not equivalent:
            raise SimError('SigConnectTypeMismatch',
                           (mySignalType, otherSignalType, 
                            self.GetPath(), otherPort.GetPath()))
        
        #Make sure to put the known type into the missing type (if necessary)
        #Don't call it if already equivalent
        if mySignalType != SIGNAL_TYPE_NONE and (not equivalent or otherSignalType == SIGNAL_TYPE_NONE):
            otherPort.CreateProperty(mySignalType)
            
        elif otherSignalType != SIGNAL_TYPE_NONE and (not equivalent or mySignalType == SIGNAL_TYPE_NONE):
            self.CreateProperty(otherSignalType)
            
            
        return super(Port_Signal,self).ConnectTo(otherPort)
        

    def Disconnect(self, internalCall=False):
        """break connection to other port"""
        if not self._connection: return        
        if self._varType == None:
            self.DeleteProperty()
        super(Port_Signal, self).Disconnect()    

    def CreateProperty(self, varType):
        """remove previous property and create one of type varType"""
        # check for a type that includes a compound
        # This implieas that any variable can be specified as "per compound" and also 
        # that no property can have a '_' in its name
        
        #Get the type name and compound name
        varTypeLst = varType.split('_',1)
        varTypeName = varTypeLst[0]
        cmpName = None
        if len(varTypeLst) > 1:
            cmpName = varTypeLst[1]
            
            
        #Is the propertyalready there?? Don't check on the compound
        if not (self._properties.has_key(varTypeName)):
            # remove previous property, if any
            self.DeleteProperty()
            self._properties[varTypeName] = BasicProperty(varTypeName, self)
        
        #Create the property and update the member variables
        self._prop = self._properties[varTypeName]# = BasicProperty(varTypeName, self)
        self._varType = varTypeName
        self._cmpName = cmpName
        
        
        
    def DeleteProperty(self):
        """remove any current property"""
        if self._prop:
            self._prop.CleanUp()
        self._properties.clear()
        self._prop = None
        self._varType = None
        self._cmpName = None

    def GetValue(self):
        """get the value from the signal property"""
        if self._prop:
            return self._prop.GetValue()
        else:
            return None

    def GetPropValue(self, name):
        """
        for conformity with super class - return none if wrong type
        """
        name = name.split('_', 1)[0]  #In case if wrongly passed a name of a compound appended to name
        
        if name == self._varType:
            return self.GetValue()
        else:
            return None
        
    def SetValue(self, value, calcStatus):
        assert(self._prop)
        self._prop.SetValue(value, calcStatus)
        
        
    def SetPropValue(self, name, value, calcStatus):
        """
        for conformity with super class - do nothing if wrong type
        """
        name = name.split('_', 1)[0]  #In case if wrongly passed a name of a compound appended to name
        if name == self._varType:
            self.SetValue(value, calcStatus)
    
    def ShareWith(self, port, propType=None, calcStatus=CALCULATED_V):
        """shares bidirectionally all values with port
        (of PropertyType.calcType = propType if propType not None)
        """
        
        #Get the type objects
        myType, otherType = self.GetType(), port.GetType()
        if myType == None and otherType == None:
            return
        
        
        #Compare generic types. Do not check on compounds
        equivalent = True
        try:
            if myType.unitType != otherType.unitType:
                equivalent = S42Glob.unitSystem.IsEquivalentType(myType.unitType, otherType.unitType)
        except:
            #if it failed comparing, then assume they are equivalent
            pass
        
        if not equivalent:
            raise SimError('SigShareMismatch',
                           (self.GetSignalType(), port.GetSignalType(), self.GetPath(), port.GetPath()))
        
        
        #Put my value into the other port
        prop = self._prop
        val = self.GetLocalValue()
        if prop and (propType == None or myType.calcType & propType):
            port.SetValue(val, calcStatus)
        
            
        #Put the value from the other port into myself
        prop = port._prop
        val = port.GetLocalValue()
        if prop and (propType == None or otherType.calcType & propType):
            self.SetValue(val, calcStatus)
        
            
    def GetType(self):
        """returns property type object"""
        if self._prop:
            type = self._prop.GetType()
            self._varType = type.name  #redudnant check to keep it synchronized
            return type
        
        elif self._properties:
            #Somehow we don't have a self._prop but we do have properties ??
            items = self._properties.items()
            self._prop = items[0][1]
            type = self._prop.GetType()
            self._varType = type.name
            return type
        
        return None
    
    
    def GetSignalType(self):
        """The type of the signal as a stream with the name of the compound if necessary appended at the end
        preceded of a '_'"""
        try:
            varType = self.GetType().name
            if self._cmpName:
                varType += '_' + self._cmpName
            return varType
        except:
            return SIGNAL_TYPE_NONE
        
    def GetCompoundName(self):
        """In case the signal is associated to a specific property"""
        try:
            return self._cmpName
        except:
            self._cmpName = None
            return None
    
    def SetSignalType(self, varType):
        """use varType string to determine what kind of signal to handle"""

        conn = self._connection
        
        #If the connection has a type, then delete the type in both
        if varType == None or varType == SIGNAL_TYPE_NONE:
            if self._varType != None and conn:
                conn.DeleteProperty()
            self.DeleteProperty()
            self._varType = None
            return
        varTypeName = varType
        if varType:
            varTypeName = varType.split('_', 1)[0]
        #Check the connection to see if the type can be set
        if conn and conn._varType and  conn._varType != varTypeName:
            raise SimError('SigConnectTypeMismatch', 
                           (varTypeName, conn._varType, self.GetPath(), conn.GetPath()) )
        
        
        # This call takes care of updating of clearingthe already existing property and
        # updating themember variables.
        # Nothign will happen if the type is already there
        self.CreateProperty(varType)
        
        
        if conn:
            conn.CreateProperty(varType)
            
    def GetLocalValue(self, propName=None):
        """return value for property with propName, but return None
        if that value was passed from outside and this is forget pass"""
        if propName:
            return super(Port_Signal, self).GetLocalValue(propName)
        
        try:
            if not self._prop: 
                return None
            calcStatus = self._prop.GetCalcStatus()
            if calcStatus & UNKNOWN_V:
                return None
            if  self._parentOp.IsForgetting() and calcStatus & PASSED_V:
                return None
            return self._prop.GetValue()
        except LookupError:
            return None        
        
    def GetProperty(self, propName=None):
        if propName == None:
            return self._prop
        else:
            return super(Port_Signal, self).GetProperty(propName)
        
        
    def UpdateConnection(self):
        """Update the only property available"""
        conn = self._connection
        myProp = self._prop
        
        if not conn:
            if myProp != None:
                if myProp.GetCalcStatus() & PASSED_V:
                    myProp.SetValue(None, UNKNOWN_V)
            return 1

        connProp = conn._prop
        
        if self._estimated:
            # estimated ports don't pass information
            # make sure there is no passed value left
            if connProp != None:
                if connProp.GetCalcStatus() & PASSED_V:
                    connProp.SetValue(None, UNKNOWN_V)
            return   
        
        isForgetting = self._parentOp.IsForgetting()
        
        
        if myProp == None and connProp == None:
            return
        
        #this should never happen but lets code for it anyway
        if myProp == None and connProp != None:
            self.SetSignalType(conn.GetSignalType())
            myProp = self._prop
        elif connProp == None and myProp != None:
            conn.SetSignalType(self.GetSignalType())
            connProp = conn._prop
        
        
        myStatus = myProp.GetCalcStatus()
        connStatus = connProp.GetCalcStatus()
        
        if connStatus & ESTIMATED_V:
            # the connection was an estimate
            # if I have known value and we aren't forgetting
            # add connection port to iteration stack
            myValue = myProp.GetValue()
            if not isForgetting and myValue != None:
                conn._parentOp.PushIterationProperty(connProp, myValue)
                
        elif isForgetting:
            # if calculated value was not recalculated during forget solve
            # (i.e. not NEW_V) then forget the connected value                
            if connStatus & PASSED_V:
                isNew = myStatus & NEW_V
                isCalc = myStatus & CALCULATED_V
                if((myStatus & UNKNOWN_V) or
                   (isNew and not isCalc) or
                   (isCalc and not isNew) or
                   myProp.GetValue() != connProp.GetValue()):
                    connProp.SetValue(None, UNKNOWN_V)
        else:
            # normal calculation update from connection as appropriate
            myValue = myProp.GetValue()
            connValue = connProp.GetValue()
            if myValue != None and not (myStatus & PASSED_V):
                connProp.SetValue(myValue, PASSED_V)
                    
        return 1        
        
#import psyco
#psyco.bind(Port_Material.UpdateConnection)
#psyco.bind(Port_Material.CalcFlows)
#psyco.bind(Port_Material.CalcFlows)

class PortStateObj(object):
    """wrapper object for the state flag in the ports"""
    def __init__(self, port):
        self.name = PORT_STATE
        self.port = port
        
    def __str__(self):
        if self.GetValue() == FIXALL_STATE:
            desc = 'All values fixed'
        else:
            desc = 'All values estimated'
        return self.GetPath() + ' = ' + str(self.GetValue()) + ' (' + desc + ')'
    
    def GetName(self):
        return self.name
    
    def GetParent(self):
        return self.port
    
    def GetPath(self):
        return '%s.%s' %(self.port.GetPath(), self.name)
    
    def GetValue(self):
        try:
            return self.port.state
        except:
            self.port.state = FIXALL_STATE
            return FIXALL_STATE
    
    def SetValue(self, value, dummy=None):
        """Dummy is jsut to make it match the generic call with a status"""
        if value == FIXALL_STATE: 
            self.port.SetState(value)
        elif value == ESTIMATEALL_STATE: 
            self.port.SetState(value)
        else:
            value = NONE_STATE
            self.port.SetState(value)
        if value == ESTIMATEALL_STATE:
            self.port.AllPropsAsEstimates()
        elif value == FIXALL_STATE:
            self.port.AllPropsAsNonEstimates()
        else:
            pass
        
        