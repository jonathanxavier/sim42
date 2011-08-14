"""Models a heater

Classes:
HeaterCooler -- Common class for the heater/cooler. Inherits from UnitOperation
Heater - models heater with in and out material streams and an energy inlet
Cooler - models cooler with in and out material streams and an energy outlet
HeatExchanger - models a counter current or co current two sided heat exchanger
HeatExchangerUA - models a multisided heat exchanger with a fixed amount of two sides
MultiSidedHeatExchangerOp - models a multisided heat exchanger solving simultaneous equations

"""

import math, string, copy, operator

import numpy
from numpy import array, float, zeros, ones, int, sum, argmin, concatenate
from numpy import transpose, repeat, reshape, take, put, absolute, where
from numpy.linalg import solve as solve_linear_equations, inv as inverse, det as determinant


import UnitOperations
import Balance, Tower, Custom
from sim.solver import Error
from sim.solver.Variables import *
from sim.solver import EquationSolver
from sim.solver.Error import SimError
from sim.solver.Messages import MessageHandler


VALID_UNIT_OPERATIONS = ['Heater',
                         'Cooler',
                         'HeatExchanger',
                         'HeatExchangerUA',
                         'MultiSidedHeatExchangerOp']

REFERENCE_SIDE_PAR = 'ReferenceSide'
NUSIDES_PAR = 'NumberSides'
NUSEGMENTS_PAR = 'NumberSegments'
COUNTER_CURRENT_PAR = 'IsCounterCurrent'
IGNORE_UA_PAR = 'IgnoreUA'
FINDPH_CHANGE_PAR = 'TrackPhaseChange'
SEGMENTSBASE_PAR = 'BaseForSegments'
INSTALLEDPROFILES_PAR = 'InstalledProfiles'


CUSTOM_SOLVE_OBJ = 'CustomSolve'

SIDE_BASE_NAME = 'side'
HT_BASE_NAME = 'heatTransfer'

#Init modes
SCRATCH_INIT = Tower.SCRATCH_INIT
RESTART_INIT = Tower.RESTART_INIT
LASTCONV_INIT = Tower.LASTCONV_INIT

#Some constants
MF_IDX = 2
H1_IDX = 1
H0_IDX = 0


LOCALEMPTY_VAL = 1.0E-100

class HeaterCooler(UnitOperations.UnitOperation):
    """Base class for the heater and cooler. Inherits from UnitOperation"""
    def __init__(self, isHeater, initScript = None):
        """If isHeater is true, then it is heater, else it is cooler

        Init Info:
        """          
        super(HeaterCooler, self).__init__(initScript)

        self.balance = Balance.Balance(Balance.MOLE_BALANCE | Balance.ENERGY_BALANCE)
        
        inPort = self.CreatePort(MAT|IN, IN_PORT)
        outPort = self.CreatePort(MAT|OUT, OUT_PORT)
        dpPort = self.CreatePort(SIG, DELTAP_PORT)
        dpPort.SetSignalType(DELTAP_VAR)

        inPort.SetLocked(True)
        outPort.SetLocked(True)
        dpPort.SetLocked(True)
        
        if isHeater:
            qPort = self.CreatePort(ENE|IN, IN_PORT + 'Q')
            self.balance.AddInput((inPort, qPort))
            self.balance.AddOutput(outPort)
        else:
            qPort = self.CreatePort(ENE|OUT, OUT_PORT + 'Q')
            self.balance.AddInput(inPort)
            self.balance.AddOutput((outPort, qPort))
            
        
        self.storedProfiles = {}
        self.SetParameterValue(NUSEGMENTS_PAR, 1)
        
    def Solve(self):
        """Solve"""
        
        self.storedProfiles = {}
        
        ## if not self.ValidateOk(): return None
        self.FlashAllPorts()  # make sure anything that can be flashed has been

        self.balance.DoBalance()
        
        hadPressure = self.CalcDP()
        didBalance = 0
        while self.FlashAllPorts():
            self.balance.DoBalance()
            didBalance = 1
            
        if not didBalance:  # make sure at least one last balance is done
            self.balance.DoBalance()
        
        if not hadPressure:
            self.CalcDP()
        return 1

    def CalcDP(self):
        """
        Calculate side pressure drop
        """
        ## should have proper pressure drop calculation
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)
        dpPort = self.GetPort(DELTAP_PORT)
        pIn = inPort.GetPropValue(P_VAR)
        pOut = outPort.GetPropValue(P_VAR)
        dp = dpPort.GetValue()
        if pOut == None:
            if dp != None and pIn != None:
                outPort.SetPropValue(P_VAR, pIn - dp, CALCULATED_V)
            else:
                return 0
        elif pIn == None:
            if dp != None:
                inPort.SetPropValue(P_VAR, pOut + dp, CALCULATED_V)
            else:
                return 0
        else:
            dpPort.SetPropValue(DELTAP_VAR, pIn - pOut, CALCULATED_V)
        return 1
        
    def GetObject(self, desc):
        #import wingdbstub
        #f = open(r'C:\temp.out', 'a')
        #f.write('GetObject: ' + self.GetPath() + ' ' + desc + '\n')
        obj = super(HeaterCooler, self).GetObject(desc)
        if obj: return obj
        
        prof = self.storedProfiles.get(desc, None)
        nuSegs = self.GetParameterValue(NUSEGMENTS_PAR)
        if nuSegs == None: nuSegs = 1
        #f.write('StoredProfile: ' + str(prof)  + '\n')
        if prof != None: 
           if len(prof) - 1 == nuSegs:
               return prof
        
        inPort = self.GetPort(IN_PORT)
        outPort = self.GetPort(OUT_PORT)
        qPort = self.GetPort(IN_PORT + 'Q')
        if not qPort:
            qPort = self.GetPort(OUT_PORT + 'Q')
        
        if desc == P_VAR or desc == H_VAR:
            try:
                varIn = inPort.GetPropValue(desc)
                varOut = outPort.GetPropValue(desc)
                if nuSegs and varIn != None and varOut != None:
                    prof =  EquationSolver.CreateLinearDistArray(nuSegs+1, varIn, varOut)
                    self.storedProfiles[desc] = prof
                    return prof
                return None
            except:
                return None
            
        elif desc == ENERGY_VAR:
            try:
                q = qPort.GetValue()
                if q != None and nuSegs:
                    qPerSeg = q/nuSegs
                    prof = ones(nuSegs+1, Float) * qPerSeg
                    #The first value stands for lossed which are set to 0.0 for now
                    prof[0] = 0.0
                    self.storedProfiles[desc] = prof
                    return prof
                return None
            except:
                return None
            
        elif desc == ENERGY_VAR + 'Acum':
            #Call recursively to get ENERGY
            try:
                qProf = self.GetObject(ENERGY_VAR)
                if qProf != None:
                    prof = Numeric.absolute(Numeric.add.accumulate(qProf))
                    self.storedProfiles[desc] = prof
                    return prof
                return None
            except:
                return None
        else:
            try:
                phase = OVERALL_PHASE
                #f.write('Almost in: "' + str(desc)  + '"\n')
                if not ' ' in desc:
                    propName = desc
                    tempDesc = desc.split('_', 1)
                    if len(tempDesc) == 2:
                        if tempDesc[0] == Tower.TOWER_VAP_PHASE:
                            phase = VAPOUR_PHASE
                            propName = tempDesc[1]
                        elif tempDesc[0] == Tower.TOWER_LIQ_PHASE:
                            phase = LIQUID_PHASE
                            propName = tempDesc[1]
                    #f.write('Calling: "' + str(propName)  + '"\n')
                    prof = self.Profile(propName, phase)
                    #f.write('FinalProfile: "' + str(prof)  + '"\n')
                    return prof
            except:
                #f.write('Error: "'  + '"\n')
                return None

    def Profile(self, propName, phase=OVERALL_PHASE):
        """Returns a profile"""
        
        nuSegments = self.GetParameterValue(NUSEGMENTS_PAR)
        
        #Build the key name of the profile
        if phase == OVERALL_PHASE:
            keyPropName = propName
        elif phase == VAPOUR_PHASE:
            keyPropName = ('%s_%s' %(Tower.TOWER_VAP_PHASE, propName))
        elif phase == LIQUID_PHASE:
            keyPropName = ('%s_%s' %(Tower.TOWER_LIQ_PHASE, propName))
            
        #Return the stored profile if available
        storedProfiles = self.storedProfiles
        profile = storedProfiles.get(keyPropName, None)
        if profile != None and len(profile) == nuSegments + 1:
            return profile
        
        #Get the thermo
        thCaseObj = self.GetThermo()
        if not thCaseObj: return None
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        
        #Has to be requesting a supported property
        if propName != VPFRAC_VAR and propName != MASSVPFRAC_VAR:
           if not propName in thAdmin.GetPropertyNames(prov): 
               return None
        profile = None
        
        #Get the h and p profiles
        hProf = self.GetObject(H_VAR)
        pProf = self.GetObject(P_VAR)
        if hProf == None or pProf == None: return None
        
        #Get composition
        fracs = self.GetPort(IN_PORT).GetCompositionValues()
        if not fracs or None in fracs: return None
        nuCmps = len(fracs)
        
        
        #A flash will be performed therefore we should make sure we get as much info in one shot as possible
        ignoreNames = (P_VAR, H_VAR, ENERGY_VAR + 'Acum', ENERGY_VAR, VPFRAC_VAR, MASSVPFRAC_VAR)
        propNames = []
        if not propName in ignoreNames:
            propNames.append(propName)
        
        #Always calculate molecular weight for the bulk and vapour
        if len(propNames) == 0:
            #At least do MW
            propNames.append(MOLEWT_VAR)
        elif propName != MOLEWT_VAR:
            mw = storedProfiles.get(MOLEWT_VAR, None)
            if mw == None or len(mw) != nuSegments + 1:
                #Get MW just in case
                propNames.append(MOLEWT_VAR)
            else:
                mw = storedProfiles.get('%s_%s' %(Tower.TOWER_VAP_PHASE, MOLEWT_VAR))
                if mw == None or len(mw) != nuSegments + 1:
                    propNames.append(MOLEWT_VAR)
            
            
        #Build a list of all the properties that should get calculated int he flash call
        #The parameter Profiles helps to predefine the profiles that will be requested
        calcProfiles = self.GetParameterValue(INSTALLEDPROFILES_PAR)
        if isinstance(calcProfiles, str) or isinstance(calcProfiles, unicode):
            knownNames = storedProfiles.keys()
            for item in calcProfiles.split(' '):
                #get the name of the property
                item = item.split('_', 1)[-1]
                
                #add it to the list if necessary
                if (not item in ignoreNames) and (not item in propNames):
                    if (not item in knownNames) or (len(storedProfiles[item]) != nuSegments + 1):
                        propNames.append(item)
                    
                
        #Dimension arrays
        nuProps = len(propNames)
        profilesBulk = zeros((nuProps, nuSegments+1), Float)
        profilesVap = zeros((nuProps, nuSegments+1), Float)
        profilesLiq = zeros((nuProps, nuSegments+1), Float)
        profilesVapFrac = zeros(nuSegments+1, Float)
        
        
        #define composition bulk
        cmps = CompoundList(None)
        for frac in fracs:
            prop = BasicProperty(FRAC_VAR)
            prop.SetValue(frac, FIXED_V)
            cmps.append(prop)
            
            
        #Do flash calculations
        myName = self.GetName()
        txtPropNames = str(propNames)
        props = MaterialPropertyDict()
        nuSolids = self.NumberSolidPhases()
        for i in range(nuSegments+1):
            props[P_VAR].SetValue(pProf[i], FIXED_V)
            props[H_VAR].SetValue(hProf[i], FIXED_V)
            self.InfoMessage('CalculatingProfile', (myName, i, txtPropNames))
            results = thAdmin.Flash(prov, case, cmps, props, 1, propNames, nuSolids=nuSolids)
            for nuProp in range(nuProps):
                profilesBulk[nuProp][i] = results.bulkProps[[nuProp]]
                profilesVap[nuProp][i] = results.phaseProps[0][[nuProp]]
                profilesLiq[nuProp][i] = results.phaseProps[1][[nuProp]]
                profilesVapFrac[i] = results.phaseFractions[0]
        self.InfoMessage('DoneProfile', myName)
                       
        #Store all calculated properties
        for nuProp in range(nuProps):
            storedProfiles[propNames[nuProp]] = array(profilesBulk[nuProp, :], Float)
            storedProfiles['%s_%s' %(Tower.TOWER_VAP_PHASE, propNames[nuProp])] = array(profilesVap[nuProp, :], Float)
            storedProfiles['%s_%s' %(Tower.TOWER_LIQ_PHASE, propNames[nuProp])] = array(profilesLiq[nuProp, :], Float)
        
        #Store Vap fraction
        vf = storedProfiles[VPFRAC_VAR] = array(profilesVapFrac, Float)
        
        #Store Mass vap fraction
        vapmw = storedProfiles['%s_%s' %(Tower.TOWER_VAP_PHASE, MOLEWT_VAR)]
        bulkmw = storedProfiles[MOLEWT_VAR]
        storedProfiles[MASSVPFRAC_VAR] = vf * vapmw / bulkmw
            
        
        return storedProfiles.get(keyPropName, None)   
                
    
    def SetParameterValue(self, paramName, value):
        #Trap some parameters that will not triger a solve
        #The logic behind these parameters is that they do not affect the final results
        if paramName in ['Profiles', INSTALLEDPROFILES_PAR, NUSEGMENTS_PAR]:
            if not self.ValidateParameter(paramName, value):
                raise Error.SimError('CantSetParameter', (paramName, str(value)))
                return 0
            self.parameters[paramName] = value
            return 1
        
        super(HeaterCooler, self).SetParameterValue(paramName, value)
        
    def AdjustOldCase(self, version):
        super(HeaterCooler, self).AdjustOldCase(version)
        if version[0] < 44:
            if not self.GetParameterValue(NUSEGMENTS_PAR):
                self.parameters[NUSEGMENTS_PAR] = 1
            if not hasattr(self, 'storedProfiles'):
                self.storedProfiles = {}
    def _CloneCreate(self):
        """By default just clone with the __class__ call"""
        if self.GetPort(IN_PORT + 'Q') != None:
            clone = self.__class__(1)
        else:
            clone = self.__class__(0)
        return clone

    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(HeaterCooler, self)._RemoveFromCloneList(clone, attrNamesToClone)
        dontClone = ["balance"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone

class Heater(HeaterCooler):
    """Heater - unit operation having in and out material ports
    and inlet energy port"""

    def __init__(self, initScript = None):
        """Just call super class __init__ with isHeater = 1
        """          
        HeaterCooler.__init__(self, 1, initScript)

class Cooler(HeaterCooler):
    """Cooler - unit operation having in and out material ports
    and outlet energy port"""

    def __init__(self, initScript = None):
        """Just call super class __init__ with isHeater = 0
        """          
        HeaterCooler.__init__(self, 0, initScript)

class HeatExchanger(UnitOperations.UnitOperation):
    """A simple two sided heat exchanger with InH -> OutH on one side
    and InC -> OutC on the other.  For delta T purposes, side H is the hot
    side.
    Four signal ports are available:
        DELTAP_PORT + 'H' for the hot side pressure drop
        DELTAP_PORT + 'C' for the cold side pressure drop
        DELTAT_PORT + 'HI for the temperature approach at the hot inlet end
        DELTAT_PORT + 'HO' for the temperature approach at the hot outlet end
    
    Parameters are:
        COUNTER_CURRENT_PAR - 1 for counter current (default) 0 for cocurrent
    """
    
    def __init__(self, initScript=None):
        """Init heat exchanger - build it from Heater, Cooler and Set operations
        """
        UnitOperations.UnitOperation.__init__(self, initScript)
        
        self.coldSide = Heater()
        self.AddUnitOperation(self.coldSide, 'ColdSide')
        self.hotSide = Cooler()
        self.AddUnitOperation(self.hotSide, 'HotSide')
        
        # connect the energy ports
        self.ConnectPorts('HotSide',OUT_PORT + 'Q','ColdSide',IN_PORT + 'Q')
        
        # export the flow ports
        self.coldPortIn = self.coldSide.GetPort(IN_PORT)
        self.hotPortIn = self.hotSide.GetPort(IN_PORT)
        self.coldPortOut = self.coldSide.GetPort(OUT_PORT)
        self.hotPortOut = self.hotSide.GetPort(OUT_PORT)

        self.BorrowChildPort(self.coldPortIn, IN_PORT + 'C')
        self.BorrowChildPort(self.hotPortIn, IN_PORT + 'H')
        self.BorrowChildPort(self.coldPortOut, OUT_PORT + 'C')
        self.BorrowChildPort(self.hotPortOut, OUT_PORT + 'H')
        
        # export the delta P ports
        self.ports_sig[DELTAP_PORT + 'H'] = self.hotSide.GetPort(DELTAP_PORT)
        self.ports_sig[DELTAP_PORT + 'C'] = self.coldSide.GetPort(DELTAP_PORT)
        
        # create Delta T Ports
        self.deltaTHI = self.CreatePort(SIG, DELTAT_PORT + 'HI')
        self.deltaTHI.SetSignalType(DELTAT_VAR)
        self.deltaTHO = self.CreatePort(SIG, DELTAT_PORT + 'HO')
        self.deltaTHO.SetSignalType(DELTAT_VAR)
        
        # default parameters
        self.SetParameterValue(COUNTER_CURRENT_PAR, 1)

        self.UA = self.CreatePort(SIG, UA_PORT)
        self.UA.SetSignalType(UA_VAR)
        self.lastLMTD = None
        self.tinydt = 0.00001 #Breaking point for using LMDT or MDT when dt1 -> dt2

    def CleanUp(self):
        self.coldSide = self.hotSide = None
        self.coldPortIn = self.hotPortIn = self.coldPortOut = self.hotPortOut = None
        self.deltaTHI = self.deltaTHO = self.UA = None
        super(HeatExchanger, self).CleanUp()
    
    def GetListOfReqParam(self): return (COUNTER_CURRENT_PAR)
    def SetParameterValue(self, paramName, value):
        """
        short cut setting of child parameters
        NULIQPH_PAR + 'H' - number of liquid phases on hot side
        NULIQPH_PAR + 'C' - number of liquid phases on cold side
        """
        UnitOperations.UnitOperation.SetParameterValue(self, paramName, value)
        
        if paramName == NULIQPH_PAR + 'H':
            self.hotSide.SetParameterValue(NULIQPH_PAR, value)
        elif paramName == NULIQPH_PAR + 'C':
            self.coldSide.SetParameterValue(NULIQPH_PAR, value)
        
                
    def calcDeltaT(self, hotPort, coldPort, dtPort):
        hotT = hotPort.GetPropValue(T_VAR)
        dt = dtPort.GetValue()
        if dt != None:
            if hotT != None:
                
                coldPort.SetPropValue(T_VAR, hotT - dt, CALCULATED_V | PARENT_V)
            else:
                coldT = coldPort.GetPropValue(T_VAR)
                if coldT != None:
                    hotPort.SetPropValue(T_VAR, coldT + dt, CALCULATED_V | PARENT_V)
        elif hotT != None:
            coldT = coldPort.GetPropValue(T_VAR)
            if coldT != None:
                dt = hotT - coldT
                dtPort.SetValue(dt, CALCULATED_V)
        return dt

    def SolveForDeltas(self):
        """Return dt1, dt2, LMTD to make the code compatible with older code"""
        dt1 = None
        dt2 = None
        LMTD = None
        
        isCounterCurrent = self.GetParameterValue(COUNTER_CURRENT_PAR)
        if isCounterCurrent:
            dt1 = self.calcDeltaT(self.hotPortIn, self.coldPortOut, self.deltaTHI)
            dt2 = self.calcDeltaT(self.hotPortOut, self.coldPortIn, self.deltaTHO)
        else:
            dt1 = self.calcDeltaT(self.hotPortIn, self.coldPortIn, self.deltaTHI)
            dt2 = self.calcDeltaT(self.hotPortOut, self.coldPortOut, self.deltaTHO)
            
        if dt1 != None and dt2 != None:
            if dt1>= 0.0 and dt2 >= 0.0:
                if abs(dt1-dt2) < self.tinydt or dt1*dt2 <= self.tinydt:
                    #Use average
                    LMTD = (dt1 + dt2) / 2
                else:
                    #Use ln
                    LMTD = (dt2 - dt1) / math.log(dt2/dt1)
                self.unitOpMessage = ('OK', )   
            else:
                self.unitOpMessage = ('TemperatureCross', (dt1, dt2, self.GetPath()))
                raise Error.SimError('TemperatureCross', (dt1, dt2, self.GetPath()))                
                    
        elif dt1 != None:
            if dt1 < 0.0:
                self.unitOpMessage = ('TemperatureCross', (dt1, dt2, self.GetPath()))
                raise Error.SimError('TemperatureCross', (dt1, dt2, self.GetPath()))                  
            
        elif dt2 != None:
            if dt2 < 0.0:
                self.unitOpMessage = ('TemperatureCross', (dt1, dt2, self.GetPath()))
                raise Error.SimError('TemperatureCross', (dt1, dt2, self.GetPath()))               
        
        return dt1, dt2, LMTD
            
    
    def Solve(self):
        """Just need to to delta T stuff since children handle everything else"""

        portQ = self.hotSide.GetPort(OUT_PORT + 'Q')

        Q = portQ.GetValue()
        UA = self.UA.GetValue()
        LMTD = None
        
        dt1, dt2, LMTD = self.SolveForDeltas()
        isCounterCurrent = self.GetParameterValue(COUNTER_CURRENT_PAR)
                      
            
        #Case for T known. Put values in UA and Q. This will raise consistency errors if needed
        if LMTD != None:
            if Q != None:
                UA = Q / LMTD
                self.UA.SetValue(UA, CALCULATED_V)
            elif UA != None:
                Q = UA * LMTD
                portQ.SetValue(Q, CALCULATED_V|PARENT_V)
                
        #Anything new that can be done will depend on UA spec
        #Solve if UA and a T in each side is known 
        elif UA != None:
            
            #Get F
            F, f = self.hotPortIn.GetPropValue(MOLEFLOW_VAR), self.coldPortIn.GetPropValue(MOLEFLOW_VAR)
            
            #Get T
            T1, T2 = self.hotPortIn.GetPropValue(T_VAR), self.hotPortOut.GetPropValue(T_VAR)
            t1, t2 = self.coldPortIn.GetPropValue(T_VAR), self.coldPortOut.GetPropValue(T_VAR)
                
            #If three T known and Q and U known but not the second flow
            if Q != None:
                lstT = [T1, T2, t1, t2]
                nuUnkT = lstT.count(None)
                if nuUnkT == 1:
                    nuUnkF = [F, f].count(None)
                    if nuUnkF == 1:
                        #Let's try finding the missing T from LMTD known
                        LMTD = Q/UA
                        idxUnkT = lstT.index(None)
                        u = EquationSolver.Unknowns()
                        numMethodSetings = EquationSolver.NumericMethodSettings(self)
                        numMethodSetings.solveMethod = EquationSolver.SECANT
                        
                        #T1
                        isSpec = True
                        if T1 == None: T1, isSpec = T2, False
                        unkVar = EquationSolver.SolverVariable('T1', T1, T1, isSpec, 100.0, 0.001, 1E30)
                        u.AddUnknown(unkVar)
                        
                        #T2
                        isSpec = True
                        if T2 == None: T2, isSpec = T1, False
                        unkVar = EquationSolver.SolverVariable('T2', T2, T2, isSpec, 100.0, 0.001, 1E30)
                        u.AddUnknown(unkVar)
                        
                        #t1
                        isSpec = True
                        if t1 == None: t1, isSpec = t2, False
                        unkVar_t1 = EquationSolver.SolverVariable('t1', t1, t1, isSpec, 100.0, 0.001, 1E30)
                        
                        #t2
                        isSpec = True
                        if t2 == None: t2, isSpec = t1, False
                        unkVar_t2 = EquationSolver.SolverVariable('t2', t2, t2, isSpec, 100.0, 0.001, 1E30)
                        
                        if isCounterCurrent:
                            u.AddUnknown(unkVar_t2)
                            u.AddUnknown(unkVar_t1)
                        else:
                            u.AddUnknown(unkVar_t1)
                            u.AddUnknown(unkVar_t2)
                            
                        #LMTD
                        isSpec = True
                        unkVar = EquationSolver.SolverVariable('LMTD', LMTD,  LMTD, isSpec, 100.0, 0.001, 1E30)
                        u.AddUnknown(unkVar)
            
                        x, rhs, converged = EquationSolver.SolveNonLinearEquations(self, u, numMethodSetings, [])
                        if converged:
                            foundT = x[idxUnkT]
                            if idxUnkT == 0: self.hotPortIn.SetPropValue(T_VAR, foundT, CALCULATED_V|PARENT_V)
                            elif idxUnkT == 1: self.hotPortOut.SetPropValue(T_VAR, foundT, CALCULATED_V|PARENT_V)
                            elif idxUnkT == 2:
                                if isCounterCurrent:
                                    foundT = x[idxUnkT+1]
                                    self.coldPortIn.SetPropValue(T_VAR, foundT, CALCULATED_V|PARENT_V)
                                else:
                                    self.coldPortIn.SetPropValue(T_VAR, foundT, CALCULATED_V|PARENT_V)
                            elif idxUnkT == 3:
                                if isCounterCurrent:
                                    foundT = x[idxUnkT-1]
                                    self.coldPortOut.SetPropValue(T_VAR, foundT, CALCULATED_V|PARENT_V)
                                else:
                                    self.coldPortOut.SetPropValue(T_VAR, foundT, CALCULATED_V|PARENT_V)
                            dt1, dt2, LMTD = self.SolveForDeltas()
                        return
                    
            #Dummy loop for breaking if needed
            stay = 1
            while stay:
                stay = 0 #Make sure it will not iterate
                
                #Upper case for hot strem. Lower case for cold stream

                #Nothing can be done if extensive vars are unknown
                #F, f = self.hotPortIn.GetPropValue(MOLEFLOW_VAR), self.coldPortIn.GetPropValue(MOLEFLOW_VAR)
                Cmps, cmps = self.hotPortIn.GetCompounds(), self.coldPortIn.GetCompounds()
                if F == None or f == None:
                    break
                if not Cmps.AreValuesReady() or not cmps.AreValuesReady():
                    break
                else:
                    Fracs, fracs = Cmps.GetValues(), cmps.GetValues()

                #No pressures, no solution
                P1, P2 = self.hotPortIn.GetPropValue(P_VAR), self.hotPortOut.GetPropValue(P_VAR)
                p1, p2 = self.coldPortIn.GetPropValue(P_VAR), self.coldPortOut.GetPropValue(P_VAR)
                if None in (P1, P2, p1, p2):
                    break

                #Get T
                #T1, T2 = self.hotPortIn.GetPropValue(T_VAR), self.hotPortOut.GetPropValue(T_VAR)
                #t1, t2 = self.coldPortIn.GetPropValue(T_VAR), self.coldPortOut.GetPropValue(T_VAR)

                
                #Nothing can be done if two T are unknown in the same side
                if T1 == None:
                    if T2 == None:
                        break
                    else:
                        T = T2
                        H = self.hotPortOut.GetPropValue(H_VAR)
                        P = P2
                        PIter = P1
                        TIsIn = 0
                        
                else:
                    T = T1
                    H = self.hotPortIn.GetPropValue(H_VAR)
                    P = P1
                    PIter = P2
                    TIsIn = 1

                if t1 == None:
                    if t2 == None:
                        break
                    else:
                        t = t2
                        h = self.coldPortOut.GetPropValue(H_VAR)
                        p = p2
                        pIter = p1
                        tIsIn = 0
                else:
                    t = t1
                    h = self.coldPortIn.GetPropValue(H_VAR)
                    p = p1
                    pIter = p2
                    tIsIn = 1

                if TIsIn and tIsIn:
                    if T < t:
                        self.unitOpMessage = ('HotTLowerThanColdT', (T, t, self.GetPath()))
                        raise Error.SimError('HotTLowerThanColdT', (T, t, self.GetPath()))   
                    
                hotThermo = self.hotSide.GetThermo()
                thAdmin, Prov, Case = hotThermo.thermoAdmin, hotThermo.provider, hotThermo.case
                coldThermo = self.coldSide.GetThermo()
                prov, case = coldThermo.provider, coldThermo.case
                hotInfo = (T, P, H, F, Fracs, TIsIn, thAdmin, Prov, Case)
                coldInfo = (t, p, h, f, fracs, tIsIn, thAdmin, prov, case)
                scaleFactor = self.deltaTHI.GetType().scaleFactor
                TIter, conv = self.SolveForQ(UA, hotInfo, coldInfo, PIter, pIter, scaleFactor)
                if conv:
                    if TIsIn: self.hotPortOut.SetPropValue(T_VAR, TIter, CALCULATED_V|PARENT_V)
                    else: self.hotPortIn.SetPropValue(T_VAR, TIter, CALCULATED_V|PARENT_V)
                else:
                    self.unitOpMessage = ('CouldNotConvergeUA', (UA, self.GetPath()))
                    self.InfoMessage('CouldNotConvergeUA', (UA, self.GetPath()))   

                dt1, dt2, LMTD = self.SolveForDeltas()
                
                    
    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        """In this case, is is only used for finding a T for LMTD knownn"""
        
        S1T1 = x[0]
        S1T2 = x[1]
        S2T1 = x[2]
        S2T2 = x[3]
        LMTD = x[4]
        scaleT = 100.0
        
        #LMTD - CalcLMTD = 0
        rhs[eqnNo] = (LMTD - self.CalcLMTD(S1T1, S2T1, S1T2, S2T2)) / scaleT
        eqnNo += 1

        #Eqn's for known vars
        for idx in range(len(x)):
            if isFix[idx]:
                rhs[eqnNo] = (x[idx] - initx[idx]) / scaleT
                eqnNo += 1

        return eqnNo
        

    def CalcLMTD(self, S1T1, S2T1, S1T2, S2T2):
        """Calculates LMTD"""
        dt1 = S1T1 - S2T1
        dt2 = S1T2 - S2T2 + 1E-30

        if (dt1 * dt2 < 0.0):
            #set the smaller dt to 1e-30
            if (abs(dt1) > abs(dt2)):
                #dt2 is smaller
                dt2 = ((dt1)/abs(dt1)) * 1E-30
            else:
                dt1 = ((dt2)/abs(dt2)) * 1E-30

        elif (dt1 * dt2 == 0.0):
            dt1 = 1E-30
            dt2 = dt1

        if (abs(dt1 - dt2) < 0.0000000001):
            dt1 = dt1 + 0.0000000001

        return (dt1 - dt2) / (math.log(dt1 / dt2) + 1E-30)
    
    
    def SolveForQ(self, UA, hotInfo, coldInfo, PIter, pIter, scaleFactor):
        """Runs Newton Raphson mehod to find a Q from two temps knwon

        UA = UA
        hotInfo = (T, P, H, F, Fracs, TIsIn) . TIsIn = true if the T is known in the inlet
        coldInfo = (t, p, h, f, fracs, tIsIn) . tIsIn = true if the t is known in the inlet
        PIter = P hot side of unknown T
        pIter = p cold side of unknown t
        scaleFactor = scaleFactor of Q

        returns - Tuple with (Q, ConvergedBoolean)
        
        """

        #Uses a sligthly modified version of the bisection method and a quasi newton method to converge

        maxIter = 40
        tolerance = 0.000001
        tinydt = self.tinydt
        minStep = 0.00000001
        largedt = 1000
        damp = 0.9
        switch = 0.01   #Paremeter for switching to newton raphson
        bigError = 1000


        #Target = newQ - QIter = 0

        #Load vars
        T, P, H, F, Fracs, TIsIn, thAdmin, Prov, Case = hotInfo
        t, p, h, f, fracs, tIsIn, thAdmin, prov, case = coldInfo

        #Sign

        if TIsIn: S = -1
        else: S = 1
        if tIsIn: s = 1
        else: s = -1

        def GetHXDT():
            if self.GetParameterValue(COUNTER_CURRENT_PAR):
                if TIsIn:
                    if tIsIn:
                        dt1 = T - tIter
                        dt2 = TIter - t
                    else:
                        dt1 = T - t
                        dt2 = TIter - tIter
                else:
                    if tIsIn:
                        dt1 = TIter - tIter
                        dt2 = T - t
                    else:
                        dt1 = TIter - t
                        dt2 = T - tIter
            else:
                if TIsIn:
                    if tIsIn:
                        dt1 = T - t
                        dt2 = TIter - tIter
                    else:
                        dt1 = T - tIter
                        dt2 = TIter - t
                else:
                    if tIsIn:
                        dt1 = TIter - t
                        dt2 = T - tIter                        
                    else:
                        dt1 = TIter - tIter
                        dt2 = T - t
                        
            
            if dt1>= 0.0 and dt2 >= 0.0:
                if abs(dt1-dt2) < tinydt or dt1*dt2 <= tinydt:
                    #Use average
                    return (dt1 + dt2) / 2
                else:
                    #Use ln
                    return (dt2 - dt1) / math.log(dt2/dt1)
            else:
                return None

            
        #Before anything, check if the last solution is good enough for Newton
        newton = 0
        if self.lastLMTD != None:
            LMTD = self.lastLMTD
            Q = UA * LMTD
            HIter = H + S*Q*3.6/F   #Conversion from W to kJ/h
            hIter = h + s*Q*3.6/f   #Conversion from W to kJ/h
            try:
                TIter = thAdmin.GetProperties(Prov, Case, (P_VAR, PIter), (H_VAR, HIter), OVERALL_PHASE, Fracs, [T_VAR])
                tIter = thAdmin.GetProperties(prov, case, (P_VAR, pIter), (H_VAR, hIter), OVERALL_PHASE, fracs, [T_VAR])
                TIter = TIter[0]
                tIter = tIter[0]
                newLMTD = GetHXDT()
                if newLMTD != None: 
                    error = (newLMTD - LMTD) / scaleFactor
                    if abs(error) < switch:
                        newton = 1
                    
                    #Newton could be done. Get a crude differential
                    dx = 0.01*scaleFactor
                    LMTD = self.lastLMTD + dx
                    Q = UA * LMTD
                    HIter = H + S*Q*3.6/F   #Conversion from W to kJ/h
                    hIter = h + s*Q*3.6/f   #Conversion from W to kJ/h
                    TIter = thAdmin.GetProperties(Prov, Case, (P_VAR, PIter), (H_VAR, HIter), OVERALL_PHASE, Fracs, [T_VAR])
                    tIter = thAdmin.GetProperties(prov, case, (P_VAR, pIter), (H_VAR, hIter), OVERALL_PHASE, fracs, [T_VAR])
                    TIter = TIter[0]
                    tIter = tIter[0]
                    newLMTD = GetHXDT()
                    if newLMTD != None: 
                        newError = (newLMTD - LMTD) / scaleFactor
                        dF = newError - error
                        dx_dF = dx/dF
                        curr = self.lastLMTD
                    else:
                        newton = 0
                        
                        
            except:
                newton = 0
                
        if not newton:
            #Estimate some boundaries for LMTD
            if not self.GetParameterValue(COUNTER_CURRENT_PAR):
                #Minimum LMTD
                minLMTD = abs(T-t)/2
                
                #Max LMTD
                if (TIsIn and tIsIn) or (not TIsIn and not tIsIn):
                    maxLMTD = abs(T-t)
                else:
                    #Something relatively large
                    maxLMTD = 2*abs(T-t)
            else:
                if (TIsIn and tIsIn):
                    minLMTD = tinydt
                    maxLMTD = abs(T - t)
                elif (not TIsIn and not tIsIn):
                    minLMTD = abs(T-t)
                    #Something relatively large
                    maxLMTD = 3*abs(T-t)
                else:
                    minLMTD = abs(T-t)/2
                    #Something relatively large
                    maxLMTD = 2*abs(T-t)
                    
            #Test if values can be obtained in between the boundary
            error = None
            while 1:
                step = (maxLMTD-minLMTD)/2.0
                LMTD = minLMTD + step
                Q = UA * LMTD
                HIter = H + S*Q*3.6/F   #Conversion from W to kJ/h
                hIter = h + s*Q*3.6/f   #Conversion from W to kJ/h
                try:
                    TIter = thAdmin.GetProperties(Prov, Case, (P_VAR, PIter), (H_VAR, HIter), OVERALL_PHASE, Fracs, [T_VAR])
                    tIter = thAdmin.GetProperties(prov, case, (P_VAR, pIter), (H_VAR, hIter), OVERALL_PHASE, fracs, [T_VAR])
                    TIter = TIter[0]
                    tIter = tIter[0]
                    newLMTD = GetHXDT()
                    if newLMTD != None: 
                        error = (newLMTD - LMTD) / scaleFactor
                    
                    #The flash was calculated properly. Now lets make sure the error doesn't get reduced in the max boundary
                    if error == None:
                        error = bigError
                    break
                
                except:
                    #Max is too big, reduce it a little
                    maxLMTD *= damp
                
                if maxLMTD <= tinydt:
                    #Couldnt even initialize
                    self.lastLMTD = None
                    return None, 0
            
    
            #Pick three points evenly distributed within temporary boundaries 
            step *= 0.5
            curr = LMTD                 #Current accepted value of LMTD
            try1 = LMTD + step          #A step lower than LMTD
            try2 = LMTD - step          #A step greater than LMTD. Just in case there si something weird with bisection
            
            
        infoBisect = None
        canSwitch = 1
        iter = 0
        while iter <= maxIter:
            iter += 1

            lastCurr = curr
                  
            #Use quasi newton when close to solution
            if newton:
                adjustment = -error * dx_dF
                stepLength = 1.0
                
                while 1:
                    actualAdjustment = stepLength * adjustment
                    LMTD = curr + actualAdjustment
                    Q = UA * LMTD
                    HIter = H + S*Q*3.6/F   #Conversion from W to kJ/h
                    hIter = h + s*Q*3.6/f   #Conversion from W to kJ/h
                    try:
                        TIter = thAdmin.GetProperties(Prov, Case, (P_VAR, PIter), (H_VAR, HIter), OVERALL_PHASE, Fracs, [T_VAR])
                        tIter = thAdmin.GetProperties(prov, case, (P_VAR, pIter), (H_VAR, hIter), OVERALL_PHASE, fracs, [T_VAR])
                        TIter = TIter[0]
                        tIter = tIter[0]
                        newLMTD = GetHXDT()
                        if newLMTD != None: 
                            newError = (newLMTD - LMTD) / scaleFactor
                            if abs(newError) < abs(error):
                                break
                
                    finally:
                        # errors did not go down - back down step size
                        if stepLength < minStep:
                            # step size too small - bail
                            break
            
                        stepLength /= 4.0
                        
                if abs(newError) > abs(error):
                    if infoBisect != None:
                        #Back to bisecting
                        (iter, curr, try1, try2, newError, error, step) = infoBisect
                    else:
                        break
                else:
                    # update rate of change
                    dF = newError-error
                    dx = actualAdjustment
                    dx_dF = dx / dF
                    curr = newLMTD
                    
            #Far from solution. Do bisection
            else:
                
                step *= 0.5
                newError = None
                
                #Try the first guess
                LMTD = try1
                Q = UA * LMTD
                HIter = H + S*Q*3.6/F   #Conversion from W to kJ/h
                hIter = h + s*Q*3.6/f   #Conversion from W to kJ/h
                try:
                    TIter = thAdmin.GetProperties(Prov, Case, (P_VAR, PIter), (H_VAR, HIter), OVERALL_PHASE, Fracs, [T_VAR])
                    tIter = thAdmin.GetProperties(prov, case, (P_VAR, pIter), (H_VAR, hIter), OVERALL_PHASE, fracs, [T_VAR])
                    TIter = TIter[0]
                    tIter = tIter[0]
                    newLMTD = GetHXDT()
                    if newLMTD != None: 
                        newError = (newLMTD - LMTD) / scaleFactor
    
                    if newError == None:
                        stay = 1
                    elif abs(newError) > abs(error):
                        stay = 1
                    else:
                        stay = 0
                        curr = LMTD
                        if newError * error <= 1.0:
                            #Sign was crossed, give a smaller step from last solution
                            if curr > try1:
                                try1 = LMTD + step
                                try2 = LMTD - step
                            else:
                                try1 = LMTD - step
                                try2 = LMTD + step
                                
                        else:
                            #Error was reduced, but sign didn't change.
                            if curr > try1:
                                try1 = LMTD - step
                                try2 = LMTD + step
                            else:
                                try1 = LMTD + step
                                try2 = LMTD - step
                                
                except:
                    stay = 1
    
                if stay:
                    #Try second guess
                    LMTD = try2
                    Q = UA * LMTD
                    HIter = H + S*Q*3.6/F   #Conversion from W to kJ/h
                    hIter = h + s*Q*3.6/f   #Conversion from W to kJ/h
                    try:
                        TIter = thAdmin.GetProperties(Prov, Case, (P_VAR, PIter), (H_VAR, HIter), OVERALL_PHASE, Fracs, [T_VAR])
                        tIter = thAdmin.GetProperties(prov, case, (P_VAR, pIter), (H_VAR, hIter), OVERALL_PHASE, fracs, [T_VAR])
                        TIter = TIter[0]
                        tIter = tIter[0]
                        newLMTD = GetHXDT()
                        if newLMTD != None: 
                            newError = (newLMTD - LMTD) / scaleFactor
    
                        if newError == None:
                            stay = 1
                        elif abs(newError) > abs(error):
                            stay = 1
                        else:
                            stay = 0
                            curr = LMTD
                            if newError * error <= 1.0:
                                #Sign was crossed, give a smaller step from last solution
                                if curr > try1:
                                    try1 = LMTD + step
                                    try2 = LMTD - step
                                else:
                                    try1 = LMTD - step
                                    try2 = LMTD + step
                                    
                            else:
                                #Error was reduced, but sign didn't change.
                                if curr > try1:
                                    try1 = LMTD - step
                                    try2 = LMTD + step
                                else:
                                    try1 = LMTD + step
                                    try2 = LMTD - step
                    except:
                        stay = 1
                        
                    if stay:
                        #New guesses will be closer to current value
                        try1 = curr - step
                        try2 = curr + step
                        newError = error
                        
                #Check if it can switch to Newton
                if abs(newError) < switch and iter > 3 and canSwitch == 1:
                    dx = curr - lastCurr
                    dF = newError - error
                    if abs(dx) > tinydt and abs(dF) > tinydt/scaleFactor:
                        newton = 1
                        canSwitch = 0
                        dx_dF = dx/dF
                        infoBisect = (iter, curr, try1, try2, newError, error, step)
                        
                #If step is too small leave
                if step < minStep:
                    # step size too small - bail
                    break

        
            if abs(newError/tolerance) <=1.0:
                self.lastLMTD = LMTD
                return TIter, 1

            error = newError

            
        #Just return the last value used flagged as not converged.
        #Do not raise any errors or messages
        self.lastLMTD = None
        return TIter, 0


    def AdjustOldCase(self, version):
        super(HeatExchanger, self).AdjustOldCase(version)
        if version[0] < 13:
            port = self.GetPort(UA_PORT)
            if not port:
                self.UA = self.CreatePort(SIG, UA_PORT)
                self.UA.SetSignalType(UA_VAR)
                self.lastLMTD = None
                self.tinydt = 0.00001 #Breaking point for using LMDT or MDT when dt1 -> dt2
                try:
                    self.Solve()
                except:
                    pass  # should already be messages


class _Side(EquationSolver.EquationBasedOp):
    
    def __init__(self, parentOp, parentObj):
        super(_Side, self).__init__()

        self._parentOp = parentOp

        self._portIn = self.CreatePort(IN|MAT, IN_PORT)
        self._portIn.SetLocked(True)
        
        self._portOut = self.CreatePort(OUT|MAT, OUT_PORT)
        self._portOut.SetLocked(True)
        
        self._portDP = self.CreatePort(SIG, DELTAP_PORT)
        self._portDP.SetLocked(True)
        self._portDP.SetSignalType(DELTAP_VAR)
        
        self._portDT = self.CreatePort(SIG, DELTAT_PORT)
        self._portDT.SetLocked(True)
        self._portDT.SetSignalType(DELTAT_VAR)
        
        self._parCountCur = None
        self._parIsReference = False
        
        self.storedProfiles = {}
        
        self.TArray = None
        self.PArray = None
        self.HArray = None
        self.QArray = None
        self.molarFlow = None
        
        self.moleFlowIdx = None
        self.TIndex = None
        self.PIndex = None
        self.HIndex = None
        self.QIndex = None
        
        
        
    def CleanUp(self):
        self._parentOp = self._portIn = self._portOut = None
        self._portDP = self._portDT = None
        self.storedProfiles = {}
        super(_Side, self).CleanUp()
        
    def UpdateStructure(self):
        super(_Side, self).UpdateStructure()

        #Parameters. Expect a dictionary
        params = self._parentOp.GetCorrespondingParameters(self)
        
        parCountCur = params.get(COUNTER_CURRENT_PAR, None)
        if self._parCountCur != None and parCountCur != None:
            if parCountCur != self._parCountCur:
                self._parentOp.ClearConvResults()
        self._parCountCur = parCountCur

        myIdx = self._parentOp.GetIndexOfSide(self)
        refIdx = self._parentOp.GetParameterValue(REFERENCE_SIDE_PAR)
        if myIdx == refIdx:
            self._parIsReference = True
        else:
            self._parIsReference = False 
        
    def GetIndexOfVariables(self):
        """Gets the dictionary with the index of each var"""
        return self._varIdxVars
        
    def GetIsCoCurrent(self):
        """Gets if the side is co current with respect to the base side"""
        return not self._parCountCur

    def GetIsCounterCurrent(self):
        """Gets if the side is counter current with respect to the base side"""
        return self._parCountCur

    def GetIsReference(self):
        """True if this side is the reference side for co or counter current"""
        return self._parIsReference

    def GetNumberOfSegments(self):
        """Number of segments that the side is divided on"""
        return self._parentOp.GetNumberOfSegments()
        

    def Solve(self):
        """Solve what can"""
        #return
        self.FlashAllPorts()

        #Share mole flows and fractions
        #self._portIn.SharePropWith(self._portOut, MOLEFLOW_VAR)
        #self._portIn.SharePropWith(self._portOut, MASSFLOW_VAR)
        #self._portIn.ShareComposition(self._portOut)
        
        #Calc delta T along side
        self.CalcDeltaT(self._portIn, self._portOut, self._portDT)
          
        #Solve for DP
        PIn = self._portIn.GetLocalValue(P_VAR)
        POut = self._portOut.GetLocalValue(P_VAR)
        dP = self._portDP.GetLocalValue()
        if None != PIn and None != POut:
            self._portDP.SetPropValue(DELTAP_VAR, PIn-POut, CALCULATED_V)
        elif None != PIn and None != dP:
            self._portOut.SetPropValue(P_VAR, PIn-dP, CALCULATED_V)
        elif None != POut and None != dP:
            self._portIn.SetPropValue(P_VAR, POut+dP, CALCULATED_V)
        elif None != PIn and None != POut:
            self._portIn.SetPropValue(DELTAP_VAR, POut+dP, CALCULATED_V)
        else:
            #Can't solve
            return False
        
        self.FlashAllPorts()
        
        #Calc delta T along side
        self.CalcDeltaT(self._portIn, self._portOut, self._portDT)
        

        self.scaleFactorT = 100.0  #self._portIn.GetProperty(T_VAR).GetType().scaleFactor
        self.scaleFactorH = 3000.0 #self._portIn.GetProperty(H_VAR).GetType().scaleFactor
        self.scaleFactorF = 10.0   #self._portIn.GetProperty(MOLEFLOW_VAR).GetType().scaleFactor
        
        return True        
    
    def CalcDeltaT(self, port1, port2, dtPort):
        T1 = port1.GetLocalValue(T_VAR)
        T2 = port2.GetLocalValue(T_VAR)
        dt = dtPort.GetLocalValue()
        if not None in (T1, T2, dt): return dt
        if dt != None:
            if T1 != None:
                port2.SetPropValue(T_VAR, T1 - dt, CALCULATED_V)
            else:
                T2 = port2.GetPropValue(T_VAR)
                if T2 != None:
                    port1.SetPropValue(T_VAR, T2 + dt, CALCULATED_V)
        elif T1 != None:
            T2 = port2.GetPropValue(T_VAR)
            if T2 != None:
                dt = T1 - T2
                dtPort.SetValue(dt, CALCULATED_V)
        return dt 
        
    def PrepareForSolve(self):
        """Prepares and calculates info that is not taken in the simultaneous equations. Returns False if can not solve"""
        
        #self.TArray = None
        #self.PArray = None
        #self.HArray = None
        #self.QArray = None
        retVal = True
        
        PIn = self._portIn.GetPropValue(P_VAR)
        POut = self._portOut.GetPropValue(P_VAR)
        if PIn == None or POut == None: retVal = False
        
        cmps = self._portIn.GetCompositionValues()
        if None in cmps: retVal = False #All compositions must be known

        #Get thermo
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: retVal = False
        
        return retVal


    def AssignResults(self, vals):
        """Assign the results into the appropriate ports"""
        #Overwrite everything for consistency checks
        isCoCurrent = self.GetIsCoCurrent()
        
        pIn = self._portIn
        pOut = self._portOut
        
        if isCoCurrent:
            h = self.HArray[0]
            pIn.SetPropValue(H_VAR, h, CALCULATED_V|PARENT_V)
        else:
            h = self.HArray[-1]
            pIn.SetPropValue(H_VAR, h, CALCULATED_V|PARENT_V)
                
            
        if isCoCurrent:
            h = self.HArray[-1]
            pOut.SetPropValue(H_VAR, h, CALCULATED_V|PARENT_V)
        else:
            h = self.HArray[0]
            pOut.SetPropValue(H_VAR, h, CALCULATED_V|PARENT_V)
                  
            
        mf = self.molarFlow
        pIn.SetPropValue(MOLEFLOW_VAR, mf, CALCULATED_V|PARENT_V)
        pOut.SetPropValue(MOLEFLOW_VAR, mf, CALCULATED_V|PARENT_V)            
             
            
    def GetArray(self, type):
        """Returns an array of values of a given type"""
        if type == T_VAR:
            return self.TArray
        elif type == ENERGY_VAR:
            #Solution algorith keeps it in kJ/h !!
            return self.QArray  #In kJ/h
        elif type == P_VAR:
            return self.PArray
        elif type == H_VAR:
            return self.HArray
        
    def LoadUnknowns(self, u):
        """Load the unknown variables. Returns False is there are not enough known variables"""
        #Load vars in a convenient way
        
        parent = self._parentOp
        nuSegments = self.GetNumberOfSegments()
        isCoCurrent = self.GetIsCoCurrent()
        findPhCh = self._parentOp.findPhCh
        initMode = parent.initMode
        
        portIn = self._portIn
        TIn = portIn.GetPropValue(T_VAR)
        PIn = portIn.GetPropValue(P_VAR)
        HIn = portIn.GetPropValue(H_VAR)
        molarFlow = portIn.GetPropValue(MOLEFLOW_VAR)
        fracs = portIn.GetCompositionValues()
        self.fracs = fracs
        
        portOut = self._portOut
        TOut = portOut.GetPropValue(T_VAR)
        POut = portOut.GetPropValue(P_VAR)
        HOut = portOut.GetPropValue(H_VAR)
        
        if None in fracs or None in (PIn, POut): return False
        
        
        TArray = zeros(nuSegments+1, Float)
        PArray = zeros(nuSegments+1, Float)
        HArray = zeros(nuSegments+1, Float)
        QArray = zeros(nuSegments, Float)
        #self.TArray = TArray = zeros(nuSegments+1, Float)
        #self.PArray = PArray = zeros(nuSegments+1, Float)
        #self.HArray = HArray = zeros(nuSegments+1, Float)
        #self.QArray = QArray = zeros(nuSegments, Float)
        
        if findPhCh:
            #There could be changes in length of profiles which are not part of solver. 
            #Prepare for them
            self.storedProfiles[T_VAR] = None
            self.storedProfiles[P_VAR] = None
            self.storedProfiles[H_VAR] = None
            self.storedProfiles[ENERGY_VAR] = None
            
            
        #Keep track of the index where the unknwons are put in
        self.moleFlowIdx = None
        self.TIndex = zeros(nuSegments+1, Int)
        self.HIndex = zeros(nuSegments+1, Int)
        self.QIndex = zeros(nuSegments, Int)

        myParent = self._parentOp
        myIdxInMyParent = myParent.GetIndexOfSide(self)
        self.idxInParent = myIdxInMyParent
            
        #The values obtained from the ports could be None. 
        #Use estimates from the parents which should have values everywhere
        tempTOut, tempTIn = parent._estTOutVec[myIdxInMyParent], parent._estTInVec[myIdxInMyParent]
        
        #Lets do specs with enthalpies
        tempHOut, tempHIn = HOut, HIn
        if HIn == None:
            tempHIn = self.GetEnthalpy(PIn, tempTIn, fracs)
        if HOut == None:
            tempHOut = self.GetEnthalpy(POut, tempTOut, fracs)
        
        dH = (tempHOut - tempHIn) / nuSegments
        dT = (tempTOut - tempTIn) / nuSegments
        dP = (POut - PIn) / nuSegments        
        
        #Add molar flow
        name = 'MolarFlow_Side' + str(myIdxInMyParent)
        isSpec = True
        if molarFlow == None:
            if initMode == SCRATCH_INIT or self.molarFlow == None:
                molarFlow = parent._estMoleFlowVec[myIdxInMyParent]
                initMode = SCRATCH_INIT
            else:
                molarFlow = self.molarFlow
            isSpec = False
        self.molarFlow = molarFlow
        scaleFactorF = self.scaleFactorF
        tempUnkVar = EquationSolver.SolverVariable(name, molarFlow, molarFlow, isSpec, scaleFactorF)
        self.moleFlowIdx = u.AddUnknown(tempUnkVar) #Returns the index where the unk was put

        
        scaleFactorT = self.scaleFactorT
        scaleFactorH = self.scaleFactorH
        scaleFactorQ = scaleFactorF*scaleFactorH
        self.scaleFactorQ = scaleFactorQ
        if initMode != SCRATCH_INIT:
            try:
                TArray[:] = self.TArray[:]
                HArray[:] = self.HArray[:]
                QArray[:] = self.QArray[:]
            except:
                initMode = parent.initMode = SCRATCH_INIT
            
        for i in range(nuSegments+1):
            #Setup P, T depending on coCurrent/counterCurrent
            
            nameT = 'T_Side' + str(myIdxInMyParent) + '_Seg_' + str(i)
            isSpecT = False
            
            nameH = 'H_Side' + str(myIdxInMyParent) + '_Seg_' + str(i)
            isSpecH = False

            if (isCoCurrent):
                if initMode == SCRATCH_INIT:
                    HArray[i] = tempHIn + dH * i
                if i == 0:
                    if HIn != None: 
                        isSpecH = True  #It was in the port already
                        HArray[i] = HIn
                        if TIn: TArray[i] = TIn
                elif i == nuSegments:
                    if HOut != None: 
                        isSpecH = True  #It was in the port already
                        HArray[i] = HOut
                        if TOut: TArray[i] = TOut
                PArray[i] = PIn + dP * i
                
            else:
                if initMode == SCRATCH_INIT:
                    HArray[i] = tempHOut - dH * i
                if i == 0:
                    if HOut != None: 
                        isSpecH = True  #It was in the port already
                        HArray[i] = HOut
                        if TOut: TArray[i] = TOut
                elif i == nuSegments:
                    if HIn != None: 
                        isSpecH = True  #It was in the port already
                        HArray[i] = HIn
                        if TIn: TArray[i] = TIn
                PArray[i] = POut - dP * i


            #Initialize Enthalpies
            if initMode == SCRATCH_INIT:
                TArray[i] = self.GetTemperature(PArray[i], HArray[i], fracs)

            #Setup the unknowns
            tempUnkVar = EquationSolver.SolverVariable(nameT, TArray[i], TArray[i], isSpecT, scaleFactorT)
            self.TIndex[i] = u.AddUnknown(tempUnkVar)  #Returns the index where the unk was put
            
            tempUnkVar = EquationSolver.SolverVariable(nameH, HArray[i], HArray[i], isSpecH, scaleFactorH)
            self.HIndex[i] = u.AddUnknown(tempUnkVar)  #Returns the index where the unk was put

            
            if (i > 0):
                #Do this balance directly. Do not use last converged results
                nameQ = 'Q_Side' + str(myIdxInMyParent) + '_Seg_' + str(i-1)
                isSpecQ = False
                QArray[i-1] = (-HArray[i-1] + HArray[i]) * molarFlow
                tempUnkVar = EquationSolver.SolverVariable(nameQ, QArray[i-1], QArray[i-1], isSpecQ, scaleFactorQ)
                self.QIndex[i-1] = u.AddUnknown(tempUnkVar)  #Returns the index where the unk was put

        if findPhCh:
            #Prepare for doing full flashes
            self.propDict = MaterialPropertyDict()

            #Get composition and load it into BasicProperties
            self.cmpDict = compounds = CompoundList(None)
            for cmpIdx in range(len(fracs)):
                prop = BasicProperty(FRAC_VAR)
                prop.SetValue(fracs[cmpIdx], FIXED_V)
                compounds.append(prop)
            compounds.Normalize()
                
        self.molarFlow = molarFlow
        self.TArray = TArray[:]
        self.HArray = HArray[:]
        self.QArray = QArray[:]
        self.PArray = PArray[:]
                
        return True


    def GetEnthalpy(self, P, T, fracs):
        """Gets enthalpy for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        inProp1 = [P_VAR, P]
        inProp2 = [T_VAR, T]
        propList = [H_VAR]
        vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, OVERALL_PHASE, fracs, propList)
        return vals[0]

    def GetTemperature(self, P, H, fracs):
        """Gets T for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        inProp1 = [P_VAR, P]
        inProp2 = [H_VAR, H]
        propList = [T_VAR]
        vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, OVERALL_PHASE, fracs, propList)
        return vals[0]
    
    def GetPropertiesFromPH(self, P, H, fracs, props, phase=OVERALL_PHASE):
        """Gets T for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        inProp1 = [P_VAR, P]
        inProp2 = [H_VAR, H]
        vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, props)
        return vals

    def GetPropertiesFromPT(self, P, T, fracs, props, phase=OVERALL_PHASE):
        """Gets T for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        inProp1 = [P_VAR, P]
        inProp2 = [T_VAR, T]
        vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, phase, fracs, props)
        return vals
    

    def PHFlash(self, P, H, fracs, props=(T_VAR,)):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        self.propDict[P_VAR].SetValue(P, FIXED_V)
        self.propDict[H_VAR].SetValue(H, FIXED_V)
        self.propDict[VPFRAC_VAR].SetValue(None, FIXED_V)
        nuSolids = self.NumberSolidPhases()
        results = thAdmin.Flash(prov, case, self.cmpDict, self.propDict, 2, props, nuSolids=nuSolids)
        return results
    
    def PTFlash(self, P, T, fracs, props=(T_VAR,)):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        self.propDict[P_VAR].SetValue(P, FIXED_V)
        self.propDict[T_VAR].SetValue(T, FIXED_V)
        self.propDict[VPFRAC_VAR].SetValue(None, FIXED_V)
        nuSolids = self.NumberSolidPhases()                    
        results = thAdmin.Flash(prov, case, self.cmpDict, self.propDict, 2, props, nuSolids=nuSolids)
        return results    
    
        
    def BubPtFlash(self, P, fracs, props=(T_VAR, H_VAR)):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        self.propDict[P_VAR].SetValue(P, FIXED_V)
        self.propDict[H_VAR].SetValue(None, FIXED_V)
        self.propDict[VPFRAC_VAR].SetValue(0.0, FIXED_V)
        nuSolids = self.NumberSolidPhases()                    
        results = thAdmin.Flash(prov, case, self.cmpDict, self.propDict, 2, props, nuSolids=nuSolids)
        return results
    
    def DewPtFlash(self, P, fracs, props=(T_VAR, H_VAR)):
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        self.propDict[P_VAR].SetValue(P, FIXED_V)
        self.propDict[H_VAR].SetValue(None, FIXED_V)
        self.propDict[VPFRAC_VAR].SetValue(1.0, FIXED_V)
        nuSolids = self.NumberSolidPhases()                    
        results = thAdmin.Flash(prov, case, self.cmpDict, self.propDict, 2, props, nuSolids=nuSolids)
        return results
    
    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        """Calculates the right hand side of the design equations. Returns the next avilable index for a new equation"""

        molarFlow = x[self.moleFlowIdx]
        self.QArray[:] = take(x, self.QIndex)
        self.HArray[:] = take(x, self.HIndex)
        self.TArray[:] = take(x, self.TIndex)
        
        self.molarFlow = molarFlow
        nuSegments = self.GetNumberOfSegments()
        findPhCh = self._parentOp.findPhCh
        segType = self._parentOp.segType
        
        if findPhCh:
            profs = self.storedProfiles
            tProfPhCh = list(self.TArray)
            hProfPhCh = list(self.HArray)
            qProfPhCh = list(self.QArray)
            pProfPhCh = list(self.PArray)
            phChIdx = []
            tInSeg = []  #Keep a list of Temperatures calculated in each segment
            hInSeg = []  #Keep a list of H calculated in each segment
            idxInSeg = [] #Keep track of the idx of each property
            
            idxPhCh = -1
        
        for i in range(nuSegments+1):
            if i < nuSegments:
                #qi - m.[H(i)-H(i+1)] = 0
                #self.QArray[i] = x[self.QIndex[i]]
                #self.HArray[i] = x[self.HIndex[i]]
                #self.HArray[i+1] = x[self.HIndex[i+1]]
                rhs[eqnNo] = self.QArray[i] - molarFlow * (self.HArray[i+1] - self.HArray[i])
                rhs[eqnNo] /= self.scaleFactorQ
                eqnNo += 1
                
                if i and segType == ENERGY_VAR and self.idxInParent:
                    #Same spacing in energy between segments
                    #Do this set of equations for nuSides - 1 sides
                    rhs[eqnNo] = (self.QArray[i] - self.QArray[i-1]) / self.scaleFactorQ
                    eqnNo += 1

            #Ti - f(pi,Hi) = 0
            #self.TArray[i] = x[self.TIndex[i]]
            P, H = self.PArray[i], self.HArray[i]
            if not findPhCh:
                T = self.GetTemperature(P, H, self.fracs)
                
            else:
                #Do all this code to find phase changes and update the profiles accordingly
                res = self.PHFlash(P, H, self.fracs)
                T = res.bulkProps[0]
                vf = res.phaseFractions[0]
                tInSeg.append((T,))
                hInSeg.append((H,))
                idxInSeg.append((idxPhCh,))
                if i:
                    if vf != vfOld:
                        vMax = max(vf, vfOld)
                        vMin = min(vf, vfOld)
                        if vMax < 0.99999 and vMin > 0.00001:
                            #Condensing all the way. No phase change
                            idxPhCh += 1
                            #tInSeg.append((T,))
                            #hInSeg.append((H,))
                            #idxInSeg.append((idxPhCh,))
                        else:
                            if vfOld > vf:
                                if vMax >= 0.99999:
                                    newP = (pProfPhCh[idxPhCh] + pProfPhCh[idxPhCh+1] ) / 2.0
                                    res = self.DewPtFlash(newP, self.fracs)
                                    newT, newH = res.bulkProps[0], res.bulkProps[1]
                                    idxPhCh += 1
                                    tProfPhCh.insert(idxPhCh, newT)
                                    hProfPhCh.insert(idxPhCh, newH)
                                    pProfPhCh.insert(idxPhCh, newP)
                                    qProfPhCh[idxPhCh-1] = molarFlow * (hProfPhCh[idxPhCh] - hProfPhCh[idxPhCh-1])
                                    qProfPhCh.insert(idxPhCh, molarFlow * (hProfPhCh[idxPhCh+1] - hProfPhCh[idxPhCh]))
                                    phChIdx.append(idxPhCh)
                                    tInSeg[-2] = (tInSeg[-2][0], newT)
                                    hInSeg[-2] = (hInSeg[-2][0], newH)
                                    idxInSeg[-2] = (idxPhCh-1, idxPhCh)
                                    
                                if vMin <= 0.00001:
                                    newP = (pProfPhCh[idxPhCh] + pProfPhCh[idxPhCh+1] ) / 2.0
                                    res = self.BubPtFlash(P, self.fracs)
                                    newT, newH = res.bulkProps[0], res.bulkProps[1]
                                    idxPhCh += 1
                                    tProfPhCh.insert(idxPhCh, newT)
                                    hProfPhCh.insert(idxPhCh, newH)
                                    pProfPhCh.insert(idxPhCh, newP)
                                    qProfPhCh[idxPhCh-1] = molarFlow * (hProfPhCh[idxPhCh] - hProfPhCh[idxPhCh-1])
                                    qProfPhCh.insert(idxPhCh, molarFlow * (hProfPhCh[idxPhCh+1] - hProfPhCh[idxPhCh]))
                                    phChIdx.append(idxPhCh)
                                    if len(tInSeg[-2]) == 1:
                                        tInSeg[-2] = (tInSeg[-2][0], newT)
                                        hInSeg[-2] = (hInSeg[-2][0], newH)
                                        idxInSeg[-2] = (idxPhCh-1, idxPhCh)
                                    else:
                                        tInSeg[-2] = (tInSeg[-2][0], tInSeg[-2][1], newT)
                                        hInSeg[-2] = (hInSeg[-2][0], hInSeg[-2][1], newH)
                                        idxInSeg[-2] = (idxPhCh-2, idxPhCh-1, idxPhCh)
                                    
                            else:
                                if vMin <= 0.00001:
                                    newP = (pProfPhCh[idxPhCh] + pProfPhCh[idxPhCh+1] ) / 2.0
                                    res = self.BubPtFlash(P, self.fracs)
                                    newT, newH = res.bulkProps[0], res.bulkProps[1]
                                    idxPhCh += 1
                                    tProfPhCh.insert(idxPhCh, newT)
                                    hProfPhCh.insert(idxPhCh, newH)
                                    pProfPhCh.insert(idxPhCh, newP)
                                    qProfPhCh[idxPhCh-1] = molarFlow * (hProfPhCh[idxPhCh] - hProfPhCh[idxPhCh-1])
                                    qProfPhCh.insert(idxPhCh, molarFlow * (hProfPhCh[idxPhCh+1] - hProfPhCh[idxPhCh]))
                                    phChIdx.append(idxPhCh)
                                    tInSeg[-2] = (tInSeg[-2][0], newT)
                                    hInSeg[-2] = (hInSeg[-2][0], newH)
                                    idxInSeg[-2] = (idxPhCh-1, idxPhCh)
                                    
                                if vMax >= 0.99999:
                                    newP = (pProfPhCh[idxPhCh] + pProfPhCh[idxPhCh+1] ) / 2.0
                                    res = self.DewPtFlash(newP, self.fracs)
                                    newT, newH = res.bulkProps[0], res.bulkProps[1]
                                    idxPhCh += 1
                                    tProfPhCh.insert(idxPhCh, newT)
                                    hProfPhCh.insert(idxPhCh, newH)
                                    pProfPhCh.insert(idxPhCh, newP)
                                    qProfPhCh[idxPhCh-1] = molarFlow * (hProfPhCh[idxPhCh] - hProfPhCh[idxPhCh-1])
                                    qProfPhCh.insert(idxPhCh, molarFlow * (hProfPhCh[idxPhCh+1] - hProfPhCh[idxPhCh]))
                                    phChIdx.append(idxPhCh)
                                    if len(tInSeg[-2]) == 1:
                                        tInSeg[-2] = (tInSeg[-2][0], newT)
                                        hInSeg[-2] = (hInSeg[-2][0], newH)
                                        idxInSeg[-2] = (idxPhCh-1, idxPhCh)
                                    else:
                                        tInSeg[-2] = (tInSeg[-2][0], tInSeg[-2][1], newT)
                                        hInSeg[-2] = (hInSeg[-2][0], hInSeg[-2][1], newH)
                                        idxInSeg[-2] = (idxPhCh-2, idxPhCh-1, idxPhCh)
                    else:
                        idxPhCh += 1
                    
                else:
                    idxPhCh += 1

                vfOld = vf
                
            #Finally load the equation
            rhs[eqnNo] = self.TArray[i] - T
            rhs[eqnNo] /= self.scaleFactorT
            eqnNo += 1

        
        #Load back
        if findPhCh:
            profs[T_VAR] = tProfPhCh
            profs[H_VAR] = hProfPhCh
            profs[ENERGY_VAR] = qProfPhCh
            profs[P_VAR] = pProfPhCh
            profs['PhChangeIdx'] = phChIdx
            profs['TPerSeg'] = tInSeg
            profs['HPerSeg'] = hInSeg
            profs['IdxPerSeg'] = idxInSeg
            
        #Equations for specs
        if isFix[self.moleFlowIdx]:
            rhs[eqnNo] = molarFlow - initx[self.moleFlowIdx]
            rhs[eqnNo] /= self.scaleFactorF
            eqnNo += 1
            
        for idx in self.HIndex:
            if isFix[idx]:
                rhs[eqnNo] = x[idx] - initx[idx]
                rhs[eqnNo] /= self.scaleFactorH
                eqnNo += 1
                
        return eqnNo

    def CalculateJacobian(self, x, j, isFix, initx, eqnNo=0):

        molarFlow = x[self.moleFlowIdx]
        nuSegments = self.GetNumberOfSegments()     
        segType = self._parentOp.segType
        
        for i in range(nuSegments+1):
            if i < nuSegments:
                #qi - m.[H(i)-H(i+1)] = 0
                #qArray(i) = x(qIndex(i))
                #HArray(i) = x(hIndex(i))
                #HArray(i + 1) = x(hIndex(i + 1))
                #rhs(eqnNo) = qArray(i) - molarFlow * (HArray(i) - HArray(i + 1))
                j[eqnNo][self.QIndex[i]] = 1.0/self.scaleFactorQ
                j[eqnNo][self.moleFlowIdx] = -(self.HArray[i+1] - self.HArray[i])/self.scaleFactorQ
                j[eqnNo][self.HIndex[i+1]] = -molarFlow/self.scaleFactorQ
                j[eqnNo][self.HIndex[i]] = molarFlow/self.scaleFactorQ 
                
                eqnNo += 1
                
                if i and segType == ENERGY_VAR and self.idxInParent:
                    #Same spacing in energy between segments
                    j[eqnNo][self.QIndex[i]] = 1.0/self.scaleFactorQ
                    j[eqnNo][self.QIndex[i-1]] = -1.0/self.scaleFactorQ
                    eqnNo += 1
                
          
            #Ti - f(pi,Hi) = 0
            #tArray(i) = x(tIndex(i))
            #Ti - f(pi,Hi) = 0
            j[eqnNo][self.TIndex[i]] = 1.0/self.scaleFactorT
          
            P, H = self.PArray[i], self.HArray[i]
            oldT = self.GetTemperature(P, H, self.fracs)
            shift = 100.0

            H = self.HArray[i] + shift
            T = self.GetTemperature(P, H, self.fracs)
            j[eqnNo][self.HIndex[i]] = -((T - oldT) / shift)/self.scaleFactorT
            eqnNo += 1
            
            


        #Jacobian for specs
        if isFix[self.moleFlowIdx]:
            j[eqnNo][self.moleFlowIdx] = 1.0/self.scaleFactorF
            eqnNo += 1
        for idx in self.HIndex:
            if isFix[idx]:
                j[eqnNo][idx] = 1.0/self.scaleFactorH
                eqnNo += 1

        return eqnNo
    
    
    def GetContents(self):
        results = super(_Side, self).GetContents()
        idx = self._parentOp.GetIndexOfSide(self)
        obj = self._parentOp.GetObject(COUNTER_CURRENT_PAR + str(idx))
        results.append((COUNTER_CURRENT_PAR, obj))
        results.append((T_VAR, self.TArray))
        results.append((P_VAR, self.PArray))
        results.append((H_VAR, self.HArray))
        results.append((ENERGY_VAR, self.QArray))
        return results

        
    def GetObject(self, desc):
        obj = super(_Side, self).GetObject(desc)
        if obj: return obj
        
        if desc == COUNTER_CURRENT_PAR:
            idx = self._parentOp.GetIndexOfSide(self)
            obj = self._parentOp.GetObject(COUNTER_CURRENT_PAR + str(idx))
            return obj
        elif desc == T_VAR:
            if not self.TArray: return None
            if None in self.TArray: return None
            return self.TArray
        elif desc == P_VAR:
            if not self.PArray: return None
            if None in self.PArray: return None
            return self.PArray
        elif desc == H_VAR:
            if not self.HArray: return None
            if None in self.HArray: return None
            return self.HArray
        elif desc == ENERGY_VAR:
            #Solution algorith uses it in kJ/h !!. Convert to J/s
            if not self.QArray or None in self.QArray:
                return None
            #For countercurrent, the values should have the opposite side
            #so the increases or decreases in energy match the flow direction
            qOut = zeros(1+len(self.QArray), Float)
            if self.GetIsCoCurrent():
                mySign = 1
                qOut[1:] = mySign*self.QArray / 3.6
                return qOut
            else:
                mySign = -1
                qOut[:-1] = mySign*self.QArray / 3.6
                return qOut
            #return mySign*Numeric.array(self.QArray, Numeric.Float) / 3.6
        elif desc == ENERGY_VAR + 'Acum':
            if not self.QArray or None in self.QArray:
                return None
            qOut = zeros(1+len(self.QArray), Float)
            qOut[1:] = self.QArray / 3.6
            return Numeric.absolute(Numeric.add.accumulate(qOut))
        else:
            try:
                phase = OVERALL_PHASE
                propName = desc
                tempDesc = desc.split('_', 1)
                if len(tempDesc) == 2:
                    if tempDesc[0] == Tower.TOWER_VAP_PHASE:
                        phase = VAPOUR_PHASE
                        propName = tempDesc[1]
                    elif tempDesc[0] == Tower.TOWER_LIQ_PHASE:
                        phase = LIQUID_PHASE
                        propName = tempDesc[1]
                return self.Profile(propName, phase)
            except:
                return None

    def Profile(self, propName, phase=OVERALL_PHASE):
        """Returns a profile"""
        nuSegments = self.GetNumberOfSegments()
        
        if phase == OVERALL_PHASE:
            keyPropName = propName
        elif phase == VAPOUR_PHASE:
            keyPropName = ('%s_%s' %(Tower.TOWER_VAP_PHASE, propName))
        elif phase == LIQUID_PHASE:
            keyPropName = ('%s_%s' %(Tower.TOWER_LIQ_PHASE, propName))
            
        #Return the stored profile if available
        storedProfiles = self.storedProfiles
        profile = storedProfiles.get(keyPropName, None)
        if profile != None and len(profile) == nuSegments + 1:
            return profile
        
        #Get the thermo
        thCaseObj = self.GetThermo()
        if not thCaseObj: return None
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        
        #Has to be requesting a supported property
        if propName != VPFRAC_VAR and propName != MASSVPFRAC_VAR:
            if not propName in thAdmin.GetPropertyNames(prov): 
                return None
        profile = None
        
        
        if not self.HArray or not self.PArray: return None
        
        
        #Get composition
        fracs = self._portIn.GetCompositionValues()
        if not fracs or None in fracs: return None
        nuCmps = len(fracs)

        
        #A flash will be performed, make sure we get as much info in one shot as possible
        ignoreNames = (P_VAR, H_VAR, ENERGY_VAR + 'Acum', ENERGY_VAR, VPFRAC_VAR, MASSVPFRAC_VAR)
        propNames = []
        if not propName in ignoreNames:
            propNames.append(propName)
        
        #Always calculate molecular weight for the bulk and vapour
        if len(propNames) == 0:
            #At least do MW
            propNames.append(MOLEWT_VAR)
        elif propName != MOLEWT_VAR:
            mw = storedProfiles.get(MOLEWT_VAR, None)
            if mw == None or len(mw) != nuSegments + 1:
                #Get MW just in case
                propNames.append(MOLEWT_VAR)
            else:
                mw = storedProfiles.get('%s_%s' %(Tower.TOWER_VAP_PHASE, MOLEWT_VAR))
                if mw == None or len(mw) != nuSegments + 1:
                    propNames.append(MOLEWT_VAR)
        
            
        #Build a list of all the properties that should get calculated in the flash call
        #The parameter Profiles helps to predefine the profiles that will be requested
        calcProfiles = self.GetParameterValue(INSTALLEDPROFILES_PAR)
        if isinstance(calcProfiles, str) or isinstance(calcProfiles, unicode):
            
            knownNames = self.storedProfiles.keys()
            for item in calcProfiles.split(' '):
                #get the name of the property
                item = item.split('_', 1)[-1]
                
                #add it to the list if necessary
                if (not item in ignoreNames) and (not item in propNames):
                    if (not item in knownNames) or (len(storedProfiles[item]) != nuSegments + 1):
                        propNames.append(item)
                    
        #Dimension arrays
        nuProps = len(propNames)
        profilesBulk = zeros((nuProps, nuSegments+1), Float)
        profilesVap = zeros((nuProps, nuSegments+1), Float)
        profilesLiq = zeros((nuProps, nuSegments+1), Float)
        profilesVapFrac = zeros(nuSegments+1, Float)
        
        #define composition bulk
        cmps = CompoundList(None)
        for frac in fracs:
            prop = BasicProperty(FRAC_VAR)
            prop.SetValue(frac, FIXED_V)
            cmps.append(prop)
            
        #Do flash calculations
        myName = self.GetName()
        txtPropNames = str(propNames)
        props = MaterialPropertyDict()
        nuSolids=self.NumberSolidPhases()
        for i in range(nuSegments+1):
            props[P_VAR].SetValue(self.PArray[i], FIXED_V)
            props[H_VAR].SetValue(self.HArray[i], FIXED_V)
            self.InfoMessage('CalculatingProfile', (myName, i, txtPropNames))
            results = thAdmin.Flash(prov, case, cmps, props, 1, propNames, nuSolids=nuSolids)
            for nuProp in range(nuProps):
                profilesBulk[nuProp][i] = results.bulkProps[[nuProp]]
                profilesVap[nuProp][i] = results.phaseProps[0][[nuProp]]
                profilesLiq[nuProp][i] = results.phaseProps[1][[nuProp]]
                profilesVapFrac[i] = results.phaseFractions[0]
        self.InfoMessage('DoneProfile', myName)
                       
        #Store all calculated properties
        for nuProp in range(nuProps):
            storedProfiles[propNames[nuProp]] = array(profilesBulk[nuProp, :], Float)
            storedProfiles['%s_%s' %(Tower.TOWER_VAP_PHASE, propNames[nuProp])] = array(profilesVap[nuProp, :], Float)
            storedProfiles['%s_%s' %(Tower.TOWER_LIQ_PHASE, propNames[nuProp])] = array(profilesLiq[nuProp, :], Float)
        
        #Store Vap fraction
        vf = storedProfiles[VPFRAC_VAR] = array(profilesVapFrac, Float)
        
        #Store Mass vap fraction
        vapmw = storedProfiles['%s_%s' %(Tower.TOWER_VAP_PHASE, MOLEWT_VAR)]
        bulkmw = storedProfiles[MOLEWT_VAR]
        storedProfiles[MASSVPFRAC_VAR] = vf * vapmw / bulkmw
            
        
        return self.storedProfiles.get(keyPropName, None)              

        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(_Side, self).AdjustOldCase(version)


        #Borrow DeltaT signals
        if version[0] < 14:
            #First make sure it is there
            dtPort = self.GetPort(DELTAT_PORT)
            if not dtPort:
                dtPort = self.CreatePort(SIG, DELTAT_PORT)
                dtPort.SetSignalType(DELTAT_VAR)
                self.CalcDeltaT(self._portIn, self._portOut, dtPort)
            self._portDT = dtPort
                
        if version[0] < 39:
            if not hasattr(self, 'storedProfiles'):
                self.storedProfiles = {}
        if version[0] < 59:
            self.molarFlow = None
            
    def _CloneParameters(self, clone, attrNamesToClone):
        #Clone parameters
        for paramName in self.parameters:
            #Do a copy just in case
            clone.parameters[paramName] = copy.deepcopy(self.parameters[paramName])
            
        for paramName in self.parameterPropertyTypes:
            #Can safely point to the same thing as they are global types
            clone.parameterPropertyTypes[paramName] = self.parameterPropertyTypes[paramName]
            
        if "parameters" in attrNamesToClone: attrNamesToClone.remove("parameters")
        if "parameterPropertyTypes" in attrNamesToClone: attrNamesToClone.remove("parameterPropertyTypes") 
        
        return attrNamesToClone
            
class _HeatTransfer(EquationSolver.EquationBasedOp):
    def __init__(self, parentOp, parentObj, side1, side2):

        super(_HeatTransfer, self).__init__()

        self._parentOp = parentOp
        self._side1 = side1
        self._side2 = side2
        self._useInCalcualtions = False

        #UA port
        self._portUA = self.CreatePort(SIG, UA_PORT)
        self._portUA.SetLocked(True)
        self._portUA.SetSignalType(UA_VAR)
        
        self._portDTIn = self.CreatePort(SIG, DELTAT_PORT + '_In')
        self._portDTIn.SetLocked(True)
        self._portDTIn.SetSignalType(DELTAT_VAR)
        
        self._portDTOut = self.CreatePort(SIG, DELTAT_PORT + '_Out')
        self._portDTOut.SetLocked(True)
        self._portDTOut.SetSignalType(DELTAT_VAR)
        
        self.storedProfiles = {}
        
        self.duty = None
        self.lmtd = None
        self.ua = None
        
    def CleanUp(self):
        self._parentOp = self._side1 = self._side2 = None
        self._portUA = self._portDTIn = self._portDTOut = None
        super(_HeatTransfer, self).CleanUp()
        

    def GetObject(self, desc):
        obj = super(_HeatTransfer, self).GetObject(desc)
        if obj: return obj
        
        if desc == ENERGY_VAR:
            #Solution algorith uses it in kJ/h !!. Return in J/s
            if not self.duty or None in self.duty:
                return None
            
            return Numeric.array(self.duty, Numeric.Float) / 3.6
        
        #elif desc == ENERGY_VAR + '_Acum':
            #if not self.duty or None in self.duty:
                #return None
            #return Numeric.add.accumulate(self.duty) / 3.6
        
        elif desc == 'lmtd':
            if hasattr(self, 'lmtd') and not self.lmtd or None in self.lmtd:
                return None
            return array(self.lmtd, Float)
        
        elif desc == 'ua':
            if hasattr(self, 'ua') and not self.ua or None in self.ua:
                return None
            return array(self.ua, Float) / 3.6
        
        
    def AssignResults(self, vals):
        """Assign the results into the appropriate ports"""
        
        if self.ua != None:
            self._portUA.SetValue(sum(self.ua)/3.6, CALCULATED_V|PARENT_V)
            
        
    def PrepareForSolve(self):
        """Prepares and calculates info that is not taken in the simultaneous equations. Returns False if can not solve"""
        
        #Just check if it needs to be included in the calculations
        #Only include heat transfer objects with UA different form 0
        UA = self._portUA.GetValue()
        if UA == 0:
            self._useInCalcualtions = False
        else:
            self._useInCalcualtions = True

        self.scaleFactorUA = 1000.0 #self._portUA.GetType().scaleFactor * 3.6/10.0 #Update for using kJ/(hr-K)       
            
        return True   
    
    def GetNumberOfSegments(self):
        """Number of segments that the side is divided on"""
        return self._parentOp.GetNumberOfSegments()        
    
    def UseInCalculations(self):
        """Returns true if the object should be included in calculations"""
        return self._useInCalcualtions
        
    
    def LoadUnknowns(self, u):
        """Load the unknown variables. Returns False is there are not enough known variables"""
        
        #Load vars in a convenient way
        parent = self._parentOp
        nuSegments = self.GetNumberOfSegments()
        segType = parent.segType
        findPhCh = parent.findPhCh
        side1 = self._side1
        side2 = self._side2
        SolverVariable = EquationSolver.SolverVariable
        AddUnknown = u.AddUnknown
        initMode = parent.initMode
        
        #Dimension arrays
        duty = zeros(nuSegments, Float) 
        ua = zeros(nuSegments, Float)
        lmtd = zeros(nuSegments, Float)
        logTerm = zeros(nuSegments, Float)
        usePinchEqn = zeros(nuSegments, Int)
        countPinch = zeros(nuSegments, Int)
        dutyIndex = zeros(nuSegments, Int)
        uaIndex = zeros(nuSegments, Int)
        
        
        if findPhCh:
            #There could be changes in length of profiles which are not part of solver. 
            #Prepare for them
            self.storedProfiles['LMTD'] = None
            self.storedProfiles[UA_VAR] = None
            self.storedProfiles[ENERGY_VAR] = None
        
        
        S1T = side1.GetArray(T_VAR)
        S2T = side2.GetArray(T_VAR)
        idx1 = parent.GetIndexOfSide(side1)
        idx2 = parent.GetIndexOfSide(side2)
        
        try:
            if initMode != SCRATCH_INIT:
                ua[:] = self.ua[:]
        except:
            initMode = parent.initMode = SCRATCH_INIT
        
        name = 'UA%i_%i' %(idx1, idx2)
        isSpec = True
        UA = self._portUA.GetValue()
        if UA != None:
            UA = UA * 3.6 #Convert to kJ(hr-K)
        if UA == None:
            isSpec = False
            if initMode == SCRATCH_INIT or self._UA == None:
                QArray = side1.GetArray(ENERGY_VAR)
                if side1.GetIsCoCurrent(): mySign = -1
                else: mySign = 1
                Q = mySign*QArray[0]
                tempLmtd = self.CalcLMTD(S1T[0], S2T[0], S1T[1], S2T[1])
                UA = nuSegments*Q/tempLmtd
            else:
                UA = self._UA
        scaleFactorUA = self.scaleFactorUA
        tempUnkVar = SolverVariable(name, UA, UA, isSpec, scaleFactorUA)
        self.UAIndex = AddUnknown(tempUnkVar) #Returns the index where the unk was put
            
        
        scaleFactorQ = side1.scaleFactorF * side1.scaleFactorH
        self.scaleFactorQ = scaleFactorQ
        isSpec = False
        for i in range(nuSegments):
            name = 'Q%i_%i_Seg_%i' %(idx1, idx2, i)
            usePinchEqn[i] = False
            countPinch[i] = 0
            lmtd[i] = self.CalcLMTD(S1T[i], S2T[i], S1T[i+1], S2T[i+1])
            
            if initMode == SCRATCH_INIT:
                ua[i] = uaSeg = (UA / nuSegments)
            else:
                uaSeg = ua[i]
            duty[i] = uaSeg * lmtd[i]
            tempUnkVar = SolverVariable(name, duty[i], duty[i], isSpec, scaleFactorQ)
            dutyIndex[i] = AddUnknown(tempUnkVar) #Returns the index where the unk was put

            #If segments are based on even separation of energy instead of UA, 
            #then add the UA vals per segment as variabls
            if segType == ENERGY_VAR:
                name = 'UA%i_%i_Seg_%i' %(idx1, idx2, i)
                tempUnkVar = SolverVariable(name, uaSeg, uaSeg, isSpec, scaleFactorUA)
                uaIndex[i] = AddUnknown(tempUnkVar) #Returns the index where the unk was put
            
                
        #Load everrything into member variables
        self._UA = UA
        self.duty = duty
        self.lmtd = lmtd
        self.ua = ua
        self.logTerm = logTerm
        self.usePinchEqn = usePinchEqn
        self.countPinch = countPinch
        self.dutyIndex = dutyIndex
        self.uaIndex = uaIndex
        
        
        return True


    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        """Calculates the right hand side of the design equations"""

        #Structural things
        nuSegments = self.GetNumberOfSegments()
        segType = self._parentOp.segType
        side1 = self._side1
        side2 = self._side2
        findPhCh = self._parentOp.findPhCh

        #Load from incomming x
        self._UA = UA = x[self.UAIndex]
        self.duty[:] = take(x, self.dutyIndex)
        if segType == ENERGY_VAR:
            self.ua[:] = take(x, self.uaIndex)
        else:
            self.ua[:] = ones(nuSegments, Float) * UA
        
        S1T = side1.GetArray(T_VAR)
        S2T = side2.GetArray(T_VAR)
        if findPhCh:
            phChS1T = side1.storedProfiles[T_VAR]
            phChS2T = side2.storedProfiles[T_VAR]
            phChIdx1 = side1.storedProfiles['PhChangeIdx']
            phChIdx2 = side2.storedProfiles['PhChangeIdx']
            tPerSeg1 = side1.storedProfiles['TPerSeg']
            tPerSeg2 = side2.storedProfiles['TPerSeg']
            hPerSeg1 = side1.storedProfiles['HPerSeg']
            hPerSeg2 = side2.storedProfiles['HPerSeg']
            idxPerSeg1 = side1.storedProfiles['IdxPerSeg']
            idxPerSeg2 = side2.storedProfiles['IdxPerSeg'] 
            
            if not phChIdx1 and not phChIdx2:
                findPhCh = False
        
        #Load into locals
        duty = self.duty
        ua = self.ua
        lmtd = self.lmtd
        
        
        if findPhCh:
            profs = self.storedProfiles
            uaProfPhCh = list(ua)
            lmtdProfPhCh = list(lmtd)
            qProfPhCh = list(duty)
            phChIdx = []
            
            lmtdPerSeg = []
            uaPerSeg = []
            qPerSeg = []
            
            idxPhCh = -1        
        
        
        for i in range(nuSegments):
            if (self.usePinchEqn[i]):
                #figure out what to pinch i or i+1
                if (abs(S1T[i] - S2T[i]) < 0.0000001):
                    if (S1T[i] < S2T[i]):
                        rhs[eqnNo] = S1T[i] - S2T[i] + 0.0000000001
                    else:
                        rhs[eqnNo] = S1T[i] - S2T[i] - 0.0000000001
                    
                else:
                    if (S1T[i+1] < S2T[i+1]):
                        rhs[eqnNo] = S1T[i+1] - S2T[i+1] + 0.0000000001
                    else:
                        rhs[eqnNo] = S1T[i+1] - S2T[i+1] - 0.0000000001
                rhs[eqnNo] /= self.scaleFactorT
                lmtd[i] = self.CalcLMTD(S1T[i], S2T[i], S1T[i+1], S2T[i+1])
                
                if findPhCh:
                    uaPerSeg.append((ua[i],))
                    qPerSeg.append((duty[i],))
                    lmtdPerSeg.append((lmtd[i],))
                    idxPhCh += 1
            else:
                #qi - UAi.LMTDi = 0
                if not findPhCh:
                    lmtd[i] = self.CalcLMTD(S1T[i], S2T[i], S1T[i+1], S2T[i+1])
                    rhs[eqnNo] = duty[i] - ua[i] * lmtd[i]
                    rhs[eqnNo] /= self.scaleFactorQ
                else:
                    if len(tPerSeg1[i]) == 1 and len(tPerSeg2[i]) == 1:
                        #There was no phase change
                        lmtd[i] = self.CalcLMTD(S1T[i], S2T[i], S1T[i+1], S2T[i+1])
                        idxPhCh += 1
                        lmtdProfPhCh[idxPhCh] = lmtd[i]
                        
                        uaPerSeg.append((ua[i],))
                        qPerSeg.append((duty[i],))
                        lmtdPerSeg.append((lmtd[i],))
                        
                        rhs[eqnNo] = duty[i] - ua[i] * lmtd[i]
                        rhs[eqnNo] /= self.scaleFactorQ
                        
                    else:
                        
                        #Most of the following code is used to find where the phase change occur in each side
                        #and then estimate the amount of heat transferred after each phase change and the
                        #temperatures in the sides that are not changing phase. 
                        #The code gets lengthy because phase changes can occur in both sides and there can be 
                        #up to two phase changes in each side
                        fracsFwd1 = []
                        if len(tPerSeg1[i]) != 1:
                            h0 = hPerSeg1[i][0]
                            h1 = hPerSeg1[i+1][0]
                            dHTot = h1 - h0
                            for h in hPerSeg1[i][1:]:
                                fracsFwd1.append((h-h0)/dHTot)
                            tempT1 = tPerSeg1[1:]
                            
                        fracsFwd2 = []
                        if len(tPerSeg2[i]) != 1:
                            h0 = hPerSeg2[i][0]
                            h1 = hPerSeg2[i+1][0]
                            dHTot = h1 - h0
                            
                            for h in hPerSeg2[i][1:]:
                                fracsFwd2.append((h-h0)/dHTot)
                                
                        s1tsTemp = list(tPerSeg1[i][1:])
                        s2tsTemp = list(tPerSeg2[i][1:])
                        s1t = [tPerSeg1[i][0]]
                        s2t = [tPerSeg2[i][0]]
                        fracs = [0.0]
                        qTot = duty[i]
                        qTemp = [0.0]
                        while fracsFwd1 or fracsFwd2:
                            if fracsFwd1 and fracsFwd2:
                                if fracsFwd1[0] > fracsFwd2[0]:
                                    frac = fracsFwd2.pop(0)
                                    fracs.append(frac)
                                    t = s2tsTemp.pop(0)
                                    qTemp.append(qTot*(fracs[-1] - fracs[-2]))
                                    s2t.append(t)
                                    s1t.append(None)
                                else:
                                    frac = fracsFwd1.pop(0)
                                    fracs.append(frac)
                                    t = s1tsTemp.pop(0)
                                    qTemp.append(qTot*(fracs[-1] - fracs[-2]))
                                    s1t.append(t)
                                    s2t.append(None)
                            elif fracsFwd1:
                                frac = fracsFwd1.pop(0)
                                fracs.append(frac)
                                t = s1tsTemp.pop(0)
                                qTemp.append(qTot*(fracs[-1] - fracs[-2]))
                                s1t.append(t)
                                s2t.append(None)
                            elif fracsFwd2:
                                frac = fracsFwd2.pop(0)
                                fracs.append(frac)
                                t = s2tsTemp.pop(0)
                                qTemp.append(qTot*(fracs[-1] - fracs[-2]))
                                s2t.append(t)
                                s1t.append(None)
                        s1t.append(tPerSeg1[i+1][0])
                        s2t.append(tPerSeg2[i+1][0])
                        fracs.append(1.0)
                        qTemp.append(qTot*(fracs[-1] - fracs[-2]))
                        qTemp.pop(0)
                        uaTemp = []
                        lmtdTemp = []
                        
                        #Finally estimate missint T and calculate LMTDs
                        for j in range(len(s1t)-1):
                            s1t0, s1t1 = s1t[j], s1t[j+1]
                            s2t0, s2t1 = s2t[j], s2t[j+1]
                            if s1t1 == None:
                                for k in range(j+2, len(s1t)):
                                    if s1t[k] != None:
                                        s1t1 = s1t[j+1] = (fracs[j+1]/(fracs[k]-fracs[j]))*(s1t[k]-s1t[j]) + s1t[j]
                                        break
                            if s2t1 == None:
                                for k in range(j+2, len(s2t)):
                                    if s2t[k] != None:
                                        s2t1 = s2t[j+1] = (fracs[j+1]/(fracs[k]-fracs[j]))*(s2t[k]-s2t[j]) + s2t[j]
                                        break
                            lmtdTemp.append(self.CalcLMTD(s1t0, s2t0, s1t1, s2t1))
                            uaTemp.append(qTemp[j]/lmtdTemp[j])
                            
                            rhs[eqnNo] -= uaTemp[j]
                            
                            if not j: 
                                lmtdProfPhCh[idxPhCh] = lmtdTemp[j]
                                uaProfPhCh[idxPhCh] = uaTemp[j]
                                qProfPhCh[idxPhCh] = qTemp[j]
                                idxPhCh +=1
                            else:
                                lmtdProfPhCh.insert(idxPhCh, lmtdTemp[j])
                                uaProfPhCh.insert(idxPhCh, uaTemp[j])
                                qProfPhCh.insert(idxPhCh, qTemp[j])
                                idxPhCh += 1
                                
                        uaPerSeg.append(tuple(uaTemp))
                        qPerSeg.append(tuple(qTemp))
                        lmtdPerSeg.append(tuple(lmtdTemp))
                                
                        tPerSeg1[i] = tuple(s1t[:-1])
                        tPerSeg2[i] = tuple(s2t[:-1])
                        
                        rhs[eqnNo] += ua[i]
                        rhs[eqnNo] /= self.scaleFactorUA /1000.0
            eqnNo += 1
            
            #if i and segType == ENERGY_VAR:
                ##Same spacing in energy between segments
                #rhs[eqnNo] = x[side1.QIndex[i]] - x[side1.QIndex[i-1]]
                #eqnNo += 1

        if segType == ENERGY_VAR:
            #UA = sum(ua)
            rhs[eqnNo] = (UA - Numeric.sum(ua)) / self.scaleFactorUA
            eqnNo += 1
            
        #contribute UA if was a spec
        if isFix[self.UAIndex]:
            rhs[eqnNo] = UA - initx[self.UAIndex]
            rhs[eqnNo] /= self.scaleFactorUA
            eqnNo += 1
        
        return eqnNo
        

    def CalcLMTD(self, S1T1, S2T1, S1T2, S2T2):
        """Calculates LMTD"""
        dt1 = S1T1 - S2T1
        dt2 = S1T2 - S2T2 + 1E-30

        if (dt1 * dt2 < 0.0):
            #set the smaller dt to 1e-30
            if (abs(dt1) > abs(dt2)):
                #dt2 is smaller
                dt2 = ((dt1)/abs(dt1)) * 1E-30
            else:
                dt1 = ((dt2)/abs(dt2)) * 1E-30

        elif (dt1 * dt2 == 0.0):
            dt1 = 1E-30
            dt2 = dt1

        if (abs(dt1 - dt2) < 0.0000000001):
            dt1 = dt1 + 0.0000000001

        return (dt1 - dt2) / (math.log(dt1 / dt2) + 1E-30)
           

    def CalculateJacobian(self, x, j, isFix, initx, eqnNo=0):
        S1T = copy.copy(self._side1.GetArray(T_VAR))
        S2T = copy.copy(self._side2.GetArray(T_VAR))
        nuSegments = self.GetNumberOfSegments()
        UA = x[self.UAIndex]
        
        segType = self._parentOp.segType
        duty = self.duty
        ua = self.ua
        lmtd = self.lmtd
        side1 = self._side1
        side2 = self._side2
        
        for i in range(nuSegments):

            if segType == ENERGY_VAR:
                ua = x[self.uaIndex[i]]
            else:
                ua = (UA / nuSegments)
            
            if (self.usePinchEqn[i]):
                #figure out what to pinch i or i+1
                if (abs(S1T[i] - S2T[i]) < 0.0000001):
                    #rhs(eqnNo) = S1T(i) - S2T(i) + 0.0000000001
                    j[eqnNo][side1.TIndex[i]] = 1.0/self.scaleFactorT
                    j[eqnNo][side2.TIndex[i]] = -1.0/self.scaleFactorT
                else:
                    #rhs(eqnNo) = S1T(i + 1) - S2T(i + 1) + 0.0000000001
                    j[eqnNo][side1.TIndex[i + 1]] = 1.0/self.scaleFactorT
                    j[eqnNo][side2.TIndex[i + 1]] = -1.0/self.scaleFactorT
                
            else:
                #qi - UAi.LMTDi = 0
                #duty(i) = x(iv + 1)
                
                j[eqnNo][self.dutyIndex[i]] = 1.0/self.scaleFactorQ
                if segType == ENERGY_VAR:
                    #rhs(eqnNo) = duty(i) - uai * CalcLmtd(S1T(i), S2T(i), S1T(i + 1), S2T(i + 1))
                    j[eqnNo][self.uaIndex[i]] = (-self.CalcLMTD(S1T[i], S2T[i], S1T[i + 1], S2T[i + 1]))/self.scaleFactorQ
                else:
                    #rhs(eqnNo) = duty(i) - UA / side1.numSegments * CalcLmtd(S1T(i), S2T(i), S1T(i + 1), S2T(i + 1))
                    j[eqnNo][self.UAIndex] = (-self.CalcLMTD(S1T[i], S2T[i], S1T[i + 1], S2T[i + 1]) / nuSegments)/self.scaleFactorQ

                #analytical derivatives are too complicated for my tiny brain and are left as an exercise for Raul <g>.
                if (S1T[i] > S2T[i]):
                    shift = 0.000001
                else:
                    shift = -0.000001
                
                shift = -0.000001
                oldV = -self.CalcLMTD(S1T[i], S2T[i], S1T[i + 1], S2T[i + 1])
                S1T[i] = S1T[i] + shift
                newV = -self.CalcLMTD(S1T[i], S2T[i], S1T[i + 1], S2T[i + 1])
                j[eqnNo][side1.TIndex[i]] = (ua * (newV - oldV) / shift)/self.scaleFactorQ
                S1T[i] = S1T[i] - shift

                j[eqnNo][side2.TIndex[i]] = -j[eqnNo][side1.TIndex[i]]

                S1T[i + 1] = S1T[i + 1] + shift
                newV = -self.CalcLMTD(S1T[i], S2T[i], S1T[i + 1], S2T[i + 1])
                j[eqnNo][side1.TIndex[i + 1]] = (ua * (newV - oldV) / shift)/self.scaleFactorQ
                S1T[i + 1] = S1T[i + 1] - shift

                j[eqnNo][side2.TIndex[i + 1]] = -j[eqnNo][side1.TIndex[i + 1]]
            
            eqnNo += 1

            #if i and segType == ENERGY_VAR:
                ##Same spacing in energy between segments
                #j[eqnNo][side1.QIndex[i]] = 1.0/self.scaleFactorQ
                #j[eqnNo][side1.QIndex[i-1]] = -1.0/self.scaleFactorQ
                #eqnNo += 1
            
                    
        if segType == ENERGY_VAR:
            #UA = sum(ua)
            j[eqnNo][self.UAIndex] = 1.0 / self.scaleFactorUA
            for idx in self.uaIndex:
                j[eqnNo][idx] = - 1.0 / self.scaleFactorUA
            eqnNo += 1
                    
                    
        #contribute UA if was a spec
        if isFix[self.UAIndex]:
            j[eqnNo][self.UAIndex] = 1.0/self.scaleFactorUA
            eqnNo += 1
            
        return eqnNo
    

    def SanityCheck(self, x, initx):
        """Checks for temperature crosses"""
        #make sure there is no temperature cross

        side1 = self._side1
        side2 = self._side2
        nuSegments = self.GetNumberOfSegments()
        
        for i in range(nuSegments):
          dt1 = x[side1.TIndex[i]] - x[side2.TIndex[i]]
          dt2 = x[side1.TIndex[i+1]] - x[side2.TIndex[i+1]]
          
          if (dt1 * dt2 < 0.0):
              pass
              #if len(self._parentOp._sides) == 2:
                  ##set the smaller dt to 1e-10
                  #if (abs(dt1) > abs(dt2)):
                     ##dt2 is smaller
                     #if (abs(dt2) < 0.0001):
                        #self.countPinch[i] += 1
                     
                     #dt2 = ((dt1)/abs(dt1)) * 0.0000000001
                     #x[side1.TIndex[i+1]] = dt2 + x[side2.TIndex[i+1]]
                  #else:
                     ##dt1 is smaller
                     #if (abs(dt1) < 0.00001):
                        #self.countPinch[i] += 1
                     
                     #dt1 = ((dt2)/abs(dt2)) * 0.0000000001
                     #x[side1.TIndex[i]] = dt1 + x[side2.TIndex[i]]

          #elif (dt1 * dt2 == 0.0):
             #dt1 = 0.0000000001
             #x[side1.TIndex[i]] = dt1 + x[side2.TIndex[i]]
             #dt2 = dt1
             #x[side1.TIndex[i+1]] = dt2 + x[side2.TIndex[i+1]]
          else:
             self.countPinch[i] = 0

          if (self.countPinch[i] > 4):
             self.usePinchEqn[i] = True

             
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(_HeatTransfer, self).AdjustOldCase(version)


        #Borrow DeltaT signals
        if version[0] < 14:
            dtPort = self.GetPort(DELTAT_PORT + '_In')
            if not dtPort:
                dtPort = self.CreatePort(SIG, DELTAT_PORT + '_In')
                dtPort.SetSignalType(DELTAT_VAR)
            self._portDTIn = dtPort
            
            dtPort = self.GetPort(DELTAT_PORT + '_Out')
            if not dtPort:
                dtPort = self.CreatePort(SIG, DELTAT_PORT + '_Out')
                dtPort.SetSignalType(DELTAT_VAR)
            self._portDTOut = dtPort
             
            #Calc delta T of across side with respect of the in port of side1
            #port1 = self._side1.GetPort(IN_PORT)
            #coCurr = (self._side1.GetIsCounterCurrent() == self._side2.GetIsCounterCurrent())
            #if coCurr:
                #port2 = self._side2.GetPort(IN_PORT)
            #else:
                #port2 = self._side2.GetPort(OUT_PORT)
            #self.CalcDeltaT(port1, port2, self._portDTIn)
            
            ##Calc delta T of across side with respect of the out port of side1
            #port1 = self._side1.GetPort(OUT_PORT)
            #if coCurr:
                #port2 = self._side2.GetPort(OUT_PORT)
            #else:
                #port2 = self._side2.GetPort(IN_PORT)
            #self.CalcDeltaT(port1, port2, self._portDTOut)
            
            self._parentOp.ForgetAllCalculations()
             
        if version[0] < 38:
            if not hasattr(self, 'ua'):
                self.ua = None
            if not hasattr(self, 'lmtd'):
                self.lmtd = None
                
        if version[0] < 39:
            if not hasattr(self, 'storedProfiles'):
                self.storedProfiles = {}
    def _CloneParameters(self, clone, attrNamesToClone):
        #Clone parameters
        for paramName in self.parameters:
            #Do a copy just in case
            clone.parameters[paramName] = copy.deepcopy(self.parameters[paramName])
            
            
        for paramName in self.parameterPropertyTypes:
            #Can safely point to the same thing as they are global types
            clone.parameterPropertyTypes[paramName] = self.parameterPropertyTypes[paramName]
            
        if "parameters" in attrNamesToClone: attrNamesToClone.remove("parameters")
        if "parameterPropertyTypes" in attrNamesToClone: attrNamesToClone.remove("parameterPropertyTypes") 
        
        return attrNamesToClone
    
    
class MultiSidedHeatExchangerOp(EquationSolver.EquationBasedOp):
    def __init__(self, initScript=None):
        super(MultiSidedHeatExchangerOp, self).__init__(initScript)

        self._sides  = []
        self._hTransfer = []
        self._hTransferList = []
        self._balance = None
        self._matBalances = None
        self.estimates = {}
        self.signals = {}
        self.portSpecs = []
        self.activeSpecs = []
        self.inactiveSpecs = []
        self.hComposite = HotComposite(self, 'HotComposite')
        self.cComposite = ColdComposite(self, 'ColdComposite')
        
        self.canRestart = 0
        self.dontRestartNextTime = 1
        self.LoadDefaultParameters()
        self.customSolver = None

    ## CLEAN UP AND OLD CASES ################################################################
    def __getstate__(self):
        """return info to pickle for storing"""
        try: 
            state = self.__dict__.copy()
            if state['customSolver']:
                #Don't store the custom solver method
                try:
                    #The str(type(state['customSolver'])) call returns something like this:
                    #"<class 'CustomSolveMethod'>"
                    #Change it to something like this:
                    #'CustomSolveMethod'
                    s = str(type(state['customSolver'])).split(' ', 1)[1][1:-2]
                    state['customSolver'] = s
                except:
                    pass
            return state
        except: 
            return self.__dict__
        
    def __setstate__(self, oldState):
        """build from stored info"""
        
        self.__dict__ = oldState
        if self.__dict__.has_key('customSolver'):
            if self.customSolver:
                try:
                    #The custom solver model was stored as a string. 
                    #Try to recreate it as an a object
                    lstMods = self.customSolver.split('.', 1)
                    if len(lstMods) > 1:
                        exec('import %s' %lstMods[0])
                    customSolver = eval('%s()' %self.customSolver)
                    self.customSolver = customSolver
                    customSolver.Initialize(self, CUSTOM_SOLVE_OBJ)
                except:
                    self.InfoMessage('CouldNotRestorePlugIn', (str(self.customSolver), ))
                    customSolver = PressureDropModel()
                    self.customSolver = None

    def CleanUp(self):
        if self._balance:
            self._balance.CleanUp()
            self._balance = None
        if self._matBalances:
            for bal in self._matBalances:
                bal.CleanUp()
        self._sides  = []
        self._hTransfer = []
        self._hTransferList = []
        self.fracsObjVec = []
        self.propsObjVec = []
        
        if hasattr(self, 'portSpecs'):
            for spec in self.portSpecs:
                spec.CleanUp()
        self.portSpecs = []
        
        for signal in self.signals.values():
            signal.CleanUp()
            
        for signal in self.estimates.values():
            signal.CleanUp()
            
            
        if hasattr(self, 'customSolver') and self.customSolver != None:
            try:
                self.customSolver.CleanUp()
                self.customSolver = None
            except:
                pass
        self.hComposite.CleanUp()
        self.cComposite.CleanUp()
        super(MultiSidedHeatExchangerOp, self).CleanUp()
        
    def AdjustOldCase(self, version):
        
        """
        fixup old versions
        """
        super(MultiSidedHeatExchangerOp, self).AdjustOldCase(version)

        #Borrow DeltaT signals
        if version[0] < 14:
            #First make sure it is there
            for i in range(len(self._sides)):
                side = self._sides[i]
                dtPort = side.GetPort(DELTAT_PORT)
                if not dtPort:
                    dtPort = side.CreatePort(SIG, DELTAT_PORT)
                    dtPort.SetSignalType(DELTAT_VAR)
                self.BorrowChildPort(dtPort, DELTAT_PORT + str(i))

                
            for i in range(len(self._hTransfer)):
                row = self._hTransfer[i]
                for j in range(len(row)):
                    hTransfer = row[j]
                    if hTransfer != None:
                        dtPort = hTransfer.GetPort(DELTAT_PORT + '_In')
                        if not dtPort:
                            dtPort = hTransfer.CreatePort(SIG, DELTAT_PORT + '_In')
                            dtPort.SetSignalType(DELTAT_VAR)
                        self.BorrowChildPort(dtPort, DELTAT_PORT + str(j) + '_' + str(i) + '_In')
                        
                        dtPort = hTransfer.GetPort(DELTAT_PORT + '_Out')
                        if not dtPort:
                            dtPort = hTransfer.CreatePort(SIG, DELTAT_PORT + '_Out')
                            dtPort.SetSignalType(DELTAT_VAR)
                        self.BorrowChildPort(dtPort, DELTAT_PORT + str(j) + '_' + str(i) + '_Out')
                        
        if version[0] < 24:
            if not hasattr(self, '_hTransferList'):
                self._hTransferList = []
                for row in self._hTransfer:
                    for hTransfer in row:
                        if hTransfer:
                            self._hTransferList.append(hTransfer)
            self.ForgetAllCalculations()
            
        if version[0] < 27:
            #Recalculate DT
            self.ForgetAllCalculations()

        if version[0] < 34:
            #Load a balance
            self._balance = Balance.Balance(Balance.ENERGY_BALANCE)
            self._balance.AddInput(self.GetPorts(IN|MAT))
            self._balance.AddOutput(self.GetPorts(OUT|MAT))
            self._matBalances = []
            for side in self._sides:
                bal = Balance.Balance(Balance.MOLE_BALANCE)
                bal.AddInput(side.GetPorts(IN|MAT))
                bal.AddOutput(side.GetPorts(OUT|MAT))
                self._matBalances.append(bal)            
            
        if version[0] < 39:
            #Load a balance
            self.SetParameterValue(EquationSolver.MONITCONV_PAR, 1)
            self.SetParameterValue(FINDPH_CHANGE_PAR, 0)
            self.SetParameterValue(SEGMENTSBASE_PAR, ENERGY_VAR)
        if version[0] < 56:
            if not hasattr(self, 'signals'):
                self.signals = {}
            if not hasattr(self, 'activeSpecs'):
                self.activeSpecs = []
            if not hasattr(self, 'inactiveSpecs'):
                self.inactiveSpecs = []
                
        if version[0] < 57:
            if not hasattr(self, 'estimates'):
                self.estimates = {}
            if not hasattr(self, 'canRestart'):
                self.canRestart = False
                
        if version[0] < 59:
            if not hasattr(self, 'hComposite'):
                self.hComposite = HotComposite(self, 'HotComposite')
            if not hasattr(self, 'cComposite'):
                self.cComposite = ColdComposite(self, 'ColdComposite')
                
                
        if version[0] < 60:
            self.portSpecs = []
        if version[0] < 70:
            self.customSolver = None
        for signal in self.signals.values():
            signal.AdjustOldCase(version)        
        
    ##########################################################################################

    ## PARAMETERS ############################################################################
    def LoadDefaultParameters(self):
        """Loads default parameters. Handy when inheriting"""
        #Initialize with two sides
        self.SetParameterValue(NUSEGMENTS_PAR, 1)
        self.SetParameterValue(NUSIDES_PAR, 2)      
        self.SetParameterValue(FINDPH_CHANGE_PAR, 0)
        self.SetParameterValue(SEGMENTSBASE_PAR, ENERGY_VAR)
        self.SetParameterValue(EquationSolver.MONITCONV_PAR, 1)

    def SetParameterValue(self, paramName, value):
        
        #Trap some parameters that will not triger a solve
        #The logic behind these parameters is that they do not affect the final results
        if paramName in ['Profiles', INSTALLEDPROFILES_PAR]:
            if not self.ValidateParameter(paramName, value):
                raise Error.SimError('CantSetParameter', (paramName, str(value)))
                return 0
            self.parameters[paramName] = value
            return 1        
        
        valueChanged = self.parameters.get(paramName ,None) != value
        super(MultiSidedHeatExchangerOp, self).SetParameterValue(paramName, value)

        if paramName == NUSIDES_PAR:
            nuSides = self.parameters[NUSIDES_PAR]
            if nuSides != len(self._sides): self.canRestart = False
            
            #Fix for the COUNTER_CURRENT_PAR
            #Add if necessary
            for i in range(nuSides):
                val = self.GetParameterValue(COUNTER_CURRENT_PAR + str(i))
                if val == None:
                    self.parameters[COUNTER_CURRENT_PAR + str(i)] = True
            #Delete if necessary
            for i in range(nuSides, len(self._sides)):
                val = self.GetParameterValue(COUNTER_CURRENT_PAR + str(i))
                if val != None:
                    del self.parameters[COUNTER_CURRENT_PAR + str(i)]

                    
            #Make sure one of the sides is the reference side for defining co or counter current
            val = self.GetParameterValue(REFERENCE_SIDE_PAR)
            if val == None:
                if nuSides > 0 :
                    self.parameters[REFERENCE_SIDE_PAR] = 0
                    self.parameters[COUNTER_CURRENT_PAR + str(0)] = False #For consistency, make reference side cocurrent
                else:
                    self.parameters[REFERENCE_SIDE_PAR] = -1

            #Reference side doesnt exist anymore
            elif val >= nuSides:
                self.parameters[REFERENCE_SIDE_PAR] = 0
                ref = self.parameters[COUNTER_CURRENT_PAR + str(0)]
                for i in range(nuSides):
                    if i != 0:
                        val = self.parameters[COUNTER_CURRENT_PAR + str(i)]
                        if val == ref:
                            self.parameters[COUNTER_CURRENT_PAR + str(i)] = False
                        else:
                            self.parameters[COUNTER_CURRENT_PAR + str(i)] = True
                self.parameters[COUNTER_CURRENT_PAR + str(0)] = False     #For consistency, make reference side cocurrent
            self.UpdateStructure()
            
        elif paramName == NUSEGMENTS_PAR:
            self.UpdateStructure()
        
        elif paramName == REFERENCE_SIDE_PAR:
            if valueChanged: self.canRestart = False
            nuSides = self.GetParameterValue(NUSIDES_PAR)
            value = int(value)
            ref = self.parameters[COUNTER_CURRENT_PAR + str(value)]
            for i in range(nuSides):
                val = self.parameters[COUNTER_CURRENT_PAR + str(i)]
                if val == ref:
                    self.parameters[COUNTER_CURRENT_PAR + str(i)] = False
                else:
                    self.parameters[COUNTER_CURRENT_PAR + str(i)] = True
            #self.parameters[COUNTER_CURRENT_PAR + str(value)] = False     #For consistency, make reference side cocurrent
            self.UpdateStructure()
            
        elif paramName[:len(COUNTER_CURRENT_PAR)] == COUNTER_CURRENT_PAR:
            if valueChanged: self.canRestart = False
            #Just for consistency, make sure a bool integer is stored
            self.parameters[paramName] = bool(value)
            self.UpdateStructure()
        

    def ValidateParameter(self, paramName, value):
        """Validates the NUSTIN_PAR"""
        if not super(MultiSidedHeatExchangerOp, self).ValidateParameter(paramName, value):
            return 0
        if paramName == NUSIDES_PAR:
            #Not number or negative
            if not type(value) in (type(1), type(1.0)) or value < 2:
                return 0
        elif paramName == NUSEGMENTS_PAR:
            #Not number or lower than one
            if not type(value) in (type(1), type(1.0)) or value < 1:
                return 0
        elif paramName == REFERENCE_SIDE_PAR:
            #Not number or lower than one
            if not type(value) in (type(1), type(1.0)):
                return 0
            #attempting to set an index higher than the number of sides
            nuSides = self.GetParameterValue(NUSIDES_PAR)
            if nuSides == None:
                return 0
            elif nuSides <= int(value):
                return 0
        elif paramName[:len(COUNTER_CURRENT_PAR)] == COUNTER_CURRENT_PAR:
            try:
                idx = int(paramName[len(COUNTER_CURRENT_PAR):])
                refSide = self.GetParameterValue(REFERENCE_SIDE_PAR)
                #Can not change the side of the reference side
                if idx == refSide:
                    return 0
            except:
                return 0

            
        return 1
    

    def GetCorrespondingParameters(self, obj):
        """Passes the parameters that correspond to a specific obj"""
        if isinstance(obj, _Side):
            if not obj in self._sides:
                return None
            params = {}
            idx = self._sides.index(obj)
            
            val = self.GetParameterValue(COUNTER_CURRENT_PAR + str(idx))
            params[COUNTER_CURRENT_PAR] = val
            
            val = self.GetParameterValue(REFERENCE_SIDE_PAR)
            params[REFERENCE_SIDE_PAR] = val
            
            return params
    ##########################################################################################
    
    ## SIDE AND HEAT TRANSFER OBJECT ADMINSTRATION ###########################################
    def GetIndexOfSide(self, obj):
        """Passes the index of a side"""
        if isinstance(obj, _Side):
            if not obj in self._sides:
                return None
            idx = self._sides.index(obj)
            return idx
        
            
    def UpdateStructure(self):
        """Update contents and references based on current state of parent unitop"""
        super(MultiSidedHeatExchangerOp, self).UpdateStructure()
        
        
        #Actual data from unit operation
        nuSides = self.GetNumberOfSides()
        nuSegments = self.GetNumberOfSegments()

        #Current data in this object
        currNuSides = len(self._sides)
        currNuHTransfer = len(self._hTransfer)


        #Check if something can be done
        if nuSides == None or nuSegments == None:
            #Can't do much
            return

        #Fix for sides
        
        #del if necessary
        sigDel = []
        for i in range(currNuSides, nuSides, -1):
            name = self.GetChildName(self._sides[i-1])
            side = self._sides[i-1]
            
            #See if the sides are being used in signal objects
            try:
                for obj in self.signals.values():
                    if hasattr(obj, 'side') and obj.side is side:
                        obj.CleanUp()
                        sigDel.append(obj)
                    elif hasattr(obj, 'fromSide') and obj.fromSide is side:
                        obj.CleanUp()
                        sigDel.append(obj)
                    elif hasattr(obj, 'toSide') and obj.toSide is side:
                        obj.CleanUp()
                        sigDel.append(obj)
                            
                for obj in self.estimates.values():
                    if hasattr(obj, 'side') and obj.side is side:
                        obj.CleanUp()
                        sigDel.append(obj)
            except:
                pass
            
            del self._sides[i-1]
            self.DelUnitOperation(name)
           
        try:
            for obj in sigDel:
                self.DeleteObject(obj)
        except:
            pass

        #add if necessary
        for i in range(currNuSides, nuSides):
            side = _Side(self, self)
            self._sides.append(side)
            self.AddUnitOperation(side, SIDE_BASE_NAME + str(i))
            self.BorrowChildPort(side.GetPort(IN_PORT), IN_PORT + str(i))
            self.BorrowChildPort(side.GetPort(OUT_PORT), OUT_PORT + str(i))
            self.BorrowChildPort(side.GetPort(DELTAP_PORT), DELTAP_PORT + str(i))
            self.BorrowChildPort(side.GetPort(DELTAT_PORT), DELTAT_PORT + str(i))
            
        #Fix for heat transfer object

        #del if necessary        
        sigDel = []
        for i in range(currNuHTransfer, nuSides, -1):
            #Delete whole row
            for hTransfer in self._hTransfer[i-1]:
                if hTransfer:
                    #See if the sides are being used in signal objects
                    try:
                        for obj in self.signals.values():
                            if hasattr(obj, 'heatTran')and obj.heatTran is hTransfer:
                                obj.CleanUp()
                                sigDel.append(obj)
                    except:
                        pass
                        
                    name = self.GetChildName(hTransfer)
                    self.DelUnitOperation(name)
                    self._hTransferList.remove(hTransfer)
            del self._hTransfer[i-1]
        try:
            for obj in sigDel:
                self.DeleteObject(obj)
        except:
            pass

            
        #add if necessary
        for i in range(currNuHTransfer, nuSides):
            #Add a row
            self._hTransfer.append([])
            for j in range(i+1):
                #Keep a space for i == j but just store None
                if j == i:
                    self._hTransfer[i].append(None)
                else:
                    hTransfer = _HeatTransfer(self, self, self._sides[j], self._sides[i])
                    self._hTransfer[i].append(hTransfer)
                    self._hTransferList.append(hTransfer)
                    self.AddUnitOperation(hTransfer, HT_BASE_NAME + str(j) + '_' + str(i))
                    self.BorrowChildPort(hTransfer.GetPort(UA_PORT), UA_PORT + str(j) + '_' + str(i))
                    self.BorrowChildPort(hTransfer.GetPort(DELTAT_PORT + '_In'), DELTAT_PORT + str(j) + '_' + str(i) + '_In')
                    self.BorrowChildPort(hTransfer.GetPort(DELTAT_PORT + '_Out'), DELTAT_PORT + str(j) + '_' + str(i) + '_Out')
                    
        #Update strucuture of all children
        nuSegments = self.GetNumberOfSegments()
        for i in range(len(self._sides)):
            side = self._sides[i]
            side.UpdateStructure()
            try:
                var = self.convRes.get('T%i'%i, None)
                if var != None:
                    self.convRes['T%i'%i] = EquationSolver.CreateLinearDistArray(nuSegments+1, var[0], var[-1])

                var = self.convRes.get('H%i'%i, None)
                if var != None:
                    self.convRes['H%i'%i] = EquationSolver.CreateLinearDistArray(nuSegments+1, var[0], var[-1])

                var = self.convRes.get('Q%i'%i, None)
                if var != None:
                    self.convRes['Q%i'%i] = EquationSolver.CreateLinearDistArray(nuSegments, var[0], var[-1])    
                
                
                if side.TArray != None:
                    side.TArray = EquationSolver.CreateLinearDistArray(nuSegments+1, side.TArray[0], side.TArray[-1])

                if side.HArray != None:
                    side.HArray = EquationSolver.CreateLinearDistArray(nuSegments+1, side.HArray[0], side.HArray[-1])

                if side.QArray != None:
                    side.QArray = EquationSolver.CreateLinearDistArray(nuSegments, side.QArray[0], side.QArray[-1])

            except:
                pass
                    
        for hTransfer in self._hTransferList:
            hTransfer.UpdateStructure()
            try:
                idx0, idx1 = self.GetIndexOfSide(hTransfer._side1), self.GetIndexOfSide(hTransfer._side2)
                var = self.convRes.get('Q%i_%i' %(idx0, idx1), None)
                if var != None:
                    qTot = Numeric.sum(var)
                    self.convRes['Q%i_%i' %(idx0, idx1)] = (qTot/nuSegments)*ones(nuSegments, Float)
                
                var = self.convRes.get('UA%i_%i' %(idx0, idx1), None)
                if var != None:
                    self.convRes['ua%i_%i' %(idx0, idx1)] = (var/nuSegments)*ones(nuSegments, Float)
                   
                if hTransfer.duty != None:
                    qTot = Numeric.sum(hTransfer.duty)
                    hTransfer.duty = (qTot/nuSegments)*ones(nuSegments, Float)
                
                if hTransfer._UA != None:
                    self.ua = (hTransfer._UA/nuSegments)*ones(nuSegments, Float)
            
            except:
                pass
            
                    
        #Load a balance
        self._balance = Balance.Balance(Balance.ENERGY_BALANCE)
        self._balance.AddInput(self.GetPorts(IN|MAT))
        self._balance.AddOutput(self.GetPorts(OUT|MAT))
        
        #This blances are not needed as the side child unit op already calculates them
        self._matBalances = []
        for side in self._sides:
            bal = Balance.Balance(Balance.MOLE_BALANCE)
            bal.AddInput(side.GetPorts(IN|MAT))
            bal.AddOutput(side.GetPorts(OUT|MAT))
            self._matBalances.append(bal)

    def GetNumberOfSides(self):
        return self.GetParameterValue(NUSIDES_PAR)
    
    def GetNumberOfSegments(self):
        return self.GetParameterValue(NUSEGMENTS_PAR)

    def GetSide(self, idx):
        return self._sides[idx]
    ##########################################################################################
    
    ## SOLVE METHODS #########################################################################
    def Solve(self):
        
        self.unitOpMessage = ('NoMessage', )
        nuSides = len(self._sides)
        
        #Clear some profiles
        for side in self._sides:
            side.storedProfiles = {}
        for hTransfer in self._hTransferList:
            hTransfer.storedProfiles = {}
            
        #Put this stuff here rather than in LoadUnknwons so it always gets done
        activeSpecs = self.activeSpecs = []
        inactiveSpecs = self.inactiveSpecs = []
        for signal in self.signals.values():
            signal.Reset()
            if signal.value != None:
                activeSpecs.append(signal)
            else:
                inactiveSpecs.append(signal)            
            
        self.converged = False
        self.hComposite.Clear()
        self.cComposite.Clear()
        
        if hasattr(self, 'customSolver') and self.customSolver != None:
            self.customSolver.Solve()
            if self.IsForgetting():
                return
        
        super(MultiSidedHeatExchangerOp, self).Solve()
        if self.converged:
            self.ClearConvResults()
            self.StoreConvResults()
            if len(self._sides) > 2:
                try:
                    self.AssignSidesToComposites()
                except:
                    try:
                        self.hComposite.T = None
                        self.cComposite.T = None
                        self.hComposite.Q = None
                        self.cComposite.Q = None
                    except:
                        pass
            #for signal in self.inactiveSpecs:
            #Do all the signals for consistency checks
            for signal in self.signals.values():
                signal.AssignResultsToPort()
        else:
            try:
                if not self.IsForgetting():
                    if self.inactiveSpecs and self.segType == ENERGY_VAR:
                        for signal in self.inactiveSpecs:
                            if hasattr(signal, 'SolveFromPortValues'):
                                signal.SolveFromPortValues()
            except:
                pass
            
        self.CalcHeatTransfDTs()
        self.CheckTCross()
        
    def PrepareForSolve(self):
       
        ready = True
        
        self.segType = self.GetParameterValue(SEGMENTSBASE_PAR)
        self.findPhCh = self.GetParameterValue(FINDPH_CHANGE_PAR)
        
        #How to initialize?
        #Keep order so Restart overrides LastConverged
        initMode = SCRATCH_INIT
        if self.GetParameterValue(EquationSolver.TRYLASTCONVERGED_PAR) and self.canRestart:
            initMode = LASTCONV_INIT
        if self.GetParameterValue(EquationSolver.TRYTORESTART_PAR) and self.canRestart:
            initMode = RESTART_INIT
        self.initMode = initMode
        if not self.canRestart:
            self.ClearConvResults()
        self.canRestart = True
        
        if self.segType != ENERGY_VAR:
            self.segType = UA_VAR
        
        #Load sides
        for side in self._sides:
            if not side.PrepareForSolve():
                ready = False
           
        nuSides = len(self._sides)
        nuUAs = 0
        for hTransfer in self._hTransferList:
            if not hTransfer.PrepareForSolve():
                ready = False
            if hTransfer.UseInCalculations():
                nuUAs += 1
                        
        self.doQTransfer = True
        if nuUAs >= nuSides:
            #nuUAs are expected to be calculated and there can only solve for nuSides - 1
            self.doQTransfer = False

            
        #See if new T are known from DT
        self.CalcHeatTransfDTs()

        #Don't solve anything else if forgetting
        if self.IsForgetting():
            return False
        
        #Balance
        self.FlashAllPorts(CALCULATED_V|PARENT_V)
        for bal in self._matBalances:
            bal.DoBalance(CALCULATED_V|PARENT_V)
        self._balance.DoBalance(CALCULATED_V|PARENT_V)
        self.FlashAllPorts(CALCULATED_V|PARENT_V)
        
        
        #Returns None if a p or a composition is missing
        nuSpecs = self.LoadPropVectors(1)
        if nuSpecs == None: 
            ready = False
            self.balMode = False
        else:
            if len(self.missingVars) == 1:
                #Solve for the missing variable
                self.SolveBalance()
                self.balMode = True
            elif not self.missingVars:
                #Fake a missing varaible for redundancy check
                self.missingVarType = MF_IDX
                self.missingNuSide = 0
                self.SolveBalance()
                self.balMode = True
                self.missingVarType = None
                self.missingNuSide = None
            else:
                self.balMode = False
                
            
        if self.balMode and self.segType == ENERGY_VAR:
            self.SolveProfilesFromBalance(self.doQTransfer, True)
            self.AssignResults(None)
            self.FlashAllPorts()
            ready = False
                
        #Quick workaround so the simultaneous solver doesn't get triggered but still solves the balance
        if self.GetParameterValue(IGNORE_UA_PAR):
            ready = False
        
        if self.findPhCh and ready and len(self._sides) > 2:
            self.findPhCh = False
        
        self._numMethodSetings.solveMethod = self.GetParameterValue(EquationSolver.SOLVE_METH_PAR)
        self.needAllProfiles = True
        
        return ready
    
    def CalcHeatTransfDTs(self):
        """Solve for the delta T of the heat transfer children"""
        #an option to having this parent solving for the children would be to create T clones in the sides and T signals in the hTransfer
        #and connect them so the DeltaT get calculated right in the hTransfer unit op

        for hTransfer in self._hTransferList:
            s1, s2 = hTransfer._side1, hTransfer._side2
            
            s1IsCoCurr = s1.GetIsCoCurrent()
            s2IsCoCurr = s2.GetIsCoCurrent()
            if s1IsCoCurr:
                port1 = s1.GetPort(IN_PORT)
            else:
                port1 = s1.GetPort(OUT_PORT)
            if s2IsCoCurr:
                port2 = s2.GetPort(IN_PORT)
            else:
                port2 = s2.GetPort(OUT_PORT)
            self.CalcDeltaT(port1, port2, hTransfer._portDTIn) 
                
            if not s1IsCoCurr:
                port1 = s1.GetPort(IN_PORT)
            else:
                port1 = s1.GetPort(OUT_PORT)
            if not s2IsCoCurr:
                port2 = s2.GetPort(IN_PORT)
            else:
                port2 = s2.GetPort(OUT_PORT)
            self.CalcDeltaT(port1, port2, hTransfer._portDTOut)   
                        

    def CalcDeltaT(self, port1, port2, dtPort):
        """Calculates delta t for any combination. Always pass the PARENT_V flag as this is done for children u ops"""
        T1 = port1.GetPropValue(T_VAR)
        T2 = port2.GetPropValue(T_VAR)
        dt = dtPort.GetValue()
        dtStatus = dtPort._prop.GetCalcStatus()
        if not None in (T1, T2, dt): 
            dt = T1 - T2
            dtPort.SetValue(dt, CALCULATED_V|PARENT_V)
            return dt
        if dt != None:
            if T1 != None:
                port2.SetPropValue(T_VAR, T1 - dt, CALCULATED_V|PARENT_V)
            else:
                T2 = port2.GetPropValue(T_VAR)
                if T2 != None:
                    port1.SetPropValue(T_VAR, T2 + dt, CALCULATED_V|PARENT_V)
        elif T1 != None:
            T2 = port2.GetPropValue(T_VAR)
            if T2 != None:
                dt = T1 - T2
                dtPort.SetValue(dt, CALCULATED_V|PARENT_V)

        return dt 
    

    

    def SolveBalance(self):
        
        #In all this code, m stands for missing
        
        mVarType = self.missingVarType
        mNuSide = self.missingNuSide
        balVars = self.balanceVars
        mySign = self.sign
        
        if mNuSide == None: return #already solved
        
        #Load all the rows that are fully known
        h0 = concatenate((balVars[H0_IDX, :mNuSide], balVars[H0_IDX, mNuSide+1:]))
        h1 = concatenate((balVars[H1_IDX, :mNuSide], balVars[H1_IDX, mNuSide+1:]))
        mf = concatenate((balVars[MF_IDX, :mNuSide], balVars[MF_IDX, mNuSide+1:]))
        s =  concatenate((mySign[:mNuSide],       mySign[mNuSide+1:]))
        
        #Add all the energy balance but the missing term
        termA = sum( (h1 - h0) * s * mf )
        
        #Solve for the missing term inthe missing row
        if mVarType == H1_IDX:
            #Solve for enthalpy
            var = -termA / (balVars[MF_IDX, mNuSide] * mySign[mNuSide]) + balVars[H0_IDX, mNuSide]
            balVars[H1_IDX, mNuSide] = var
        elif mVarType == H0_IDX:
            #Solve for enthalpy
            var = termA / (balVars[MF_IDX, mNuSide] * mySign[mNuSide]) + balVars[H1_IDX, mNuSide]
            balVars[H0_IDX, mNuSide] = var
        else:
            #Solve for mole flow
            var = -termA / ((balVars[H1_IDX, mNuSide] - balVars[H0_IDX, mNuSide]) * mySign[mNuSide])
            balVars[MF_IDX, mNuSide] = var
            
            
            
    def SolveProfilesFromBalance(self, doQTransfer=True, doAllProfiles=True):
        """Solve the hx from the balance results"""  
           
        #Useful variables
        nuSegments = self.GetNumberOfSegments()
        nuSides = len(self._sides)
        CreateLinearDistArray = EquationSolver.CreateLinearDistArray
        balVars = self.balanceVars
        s = self.sign
        
        #Doing phase change ??
        findPhCh = self.findPhCh
        if self.findPhCh and nuSides > 2:
            self.InfoMessage('CantFindPhCh', (self.GetPath(),), MessageHandler.errorMessage)
            self.findPhCh = False
        if findPhCh: qPhChLst = []
        
        
        #Load vectors
        h0Vec       = balVars[H0_IDX]
        h1Vec       = balVars[H1_IDX]
        mfVec       = balVars[MF_IDX]
        p0Vec       = self.p0Vec
        p1Vec       = self.p1Vec
        t0Vec       = self.t0Vec
        t1Vec       = self.t1Vec
        vf0Vec      = self.vf0Vec
        vf1Vec      = self.vf1Vec
        fracsVec    = self.fracsVec
        fracsObjVec = self.fracsObjVec
        propsObjVec = self.propsObjVec
        isColdVec   = zeros(nuSides, Int)
        
        #Should it solve all the profiles and do PH flashes in each segment??
        if doAllProfiles: calcProf = ones(nuSides, Int)
        else: calcProf = zeros(nuSides, Int)
        
        nuSolids = self.NumberSolidPhases()
        #Flash what is needed and fill in the missing vectors
        for row, col in self.missingFlashIdx:
            calcProf[row] = 1
            thCaseObj = self._sides[row].GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            
            if col == H0_IDX: p, h = p0Vec[row], h0Vec[row]
            else: p, h = p1Vec[row], h1Vec[row]
            props = propsObjVec[row]
            cmps = fracsObjVec[row]
            props[P_VAR].SetValue(p, FIXED_V)
            props[H_VAR].SetValue(h, FIXED_V)
            results = thAdmin.Flash(prov, case, cmps, props, 2, (T_VAR, CP_VAR), nuSolids=nuSolids)
            if col == H0_IDX:
                t0Vec[row] = results.bulkProps[0]
                vf0Vec[row] = results.phaseFractions[0]
            else:
                t1Vec[row] = results.bulkProps[0]
                vf1Vec[row] = results.phaseFractions[0]
                
        isColdVec[:] = where((h1Vec-h0Vec)*s > 0.0, 1, 0)
        qVec = mfVec * (h1Vec - h0Vec) * s  #kJ/h
        
        #Fill in molar flows
        for i in range(nuSides):
            self._sides[i].molarFlow = mfVec[i]
        
            
        if findPhCh:
            for i in range(nuSides):
                vF0 = vf0Vec[i]
                vF1 = vf1Vec[i]
                
                #Different vap fracs?
                if vF0 != vF1:
                    vMax = max(vF0, vF1)
                    vMin = min(vF0, vF1)
                    
                    if vMax < 0.99999 and vMin > 0.00001:
                        #Condensing all the way. No phase change
                        continue
                    
                    else:
                        #There is for sure a phase change.
                        thCaseObj = self._sides[i].GetThermo()
                        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
                        
                        #Use pAvg for calcs
                        p0 = p0Vec[i]
                        p1 = p1Vec[i]
                        pAvg = (p0 + p1) / 2.0
                        props = MaterialPropertyDict()
                        props[P_VAR].SetValue(pAvg, FIXED_V)
                        
                        #Get compositions
                        cmps = fracsObjVec[i]
                    
                        qDew = None
                        qBub = None
                        if vMax >= 0.99999:
                            #It was vap and began condensing
                            props[VPFRAC_VAR].SetValue(1.0, FIXED_V)
                            
                            results = thAdmin.Flash(prov, case, cmps, props, 2, (H_VAR, T_VAR), nuSolids=nuSolids)
                            hDew = results.bulkProps[0]
                            qDew = mfVec[i] * (hDew - h0Vec[i])
                            qPhChLst.append(abs(qDew))
                                    
                        if vMin <= 0.00001:
                            #Got fully liquified
                            props[VPFRAC_VAR].SetValue(0.0, FIXED_V)
                            results = thAdmin.Flash(prov, case, cmps, props, 2, (H_VAR, T_VAR), nuSolids=nuSolids)
                            hBub = results.bulkProps[0]
                            qBub = mfVec[i] * (hBub - h0Vec[i])
                            qPhChLst.append(abs(qBub))
                            
            qPhChLst.sort()
            tempQArr = Numeric.absolute(CreateLinearDistArray(nuSegments+1, 0.0, qVec[0]))
            
            #Find phase changes for deciding how to divide segments
            lastIdx = 0
            for val in qPhChLst:
                for i in range(lastIdx, nuSegments):
                    if val >= tempQArr[i] and val <= tempQArr[i+1]:
                        if (val - tempQArr[i]) < (tempQArr[i+1] - val) or (i == nuSegments - 1):
                            tryIdx = i
                        else:
                            tryIdx = i+1
    
                        if tryIdx > lastIdx:
                            tempQArr[tryIdx] = val
                            lastIdx = tryIdx
                        elif lastIdx < nuSegments-1:
                            tryIdx = lastIdx+1
                            tempQArr[tryIdx] = val
                            lastIdx = tryIdx
                            
                        break
                    
            normSegs = tempQArr/tempQArr[-1]
        
        for nuSide in range(nuSides):
            side = self._sides[nuSide]
            
            if findPhCh:
                side.HArray = Numeric.sign(h1Vec[nuSide] - h0Vec[nuSide])*tempQArr/mfVec[nuSide] + h0Vec[nuSide]
                dp = p1Vec[nuSide] - p0Vec[nuSide]
                side.PArray = p0Vec[nuSide]*ones(nuSegments+1, Float) + normSegs*dp
            else:
                if doAllProfiles or calcProf[nuSide]:
                    side.HArray = CreateLinearDistArray(nuSegments+1, h0Vec[nuSide], h1Vec[nuSide])
                    side.PArray = CreateLinearDistArray(nuSegments+1, p0Vec[nuSide], p1Vec[nuSide])
            
            #QArray is kept (for different reasons) in kJ/h, hence hte 3.6 conversion is not needed
            side.QArray = side.molarFlow * (side.HArray[1:] - side.HArray[:-1])
            
            if doAllProfiles or calcProf[nuSide]:
                side.TArray = zeros(nuSegments+1, Float)
                for seg in range(nuSegments):
                    if seg:
                        side.TArray[seg] = side.GetTemperature(side.PArray[seg], side.HArray[seg], fracsVec[nuSide])
                side.TArray[0] = t0Vec[nuSide]
                side.TArray[-1] = t1Vec[nuSide]
            
            
        if not doQTransfer:
            return
            
        #Finally solve for the heat transfer objects
        self.CalcHeatTransfDTs()
        
        qTrMatrixCt = zeros((nuSides-1, nuSides-1), Float)
        
        col = 0
        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations():
                idx1 = self.GetIndexOfSide(hTransfer._side1)
                idx2 = self.GetIndexOfSide(hTransfer._side2)
                qTrMatrixCt[idx1, col] = 1.0
                try:
                    qTrMatrixCt[idx2, col] = -1.0
                except:
                    pass
                col+=1
                
        qTrMatrix = solve_linear_equations(array(qTrMatrixCt),-array(qVec[:-1]))
        hTrIdx = -1
        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations():
                hTrIdx += 1
                S1T = hTransfer._side1.TArray
                S2T = hTransfer._side2.TArray
                
                if findPhCh:
                    #It must be a two sided for now, hence the q side = q transfer
                    #I don't quite remember the sign that it hsould have, so just use the 
                    #sign from the liner solver
                    duty = Numeric.sign(qTrMatrix[hTrIdx]) * absolute(array(self._sides[0].QArray, Float))
                else:
                    qPerSeg = qTrMatrix[hTrIdx]/nuSegments
                    duty = hTransfer.duty = ones(nuSegments, Float) * qPerSeg
                    
                #lmtd = hTransfer.lmtd = zeros(nuSegments, Float)
                ua = hTransfer.ua = zeros(nuSegments, Float)
                
                lmtd = map(hTransfer.CalcLMTD, S1T[:-1], S2T[:-1], S1T[1:], S2T[1:])
                lmtd = hTransfer.lmtd = array(lmtd, Float)
                #for i in range(nuSegments):
                    #lmtd[i] = hTransfer.CalcLMTD(S1T[i], S2T[i], S1T[i+1], S2T[i+1])
                ua[:] = duty/lmtd
                hTransfer._UA = sum(ua)   #kJ/(h*K)
                #hTransfer._portUA.SetValue(sum(ua)/3.6, CALCULATED_V|PARENT_V)
                
        self.converged = True
            
            
        
    def SolveFromBalance(self, doQTransfer=True):
        """Solve the hx from the balance results"""  
        
        nuSegments = self.GetNumberOfSegments()
        nuSides = len(self._sides)
        CreateLinearDistArray = EquationSolver.CreateLinearDistArray
        
        if self.findPhCh and nuSides > 2:
            self.InfoMessage('CantFindPhCh', (self.GetPath(),), MessageHandler.errorMessage)
            self.findPhCh = False
        
        findPhCh = self.findPhCh
        if findPhCh:
            qPhChLst = []
        
        #Dimension some arrays
        h0Vec = zeros(nuSides, Float)
        h1Vec = zeros(nuSides, Float)
        p0Vec = zeros(nuSides, Float)
        p1Vec = zeros(nuSides, Float)
        t0Vec = zeros(nuSides, Float)
        t1Vec = zeros(nuSides, Float)
        vf0Vec = zeros(nuSides, Float)
        vf1Vec = zeros(nuSides, Float)
        qVec = zeros(nuSides, Float)
        moleFlowVec = zeros(nuSides, Float)
        isColdVec = zeros(nuSides, Int)
        isCoCurrVec = zeros(nuSides, Int)
        fracsVec = []
        
        nuSolids = self.NumberSolidPhases()
        #Iterate per side to get properties and finding phase changes
        for i in range(nuSides):
            side = self._sides[i]
            isCoCurrent = isCoCurrVec[i] = side.GetIsCoCurrent()
            portIn = side._portIn
            portOut = side._portOut
            
            moleFlowVec[i] = side.molarFlow = portIn.GetPropValue(MOLEFLOW_VAR)
            fracsVec.append(portIn.GetCompositionValues())
            
            if isCoCurrent:
                h0Vec[i] = portIn.GetPropValue(H_VAR)
                h1Vec[i] = portOut.GetPropValue(H_VAR)
                t0Vec[i] = portIn.GetPropValue(T_VAR)
                t1Vec[i] = portOut.GetPropValue(T_VAR)
                p0Vec[i] = portIn.GetPropValue(P_VAR)
                p1Vec[i] = portOut.GetPropValue(P_VAR)
                vf0Vec[i] = portIn.GetPropValue(VPFRAC_VAR)
                vf1Vec[i] = portOut.GetPropValue(VPFRAC_VAR)
                if h0Vec[i] > h1Vec[i]:
                    isColdVec[i] = 0
                else:
                    isColdVec[i] = 1
                qVec[i] = moleFlowVec[i] * (h1Vec[i] - h0Vec[i])
            else:
                h1Vec[i] = portIn.GetPropValue(H_VAR)
                h0Vec[i] = portOut.GetPropValue(H_VAR)
                t1Vec[i] = portIn.GetPropValue(T_VAR)
                t0Vec[i] = portOut.GetPropValue(T_VAR)
                p1Vec[i] = portIn.GetPropValue(P_VAR)
                p0Vec[i] = portOut.GetPropValue(P_VAR)
                vf1Vec[i] = portIn.GetPropValue(VPFRAC_VAR)
                vf0Vec[i] = portOut.GetPropValue(VPFRAC_VAR)
                if h1Vec[i] > h0Vec[i]:
                    isColdVec[i] = 0
                else:
                    isColdVec[i] = 1
                qVec[i] = moleFlowVec[i] * (h0Vec[i] - h1Vec[i])
                    
            
            if findPhCh:
                
                vF0 = vf0Vec[i]
                vF1 = vf1Vec[i]
                
                #Different vap fracs?
                if vF0 != vF1:
                    vMax = max(vF0, vF1)
                    vMin = min(vF0, vF1)
                    
                    if vMax < 0.99999 and vMin > 0.00001:
                        #Condensing all the way. No phase change
                        pass
                    
                    else:
                        #There is for sure a phase change.

                        thCaseObj = self.GetThermo()
                        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
                        
                        #Use pAvg for calcs
                        p0 = portIn.GetPropValue(P_VAR)
                        p1 = portOut.GetPropValue(P_VAR)
                        pAvg = (p0 + p1) / 2.0
                        props = MaterialPropertyDict()
                        props[P_VAR].SetValue(pAvg, FIXED_V)
                        
                        
                        #Get composition and load it into BasicProperties
                        compounds = CompoundList(None)
                        for cmpIdx in range(len(fracsVec[i])):
                            prop = BasicProperty(FRAC_VAR)
                            prop.SetValue(fracsVec[i][cmpIdx], FIXED_V)
                            compounds.append(prop)
                        compounds.Normalize()
                    
                        qDew = None
                        qBub = None
                        if vMax >= 0.99999:
                            #It was vap and began condensing
                            props[VPFRAC_VAR].SetValue(1.0, FIXED_V)
                            
                            results = thAdmin.Flash(prov, case, compounds, props, 2, (H_VAR, T_VAR), nuSolids=nuSolids)
                            hDew = results.bulkProps[0]
                            qDew = moleFlowVec[i] * (hDew - h0Vec[i])
                            qPhChLst.append(abs(qDew))
                                    
                        if vMin <= 0.00001:
                            #Got fully liquified
                            props[VPFRAC_VAR].SetValue(0.0, FIXED_V)
                            results = thAdmin.Flash(prov, case, compounds, props, 2, (H_VAR, T_VAR), nuSolids=nuSolids)
                            hBub = results.bulkProps[0]
                            qBub = moleFlowVec[i] * (hBub - h0Vec[i])
                            qPhChLst.append(abs(qBub))
                        

        if findPhCh:
            qPhChLst.sort()
            tempQArr = Numeric.absolute(CreateLinearDistArray(nuSegments+1, 0.0, qVec[0]))
            
            #Find phase changes for deciding how to divide segments
            lastIdx = 0
            for val in qPhChLst:
                for i in range(lastIdx, nuSegments):
                    if val >= tempQArr[i] and val <= tempQArr[i+1]:
                        if (val - tempQArr[i]) < (tempQArr[i+1] - val) or (i == nuSegments - 1):
                            tryIdx = i
                        else:
                            tryIdx = i+1
    
                        if tryIdx > lastIdx:
                            tempQArr[tryIdx] = val
                            lastIdx = tryIdx
                        elif lastIdx < nuSegments-1:
                            tryIdx = lastIdx+1
                            tempQArr[tryIdx] = val
                            lastIdx = tryIdx
                            
                        break
                    
            normSegs = tempQArr/tempQArr[-1]
        
        for nuSide in range(nuSides):
            side = self._sides[nuSide]
            portIn = side._portIn
            portOut = side._portOut
            
            if findPhCh:
                side.HArray = Numeric.sign(h1Vec[nuSide] - h0Vec[nuSide])*tempQArr/moleFlowVec[nuSide] + h0Vec[nuSide]
                dp = p1Vec[nuSide] - p0Vec[nuSide]
                side.PArray = p0Vec[nuSide]*ones(nuSegments+1, Float) + normSegs*dp
            else:
                side.HArray = CreateLinearDistArray(nuSegments+1, h0Vec[nuSide], h1Vec[nuSide])
                side.PArray = CreateLinearDistArray(nuSegments+1, p0Vec[nuSide], p1Vec[nuSide])
            
            side.QArray = zeros(nuSegments, Float)
            side.TArray = zeros(nuSegments+1, Float)
            for seg in range(nuSegments):
                #QArray is kept (for different reasons) in kJ/h, hence hte 3.6 conversion is not needed
                side.QArray[seg] = moleFlowVec[nuSide]* (side.HArray[seg+1] - side.HArray[seg])
                if seg:
                    side.TArray[seg] = side.GetTemperature(side.PArray[seg], side.HArray[seg], fracsVec[nuSide])
            side.TArray[0] = t0Vec[nuSide]
            side.TArray[-1] = t1Vec[nuSide]
            
            
        self.converged = True
        
        if not doQTransfer:
            return
            
        #Finally solve for the heat transfer objects
        self.CalcHeatTransfDTs()
        
        qTrMatrixCt = zeros((nuSides-1, nuSides-1), Float)
        
        col = 0
        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations():
                idx1 = self.GetIndexOfSide(hTransfer._side1)
                idx2 = self.GetIndexOfSide(hTransfer._side2)
                qTrMatrixCt[idx1, col] = 1.0
                try:
                    qTrMatrixCt[idx2, col] = -1.0
                except:
                    pass
                col+=1
                
        qTrMatrix = solve_linear_equations(array(qTrMatrixCt),-array(qVec[:-1]))
        hTrIdx = -1
        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations():
                hTrIdx += 1
                S1T = hTransfer._side1.TArray
                S2T = hTransfer._side2.TArray
                
                if findPhCh:
                    #It must be a two sided for now, hence the q side = q transfer
                    #I don't quite remember the sign that it hsould have, so just use the 
                    #sign from the liner solver
                    duty = sign(qTrMatrix[hTrIdx]) * absolute(array(self._sides[0].QArray, Float))
                else:
                    qPerSeg = qTrMatrix[hTrIdx]/nuSegments
                    duty = hTransfer.duty = ones(nuSegments, Float) * qPerSeg
                    
                lmtd = hTransfer.lmtd = zeros(nuSegments, Float)
                ua = hTransfer.ua = zeros(nuSegments, Float)
                
                for i in range(nuSegments):
                    lmtd[i] = hTransfer.CalcLMTD(S1T[i], S2T[i], S1T[i+1], S2T[i+1])
                ua[:] = duty/lmtd
                hTransfer._UA = sum(ua)   #kJ/(h*K)
                hTransfer._portUA.SetValue(sum(ua)/3.6, CALCULATED_V|PARENT_V)
                
        self.converged = True
        
    
    def SolveForMissingMoleFlow(self):
        """Assume that all ports are flashed, and all mole flows but one are also known.
        Solve for the missing mole flow. Return true if success"""
        #Perhpaps we could still do a balance
        self.LoadPropVectors(False)
        nuSides = len(self._sides)
        try: 
            TInVec = self._estTInVec
            TOutVec = self._estTOutVec
            HInVec = self._estHInVec
            HOutVec = self._estHOutVec
            moleFlowVec = self._estMoleFlowVec
            
            dh = array(HOutVec, Float) - array(HInVec, Float)
            acum = 0.0
            missIdx = None
            for i in range(nuSides):
                if moleFlowVec[i] != None: 
                    acum += moleFlowVec[i]*dh[i]
                else:
                    missIdx = i
                    denom = dh[i]
            flow = -acum/denom
            self._sides[missIdx]._portIn.SetPropValue(MOLEFLOW_VAR, flow, CALCULATED_V|PARENT_V)
            self._sides[missIdx]._portOut.SetPropValue(MOLEFLOW_VAR, flow, CALCULATED_V|PARENT_V)
            
            return True
        except:
            return False
        

    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        
        #Load the variables into the proper vectors
        balVars = self.balanceVars
        cnt = 0
        for nuSide, varType in self.missingVars[:-1]:
            balVars[varType, nuSide] = x[cnt]
            cnt += 1
        
        #Solve the balance
        self.SolveBalance()
        
        #Solve profiles
        self.SolveProfilesFromBalance(self.doQTransfer, self.needAllProfiles)
        self.needAllProfiles = False
        
        #Recalculate composite sides if necessary
        if self.refreshComp:
            self.AssignSidesToComposites()
        
        #Calculate the errors in the specs
        eqnNo = 0
        for spec in self.activeSpecs:
            rhs[eqnNo] = spec.Error()
            eqnNo += 1
        for spec in self.portSpecs:
            rhs[eqnNo] = spec.Error()
            eqnNo += 1
        return eqnNo
        
    def CalculateRHSOld(self, x, rhs, isFix, initx, eqnNo=0):
        """Calculates the right hand side of the design equations"""
        nuSegments = self.GetNumberOfSegments()
        
        for side in self._sides:
            eqnNo = side.CalculateRHS(x, rhs, isFix, initx, eqnNo)
        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations():
                eqnNo = hTransfer.CalculateRHS(x, rhs, isFix, initx, eqnNo)

        #Contribute the heat balance eqns -- between the sides and the heat transfer object.
        for i in range(nuSegments):
            for side in self._sides:
                if side.GetIsCoCurrent():
                    mySign = +1
                else:
                    mySign = -1
                mySumQ = mySign*side.QArray[i]
                for hTransfer in self._hTransferList:
                    if hTransfer.UseInCalculations() and (hTransfer._side1==side or hTransfer._side2==side):
                        if hTransfer._side1==side:
                            mySumQ += hTransfer.duty[i]
                        else:
                            mySumQ -= hTransfer.duty[i]
                rhs[eqnNo] = mySumQ/side.scaleFactorQ
                eqnNo += 1
                
                
        if self.refreshComp:
            self.AssignSidesToComposites()
        #now do equations for specs
        for spec in self.activeSpecs:
            rhs[eqnNo] = spec.Error()
            eqnNo += 1
            
        return eqnNo
    


    def CalculateJacobianOld(self, x, j, isFix, initx, eqnNo=0):

        #zero out the matrix
        for i2 in range(len(x)):
            for j2 in range(len(x)):
                j[i2][j2] = 0.0

                
        for side in self._sides:
            eqnNo = side.CalculateJacobian(x, j, isFix, initx, eqnNo)

        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations():
                eqnNo = hTransfer.CalculateJacobian(x, j, isFix, initx, eqnNo)
                        
                        
        nuSegments = self.GetNumberOfSegments()

        for i in range(nuSegments):
            for side in self._sides:
                if side.GetIsCoCurrent():
                    mySign = +1
                else:
                    mySign = -1
                j[eqnNo][side.QIndex[i]] = mySign*1.0/side.scaleFactorQ
                isCoCurrent = side.GetIsCoCurrent()
                isReference = side.GetIsReference()
                for hTransfer in self._hTransferList:
                    if hTransfer.UseInCalculations() and (hTransfer._side1==side or hTransfer._side2==side):
                        if hTransfer._side1==side:
                            j[eqnNo][hTransfer.dutyIndex[i]] = +1.0/side.scaleFactorQ
                        else:
                            j[eqnNo][hTransfer.dutyIndex[i]] = -1.0/side.scaleFactorQ
                eqnNo += 1
                
        for spec in self.activeSpecs:
            #For now this spec can only be a T aproach spec
            spec.LoadJacobianTerms(j[eqnNo])
            eqnNo += 1
            
        return eqnNo
    
    def SanityCheckOld(self, x, initx):
        """Method used in case is supports a check for new values for x"""
        for side in self._sides:
            if hasattr(side, 'SanityCheck'):
                side.SanityCheck(x, initx)
        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations() and hasattr(hTransfer, 'SanityCheck'):
                hTransfer.SanityCheck(x, initx)    
    
    ##########################################################################################
    
    ## LOAD DATA #########################################################################
    def LoadPropVectors(self, useEst=False):
        """Load T, H, mole flows, etc as vectors. Return number of know variables"""
        
        #Initialize vars
        nuSides  = len(self._sides)
        nuSpecs = self.nuSpecs = 0
        nuUASpecs = self.nuUASpecs = 0
        
        
        #Estimates
        estimates = []
        if useEst: estimates = self.estimates.values()
        estTInVec      = self._estTInVec  = []
        estTOutVec     = self._estTOutVec = []
        estMFVec       = self._estMoleFlowVec = []
        

        #Clear these variables
        mFlashIdx = self.missingFlashIdx = []          #Keep track of everything that is missing a flash
        mVars     = self.missingVars = []              #Keep track of all
        mVarType     = self.missingVarType = None            #Keep track of last one
        mNuSide  = self.missingNuSide = None         #Keep track of last one
        
        
        #Dimension some arrays
        balVars = self.balanceVars = zeros((3, nuSides), Float)
        s       = self.sign        = ones(nuSides, Float)
        h0Vec   = self.h0Vec       = zeros(nuSides, Float)
        h1Vec   = self.h1Vec       = zeros(nuSides, Float)
        p0Vec   = self.p0Vec       = zeros(nuSides, Float)
        p1Vec   = self.p1Vec       = zeros(nuSides, Float)
        t0Vec   = self.t0Vec       = zeros(nuSides, Float)
        t1Vec   = self.t1Vec       = zeros(nuSides, Float)
        vf0Vec  = self.vf0Vec      = zeros(nuSides, Float)
        vf1Vec  = self.vf1Vec      = zeros(nuSides, Float)
        mfVec   = self.mfVec       = zeros(nuSides, Float)
        fracsVec       = self.fracsVec        = []
        fracsObjVec    = self.fracsObjVec     = []
        propsObjVec    = self.propsObjVec     = []
        counterCurrVec = self._counterCurrVec = []
        
        self.portSpecs = []
        
        #Loop per side
        for i in range(nuSides):
            side = self._sides[i]
            isCoCurrent = not side.GetIsCounterCurrent()
            counterCurrVec.append(not isCoCurrent)
            
            pIn = side._portIn
            t  = pIn.GetPropValue(T_VAR)
            h  = pIn.GetPropValue(H_VAR)
            vf = pIn.GetPropValue(VPFRAC_VAR)
            p  = pIn.GetPropValue(P_VAR)
            mf = pIn.GetPropValue(MOLEFLOW_VAR)
            z  = pIn.GetCompositionValues()
            
            #Check if they add for a spec count and if there are estimates
            if h != None: 
                nuSpecs += 1
            else:
                for est in estimates:
                    if isinstance(est, EstimateTemperature) and (est.side is side) and (est.atInlet):
                        t = est.port.GetValue()
                        break
                    
            if mf != None: 
                nuSpecs += 1
            
            #Vector for estimates
            estTInVec.append(t)
            estMFVec.append(mf)
            
                
            if isCoCurrent:
                if h != None: 
                    h0Vec[i] = h
                    if t != None: t0Vec[i] = t
                    if vf != None: vf0Vec[i] = vf
                else:
                    mNuSide = i
                    mVarType = H0_IDX
                    mVars.append((mNuSide, mVarType))
                    mFlashIdx.append((mNuSide, mVarType))
                if p != None: p0Vec[i] = p
                else: 
                    #self.unitOpMessage = ('Missing Pressure', ('Side %i' %i))
                    self.unitOpMessage = ('MissingVariable', (P_VAR, 'Side %i' %i))
                    return None
            else:
                if h != None: 
                    h1Vec[i] = h
                    if t != None: t1Vec[i] = t
                    if vf != None: vf1Vec[i] = vf
                else:
                    mNuSide = i
                    mVarType = H1_IDX
                    mVars.append((mNuSide, mVarType))
                    mFlashIdx.append((mNuSide, mVarType))
                if p != None: p1Vec[i] = p
                else: 
                    #self.unitOpMessage = ('Missing Pressure', ('Side %i' %i))
                    self.unitOpMessage = ('MissingVariable', (P_VAR, 'Side %i' %i))
                    return None
            #Flash variables
            if z != None:
                compounds = CompoundList(None)
                for cmpIdx in range(len(z)):
                    prop = BasicProperty(FRAC_VAR)
                    prop.SetValue(z[cmpIdx], FIXED_V)
                    compounds.append(prop)
                compounds.Normalize()
                fracsObjVec.append(compounds)
                fracsVec.append(z)
            else:
                fracsObjVec.append(None)
                return None
            propsObjVec.append(MaterialPropertyDict())
            
            
            #Check if they add for a spec count and if there are estimates
            pOut = side._portOut
            t  = pOut.GetPropValue(T_VAR)
            h  = pOut.GetPropValue(H_VAR)
            vf = pOut.GetPropValue(VPFRAC_VAR)
            p  = pOut.GetPropValue(P_VAR)
            if h != None: 
                nuSpecs += 1
            else:
                for est in estimates:
                    if isinstance(est, EstimateTemperature) and (est.side is side) and (not est.atInlet):
                        t = est.port.GetValue()
                        break
                    
            #Vectors for estimates
            estTOutVec.append(t)
            
            #Vectors for balance
            if not isCoCurrent:
                if h != None: 
                    h0Vec[i] = h
                    if t != None:  t0Vec[i] = t
                    if vf != None: vf0Vec[i] = vf
                else:
                    mNuSide = i
                    mVarType = H0_IDX
                    mVars.append((mNuSide, mVarType))
                    mFlashIdx.append((mNuSide, mVarType))
                if p != None:  p0Vec[i] = p
                else: 
                    #self.unitOpMessage = ('Missing Pressure', ('Side %i' %i))
                    self.unitOpMessage = ('MissingVariable', (P_VAR, 'Side %i' %i))
                    return None
            else:
                if h != None: 
                    h1Vec[i] = h
                    if t != None:  t1Vec[i] = t
                    if vf != None: vf1Vec[i] = vf
                else:
                    mNuSide = i
                    mVarType = H1_IDX
                    mVars.append((mNuSide, mVarType))
                    mFlashIdx.append((mNuSide, mVarType))
                if p != None:  p1Vec[i] = p
                else: 
                    #self.unitOpMessage = ('Missing Pressure', ('Side %i' %i))
                    self.unitOpMessage = ('MissingVariable', (P_VAR, 'Side %i' %i))
                    return None
                
                
            #Vectors for balance
            if mf != None:
                mfVec[i] = mf
            else:
                mNuSide = i
                mVarType = MF_IDX
                mVars.append((mNuSide, mVarType))                
                
            #Do UA
            for j in range(i):
                prop = self.GetPort(UA_PORT + str(j) + '_' + str(i)).GetProperty()
                UA = prop.GetValue()
                status = prop.GetCalcStatus()
                if UA and (status & (FIXED_V|PASSED_V)):
                    spec = PortUASpec(self, j, i, UA)
                    self.portSpecs.append(spec)
                    nuUASpecs += 1
                    nuSpecs += 1
                    
        
        #See if we 
        for i in range(nuSides):
            for j in range(i):
                if not t0Vec[j] and not t0Vec[i]:
                    prop = prop = self.GetPort('%s%i_%i_In' %(DELTAT_PORT, j, i)).GetProperty()
                    val = prop.GetValue()
                    status = prop.GetCalcStatus()
                    if val != None and (status & (FIXED_V|PASSED_V)):
                        spec = PortDTAcrossSidesSpec(self, j, i, 1, val)
                        self.portSpecs.append(spec)
                        nuSpecs += 1
                        
                if not t1Vec[j] and not t1Vec[i]:
                    prop = prop = self.GetPort('%s%i_%i_Out' %(DELTAT_PORT, j, i)).GetProperty()
                    val = prop.GetValue()
                    status = prop.GetCalcStatus()
                    if val != None and (status & (FIXED_V|PASSED_V)):
                        spec = PortDTAcrossSidesSpec(self, j, i, 0, val)
                        self.portSpecs.append(spec)
                        nuSpecs += 1    
            
                    
        self.sign = where(counterCurrVec, -1.0, 1.0)
        
        self.missingVars = mVars
        self.missingVarType = mVarType
        self.missingNuSide = mNuSide
        self.nuUASpecs = nuUASpecs
        self.nuSpecs = nuSpecs
        balVars[H0_IDX, :] = h0Vec[:]
        balVars[H1_IDX, :] = h1Vec[:]
        balVars[MF_IDX, :] = mfVec[:]
        
        self.scaleFactorH = max( 8000.0, max(absolute(h0Vec)) )
        self.scaleFactorF = max( 100.0, max(absolute(mfVec)) )
        
        return nuSpecs
    
    
    def AssignSidesToComposites(self):
        """Assign cold sides and hot sides to the corresonding composite"""
        cSides = []
        hSides = []
        for side in self._sides:
            if side.GetIsCounterCurrent():
                if side.HArray[0] > side.HArray[-1]:
                    cSides.append(side)
                else:
                    hSides.append(side)
            else:
                if side.HArray[0] > side.HArray[-1]:
                    hSides.append(side)
                else:
                    cSides.append(side)
        self.hComposite.SetSides(hSides)
        self.cComposite.SetSides(cSides)
        self.hComposite.UpdateProfiles()
        self.cComposite.UpdateProfiles()
        self.hComposite.MergeData(self.cComposite)
        
    def CheckTCross(self):
        
        #Check for T crosses
        nuSides = len(self._sides)
        if nuSides == 2:
            side0 = self._sides[0]
            side1 = self._sides[1]
            
            t0_0 = side0._portIn.GetPropValue(T_VAR)
            t0_1 = side0._portOut.GetPropValue(T_VAR)
            if side0.GetIsCounterCurrent() != side1.GetIsCounterCurrent():
                t1_0 = side1._portOut.GetPropValue(T_VAR)
                t1_1 = side1._portIn.GetPropValue(T_VAR)
            else:
                t1_1 = side1._portOut.GetPropValue(T_VAR)
                t1_0 = side1._portIn.GetPropValue(T_VAR)
            
            if t0_0 and t0_1 and t1_0 and t1_1:
                dt1 = t0_0 - t1_0
                dt2 = t0_1 - t1_1
                if dt1 * dt2 < 0.0:
                    self.unitOpMessage = ('TemperatureCross', (dt1, dt2, self.GetPath()))
                    if not self.IsForgetting():
                        self.InfoMessage('TemperatureCross', (dt1, dt2, self.GetPath()), MessageHandler.errorMessage)
                    
                else:
                    tArr0 = side0.GetArray(T_VAR)
                    tAtt1 = side1.GetArray(T_VAR)
                    if tArr0 and tAtt1:
                        deltas = tArr0 - tAtt1
                        if min(deltas) < 0.0 and max(deltas) > 0.0:
                            self.unitOpMessage = ('InternalTCross', (self.GetPath(), ))
                            if not self.IsForgetting():
                                self.InfoMessage('InternalTCross', (self.GetPath(), ))
                        else:
                            hIn_s0 = side0._portIn.GetPropValue(H_VAR)
                            hOut_s0 = side0._portOut.GetPropValue(H_VAR)
                            if hIn_s0 != None and hOut_s0 != None:
                                zeroiscold = hIn_s0 < hOut_s0
                                if (zeroiscold and max(deltas) > 0.0) or (not zeroiscold and min(deltas) < 0.0):
                                    self.unitOpMessage = ('TemperatureCross', (dt1, dt2, self.GetPath()))
                                    if not self.IsForgetting():
                                        self.InfoMessage('TemperatureCross', (dt1, dt2, self.GetPath()), MessageHandler.errorMessage)
                                else:
                                    try:
                                        if self.converged:
                                            self.unitOpMessage = ('OK', )
                                    except:
                                        pass
                            
        elif nuSides > 2:
            outTLst = []
            inTLst = []
            #Load the min and max inlets and all the outlets
            for side in self._sides:
                outT = side._portOut.GetPropValue(T_VAR)
                if not outT: return
                inT = side._portIn.GetPropValue(T_VAR)
                if not inT: return
                
                outTLst.append(outT)
                inTLst.append(inT)
                
            #Check if any of the outlet temperatures is beyond the limits set by the inlet Ts
            if min(outTLst) < min(inTLst) or max(outTLst) > max(inTLst):
                self.unitOpMessage = ('TemperatureCross', (self.GetPath(), ))
                if not self.IsForgetting():
                    self.InfoMessage('TemperatureCross', (min(outTLst) - min(inTLst), -max(outTLst) + max(inTLst), self.GetPath()), MessageHandler.errorMessage)
            else:
                try:
                    if self.converged:
                        self.unitOpMessage = ('OK', )
                except:
                    pass
                
        return

    

    def LoadUnknowns(self, u):
        if not super(MultiSidedHeatExchangerOp, self).LoadUnknowns(u):
            return False
        
        nuSegments = self.GetNumberOfSegments()
        nuSides = self.GetNumberOfSides()
        u = self._unknowns        
        
        #See if there are enough specs for solving
        if self.initMode == LASTCONV_INIT:
            if not self.RetrieveConvResults():
                self.initMode == SCRATCH_INIT
        initMode = self.initMode
        
        #Regardless of init mode, let it still estimate vals
        self.refreshComp = False
        for spec in self.activeSpecs:
            if isinstance(spec, HXObject_CompositeSide):
                self.refreshComp = True
                
                
        #Spec count already added the balance specs (mole flows and enthalpies)
        nuSpecs = self.nuSpecs
        nuSpecs += len(self.activeSpecs)
        self.nuSpecs = nuSpecs
        nuSpecsNeeded = self.GetNuSpecsNeeded()
        
        #if self.nuUASpecs:
            #for hTransfer in self._hTransferList:
                #nuUAs = 0
                #if hTransfer.UseInCalculations():
                    #nuUAs += 1
                #if nuUAs >= nuSides:
                    ##nuUAs are expected to be calculated and there can only solve for nuSides - 1
                    #return False
        
        if nuSpecs < nuSpecsNeeded:
            missSpecs = nuSpecsNeeded - nuSpecs
            #self.unitOpMessage = ('Missing %i Specs' %missSpecs, )
            self.unitOpMessage = ('MissingSpecs', (missSpecs,))
            return False
        elif nuSpecs > nuSpecsNeeded:
            overSpecs = nuSpecs - nuSpecsNeeded
            self.unitOpMessage = ('Over Specified by %i' %overSpecs, )
            self.InfoMessage('TooManyTowerSpecs', (nuSpecs, nuSpecsNeeded, self.GetPath()))
            return False
        
        #Load estimates
        if not self.LoadMoleFlowEstimates(): 
            self.InfoMessage('CantEstimate', (MOLEFLOW_VAR, self.GetPath()))
            return False
        if not self.LoadTemperatureEstimates(): 
            self.InfoMessage('CantEstimate', (T_VAR, self.GetPath()))
            return False
        
        
        initMode = self.initMode
        
        #Create iteration variables right here
        estTOutVec     = self._estTOutVec
        estTInVec      = self._estTInVec
        estMFVec       = self._estMoleFlowVec
        counterCurrVec = self._counterCurrVec
        for nuSide, varType in self.missingVars[:-1]:
            side = self._sides[nuSide]
            
            if varType == H0_IDX:
                if not counterCurrVec[nuSide]:
                    t = self.t0Vec[nuSide] = estTInVec[nuSide]
                else:
                    t = self.t0Vec[nuSide] = estTOutVec[nuSide]
                p = self.p0Vec[nuSide]
                
                if initMode:
                    try:
                        h = side.HArray[0]
                        if h == None:
                            initMode = self.initMode = SCRATCH_INIT
                    except:
                        initMode = self.initMode = SCRATCH_INIT
                if initMode == SCRATCH_INIT:
                    fracs = self.fracsVec[nuSide]
                    h = side.GetEnthalpy(p, t, fracs)
                name = 'H_%s_%s' %(nuSide, varType)
                tempUnkVar = EquationSolver.SolverVariable(name, h, h, False, self.scaleFactorH)
                u.AddUnknown(tempUnkVar) #Returns the index where the unk was put
                
                
            elif varType == H1_IDX:
                if not counterCurrVec[nuSide]:
                    t = self.t1Vec[nuSide] = estTOutVec[nuSide]
                else:
                    t = self.t1Vec[nuSide] = estTInVec[nuSide]
                p = self.p1Vec[nuSide]

                if initMode:
                    try:
                        h = side.HArray[-1]
                        if h == None:
                            initMode = self.initMode = SCRATCH_INIT
                    except:
                        initMode = self.initMode = SCRATCH_INIT
                if initMode == SCRATCH_INIT:
                    fracs = self.fracsVec[nuSide]
                    h = side.GetEnthalpy(p, t, fracs)
                name = 'H_%s_%s' %(nuSide, varType)
                tempUnkVar = EquationSolver.SolverVariable(name, h, h, False, self.scaleFactorH)
                u.AddUnknown(tempUnkVar) #Returns the index where the unk was put
                
                
            elif varType == MF_IDX:
                if initMode:
                    try:
                        mf = float(side.molarFlow)
                    except:
                        initMode = self.initMode = SCRATCH_INIT
                if initMode == SCRATCH_INIT:
                    mf = self.mfVec[nuSide] = estMFVec[nuSide]
                name = 'MF_%s_%s' %(nuSide, varType)
                tempUnkVar = EquationSolver.SolverVariable(name, mf, mf, False, self.scaleFactorF)
                u.AddUnknown(tempUnkVar) #Returns the index where the unk was put
                
                
                    
        if not self.findPhCh and self.GetParameterValue(FINDPH_CHANGE_PAR):
            self.InfoMessage('CantFindPhCh', (self.GetPath(),), MessageHandler.errorMessage)
            
        return True
    
    
    def LoadUnknownsOld(self, u):
        if not super(MultiSidedHeatExchangerOp, self).LoadUnknowns(u):
            return False
        
        if self.GetParameterValue(IGNORE_UA_PAR):
            return False
        
        nuSegments = self.GetNumberOfSegments()
        nuSides = self.GetNumberOfSides()
        u = self._unknowns
    
        #Get thermo
        self._thCaseObj = self.GetThermo()
        if not self._thCaseObj: return False
        
        #See if there are enough specs for solving
        if self.initMode == LASTCONV_INIT:
            if not self.RetrieveConvResults():
                self.initMode == SCRATCH_INIT
            
        
        #Regardless of init mode, let it still estimate vals
        self.refreshComp = False
        for spec in self.activeSpecs:
            if not isinstance(spec, TemperatureApproachVar):
                self._numMethodSetings.solveMethod = EquationSolver.SECANT
            if isinstance(spec, HXObject_CompositeSide):
                self.refreshComp = True
                
        
        #First load the specs from material ports
        nuSpecsNeeded = self.GetNuSpecsNeeded()
        nuSpecs = self.LoadPropVectors(True)
            
        nuSpecs += len(self.activeSpecs)
        
        if nuSpecs < nuSpecsNeeded: return False
        
        if not self.LoadMoleFlowEstimates(): return False
        
        if not self.LoadTemperatureEstimates(): return False
        
        for side in self._sides:
            if not side.LoadUnknowns(u): return False

        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations():
                if not hTransfer.LoadUnknowns(u): return False
                    
        if not self.findPhCh and self.GetParameterValue(FINDPH_CHANGE_PAR) :
            self.InfoMessage('CantFindPhCh', (self.GetPath(),), MessageHandler.errorMessage)
            
        return True
    
                        

    def LoadMoleFlowEstimates(self):
        """Fill in the missing mole flows in mole flow est"""
        nuSides = len(self._sides)
        moleFlowVec = self._estMoleFlowVec
        if None in moleFlowVec:
            val = max(moleFlowVec)
            if val == None:
                val = 10.0
                
            for i in range(nuSides):
                if moleFlowVec[i] == None:
                    moleFlowVec[i] = val
                    
        return True
    
    def LoadTemperatureEstimates(self):
        """Fill in the missing T"""
        nuSides = len(self._sides)
        TInVec = self._estTInVec
        TOutVec = self._estTOutVec
        
        for i in range(nuSides-1):
            s0, s1 = self._sides[i], self._sides[i+1]
            T0In, T0Out = TInVec[i], TOutVec[i]
            T1In, T1Out = TInVec[i+1], TOutVec[i+1]
            lstT = [T0In, T0Out, T1In, T1Out]
            nuNones = lstT.count(None)     
            
            
            #For temperatures
            if s0.GetIsCoCurrent() == s1.GetIsCoCurrent():
                #Initialize with a cocurrent algorithm

                if nuNones == 1:
                    idx = lstT.index(None)
                    if idx == 0:
                        if TOutVec[i] > TOutVec[i+1]:
                            TInVec[i] = TInVec[i+1]*1.1
                        else:
                            TInVec[i] = TInVec[i+1]*0.9
                    elif idx == 1:
                        if TInVec[i] > TInVec[i+1]:
                            TOutVec[i] = TOutVec[i+1]*1.1
                        else:
                            TOutVec[i] = TOutVec[i+1]*0.9
                    elif idx == 2:
                        if TOutVec[i+1] > TOutVec[i]:
                            TInVec[i+1] = TInVec[i]*1.1
                        else:
                            TInVec[i+1] = TInVec[i]*0.9
                    elif idx == 3:
                        if TInVec[i+1] > TInVec[i]:
                            TOutVec[i+1] = TOutVec[i]*1.1
                        else:
                            TOutVec[i+1] = TOutVec[i]*0.9
                            
                    #else: #hot side is s1
                        #if idx == 0:
                            #TInVec[i] = TOutVec[i] * 0.9 #lower                            
                        #elif idx == 1:
                            #TOutVec[i] = (TInVec[i] + TOutVec[i+1]) /2.0 #lower 
                        #elif idx == 2:
                            #TInVec[i+1] = TOutVec[i+1] * 1.1 #higher
                        #elif idx == 3:
                            #TOutVec[i+1] = (TInVec[i+1] + TOutVec[i]) / 2.0 #half way 
                            
                            
                elif nuNones == 2:
                    idxMax = lstT.index(max(lstT))
                    if idxMax == 0 or idxMax == 1:                            #hot side is s0
                        if lstT[0] == None and lstT[2] == None:
                            TInVec[i] = TOutVec[i] * 1.1                      #higher
                            TInVec[i+1] = TOutVec[i+1] * 0.9                  #lower                            
                        elif lstT[0] == None and lstT[3] == None:
                            TInVec[i] = TOutVec[i] * 1.1                      #higher
                            TOutVec[i+1] = (TInVec[i+1] + TOutVec[i]) / 2.0   #half way
                        elif lstT[1] == None and lstT[2] == None:
                            TOutVec[i] = (TInVec[i] + TOutVec[i+1]) / 2.0     #half way
                            TInVec[i+1] = TOutVec[i+1] * 0.9                  #lower 
                        elif lstT[1] == None and lstT[3] == None:
                            diff = TInVec[i] - TInVec[i+1]
                            TOutVec[i] = TInVec[i] - diff/3.0                 #a third of the way
                            TOutVec[i+1] = TInVec[i+1] + diff/3.0             #a third of the way
                        else:
                            return False                                      #Can not solve if two T are in the same stream
                        
                    else: #hot side is s1
                        if lstT[0] == None and lstT[2] == None:
                            TInVec[i] = TOutVec[i] * 0.9                      #lower
                            TInVec[i+1] = TOutVec[i+1] * 1.1                  #higher
                        elif lstT[0] == None and lstT[3] == None:
                            TInVec[i] = TOutVec[i] * 0.9                      #lower 
                            TOutVec[i+1] = (TInVec[i+1] + TOutVec[i]) / 2.0   #half way 
                        elif lstT[1] == None and lstT[2] == None:
                            TOutVec[i] = (TInVec[i] + TOutVec[i+1]) /2.0      #lower  
                            TInVec[i+1] = TOutVec[i+1] * 1.1                  #higher
                        elif lstT[1] == None and lstT[3] == None:
                            diff = TInVec[i+1] - TInVec[i]
                            TOutVec[i+1] = TInVec[i+1] - diff/3.0             #a third of the way
                            TOutVec[i] = TInVec[i] + diff/3.0                 #a third of the way
                        else:
                            return False                                      #Can not solve if two T are in the same stream
                            
                elif nuNones == 3 and self.initMode != LASTCONV_INIT:
                    return #Can't solve for now

                elif nuNones == 4 and self.initMode != LASTCONV_INIT:
                    return #Can't solve
                    
                    
            else:
                #Initialize as counter current
                if nuNones == 1:
                    idx = lstT.index(None)
                    
                    #Find hot side
                    hotSide = 1
                    if idx == 0 or idx == 3:
                        if lstT[1] > lstT[2]: #hot side is s0
                            hotSide = 0
                    if idx == 1 or idx == 2:
                        if lstT[0] > lstT[3]: #hot side is s0
                            hotSide = 0
                            
                    if hotSide == 0:
                        if idx == 0:
                            TInVec[i] = max(TOutVec[i+1], TOutVec[i]) * 1.1      #higher
                        elif idx == 1:
                            TOutVec[i] = (TInVec[i] + TInVec[i+1]) / 2.0         #half way
                        elif idx == 2:
                            TInVec[i+1] = min(TOutVec[i+1], TOutVec[i]) * 0.9    #lower                            
                        elif idx == 3:
                            TOutVec[i+1] = (TInVec[i+1] + TInVec[i]) / 2.0       #half way 
                    else:
                       if idx == 0:
                            TInVec[i] = min(TOutVec[i+1], TOutVec[i]) * 0.9      #lower                            
                       elif idx == 1:
                           TOutVec[i] = (TInVec[i+1] + TInVec[i]) / 2.0          #half way 
                       elif idx == 2:
                           TInVec[i+1] = max(TOutVec[i+1], TOutVec[i]) * 1.1     #higher
                       elif idx == 3:
                           TOutVec[i+1] = (TInVec[i] + TInVec[i+1]) / 2.0        #half way

                    
                    
                elif nuNones == 2:
                    #Find hot side on the fly
                    if lstT[0] == None and lstT[2] == None:
                        #This one has two possible hot sides. 
                        #Pick higher outlet as the hot side
                        if lstT[1] > lstT[3]:
                            TInVec[i] = max(TOutVec[i+1], TOutVec[i]) * 1.1      #higher
                            TInVec[i+1] = min(TOutVec[i+1], TOutVec[i]) * 0.9    #lower
                        else:
                            TInVec[i] = min(TOutVec[i+1], TOutVec[i]) * 0.9      #lower  
                            TInVec[i+1] = max(TOutVec[i+1], TOutVec[i]) * 1.1    #higher

                    elif lstT[0] == None and lstT[3] == None:
                        if lstT[1] > lstT[2]:
                            TInVec[i] = TOutVec[i] * 1.1                         #higher
                            TOutVec[i+1] = (TInVec[i+1] + TInVec[i]) / 2.0       #half way
                        else:
                            TInVec[i] = TOutVec[i] * 0.9                         #lower  
                            TOutVec[i+1] = (TInVec[i] + TInVec[i+1]) / 2.0       #half way
                                            
                    elif lstT[1] == None and lstT[2] == None:
                        if lstT[0] > lstT[3]:
                            TInVec[i+1] = TOutVec[i+1] * 0.9                     #lower
                            TOutVec[i] = (TInVec[i] + TInVec[i+1]) / 2.0         #half way
                        else:
                            TInVec[i+1] = TOutVec[i+1] * 1.1                     #higher
                            TOutVec[i] = (TInVec[i+1] + TInVec[i]) / 2.0         #half way 
                        
                    elif lstT[1] == None and lstT[3] == None:
                        if lstT[0] > lstT[2]:
                            TOutVec[i] = (TInVec[i] + TInVec[i+1]) / 2.0         #half way
                            TOutVec[i+1] = (TInVec[i+1] + TInVec[i]) / 2.0       #half way 
                        else:
                            TOutVec[i] = (TInVec[i+1] + TInVec[i]) / 2.0         #half way 
                            TOutVec[i+1] = (TInVec[i] + TInVec[i+1]) / 2.0       #half way
                        
                    else:
                        return False #Can not solve if two T are in the same stream
                   
                elif nuNones == 3 and self.initMode != LASTCONV_INIT:
                    return False #Can't solve for now
                
                elif nuNones == 4 and self.initMode != LASTCONV_INIT:
                    return False #Can't solve

        return True

    def AssignResults(self, vals):
        """Assign the results into the appropriate ports"""
        for side in self._sides:
            side.AssignResults(vals)
            
        for hTransfer in self._hTransferList:
            if hTransfer.UseInCalculations():
                hTransfer.AssignResults(vals)
    
    def ClearConvResults(self):
        self.convRes = {}
        
    def StoreConvResults(self):
        """Store the converged results. Return 1 if successful, 0 otherwise"""
        self.ClearConvResults()
        try:
            #The keys of convRes must exactly match the names of the attributes in the tower
            nuSides = len(self._sides)
            self.convRes['nuSides'] = nuSides
            for i in range(nuSides):
                side = self._sides[i]
                self.convRes['MF%i'%i] = side.molarFlow
                self.convRes['T%i'%i] = array(side.TArray, Float)
                self.convRes['H%i'%i] = array(side.HArray, Float)
                self.convRes['Q%i'%i] = array(side.QArray, Float)
                
            nuHTransf = len(self._hTransferList)
            self.convRes['nuHTransf'] = nuHTransf
            for hTransfer in self._hTransferList:
                idx0, idx1 = self.GetIndexOfSide(hTransfer._side1), self.GetIndexOfSide(hTransfer._side2)
                self.convRes['UA%i_%i' %(idx0, idx1)] = hTransfer._UA
                self.convRes['Q%i_%i' %(idx0, idx1)] = array(hTransfer.duty, Float)
                self.convRes['ua%i_%i' %(idx0, idx1)] = array(hTransfer.ua, Float)
                
            return 1
                         
        except:
            #Clear everything if everythign went wrong
            self.ClearConvResults()
            return 0
            
    def RetrieveConvResults(self):
        """Put the last converged results in the attributes used by the tower. 
        Return 1 if successful, 0 otherwise. """
        
        tempDict = {}
        
        try:
            #Do a check here just as a safety check to see if the last converged results
            #in fact match the current status of the tower.
            #No need to clear in case this fails
            if not self.convRes: return 0
            nuSides = len(self._sides)
            if nuSides != self.convRes['nuSides']: return 0
            nuHTransf = len(self._hTransferList)
            if nuHTransf != self.convRes['nuHTransf']: return 0
            
            for i in range(nuSides):
                side = self._sides[i]
                tempDict['MF%i'%i] = side.molarFlow
                side.molarFlow = self.convRes['MF%i'%i]
                
                tempDict['T%i'%i] = side.TArray
                side.TArray = array(self.convRes['T%i'%i], Float)
                
                tempDict['H%i'%i] = side.HArray
                side.HArray = array(self.convRes['H%i'%i], Float)
                
                tempDict['Q%i'%i] = side.QArray
                side.QArray = array(self.convRes['Q%i'%i], Float)
                
            for hTransfer in self._hTransferList:
                idx0, idx1 = self.GetIndexOfSide(hTransfer._side1), self.GetIndexOfSide(hTransfer._side2)
                
                tempDict['UA%i_%i' %(idx0, idx1)] = hTransfer._UA
                hTransfer._UA = self.convRes['UA%i_%i' %(idx0, idx1)]
                
                tempDict['Q%i_%i' %(idx0, idx1)] = hTransfer.duty
                hTransfer.duty = array(self.convRes['Q%i_%i' %(idx0, idx1)], Float)
                
                tempDict['ua%i_%i' %(idx0, idx1)] = hTransfer.ua
                hTransfer.ua = array(self.convRes['ua%i_%i' %(idx0, idx1)], Float)
                
            return 1
        
        except:
            try:
                #Put it back to what it was if it failed
                for i in range(nuSides):
                    side = self._sides[i]
                    side.molarFlow = tempDict['MF%i'%i]
                    side.TArray = tempDict['T%i'%i]
                    side.HArray = tempDict['H%i'%i]
                    side.QArray = tempDict['Q%i'%i]
                    
                for hTransfer in self._hTransferList:
                    idx0, idx1 = self.GetIndexOfSide(hTransfer._side1), self.GetIndexOfSide(hTransfer._side2)
                    hTransfer._UA = tempDict['UA%i_%i' %(idx0, idx1)]
                    hTransfer.duty = tempDict['Q%i_%i' %(idx0, idx1)]
                    hTransfer.ua = tempDict['ua%i_%i' %(idx0, idx1)]
                
                return 0
            except:
                return 0
                
                
                
    ##########################################################################################
                    
    ## DEGREES OF FREEDOM #####################################################################
    def GetNuSpecsNeeded(self):
        #nu = self.GetTotalNuOfUnkNeededFor1Segment() - self.GetTotalNuOfEqNeededFor1Segment()
        nu = len(self._sides) * 3 - 1
        return nu
    
    ###def GetTotalNuOfEqNeededFor1Segment(self):
        ###"""Returns the amount of equations needed if only one segment was specified"""
        ###nuSides = self.GetNumberOfSides()
        ###totNuEqn = 0
        
        ####1PH flash per mat port
        ###totNuEqn += nuSides * 2

        ####1 ene balance per side
        ###totNuEqn += nuSides

        ####1 ene balance across sides per side
        ###totNuEqn += nuSides

        ####eqns for UA = amount of slots in a lower triangular matrix
        ####totNuEqn += (nuSides*nuSides - nuSides)/2
        
        ####Lets change it to nuSides-1 and the others should be 0
        ###totNuEqn += nuSides-1

        ###return totNuEqn

    
    ###def GetTotalNuOfUnkNeededFor1Segment(self):
        ###"""Returns the amount of unknowns needed if only one segment was specified"""
        ###nuSides = self.GetNumberOfSides()
        ###nuUnk = 0

        ####6 Vars per side H0, T0, H1, T1, moleFlow Q
        ###nuUnk += nuSides * 6

        ####As many UA as Qij (Heat across sides). Amount of slots in a lower triangular matrix
        ####nuUnk += ((nuSides*nuSides - nuSides)/2 ) *2
        ###nuUnk += (nuSides-1)*2
        
        ###return nuUnk
           
    ##########################################################################################
    
    ##OBJECT HANDLING #########################################################################
    def AddObject(self, obj, name):
        """adds an object to the appropriate container, based on its type"""
        
        if isinstance(obj, HXObject):
            prevObj = self.GetObject(name)
            if prevObj:
                raise SimError('CantAddObject', (name, self.GetPath()))
    
            self.LinkToObject(obj, name)
            try:
                obj.Initialize(self, name)
            except:
                obj.UnlinkObject(self, obj)
                raise
        elif isinstance(obj, Custom.CustomSolveMethod):
            if name != CUSTOM_SOLVE_OBJ:
                self.InfoMessage('CantChangeName', (CUSTOM_SOLVE_OBJ,), MessageHandler.errorMessage)
                #Should it really raise an error ??
                raise SimError ('CantChangeName', (CUSTOM_SOLVE_OBJ,))
            if self.customSolver:
                self.DeleteObject(self.customSolver)
            self.customSolver = obj
            obj.Initialize(self, CUSTOM_SOLVE_OBJ)
            self.ForgetAllCalculations()
        else:
            super(MultiSidedHeatExchangerOp, self).AddObject(obj, name)
            
    def GetObject(self, name):
        obj = super(MultiSidedHeatExchangerOp, self).GetObject(name)
        if obj != None: return obj
        
        obj = self.signals.get(name, None)
        if obj != None: return obj
        
        obj = self.estimates.get(name, None)
        if obj != None: return obj
        
        if name == 'HotComposite': return self.hComposite
        
        if name == 'ColdComposite': return self.cComposite
        
        if name == CUSTOM_SOLVE_OBJ:
            return self.customSolver
        
        return None
            
    def GetContents(self):
        results = super(MultiSidedHeatExchangerOp, self).GetContents()
        for k, v in self.signals.items():
            results.append((k, v))
        for k, v in self.estimates.items():
            results.append((k, v))
        return results
        
    def DeleteObject(self, obj):
        """
        check that we aren't deleting a port
        """
        if isinstance(obj, Ports.Port) and self is obj.GetParent():
            #All the ports that are created and owned in this unit op are administerd by objects.
            #Do not allow direct deletion of those objects.
            #The rest of the many ports that are displayed by this unit op are all borrowed from child unit ops
            #The deletion of those ports should be processed normally
            raise SimError('CantDelPortDirectly', (obj.GetPath(), self.GetPath()))
        elif isinstance(obj, HXObject):
            try:
                locked = obj.locked
            except AttributeError:
                locked = False
                
            if locked:
                raise SimError('CannotRemoveLockedObject', obj.GetPath())
            else:
                self.UnlinkObject(obj)
                obj.CleanUp()
                
        elif isinstance(obj, Custom.CustomSolveMethod) and self.customSolver is obj:
            if hasattr(self.customSolver, 'CleanUp'):
                self.customSolver.CleanUp()
            self.customSolver = None
            return
        else:
            super(MultiSidedHeatExchangerOp, self).DeleteObject(obj)
        
    def LinkToObject(self, obj, name):
        """
        add object to the appropriate dictionary using name
        """
        
        if isinstance(obj, HXObject):
            if isinstance(obj, EstimatePerSide):
                #Redundant check, but just in case
                if self.estimates.get(name, None) != None:
                    raise SimError('CantAddObject', (name, self.GetPath()))
                self.estimates[name] = obj
            else:
                #Redundant check, but just in case
                if self.signals.get(name, None) != None:
                    raise SimError('CantAddObject', (name, self.GetPath()))
                self.signals[name] = obj
            
        #Lets not unconverge or resolve for now.
        
    def UnlinkObject(self, obj):
        """remove obj from the appropriate list"""
        if self.signals.has_key(obj.name):
            del self.signals[obj.name]
            if obj in self.activeSpecs:
                idx = self.activeSpecs.index(obj)
                del self.activeSpecs[idx]
            if obj in self.inactiveSpecs:
                idx = self.inactiveSpecs.index(obj)
                del self.inactiveSpecs[idx]
        if self.estimates.has_key(obj.name):
            del self.estimates[obj.name]
    def ChangeObjectName(self, fromName, toName):
        if fromName in self.signals.keys():
            self.signals[toName] = self.signals[fromName]
            self.signals[toName].name = toName
            del self.signals[fromName]
        elif fromName in self.estimates.keys():
            self.estimates[toName] = self.estimates[fromName]
            self.estimates[toName].name = toName
            del self.estimates[fromName]
    ##################################################################################################
    
    
    ## CLONING ##############################################################
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(MultiSidedHeatExchangerOp, self)._RemoveFromCloneList(clone, attrNamesToClone)
        
        dontClone = ["_sides", "_hTransfer", "_hTransferList", "_balance", "_matBalances",
                     "portSpecs", "activeSpecs", "inactiveSpecs", "hComposite",
                     "cComposite", "customSolver"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
    
    def _CloneParameters(self, clone, attrNamesToClone):
        #Clone parameters
        for paramName in self.parameters:
            #Do a copy just in case
            clone.parameters[paramName] = copy.deepcopy(self.parameters[paramName])
            
            
        for paramName in self.parameterPropertyTypes:
            #Can safely point to the same thing as they are global types
            clone.parameterPropertyTypes[paramName] = self.parameterPropertyTypes[paramName]
            
        if "parameters" in attrNamesToClone: attrNamesToClone.remove("parameters")
        if "parameterPropertyTypes" in attrNamesToClone: attrNamesToClone.remove("parameterPropertyTypes") 
        
        clone.UpdateStructure()
        
        return attrNamesToClone
    
    ##################################################################################################
    
class HeatExchangerUA(MultiSidedHeatExchangerOp):
    def __init__(self, initScript=None):
        super(HeatExchangerUA, self).__init__(initScript)
        
            
    def LoadDefaultParameters(self):
        #Initialize with two sides
        self.SetParameterValue(NUSEGMENTS_PAR, 1)
        self.SetParameterValue(NUSIDES_PAR, 2)
        self.SetParameterValue(FINDPH_CHANGE_PAR, 0)
        self.SetParameterValue(SEGMENTSBASE_PAR, ENERGY_VAR)
        self.SetParameterValue(EquationSolver.MONITCONV_PAR, 1)
        
    def ValidateParameter(self, paramName, value):
        """Validates the NUSTIN_PAR"""
        if not super(HeatExchangerUA, self).ValidateParameter(paramName, value):
            return 0
        if paramName == NUSIDES_PAR:
            #Not number and must be two
            if not type(value) in (type(1), type(1.0)) or value != 2:
                return 0
            
        return 1
    
class CompositeSide(object):
    def __init__(self, hx, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - hx will call this when it is added to it
        """
        self.hx = hx
        self.name = name
        self.sides = []
        self.fwd = []
        self.T = None
        self.Q = None
        
        
    def GetName(self):
        return self.name

    def GetPath(self):
        return '%s.%s' %(self.hx.GetPath(), self.GetName())
    
    def GetParent(self):
        return self.hx
    
    def CleanUp(self):
        self.hx = None
        self.sides = None
        
    def Clear(self):
        """Clear all results"""
        self.sides = []
        self.T = None
        self.Q = None
        
    def SetSides(self, sides):
        """Gets a list of sides that conform the composite sides. The profiles are built right here"""
        self.Clear()
        self.sides = sides
        
    def SideCompare(self, side0, side1):
        """Order from colder to hotter"""
        tmin0 = min(side0.TArray)
        tmin1 = min(side1.TArray)
        return cmp(tmin0, tmin1)
        
    def GetT_From_Q(self, q, startIn=0):
        """Returns a temperature based on an energy value"""
        if self.T == None or self.Q == None: return None
        return self.InterpolateFromVectors(q, self.Q, self.T, startIn)
                        
    def GetQ_From_T(self, t, startIn=0):
        """Returns a q based on a temperature"""
        if self.T == None or self.Q == None: return None
        return self.InterpolateFromVectors(t, self.T, self.Q, startIn)
    
    def InterpolateFromVectors(self, val, fromVec, mapVec, startIn=0):
        """Map the matching value (val) that is contained in (fromVec) from the vector mapVec.
        Do interpolation if necessary"""
        length = len(fromVec)
        if length != len(mapVec):
            raise SimeError('CantInterpolate', (self.hx.GetPath()))
        for i in range(startIn, length):
            if fromVec[i] == val:
                return mapVec[i]
            elif fromVec[i] > val:
                if i == 0 or i == length:
                    raise SimeError('CantInterpolate', (self.hx.GetPath()))
                else:
                    frac = (val - fromVec[i-1]) / (fromVec[i] - fromVec[i-1])
                    return mapVec[i-1] + frac*(mapVec[i] - mapVec[i-1])
    
    def UpdateProfiles(self):
        if not self.sides: return
        
        sides = self.sides
        sides.sort(self.SideCompare)
        self.fwd = []
        
        vals = array(sides[0].TArray, Float)
        baseLen = len(vals)
        revIdx = range(baseLen)
        revIdx.reverse()
        
        tTot = None
        qTot = zeros(1, Float)
        for side in sides:
            if side.TArray[0] == side.TArray[-1]:
                fwd = side.HArray[0] < side.HArray[-1]
                self.fwd.append(fwd)
            else:
                fwd = side.TArray[0] < side.TArray[-1]
                self.fwd.append(fwd)
            
            tSide = array(side.TArray, Float) #K
            qSide = array(side.QArray, Float) #kJ/h
            if not fwd:
                tSide = take(tSide, revIdx)
                qSide = take(qSide, revIdx[1:])
            
            qSide = qSide / 3.6               #J/s
            qSide = absolute(Numeric.add.accumulate(qSide))
            
            if tTot == None: 
                tTot = tSide
                qTot = concatenate((qTot, qSide))
            else:
                in0 = tTot[0]
                end0 = tTot[-1]
                in1 = tSide[0]
                end1 = tSide[-1]

                if in0 == in1 and end0 == end1:
                    #Identical sides
                    tTot = array([in0, end1], Float)
                    qTot = array([qTot[0], qTot[-1]+qSide[-1]], Float)
                    
                elif end0 <= in1:
                    #Just link next side after this one
                    tTot = concatenate((tTot, tSide[1:]))
                    qSide += qTot[-1]
                    qTot = concatenate((qTot, qSide))
                elif in0 <= in1: #Whatever happens, concatenate at the end...
                    if end0 <= end1:
                        #Do the normal extrapolation...
                        qLeft = 0.0
                        for i in range(1, len(tTot)):
                            if tTot[i] == in1:
                                tTot = tTot[:i+1]
                                qLeft = qTot[-1] - qTot[i]
                                qTot = qTot[:i+1]
                                break
                            elif tTot[i] > in1:
                                frac = (in1 - tTot[i-1]) / (tTot[i] - tTot[i-1])
                                q = qTot[i-1] + frac*(qTot[i] - qTot[i-1])
                                if q > 0.0:
                                    qLeft = qTot[-1] - q
                                    qTot[i] = q
                                    qTot = qTot[:i+1]
                                    tTot[i] = in1
                                    tTot = tTot[:i+1]
                                else:
                                    qLeft = qTot[-1] - q
                                    qTot = qTot[:i]
                                    tTot = tTot[:i]
                                break
                            
                        qSide += qTot[-1] + qLeft
                        for i in range(1, len(tSide)):
                            if tSide[i] == end0:
                                off = 1
                                #qAdd = qSide[i-off] - qSide[:i-off]
                                #qSide = qSide[i-off:] + qAdd
                                qTot = concatenate((qTot, qSide[i-off:]))
                                tTot = concatenate((tTot, tSide[i:]))
                                break
                            elif tSide[i] > end0:
                                frac = (end0 - tSide[i-1]) / (tSide[i] - tSide[i-1])
                                #q in qSide is offset by one
                                off = 1
                                if i == 1:
                                    q = 0.0 + frac*(qSide[i-off] - 0.0)
                                else:
                                    q = qSide[i-1-off] + frac*(qSide[i-off] - qSide[i-1-off])
                                tTot = concatenate((tTot, array([end0], Float), tSide[i:]))
                                qTot = concatenate((qTot, array([q], Float), qSide[-off+i:]))
                                break
                    else:
                        idxIn1TouchTot = None
                        for i in range(1, len(tTot)):
                            if tTot[i] == in1:
                                idxIn1TouchTot = i
                                break
                            elif tTot[i] > in1:
                                #Squeeze the in1 temperautre into tTot
                                frac = (in1 - tTot[i-1]) / (tTot[i] - tTot[i-1])
                                q = qTot[i-1] + frac*(qTot[i] - qTot[i-1])
                                qTot = concatenate((qTot[:i], array([q], Float), qTot[i:]))
                                tTot = concatenate((tTot[:i], array([in1], Float), tTot[i:]))
                                idxIn1TouchTot = i
                                break
                            
                        for i in range(idxIn1TouchTot, len(tTot)):
                            if tTot[i] == end1:
                                tTot = concatenate((tTot[:idxIn1TouchTot], tTot[i:]))
                                qTot = concatenate((qTot[:idxIn1TouchTot], qTot[i:]))
                                qTot[idxIn1TouchTot+1:] += qSide[-1]
                                break
                            elif tTot[i] > end1:
                                #Squeeze the in1 temperautre into tTot
                                frac = (end1 - tTot[i-1]) / (tTot[i] - tTot[i-1])
                                q = qTot[i-1] + frac*(qTot[i] - qTot[i-1])
                                
                                tTot = concatenate((tTot[:idxIn1TouchTot+1], array([end1], Float), tTot[i:]))
                                qTot = concatenate((qTot[:idxIn1TouchTot+1], array([q], Float), qTot[i:]))
                                qTot[idxIn1TouchTot+1:] += qSide[-1]
                                break
                            
                else:
                    raise SimError('ErrBuildComposite', (self.hx.GetPath(),))
                            
            
        self.T = tTot
        self.Q = qTot
            
        

    def MergeData(self, other):
        success = 1
        try:
            maxLen = len(self.T) + len(other.T)

            myLen = len(self.T)
            myT = self.T
            myQ = self.Q
            
            otherLen = len(other.T)
            otherT = other.T
            otherQ = other.Q
            
            if abs(myQ[-1] - otherQ[-1]) > 1.0E-4: return 0
            otherQ[-1] = myQ[-1]
            if myQ[0] != myQ[0]: return 0
            
            t0 = zeros(maxLen, Float)
            q0 = zeros(maxLen, Float)
            t1 = zeros(maxLen, Float)
            q1 = zeros(maxLen, Float)
            
            longQ = concatenate((myQ, otherQ))
            longQ = list(longQ)
            longQ.sort()
            
            lastq = None
            idxTo = -1
            myLastIdx = 0
            otherLastIdx = 0
            for q in longQ:
                if lastq == q:
                    continue
                idxTo += 1
                lastq = q
                for idxMine in range(myLastIdx, myLen):
                    q0Curr = myQ[idxMine]
                    if q0Curr == q:
                        q0[idxTo] = q0Curr
                        t0[idxTo] = myT[idxMine]
                        myLastIdx = idxMine + 1
                        break
                    elif q0Curr < q:
                        q0[idxTo] = q0Curr
                        t0[idxTo] = myT[idxMine]
                        myLastIdx = idxMine + 1
                    elif q0Curr > q:
                        q0[idxTo] = q
                        startIn = 0
                        if idxMine > 0: startIn = idxMine-1
                        t0[idxTo] = self.GetT_From_Q(q, startIn)
                        myLastIdx = idxMine
                        break

                for idxOther in range(otherLastIdx, otherLen):
                    q1Curr = otherQ[idxOther]
                    if q1Curr == q:
                        q1[idxTo] = q1Curr
                        t1[idxTo] = otherT[idxOther]
                        otherLastIdx = idxOther + 1
                        break
                    elif q1Curr < q:
                        q1[idxTo] = q1Curr
                        t1[idxTo] = otherT[idxOther]
                        otherLastIdx = idxOther + 1
                    elif q1Curr > q:
                        q1[idxTo] = q
                        startIn = 0
                        if idxOther > 0: startIn = idxOther-1
                        t1[idxTo] = other.GetT_From_Q(q, startIn)
                        otherLastIdx = idxOther
                        break 
                        
            self.T = t0[:idxTo+1]
            self.Q = q0[:idxTo+1]
            other.T = t1[:idxTo+1]
            other.Q = q1[:idxTo+1]
            
            return 1
            
        except:
            return 0
        
        
    def GetObject(self, desc):
        if not self.sides: return None
        
        if desc == T_VAR: return self.T
        if desc == ENERGY_VAR + 'Acum': return self.Q
        try:
            if desc == 'ua': return self.ua
            if desc == 'lmtd': return self.lmtd
        except:
            return None
            
class HotComposite(CompositeSide):
    """Hot composite"""        
    
    def __str__(self):
        return 'HotCompositeSide'
    
    
class ColdComposite(CompositeSide):
    """Display this side as going cocurrent"""
            
    def __str__(self):
        return 'ColdCompositeSide'

            
class HXObject(object):
    def Initialize(self, hx, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - hx will call this when it is added to it
        """
        
        #As opposed to the tower, do not crate the port here.
        #Let each object handle/create its own port
        
        self.hx = hx
        self.name = name
        
    def CleanUp(self):
        """remove all references"""
        if hasattr(self, 'port'):
            if self.hx and self.port:
                self.hx.DeletePort(self.port)
            self.port = None
        self.hx = None
        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        pass  # handled by derived classes if necessary
    
    def GetPath(self):
        """return object path to this object"""
        return '%s.%s' % (self.hx.GetPath(), self.name)
        
    def GetParent(self):
        """return stage as parent in hierarchy"""
        return self.hx
    
    def SetParent(self, parent):
        self.hx = parent
        if hasattr(self, "ReactorPortName"):
            self.port = parent.GetPort(self.ReactorPortName())
    
    def GetContents(self):
        """return list of (description, obj) tuples of contained objects"""
        if hasattr(self, 'port'):
            return [('Port',self.port)]
        else:
            return []
        
    def GetObject(self, name):
        """returns contained object based on name"""
        if name == 'Port' and hasattr(self, 'port'):
            return self.port
        else:
            return None
        
    def AddObject(self, obj, name):
        """ use add to change parent stage """
        if name == 'NewName':
            newName = str(obj)
            self.ChangeName(self.name, newName)
            
        else:
            raise SimError('CantAddObject', (name, self.hx.GetPath()))
            
    def ChangeName(self, fromName, toName):
        """
        Change name in corresponding dictionary and in associated port if necessary
        """
        
        if self.hx.GetObject(toName):
            self.InfoMessage('DuplicateName', (toName, self.hx.GetPath()))
            return
        
        if hasattr(self,'HXPortName'):
            oldPortName = self.HXPortName()
            
        #Let the hx rename the object
        self.hx.ChangeObjectName(fromName, toName)
            
        #Change port name if necessary
        if hasattr(self,'HXPortName'):
            newPortName = self.HXPortName()
            self.hx.RenamePort(oldPortName, newPortName)
            
    def Clone(self):
        """Clone the object"""
        clone = self.__class__()
        clone.name = self.name
        return clone
    
            
class HXObject_Side(HXObject):
    """Heat exchanger object that depends on a side"""
    def __init__(self, sideIdx):
        """Hold the indexes just for now. They will be deleted once Initialize is called"""
        self.sideIdx = sideIdx
        self.scaleFactor = 1.0
    
    def Initialize(self, hx, name):
        """
        grab the actual instances of the sides involved
        """
        super(HXObject_Side, self).Initialize(hx, name)
        
        self.side = self.hx.GetSide(self.sideIdx)
        
    def SetParent(self, parent):
        super(HXObject_Side, self).SetParent(parent)
        self.side = self.hx.GetSide(self.sideIdx)
        
        
    def CleanUp(self):
        """remove all references"""
        super(HXObject_Side, self).CleanUp()
        self.side = None
        
    def HXPortName(self):
        return 'Variable_%d_%s' %(self.sideIdx, self.name)
        
    def SetScaleFactor(self, scaleFactor):
        self.scaleFactor = scaleFactor
        
    def GetScaleFactor(self):
        return self.scaleFactor
    
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.sideIdx)
        clone.name = self.name
        clone.scaleFactor = self.scaleFactor
        return clone
    
class PropertyPerSide(HXObject_Side):
    """Heat exchanger property object that depends on a side"""
    def __init__(self, sideIdx, varType, isIn=1):
        """Hold the indexes just for now. They will be deleted once Initialize is called"""
        super(PropertyPerSide, self).__init__(sideIdx)
        self.atInlet = isIn
        self.varType = varType.strip()
        self.fracs = None
        self.compounds = None
        self.scaleFactor = PropTypes[self.varType].scaleFactor
        if not self.scaleFactor:
            self.scaleFactor = 1.0
            
    def CleanUp(self):
        self.compounds = None
        super(PropertyPerSide, self).CleanUp()
        
    def Initialize(self, hx, name):
        """
        create a port for the signal
        """
        super(PropertyPerSide, self).Initialize(hx, name)
        
        self.port = self.hx.CreatePort(SIG, self.HXPortName())
        self.port.SetSignalType(self.varType)
        
    def HXPortName(self):
        if self.atInlet: return 'Variable%sIn_%d_%s' % (self.varType, self.sideIdx, self.name)
        else: return 'Variable%sOut_%d_%s' % (self.varType, self.sideIdx, self.name)
        
    def Reset(self):
        """Get the value from the port"""
        self.value = self.port.GetValue()
        try:
            self.fracs = self.side._portIn.GetCompositionValues()
            if self.fracs == None:
                self.fracs = self.side._portOut.GetCompositionValues()
            compounds = CompoundList(None)
            for i in self.fracs:
                prop = BasicProperty(FRAC_VAR)
                prop.SetValue(i, FIXED_V)
                compounds.append(prop)
            compounds.Normalize()
            self.compounds = compounds
        except:
            self.fracs = None
            self.compounds = None
            
    def GetCurrentHXValue(self):
        """Get the current value according to iteration variables"""
        try:
            side = self.side
            coCurr = side.GetIsCoCurrent()
            if self.atInlet:
                if coCurr: idx = 0
                else: idx = -1
            else:
                if coCurr: idx = -1
                else: idx = 0
                
            if self.varType == T_VAR:
                return side.TArray[idx]
            elif self.varType == P_VAR:
                return side.PArray[idx]
            elif self.varType == H_VAR:
                return side.HArray[idx]
            else:
                p = side.PArray[idx]
                h = side.HArray[idx]
                props = MaterialPropertyDict()
                props[P_VAR].SetValue(p, FIXED_V)
                props[H_VAR].SetValue(h, FIXED_V)
                thCaseObj = self.hx.GetThermo()
                nuSolids = self.hx.NumberSolidPhases()
                thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
                results = thAdmin.Flash(prov, case, self.compounds, props, 2, (self.varType,), nuSolids=nuSolids)
                return results.bulkProps[0]
        except:
            return None
        
    def Error(self):
        """Return the scaled error"""
        value = self.GetCurrentHXValue()
        return (self.value - value) / self.scaleFactor
        
    def AssignResultsToPort(self):
        """Would get called if spec was not active, then put the newly calculated value"""
        value = self.GetCurrentHXValue()
        self.port.SetValue(value, CALCULATED_V)
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.sideIdx, self.varType, self.atInlet)
        clone.name = self.name
        clone.scaleFactor = self.scaleFactor
        return clone
        
class EnergySideVar(PropertyPerSide):
    """Energy tranferred from one side to another"""
    def __init__(self, sideIdx, inMinusOut=1):
        varType = ENERGY_VAR
        super(EnergySideVar, self).__init__(sideIdx, varType)
        self.inMinusOut = inMinusOut
            
    def HXPortName(self):
        if self.inMinusOut:
            return 'EnergyLost_%d_%s' %(self.sideIdx, self.name)
        return 'EnergyGained_%d_%s' %(self.sideIdx, self.name)
        
    def Reset(self):
        """Get the value from the port"""
        self.value = self.port.GetValue()
            
    def SolveFromPortValues(self):
        """Attempt to fill in the value of the port based on the values of the port of the associated side"""
        try:
            nuSegments = self.hx.GetNumberOfSegments()
            side = self.side
            pIn = side._portIn
            pOut = side._portOut
            mf = pIn.GetPropValue(MOLEFLOW_VAR)
            h0 = pIn.GetPropValue(H_VAR)
            h1 = pOut.GetPropValue(H_VAR)
            if h0 != None and h1 != None and mf != None:
                
                dq = (h1 - h0) * mf / 3.6
                
                if self.inMinusOut:
                    self.port.SetValue(-dq, CALCULATED_V)
                else:
                    self.port.SetValue(dq, CALCULATED_V)
            
        except:
            return None        
        
    def GetCurrentHXValue(self):
        """Get the current value according to iteration variables"""
        try:
            side = self.side
            coCurr = side.GetIsCoCurrent()
            if self.inMinusOut:
                if coCurr: 
                    idx0 = 0
                    idx1 = -1
                else: 
                    idx0 = -1
                    idx1 = 0
            else:
                if coCurr: 
                    idx0 = -1
                    idx1 = 0
                else: 
                    idx0 = 0
                    idx1 = -1
                
            return (side.HArray[idx0] - side.HArray[idx1]) * side.molarFlow / 3.6
        except:
            return None
        
        
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.sideIdx, self.inMinusOut)
        clone.name = self.name
        clone.scaleFactor = self.scaleFactor
        return clone
        
class EstimatePerSide(HXObject_Side):
    """Heat exchanger estimate object that depends on a side"""
    def __init__(self, sideIdx, varType):
        """Hold the indexes just for now. They will be deleted once Initialize is called"""
        super(EstimatePerSide, self).__init__(sideIdx)
        self.varType = varType
            
    def Initialize(self, hx, name):
        """
        create a port for a T signal
        """
        super(EstimatePerSide, self).Initialize(hx, name)
        
        self.port = self.hx.CreatePort(SIG, self.HXPortName())
        self.port.SetSignalType(self.varType)
        
    def HXPortName(self):
        return 'Estimate_%d_%s' % (self.sideIdx, self.name)
        
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.sideIdx, self.varType)
        clone.name = self.name
        clone.scaleFactor = self.scaleFactor
        return clone
    
class EstimateTemperature(EstimatePerSide):
    """Heat exchanger estimate object that depends on a side"""
    def __init__(self, sideIdx, isIn=1):
        """Hold the indexes just for now. They will be deleted once Initialize is called"""
        super(EstimateTemperature, self).__init__(sideIdx, T_VAR)
        self.atInlet = isIn
        
    def HXPortName(self):
        if self.atInlet: return 'EstimateTIn_%d_%s' % (self.sideIdx, self.name)
        else: return 'EstimateTOut_%d_%s' % (self.sideIdx, self.name)
        
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.sideIdx, self.atInlet)
        clone.name = self.name
        clone.scaleFactor = self.scaleFactor
        return clone
    
    
class HXObject_CompositeSide(HXObject):
    
    def Initialize(self, hx, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(HXObject_CompositeSide, self).Initialize(hx, name)
        #Make sure we do this so the port can be deleted directly
        self.port = self.hx.CreatePort(SIG, self.HXPortName())
        self.port.SetSignalType(self.varType)
        
        
    def Reset(self):
        """Get the value from the port"""
        self.value = self.port.GetValue() 
        
    def Error(self):
        """Return the scaled error"""
        value = self.GetCurrentHXValue()
        return (self.value - value) / self.scaleFactor
        
    def AssignResultsToPort(self):
        """Would get called if spec was not active, then put the newly calculated value"""
        value = self.GetCurrentHXValue()
        self.port.SetValue(value, CALCULATED_V)
    
    def Clone(self):
        """Clone the object"""
        clone = self.__class__()
        clone.name = self.name
        if hasattr(self, 'scaleFactor'):
            clone.scaleFactor = self.scaleFactor
        return clone
        
class HXObject_CompositeApproachT(HXObject_CompositeSide):
    def __init__(self):
        self.value = None
        self.varType = DELTAT_VAR
        self.scaleFactor = PropTypes[self.varType].scaleFactor
        if not self.scaleFactor:
            self.scaleFactor = 1.0
    
    def HXPortName(self):
        return 'CompositeAppT_%s' %self.name
        
    def GetCurrentHXValue(self):
        """Get the current value according to iteration variables"""
        self.lastIdx = None
        try:
            #Results should be merged already
            t0 = self.hx.hComposite.T
            t1 = self.hx.cComposite.T
            delta = absolute(t1 - t0)
            self.lastIdx = argmin(delta)
            approach = delta[self.lastIdx]
            
            return approach
        
        except:
            return None
        
    
class HXObject_CompositeSideUA(HXObject_CompositeSide):
    def __init__(self):
        self.value = None
        self.varType = UA_VAR
        self.scaleFactor = PropTypes[self.varType].scaleFactor
        if not self.scaleFactor:
            self.scaleFactor = 1.0    
            
    def HXPortName(self):
        return 'OverallUA_%s' %self.name
    
    def GetCurrentHXValue(self):
        """Get the current value according to iteration variables"""
        try:
            #Results should be merged already
            hx = self.hx
            t0 = hx.hComposite.T
            t1 = hx.cComposite.T
            duty = array(map(operator.sub, hx.hComposite.Q[1:], hx.hComposite.Q[:-1]), Float)
            lmtd = array(map(CalcLMTD, t0[:-1], t1[:-1], t0[1:], t1[1:]), Float)
            ua = duty / lmtd
            hx.hComposite.lmtd = hx.cComposite.lmtd = lmtd
            hx.hComposite.ua = hx.cComposite.ua = ua
            return sum(ua)
            
        except:
            return None
    
    
class HXObject_Transfer(HXObject):
    """Heat exchanger object that depends on a heat transfer (i.e. on two sides)"""
    def __init__(self, fromIdx, toIdx):
        """Hold the indexes just for now. They will be deleted once Initialize is called"""
        self.fromIdx = fromIdx
        self.toIdx = toIdx
        self.scaleFactor = 1.0
        
    def Initialize(self, hx, name):
        """
        grab the actual instances of the sides involved
        """
        super(HXObject_Transfer, self).Initialize(hx, name)
        self.LoadObjects()
        
    def LoadObjects(self):
        self.fromSide = self.hx.GetSide(self.fromIdx)
        self.toSide = self.hx.GetSide(self.toIdx)
        minIdx = min(self.fromIdx, self.toIdx)
        maxIdx = max(self.fromIdx, self.toIdx)
        self.heatTran = self.hx._hTransfer[maxIdx][minIdx]
        
    def SetParent(self, parent):
        super(HXObject_Transfer, self).SetParent(parent)
        self.LoadObjects()
        
    def CleanUp(self):
        """remove all references"""
        super(HXObject_Transfer, self).CleanUp()
        self.fromSide = None
        self.toSide = None
        self.heatTran = None
        
    def HXPortName(self):
        return 'Variable_%d_%d_%s' %(self.fromIdx, self.toIdx, self.name)        
        
    def SetScaleFactor(self, scaleFactor):
        self.scaleFactor = scaleFactor
        
    def GetScaleFactor(self):
        return self.scaleFactor
        
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.fromIdx, self.toIdx)
        clone.name = self.name
        clone.scaleFactor = self.scaleFactor
        return clone
    
    
class HXTranferVar(HXObject_Transfer):
    def __init__(self, fromIdx, toIdx, varType):
        super(HXTranferVar, self).__init__(fromIdx, toIdx)
        self.value = None
        self.varType = varType
        self.scaleFactor = PropTypes[self.varType].scaleFactor
        if not self.scaleFactor:
            self.scaleFactor = 1.0
    
    def Initialize(self, hx, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(HXTranferVar,self).Initialize(hx, name)
            
        #Make sure we do this so the port can be deleted directly
        self.port = self.hx.CreatePort(SIG, self.HXPortName())
        self.port.SetSignalType(self.varType)
    
    def Reset(self):
        """Get the value from the port"""
        self.value = self.port.GetValue()        
        
    def Error(self):
        """Return the scaled error"""
        value = self.GetCurrentHXValue()
        return (self.value - value) / self.scaleFactor
        
    def AssignResultsToPort(self):
        """Would get called if spec was not active, then put the newly calculated value"""
        value = self.GetCurrentHXValue()
        self.port.SetValue(value, CALCULATED_V)
        
        
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.fromIdx, self.toIdx, self.varType)
        clone.name = self.name
        clone.scaleFactor = self.scaleFactor
        return clone
        
class EnergyTransferVar(HXTranferVar):
    """Energy tranferred from one side to another"""
    def __init__(self, fromIdx, toIdx):
        varType = ENERGY_VAR
        super(EnergyTransferVar, self).__init__(fromIdx, toIdx, varType)
        
        self.eneSign = 1.0
        if fromIdx > toIdx:
            #The heat transfer object always define values from lower index to higher index
            self.eneSign = -1.0
            
    def HXPortName(self):
        return 'Energy_%d_%d_%s' %(self.fromIdx, self.toIdx, self.name)
        
    def GetCurrentHXValue(self):
        """Get the current value according to iteration variables"""
        try:
            value = self.heatTran.GetObject(ENERGY_VAR)
            if value != None:
                #Value is an array in J/s
                return Numeric.sum(value) * self.eneSign
        except:
            return None
        
        
        
class TemperatureApproachVar(HXTranferVar):
    """Approach temperature between sides"""
    def __init__(self, fromIdx, toIdx):
        varType = DELTAT_VAR
        super(TemperatureApproachVar, self).__init__(fromIdx, toIdx, varType)
        self.idxCantUse = []
            
    def HXPortName(self):
        return 'TApproach_%d_%d_%s' %(self.fromIdx, self.toIdx, self.name)
    
    def Reset(self):
        """See if there are pairs of temperatures that can not be used as iteration variables"""
        super(TemperatureApproachVar, self).Reset()
        self.idxCantUse = []
        nuSegments = self.hx.GetNumberOfSegments()
        s0 = self.fromSide
        s1 = self.toSide
        counter0 = s0.GetIsCounterCurrent()
        counter1 = s1.GetIsCounterCurrent()
        t0In = s0._portIn.GetPropValue(T_VAR)
        t0Out = s0._portOut.GetPropValue(T_VAR)
        t1In = s1._portIn.GetPropValue(T_VAR)
        t1Out = s1._portOut.GetPropValue(T_VAR)
        
        if counter0 == counter1:
            if t0In != None and t1In != None:
                if counter0: self.idxCantUse.append(nuSegments-1)
                else: self.idxCantUse.append(0)
            if t0Out != None and t1Out != None:
                if counter0: self.idxCantUse.append(0)
                else: self.idxCantUse.append(nuSegments-1)
        else:
            if t0In != None and t1Out != None:
                if counter0: self.idxCantUse.append(nuSegments-1)
                else: self.idxCantUse.append(0)
            if t0Out != None and t1In != None:
                if counter0: self.idxCantUse.append(0)
                else: self.idxCantUse.append(nuSegments-1)
                
                
                
    def GetCurrentHXValue(self):
        """Get the current value according to iteration variables"""
        self.lastIdx = None
        try:
            t0 = self.fromSide.GetObject(T_VAR)
            t1 = self.toSide.GetObject(T_VAR)
            delta = absolute(t1 - t0)
            self.lastIdx = argmin(delta)
            approach = delta[self.lastIdx]
            
            #lastIdx is used for calculating jacobian. Do not use that idx if it is a forbidden idx 
            if self.lastIdx in self.idxCantUse:
                for i in self.idxCantUse:
                    delta[i] = 1.0E100
                self.lastIdx = argmin(delta)
            
            return approach
        
        except:
            return None
        
    
    def LoadJacobianTerms(self, jacRow):
        """This spec is part of a system of equations and while solving we nee to know the derivative of this
        equation with respect of all the relevant varibles.
        The input is the row of a jacobian and it should load the derivative in the proper place"""
        s0 = self.fromSide
        s1 = self.toSide
        
        t0 = s0.TArray[self.lastIdx]
        t1 = s1.TArray[self.lastIdx]
        
        #Get the index from the overall vector of unknowns is each T variable located
        t0Idx = s0.TIndex[self.lastIdx]
        t1Idx = s1.TIndex[self.lastIdx]
        
        
        #The equation that we are solving is... (Everything is divided by scale factor!!)
        #0.0 = specVal - currVal = specVal - (abs(t1 - t0))
        #
        #Removing the abs function...
        #if t1 > t0: 0.0 = specVal - (t1 - t0) ; d/dt1 = -1.0 ; d/dt0 = 1.0
        #else: 0.0 = specVal - (t0 - t1)       ; d/dt1 = 1.0  ; d/dt0 = -1.0
        
        if t1 > t0: 
            jacRow[t1Idx] = -1.0 / self.scaleFactor
            jacRow[t0Idx] = 1.0 / self.scaleFactor
        else: 
            jacRow[t1Idx] = 1.0 / self.scaleFactor
            jacRow[t0Idx] = -1.0 / self.scaleFactor
         
class PortUASpec(HXTranferVar):
    """Spec that gets created on the fly when there is a ua spec"""
    def __init__(self, hx, fromIdx, toIdx, value):
        super(PortUASpec, self).__init__(fromIdx, toIdx, UA_VAR)
        self.hx = hx
        self.scaleFactor = 1000.0
        self.value = value
        self.LoadObjects()
        
    def Reset(self):
        """Get the value from the port"""
        self.value = self.heatTran._portUA.GetValue()    
        
        
    def GetCurrentHXValue(self):
        """Get the current value according to iteration variables"""
        try:
            return sum(self.heatTran.ua)/3.6     #Return in internal units
        except:
            return None
        
    def AssignResultsToPort(self):
        pass
        
        
class PortDTAcrossSidesSpec(HXTranferVar):
    """Spec that gets created on the fly when there is a ua spec"""
    def __init__(self, hx, fromIdx, toIdx, isIn, value):
        super(PortDTAcrossSidesSpec, self).__init__(fromIdx, toIdx, DELTAT_VAR)
        self.hx = hx
        self.scaleFactor = 100.0
        self.value = value
        self.LoadObjects()
        self.isIn = isIn
        
    def Reset(self):
        """Get the value from the port"""
        if self.isIn:            
            self.value = self.heatTran._portDTIn.GetValue()
        else:
            self.value = self.heatTran._portDTOut.GetValue()
        
            
    def GetCurrentHXValue(self):
        """Get the current value according to iteration variables"""
        try:
            if self.isIn:
                t0 = self.fromSide.TArray[0]
                t1 = self.toSide.TArray[0]
            else:
                t0 = self.fromSide.TArray[-1]
                t1 = self.toSide.TArray[-1]
            return t0 - t1
        except:
            return None
        
    def AssignResultsToPort(self):
        pass
        
        
def CalcLMTD(S1T1, S2T1, S1T2, S2T2):
    """Calculates LMTD"""
    dt1 = S1T1 - S2T1
    dt2 = S1T2 - S2T2 + 1E-30

    if (dt1 * dt2 < 0.0):
        #set the smaller dt to 1e-30
        if (abs(dt1) > abs(dt2)):
            #dt2 is smaller
            dt2 = ((dt1)/abs(dt1)) * 1E-30
        else:
            dt1 = ((dt2)/abs(dt2)) * 1E-30

    elif (dt1 * dt2 == 0.0):
        dt1 = 1E-30
        dt2 = dt1

    if (abs(dt1 - dt2) < 0.0000000001):
        dt1 = dt1 + 0.0000000001

    return (dt1 - dt2) / (math.log(dt1 / dt2) + 1E-30)