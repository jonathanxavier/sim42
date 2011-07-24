"""ComponentSplitter class(es)"""

from sim.solver import Ports, Error
from sim.solver.Variables import *
import UnitOperations, Balance
import re

class SplitList(list):
    """
    List for holding the signal ports with split fractions
    """
    def __init__(self, parent):
        self.parent = parent
        
    def __str__(self):
        result = 'Splits:\n'
        for p in self:
            result += '   %s = ' % p.GetName()
            v = p.GetValue()
            if v != None:
                result += '%f\n' % v
            else:
                result += 'None\n'
        return result
        
    def CleanUp(self):
        self.parent = None
       
    def GetObject(self, desc):
        return self.parent.GetPort(desc)
   
    
class SimpleComponentSplitter(UnitOperations.UnitOperation):
    """
    Basic class has single material input port and two material output ports
    Also has a FractionList which has signal ports containing mole fraction of
    inlet component moles going into first outlet
    """
    def __init__(self, initScript = None):
        """
        create the ports and init the balance
        """
        UnitOperations.UnitOperation.__init__(self, initScript)
        self.portOut0 = self.CreatePort(OUT|MAT, OUT_PORT + str(0))
        self.portOut1 = self.CreatePort(OUT|MAT, OUT_PORT + str(1))
        self.portIn = self.CreatePort(IN|MAT, IN_PORT)
        self._balance = Balance.Balance(Balance.MOLE_BALANCE | Balance.ENERGY_BALANCE)
        self._balance.AddInput(self.portIn)
        self._balance.AddOutput(self.portOut0)
        self._balance.AddOutput(self.portOut1)
        self.splits = SplitList(self)  # list to hold split fraction signal ports
        self.borrowedSplits = None  # used by containing op to be notified of split list changes

    def CleanUp(self):
        self.portOut0 = self.portOut1 = self.portIn = None
        if self._balance:
            self._balance.CleanUp()
            self._balance = None
        self.splits.CleanUp()
        super(SimpleComponentSplitter, self).CleanUp()
        
    def GetObject(self, desc):
        if desc == 'Splits':
            return self.splits
        return super(SimpleComponentSplitter, self).GetObject(desc)
 
    def ThermoChanged(self, thCaseObj):
        """
        intercept this to set up splits list
        """
        super(SimpleComponentSplitter, self).ThermoChanged(thCaseObj)
        if thCaseObj == None: return

        thAdmin = thCaseObj.thermoAdmin
        provider = thCaseObj.provider
        thCase = thCaseObj.case
        
        
        # current list structure does not let me know what compounds were removed
        # or added, so I can only adjust length of port compoundlists
        #oldCompoundCount = len(self.splits)
        cmpNames = thAdmin.GetSelectedCompoundNames(provider, thCase)
        #newCompoundCount = len(cmpNames)
        
        ports = self.GetPorts(SIG)
        portsKeep = []
        portsCreate = []
        for cmpName in cmpNames:
            cmpName = re.sub(' ', '_', cmpName)
            portName = cmpName + '_Split'
            port = self.GetPort(portName)
            if port != None:
                portsKeep.append(port)
                if port in ports:
                    #It should be here !
                    ports.pop(ports.index(port))
            else:
                portsCreate.append(portName)
        portsDelete = ports
        
        #Delete unnecessary ports
        for port in portsDelete:
            self.DeletePort(port)
            
        #Create new ports as needed
        for portName in portsCreate:
            port = self.CreatePort(SIG, portName)
            port.SetSignalType(FRAC_VAR)
                
        #Update list of splits and keep them in order
        cnt = 0
        splitsLen = len(self.splits)
        nuCmps = len(cmpNames)
        if splitsLen > nuCmps:
            for i in range(splitsLen - nuCmps):
                self.splits.pop()
        elif splitsLen < nuCmps:
            for i in range(nuCmps - splitsLen):
                self.splits.append(None)
                
        for i in range(len(self.splits)):
            cmpName = re.sub(' ', '_', cmpNames[i])
            portName = cmpName + '_Split'
            self.splits[i] = self.GetPort(portName)
        
        if self.borrowedSplits:
            self.borrowedSplits.GrabSplitPorts()
            
        #while oldCompoundCount > newCompoundCount:
            #self.DeletePort(self.splits[oldCompoundCount - 1])
            #del self.splits[oldCompoundCount - 1]  # delete last compound
            #oldCompoundCount -= 1
        #while oldCompoundCount < newCompoundCount:
            #port = self.CreatePort(SIG, re.sub(' ','_',cmpNames[oldCompoundCount]) + '_Split')
            #port.SetSignalType(FRAC_VAR)
            #self.splits.append(port)
            #oldCompoundCount += 1
    
    def AppendCompound(self, cmpIdx=-1):
        """Add a compound to the port"""
        super(SimpleComponentSplitter, self).AppendCompound(cmpIdx)
        cmpNames = self.GetCompoundNames()
        port = self.CreatePort(SIG, re.sub(' ','_',cmpNames[cmpIdx]) + '_Split')
        port.SetSignalType(FRAC_VAR)
        self.splits.append(port)
        if self.borrowedSplits:
            self.borrowedSplits.GrabSplitPorts()

    def DeleteCompound(self, cmpName):
        """Deletes a compound from the port"""
        self.DeletePort(self.splits[self.GetCompoundNumber(cmpName)])
        del self.splits[self.GetCompoundNumber(cmpName)]
        super(SimpleComponentSplitter, self).DeleteCompound(cmpName)
        if self.borrowedSplits:
            self.borrowedSplits.GrabSplitPorts()

    def MoveCompound(self, idx1, idx2):
        super(SimpleComponentSplitter, self).MoveCompound(idx1, idx2)
        cmp1 = self.splits[idx1]
        if idx1 < idx2:
            # moving a compound down, insert first
            self.splits.insert(idx2, cmp1)
            del self.splits[idx1]
        elif idx1 > idx2:
            # moving a compound up, delete first
            del self.splits[idx1]
            self.splits.insert(idx2, cmp1)
            

    def GetCompoundNumber(self, cmpName):
        """
        return the position index for compound with name cmpName
        """
        try:
            cmpNames = self.GetCompoundNames()
            return cmpNames.index(cmpName)
        except:
            return None

    def CalcSplitFlows(self, splits, portOut):
        """
        calculate what one can between feed and portOut
        return true if splits has been changed
        """
        flowIn = self.portIn.GetPropValue(MOLEFLOW_VAR)
        flowOut = portOut.GetPropValue(MOLEFLOW_VAR)
        feedFrac = self.portIn.GetCompositionValues()
        outFrac = portOut.GetCompositionValues()
        nComps = len(feedFrac)
        inFlows = nComps * [None]
        outFlows = nComps * [None]
        inCalc = 0
        outCalc = 0
        splitsCalc = 0
        
        for i in range(nComps):
            if flowIn != None and feedFrac[i] != None:
                inFlows[i] = flowIn * feedFrac[i]
            if flowOut != None and outFrac[i] != None:
                outFlows[i] = flowOut * outFrac[i]
                
            if splits[i] != None:
                if inFlows[i] != None:
                    outFlows[i] = splits[i] * inFlows[i]
                    outCalc = 1  # have new out results
                elif outFlows[i] != None and splits[i] != 0.0:
                    inFlows[i] = outFlows[i] / splits[i]
                    inCalc = 1  # have new in results
            elif inFlows[i] and outFlows[i] != None:
                splits[i] = outFlows[i] / inFlows[i]
                splitsCalc = 1 # new split calculated

        if outCalc:
            sum = 0.0
            for i in range(nComps):
                if outFlows[i] != None:
                    sum += outFlows[i]
                else:
                    sum = None
                    break
            if sum:
                for i in range(nComps):
                    outFlows[i] /= sum
                portOut.SetCompositionValues(outFlows, CALCULATED_V)
                portOut.SetPropValue(MOLEFLOW_VAR, sum, CALCULATED_V)
                
        if inCalc:
            sum = 0.0
            for i in range(nComps):
                if inFlows[i] != None:
                    sum += inFlows[i]
                else:
                    sum = None
                    break
            if sum:
                for i in range(nComps):
                    inFlows[i] /= sum
                self.portIn.SetCompositionValues(inFlows, CALCULATED_V)
                self.portIn.SetPropValue(MOLEFLOW_VAR, sum, CALCULATED_V)
         
        return splitsCalc
        
    def Solve(self):
        # make sure basic calcs are done
        for port in self.GetPorts(MAT|IN|OUT):
            port.CalcFlows()
        self._balance.DoBalance()
        
        splitValues = []
        for split in self.splits:
            splitValues.append(split.GetValue())
        nComps = len(splitValues)
        if self.CalcSplitFlows(splitValues,self.portOut0):
            for i in range(nComps):
                self.splits[i].SetValue(splitValues[i], CALCULATED_V)
                
        for i in range(nComps):
            if splitValues[i] != None:
                splitValues[i] = 1.0 - splitValues[i]
        
        if self.CalcSplitFlows(splitValues, self.portOut1):
            for i in range(nComps):
                if splitValues[i] != None:
                    self.splits[i].SetValue(splitValues[i], CALCULATED_V)
            
        self._balance.DoBalance()
        while self.FlashAllPorts():
            self._balance.DoBalance()

    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(SimpleComponentSplitter, self)._RemoveFromCloneList(clone, attrNamesToClone)
        dontClone = ["splits", "_balance", "borrowedSplits"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone

class ComponentSplitter(UnitOperations.UnitOperation):
    """
    Combines a SimpleComponentSplitter with a balance to provide a
    unitop which can approximate simple towers etc.
    """
    def __init__(self, initScript = None):
        """
        set up the basic flowsheet
        """
        UnitOperations.UnitOperation.__init__(self, initScript)
        
        self.feedBalance = Balance.BalanceOp()
        self.AddUnitOperation(self.feedBalance, 'FeedBalance')
        
        self.feedBalance.SetParameterValue(NUSTOUT_PAR + Balance.S_MAT, 1)
        self.feedBalance.SetParameterValue(Balance.BALANCETYPE_PAR,
                       Balance.MOLE_BALANCE | Balance.ENERGY_BALANCE)

        self.SetParameterValue(NUSTIN_PAR + Balance.S_MAT, 1)
        self.SetParameterValue(NUSTIN_PAR + Balance.S_ENE, 1)

        self.splitter = SimpleComponentSplitter()
        self.splitter.borrowedSplits = self
        self.AddUnitOperation(self.splitter, 'Splitter')

        for port in self.splitter.GetPorts(MAT|OUT):
            self.BorrowChildPort(port, port.GetName())
                        
        self.ConnectPorts('FeedBalance', OUT_PORT + '0', 'Splitter', IN_PORT)

    def CleanUp(self):
        self.feedBalance = self.splitter = None
        super(ComponentSplitter, self).CleanUp()

    def GetObject(self, desc):
        if desc == 'Splits':
            return self.splitter.splits
        return super(ComponentSplitter, self).GetObject(desc)
        
    def SetParameterValue(self, name, value):
        """
        need to reset borrowed feed ports if they change
        """
        super(ComponentSplitter, self).SetParameterValue(name, value)
        if name == NUSTIN_PAR + Balance.S_MAT:
            self.feedBalance.SetParameterValue(name, value)
            self.ports_mat_IN.clear()
            for port in self.feedBalance.GetPorts(MAT|IN):
                self.BorrowChildPort(port, port.GetName())
            return
        
        if name == NUSTIN_PAR + Balance.S_ENE:
            self.feedBalance.SetParameterValue(name, value)
            self.ports_ene_IN.clear()
            for port in self.feedBalance.GetPorts(ENE|IN):
                self.BorrowChildPort(port, port.GetName())
            return

        if name == NUSTOUT_PAR + Balance.S_ENE:
            self.feedBalance.SetParameterValue(name, value)
            self.ports_ene_OUT.clear()
            for port in self.feedBalance.GetPorts(ENE|OUT):
                self.BorrowChildPort(port, port.GetName())
            return

    def GrabSplitPorts(self):
        """
        Borrow the splitter split ports
        """
        self.ports_sig.clear()       
        for port in self.splitter.GetPorts(SIG|MAT|OUT):
            self.BorrowChildPort(port, port.GetName())
        
    def ThermoChanged(self, thCaseObj):
        """
        intercept this to borrow split ports
        """
        super(ComponentSplitter, self).ThermoChanged(thCaseObj)
        self.GrabSplitPorts()        
            
