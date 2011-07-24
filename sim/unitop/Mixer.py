"""Models a mixer

Classes:
Mixer -- Class for the mixer. Inherits from UnitOperation

"""

import UnitOperations
import Balance
from sim.solver.Variables import *

NONE_METHOD = "DontCalculate"
LOWESTP_METHOD = "LowestPInOutlet"
ALLP_EQUAL = "AllPEqual"
CALCPMODE_PAR = "CalcPressureMode"
AV_CALCPMODE_PAR = "AvCalcPressureModes"

class Mixer(UnitOperations.UnitOperation):
    """Class for the mixer. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """Init the mixer

        Init Info:
        nuStreamsIn = 2
        """          
        super(Mixer, self).__init__(initScript)

        self.CreatePort(MAT|OUT, OUT_PORT)
        self.SetParameterValue(NUSTIN_PAR, 2)
        self.SetParameterValue(CALCPMODE_PAR, LOWESTP_METHOD)
        self.SetParameterValue(AV_CALCPMODE_PAR, "%s %s %s" %(NONE_METHOD, LOWESTP_METHOD, ALLP_EQUAL))

        
    def GetListOfReqParam(self): return (NUSTIN_PAR)
    
    def AdjustOldCase(self, version):
        super(Mixer, self).AdjustOldCase(version)
        if version[0] < 72:
            val = self.GetParameterValue(CALCPMODE_PAR)
            if val == None:
                self.parameters[CALCPMODE_PAR] = LOWESTP_METHOD
            self.parameters[AV_CALCPMODE_PAR] = "%s %s %s" %(NONE_METHOD, LOWESTP_METHOD, ALLP_EQUAL)
    
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        
        super(Mixer, self).SetParameterValue(paramName, value)
        if paramName == NUSTIN_PAR: self.UpdatePortsIn()

           
    def UpdatePortsIn(self):
        """Update the amount and names of the ports in"""        
        nuPorts = self.GetNumberPorts(MAT|IN)
        nuStIn = self.parameters[NUSTIN_PAR]
        
        for i in range(nuPorts, nuStIn, -1):
            self.DeletePortNamed(IN_PORT + str(i - 1))
        for i in range(nuPorts, nuStIn):
            self.CreatePort(MAT|IN, IN_PORT + str(i))

        self._balance = Balance.Balance(Balance.MOLE_BALANCE|Balance.ENERGY_BALANCE)
        self._balance.AddOutput(self.GetPort(OUT_PORT))
        for i in range(nuStIn):
            self._balance.AddInput(self.GetPort(IN_PORT + str(i)))

            
    def Solve(self):
        """Solve"""
        # set outlet pressure to lowest inlet
        solveP = self.GetParameterValue(CALCPMODE_PAR)
        
        if solveP == LOWESTP_METHOD:
            # set outlet pressure to lowest inlet
            minP = None
            nuNones = 0
            ourPort = self.ports_mat_OUT[OUT_PORT]
            
            #Check to see if there is an out P already
            outP = ourPort.GetPropValue(P_VAR)
            
            #Find minP of the inlet and keep track of how many are unknown
            inPorts = self.ports_mat_IN.values()
            for port in inPorts:
                p = port.GetPropValue(P_VAR)
                if p == None:
                    #minP = None
                    nuNones += 1
                    missingPort = port
                    if outP == None or nuNones > 1:
                        break
                elif minP == None: 
                    minP = p
                else:
                    minP = min(minP, p)
                    
            #All inlet P known, then set the minP in the out
            if nuNones == 0:
                ourPort.SetPropValue(P_VAR, minP, CALCULATED_V)
                
            #Outlet P is known and only one inlet P is missing
            elif outP != None and nuNones == 1:
                if minP == None or outP <= minP:  #What to do if not? Raise an error?
                    missingPort.SetPropValue(P_VAR, outP, CALCULATED_V)
                
        elif solveP == ALLP_EQUAL:
            ports = self.GetPorts(IN|OUT|MAT)
            aP = None
            for port in ports:
                aP = port.GetPropValue(P_VAR)
                if aP != None:
                    break
            if aP != None:
                for port in ports:
                    port.SetPropValue(P_VAR, aP, CALCULATED_V)
                    
        self.FlashAllPorts()
        self._balance.DoBalance()
        while self.FlashAllPorts():
            self._balance.DoBalance()

        return 1
    

    def ValidateParameter(self, paramName, value):
        """Validates the NUSTIN_PAR"""
        if not super(Mixer, self).ValidateParameter(paramName, value):
            return 0
        if paramName == NUSTIN_PAR:
            #Not number or negative
            if not type(value) in (type(1), type(1.0)) or value < 1:
                return 0
        return 1
    
    def DeleteObject(self, obj):
        """Trap and prevent attempt to delete"""
        if isinstance(obj, OpParameter):
            if obj.name == NUSTIN_PAR or obj.name == AV_CALCPMODE_PAR:
                raise AssertionError
        super(Mixer, self).DeleteObject(obj)
        