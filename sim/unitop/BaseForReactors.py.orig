"""Provides base classes for modeling reactors

Classes:
ReactionDisplay - For rendering reaction
Reaction - Reaction class
"""
import re, string

import UnitOperations
from sim.solver import Flowsheet, Error
from sim.solver.Variables import *
from numpy import *

NURXN_PAR = 'NumberRxn'
REACTION = 'Rxn'
COEFF = 'Coeff'
BALANCEDRXN = 'BalancedRxn'
RXNFFORMULA_PAR = 'Formula'
RXNCONV = 'Conversion'
RXNEXTENT = 'RxnExtent'
RXNORDER_PAR = 'RxnOrder'
SIMULTANEOUSRXN_PAR = 'SimultaneousRxn'
QEXOTHERMIC_ISPOS_PAR = 'QExothermicIsPositive'

#Assign a constant to each type of reactor
CSTR_TYPE       = 1
PFR_TYPE        = 2
CONVERSION_TYPE = 3
EQUILIB_TYPE    = 4

TRACE = 1.0E-15

class ReactionDisplay(object):
    """ An object to display the reaction detail """
    def __init__(self, parent):
        self.parent = parent
        self.exportList = []

    def __str__(self):
        rxn = self.parent
        result = 'Reaction = ' + rxn.FormulaString() + '\nOrder = ' + \
                str(rxn.GetParameterValue(RXNORDER_PAR)) + '\nStoichmetric coefficients:'
        maxLength = 0
        for cmpName in rxn.cmpNames: maxLength = max(maxLength, len(cmpName))        
        for i in range(len(rxn.stoichCoeffs)):
            result += '\n   ' + rxn.cmpNames[i] + ' ' * (maxLength - len(rxn.cmpNames[i]) + 2)
            v = rxn.stoichCoeffs[i]
            if v < 0:
                result += '%f' % v
            else:
                result += ' %f' % v
            if i == rxn.baseCompIdx: result += ' (Base Comp)'
        return result

    def CleanUp(self):
        self.parent = None

    def GetValues(self):
        rxn = self.parent
        self.exportList = []
        self.exportList.append(rxn.rxnName)
        self.exportList.append(rxn.baseCompIdx)
        self.exportList.extend(rxn.stoichCoeffs)
        return self.exportList
        
          
class Reaction(UnitOperations.UnitOperation):
    """ class for a reaction """
    def __init__(self, initScript=None):
        super(Reaction, self).__init__(initScript)
        self.rxnName = 'Unknown'
        self.rxnExtent = BasicProperty(GENERIC_VAR) # so that i can export for inspection
        self.rxnExtent.SetValue(0.0)
        self.stoichCoeffs = []
        self.cmpNames = []
        self.baseCompIdx = -1
        
        self.SetParameterValue(RXNFFORMULA_PAR, '')
        self.SetParameterValue(RXNORDER_PAR, -1)
        self.display = ReactionDisplay(self)

    def SetParameterValue(self, paramName, value):
        super(Reaction, self).SetParameterValue(paramName, value)
        if paramName == RXNFFORMULA_PAR and self.parameters[paramName] != '':
            self.ParseFormula()
            # stored the parsed formula to ger rid of the compound index in the formula
            parsedFormula = self.FormulaString()
            super(Reaction, self).SetParameterValue(paramName, parsedFormula)

    def CleanUp(self):
        self.display.CleanUp()
        super(Reaction, self).CleanUp()

    def GetContents(self):
        result = [('Reaction', self.display)]
        return result
    
    def GetObject(self, name):
        if name == COEFF:
            return self.display
        elif name == RXNEXTENT:         # export for display
            return self.rxnExtent
        elif name == BALANCEDRXN:
            return self.BalancedRxn()
        else:
            return super(Reaction, self).GetObject(name)        

    def FormulaString(self):
        # Build the formula from internal data
        # Group the product first; then the reactant
        cmpNames = self.GetCompoundNames()
        formula = ''
        for loop in range(2):
            for i in range(len(cmpNames)):
                if i == self.baseCompIdx:
                    cmp = "!'" + cmpNames[i] + "'"
                else:
                    cmp = "'" + cmpNames[i] + "'"
                cmp = re.sub(' ', '_', cmp)
                coeff = self.Coeff(i)
                if loop == 0 and coeff > 0.0:
                    formula += '+' + str(coeff) + '*' + cmp
                elif loop == 1 and coeff < 0:
                    formula += str(coeff) + '*' + cmp
        return self.rxnName + ':' + formula[1:]        

    def CompoundIndex(self, cmp):
        '''
        Given a compound name, return its index (posiiton in the list)
        returns -1 when cmp is not a selected compound        
        '''
        # handling of underscore and space<g>
        idx = -1
        try:
            x = re.sub('_', ' ', cmp)
            idx = self.cmpNames.index(x)
        except:
            try:
                idx = self.cmpNames.index(cmp)
            except:
                pass
        return idx
    
    def ParseFormula(self):
        eqnStr = self.parameters[RXNFFORMULA_PAR]
        eqn = eqnStr    # keep a copy of the original equation
        if (eqnStr == None or eqnStr == ''): return
        
        # reset all coeffs to zero
        cmpNames = self.GetCompoundNames()
        self.cmpNames = cmpNames

        self.stoichCoeffs = []
        for i in range(len(cmpNames)):
            self.stoichCoeffs.append(0)

        # replace compounds within quotes by the index
        # for compounds with '-'
        cmps = re.findall(r'"[^"]+"|\'[^\']+\'', eqnStr)
        for token in cmps:
            # strip out the quote
            cmp = token[1:-1]
            try:
                idx = self.CompoundIndex(cmp)
                #eqnStr = re.sub(token, str(idx), eqnStr)
                eqnStr = eqnStr.replace(token, str(idx))
            except:
                pass
        
        try:
            # extract the reaction name
            tokens = re.split(r'\:', eqnStr, 1)
            if (len(tokens) == 2):
                eqnStr = string.strip(tokens[1])
                self.rxnName = string.strip(tokens[0])

            # replace all - by +- so that when i split the tokens,
            # the signs of the coeff are preserved
            eqnStr = re.sub('\-', '+-', eqnStr)
            tokens = re.split('\+', eqnStr)
            for token in tokens:
                if (string.strip(token) == ''):
                    continue
                x = re.split('\*', string.strip(token))
                # if coeff is missing, assume 1 or -1
                if len(x) == 1:
                    x0 = x[0]
                    if x0[0] == '-':
                        x.append(x0[1:])
                        x[0] = '-1'
                    else:    
                        x.append(x0)
                        x[0] = '1'
                # let underscores stand for spaces
                cmp = re.sub('_', ' ', string.strip(x[1]))
                # base compound indicator
                baseCmp = 0
                if (cmp[0] == '!'):
                    cmp = cmp[1:]
                    baseCmp = 1
                # if the input compound name is numeric, it is the compound index
                try:
                    idx = int(cmp)
                except:
                    idx = cmpNames.index(cmp)
                coef = float(string.strip(x[0]))
                self.stoichCoeffs[idx]= coef
                if baseCmp:
                    self.baseCompIdx = idx
        except:
            #self.SetParameterValue(RXNFFORMULA_PAR, '')            
            self.stoichCoeffs = []
            raise Error.SimError('EqnSyntax', (eqn, self.GetPath()))
        
        # base compound must be a reactant
        # check for equation mass balance later (need MW of selected compounds)
        if self.baseCompIdx < 0:
            raise Error.SimError('EqnSyntax', (eqn, self.GetPath()))            
        elif self.stoichCoeffs[self.baseCompIdx] >= 0:
            raise Error.SimError('EqnSyntax', (eqn, self.GetPath()))
        
        
    def Coeff(self, ith):
        try:    
            return self.stoichCoeffs[ith]
        except:
            return 0.0

    def BaseCompIdx(self):
        return self.baseCompIdx
    
    def AppendCompound(self, cmpIdx=-1):
        """Add a compound """
        super(Reaction, self).AppendCompound(cmpIdx)
        self.ParseFormula()

    def DeleteCompound(self, cmpName):
        """Deletes a compound from the reaction"""
        super(Reaction, self).DeleteCompound(cmpName)
        # Nothing for now, reparse the formula to 
        # get rid of the references to the deleted compound at AfterDeleteCompoundCleanUp

    def AfterCompoundDeleted(self, cmpName):
        """Deletes a compound from the reaction"""
        super(Reaction, self).AfterCompoundDeleted(cmpName)
        # reparse the formula to get rid of the references to the deleted compound
        self.SetParameterValue(RXNFFORMULA_PAR, self.parameters[RXNFFORMULA_PAR])

    def MoveCompound(self, cmp1Idx, cmp2Idx):
        super(Reaction, self).MoveCompound(cmp1Idx, cmp2Idx)
        # formula must not be using the compound index
        self.ParseFormula()        

    def ThermoChanged(self, thCaseObj):
        """
        intercept this to set up the stoichCoeffs list
        """
        # YK to do: fix up later to match compound names
        super(Reaction, self).ThermoChanged(thCaseObj)
        self.ParseFormula()

    def ValidateOk(self):
        if self.baseCompIdx < 0 : return 0
        eqn = self.parameters[RXNFFORMULA_PAR]
        if eqn == None or eqn == '': return 0
        cmpNames = self.GetCompoundNames()
        if len(cmpNames) > 0 and len(self.stoichCoeffs) == 0: return 0
        if self.rxnConv:
            if self.rxnConv.GetValue() == None: return 0
        return 1
        
    def BalancedRxn(self):
        # Check the MW to see if the reaction is balanced
        # returns 1 if balanced, 0 if not and None if not sure
        try:
            lhs = 0.0
            rhs = 0.0
            thCaseObj = self.GetThermo()
            thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
            for i in range(len(self.cmpNames)): 
                mw = thAdmin.GetSelectedCompoundProperties(prov, case, i, [MOLE_WT])[0]
                coeff = self.stoichCoeffs[i]
                if coeff > 1.0e-6:
                    lhs = lhs + coeff * mw
                elif coeff < -1.0e-6:
                    rhs = rhs - coeff * mw
            if abs(rhs-lhs) < 1.0e-3:
                return 1
            else:
                return 0
        except:
            return None
        


    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(Reaction, self)._RemoveFromCloneList(clone, attrNamesToClone)
        #This is not really needed as the algorithm should end up not cloning it 
        #but lets keep this here for clarity
        dontClone = ["display"]
        
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
            
        return attrNamesToClone
    
class ReactorObject(object):
    """Custom objects that could potentially be added to reactors"""
    def Initialize(self, reactor, name):
        """
        not __init__ as we want interface to be able to create it
        without parameters - reactor will call this when it is added to it
        """
        
        #As opposed to the tower, do not crate the port here.
        #Let each object handle/create its own port
        
        self.reactor = reactor
        self.name = name
        
        import KineticReactor, ConvRxn, EquiliReactor
        if isinstance(reactor, KineticReactor.CSTR):        
            self.reactorType = CSTR_TYPE
        elif isinstance(reactor, KineticReactor.PFR):        
            self.reactorType = PFR_TYPE
        elif isinstance(reactor, ConvRxn.ConvReactor):        
            self.reactorType = CONVERSION_TYPE    
        elif isinstance(reactor, EquiliReactor.EquilibriumReactor):        
            self.reactorType = EQUILIB_TYPE
            
        
    def CleanUp(self):
        """remove all references"""
        if hasattr(self, 'port'):
            if self.reactor and self.port:
                self.reactor.DeletePort(self.port)
            self.port = None
        self.reactor = None
        
    def AdjustOldCase(self, version):
        """
        fixup old versions
        """
        pass  # handled by derived classes if necessary
    
    def GetPath(self):
        """return object path to this object"""
        return '%s.%s' % (self.reactor.GetPath(), self.name)
        
    def SetParent(self, parent):
        """The parent must have a port with the necessary name"""
        self.reactor = parent
        if hasattr(self, "ReactorPortName"):
            self.port = parent.GetPort(self.ReactorPortName())
            
        
    def GetParent(self):
        """return stage as parent in hierarchy"""
        return self.reactor
    
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
            raise SimError('CantAddObject', (name, self.reactor.GetPath()))
            
    def ChangeName(self, fromName, toName):
        """
        Change name in corresponding dictionary and in associated port if necessary
        """
        
        if self.reactor.GetObject(toName):
            self.InfoMessage('DuplicateName', (toName, self.reactor.GetPath()))
            return
        
        if hasattr(self,'ReactorPortName'):
            oldPortName = self.ReactorPortName()
            
        #Let the reactor rename the object
        self.reactor.ChangeObjectName(fromName, toName)
            
        #Change port name if necessary
        if hasattr(self,'ReactorPortName'):
            newPortName = self.ReactorPortName()
            self.reactor.RenamePort(oldPortName, newPortName)
            
    def Clone(self):
        """Clone the object"""
        clone = self.__class__()
        clone.name = self.name
        clone.reactorType = self.reactorType
        return clone
    
            
class ReactorVariable(ReactorObject):
    def __init__(self, varType):
        """Hold the indexes just for now. They will be deleted once Initialize is called"""
        super(ReactorVariable, self).__init__()
        self.varType = varType.strip()
        self.scaleFactor = None
        if PropTypes.has_key(self.varType):
            self.scaleFactor = PropTypes[self.varType].scaleFactor
        if not self.scaleFactor:
            self.scaleFactor = 1.0
            
    def Initialize(self, reactor, name):
        """
        create a port for the signal
        """
        super(ReactorVariable, self).Initialize(reactor, name)
        
        self.port = self.reactor.CreatePort(SIG, self.ReactorPortName())
        self.port.SetSignalType(self.varType)
        
    def ReactorPortName(self):
        return 'Variable_%s' % (self.name,)
    
    def Reset(self):
        """Get the value from the port"""
        self.value = self.port.GetValue()
            
    def Error(self):
        """Return the scaled error"""
        value = self.GetCurrentReactorValue()
        return (self.value - value) / self.scaleFactor
        
    def AssignResultsToPort(self):
        """Would get called if spec was not active, then put the newly calculated value"""
        value = self.GetCurrentReactorValue()
        self.port.SetValue(value, CALCULATED_V)
        
    def SetScaleFactor(self, scaleFactor):
        self.scaleFactor = scaleFactor
        
    def GetScaleFactor(self):
        return self.scaleFactor
    
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.varType)
        clone.name = self.name
        clone.reactorType = self.reactorType
        clone.scaleFactor = self.scaleFactor
        return clone
    
class ReactorProperty(ReactorVariable):
    """Reactor property that is calculated either in the inlet or the outlet"""
    def __init__(self, varType, isIn=1):
        """Define if this has to be calcualted i nthe inlet or outlet"""
        super(ReactorProperty, self).__init__(varType)
        self.atInlet = isIn
    
        
    def ReactorPortName(self):
        if self.atInlet: return 'Variable%sIn_%s' % (self.varType, self.name)
        return 'Variable%sOut_%s' % (self.varType, self.name)
        

    def GetCurrentReactorValue(self):
        """Get the current value according to iteration variables"""
        try:
            reactor = self.reactor
            if self.atInlet:
                p = reactor._P0
                z = reactor._z0
                t = reactor._T0
            else:
                p = reactor._P
                z = reactor._z
                t = reactor._T
                
            if self.varType == T_VAR:
                return t
            elif self.varType == P_VAR:
                return p
            elif self.varType == H_VAR:
                return h
            else:
                compounds = CompoundList(None)
                for i in z:
                    prop = BasicProperty(FRAC_VAR)
                    prop.SetValue(i, FIXED_V)
                    compounds.append(prop)
                
                props = MaterialPropertyDict()
                props[P_VAR].SetValue(p, FIXED_V)
                props[T_VAR].SetValue(t, FIXED_V)
                thCaseObj = reactor.GetThermo()
                nuSolids = reactor.NumberSolidPhases()
                thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
                results = thAdmin.Flash(prov, case, compounds, props, 2, (self.varType,), nuSolids=nuSolids)
                return results.bulkProps[0]
        except:
            return None
        
    def Clone(self):
        """Clone the object"""
        clone = super(ReactorVariable, self).Clone()
        clone.atInlet = self.atInlet
        
        return clone
        
class ReactorConversion(ReactorVariable):
    """Reactor conversion of a specified compound"""
    def __init__(self, cmpName):
        """Define if this has to be calcualted i nthe inlet or outlet"""
        super(ReactorConversion, self).__init__(FRAC_VAR)
        self.cmpName = re.sub(" ", "_", cmpName)
        self.cmpIdx = None
    
    #def ReactorPortName(self):
        #"""Return a customized name for the port"""
        
        #return 'Variable_%s' % (self.cmpName, self.name)
        
    def GetObject(self, description):
        if description == "Compound":
            return ReactorCompound(self, "Compound", self.cmpName)
        elif description == "Type":
            return "Conversion"
        
    def Reset(self):
        """Load the name of the compound and its index"""
        super(ReactorConversion, self).Reset()
        
        self.cmpIdx = None
        cmpNames = self.reactor.GetCompoundNames()
        cmpName = self.cmpName
        
        if cmpName in cmpNames:
            self.cmpIdx = cmpNames.index(cmpName)
            return
        
        cmpName = re.sub("_", " ", self.cmpName)
        if cmpName in cmpNames:
            self.cmpIdx = cmpNames.index(cmpName)
            return
        
    def GetCurrentReactorValue(self):
        """Get the current value according to iteration variables"""
        try:
            reactor = self.reactor
            i = self.cmpIdx
            return (reactor._fCmp0[i] - reactor._fCmp[i] ) / reactor._fCmp0[i]
            
        except:
            return None
        
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.cmpName)
        clone.name = self.name
        clone.reactorType = self.reactorType
        clone.scaleFactor = self.scaleFactor
        clone.cmpName = self.cmpName
        clone.cmpIdx = self.cmpIdx
        
        return clone
            
class ReactorSelectivity(ReactorVariable):
    """Reactor selectivity between two specified compounds"""
    def __init__(self, desiredCmpName, undesiredCmpName):
        """Define if this has to be calcualted i nthe inlet or outlet"""
        super(ReactorSelectivity, self).__init__(FRAC_VAR)
        self.dCmpName = re.sub(" ", "_", desiredCmpName)
        self.uCmpName = re.sub(" ", "_", undesiredCmpName)
        self.dCmpIdx = None
        self.uCmpIdx = None
    
    #def ReactorPortName(self):
        #"""Return a customized name for the port"""
        
        #return 'Selectivity_%s' % (self.name,)
        

    def GetObject(self, description):
        if description == "DesiredCompound":
            return ReactorCompound(self, "DesiredCompound", self.dCmpName)
        elif description == "UndesiredCompound":
            return ReactorCompound(self, "UndesiredCompound", self.uCmpName)
        elif description == "Type":
            return "Selectivity"
        
    def Reset(self):
        """Load the name of the compound and its index"""
        super(ReactorSelectivity, self).Reset()
        
        cmpNames = self.reactor.GetCompoundNames()
        
        #Do it for the desired compound
        dCmpName = self.dCmpName
        self.dCmpIdx = None
        if dCmpName in cmpNames:
            self.dCmpIdx = cmpNames.index(dCmpName)
        else:
            dCmpName = re.sub("_", " ", self.dCmpName)
            if dCmpName in cmpNames:
                self.dCmpIdx = cmpNames.index(dCmpName)
        
        
        #Do it for the undesired compound
        uCmpName = self.uCmpName
        self.uCmpIdx = None
        if uCmpName in cmpNames:
            self.uCmpIdx = cmpNames.index(uCmpName)
        else:
            uCmpName = re.sub("_", " ", self.uCmpName)
            if uCmpName in cmpNames:
                self.uCmpIdx = cmpNames.index(uCmpName)
        
    def GetCurrentReactorValue(self):
        """Get the current value according to iteration variables"""
        try:
            reactor = self.reactor
            d = self.dCmpIdx
            u = self.uCmpIdx
            uVal = reactor._fCmp[u]
            if abs(uVal) < TRACE:
                uVal = TRACE
            return reactor._fCmp[d] / uVal
            
        except:
            return None
 
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.dCmpName, self.uCmpName)
        clone.name = self.name
        clone.reactorType = self.reactorType
        clone.scaleFactor = self.scaleFactor
        clone.dCmpName = self.dCmpName
        clone.uCmpName = self.uCmpName
        clone.dCmpIdx = self.dCmpIdx
        clone.uCmpIdx = self.uCmpIdx
        
        return clone
        
class ReactorYield(ReactorVariable):
    """Reactor selectivity between two specified compounds"""
    def __init__(self, desiredCmpName, baseCmpName):
        """Define if this has to be calcualted i nthe inlet or outlet"""
        super(ReactorYield, self).__init__(FRAC_VAR)
        self.dCmpName = re.sub(" ", "_", desiredCmpName)
        self.bCmpName = re.sub(" ", "_", baseCmpName)
        self.dCmpIdx = None
        self.bCmpIdx = None
    
    #def ReactorPortName(self):
        #"""Return a customized name for the port"""
        
        #return 'Yield_%s' % (self.name,)
        

    def GetObject(self, description):
        if description == "DesiredCompound":
            return ReactorCompound(self, "DesiredCompound", self.dCmpName)
        elif description == "BaseCompound":
            return ReactorCompound(self, "BaseCompound", self.bCmpName)
        elif description == "Type":
            return "Yield"
        
    def Reset(self):
        """Load the name of the compound and its index"""
        super(ReactorYield, self).Reset()
        
        cmpNames = self.reactor.GetCompoundNames()
        
        #Do it for the desired compound
        dCmpName = self.dCmpName
        self.dCmpIdx = None
        if dCmpName in cmpNames:
            self.dCmpIdx = cmpNames.index(dCmpName)
        else:
            dCmpName = re.sub("_", " ", self.dCmpName)
            if dCmpName in cmpNames:
                self.dCmpIdx = cmpNames.index(dCmpName)
        
        
        #Do it for the undesired compound
        bCmpName = self.bCmpName
        self.bCmpIdx = None
        if bCmpName in cmpNames:
            self.bCmpIdx = cmpNames.index(bCmpName)
        else:
            bCmpName = re.sub("_", " ", self.bCmpName)
            if bCmpName in cmpNames:
                self.bCmpIdx = cmpNames.index(bCmpName)
        
    def GetCurrentReactorValue(self):
        """Get the current value according to iteration variables"""
        try:
            reactor = self.reactor
            d = self.dCmpIdx
            b = self.bCmpIdx
            
            bVal = reactor._fCmp0[b] - reactor._fCmp[b]
            if abs(bVal) < TRACE:
                bVal = TRACE
                
            return reactor._fCmp[d] / bVal
            
        except:
            return None
        
    def Clone(self):
        """Clone the object"""
        clone = self.__class__(self.dCmpName, self.bCmpName)
        clone.name = self.name
        clone.reactorType = self.reactorType
        clone.scaleFactor = self.scaleFactor
        clone.dCmpName = self.dCmpName
        clone.bCmpName = self.bCmpName
        clone.dCmpIdx = self.dCmpIdx
        clone.bCmpIdx = self.bCmpIdx
        
        return clone
        
#import KineticReactor, ConvRxn, EquiliReactor
        

class ReactorCompound(object):
    def __init__(self, parent, name, cmpName=""):
        self.parent = parent
        self.name = name
        self.cmpName = cmpName
        
    def GetName(self):
        return self.name
    
    def GetPath(self):
        return self.parent.GetPath + "." + self.name
    
    def GetParent(self):
        return self.parent
    
    def SetValue(self, value, status=None):
        self.cmpName = re.sub(" ", "_", value)
        if self.name == "Compound":
            self.parent.cmpName = re.sub(" ", "_", value)
        elif self.name == "DesiredCompound":
            self.parent.dCmpName = re.sub(" ", "_", value)
        elif self.name == "UndesiredCompound":
            self.parent.uCmpName = re.sub(" ", "_", value)
        elif self.name == "BaseCompound":
            self.parent.bCmpName = re.sub(" ", "_", value)
            
    def GetValue(self):
        return re.sub(' ', '_', self.cmpName)
    
        
