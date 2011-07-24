"""Set module - provides a simple aX + b relationship between two
signal ports

Classes:
Set -- Inherits from UnitOperation

"""

import UnitOperations
from sim.solver import Error
from sim.solver.Variables import *
from sim.solver import S42Glob
from sim.solver.Ports import *
from sim.solver.Messages import MessageHandler
from sim.solver.Error import SimError

MULT_PORT = 'multiplier'
ADD_PORT = 'addition'
class Set(UnitOperations.UnitOperation):
    """Class for a set unit op. Inherits from UnitOperation
    provides a simple aX + b relationship between two
    signal ports
    
    Has the following signal values:
        MULT_PORT - the 'a' parameter
        ADD_PORT  - the 'b' parameter
        
        The outlet signal port 1 value will be calculated by multiplying 
        the port 0 value by the multiplier and adding the
        addition to it
        
        v1 = a * v0 + b
        
        The SIGTYPE_PAR is required to set port types and
        for units on the addition parameter.
    """
    def __init__(self, initScript = None):
        """Init the set

        Init Info:
        varType = GENERIC_VAR
        'multiplier' and 'addition' are initially set to 1 and 0 initially
        """          
        super(Set, self).__init__(initScript)

        self.inPort = self.CreatePort(SIG, SIG_PORT + str(0))
        self.outPort = self.CreatePort(SIG, SIG_PORT + str(1))
        self.multPort = self.CreatePort(SIG, MULT_PORT)
        self.addPort = self.CreatePort(SIG, ADD_PORT)
        
        self.multPort.SetSignalType(GENERIC_VAR)
        self.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        
    def GetListOfReqParam(self): return (SIGTYPE_PAR, )
                           
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        super(Set, self).SetParameterValue(paramName, value)
        if paramName == SIGTYPE_PAR:
            #Value may come as a propertyt type name with a compound appended at the end preceded by _
            #in this case, lets, only set the typename, not the compound name
            value = value.split('_')[0] 
            self.inPort.SetSignalType(value)
            self.outPort.SetSignalType(value)
            if value == T_VAR:
                self.addPort.SetSignalType(DELTAT_VAR)
            elif value == P_VAR:
                self.addPort.SetSignalType(DELTAP_VAR)
            else:
                self.addPort.SetSignalType(value)
                
    def ValidateParameter(self, paramName, value):
        if not super(Set, self).ValidateParameter(paramName, value):
            return 0
        if paramName == SIGTYPE_PAR:
            currName = self.parameters.get(SIGTYPE_PAR, None)
            if not currName: return 1
            currName = currName.split('_', 1)[0]
            validateName = value.split('_', 1)[0]
            equivalent = 1
            try:
                equivalent = S42Glob.unitSystem.IsEquivalentType(PropTypes[currName].unitType, PropTypes[validateName].unitType)
            except:
                #if it failed comparing, then assume they are equivalent
                pass
            if equivalent: return 1
            
            #The types are not equivalent. If any port is already connected, then 
            #there will be a type conflict, hence, return false
            for port in (self.inPort, self.outPort, self.addPort):
                conn = port.GetConnection()
                if conn != None:
                    return 0
                    
        return 1
    
    def DeleteObject(self, obj):
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() in (SIGTYPE_PAR):
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return
            
        super(Set, self).DeleteObject(obj)
        
        
    def Solve(self):
        """Solve"""
        p0 = self.inPort
        p1 = self.outPort
        aPort  = self.multPort
        bPort  = self.addPort
        
        
        ##Don't do redundant validation of type
        ##varType = self.GetParameterValue(SIGTYPE_PAR)
        
        ##if p0.GetSignalType() != varType:
            ##raise Error.SimError('SetVarTypeMismatch', 
                  ##(p0.GetSignalType(), varType, self.GetPath()))

        ##if p1.GetSignalType() != varType:
            ##raise Error.SimError('SetVarTypeMismatch', 
                  ##(p1.GetSignalType(), varType, self.GetPath()))
        
        v0 = p0.GetValue()
        v1 = p1.GetValue()

        a = aPort.GetValue()
        b = bPort.GetValue()
        
        if a == None:
            if v0 and v1 != None and b != None:
                aPort.SetValue((v1 - b) / v0, CALCULATED_V)
        elif b == None:
            if v0 != None and v1 != None:
                bPort.SetValue(v1 - v0 * a, CALCULATED_V)
        elif v0 != None:
            p1.SetValue(v0*a + b, CALCULATED_V)
        elif v1 != None and a != 0.0:
            p0.SetValue((v1 - b)/a, CALCULATED_V)

    def MakingPortConnection(self, myPort, otherPort):
        if otherPort == None:
            #This code can not be used as is because setting the parameter value while disconnecting
            #will raise an exception.
            #The ideal would be, being able to run this code after disconnecting
            
            # disconnecting, reset the signal type to generic if no more connections
            ###setSig = 1
            ###inPort, outPort, addPort = self.inPort, self.outPort, self.addPort
            ###ports = (inPort, outPort, addPort)
            ###for port in ports:
                ###if port != myPort and port.IsPortConnected():
                    ###setSig = 0
                    ###break
            ###if setSig:
                ###try:
                    ####Keep all the values
                    ###valIn, statIn   = inPort.GetLocalValue(), inPort._prop.GetCalcStatus()
                    ###valOut, statOut = outPort.GetLocalValue(), outPort._prop.GetCalcStatus()
                    ###valAdd, statAdd = addPort.GetLocalValue(), addPort._prop.GetCalcStatus()
                    
                    ###self.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
                    
                    ###if valIn != None and statIn & FIXED_V:
                        ###inPort.SetValue(valIn, statIn)
                        
                    ###if valOut != None and statOut & FIXED_V:
                        ###outPort.SetValue(valOut, statOut)

                    ###if valAdd != None and statAdd & FIXED_V:
                        ###addPort.SetValue(valAdd, statAdd)    

                ###except:
                    ###self.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
            pass
        else:
            # when connecting my signals to ports with diffent types
            # if both Sig0 and Sig1 have not been connected
            # set my signal type according to connecting port
            setSig = 0
            otherType = otherPort.GetSignalType()
            myType = myPort.GetSignalType()
            
            #Only keep the part of the type with out the compound
            #A set unit op does not care about which compound is being dealt with
            myType = myType.split('_', 1)[0]
            otherType = otherType.split('_', 1)[0]
            
            if myType != SIGNAL_TYPE_NONE and otherType != SIGNAL_TYPE_NONE and myType != otherType:
                if myPort is self.inPort:                
                    if not self.outPort.IsPortConnected():
                        setSig = 1
                elif myPort is self.outPort:                
                    if not self.inPort.IsPortConnected():
                        setSig = 1
                        
                if setSig:
                    # preserve the Add port value if it is not connected            
                    addPortValue = self.addPort.GetValue()
                    calcStatus = self.addPort._prop.GetCalcStatus()
                    self.SetParameterValue(SIGTYPE_PAR, otherType)
                    if not self.addPort.IsPortConnected() and addPortValue != None:
                        self.addPort.SetValue(addPortValue, calcStatus)
                        
                

    def AdjustOldCase(self, version):
        super(Set, self).AdjustOldCase(version)
        
        if version[0] < 61:
            typeName = self.GetParameterValue(SIGTYPE_PAR)
            if typeName:
                typeLst = typeName.split('_', 1)
                if len(typeLst) > 1:
                    #Only keep the first part of the type. The second part is the name of the compund
                    #if any
                    self._parameters[SIGTYPE_PAR] = typeLst[0]
                     
                     
                     
