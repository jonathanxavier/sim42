"""Models a distillation tower

Classes:
Tower -- Class for the Tower. Inherits from UnitOperation

"""

import string, sys, time, re, copy
from sim.unitop import UnitOperations, Properties
from sim.solver import Ports
from sim.solver.Variables import *
from sim.solver.Error import SimError
from sim.solver.Messages import MessageHandler

import numpy, math
N = numpy
from numpy import array, zeros, ones, float, int, take, put, add, clip, sum
from numpy import transpose, dot, outer as outerproduct, dot as matrixmultiply, where, absolute
from numpy.linalg import solve as solve_linear_equations, inv as inverse, det as determinant

NORMAL_STAGE = 0
TOP_STAGE = 1
BOTTOM_STAGE = 2
REFLUX = 'Reflux'
REBOIL = 'Reboil'
VOLFRAC_SPEC = "LiqVolFraction"
MASSFRAC_SPEC = "MassFraction"
WATERFREE = "WaterFree"   #constant for water free profiles

#Pre-defined parameters
TRYTOSOLVE_PAR = 'TryToSolve'
TRYTORESTART_PAR = 'TryToRestart'
MAXINNERERROR_PAR = 'MaxInnerError'
MAXOUTERERROR_PAR = 'MaxOuterError'
MININNERSTEP_PAR = 'MinInnerStep'
MAXOUTERLOOPS_PAR = 'MaxOuterLoops'
MAXINNERLOOPS_PAR = 'MaxInnerLoops'
DAMPINGFACTOR_PAR = 'DampingFactor'
WATERDAMPING_PAR = 'WaterDamping'
INITKPOWER_PAR = 'InitKPower'
EFFICIENCIES_PAR = 'Efficiencies'
TRIGGERSOLVE_PAR = 'TriggerSolve'
FREQ_JAC_MSG_PAR = 'FreqJacobianMsg'
TRYLASTCONVERGED_PAR = 'TryLastConverged'
CONV_REPORT_LEVEL_PAR = 'ConvReportLevel'
USEKMIXMODEL_PAR = 'UseKMixForWaterDraws'

TOWER_LIQ_PHASE = 'L'
TOWER_VAP_PHASE = 'V'
TOWER_WATER_PHASE = 'W'

tiniestValue = 1.e-100
logTiniestValue = math.log(tiniestValue)
logLargestValue = -logTiniestValue
largestValue = math.exp(logLargestValue)

smallestAllowedFlow = 1.e-40
logSmallestAllowedFlow = math.log(smallestAllowedFlow)
largestAllowedFlow = 1.e40
logLargestAllowedFlow = math.log(largestAllowedFlow)

#Init modes
SCRATCH_INIT = 0
RESTART_INIT = 1
LASTCONV_INIT = 2

#Init tower object 
INIT_TOWER_OBJ = "InitTowerAlgorithm"

class Stage(object):
    """Tower equilibrium stage"""
    def __init__(self, tower, stageNo):
        self.tower = tower
        self.number = stageNo
        
        #Sub Cooling Object
        self.subCool = None
        
        # draws and feeds will all have names and be stored in a dictionary
        self.liqDraws = {}
        self.vapDraws = {}
        self.liqClones = {}
        self.vapClones = {}
        self.feeds = {}
        self.qfeeds = {}
        self.estimates = {}
        self.specs = {}
        self.activeSpecs = []       #Gets filled in dynamically when solving
        self.inactiveSpecs = []     #Gets filled in dynamically when solving
        self.liqDrawsActive = []
        self.vapDrawsActive = []
        self.type = NORMAL_STAGE    #The type will be defined in InsertStage
        self.waterDraw = None
        self.userSpecs = 0
        
        #A type could be predifined but the tower is still capable of accepting it or not
        self.tower.InsertStage(self)

    def __str__(self):
        contents = self.GetContents()
        s = 'Stage_%d' % self.number
        for i in contents:
            s += '\n%s: %s' % i
        return s
            
    def CleanUp(self):
        for draw in self.liqDraws:
            self.liqDraws[draw].CleanUp()
        self.liqDraws = {}
            
        for draw in self.vapDraws:
            self.vapDraws[draw].CleanUp()
        self.vapDraws = {}

        for clone in self.liqClones:
            self.liqClones[clone].CleanUp()
        self.liqClones = {}
            
        for clone in self.vapClones:
            self.vapClones[clone].CleanUp()
        self.vapClones = {}

        for feed in self.feeds:
            self.feeds[feed].CleanUp()
        self.feeds = {}
            
        for feed in self.qfeeds:
            self.qfeeds[feed].CleanUp()
        self.qfeeds = {}
            
        for est in self.estimates:
            self.estimates[est].CleanUp()
        self.estimates = {}
        
        for spec in self.specs:
            self.specs[spec].CleanUp()
            
        if self.waterDraw:
            self.waterDraw.CleanUp()
            self.waterDraw = {}
            
        if self.subCool:
            self.subCool.CleanUp()
            
        self.specs = {}
        self.activeSpecs = []  
        self.inactiveSpecs = []
        self.liqDrawsActive = []
        self.vapDrawsActive = []
        self.tower = None
        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        
        if version[0] < 37:
            if not hasattr(self, 'subCool'):
                self.subCool = None
        
        for draw in self.liqDraws:
            self.liqDraws[draw].AdjustOldCase(version)
            
        for draw in self.vapDraws:
            self.vapDraws[draw].AdjustOldCase(version)

        for clone in self.liqClones:
            self.liqClones[clone].AdjustOldCase(version)
            
        for clone in self.vapClones:
            self.vapClones[clone].AdjustOldCase(version)

        for feed in self.feeds:
            self.feeds[feed].AdjustOldCase(version)
            
        for feed in self.qfeeds:
            self.qfeeds[feed].AdjustOldCase(version)
            
        for est in self.estimates:
            self.estimates[est].AdjustOldCase(version)
        
        for spec in self.specs:
            self.specs[spec].AdjustOldCase(version)
            
        if self.waterDraw:
            self.waterDraw.AdjustOldCase(version)

        if version[0] < 3:
            self.userSpecs = 0
            
        if self.subCool:
            self.subCool.AdjustOldCase(version)
            
    def Add(self, numNewStages, recursing=0):
        """adds numNewStages below this stage"""
        type = None
        numNewStages = int(numNewStages)
        if numNewStages < 1:
            return
        newStage = Stage(self.tower, self.number + 1)
        newStage.Add(numNewStages - 1, recursing=1)
        
        if not recursing:
            #Make sure all the stages were added as one section in case it was
            #added below a bottom stage
            if self.type == BOTTOM_STAGE:
                if numNewStages > 2:
                    self.tower.stages[self.number+1].type = TOP_STAGE
                    self.tower.stages[self.number+numNewStages].type = BOTTOM_STAGE
                    for i in range(numNewStages-2):
                        self.tower.stages[self.number+2+i].type = NORMAL_STAGE
        
        #Quick dirty hack to make sure that the last stage added has the correct type
        ##Still needs to correct in case only one stages is added as a side stripper !!
        if numNewStages == 1:
            tower = self.tower
            if newStage.type == NORMAL_STAGE and newStage.number+1 < tower.numStages:
                if tower.stages[newStage.number+1].type == TOP_STAGE:
                    newStage.type = BOTTOM_STAGE
        
            #Make sure this gets called
            self.tower.ForgetAllCalculations()

    def Minus(self, numStages):
        """
        removes numStage from below this stage
        If the stage immediately below this is a TOP_STAGE, then the number must be such that
        the last stage to be removed is the corresponding BOTTOM_STAGE
        """
        stages = self.tower.stages
        numStages = int(numStages)
        firstStage= self.number + 1
        lastStage = self.number + numStages
        if lastStage > self.tower.numStages:
            raise SimError('TowerRemoveLastStage', (numStages, self.number))
        if self.tower.stages[firstStage].type == TOP_STAGE:
            if self.tower.stages[lastStage].type != BOTTOM_STAGE:
                raise SimError('TowerSSRemoveError')
            lastNormal = lastStage - 1
        elif self.tower.stages[firstStage].type == BOTTOM_STAGE:
            raise SimError('TowerSSRemoveError')
        else:
            lastNormal = lastStage
            
        #Check for feeds from pump arounds
        for feed in stages[firstStage].feeds.values():
            pa = feed.pumpFromDraw
            if pa and isinstance(pa, PumpAround):
                #A pump around. Cannot delete unless the whole thing is deleted
                if pa.stage.number < firstStage or pa.stage.number > lastStage:
                    raise SimError('TowerPARemovalError', (firstStage, pa.stage.number))
        #Check for feeds from pump arounds        
        for feed in stages[lastStage].feeds.values():
            pa = feed.pumpFromDraw
            if pa and isinstance(pa, PumpAround):
                #A pump around. Cannot delete unless the whole thing is deleted
                if pa.stage.number < firstStage or pa.stage.number > lastStage:
                    raise SimError('TowerPARemovalError', (lastStage, pa.stage.number))
                
        for i in range(firstStage+1, lastNormal+1):
            if self.tower.stages[i].type != NORMAL_STAGE:
                raise SimError('TowerSSRemoveError')
            
            #Check for feeds from pump arounds
            for feed in stages[i].feeds.values():
                pa = feed.pumpFromDraw
                if pa and isinstance(pa, PumpAround):
                    #A pump around. Cannot delete unless the whole thing is deleted
                    if pa.stage.number < firstStage or pa.stage.number > lastStage:
                        raise SimError('TowerPARemovalError', (i, pa.stage.number))

        self.tower.RemoveStages(firstStage, lastStage)
        
        #Make sure this gets called
        self.tower.ForgetAllCalculations()
        
        
    def AddObject(self, obj, name):
        """adds an object to the appropriate container, based on its type"""

        prevObj = self.GetObject(name)
        if prevObj:
            #self.DeleteObject(prevObject)
            #Don't delete, raise error
            raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))

        self.LinkToObject(obj, name)
        obj.Initialize(self, name)
        
    def LinkToObject(self, obj, name):
        """
        add object to the appropriate dictionary using name
        """
        if isinstance(obj, Feed):
            if self.feeds.get(name, None): 
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            self.feeds[name] = obj
        elif isinstance(obj, InternalLiquidClone):
            # must precede draws as they are derived from them
            if self.liqClones.get(name, None): 
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            self.liqClones[name] = obj
        elif isinstance(obj, InternalVapourClone):
            # must precede draws as they are derived from them
            if self.vapClones.get(name, None): 
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            self.vapClones[name] = obj
        elif isinstance(obj, WaterDraw):
            # must precede draws as they are derived from them
            if self.waterDraw: 
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            self.waterDraw = obj
        elif isinstance(obj, LiquidDraw):
            if self.liqDraws.get(name, None): 
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            self.liqDraws[name] = obj
        elif isinstance(obj, VapourDraw):
            if self.vapDraws.get(name, None): 
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            self.vapDraws[name] = obj
        elif isinstance(obj, EnergyFeed):
            if self.qfeeds.get(name, None): 
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            self.qfeeds[name] = obj
        elif isinstance(obj, Estimate):
            if self.estimates.get(name, None):
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            #This is a tricky one, because the Estimate name can not exist in any of the draws
            #because of conflicts in the port name
            for draw in self.liqDraws.values() + self.vapDraws.values():
                if name in draw.estimates:
                    raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            for clone in self.liqClones.values() + self.vapClones.values():
                if name in clone.estimates:
                    raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
                    
            self.estimates[name] = obj
            return 
        elif isinstance(obj, StageSpecification):
            if self.specs.get(name, None): 
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            #This is a tricky one, because the Estimate name can not exist in any of the draws
            #because of conflicts in the port name
            for draw in self.liqDraws.values() + self.vapDraws.values():
                if name in draw.drawSpecs:
                    raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            for clone in self.liqClones.values() + self.vapClones.values():
                if name in clone.drawSpecs:
                    raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            self.specs[name] = obj
            
        elif isinstance(obj, DegSubCooling):
            if self.number != 0:
                raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
            else:
                self.subCool = obj
        else:
            raise SimError('CantAddToStage',(name, self.number, self.tower.GetPath()))
        
        #The following lines are not done by estimates because there is a "return" right there
        self.tower.converged = 0
        self.tower.ForgetAllCalculations()

    def DeleteObject(self, obj):
        try:
            locked = obj.locked
        except AttributeError:
            locked = False
            
        if locked:
            raise SimError('CannotRemoveLockedObject', obj.GetPath())
        else:
            self.UnlinkObject(obj)
            obj.CleanUp()

    def UnlinkObject(self, obj):
        """remove obj from the appropriate list"""
        if isinstance(obj, Feed):
            name = obj.name
            del self.feeds[name]
        elif isinstance(obj, InternalLiquidClone):
            # must precede draws as they are derived from them
            name = obj.name
            del self.liqClones[name]
        elif isinstance(obj, InternalVapourClone):
            # must precede draws as they are derived from them
            name = obj.name
            del self.vapClones[name]
        elif isinstance(obj, WaterDraw):
            self.waterDraw = None
        elif isinstance(obj, LiquidDraw):
            name = obj.name
            del self.liqDraws[name]
        elif isinstance(obj, VapourDraw):
            name = obj.name
            del self.vapDraws[name]
        elif isinstance(obj, EnergyFeed):
            name = obj.name
            del self.qfeeds[name]
        elif isinstance(obj, Estimate):
            name = obj.name
            del self.estimates[name]
            return
        elif isinstance(obj, StageSpecification):
            name = obj.name
            del self.specs[name]
        elif isinstance(obj, DegSubCooling):
            if not (obj is self.subCool):
                raise SimError('CantDeleteFromStage', (obj.name, self.number, self.tower.GetPath()))
            self.subCool = None
        else:
            raise SimError('CantDeleteFromStage', (obj.name, self.number, self.tower.GetPath()))
        self.tower.converged = 0
        
    def ChangeObjectName(self, fromName, toName):
        
        if fromName in self.feeds.keys():
            self.feeds[toName] = self.feeds[fromName]
            self.feeds[toName].name = toName
            del self.feeds[fromName]
            
        elif fromName in self.liqClones.keys():
            self.liqClones[toName] = self.liqClones[fromName]
            self.liqClones[toName].name = toName
            del self.liqClones[fromName]
            
        elif fromName in self.vapClones.keys():
            self.vapClones[toName] = self.vapClones[fromName]
            self.vapClones[toName].name = toName
            del self.vapClones[fromName]
            
        elif self.waterDraw and fromName == self.waterDraw.name:
            self.waterDraw.name = toName

        elif fromName in self.liqDraws.keys():
            self.liqDraws[toName] = self.liqDraws[fromName]
            self.liqDraws[toName].name = toName
            del self.liqDraws[fromName]
            
        elif fromName in self.vapDraws.keys():
            self.vapDraws[toName] = self.vapDraws[fromName]
            self.vapDraws[toName].name = toName
            del self.vapDraws[fromName]            

        elif fromName in self.qfeeds.keys():
            self.qfeeds[toName] = self.qfeeds[fromName]
            self.qfeeds[toName].name = toName
            del self.qfeeds[fromName]

        elif fromName in self.estimates.keys():
            self.estimates[toName] = self.estimates[fromName]
            self.estimates[toName].name = toName
            del self.estimates[fromName]
            
        elif fromName in self.specs.keys():
            self.specs[toName] = self.specs[fromName]
            self.specs[toName].name = toName
            del self.specs[fromName]
            
                
    def ChangeNumber(self, toNumber):
        """
        increase stage number by 1
        """
        oldNumber = self.number
        self.number = toNumber
        for o in self.liqDraws.values(): o.ChangeStageNumber(self.tower, oldNumber, self.number)
        for o in self.vapDraws.values(): o.ChangeStageNumber(self.tower, oldNumber, self.number)
        for o in self.liqClones.values(): o.ChangeStageNumber(self.tower, oldNumber, self.number)
        for o in self.vapClones.values(): o.ChangeStageNumber(self.tower, oldNumber, self.number)
        for o in self.feeds.values(): o.ChangeStageNumber(self.tower, oldNumber, self.number)
        for o in self.qfeeds.values(): o.ChangeStageNumber(self.tower, oldNumber, self.number)
        for o in self.estimates.values(): o.ChangeStageNumber(self.tower, oldNumber, self.number)
        for o in self.specs.values(): o.ChangeStageNumber(self.tower, oldNumber, self.number)
        if self.waterDraw:
            self.waterDraw.ChangeStageNumber(self.tower, oldNumber, self.number)

    def GetPath(self):
        """return object path to this stage"""        
        return '%s.Stage_%d' % (self.tower.GetPath(), self.number)
    
    def GetParent(self):
        """return tower as parent in hierarchy"""
        return self.tower
    
    def GetObject(self, name):
        """returns contained object based on name"""
        if self.feeds.has_key(name): return self.feeds[name]
        if self.qfeeds.has_key(name): return self.qfeeds[name]
        if self.liqDraws.has_key(name): return self.liqDraws[name]
        if self.vapDraws.has_key(name): return self.vapDraws[name]
        if self.liqClones.has_key(name): return self.liqClones[name]
        if self.vapClones.has_key(name): return self.vapClones[name]
        if self.estimates.has_key(name): return self.estimates[name]
        if self.specs.has_key(name): return self.specs[name]
        if self.waterDraw and self.waterDraw.name == name: return self.waterDraw
        if self.subCool and self.subCool.name == name:
            return self.subCool
        
    def GetContents(self):
        """return list of (description, obj) tuples of contained objects"""
        result = []
        for key in self.feeds:
            result.append((key, self.feeds[key]))

        for key in self.qfeeds:
            result.append((key, self.qfeeds[key]))
        for key in self.liqDraws:
            result.append((key, self.liqDraws[key]))

        for key in self.vapDraws:
            result.append((key, self.vapDraws[key]))

        for key in self.liqClones:
            result.append((key, self.liqClones[key]))

        for key in self.vapClones:
            result.append((key, self.vapClones[key]))

        for key in self.specs:
            result.append((key, self.specs[key]))
        for key in self.estimates.keys():
            result.append((key, self.estimates[key]))
        if self.subCool:
            result.append((self.subCool.name, self.subCool))
        return result

    def Reset(self, initMode=SCRATCH_INIT):
        """reset variables from previous calculations"""
        
        for feed in self.feeds.values() + self.qfeeds.values():
            feed.Reset()
        
        for draw in self.liqDraws.values() + self.vapDraws.values():
            draw.Reset()
            
        for clone in self.liqClones.values() + self.vapClones.values():
            clone.Reset()

        for spec in self.specs.values():
            spec.Reset()
            
        if self.waterDraw:
            self.waterDraw.Reset(initMode)
        
        #This one has to be last
        if self.subCool:
            self.subCool.Reset()
            
            
        #Load active draws as sorted lists
        self.liqDrawsActive = []
        names = self.liqDraws.keys()
        names.sort()
        for name in names:
            draw = self.liqDraws[name]
            if (not draw.zeroFlow) or (isinstance(draw, PumpAround)) or (self.number != self.tower.numStages-1 and self.type == BOTTOM_STAGE):
                self.liqDrawsActive.append(draw)
            else:
                if len(draw.portSpecs) > 1 or draw.drawActiveSpecs:
                    raise SimError ('CantUseSpecInZeroFlow', (draw.GetPath(),))
                else:
                    draw.portSpecs = []
            
        self.vapDrawsActive = []
        names = self.vapDraws.keys()
        names.sort()
        for name in names:
            draw = self.vapDraws[name]
            if (not draw.zeroFlow) or (isinstance(draw, PumpAround)) or (self.number != 0 and self.type == TOP_STAGE):
                self.vapDrawsActive.append(draw)
            else:
                if len(draw.portSpecs) > 1 or draw.drawActiveSpecs:
                    raise SimError ('CantUseSpecInZeroFlow', (draw.GetPath(),))
                else:
                    draw.portSpecs = []
                    
        #Has to be 0 or 1 as it will be used as an offset
        self.totCond = 0
        if self.type == TOP_STAGE and not self.vapDrawsActive:
            self.totCond = 1
            
        #Has to be 0 or 1 as it will be used as an offset
        self.totReb = 0
        if self.type == BOTTOM_STAGE and not self.liqDrawsActive:
            self.totReb = 1
                
        self.calculatedQ = 0.0
        
        
    def NumberInner(self, cntActiveOnly=0):
        """return the number of inner loop equations required"""
        if cntActiveOnly:
            #Actual equations used while calculating
            nEqns = len(self.liqDrawsActive) + len(self.vapDrawsActive)
            
            # reset the basis flag on all draws
            for draw in self.liqDraws.values() + self.vapDraws.values():
                draw.isBasis = 0            
                
            if self.type == TOP_STAGE:
                if len(self.vapDrawsActive):
                    # use an arbitrary draw as the basis for stage flow ratios
                    self.vapDrawsActive[0].isBasis = 1
            elif self.type == BOTTOM_STAGE:
                if len(self.liqDrawsActive):
                    # use an arbitrary draw as the basis for stage flow ratios
                    self.liqDrawsActive[0].isBasis = 1
            else:
                # either normal stage or no appropriate draws
                nEqns += 1            
            
        else:
            #Desing equation that matches configuration
            nEqns = len(self.liqDraws) + len(self.vapDraws)
        
            # reset the basis flag on all draws
            for draw in self.liqDraws.values() + self.vapDraws.values():
                draw.isBasis = 0
                
            if self.type == TOP_STAGE and len(self.vapDraws):
                # use an arbitrary draw as the basis for stage flow ratios
                self.vapDraws.values()[0].isBasis = 1
            elif self.type == BOTTOM_STAGE and len(self.liqDraws):
                # use an arbitrary draw as the basis for stage flow ratios
                self.liqDraws.values()[0].isBasis = 1
            else:
                # either normal stage or no appropriate draws
                nEqns += 1
            
        return nEqns

    def NumberSpecs(self):
        """
        return the number of specs associated with this stage
        if there is an unknown EnergyFeed, a spec is subtracted
        """
        
        #numSpecs = len(self.specs)
        activeSpecs = self.activeSpecs = []
        inactiveSpecs = self.inactiveSpecs = []
        for spec in self.specs.values():
            if spec.port.GetValue() != None:
                if self.subCool and self.subCool.isCalculated and isinstance(spec, StageSpecification) and spec.type == T_VAR:
                    ##If it is subCooled and the subCool object has a calculated value
                    ##then it means that the sat T and the T in the liq are both known
                    ##hence, this T should not be a counted as a spec (this should be the liq)
                    pass
                else:
                    activeSpecs.append(spec)
            else:
                inactiveSpecs.append(spec)

        numSpecs = len(activeSpecs)
        for draw in self.liqDraws.values() + self.vapDraws.values():
            numSpecs += draw.NumberSpecs()
            
        for clone in self.liqClones.values() + self.vapClones.values():
            numSpecs += clone.NumberSpecs()

        # save the number of actual specs given by user
        if self.tower.converged == 0:
            self.userSpecs = numSpecs
            for qfeed in self.qfeeds.values():
                if qfeed.port.GetValue() != None:
                    self.userSpecs += 1

        for qfeed in self.qfeeds.values():
            if qfeed.port.GetValue() == None:
                numSpecs -= 1
                break
        
        if self.type == TOP_STAGE and len(self.vapDraws) == 0:
            # automatically add a zero flow spec if no vapour draw on top
            numSpecs += 1
        if self.type == BOTTOM_STAGE and len(self.liqDraws) == 0:
            # automatically add a zero flow spec if no liquid draw on bottom
            numSpecs += 1
            
        return numSpecs

    def NumberOfUserSpecs(self):
        """
        return number of user supplied specs on this stage
        """
        return self.userSpecs
    
    def NumberOfSpecsRequired(self):
        """
        the number of user specs this stage requires
        """
        nReq = len(self.liqDraws) + len(self.vapDraws) + len(self.qfeeds)
        if self.type == TOP_STAGE or self.type == BOTTOM_STAGE:
            nReq -= 1
        return nReq
    
    def TotalFeed(self, f):
        """
        return add the total component feed moles for this stage
        to array f, which must be sized correctly
        """
        totVap = 0.0
        totLiq = 0.0
        for feed in self.feeds.values():
            f += feed.MoleArray()            
            totVap += feed.TotalVapourFlow()
            totLiq += feed.TotalLiquidFlow()
        return totVap, totLiq

    def TotalQFlow(self):
        """
        return add the total feed heat flow to this stage
        """
        q = 0.
        for feed in self.feeds.values():
            q += feed.TotalQFlow()
            
        for feed in self.qfeeds.values():
            feedQ = feed.TotalQFlow()
            if feedQ != None:
                q += feedQ
        return q

    def GetPressure(self, useConns=False):
        """
        check the draw ports and see if there is a known pressure
        return the first one found (if more than one, they should be the same)
        UseConns is used to see if a pressure will be interpolated based on all the internal connections
        """
        if useConns:
            tower = self.tower
            cnt = 0
            sumP = 0.0
            
        for draw in self.liqDraws.values() + self.vapDraws.values():
            p = draw.port.GetPropValue(P_VAR)
            if p:
                self.pressureSpec = p
                return p

            elif useConns:
                #Check if the connected feed has a known P in the stage
                #It could only be possibly known if the stage is above it
                #due to the P profile algorithm
                if draw.pumpToFeed:
                    connNu = draw.pumpToFeed.stage.number
                    if tower.P[connNu]:
                        cnt += 1
                        sumP += tower.P[connNu]

        for clone in self.liqClones.values() + self.vapClones.values():
            p = clone.port.GetPropValue(P_VAR)
            if p:
                self.pressureSpec = p
                return p

        #some side strippers may use the feed from an internal connection to provide a p
        if useConns:
            for feed in self.feeds.values():
                if feed.pumpFromDraw:
                    connNu = feed.pumpFromDraw.stage.number
                    if tower.P[connNu]:
                        cnt += 1
                        sumP += tower.P[connNu]
            
            if cnt:
                return sumP/float(cnt)
            
        return None

    def SetPressure(self, value):
        """
        set a pressure to all the objects of this stage as calculated values
        """
        for draw in self.liqDraws.values() + self.vapDraws.values():
            draw.port.SetPropValue(P_VAR, value, CALCULATED_V)

        for clone in self.liqClones.values() + self.vapClones.values():
            clone.port.SetPropValue(P_VAR, value, CALCULATED_V)
    
        
    def EstimateTemperature(self):
        """
        If there is a temperature estimate, return it
        """
        for estimate in self.estimates.values():
            if estimate.type == T_VAR:
                value = estimate.port.GetValue()
                if value:
                    if self.subCool:
                        if self.subCool.isCalculated:
                            #should not use it
                            return value
                        else:
                            return value + self.GetDegreesSubCooled()
                    return value
        for estimate in self.activeSpecs:
            if estimate.type == T_VAR:
                value = estimate.port.GetValue()
                if value:
                    if self.subCool:
                        if self.subCool.isCalculated:
                            #Cant use
                            return None
                        else:
                            return value + self.GetDegreesSubCooled()
                    return value
        return None

    def LargestFeedTemperature(self, useConns=False):            
        """
        If not and there are feeds, return the temperature of largest feed
        Otherwise return None
        """
        largestFeedT = None
        largestFeedF = 0.
        for feed in self.feeds.values():
            flow = feed.port.GetPropValue(MOLEFLOW_VAR)
            temp = feed.port.GetPropValue(T_VAR)
            if temp and flow and flow > largestFeedF:
                largestFeedF = flow
                largestFeedT = temp
            elif useConns and feed.pumpFromDraw and not isinstance(feed.pumpFromDraw, PumpAround):
                connNu = feed.pumpFromDraw.stage.number
                temp = self.tower.T[connNu]
                if temp and not largestFeedF:
                    largestFeedT = temp
                    
                
        return largestFeedT

    def SpecErrors(self):
        """
        scan ports for specs as well as ones defined for  stage
        return a list of errors
        """
        results = []
        #names = self.vapDraws.keys()
        #names.sort()
        #for name in names:
        for draw in self.vapDrawsActive:
            results.extend(draw.SpecErrors())
            #results.extend(self.vapDraws[name].SpecErrors())
                
        #names = self.liqDraws.keys()
        #names.sort()
        #for name in names:
            #results.extend(self.liqDraws[name].SpecErrors())
        for draw in self.liqDrawsActive:
            results.extend(draw.SpecErrors())
            
        names = self.vapClones.keys()
        names.sort()
        for name in names:
            results.extend(self.vapClones[name].SpecErrors())
                
        names = self.liqClones.keys()
        names.sort()
        for name in names:
            results.extend(self.liqClones[name].SpecErrors())

        for spec in self.activeSpecs:
            results.append(spec.Error())                        

        if self.type == TOP_STAGE and len(self.vapDrawsActive) == 0 and self.number != 0:
            # automatically add a zero flow spec if no vapour draw on top
            results.append(self.tower.V[self.number]/self.tower.totalFeedFlow)
        if self.type == BOTTOM_STAGE and len(self.liqDrawsActive) == 0 and self.number != self.tower.numStages-1:
            # automatically add a zero flow spec if no liquid draw on bottom
            results.append(self.tower.L[self.number]/self.tower.totalFeedFlow)

        return results

    def TotalDrawFlow(self):
        """
        return total draw flow assuming those flows are already updated
        Note that any water draw is not included
        """
        total = 0.
        for draw in self.vapDraws.values() + self.liqDraws.values():
            total += draw.flow
            
        return total

    def EstimateReflux(self):
        """
        If there is a reflux spec or estimate, return its value
        """
        for est in self.estimates.values():
            if est.type == REFLUX:
                return est.port.GetValue()
    
        for spec in self.specs.values():
            if spec.type == REFLUX:
                return spec.spec
            
    def UnknownQ(self):
        """
        return 1 if any energy feed is unknown
        """
        for feed in self.qfeeds.values():
            if feed.q == None:
                return 1
        return 0
    
    def AssignQ(self, q):
        """assign a Q to first unknown energy feed"""
        self.calculatedQ = q

    def AssignResultsToPorts(self):
        """
        Assign all results to their respective ports
        """
        
        if self.subCool:
            val = self.GetDegreesSubCooled()
            if val == None:
                #Make sure the value is there.
                #This call should only be needed when a tower was already converged but the
                #degrees of subcooling got deleted
                self.SetDegreesSubCooled(self.tower.T[0] - self.tower.subCoolT[0])
        
        for spec in self.inactiveSpecs:
            spec.AssignResultsToPort()
        
        for draw in self.liqDraws.values() + self.vapDraws.values():
            draw.AssignResultToPort()
        
        for clone in self.liqClones.values() + self.vapClones.values():
            clone.AssignResultToPort()

        if self.waterDraw:
            self.waterDraw.AssignResultToPort()
            
        totalKnownQ = 0.0
        assignTo = None
        for feed in self.qfeeds.values():
            qFeed = feed.TotalQFlow()
            if qFeed is not None:
                totalKnownQ += qFeed * 3.6 # conversion from W
            elif assignTo:
                assignTo = None  # more than one unknown
                break
            else:
                assignTo = feed
                
        if assignTo:
            if assignTo.AssignQ(self.calculatedQ + totalKnownQ):
                assignTo.AssignResultToPort()
                
                
        if self.subCool:
            self.subCool.AssignResultToPort()
            
        ## I am removing the following error check as I don't think it is needed and can cause an
        ## unnecessary error when a tower whose results are already known is solved
        ##elif self.calculatedQ != 0.0:
        ##   raise SimError('TowerQSpecError', self.number)            
        
    def ReadyToSolve(self):
        """
        return 1 if stage feeds are ready 0 otherwise
        """
        for feed in self.feeds.values():
            if not feed.ReadyToSolve(): return 0
            
            
        if self.subCool:
            #Load the value of degrees of subcooling
            #This is redundat with the call to ReadyToSolve, but it is needed such
            #that the vapour draw knows what to do
            self.SetDegreesSubCooled(self.subCool.port.GetValue())
            
        #Do not quit if one of the specs is not ready.
        #The ReadyToSolve call is made so the values get loaded into self.value
        #and the code should be moved into Reset after this works fine
        for spec in self.specs.values():
            spec.ReadyToSolve()
            
        for draw in self.liqDraws.values():
            if self.subCool:
                draw.isSubCooled = True
            draw.ReadyToSolve()
            
        for draw in self.vapDraws.values():
            if self.subCool:
                draw.isSubCooled = True
            draw.ReadyToSolve()    
            
        for clone in self.liqClones.values():
            if self.subCool:
                clone.isSubCooled = True
            clone.ReadyToSolve()
    
        for clone in self.vapClones.values():
            if self.subCool:
                clone.isSubCooled = True
            clone.ReadyToSolve()
            
        if self.waterDraw and self.subCool:
            self.waterDraw.isSubCooled = True
            
        numberUnknownQ = 0
        for feed in self.qfeeds.values():
            feed.Reset()   # to get port value
            if feed.TotalQFlow() == None:
                numberUnknownQ += 1
        if numberUnknownQ > 1:
            return 0
        
        try:
            # try and detect pressure change
            if self.tower.IsForgetting():
                if hasattr(self, 'pressureSpec') and self.pressureSpec and \
                   self.pressureSpec != self.GetPressure():
                    return 0             
        except:
            pass
        if self.subCool:
            if not self.subCool.ReadyToSolve():
                return 0
            
        return 1

    def GetDegreesSubCooled(self):
        """Return the degrees of subcooling from the local value, not from the port"""
        
        #Note that in this case, None is not the same as 0.0
        try:
            return self.subCool.value
        except:
            return None
        
    def SetDegreesSubCooled(self, value):
        """Set the degrees of subcooling to the local value"""
        self.subCool.value = value
        
    def GetSubCooledTemp(self):
        """Return the subcooled temperature"""
        return self.subCool.subCooledT
        
    def IsSubCooled(self):
        """Return if it has a subcooling object"""
        return self.subCool
    
    def SolveSubCooledFlow(self):
        """The vapour flow is zero if the stage is subcooling"""
        if self.subCool:
            try:
                #Do not go through self.GetDegreesSubCooled(). Get the value from the port directly
                dt = self.subCool.port.GetValue()
                if dt != None and dt > 0.0:
                    for draw in self.vapDraws.values() + self.vapClones.values():
                        draw.port.SetPropValue(MOLEFLOW_VAR, 0.0, CALCULATED_V)
            except:
                pass
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        for name, obj in self.feeds.items():
            prevObj = clone.GetObject(name)
            if name[-4:] != '_paR':
                if not prevObj:
                    objClone = obj.Clone()
                    clone.AddObject(objClone, name)
                    objClone = clone.GetObject(name)
                else:
                    objClone = prevObj
                if objClone != None:
                    obj.CloneContents(objClone)
                
        for name, obj in self.liqDraws.items():
            prevObj = clone.GetObject(name)
            if not prevObj:
                objClone = obj.Clone()
                clone.AddObject(objClone, name)
                objClone = clone.GetObject(name)
            else:
                objClone = prevObj
            if objClone != None:
                obj.CloneContents(objClone)
                
        for name, obj in self.vapDraws.items():
            prevObj = clone.GetObject(name)
            if not prevObj:
                objClone = obj.Clone()
                clone.AddObject(objClone, name)
                objClone = clone.GetObject(name)
            else:
                objClone = prevObj
            if objClone != None:
                obj.CloneContents(objClone)
                
        for name, obj in self.liqClones.items():
            prevObj = clone.GetObject(name)
            if not prevObj:
                objClone = obj.Clone()
                clone.AddObject(objClone, name)
                objClone = clone.GetObject(name)
            else:
                objClone = prevObj
            if objClone != None:
                obj.CloneContents(objClone)
                
        for name, obj in self.vapClones.items():
            prevObj = clone.GetObject(name)
            if not prevObj:
                objClone = obj.Clone()
                clone.AddObject(objClone, name)
                objClone = clone.GetObject(name)
            else:
                objClone = prevObj
            if objClone != None:
                obj.CloneContents(objClone)
                
        for name, obj in self.qfeeds.items():
            prevObj = clone.GetObject(name)
            if name[-4:] != '_paQ':
                if not prevObj:
                    objClone = obj.Clone()
                    clone.AddObject(objClone, name)
                    objClone = clone.GetObject(name)
                else:
                    objClone = prevObj
                if objClone != None:
                    obj.CloneContents(objClone)
                
        for name, obj in self.specs.items():
            prevObj = clone.GetObject(name)
            if not prevObj:
                objClone = obj.Clone()
                clone.AddObject(objClone, name)
                objClone = clone.GetObject(name)
            else:
                objClone = prevObj
            if objClone != None:
                obj.CloneContents(objClone)
                
        for name, obj in self.estimates.items():
            prevObj = clone.GetObject(name)
            if not prevObj:
                objClone = obj.Clone()
                clone.AddObject(objClone, name)
                objClone = clone.GetObject(name)
            else:
                objClone = prevObj
            if objClone != None:
                obj.CloneContents(objClone)
                
        if self.waterDraw != None:
            if not clone.waterDraw:
                objClone = self.waterDraw.Clone()
                clone.AddObject(objClone, self.waterDraw.name)
                objClone = clone.GetObject(self.waterDraw.name)
            else:
                objClone = clone.waterDraw
            if objClone != None:
                self.waterDraw.CloneContents(objClone)
                
        if self.subCool != None:
            if not clone.subCool:
                objClone = self.subCool.Clone()
                clone.AddObject(objClone, self.subCool.name)
                objClone = clone.GetObject(self.subCool.name)
            else:
                objClone = clone.subCool
            if objClone != None:
                self.subCool.CloneContents(objClone)
                    
                    
class StageObject(object):
    """common class for feeds and draws"""
    def Initialize(self, stage, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        self.stage = stage
        self.name = name

    def CleanUp(self):
        """remove all references"""
        self.stage = None
 
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        pass  # handled by derived classes if necessary

    def GetPath(self):
        """return object path to this object"""
        return '%s.%s' % (self.stage.GetPath(), self.name)
        
    def GetParent(self):
        """return stage as parent in hierarchy"""
        return self.stage
    
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
        if name == 'ParentStage':
            tower = self.stage.GetParent()
            oldNumber = self.stage.number
            newNumber = int(obj)
            if oldNumber == newNumber: return
            newStage = tower.stages[newNumber]
            
            #Raise error if destiny stage already has an object with the same name
            if newStage.GetObject(self.name):
                tower.InfoMessage('CantMoveToStage',(self.name, newNumber, tower.GetPath()))
                raise AssertionError
            
            self.stage.UnlinkObject(self)
            self.stage = tower.stages[newNumber]
            self.stage.LinkToObject(self, self.name)
            self.ChangeStageNumber(tower, oldNumber, newNumber)
            
            
        elif name == 'NewName':
            newName = str(obj)
            self.ChangeName(self.stage.GetParent(), self.name, newName)
            
        else:
            raise SimError('CantAddToStageObject',(name, self.name,
                                            self.stage.number, self.stage.tower.GetPath()))
            
    def Stage(self): 
        return self.stage
    
    def ChangeName(self, tower, fromName, toName):
        """
        Change name in corresponding dictionary and in associated port if necessary
        """
        if self.stage.GetObject(toName):
            self.InfoMessage('DuplicateName', (toName, self.stage.GetPath()))
            return
        
        number = self.stage.number
        if hasattr(self,'TowerPortName'):
            oldPortName = self.TowerPortName(number)
        
        #Let the stage rename the object
        self.stage.ChangeObjectName(fromName, toName)

        #Change port name if necessary
        if hasattr(self,'TowerPortName'):
            newPortName = self.TowerPortName(number)
            tower.RenamePort(oldPortName, newPortName)
    
    def ChangeStageNumber(self, tower, fromNumber, toNumber):
        """
        Must change port name that tower uses for this object's port - if they have one
        """
        if hasattr(self,'TowerPortName'):
            tower.RenamePort(self.TowerPortName(fromNumber), self.TowerPortName(toNumber))
    
    
    def Clone(self):
        clone = self.__class__()
        return clone
    
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        pass
    
class DegSubCooling(StageObject):
    """Degrees of subcooling. Technically it could go in any stage, but in practice
    this object should only be installed in the top stage"""
    
    def __init__(self):
        self.value = None
        self.subCooledT = None
        self.isCalculated = False
    
    def __str__(self):
        return 'DegSubCool:' + self.name
        
    def Initialize(self, stage, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(DegSubCooling, self).Initialize(stage, name)
        self.port = stage.tower.CreatePort(SIG, self.TowerPortName(stage.number))
        self.port.SetSignalType(DELTAT_VAR)

    def CleanUp(self):
        self.stage.tower.DeletePort(self.port)
        self.port = None
        super(DegSubCooling, self).CleanUp()
        
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'DegSubCool_%d_%s' % (stageNo, self.name)
    
    def AddObject(self, obj, name):
        """ use add to change parent stage """
        if name == 'ParentStage':
            tower = self.stage.GetParent()
            oldNumber = self.stage.number
            newNumber = int(obj)
            if oldNumber == newNumber: return
            
            #Don't let it change stage unless it is to a top stage
            if newNumber != 0:
                raise SimError('CantAddToStageObject',(name, self.name,
                                            self.stage.number, self.stage.tower.GetPath()))
            
            
        elif name == 'NewName':
            newName = str(obj)
            self.ChangeName(self.stage.GetParent(), self.name, newName)
            
        else:
            raise SimError('CantAddToStageObject',(name, self.name,
                                            self.stage.number, self.stage.tower.GetPath()))
        
    def Reset(self):
        """Nothing here"""
        #self.value = self.port.GetValue()
        pass
        
    def ReadyToSolve(self):
        """Check (and load) if it has a value in the port or if it can be calculated"""
        
        #Value is the degrees of subcooling
        #It is ready if it has any of value or subCooledT
        
        self.value = self.port.GetValue()
        self.subCooledT = None
        if self.value == None:
            self.isCalculated = True
            
            ##Check if a vap or a liq T are known
            stage = self.stage
            aVapT = None
            aLiqT = None
            
            for draw in stage.liqDraws.values() + stage.liqClones.values():
                aLiqT = draw.port.GetPropValue(T_VAR) 
                if aLiqT:
                    self.subCooledT = aLiqT
                    return True
                
            for draw in stage.vapDraws.values() + stage.vapClones.values():
                aVapT = draw.port.GetPropValue(T_VAR) 
                if aVapT:
                    self.subCooledT = aVapT
                    return True
                
            if aLiqT == None and aVapT == None:
                for spec in stage.specs.values():
                    if isinstance(spec, StageSpecification):
                        if spec.type == T_VAR:
                            try:
                                if spec.value != None:
                                    aVapT = spec.value
                                    self.subCooledT = aVapT
                                    return True
                            except:
                                pass
                            
            return False
                
        else:
            self.isCalculated = False
        return True
                    
    def AssignResultToPort(self):
        """Put the degrees of subcooling into port in case it was obtained from the draws"""
        if self.isCalculated:
            #value = self.stages.tower.T[0] - self.stage.tower.subCooledT[0]
            self.port.SetValue(self.value, CALCULATED_V)
        
    def AdjustOldCase(self, version):
        if version[0] < 48:
            if not hasattr(self, 'subCooledT'):
                self.subCooledT = None
    def Clone(self):
        clone = super(DegSubCooling, self).Clone()
        clone.value = self.value
        clone.subCooledT = self.subCooledT
        clone.isCalculated = self.isCalculated
        return clone
    
    
    
class Feed(StageObject):
    """Feed to tower stage"""
    def __str__(self):
        return 'Feed:' + self.name
        
    def Initialize(self, stage, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(Feed, self).Initialize(stage, name)
        self.port = stage.tower.CreatePort(MAT|IN, self.TowerPortName(stage.number))
        self.pumpFromDraw = None
        self.flow = None

    def AddObject(self, obj, name):
        """ Do not allow change of name if it is comes from a PumpAround. Change name of pumparound instead """
        if name == 'NewName':
            if self.pumpFromDraw:
                self.stage.GetParent().InfoMessage('CantChangeName', (self.GetPath(),))
                return
            
        super(Feed, self).AddObject(obj, name)
        
        
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'Feed_%d_%s' % (stageNo, self.name)

 
    def CleanUp(self):
        """remove all references"""
        self.stage.tower.DeletePort(self.port)
        if self.pumpFromDraw:
            self.pumpFromDraw.pumpToFeed = None
        self.port = self.pumpFromDraw = None
        super(Feed, self).CleanUp()
        
    def MoleArray(self):
        """return an array of moles in feed"""
        moles = self.TotalFlow()
        
        if moles == 0.0:
            return zeros(self.stage.tower.numCompounds, Float)
        
        x = array(self.port.GetCompositionValues())
        return (x / Numeric.sum(x)) * moles

    def MoleFracs(self):
        """return an array of moleFractions"""
        x = array(self.port.GetCompositionValues())
        return x / Numeric.sum(x)
    
    def MassFracs(self):
        moleFracs = self.MoleFracs()
        tower = self.stage.tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        # temperature, pressure and phase are just dummies
        fracs = thAdmin.GetArrayProperty(prov, case, (T_VAR, 0.0), (P_VAR, 0.0),
                                         LIQUID_PHASE, moleFracs, 'MassFraction')
        return fracs

    def MassFlow(self):
        """
        return the total mass flow of the draw
        """
        moleFracs = self.MoleFracs()
        tower = self.stage.tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        mw = thAdmin.GetProperties(prov, case, (T_VAR, 0.0), (P_VAR, 0.0), 
                                   LIQUID_PHASE, moleFracs, ('MolecularWeight',))[0]
        return mw*self.flow
    
    def ReadyToSolve(self):
        """
        return true if feed is known or pumparound
        """
        if self.pumpFromDraw:
            if isinstance(self.pumpFromDraw, PumpAround): 
                return 1
            else:
                #This could happen if the ports get disconnected because the objects do
                #not get notified when they get disconnected
                self.pumpFromDraw.pumpFromFeed = None
                self.pumpFromDraw = None
        
        # can't be sure pumpFromDraw is known yet so must check connection
        connection = self.port.GetConnection()
        if connection and connection.GetParent() == self.stage.tower: return 1
        
        tower = self.stage.tower
        retVal = self.port.AlreadyFlashed() and self.port.GetPropValue(MOLEFLOW_VAR) != None
        #if not retVal and not tower.IsForgetting(): 
            #tower.InfoMessage('TowerMissingFeedInfo', self.GetPath())
        
        return retVal  
        
    def TotalFlow(self):
        """return the total molar flow of the feed (0 if pump around)"""
        if self.pumpFromDraw:
            return 0.
        else:
            return self.port.GetPropValue(MOLEFLOW_VAR)
        

    def TotalVapourFlow(self):
        """return molar flow times vapour fraction """
        flow = self.TotalFlow()
        if flow:
            return flow * self.port.GetPropValue(VPFRAC_VAR)
        else:
            return 0.0

    def TotalLiquidFlow(self):
        """return molar flow time one minus vapour fraction """
        flow = self.TotalFlow()
        if flow:
            return flow * (1.0 - self.port.GetPropValue(VPFRAC_VAR))
        else:
            return 0.0

    def TotalQFlow(self):
        """return heat flow (0 if pump around)"""
        if self.pumpFromDraw:
            return 0.
        else:
            return self.port.GetPropValue(ENERGY_VAR)
        
    def Reset(self):
        """reset any variables from previous calculations"""
        
        #First check if it is connected to a draw in a stage above
        if hasattr(self, 'pumpFromDraw') and self.pumpFromDraw:
            if self.pumpFromDraw.stage.number > self.stage.number:
                #Already Reset by the draw. Just leave
                return
        
        self.flow = self.port.GetPropValue(MOLEFLOW_VAR)
        
    
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        clone.flow = self.flow
        
        
class Draw(StageObject):
    """draw from tower stage"""
    def Initialize(self, stage, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(Draw,self).Initialize(stage, name)
        self.port = stage.tower.CreatePort(MAT|OUT, self.TowerPortName(stage.number))

        #This variable is updated by the stage object
        #when running ReadyToSolve
        self.isSubCooled = False
        
        self.isBasis = 0
        self.pumpToFeed = None
        self.flow = None
        self.estimates = {}
        self.portSpecs = []   # specs created from info in port
        self.drawSpecs = {}
        self.drawActiveSpecs = []       #Gets filled in dynamically when solving
        self.drawInactiveSpecs = []     #Gets filled in dynamically when solving
        self.userSpecs = 0
        
        #Requesting vol flows require knowing the phase. 
        #This will have to get specified by whoever inherits from it
        self.phase = ''               #String recognized locally by the tower
        self.phaseForCalcs = None     #Constant recognized globally by sim42
        
    def CleanUp(self):
        if self.pumpToFeed:
            self.pumpToFeed.pumpFromDraw = None
        self.pumpToFeed = None

        self.stage.tower.DeletePort(self.port)
        self.port = None

        for est in self.estimates:
            self.estimates[est].CleanUp()
        self.estimates = None
        
        for spec in self.portSpecs:
            spec.CleanUp()
        self.portSpecs = None
            
        for spec in self.drawSpecs:
            self.drawSpecs[spec].CleanUp()
        self.drawSpecs = None
        
        self.drawActiveSpecs = []
        self.drawInactiveSpecs = []
                
        super(Draw,self).CleanUp()

    def AdjustOldCase(self, version):
        """
        fixup for older recalled versions
        """
        if version[0] < 2:
            self.drawSpecs = {}
        if version[0] < 3:
            self.userSpecs = 0
        if version[0] < 29:
            if not hasattr(self, 'phase'):
                self.phase = None
            if not hasattr(self, 'phaseForCalcs'):
                self.phaseForCalcs = None
        if version[0] < 37:
            if not hasattr(self, 'isSubCooled'):
                self.isSubCooled = False
                
        for spec in self.drawSpecs.values():
            spec.AdjustOldCase(version)
            
        for est in self.estimates.values():
            est.AdjustOldCase(version)
            
        super(Draw, self).AdjustOldCase(version)
            
    def ChangeStageNumber(self, tower, fromNumber, toNumber):
        """
        Must change port name that tower uses for this object's port - if they have one
        """
        super(Draw, self).ChangeStageNumber(tower, fromNumber, toNumber)
        
        for obj in self.estimates.values():
            if hasattr(obj, 'TowerPortName'):
                tower.RenamePort(obj.TowerPortName(fromNumber), obj.TowerPortName(toNumber))
        for obj in self.drawSpecs.values():
            if hasattr(obj, 'TowerPortName'):
                tower.RenamePort(obj.TowerPortName(fromNumber), obj.TowerPortName(toNumber))
                
                
    def AddObject(self, obj, name):
        """only a flow estimate or a specification can be added"""
        if isinstance(obj, Estimate):
            if name in self.estimates:
                self.DeleteObject(self.estimates[name])
            else:
                #The name can't be repeated in the whole stage because there is a
                #problem with the name of the port
                stage = self.stage
                if name in stage.estimates:
                    raise SimError('CantAddToStage',(name, stage.number, stage.tower.GetPath()))
                for draw in stage.liqDraws.values() + stage.vapDraws.values():
                    if name in draw.estimates:
                        raise SimError('CantAddToStage',(name, stage.number, stage.tower.GetPath()))
                for clone in stage.liqClones.values() + stage.vapClones.values():
                    if name in clone.estimates:
                        raise SimError('CantAddToStage',(name, stage.number, stage.tower.GetPath()))
    
            self.estimates[name] = obj
            obj.Initialize(self, name)
        elif  isinstance(obj, DrawSpec):
            if name in self.drawSpecs:
                self.DeleteObject(self.drawSpecs[name])
            else:
                #The name can't be repeated in the whole stage because there is a
                #problem with the name of the port
                stage = self.stage
                if name in stage.specs:
                    raise SimError('CantAddToStage',(name, stage.number, stage.tower.GetPath()))
                for draw in stage.liqDraws.values() + stage.vapDraws.values():
                    if name in draw.drawSpecs:
                        raise SimError('CantAddToStage',(name, stage.number, stage.tower.GetPath()))
                for clone in stage.liqClones.values() + stage.vapClones.values():
                    if name in clone.drawSpecs:
                        raise SimError('CantAddToStage',(name, stage.number, stage.tower.GetPath()))
                    
            self.drawSpecs[name] = obj
            obj.Initialize(self, name)
            
            #If the tower is already converged, then this spec is probably
            #for vieweing purposes... Reset it.
            tower = self.stage.tower
            if tower.converged and not tower.GetParameterValue(IGNORED_PAR) and tower.GetParameterValue(TRYTOSOLVE_PAR):
                if not isinstance(obj, PropertySpecWithSettings):
                    obj.Reset()
                    #Put it in the inactive specs list
                    self.drawInactiveSpecs.append(obj)
                    obj.AssignResultsToPort()

        elif name == 'ParentStage':
            tower = self.stage.GetParent()
            oldNumber = self.stage.number
            newNumber = int(obj)
            if oldNumber == newNumber: return
            newStage = tower.stages[newNumber]
            
            #Raise error if destiny stage already has an object with the same name
            if newStage.GetObject(self.name):
                tower.InfoMessage('CantMoveToStage',(self.name, newNumber, tower.GetPath()))
                raise AssertionError
            
            self.stage.UnlinkObject(self)
            self.stage = tower.stages[newNumber]
            self.stage.LinkToObject(self, self.name)
            self.ChangeStageNumber(tower, oldNumber, newNumber)
            
            for spec in self.drawSpecs.values():
                spec.stage = self.stage
                spec.ChangeStageNumber(tower, oldNumber, newNumber)
            for est in self.estimates.values():
                est.stage = self.stage
                est.ChangeStageNumber(tower, oldNumber, newNumber)
            
        else:
            super(Draw, self).AddObject(obj, name)

    def DeleteObject(self, obj):
        if isinstance(obj, Estimate):
            obj.CleanUp()
            for i in self.estimates.iteritems():
                if i[1] is obj:
                    break
            if i and i[1] is obj:            
                del self.estimates[i[0]]
        elif isinstance(obj, DrawSpec):
            obj.CleanUp()
            for i in self.drawSpecs.iteritems():
                if i[1] is obj:
                    break
            if i and i[1] is obj:            
                del self.drawSpecs[i[0]]
        self.stage.tower.converged = 0
            
    def GetContents(self):
        """if there is estimate, return it as contents"""
        
        results =[]
        for est in self.estimates:
            results.append((est,self.estimates[est]))
 
        for spec in self.drawSpecs:
            results.append((spec,self.drawSpecs[spec]))
            
        return results
        
    def GetObject(self, name):
        obj = StageObject.GetObject(self, name)
        if obj: return obj
        
        if name in self.estimates:
            return self.estimates[name]
        elif name in self.drawSpecs:
            return self.drawSpecs[name]
        elif name == 'MassFractions' and hasattr(self, 'MassFracs'):
            return self.MassFracs()
        else:
            return None

    def Reset(self):
        """
        reset old variables
        determine if this draw is a pumparound connected to a Feed
        assign flow if fixed or estimated
        """
        self.flow = None
        self.pumpToFeed = None
        self.isBasis = 0
        self.portSpecs = []   # specs created from info in port
        self.isSubCooled = self.stage.IsSubCooled()
        self.flowSpecType = None
        self.flowSpecVal = None
        self.zeroFlow = False  #Tag draw when spec is a zero flow. 
        
        for spec in self.drawSpecs:
            self.drawSpecs[spec].Reset()
        
        # check port for known info and create specs as necessary
        moleFlow = self.port.GetPropValue(MOLEFLOW_VAR)
        if moleFlow != None:
            if moleFlow <= smallestAllowedFlow: self.zeroFlow = True
            spec = PortDrawMoleFlowSpec(self, moleFlow, self.port)
            self.portSpecs.append(spec)
            self.flowSpecType = MOLEFLOW_VAR
            self.flowSpecVal = moleFlow
        else:    
            massFlow = self.port.GetPropValue(MASSFLOW_VAR)        
            if massFlow != None:
                if massFlow <= smallestAllowedFlow: self.zeroFlow = True
                spec = PortDrawMassFlowSpec(self, massFlow, self.port)
                self.portSpecs.append(spec)
                self.flowSpecType = MASSFLOW_VAR
                self.flowSpecVal = massFlow
            else:    
                stdVolFlow = self.port.GetPropValue(STDVOLFLOW_VAR)        
                if stdVolFlow != None:
                    if stdVolFlow <= smallestAllowedFlow: self.zeroFlow = True
                    spec = PortDrawStdVolFlowSpec(self, stdVolFlow, self.port)
                    self.portSpecs.append(spec)
                    self.flowSpecType = STDVOLFLOW_VAR
                    self.flowSpecVal = stdVolFlow
                else:
                    volFlow = self.port.GetPropValue(VOLFLOW_VAR)        
                    if volFlow != None:
                        if volFlow <= smallestAllowedFlow: self.zeroFlow = True
                        spec = PortDrawVolFlowSpec(self, volFlow, self.port)
                        self.portSpecs.append(spec)
                        self.flowSpecType = VOLFLOW_VAR
                        self.flowSpecVal = volFlow

        portTemp = self.port.GetPropValue(T_VAR)        
        if portTemp != None:
            if self.isSubCooled and self.stage.subCool.isCalculated:
                ##If it is subCooled and the subCool object has a calculated value
                ##then it means that the sat T and the T in the liq are both known
                ##hence, this T should not be counted as a spec (this should be the liq)
                ##as the 
                pass
            else:
                spec = PortTemperatureSpec(self, portTemp, self.port)
                self.portSpecs.append(spec)
            
        moleFracs = self.port.GetCompositionValues()
        for i in range(len(moleFracs)):
            if moleFracs[i] != None:
                spec = PortMoleFracSpec(self.stage, self.phase, i, moleFracs[i], self.port)
                self.portSpecs.append(spec)

        estFlow = None
        for est in self.estimates:
            estimate = self.estimates[est]
            if estimate.port.GetType().name == MOLEFLOW_VAR:
                estFlow = estimate.port.GetValue()
                
        if estFlow != None:
            self.flow = estFlow
        elif moleFlow != None:
            self.flow = moleFlow
        if self.zeroFlow:
            self.flow = smallestAllowedFlow
        
        if self.pumpToFeed:
            self.pumpToFeed.pumpFromDraw = None
            self.pumpToFeed = None
            
        connection = self.port.GetConnection()
        if connection and connection.GetParent() == self.stage.tower:
            # it is connected back to this tower
            # can figure out stage from name
            (toNumber, toName) = string.split(connection.GetName(),'_',2)[1:]
            toNumber = int(toNumber)
            self.pumpToFeed = self.stage.tower.stages[toNumber].feeds[toName]
            self.pumpToFeed.pumpFromDraw = self  # circular reference that needs breaking to delete
            self.pumpToFeed.Reset()
            if self.flow != None:
                #Check if self.pumpToFeed.flow already has a value??
                self.pumpToFeed.flow = self.flow
            elif self.pumpToFeed.flow != None:
                self.flow = self.pumpToFeed.flow
                
        elif self.pumpToFeed and not isinstance(self, PumpAround):
            #Make sure that it doesn't have a pumpToFeed left over from a broken connection
            #This is necessary because it doesn't get notified when disconnected
            self.pumpToFeed.pumpFromDraw = None
            self.pumpToFeed = None
            
            
    def NumberSpecs(self):
        """
        return the number of specs associated with this draw
        """
        numSpecs = 0
        portFlow = self.port.GetPropValue(MOLEFLOW_VAR)        
        if portFlow != None:
            numSpecs += 1
        else:
            portFlow = self.port.GetPropValue(MASSFLOW_VAR)
            if portFlow != None:
                numSpecs += 1
            else:
                portFlow = self.port.GetPropValue(STDVOLFLOW_VAR)
                if portFlow != None:
                    numSpecs += 1
                else:
                    portFlow = self.port.GetPropValue(VOLFLOW_VAR)
                    if portFlow != None:
                        numSpecs += 1
                                    
        portTemp = self.port.GetPropValue(T_VAR)        
        if portTemp != None:
            #The following tow variables will be up to date as long as this variable is called
            #after ReadyToSolve()
            if self.isSubCooled and self.stage.subCool.isCalculated:
                ##If it is subCooled and the subCool object has a calculated value
                ##then it means that the sat T and the T in the liq are both known
                ##hence, this T should not be a counted as a spec (this should be the liq)
                ##as the 
                pass
            else:
                numSpecs += 1
        
        moleFracs = self.port.GetCompositionValues()
        for i in range(len(moleFracs)):
            if moleFracs[i] != None:
                numSpecs += 1

        #numSpecs += len(self.drawSpecs)
        drawActiveSpecs = self.drawActiveSpecs = []
        drawInactiveSpecs = self.drawInactiveSpecs = []
        for spec in self.drawSpecs.values():
            if spec.port.GetValue() != None:
                drawActiveSpecs.append(spec)
            else:
                drawInactiveSpecs.append(spec)
        numSpecs += len(drawActiveSpecs)
        
        if self.stage.tower.converged == 0:
            self.userSpecs = numSpecs  # save last unconverged number
        return numSpecs

    def NumberOfUserSpecs(self):
        """
        return number of user supplied specs on this draw
        """
        return self.userSpecs

    def SpecErrors(self):
        """
        return list of specification errors
        """
        results = []
        for spec in self.portSpecs:
            results.append(spec.Error())
        for spec in self.drawActiveSpecs:
            results.append(spec.Error())
            
        return results
        

    def AssignResultToPort(self):
        """
        assign P, and flow to port
        """
        stageNo = self.stage.number
        tower = self.stage.tower
        self.port.SetPropValue(P_VAR, tower.P[stageNo], CALCULATED_V)
        self.port.SetPropValue(MOLEFLOW_VAR, self.flow, CALCULATED_V)
        for spec in self.drawInactiveSpecs:
            spec.AssignResultsToPort()

    def ReadyToSolve(self):
        """
        return 1 if draw specs are ready 0 otherwise
        """
        
        #Do not quit if not ready to solve.
        #This call is not used anymore to check if ready to solve. Its only
        #purpose is loading the values into self.value
        for spec in self.drawSpecs:
            self.drawSpecs[spec].ReadyToSolve()

        for spec in self.portSpecs:
            # need to check for port so as not to break old stored cases
            if hasattr(spec, 'port') and spec.SpecValue() == None:
                self.portSpecs = []
                break
        
        for est in self.estimates:
            self.estimates[est].ReadyToSolve()
            
        return 1

    def MassFlow(self):
        """
        return the total mass flow of the draw
        """
        tower = self.stage.tower
        moleFracs = self.MoleFracs()
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        mw = thAdmin.GetProperties(prov, case, (T_VAR,0.0), (P_VAR, 0.0), 
                                   LIQUID_PHASE, moleFracs, ('MolecularWeight',))[0]
        return mw*self.flow
    
    def VolumeFlow(self):
        """
        return the total mass flow of the draw
        """
        tower = self.stage.tower
        moleFracs = self.MoleFracs()
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        stageNo = self.stage.number
        T, P = tower.T[stageNo], tower.P[stageNo]
        if self.isSubCooled:
            T -= self.stage.GetDegreesSubCooled()
        molVol = thAdmin.GetProperties(prov, case, (T_VAR, T), (P_VAR, P), 
                                       self.phaseForCalcs, moleFracs, (MOLARV_VAR,))[0]
        return molVol*self.flow

    def StdVolumeFlow(self):
        """
        return the total mass flow of the draw
        """
        tower = self.stage.tower
        moleFracs = self.MoleFracs()
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        refT = tower.GetStdVolRefT()
        stdMolVol = thAdmin.GetProperties(prov, case, (T_VAR,refT), (P_VAR, 101.325), 
                                          LIQUID_PHASE, moleFracs, (STDLIQVOL_VAR,))[0]
        return stdMolVol*self.flow
    
    
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        clone.isSubCooled = self.isSubCooled
        clone.flow = self.flow
        clone.userSpecs = self.userSpecs
        clone.phase = self.phase
        clone.phaseForCalcs = self.phaseForCalcs
        
        for name, obj in self.drawSpecs.items():
            prevObj = clone.GetObject(name)
            if not prevObj:
                objClone = obj.Clone()
                clone.AddObject(objClone, name)
                objClone = clone.GetObject(name)
            else:
                objClone = prevObj
            if objClone != None:
                obj.CloneContents(objClone)
                
        for name, obj in self.estimates.items():
            prevObj = clone.GetObject(name)
            if not prevObj:
                objClone = obj.Clone()
                clone.AddObject(objClone, name)
                objClone = clone.GetObject(name)
            else:
                objClone = prevObj
            if objClone != None:
                obj.CloneContents(objClone)
                    
                    
class LiquidDraw(Draw):
    """Liquid draw from tower stage"""
    def __str__(self):
        return 'LiquidDraw:' + self.name
        
    def Initialize(self, stage, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(LiquidDraw,self).Initialize(stage, name)
        self.phase = TOWER_LIQ_PHASE
        self.phaseForCalcs = LIQUID_PHASE

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(LiquidDraw, self).AdjustOldCase(version)
        if version[0] < 29:
            self.phaseForCalcs = LIQUID_PHASE
                
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'LiquidDraw_%d_%s' % (stageNo, self.name)
            
    def AssignResultToPort(self):
        """
        assign VF and liquid mole fractions to port and calc super class
        """
        super(LiquidDraw,self).AssignResultToPort()
        
        stageNo = self.stage.number
        tower = self.stage.tower
        # self.port.SetPropValue(VPFRAC_VAR, 0.0, CALCULATED_V)
        # switch back to T until prop pkg problem resolved
        
        T = tower.T[stageNo]
        if self.isSubCooled:
            T -= self.stage.GetDegreesSubCooled()
                
        self.port.SetPropValue(T_VAR, T, CALCULATED_V)
        self.port.SetCompositionValues(tower.x[stageNo], CALCULATED_V)

    def MoleFracs(self):
        """return the current mole fractions"""
        return self.stage.tower.x[self.stage.number]
    
    def MassFracs(self):
        moleFracs = self.MoleFracs()
        tower = self.stage.tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        # temperature, pressure and phase are just dummies
        fracs = thAdmin.GetArrayProperty(prov, case, (T_VAR, 0.0), (P_VAR, 0.0),
                                         LIQUID_PHASE, moleFracs, 'MassFraction')
        return fracs

    def VolumeFracs(self):
        moleFracs = self.MoleFracs()
        tower = self.stage.tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        # temperature, pressure and phase are just dummies
        fracs = thAdmin.GetArrayProperty(prov, case, (T_VAR, 0.0), (P_VAR, 0.0),
                                         LIQUID_PHASE, moleFracs, 'IdealVolumeFraction')
        return fracs
        
    
class VapourDraw(Draw):
    """Vapour draw from tower stage"""
    def __str__(self):
        return 'VapourDraw:' + self.name
        
    def Initialize(self, stage, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(VapourDraw,self).Initialize(stage, name)
        self.phase = TOWER_VAP_PHASE
        self.phaseForCalcs = VAPOUR_PHASE

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        super(VapourDraw, self).AdjustOldCase(version)
        if version[0] < 29:
            self.phaseForCalcs = VAPOUR_PHASE
        
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'VapourDraw_%d_%s' % (stageNo, self.name)

    def AssignResultToPort(self):
        """
        assign VF and vapour mole fractions to port and calc super class
        """
        super(VapourDraw, self).AssignResultToPort()
        
        stageNo = self.stage.number
        tower = self.stage.tower
        #self.port.SetPropValue(VPFRAC_VAR, 1.0, CALCULATED_V)
        # switch back to T until prop pkg problem resolved
        T = tower.T[stageNo]
        if self.isSubCooled:
            T -= self.stage.GetDegreesSubCooled()
            
        self.port.SetPropValue(T_VAR, T, CALCULATED_V)
        self.port.SetCompositionValues(tower.y[stageNo], CALCULATED_V)

    def MoleFracs(self):
        """return the current mole fractions"""
        return self.stage.tower.y[self.stage.number]
        

    def MassFracs(self):
        moleFracs = self.MoleFracs()
        tower = self.stage.tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        # temperature, pressure and phase are just dummies
        fracs = thAdmin.GetArrayProperty(prov, case, (T_VAR, 0.0), (P_VAR, 0.0),
                                         VAPOUR_PHASE, moleFracs, 'MassFraction')
        return fracs
        
    def VolumeFracs(self):
        moleFracs = self.MoleFracs()
        tower = self.stage.tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        # temperature, pressure and phase are just dummies
        fracs = thAdmin.GetArrayProperty(prov, case, (T_VAR, 0.0), (P_VAR, 0.0),
                                         VAPOUR_PHASE, moleFracs, 'IdealVolumeFraction')
        return fracs

class PumpAround(Draw):
    """
    super class providing the general pump around behavior in
    derived LiquidPumpAround and VapourPumpAround classes
    """
    def __init__(self, destStageNo, isHeating=0):
        """
        save the destination stage number and Q direction for Initialize
        """
        super(PumpAround, self).__init__()
        self.destStageNo = destStageNo
        self.isHeating = isHeating
        
    def AddObject(self, obj, name):
        if name == 'ReturnStage':
            self.paFeed.name
            self.paQ.name
            
            #This call does some redundant validation, but it is better than
            #succeeding at moving q and failing at movinf feed
            tower = self.stage.GetParent()
            oldNumber = self.paFeed.stage.number
            newNumber = int(obj)
            if oldNumber == newNumber: return
            newStage = tower.stages[newNumber]
            
            #Raise error if destiny stage already has an object with the same name
            if newStage.GetObject(self.paFeed.name):
                tower.InfoMessage('CantMoveToStage',(self.paFeed.name, newNumber, tower.GetPath()))
                raise AssertionError
            if newStage.GetObject(self.paQ.name):
                tower.InfoMessage('CantMoveToStage',(self.paFeed.name, newNumber, tower.GetPath()))
                raise AssertionError
            
            #Could use some validation here to ensure both succeeded
            self.paFeed.AddObject(obj, 'ParentStage')
            self.paQ.AddObject(obj, 'ParentStage')
            
            
        else:
            super(PumpAround, self).AddObject(obj, name)
        
    def CleanUp(self):
        """
        get rid of the feeds we created
        """
        if self.destStage:
            if self.paFeed.stage:  # in case it has already been cleaned up
                self.paFeed.locked = False
                self.destStage.DeleteObject(self.paFeed)
            if self.paQ.stage:
                self.paQ.locked = False
                self.destStage.DeleteObject(self.paQ)
            self.destStage = None
            
        super(PumpAround,self).CleanUp()
        
    def Initialize(self, stage, name):
        """
        set up return
        """
        super(PumpAround,self).Initialize(stage, name)
        self.paFeed = Feed()
        self.paFeed.locked = True
        self.paQ = EnergyFeed(self.isHeating)
        self.paQ.locked = True
        self.destStage = stage.tower.GetObject('Stage_%d' % self.destStageNo)
        if not self.destStage:
            stage.DeleteObject(self)
            raise SimError('InvalidTowerPADest', (self.destStageNo, name, stage.GetPath()))
        self.destStage.AddObject(self.paFeed, name + "_paR")
        self.destStage.AddObject(self.paQ, name + "_paQ")
        self.paFeed.pumpFromDraw = self

    def ChangeName(self, tower, fromName, toName):
        """
        Do the stuff from the parent and also change the names of the associated stage (i.e. where stuff moves to)
        """

        self.paFeed.ChangeName(tower, self.paFeed.name, toName + "_paR")
        self.paQ.ChangeName(tower, self.paQ.name, toName + "_paQ")
        
        super(PumpAround, self).ChangeName(tower, fromName, toName)
        
        
    def Reset(self):
        """
        set up the pump around variables
        """
        # check port for specs and create as necessary
        portFlow = self.paFeed.port.GetPropValue(MOLEFLOW_VAR)
        if portFlow:
            self.port.SetPropValue(MOLEFLOW_VAR, portFlow, CALCULATED_V)
            
        portFlow = self.paFeed.port.GetPropValue(MASSFLOW_VAR)
        if portFlow:
            self.port.SetPropValue(MASSFLOW_VAR, portFlow, CALCULATED_V)

        super(PumpAround,self).Reset()
        self.pumpToFeed = self.paFeed
        self.pumpToFeed.pumpFromDraw = self  # circular reference that needs breaking to delete
        self.pumpToFeed.Reset()
        if self.flow != None:
            self.pumpToFeed.flow = self.flow
        elif self.pumpToFeed.flow != None:
            self.flow = self.pumpToFeed.flow
            
    def NumberSpecs(self):
        """
        return the number of specs associated with this draw
        """
        numSpecs = super(PumpAround, self).NumberSpecs()
        portFlow = self.port.GetPropValue(MOLEFLOW_VAR)
        massFlow = self.port.GetPropValue(MASSFLOW_VAR)
        if portFlow == None and massFlow == None:
            # check and see if can get flow from return port
            if self.paFeed.port.GetPropValue(MOLEFLOW_VAR):
                numSpecs += 1
            else:
                portFlow = self.port.GetPropValue(MASSFLOW_VAR)
                if portFlow != None:
                    numSpecs += 1
            
        if self.stage.tower.converged == 0:
            self.userSpecs = numSpecs  # save last unconverged number
        return numSpecs
            
    def AssignResultToPort(self):
        """
        assign flow to Feed
        """
        stageNo = self.stage.number
        tower = self.stage.tower
        self.paFeed.port.SetPropValue(MOLEFLOW_VAR, self.flow, CALCULATED_V)
        self.paFeed.port.SetPropValue(P_VAR, tower.P[stageNo], CALCULATED_V)
        super(PumpAround,self).AssignResultToPort()
        if self.flow:
            hDraw = self.HDraw()
            if self.paQ.q == None:
                #tower._lastEneErrs[self.paQ.stage.number] is negative if energy is being added to the tower (heating)
                qTotal = hDraw * self.flow - tower._lastEneErrs[self.paQ.stage.number] #Non conversion needed
            else:
                #self.paQ.TotalQFlow()*3.6  is negative if energy is leaving the tower (condensing)
                qTotal = hDraw * self.flow + self.paQ.TotalQFlow()*3.6                 # note W to KJ/h conversion
            self.paFeed.port.SetPropValue(H_VAR, qTotal/self.flow, CALCULATED_V)
            
    def Clone(self):
        return self.__class__(self.destStageNo, self.isHeating)
        
class LiquidPumpAround(PumpAround, LiquidDraw):
    def __str__(self):
        return 'LiquidPADraw:' + self.name
        
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'LiquidPADraw_%d_%s' % (stageNo, self.name)

    def AssignResultToPort(self):
        """
        assign liquid mole fractions to return port and calc super class
        """
        super(LiquidPumpAround,self).AssignResultToPort()
        
        stageNo = self.stage.number
        tower = self.stage.tower
        self.paFeed.port.SetCompositionValues(tower.x[stageNo], CALCULATED_V)
    

    def HDraw(self):
        """
        return the molar enthalpy for draw fluid
        """
        stageNo = self.stage.number
        tower = self.stage.tower
        
        ##Should it handle subcooled liquid ??
        
        hmass = tower.hlModel[0][stageNo] + tower.hlModel[1][stageNo]*tower.T[stageNo]
        mw = Numeric.sum(tower.x[stageNo]*tower.mw)
        return hmass * mw
       
class VapourPumpAround(PumpAround, VapourDraw):
    def __str__(self):
        return 'LiquidPADraw:' + self.name
        
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'LiquidPADraw_%d_%s' % (stageNo, self.name)

    def AssignResultToPort(self):
        """
        assign vapour mole fractions to return port and calc super class
        """
        super(VapourPumpAround, self).AssignResultToPort()
        
        stageNo = self.stage.number
        tower = self.stage.tower
        self.paFeed.port.SetCompositionValues(tower.y[stageNo], CALCULATED_V)
    

    def HDraw(self):
        """
        return the molar enthalpy for draw fluid
        """
        stageNo = self.stage.number
        tower = self.stage.tower
        hmass = tower.hvModel[0][stageNo] + tower.hvModel[1][stageNo]*tower.T[stageNo]
        mw = Numeric.sum(tower.y[stageNo]*tower.mw)
        return hmass * mw       
    
class InternalLiquidClone(LiquidDraw):
    """port duplicating the interal liquid flow from a stage"""
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'InternalLiquid_%d_%s' % (stageNo, self.name)
    
class InternalVapourClone(VapourDraw):
    """port duplicating the internal vapour flow from a stage"""
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'InternalVapour_%d_%s' % (stageNo, self.name)
    
class WaterDraw(Draw):
    """aqueous phase draw from stage"""
    def __str__(self):
        return 'WaterDraw:' + self.name
        
    def Initialize(self, stage, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(WaterDraw,self).Initialize(stage, name)
        self.phase = TOWER_WATER_PHASE
        self.moleFlows = None
        self.damping = stage.tower.GetParameterValue(WATERDAMPING_PAR)
        if not self.damping:
            self.damping = 0.5
            stage.tower.SetParameterValue(WATERDAMPING_PAR, self.damping)
        self.convRes = {}

    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'WaterDraw_%d_%s' % (stageNo, self.name)

    def Reset(self, initMode=SCRATCH_INIT):
        """
        get damping factor
        """
        self.damping = self.stage.tower.GetParameterValue(WATERDAMPING_PAR)
        if not self.damping: self.damping = 0.5
        if not initMode: self.moleFlows = None
        
        super(WaterDraw, self).Reset()
       
    def CleanUp(self):
        self.moleFlows = None
        self.convRes = None
        super(WaterDraw,self).CleanUp()
    def InitializeKFactors(self):
        """
        do a three phase flash to get initial variables
        """
        # figure out the feed composition
        stage = self.stage
        tower = stage.tower
        stageNo = stage.number
 
        # calculate total component feed to stage
        f = zeros(tower.numCompounds, Float)
        
        # add any feeds
        stage.TotalFeed(f)
        
        # vapour from below
        if stage.type != BOTTOM_STAGE:
            f += tower.y[stageNo + 1] * tower.V[stageNo + 1]
            
        # liquid from above
        if stage.type != TOP_STAGE:
            f += tower.x[stageNo - 1] * tower.L[stageNo - 1]
            
        # pumparounds
        for s in tower.stages:
            for draw in s.vapDraws.values():
                if draw.pumpToFeed and draw.pumpToFeed.stage is stage:
                    f += tower.y[draw.stage.number] * draw.flow
                    
            for draw in s.liqDraws.values():
                if draw.pumpToFeed and draw.pumpToFeed.stage is stage:
                    f += tower.x[draw.stage.number] * draw.flow                    
        
        ###Current vapour removed
        ##vFracs = [tower.V[stageNo]]
        ##v = zeros(tower.numCompounds, Float)
        ##v += tower.y[stageNo]*vFracs[0]
        ##for draw in stage.vapDraws.values():
            ##if not draw.isBasis:
                ##vFracs.append(draw.flow)
                ##v += tower.y[stageNo]*vFracs[-1]
        ##vFracs = array(vFracs, Float)
        ##vFracs = vFracs / sum(vFracs)
                
        ###Current liquid removed
        ##lFracs = [tower.L[stageNo]]
        ##l = zeros(tower.numCompounds, Float)
        ##l += tower.x[stageNo]*lFracs[0]
        ##lItems = []
        ##for draw in stage.liqDraws.values():
            ##if not draw.isBasis:
                ##lItems.append(draw)
                ##lFracs.append(draw.flow)
                ##l += tower.x[stageNo]*lFracs[-1]
        ##lFracs = array(lFracs, Float)
        ##lFracs = lFracs / sum(lFracs)
                
        compounds = CompoundList(tower)
        for i in range(tower.numCompounds):
            prop = BasicProperty(FRAC_VAR)
            prop.SetValue(f[i])
            compounds.append(prop)
        compounds.Normalize()
        
        props = MaterialPropertyDict()
        
        #Use the subcooled T
        T = tower.T[stageNo]
        if self.isSubCooled:
            T -= self.stage.GetDegreesSubCooled()
        
        props[T_VAR].SetValue(T)
        props[P_VAR].SetValue(tower.P[stageNo])
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        results = thAdmin.Flash(prov, case, compounds, props, 2, (H_VAR, CP_VAR))
        try: self.liq1Frac = results.phaseFractions[1]/(results.phaseFractions[1]+results.phaseFractions[2])
        except: self.liq1Frac = None
        self.results = results
        
        ##This is just for testing
        #self.res1LiqPh = thAdmin.Flash(prov, case, compounds, props, 1, (H_VAR, CP_VAR))
        #T2 = T + 1.0
        #props[T_VAR].SetValue(T2)
        #self.results2 = thAdmin.Flash(prov, case, compounds, props, 2, (H_VAR, CP_VAR))
        #self.res1LiqPh2 = thAdmin.Flash(prov, case, compounds, props, 1, (H_VAR, CP_VAR))
        
        damping = self.damping
        oneMinusDamp = 1.0 - damping
        totalFeed = sum(f)
        newFlow = totalFeed * results.phaseFractions[2]
        
        try:
            self.oldFlows, self.oldFlow = array(self.moleFlows, Float), self.flow
        except:
            pass
        self.f = f
        self.totalFeed = totalFeed
        
        if newFlow == 0.0 and self.flow:
            self.flow *= oneMinusDamp
            self.moleFlows *= oneMinusDamp
            self.error = self.flow/totalFeed
            
        elif self.flow:
            self.error = abs(self.flow - newFlow) / totalFeed
            self.flow = self.flow * oneMinusDamp + newFlow * damping
            self.moleFlows = (self.moleFlows * oneMinusDamp +
                              array(results.phaseComposition[2]) * newFlow * damping)
            
            #Get properties at damped composition
            vals = thAdmin.GetProperties(prov, case, (T_VAR,T), (P_VAR, tower.P[stageNo]),
                                         LIQUID_PHASE, self.moleFlows/Numeric.sum(self.moleFlows), (H_VAR, CP_VAR))
            self.wEnthalpy = vals[0]
            self.wCp = vals[1]
            self.baseT = T
            #tower.InfoMessage('WaterInfo_Tot_Wat_HC', (self.flow, self.moleFlows[0], Numeric.sum(self.moleFlows[1:]), T, 
                                                       #newFlow, 
                                                       #(array(results.phaseComposition[2]) * newFlow)[0], 
                                                       #Numeric.sum((array(results.phaseComposition[2]) * newFlow)[1:])))
            #tower.InfoMessage('WaterInfo_Feed', (totalFeed, f[0], Numeric.sum(f[1:])))
        else:
            self.error = newFlow / totalFeed
            self.flow = newFlow
            self.moleFlows = array(results.phaseComposition[2]) * self.flow
            self.wEnthalpy = results.phaseProps[2][0]
            self.wCp = results.phaseProps[2][1]
            self.baseT = T
            
        if self.flow:
            try:
                self.x = self.moleFlows/self.flow
            except:
                self.x = self.moleFlows
        else:
            self.x = self.moleFlows
            
        ###Rebalance things
        ###lChange = f - v - l - self.moleFlows
        ###lNew = l+lChange
        ###if min(lChange + l) >= 0.0:
            ####Current Kb
            ###Kb = math.exp(tower.logSFactors[stageNo]) * tower.L[stageNo] / tower.V[stageNo]
            
            ####New L and new x
            ###tower.L[stageNo] = clip(tower.L[stageNo] + sum(lChange * lFracs[0]), tiniestValue, largestValue)
            ###tower.x[stageNo, :] = clip( lNew/sum(lNew), tiniestValue, largestValue )
            
            ####New lnS based on new L
            ###tower.logSFactors[stageNo] = math.log(Kb * tower.V[stageNo] / tower.L[stageNo])
            
            ####Update draws
            ###for i in range(len(lItems)):
                ###draw.flow = clip(draw.flow + sum(lChange * lFracs[i+1]), tiniestValue, largestValue)
            
            
        return results
    
    def QFlow(self):
        """
        return an estimate of energy flow based on stage T and stored H and Cp
        """
        if not self.flow: return 0.0
        
        tower = self.stage.tower
        stageNo = self.stage.number
        T = tower.T[stageNo]
        
        #Should it do it at subcooled T
        #Looks like yes as this is used in the energy balance
        if self.isSubCooled:
            T -= self.stage.GetDegreesSubCooled()

        hNew = self.wEnthalpy + (T - self.baseT) * self.wCp
        return hNew * self.flow
        
    def AssignResultToPort(self):
        """
        assign vapour mole fractions to port and calc super class
        """
        Draw.AssignResultToPort(self)
        
        #self.port.SetPropValue(VPFRAC_VAR, 0.0, CALCULATED_V)
        # switch back to T until prop pkg problem resolved
        stageNo = self.stage.number
        tower = self.stage.tower
        T = tower.T[stageNo]
        
        #Use the subcooled T
        if self.isSubCooled:
            T -= self.stage.GetDegreesSubCooled()
            
        self.port.SetPropValue(T_VAR, T, CALCULATED_V)
        if self.moleFlows:
            stageNo = self.stage.number
            tower = self.stage.tower
            self.port.SetCompositionValues(self.moleFlows/Numeric.sum(self.moleFlows), CALCULATED_V)

    def MoleFracs(self):
        """return the current mole fractions"""
        return self.moleFlows/Numeric.sum(self.moleFlows)

    def Error(self):
        """
        return current error
        """
        return self.error
    
    
    def StoreConvResults(self):
        """Tower just got coonverged. Store keep trck of my current results"""
        
        self.convRes = {}
        try:
            #The keys of convRes must exactly match the names of the attributes in the tower
            self.convRes['flow'] = self.flow
            self.convRes['wEnthalpy'] = self.wEnthalpy
            self.convRes['wCp'] = self.wCp
            self.convRes['baseT'] = self.baseT
            self.convRes['moleFlows'] = array(self.moleFlows, Float)
            
            return 1
                         
        except:
            #Clear everything if everythign went wrong
            self.convRes = {}
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
            
            #numCompounds is only updated if a Solve call was first made
            #Make sure this method is always called after the step where
            #Solve updates numCompounds !!
            if self.stage.tower.numCompounds != len(self.convRes['moleFlows']): return 0
            
            for key in self.convRes:
                tempDict[key] = self.__dict__[key]
                if key == 'moleFlows':
                    self.__dict__[key] = array(self.convRes[key], Float)
                else:
                    self.__dict__[key] = self.convRes[key]
                
            return 1
        
        except:
            #Put it back to what it was if it failed
            for key in tempDict:
                self.__dict__[key] = tempDict[key]
                
            return 0

    def AdjustOldCase(self, version):
        """
        fixup for older recalled versions
        """
        if version[0] < 47:
            if not hasattr(self, 'convRes'):
                self.convRes = {}
        super(WaterDraw, self).AdjustOldCase(version)
        
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        super(WaterDraw, self).CloneContents(clone)
        clone.moleFlows = copy.deepcopy(self.moleFlows)
        clone.damping = self.damping
        clone.convRes = copy.deepcopy(self.convRes)
        
        if hasattr(self, 'error'):
            clone.error = self.error
        if hasattr(self, 'wEnthalpy'):
            clone.wEnthalpy = self.wEnthalpy
        if hasattr(self, 'wCp'):
            clone.wCp = self.wCp
        if hasattr(self, 'baseT'):
            clone.baseT = self.baseT
        if hasattr(self, 'x'):
            clone.x = copy.deepcopy(self.x)
                   
        
class EnergyFeed(StageObject):
    """Energy flow to tower stage"""
    def __str__(self):
        return 'EnergyFeed:' + self.name
    
    def __init__(self, isIn=1):
        """Most init takes place in Initialize, but this give direction of port"""
        self.incoming = isIn
        self.assignedQ = None
        self.q = None
        
    def Initialize(self, stage, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - stage will call this when it is added to it
        """
        super(EnergyFeed,self).Initialize(stage, name)
        if self.incoming:
            portType = ENE|IN
        else:
            portType = ENE|OUT
            
        self.port = stage.tower.CreatePort(portType, self.TowerPortName(stage.number))

    def AddObject(self, obj, name):
        """ Do not allow change of name if it is comes from a PumpAround. Change name of pumparound instead """
        if name == 'NewName':
            #Blindly assume it comes from pumparound if the name ends with paQ
            if self.name[-4:] == "_paQ":
                self.stage.GetParent().InfoMessage('CantChangeName', (self.GetPath(),))
                return
            
        super(EnergyFeed, self).AddObject(obj, name)        
        
    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        return 'EnergyFeed_%d_%s' % (stageNo, self.name)


    def CleanUp(self):
        self.stage.tower.DeletePort(self.port)
        self.port = None
        super(EnergyFeed,self).CleanUp()
        
    def TotalQFlow(self):
        """return heat flow"""
        
        q = self.q
        if q and not self.incoming:
            q *= -1.
        
        self.assignedQ = None
        return q

    def AssignQ(self, value):
        """
        if q is unknown set assignedQ to value and return 1
        otherwise return 0
        """
        if self.q == None:
            self.assignedQ = value
            return 1
        return 0
        
    def Reset(self):
        """reset any variables from previous calculations"""
        self.q = self.port.GetValue()

    def AssignResultToPort(self):
        """
        assign energy flow to port
        """
        if self.assignedQ == None:
            return
        
        stageNo = self.stage.number
        tower = self.stage.tower
        if self.incoming:
            q = -self.assignedQ
        else:
            q = self.assignedQ
        # note conversion to W
        self.port.SetValue(q/3.6, CALCULATED_V)
        
    def WasCalculated(self):
        """
        return true if value was or will be calculated by tower
        """
        if self.assignedQ is None and self.port.GetValue(): return 0
        return 1
    def Clone(self):
        return self.__class__(self.incoming)
    
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        super(EnergyFeed, self).CloneContents(clone)
        clone.q = self.q
        clone.assignedQ = self.assignedQ
        
        
class FluidVariable(object):
    """base class for temperature and flow Estimates and Specs"""
    def __init__(self, varType):
        """type is variable type for estimate"""
        self.varType = varType

        
    def Initialize(self, parent, name):
        """save parent object and my name"""
        self.parent = parent
        if isinstance(parent, Stage):
            self.stage = parent
        else:
            self.stage = parent.stage  # should be a stage object
            
        self.name = name
        self.port = self.stage.tower.CreatePort(SIG, self.TowerPortName(self.stage.number))
        self.port.SetSignalType(self.varType)

    def TowerPortName(self, stageNo):
        """
        return the name the parent tower will use for this port
        """
        if isinstance(self, Estimate):
            return 'Estimate_%d_%s' % (stageNo, self.name)
        else:
            return 'Variable_%d_%s' % (stageNo, self.name)

    def ChangeStageNumber(self, tower, fromNumber, toNumber):
        """
        Must change port name that tower uses for this object's port - if they have one
        """
        if hasattr(self,'TowerPortName'):
            tower.RenamePort(self.TowerPortName(fromNumber), self.TowerPortName(toNumber))

    def CleanUp(self):
        self.stage.tower.DeletePort(self.port)
        self.port = None
        self.parent = None
        

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        pass  # handled by derived classes if necessary


    def GetContents(self):
        return [('Port',self.port)]
    
    def GetObject(self, name):
        if name == 'Port' or name == 'Value': return self.port
        else: return None
        
    def GetPath(self):
        """return object path to this object"""
        return '%s.%s' % (self.parent.GetPath(), self.name)
    
    def GetParent(self): return self.parent
    
    def ReadyToSolve(self):
        """assume ready if port has value"""
        self.value = self.port.GetValue()
        return self.value != None

    def Reset(self):
        """do any processing necessary before solving"""
        pass # this base class has nothing to do
    def Clone(self):
        return self.__class__(self.varType)
    
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        pass
        
        
class Estimate(FluidVariable):
    """flow or temperature estimate"""
    def __init__(self, type):
        """
        type is a variable type for units or REFLUX for a reflux spec
        """
        self.type = type
        if type == REFLUX:
            self.type = REFLUX
            type = GENERIC_VAR

        FluidVariable.__init__(self, type)
        
    def __str__(self):
        return 'Estimate:' + self.name
    
    def Clone(self):
        return self.__class__(self.type)

class StageSpecification(FluidVariable):
    """
    stage specification
    """
    def __init__(self, type, phase=''):
        """
        type is a variable type for units or REFLUX for a reflux spec
        phase is TOWER_LIQ_PHASE, TOWER_VAP_PHASE or TOWER_WATER_PHASE or just empty if phase
        is not relevant
        """
        
        self.type = type
        self.phase = phase
        self.spec = None
        if type == REFLUX or type == REBOIL:
            self.type = type
            type = GENERIC_VAR
            
        super(StageSpecification,self).__init__(type)

    def __str__(self):
        return 'Specification:' + self.name

    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        
        parent = self.parent
        tower = parent.tower
        stageNo = parent.number
        
        if self.type == T_VAR:
            T = tower.T[stageNo]
            if parent.IsSubCooled():
                T -= parent.GetDegreesSubCooled()
            return T
        
        if self.type == REFLUX: 
            draw = parent.TotalDrawFlow()
            return tower.L[stageNo]/draw
        
        if self.type == REBOIL: 
            draw = parent.TotalDrawFlow()
            return tower.V[stageNo]/draw
        
        if self.type == MOLEFLOW_VAR:
            if self.phase == TOWER_LIQ_PHASE:
                return tower.L[stageNo]
            elif self.phase == TOWER_VAP_PHASE:
                return tower.V[stageNo]
            else:
                raise SimError('InvalidTowerSpecPhase', (stageNo, tower.GetPath()))
    
    def AssignResultsToPort(self):
        """Would get called if spec was not active, then put the newly calculated value"""
        value = self.GetCurrentTowerValue()
        self.port.SetValue(value, CALCULATED_V)
    
    def Reset(self):
        """check that there is a value - cache it"""
        self.spec = self.port.GetValue()
        super(StageSpecification,self).Reset()
    
    def Error(self):
        """Calculate error"""
        
        value = self.GetCurrentTowerValue()
        
        if self.type == T_VAR:
            return (self.spec - value)/ 500.0
        
        if self.type == REFLUX or self.type == REBOIL:
            return self.spec - value
        
        tower = self.parent.tower
        stageNo = self.parent.number
        if self.type == MOLEFLOW_VAR:
            if self.phase == TOWER_LIQ_PHASE:
                return (self.spec - value)/tower.totalFeedFlow
            elif self.phase == TOWER_VAP_PHASE:
                return (self.spec - value)/tower.totalFeedFlow
            else:
                raise SimError('InvalidTowerSpecPhase', (stageNo, tower.GetPath()))            
        

    def Clone(self):
        return self.__class__(self.type, self.phase)
            
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        super(StageSpecification, self).CloneContents(clone)
        clone.spec = self.spec
    
class RefluxRatioSpec(StageSpecification):
    """reflux ratio spec for a stage L/totaldraw"""
    def __init__(self):
        super(RefluxRatioSpec, self).__init__(REFLUX)
    def __str__(self):
        return 'Reflux Spec:' + self.name
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        parent = self.parent
        draw = parent.TotalDrawFlow()
        return parent.tower.L[parent.number]/draw
    
    def Error(self):
        """Calculate error"""
        value = self.GetCurrentTowerValue()    
        return self.spec - value
    
    def Clone(self):
        return self.__class__()
    
class ReboilRatioSpec(StageSpecification):
    """reboil ratio spec for a stage V/totaldraw"""
    def __init__(self):
        super(ReboilRatioSpec, self).__init__(REBOIL)
    def __str__(self):
        return 'Reboil Spec:' + self.name
    
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        parent = self.parent
        draw = parent.TotalDrawFlow()
        return parent.tower.V[parent.number]/draw

    def Error(self):
        """Calculate error"""
        value = self.GetCurrentTowerValue()    
        return self.spec - value
    
    
    def Clone(self):
        return self.__class__()
    
class DrawSpec(FluidVariable):
    """
    spec that can be assigned to a draw - will be derived from
    """
    def __init__(self, varType):
        super(DrawSpec, self).__init__(varType)

    def AssignResultsToPort(self):
        """Would get called if spec was not active, then put the newly calculated value"""
        value = self.GetCurrentTowerValue()
        self.port.SetValue(value, CALCULATED_V)        
        
class ComponentSpec(DrawSpec):
    """
    parent class for specifications involving components
    """
    def __init__(self, varType):
        """
        varType is passed to super class to initialize the signal port type
        """
        self.components = []
        super(ComponentSpec, self).__init__(varType)
        self.spec = None

    def GetObject(self,name):
        if name == 'Components':
            return self.components
        else:
            return super(ComponentSpec, self).GetObject(name)
        
    def Add(self, description):
        """
        the description should be a space delimited list of components
        that will be added to the list of components to be summed for the spec
        """
        cmps = re.split(r'[\s,]', description)
        tower = self.parent.stage.tower
        cmpNames = tower.GetCompoundNames()
        for cmp in cmps:
            if cmp:
                cmpName = re.sub('_', ' ', cmp)  # let underscores stand for spaces
                if not cmpName in cmpNames:
                    #Keep the name the way it was orginally
                    cmpName = cmp.strip()
                self.components.append(cmpName)
                
        #If converged it would be cool to just put the value in place, 
        #but unfortunately it needs a recalc
        tower.converged = 0
        tower.ForgetAllCalculations()
        
                
    def Minus(self, description):
        """
        the description should be a space delimited list of components
        that will be removed from the list of components to be summed for the spec
        """
        cmps = re.split(r'[\s,]', description)
        tower = self.parent.stage.tower
        cmpNames = tower.GetCompoundNames()
        for cmp in cmps:
            if cmp:
                cmpName = re.sub('_', ' ', cmp)  # let underscores stand for spaces
                try:
                    if not cmpName in cmpNames:
                        #Keep the name the way it was orginally
                        cmpName = cmp.strip()
                    self.components.remove(cmpName)
                except ValueError:
                    pass   # just ignore if not already in list
                
        #If converged, then just put the value in place
        tower.converged = 0
        tower.ForgetAllCalculations()
            
        
    def Reset(self):
        """
        get component list positions for components
        before actual solution
        """
        self.compNo = []
        compoundNames = self.stage.tower.GetCompoundNames()
        for cmpName in self.components:
            self.compNo.append(compoundNames.index(cmpName))

    def Clone(self):
        clone = self.__class__(self.varType)
        clone.components = copy.deepcopy(self.components)
        return clone
    
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        super(ComponentSpec, self).CloneContents(clone)
        if hasattr(self, 'compNo'):
            clone.compNo = copy.deepcopy(self.compNo)
    
class MoleFractionSpec(ComponentSpec):
    """
    specify the sum of the mole fractions for one or more components
    """
    def __init__(self):
        super(MoleFractionSpec,self).__init__(FRAC_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        sum = 0.0
        moleFracs = self.parent.MoleFracs()
        for cmpNo in self.compNo:
            sum += moleFracs[cmpNo]
        return sum
    
    def Error(self):
        value = self.GetCurrentTowerValue()
        return value - self.value
    
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
    
class VolFractionSpec(ComponentSpec):
    """
    specify the sum of the mole fractions for one or more components
    """
    def __init__(self):
        super(VolFractionSpec,self).__init__(FRAC_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""        
        sum = 0.0
        fracs = self.parent.VolumeFracs()
        for cmpNo in self.compNo:
            sum += fracs[cmpNo]
        return sum
            
    def Error(self):
        value = self.GetCurrentTowerValue()
        return value - self.value
    
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
class MassFractionSpec(ComponentSpec):
    """
    specify the sum of the mole fractions for one or more components
    """
    def __init__(self):
        super(MassFractionSpec,self).__init__(FRAC_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        sum = 0.0
        fracs = self.parent.MassFracs()
        for cmpNo in self.compNo:
            sum += fracs[cmpNo]
        return sum
            
    def Error(self):
        value = self.GetCurrentTowerValue()
        return value - self.value
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
class ComponentMoleFlowSpec(ComponentSpec):
    """
    specify the sum of the molar flows for one or more components
    """
    def __init__(self):
        super(ComponentMoleFlowSpec,self).__init__(MOLEFLOW_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        sum = 0.0
        moleFracs = self.parent.MoleFracs()
        for cmpNo in self.compNo:
            sum += moleFracs[cmpNo]
        return sum * self.parent.flow
    
    def Error(self):
        value = self.GetCurrentTowerValue()
        return value - self.value
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
class ComponentMassFlowSpec(ComponentSpec):
    """
    specify the sum of the mass flows for one or more components
    """
    def __init__(self):
        super(ComponentMassFlowSpec,self).__init__(MASSFLOW_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""        
        sum = 0.0
        massFracs = self.parent.MassFracs()
        massFlow = self.parent.MassFlow()
        for cmpNo in self.compNo:
            sum += massFracs[cmpNo]
        return sum * massFlow
    
    def Error(self):
        value = self.GetCurrentTowerValue()
        return value - self.value
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
class ComponentStdVolFlowSpec(ComponentSpec):
    """
    specify the sum of the std vol flows for one or more components
    """
    def __init__(self):
        super(ComponentStdVolFlowSpec,self).__init__(STDVOLFLOW_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""  
        
        sum = 0.0
        volFracs = self.parent.VolumeFracs()
        stdVolFlow = self.parent.StdVolumeFlow()
        for cmpNo in self.compNo:
            sum += volFracs[cmpNo]
        return sum * stdVolFlow
    
    
    def Error(self):
        value = self.GetCurrentTowerValue()
        return value - self.value    
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
class MoleRecoverySpec(ComponentSpec):
    """
    specify the sum of the molar flows for one or more components, divided
    by the total feed to the tower for those components
    """
    def __init__(self):
        super(MoleRecoverySpec, self).__init__(FRAC_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        sum = 0.0
        moleFracs = self.parent.MoleFracs()
        feeds = Numeric.sum(self.stage.tower.f, 0)
        sumF = 0.0
        for cmpNo in self.compNo:
            sum += moleFracs[cmpNo]
            sumF += feeds[cmpNo]
        if not sumF:
            return None
        return (sum * self.parent.flow) / sumF
    
    def Error(self):
        value = self.GetCurrentTowerValue()
        if value == None:
            return 1.0    #Just return an error
        return value - self.value
    
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
class MassRecoverySpec(ComponentSpec):
    """
    specify the sum of the mass flows for one or more components, divided
    by the total feed to the tower for those components
    """
    def __init__(self):
        super(MassRecoverySpec, self).__init__(FRAC_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""        
        sum = 0.0
        moleFracs = self.parent.MoleFracs()
        feeds = Numeric.sum(self.stage.tower.f, 0)
        sumF = 0.0
        flow = self.parent.flow
        tower = self.stage.tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        for cmpNo in self.compNo:
            cmpMwt = thAdmin.GetSelectedCompoundProperties(prov, case, cmpNo, 'MolecularWeight')[0]
            sum += moleFracs[cmpNo] * flow * cmpMwt
            sumF += feeds[cmpNo] * cmpMwt
        if not sumF:
            return None
        return sum / sumF
    
    
    def Error(self):
        value = self.GetCurrentTowerValue()
        if value == None:
            return 1.0    #Just return an error
        return value - self.value
    
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
class StdVolRecoverySpec(ComponentSpec):
    """
    specify the sum of the liq std vol flows for one or more components, divided
    by the total feed to the tower for those components
    """
    def __init__(self):
        super(StdVolRecoverySpec, self).__init__(FRAC_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""        
        
        parent = self.parent
        tower = self.stage.tower
        
        volFracs = parent.VolumeFracs()
        stdVolFlow = parent.StdVolumeFlow()   #m3/h
        
        feeds = Numeric.sum(tower.f, 0)       #kmole/h per compound
        totFeedFlow = Numeric.sum(feeds)      #kmole/h
        feedsMoleFracs = feeds/totFeedFlow
        
        
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        
        refT = tower.GetStdVolRefT()
        feedStdMolVol = thAdmin.GetProperties(prov, case, (T_VAR,refT), (P_VAR, 101.325), 
                                              LIQUID_PHASE, feedsMoleFracs, (STDLIQVOL_VAR,))[0]
        feedVolFracs = thAdmin.GetArrayProperty(prov, case, (T_VAR, 0.0), (P_VAR, 0.0),
                                                LIQUID_PHASE, feedsMoleFracs, 'IdealVolumeFraction')
        feedStdVolFlow = totFeedFlow*feedStdMolVol    #m3/h = kmole/h * m3/kmole
        
        sum = 0.0
        sumF = 0.0
        for cmpNo in self.compNo:
            sum += volFracs[cmpNo] * stdVolFlow
            sumF += feedVolFracs[cmpNo] * feedStdVolFlow
        if not sumF:
            return None
        return sum / sumF
    
    
    def Error(self):
        value = self.GetCurrentTowerValue()
        if value == None:
            return 1.0    #Just return an error
        return value - self.value
    
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    
class MoleRatioSpec(ComponentSpec):
    """
    ratio of component mole fractions
    this is entered by having a component name '/' separating
    the numerator and denominator components
    i.e. spec + PROPANE / ISOBUTANE for the command interface
    """
    def __init__(self):
        super(MoleRatioSpec,self).__init__(FRAC_VAR)
        
    def Reset(self):
        """
        get component list positions for components
        before actual solution
        use '/' as numerator - denominator separator
        """
        self.compNo = []
        self.denomNo = []
        compoundNames = self.stage.tower.GetCompoundNames()
        addTo = self.compNo
        for cmpName in self.components:
            if cmpName == '/':
                addTo = self.denomNo
            else:
                addTo.append(compoundNames.index(cmpName))

    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""                        
        sumNumerator  = 0.0
        sumDenominator = 0.0
        
        moleFracs = self.parent.MoleFracs()
        for cmpNo in self.compNo:
            sumNumerator += moleFracs[cmpNo]
            
        for cmpNo in self.denomNo:
            sumDenominator += moleFracs[cmpNo]                
        
        if sumDenominator:
            return sumNumerator/sumDenominator
        else:
            return None
        
    def Error(self):
        value = self.GetCurrentTowerValue()
        if value != None:
            return value/self.value - 1.0
        
        return 1.0  # just an error rather than return none
    def Clone(self):
        clone = self.__class__()
        clone.components = copy.deepcopy(self.components)
        return clone
    def CloneContents(self, clone):
        """Clone the contents of this object into the object being passed in. 
        A CloneContents call is needed instead of a Clone call because the object needs to be fully installed
        on the tower before it can be set up"""
        super(MoleRatioSpec, self).CloneContents(clone)
        if hasattr(self, 'denomNo'):
            clone.denomNo = copy.deepcopy(self.denomNo)
        
class MassRatioSpec(MoleRatioSpec):
    """
    same as MoleRatioSpec, but based on mass fractions
    """
    
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""    
        sumNumerator  = 0.0
        sumDenominator = 0.0
        
        massFracs = self.parent.MassFracs()
        for cmpNo in self.compNo:
            sumNumerator += massFracs[cmpNo]
            
        for cmpNo in self.denomNo:
            sumDenominator += massFracs[cmpNo]
            
        if sumDenominator:
            return sumNumerator/sumDenominator
        else:
            return None
        
class StdVolRatioSpec(MoleRatioSpec):
    """
    same as MoleRatioSpec, but based on mass fractions
    """
    
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""    
        sumNumerator  = 0.0
        sumDenominator = 0.0
        
        volFracs = self.parent.VolumeFracs()
        for cmpNo in self.compNo:
            sumNumerator += volFracs[cmpNo]
            
        for cmpNo in self.denomNo:
            sumDenominator += volFracs[cmpNo]
            
        if sumDenominator:
            return sumNumerator/sumDenominator
        else:
            return None


class PropertySpec(DrawSpec):
    """
    specification of a specific property on a draw
    """
    def __init__(self, propName):
        """propName is the name of the property to be specified"""
        super(PropertySpec,self).__init__(propName)
        self.propName = propName
        self.scaleFactor = PropTypes[propName].scaleFactor
        if not self.scaleFactor:
            self.scaleFactor = 1.0
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        parent = self.parent
        tower = parent.stage.tower
        stageNo = parent.stage.number
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        moleFracs = parent.MoleFracs()
        t = tower.T[stageNo]
        if parent.isSubCooled:
            t -= parent.stage.GetDegreesSubCooled()
        p = tower.P[stageNo]
        if parent.phase == TOWER_VAP_PHASE:
            phase = VAPOUR_PHASE
        else:
            phase = LIQUID_PHASE
        propValue = thAdmin.GetProperties(prov, case, (T_VAR,t), (P_VAR, p), phase,
                                          moleFracs, (self.propName,))[0]
        return propValue
        
    def Error(self):
        value = self.GetCurrentTowerValue()
        return (value - self.value)/self.scaleFactor
        
    def Clone(self):
        clone = self.__class__(self.propName)
        clone.scaleFactor = self.scaleFactor
        return clone
    
class SpecialPropertySpec(DrawSpec):
    """
    specification of a special specific property on a draw
    """

    def __init__(self, propName):
        """propName is the name of the property to be specified"""
        
        #check first if it exists
        #The unit operation Properties has all this info stored in constants
        if not propName in Properties.SPECIAL_PROPS:
            raise SimError('CantCreateSpec', (propName,))
        
        #This line loads self.varType = propName which is wrong !!
        #This problem if fixed in following lines !!
        super(SpecialPropertySpec, self).__init__(propName)
        
        self.propName = propName

        #Variables to recognize the type of var
        self.callType = ""
        self.callName = propName  #Default
        self.callIdx = None
        
        #Fix for self.varType so the signal port gets created properly
        #IMPORTANT so the port gets created with the right type!!
        idx = Properties.SPECIAL_PROPS.index(propName)
        self.varType = Properties.SPECIAL_PROP_TYPES[idx]
        self.scaleFactor = PropTypes[self.varType].scaleFactor
        if not self.scaleFactor:
            self.scaleFactor = 1.0
        
        #Bunch of if statements to know what and how to request before hand
        if propName in (BUBBLEPOINT_VAR, DEWPOINT_VAR, WATERDEWPOINT_VAR, CO2VSE_VAR, CO2LSE_VAR, HVAPCTEP_VAR):
            self.callType = P_VAR

        elif propName in (BUBBLEPRESSURE_VAR, HVAPCTET_VAR):
            self.callType = T_VAR
            
        elif propName in (Properties.KINEMATICVISCOSITY_VAR, Properties.DYNAMICVISCOSITY_VAR):
            #This is always gotten in a pair, so dissect the info
            self.callType = T_VAR
            self.callName = LIQUIDVISCOSITY_VAR
            if propName == KINEMATICVISCOSITY_VAR: self.callIdx = 0
            else: self.callIdx = 1

        elif propName in (Properties.PARAFFIN_VAR, Properties.NAPHTHENE_VAR, Properties.AROMATIC_VAR):
            #This var is always gotten in three, so dissect the info
            self.callType = ""
            self.callName = PNA_VAR
            
            if propName == PARAFFIN_VAR: 
                self.callIdx = 0
            elif propName == NAPHTHENE_VAR: 
                self.callIdx = 1
            else: 
                self.callIdx = 2
        elif propName == JT_VAR:
            self.callType == P_VAR + '_' + T_VAR
        else:
            #The resto only depend on  composition
            self.callType = ""
            
            
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        parent = self.parent
        tower = parent.stage.tower
        stageNo = parent.stage.number
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        moleFracs = self.parent.MoleFracs()
        prop = ""
        if self.callType == P_VAR:
            prop = tower.P[stageNo]
        elif self.callType == T_VAR:
            prop = tower.T[stageNo]
            if parent.isSubCooled:
                prop -= parent.stage.GetDegreesSubCooled()
        elif self.callType == P_VAR + '_' + T_VAR:
            prop = (tower.T[stageNo], tower.P[stageNo])
            
        propValue, status = thAdmin.GetSpecialProperty(prov, case, prop, moleFracs, self.callName)
        
        try:
            #See if the answer came in indexes
            if self.callIdx != None:
                propValue = propValue.split()[self.callIdx]
                
            #Value comes as a string
            propValue = float(propValue)  
        except:
            propValue = None
            tower.InfoMessage('ErrSpecialProp', (self.GetPath(), status))
        return propValue

    
    def Error(self):
        value = self.GetCurrentTowerValue()
        if value == None: return 1.0
        return (value - self.value)/self.scaleFactor

    
    def Clone(self):
        clone = self.__class__(self.propName)
        clone.scaleFactor = self.scaleFactor
        return clone
    
class PropertySpecWithSettings(DrawSpec):
    """This spec is used for properties that require a number of settings.
    the settings depend on the property being used and on how they are handled by the thermo provider"""
    
    def __init__(self, propName):
        """Basic initialization of the property"""
        self.settings = {}
        self.settingsStr = ""
        self.propName = propName
        self.validCurves = [Properties.TBP_OPT, Properties.D86_OPT, Properties.D2887_OPT,
                            Properties.EFV_OPT, Properties.D1160_OPT, Properties.D1160Vac_OPT]
        
        if propName != CUTTEMPERATURE_VAR and propName != GAPTEMPERATURE_VAR:
            #support only CUTTEMPERATURE for now
            raise SimError('CantCreateSpec', (propName,))
        
        else:
            #Keep in the if statement to point out that this 
            #only applies for the CUTTEMPERATURE
        
            #This line loads self.varType = propName which is wrong !!
            #This problem if fixed in following lines !!
            super(PropertySpecWithSettings, self).__init__(propName)
            
            #Fix for self.varType so the signal port gets created properly
            #IMPORTANT so the port gets created with the right type!!
            self.varType = self.GetVarType()
            self.scaleFactor = PropTypes[self.varType].scaleFactor
            if not self.scaleFactor:
                self.scaleFactor = 100.0
        
            self.InitializeSettings()
            
    def GetVarType(self):
        """Defines the type associated with the prop name"""
        #Only T is used for now
        if self.propName == CUTTEMPERATURE_VAR:
            return T_VAR
        elif self.propName == GAPTEMPERATURE_VAR:
            return DELTAT_VAR
        
    def GetRequiredSettings(self):
        """Returns a list with the names of the required settings"""
        if self.propName == CUTTEMPERATURE_VAR:
            return ['CurveType', 'CutValue']
        elif self.propName == GAPTEMPERATURE_VAR:
            return ['CurveType', 'LowerValue', 'HigherValue']
        
    def InitializeSettings(self):
        """Define the names of the required settings and put some defaults"""
        
        if self.propName == CUTTEMPERATURE_VAR:
            s0 = self.settings['CurveType'] = SpecSetting(self, 'CurveType')
            s0.SetValue(Properties.TBP_OPT)
            
            s1 = self.settings['CutValue'] = SpecSetting(self, 'CutValue')
            s1.SetValue(95.0)
            
            self.settingsStr = '%s %s' %(s0.GetValue(), s1.GetValue())
    
        elif self.propName == GAPTEMPERATURE_VAR:
            s0 = self.settings['CurveType'] = SpecSetting(self, 'CurveType')
            s0.SetValue(Properties.D86_OPT)
            
            s1 = self.settings['LowerValue'] = SpecSetting(self, 'LowerValue')
            s1.SetValue(5.0)
            
            s2 = self.settings['HigherValue'] = SpecSetting(self, 'HigherValue')
            s2.SetValue(95.0)
            
            self.settingsStr = '%s %s %s' %(s0.GetValue(), s1.GetValue(), s2.GetValue())
    
    def GetObject(self, name):
        if name in self.settings.keys():
            return self.settings[name]
        elif name == 'RequiredSettings':
            return self.GetRequiredSettings()
        else:
            return super(PropertySpecWithSettings, self).GetObject(name)    
        
        
    def ReadyToSolve(self):
        """assume ready if port has value and if settings are known"""
        retVal = super(PropertySpecWithSettings, self).ReadyToSolve()
        
        try:
            
            #Rigorous validation for this property
            if self.propName == CUTTEMPERATURE_VAR:
                s0 = self.settings['CurveType']
                s1 = self.settings['CutValue']
                self.settingsStr = ''
                if s0.GetValue() not in self.validCurves:
                    tower = self.parent.stage.tower
                    tower.InfoMessage('WrongSetting', (str(s0.GetValue()), s0.GetName(), self.GetPath()))
                    retVal = False
                if s1.GetValue() < 0.0 or s1.GetValue() > 100.0:
                    tower = self.parent.stage.tower
                    tower.InfoMessage('WrongSetting', (str(s1.GetValue())+'%', s1.GetName(), self.GetPath()))
                    retVal = False
                self.settingsStr = '%s %s' %(s0.GetValue(), s1.GetValue())
                
            elif self.propName == GAPTEMPERATURE_VAR:
                s0 = self.settings['CurveType']
                s1 = self.settings['LowerValue']
                s2 = self.settings['HigherValue']
                self.settingsStr = ''
                s0Val = s0.GetValue()
                s1Val = s1.GetValue()
                s2Val = s2.GetValue()
                if s0Val not in self.validCurves:
                    tower = self.parent.stage.tower
                    tower.InfoMessage('WrongSetting', (str(s0Val), s0.GetName(), self.GetPath()))
                    retVal = False
                if s1Val < 0.0 or s1Val > 100.0:
                    tower = self.parent.stage.tower
                    tower.InfoMessage('WrongSetting', (str(s1Val)+'%', s1.GetName(), self.GetPath()))
                    retVal = False
                if s2Val < 0.0 or s2Val > 100.0 or s1Val >= s2Val:
                    tower = self.parent.stage.tower
                    tower.InfoMessage('WrongSetting', (str(s2Val)+'%', s2.GetName(), self.GetPath()))
                    retVal = False
                self.settingsStr = '%s %s %s' %(s0Val, s1Val, s2Val)
                
        except:
            return False
            
        return retVal
    
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        tower = self.parent.stage.tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        moleFracs = self.parent.MoleFracs()
            
        propValue, status = thAdmin.GetSpecialProperty(prov, case, self.settingsStr, moleFracs, self.propName)
            
        #Value comes as a string
        try:
            propValue = float(propValue)
        except:
            propValue = None
            tower.InfoMessage('ErrSpecialProp', (self.GetPath(), status))
        
        return propValue
    
    def Error(self):
        value = self.GetCurrentTowerValue()
        if value == None: return 1.0
        return (value - self.value)/self.scaleFactor
    
    def CleanUp(self):
        for setting in self.settings.values():
            setting.CleanUp()
        self.settings = None
        super(PropertySpecWithSettings, self).CleanUp()
    
    def Clone(self):
        clone = self.__class__(self.propName)
        for name, obj in self.settings.items():
            clone.settings[name] = SpecSetting(clone, name)
            clone.settings[name].SetValue(obj.GetValue())
        clone.settingsStr = copy.deepcopy(self.settingsStr)
        
        return clone
    
class SpecSetting(object):
    """Wrapper object for a setting of a spec in PropertySpecWithSettings"""
    def __init__(self, spec, name):
        self.parent = spec
        self.name = name
        self.value = None
        
    def __str__(self):
        return str(self.value)
        
    def GetPath(self):
        return '%s.%s' %(self.parent.GetPath(), self.name)
    
    def GetName(self):
        return self.name
    
    def GetParent(self):
        return self.parent
    
    def GetValue(self):
        return self.value
    
    def SetValue(self, value, calcStatus=None): #calcStatus is not used
        self.value = value
    
    def GetObject(self, desc):
        if desc == 'Value':
            return self.GetValue()
        
    def CleanUp(self):
        self.parent = None

class PumpAroundReturnPropSpec(PropertySpec):
    """
    spec that can be assigned to a draw.
    this is just like a draw spec but it grabs values from the feed port instead
    """
    def __init__(self, varType):
        super(PumpAroundReturnPropSpec, self).__init__(varType)
        self.model = None
        
        
    def AdjustOldCase(self, version):
        super(PumpAroundReturnPropSpec, self).AdjustOldCase(version)
        if not hasattr(self, 'model'):
            self.model = None
        
    def ReadyToSolve(self):
        """Clear the model if this is not an active spec"""
        retVal = super(PumpAroundReturnPropSpec, self).ReadyToSolve()
        if not retVal:
            self.ClearModel()
        return retVal
    
    def ClearModel(self):
        self.model = None
            
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""

        parent = self.parent
        tower = parent.stage.tower
        stageNo = parent.stage.number
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        
        hDraw = parent.HDraw()
        if parent.paQ.q == None:
            qTotal = hDraw * parent.flow - tower._lastEneErrs[parent.paQ.stage.number]  #Non conversion needed
        else:     
            qTotal = hDraw * parent.flow + parent.paQ.TotalQFlow()*3.6                  # note W to KJ/h conversion
        h = qTotal/parent.flow
        p = tower.P[stageNo]
        moleFracs = parent.MoleFracs()
        
        if self.model:
            try:
                propValue = self.PropertyFromModel(h, p, moleFracs)
                #phase = OVERALL_PHASE
                #validateValue = thAdmin.GetProperties(prov, case, (H_VAR,h), (P_VAR, p), phase, moleFracs, (T_VAR,))[0]
                #tower.InfoMessage('SpecWithModelErr', (str(propValue-validateValue,)))
                if propValue != None:
                    return propValue
            except:
                pass
        
        phase = OVERALL_PHASE
        propValue = thAdmin.GetProperties(prov, case, (H_VAR,h), (P_VAR, p), phase,
                                          moleFracs, (self.propName,))[0]
        
        return propValue        
    def Clone(self):
        clone = super(PumpAroundReturnPropSpec, self).Clone()
        clone.model = copy.deepcopy(self.model)
        return clone
    
class PumpAroundReturnTSpec(PumpAroundReturnPropSpec):
    def __init__(self):
        super(PumpAroundReturnTSpec, self).__init__(T_VAR)
        
    def InitModel(self):
        try:
            self.model = None
            parent = self.parent
            tower = parent.stage.tower
            stageNo = parent.stage.number
            thCaseObj = tower.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            
            hDraw = parent.HDraw()
            if parent.paQ.q == None:  #This needs to be fixed
                qTotal = hDraw * parent.flow - tower._lastEneErrs[parent.paQ.stage.number]  #Non conversion needed
            else:     
                qTotal = hDraw * parent.flow + parent.paQ.TotalQFlow()*3.6                  # note W to KJ/h conversion
            h = qTotal/parent.flow
            p = tower.P[stageNo]
            moleFracs = parent.MoleFracs()
            
            phase = OVERALL_PHASE
            value = thAdmin.GetProperties(prov, case, (H_VAR,h), (P_VAR, p), phase,
                                              moleFracs, (T_VAR, 'Cp', 'MolecularWeight'))
            
            hMass = h/value[2]   # make enthalpy on mass basis
            value[1] /= value[2]   # make Cp on mass basis
    
            value[0] = hMass - value[1]*value[0] #convert H to A term (B is just Cp)
            self.model = value
        except:
            self.model = None
        
    def PropertyFromModel(self, h, p, x):
        if not self.model: return None
        mw = self.parent.stage.tower.mw
        mw = add.reduce(x*mw)
        hMass = h/mw
        return (hMass - self.model[0]) / self.model[1]
                
    
class PumpAroundDTSpec(PumpAroundReturnPropSpec):
    def __init__(self):
        super(PumpAroundDTSpec, self).__init__(DELTAT_VAR)
        
    def GetCurrentTowerValue(self):
        """Gets the value based in the current values kept in the tower arrays"""
        parent = self.parent
        tower = parent.stage.tower
        stageNo = parent.stage.number
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        
        hDraw = parent.HDraw()
        if parent.paQ.q == None:
            qTotal = hDraw * parent.flow - tower._lastEneErrs[parent.paQ.stage.number]  #Non conversion needed
        else:     
            qTotal = hDraw * parent.flow + parent.paQ.TotalQFlow()*3.6                  # note W to KJ/h conversion
        h = qTotal/parent.flow
        p = tower.P[stageNo]
        moleFracs = parent.MoleFracs()
        
        try:
            propValue = self.PropertyFromModel(h, p, moleFracs)
            if propValue != None:
                #phase = OVERALL_PHASE
                #validateValue = thAdmin.GetProperties(prov, case, (H_VAR,h), (P_VAR, p), phase, moleFracs, (T_VAR,))[0]
                #validateValue = tower.T[stageNo] - validateValue
                #tower.InfoMessage('SpecWithModelErr', (str(propValue-validateValue,)))
                return propValue
        except:
            pass
    
        phase = OVERALL_PHASE
        propValue = thAdmin.GetProperties(prov, case, (H_VAR,h), (P_VAR, p), phase, moleFracs, (T_VAR,))[0]
        
        return tower.T[stageNo] - propValue
        
    def InitModel(self):
        try:
            self.model = None
            parent = self.parent
            tower = parent.stage.tower
            stageNo = parent.stage.number
            thCaseObj = tower.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            
            hDraw = parent.HDraw()
            if parent.paQ.q == None:  #This needs to be fixed
                qTotal = hDraw * parent.flow - tower._lastEneErrs[parent.paQ.stage.number]  #Non conversion needed
            else:     
                qTotal = hDraw * parent.flow + parent.paQ.TotalQFlow()*3.6                  # note W to KJ/h conversion
            h = qTotal/parent.flow
            p = tower.P[stageNo]
            moleFracs = parent.MoleFracs()
            
            phase = OVERALL_PHASE
            value = thAdmin.GetProperties(prov, case, (H_VAR,h), (P_VAR, p), phase,
                                              moleFracs, (T_VAR, 'Cp', 'MolecularWeight'))
            
            hMass = h/value[2]   # make enthalpy on mass basis
            value[1] /= value[2]   # make Cp on mass basis
    
            value[0] = hMass - value[1]*value[0] #convert H to A term (B is just Cp)
            self.model = value
        except:
            self.model = None
        
    def PropertyFromModel(self, h, p, x):
        if not self.model: return None
        mw = self.parent.stage.tower.mw
        mw = add.reduce(x*mw)
        hMass = h/mw
        t = (hMass - self.model[0]) / self.model[1]
        stage = self.parent.stage
        tower = stage.tower
        return tower.T[stage.number] - t
            
    
class PortDrawMoleFlowSpec(object):
    """Molar flow specification - created by tower itself from output port values"""
    def __init__(self, draw, flow, port):
        """
        draw is the draw object for this spec
        flow is the mole flow specification
        port is the port containing the spec - used to determine if spec still valid
        """
        self.draw = draw
        self.flow = flow
        self.port = port

    def CleanUp(self):
        self.draw = None
        self.port = None
        
    def SpecValue(self):
        """
        return the spec value - mainly to determine if still known
        """
        return self.port.GetPropValue(MOLEFLOW_VAR)
        
    def Error(self):
        """calculate error in spec"""
        error = self.draw.flow - self.flow
        error /= self.draw.stage.tower.totalFeedFlow
        return error

class PortDrawMassFlowSpec(object):
    """Molar flow specification - created by tower itself from output port values"""
    def __init__(self, draw, flow, port):
        """
        draw is the draw object for this spec
        flow is the mole flow specification
        port is the port containing the spec - used to determine if spec still valid
        """
        self.draw = draw
        self.flow = flow
        self.port = port

    def CleanUp(self):
        self.draw = None
        self.port = None
        
    def SpecValue(self):
        """
        return the spec value - mainly to determine if still known
        """
        return self.port.GetPropValue(MASSFLOW_VAR)
        
    def Error(self):
        """calculate error in spec"""
        error = self.draw.MassFlow() - self.flow
        # when scaling, just use 100 as rough average mole weight
        error /= self.draw.stage.tower.totalFeedFlow * 100.
        return error
    
class PortDrawVolFlowSpec(object):
    """Vol flow specification - created by tower itself from output port values"""
    def __init__(self, draw, flow, port):
        """
        draw is the draw object for this spec
        flow is the mole flow specification
        port is the port containing the spec - used to determine if spec still valid
        """
        self.draw = draw
        self.flow = flow
        self.port = port

    def CleanUp(self):
        self.draw = None
        self.port = None        
        
    def SpecValue(self):
        """
        return the spec value - mainly to determine if still known
        """
        return self.port.GetPropValue(VOLFLOW_VAR)
        
    def Error(self):
        """calculate error in spec"""
        error = self.draw.VolumeFlow() - self.flow
        # lets use just scale with respect to the known spec
        error /= 100.0
        return error
    
class PortDrawStdVolFlowSpec(object):
    """Vol flow specification - created by tower itself from output port values"""
    def __init__(self, draw, flow, port):
        """
        draw is the draw object for this spec
        flow is the mole flow specification
        port is the port containing the spec - used to determine if spec still valid
        """
        self.draw = draw
        self.flow = flow
        self.port = port

    def CleanUp(self):
        self.draw = None
        self.port = None        
        
    def SpecValue(self):
        """
        return the spec value - mainly to determine if still known
        """
        return self.port.GetPropValue(STDVOLFLOW_VAR)
        
    def Error(self):
        """calculate error in spec"""
        error = self.draw.StdVolumeFlow() - self.flow
        # lets use just scale with respect to the known spec
        error /= max(self.flow, 1.0)
        return error     
    
class PortTemperatureSpec(object):
    """Temperature specification - created by tower itself from output port values"""
    def __init__(self, draw, temperature, port):
        """
        draw is the draw object for this spec
        flow is the mole flow specification
        port is the port containing the spec - used to determine if spec still valid
        """
        self.draw = draw
        self.temperature = temperature
        self.port = port

    def CleanUp(self):
        self.draw = None
        self.port = None
        
    def SpecValue(self):
        """
        return the spec value - mainly to determine if still known
        """
        return self.port.GetPropValue(T_VAR)
        
    def Error(self):
        """calculate error in spec"""
        stage = self.draw.stage
        tower = stage.tower
        stageNo = stage.number
        T = tower.T[stageNo]
        if self.draw.isSubCooled:
            T -= stage.GetDegreesSubCooled()
        error = (T - self.temperature) / 500.
        return error

class PortMoleFracSpec(object):
    """Mole fraction spec - created by tower itself from output port values"""
    def __init__(self, stage, phase, cmpNo, frac, port):
        """
        stage is the stage spec applies to
        phase is liquid or vapour
        cmpNo is the component number in the component list
        frac is the mole fraction spec
        port is the port containing the spec - used to determine if spec still valid
        """
        self.stage = stage
        self.phase = phase
        self.cmpNo = cmpNo
        self.frac = frac
        self.port = port

    def CleanUp(self):
        self.draw = None
        self.port = None
        self.stage = None
        self.frac = None
        
    def SpecValue(self):
        """
        return the spec value - mainly to determine if still known
        """
        moleFracs = self.port.GetCompositionValues()
        return moleFracs[self.cmpNo]
        
    def Error(self):
        """calculate the error in the spec"""
        tower = self.stage.tower
        if self.phase == TOWER_LIQ_PHASE:
            x = tower.x[self.stage.number, self.cmpNo]
        elif self.phase == TOWER_VAP_PHASE:
            x = tower.y[self.stage.number, self.cmpNo]
        else:
            raise SimError('InvalidDrawPhase', (self.stage.number, tower.GetPath()))
        
        return x - self.frac
    
class Tower(UnitOperations.UnitOperation):
    """inside/out distillation tower operation"""
    def __init__(self, initScript = None):
        """Init the Tower

        It will initially be populated by just two stages
        """         
        super(Tower, self).__init__(initScript)

        # initially turn off solver
        self.SetParameterValue(TRYTOSOLVE_PAR, 0)
        self.SetParameterValue(TRYTORESTART_PAR, 1)
        self.SetParameterValue(TRIGGERSOLVE_PAR, 0)
        self.SetParameterValue(FREQ_JAC_MSG_PAR, 10)
        self.SetParameterValue(TRYLASTCONVERGED_PAR, 0)
        
        #Add a pressure profile object
        #Note... this profile is used for interaction with users and 
        #is different from the array self.P which is used in the calculations
        self.pProfile = ProfileObj(self, P_VAR, 'P_Profile')
        
        #This has to be there before adding any stage
        self.converged = 0
        self.canRestart = 0
        self.dontRestartNextTime = 1
        self.convRes = {}
        
        #Add two stages
        self.stages = []
        self.numStages = 0
        self.numInnerEqns = 0
        self.numCompounds = 0
        Stage(self, 0)
        Stage(self, 1)
        
        self.totReb = 0
        self.totCond = 0
        
        self.SetParameterValue(MAXINNERERROR_PAR, 0.0001)  # maximum allowable inner loop error
        self.SetParameterValue(MAXOUTERERROR_PAR, 0.0001)  # maximum Sum Yi error on any stage
        self.SetParameterValue(MININNERSTEP_PAR, 0.0001)   # smallest Jacobian correct scale factor
        self.SetParameterValue(MAXOUTERLOOPS_PAR, 20)      # maximum allowable outer loops
        self.SetParameterValue(MAXINNERLOOPS_PAR, 50)      # maximum inner loops
        self.SetParameterValue(EFFICIENCIES_PAR, 1.0)      # default overall efficiency
        #self.SetParameterValue(CONV_REPORT_LEVEL_PAR, 0)
        
        self.storedProfiles = {}
        
        #Initialization algorithm object
        self.initTowerObj = None
        self.AddObject(InitializeTower(), INIT_TOWER_OBJ)
        
        
    def __getstate__(self):
        """return info to pickle for storing"""
        try: 
            state = self.__dict__.copy()
            if state['initTowerObj']:
                #Don't store the pressure drop model
                #as it could be custom made
                try:
                    #The str(type(state['initTowerObj'])) call returns something like this:
                    #"<class 'PressureDropModel'>"
                    #Change it to something like this:
                    #'PressureDropModel'
                    s = str(type(state['initTowerObj'])).split(' ', 1)[1][1:-2]
                    state['initTowerObj'] = s
                except:
                    pass
            return state
        except: 
            return self.__dict__
        
    def __setstate__(self, oldState):
        """build from stored info"""
        
        self.__dict__ = oldState
        if self.__dict__.has_key('initTowerObj'):
            if self.initTowerObj:
                try:
                    #The pressure drop model was stored as a string. 
                    #Try to recreate it as an a object
                    lstMods = self.initTowerObj.split('.', 1)
                    if len(lstMods) > 1:
                        exec('import %s' %lstMods[0])
                    initTowerObj = eval('%s()' %self.initTowerObj)
                    self.initTowerObj = None
                    self.AddObject(initTowerObj, INIT_TOWER_OBJ)
                except:
                    initTowerObj = InitializeTower()
                    self.initTowerObj = None
                    self.AddObject(initTowerObj, INIT_TOWER_OBJ)
            else:
                initTowerObj = InitializeTower()
                self.AddObject(initTowerObj, INIT_TOWER_OBJ)
        
    def ClearConvResults(self):
        self.convRes = {}
        
    def StoreConvResults(self):
        """Store the converged results. Return 1 if successful, 0 otherwise"""
        self.ClearConvResults()
        try:
            #The keys of convRes must exactly match the names of the attributes in the tower
            self.convRes['flowMatrix'] = array(self.flowMatrix, Float)
            self.convRes['T'] = array(self.T, Float)
            self.convRes['V'] = array(self.V, Float)
            self.convRes['L'] = array(self.L, Float)
            self.convRes['l'] = array(self.l, Float)
            self.convRes['v'] = array(self.v, Float)
                
            self.convRes['A'] = array(self.A, Float)
            self.convRes['B'] = array(self.B, Float)
            self.convRes['alpha'] = array(self.alpha, Float)
    
            self.convRes['hlModel'] = array(self.hlModel, Float)
            self.convRes['hvModel'] = array(self.hvModel, Float)
            self.convRes['jacobian'] = array(self.jacobian, Float)
            self.convRes['logSFactors'] = array(self.logSFactors, Float)
            
            if self.waterDraws:
                for wd in self.waterDraws:
                    wd.StoreConvResults()
            
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
            if self.numStages != len(self.convRes['T']): return 0
            
            #numCompounds is only updated if a Solve call was first made
            #Make sure this method is always called after the step where
            #Solve updates numCompounds !!
            if self.numCompounds != len(self.convRes['l'][0, :]): return 0
            
            if self.waterDraws:
                for wd in self.waterDraws:
                    if not wd.RetrieveConvResults():
                        raise SimError('CouldNotGetLastConv', wd.GetPath())
            
            try:
                for key in self.convRes:
                    tempDict[key] = self.__dict__[key]
                    self.__dict__[key] = array(self.convRes[key], Float)
            except:
                if key != 'jacobian':
                    raise
                else:
                    self.jacobian = None
            return 1
        
        except:
            #Put it back to what it was if it failed
            for key in tempDict:
                self.__dict__[key] = tempDict[key]
                
            return 0
        
        
    def CleanUp(self):
        try:
            for stage in self.stages:
                stage.CleanUp()
            self.stages = []
            self.storedProfiles = None
            self.pProfile.CleanUp()
            self.convRes = None
            if hasattr(self, '_lastEneErrs'):
                self._lastEneErrs = None
            if hasattr(self.initTowerObj, 'CleanUp'):
                self.initTowerObj.CleanUp()
            self.useStages = []
        except:
            self.InfoMessage('ErrInCleanUp', (self.GetPath(),), MessageHandler.errorMessage)
        super(Tower, self).CleanUp()

    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        for stage in self.stages:
            stage.AdjustOldCase(version)
        super(Tower, self).AdjustOldCase(version)
        
        if version[0] < 36:
            #Add the pressure profile object
            if not hasattr(self, 'pProfile'):
                self.pProfile = ProfileObj(self, P_VAR, 'P_Profile')
                self.pProfile.SetSize(self.numStages)
        
        if version[0] < 39:
            if not hasattr(self, 'storedProfiles'):
                self.storedProfiles = {}
                
        if version[0] < 45:
            self.parameters[TRIGGERSOLVE_PAR] = 0
        if version[0] < 46:
            self.parameters[FREQ_JAC_MSG_PAR] = 10
            self.parameters[TRYLASTCONVERGED_PAR] = 0
        if version[0] < 47:
            if not hasattr(self, 'convRes'):
                self.ClearConvResults()
            
        if version[0] < 49:
            if not hasattr(self, 'initTowerObj'):
                self.initTowerObj = None
                self.AddObject(InitializeTower(), INIT_TOWER_OBJ)
        if version[0] < 58:
            self.totCond = 0
            self.totReb = 0
                
                
    def ValidateParameter(self, paramName, value):
        if not super(Tower, self).ValidateParameter(paramName, value):
            return False
        if paramName in (MAXOUTERLOOPS_PAR, MAXINNERLOOPS_PAR, 
                         MAXOUTERERROR_PAR, MAXINNERERROR_PAR, MININNERSTEP_PAR):
            if value <= 0:
                return False
        if paramName == FREQ_JAC_MSG_PAR and int(value) < 0:
            return False
        
        return True
    
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter and set converged to false"""
        
        #Trap some parameters that will not triger a solve
        #The logic behind these parameters is that they do not affect the final results
        if paramName in [CONV_REPORT_LEVEL_PAR, MAXINNERLOOPS_PAR, MAXOUTERLOOPS_PAR, FREQ_JAC_MSG_PAR,
                         DAMPINGFACTOR_PAR, INITKPOWER_PAR, WATERDAMPING_PAR, MININNERSTEP_PAR,
                         USEKMIXMODEL_PAR, 'Profiles']:
            if not self.ValidateParameter(paramName, value):
                raise Error.SimError('CantSetParameter', (paramName,str(value)))
                return 0
            self.parameters[paramName] = value
            return 1
        
                
        self.converged = 0
        super(Tower, self).SetParameterValue(paramName, value)    
    
    def ThermoChanged(self, thCaseObj):
        """Catch when the thermo changes"""
        super(Tower, self).ThermoChanged(thCaseObj)
        
        #Prepare for the odd case of a thermo set to None or compounds gone that are used in specs
        for stage in self.stages:
            for draw in stage.liqDraws.values() + stage.vapDraws.values():
                draw.Reset()
            for draw in stage.liqClones.values() + stage.vapClones.values():
                draw.Reset()
                
                
    def UpdateResultsStagesRemoved(self, firstStage, lastStage):
        try:
            nuStagesRem = lastStage - firstStage + 1
            convRes = self.convRes
            for varName in ['T', 'L', 'V', 
                            'A', 'B', 'logSFactors']:
                var = self.__dict__[varName]
                if var:
                    newVar = zeros(len(var)-nuStagesRem, Float)
                    newVar[0: firstStage] = var[0:firstStage]
                    newVar[firstStage:] = var[lastStage+1:]
                    self.__dict__[varName] = newVar
                if convRes:
                    var = convRes.get(varName, None)
                    if var:
                        newVar = zeros(len(var)-nuStagesRem, Float)
                        newVar[0: firstStage] = var[0:firstStage]
                        newVar[firstStage:] = var[lastStage+1:]
                        convRes[varName] = newVar
                        
            for varName in ['v', 'l', 'alpha']:
                var = self.__dict__[varName]
                if var:
                    dims = Numeric.shape(var)
                    newVar = zeros((dims[0]-nuStagesRem, dims[1]), Float)
                    newVar[0:firstStage][:] = var[0:firstStage][:]
                    newVar[firstStage:][:] = var[lastStage+1:][:]
                    self.__dict__[varName] = newVar
                if convRes:
                    var = convRes.get(varName, None)
                    if var:
                        dims = Numeric.shape(var)
                        newVar = zeros((dims[0]-nuStagesRem, dims[1]), Float)
                        newVar[0:firstStage][:] = var[0:firstStage][:]
                        newVar[firstStage:][:] = var[lastStage+1:][:]
                        convRes[varName] = newVar
                        
            for varName in ['hlModel', 'hvModel']:
                var = self.__dict__[varName]
                if var:
                    dims = Numeric.shape(var)
                    newVar = zeros((dims[0], dims[1]-nuStagesRem), Float)
                    newVar[:, 0:firstStage] = var[:, 0:firstStage]
                    newVar[:, firstStage:] = var[:, lastStage+1:]
                    self.__dict__[varName] = newVar
                if convRes:
                    var = convRes.get(varName, None)
                    if var:
                        dims = Numeric.shape(var)
                        newVar = zeros((dims[0], dims[1]-nuStagesRem), Float)
                        newVar[:, 0:firstStage] = var[:, 0:firstStage]
                        newVar[:, firstStage:] = var[:, lastStage+1:]
                        convRes[varName] = newVar                        
                        
                        
            if self.v and self.V:
                self.y = transpose(transpose(self.v)/self.V)
                
            if self.l and self.L:
                self.x = transpose(transpose(self.l)/self.L)
                        
                        
            if self.jacobian:
                self.jacobian = None
            if self.convRes['jacobian']:
                self.convRes['jacobian'] = None
                        
        except:
            self.dontRestartNextTime = 1        
        
    def UpdateResultsStageAdded(self, currNuStages, nuNewStage):
        try:
            convRes = self.convRes
            for varName in ['T', 'L', 'V', 'A', 'B', 'logSFactors']:
                var = self.__dict__[varName]
                if var:
                    newVar = zeros(len(var)+1, Float)
                    newVar[0: nuNewStage] = var[0:nuNewStage]
                    newVar[nuNewStage] = var[nuNewStage-1]
                    newVar[nuNewStage+1:] = var[nuNewStage:]
                    self.__dict__[varName] = newVar
                if convRes:
                    var = convRes.get(varName, None)
                    if var:
                        newVar = zeros(len(var)+1, Float)
                        newVar[0: nuNewStage] = var[0:nuNewStage]
                        newVar[nuNewStage] = var[nuNewStage-1]
                        newVar[nuNewStage+1:] = var[nuNewStage:]
                        convRes[varName] = newVar
                        
            for varName in ['v', 'l', 'alpha']:
                var = self.__dict__[varName]
                if var:
                    dims = Numeric.shape(var)
                    newVar = zeros((dims[0]+1, dims[1]), Float)
                    newVar[0:nuNewStage][:] = var[0:nuNewStage][:]
                    newVar[nuNewStage][:] = var[nuNewStage-1][:]
                    newVar[nuNewStage+1:][:] = var[nuNewStage:][:]
                    self.__dict__[varName] = newVar
                if convRes:
                    var = convRes.get(varName, None)
                    if var:
                        dims = Numeric.shape(var)
                        newVar = zeros((dims[0]+1, dims[1]), Float)
                        newVar[0:nuNewStage][:] = var[0:nuNewStage][:]
                        newVar[nuNewStage][:] = var[nuNewStage-1][:]
                        newVar[nuNewStage+1:][:] = var[nuNewStage:][:]
                        convRes[varName] = newVar
                        
            for varName in ['hlModel', 'hvModel']:
                var = self.__dict__[varName]
                if var:
                    dims = Numeric.shape(var)
                    newVar = zeros((dims[0], dims[1]+1), Float)
                    newVar[:, 0:nuNewStage] = var[:, 0:nuNewStage]
                    newVar[:, nuNewStage] = var[:, nuNewStage-1]
                    newVar[:, nuNewStage+1:] = var[:, nuNewStage:]
                    self.__dict__[varName] = newVar
                if convRes:
                    var = convRes.get(varName, None)
                    if var:
                        dims = Numeric.shape(var)
                        newVar = zeros((dims[0], dims[1]+1), Float)
                        newVar[:, 0:nuNewStage] = var[:, 0:nuNewStage]
                        newVar[:, nuNewStage] = var[:, nuNewStage-1]
                        newVar[:, nuNewStage+1:] = var[:, nuNewStage:]
                        convRes[varName] = newVar
                        
                        
            if self.v and self.V:
                self.y = transpose(transpose(self.v)/self.V)
                
            if self.l and self.L:
                self.x = transpose(transpose(self.l)/self.L)
                
                
            if self.jacobian:
                self.jacobian = None
            if self.convRes['jacobian']:
                self.convRes['jacobian'] = None
                        
        except:
            self.dontRestartNextTime = 1
        
    def InsertStage(self, stage):
        """insert stage into stage array"""
        self.converged = 0
        #self.dontRestartNextTime = 1
        assert(stage.number - 1 <= self.numStages)
        for i in range(self.numStages-1, stage.number-1, -1):
            self.stages[i].ChangeNumber(i + 1)
            
        self.stages.insert(stage.number, stage)
        
        #Use these to variables to check if it can restart
        if not self.dontRestartNextTime:
            self.UpdateResultsStageAdded(self.numStages, stage.number)
            if not self.dontRestartNextTime:
                try: self.numInnerEqns += 1
                except: pass
                    
        #Now update the P_Profile
        self.pProfile.AddProperty(stage.number)
        
        if stage.number == 0 or self.stages[stage.number - 1].type == BOTTOM_STAGE:
            stage.type = TOP_STAGE
        elif stage.number == self.numStages:
            stage.type = BOTTOM_STAGE
        self.numStages += 1
        

    def RemoveStages(self, firstStage, lastStage):
        
        #Check if efficiencies parameter should be modified
        effParam = self.GetParameterValue(EFFICIENCIES_PAR)
        try:
            newEffParam = AdjustEffMatrixForRemoval(effParam, firstStage, lastStage)
            if newEffParam:
                self.SetParameterValue(EFFICIENCIES_PAR, newEffParam)
                self.InfoMessage("ChangedEffMatrix", (self.GetPath(),))
        except:
            #Notify of the error but don't quit
            self.InfoMessage("TowerUpdateEffErr", (self.GetPath(),))
        
        self.converged = 0
        #self.dontRestartNextTime = 1
        for i in range(firstStage, lastStage + 1):
            self.stages[i].CleanUp()
        self.UpdateResultsStagesRemoved(firstStage, lastStage)
        if not self.dontRestartNextTime:
            try: self.numInnerEqns -= (lastStage - firstStage + 1)
            except: pass
        
        #Now update the P_Profile
        self.pProfile.RemoveProperties(firstStage, lastStage)
        
        bottomStages = self.numStages - lastStage - 1
        self.stages[firstStage:firstStage + bottomStages] = \
            self.stages[lastStage+1:self.numStages]
        oldNumStages = self.numStages
        self.numStages -= lastStage - firstStage + 1
        del self.stages[self.numStages:oldNumStages]
        for i in range(firstStage,firstStage+bottomStages):
            self.stages[i].ChangeNumber(i)
        
    def AddObject(self, obj, name):
        if isinstance(obj, InitializeTower):
            if name != INIT_TOWER_OBJ:
                self.InfoMessage('CantChangeName', (INIT_TOWER_OBJ,), MessageHandler.errorMessage)
                #Should it really raise an error ??
                raise SimError ('CantChangeName', (INIT_TOWER_OBJ,))
            if self.initTowerObj:
                self.DeleteObject(self.initTowerObj)
            self.initTowerObj = obj
            obj.Initialize(self, INIT_TOWER_OBJ)
        else:
            super(Tower, self).AddObject(obj, name)
            
    def GetObject(self, name):
        """returns contained object based on name"""
        if name == INIT_TOWER_OBJ:
            return self.initTowerObj
        
        if self.__dict__.has_key(name): 
            if name == T_VAR:
                #Pass the T profile taking into account the subcooled temperature
                if self.stages[0].IsSubCooled():
                    subCoolDT = self.stages[0].GetDegreesSubCooled()
                    if subCoolDT:
                        tempT = array(self.T, Float)
                        tempT[0] = tempT[0] - subCoolDT
                        return tempT
            return self.__dict__[name]
        
        split = string.splitfields(name, '_',1)
        
        if len(split) == 2 and split[0] == 'Stage':
            split = string.splitfields(split[1], '_', 1)
            stageNo = int(split[0])
            if stageNo < self.numStages:
                stage = self.stages[stageNo]
                if len(split) > 1:
                    return stage.GetObject(split[1])
                else:
                    return stage
        elif len(split) == 2 and (split[0] == TOWER_LIQ_PHASE or split[0] == TOWER_VAP_PHASE):
            return self.Profile(split[0], split[1])
        
        elif name == 'P_Profile':
            #This is a special profile because it can receive input from the user
            return self.pProfile
        
        return super(Tower, self).GetObject(name)


    def DeleteObject(self, obj):
        """
        check that we aren't deleting a port
        """
        if isinstance(obj, Ports.Port):
            raise SimError('TowerDeletePort', (obj.GetPath(), self.GetPath()))
        elif isinstance(obj, Stage):
            if obj.number > 0:
                # tell the stage above to remove 1 stage from below
                self.stages[obj.number - 1].Minus(1)
        elif isinstance(obj, InitializeTower) and obj is self.initTowerObj:
            if hasattr(self.initTowerObj, 'CleanUp'):
                self.initTowerObj.CleanUp()
            self.initTowerObj = None
        else:
            super(Tower, self).DeleteObject(obj)            

    def GetContents(self):
        result = super(Tower, self).GetContents()
        result.append(('Stage_0',self.stages[0]))
        result.append(('Stage_%d' % (self.numStages - 1), self.stages[self.numStages - 1]))

        arrayType = type(zeros((1)))
        for key in self.__dict__:
            obj = self.__dict__[key]
            if type(obj) == arrayType:
                result.append((key, 'Array[%s]' % str(obj.shape)))
        return result
    

    def AppendCompound(self, cmpIdx=-1):
        """
        Not converged if the component list changes
        """
        self.converged = 0
        super(Tower, self).AppendCompound(cmpIdx)
        
    def DeleteCompound(self, cmp):
        """
        not converged if the component list changes
        """
        self.converged = 0
        super(Tower, self).DeleteCompound(cmp)
        
    def NeedToSolve(self):
        """return true if a solution is necessary and possible"""
        
        if not self.GetParameterValue(TRYTOSOLVE_PAR):
            if not self.GetParameterValue(TRIGGERSOLVE_PAR):
                return 0

        readyToSolve = 1
        numberInner = 0
        numberSpecs = 0
        someP = None
        checkP = True
        pProps = self.pProfile.GetProperties()
        for stage in self.stages:
            # check that all feeds are known
            if not stage.ReadyToSolve():
                readyToSolve = 0
                # don't break so spec numbers are calculated
                
                
            #Split between known and unknwon spec objects
            numberInner += stage.NumberInner()
            numberSpecs += stage.NumberSpecs()
            
            
            #Check if a pressure can be obtained
            if not someP and checkP:
                someP = pProps[stage.number].GetValue()
                if not someP:
                    someP = stage.GetPressure()
                    
                #There should be at least one pressure in the main section of the tower
                #stop checking for lower sections
                if stage.type == BOTTOM_STAGE:
                    checkP = False

                    
        if not someP:
            if readyToSolve:
                self.InfoMessage('TowerNoPressure', self.GetPath())
            readyToSolve = 0
                
        if readyToSolve:
            specsNeeded = numberInner - self.numStages
            if numberSpecs < specsNeeded:
                readyToSolve = 0            

            elif self.converged and not self.IsForgetting():
                for stage in self.stages:
                    stage.AssignResultsToPorts()
                self.FlashAllPorts()
                return 0
        
            elif numberSpecs > specsNeeded:
                #Re do the loop and get the correct info of the specs
                numSpecsDisp = 0
                numReqDisp = 0
                for stage in self.stages:
                    numSpecsDisp += stage.userSpecs
                    numReqDisp += stage.NumberOfSpecsRequired()
                #Hack to clear this flag. The correct way woudl be to 
                #call this method from a try except block 
                if not self.IsForgetting():
                    self.parameters[TRIGGERSOLVE_PAR] = 0
                raise SimError("TooManyTowerSpecs", (numSpecsDisp, numReqDisp, self.GetPath()))
        
        if len(self.stages) == self.numStages and (numberInner-self.totReb-self.totCond) == self.numInnerEqns and \
           self.numCompounds == len(self.GetCompoundNames()) and not self.dontRestartNextTime:
        #if len(self.stages) == self.numStages and \
           #self.numCompounds == len(self.GetCompoundNames()) and not self.dontRestartNextTime:
            self.canRestart = 1
        else:
            self.canRestart = 0
            
        # if not ready to solve, then cannot be converged
        self.converged = 0
        
        if self.IsForgetting():
            return 0

        return readyToSolve
    
    def PropagatePressures(self):
        """Propagate the pressures into all the objects of a given stage if the stage has a known pressure
        """
        
        pProfile = self.pProfile
        for i in range(self.numStages):
            stage = self.stages[i]
            prop = pProfile.props[i]
            
            pVal_0 = stage.GetPressure()
            pVal_1 = prop.GetValue()
            
            if pVal_1 != None:
                stage.SetPressure(pVal_1)
            elif pVal_0 != None:
                prop.SetValue(pVal_0, CALCULATED_V)
                #Put it back to this stage so it propagates to the rest of the objects
                stage.SetPressure(pVal_0)
                
            
    def Forget(self):
        """Get rid of the pressue profile"""
        super(Tower, self).Forget()
        self.pProfile.Forget()
    
    def Solve(self):
        
        #Get rid of all the previously requested profiles
        self.storedProfiles = {}
        
        self.FlashAllPorts()     # make sure feeds are calculated
        
        #This is a customized Forget which just clears calcualted values
        self.pProfile.Forget()   #Always call this to begin with
        
        
        #Put a zero flow in top vapour draw if subcooling
        #Do this regardless of the TryToSolve status
        self.stages[0].SolveSubCooledFlow()
        
        if not self.NeedToSolve():
            #Solve for the pressures that are already known
            self.PropagatePressures()
            #Trigger solve acts as a button, hence, we should make it 0 regardless of its current value.
            if not self.IsForgetting():
                self.parameters[TRIGGERSOLVE_PAR] = 0
            return
        
        #Trigger solve acts as a button, hence, we should make it 0 regardless of its current
        #value. 
        self.parameters[TRIGGERSOLVE_PAR] = 0
        
        #This variable is needed by pump around specs
        self._lastEneErrs = None
        
        maxInnerError = self.GetParameterValue(MAXINNERERROR_PAR)
        maxOuterError = self.GetParameterValue(MAXOUTERERROR_PAR)
        minInnerStep  = self.GetParameterValue(MININNERSTEP_PAR)
        maxOuterLoops = self.GetParameterValue(MAXOUTERLOOPS_PAR)
        maxInnerLoops = self.GetParameterValue(MAXINNERLOOPS_PAR)
        if not maxInnerLoops: maxInnerLoops = 50
        
        self.path = self.GetPath()
        path = self.path
        
        self.useOldCode = self.GetParameterValue('UseOldCode')
        if self.useOldCode == None:
            self.useOldCode = True
            if self.GetParameterValue('UseNewCode') == 1:
                self.useOldCode = False
        
        #Custom way of reporting info messages when iterating
        self.convRepLevel = self.GetParameterValue(CONV_REPORT_LEVEL_PAR)
        if not self.convRepLevel:
            self.convRepLevel = 0
            
        #Is it a debug run ?
        self.debug = False
        if self.convRepLevel >= 20:
            self.debug = True
            self.convRepLevel |= 3
            
            ##DEBUG CODE ##########################################
            try:
                self.file = file = open('C:\\temp\\distdebug.txt', 'a')
                file.seek(0, 2) #Go to the end of the file
            except:
                try:
                    self.file = file = open('C:\\temp\\distdebug.txt', 'w')
                except:
                    self.debug = False
            if self.debug:
                txt = '**************************************************************************************************\n'
                file.write(txt)
                txt = '****SOLVING %s %s %s**********************************************\n' %(path, time.asctime(), time.time())
                file.write(txt)
                txt = '***************************************************************************************************\n\n'
                file.write(txt)
                file.flush()
                
                baseCmp = self.GetParameterValue('BaseDebugCmp')
                if not baseCmp: baseCmp = 'WATER'
            ######################################################
           
           
        #How often to display the jacobian message
        self.freqJacMsg = self.GetParameterValue(FREQ_JAC_MSG_PAR)
        if not self.freqJacMsg: self.freqJacMsg = 10
        
        self.dampingFactor = self.GetParameterValue(DAMPINGFACTOR_PAR)
        if self.dampingFactor is None:
            self.dampingFactor = 1.0
        self.initKPower = self.GetParameterValue(INITKPOWER_PAR)
        if self.initKPower is None:
            self.initKPower = 1.0
        
        outerLoopCount = 0
        outerError = 1.0   # must fail first time
        self.cmpNames = self.GetCompoundNames()
        self.numCompounds = len(self.cmpNames)
        self.mw = zeros(self.numCompounds, Float)
        thCaseObj = self.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        for i in range(self.numCompounds):
            self.mw[i] = thAdmin.GetSelectedCompoundProperties(prov, case, i, ['MolecularWeight'])[0]
            
        if self.debug:
            ##DEBUG CODE ##########################################
            self.waterIdx = 0
            if baseCmp in self.cmpNames:
                self.waterIdx = self.cmpNames.index(baseCmp)
            else:
                txt = "** WARNING... NO %s IN SYSTEM. FIRST COMPUND WILL BE PUT IN THE COLUMN FOR %s\n" %(baseCmp, baseCmp)
                file.write(txt)
            #######################################################
            
        self.LoadStagesWithObjects()
            
        #How to initialize?
        #Keep order so Restart overrides LastConverged
        initMode = SCRATCH_INIT
        if self.GetParameterValue(TRYLASTCONVERGED_PAR) and self.canRestart:
            initMode = LASTCONV_INIT
        if self.GetParameterValue(TRYTORESTART_PAR) and self.canRestart:
            initMode = RESTART_INIT
        try:
            if initMode == LASTCONV_INIT:
                if not self.RetrieveConvResults():
                    initMode = SCRATCH_INIT
                    
            # this will fail if everything is not available
            self.SetUpArrays(initMode)
            totCond = self.totCond = self.stages[0].totCond
            totReb = self.totReb = self.stages[-1].totReb
            if self.debug:
                ##DEBUG CODE ##########################################
                txt = '****lnalpha from initialization step ( lnalpha = lnK)\n'
                file.write(txt)
                TowerDumpAlpha(self)
                ######################################################            
            
            ##S = Numeric.exp(self.logSFactors[self.totCond:self.numStages-self.totReb])
            ##self.scale = 1.0#Numeric.multiply.reduce(S) ** (1.0/(self.numStages-self.totCond-self.totReb))
            
            ##self.logSFactors[totCond:self.numStages-totReb] = Numeric.log(S / self.scale)
            
            self.SolveFlowMatrix(self.logSFactors)  # calculate initial compositions from those estimates
            self.dokmix = False
            if initMode == SCRATCH_INIT and self.waterDraws:
                dokmix = self.GetParameterValue(USEKMIXMODEL_PAR)
                if not dokmix: self.dokmix = False
                else: self.dokmix = True
                
            if not initMode:
                #Clean this up
                self.A = None
                self.B = None
                
                self.dontRestartNextTime = 0  # reset after a full start
                self.hlModel = None
                self.hvModel = None
                if self.isSubCool and self.subCoolDT == None:
                    self.stages[0].SetDegreesSubCooled(self.T[0] - self.subCoolT[0]) #Keep up to date
                self.InitOuterProperties()      # initialize the outer property coefficients
                if self.specsWModel:
                    #The simple models for pump around specs can only be loaded after a call to 
                    #InnerErrors
                    errors = self.InnerErrors()
                    for spec in self.specsWModel:
                        spec.InitModel()
                self.InfoMessage('TowerCalcJacobian', path)
                self.jacobian = self.CalcJacobian()  # calculate initial inverse Jacobian
                
            elif not hasattr(self, 'jacobian') or self.jacobian == None or Numeric.shape(self.jacobian)[0]!=self.numInnerEqns:
                #For some reason the old jacobian is gone or not good anymore
                self.jacobian = self.CalcJacobian()
            
                
            self.errors = self.InnerErrors()
            totalError = Numeric.sum(Numeric.absolute(self.errors))
            oldErrors = zeros(self.numInnerEqns, Float)
            oldLogSFactors = zeros(self.numInnerEqns+totCond+totReb, Float)
            oldT = array(self.T)
            outerLoopCount = 0
            self.outerError = outerError = 1.0   # must fail first time
            self.converged = 0
            
            while 1:  # outer loop
                innerLoopCount = 0
                #outerOldT = array(self.T, Float)
                if self.convRepLevel & 2: outerOldT = array(self.T, Float)
                
                if self.debug:
                    ##DEBUG CODE ##########################################
                    txt = '***********************************************************************\n'
                    file.write(txt)
                    txt = '***********************************************************************\n'
                    file.write(txt)
                    txt = 'Entered OuterLoop %i\n' %(outerLoopCount+1)
                    file.write(txt)
                    txt = 'Stage       T              L              V              B              A           lnKb\n'
                    file.write(txt)
                    lnKb = self.A - self.B/self.T
                    for i in range(self.numStages):
                        txt = '%5i %7.6g %14.7g %14.7g %14.8g %14.8g %14.8g\n' %(i, self.T[i], self.L[i], self.V[i], self.B[i], self.A[i], lnKb[i])
                        file.write(txt)
                    file.write('\n\n')
                    file.flush()
                    ######################################################
                    
                while innerLoopCount < maxInnerLoops:   # inner loop
                    innerLoopCount += 1
                    innerConverged = 0
                    oldErrors[:] = self.errors[:]
                    oldTotalError = totalError
                    oldLogSFactors[:] = self.logSFactors[:]
                    oldT[:] = self.T[:]
                    adjustment = -dot(self.jacobian, self.errors)
                    
                    # initial step length limited to 1 over largest correction
                    stepLength = 1.0 / max(1.0, max(absolute(adjustment)))                    

                    if self.debug:
                        ##DEBUG CODE ##########################################
                        txt = '    ***************\n    Entered InnerLoop %i\n    Stage       T            lnS            lnR              L              V             xw             xhc             yw            yhc\n' %(innerLoopCount)
                        file.write(txt)
                        wIdx = self.waterIdx
                        drawRatios = -3271 * ones(self.numStages, Float)
                        drawRatios[:len(self.logSFactors[self.numStages:])] = self.logSFactors[self.numStages:]
                        for i in range(self.numStages):
                            txt = '    %5i %7.6g %14.7g %14.7g %14.7g %14.7g %14.8g %14.8g %14.8g %14.8g\n' %(i, self.T[i], 
                                                                                                       self.logSFactors[i], drawRatios[i],
                                                                                                       self.L[i], self.V[i], 
                                                                                                       self.x[i, wIdx], sum(self.x[i, :])-self.x[i, wIdx], 
                                                                                                       self.y[i, wIdx], sum(self.y[i, :])-self.y[i, wIdx])
                            file.write(txt)
                        file.write('\n\n')
                        file.flush()
                        ######################################################
                        
                    # loop until reduction in errors or step length become too small
                    while 1:
                        actualAdjustment = stepLength * adjustment
                        self.logSFactors[totCond:self.numStages-totReb] += actualAdjustment[:self.numStages-totCond-totReb]
                        self.logSFactors[self.numStages:] += actualAdjustment[self.numStages-totCond-totReb:]
                        
                        # calculate comps, flows and temps from new stripping factors
                        self.SolveFlowMatrix(self.logSFactors)
                        self.CalculateTemperatures()
                        
                        # check errors
                        self.errors = self.InnerErrors()
                        totalError = Numeric.sum(Numeric.absolute(self.errors))
                        
                        if totalError < oldTotalError:
                            break
                        
                        # errors did not go down - back down step size
                        self.logSFactors[:] = oldLogSFactors[:]
                        self.T[:] = oldT[:]
                        if stepLength < minInnerStep:
                            # step size too small - go back to original and bail
                            self.SolveFlowMatrix(self.logSFactors)
                            ## only for debugging
                            self.errors = self.InnerErrors()
                            break

                        stepLength /= 4
                    
                    if stepLength < minInnerStep:
                        # smallest step did't work - exit
                        break
                    
                    #Pass an info message depending on the level of report
                    if self.convRepLevel & 1:
                        idxMaxErr = Numeric.argmax(absolute(self.errors))
                        self.InfoMessage('InnerErrorDetail', (path, totalError, self.errors[idxMaxErr], 
                                                              self.eqnLbls[idxMaxErr]))
                    else:
                        self.InfoMessage('TowerInnerError', (path, totalError))
                        
                    if self.debug:
                        ##DEBUG CODE ##########################################
                        txt = '    ***************\n'
                        file.write(txt)
                        txt = "    %s Inner Details. Error: %13.6g ; MaxErrorValue: %13.6g ; MaxErrorEqnName: %s " % (path, totalError, self.errors[idxMaxErr], self.eqnLbls[idxMaxErr])
                        file.write(txt)
                        file.write('\n\n')
                        file.flush()
                        ######################################################
                        
                        
                    if totalError < maxInnerError:
                        innerConverged = 1
                        break
                    
                    # update jacobian        
                    self.jacobian = self.UpdateJacobian(self.jacobian, actualAdjustment, (self.errors - oldErrors))
                    
                    
                #Do a summary if requested
                if self.convRepLevel & 2:
                    dt = self.T-outerOldT
                    idxMaxErr = Numeric.argmax(absolute(self.errors))
                    idxMaxDT = Numeric.argmax(absolute(dt))
                    self.InfoMessage('InnerLoopSummary', (path,
                                                          self.eqnLbls[idxMaxErr], self.errors[idxMaxErr],
                                                          idxMaxDT,  dt[idxMaxDT],
                                                          innerConverged, innerLoopCount))                    
                    
                    
                if self.debug:
                    ##DEBUG CODE ##########################################
                    txt = '    ***************\n'
                    file.write(txt)
                    txt = """    %s Inner Loop Summary:
    MaxErrorEqnName:......... %s
    MaxErrorValue:........... %.6g
    
    MaxDeltaTStage(0 at top): %i
    MaxDeltaTValue(New-Old):. %.4g
    
    Converged:............... %i
    Iterations:.............. %i""" %(path,
                                      self.eqnLbls[idxMaxErr], self.errors[idxMaxErr],
                                      idxMaxDT,  dt[idxMaxDT],
                                      innerConverged, innerLoopCount)
                    file.write(txt)
                    file.write('\n\n')
                    file.flush()
                ######################################################
                    
                if innerConverged and outerError < maxOuterError:
                    if not self.waterDraws:
                        self.converged = 1
                        break
                    else:
                        if not self.dokmix:
                            self.converged = 1
                            break
                        else:
                            #If doing a kmix model, deactivate it and let it finish converging
                            #wastes a few more iterations but seem to be more stable
                            self.dokmix = False
                
                outerLoopCount += 1
                if outerLoopCount > maxOuterLoops:
                    self.converged = 0
                    break
                
                # update the outer model
                self.InitOuterProperties()
                
                # calculate outer error = sum(Xi * alphai * Kb) - take largest stage error
                outerErrorVec = add.reduce(transpose(self.x*self.alpha)* (Numeric.exp(self.A - self.B/self.T))) - 1.
                outerError = max(Numeric.absolute(outerErrorVec))
                
                #Add the water error to the outer error
                wError = 0.0
                for wdraw in self.waterDraws: wError += wdraw.Error()
                outerError += wError
                self.outerError = outerError
                if not self.convRepLevel:
                    self.InfoMessage('TowerOuterError', (path, outerLoopCount, outerError))
                else:
                    idxMaxErr = Numeric.argmax(absolute(outerErrorVec))
                    self.InfoMessage('OuterErrorDetail', (path, outerLoopCount, outerErrorVec[idxMaxErr], idxMaxErr, wError))
                
                if self.debug:
                    ##DEBUG CODE ##########################################
                    txt = '***************\n'
                    file.write(txt)
                    txt = "%s Iteration %d Outer Error %13.6g. MaxErrorStage(0 at top) %i WaterDrawError %13.6g" % (path, outerLoopCount, outerErrorVec[idxMaxErr], idxMaxErr, wError)
                    file.write(txt)
                    file.write('\n\n')
                    file.flush()
                    ######################################################
                
                # calculate new jacobian if inner failed
                if not innerConverged:
                    self.InfoMessage('TowerCalcJacobian', path)
                    self.jacobian = self.CalcJacobian()
                else:
                    self.SolveFlowMatrix(self.logSFactors)
                    self.CalculateTemperatures()
                    
                if self.debug:
                    ##DEBUG CODE ##########################################
                    txt = '***************\nRebalance after updating Outer Properties'
                    file.write(txt)
                    TowerDumpFlowsPerCmp(self)
                    ######################################################
                    
                self.errors = self.InnerErrors()
                totalError = Numeric.sum(Numeric.absolute(self.errors))
                
        except ArithmeticError, e:
            self.converged = False
            self.InfoMessage('ERRTowerArithmetic', path)
            return
        except SimError, e:
            self.converged = False
            self.InfoMessage(e.messageKey, e.extraData, MessageHandler.errorMessage)
        except:
            self.converged = False
            
        
        if self.debug:
            ##DEBUG CODE ##########################################
            txt = '****FINISHED %s %s %s**********************************************\n' %(self.GetPath(), time.asctime(), time.time())
            file.write(txt)
            txt = '***************************************************************************************************\n\n'
            file.write(txt)
            file.close()
            
            try:
                del self.lnFugL
                del self.lnFugV
                del self.file
                del self.waterIdx
            except:
                pass
            #########################################################
        
        
        if self.converged:
            
            #Make sure that it didn't converge to a subcooled temperature when there is a
            #vapour draw with flow != 0.0
            if self.subCoolT != None and abs(self.V[0]) > 1.0E-7:
                if abs(self.T[0] - self.subCoolT[0]) != 1.0E-8:
                    self.InfoMessage('TwrSubCooledVapDraw', (self.T[0]-self.subCoolT[0],))
                    self.converged = False
                    return
            
            self.pProfile.SetValues(self.P, CALCULATED_V)
            for stage in self.stages:
                stage.AssignResultsToPorts()
                
            #Keep track of converged results
            self.StoreConvResults()
            
            try:
                self.FlashAllPorts()
            except SimError, e:
                self.converged = False
                self.InfoMessage(e.messageKey, e.extraData, MessageHandler.errorMessage)
                
                
            #Just for debugging
            if self.convRepLevel & 4:
                TowerOverallBalancePerSection(self)
                
        else:
            self.InfoMessage('TowerFailedToConverge',  (path, outerLoopCount, outerError))
            

    def LoadStagesWithObjects(self):
        """Loads the relevant stages into one handy list"""
        self.useStages = []
        for stage in self.stages:
            if stage.feeds or stage.qfeeds or stage.vapDraws or stage.liqDraws or stage.vapClones or stage.liqClones:
                self.useStages.append(stage)
                continue
            if stage.subCool or stage.specs or stage.estimates or stage.waterDraw:
                self.useStages.append(stage)
                continue
        
    def SetUpArrays(self, initMode):
        """
        Initialize the arrays needed to solve column
        initMode can be:
            SCRATCH_INIT = 0
            RESTART_INIT = 1
            LASTCONV_INIT = 2
        """
        
        
        if not self.initTowerObj:
            self.AddObject(InitializeTower(), INIT_TOWER_OBJ)
            
        #Let the dedicated object handle this
        self.initTowerObj.SetUpArrays(initMode)
        
            
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

    def SolveFlowMatrix(self, logSFactors):
        """
        use the log of the flow ratios to calculate component flows
        from the inner model
        """
        # check minimums
        logSFactors = clip(logSFactors, logTiniestValue, logLargestValue)
        
        # extract stripping factors and draw ratios
        Sj = Numeric.exp(logSFactors[:self.numStages])
        drawRatios = Numeric.exp(logSFactors[self.numStages:])
        
        # calculate the draw ratio terms
        RvTerm = ones(self.numStages, Float)  # 1 + sum(Rvjn)
        RlTerm = ones(self.numStages, Float)  # 1 + sum(Rljn)
        # pump around terms, obviously not efficient, but expedient
        paVTerm = zeros((self.numStages, self.numStages), Float)
        paLTerm = zeros((self.numStages, self.numStages), Float)

        # index of non basis draws - order counts
        ratioCount = 0
        hasPumps = 0  # keep track of whether we can skip pump calcs
        for stage in self.useStages:
            for draw in stage.vapDrawsActive:
                if draw.isBasis:
                    # if it is a basis, then D/V = 1.0
                    term = 1.0
                else:
                    term = drawRatios[ratioCount]
                    RvTerm[stage.number] += term
                    ratioCount += 1
                    
                if draw.pumpToFeed:
                    hasPumps = 1    # must process pumparounds
                    feedStageNo = draw.pumpToFeed.stage.number
                    paVTerm[feedStageNo, stage.number] += term
                    
            for draw in stage.liqDrawsActive:
                if draw.isBasis:
                    # if it is a basis, then D/V = 1.0
                    term = 1.0
                else:
                    term = drawRatios[ratioCount]
                    RlTerm[stage.number] += term
                    ratioCount += 1
                    
                if draw.pumpToFeed:
                    hasPumps = 1    # must process pumparounds
                    feedStageNo = draw.pumpToFeed.stage.number
                    paLTerm[feedStageNo, stage.number] += term
                    
        if (ratioCount + self.numStages - self.totCond - self.totReb) != self.numInnerEqns:
            raise SimError('EqnNumbMismatch', self.GetPath())
                
        if self.useEff:
            effOffset = zeros(self.numStages, Float)  # need this predefined
            effOffsetPA = zeros((self.numStages, self.numStages), Float)
            eff = self.eff

        rhs = zeros(self.numStages, Float)
        for i in range(self.numCompounds):
            # create solution matrix
            flowMatrix = zeros((self.numStages, self.numStages), Float)

            if self.useEff:
                alphaSj = 1.0/(eff[:,i]*self.alpha[:,i]*Sj)
                effterm = (1. - eff[:,i])*alphaSj/RvTerm
                for section in self.sections:
                    # want to slide term along one - j-1 so first zero, last not used
                    #Loop for each section of the tower (main section and side strippers)
                    #top and bottom are actual indexes where the TOP_STAGE and BOTTOM_STAGE occur
                    top, bottom = section
                    effOffset[top+1:bottom+1] = effterm[top:bottom]
                    #put(effOffset, range(1, self.numStages), effterm[:-1])
                diag = RvTerm + RlTerm * alphaSj + effOffset
                upper = -1.0 - (1.0 - eff[:,i])*alphaSj*RlTerm/RvTerm
            else:
                alphaSj = 1.0/(self.alpha[:,i]*Sj)
                diag = RvTerm + RlTerm*alphaSj
                upper = -ones(self.numStages, Float)
                
            rhs[:] = self.f[:,i]
            for wdraw in self.waterDraws:
                stageNo = wdraw.stage.number
                if wdraw.moleFlows:
                    rhs[stageNo] -= wdraw.moleFlows[i]
                    
            for j in range(self.numStages):
                if self.stages[j].type != TOP_STAGE:
                    flowMatrix[j][j-1] = -alphaSj[j-1]
                flowMatrix[j][j] = diag[j]
                if self.stages[j].type != BOTTOM_STAGE:
                    flowMatrix[j][j+1] = upper[j]

            if hasPumps:
                if self.useEff:
                    term = effterm * paLTerm
                    for section in self.sections:
                        top, bottom = section
                        effOffsetPA[:, top+1:bottom+1] = term[:, top:bottom]
                    flowMatrix += -paVTerm - paLTerm * alphaSj + effOffsetPA
                else:
                    flowMatrix += -paVTerm - paLTerm * alphaSj
                
            try:
                self.v[:,i] = solve_linear_equations(flowMatrix, rhs)
            except:
                raise SimError('TowerCmpMatrixError', (self.GetPath(), i))
            
            self.l[:,i] = self.v[:,i]*alphaSj
            if self.useEff:
                for section in self.sections:
                    top, bottom = section
                    self.l[top:bottom,i] -= effterm[top:bottom]*self.v[top+1:bottom+1,i]
                    #self.l[:-1,i] -= effterm[:-1]*self.v[1:,i]
                self.l[:,i] = clip(self.l[:,i], tiniestValue, largestValue)
            
        ## probably don't need both x and y, but efficiency can come later
        self.V = Numeric.add.reduce(self.v, 1)
        self.L = Numeric.add.reduce(self.l, 1)
        self.x = clip(transpose(transpose(self.l)/add.reduce(self.l, 1)), tiniestValue, largestValue)
        self.y = clip(transpose(transpose(self.v)/add.reduce(self.v, 1)), tiniestValue, largestValue)
        
        #The next code results in oscillations (some times)
        #try:
            #if self.totCond:
                #if self.A != None:
                    #self.y[0] = self.alpha[0] * math.exp(self.A[0] - self.B[0]/self.T[0]) * self.x[0]
                #else:
                    #self.y[0] = self.alpha[0] * self.x[0]
            #if self.totReb:
                #if self.A != None:
                    #self.x[-1] = self.y[-1] / (self.alpha[-1] * math.exp(self.A[-1] - self.B[-1]/self.T[-1]))
                #else:
                    #self.x[-1] = self.y[-1] / self.alpha[-1]
                    
                    
        #except:
            #pass
        

        # keep flow terms for heat balance
        self.RvTerm = RvTerm
        self.RlTerm = RlTerm
        self.paVTerm = paVTerm
        self.paLTerm = paLTerm
        self.hasPumps = hasPumps

        # fill in the draw flows
        ratioCount = self.numStages
        for stage in self.useStages:
            for draw in stage.vapDrawsActive:
                if not draw.isBasis:
                    draw.flow = math.exp(self.logSFactors[ratioCount])*self.V[stage.number]
                    ratioCount += 1
                else:
                    draw.flow = self.V[stage.number]
                    
            for draw in stage.liqDrawsActive:
                if not draw.isBasis:
                    draw.flow = math.exp(self.logSFactors[ratioCount])*self.L[stage.number]
                    ratioCount += 1
                else:
                    draw.flow = self.L[stage.number]
                    
            # fill in clone flows
            for clone in stage.liqClones.values():
                clone.flow = self.L[stage.number]
                
            for clone in stage.vapClones.values():
                clone.flow = self.V[stage.number]
                
        #Method for debugging
        #TowerBalancePerStage(self)
        
        if (ratioCount - self.totCond - self.totReb) != self.numInnerEqns:
            raise SimError('EqnNumbMismatch', self.GetPath())
       
    def GetLnK(self, t, p, x, y):
        """
        Calculate the LnK values for the stages from t, p, x, y
        where those are Numeric arrays nStages long
        """
        
        
        #y = clip(transpose(transpose(y)/add.reduce(y, 1)), tiniestValue, largestValue)
        #x = clip(transpose(transpose(x)/add.reduce(x, 1)), tiniestValue, largestValue)
        
        fugacity = 'LnFugacity'
        thCaseObj = self.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        lnFugL = thAdmin.GetArrayProperty(prov, case, (T_VAR, t), (P_VAR, p),
                                          ones(self.numStages)*LIQUID_PHASE,
                                          x, fugacity)

        lnFugV = thAdmin.GetArrayProperty(prov, case, (T_VAR, t), (P_VAR, p), 
                                          ones(self.numStages)*VAPOUR_PHASE,
                                          y, fugacity)
        
        if self.debug:
            ##DEBUG CODE ##########################################
            self.lnFugL = lnFugL
            self.lnFugV = lnFugV
            ########################################################
        
        lnK = lnFugL + Numeric.log(y) - lnFugV - Numeric.log(x)
        
        if self.dokmix:
            try:
                #Three phase algorithm from Schuil & Bool paper
                #"Three phase flash and distillation". 1985
                for wdraw in self.waterDraws:
                    if wdraw.liq1Frac == None: continue
                    nuStage = wdraw.stage.number
                    wx = wdraw.x
                    wLnFug = thAdmin.GetArrayProperty(prov, case, (T_VAR, t[nuStage]), (P_VAR, p[nuStage]),
                                                       LIQUID_PHASE, wx, fugacity)
                    a = wdraw.liq1Frac
                    wlnK0 = lnK[nuStage][:]
                    wlnK1 = wLnFug + Numeric.log(y[nuStage, :]) - lnFugV[nuStage, :] - Numeric.log(wx)
                    wK0 = Numeric.exp(wlnK0)
                    wK1 = Numeric.exp(wlnK1)
                    wK = (wK0*wK1) / ( a*wK1 + (1.0-a)*wK0)
                    lnK[nuStage][:] = Numeric.log(wK)
            except:
                pass
                #self.InfoMessage('ErrorThreePhase', (self.GetPath(),))
        
        return lnK
    
    def GetBubbleLnK(self, p, x):
        """
        Calculate lnK from bubble point calc for a single composition x at p
        return (t, lnK) where t is the bubble point temperature
        """
        matDict = MaterialPropertyDict()
        matDict[P_VAR].SetValue(p, FIXED_V)
        matDict[VPFRAC_VAR].SetValue(0.0, FIXED_V)
        cmps = CompoundList(None)
        for i in range(len(x)):
            cmps.append(BasicProperty(FRAC_VAR))
        cmps.SetValues(x, FIXED_V)
        thCaseObj = self.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        liqPhases = 1
        results = thAdmin.Flash(prov, case, cmps, matDict, liqPhases, (T_VAR))
        t = results.bulkProps[0]
        y = clip(results.phaseComposition[0], tiniestValue, largestValue)
            
        return (t, y, Numeric.log(y/x))
        
    def GetEnthalpyModel(self, t, p, x, phase, oldModel = None):
        """
        calculate the H values for the stages from t, p, x and phase
        where all but phase are Numeric arrays nStages long
        """
        thCaseObj = self.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        value = transpose(thAdmin.GetProperties(prov, case, (T_VAR,t), (P_VAR, p), 
                                                ones(self.numStages)*phase,
                                                x, (H_VAR, 'Cp', 'MolecularWeight')))
        
        value[0] /= value[2]   # make enthalpy on mass basis
        value[1] /= value[2]   # make Cp on mass basis

        value[0] -= value[1]*t #self.T # convert H to A term (B is just Cp)
        newModel = Numeric.resize(value, (2,self.numStages))
        if oldModel is not None and self.dampingFactor < 1.0:
            return oldModel + (newModel - oldModel) * self.dampingFactor
        else:
            return newModel
        
    def ModelEnthalpy(self, t, x, model):
        """
        return array (nstage long) of enthalpies calculated from inner model
        t and x are arrays of termperature and mole fraction nstage long
        """
        hmass = model[0] + model[1]*t
        mw = add.reduce(x*self.mw,1)
        return hmass * mw

    def CalculateTemperatures(self):
        """
        use the Kb model to calculate new temperatures using the
        relation that for sum yi = 1 then Kb = 1/sum(alphai * xi)
        """
        ## this needs correction for efficiencies !!!
        #if min(self.L) < -1.0 or min(self.V) < -1.0: return
        Kb = Numeric.sum(self.alpha*self.x, 1)
        deltaT = self.B/(self.A + Numeric.log(Kb)) - self.T
        
        self.T += deltaT
        self.T = clip(self.T, 1.0, 10000.0)
        
    def InitOuterProperties(self):
        """
        Set up the parameters for LnKb = A - B/T
        and for the enthalpy model H = (H0 + C0*T)*Mwt
        """
        
        T = self.T
        lnK = self.GetLnK(T, self.P, self.x, self.y)
        dampingFactor = self.dampingFactor
        maxK = max(abs(transpose(lnK)))
        bptCount = 0
        for i in range(self.numStages):
            if maxK[i] < 0.5:
                try:
                    (newT, newY, newLnK) = self.GetBubbleLnK(self.P[i], self.x[i])
                    self.T[i] = newT
                    lnK[i,:] = newLnK
                    self.y[i,:] = newY
                    bptCount += 1
                except:
                    pass  # if the flash fails just keep doing what we were doing
               
        if bptCount == self.numStages and self.dampingFactor == 1.0:
            dampingFactor = 0.9   # to prevent exact error match
        else:
            dampingFactor = self.dampingFactor
            
        t2 = T + 1.0   # for numerical derivative
        lnK2 = self.GetLnK(t2, self.P, self.x, self.y)
        
        if self.debug:
            ##DEBUG CODE ##########################################
            file = self.file
            txt = '***************\nCalculating OuterProps \nStage       T             xw             xhc             yw            yhc             Kw            Khc        fugLiqw       fugLiqhc        fugVapw       fugVaphc\n'
            file.write(txt)
            wIdx = self.waterIdx
            for i in range(self.numStages):
                txt = '%5i %7.6g %14.8g  %14.8g %14.8g %14.8g %14.8g  %14.8g %14.8g %14.8g %14.8g %14.8g\n' %(i, self.T[i], 
                                                                       self.x[i, wIdx], sum(self.x[i, :])-self.x[i, wIdx], 
                                                                       self.y[i, wIdx], sum(self.y[i, 1:])-self.y[i, wIdx], 
                                                                       lnK[i, wIdx], sum(lnK[i, 1:])-lnK[i, wIdx],
                                                                       self.lnFugL[i, wIdx], sum(self.lnFugL[i, 1:])-self.lnFugL[i, wIdx],
                                                                       self.lnFugV[i, wIdx], sum(self.lnFugV[i, 1:])-self.lnFugV[i, wIdx])
                file.write(txt)
            file.write('\n\n')
            file.flush()        
            
            TowerDumpPropPerCmp(self, lnK, 'lnKValues')
            ######################################################
        
        #Keep this code commented out for whenever I want to do some sampling of the K vals
        if hasattr(self, 'doplots'):
            if self.doplots:
                wIdx = self.waterIdx
                lnKArray = zeros((10, lnK.shape[0], lnK.shape[1]), Float)
                for i in range(10):
                    lnKArray[i] = self.GetLnK(T+float(i), self.P, self.x, self.y)
                
                xtemp = array(self.x, Float)
                xtemp[:, wIdx] *= 1.1
                xtemp = clip(transpose(transpose(xtemp)/add.reduce(xtemp, 1)), tiniestValue, largestValue)
                lnKArray2 = zeros((10, lnK.shape[0], lnK.shape[1]), Float)
                for i in range(10):
                    lnKArray2[i] = self.GetLnK(T+float(i), self.P, xtemp, self.y)
                    
                lnKArray3 = zeros((10, lnK.shape[0], lnK.shape[1]), Float)
                for i in range(10):
                    xtemp2 = array(self.x, Float)
                    xtemp2[:, wIdx] *= 1.0 + 2.0*i / 10.0
                    xtemp2 = clip(transpose(transpose(xtemp2)/add.reduce(xtemp2, 1)), tiniestValue, largestValue)
                    lnKArray3[i] = self.GetLnK(T, self.P, xtemp2, self.y)
                            
        if not self.useOldCode:
            try:
                self.V = clip(self.V, smallestAllowedFlow, largestAllowedFlow)
                self.L = clip(self.L, smallestAllowedFlow, largestAllowedFlow)
                KbCurrent = Numeric.exp(self.logSFactors[:self.numStages]) * self.L / self.V
                KbCurrent[0] = KbCurrent[self.totCond]
                KbCurrent[-1] = KbCurrent[-1-self.totReb]
                lnKbCurrent = Numeric.log(KbCurrent)
            except:
                #Something is screwed up, perhaps a flow went negative
                #This sometimes happens to self.V[0] ~ -1.0E-40 for total condenser
                lnKbCurrent = None
            
        # weighting factors from Russell's paper
        dt = (1./t2 - 1./T)  # need this later
        t = clip(transpose(self.y*(lnK2 - lnK))/dt, -10000., 0.0)
        sumt = add.reduce(t)
        sumt = Numeric.where(Numeric.absolute(sumt) < tiniestValue, tiniestValue, sumt)
        w = transpose(t / sumt)
        lnKb1 = add.reduce(w*lnK, 1)
        lnKb2 = add.reduce(w*lnK2, 1)
        
        # B parameter is by difference
        oldB = None
        if self.B != None: oldB = array(self.B)
        self.B = clip((lnKb1 - lnKb2)/dt, 50., 100000.)
        if self.useOldCode:
            #Old code
            self.A = lnKb1 + self.B/T
            lnAlpha = clip(transpose(transpose(lnK) - self.A + self.B/T), logTiniestValue, logLargestValue)
            if dampingFactor < 1.0: self.alpha *= Numeric.power(Numeric.exp(lnAlpha)/self.alpha, dampingFactor)
            else: self.alpha = Numeric.exp(lnAlpha)            
        else:
            try:
                if lnKbCurrent == None or max(absolute(Numeric.exp(lnKb1) - KbCurrent)) > 20.0:
                    #Use a new Kb
                    lnKb1 = clip(lnKb1, -4.0, 7.0) #keep it bound
                    if dampingFactor < 1.0:
                        #Damp K values directly as it is meaningless to damp alpha when a new Kb is used
                        if oldB != None: oldK = self.alpha * Numeric.exp(self.A - oldB/T)
                        else: oldK = self.alpha
                        lnK = Numeric.log (oldK * Numeric.power(Numeric.exp(lnK)/oldK, dampingFactor))
                    self.A = lnKb1 + self.B/T
                    lnAlpha = clip(transpose(transpose(lnK) - self.A + self.B/T), logTiniestValue, logLargestValue)
                    
                    #Finally notify logSFactors about changes to Kb
                    self.logSFactors[:self.numStages] = Numeric.log(Numeric.exp(lnKb1) * self.V / self.L)
                else:
                    #Keep Kb constant by updating A to match it
                    if not self.A: self.A = lnKb1 + self.B/T
                    else: self.A = lnKbCurrent + self.B/T
                    
                    lnAlpha = clip(transpose(transpose(lnK) - self.A + self.B/T), logTiniestValue, logLargestValue)
                    if dampingFactor < 1.0: self.alpha *= Numeric.power(Numeric.exp(lnAlpha)/self.alpha, dampingFactor)
                    else: self.alpha = Numeric.exp(lnAlpha)
                    
            except:
                #Old code
                self.A = lnKb1 + self.B/T
                lnAlpha = clip(transpose(transpose(lnK) - self.A + self.B/T), logTiniestValue, logLargestValue)
                if dampingFactor < 1.0: self.alpha *= Numeric.power(Numeric.exp(lnAlpha)/self.alpha, dampingFactor)
                else: self.alpha = Numeric.exp(lnAlpha)
            
            
        if self.debug:
            ##DEBUG CODE ##########################################
            TowerDumpAlpha(self)
            ######################################################
            
        #Enthalpy model
        if self.isSubCool:
            if self.subCoolDT != None:
                self.hlModel = self.GetEnthalpyModel(self.T-self.subCoolDT, self.P, self.x, LIQUID_PHASE, self.hlModel)
                self.hvModel = self.GetEnthalpyModel(self.T-self.subCoolDT, self.P, self.y, VAPOUR_PHASE, self.hvModel)
            else:
                self.subCoolT[1:] = self.T[1:]
                self.stages[0].SetDegreesSubCooled(self.T[0] - self.subCoolT[0]) #Keep up to date
                self.hlModel = self.GetEnthalpyModel(self.subCoolT, self.P, self.x, LIQUID_PHASE, self.hlModel)
                self.hvModel = self.GetEnthalpyModel(self.subCoolT, self.P, self.y, VAPOUR_PHASE, self.hvModel)
        else:
            self.hlModel = self.GetEnthalpyModel(self.T, self.P, self.x, LIQUID_PHASE, self.hlModel)
            self.hvModel = self.GetEnthalpyModel(self.T, self.P, self.y, VAPOUR_PHASE, self.hvModel)
            
        for spec in self.specsWModel:
            spec.InitModel()
            
            
        
        if self.waterDraws and not self.useOldCode:
            stay = True
            maxIter = 10
            iterCnt = 0
            while stay and iterCnt < maxIter:
                #Iterate until values are positive
                #maybe it should only check in stages of the water draws
                iterCnt += 1
                for wdraw in self.waterDraws:
                    wdraw.InitializeKFactors()
                self.SolveFlowMatrix(self.logSFactors)
                stay = False
                for wdraw in self.waterDraws:
                    if min(self.l[wdraw.stage.number, :]) < (-1.0E-5):
                        stay = True
                        break
        else:
            for wdraw in self.waterDraws:
                wdraw.InitializeKFactors()
            
                    
    def InnerErrors(self):
        """
        Calculate and return the inner loop errors
        """
        
        #Calcualte enthalpies
        if self.isSubCool:
            if self.subCoolDT != None:
                hl = self.ModelEnthalpy(self.T-self.subCoolDT, self.x, self.hlModel)
                hv = self.ModelEnthalpy(self.T-self.subCoolDT, self.y, self.hvModel)
            else:
                self.subCoolT[1:] = self.T[1:]
                self.stages[0].SetDegreesSubCooled(self.T[0] - self.subCoolT[0]) #Keep up to date
                hl = self.ModelEnthalpy(self.subCoolT, self.x, self.hlModel)
                hv = self.ModelEnthalpy(self.subCoolT, self.y, self.hvModel)
        else:
            hl = self.ModelEnthalpy(self.T, self.x, self.hlModel)
            hv = self.ModelEnthalpy(self.T, self.y, self.hvModel)
                
        # basic heat balance
        errors = zeros(self.numInnerEqns, Float)
        errors[:self.numStages] = self.fQ
        scale = Numeric.absolute(self.fQ)  # scale factor

        hTerm = hl*self.L*self.RlTerm
        errors[:self.numStages] -= hTerm
        scale += Numeric.absolute(hTerm)
        
        hTerm = hv*self.V*self.RvTerm
        errors[:self.numStages] -= hTerm
        scale += Numeric.absolute(hTerm)
                
        hTerm = hl[:-1]*self.L[:-1] * (self.stageType[1:self.numStages] != TOP_STAGE)
        errors[1:self.numStages] += hTerm

        if self.hasPumps:
            errors[:self.numStages] += add.reduce(hl*self.L*self.paLTerm,1) + add.reduce(hv*self.V*self.paVTerm,1)
        
        hTerm = hv[1:]*self.V[1:]
        errors[:self.numStages-1] += hTerm * (self.stageType[:self.numStages-1] != BOTTOM_STAGE)
        
        for wdraw in self.waterDraws:
            stageNo = wdraw.stage.number
            errors[stageNo] -= wdraw.QFlow()        
        
        
        # spec errors
        numSpecsNeeded = self.numInnerEqns - self.numStages
        specErrors = []
        unknownQs = []
        
        #Pump around specs need to know the Q flows. 
        #Temporarily copy the errors into a member variable so the pump around specs
        #can take from there when their Q is unknwon
        self._lastEneErrs = array(errors)
        
        #Do some extra processing depending on the report level of tower
        if self.convRepLevel:
            eqnLbls = self.eqnLbls = []
            for i in range(self.numStages):
                eqnLbls.append('EneBalStage_%i' %i)
            for i in range(self.numStages, self.numInnerEqns):
                eqnLbls.append('ForASpec_%i' %i)
            specLbls = self.GetSpecLbls()
        
        for stage in self.useStages:
            specErrors.extend(stage.SpecErrors())
            if stage.UnknownQ():
                unknownQs.append(stage.number)
        numUnknownQs = len(unknownQs)
        numSpecsNeeded += numUnknownQs
        
        if len(specErrors) != numSpecsNeeded:
            raise SimError('WrongNumberTowerSpecs', (len(specErrors), numSpecsNeeded, self.GetPath()))
        
        i = self.numStages
        for error in specErrors:
            if numUnknownQs:
                numUnknownQs -= 1
                stageNo = unknownQs[numUnknownQs]
                self.stages[stageNo].AssignQ(errors[stageNo])
                errors[stageNo] = error
                scale[stageNo] = 1.0  # error is scaled already (I hope)
                if self.convRepLevel:
                    eqnLbls[stageNo] = specLbls.pop(0)
            else:
                errors[i] = error
                if self.convRepLevel:
                    eqnLbls[i] = specLbls.pop(0)
                i += 1
        
        errors[:self.numStages] /= scale
        
                
        return errors
    
    def GetSpecLbls(self):
        """Method used to create an ordered list of labels for each spec"""
        eqnLbl = []
            
        for stage in self.stages:
            names = stage.vapDraws.keys()
            names.sort()
            for name in names:
                draw = stage.vapDraws[name]
                for spec in draw.portSpecs:
                    eqnLbl.append('Stage_%i_VapDrawPortSpec_%s' %(stage.number, spec.__class__.__name__))
                
                for spec in draw.drawActiveSpecs:
                    eqnLbl.append(spec.GetPath())
                    
            names = stage.liqDraws.keys()
            names.sort()
            for name in names:
                draw = stage.liqDraws[name]
                for spec in draw.portSpecs:
                    eqnLbl.append('Stage_%i_LiqDrawPortSpec_%s' %(stage.number, spec.__class__.__name__))
                
                for spec in draw.drawActiveSpecs:
                    eqnLbl.append(spec.GetPath())
                    
            names = stage.vapClones.keys()
            names.sort()
            for name in names:
                draw = stage.vapClones[name]
                for spec in draw.portSpecs:
                    eqnLbl.append('Stage_%i_VapDrawPortSpec_%s' %(stage.number, spec.__class__.__name__))
                
                for spec in draw.drawActiveSpecs:
                    eqnLbl.append(spec.GetPath())
                    
            names = stage.liqClones.keys()
            names.sort()
            for name in names:
                draw = stage.liqClones[name]
                for spec in draw.portSpecs:
                    eqnLbl.append('Stage_%i_LiqDrawPortSpec_%s' %(stage.number, spec.__class__.__name__))
                
                for spec in draw.drawActiveSpecs:
                    eqnLbl.append(spec.GetPath())
                
            for spec in stage.activeSpecs:
                eqnLbl.append(spec.GetPath())
                
            if stage.type == TOP_STAGE and len(stage.vapDraws) == 0:
                # automatically add a zero flow spec if no vapour draw on top
                eqnLbl.append('Stage_%i_ZeroVapFlowSpec' %stage.number)
            elif stage.type == BOTTOM_STAGE and len(stage.liqDraws) == 0:
                # automatically add a zero flow spec if no liquid draw on bottom
                eqnLbl.append('Stage_%i_ZeroLiqFlowSpec' %stage.number)
        return eqnLbl
    
    
    def CalcJacobian(self):
        """
        Use crude numerical differences to approximate Jacobian
        return inverse
        """
        #get base values
        self.SolveFlowMatrix(self.logSFactors)
        self.CalculateTemperatures()
        baseErrors = self.InnerErrors()
        jacobian = zeros((self.numInnerEqns, self.numInnerEqns), Float)
        numInnerEqns = self.numInnerEqns
        path = self.GetPath()
        delta = 0.001
        saveT = array(self.T)
        
        #Pass a message every x calculations, so the solver doesn't look dead
        distCnt = 0
        msgEvery = self.freqJacMsg
        totCond = self.totCond
        totReb = self.totReb
        numStages = self.numStages
        #for i in range(numInnerEqns+nuWDraws):
        for i in range(numInnerEqns):
            distCnt +=1
            if distCnt == msgEvery:
                self.InfoMessage('CalcDisturbance', (i+1, numInnerEqns, path))
                distCnt = 0   
            
            sIdx = i+totCond
            if i+totCond >= numStages-1:
                sIdx += totReb
            saveSF = self.logSFactors[sIdx]
            step = delta * self.logSFactors[sIdx]
            if abs(step) < delta:
                step = delta
            self.logSFactors[sIdx] += step
            self.SolveFlowMatrix(self.logSFactors)
            self.CalculateTemperatures()
            jacobian[:,i] = (self.InnerErrors() - baseErrors)/step
            self.logSFactors[sIdx] = saveSF
            self.T[:] = saveT[:]
        self.SolveFlowMatrix(self.logSFactors)
        self.CalculateTemperatures()
        
        try:
            return inverse(jacobian)
        except:
            raise SimError('CouldNotInvertJacobian', path)
           
    def UpdateJacobian(self, B, dx, dF, rhs=None, oldRhs=None):
        """
        Use Broyden method (following Numerical Recipes in C, 9.7)
        to update inverse Jacobian
        B is previous inverse Jacobian (n x n)
        dx is delta x for last step (n)
        dF is delta errors for last step (n)
        """
        
        dotdxB = dot(dx, B)
        denom = dot(dotdxB, dF)
        if abs(denom) < tiniestValue:
            return B       # what else to do?
        
        return B + outerproduct((dx - dot(B, dF)), dotdxB)/denom
            
    def Profile(self, phase, property):
        """
        return a nstage list of property values for phase where phase is L or V
        """
        waterFree = 0
        if WATERFREE == property[:len(WATERFREE)]:
            property = property[len(WATERFREE):]
            waterFree = 1
            
        if waterFree:
            cmpNames = self.GetCompoundNames()
            if 'WATER' in cmpNames:
                idxWater = cmpNames.index('WATER')
            else:
                waterFree = 0
                
        frac = None
        if phase == TOWER_LIQ_PHASE:
            phase = LIQUID_PHASE
            try: frac = array(self.x, Float)
            except: return None
        elif phase == TOWER_VAP_PHASE:
            phase = VAPOUR_PHASE
            try: frac = array(self.y, Float)
            except: return None
        else:
            return None
        
        #Zero out the water if necessary
        if frac != None and waterFree:
            frac = array(frac, Float)
            frac[:, idxWater] *= 0.0
            frac = transpose(transpose(frac) / add.reduce(frac, 1))
            
            
        if property == FRAC_VAR or property == CMPMOLEFRAC_VAR:
            #if waterFree: return CompositionProfile(self, waterFrac)
            return CompositionProfile(self, frac)
        elif property == CMPMASSFRAC_VAR:
            #if waterFree: return MassCompositionProfile(self, waterFrac)
            return MassCompositionProfile(self, frac)
        elif property == STDVOLFRAC_VAR or property == 'IdealVolumeFraction':
            #if waterFree: IdealVolCompositionProfile(self, waterFrac)
            return IdealVolCompositionProfile(self, frac)
        elif property == MOLEFLOW_VAR:
            if phase == LIQUID_PHASE:
                if not waterFree: return self.L
                return self.L -self.l[:, idxWater]
            else:
                if not waterFree: return self.V
                return self.V -self.v[:, idxWater]
            
        elif property == MASSFLOW_VAR:
            mwts = ones(self.numStages, Float)
            thCaseObj = self.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            var1, var2 = (T_VAR,0.0), (P_VAR, 0.0)
            for i in range(self.numStages):
                moleFracs = frac[i]
                mwts[i] = thAdmin.GetProperties(prov, case, var1, var2, phase, moleFracs, ('MolecularWeight',))[0]
            if phase == LIQUID_PHASE:
                if not waterFree: return self.L*mwts
                return (self.L - self.l[:, idxWater])*mwts
            else:
                if not waterFree: return self.V*mwts
                return (self.V - self.v[:, idxWater])*mwts
            
        elif property == STDVOLFLOW_VAR:
            stdMolVol = ones(self.numStages, Float)
            thCaseObj = self.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            refT = self.GetStdVolRefT()
            var1, var2  = (T_VAR,refT), (P_VAR, 101.325)
            for i in range(self.numStages):
                moleFracs = frac[i]
                stdMolVol[i] = thAdmin.GetProperties(prov, case, var1, var2, LIQUID_PHASE, moleFracs, (STDLIQVOL_VAR,))[0]
            if phase == LIQUID_PHASE:
                if not waterFree: return self.L*stdMolVol
                return (self.L - self.l[:, idxWater])*stdMolVol
            else:
                if not waterFree: return self.V*stdMolVol
                return (self.V - self.v[:, idxWater])*stdMolVol
            
        elif property == VOLFLOW_VAR:
            
            thCaseObj = self.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            T, P = self.T, self.P
            
            #See if the molar v was already requested and loaded
            if waterFree: molVol = self.storedProfiles.get((phase, WATERFREE+MOLARV_VAR), None)
            else: molVol = self.storedProfiles.get((phase, MOLARV_VAR), None)
            if not molVol or len(molVol) != self.numStages:
                molVol = ones(self.numStages, Float)
                
                for i in range(self.numStages):
                    moleFracs = frac[i]
                    molVol[i] = thAdmin.GetProperties(prov, case, (T_VAR, T[i]), (P_VAR, P[i]), phase, moleFracs, (MOLARV_VAR,))[0]
                    
                #Load it before leaving
                if waterFree: self.storedProfiles[(phase, WATERFREE+MOLARV_VAR)] = molVol
                else: self.storedProfiles[(phase, MOLARV_VAR)] = molVol
            else:
                pass
            if phase == LIQUID_PHASE:
                if not waterFree: return self.L * molVol
                return (self.L - self.l[:, idxWater]) * molVol
            else:
                if not waterFree: return self.V * molVol
                return (self.V - self.v[:, idxWater]) * molVol
        else:       
            thCaseObj = self.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            
            #See if the molar v was already requested and loaded
            if waterFree: prof = self.storedProfiles.get((phase, WATERFREE + property), None)
            else: prof = self.storedProfiles.get((phase, property), None)
            if not prof or len(prof) != self.numStages:
                
                prof = Numeric.reshape(thAdmin.GetProperties(prov, case,
                                            (T_VAR,self.T), (P_VAR, self.P), ones(self.numStages)*phase,
                                            frac, (property,)), (self.numStages,))
                #Load it before leaving
                if waterFree: self.storedProfiles[(phase, WATERFREE + property)] = prof
                else: self.storedProfiles[(phase, property)] = prof
            else:
                pass
            return prof
        

    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(Tower, self)._RemoveFromCloneList(clone, attrNamesToClone)
        dontClone = ['initTowerObj', 'draws', 'stages', 'waterDraws', 'pProfile', 'feeds', 'converged']
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
    

    def _CloneCreate(self):
        """Clone with the __class__ call and add the stages right here"""
        clone = self.__class__()
        
        #First find out the sections
        sections = []
        lastWasTop = False
        lastWasBot = False
        for stage in self.stages:
            
            if stage.type == TOP_STAGE:
                if lastWasBot:
                    sections.append((stage.number, None))
                elif lastWasTop:
                    last = sections.pop()
                    sections.append((last[0], stage.number -1))
                    sections.append((stage.number, None))
                else:
                    sections.append((stage.number, None))
                    
                lastWasBot = False
                lastWasTop = True
                
            elif stage.type == BOTTOM_STAGE:
                if lastWasTop:
                    last = sections.pop()
                    sections.append((last[0], stage.number))
                elif lastWasBot:
                    sections.append((sections[-1][1]+1, stage.number))
                else:
                    sections.append((0, stage.number))
                lastWasBot = True
                lastWasTop = False
                
        #First find out the sections
        sectionsClone = []
        lastWasTop = False
        lastWasBot = False
        for stage in clone.stages:
            if stage.type == TOP_STAGE:
                if lastWasBot:
                    sectionsClone.append((stage.number, None))
                elif lastWasTop:
                    last = sectionsClone.pop()
                    sectionsClone.append((last[0], stage.number -1))
                    sectionsClone.append((stage.number, None))
                else:
                    sectionsClone.append((stage.number, None))
                    
                lastWasBot = False
                lastWasTop = True
                
            elif stage.type == BOTTOM_STAGE:
                if lastWasTop:
                    last = sectionsClone.pop()
                    sectionsClone.append((last[0], stage.number))
                elif lastWasBot:
                    sectionsClone.append((sectionsClone[-1][1]+1, stage.number))
                else:
                    sectionsClone.append((0, stage.number))
                lastWasBot = True
                lastWasTop = False
            
        idx = 0
        for top, bottom in sections:
            
            if len(sectionsClone) < idx + 1:
                clone.stages[-1].Add(bottom - top + 1)
                sectionsClone.append((top, bottom))
            else:
                change = 0
                topClone, bottomClone = sectionsClone[idx]
                if (bottom - top) > (bottomClone - topClone):
                    change = (bottom - top) - (bottomClone - topClone)
                    clone.stages[top].Add(change)
                elif (bottom - top) < (bottomClone - topClone):
                    change = (bottom - top) - (bottomClone - topClone)
                    clone.stages[top].Minus(-change)
                sectionsClone[idx] = (top, bottom)
                if change != 0:
                    for i in range(len(sectionsClone[idx+1:])):
                        sectionsClone[idx+1] = (sectionsClone[idx+1+i][0]+change, sectionsClone[idx+1+i][1]+change)
                    
            idx += 1
            
        
        if len(self.stages) != len(clone.stages):
            return None
        
        idx = 0
        for stage in self.stages:
            stage.CloneContents(clone.stages[idx])
            idx += 1
            
        self.pProfile.CloneContents(clone.pProfile)
        clone.converged = 0
        clone.canRestart = self.canRestart
        clone.dontRestartNextTime = self.dontRestartNextTime
        clone.convRes = copy.deepcopy(self.convRes)
        clone.numInnerEqns = self.numInnerEqns
        clone.numCompounds = self.numCompounds
        clone.totReb = self.totReb
        clone.totCond = self.totCond
        
        clone.storedProfiles = copy.deepcopy(self.storedProfiles)
        
        if self.initTowerObj != None:
            try:
                clone.initTowerObj = self.initTowerObj.Clone()
                clone.initTowerObj.SetParent(clone)
            except:
                pass
            
        return clone
        
TOWER_FEED = 'feed'        
CONDENSER_VAPOUR = 'condenserV'         #V_PORT
CONDENSER_LIQUID = 'condenserL'         #L_PORT
CONDENSER_DUTY = 'condenserQ'
REBOILER_LIQUID = 'reboilerL'           #L_PORT
REBOILER_DUTY = 'reboilerQ'
BOTTOM_FEED = 'bottomFeed'              #FEED_PORT
BOTTOM_LIQUID = 'bottomL'               #L_PORT
TOP_FEED = 'overheadFeed'               #FEED_PORT
TOP_VAPOUR = 'overheadV'                #V_PORT


class CompositionProfile(object):
    """
    container for tower composition profile - mainly to implement GetObject
    """
    def __init__(self, tower, frac):
        """
        tower is the tower
        frac is a nStage by nComp Numeric array of mole fractions
        """
        self.tower = tower
        self.frac = Numeric.transpose(frac)
        
    def GetObject(self, name):
        """
        if name is a compound name, return that mole fraction profile
        """
        cmpNames = self.tower.GetCompoundNames()
        if not name in cmpNames:
            name = re.sub('_', ' ', name)
            if name in cmpNames:
                i = cmpNames.index(name)
                return self.frac[i]
        else:
            i = cmpNames.index(name)
            return self.frac[i]
        

class MassCompositionProfile(CompositionProfile):
    """
    container for tower mass composition profile
    """
    def __init__(self, tower, frac):
        """
        tower is the tower
        frac is a nStage by nComp Numeric array of mole fractions
        """
        self.tower = tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        GetArrayProperty = thAdmin.GetArrayProperty
        var1, var2 = ('T', 0.0), ('P', 0.0)
        for i in range(tower.numStages):
            # T, P and phase are dummies
            frac[i] = GetArrayProperty(prov, case, var1, var2, VAPOUR_PHASE, frac[i], 'MassFraction')
            
        self.frac = Numeric.transpose(frac)
        
class IdealVolCompositionProfile(CompositionProfile):
    """
    container for tower ideal vol composition profile (std vol?)
    """
    def __init__(self, tower, frac):
        """
        tower is the tower
        frac is a nStage by nComp Numeric array of mole fractions
        """
        self.tower = tower
        thCaseObj = tower.GetThermo()
        thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
        refT = tower.GetStdVolRefT()
        GetArrayProperty = thAdmin.GetArrayProperty
        var1, var2 = (P_VAR, 101.325), (T_VAR, refT)
        for i in range(tower.numStages):
            frac[i] = GetArrayProperty(prov, case, var1, var2, LIQUID_PHASE, frac[i], STDVOLFRAC_VAR)
        self.frac = Numeric.transpose(frac)        
        
class DistillationColumn(Tower):
    def __init__(self, initScript = None):
        Tower.__init__(self, initScript)
        self.SetParameterValue(DAMPINGFACTOR_PAR, 1.0)
        self.SetParameterValue(INITKPOWER_PAR, 1.0)
        
        # Add one stage for feed
        self.stages[0].Add(1)
        # Create a feed and add to stage 1
        feed = Feed()
        self.stages[1].AddObject(feed, TOWER_FEED)
        # Create reflux, top vapour draw, top liquid draw, condenser duty
        # and add to stage 0
        reflux = RefluxRatioSpec()
        overheadVap = VapourDraw()
        overheadLiq = LiquidDraw()
        overheadDuty = EnergyFeed(0)
        self.stages[0].AddObject(reflux, REFLUX)
        self.stages[0].AddObject(overheadVap, CONDENSER_VAPOUR)
        self.stages[0].AddObject(overheadLiq, CONDENSER_LIQUID)
        self.stages[0].AddObject(overheadDuty, CONDENSER_DUTY)
        # Add reboiler
        reboilerDuty = EnergyFeed()
        reboilerDraw = LiquidDraw()
        self.stages[2].AddObject(reboilerDraw, REBOILER_LIQUID)
        self.stages[2].AddObject(reboilerDuty, REBOILER_DUTY)

class RefluxedAbsorber(Tower):
    def __init__(self, initScript = None):
        Tower.__init__(self, initScript)
        self.SetParameterValue(DAMPINGFACTOR_PAR, 1.0)
        self.SetParameterValue(INITKPOWER_PAR, 1.0)

        reflux = RefluxRatioSpec()
        overheadVap = VapourDraw()
        overheadLiq = LiquidDraw()
        overheadDuty = EnergyFeed(0)
        # Conderser
        self.stages[0].AddObject(reflux, REFLUX)
        self.stages[0].AddObject(overheadVap, CONDENSER_VAPOUR)
        self.stages[0].AddObject(overheadLiq, CONDENSER_LIQUID)
        self.stages[0].AddObject(overheadDuty, CONDENSER_DUTY)
        # absorber bottom
        feed = Feed()
        bottomLiquid = LiquidDraw()
        self.stages[1].AddObject(feed, BOTTOM_FEED)
        self.stages[1].AddObject(bottomLiquid, BOTTOM_LIQUID)

class ReboiledAbsorber(Tower):
    def __init__(self, initScript = None):
        Tower.__init__(self, initScript)
        self.SetParameterValue(DAMPINGFACTOR_PAR, 1.0)
        self.SetParameterValue(INITKPOWER_PAR, 1.0)
        # absorber top
        feed = Feed()
        overheadVap = VapourDraw()
        self.stages[0].AddObject(feed, TOP_FEED)
        self.stages[0].AddObject(overheadVap, TOP_VAPOUR)
        # Add reboiler
        reboilerDuty = EnergyFeed()
        reboilerDraw = LiquidDraw()
        self.stages[1].AddObject(reboilerDraw, REBOILER_LIQUID)
        self.stages[1].AddObject(reboilerDuty, REBOILER_DUTY)


class Absorber(Tower):
    def __init__(self, initScript = None):
        Tower.__init__(self, initScript)
        self.SetParameterValue(DAMPINGFACTOR_PAR, 1.0)
        self.SetParameterValue(INITKPOWER_PAR, 1.0)
        # absorber top
        feed = Feed()
        overheadVap = VapourDraw()
        self.stages[0].AddObject(feed, TOP_FEED)
        self.stages[0].AddObject(overheadVap, TOP_VAPOUR)
         # absorber bottom
        feed = Feed()
        bottomLiquid = LiquidDraw()
        self.stages[1].AddObject(feed, BOTTOM_FEED)
        self.stages[1].AddObject(bottomLiquid, BOTTOM_LIQUID)




def AdjustEffMatrixForRemoval(inputString, removeFrom, removeTo):
    """
    Return an adjusted efficiencies matrix for the removal of stages going from:
    removeFrom to removeTo. Return None if no change was required
    """
    
    if not isinstance(inputString, str): 
       return None

    outputString =''
    
    if '@' in inputString:
        #Split data per compounds and dimension an array with defaul values
        if inputString[0] == ':': 
            inputString = inputString[1:]
            outputString = ':'
            
        addAt = False
        cmpDataTokens = inputString.split('@')
        for cmpToken in cmpDataTokens:
            if addAt:
                if outputString[-1] != ' ' and outputString[-1] != ':':
                    outputString += ' '
                outputString += '@'
            else:
                addAt = True
                
            if not cmpToken: 
                continue
                
            cmpNameRaw, data = cmpToken.split(' ', 1)
            
            #Make sure it is the name of a compound
            if '-' in cmpNameRaw:
                cmpName = cmpNameRaw.split('-')
                if cmpName[0]:
                    firstVal = cmpName[0]
                else:
                    firstVal = 1.0
                if cmpName[1]:
                    secondVal = cmpName[1]
                else:
                    secondVal = 1.0
                    
            else:
                firstVal = 'notACmp'
                secondVal = 'notACmp'
            try: 
                
                float(firstVal)
                float(secondVal)
                #assume this whole token is the genericEff
                modifData = AdjustInputArrayForRemoval(cmpToken, removeFrom, removeTo)
                if modifData:
                    outputString += modifData
                else:
                    outputString += cmpToken

            except: 
                #First token is not a number so it can be assumed to be a compound
                modifData = AdjustInputArrayForRemoval(data, removeFrom, removeTo)
                if modifData:
                    outputString += cmpNameRaw + ' ' + modifData
                else:
                    outputString += cmpNameRaw + ' ' + data
                    
    else:
        outputString = AdjustInputArrayForRemoval(inputString, removeFrom, removeTo)
    
    return outputString

def AdjustInputArrayForRemoval(inputString, removeFrom, removeTo, defaultValue = 1.0):    
    """
    Return an adjusted array (vector) for the removal of stages going from:
    removeFrom to removeTo. Return None if no change was required
    """
    
    outputString = ''
    
    if not inputString:
        return None
    
    if inputString[0] == ':':
        inputString = inputString[1:]
        outputString = ':'
        
    tokens = inputString.split()
    if len(tokens) == 1:
        return None

    totRemoved = removeTo - removeFrom + 1
    addSpace = False
    while tokens:
        if addSpace and outputString and outputString[-1] != ' ':
            outputString += ' '
        else:
            addSpace = True
            
        indexString = tokens.pop(0)
        if tokens:
            value = tokens.pop(0)
        else:
            value = defaultValue
            
        indicies = indexString.split('-')
        keepValue = True
        if len(indicies) == 2:
            isInside = False
            if indicies[0]:
                firstIndex = int(indicies[0])
                
                if firstIndex < removeFrom:
                    outputString += indicies[0] + '-'
                    
                    if not indicies[1]:
                        pass
                    else:
                        lastIndex = int(indicies[1])
                        if lastIndex < removeFrom:
                            outputString += indicies[1]
                        elif lastIndex > removeTo:
                            outputString += str(lastIndex - totRemoved)
                        else:
                            outputString += str(removeFrom-1)
                        
                elif firstIndex > removeTo:
                    outputString += str(firstIndex - totRemoved) + '-'
                    if not indicies[1]:
                        pass
                    else:
                        lastIndex = int(indicies[1])
                        outputString += str(lastIndex - totRemoved)
                    
                else:
                    if not indicies[1]:
                        outputString += str(removeFrom) + '-'
                    else:
                        lastIndex = int(indicies[1])
                        if indicies[1] > removeTo:
                            outputString += str(removeFrom) + '-'
                            outputString += str(lastIndex - totRemoved)
                        else:
                            keepValue = False
                        
            elif indicies[1]:
                lastIndex = int(indicies[1])
                if lastIndex < removeFrom:
                    outputString += '-' + indicies[1]
                elif lastIndex > removeTo:
                    outputString += '-' + str(lastIndex - totRemoved)
                else:
                    outputString += '-' + str(removeFrom - 1)
                                    
            else:
                keepValue = False
            
        else:
            idx = int(indicies[0])
            if idx < removeFrom:
                outputString += indicies[0]
            elif idx > removeTo:
                outputString += str(idx - totRemoved)
            else:
                keepValue = False
                
        if keepValue:
            outputString += ' ' + str(value)
            
            
    return outputString
    
    
            
def BuildEfficienciesMatrix(inputString, numberElements, cmpNames, defaultValue = 1.0):
    """This method returns a Numeric array of efficiencies for each compound for each stage in the tower
    It uses the implementation of ParseInputArray to do most of the work
    To specify a set of efficiencies for a compound just 
    
    ':0 .32 1 .18 8 .91 @PROPANE 0 .2 1 .4 2 .6 3-7 .7 @n-BUTANE 1 .3 4-5 .8 6- .4 @CARBON_DIOXIDE -3 .2 4 .6'
    """
    
    numCompounds = len(cmpNames)
    
    if isinstance(inputString, str) and '@' in inputString:
        
        #Use detail
        
        #Keep track of which compounds have not been specified
        colsNotUsed = range(numCompounds)
        
        #Flag if a set of generic efficiencies have been used yet
        #(i.e. a set of values with out an associated compound)
        usesGenericEff = False
        
        #Split data per compounds and dimension an array with defaul values
        if inputString[0] == ':': inputString = inputString[1:]
        cmpDataTokens = inputString.split('@')
        eff = ones((numberElements, numCompounds), Float) * defaultValue
        genericEff = None
        for cmpToken in cmpDataTokens:
            if not cmpToken: continue
            cmpName, data = cmpToken.split(' ', 1)
            #cmpName = cmpName.strip() ... not needed
            cmpName = re.sub('_', ' ', cmpName )
            if cmpName in cmpNames:
                col = cmpNames.index(cmpName)
                data = data.strip()
                stageEff = ParseInputArray(data, numberElements)
                eff[:, col] = clip(stageEff[:], 0.0, 1.0)
                if col in colsNotUsed:
                    colsNotUsed.remove(col)
            elif not usesGenericEff:        
                
                if '-' in cmpName:
                    cmpName = cmpName.split('-')
                    if cmpName[0]:
                        firstVal = cmpName[0]
                    else:
                        firstVal = 1.0
                    if cmpName[1]:
                        secondVal = cmpName[1]
                    else:
                        secondVal = 1.0
                        
                else:
                    firstVal = 'notACmp'
                    secondVal = 'notACmp'
                    
                try: 
                    float(firstVal)
                    float(secondVal)
                    #assume this whole token is the genericEff
                    genericEff = ParseInputArray(cmpToken, numberElements)
                    usesGenericEff = True
                except: 
                    #Not a number and a non selected compound. Just ignore
                    pass

            
        #Finally set the generic eficiencies that were not given for specific compounds
        if usesGenericEff:
            for col in colsNotUsed:
                eff[:, col] = clip(genericEff[:], 0.0, 1.0)
        
    else:
        #Use same eff for all compounds
        stageEff = ParseInputArray(inputString, numberElements)
        stageEff = clip(stageEff, 0.0, 1.0)
        eff = Numeric.reshape(Numeric.repeat(stageEff, numCompounds), (numberElements, numCompounds))   
    
    return eff
    

def ParseInputArray(inputString, numberElements, defaultValue = 1.0):
    """
    takes an input string which has pairs of index values elements and returns
    a Numeric Array numberElements long with values as indicated in the string.

    The string should start with a colon so it isn't confused with a number
    A simple form would be :0 .2 1 .4 2 .6 which would return [.2, .4, .6]
    Dashes can be used to indicate ranges (no spaces though) :0-3 .2 4 .6 yields [.2 .2 .2 .2 .6]
    A dash with nothing following means a range extending to the last element.
    A dash with nothing in front goes from 0 to the number following the dash.
    Elements not mentioned are assigned the defaultValue
    As a special case, a single token without an index is assigned to all elements and
      in this case the leading colon can be omitted.
    """    
    if isinstance(inputString, float) or isinstance(inputString, int):
        return ones(numberElements, Float) * inputString
    
    # hack to get it going
    inputString = re.sub('_', ' ', inputString)
    
    if inputString[0] == ':':
        inputString = inputString[1:]
    tokens = inputString.split()
    if len(tokens) == 1:
        return ones(numberElements, Float) * float(tokens[0])
    returnValues = ones(numberElements, Float) * defaultValue

    while tokens:
        indexString = tokens.pop(0)
        if tokens:
            value = tokens.pop(0)
        else:
            value = defaultValue
            
        indicies = indexString.split('-')
        if len(indicies) == 2:
            if indicies[0]:
                firstIndex = int(indicies[0])
            else:
                firstIndex = 0
            if indicies[1]:
                lastIndex = int(indicies[1]) + 1
            else:
                lastIndex = numberElements
            if lastIndex > numberElements:
                lastIndex == numberElements
            put(returnValues, range(firstIndex, lastIndex), float(value))
        else:
            idx = int(indicies[0])
            if idx < numberElements:
                returnValues[idx] = float(value)

    return returnValues



if __name__ == '__main__':
    #Test ParseInpuArrayMethod
    inputString = '0.9'
    numStages = 13
    numCompounds = 5
    stageEff = ParseInputArray(inputString, numStages)
    eff = Numeric.reshape(Numeric.repeat(stageEff, numCompounds), (numStages, numCompounds))
    
    inputString = ':0 .2 1 .4 2 .6'
    stageEff = ParseInputArray(inputString, numStages)
    eff = Numeric.reshape(Numeric.repeat(stageEff, numCompounds), (numStages, numCompounds))    
    
    inputString = ':0-3 .2 4 .6'
    stageEff = ParseInputArray(inputString, numStages)
    eff = Numeric.reshape(Numeric.repeat(stageEff, numCompounds), (numStages, numCompounds))
    
    inputString = ':-2 .32 4 .18 8 .91 @PROPANE 0 .2 1 .4 2 .6 3-7 .7 @n-BUTANE 1 .3 4-5 .8 6- .4 @CARBON_DIOXIDE -3 .2 4 .6'
    numStages = 13
    cmpNames = ['PROPANE', 'n-BUTANE', 'ISOBUTANE', 'n-PENTANE']
    
    eff = BuildEfficienciesMatrix(inputString, numStages, cmpNames)
    print eff
    
    #lets switch order
    cmpNames = ['PROPANE', 'ISOBUTANE', 'n-BUTANE', 'n-PENTANE']
    eff = BuildEfficienciesMatrix(inputString, numStages, cmpNames)
    print eff
    
    
    #lets add a compound
    cmpNames = ['PROPANE', 'CARBON DIOXIDE', 'n-BUTANE', 'n-PENTANE']
    eff = BuildEfficienciesMatrix(inputString, numStages, cmpNames)
    print eff
    
    
    #Now get rid of the generic efficiencies 
    inputString = ':@PROPANE 0 .2 1 .4 2 .6 3-7 .7 @n-BUTANE 1 .3 4-5 .8 6- .4 @CARBON_DIOXIDE -3 .2 4 .6'
    eff = BuildEfficienciesMatrix(inputString, numStages, cmpNames)
    print eff    
    
    #Now specify things as usual
    inputString = '0.9'
    eff = BuildEfficienciesMatrix(inputString, numStages, cmpNames)
    print eff
    inputString = ':0 .2 1 .4 2 .6'
    eff = BuildEfficienciesMatrix(inputString, numStages, cmpNames)
    print eff    
    
    
    
    
class ProfileProperty(BasicProperty):
    """Crude light weight implementation of the BasicProperty from Variables.py"""
    def __init__(self, typeName, parent):
        """Init a property with everything as None or unknown
        typeName is the string indicating the type of variable (T_VAR, P_VAR etc)
        port is the port to which the property will belong
        """
        
        super(ProfileProperty, self).__init__(typeName, None)
        
        #This should be the unit operation (in this case the Tower)
        self.parent = parent
        self._unitop = parent.GetParent()
        self.idx = -1
        
    def __str__(self):
        """very basic representation"""
        return 'ProfileProperty ' + self._type.name
    
    def CleanUp(self):
        """
        clean up before deleting
        """
        super(ProfileProperty, self).CleanUp()
        self.parent = None
        self._unitop = None
        
    def SetIndex(self, idx):
        """Set the index of the property with respect to the wole profile"""
        self.idx = idx
        
    def GetIndex(self):
        """Returns the index of this property"""
        return self.idx
        
    def SetValue(self, value, calcStatus=CALCULATED_V):
        """used to assign a value to the property"""
        
        if calcStatus & FIXED_V:
            if value == None:
                calcStatus = UNKNOWN_V
            else:
                value = float(value)
        
        if calcStatus & FIXED_V:
            if self._calcStatus == calcStatus and value == self._value:
                return
            self._calcStatus = calcStatus
            self._value = value
            self._unitop.ForgetAllCalculations()
            
        elif calcStatus == UNKNOWN_V:
            if value != None:
                raise SimError('SetValueUnknownNotNone')
            if self._calcStatus & UNKNOWN_V:
                return  # already unknown
            
            self._calcStatus = UNKNOWN_V
            self._value = None
            self._unitop.ForgetAllCalculations()
            
        elif calcStatus & (CALCULATED_V):
            # ignore attempts to calculate or pass unknown values
            if value == None: return
            
            # is there already a value
            #Just check tolerance
            if self.GetValue() != None:
                self.CheckTolerance(value)
            else:
                #No need to "notify" yet
                self._calcStatus = calcStatus
                self._value = value
                
        else:
            raise SimError('InvalidCalcStatusInSet')

    def Forget(self, connProp=None, skipStatus=0):
        """
        forget value if it has been calculated, but is not a new value
        connProp is a BasicProperty connected to this one or None
        if skipStatus is not 0 then variable will only be skipped if _calcStatus
        has one of the skipStatus bits set
        """
        if skipStatus and not(skipStatus & self._calcStatus):
            return
        
        if (self._calcStatus & CALCULATED_V):
            self._calcStatus = UNKNOWN_V
            self._value = None
                
                
    def CheckTolerance(self, value):
        """check to see if value is tolerably equal to the current value
        If not place on parent flowsheet consistency error list
        """
        tolerance = self._unitop.GetTolerance()
        error = self.CalculateError(value)
        if error > tolerance:
            self._unitop.PushConsistencyError(self, value)        

    def GetName(self):
        return 'Item%d' %self.GetIndex()
            
    def GetPath(self):
        return "%s.%s" %(self.parent.GetPath(), self.GetName())

    def GetParent(self):
        """return parent"""
        return self.parent
        
        
class ProfileObj(object):
    def __init__(self, parent, typeName, name="Profile"):
        self.parent = parent
        self.name = name
        self.props = []
        self.typeName = typeName
        self.type = PropTypes.get(typeName, PropTypes[GENERIC_VAR])

    def GetType(self):
        return self.type
        
    def CleanUp(self):
        """Clean up"""
        self.parent = None
        self.type = None
        map(ProfileProperty.CleanUp, self.props)
        
    def SetSize(self, size):
        """Dimensions the profile. Just appends or deletes to thed end of the profile"""
        
        currSize = len(self.props)
        
        #Delete if needed
        map(ProfileProperty.CleanUp, self.props[size:])
        del self.props[size:]
             
        
        for i in range(currSize, size):
            self.AddProperty()
            
        #Re assign all the indexes
        map(ProfileProperty.SetIndex, self.props, range(size))
        
    def GetSize(self):
        return len(self.props)
            
    def AddProperty(self, idx=-1):
        """Add a property in the given index, if idx=-1, then append at the end"""
        if idx == -1:
            self.props.append(ProfileProperty(self.typeName, self))
            size = len(self.props)
            self.props[-1].SetIndex(size-1)
        else:
            self.props.insert(idx, ProfileProperty(self.typeName, self))
            #Re assign all the indexes
            size = len(self.props)
            map(ProfileProperty.SetIndex, self.props[idx:], range(idx, size))
        
    def RemoveProperty(self, idx=-1):
        """Remove a property in the given index, if idx=-1, then remove from the end"""
        if idx == -1:
            prop = self.props.pop()
            prop.CleanUp()
        else:
            self.props[idx].CleanUp()
            del self.props[idx]
            #Re assign all the indexes
            size = len(self.props)
            map(ProfileProperty.SetIndex, self.props[idx:], range(idx, size))
            
            
    def RemoveProperties(self, fromIdx, toIdx):
        """Remove properties by a range of indexes"""
        for i in range(fromIdx, toIdx+1):
            self.props[i].CleanUp()
        
        del self.props[fromIdx:toIdx+1]
        #Re assign all the indexes
        size = len(self.props)
        map(ProfileProperty.SetIndex, self.props[fromIdx:], range(fromIdx, size))
        
            
    def GetName(self):
        return self.name
    
    def GetParent(self):
        return self.parent
    
    def GetPath(self):
        return "%s.%s" %(self.parent.GetPath(), self.name)
    
    def GetProperties(self):
        """return the object that holds all the properties"""
        return self.props
    
    def SetValues(self, values, status=CALCULATED_V):
        """Set the values of the whoel profile. status applies to all the values"""
        
        #Make status a list in case it is an integer
        if isinstance(status, int):
            s = len(self.props)
            status = [status]*s
        
        #Loop with map
        map(ProfileProperty.SetValue, self.props, values, status)
        
    def GetValues(self):
        """Get all the values in one single vector"""
        values = map(ProfileProperty.GetValue, self.props)
        return values
        
    def Forget(self):
        """Call th forget of each property"""
        map(ProfileProperty.Forget, self.props)
        
    def GetObject(self, desc):
        if desc[:4] == 'Item':
            try:
                idx = int(desc[4:])
                return self.props[idx]
            except:
                None
                              
        elif desc == 'Size':
            return len(self.props)
        
        elif desc == 'Values':
            return self.GetValues()
        
        elif desc == 'Values':
            return self.GetValues()
        
        elif desc == 'UnitType':
            return self.type.unitType
        
        elif desc == 'Details':
            #Just pas a list of tuples withe value, status and type id
            def DetailedTuple(prop):
                return (prop.GetValue(), prop.GetCalcStatus(), self.type.unitType)
            
            return map(DetailedTuple, self.props)
        
    def DeleteObject(self, prop):
        """This call is used by the cli and is intended to set the value of the prop as None"""
        prop.SetValue(None, UNKNOWN_V)

    def CloneContents(self, clone):
        if self.GetSize() != clone.GetSize():
            clone.SetSize(self.GetSize())
             
        idx = 0
        for prop in self.props:
            propClone = clone.props[idx]
            if prop._calcStatus & FIXED_V:
                propClone._calcStatus = prop._calcStatus
                propClone._value = prop._value
            idx += 1
        
        
class InitializeTower(object):
    def __init__(self):
        self.name = None
        self.tower = None
        
    def __str__(self):
        return "Default initialization for the tower"
    
    def Initialize(self, tower, name='Initialize'):
        """Method that looks like then one in the tower that gets called once the object is added to the parent"""
        self.tower = tower
        self.name = name
        
        
    def GetName(self): return self.name
    
    def GetParent(self): return self.tower

    def SetParent(self, parent): self.tower = parent
    
    def GetPath(self): return '%s.%s' %(self.tower.GetPath(), self.name)
    
    def CleanUp(self): self.tower = None
        
    def SetUpArrays(self, initMode):
        """
        Initialize the arrays needed to solve column
        initMode can be:
            SCRATCH_INIT = 0
            RESTART_INIT = 1
            LASTCONV_INIT = 2
            
        This method should initialize:
            All the mole flows in all the material draws
            self.alpha, 
            tower.logSFactors,
            where 
                 Kij = alphaij*Kbj
                 Sj = Kbj*Vj/Lj        from j=0-numStages-1
                 Sj = drawmoleflow/Vj  from j=numStages-numEquations. Vj changes to Lj for liquid draws
            not that this implies that very likely this method has to initialize Vj, Lj, Tj
            
        This method should load
            self.f, self.fQ
            
        This method should solve for
            self.P
            
        
        """
        
        tower = self.tower
        
        self.InitializeMemberVariables(tower, initMode)
        self.LoadSubCoolingInfo(tower, initMode)
        self.ResetDraws(tower, initMode)
        self.SolveP_LoadFinalInfo(tower, initMode)
        self.EstimateAlpha(tower, initMode)
        self.EstimateDraws(tower, initMode)
        self.LoadEfficiencies(tower, initMode)
        self.EstimateL_V_And_logS(tower, initMode)
        
        
    def InitializeMemberVariables(self, tower, initMode):
        
        if not initMode:
            #If starting from scratch
            tower.flowMatrix = zeros((tower.numStages, tower.numStages), Float)
            tower.T = zeros(tower.numStages, Float)
            tower.V = zeros(tower.numStages, Float)
            tower.L = zeros(tower.numStages, Float)
            tower.v = zeros((tower.numStages, tower.numCompounds), Float)
            tower.l = zeros((tower.numStages, tower.numCompounds), Float)
            tower.alpha = ones((tower.numStages, tower.numCompounds), Float)
            #Can not init logSFactors yet
        
        #Pressure is calculated here
        tower.P = zeros(tower.numStages, Float)
        
        #Either the sub cool DT or the subcooled T must be known
        tower.isSubCool = False
        tower.subCoolDT = None
        tower.subCoolT = None
        
        #Stage types
        tower.stageType = zeros(tower.numStages)
        
        #Feeds and draws
        tower.f = zeros((tower.numStages, tower.numCompounds), Float)
        tower.fQ = zeros(tower.numStages, Float)
        tower.feeds = []
        tower.draws =[]
        tower.waterDraws = []
        tower.sections = []
        tower.specsWModel = []
        tower.mainFeed = None
        
        #Equations
        tower.numInnerEqns = 0
        
        #Efficiencies
        tower.useEff = 0
        tower.eff = None
        
    def LoadSubCoolingInfo(self, tower, initMode):
        """Load the subcooling variables"""
        
        #Either the sub cool DT or the subcooled T must be known
        if tower.stages[0].IsSubCooled():
            infovector = zeros(tower.numStages, Float)
            tower.isSubCool = True
            tower.subCoolDT = tower.stages[0].GetDegreesSubCooled()
            if tower.subCoolDT == None:
                tower.subCoolT = tower.stages[0].GetSubCooledTemp()
                if tower.subCoolT == None:
                    raise SimError('MissingSubCoolInfo', (tower.GetPath(),))
                else:
                    #Keep it as a vector to make code easier
                    infovector[0] = tower.subCoolT
                    tower.subCoolT = infovector
            else:
                #Keep it as a vector to make code easier
                if tower.subCoolDT == 0.0:
                    tower.isSubCool = False
                else:
                    infovector[0] = tower.subCoolDT
                    tower.subCoolDT = infovector
                
    def ResetDraws(self, tower, initMode):
        """Reset feeds and draws"""
                
        tower.sections = []
        sections = tower.sections
        lastWasTop = False
        lastWasBot = False
        for stage in tower.stages:
            tower.stageType[stage.number] = stage.type
            
            if stage.type == TOP_STAGE:
                if lastWasBot:
                    sections.append((stage.number, None))
                elif lastWasTop:
                    last = sections.pop()
                    sections.append((last[0], stage.number -1))
                    sections.append((stage.number, None))
                else:
                    sections.append((stage.number, None))
                    
                lastWasBot = False
                lastWasTop = True
                
            elif stage.type == BOTTOM_STAGE:
                if lastWasTop:
                    last = sections.pop()
                    sections.append((last[0], stage.number))
                elif lastWasBot:
                    sections.append((tower.sections[-1][1]+1, stage.number))
                else:
                    sections.append((0, stage.number))
                lastWasBot = True
                lastWasTop = False
                        
            # reset all feed pumpFromDraw references
            for feed in stage.feeds.values():
                feed.pumpFromDraw = None
                tower.feeds.append(feed)
                
        if not tower.feeds:
            raise SimError('TwrNoFeed', (tower.GetPath(),))
        
        # reset stage variables and make draw list
        #Can not use prevoius for loop because of pumparounds being reset
        for stage in tower.stages:
            stage.Reset(initMode)
            draws = stage.liqDraws.values() + stage.vapDraws.values()
            tower.draws.extend(draws)
            for draw in draws:
                for spec in draw.drawActiveSpecs:
                    if hasattr(spec,'InitModel'):
                        tower.specsWModel.append(spec)
            
            # make list of water draws
            if stage.waterDraw: tower.waterDraws.append(stage.waterDraw)
                
    def SolveP_LoadFinalInfo(self, tower, initMode):
        """Solve for Pressure and could also use the same loop to load more information such
        as feeds
        """
        
        
        #Calculate P and estimate T profiles. 
        #Also load water draws, feed and feedQ values
        
        lastPStage = None
        lastP = None
        useFeedP = useConnT = False
        lastTStage = None
        lastT = None
        aFeedTemp = None

        pProps = tower.pProfile.GetProperties()
        for j in range(tower.numStages):
            stage = tower.stages[j]
            
            if tower.stageType[j] == TOP_STAGE:
                lastP = None
                ##If it is a lower section of the tower (side stripper)
                ##then use the internal connections (feeds) as sources for pressure
                if j:
                    useFeedP = True
            
            # count the number of inner equations needed
            #True means that it will only take into account draws that are not zero flow
            tower.numInnerEqns += stage.NumberInner(True) 
            
            # get total feeds
            stage.TotalFeed(tower.f[j])

            # make list of water draws
            #if stage.waterDraw: tower.waterDraws.append(stage.waterDraw)
                
            # note conversion from W to KJ/hr
            qFlow = stage.TotalQFlow()
            if qFlow:
                tower.fQ[j] = qFlow * 3.6
            
            # establish pressure profile
            p = pProps[j].GetValue()
            if p == None:
                #Not given in the profile object, see if it can be obtained in one of the
                #objects from the stage
                p = stage.GetPressure(useFeedP)

            if p:
                if lastPStage == None:
                    lastPStage = -1
                    lastP = p
                elif lastP == None:
                    lastP = p
                    
                intP = tower.CreateLinearDistList(j - lastPStage + 1, lastP, p)
                put(tower.P, range(lastPStage + 1, j + 1), array(intP[1:]))
                lastPStage = j
                lastP = p

            #elif j == tower.numStages - 1:
            elif tower.stageType[j] == BOTTOM_STAGE:
                if lastP == None:
                    #If it made it all the way here, it means that this is the last stage
                    #of a side stripper (not the main section) and that it could not find
                    #a pressure for it. This could not be caught in NeedToSolve
                    #so an error has to be raised so the calculation stops.
                    #This should not happen if the side stripper is internally connected such that 
                    #it can get a Pressure from its internal connections
                    raise SimError('TowerNoPressure', tower.GetPath())
                
                p = lastP
                intP = tower.CreateLinearDistList(j - lastPStage + 1, lastP, p)
                put(tower.P, range(lastPStage + 1, j + 1), array(intP[1:]))
                lastPStage = j
                
            if not initMode:
                # estimate temperature profile
                t = stage.EstimateTemperature()
                if t == None and stage.type == TOP_STAGE:
                    #Reset variables
                    aFeedTemp = None
                    lastT = None
                    if j:
                        #Is a side stripper. 
                        #Use the t already estimated for the connected stage above 
                        useConnT = True
                    aFeedTemp = t = stage.LargestFeedTemperature(useConnT)
                    
                elif aFeedTemp == None:
                    aFeedTemp = stage.LargestFeedTemperature(useConnT)
                    
                if t != None:
                    if lastTStage == None:
                        lastTStage = -1
                        lastT = t
                    elif lastT == None:
                        lastT = t
                        
                    intT = tower.CreateLinearDistList(j - lastTStage + 1, lastT, t)
                    put(tower.T, range(lastTStage + 1, j + 1), array(intT[1:]))
                    lastTStage = j
                    lastT = t
                elif tower.stageType[j] == BOTTOM_STAGE: #j == tower.numStages - 1:
                    if lastT == None:
                        #Should it even come here??
                        lastT = aFeedTemp
                        lastTStage = -1
                        
                    t = lastT
                    intT = tower.CreateLinearDistList(j - lastTStage + 1, lastT, t)
                    put(tower.T, range(lastTStage + 1, j + 1), array(intT[1:]))
                    lastTStage = j
            
                    
        tower.totalFeedFlow = add.reduce(tower.f.flat)  # used for missing draws and error scaling
                    
                    
    def EstimateAlpha(self, tower, initMode):
        """In this case, Alpha has the same values as K"""
        
        #Estimate K values
        if not initMode:
            thCaseObj = tower.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            if tower.initKPower != 0:
                tower.alpha = thAdmin.GetIdealKValues(prov, case, tower.T, tower.P)

                # kludgy knob to change initial K guesses
                if tower.initKPower != 1.0:
                    tower.alpha = Numeric.power(tower.alpha, tower.initKPower)
                    
                if tower.waterDraws:
                    stageNo = tower.numStages + 1
                    for wDraw in tower.waterDraws:
                        # use T and P from highest
                        stageNo = min(stageNo, wDraw.stage.number)
                        
                    feedComp = Numeric.add.reduce(tower.f,0) / Numeric.add.reduce(tower.f.flat)
                    compounds = CompoundList(None)
                    for i in range(tower.numCompounds):
                        prop = BasicProperty(FRAC_VAR)
                        prop.SetValue(feedComp[i], FIXED_V)
                        compounds.append(prop)
                    compounds.Normalize()
    
                    props = MaterialPropertyDict()
                    props[T_VAR].SetValue(tower.T[stageNo], FIXED_V)
                    props[P_VAR].SetValue(tower.P[stageNo], FIXED_V)
                        
                    results = thAdmin.Flash(prov, case, compounds, props, 2, (H_VAR, 'Cp'))
                    waterFlow = tower.totalFeedFlow * results.phaseFractions[2]

                    numWaterDraws = len(tower.waterDraws)
                    for wDraw in tower.waterDraws:
                        wDraw.flow = waterFlow / numWaterDraws
                        wDraw.wEnthalpy = results.phaseProps[2][0]
                        wDraw.wCp = results.phaseProps[2][1]
                        wDraw.baseT = tower.T[stageNo]
                        wDraw.moleFlows = array(results.phaseComposition[2]) * wDraw.flow                    
                
            else:
                # if k power is 0, use T, P flash on combined feeds for initial K values
                tower.alpha = ones((tower.numStages, tower.numCompounds), Float)
                feedComp = Numeric.add.reduce(tower.f,0) / Numeric.add.reduce(tower.f.flat)
                compounds = CompoundList(None)
                for i in range(tower.numCompounds):
                    prop = BasicProperty(FRAC_VAR)
                    prop.SetValue(feedComp[i], FIXED_V)
                    compounds.append(prop)
                compounds.Normalize()

                props = MaterialPropertyDict()
                for i in range(tower.numStages):
                    props[T_VAR].SetValue(tower.T[i], FIXED_V)
                    props[P_VAR].SetValue(tower.P[i], FIXED_V)
                    
                    results = thAdmin.Flash(prov, case, compounds, props, 1, ())
                    tower.alpha[i:] = Numeric.clip(results.phaseComposition[VAPOUR_PHASE],tiniestValue, 1.0)/ \
                        Numeric.clip(results.phaseComposition[LIQUID_PHASE],tiniestValue, 1.0)
                    
                
    def EstimateDraws(self, tower, initMode):
        """Estimate a value for the missing draws"""
    
        drawFlow = 0
        missingDrawFlows = 0
        for draw in tower.draws:
            if draw.flow != None:
                drawFlow += draw.flow
            else:
                missingDrawFlows += 1
                
        #Estimate missing flow in draws
        if missingDrawFlows:
                        
            remainingDraw = tower.totalFeedFlow - drawFlow
            if remainingDraw < 0.:
                remainingDraw = 0.3 * tower.totalFeedFlow  # arbitrary positive flow
            perDrawFlow = remainingDraw / missingDrawFlows
            for draw in tower.draws:
                if draw.flow == None:
                    draw.flow = perDrawFlow
                        
            
    def LoadEfficiencies(self, tower, initMode):
        """Loads the efficiencies matrix"""
        
        #Now calculate efficiencies
        tower.useEff = 0
        efficiencies = tower.GetParameterValue(EFFICIENCIES_PAR)
        if efficiencies:
            stagesToCheck = []
            #eff already comes "clipped" between 0.0 and 1.0 and per compound
            eff = BuildEfficienciesMatrix(efficiencies, tower.numStages, tower.cmpNames, 1.0)
            
            if min(eff) < 1.0:
                tower.useEff = 1
                tower.eff = eff
                for stage in tower.stages:
                    # check for top stages without vapour draws
                    if stage.type == TOP_STAGE:
                        # see if there is a vapour draw used as the flow basis for this stage
                        hasVapDraw = 0
                        for draw in stage.vapDraws.values():
                            if draw.isBasis:
                                hasVapDraw = 1
                                break;
                            
                        if not hasVapDraw:
                            tower.eff[stage.number] = ones(tower.numCompounds, Float)
                        else:
                            if min(eff[stage.number]) < 1.0:
                                try:
                                    if draw.flow != None and draw.flow < 1.0E-4:
                                        #Low vap flow, then set top eff to 1.0
                                        tower.eff[stage.number] = ones(tower.numCompounds, Float)
                                        ##Don't use this one for now
                                        tower.InfoMessage('TowerEffSetToOne', ())
                                        #stagesToCheck.append(stage.number)
                                except:
                                    pass
                                
                        
    def EstimateL_V_And_logS(self, tower, initMode):
        """Estimate L and V profiles"""
        
        if not initMode:
            # set up stage flows
            vapFromBelow = 0.
            liqFromAbove = 0.
            for stage in tower.stages:
                #Make initial estimates for flows leaving stage
                #This counts on being called in order from top to bottom
    
                # get vap and liq feed and draw totals
                totalVapFeed = 0.
                totalLiqFeed = 0.
                for feed in stage.feeds.values():
                    totalVapFeed += feed.TotalVapourFlow()
                    totalLiqFeed += feed.TotalLiquidFlow()
                    if feed.pumpFromDraw and feed.pumpFromDraw.flow:
                        if feed.pumpFromDraw.phase == TOWER_VAP_PHASE:
                            totalVapFeed += feed.pumpFromDraw.flow
                        else:
                            totalLiqFeed += feed.pumpFromDraw.flow
                    
                totalVapDraw = 0.0
                for draw in stage.vapDraws.values():
                    totalVapDraw += draw.flow
                    
                totalLiqDraw = 0.0
                for draw in stage.liqDraws.values():
                    totalLiqDraw += draw.flow
                    
                if stage.waterDraw and stage.waterDraw.flow:
                    totalLiqDraw += stage.waterDraw.flow
                    
                    
                vapFlow = vapFromBelow   # vapFromBelow calculated from stage above
                liqFlow = 0.             # temporary value
                
                # if this is a top stage, then use a guessed (or estimated) reflux ratio
                # to determine a liquid leaving.  Vapour leaving will be the basis draw
                # or zero
                if stage.type == TOP_STAGE:
                    liqFromAbove = 0.
                    # see if we can estimate liquid flow
                    reflux = stage.EstimateReflux()
                    if reflux > 0.0:
                        liqFlow = (totalLiqDraw + totalVapDraw) * reflux
                    else:
                        liqFlow = totalLiqFeed - totalLiqDraw
    
                    if liqFlow <= 0.0:
                        #Estimate a reflux ratio
                        reflux = 2.0
                        liqFlow = (totalLiqDraw + totalVapDraw) * reflux  
    
                    
                    # see if there is a vapour draw used as the flow basis for this stage
                    for draw in stage.vapDraws.values():
                        if draw.isBasis:
                            vapFlow = draw.flow
                            totalVapDraw -= draw.flow  # so it isn't counted twice
                            break;
                        
                if stage.type == BOTTOM_STAGE:
                    # not elif or else, because the else to this should occur for both other types
                    vapFromBelow = 0.
                    # see if there is a liquid draw used as the flow basis for this stage
                    for draw in stage.liqDraws.values():
                        if draw.isBasis:
                            liqFlow = draw.flow
                            break;
                        
                if liqFlow == 0.:
                    #Balance in the liquid
                    liqFlow = totalLiqFeed - totalLiqDraw + liqFromAbove
                         
                            
                    # set some minimum flow
                    minLiqFlow = (vapFlow + totalLiqDraw + totalVapDraw)* 0.001
                    liqFlow = max(liqFlow, minLiqFlow)
                        
                if stage.type != BOTTOM_STAGE:
                    # figure vapFromBelow by mole balance
                    vapFromBelow =  (vapFlow + liqFlow + totalVapDraw + totalLiqDraw
                                    - liqFromAbove - totalVapFeed - totalLiqFeed)
                    # set a minimum
                    minVapFlow = (vapFlow + liqFlow + totalLiqDraw + totalVapDraw) * 0.1
                    vapFromBelow = max(vapFromBelow, minVapFlow)
                        
                    
                    
                liqFromAbove = liqFlow
                tower.V[stage.number] = vapFlow
                tower.L[stage.number] = liqFlow
                ## probably need to add estimate checks
                
                
            #Initialize stripping factors
            totCond = tower.stages[0].totCond
            totReb = tower.stages[-1].totReb
            tower.logSFactors = ones(tower.numInnerEqns+totCond+totReb, Float)
            tower.L = clip(tower.L, smallestAllowedFlow, largestAllowedFlow)
            tower.V = clip(tower.V, smallestAllowedFlow, largestAllowedFlow)
            tower.logSFactors[:tower.numStages] = Numeric.log(tower.V/tower.L) # assume initial Kb = 1
                
            # Initialize the draw ratios - must be in correct  order        
            tower.numDrawRatios = tower.numInnerEqns - tower.numStages-totCond-totReb
            ratioCount = tower.numStages
            for stage in tower.stages:
                if ratioCount-totCond-totReb >= tower.numInnerEqns:
                    break    # skip rest of loop once all have been found
                #names = stage.vapDraws.keys()
                #names.sort()
                #for name in names:
                    #draw = stage.vapDraws[name]
                for draw in stage.vapDrawsActive:
                    if not draw.isBasis:
                        tower.logSFactors[ratioCount] = math.log(draw.flow/tower.V[stage.number])
                        ratioCount += 1
                        
                #names = stage.liqDraws.keys()
                #names.sort()
                #for name in names:
                    #draw = stage.liqDraws[name]
                for draw in stage.liqDrawsActive:
                    if not draw.isBasis:
                        drawFlow = max(draw.flow, smallestAllowedFlow)
                        tower.logSFactors[ratioCount] = math.log(drawFlow/tower.L[stage.number])
                        ratioCount += 1
                    
            if ratioCount - totCond - totReb != tower.numInnerEqns:
                raise SimError('EqnNumbMismatch', tower.GetPath())
        

        



            
    def Clone(self):
        clone = self.__class__()
        clone.name = self.name
        return clone
        
def TowerDumpPropPerCmp(tower, prop, label='lnKvals'):
    try:
        f = file = tower.file
        txt = '*************** %s **********************\n' %label
        f.write(txt)
        txt = 'Stage '
        f.write(txt)
        baseLen = 14
        length = baseLen*ones(len(tower.cmpNames), Int)
        
        for j in range(len(tower.cmpNames)):
            cmpName = re.sub(' ', '_', tower.cmpNames[j])
            length[j] = max(len(cmpName), baseLen)
            txt = '%*s ' %(length[j], cmpName)
            f.write(txt)
        txt = '\n'
        f.write(txt)

        for i in range(tower.numStages):
            txt = '%5i' %i
            f.write(txt)
            for j in range(len(tower.cmpNames)):
                txt = '%*.8g ' %(length[j], prop[i, j])
                file.write(txt)
            txt = '\n'
            f.write(txt)
        file.write('\n\n')
        file.flush()    
    except:
        pass
    
def TowerDumpFlowsPerCmp(tower):
    try:
        f = file = tower.file
        txt = '*************** Vapour flow per compound**********************\n'
        f.write(txt)
        txt = 'Stage '
        f.write(txt)
        baseLen = 14
        length = baseLen*ones(len(tower.cmpNames), Int)
        
        for j in range(len(tower.cmpNames)):
            cmpName = tower.cmpNames[j]
            length[j] = max(len(cmpName), baseLen)
            txt = '%*s ' %(length[j], cmpName)
            f.write(txt)
        txt = '\n'
        f.write(txt)

        for i in range(tower.numStages):
            txt = '%5i' %i
            f.write(txt)
            for j in range(len(tower.cmpNames)):
                txt = '%*.8g ' %(length[j], tower.v[i, j])
                file.write(txt)
            txt = '\n'
            f.write(txt)
        file.write('\n\n')
        file.flush()
        
        
        txt = '*************** Liquid flow per compound**********************\n'
        f.write(txt)
        txt = 'Stage '
        f.write(txt)
        baseLen = 14
        length = baseLen*ones(len(tower.cmpNames), Int)
        
        for j in range(len(tower.cmpNames)):
            cmpName = re.sub(' ', '_', tower.cmpNames[j])
            length[j] = max(len(cmpName), baseLen)
            txt = '%*s ' %(length[j], cmpName)
            f.write(txt)
        txt = '\n'
        f.write(txt)

        for i in range(tower.numStages):
            txt = '%5i' %i
            f.write(txt)
            for j in range(len(tower.cmpNames)):
                txt = '%*.8g ' %(length[j], tower.l[i, j])
                file.write(txt)
            txt = '\n'
            f.write(txt)
        file.write('\n\n')
        file.flush()

    except:
        pass
    
def TowerDumpAlpha(tower):
    try:
        f = file = tower.file
        txt = '*************** lnAlpha**********************\n'
        f.write(txt)
        txt = 'Stage '
        f.write(txt)
        baseLen = 14
        length = baseLen*ones(len(tower.cmpNames), Int)
        
        for j in range(len(tower.cmpNames)):
            cmpName = re.sub(' ', '_', tower.cmpNames[j])
            length[j] = max(len(cmpName), baseLen)
            txt = '%*s ' %(length[j], cmpName)
            f.write(txt)
            
        txt = '\n'
        f.write(txt)

        for i in range(tower.numStages):
            txt = '%5i' %i
            f.write(txt)
            for j in range(len(tower.cmpNames)):
                txt = '%*.8g ' %(length[j], Numeric.log(tower.alpha[i, j]))
                file.write(txt)
            txt = '\n'
            f.write(txt)
        file.write('\n\n')
        file.flush()
           

    except:
        pass
    
    
def TowerBalancePerStage(tower):
    """Handy method for debugging balances. Not part of tower solution scheme"""
    try:
        for stage in tower.stages:
            nuStage = stage.number
            matbal = 0.0
            for draw in stage.liqDraws.values():
                if not draw.isBasis:
                    matbal -= draw.flow
            for draw in stage.vapDraws.values():
                if not draw.isBasis:
                    matbal -= draw.flow
            for feed in stage.feeds.values():
                if feed.pumpFromDraw:
                    matbal += feed.pumpFromDraw.flow
                else:
                    matbal += feed.flow
            if stage.waterDraw:
                if stage.waterDraw.flow:
                    matbal -= stage.waterDraw.flow
                
            matbal -= tower.V[nuStage]
            matbal -= tower.L[nuStage]
            if stage.type != TOP_STAGE:
                matbal += tower.L[nuStage-1]
            if stage.type != BOTTOM_STAGE:
                matbal += tower.V[nuStage+1]
            tower.InfoMessage('MaterialBalance', ('Stage: %i Bal: %g' %(nuStage, matbal),))
    except:
        tower.InfoMessage('FailedMaterialBalance')
        
def TowerBalanceStage(tower, stage, ignore=None):
    """Handy method for debugging balances. Not part of tower solution scheme"""
    
    nuStage = stage.number
    matbal = 0.0
    for draw in stage.liqDraws.values():
        if not draw.isBasis:
            matbal -= draw.flow
    for draw in stage.vapDraws.values():
        if not draw.isBasis:
            matbal -= draw.flow
    for feed in stage.feeds.values():
        if feed.pumpFromDraw:
            matbal += feed.pumpFromDraw.flow
        else:
            matbal += feed.flow
    if stage.waterDraw:
        if stage.waterDraw.flow:
            matbal -= stage.waterDraw.flow
        
    matbal -= tower.V[nuStage]
    matbal -= tower.L[nuStage]
    if stage.type != TOP_STAGE:
        matbal += tower.L[nuStage-1]
    if stage.type != BOTTOM_STAGE:
        matbal += tower.V[nuStage+1]
    tower.InfoMessage('MaterialBalance', ('Stage: %i Bal: %g' %(nuStage, matbal),))
        
        
def TowerOverallBalancePerSection(tower):
    """Handy method for debugging balances. Not part of tower solution scheme"""
    
    try:
        cnt = 0
        for section in tower.sections:
            top, bottom = section
            matbal = 0.0
            enebal = 0.0
            cnt += 1
            for stage in tower.stages[top: bottom+1]:
                nuStage = stage.number
                
                for draw in stage.liqDraws.values():
                    matbal -= draw.port.GetPropValue(MOLEFLOW_VAR)
                    enebal -= draw.port.GetPropValue(ENERGY_VAR)
                    
                for draw in stage.vapDraws.values():
                    matbal -= draw.port.GetPropValue(MOLEFLOW_VAR)
                    enebal -= draw.port.GetPropValue(ENERGY_VAR)
                    
                if stage.waterDraw:
                    if stage.waterDraw.flow:
                        matbal -= stage.waterDraw.port.GetPropValue(MOLEFLOW_VAR)
                        enebal -= stage.waterDraw.port.GetPropValue(ENERGY_VAR)
                        
                for feed in stage.feeds.values():
                    val = feed.port.GetPropValue(MOLEFLOW_VAR)
                    if val == None and feed.pumpFromDraw:
                        val = feed.pumpFromDraw.port.GetPropValue(MOLEFLOW_VAR)
                    matbal += val
                    
                    val = feed.port.GetPropValue(ENERGY_VAR)
                    if val == None and feed.pumpFromDraw:
                        val = feed.pumpFromDraw.port.GetPropValue(ENERGY_VAR)
                    enebal += val
                    
                for feed in stage.qfeeds.values():
                    if feed.incoming:
                        enebal += feed.port.GetValue()
                    else:
                        enebal -= feed.port.GetValue()
                        
            tower.InfoMessage('OverallMatBalance', ('Section: %i MatBal: %g kmol/h' %(cnt, matbal),))
            tower.InfoMessage('OverallEneBalance', ('Section: %i EneBal: %g J/s' %(cnt, enebal),))
        
    except:
        #Quit silently
        pass
    
    
    
    
    
        
