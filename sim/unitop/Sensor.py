"""Sensor module - provides a signal port for reporting a variables value,
but can also use that signal to 'calculate' the variable

Classes:
Sensor -- Class for the sensor. Inherits from Stream_Material

"""

import Stream
from sim.solver.Variables import *

class PropertySensor(Stream.Stream_Material):
    """Class for the sensor. Inherits from Stream_Material
    provides a signal port for reporting a variables value,
    but can also use that signal to 'calculate' the variable    
    """
    def __init__(self, initScript = None):
        """Init the sensor

        Init Info:
        varType = GENERIC_VAR
        """          
        Stream.Stream_Material.__init__(self, initScript)

        self.CreatePort(SIG, SIG_PORT)
        self.SetParameterValue(SIGTYPE_PAR, GENERIC_VAR)
        
    def GetListOfReqParam(self): return (SIGTYPE_PAR, )
    
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        Stream.Stream_Material.SetParameterValue(self, paramName, value)
        if paramName == SIGTYPE_PAR:
            self.GetPort(SIG_PORT).SetSignalType(value)
                       
    #def Solve(self):
        #"""Solve"""
        #super(PropertySensor,self).Solve()
        #sigPort = self.GetPort(SIG_PORT)
        #inPort = self.GetPort(IN_PORT)
        #outPort = self.GetPort(OUT_PORT)
        
        #varType = self.GetParameterValue(SIGTYPE_PAR)
        #sigValue = sigPort.GetValue()
        #if sigValue == None:
            #sigValue = inPort.GetPropValue(varType)
            #if sigValue == None:
                #sigValue = outPort.GetPropValue(varType)
        
        #if sigValue != None:
            #sigPort.SetValue(sigValue, CALCULATED_V)
            #inPort.SetPropValue(varType, sigValue, CALCULATED_V)
            #outPort.SetPropValue(varType, sigValue, CALCULATED_V)
            
        #super(PropertySensor,self).Solve()

class EnergySensor(Stream.Stream_Energy):
    """Class for the sensor. Inherits from Stream_Energy
    provides a signal port for reporting a energy value,
    but can also use that signal to 'calculate' the energy    
    """
    def __init__(self, initScript = None):
        """Init the sensor

        Init Info:
        varType = GENERIC_VAR
        """          
        Stream.Stream_Energy.__init__(self, initScript)
        self.CreatePort(SIG, SIG_PORT)
        self.GetPort(SIG_PORT).SetSignalType(ENERGY_VAR)
    
    def Solve(self):
        """Solve"""
        sigPort = self.GetPort(SIG_PORT)
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)
        
        sigValue = sigPort.GetValue()
        if sigValue == None:
            sigValue = inPort.GetValue()
            if sigValue == None:
                sigValue = outPort.GetValue()
        
        if sigValue != None:
            sigPort.SetValue(sigValue, CALCULATED_V)
            inPort.SetValue(sigValue, CALCULATED_V)
            outPort.SetValue(sigValue, CALCULATED_V)
            
        Stream.Stream_Energy.Solve(self)
