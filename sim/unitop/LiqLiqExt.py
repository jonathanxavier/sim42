"""Models a liquid liquid extraction countercurrent cascade

Classes:
LiqLiqEx -- Class for the L L extractor. Inherits from UnitOperation

Remarks:
The main component to be extracted needs to be specified. This should
change soon

"""
from sim.solver import Flowsheet, Ports
from sim.solver.Variables import *
from sim.solver.Messages import MessageHandler
from sim.thermo.VMConstants import *  # this should be replaced with generic import
import UnitOperations, Flash, Balance
from numpy.oldnumeric import *

VALID_UNIT_OPERATIONS = ['LLStage',
                         'LiqLiqEx']

STAGE = 'Stage'
FLASH = 'innerFlash'
MIX = 'innerMixer'

RESETINIT_PAR = "Reset"

class LLStage(UnitOperations.UnitOperation):
    """Class to mix two inlets and iso thermally flash them.
    Inherits from UnitOperation"""

    def __init__(self, initScript = None):
        """Init the flash

        Init Info:
        nuLiqphases = 2
        nuStreamsIn = 2

        """         
        super(LLStage, self).__init__(initScript)

        #Create a separator
        self.innerFlash = innerFlash = Flash.SimpleFlash()        
        self.AddUnitOperation(innerFlash, FLASH)

        #Create a balance
        self.innerMixer = innerMixer = Balance.BalanceOp()
        self.AddUnitOperation(innerMixer, MIX)
        
        #Initialize params
        self.InitializeParameters()
        
        #Share the ports directly
        self.ports_mat_OUT = innerFlash.ports_mat_OUT
        self.ports_mat_IN = innerMixer.ports_mat_IN
        
        #Connect the balance to the separator
        self.ConnectPorts(MIX, OUT_PORT + str(0), FLASH, IN_PORT)
        
    def CleanUp(self):
        self.innerMixer = None
        self.innerFlash = None
        super(LLStage, self).CleanUp()
        
    def AdjustOldCase(self, version):
        """apply any necessary fixups to a recalled operation"""
        super(LLStage, self).AdjustOldCase(version)
        if version[0] < 35:
            #Not really needed
            self.innerFlash = self.GetChildUO(FLASH)
            self.innerMixer = self.GetChildUO(MIX)
            
                
    def InitializeParameters(self):
        innerMixer = self.innerMixer
        innerMixer.SetParameterValue(NUSTIN_PAR + Balance.S_MAT, 2)
        innerMixer.SetParameterValue(NUSTOUT_PAR + Balance.S_MAT, 1)
        innerMixer.SetParameterValue(Balance.BALANCETYPE_PAR, Balance.MOLE_BALANCE)
        innerMixer.SetParameterValue(NULIQPH_PAR, 2)
        
        innerFlash = self.innerFlash
        innerFlash.SetParameterValue(NULIQPH_PAR, 2)
        
            
    def Solve(self):
        """Solve"""
        if not self.ValidateOk(): return None

        flash = self.GetChildUO(FLASH)
        t0 = self.GetPort(IN_PORT + str(0)).GetPropValue(T_VAR)
        t1 = self.GetPort(IN_PORT + str(1)).GetPropValue(T_VAR)

        if t0 == None or t1 == None: return None
        flash.GetPort(IN_PORT).SetPropValue(T_VAR, (t0+t1)/2.0, CALCULATED_V | PARENT_V)

        p0 = self.GetPort(IN_PORT + str(0)).GetPropValue(P_VAR)
        p1 = self.GetPort(IN_PORT + str(1)).GetPropValue(P_VAR)
        if p0 == None or p1 == None: return None
        flash.GetPort(IN_PORT).SetPropValue(P_VAR, (p0+p1)/2.0, CALCULATED_V | PARENT_V)

        return 1

    def ValidateOk(self):
        """True if the uo is ready to be calculated"""          
        if not self.GetThermo(): return 0
        return 1

    def AddObject(self, obj, name, validChange=False):    
        if name == 'NewName':
            if not validChange:
                return
        super(LLStage, self).AddObject(obj, name)
        
        
        
class LiqLiqEx(Flowsheet.Flowsheet):
    """ Models a liquid liquid extraction countercurrent cascade
    
    The feed enters the first stage and the solvent enters the last stage
        
    """
    def __init__(self, initScript = None):
        """Init the extractor

        Init Info:
        nuStages = 5
        maxIter = 40

        """
        #The stages are simulated with a Balance and Flash uops
        super(LiqLiqEx, self).__init__(initScript)
        
        #Assume this at the beginning
        self.UpdateFeedIsLessDense()  #Feed flow is index 0
        self.reconnect = 0        #If self.feedIsLessDense, then it is needed to reconnect ports (i.e. feed flow is index 1 now)
        
        self.LoadPortNames()
        self.InitializeParameters()

    def CleanUp(self):
        super(LiqLiqEx, self).CleanUp()
        
        
    def AdjustOldCase(self, version):
        """apply any necessary fixups to a recalled operation"""
        super(LiqLiqEx, self).AdjustOldCase(version)
        if version[0] < 35:
            self.LoadPortNames()
            if hasattr(self, 'feedIsLessDense'):
                self.topPortOutName = L_PORT + str(self.feedIsLessDense)
                self.botPortOutName = L_PORT + str(not self.feedIsLessDense)
        
    def LoadPortNames(self):
        self.feedTopName = FEED_PORT
        self.feedBotName = SOLV_PORT
        self.drawTopName = EXTR_PORT
        self.drawBotName = RAFF_PORT
        
    def GetClassDefOfStageUsed(self):
        return LLStage
    
    def InitializeParameters(self):
        self.SetParameterValue(NUSTAGES_PAR, 5)
        self.SetParameterValue(MAXITER_PAR, 40)
        
        # Need to set this for ports
        self.SetParameterValue(NULIQPH_PAR, 2)
        
        # Thie will always be 0, but attempting to reset it will clear estimates
        self.SetParameterValue(RESETINIT_PAR, 0)
        
    
    def GetListOfReqParam(self): return (NUSTAGES_PAR, )
    def GetListOfOptParam(self): return (MAXITER_PAR, )

    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        if paramName == RESETINIT_PAR:
            self.ClearEstimates()
            # just in case this doesn't get done in UnitOperations because value
            # is the same
            self.ForgetAllCalculations()
            value = 0
        
        if paramName == NUSTAGES_PAR: 
            value = int(value)
        super(LiqLiqEx, self).SetParameterValue(paramName, value)
        if paramName == NUSTAGES_PAR: 
            self.UpdateStages()
        
    def ValidateParameter(self, paramName, value):
        """Validates the value of a parameter. Return 1 if vaidated properly"""
        if not super(LiqLiqEx, self).ValidateParameter(paramName, value):
            return False
        
        if paramName == NUSTAGES_PAR:
            try: value = int(value)
            except: return False
            if value < 2:
                return False

        return True
    
    def DeleteObject(self, obj):
        if isinstance(obj, UnitOperations.OpParameter):
            paramName = obj.name
            if paramName == NUSTAGES_PAR:
                self.InfoMessage('CantDeleteObject', (paramName, ), MessageHandler.errorMessage)
                return
        super(LiqLiqEx, self).DeleteObject(obj)
        
            
    def UpdateStages(self):
        """Update the amount of stages"""        
        
        #How many stages should be there
        nuStages = self.parameters[NUSTAGES_PAR]
        
        #How many stages are there
        nuChUO = 0
        for uoName in self.chUODict:
            if uoName[:len(STAGE)] == STAGE:
                nuChUO += 1
        
        #Everytihng is fine
        if nuChUO == nuStages:
            return
        
        #Grab the type of stage being used
        StageClass = self.GetClassDefOfStageUsed()
        
        #Initializing
        if nuChUO == 0:
            for i in range(nuChUO, nuStages):
                innerStage = StageClass()
                self.AddUnitOperation(innerStage, STAGE + str(i))
            topStage = self.GetChildUO(STAGE + str(0))
            btmStage = self.GetChildUO(STAGE + str(nuStages-1))
            
            #Make the appropriate borrowing of ports in the feeds
            #This should only be needed once as the top and bottom stage will always stay there
            self.BorrowChildPort(topStage.GetPort(IN_PORT + str(0)), self.feedTopName)
            self.BorrowChildPort(btmStage.GetPort(IN_PORT + str(1)), self.feedBotName)
        
        else:
            topStage = self.GetChildUO(STAGE + str(0))
            btmStage = self.GetChildUO(STAGE + str(nuChUO-1))
            
            #Need to delete stages
            if  nuChUO > nuStages:
                for i in range(nuChUO, nuStages, -1):
                    #Start deleting stages one before the last stage
                    #Should not run into problems because the minimum allowed of stages is 2
                    self.DelUnitOperation(STAGE + str(i - 2))
                #Rename the stage
                btmStage.AddObject(STAGE + str(nuStages-1), 'NewName', True)
                    
            #Need to add stages
            else:
                #Rename the stage
                btmStage.AddObject(STAGE + str(nuStages-1), 'NewName', True)
                
                #Add the stages one before the last one
                for i in range(nuChUO, nuStages):
                    innerStage = StageClass()
                    self.AddUnitOperation(innerStage, STAGE + str(i-1))
                    
            
        #Make the internal connections
        self.ConnectInnerPorts()

    def ConnectInnerPorts(self):
        """Connects the outlet of each stage to the inlet of the corresponding stage"""

        #Grab the type of stage being used
        StageClass = self.GetClassDefOfStageUsed()
        
        nuStages = self.parameters[NUSTAGES_PAR]
        fld = self.feedIsLessDense
        
        #Make sure there is no problems with changes due to feedIsLessDense
        topStage = self.GetChildUO(STAGE + str(0))
        btmStage = self.GetChildUO(STAGE + str(nuStages-1))

        #Fix at top stage if needed
        #Note that the extract port can change from Liq0 to Liq1 depending on density of the compounds
        extPort = topStage.GetPort(self.topPortOutName)
        stagePort = topStage.GetPort(self.botPortOutName)
        if extPort.IsPortConnected():
            #If the extract port is connected to another stage then diconnect
            if isinstance(extPort.GetConnection().GetParent(), StageClass):
                extPort.Disconnect()
        if stagePort.IsPortConnected():
            #If a stage port is connected to something different than a stage, then
            #assume that the extract should be connected there
            if not isinstance(stagePort.GetConnection().GetParent(), StageClass):
                extPort.ConnectTo(stagePort.GetConnection())

        #Fix at btm stage if needed
        #Note that the raffinate port can change from Liq0 to Liq1 depending on density of the compounds
        raffPort = btmStage.GetPort(self.botPortOutName)
        stagePort = btmStage.GetPort(self.topPortOutName)
        if raffPort.IsPortConnected():
            #If the extract port is connected to another stage then diconnect
            if isinstance(extPort.GetConnection().GetParent(), StageClass):
                raffPort.Disconnect()
        if stagePort.IsPortConnected():
            #If a stage port is connected to something different than a stage, then
            #assume that the extract should be connected there
            if not isinstance(stagePort.GetConnection().GetParent(), StageClass):
                raffPort.ConnectTo(stagePort.GetConnection())
                
        for i in range(nuStages - 1):   #Connect equilibrium stages
            self.ConnectPorts(STAGE + str(i), self.botPortOutName, STAGE + str(i + 1), IN_PORT + str(0))
            self.ConnectPorts(STAGE + str(i + 1), self.topPortOutName, STAGE + str(i), IN_PORT + str(1))
        
        #Now make sure the ports are properly borrowed out
        tempPort = self.GetPort(self.drawTopName)
        if not tempPort is extPort:
            #Note that it only gets deleted here because it is borrowed 
            #(i.e. the real owner of the port still keeps the port)
            if tempPort: self.DeletePort(tempPort)
            self.BorrowChildPort(extPort, self.drawTopName)
            
        tempPort = self.GetPort(self.drawBotName)
        if not tempPort is raffPort:
            #Note that it only gets deleted here because it is borrowed 
            #(i.e. the real owner of the port still keeps the port)
            if tempPort: self.DeletePort(tempPort)
            self.BorrowChildPort(raffPort, self.drawBotName)
        
        self.reconnect = 0
        
    def UpdateFeedIsLessDense(self):
        """Checks if the feed has a lower density than the solvent.

           If self.feedIsLessDense changes its value, then flag to reconnect ports

        """
        thCaseObj = self.GetThermo()
        if not thCaseObj:
            feedIsLessDense = 1
            self.topPortOutName = L_PORT + str(feedIsLessDense)
            self.botPortOutName = L_PORT + str(not feedIsLessDense)
            self.feedIsLessDense = feedIsLessDense
            return
        
        try:
            #Mass density of feed
            port = self.GetPort(self.feedTopName)
            p = port.GetPropValue(P_VAR)
            t = port.GetPropValue(T_VAR)
            x = port.GetCompositionValues()
            
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            vals0 = thAdmin.GetProperties(prov, case, (T_VAR,t), (P_VAR, p), 1, x, (MASSDEN_VAR,))
        
            #Mass density of solvent
            port = self.GetPort(self.feedBotName)
            p = port.GetPropValue(P_VAR)
            t = port.GetPropValue(T_VAR)
            x = port.GetCompositionValues()
            vals1 = thAdmin.GetProperties(prov, case, (T_VAR,t), (P_VAR, p), 1, x, (MASSDEN_VAR,))
            
            feedIsLessDense = vals0[0] < vals1[0]
            if self.feedIsLessDense != feedIsLessDense: self.reconnect = 1
            else: self.reconnect = 0
            self.topPortOutName = L_PORT + str(feedIsLessDense)
            self.botPortOutName = L_PORT + str(not feedIsLessDense)
            self.feedIsLessDense = feedIsLessDense
        
        except:
            feedIsLessDense = 1
            self.topPortOutName = L_PORT + str(feedIsLessDense)
            self.botPortOutName = L_PORT + str(not feedIsLessDense)
            self.feedIsLessDense = feedIsLessDense
            return
        
            
    def Solve(self):
        """Solve"""
        
        self.FlashAllPorts()
        if not self.ValidateOk(): return None
        self.UpdateFeedIsLessDense()
        fld = self.feedIsLessDense
        if self.reconnect: self.ConnectInnerPorts()
        super(LiqLiqEx, self).Solve()  # get everything available
        
        # check to see if already solved
        nuStages = self.parameters[NUSTAGES_PAR]
        topStage = self.GetChildUO(STAGE + str(0))
        btmStage = self.GetChildUO(STAGE + str(nuStages-1))
        ZExtract = topStage.GetPort(self.topPortOutName).GetPropValue(ZFACTOR_VAR)
        ZRaffinate = btmStage.GetPort(self.botPortOutName).GetPropValue(ZFACTOR_VAR)
        if ZExtract == None or ZRaffinate == None:
            # nope - initialize the stages and try again
            if not self.InitStages(): return None
            super(LiqLiqEx, self).Solve()
        
        return 1

    def ValidateOk(self):
        """True if the uo is ready to be calculated"""
        
        if self.IsForgetting(): return 0
        if self.parentUO and self.parentUO.IsForgetting(): return 0
        if self.parameters[NUSTAGES_PAR] <= 0: return 0
        if not self.GetThermo(): return 0
        
        feedPort = self.GetPort(self.feedTopName)
        solvPort = self.GetPort(self.feedBotName)
        nuStages = self.parameters[NUSTAGES_PAR]
        
        if feedPort.GetNuKnownProps(CANFLASH_PROP) < 2: return 0
        if feedPort.GetNuKnownProps(EXTENSIVE_PROP) < 1: return 0
        if not feedPort.GetCompounds().AreValuesReady(): return 0
        
        if solvPort.GetNuKnownProps(CANFLASH_PROP) < 2: return 0
        if solvPort.GetNuKnownProps(EXTENSIVE_PROP) < 1: return 0
        if not solvPort.GetCompounds().AreValuesReady(): return 0
        
        return 1

    def InitStages(self):
        """Init values

        Assumes T and P axist and they change linearly through stages

        """
        thCaseObj = self.GetThermo()
        if not thCaseObj: return 0
        nuStages = self.parameters[NUSTAGES_PAR]
        fld = self.feedIsLessDense
        
        #Grab the type of stage being used
        StageClass = self.GetClassDefOfStageUsed()        
        
        #Stuff from feed
        fPort = self.GetPort(self.feedTopName)
        fCmp = array(fPort.GetCompositionValues(), Float)
        (fT, fP, fMol) = (fPort.GetPropValue(T_VAR), fPort.GetPropValue(P_VAR), fPort.GetPropValue(MOLEFLOW_VAR))
        fFlow = fMol * fCmp
        
        #Stuff from solvent
        sPort = self.GetPort(self.feedBotName)
        sCmp= array(sPort.GetCompositionValues(), Float)
        (sT, sP, sMol) = (sPort.GetPropValue(T_VAR), sPort.GetPropValue(P_VAR), sPort.GetPropValue(MOLEFLOW_VAR))
        sFlow = sMol * sCmp

        #Calculate as if there was only one overall stage and do estimates
        tempOverallStage = StageClass()
        
        try:
            tempOverallStage.SetThermo(thCaseObj)
    
            #Define in0Port
            in0Port = tempOverallStage.GetPort(IN_PORT + str(0))        
            in0Port.GetCompounds().SetValues(fCmp, FIXED_V)
            in0Port.GetProperty(T_VAR).SetValue(fT, FIXED_V)
            in0Port.GetProperty(P_VAR).SetValue(fP, FIXED_V)        
            in0Port.GetProperty(MOLEFLOW_VAR).SetValue(fMol, FIXED_V)   
    
            #Define in1Port
            in1Port = tempOverallStage.GetPort(IN_PORT + str(1))
            in1Port.GetCompounds().SetValues(sCmp, FIXED_V)
            in1Port.GetProperty(T_VAR).SetValue(sT, FIXED_V)
            in1Port.GetProperty(P_VAR).SetValue(sP, FIXED_V)        
            in1Port.GetProperty(MOLEFLOW_VAR).SetValue(sMol, FIXED_V)   
    
            #Solve manually (there's no Flowsheet to take care of details)
            tempOverallStage.GetChildUO(MIX).Solve()    #Balance
            tempOverallStage.Solve()                    #Pass T and P to flash
            for port in tempOverallStage.GetChildUO(MIX).GetPorts():
                port.UpdateConnection()            
            #tempOverallStage.FlashAllPorts()            #
            tempOverallStage.GetChildUO(FLASH).Solve()
            
            #Get vals for estimates, and clean up tempOverallStage
            (out0Port, out1Port) = (tempOverallStage.GetPort(self.botPortOutName), tempOverallStage.GetPort(L_PORT+ str(fld)))
            (out0Cmp, out1Cmp) = (array(out0Port.GetCompositionValues(), Float), array(out1Port.GetCompositionValues(), Float))
            (out0Mol, out1Mol) = (out0Port.GetPropValue(MOLEFLOW_VAR), out1Port.GetPropValue(MOLEFLOW_VAR))
            (out0Flow, out1Flow) = (out0Cmp * out0Mol, out1Cmp * out1Mol)
                
        except:
            #Hack so it doesn't break the therm under use
            tempOverallStage.thermoAdmin = thCaseObj.thermoAdmin
            tempOverallStage.SetThermo(None)
            tempOverallStage.CleanUp()
            tempOverallStage.thermoAdmin = None
            return 0
        #Hack so it doesn't break the therm under use
        tempOverallStage.thermoAdmin = thCaseObj.thermoAdmin
        tempOverallStage.SetThermo(None)
        tempOverallStage.CleanUp()
        tempOverallStage.thermoAdmin = None

        #Estimate which liquid is being extracted the most and
        #estimate how much liquid is being extracted per stage        
        #Based in definition of Kd and E shown in pg 240 "Separation Process Principles"; Seader, et al
        lstLiqRem = []
        nuCmps = len(fFlow)
        liqRemaining = zeros((nuCmps, nuStages), Float)
        for cmpNo in range(nuCmps):
            try:
                Kd = (out1Flow[cmpNo] / (out1Mol-out1Flow[cmpNo])) / (out0Flow[cmpNo] / (out0Mol-out0Flow[cmpNo]))
            except:
                Kd = 0.0
            E = Kd * (sMol-sFlow[cmpNo]) / (fMol-fFlow[cmpNo])
            powSeries = multiply.accumulate(ones(nuStages) * E)
            denom = sum(powSeries) + 1
            numer = concatenate(([1.], powSeries[:-1])) #Insert a 1 at the beginning and get rid of last number
            numer = add.accumulate(numer)
            fracRemaining = numer/denom            
            fracRemaining = fracRemaining[-1::-1]       #Just reverse values
            liqRemaining[cmpNo] = fracRemaining * fFlow[cmpNo]
        
        #Guess all the inner flows for the solvent phase
        listT = self.CreateLinearDistList(nuStages + 1, fT, sT)
        listP = self.CreateLinearDistList(nuStages + 1, fP, sP)
        
        for i in range(nuStages-1):
            stageTo = self.chUODict[STAGE + str(i)]
            in1ToPort = stageTo.GetPort(IN_PORT + str(1))
            in1ToPort.SetPropValue(T_VAR, listT[i+1], FIXED_V | ESTIMATED_V)
            in1ToPort.SetPropValue(P_VAR, listP[i+1], FIXED_V | ESTIMATED_V)
             
        for i in range(nuStages - 1, 0, -1):
            stage = self.chUODict[STAGE + str(i)]
            stageTo = self.chUODict[STAGE + str(i - 1)]
            in1Port = stage.GetPort(IN_PORT + str(1))
            in1ToPort = stageTo.GetPort(IN_PORT + str(1))
            
            in1Mol = in1Port.GetPropValue(MOLEFLOW_VAR) #Mol in solvent phase
            in1Cmp = array(in1Port.GetCompositionValues(), Float)
            #Flow going into next stage is same flow with some addition of the liquid moving
            in1ToFlow = in1Mol * in1Cmp
            amountMoved = liqRemaining[:, i-1] - liqRemaining[:, i]  #[:, i] = all cmps, stage i
            in1ToFlow = in1ToFlow + amountMoved
            
            # Estimates are not passed through connections
            in1ToPort.GetCompounds().SetValues(in1ToFlow, FIXED_V | ESTIMATED_V)
            in1ToPort.SetPropValue(MOLEFLOW_VAR, sum(in1ToFlow), FIXED_V | ESTIMATED_V)
        return 1

    def ClearEstimates(self):
        """
        removes the estimates provide by InitStage and solution so new ones will be created
        """
        nuStages = self.parameters[NUSTAGES_PAR]
        for i in range(nuStages - 1, 0, -1):
            stage = self.chUODict[STAGE + str(i)]
            stageM1 = self.chUODict[STAGE + str(i - 1)]
            solventPort = stage.GetPort(IN_PORT + str(1))
            solventPortM1 = stageM1.GetPort(IN_PORT + str(1))
            tempComp = solventPort.GetCompositionValues()
            for j in range(len(tempComp)):
                tempComp[j] = None
            solventPortM1.SetCompositionValues(tempComp, UNKNOWN_V)
            solventPortM1.SetPropValue(T_VAR, None, UNKNOWN_V)
            solventPortM1.SetPropValue(P_VAR, None, UNKNOWN_V)
            solventPortM1.SetPropValue(MOLEFLOW_VAR, None, UNKNOWN_V)
        
    def CreateLinearDistList(self, nuVals, bound1, bound2):
        """Create a set of values distributed linearly

        nuVals -- Number of values desired
        bound1 -- Boundary 1
        bound2 -- Boundary 2

        """              
        vals = []
        delta = (bound2 - bound1) / (nuVals - 1)
        for i in range(nuVals): vals.append(delta * i + bound1)
        return vals

