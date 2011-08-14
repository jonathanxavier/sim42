
from sim.solver import EquationSolver
from sim.solver.Variables import *
from sim.solver.Messages import MessageHandler

from sim.unitop import UnitOperations, Balance

from numpy.oldnumeric import array, zeros, ones, Float, Int, pi, where
import numpy
PI = pi  #To be consistent, make pi uppercase like any other constant


EFFIC_PAR = 'Efficiency'

PROCESS_PORT = 'Process'
MOTIVE_PORT = 'Motive'
DISCHARGE_PORT = 'Discharge'
NOZZLE_DIAM_PORT = 'NozzleDiameter'
THROAT_DIAM_PORT = 'ThroatDiameter'

#Constant to refer to a specific fraction of the ejector
_P_FRACS = 0
_M_FRACS = 1
_D_FRACS = 2


#Load a fixed index for each unknown
w1Idx, w2Idx, w3Idx, p1Idx, p2Idx, p3Idx, S1Idx, S2Idx, S3Idx = range(9)
v1Idx, v2Idx, v3Idx, H1Idx, H2Idx, H3Idx, d1Idx, d2Idx, d3Idx = range(9, 18)

class EjectorOp(EquationSolver.EquationBasedOp):
    """Class for the ejector unit op. Inherits from UnitOperation"""
    def __init__(self, initScript=None):
        """Init the ejector

        Init Info:
        Efficiency = 1.0

        """
        
        super(EjectorOp, self).__init__(initScript)
        self.SetParameterValue(EquationSolver.SOLVE_METH_PAR, EquationSolver.NR)
        
        
        #Init Efficiency as 1.0
        self.SetParameterValue(EFFIC_PAR, 1.0)

        #Material ports
        p = self.CreatePort(IN|MAT, PROCESS_PORT)
        m = self.CreatePort(IN|MAT, MOTIVE_PORT)
        d = self.CreatePort(OUT|MAT, DISCHARGE_PORT)

        #Signal ports
        nozzDiam = self.CreatePort(SIG, NOZZLE_DIAM_PORT)
        thrDiam = self.CreatePort(SIG, THROAT_DIAM_PORT)
        nozzDiam.SetSignalType(LENGTH_VAR)
        thrDiam.SetSignalType(LENGTH_VAR)

        p.SetLocked(True)
        m.SetLocked(True)
        d.SetLocked(True)
        nozzDiam.SetLocked(True)
        thrDiam.SetLocked(True)

        #Load a balance
        self._balance = Balance.Balance(Balance.MOLE_BALANCE)
        self._balance.AddInput(self.GetPorts(IN|MAT))
        self._balance.AddOutput(self.GetPorts(OUT|MAT))       
        
        #Setting for simoultaneous solution
        self._nuUnk = 18
        self._lowBoundLst = self._nuUnk*[None]
        self._unkName = self._nuUnk*['']
        self._canBeSpec = self._nuUnk*[False]
        self._nuEqns = 10

        #Member variables that are used during solution
        self._matProcess = None
        self._matMotive = None
        self._matDischarge = None
        self._unkFracs = None #Any value for now
        self._pFracs = None
        self._mFracs = None
        self._dFracs = None
        self._pureCmpMW = None
        self._thCaseObj = None
        self._eff = None

        #Lower bounds are wrong, should support negatives
        self._lowBoundLst[w1Idx] = -1E+30
        self._lowBoundLst[w2Idx] = -1E+30
        self._lowBoundLst[w3Idx] = -1E+30
        self._lowBoundLst[p1Idx] = 0.000001
        self._lowBoundLst[p2Idx] = 0.000001
        self._lowBoundLst[p3Idx] = 0.000001
        self._lowBoundLst[S1Idx] = 0.00001
        self._lowBoundLst[S2Idx] = 0.00001
        self._lowBoundLst[S3Idx] = 0.00001
        self._lowBoundLst[v1Idx] = -1E+30
        self._lowBoundLst[v2Idx] = -1E+30
        self._lowBoundLst[v3Idx] = -1E+30
        self._lowBoundLst[H1Idx] = -1E+30
        self._lowBoundLst[H2Idx] = -1E+30
        self._lowBoundLst[H3Idx] = -1E+30
        self._lowBoundLst[d1Idx] = 0.0000000001
        self._lowBoundLst[d2Idx] = 0.0000000001
        self._lowBoundLst[d3Idx] = 0.0000000001
        
        #Indicate if a variable can be used as a spec when deciding if there is enough known info to solve
        self._canBeSpec[w1Idx] = True
        self._canBeSpec[w2Idx] = True
        self._canBeSpec[w3Idx] = True
        self._canBeSpec[p1Idx] = True
        self._canBeSpec[p2Idx] = True
        self._canBeSpec[p3Idx] = True
        self._canBeSpec[S1Idx] = True
        self._canBeSpec[S2Idx] = True
        self._canBeSpec[S3Idx] = True
        self._canBeSpec[v1Idx] = False
        self._canBeSpec[v2Idx] = False
        self._canBeSpec[v3Idx] = False
        self._canBeSpec[H1Idx] = True
        self._canBeSpec[H2Idx] = True
        self._canBeSpec[H3Idx] = True
        self._canBeSpec[d1Idx] = False
        self._canBeSpec[d2Idx] = False
        self._canBeSpec[d3Idx] = False      
        
        self._unkName[w1Idx] = 'W1'
        self._unkName[w2Idx] = 'W2'
        self._unkName[w3Idx] = 'W3'
        self._unkName[p1Idx] = 'P1'
        self._unkName[p2Idx] = 'P2'
        self._unkName[p3Idx] = 'P3'
        self._unkName[S1Idx] = 'S1'
        self._unkName[S2Idx] = 'S2'
        self._unkName[S3Idx] = 'S3'
        self._unkName[v1Idx] = 'v1'
        self._unkName[v2Idx] = 'v2'
        self._unkName[v3Idx] = 'v3'
        self._unkName[H1Idx] = 'H1'
        self._unkName[H2Idx] = 'H2'
        self._unkName[H3Idx] = 'H3'
        self._unkName[d1Idx] = 'Den1'
        self._unkName[d2Idx] = 'Den2'
        self._unkName[d3Idx] = 'Den3'

        self.UpdateStructure()

    def DeleteObject(self, obj):
        if isinstance(obj, UnitOperations.OpParameter):
            if obj.GetName() == EFFIC_PAR:
                self.InfoMessage('CantDeleteObject', (obj.GetPath(),), MessageHandler.errorMessage, 1)
                return

        super(EjectorOp, self).DeleteObject(obj)        
        
    def UpdateStructure(self):
        """Update contents and references based on current state of parent unitop"""
        super(EjectorOp, self).UpdateStructure()
        uo = self
        
        #Get materials ports
        self._matProcess = uo.GetPort(PROCESS_PORT)
        self._matMotive = uo.GetPort(MOTIVE_PORT)
        self._matDischarge = uo.GetPort(DISCHARGE_PORT) 
        
        #Get signal ports
        self._sigNozzDiam = uo.GetPort(NOZZLE_DIAM_PORT)
        self._sigThrDiam = uo.GetPort(THROAT_DIAM_PORT)

    def GetNuSpecsNeeded(self):
        #Number of specs needed is just a substractions on unknwons - nu equations
        return self._nuUnk - self._nuEqns
        

    def PrepareForSolve(self):
        if not super(EjectorOp, self).PrepareForSolve():
            return False
        
        ready = True
        
        uo = self

        #Get thermo
        self._thCaseObj = uo.GetThermo()
        if not self._thCaseObj:
            ready = False
        else:
            thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case

        #Get molecular weights
        nuCmps = len(self._matProcess.GetCompositionValues())
        if not nuCmps: 
            ready = False
        else:
            MWLst = []
            for i in range(nuCmps):
                #Note: cmpMwt is an array with only one element because only one prop (Mwt) was requested
                MWLst.append(thAdmin.GetSelectedCompoundProperties(prov, case, i, 'MolecularWeight')[0])
            self._pureCmpMW = array(MWLst, Float)

        self._eff = self.GetParameterValue(EFFIC_PAR)
        if self._eff == None:
            ready = False
        
        self._nuCmps = nuCmps

        self._balance.DoBalance()
        self.FlashAllPorts()
        
        return ready
        

    def AssignResults(self, vals):
        """Assign the results into the appropriate ports"""
        
        vals = self.ConvertFromMKS(vals)
        isFix = self._unknowns.GetIsFixed()
        nuCmps = self._nuCmps
        pFrac = self._pFracs
        mFrac = self._mFracs
        dFrac = self._dFracs

        _MW1Val = Numeric.sum(pFrac*self._pureCmpMW)
        _MW2Val = Numeric.sum(mFrac*self._pureCmpMW)
        _MW3Val = Numeric.sum(dFrac*self._pureCmpMW)
        
        
        port = self._matProcess
        if not isFix[w1Idx]:
            port.SetPropValue(MASSFLOW_VAR, vals[w1Idx], CALCULATED_V)
        if not isFix[p1Idx]:
            port.SetPropValue(P_VAR, vals[p1Idx], CALCULATED_V)
        if not isFix[H1Idx]:
            port.SetPropValue(H_VAR, vals[H1Idx]*_MW1Val, CALCULATED_V)
        if self._unkFracs == _P_FRACS:
            port.SetCompositionValues(self._pFracs, CALCULATED_V)

        port = self._matMotive
        if not isFix[w2Idx]:
            port.SetPropValue(MASSFLOW_VAR, vals[w2Idx], CALCULATED_V)
        if not isFix[p2Idx]:
            port.SetPropValue(P_VAR, vals[p2Idx], CALCULATED_V)
        if not isFix[H2Idx]:
            port.SetPropValue(H_VAR, vals[H2Idx]*_MW2Val, CALCULATED_V)
        if self._unkFracs == _M_FRACS:
            port.SetCompositionValues(self._mFracs, CALCULATED_V)
                
        port = self._matDischarge
        if not isFix[w3Idx]:
            port.SetPropValue(MASSFLOW_VAR, vals[w3Idx], CALCULATED_V)
        if not isFix[p3Idx]:
            port.SetPropValue(P_VAR, vals[p3Idx], CALCULATED_V)
        if not isFix[H3Idx]:
            port.SetPropValue(H_VAR, vals[H3Idx]*_MW3Val, CALCULATED_V)
        if self._unkFracs == _D_FRACS:
            port.SetCompositionValues(self._dFracs, CALCULATED_V)
                
        port = self._sigNozzDiam
        if not isFix[S2Idx]: 
            diam = Numeric.sqrt(4.0*vals[S2Idx]/PI)
            port.SetValue(diam, CALCULATED_V)
 
        port = self._sigThrDiam
        if not isFix[S3Idx]: 
            diam = Numeric.sqrt(4.0*vals[S3Idx]/PI)
            port.SetValue(diam, CALCULATED_V)
        
        
                
    def LoadUnknowns(self, u):
        """Load the unknown variables. Returns False is there are not enough known variables"""
        #Load vars in a convenient way

        p, m, d = self._matProcess, self._matMotive, self._matDischarge

        #Load everything into lists (in order to allow for None values) which then will be converted to Numeric vectors
        unkNamLst = self._unkName
        unkValLst = self._nuUnk*[None]
        unkInitValLst = self._nuUnk*[None]
        unkIsFixLst = self._nuUnk*[False]
        unkScaleFact = self._nuUnk*[1.0]
        
        
        #First load everytihng that is already known!!

        #Load some unknown vals
        unkValLst[w1Idx] = w1Val = p.GetPropValue(MASSFLOW_VAR)
        unkValLst[w2Idx] = w2Val = m.GetPropValue(MASSFLOW_VAR)
        unkValLst[w3Idx] = w3Val = d.GetPropValue(MASSFLOW_VAR)
        
        #Can not use three mass flows as specs
        self._canBeSpec[w3Idx] = where((w1Val!=None and w2Val!=None), False, True)
        
        unkValLst[p1Idx] = p1Val = p.GetPropValue(P_VAR)
        unkValLst[p2Idx] = p2Val = m.GetPropValue(P_VAR)
        unkValLst[p3Idx] = p3Val = d.GetPropValue(P_VAR)

        unkValLst[d1Idx] = d1Val = p.GetPropValue(MASSDEN_VAR)
        unkValLst[d2Idx] = d2Val = m.GetPropValue(MASSDEN_VAR)
        unkValLst[d3Idx] = d3Val = d.GetPropValue(MASSDEN_VAR)
        
        nozzDiamVal = self._sigNozzDiam.GetValue()
        thrDiamVal = self._sigThrDiam.GetValue()
        if nozzDiamVal != None and thrDiamVal != None:
            if thrDiamVal <= nozzDiamVal or nozzDiamVal <= 0.0 or thrDiamVal <= 0.0:
                self.InfoMessage('WrongDiamEjector', (self.GetPath(), nozzDiamVal, thrDiamVal),addToUnitOpMsg=1)
                return False
        

        _H1MolVal = p.GetPropValue(H_VAR)
        _H2MolVal = m.GetPropValue(H_VAR)
        _H3MolVal = d.GetPropValue(H_VAR)
        
        _MW1Val = p.GetPropValue(MOLEWT_VAR)
        _MW2Val = m.GetPropValue(MOLEWT_VAR)
        _MW3Val = d.GetPropValue(MOLEWT_VAR)

        self._pFracs = pFracs = p.GetCompositionValues()
        self._mFracs = mFracs = m.GetCompositionValues()
        self._dFracs = dFracs = d.GetCompositionValues()
        nuCmps = len(pFracs)

        
        #Two ports must have full known fracs. Make fractions Numeric arrays
        if None in pFracs:
            self._unkFracs = _P_FRACS
            if None in mFracs or None in dFracs:
                return False #Can not solve
            else:
                self._mFracs = array(self._mFracs, Float)
                self._dFracs = array(self._dFracs, Float)
        elif None in mFracs:
            self._unkFracs = _M_FRACS
            if None in dFracs:
                return False #Can not solve
            self._pFracs = array(self._pFracs, Float)
            self._dFracs = array(self._dFracs, Float)
        elif None in dFracs:
            self._unkFracs = _D_FRACS
            self._pFracs = array(self._pFracs, Float)
            self._mFracs = array(self._mFracs, Float)
        else:
            self._unkFracs = None
            self._pFracs = array(self._pFracs, Float)
            self._mFracs = array(self._mFracs, Float)
            self._dFracs = array(self._dFracs, Float)

            
        #In case ports were flashed but some vars are not there (only density in this case)
        if d1Val == None and p1Val != None and _H1MolVal != None and self._unkFracs != _P_FRACS:
            unkValLst[d1Idx] = d1Val = self.GetDensity(p1Val, _H1MolVal, pFracs)
        if d2Val == None and p2Val != None and _H2MolVal != None and self._unkFracs != _M_FRACS:
            unkValLst[d2Idx] = d2Val = self.GetDensity(p2Val, _H2MolVal, mFracs)
        if d3Val == None and p3Val != None and _H3MolVal != None and self._unkFracs != _D_FRACS:
            unkValLst[d3Idx] = d3Val = self.GetDensity(p3Val, _H3MolVal, dFracs)

            
        #Calculate surfaces
        S1Val = None
        if nozzDiamVal != None: S2Val = (PI/4.0) * (nozzDiamVal**2)
        else: S2Val = None
        if thrDiamVal != None: S3Val = (PI/4.0) * (thrDiamVal**2)
        else: S3Val = None
        unkValLst[S1Idx] = S1Val
        unkValLst[S2Idx] = S2Val
        unkValLst[S3Idx] = S3Val
            
        
        #Finally try to see if v are known
        if not None in (w1Val, d1Val, S1Val):
            unkValLst[v1Idx] = v1Val = w1Val/d1Val/S1Val
        else:
            unkValLst[v1Idx] = v1Val = None
            
        if not None in (w2Val, d2Val, S2Val):
            unkValLst[v2Idx] = v2Val = w2Val/d2Val/S2Val
        else:
            unkValLst[v2Idx] = v2Val = None

        if not None in (w3Val, d3Val, S3Val):
            unkValLst[v3Idx] = v3Val = w3Val/d3Val/S3Val
        else:
            unkValLst[v3Idx] = v3Val = None

        #Load Mass enthalpies
        if _H1MolVal != None and _MW1Val != None:
            unkValLst[H1Idx] = H1Val = _H1MolVal/_MW1Val
        else:
            unkValLst[H1Idx] = H1Val = None
        
        if _H2MolVal != None and _MW2Val != None:
            unkValLst[H2Idx] = H2Val = _H2MolVal/_MW2Val
        else:
            unkValLst[H2Idx] = H2Val = None
        
        if _H3MolVal != None and _MW3Val != None:
            unkValLst[H3Idx] = H3Val = _H3MolVal/_MW3Val
        else:
            unkValLst[H3Idx] = H3Val = None
        
        
        #If not enough info is known then return False
        cnt = 0
        for i in range(self._nuUnk):
            if unkValLst[i] != None and self._canBeSpec[i]:
                cnt += 1
                
        if self._nuUnk - self._nuEqns > cnt:
            return False

        #Load lists with info on which vals are knwon(fixed) already
        for i in range(self._nuUnk):
            v = unkValLst[i]
            if v != None and self._canBeSpec[i]:
                unkIsFixLst[i] = True


        #Now create necessary estimates
        #Mass flows
        lst = [w1Val, w2Val, w3Val]
        nuNones = lst.count(None)
        if nuNones == 1:
            if w1Val == None: w1Val = -w2Val + w3Val
            elif w2Val == None: w2Val = -w1Val + w3Val
            elif w3Val == None: w3Val = w1Val + w2Val
        elif nuNones == 2:
            if w1Val != None:
                w2Val = w1Val*10.0
                w3Val = w1Val + w2Val
            elif w2Val != None:
                w1Val = w2Val/10.0
                w3Val = w1Val + w2Val
            elif w3Val != None:
                w1Val = w3Val*1.0/10.0
                w2Val = w3Val*9.0/10.0
        elif nuNones == 3:
            #What to do?
            w1Val = 20.0
            w2Val = 30.0
            w3Val = w1Val + w2Val        

        unkValLst[w1Idx] = w1Val
        unkValLst[w2Idx] = w2Val
        unkValLst[w3Idx] = w3Val

        #Do fractions
        if self._unkFracs != None:
            if self._unkFracs == _P_FRACS:
                mFlows = self._mFracs*(w2Val/Numeric.sum(self._pureCmpMW*self._mFracs))
                dFlows = self._dFracs*(w3Val/Numeric.sum(self._pureCmpMW*self._dFracs))
                self._pFracs = -mFlows+dFlows
                self._pFracs = self._pFracs/Numeric.sum(self._pFracs)   #Normalize
            elif self._unkFracs == _M_FRACS:
                pFlows = self._pFracs*(w1Val/Numeric.sum(self._pureCmpMW*self._pFracs))
                dFlows = self._dFracs*(w3Val/Numeric.sum(self._pureCmpMW*self._dFracs))
                self._mFracs = -pFlows+dFlows
                self._mFracs = self._mFracs/Numeric.sum(self._mFracs)   #Normalize
            elif self._unkFracs == _D_FRACS:
                pFlows = self._pFracs*(w1Val/Numeric.sum(self._pureCmpMW*self._pFracs))
                mFlows = self._mFracs*(w2Val/Numeric.sum(self._pureCmpMW*self._mFracs))
                self._dFracs = pFlows+mFlows
                self._dFracs = self._dFracs/Numeric.sum(self._dFracs)   #Normalize
                

        #Pressures
        lst = [p1Val, p2Val, p3Val]
        nuNones = lst.count(None)
        if nuNones == 1:
            if p1Val == None: p1Val = p3Val/5
            elif p2Val == None: p2Val = p1Val*10.0
            elif p3Val == None: p3Val = p1Val*5.0
        elif nuNones == 2:
            if p1Val != None:
                p2Val = p1Val*10.0
                p3Val = p1Val*5.0
            elif p2Val != None:
                p1Val = p2Val/10.0
                p3Val = p1Val*5.0
            elif p3Val != None:
                p1Val = p3Val/5.0
                p2Val = p1Val*10.0
        elif nuNones == 3:
            #What to do?
            p1Val = 101.0
            p2Val = 800.0
            p3Val = 500.0   
        unkValLst[p1Idx] = p1Val
        unkValLst[p2Idx] = p2Val
        unkValLst[p3Idx] = p3Val
        

        #Enthalpies
        if None in (H1Val, H2Val, H3Val):
            (H1Val, H2Val, H3Val) = self.FillInWithAverage((H1Val, H2Val, H3Val))
            if None in (H1Val, H2Val, H3Val):
                #What to do??
                #Could estimate a T and get H from there
                H1Val = H2Val = H3Val = 10000.0
        unkValLst[H1Idx] = H1Val
        unkValLst[H2Idx] = H2Val
        unkValLst[H3Idx] = H3Val
        

        #Densities
        if None in (d1Val, d2Val, d3Val):
            (d1Val, d2Val, d3Val) = self.FillInWithAverage((d1Val, d2Val, d3Val))
            if None in (d1Val, d2Val, d3Val):
                #What to do??
                #Could get it from flashing the estimates of H and P
                d1Val = d2Val = d3Val = 1000.0
        unkValLst[d1Idx] = d1Val
        unkValLst[d2Idx] = d2Val
        unkValLst[d3Idx] = d3Val


        #Surfaces
        lst = [S1Val, S2Val, S3Val]
        nuNones = lst.count(None)
        if nuNones == 1:
            if S1Val == None: S1Val = -S2Val + S3Val
            elif S2Val == None: S2Val = -S1Val + S3Val
            elif S3Val == None: S3Val = S1Val + S2Val
        elif nuNones == 2:
            if S1Val != None:
                S2Val = S1Val/2.0
                S3Val = S1Val + S2Val
            elif S2Val != None:
                S1Val = S2Val*2.0
                S3Val = S1Val + S2Val
            elif S3Val != None:
                S1Val = S3Val*2.0/3.0
                S2Val = S3Val/3.0
        elif nuNones == 3:
            #What to do?
            S1Val = 20.0
            S2Val = 10.0
            S3Val = S1Val + S2Val
        unkValLst[S1Idx] = S1Val
        unkValLst[S2Idx] = S2Val
        unkValLst[S3Idx] = S3Val

        
        #Velocities. Estimate based in known or newly estimated values
        unkValLst[v1Idx] = v1Val = w1Val/d1Val/S1Val
        unkValLst[v2Idx] = v2Val = w2Val/d2Val/S2Val
        unkValLst[v3Idx] = v3Val = w3Val/d3Val/S3Val

        #Load scale factors based on the numbers that the solver will be working with
        self.scaleFactorW = min(abs(w1Val), abs(w2Val), abs(w3Val))
        if not self.scaleFactorW: self.scaleFactorW = 1.0
        self.scaleFactorS = S2Val
        self.scaleFactorP = min(p1Val, p2Val, p3Val)
        self.scaleFactorPS = self.scaleFactorP*self.scaleFactorS
        self.scaleFactorH = min(abs(H1Val), abs(H2Val), abs(H3Val))
        if not self.scaleFactorH: self.scaleFactorH = 10.0
        self.scaleFactorD = min(d1Val, d2Val, d3Val)
        self.scaleFactorv = min(abs(v1Val), abs(v2Val), abs(v3Val))
        if not self.scaleFactorv: self.scaleFactorv = 10.0
        
        #Put them in place for solver
        unkScaleFact[p1Idx] = self.scaleFactorP
        unkScaleFact[w1Idx] = self.scaleFactorW
        unkScaleFact[d1Idx] = self.scaleFactorD
        unkScaleFact[S1Idx] = self.scaleFactorS
        unkScaleFact[v1Idx] = self.scaleFactorv
        unkScaleFact[H1Idx] = self.scaleFactorH
        
        #Do unit conversion
        unkValLst = self.ConvertToMKS(unkValLst)
        unkScaleFact = self.ConvertToMKS(unkScaleFact)
        self.scaleFactorP = unkScaleFact[p1Idx]
        self.scaleFactorW = unkScaleFact[w1Idx]
        self.scaleFactorD = unkScaleFact[d1Idx]
        self.scaleFactorS = unkScaleFact[S1Idx]
        self.scaleFactorv = unkScaleFact[v1Idx]
        self.scaleFactorH = unkScaleFact[H1Idx]
        self.scaleFactorPS = self.scaleFactorP*self.scaleFactorS
        
        #Load the unknowns object
        unkInitValLst = list(unkValLst)
        self._unknowns.SetNames(unkNamLst)
        self._unknowns.SetValues(unkValLst)
        self._unknowns.SetInitValues(unkInitValLst)
        self._unknowns.SetIsFixed(unkIsFixLst)
        self._unknowns.SetScaleFactors(unkScaleFact)

        return True


    def ConvertToMKS(self, vals):
        """Converto all the units to m, kg, s units. It expects the std units from sim42"""

        #Copy values do not override
        vals = list(vals)
        
        vals[w1Idx] = vals[w1Idx] * (1/3600.0) #kg/h -> kg/s
        vals[w2Idx] = vals[w2Idx] * (1/3600.0)
        vals[w3Idx] = vals[w3Idx] * (1/3600.0)
        vals[p1Idx] = vals[p1Idx] * (1000.0)   #kPa -> Pa
        vals[p2Idx] = vals[p2Idx] * (1000.0)
        vals[p3Idx] = vals[p3Idx] * (1000.0)
        vals[S1Idx] = vals[S1Idx]
        vals[S2Idx] = vals[S2Idx]
        vals[S3Idx] = vals[S3Idx]
        vals[v1Idx] = vals[v1Idx] * (1/3600.0)#m/h -> m/s
        vals[v2Idx] = vals[v2Idx] * (1/3600.0)
        vals[v3Idx] = vals[v3Idx] * (1/3600.0)
        vals[H1Idx] = vals[H1Idx] * (1000.0)  #kJ/kg -> J/kg
        vals[H2Idx] = vals[H2Idx] * (1000.0)
        vals[H3Idx] = vals[H3Idx] * (1000.0)
        vals[d1Idx] = vals[d1Idx]
        vals[d2Idx] = vals[d2Idx]
        vals[d3Idx] = vals[d3Idx]
        
        return vals
        

    def ConvertFromMKS(self, vals):
        """Converto all the units to m, kg, s units. It expects the std units from sim42"""

        #Copy values do not override
        vals = list(vals)
        
        vals[w1Idx] = vals[w1Idx] * (3600.0) #kg/s -> kg/h
        vals[w2Idx] = vals[w2Idx] * (3600.0)
        vals[w3Idx] = vals[w3Idx] * (3600.0)
        vals[p1Idx] = vals[p1Idx] * (1/1000.0)   #Pa -> kPa
        vals[p2Idx] = vals[p2Idx] * (1/1000.0)
        vals[p3Idx] = vals[p3Idx] * (1/1000.0)
        vals[S1Idx] = vals[S1Idx]
        vals[S2Idx] = vals[S2Idx]
        vals[S3Idx] = vals[S3Idx]
        vals[v1Idx] = vals[v1Idx] * (3600.0)#m/s -> m/h
        vals[v2Idx] = vals[v2Idx] * (3600.0)
        vals[v3Idx] = vals[v3Idx] * (3600.0)
        vals[H1Idx] = vals[H1Idx] * (1/1000.0)  #kJ/kg -> J/kg
        vals[H2Idx] = vals[H2Idx] * (1/1000.0)
        vals[H3Idx] = vals[H3Idx] * (1/1000.0)
        vals[d1Idx] = vals[d1Idx]
        vals[d2Idx] = vals[d2Idx]
        vals[d3Idx] = vals[d3Idx]
        
        return vals

    def FillInWithAverage(self, vals):
        """Returns a copy of the sequence comming in but with the average value set in the places where the value is None"""
    
        sum = 0.0
        nu = 0
        
        #dont touch what comes in, create a copy!
        vals = list(vals)
        
        for val in vals:
            if val != None:
                sum += val
                nu += 1
        
        if not nu: av = None
        else: av = sum/nu

        for i in range(len(vals)):
            if vals[i] == None:
                vals[i] = av

        return vals


    def GetDensity(self, P, H, fracs):
        """Gets density for the particular system"""
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case
        inProp1 = [P_VAR, P]
        inProp2 = [H_VAR, H]
        propList = [MASSDEN_VAR]
        vals = thAdmin.GetProperties(prov, case, inProp1, inProp2, OVERALL_PHASE, fracs, propList)
        return vals[0]


    def CalculateRHS(self, x, rhs, isFix, initx, eqnNo=0):
        """Calculates the right hand side of the design equations"""
        nuCmps = self._nuCmps
        thAdmin, prov, case = self._thCaseObj.thermoAdmin, self._thCaseObj.provider, self._thCaseObj.case

        #Do fractions
        if self._unkFracs != None:
            w1Val, w2Val, w3Val = x[w1Idx], x[w2Idx], x[w3Idx]
            if self._unkFracs == _P_FRACS:
                mFlows = self._mFracs*(w2Val/Numeric.sum(self._pureCmpMW*self._mFracs))
                dFlows = self._dFracs*(w3Val/Numeric.sum(self._pureCmpMW*self._dFracs))
                self._pFracs = -mFlows+dFlows
                self._pFracs = self._pFracs/Numeric.sum(self._pFracs)   #Normalize
            elif self._unkFracs == _M_FRACS:
                pFlows = self._pFracs*(w1Val/Numeric.sum(self._pureCmpMW*self._pFracs))
                dFlows = self._dFracs*(w3Val/Numeric.sum(self._pureCmpMW*self._dFracs))
                self._mFracs = -pFlows+dFlows
                self._mFracs = self._mFracs/Numeric.sum(self._mFracs)   #Normalize
            elif self._unkFracs == _D_FRACS:
                pFlows = self._pFracs*(w1Val/Numeric.sum(self._pureCmpMW*self._pFracs))
                mFlows = self._mFracs*(w2Val/Numeric.sum(self._pureCmpMW*self._mFracs))
                self._dFracs = pFlows+mFlows
                self._dFracs = self._dFracs/Numeric.sum(self._dFracs)   #Normalize
        
        pFrac = self._pFracs
        mFrac = self._mFracs
        dFrac = self._dFracs
        

        _MW1Val = Numeric.sum(pFrac*self._pureCmpMW)
        _MW2Val = Numeric.sum(mFrac*self._pureCmpMW)
        _MW3Val = Numeric.sum(dFrac*self._pureCmpMW)
        

        # w1+w2-w3=0
        rhs[0] = x[w1Idx] + x[w2Idx] - x[w3Idx]
        rhs[0] /= self.scaleFactorW

        # w1v1+p1S1+w2v2+p2S2-w3v3-p3S3=0
        rhs[1] = x[w1Idx]*x[v1Idx] + x[p1Idx]*x[S1Idx] + x[w2Idx]*x[v2Idx] + x[p2Idx]*x[S2Idx] - x[w3Idx]*x[v3Idx] - x[p3Idx]*x[S3Idx]
        rhs[1] /= self.scaleFactorPS

        # w1(H1+0.5v1^2)+w2(H2+0.5v2^2)-w3(H3/eff+0.5v3^2)
        rhs[2] = x[w1Idx]*(x[H1Idx] + 0.5*x[v1Idx]**2) + x[w2Idx]*(x[H2Idx] + 0.5*x[v2Idx]**2) - x[w3Idx]*(x[H3Idx]/self._eff + 0.5*x[v3Idx]**2)
        rhs[2] /= (self.scaleFactorW*self.scaleFactorH)
        
        # v1d1S1-w1=0
        rhs[3] = x[v1Idx] * x[d1Idx] * x[S1Idx] - x[w1Idx]
        rhs[3] /= self.scaleFactorW

        # v2d2S2-w2=0
        rhs[4] = x[v2Idx] * x[d2Idx] * x[S2Idx] - x[w2Idx]
        rhs[4] /= self.scaleFactorW

        # v3d3S3-w3=0
        rhs[5] = x[v3Idx] * x[d3Idx] * x[S3Idx] - x[w3Idx]
        rhs[5] /= self.scaleFactorW

        # d1 - f(p1,H1) = 0
        P = x[p1Idx] / 1000.0 #Make it kPa
        H = x[H1Idx]*_MW1Val / 1000.0 #Make it kJ
        den = self.GetDensity(P, H, pFrac)
        rhs[6] = x[d1Idx] - den
        rhs[6] /= self.scaleFactorD
        
        # d2 - f(p2,H2) = 0
        P = x[p2Idx] / 1000.0 #Make it kPa
        H = x[H2Idx]*_MW2Val / 1000.0 #Make it kJ
        den = self.GetDensity(P, H, mFrac)
        rhs[7] = x[d2Idx] - den
        rhs[7] /= self.scaleFactorD
        
        # d3 - f(p3,H3) = 0
        P = x[p3Idx] / 1000.0 #Make it kPa
        H = x[H3Idx]*_MW3Val / 1000.0 #Make it kJ
        den = self.GetDensity(P, H, dFrac)
        rhs[8] = x[d3Idx] - den
        rhs[8] /= self.scaleFactorD
        
        # S1+S2-S3=0
        rhs[9] = x[S1Idx] + x[S2Idx] - x[S3Idx]
        rhs[9] /= self.scaleFactorS

        
        #Eqn's for known vars
        cntEqn = 10
        for idx in range(len(x)):
            if isFix[idx]:
                rhs[cntEqn] = (x[idx] - initx[idx]) / self._unknowns._unkScaleFacts[idx]
                cntEqn += 1

        return cntEqn
        

    def CalculateJacobian(self, x, j, isFix, initx, eqnNo=0):

        nuCmps = self._nuCmps
        nuVars = len(x)
        
        pFrac = self._pFracs
        mFrac = self._mFracs
        dFrac = self._dFracs

        _MW1Val = Numeric.sum(pFrac*self._pureCmpMW)
        _MW2Val = Numeric.sum(mFrac*self._pureCmpMW)
        _MW3Val = Numeric.sum(dFrac*self._pureCmpMW)
        


        # w1+w2-w3=0
        # dw1_dy=1; dw2_dy=1; dw3_dy=-1
        
        j[0][w1Idx] = 1.0 / self.scaleFactorW
        j[0][w2Idx] = 1.0 / self.scaleFactorW
        j[0][w3Idx] = -1.0 / self.scaleFactorW


        #w1v1+p1S1+w2v2+p2S2-w3v3-p3S3=0
        #
        j[1][w1Idx] = x[v1Idx] / self.scaleFactorPS
        j[1][v1Idx] = x[w1Idx] / self.scaleFactorPS
        j[1][p1Idx] = x[S1Idx] / self.scaleFactorPS
        j[1][S1Idx] = x[p1Idx] / self.scaleFactorPS
        j[1][w2Idx] = x[v2Idx] / self.scaleFactorPS
        j[1][v2Idx] = x[w2Idx] / self.scaleFactorPS
        j[1][p2Idx] = x[S2Idx] / self.scaleFactorPS
        j[1][S2Idx] = x[p2Idx] / self.scaleFactorPS
        j[1][w3Idx] = -x[v3Idx] / self.scaleFactorPS
        j[1][v3Idx] = -x[w3Idx] / self.scaleFactorPS
        j[1][p3Idx] = -x[S3Idx] / self.scaleFactorPS
        j[1][S3Idx] = -x[p3Idx] / self.scaleFactorPS


        #w1(H1+0.5v1^2)+w2(H2+0.5v2^2)-w3(H3/eff+0.5v3^2)
        j[2][w1Idx] = (x[H1Idx] + 0.5 * x[v1Idx] ** 2) / (self.scaleFactorW*self.scaleFactorH)
        j[2][H1Idx] = (x[w1Idx]) / (self.scaleFactorW*self.scaleFactorH)
        j[2][v1Idx] = (x[w1Idx] * x[v1Idx]) / (self.scaleFactorW*self.scaleFactorH)
        j[2][w2Idx] = (x[H2Idx] + 0.5 * x[v2Idx] ** 2) / (self.scaleFactorW*self.scaleFactorH)
        j[2][H2Idx] = (x[w2Idx]) / (self.scaleFactorW*self.scaleFactorH)
        j[2][v2Idx] = (x[w2Idx] * x[v2Idx]) / (self.scaleFactorW*self.scaleFactorH)
        j[2][w3Idx] = (-(x[H3Idx] / self._eff + 0.5 * x[v3Idx] ** 2)) / (self.scaleFactorW*self.scaleFactorH)
        j[2][H3Idx] = (-x[w3Idx] / self._eff) / (self.scaleFactorW*self.scaleFactorH)
        j[2][v3Idx] = (-x[w3Idx] * x[v3Idx]) / (self.scaleFactorW*self.scaleFactorH)


        # v1d1S1-w1=0
        j[3][v1Idx] = x[d1Idx] * x[S1Idx] / self.scaleFactorW
        j[3][d1Idx] = x[v1Idx] * x[S1Idx] / self.scaleFactorW
        j[3][S1Idx] = x[v1Idx] * x[d1Idx] / self.scaleFactorW
        j[3][w1Idx] = -1.0 / self.scaleFactorW


        # v2d2S2-w2=0
        j[4][v2Idx] = x[d2Idx] * x[S2Idx] / self.scaleFactorW
        j[4][d2Idx] = x[v2Idx] * x[S2Idx] / self.scaleFactorW
        j[4][S2Idx] = x[v2Idx] * x[d2Idx] / self.scaleFactorW
        j[4][w2Idx] = -1.0 / self.scaleFactorW


        # v3d3S3-w3=0
        j[5][v3Idx] = x[d3Idx] * x[S3Idx] / self.scaleFactorW
        j[5][d3Idx] = x[v3Idx] * x[S3Idx] / self.scaleFactorW
        j[5][S3Idx] = x[v3Idx] * x[d3Idx] / self.scaleFactorW
        j[5][w3Idx] = -1.0 / self.scaleFactorW
        

        #d1 - f(p1,H1) = 0
        j[6][d1Idx] = 1.0 / self.scaleFactorD

        P = x[p1Idx] / 1000.0 #Make it kPa
        H = x[H1Idx]*_MW1Val / 1000.0 #Make it kJ
        frac = pFrac

        ##Can optimize thermo calls by doing all of them at once
        #Current density
        oldDen = self.GetDensity(P, H, frac)

        #Density at a new P
        #shift = 0.01
        shift = 0.0001 * self.scaleFactorP
        P += shift/1000.0 #Shift in kPa
        newDen = self.GetDensity(P, H, frac)
        j[6][p1Idx] = - (newDen-oldDen) / shift / self.scaleFactorD

        
        #Density at new H
        #shift = 1000.0
        shift = 0.0001 * self.scaleFactorH
        P = x[p1Idx] / 1000.0 #Make it kPa
        H += shift/1000.0
        newDen = self.GetDensity(P, H, frac)
        j[6][H1Idx] = - (newDen-oldDen) / shift / self.scaleFactorD
        

        # d2 - f(p2,H2) = 0
        j[7][d2Idx] = 1.0 / self.scaleFactorD

        P = x[p2Idx] / 1000.0 #Make it kPa
        H = x[H2Idx]*_MW2Val / 1000.0 #Make it kJ
        frac = mFrac
        
        #Current density
        oldDen = self.GetDensity(P, H, frac)

        #Density at a new P
        #shift = 0.01
        shift = 0.0001 * self.scaleFactorP
        P += shift/1000.0 #Shift in kPa
        newDen = self.GetDensity(P, H, frac)
        j[7][p2Idx] = - (newDen-oldDen) / shift / self.scaleFactorD

        #Density at new H
        #shift = 1000.0
        shift = 0.0001 * self.scaleFactorH
        P = x[p2Idx] / 1000.0 #Make it kPa
        H += shift/1000.0
        newDen = self.GetDensity(P, H, frac)
        j[7][H2Idx] = - (newDen-oldDen) / shift / self.scaleFactorD


        # d3 - f(p3,H3) = 0
        j[8][d3Idx] = 1.0 / self.scaleFactorD

        P = x[p3Idx] / 1000.0 #Make it kPa
        H = x[H3Idx]*_MW3Val / 1000.0 #Make it kJ
        frac = dFrac
        
        #Current density
        oldDen = self.GetDensity(P, H, frac)

        #Density at a new P
        #shift = 0.01
        shift = 0.0001 * self.scaleFactorP
        P += shift/1000.0 #Shift in kPa
        newDen = self.GetDensity(P, H, frac)
        j[8][p3Idx] = - (newDen-oldDen) / shift / self.scaleFactorD

        #Density at new H
        #shift = 1000.0
        shift = 0.0001 * self.scaleFactorH
        P = x[p3Idx] / 1000.0 #Make it kPa
        H += shift/1000.0
        newDen = self.GetDensity(P, H, frac)
        j[8][H3Idx] = - (newDen-oldDen) / shift / self.scaleFactorD


        #S1+S2-S3=0
        j[9][S1Idx] = 1.0 / self.scaleFactorS
        j[9][S2Idx] = 1.0 / self.scaleFactorS
        j[9][S3Idx] = -1.0 / self.scaleFactorS


        #User input differentials
        #Eqn's for known vars
        cntEqn = 10
        for idx in range(nuVars):
            if isFix[idx]:
                j[cntEqn][idx] = 1.0 / self._unknowns._unkScaleFacts[idx]
                cntEqn += 1

        return cntEqn

    def AdjustOldCase(self, version):
        super(EjectorOp, self).AdjustOldCase(version)
        if version[0] < 23:
            if not hasattr(self, '_balance'):
                self._balance = Balance.Balance(Balance.MOLE_BALANCE)
                self._balance.AddInput(self.GetPorts(IN|MAT))
                self._balance.AddOutput(self.GetPorts(OUT|MAT))   




