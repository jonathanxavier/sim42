"""Requests hydrate calculation from the thermo provider

Class:
Hydrate -- Which inherits from UnitOperations.UnitOperation
HydrateCurve -- Inherits form Properties.VectorProps

"""



from sim.solver.Variables import *
from sim.solver import Ports
from sim.unitop import UnitOperations, Properties
from Properties import EMPTY_VAL

import Numeric 
from Numeric import zeros, ones, Float, Int, reshape, transpose, array

THYDRATE_PORT = 'HydrateTemp'
PHYDRATE_PORT = 'HydratePress'
HYDRATEFORM_PORT = 'HydrateForm'

class Hydrate(UnitOperations.UnitOperation):
    def __init__ (self, initScript =  None):
        super(Hydrate, self).__init__(initScript)

        #
        self.outPort = self.CreatePort(MAT|OUT, OUT_PORT)
        self.outPort.SetLocked(True)
        self.inPort = self.CreatePort(MAT|IN, IN_PORT)
        self.inPort.SetLocked(True)
        
        #Add signal Ports
        self.hydTPort = self.CreatePort(SIG, THYDRATE_PORT)
        self.hydTPort.SetSignalType(T_VAR)
        self.hydTPort.SetLocked(True)
        
        self.hydPPort = self.CreatePort(SIG, PHYDRATE_PORT)
        self.hydPPort.SetSignalType(P_VAR)
        self.hydPPort.SetLocked(True)
        
        self.hydFormPort = self.CreatePort(SIG, HYDRATEFORM_PORT)
        self.hydFormPort.SetSignalType(GENERIC_VAR)
        self.hydFormPort.SetLocked(True)
        
        #Connects externally
        self.BorrowChildPort(self.inPort, IN_PORT)
        self.BorrowChildPort(self.outPort, OUT_PORT)
        
        
        
    def CleanUp(self):
        self.hydFormPort = None
        self.hydTPort = None
        self.hydPPort = None
        self.inPort = None
        self.outPort = None
        self._thCaseObj = None
        super(Hydrate, self).CleanUp()
        
        
    def SolvePorts(self):
        # share between in and out
        self.FlashAllPorts()
        self.inPort.ShareWith(self.outPort)
        self.FlashAllPorts()
        self.inPort.ShareWith(self.outPort)        
        
        
    def Solve(self):
        
        self.SolvePorts()
        self.unitOpMessage = ('NoMessage', )
        
        p = self.inPort.GetPropValue(P_VAR)
        t = self.inPort.GetPropValue(T_VAR)
        z = self.inPort.GetCompositionValues()
        
        
        if not z or None in z:
            return
        
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: return 
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        statusOut = ''
        if t:
            propName = "hydrate3phasepressure"
            port = self.hydPPort
            value, status = thAdmin.GetSpecialProperty(prov, case, t, z, propName)
            try:
                value = float(value)
                if value < 1.0E37 and value != EMPTY_VAL:
                    port.SetValue(value, CALCULATED_V)
                if status: statusOut += '%s: %s;\n' %(PHYDRATE_PORT, status)
            except:
                statusOut += '%s: %s;\n' %(PHYDRATE_PORT, status)
        if p:
            propName = "hydrate3phasetemperature"
            port = self.hydTPort
            value, status = thAdmin.GetSpecialProperty(prov, case, p, z, propName)
            try:
                value = float(value)
                if value < 1.0E37 and value != EMPTY_VAL:
                    port.SetValue(value, CALCULATED_V)
                if status: statusOut += '%s: %s;\n' %(THYDRATE_PORT, status)
            except:
                statusOut += '%s: %s;\n' %(THYDRATE_PORT, status)
                
        if t and p:
            propName = "hydrate3phaseformation"
            port = self.hydFormPort
            value, status = thAdmin.GetSpecialProperty(prov, case, [t, p], z, propName)
            try:
                if value == "YES":
                    value = 1.0
                else:
                    value = 0.0
                if value != str(EMPTY_VAL): port.SetValue(value, CALCULATED_V)
                if status: statusOut += '%s: %s;\n' %(HYDRATEFORM_PORT, status)
            except:
                statusOut += '%s: %s;\n' %(HYDRATEFORM_PORT, status)
            
        if statusOut:
            self.unitOpMessage = ('ThermoProviderMsg', (statusOut,))
            if not self.IsForgetting():
                self.InfoMessage('ThermoProviderMsg', (self.GetPath(), statusOut))
            
        
class HydrateCurve(Properties.VectorProps):
    def __init__(self, initScript=None):
        super(HydrateCurve, self).__init__(initScript)
        
        self.portTMax = self.CreatePort(SIG, 'MaxT')
        self.portTMin = self.CreatePort(SIG, 'MinT')
        self.portPMax = self.CreatePort(SIG, 'MaxP')
        
        self.portTMax.SetSignalType(T_VAR)
        self.portTMin.SetSignalType(T_VAR)
        self.portPMax.SetSignalType(P_VAR)
        
        self.portTMax.SetLocked(True)
        self.portTMin.SetLocked(True)
        self.portPMax.SetLocked(True)
        
        self.SetParameterValue('HYDRATECURVE' + Properties.ACTIVE_KEY, True)
            
        
    def GetAvVectorPropsString(self):
        return 'HYDRATECURVE'
    
    def GetAvVectorPropsList(self):
        return ['HYDRATECURVE']
            
            
    def Solve(self):
        self.SolvePorts()
        self.unitOpMessage = ('NoMessage', )
        
        #Clear results
        for key in self.results.keys():
            self.results[key] = None
            
        #Get limits
        tMax = self.portTMax.GetValue()
        tMin = self.portTMin.GetValue()
        pMax = self.portPMax.GetValue()
        if None in (tMax, tMin, pMax): return
            
        #Get thermo
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: return 
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        fracs = self.portIn.GetCompositionValues()
        if None in fracs: return
        for propName in self.results.keys():
            if propName == 'HYDRATECURVE':
                option = '%s %s %s' %(tMin, tMax, pMax)
                value, status = thAdmin.GetSpecialProperty(prov, case, option, fracs, 'HYDRATECURVE')
                try:
                    valsList = value.split()
                    rows, cols = len(valsList)/2, 2
                    vals = map(float, valsList)[:-1]
                    vals = reshape(array(vals, Float), (rows, cols))
                    self.results[propName] = vals
                    if status:
                        self.unitOpMessage = ('ThermoProviderMsg', (status,))
                    else:
                        self.unitOpMessage = ('OK')
                    if not self.IsForgetting():
                        if status: self.InfoMessage('ThermoProviderMsg', (self.GetPath(), status))
                except:
                    self.results[propName] = None
                    self.unitOpMessage = ('ThermoProviderMsg', (status,))
                    if not self.IsForgetting():
                        self.InfoMessage('ThermoProviderMsg', (self.GetPath(), status))
    
    