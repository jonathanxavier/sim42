"""Valve class(es)"""
#Pressure drop calculation added by NORFAIZAH on 24th February 2003


from sim.solver import Ports, Error
from sim.solver.Variables import *
import UnitOperations, Balance

class Valve(UnitOperations.UnitOperation):
    """Class for simple isenthalpic Valve. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """
        create the ports and init the balance
        """
        super(Valve, self).__init__(initScript)
        
        self.outPort = self.CreatePort(OUT|MAT, OUT_PORT)
        self.outPort.SetLocked(True)
        
        self.inPort = self.CreatePort(IN|MAT, IN_PORT)
        self.inPort.SetLocked(True)

        self.dpPort = self.CreatePort(SIG, DELTAP_PORT)
        self.dpPort.SetSignalType(DELTAP_VAR)
        self.dpPort.SetLocked(True)
        
        self._balance = Balance.Balance(Balance.MOLE_BALANCE|Balance.ENERGY_BALANCE)
        self._balance.AddInput(self.inPort)
        self._balance.AddOutput(self.outPort)
        
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
        
    def Solve(self):
        
        #In case dp is known
        self.SolveForPressure()
        self._balance.DoBalance()
        
        #There are very odd occassions wehre this could actually be needed
        while self.FlashAllPorts():
            self._balance.DoBalance()
            self.SolveForPressure()

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(Valve,self).AdjustOldCase(version)
        
        if version[0] < 9:
            dpPort = self.CreatePort(SIG, DELTAP_PORT)
            dpPort.SetSignalType(DELTAP_VAR)
            inPort = self.GetPort(IN_PORT)
            outPort = self.GetPort(OUT_PORT)
            pIn = inPort.GetPropValue(P_VAR)
            pOut = outPort.GetPropValue(P_VAR)
            if pIn != None and pOut != None:
                dpPort.SetPropValue(DELTAP_VAR, pIn - pOut, CALCULATED_V) 
        if version[0] < 51:
            if not hasattr(self, 'inPort'):
                self.inPort = self.GetPort(IN_PORT)
            if not hasattr(self, 'outPort'):
                self.outPort = self.GetPort(OUT_PORT)
            if not hasattr(self, 'dpPort'):
                self.dpPort = self.GetPort(DELTAP_PORT)
                





            