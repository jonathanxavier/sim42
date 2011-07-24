"""Models a simple flash and a flas with multiple inlet streams

Classes:
SimpleFlash -- Class for the simple flash. Inherits from UnitOperation
MixAndFlash -- Class for the flash with multiple inlets. Inh from UnitOperation

"""

import re

import UnitOperations
import Mixer
import Balance

from sim.solver.Variables import *

FLASH = 'myFlash'  #Child flash name of the stage flash
MIX = 'myMixer'    #Child mixer name of the stage flash

VALID_UNIT_OPERATIONS = ['SimpleFlash',
                         'MixAndFlash']

KEY_CMP_PAR = "KeyCmp"

class SimpleFlash(UnitOperations.UnitOperation):
    """Class for the simple flash. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """
        Init the flash
        """      
        UnitOperations.UnitOperation.__init__(self, initScript)
        
        self.feedPort = self.CreatePort(IN|MAT, IN_PORT)
        self.feedPort.SetLocked(True)
        
        self.vapPort = self.CreatePort(OUT|MAT, V_PORT)
        self.vapPort.SetLocked(True)

        #Initialize this to 0 and they will get updated after every call to UpdatePortsOut
        self.nuLPorts = 0
        self.nuSPorts = 0
        
        self.UpdatePortsOut()
    
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        super(SimpleFlash, self).SetParameterValue(paramName, value)
        self.UpdatePortsOut()
        
    def AddedToParent(self, parentUO, name):
        """
        call super method and then call UpdatePortsOut to set the number of
        liquid ports in accordance with the parent default NULIQPH_PAR
        """
        super(SimpleFlash, self).AddedToParent(parentUO, name)
        self.UpdatePortsOut()

    def NumberLiquidPhasesChanged(self, value):
        """
        update ports
        """
        super(SimpleFlash,self).NumberLiquidPhasesChanged(value)
        self.UpdatePortsOut()

    def NumberSolidPhasesChanged(self, value):
        """
        update ports
        """
        super(SimpleFlash,self).NumberSolidPhasesChanged(value)
        self.UpdatePortsOut()        
        
    def UpdatePortsOut(self):
        """Update the amount and names of the ports out"""
        portNames = self.GetPortNames(MAT|OUT) 
        nuLPorts = self.nuLPorts
        nuSPorts = self.nuSPorts

        #Get how many phases of each we actually have
        nuLPh = self.NumberLiqPhases()
        nuSPh = self.NumberSolidPhases()
        
        #Create or delete the liquid ports
        for i in range(nuLPorts, nuLPh, -1):
            p = self.GetPort(L_PORT + str(i - 1))
            p.SetLocked(False)
            self.DeletePort(p)
        for i in range(nuLPorts, nuLPh):
            p = self.CreatePort(MAT|OUT, L_PORT + str(i))
            p.SetLocked(True)
            
        #Create or delete the solid ports
        for i in range(nuSPorts, nuSPh, -1):
            p = self.GetPort(S_PORT + str(i - 1))
            p.SetLocked(False)
            self.DeletePort(p)
        for i in range(nuSPorts, nuSPh):
            p = self.CreatePort(MAT|OUT, S_PORT + str(i))
            p.SetLocked(True)
            
        #Update the port counts
        self.nuLPorts = nuLPh
        self.nuSPorts = nuSPh
            
        #Update the balance
        self.balance = Balance.Balance(Balance.MOLE_BALANCE | Balance.ENERGY_BALANCE)
        self.balance.AddInput(self.ports_mat_IN[IN_PORT])
        for port in self.GetPorts(MAT|OUT):
            self.balance.AddOutput(port)
            
            
    def Solve(self):
        """Solve"""
        ## needs to be able to back solve when outlet streams are known
        
        feedPort = self.feedPort
        vapPort = self.vapPort
        outletPorts = self.GetPorts(MAT|OUT)
        
        self.ShareProperties(P_VAR, feedPort, outletPorts)
        self.ShareProperties(T_VAR, feedPort, outletPorts)

        #Fix for zero flows
        fMoles = feedPort.GetPropValue(MOLEFLOW_VAR)
        if fMoles == 0:
            for p in outletPorts:
                p.SetPropValue(MOLEFLOW_VAR, 0.0, CALCULATED_V)
                p.CalcFlows()

        #Set vap frac to vap port
        vapPort.SetPropValue(VPFRAC_VAR, 1.0, CALCULATED_V)
        
        #Set vap frac to liq port if there is only one liq phase
        nuLiqPhases = self.NumberLiqPhases()
        if nuLiqPhases == 1:
            port = self.GetPort('%s_0' %L_PORT)
            if port:
                port.SetPropValue(VPFRAC_VAR, 0.0, CALCULATED_V)
        
        
        flashPort = self.PortToFlash()
        if not flashPort: return None
        thCaseObj = self.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        results = thAdmin.Flash(prov, case, flashPort.GetCompounds(), flashPort.GetProperties(),
                                self.NumberLiqPhases(),
                                nuSolids=self.NumberSolidPhases(), 
                                stdVolRefT=self.GetParameterValue(STDVOLREFT_PAR))
                               
        if results == None: return None

        propsNamesOut = list(results.propNames)
        zIndex = propsNamesOut.index(ZFACTOR_VAR)
        bulkProps = results.bulkProps
        phasesFracs = results.phaseFractions
        phasesComposit = results.phaseComposition
        phasesProps = results.phaseProps        

        flashPort.AssignFlashResults(results)
        
        self.ShareProperties(P_VAR, feedPort, outletPorts)
        self.ShareProperties(T_VAR, feedPort, outletPorts)

        #try to determine feed flow
        fMoles = feedPort.GetPropValue(MOLEFLOW_VAR)
        if feedPort is flashPort:
            #Try using the vapour phase
            if fMoles == None:
                if phasesFracs[0] != 0.0:
                    port = self.GetPort(V_PORT)
                    port.CalcFlows()
                    vMoles = port.GetPropValue(MOLEFLOW_VAR)
                    if vMoles != None:
                        fMoles = vMoles / phasesFracs[0]
            
            #Now try using the liquid phase
            if fMoles == None:
                for i in range(self.nuLPorts):
                    phFrac = phasesFracs[i+1]
                    if phFrac == 0.0:
                        continue  # can't make use of 0 phfrac
                        
                    port = self.GetPort(L_PORT + str(i))
                    port.CalcFlows()
                    pMoles = port.GetPropValue(MOLEFLOW_VAR)
                    if pMoles != None:
                        fMoles = pMoles/phFrac
                        break

            #Now try using the solid phase
            if fMoles == None:
                for i in range(self.nuSPorts):
                    phFrac = phasesFracs[i+1+self.nuLPorts]
                    if phFrac == 0.0:
                        continue  # can't make use of 0 phfrac
                        
                    port = self.GetPort(S_PORT + str(i))
                    port.CalcFlows()
                    pMoles = port.GetPropValue(MOLEFLOW_VAR)
                    if pMoles != None:
                        fMoles = pMoles/phFrac
                        break                    
                    
        if fMoles != None:
            feedPort.SetPropValue(MOLEFLOW_VAR, fMoles, CALCULATED_V)
            if feedPort is flashPort:
                vapPort.SetPropValue(MOLEFLOW_VAR, fMoles * phasesFracs[0], CALCULATED_V)
        feedPort.CalcFlows()
        
        if (vapPort is not flashPort) and abs(bulkProps[zIndex] - phasesProps[0][zIndex]) < 1.e-40:
            # single phase
            vapPort.AssignFlashResults(results)
        else:
            vapPort.AssignFlashResults(results.ResultsForPhase(0))
        vapPort.CalcFlows()
 
        
        #The following chunk of code assigns specific phases to specific ports
        #in case a parameter like this was set
        #KeyCmp_Liq0 = WATER 0.5
        #In this case it assigns the phase with a composition of 0.5 or more to the Liq0 port
        cmpNames = self.GetCompoundNames()
        nuLiqPorts = self.nuLPorts
        nuSolPorts = self.nuSPorts

        portToResultMap = {}
        resultToPortMap = {}
        count = 1
        for i in range(nuLiqPorts):
            portToResultMap[L_PORT + str(i)] = count
            #resultToPortMap[count] = L_PORT + str(i)
            count += 1
        for i in range(nuSolPorts):
            portToResultMap[S_PORT + str(i)] = count
            #resultToPortMap[count] = L_PORT + str(i)            
            count += 1
            
        idxResults = range(nuLiqPorts)
        for pName, resIdx in portToResultMap.items():
            cmpName = self.GetParameterValue(KEY_CMP_PAR + "_" + pName)
            if cmpName != None:
                cmpVal = 0.0
                lst = cmpName.split()
                if len(lst) > 1:
                    cmpName = lst[0]
                    try:
                        cmpVal = float(lst[1])
                    except:
                        pass
                cmpName = re.sub('_', ' ', cmpName)
                
                if cmpName in cmpNames:
                    idxCmp = cmpNames.index(cmpName)
                    biggest = 0.0
                    idxPhase = 0
                    onePhaseIsZero = False
                    for j in range(1, nuLiqPorts+nuSolPorts+1):
                        val = phasesComposit[j][idxCmp]
                        if not phasesFracs[j]:
                            onePhaseIsZero = True
                        if val > biggest:
                            biggest = val
                            idxPhase = j
                    if idxPhase == 0:
                        #no reordering if fractions of key compound are all 0.0
                        pass
                    elif not onePhaseIsZero or biggest >= cmpVal: 
                        temp = portToResultMap[pName]
                        for k in portToResultMap.keys():
                            if portToResultMap[k] == idxPhase:
                                portToResultMap[k] = temp
                                break
                        portToResultMap[pName] = idxPhase
                
        for pName, resIdx in portToResultMap.items():
            port = self.GetPort(pName)
            idx = resIdx
            if fMoles != None and feedPort is flashPort:
                port.SetPropValue(MOLEFLOW_VAR, fMoles * phasesFracs[idx], CALCULATED_V)
            port.AssignFlashResults(results.ResultsForPhase(idx))

        # if it couldn't calculate any other way, assigned unknown vapfracs
        for port in outletPorts:
            if port != vapPort and port.GetPropValue(VPFRAC_VAR) == None:
                port.SetPropValue(VPFRAC_VAR, 0.0, CALCULATED_V)

        if feedPort is not flashPort:
            self.balance.DoBalance()
            feedPort.Flash()
            feedPort.CalcFlows()
            for port in outletPorts:
                port.CalcFlows()
        return 1

    def CanFlashPort(self, port):
        """ return true in port has enough information to do flash """
        if port.GetNuKnownProps(CANFLASH_PROP) < 2:
            return 0

        if not port.ReadyToFlash():
            return 0
        return 1
   
    def PortToFlash(self):
        """ return the port to flash or None if flash can't be done """
        nuLiqPhases = self.NumberLiqPhases()
        if nuLiqPhases <= 0: return None
        if not self.GetThermo(): return None

        if self.CanFlashPort(self.ports_mat_IN[IN_PORT]):
            return self.ports_mat_IN[IN_PORT]

        for port in self.GetPorts(MAT|OUT):
            if self.CanFlashPort(port):
                return port
        
        return None
   
    def ValidateOk(self):
        """True if the uo is ready to be calculated"""        
        if self.PortToFlash:
            return 1
        else:
            return 0

    def AdjustOldCase(self, version):
        """
        add balance to old cases
        """
        super(SimpleFlash, self).AdjustOldCase(version)
        
        if version[0] < 19:
            self.feedPort = self.GetPort(IN_PORT)
            self.vapPort = self.GetPort(V_PORT)
            self.nuLPorts = len(self.GetPorts(MAT|OUT)) - 1
            self.nuSPorts = 0
        
        if version[0] < 6:
            self.UpdatePortsOut()
            
            
    def _CloneParameters(self, clone, attrNamesToClone):
        """Set the liq and solid phases directly such that the balance and ports are created directly"""
        super(SimpleFlash, self)._CloneParameters(clone, attrNamesToClone)
        
        #Manually put these parameters to make sure they are not being obtained from the parents
        nuLPh = self.NumberLiqPhases()
        nuSPh = self.NumberSolidPhases()
        clone.parameters[NULIQPH_PAR] = nuLPh
        clone.parameters[NUSOLPH_PAR] = nuSPh
            
        #This should recreate a number of attributes
        clone.UpdatePortsOut()
        
        #Remove these attributes from the clone list
        dontClone = ["balance", "nuLPorts", "nuSPorts"]
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
    
    
class MixAndFlash(UnitOperations.UnitOperation):
    """Class for the flash with multiple inlets. Inherits from UnitOperation"""
    #Class useful for stage calculations (i.e. equilibrium trays)
    def __init__(self, initScript = None):
        """Init the flash

        Init Info:
        nuStreamsIn = 2

        """         
        UnitOperations.UnitOperation.__init__(self, initScript)

        #The unit is made by connecting a mixer with a flash
        innerFlash = SimpleFlash()
        self.AddUnitOperation(innerFlash, FLASH)
        innerMixer = Mixer.Mixer()
        self.AddUnitOperation(innerMixer, MIX)
        
        self.SetParameterValue(NUSTIN_PAR, 2)

        # borrow the child ports for our port names
        ports = self.chUODict[FLASH].ports_mat_OUT 
        for portName in ports.keys():
            self.BorrowChildPort(ports[portName], portName)

        self.ConnectPorts(MIX, OUT_PORT, FLASH, IN_PORT)

    def AddedToParent(self, parentUO, name):
        """
        call super method and then call flash UpdatePortsOut to set the number of
        liquid ports in accordance with the parent default NULIQPH_PAR
        """
        super(MixAndFlash, self).AddedToParent(parentUO, name)
        self.chUODict[FLASH].UpdatePortsOut()

    def GetListOfReqParam(self): return (NULIQPH_PAR, NUSTIN_PAR)

    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        super(MixAndFlash, self).SetParameterValue(paramName, value)
 
        if paramName == NULIQPH_PAR:
            flash, mix = self.chUODict[FLASH], self.chUODict[MIX]
            
            flash.SetParameterValue(paramName, value)
            mix.SetParameterValue(paramName, value)

            nuPorts = self.GetNumberPorts(MAT|OUT)
            nuLPorts = nuPorts - 1
            nuLPh = flash.NumberLiqPhases()
            ports = flash.ports_mat_OUT 
            for i in range(nuLPorts, nuLPh, -1):
                self.DeletePortNamed(L_PORT + str(i - 1))
            for i in range(nuLPorts, nuLPh):
                portName = L_PORT + str(i)
                self.BorrowChildPort(ports[portName], portName)

            
        elif paramName == NUSTIN_PAR:
            mix = self.chUODict[MIX]
            
            mix.SetParameterValue(paramName, value)

            nuPorts = self.GetNumberPorts(MAT|IN)
            nuStIn = self.parameters[NUSTIN_PAR]
            ports = mix.ports_mat_IN
            for i in range(nuPorts, nuStIn, -1):
                self.DeletePortNamed(IN_PORT + str(i - 1))
            for i in range(nuPorts, nuStIn):
                portName = IN_PORT + str(i)
                self.BorrowChildPort(ports[portName], portName)


            
    def ValidateOk(self):
        """True if the uo is ready to be calculated"""          
        if self.GetParameterValue(NULIQPH_PAR) <= 0: return 0
        if self.parameters[NUSTIN_PAR] <= 0: return 0
        if not self.GetThermo(): return 0
        return 1    
