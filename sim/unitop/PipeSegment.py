"""Models a Pipe Segment 
"""

import UnitOperations, Balance, Tower
from Tower import ProfileObj
from sim.solver.Variables import *
from sim.solver import EquationSolver
from sim.solver.Error import SimError
from sim.solver.Messages import MessageHandler

import numpy
from numpy.oldnumeric import array, Float, Int, where, zeros, ones, sum, repeat
from numpy.oldnumeric import take, reshape, transpose
import math, string, copy
from math import exp, log, sqrt, sin , asin, log10
PI = math.pi

EMPTY_VAL = 1.0E-100

#Parameters
DETAILED_PAR = "Detailed"
DP_CORR_PAR = "PressureDropCorrelation"
IGNOREKINANDPOT_PAR = "IgnoreKineticAndPotential"
ENERGYMODEL_PAR = "EnergyLossModel"
AV_ENERGYMODELS_PAR = "AvEnergyLossModels"
LINEART_MODEL = "LinearTemperature"
EQUALU_MODEL = "EqualU"
LINEARQ_MODEL = "LinearEnergy"

#Ports
LENGTH_PORT = 'Length'
DIAM_PORT = 'Diameter'    #OLD NAME !! NOT USED ANYMORE
OD_PORT = 'OuterDiameter'
ID_PORT = 'InnerDiameter'
ROUGH_PORT = 'Roughness'
ELEVATION_PORT = 'Elevation'
EXT_T_PORT = 'ExternalT'


#Types of plug-in models
DP_MODEL = 'PressureDropModel'
HT_MODEL = 'HeatTransferModel'


GRAVITY = 9.81 #m/s2


#Define some default index for some key properties
P_IDX = 0
H_IDX = 1
T_IDX = 2
MASSDEN_IDX = 3

#Different calculation modes
CALC_GENERIC_MODE = 'SolveGeneric'
CALC_OUTP_MODE = 'SolveForOutP'
CALC_INP_MODE = 'SolveForInP'
CALC_D_MODE = 'SolveForDiameter'
CALC_FLOW_MODE = 'SolveForFlow'


class PipeSegment(EquationSolver.EquationBasedOp):
    """PipeSegment - unit operation having in and out material ports
    and pipe properties ports"""

    def __init__(self, initScript=None):
        """
        create the ports and init the balance
        """
        
        super(PipeSegment, self).__init__(initScript)
        
        
        self.inPort = self.CreatePort(IN|MAT, IN_PORT)
        self.inPort.SetLocked(True)
        self.outPort = self.CreatePort(OUT|MAT, OUT_PORT)
        self.outPort.SetLocked(True)

        self.enePort = self.CreatePort(OUT|ENE, OUT_PORT + 'Q')
        self.enePort.SetLocked(True)        

        self.uPort = self.CreatePort(SIG, U_PORT)
        self.uPort.SetSignalType(U_VAR)
        self.uPort.SetLocked(True)
        
        self.ambTPort = self.CreatePort(SIG, EXT_T_PORT)
        self.ambTPort.SetSignalType(T_VAR)
        self.ambTPort.SetLocked(True)
        self.ambTPort.SetValue(298.15, FIXED_V)
        
        self.dpPort = self.CreatePort(SIG, DELTAP_PORT)
        self.dpPort.SetSignalType(DELTAP_VAR)
        self.dpPort.SetLocked(True)
        
        self.lenPort = self.CreatePort(SIG, LENGTH_PORT)
        self.lenPort.SetSignalType(LENGTH_VAR)
        self.lenPort.SetLocked(True)
        
        self.iDiamPort = self.CreatePort(SIG, ID_PORT)
        self.iDiamPort.SetSignalType(LENGTH_VAR)
        self.iDiamPort.SetLocked(True)
        
        self.oDiamPort = self.CreatePort(SIG, OD_PORT)
        self.oDiamPort.SetSignalType(LENGTH_VAR)
        self.oDiamPort.SetLocked(True)
        
        self.roughPort = self.CreatePort(SIG, ROUGH_PORT)
        self.roughPort.SetSignalType(LENGTH_VAR)        
        self.roughPort.SetLocked(True)
        
        self.y0Port = self.CreatePort(SIG, '%s0' %ELEVATION_PORT)
        self.y0Port.SetSignalType(LENGTH_VAR)        
        self.y0Port.SetLocked(True)
        self.y0Port.SetValue(0.0, FIXED_V)
        
        self.y1Port = self.CreatePort(SIG, '%s1' %ELEVATION_PORT)
        self.y1Port.SetSignalType(LENGTH_VAR)        
        self.y1Port.SetLocked(True)
        
        self.LoadDefaultParameters()

        self._localMatDict = MaterialPropertyDict()
        self._localCmpList = None #This one is created when needed
        
        self.dpModel = None
        self.AddObject(PressureDropModel(), DP_MODEL)
        
        #self.htModel = None
        #self.AddObject($$, HT_MODEL)
        
        #This unit op uses different solve algorithms depending on the input
        self.calcMode = None
        self.converged = False
        
        #Keep a set of flash results for each section
        self.flashResultsArray = None  #Holds a flash results object for each node
        self.ClearProfiles()           #This will initialize the profiles
        
        #Add profile objects
        #Note... these profiles are used for interaction with users and 
        #are different from the arrays such as self.zArray which are used in the calculations
        self.liveProfiles = {}         #Profiles that can be input or retrieved by users
        self.liveProfiles['x'] = ProfileObj(self, LENGTH_VAR, 'x_Profile')
        self.liveProfiles['y'] = ProfileObj(self, LENGTH_VAR, 'y_Profile')
        #self.liveProfiles['z'] = ProfileObj(self, LENGTH_VAR, '%z_Profile')  NOT NEEDED 
        self.liveProfiles[LENGTH_PORT] = ProfileObj(self, LENGTH_VAR, '%s_Profile' %LENGTH_PORT)
        self.liveProfiles['K'] = ProfileObj(self, GENERIC_VAR, 'K_Profile')
        
        
        #Keep an instance of all the available solve methods
        self.solveMethods = {}
        solveMeth = SolveMethod_OutP()
        self.AddObject(solveMeth, CALC_OUTP_MODE)
        
        self.balance = Balance.Balance(Balance.MOLE_BALANCE | Balance.ENERGY_BALANCE)
        self.balance.AddInput(self.inPort)
        self.balance.AddOutput((self.outPort, self.enePort))
        
        self.SetParameterValue(IGNOREKINANDPOT_PAR, 0)
        
        
    def __getstate__(self):
        """return info to pickle for storing"""
        try: 
            state = self.__dict__.copy()
            if state['dpModel']:
                #Don't store the pressure drop model
                #as it could be custom made
                try:
                    #The str(type(state['dpModel'])) call returns something like this:
                    #"<class 'PressureDropModel'>"
                    #Change it to something like this:
                    #'PressureDropModel'
                    s = str(type(state['dpModel'])).split(' ', 1)[1][1:-2]
                    state['dpModel'] = s
                except:
                    pass
            return state
        except: 
            return self.__dict__
        
    def __setstate__(self, oldState):
        """build from stored info"""
        
        self.__dict__ = oldState
        if self.__dict__.has_key('dpModel'):
            if self.dpModel:
                try:
                    #The pressure drop model was stored as a string. 
                    #Try to recreate it as an a object
                    lstMods = self.dpModel.split('.', 1)
                    if len(lstMods) > 1:
                        exec('import %s' %lstMods[0])
                    dpModel = eval('%s()' %self.dpModel)
                    self.dpModel = None
                    self.AddObject(dpModel, DP_MODEL)
                except:
                    self.InfoMessage('CouldNotRestorePlugIn', (str(self.dpModel), ))
                    dpModel = PressureDropModel()
                    self.dpModel = None
                    self.AddObject(dpModel, DP_MODEL)
        
        
    ##Parameters, Objects and pressure drop models admin#########
    def AddObject(self, obj, name):
        if isinstance(obj, PressureDropModel):
            if name != DP_MODEL:
                self.InfoMessage('CantChangeName', (DP_MODEL,), MessageHandler.errorMessage)
                #Should it really raise an error ??
                raise SimError ('CantChangeName', (DP_MODEL,))
            if self.dpModel:
                self.DeleteObject(self.dpModel)
            self.dpModel = obj
            obj.Initialize(self, DP_MODEL)
            #Don't put this line yet as it screwes up the recall
            #self.ForgetAllCalculations()
        elif isinstance(obj, SolveMethod):
            self.solveMethods[name] = obj
            obj.Initialize(self, name)
        else:
            super(PipeSegment, self).AddObject(obj, name)            
    
            
    def GetObject(self, name):
        #Backward compatibility with scripts
        if name == DIAM_PORT:
            name = ID_PORT
        obj = super(PipeSegment, self).GetObject(name)
        if obj != None:
            return obj
        if name == DP_MODEL:
            return self.dpModel
        elif name == 'x_Profile':
            return self.liveProfiles['x']
        elif name == 'y_Profile':
            return self.liveProfiles['y']
        elif name == '%s_Profile' %LENGTH_PORT:
            return self.liveProfiles[LENGTH_PORT]
        elif name == 'K_Profile':
            return self.liveProfiles['K']
        elif name == P_VAR:
            #This one is kept in Pa. Return in kPa
            try: return self.pArray / 1000.0
            except: return None
        elif name == H_VAR:
            #This one is kept in J/kg. Return in kJ/kmol
            mw = self.inPort.GetPropValue(MOLEWT_VAR)
            try: return self.hArray * mw / 1000.0
            except: return None
        elif name == 'u':
            #This one is kept in W/m2K. Return in W/cm2K
            try: return self.uArray / (100.0**2)
            except: return None
        elif name == ENERGY_VAR:
            return -1.0 * self.qArray
        elif name == 'Re' or name == 'f' or name == 'Holdup' or name == 'FlowRegime':
            profile = self.storedProfiles.get(name, None)
            if profile != None:
                if profile[0] == '':
                    #Calculated with a one phase algorithm
                    return None
                else:
                    #If a two phase calc had only one phase, then it puts a -1 in that space.
                    #Change that -1 for a '-'
                    profile = map(ChangeNegToDash, profile)
            return profile
        
        elif name == 'Velocity':
            profile = self.storedProfiles.get(name, None)
            if profile != None:
                return profile
            w = self.inPort.GetPropValue(MASSFLOW_VAR) #kg/h
            if w == None: return None
            w /= 3600.0                                #kg/s
            massDen = self.GetObject(MASSDEN_VAR)      #kg/m3
            if not massDen: return None
            diam = self.iDiamPort.GetValue()            #m
            if not diam: return None
            crossArea = PI * (diam / 2.0)**2           #m2
            profile = w / (crossArea * massDen)        #m/s
            self.storedProfiles['Velocity'] = profile
            return profile
            
        else:
            try:
                phase = OVERALL_PHASE
                propName = name
                tempDesc = name.split('_', 1)
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
        
        #Load the key that should be used in storedProfiles
        if phase == OVERALL_PHASE:
            keyPropName = propName
        elif phase == VAPOUR_PHASE:
            keyPropName = ('%s_%s' %(Tower.TOWER_VAP_PHASE, propName))
        elif phase == LIQUID_PHASE:
            keyPropName = ('%s_%s' %(Tower.TOWER_LIQ_PHASE, propName))                
        
        
        #Check if it was already stored
        nuSections = self.nuSections
        profile = self.storedProfiles.get(keyPropName, None)
        if profile != None:
            return profile
        
        
        #thermo and arrays should be there
        thCaseObj = self.GetThermo()
        if not thCaseObj: return None
        if not self.hArray or not self.pArray: return None
        

        #See if the results are already loaded in the flash results array
        if self.flashResultsArray and len(self.flashResultsArray) == nuSections+1:
            try:
                fra = self.flashResultsArray
                profile = zeros(nuSections+1, Float)
                if propName != VPFRAC_VAR and propName in fra[0].propNames:
                    idxProp = fra[0].propNames.index(propName)
                    if phase == OVERALL_PHASE:
                        for i in range(nuSections+1):
                            profile[i] = fra[i].bulkProps[idxProp]
                        self.storedProfiles[keyPropName] = profile
                        return profile
                    elif phase == VAPOUR_PHASE:
                        for i in range(nuSections+1):
                            profile[i] = fra[i].phasesProps[0][idxProp]
                        self.storedProfiles[keyPropName] = profile
                        return profile
                    elif phase == LIQUID_PHASE and len(fra.self.phaseFractions) == 1:
                        #Only grab from here if the flash was performed for only one liquid
                        for i in range(nuSections+1):
                            profile[i] = fra[i].phasesProps[1][idxProp]
                        self.storedProfiles[keyPropName] = profile
                        return profile
                elif propName == VPFRAC_VAR:
                        for i in range(nuSections+1):
                            profile[i] = fra[i].phaseFractions[0]
                        self.storedProfiles[keyPropName] = profile
                        return profile
            except:
                pass
                
            
        #Load the compositions
        fracs = self.inPort.GetCompositionValues()
        if not fracs or None in fracs: return None
        nuCmps = len(fracs)
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        profile = None
        
        pArr = self.GetObject(P_VAR)
        hArr = self.GetObject(H_VAR)
        if not pArr: return None
        if not hArr: return None
        #Do a flash for what is needed
        if propName != VPFRAC_VAR:
            
            #Play with fracs to get them in an array with the same fracs for ech segment
            fracs = transpose(reshape(repeat(fracs, nuSections+1, 0), (nuCmps, nuSections+1)))
            profile = reshape(thAdmin.GetProperties(prov, case,
                              (H_VAR,hArr), (P_VAR, pArr), ones(nuSections+1)*phase,
                              fracs, (propName,)), (nuSections+1,))
            
            #Keep a copy of it
            self.storedProfiles[keyPropName] = profile
                
        elif phase == OVERALL_PHASE:
            props = MaterialPropertyDict()
             
            #Get composition and load it into BasicProperties
            compounds = CompoundList(None)
            for cmpIdx in range(len(fracs)):
                prop = BasicProperty(FRAC_VAR)
                prop.SetValue(fracs[cmpIdx], FIXED_V)
                compounds.append(prop)
            compounds.Normalize()
                    
            profile = zeros(nuSections+1, Float)
            for nSeg in range(nuSections+1):
                props[P_VAR].SetValue(pArr[nSeg], FIXED_V)
                props[H_VAR].SetValue(hArr[nSeg], FIXED_V)
                
                results = thAdmin.Flash(prov, case, compounds, props, 2, (P_VAR,))
                profile[nSeg] = results.phaseFractions[0]
                
            #Keep a copy of it
            self.storedProfiles[keyPropName] = profile
        
        return profile
        
        

    def LoadDefaultParameters(self):
        """Loads default parameters. Handy when inheriting"""
        #Initialize with two sides
        self.SetParameterValue(NUSECTIONS_PAR, 2)
        self.SetParameterValue(DP_CORR_PAR, 'OnePhase')
        self.SetParameterValue(ENERGYMODEL_PAR, LINEARQ_MODEL)
        self.SetParameterValue(AV_ENERGYMODELS_PAR, "%s %s %s" %(LINEARQ_MODEL, LINEART_MODEL, EQUALU_MODEL))
        
    def ParameterChanged(self, paramName, value):
        super(PipeSegment, self).ParameterChanged(paramName, value)
        if paramName == NUSECTIONS_PAR:
            nuSections = self.nuSections = value
            self._nuEqns = nuSections*3
            self._nuUnk = nuSections*4 + 4
            
            
    def ValidateParameter(self, paramName, value):
        if not super(PipeSegment, self).ValidateParameter(paramName, value):
            return False
        
        if paramName == NUSECTIONS_PAR:
            if value < 1:
                return False
        
        return True
        
    def DeleteObject(self, obj):
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() == NUSECTIONS_PAR:
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage)
                return
        elif isinstance(obj, PressureDropModel) and self.dpModel is obj:
            if hasattr(self.dpModel, 'CleanUp'):
                self.dpModel.CleanUp()
                self.dpModel
            self.dpModel = None
            return
        super(PipeSegment, self).DeleteObject(obj)
        
    ################################################
        
    def AssignResults(self, vals):
        """Assign the results into the appropriate ports"""
        if self.calcMode == CALC_OUTP_MODE:
            try:
                results = self.flashResultsArray[-1]
                self.outPort.SetPropValue(H_VAR, results.bulkProps[H_IDX], CALCULATED_V)
                self.outPort.SetPropValue(P_VAR, results.bulkProps[P_IDX], CALCULATED_V)
            except:
                pass
            self.outPort.Flash()
            avgVal = sum(self.uArray)/len(self.uArray)
            self.uPort.SetValue(avgVal/(100.0**2), CALCULATED_V)  #W/m2K -> W/cm2K
            self.enePort.SetValue(-1.0*sum(self.qArray), CALCULATED_V)

        elif self.calcMode == CALC_INP_MODE:
            self.outPort.AssignFlashResults(self.flashResultsArray[0])
            
        else:
            isFix = self._unknowns.GetIsFixed()
            mw = self.section.mw
            #Diameter
            if not isFix[self._diamIdx]:
                val = vals[self._diamIdx]
                self.iDiamPort.SetValue(val, CALCULATED_V)  
            
            #Mass flow
            if not isFix[self._wIdx]:
                val = vals[self._wIdx] * (3600.0) #kg/s -> kg/h
                self.inPort.SetPropValue(MASSFLOW_VAR, val, CALCULATED_V)
                self.outPort.SetPropValue(MASSFLOW_VAR, val, CALCULATED_V)        
            
            #Pressure
            if not isFix[self.pArrayIdx[0]]:
                val = vals[self.pArrayIdx[0]] * (1/1000.0)   #Pa -> kPa
                self.inPort.SetPropValue(P_VAR, val, CALCULATED_V)
            if not isFix[self.pArrayIdx[-1]]:
                val = vals[self.pArrayIdx[-1]] * (1/1000.0)   #Pa -> kPa
                self.outPort.SetPropValue(P_VAR, val, CALCULATED_V)            
            self.SolveForPressure()
               
            #Enthalpy
            if not isFix[self.hArrayIdx[0]]:
                val = vals[self.hArrayIdx[0]]* (1/1000.0) * mw  #kJ/kg -> J/kg
                self.inPort.SetPropValue(H_VAR, val, CALCULATED_V)
            if not isFix[self.hArrayIdx[-1]]:
                val = vals[self.hArrayIdx[-1]]* (1/1000.0) * mw  #kJ/kg -> J/kg
                self.outPort.SetPropValue(H_VAR, val, CALCULATED_V) 
                
            #Q
            if not isFix[self.qArrayIdx[0]]:
                self.enePort.SetValue(-1.0*sum(self.qArray), CALCULATED_V)
              
            #U
            if not isFix[self.uArrayIdx[0]]:
                avgVal = sum(self.uArray)/len(self.uArray)
                self.uPort.SetValue(avgVal/(100.0**2), CALCULATED_V)  #W/m2K -> W/cm2K 

            
    def GetNuSpecsNeeded(self):
        #Number of specs needed is just a substractions on unknwons - nu equations
        nuSections = self.nuSections
        
        #P, H, Q, U per section plus D, flow, inP, inH
        nuUnk = nuSections*4 + 4
        
        #mech ene bal eq, ene bal eq, heat transfer eq per section
        # q or u model eq per section-1
        nuEq = nuSections*3 + nuSections-1
        return nuUnk - nuEq
    
    def Solve(self):
        
        #Let the base class administer the solving. Just prevent from the two phase flash msg
        MessageHandler.IgnoreMessage('LumpLiqs')
        self.unitOpMessage = ('NoMessage', )
        self.converged = False
        tempSolveMethod = self._numMethodSetings.solveMethod
        super(PipeSegment, self).Solve()
        self._numMethodSetings.solveMethod = tempSolveMethod
        MessageHandler.UnIgnoreMessage('LumpLiqs')
        
        
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
        
    def ClearProfiles(self):
        self.storedProfiles = {}
        
        nuSections = self.nuSections
        
        self.pArray = zeros(nuSections+1, Float)
        self.hArray = zeros(nuSections+1, Float)
        self.qArray = zeros(nuSections, Float)
        self.uArray = zeros(nuSections, Float)
        
        #Physical structure
        self.diamArray = zeros(nuSections+1, Float)
        self.yArray = zeros(nuSections+1, Float)  #vertical position (not length)
        self.xArray = zeros(nuSections+1, Float)  #horizontal position (not length)
        #self.zArray = zeros(nuSections+1, Float)  #NOT NEEDED
        
        self.lenArray = zeros(nuSections, Float)  #Length per section
        #Note that lenArray[0] = sqrt((zArray[1] - zArray[0])**2 + (xArray[1] - xArray[0])**2)
        
        self.pArrayIdx = zeros(nuSections+1, Int)
        self.hArrayIdx = zeros(nuSections+1, Int)
        self.qArrayIdx = zeros(nuSections, Int)
        self.uArrayIdx = zeros(nuSections, Int)
        
        self.flashResultsArray = [None] * (nuSections + 1)
        
    def SolveLiveProfiles(self):
        """Solve for hte profiles that can be spec by the user"""
        if not self.GetParameterValue(DETAILED_PAR):
            pass
        
        nuSections = self.nuSections
        profiles = self.liveProfiles
        
        #All the info must be there. No interpolations will be done for now
        xProf = profiles['x'].GetProperties()
        yProf = profiles['y'].GetProperties()
        lenProf = profiles[LENGTH_PORT].GetProperties()
        kProf = profiles['K'].GetProperties()
        
        
        if nuSections+1 != len(xProf):
            profiles['x'].SetSize(nuSections+1)
        if nuSections+1 != len(yProf):
            profiles['y'].SetSize(nuSections+1)
        if nuSections != len(lenProf):
            profiles[LENGTH_PORT].SetSize(nuSections)
        if nuSections+1 != len(kProf):
            profiles['K'].SetSize(nuSections+1)
        
        xVals = profiles['x'].GetValues()
        yVals = profiles['y'].GetValues()
        lenVals = profiles[LENGTH_PORT].GetValues()
        kVals = profiles['K'].GetValues()
        
        y0 = self.y0Port.GetValue()
        y1 = self.y1Port.GetValue()
        totLen = self.lenPort.GetValue()
        
        #Put the values of the ports in the corresponding profiles
        if y0 != None:
            yProf[0].SetValue(y0, CALCULATED_V)
            yVals[0] = y0
        if y1 != None:
            yProf[-1].SetValue(y1, CALCULATED_V)
            yVals[-1] = y1
        if nuSections == 1 and totLen != None:
            lenVals[0] = totLen
            lenProf[0].SetValue(totLen, CALCULATED_V)
            
        #Default x0 to 0.0
        if xProf[0].GetValue() == None:
            xProf[0].SetValue(0.0, FIXED_V)
            xVals[0] = 0.0
            
        #Iterate and solve depending on the known information
        for sec in range(nuSections):
            yDisp = None
            xDisp = None
            
            if yVals[sec] != None and yVals[sec+1] != None:
                yDisp = yVals[sec+1] - yVals[sec]
            if xVals[sec] != None and xVals[sec+1] != None:
                xDisp = xVals[sec+1] - xVals[sec]  
                if yDisp != None:
                    val = sqrt(yDisp**2+xDisp**2)
                    lenProf[sec].SetValue(val, CALCULATED_V)
                    lenVals[sec] = val
                    continue
                elif lenVals[sec] != None:
                    yDisp = sqrt(lenVals[sec]**2-xDisp**2)
                    if yVals[sec] != None:
                        val = yVals[sec]+yDisp
                        yProf[sec+1].SetValue(val, CALCULATED_V)
                        yVals[sec+1] = val
                    elif yVals[sec+1] != None:
                        val = yVals[sec+1]-yDisp
                        yProf[sec].SetValue(val, CALCULATED_V)
                        yVals[sec] = val
                    continue
            if lenVals[sec] != None and yDisp != None:
                    xDisp = sqrt(lenVals[sec]**2-yDisp**2)
                    if xVals[sec] != None:
                        val = xVals[sec]+xDisp
                        xProf[sec+1].SetValue(val, CALCULATED_V)
                        xVals[sec+1] = val
                    elif xVals[sec+1] != None:
                        val = xVals[sec+1]-xDisp
                        xProf[sec].SetValue(val, CALCULATED_V)
                        xVals[sec] = val
                    continue
                    
            if kVals[sec] == None:
                kProf[sec].SetValue(0.0, FIXED_V)
        if kVals[-1] == None:
            kProf[-1].SetValue(0.0, FIXED_V)
                
            
        #Finally check if there is info that can be put in ports
        if yVals[0] != None:
            self.y0Port.SetValue(yVals[0], CALCULATED_V)
        if yVals[-1] != None:
            self.y1Port.SetValue(yVals[-1], CALCULATED_V)
        
        try:
            totLen = sum(lenVals)
            self.lenPort.SetValue(totLen, CALCULATED_V)
        except:
            pass
        
        
    def PrepareForSolve(self):
        """Share properties and if composition is unknown, then return False"""
        
        ready = True
        inPort = self.inPort
        outPort = self.outPort
        self.section = None

        forgetting = self.IsForgetting()
        
        #Get thermo
        self._thCaseObj = self.GetThermo()
        if self._thCaseObj: 
            thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        else:
            ready = False
            
        #Share the compositions
        inPort.ShareComposition(outPort)
        inPort.SharePropWith(outPort, MASSFLOW_VAR)
        self.FlashAllPorts()
        
        mw = inPort.GetPropValue(MOLEWT_VAR)
        self._fracs = inPort.GetCompositionValues()
        if None in self._fracs or not self._fracs:
            ready = False
            self.unitOpMessage = ('MissingVariable', ('Composition', self.GetName()))
        else:
            nuCmps = len(self._fracs)
            
            
            #Load the compositions into a list that can be used for flashes
            self._localCmpList = CompoundList(None)
            for i in range(nuCmps):
                self._localCmpList.append(BasicProperty(FRAC_VAR))
            self._localCmpList.SetValues(self._fracs, FIXED_V)
            
            if not mw:
                MWLst = []
                for i in range(nuCmps):
                    #Note: cmpMwt is an array with only one element because only one prop (Mwt) was requested
                    MWLst.append(thAdmin.GetSelectedCompoundProperties(prov, case, i, 'MolecularWeight')[0])
                mw = Numeric.sum(array(MWLst, Float) * array(self._fracs, Float))
                

        self.SolveForPressure()
        self.FlashAllPorts()
        
        self.nuSolPhases = self.NumberSolidPhases()
        
        self.ignoreKinAndPot = self.GetParameterValue(IGNOREKINANDPOT_PAR)
        if self.ignoreKinAndPot:
            self.balance.DoBalance()
            
        #Make sure it has sections
        nuSections = self.nuSections = self.GetParameterValue(NUSECTIONS_PAR)
        if not nuSections:
            nuSections = self.nuSections = 1
            self.SetParameterValue(NUSECTIONS_PAR, nuSections)        
        
        
        #Make sure profiles are ready for solution
        self.ClearProfiles()
        self.storedProfiles['Re'] = ones(nuSections, Float) * -1
        self.storedProfiles['f'] = ones(nuSections, Float) * -1
        self.storedProfiles['Holdup'] = ones(nuSections, Float) * -1
        self.storedProfiles['FlowRegime'] = [''] * nuSections
        
        
        #Forget all live profiles
        #This is a customized Forget which just clears calcualted values
        for prof in self.liveProfiles.values():
            prof.Forget()
        self.SolveLiveProfiles()
        detailed = self.GetParameterValue(DETAILED_PAR)
        
        
        #Don't keep on going if it is forgetting
        if self.IsForgetting():
            return False
        
        if not self.dpModel:
            #Can't solve if there is no pressure drop model
            self.InfoMessage('MissingDPModel', (self.GetPath(),))
            return False
        
        #Load all the info of the pipe
        diam = self.iDiamPort.GetValue()
        totLen = self.lenPort.GetValue()
        y0 = self.y0Port.GetValue()
        y1 = self.y1Port.GetValue()
        rough = self.roughPort.GetValue()
        tAmb = self.ambTPort.GetValue()
        if None in (totLen, y0, y1, rough, tAmb):
            if totLen == None:
                self.unitOpMessage = ('MissingVariable', (self.lenPort.GetName(), self.GetName()))
            elif y0 == None:
                self.unitOpMessage = ('MissingVariable', (self.y0Port.GetName(), self.GetName()))
            elif y1 == None:
                self.unitOpMessage = ('MissingVariable', (self.y1Port.GetName(), self.GetName()))
            elif rough == None:
                self.unitOpMessage = ('MissingVariable', (self.roughPort.GetName(), self.GetName()))
            elif tAmb == None:
                self.unitOpMessage = ('MissingVariable', (self.ambTPort.GetName(), self.GetName()))
            ready = False
        else:
            #Load y and len profiles
            try:
                self._yVec = array(self.liveProfiles['y'].GetValues(), Float)
            except:
                if y0 != y1:
                    self._yVec = EquationSolver.CreateLinearDistArray(nuSections+1, y0, y1)
                else:
                    self._yVec = ones(nuSections+1, Float)*y0
            try: self._lenVec = array(self.liveProfiles[LENGTH_PORT].GetValues(), Float)
            except: self._lenVec = zeros(nuSections, Float) + totLen/nuSections
                
            try: self._kVec = array(self.liveProfiles['K'].GetValues(), Float)
            except: self._kVec = zeros(nuSections+1, Float)  
        
        #correlation to use
        self.dpCorr = self.GetParameterValue(DP_CORR_PAR)
        if not self.dpCorr:
            self.dpCorr = 'OnePhase'
            
        self.htModel = self.GetParameterValue(ENERGYMODEL_PAR)
        if self.htModel == None or not self.htModel in (LINEARQ_MODEL, LINEART_MODEL, EQUALU_MODEL): 
            self.htModel = LINEARQ_MODEL
            
        #Check if it can solve with a specific algorithm
        if ready and inPort.AlreadyFlashed() and inPort.GetPropValue(MOLEFLOW_VAR) and \
                     ((self.enePort.GetValue() != None and self.htModel == LINEARQ_MODEL) or (self.uPort.GetValue() != None and self.htModel == EQUALU_MODEL)) and \
                     (self.iDiamPort.GetValue() != None):
            self.calcMode = CALC_OUTP_MODE
            self.InfoMessage('SolveMode_OutP', (self.GetPath(),))
            converged = self.solveMethods[CALC_OUTP_MODE].Solve()
            if converged:
                #No need to pass a parameter as everything is already in arrays
                self.AssignResults(None)
                self.SolveForPressure()
                #self.FlashAllPorts()
            ready = False
            
        #elif ready and outPort.AlreadyFlashed() and inPort.GetPropValue(MOLEFLOW_VAR)and \
                     #(self.enePort.GetValue() != None or self.uPort.GetValue() != None ) :
            #self.calcMode = CALC_INP_MODE
            #self.SolveForInP()
            #ready = False
            
        else:
            #Solve everything simoultaneously if enough info is there but no
            #special algorithm can be used
            self.calcMode = CALC_GENERIC_MODE
            self.section = section = PipeSectionInfoHolder()
            self.section.mw = mw
            self.section.tAmb = tAmb
            self.section.rough = rough
            section.dpCorr = self.dpCorr
            
        return ready
        
    
    def LoadUnknowns(self, unk):

        AddUnknown = unk.AddUnknown
        SolverVariable = EquationSolver.SolverVariable
        inPort = self.inPort
        outPort = self.outPort
        nuSections = self.nuSections
        mw = self.section.mw
        
        #Initialize the temperature specs
        self.t0Spec = None
        self.t1Spec = None
        self.QSpec = None
        self.USpec = None
            
        #Do diameter
        diamVal = self.iDiamPort.GetValue()
        isSpec = diamVal != None
        if not isSpec:
            diamVal = 0.06 #m What else to do??
        self.scaleFactorL = abs(diamVal)
        unkVar = SolverVariable('ID', diamVal, diamVal, isSpec, self.scaleFactorL, 0.0, 50.0)
        self._diamIdx = AddUnknown(unkVar) #Returns the index where the unk was put       
            
        
        #Do mass flow
        wVal = inPort.GetPropValue(MASSFLOW_VAR)
        isSpec = wVal != None
        if not isSpec:
            wVal = 100.0 #What else to do??
        wVal = wVal * (1/3600.0)   #kg/h -> kg/s
        self.scaleFactorW = min(10.0, (abs(wVal)/10.0))
        unkVar = SolverVariable('W', wVal, wVal, isSpec, self.scaleFactorW, -1E+30, 1E30)
        self._wIdx = AddUnknown(unkVar) #Returns the index where the unk was put        
        
        
        #Do pressure
        p0Val = inPort.GetPropValue(P_VAR)
        p1Val = outPort.GetPropValue(P_VAR)
        isSpec = zeros(nuSections+1, Int)
        isSpec[0] = p0Val != None
        isSpec[-1] = p1Val != None
        if None == p0Val and p1Val == None:
            p0Val = p1Val = 101.0              #kPa
        elif None == p0Val:
            p0Val = p1Val
        elif None == p1Val:
            p1Val = p0Val
        pArray = EquationSolver.CreateLinearDistArray(self.nuSections+1, p0Val, p1Val)
        pArray = pArray * (1000.0)   #kPa -> Pa
        self.scaleFactorP = min(abs(pArray))
        for i in range(nuSections+1):
            unkVar = SolverVariable('P%i'%i, pArray[i], pArray[i], isSpec[i], 
                                    self.scaleFactorP, 0.01, 1E30)
            self.pArrayIdx[i] = AddUnknown(unkVar)
        self.pArray = pArray
            
        
        #Do enthalpy
        _h0MolVal = inPort.GetPropValue(H_VAR)       #kJ/kmol
        _h1MolVal = outPort.GetPropValue(H_VAR)      #kJ/kmol
        #Make it mass enthalpy
        if None != _h0MolVal: h0Val = _h0MolVal/mw   #kJ/kg
        else: h0Val = None
        if None != _h1MolVal: h1Val = _h1MolVal/mw   #kJ/kg
        else: h1Val = None

        if self.ignoreKinAndPot:
            if h0Val != None and h1Val != None:
                #Can not use both as specs in this mode
                h1Val = None
                
        isSpec[0] = h0Val != None
        isSpec[-1] = h1Val != None
        if None == h0Val or h1Val == None:
            
            #Flash all the pairs of P, H
            thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
            nuLiqPhases = 1
            nuSolPhases = self.nuSolPhases
            matDict = self._localMatDict
            cmps = self._localCmpList
            matDict[H_VAR].SetValue(None, UNKNOWN_V)
                
            #See if a temperature is known
            self.scaleFactorT = PropTypes[T_VAR].scaleFactor
            t0 = inPort.GetPropValue(T_VAR)
            if t0 != None and h0Val == None:
                matDict[P_VAR].SetValue(p0Val, FIXED_V)      #kPa
                matDict[T_VAR].SetValue(t0, FIXED_V)         #K
                results = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, [H_VAR], nuSolPhases)
                h0Val = results.bulkProps[0]       #kJ/kmol
                h0Val /= mw                        #kJ/kg
                if h1Val == None: h1Val = h0Val
                self.t0Spec = t0
            else:
                t1 = outPort.GetPropValue(T_VAR)
                if t1 != None and h1Val == None:
                    #Do a pt flash and estimate an h1
                    matDict[P_VAR].SetValue(p1Val, FIXED_V)      #kPa
                    matDict[T_VAR].SetValue(t1, FIXED_V)         #K
                    results = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, [H_VAR], nuSolPhases)
                    h1Val = results.bulkProps[0]       #kJ/kmol
                    h1Val /= mw                                  #kJ/kg
                    if h0Val == None: h0Val = h1Val
                    self.t1Spec = t1
                    
            matDict[T_VAR].SetValue(None, UNKNOWN_V)
            
        if None == h0Val:
            h0Val = h1Val
        if None == h1Val:
            h1Val = h0Val
        if h0Val == None or h1Val == None:
            h0Val = h1Val = 1.0E4 #Just a number
        hArray = EquationSolver.CreateLinearDistArray(nuSections+1, h0Val, h1Val)
        hArray = hArray * (1000.0)                   #kJ/kg -> J/kg
        self.scaleFactorH = PropTypes[H_VAR].scaleFactor #Assume a scale factor in J/kg
        for i in range(self.nuSections+1):
            unkVar = SolverVariable('H%i'%i, hArray[i], hArray[i], isSpec[i], 
                                    self.scaleFactorH, -1E30, 1E30)
            self.hArrayIdx[i] = AddUnknown(unkVar)            
        self.hArray = hArray
            
        
        #Energy
        qTotVal = self.enePort.GetValue()
        uVal = self.uPort.GetValue()
        isSpecQ = qTotVal != None
        isSpecU = uVal != None
        #Can not spec Q and U at the same time
        isSpecU = where(isSpecQ, False, isSpecU)[0]
        if isSpecQ:
            qArray = -1.0 * (qTotVal/nuSections)*ones(nuSections, Float)
        else:
            qArray = zeros(nuSections, Float)
        if isSpecU:
            uArray = uVal*ones(nuSections, Float)
        else:
            uArray = zeros(nuSections, Float)
        uArray = uArray * (100.0**2)      #W/cm2K -> W/m2K
        
        
        self.scaleFactorQ = PropTypes[ENERGY_VAR].scaleFactor 
        self.scaleFactorU = 10.0
        isSpec = False
        for i in range(nuSections):
            unkVar = SolverVariable('Q%i'%i, qArray[i], qArray[i], isSpec, 
                                    self.scaleFactorQ, -1E30, 1E30)
            self.qArrayIdx[i] = AddUnknown(unkVar)
               
            unkVar = SolverVariable('U%i'%i, uArray[i], uArray[i], isSpec, 
                                    self.scaleFactorU, -1E30, 1E30)
            self.uArrayIdx[i] = AddUnknown(unkVar)
            
        self.qArray = qArray
        self.uArray = uArray
        
        if isSpecQ and isSpecU:
            self.unitOpMessage = ('SpecConflict', (self.enePort.GetName(), self.uPort.GetName(), self.GetName()))
            return False
        elif isSpecQ:
            self.QSpec = -1.0*qTotVal #The solver uses it with the sign reversed
        elif isSpecU:
            #Force this to be equal along pipe
            self.htModel = EQUALU_MODEL
            self.USpec = uVal * (100.0**2)      #W/cm2K -> W/m2K
            
        nuSpecsNeeded = self.GetNuSpecsNeeded()
        isSpecVec = unk.GetIsFixed()
        nuSpecs = Numeric.sum(isSpecVec) + bool(self.t0Spec) + bool(self.t1Spec) + bool(isSpecQ) + bool(isSpecU)
        if nuSpecsNeeded > nuSpecs:
            self.unitOpMessage = ('MissingSpecs', (nuSpecsNeeded-nuSpecs, ))
            return False
        
        if self.t0Spec != None or self.t1Spec != None:
            #Broyden is more stable for this method since the analytic jacobian ignores some
            #variables
            if self._numMethodSetings.solveMethod == EquationSolver.NR:
                self._numMethodSetings.solveMethod = EquationSolver.BROYDEN
                
        return True        #Check if it has enough specs


    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        """Calculates the right hand side of the design equations"""

        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        propList = self.dpModel.GetRequiredProperties()
        nuSections = self.nuSections
        section = self.section
        mw = section.mw
        yVec = self._yVec
        tAmb = section.tAmb
        rough = section.rough
        dpModel = self.dpModel
        #htModel = self.htModel
        storedProfiles = self.storedProfiles
        
        if self.htModel == LINEART_MODEL:
            if not CP_VAR in propList:
                propList.append(CP_VAR)        
        
        
        #Load stuff from x
        w = x[self._wIdx]
        diam = x[self._diamIdx]
        pArray = self.pArray[:] = take(x, self.pArrayIdx)
        hArray = self.hArray[:] = take(x, self.hArrayIdx)
        qArray = self.qArray[:] = take(x, self.qArrayIdx)
        uArray = self.uArray[:] = take(x, self.uArrayIdx)
        
        
        #Flash all the pairs of P, H
        resultsArray = (nuSections+1)*[None]
        nuLiqPhases = 1
        matDict = self._localMatDict
        cmps = self._localCmpList
        for i in range(nuSections+1):
            matDict[P_VAR].SetValue(pArray[i]/1000.0, FIXED_V)      #kPa
            matDict[H_VAR].SetValue(hArray[i]*mw/1000.0, FIXED_V)   #kJ/kmol
            resultsArray[i] = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, propList, self.nuSolPhases)
        self.flashResultsArray = resultsArray
            
        #Make a linear T profile if necessary
        if self.htModel == LINEART_MODEL:
            tLine = EquationSolver.CreateLinearDistArray(nuSections+1, resultsArray[0].bulkProps[T_IDX],
                                                         resultsArray[-1].bulkProps[T_IDX])
        
        #Load some stuff into the section object
        section.diam = diam
        section.crossArea = crossArea = PI * (diam / 2.0)**2              #m2
        section.relRough = rough/diam
        section.massFlow = w
        section.k0 = self._kVec[0]
        section.dpCorr = self.dpCorr
        
        
        for i in range(nuSections):
            bulkProps0 = resultsArray[i].bulkProps
            bulkProps1 = resultsArray[i+1].bulkProps
            
            #Load some variables
            p0 = pArray[i]
            h0 = hArray[i]
            den0, t0, y0 = bulkProps0[MASSDEN_IDX], bulkProps0[T_IDX], yVec[i]
            
            p1 = pArray[i+1]
            h1 = hArray[i+1]
            den1, t1, y1 = bulkProps1[MASSDEN_IDX], bulkProps1[T_IDX], yVec[i+1]

            v1 = w / (den1 * crossArea)
            v0 = w / (den0 * crossArea)            
                      
            q = qArray[i]
            u = uArray[i]
            
            section.y0 = self._yVec[i]
            section.y1 = self._yVec[i+1]
            section.len = self._lenVec[i]
            section.k1 = self._kVec[i+1]
            section.surfArea = surfArea = PI * diam * section.len
            
            
            #This values get loaded into the section object
            section.Re = None
            section.f = None
            section.holdup = None
            section.flowRegime = None
            
            #Mechanical energy (Bernoulli)
            #(P0-P1) - DPFromModel = 0
            dp = dpModel.CalcPressureDrop(resultsArray[i], resultsArray[i+1], section)
            rhs[eqnNo] = -(p1-p0) - dp
            rhs[eqnNo] /= self.scaleFactorP
            eqnNo += 1            
    
            #Energy balance
            #'(U + PV + kinetic + potential) - (U + PV + kinetic + potential)
            #(J/kg + m2/s2 + (m/s2)m) kg/s -> (J/s + kgm2/s2 + kgm2/s2) -> J/s + Nm + Nm -> J/s
            if self.ignoreKinAndPot:
                qIn = (h0) * w
                qOut = (h1) * w
            else:
                qIn = (h0 + v0**2/2.0 + GRAVITY*y0 ) * w    
                qOut = (h1 + v1**2/2.0 + GRAVITY*y1 ) * w
            rhs[eqnNo] = (qOut - qIn - q) / self.scaleFactorQ
            eqnNo += 1
            
            
            #Heat trhansfer equation
            #Q is negative when it leaves the system
            #Q + UADT = 0
            dt = self.CalculateDeltaT(t0, t1, tAmb)
            adt = surfArea*(dt)
            rhs[eqnNo] = (q + u*adt) / self.scaleFactorQ
            eqnNo += 1           
            
            
            #Heat transfer coefficient model
            #A simple line for now
            if i:
                if self.htModel == LINEART_MODEL:
                    rhs[eqnNo] = (t0 - tLine[i]) / self.scaleFactorT
                elif self.htModel == EQUALU_MODEL:
                    rhs[eqnNo] = (uArray[i] - uArray[i-1]) / self.scaleFactorU
                else:
                    rhs[eqnNo] = (qArray[i] - qArray[i-1]) / self.scaleFactorQ
                eqnNo += 1
                
                #U - UModel = 0
                #rhs[eqnNo] = u - htModel.CalcU(knownResults, newResults, y0, y1)
                #rhs[eqnNo] /= self.scaleFactorU
                #eqnNo += 1
                   
            section.k0 = 0.0 #This is only used for the first iter
            
            #The section should now have loaded these values
            if section.Re != None:
                storedProfiles['Re'][i] = section.Re
            if section.f != None:
                storedProfiles['f'][i] = section.f
            if section.holdup != None:
                storedProfiles['Holdup'][i] = section.holdup
            if section.flowRegime != None:
                storedProfiles['FlowRegime'][i] = section.flowRegime
            
        #In case Q or U are specs
        if self.QSpec != None:
            rhs[eqnNo] = (sum(self.qArray) - self.QSpec ) / self.scaleFactorQ
            eqnNo += 1
        if self.USpec != None:
            rhs[eqnNo] = (sum(self.uArray)/len(self.uArray) - self.USpec) / self.scaleFactorU
            eqnNo += 1
            
        #In case temperatures are specs
        if self.t0Spec:
            t0 = resultsArray[0].bulkProps[T_IDX]
            rhs[eqnNo] = (t0 - self.t0Spec) / self.scaleFactorT
            eqnNo += 1
        if self.t1Spec:
            t1 = resultsArray[-1].bulkProps[T_IDX]
            rhs[eqnNo] = (t1 - self.t1Spec) / self.scaleFactorT
            eqnNo += 1
                
        unk = self._unknowns
        #Eqn's for known vars
        for idx in range(len(x)):
            if isFix[idx]:
                rhs[eqnNo] = (x[idx] - initx[idx]) / unk._unkScaleFacts[idx]
                eqnNo += 1

        return eqnNo

    def CalculateJacobian(self, x, j, isFix, initx, eqnNo=0):
        """Calculates the right hand side of the design equations"""

        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        propList = self.dpModel.GetRequiredProperties()
        nuSections = self.nuSections
        section = self.section
        mw = section.mw
        tAmb = section.tAmb
        yVec = self._yVec
        dpModel = self.dpModel
        #htModel = self.htModel
        matDict = self._localMatDict
        cmps = self._localCmpList
        nuLiqPhases = 1
        resultsArray = self.flashResultsArray
        
        if self.htModel == LINEART_MODEL:
            if not CP_VAR in propList:
                cpIdx = len(propList)
            else:
                cpIdx = propList.index(CP_VAR)
            tLine = EquationSolver.CreateLinearDistArray(nuSections+1, resultsArray[0].bulkProps[T_IDX],
                                                         resultsArray[-1].bulkProps[T_IDX])
            cP0 = resultsArray[0].bulkProps[cpIdx]
            cPEnd = resultsArray[-1].bulkProps[cpIdx]
            
        #Load stuff from x
        w = x[self._wIdx]
        diam = x[self._diamIdx]
        pArray = self.pArray[:] = take(x, self.pArrayIdx)
        hArray = self.hArray[:] = take(x, self.hArrayIdx)
        qArray = self.qArray[:] = take(x, self.qArrayIdx)
        uArray = self.uArray[:] = take(x, self.uArrayIdx)
            
        
        #Load some stuff into the section object
        section.diam = diam
        section.crossArea = crossArea = PI * (diam / 2.0)**2              #m2
        section.relRough = section.rough/diam
        section.massFlow = w
        section.k0 = self._kVec[0]
        section.dpCorr = self.dpCorr
        
        for i in range(nuSections):
            bulkProps0 = resultsArray[i].bulkProps
            bulkProps1 = resultsArray[i+1].bulkProps
            
            #Load some variables
            #p0 = pArray[i]
            h0 = hArray[i]
            den0, t0, y0 = bulkProps0[MASSDEN_IDX], bulkProps0[T_IDX], yVec[i]
            
            #p1 = pArray[i+1]
            h1 = hArray[i+1]
            den1, t1, y1 = bulkProps1[MASSDEN_IDX], bulkProps1[T_IDX], yVec[i+1]

            v1 = w / (den1 * crossArea)
            v0 = w / (den0 * crossArea)            
                      
            q = qArray[i]
            u = uArray[i]
            
            section.y0 = self._yVec[i]
            section.y1 = self._yVec[i+1]
            section.len = self._lenVec[i]
            section.k1 = self._kVec[i+1]
            section.surfArea = surfArea = PI * diam * section.len
            
            #Mechanical energy (Bernoulli)
            #(P0-P1) - DPFromModel = 0
            j[eqnNo][self.pArrayIdx[i+1]] = -1.0 / self.scaleFactorP
            j[eqnNo][self.pArrayIdx[i]] = 1.0 / self.scaleFactorP
            
            #Do a crude differential for the effect of w
            olddp = dpModel.CalcPressureDrop(resultsArray[i], resultsArray[i+1], section)
            shift = 0.001
            section.massFlow += shift
            dp = dpModel.CalcPressureDrop(resultsArray[i], resultsArray[i+1], section)
            section.massFlow -= shift
            j[eqnNo][self._wIdx] = -((dp - olddp) / shift) / self.scaleFactorP
            
            
            #Do a crude differential for the effect of diameter
            shift = 0.0001
            section.diam += shift
            section.crossArea = crossArea = PI * (section.diam / 2.0)**2              #m2
            section.relRough = section.rough/section.diam            
            section.surfArea = surfArea = PI * section.diam * section.len
            dp = dpModel.CalcPressureDrop(resultsArray[i], resultsArray[i+1], section)
            section.diam -= shift
            section.crossArea = crossArea = PI * (section.diam / 2.0)**2              #m2
            section.relRough = section.rough/section.diam
            section.surfArea = surfArea = PI * section.diam * section.len
            j[eqnNo][self._diamIdx] = -((dp - olddp) / shift) / self.scaleFactorP
            
            
            #rhs[eqnNo] = -(p1-p0) - dp
            #rhs[eqnNo] /= self.scaleFactorP
            eqnNo += 1            
    
            #Energy balance
            #'(U + PV + kinetic + potential) - (U + PV + kinetic + potential)
            #(J/kg + m2/s2 + (m/s2)m) kg/s -> (J/s + kgm2/s2 + kgm2/s2) -> J/s + Nm + Nm -> J/s
            j[eqnNo][self.hArrayIdx[i+1]] = w / self.scaleFactorQ
            j[eqnNo][self.hArrayIdx[i]] = -w / self.scaleFactorQ
            j[eqnNo][self.qArrayIdx[i]] = -1.0 / self.scaleFactorQ
            j[eqnNo][self._wIdx] = ( (h1 + v1**2/2.0 + GRAVITY*y1) - (h0 + v0**2/2.0 + GRAVITY*y0) ) / self.scaleFactorQ
            #qIn = (h0 + v0**2/2.0 + GRAVITY*y0 ) * w    
            #qOut = (h1 + v1**2/2.0 + GRAVITY*y1 ) * w
            #rhs[eqnNo] = (qOut - qIn - q) / self.scaleFactorQ
            eqnNo += 1
            
            
            #Heat transfer equation
            #Q - UADT = 0
            dt = self.CalculateDeltaT(t0, t1, tAmb)
            adt = surfArea*(dt)
            j[eqnNo][self.qArrayIdx[i]] = 1.0 / self.scaleFactorQ
            j[eqnNo][self.uArrayIdx[i]] = adt / self.scaleFactorQ
            j[eqnNo][self._diamIdx] = u * PI * section.len * dt / self.scaleFactorQ
            #rhs[eqnNo] = (q - u*PI * diam * section.len*dt) / self.scaleFactorQ
            #rhs[eqnNo] = (q - u*adt) / self.scaleFactorQ
            eqnNo += 1           
            
            
            #Heat transfer coefficient model
            #A simple line for now
            if i:
                if self.htModel == LINEART_MODEL:
                    #Derivative of this (t0 - tLine[i]) / self.scaleFactorT
                    j[eqnNo][self.hArrayIdx[0]] = ( (-1.0 / cP0) + (i / (nuSections * cP0)) ) / self.scaleFactorT
                    j[eqnNo][self.hArrayIdx[i]] = (1.0 / resultsArray[i].bulkProps[cpIdx]) / self.scaleFactorT
                    j[eqnNo][self.hArrayIdx[-1]] = (-i / (nuSections * cPEnd)) / self.scaleFactorT
                elif self.htModel == EQUALU_MODEL:
                    #Derivative of this (uArray[i] - uArray[i-1]) / self.scaleFactorU
                    j[eqnNo][self.uArrayIdx[i]] = 1.0 / self.scaleFactorU
                    j[eqnNo][self.uArrayIdx[i-1]] = -1.0 / self.scaleFactorU
                else:
                    #Derivative of this (qArray[i] - qArray[i-1]) / self.scaleFactorQ
                    j[eqnNo][self.qArrayIdx[i]] = 1.0 / self.scaleFactorQ
                    j[eqnNo][self.qArrayIdx[i-1]] = -1.0 / self.scaleFactorQ         
                eqnNo += 1
                
                #U - UModel = 0
                #rhs[eqnNo] = u - htModel.CalcU(knownResults, newResults, y0, y1)
                #rhs[eqnNo] /= self.scaleFactorU
                #eqnNo += 1
                   
            
        #In case Q or U are specs
        if self.QSpec != None:
            #Derivative of (sum(self.qArray) - self.QSpec ) / self.scaleFactorQ
            Numeric.put(j[eqnNo], self.qArrayIdx, ones(len(self.qArray), Float)/self.scaleFactorQ)
            eqnNo += 1
        if self.USpec != None:
            #Derivative of (sum(self.uArray)/len(self.uArray) - self.USpec) / self.scaleFactorU
            Numeric.put(j[eqnNo], self.uArrayIdx, ones(len(self.uArray), Float) / len(self.uArray) / self.scaleFactorU)
            eqnNo += 1
            
        #In case temperatures are specs
        if self.t0Spec:
            t0 = resultsArray[0].bulkProps[T_IDX]
            p0 = pArray[0] / 1000.0      #kPa
            h0 = hArray[0]*mw/1000.0     #kJ/kmol
            
            shift = 1.0
            p0 += shift
            matDict[P_VAR].SetValue(p0, FIXED_V)      #kPa
            matDict[H_VAR].SetValue(h0, FIXED_V)      #kJ/kmol
            results = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, propList, self.nuSolPhases)
            j[eqnNo][self.pArrayIdx[0]] = (results.bulkProps[T_IDX] - t0) / (self.scaleFactorT*shift)
            p0 -= shift
            
            shift = 10.0
            h0 += shift
            matDict[P_VAR].SetValue(p0, FIXED_V)      #kPa
            matDict[H_VAR].SetValue(h0, FIXED_V)      #kJ/kmol
            results = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, propList, self.nuSolPhases)
            j[eqnNo][self.hArrayIdx[0]] = (results.bulkProps[T_IDX] - t0) / (self.scaleFactorT*shift)
            
            eqnNo += 1
            
        if self.t1Spec:
            t1 = resultsArray[-1].bulkProps[T_IDX]
            p1 = pArray[-1] / 1000.0      #kPa
            h1 = hArray[-1]*mw/1000.0     #kJ/kmol
            
            shift = 1.0
            p1 += shift
            matDict[P_VAR].SetValue(p1, FIXED_V)      #kPa
            matDict[H_VAR].SetValue(h1, FIXED_V)      #kJ/kmol
            results = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, propList, self.nuSolPhases)
            j[eqnNo][self.pArrayIdx[-1]] = (results.bulkProps[T_IDX] - t1) / (self.scaleFactorT*shift)
            p1 -= shift
            
            shift = 10.0
            h1 += shift
            matDict[P_VAR].SetValue(p1, FIXED_V)      #kPa
            matDict[H_VAR].SetValue(h1, FIXED_V)      #kJ/kmol
            results = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, propList, self.nuSolPhases)
            j[eqnNo][self.hArrayIdx[-1]] = (results.bulkProps[T_IDX] - t1) / (self.scaleFactorT*shift)
            
            eqnNo += 1
            
        unk = self._unknowns
        #Eqn's for known vars
        for idx in range(len(x)):
            if isFix[idx]:
                j[eqnNo][idx] = 1.0 / unk._unkScaleFacts[idx]
                eqnNo += 1

        return eqnNo     

    def CalculateDeltaT(self, t0, t1, tAmb):
        """Try getting a log dt if not just pass the arithmetic mean"""
        try:
            if (t0-tAmb) * (t1-tAmb) < 0.0:
                if t0 > tAmb:
                    t1 = tAmb + 0.000000001
                else:
                    t1 = tAmb - 0.000000001
            dt = (t0 - t1) / log( (t0-tAmb) / (t1-tAmb) )
        except:
            dt = (t0 + t1) / 2.0 - tAmb
            
        return dt
    
    def AdjustOldCase(self, version):
        super(PipeSegment, self).AdjustOldCase(version)
        if version[0] < 21:            
            if not self.GetPort(OUT_PORT + 'Q'):
                self.enePort = self.CreatePort(OUT|ENE, OUT_PORT + 'Q')
                self.enePort.SetLocked(True)        
            if not self.GetPort(U_PORT):
                self.uPort = self.CreatePort(SIG, U_PORT)
                self.uPort.SetSignalType(U_VAR)
                self.uPort.SetLocked(True)
            if not self.GetPort(EXT_T_PORT):
                self.ambTPort = self.CreatePort(SIG, EXT_T_PORT)
                self.ambTPort.SetSignalType(T_VAR)
                self.ambTPort.SetLocked(True)
                self.ambTPort.SetValue(298.15, FIXED_V)
                
            self._nuUnk = 7
            self._nuEqns = 3
            
            
        if version[0] < 41:
            if not hasattr(self, 'solveMethods'):
                self.solveMethods = {}
                solveMeth = SolveMethod_OutP()
                self.AddObject(solveMeth, CALC_OUTP_MODE)
            if not hasattr(self, 'dpModel'):
                self.dpModel = PressureDropModel()
                self.AddObject(self.dpModel, DP_MODEL)
                
            #Change of nomenclature in member variables
            #Just trying to be consistent
            if hasattr(self, '_nuSections'):
                self.nuSections = self._nuSections
                del self._nuSections
            if hasattr(self, 'portIn'):
                self.inPort = self.portIn
                del self.portIn
            if hasattr(self, 'portOut'):
                self.outPort = self.portOut
                del self.portOut
            if hasattr(self, '_P'):
                self.pArray = self._P
                del self._P
            if hasattr(self, '_PIdx'):
                self.pArrayIdx = self._PIdx
                del self._PIdx
            if hasattr(self, '_H'):
                self.hArray = self._H
                del self._H
            if hasattr(self, '_HIdx'):
                self.hArrayIdx = self._HIdx
                del self._HIdx
            if hasattr(self, '_Q'):
                self.qArray = self._Q
                del self._Q
            if hasattr(self, '_QIdx'):
                self.qArrayIdx = self._QIdx
                del self._QIdx    
            if hasattr(self, '_U'):
                self.uArray = self._U
                del self._U
            if hasattr(self, '_UIdx'):
                self.uArrayIdx = self._UIdx
                del self._UIdx 
            if hasattr(self, 'z0Port'):
                self.y0Port = self.z0Port
                del self.z0Port
            if hasattr(self, 'z1Port'):
                self.y1Port = self.z1Port
                del self.z1Port
                
            #This is not needed anymore
            if hasattr(self, '_lowBoundLst'):
                del self._lowBoundLst
            if hasattr(self, '_unkName'):
                del self._unkName
            if hasattr(self, '_canBeSpec'):
                del self._canBeSpec
            if hasattr(self, '_nuEqns'):
                del self._nuEqns
            if hasattr(self, '_nuUnk'):
                del self._nuUnk
            if hasattr(self, '_MW'):
                del self._MW    
            if hasattr(self, '_ambT'):
                del self._ambT           
            if hasattr(self, '_len'):
                del self._len        
            if hasattr(self, '_diam'):
                del self._diam           
            if hasattr(self, '_rough'):
                del self._rough
            if hasattr(self, '_relRough'):
                del self._relRough
            if hasattr(self, '_area'):
                del self._area
            if hasattr(self, '_surfArea'):
                del self._surfArea    
                
                
            #Keep this here for now
            self.diamArray = None
            self.zArray = None  #vertical position (not length)
            self.xArray = None  #horizontal position (not length)
            self.lenArray = None  #Length per section
            
            if not hasattr(self, 'flashResultsArray'):
                self.flashResultsArray = None
                
        if version[0] < 72:
            self.balance = Balance.Balance(Balance.MOLE_BALANCE | Balance.ENERGY_BALANCE)
            self.balance.AddInput(self.inPort)
            self.balance.AddOutput((self.outPort, self.enePort))
        
            val = self.GetParameterValue(IGNOREKINANDPOT_PAR)
            if val == None:
                self.parameters[IGNOREKINANDPOT_PAR] = 0
                
        if version[0] < 75:
            if hasattr(self, 'diamPort'):
                self.iDiamPort = self.diamPort
                del self.diamPort
            iDiamPort = self.GetPort(DIAM_PORT)
            if iDiamPort != None:
                self.RenamePort(DIAM_PORT, ID_PORT)
                
            oDiamPort = self.GetPort(OD_PORT)
            if oDiamPort == None:
                self.oDiamPort = self.CreatePort(SIG, OD_PORT)
                self.oDiamPort.SetSignalType(LENGTH_VAR)
                self.oDiamPort.SetLocked(True)
                
        if version[0] < 77:
            htModel = self.GetParameterValue(ENERGYMODEL_PAR)
            if htModel == None or not htModel in (EQUALU_MODEL, LINEARQ_MODEL, LINEART_MODEL):
                self.parameters[ENERGYMODEL_PAR] = LINEARQ_MODEL
            self.parameters[AV_ENERGYMODELS_PAR] = "%s %s %s" %(LINEARQ_MODEL, LINEART_MODEL, EQUALU_MODEL)
            
            
    def CleanUp(self):
        """Clean up the internal objects"""
        try:
            if self.dpModel:
                self.dpModel.CleanUp()
                self.dpModel = None
            for obj in self.solveMethods.values():
                self.solveMethods = None
                obj.CleanUp()
            for prof in self.liveProfiles.values():
                prof.CleanUp()
                self.liveProfiles = None
            if hasattr(self, 'balance'):
                self.balance.CleanUp()
        except:
            self.InfoMessage('ErrInCleanUp', (self.GetPath(),), MessageHandler.errorMessage)
        
        super(PipeSegment, self).CleanUp()
        
        
        
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(PipeSegment, self)._RemoveFromCloneList(clone, attrNamesToClone)
        dontClone = ["_localMatDict", "_localCmpList", "liveProfiles", "balance", "_thCaseObj",
                     "_fracs", "solveMethods"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
    
    
        
class PipeSectionInfoHolder(object):
    """Groups the basic structural information of a section of a pipe.
    In this case, a pipe segment is made of pipe sections"""
    def __init__(self):
        """Just define the basics"""
        self.len = None
        self.y0 = None
        self.y1 = None
        self.diam = None
        self.relRough = None
        self.surfArea = None
        self.crossArea = None
        self.dpCorr = None
        self.k0 = None
        self.k1 = None
        
    def Clone(self):
        clone = self.__class__()
        for key in self.__dict__:
            clone.__dict__[key] = UnitOperations._SafeClone(self.__dict__[key])
        return clone
        
        
class PipeObject(object):
    def __init__(self):
        
        self.name = None
        self.pipe = None
        
    def __str__(self):
        return "PipeObject"
    
    def Initialize(self, pipe, name):
        """Method that looks like then one in the tower that gets called once the object is added to the parent"""
        self.pipe = pipe
        self.name = name    
    
    def SetName(self, name):
        self.name

    def GetName(self):
        return self.name
        
    def SetParent(self, pipe):
        self.pipe = pipe
        
    def GetParent(self):
        return self.pipe
    
    def GetPath(self):
        return '%s.%s' %(self.pipe.GetPath(), self.name)
    
    def InfoMessage(self, message=None, args=None, msgType=MessageHandler.infoMessage):
        """Support for info messages just to make like easier. Just pass them directly to the parent/pipe"""
        self.pipe.InfoMessage(message, args, msgType)
        
    def CleanUp(self):
        self.pipe = None
    
    
class SolveMethod(PipeObject):
    """Calculation method depending on info known"""
    
    def __init__(self):
        super(SolveMethod, self).__init__()
        
        
        self._unknowns = EquationSolver.Unknowns()
        self._lastConvergedX = None
        self._lastX = None
        self._lastJacobian = None
        self.overSpecIdxVec = []
        
        
    def __str__(self):
        return "PipeObject"    
    
    
    def Solve(self):
        """Solve assuming that all the info is there and that the necessary specs are there. No validation here"""
        pass
        
    def GetNumMethodSettings(self):
        """Get the settings"""
        return self.pipe._numMethodSetings
    
    def LoadUnknowns(self, u):
        """Load the variables"""
        #Just a place holder for now
        pass
    
    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        """Solve the design equations"""
        #Just a place holder for now
        pass
    
    def CalculateDeltaT(self, t0, t1, tAmb):
        """Try getting a log dt if not just pass the arithmetic mean"""
        try:
            if (t0-tAmb) * (t1-tAmb) < 0.0:
                #return 0.0
                if t0 > tAmb:
                    t1 = tAmb + 0.000000001
                else:
                    t1 = tAmb - 0.000000001
            dt = (t0 - t1) / log( (t0-tAmb) / (t1-tAmb) )
        except:
            dt = (t0 + t1) / 2.0 - tAmb
            
        return dt
    
    
class SolveMethod_OutP(SolveMethod):
    def __init__(self):
        super(SolveMethod_OutP, self).__init__()
        self.knownResults = None
        self.newResults = None
        self.massFlow = None
        
    
    def Solve(self):
        """Solve for fully known dimensions, inlet and unknown outlet"""
        
        #Load some vars
        pipe = self.pipe
        nuSections = pipe.nuSections
        inPort = pipe.inPort
        dpModel = pipe.dpModel
        path = pipe.GetPath()
        mw = inPort.GetPropValue(MOLEWT_VAR)
        rough = pipe.roughPort.GetValue()
        diam = pipe.iDiamPort.GetValue()
        tAmb = pipe.ambTPort.GetValue()
        uArray = pipe.uArray  #Thse arrays should be dimensioned already
        qArray = pipe.qArray
        hArray = pipe.hArray
        pArray = pipe.pArray
        SolveNonLinearEquations = EquationSolver.SolveNonLinearEquations
        storedProfiles = pipe.storedProfiles
        
        
        #Dimension arrays
        flashResultsArray = pipe.flashResultsArray
        
        #Get some properties
        s = self.GetNumMethodSettings()
        unk = self._unknowns
        p0 = inPort.GetPropValue(P_VAR)                    #kPa
        h0 = inPort.GetPropValue(H_VAR)                    #kJ/kmol
        self.massFlow = inPort.GetPropValue(MASSFLOW_VAR)  #kg/h
        self.massFlow = self.massFlow / 3600.0             #kg/s
        #self.mw = mw
        #self.rough = rough
        #self.ambT = ambT
        
        #Make sure that there are existing flah result in the inlet port and 
        #tha all the required properties are there
        knownResults = None
        
        
        #Don't fight it and just do the flash even though the inlet port is already flashed
        if not knownResults:
            thAdmin, prov, case = pipe._thCaseObj.thermoAdmin, pipe._thCaseObj.provider, pipe._thCaseObj.case
            propList = dpModel.GetRequiredProperties()
            nuLiqPhases = 1
            matDict = pipe._localMatDict
            cmps = pipe._localCmpList
            matDict[P_VAR].SetValue(p0, FIXED_V)
            matDict[H_VAR].SetValue(h0, FIXED_V)
            knownResults = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, propList)
        self.knownResults = knownResults
        self.newResults = None
        
        
        #Create a convenient object for holding info of the section being solved
        section = PipeSectionInfoHolder()
        self.section = section
        
        #These things will not change through solution
        section.diam = diam
        section.crossArea = PI * (diam / 2.0)**2
        section.relRough = rough/diam
        section.massFlow = self.massFlow
        section.mw = mw
        section.rough = rough
        section.tAmb = tAmb
        section.k0 = pipe._kVec[0]
        section.dpCorr = pipe.dpCorr
        
        #Solve for all the sections
        for sec in range(nuSections):
            
            #Put the known flash results in place
            flashResultsArray[sec] = self.knownResults
            
            #The whole z profile should be there
            #Load it locally for the section being solved
            section.y0 = pipe._yVec[sec]
            section.y1 = pipe._yVec[sec+1]
            section.len = pipe._lenVec[sec]
            section.k1 = pipe._kVec[sec+1]
            section.surfArea = surfArea = PI * diam * section.len
            
            #This values get loaded into the section object
            section.Re = None
            section.f = None
            section.holdup = None
            section.flowRegime = None
            
            #Load unknowns
            unk.__init__()
            if not self.LoadUnknowns(unk, self.knownResults):
                #Raise error because this should not happen in here as everything was validated
                raise SimError ('CouldNotInitialize', (pipe.GetPath(),))
            
            #Previous results
            lConvX = None
            lX = None
            lJac = None
            
            #Solve simoultaneous
            self.InfoMessage('SolvingSection', (sec+1, path))
            x, rhs, converged, jacobian = SolveNonLinearEquations(self, unk, s, lConvX, lX, lJac)
            
            if not converged:
                return False
            
            #Load some arrays
            uArray[sec] = x[self.uIdx]          #W/m2K
            qArray[sec] = x[self.qIdx]          #W
            
            #Loading the following two arrays should not be necessary
            pArray[sec] = self.knownResults.bulkProps[P_IDX] * 1000.0              #Pa
            hArray[sec] = self.knownResults.bulkProps[H_IDX] * 1000.0 / mw         #J/kg
            
            #The section should now have loaded these values
            if section.Re != None:
                storedProfiles['Re'][sec] = section.Re
            if section.f != None:
                storedProfiles['f'][sec] = section.f
            if section.holdup != None:
                storedProfiles['Holdup'][sec] = section.holdup
            if section.flowRegime != None:
                storedProfiles['FlowRegime'][sec] = section.flowRegime
                
                
            #Soultion is the init of next section
            self.knownResults = self.newResults
            section.k0 = 0.0 #This is only used for the first iter
       
            
        #Fill in in the last flash results
        flashResultsArray[nuSections] = self.knownResults
        pArray[nuSections] = self.knownResults.bulkProps[P_IDX] * 1000.0              #Pa
        hArray[nuSections] = self.knownResults.bulkProps[H_IDX] * 1000.0 / mw         #J/kg
            
            
        #Everything should be in arrays from the pipe
        return True
            
            
    def LoadUnknowns(self, unk, *args):
        """load only p1, h1, u and q. The order of *args depends on implementation"""
        
        pipe = self.pipe
        nuSections = pipe.nuSections
        mw = self.section.mw
        isSpec= False
        
        #args has to come in this exact order
        results = args[0]
        p0 = results.bulkProps[P_IDX] * 1000.0              #Pa
        h0 = results.bulkProps[H_IDX] * 1000.0 / mw         #J/kg
        
        
        #Estimate outlet pressure
        p1 = p0 * 0.95
        self.scaleFactorP = min(p0, p1)
        unkVar = EquationSolver.SolverVariable('P1', p1, p1, isSpec, self.scaleFactorP, 0.01, 1E30)
        self.p1Idx = unk.AddUnknown(unkVar)
        
            
        #Do enthalpy
        h1 = h0 + h0*0.02
        self.scaleFactorH = PropTypes[H_VAR].scaleFactor * 100.0 #Assume a scale factor in J/kg
        unkVar = EquationSolver.SolverVariable('H1', h1, h1, isSpec, self.scaleFactorH, -1E30, 1E30)
        self.h1Idx = unk.AddUnknown(unkVar)            
            
        
        #Energy
        qTotVal = pipe.enePort.GetValue()
        uVal = pipe.uPort.GetValue()
        isSpecQ = qTotVal != None
        isSpecU = uVal != None
        
        #Can not spec Q and U at the same time
        isSpecU = where(isSpecQ, False, isSpecU)
        
        if isSpecQ: q = -1.0 * (qTotVal/float(nuSections) ) #Change the sign as this is an out energy port
        else: q = 0.0
        if isSpecU: u = uVal
        else: u = 0.0
        
        u *= (100.0**2)      #W/cm2K -> W/m2K
        self.scaleFactorQ = PropTypes[ENERGY_VAR].scaleFactor 
        self.scaleFactorU = 10.0
            
        unkVar = EquationSolver.SolverVariable('Q', q, q, isSpecQ, self.scaleFactorQ, -1E30, 1E30)
        self.qIdx = unk.AddUnknown(unkVar)
               
        unkVar = EquationSolver.SolverVariable('U', u, u, isSpecU, self.scaleFactorU, -1E30, 1E30)
        self.uIdx = unk.AddUnknown(unkVar)
        
        
        #No u models supported for now
        if not isSpecU and not isSpecQ:
            return False
        
        
        return True        #Check if it has enough specs
    
    
    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        
        #Load some vars
        pipe = self.pipe
        dpModel = pipe.dpModel
        #htModel = pipe.htModel
        nuSections = pipe.nuSections
        fracs = pipe._fracs
        knownResults = self.knownResults #Flash results
        knownProps = knownResults.bulkProps
        section = self.section
        ignoreKinAndPot = pipe.ignoreKinAndPot
        
        #Structure
        w = section.massFlow                  #kg/s
        y0 = section.y0                       #m
        y1 = section.y1                       #m
        crossArea = section.crossArea         #m2
        surfArea = section.surfArea           #m2
        mw = section.mw
        tAmb = section.tAmb 
        
        
        #Info for flashes
        thAdmin, prov, case = pipe._thCaseObj.thermoAdmin, pipe._thCaseObj.provider, pipe._thCaseObj.case
        propList = dpModel.GetRequiredProperties()
        nuLiqPhases = 1
        matDict = pipe._localMatDict
        cmps = pipe._localCmpList
        
        
        #Break down x into variables
        p1 = x[self.p1Idx]                 #Pa
        h1 = x[self.h1Idx]                 #J/kg
        q = x[self.qIdx]                   #W = J/s
        u = x[self.uIdx]                   #W/(m2 K) = J/(s m2 K)
        
        
        #Flash
        matDict[P_VAR].SetValue(p1/1000.0, FIXED_V)    #Pass P in kPa
        matDict[H_VAR].SetValue(h1*mw/1000.0, FIXED_V) #Pass H in kJ/kmol
        newResults = thAdmin.Flash(prov, case, cmps, matDict, nuLiqPhases, propList)
        self.newResults = newResults
        
        #Break down knownProps into variables
        p0 = knownProps[P_IDX] * 1000.0     #Pa
        h0 = knownProps[H_IDX] * 1000.0/mw  #J/kg
        t0 = knownProps[T_IDX]              #K
        den0 = knownProps[MASSDEN_IDX]      #kg/m3
        v0 = w / (den0 * crossArea)         #m/s
        
        #Get some variables obtained in newResults
        newProps = newResults.bulkProps
        t1 = newProps[T_IDX]                #K
        den1 = newProps[MASSDEN_IDX]        #kg/m3
        v1 = w / (den1 * crossArea)         #m/s
        
        #Finally !!
        #Solve the equations.
        #Let the loaded models decide what to do with the flash results
        
        #Mechanical energy (Bernoulli)
        #(P0-P1) - DPFromModel = 0
        
        dp = dpModel.CalcPressureDrop(knownResults, newResults, section)
        rhs[eqnNo] = -(p1-p0) - dp
        rhs[eqnNo] /= self.scaleFactorP
        eqnNo += 1
        
        
        #Energy balance
        #'(U + PV + kinetic + potential) - (U + PV + kinetic + potential)
        #(J/kg + m2/s2 + (m/s2)m) kg/s -> (J/s + kgm2/s3 + kgm2/s3) -> J/s + Nm/s + Nm/s -> J/s
        if ignoreKinAndPot:
            qIn = (h0) * w    
            qOut = (h1) * w
        else:
            qIn = (h0 + v0**2/2.0 + GRAVITY*y0 ) * w    
            qOut = (h1 + v1**2/2.0 + GRAVITY*y1 ) * w
        rhs[eqnNo] = (qOut - qIn - q) / self.scaleFactorQ
        eqnNo += 1
        
        #'(h1 - p1/rho1)*w - (h2 - p2/rho2)*w - Q = 0
        #rhs[eqnNo] = ((h0 - p0/den0)*w - (h1 - p1/den1)*w - q) / self.scaleFactorQ
        #eqnNo += 1
        
        
        #Heat trhansfer equation
        #Q is negative when it leaves the system
        #Q + UADT = 0
        dt = self.CalculateDeltaT(t0, t1, tAmb)
        adt = surfArea*(dt)
        rhs[eqnNo] = (q + u*adt) / self.scaleFactorQ
        eqnNo += 1           
        
        
        ##TO BE IMPLEMENTED #######################
        #Heat transfer coefficient model
        #U - UModel = 0
        #rhs[eqnNo] = u - htModel.CalcU(knownResults, newResults, y0, y1)
        #rhs[eqnNo] /= self.scaleFactorU
        #eqnNo += 1
        ###########################################
        
        
        #Eqn's for known vars
        idx = self.qIdx
        if isFix[idx]:
            rhs[eqnNo] = (x[idx] - initx[idx]) / self.scaleFactorQ
            eqnNo += 1
        
        idx = self.uIdx
        if isFix[idx]:
            rhs[eqnNo] = (x[idx] - initx[idx]) / self.scaleFactorU
            eqnNo += 1
            
        return eqnNo

    
            
class PressureDropModel(PipeObject):
    
    def __init__(self):
        super(PressureDropModel, self).__init__()
        
        #Validate the order of the properties
        reqProps = self.GetRequiredProperties()
        if reqProps[0] != P_VAR or reqProps[1] != H_VAR or \
           reqProps[2] != T_VAR or reqProps[3] != MASSDEN_VAR :
            raise SimError ('WrongOrderOfProps', (str([P_VAR, H_VAR, T_VAR, MASSDEN_VAR]), str(reqProps)))
                            
        #This is not a required property for a pipe segment hence its index is not loaded
        #automatically in a constant
        self.VISC_IDX = 4
        self.MW_IDX = 5
                            
                            
    def __str__(self):
        return "Pressure Drop model for pipe segment"
    
        
    def GetRequiredProperties(self):
        """Properties that the model requires for every flash calculation. P, H, T and MassDensity must be there in that order"""
        
        return [P_VAR, H_VAR, T_VAR, MASSDEN_VAR, 
                VISCOSITY_VAR, MOLEWT_VAR, SURFACETENSION_VAR]
        
    def GetAvailableCorrelations(self):
        return ['OnePhase', 'TwoPhase', 'Laminar', 'Blasius',
                'Colebrook', 'Churchill', 'LockMart']
    
    def CalcPressureDrop(self, results0, results1, section):
        """Return a pressure drop for the given conditions
        
        results0 = Flash results inlet
        results1 = Flash results outlet
        section = Object with structural info of section being solved
                   any new attribute can be added to this object at any time if desired
                   
        """
        
        #Get some common properties
        w = section.massFlow                      #kg/s
        y0 = section.y0                           #m
        y1 = section.y1                           #m
        den0 = results0.bulkProps[MASSDEN_IDX]    #kg/m3
        den1 = results1.bulkProps[MASSDEN_IDX]    #kg/m3
        crossArea = section.crossArea             #m2
        v0 = w / (den0 * crossArea)               #m/s
        v1 = w / (den1 * crossArea)               #m/s
        
        
        #Calculate each loss
        dpPotEne = self.CalcDPPotentialEne(results0, results1, section, den0, den1, y0, y1)
        dpKinEne = self.CalcDPKineticEne(results0, results1, section, den0, den1, v0, v1)
        dpFric = self.CalcDPFriction(results0, results1, section, den0, den1, v0, v1, y0, y1)
        
        #Return the sum
        return dpPotEne + dpKinEne + dpFric
        
        
    def CalcDPPotentialEne(self, results0, results1, section, den0, den1, y0, y1):
        """Pressure drop for potential energy
        The parameters passed in are the most common ones to use. If something else is needed, it 
        can be obtained from the other three parameters"""
        
        #Just use the common formula for now for all flows
        #g*z*rho
        denAvg = (den0 + den1) / 2.0
        val = GRAVITY * denAvg * (y1 - y0)   #(m/s2)(m)(kg/m3) -> kg/(s2m) -> Pa
        return val
        
    
    def CalcDPKineticEne(self, results0, results1, section, den0, den1, v0, v1):
        """Pressure drop for kinetic energy"""
        
        #Just use the common formula for now for all flows

        denAvg = (den0 + den1) / 2.0
        val = denAvg * 0.5 * (v1**2 - v0**2)        #(kg/m3)(m2/s2) -> kg/(s2m) -> Pa
        
        try:
            if self.pipe.GetParameterValue('UsePaige'):
                vAvg = (v1 + v0) / 2.0
                G = vAvg * denAvg
                val = denAvg*.5*(v1**2-v0**2)
                val = G**2 * log(den0/den1) / denAvg
        except:
            pass
        
        return val
    
    
    def CalcDPFriction(self, results0, results1, section, den0, den1, v0, v1, y0, y1):
        """Pressure drop due to friction"""
        
        vapFrac = results0.phaseFractions[0]
        visc0 = results0.bulkProps[self.VISC_IDX]     #Pa-s
        visc1 = results1.bulkProps[self.VISC_IDX]     #Pa-s
        len = section.len                             #m
        diam = section.diam                           #m
        w = section.massFlow                          #kg/s
        k0 = section.k0
        k1 = section.k1
        corr = section.dpCorr
        
        #Here we need a reasonable algorithm to pick the most appropriate equation
        #for the given conditions. In this case assum that the user picked it
        
        ##Should I really only compare the first letters?
        if corr == 'OnePhase':
            val = self.CalcDPFriction_Colebrook(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)
        elif corr == 'TwoPhase':
            val = self.CalcDPFriction_LockMart(results0, results1, section, w, y0, y1, len, diam)
        elif corr == 'Laminar':
            val = self.CalcDPFriction_Laminar(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)
            #val = self.CalcDPFriction_HagenPoiseuille(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)
        elif corr == 'Blasius':
            val = self.CalcDPFriction_Blasius(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)
        elif corr == 'Colebrook':
            val = self.CalcDPFriction_Colebrook(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)
        elif corr == 'Churchill':
            val = self.CalcDPFriction_Churchill(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)
        elif corr == 'LockhartMartinelli':    
            val = self.CalcDPFriction_LockMart(results0, results1, section, w, y0, y1, len, diam)
        elif corr == 'Weymouth':
            val = self.CalcDPFriction_Weymouth(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)
        elif corr == 'Panhandle':
            val = self.CalcDPFriction_Panhandle(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)
        else:
            val = self.CalcDPFriction_Colebrook(section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1)            
            
        return val
        
        
    def CalcDPFriction_Laminar(self, section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1):
        """Calculate friction loss"""
        
        v = 0.5 * (v0 + v1)
        den = 0.5 * (den0 + den1)
        visc = 0.5 * (visc0 + visc1)
        
        moody = self.CalcMoody_Laminar(section, den, v, visc, diam)
        val = moody * len * v**2 * den / (diam * 2.0)
        
        val += (k0 + k1 )* v**2 * den / 2.0
        section.f = moody
        return val
    
    def CalcMoody_Laminar(self, section, den, v, visc, diam):
        """f = 64/Re
        Valid laminar flow Re < 2100
        """
        Re = den * diam * v / visc
        
        fricIsNeg = False
        if Re < 0.0:
            fricIsNeg = True
            Re = -1.0*Re
            
        moody = 64.0/Re
            
        if fricIsNeg:
            moody = -1.0*moody
        section.Re = Re        
        return moody
    

    def CalcDPFriction_HagenPoiseuille(self, section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1):
        """f = 64/Re
        Valid laminar flow Re < 2100
        """
        v = 0.5 * (v0 + v1)
        den = 0.5 * (den0 + den1)
        visc = 0.5 * (visc0 + visc1)
        
        val = 32.0 * visc * len * v / (diam**2)
        
        val += (k0 + k1 )* v**2 * den / 2.0
        
        return val
    
    
    
    def CalcDPFriction_Blasius(self, section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1):
        """Calculate friction loss"""
        
        v = 0.5 * (v0 + v1)
        den = 0.5 * (den0 + den1)
        visc = 0.5 * (visc0 + visc1)
        
        moody = self.CalcMoody_Blasius(section, den, v, visc, diam)
        val = moody * len * v**2 * den / (diam * 2.0)
        val += (k0 + k1 )* v**2 * den / 2.0
        section.f = moody
        return val 
    
    def CalcMoody_Blasius(self, section, den, v, visc, diam):
        """Blasius equation: f = 0.316/(Re)**.25
        Valid for smooth pipes (rough.D = 0) and Re < 10E5
        """
        Re = den * diam * v / visc
        
        fricIsNeg = False
        if Re < 0.0:
            fricIsNeg = True
            Re = -1.0*Re
            
        moody = 0.316/((Re)**0.25)
            
        if fricIsNeg:
            moody = -1.0*moody
        section.Re = Re        
        return moody
    
    
    
    def CalcDPFriction_Colebrook(self, section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1):
        """Calculate friction loss"""
        
        v = 0.5 * (v0 + v1)
        den = 0.5 * (den0 + den1)
        visc = 0.5 * (visc0 + visc1)
        
        moody = self.CalcMoody_Colebrook(section, den, v, visc, diam)
        val = moody * len * v**2 * den / (diam * 2.0)
        val += (k0 + k1 )* v**2 * den / 2.0
        section.f = moody
        return val
    
    def CalcMoody_Colebrook(self, section, den, v, visc, diam):
        """Colebrook equation: 1/sqrt(f) = -2.0*log(rough/D/3.7 + 2.51/(Re*sqrt(f)))
        Valid for the nonlaminar range of the Moody charts
        """
        Re = den * diam * v / visc
        
        fricIsNeg = False
        if Re < 0.0:
            fricIsNeg = True
            Re = -1.0*Re
            
        #Init with Blasius
        oldMoody = abs(self.CalcMoody_Blasius(section, den, v, visc, diam))
        maxIter = 30
        iter = 0
        tol = 1E-4
        relRough = section.relRough
        while iter <= 40:
            iter += 1
            a = -2.0 * log10(relRough/3.7+ 2.51/(Re * sqrt(oldMoody)))
            moody = (1/a) ** 2
            if abs(moody-oldMoody) <= tol:
                break
            oldMoody = moody
        if fricIsNeg:
            moody = -1.0*moody
        section.Re = Re        
        return moody
            
             
    
    def CalcDPFriction_Churchill(self, section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1):
        """Calculate friction loss"""
        
        v = 0.5 * (v0 + v1)
        den = 0.5 * (den0 + den1)
        visc = 0.5 * (visc0 + visc1)
        
        moody = self.CalcMoody_Churchill(section, den, v, visc, diam)
        val = moody * len * v**2 * den / (diam * 2.0)
        val += (k0 + k1 )* v**2 * den / 2.0
        section.f = moody
        return val
    
    def CalcMoody_Churchill(self, section, den, v, visc, diam):
        
        Re = den * diam * v / visc
        fricIsNeg = False
        if Re < 0.0:
            fricIsNeg = True
            Re = -1.0*Re
        
        #Calc friction Factor using Churchill's formula which is good for both turbulent and laminar flow
        A = (2.457 * math.log(1.0 / ((7.0/Re) ** 0.9 + (0.27 * section.relRough)))) ** 16
        B = (37530.0 / Re) ** 16
        moody = 8.0 * ((8.0 / Re) ** 12 + 1.0 / (A + B) ** 1.5) ** (1.0 / 12.0)
        
        if fricIsNeg:
            moody = -1.0*moody
        section.Re = Re
        return moody
    
    def CalcDPFriction_Weymouth(self, section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1):
        v = 0.5 * (v0 + v1)
        den = 0.5 * (den0 + den1)
        visc = 0.5 * (visc0 + visc1)
        
        moody = self.CalcMoody_Weymouth(section, den, v, visc, diam)
        val = moody * len * v**2 * den / (diam * 2.0)
        val += (k0 + k1 )* v**2 * den / 2.0
        section.f = moody
        return val
    
    def CalcMoody_Weymouth(self, section, den, v, visc, diam):
        return 0.094/(diam/1000.0)**(1.0/3.0)
        
    def CalcDPFriction_Panhandle(self, section, den0, den1, v0, v1, visc0, visc1, len, diam, k0, k1):
        v = 0.5 * (v0 + v1)
        den = 0.5 * (den0 + den1)
        visc = 0.5 * (visc0 + visc1)
                
        moody = self.CalcMoody_Panhandle(section, den, v, visc, diam)
        val = moody * len * v**2 * den / (diam * 2.0)
        val += (k0 + k1 )* v**2 * den / 2.0
        section.f = moody
        return val
    
    def CalcMoody_Panhandle(self, section, den, v, visc, diam):
        volFlow = section.massFlow / den   #m3/s
        mwAir = 32.0*0.21 + 28.0*0.79
        mwGas = section.mw
        spGrav = mwGas/mwAir
        moody = 0.0454 * ((diam/1000.0)/(volFlow*spGrav))**0.1461
        return moody
    
    def CalcDPFriction_LockMart(self, results0, results1, section, w, y0, y1, len, diam):
        """Calculate friction loss"""
        pipe = self.pipe
        crossArea = section.crossArea
        mWBulk = section.mw
        k0 = section.k0
        k1 = section.k1
        
        try:
            vapFrac0 = results0.phaseFractions[0]  #Check
            vapFrac1 = results1.phaseFractions[0]  
            phase0Gas = results0.phaseProps[0]
            phase1Gas = results1.phaseProps[0]
            den0Gas = phase0Gas[MASSDEN_IDX]
            den1Gas = phase1Gas[MASSDEN_IDX]
            visc0Gas = phase0Gas[self.VISC_IDX]
            visc1Gas =  phase1Gas[self.VISC_IDX]
            mW0Gas = phase0Gas[self.MW_IDX]
            mW1Gas = phase1Gas[self.MW_IDX]
            v0Gas = ((w/mWBulk)*vapFrac0)*mW0Gas / (den0Gas * crossArea)
            v1Gas = ((w/mWBulk)*vapFrac1)*mW1Gas / (den1Gas * crossArea)
            ReGas = den0Gas * diam * v0Gas / visc0Gas
            dPFracGas = self.CalcDPFriction_Colebrook(section, den0Gas, den1Gas, v0Gas, v1Gas, visc0Gas, visc1Gas, len, diam, k0, k1)
        except:
            dPFracGas = 0.0
            
        try:
            liqFrac0 = results0.phaseFractions[1]  #Check
            liqFrac1 = results1.phaseFractions[1]  
            phase0Liq = results0.phaseProps[1]
            phase1Liq = results1.phaseProps[1]
            den0Liq = phase0Liq[MASSDEN_IDX]
            den1Liq = phase1Liq[MASSDEN_IDX]
            visc0Liq = phase0Liq[self.VISC_IDX]
            visc1Liq =  phase1Liq[self.VISC_IDX]
            mW0Liq = phase0Liq[self.MW_IDX]
            mW1Liq = phase1Liq[self.MW_IDX]
            v0Liq = ((w/mWBulk)*liqFrac0)*mW0Liq / (den0Liq * crossArea)
            v1Liq = ((w/mWBulk)*liqFrac1)*mW1Liq / (den1Liq * crossArea)
            ReLiq = den0Liq * diam * v0Liq / visc0Liq
            dPFracLiq = self.CalcDPFriction_Colebrook(section, den0Liq, den1Liq, v0Liq, v1Liq, visc0Liq, visc1Liq, len, diam, k0, k1)
        except:
            dPFracLiq = 0.0
            
            
        #Make sure we have something there
        if not dPFracGas: return dPFracLiq
        if not dPFracLiq: return dPFracGas
            
        chi = sqrt(dPFracLiq / dPFracGas)
        
        turbLimit = 3000.0
        
        if ReGas >= turbLimit and ReLiq >= turbLimit:
            n = 4.0
        elif ReGas < turbLimit and ReLiq < turbLimit:
            n = 2.88912
        else:
            n = 3.5
        
        sqrPhi = (1.0 + chi**(2.0/n))**n
        
        holdup = 0.0
        try:
            if chi <= 10.0 :
                alpha = (1.0 + chi**0.8)**(-0.378)
            else:
                alpha = exp(-1.165 + 0.59*log(chi) - 0.1783*(log(chi))**2.0)
            
            holdup = 1 - alpha
            if holdup > 1.0:
                holdup = 1.0
            if holdup < 0.0:
                holdup = 0.0
        except:
            pass
            
        #vHoldup = 1.0 / (alpha/v0Gas + (1.0 - alpha)/v0Liq) # Calculated with velocity "zero"
        val = dPFracGas * sqrPhi
        section.holdup = holdup
        section.f = None
        section.Re = (ReGas + ReLiq) / 2.0
        return val
        
    
    
##Different ways of calculating reynolds depending on properties.
##Diameter and length are equivalent depending on the problem
    
    def Clone(self):
        clone = self.__class__()
        for key in self.__dict__:
            clone.__dict__[key] = UnitOperations._SafeClone(self.__dict__[key])
        return clone
        
        
        
def ChangeNegToDash(val):
    """Helper function for a map call"""
    if val == -1.0:
        return '-'
    return val
def Reynolds_D_Rho_vel_mu(den, diam, vel, visc):
    return den * diam * vel / visc

def Reynolds_D_vel_nu(diam, vel, kinVisc):
    return diam * vel / kinVisc

def Reynolds_D_G_mu(diam, massVel, visc):
    return diam * massVel / visc

def Reynolds_D_w_A_mu(diam, massFlow, crossArea, visc):
    return diam * massFlow / (crossArea * visc)





    
