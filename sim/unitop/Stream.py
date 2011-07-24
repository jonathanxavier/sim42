"""Models streams

Classes:
Stream_Material -- Class for material stream. Inherits from UnitOperation
Stream_Energy -- Class for energy stream. Inherits from UnitOperation

"""
from sim.solver.Error import SimError
from sim.solver.Variables import *
from sim.solver import S42Glob
from sim.solver.Ports import SIGNAL_TYPE_NONE
from sim.solver.Messages import MessageHandler
import UnitOperations

VALID_UNIT_OPERATIONS = ['Stream_Material',
                         'Stream_Energy',
                         'Stream_Signal',
                         'ClonePort',
                         'SensorPort']

class Stream_Material(UnitOperations.UnitOperation):
    """Class for material stream. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """Init the stream"""
        super(Stream_Material, self).__init__(initScript)
        
        p = self.CreatePort(MAT|IN, IN_PORT)
        p.SetLocked(True)
        p = self.CreatePort(MAT|OUT, OUT_PORT)
        p.SetLocked(True)
       
    def AddObject(self, obj, name):
        """
        if object is clone port, create the appropriate kind of port
        other wise call parent method
        """
        
        if isinstance(obj, ClonePort):
            oldPort = self.GetPort(name)
            if oldPort:
                self.DeletePort(oldPort)  # can't have duplicates
            if obj.incoming:
                self.CreatePort(MAT|IN, name)
            else:
                self.CreatePort(MAT|OUT, name)
            self.PushSolveOp(self)
        elif isinstance(obj, SensorPort):
            oldPort = self.GetPort(name)
            if oldPort:
                self.DeletePort(oldPort)  # can't have duplicates
            port = self.CreatePort(SIG, name)
            port.SetSignalType(obj.varType)
            self.PushSolveOp(self)
        else:
            super(Stream_Material, self).AddObject(obj, name)
                
    def SensorShare(self, withPort):
        """
        Share any information from signal ports with material port withPort
        """
        sigPorts = self.GetPorts(SIG)
        for port in sigPorts:
            #Gets the type as a string with a name of the compound appended if necessary
            portTypeName = port.GetSignalType()
            
            #Get the compound name separately
            cmpName = port.GetCompoundName()
            
            
            if portTypeName != SIGNAL_TYPE_NONE and portTypeName != None:
                
                portValue = port.GetValue()
                
                if portValue != None:
                    #Put the value into the material port
                    if not cmpName:
                        withPort.SetPropValue(portTypeName, portValue, CALCULATED_V)
                    elif portTypeName[:len(CMPMOLEFRAC_VAR)] == CMPMOLEFRAC_VAR:
                        withPort.SetPropValue(portTypeName, portValue, CALCULATED_V)
                        
                    else:
                        #Any other variable per compound should be checked only for consistency
                        #as those values can not be input
                        withValue = withPort.GetPropValue(portTypeName)
                        if withValue != None:
                            port.SetValue(withValue, CALCULATED_V)
                                
                else:
                    #Put the value into the signal port
                    withValue = withPort.GetPropValue(portTypeName)
                    if withValue != None:
                        port.SetValue(withValue, CALCULATED_V)
                        
                        

    def Solve(self):
        """Solve"""
        #if self.IsForgetting(): return
        
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)
        clonePorts = self.GetPorts(MAT|IN|OUT)
        
        idx = clonePorts.index(inPort)
        clonePorts.pop(idx)
        idx = clonePorts.index(outPort)
        clonePorts.pop(idx)
        hasClones = (len(clonePorts) > 0)
        
        #Start by flashing the inPort
        inPort.Flash()
        
        while 1:
            #Everything known in "signals" goes into the "out" port
            self.SensorShare(outPort)

            #Everything in "signals" and "out" goes into "in"
            #Everything in "in" goes into "out"
            inPort.ShareWith(outPort)
            
            if hasClones:
                # share with clones
                #Everything in "signals", "out" and "in" go into "clones"
                for port in clonePorts:
                    inPort.ShareWith(port)
                    
                # share between in and out again
                #Everything in "clones" that went into "in" now go into "out"
                inPort.ShareWith(outPort)
                
                for port in clonePorts:
                    port.CalcFlows()
                    
            inPort.CalcFlows()
            outPort.CalcFlows()
            
            #Everything new in "out" finally goes into the "signals"
            self.SensorShare(outPort)

            # only have to check one flash since everything was shared
            if not inPort.Flash(skipCalcFlows=1):
                break
            
        return 1
                
    def ValidateOk(self):
        if self.GetParameterValue(NULIQPH_PAR) <= 0: return 0
        return 1

class ClonePort:
    """
    dummy class to allow AddObject to add clone ports to stream classes
    """
    def __init__(self, incoming=1):
        """
        incoming is true if input stream
        """
        self.incoming = incoming

class SensorPort:
    """
    dummy object to allow Stream_Material.AddObject to add arbitrary signal ports
    """
    def __init__(self, varType):
        """
        varType is the type of signal
        """
        self.varType = varType
        
class Stream_Energy(UnitOperations.UnitOperation):
    """Class for energy stream. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """Init the stream"""        
        super(Stream_Energy, self).__init__(initScript)
        
        p = self.CreatePort(ENE|IN, IN_PORT)
        p.SetLocked(True)
        
        p = self.CreatePort(ENE|OUT, OUT_PORT)
        p.SetLocked(True)

    def AddObject(self, obj, name):
        """
        if object is clone port, create the appropriate kind of port
        other wise call parent method
        """
        if isinstance(obj, ClonePort):
            oldPort = self.GetPort(name)
            if oldPort:
                self.DeletePort(oldPort)  # can't have duplicates
            if obj.incoming:
                self.CreatePort(ENE|IN, name)
            else:
                self.CreatePort(ENE|OUT, name)
            self.PushSolveOp(self)
        elif isinstance(obj, SensorPort):
            oldPort = self.GetPort(name)
            if oldPort:
                self.DeletePort(oldPort)  # can't have duplicates
            port = self.CreatePort(SIG, name)
            port.SetSignalType(ENERGY_VAR)
            self.PushSolveOp(self)
        else:
            super(Stream_Energy, self).AddObject(obj, name)
                
        
    def Solve(self):
        """Solve"""
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)
        ports = self.GetPorts(ENE|IN|OUT|SIG)
        for port in ports:
            inPort.ShareWith(port)
            
        if len(ports) > 2:
            # do again to avoid order dependance
            for port in ports:
                inPort.ShareWith(port)
            

        return 1

class Stream_Signal(UnitOperations.UnitOperation):
    """Class for signal stream. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """Init the stream"""        
        super(Stream_Signal, self).__init__(initScript)
        
        p = self.CreatePort(SIG, IN_PORT)
        p.SetLocked(True)
        
        p = self.CreatePort(SIG, OUT_PORT)
        p.SetLocked(True)
        
        #self.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)  # generic type by default
        self.SetParameterValue(SIGTYPE_PAR, None)
        
    def SetParameterValue(self, paramName, value):
        UnitOperations.UnitOperation.SetParameterValue(self, paramName, value)
        if paramName == SIGTYPE_PAR:
            for port in self.GetPorts():
                port.SetSignalType(value)
                
    def ValidateParameter(self, paramName, value):
        if not super(Stream_Signal, self).ValidateParameter(paramName, value):
            return 0
        if paramName == SIGTYPE_PAR:
            currName = self.parameters.get(SIGTYPE_PAR, None)
            if not currName: return 1
            currName = currName.split('_', 1)[0]
            validateName = value.split('_', 1)[0]
            equivalent = 1
            try:
                if PropTypes[currName].unitType != PropTypes[validateName].unitType:
                    equivalent = S42Glob.unitSystem.IsEquivalentType(PropTypes[currName].unitType, PropTypes[validateName].unitType)
            except:
                #if it failed comparing, then assume they are equivalent
                pass
            if equivalent: return 1
            
            #The types are not equivalent. If any port is already connected, then 
            #there will be a type conflict, hence, return false
            for port in self.GetPorts():
                conn = port.GetConnection()
                if conn != None:
                    return 0
                    
        return 1
    
    def DeleteObject(self, obj):
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() in (SIGTYPE_PAR):
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return

        super(Stream_Signal, self).DeleteObject(obj)
        
    def AddObject(self, obj, name):
        """
        if object is clone port, create the appropriate kind of port
        other wise call parent method
        """
        if isinstance(obj, ClonePort):
            oldPort = self.GetPort(name)
            if oldPort:
                self.DeletePort(oldPort)  # can't have duplicates
            port = self.CreatePort(SIG, name)
            type = self.GetParameterValue(SIGTYPE_PAR)
            if type != None:
                port.SetSignalType(type)
            self.PushSolveOp(self)
        else:
            super(Stream_Signal, self).AddObject(obj, name)
                
        
    def Solve(self):
        """Solve"""
        inPort = self.GetPort(IN_PORT)
        inPortType = inPort.GetSignalType()
        for i in range(2):                     # do twice to avoid order dependence
            for port in self.GetPorts(SIG):
                portType = port.GetSignalType()
                if inPortType != SIGNAL_TYPE_NONE:
                    if portType == SIGNAL_TYPE_NONE:
                        port.CreateProperty(inPortType)
                elif portType != SIGNAL_TYPE_NONE:
                    inPort.CreateProperty(portType)
                    inPortType = portType
                inPort.ShareWith(port)
        return 1
