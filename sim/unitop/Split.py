"""Models a simple stream splitting

Classes - Splitter - inherits from UnitOperation
"""

from sim.solver.Variables import *
from sim.solver import Error
import UnitOperations
import Balance
import copy
FLOWFRAC_PAR = 'FlowFraction'

class Splitter(UnitOperations.UnitOperation):
    """ simple stream splitting class"""

    def __init__(self, initScript = None):
        """Init the splitter
        
        Init Info:
            nuStreamsOut = 2
            
        """          
        super(Splitter, self).__init__(initScript)
        
        self.fracPortList = []
        self.matPortList = []
        
        self.CreatePort(MAT|IN, IN_PORT)  # only one inlet
        
        self.SetParameterValue(NUSTOUT_PAR, 2)
        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(Splitter,self).AdjustOldCase(version)
        
        #Do a customized version of UpdatePortsOut
        if version[0] < 31:
            nuPorts = self.GetNumberPorts(SIG)
            nuStOut = self.parameters[NUSTOUT_PAR]
            
            for i in range(nuPorts, nuStOut, -1):
                self.DeletePortNamed(FLOWFRAC_PAR + str(i - 1))
            for i in range(nuPorts, nuStOut):
                port = self.CreatePort(SIG, FLOWFRAC_PAR + str(i))
                port.SetSignalType(FRAC_VAR)
            
            self.fracPortList = []
            self.matPortList = []
            for i in range(nuStOut):
                port = self.GetPort(OUT_PORT + str(i))
                self.matPortList.append(port)
                self.fracPortList.append(self.GetPort(FLOWFRAC_PAR + str(i)))
            
                
    def SetParameterValue(self, paramName, value):
        super(Splitter, self).SetParameterValue(paramName, value)
        if paramName == NUSTOUT_PAR:
            self.UpdatePortsOut()
            
    def ValidateParameter(self, paramName, value):
        if not super(Splitter, self).ValidateParameter(paramName, value):
            return False
        if paramName == NUSTOUT_PAR:
            if not type(value) in (type(1), type(1.0)) or value < 1:
                return False
        return True
            
    def DeleteObject(self, obj):
        """Trap and prevent attempt to delete"""
        if isinstance(obj, OpParameter):
            if obj.name == NUSTOUT_PAR:
                raise AssertionError
        super(Splitter, self).DeleteObject(obj)
            
    def UpdatePortsOut(self):
        """Update the amount and names of the ports in"""        
        nuPorts = self.GetNumberPorts(MAT|OUT)
        nuStOut = self.parameters[NUSTOUT_PAR]
        
        for i in range(nuPorts, nuStOut, -1):
            self.DeletePortNamed(OUT_PORT + str(i - 1))
            self.DeletePortNamed(FLOWFRAC_PAR + str(i - 1))
        for i in range(nuPorts, nuStOut):
            self.CreatePort(MAT|OUT, OUT_PORT + str(i))
            port = self.CreatePort(SIG, FLOWFRAC_PAR + str(i))
            port.SetSignalType(FRAC_VAR)
            
        self._balance = Balance.Balance(Balance.MOLE_BALANCE|Balance.ENERGY_BALANCE)
        self._balance.AddInput(self.GetPort(IN_PORT))
        self.fracPortList = []
        self.matPortList = []
        for i in range(nuStOut):
            port = self.GetPort(OUT_PORT + str(i))
            self._balance.AddOutput(port)
            self.matPortList.append(port)
            
            self.fracPortList.append(self.GetPort(FLOWFRAC_PAR + str(i)))
       
    def CleanUp(self):
        del self.fracPortList
        del self.matPortList
        super(Splitter, self).CleanUp()
            
    def Solve(self):
        inletPort = self.GetPort(IN_PORT)
        ports = self.matPortList       #Should be in order        
        fracPorts = self.fracPortList  #Should be in order
        numMatPorts = len(ports)

        
        feedFlow = inletPort.GetPropValue(MOLEFLOW_VAR)
        #At most do it twice
        for iter in (0, 1):
            unkFracIdx = []
            sumFracs = 0.0
            foundFeed = False
            for i in range(numMatPorts):
                frac = fracPorts[i].GetValue()
                if frac != None:
                    if feedFlow != None:
                        ports[i].SetPropValue(MOLEFLOW_VAR, frac*feedFlow, CALCULATED_V)
                    elif abs(frac) > 1.0E-100:
                        moleFlow = ports[i].GetPropValue(MOLEFLOW_VAR)
                        if moleFlow != None:
                            feedFlow = moleFlow/frac
                            foundFeed = True
                            break #Start over with feed known by now
                    sumFracs += frac
                else:
                    unkFracIdx.append(i)
                    
            if not foundFeed:
                break
                    
        #Solve for the unknown frac
        if len(unkFracIdx) == 1:
            fracPorts[unkFracIdx[0]].SetValue(1.0 - sumFracs, CALCULATED_V)
            del unkFracIdx[0]
            sumFracs = 1.0
            
        gotFlowFromFracs = True
        while gotFlowFromFracs:
            gotFlowFromFracs = False
            self._balance.DoBalance()
            for p in ports:
                inletPort.ShareWith(p, INTENSIVE_PROP|CANFLASH_PROP)
                p.CalcFlows()
            self._balance.DoBalance()
            
            while self.FlashAllPorts():
                for p in ports:
                    inletPort.ShareWith(p, INTENSIVE_PROP|CANFLASH_PROP)
                self._balance.DoBalance()
                
            self._balance.DoBalance()

            feedFlow = inletPort.GetPropValue(MOLEFLOW_VAR)
            if feedFlow != None and abs(feedFlow) > 1.0E-100:
                #Solve for unkfracs
                copyUnkFracs = copy.copy(unkFracIdx)
                for idx in copyUnkFracs:
                    moleFlow = ports[idx].GetPropValue(MOLEFLOW_VAR)
                    if moleFlow != None:
                        frac = moleFlow/feedFlow
                        fracPorts[idx].SetValue(frac, CALCULATED_V)
                        sumFracs += frac
                        unkFracIdx.remove(idx)
                        
                #Solve for the unknown frac
                if len(unkFracIdx) == 1:
                    fracPorts[unkFracIdx[0]].SetValue(1.0 - sumFracs, CALCULATED_V)
                    del unkFracIdx[0]
                    sumFracs = 1.0
                        
                #Solve for unk flows
                for i in range(numMatPorts):
                    moleFlow = ports[i].GetPropValue(MOLEFLOW_VAR)
                    if moleFlow == None and i not in unkFracIdx:
                        frac = fracPorts[i].GetValue()
                        ports[i].SetPropValue(MOLEFLOW_VAR, feedFlow*frac, CALCULATED_V)
                        gotFlowFromFracs = True
            else:
                #Can the feed be obtained from the fracs?
                for i in range(numMatPorts):
                    if i in unkFracIdx: 
                        continue
                    frac = fracPorts[i].GetValue()
                    if abs(frac) < 1.0E-100: 
                        continue
                    moleFlow = ports[i].GetPropValue(MOLEFLOW_VAR)
                    if moleFlow == None: 
                        continue
                    inletPort.SetPropValue(MOLEFLOW_VAR, moleFlow/frac, CALCULATED_V)
                    gotFlowFromFracs = True
                    break
                
                        
        if not unkFracIdx:
            #Make it raise an inconsistency if fracs do not add up to 1.0
            if sumFracs > 1.001:
                frac = fracPorts[-1].GetValue()
                fracPorts[-1].SetValue(1.0 - sumFracs + frac, CALCULATED_V)
            
        return 1

    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(Splitter, self)._RemoveFromCloneList(clone, attrNamesToClone)
        dontClone = ["fracPortList", "matPortList", "_balance"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone