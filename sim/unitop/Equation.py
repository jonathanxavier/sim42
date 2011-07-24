"""
Equation module - implements basic equation handling as a
network of unitops - things like plus, minus, square etc.
"""

import UnitOperations
from sim.solver import Error
from sim.solver import Ports
from sim.solver.Variables import *
from sim.unitop import Stream
import math, string, re

IN_PORT_0 = IN_PORT + '0'
IN_PORT_1 = IN_PORT + '1'

EQUATION_PAR = 'Equation'
USEDCOUNT_PAR = 'UsedCount'

def MakeSignalName(name): return 'S_' + name

class Dyadic(UnitOperations.UnitOperation):
    """
    Base class for operators taking two arguments
    (signal ports IN_PORT_0 and IN_PORT_1)
    and produces a single result (signal port OUT_PORT)
    Add and Subtract would be examples
    
    Derived classes should provide methods CalcResult and
    CalcValue1 and if not communicative CalcValue0
    """
    def __init__(self, initScript = None):
        """
        Create the ports
        """          
        UnitOperations.UnitOperation.__init__(self, initScript)

        self.CreatePort(SIG, IN_PORT_0)
        self.CreatePort(SIG, IN_PORT_1)
        self.CreatePort(SIG, OUT_PORT)
        
    def Solve(self):
        """
        determine variable to solve for and call appropriate method
        (supplied by derived class)
        """
        p0 = self.GetPort(IN_PORT_0)
        p1 = self.GetPort(IN_PORT_1)
        pOut = self.GetPort(OUT_PORT)
        
        value0 = p0.GetValue()
        value1 = p1.GetValue()
        result = pOut.GetValue()
        
        if value0 != None:
            if value1 != None:
                try:
                    result = self.CalcResult(value0, value1)
                except ValueError:
                    return
                pOut.SetValue(result, CALCULATED_V)
            elif result != None:
                try:
                    value1 = self.CalcValue1(value0, result)
                except ValueError:
                    return
                p1.SetValue(value1, CALCULATED_V)
        elif value1 != None and result != None:
            try:
                value0 = self.CalcValue0(value1, result)
            except ValueError:
                raise Error.SimError('EqnCalcError', self.GetPath())
            p0.SetValue(value0, CALCULATED_V)
            
    def CalcValue0(self, value1, result):
        """
        Since some operations will be communicative, this is supplied by default
        """
        return self.CalcValue1(value1, result)

class Monadic(UnitOperations.UnitOperation):
    """
    Base class for operators taking a single argument
    (signal port IN_PORT)
    and producing a single result (signal port OUT_PORT)
    Square be an example
    Derived classes should provide CalcResult and CalcArgument
    """
    def __init__(self, initScript = None):
        """
        Create the ports
        """          
        UnitOperations.UnitOperation.__init__(self, initScript)

        self.CreatePort(SIG, IN_PORT_0)
        self.CreatePort(SIG, OUT_PORT)

    def Solve(self):
        """
        determine variable to solve for and call appropriate method
        (supplied by derived class)
        """
        pIn = self.GetPort(IN_PORT_0)
        pOut = self.GetPort(OUT_PORT)
        
        arg = pIn.GetValue()
        result = pOut.GetValue()
        
        if arg != None:
            try:
                result = self.CalcResult(arg)
            except ValueError:
                return
            pOut.SetValue(result, CALCULATED_V)
        elif result != None:
            try:
                arg = self.CalcArgument(result)
            except ValueError:
                return
            pIn.SetValue(arg, CALCULATED_V)

class Add(Dyadic):
    """OUT_PORT = IN_PORT_0 + IN_PORT_1"""
    precedence = 20

    def CalcResult(self, a, b):
        return a + b
    
    def CalcValue1(self, a, result):
        return result - a

class Subtract(Dyadic):
    """OUT_PORT = IN_PORT_0 - IN_PORT_1"""
    precedence = 20

    def CalcResult(self, a, b):
        return a - b
    
    def CalcValue1(self, a, result):
        return a - result
    
    def CalcValue0(self, b, result):
        return result + b

class Multiply(Dyadic):
    """OUT_PORT = IN_PORT_0 * IN_PORT_1"""
    precedence = 30

    def CalcResult(self, a, b):
        return a * b
    
    def CalcValue1(self, a, result):
        return result / a

class Divide(Dyadic):
    """OUT_PORT = IN_PORT_0 / IN_PORT_1"""
    precedence = 30

    def CalcResult(self, a, b):
        return a / b
    
    def CalcValue1(self, a, result):
        return a / result
        
    def CalcValue0(self, b, result):
        return b * result

class Power(Dyadic):
    """OUT_PORT = IN_PORT0 ** IN_PORT1"""
    precedence = 40

    def CalcResult(self, a, b):
        return a ** b
    
    def CalcValue1(self, a, result):
        return math.log(result)/math.log(a)
        
    def CalcValue0(self, b, result):
        return math.exp(math.log(result)/b)
    
class Equal(Dyadic):
    """OUT_PORT = IN_PORT ** 2"""
    precedence = 10

    def Solve(self):
        """
        Both input ports share value as does an output port
        """
        p0 = self.GetPort(IN_PORT_0)
        p1 = self.GetPort(IN_PORT_1)
        pOut = self.GetPort(OUT_PORT)
        #if p0.GetSignalType() == Ports.SIGNAL_TYPE_NONE:
            #p0.SetSignalType(GENERIC_VAR)
        #if p1.GetSignalType() == Ports.SIGNAL_TYPE_NONE:
            #p1.SetSignalType(GENERIC_VAR)
        if pOut.GetSignalType() == Ports.SIGNAL_TYPE_NONE:
            pOut.SetSignalType(GENERIC_VAR)
        
        value0 = p0.GetValue()
        value1 = p1.GetValue()
        result = pOut.GetValue()
        
        if value0 != None:
            p1.SetValue(value0, CALCULATED_V)
            pOut.SetValue(value0, CALCULATED_V)
        elif value1 != None:
            p0.SetValue(value1, CALCULATED_V)
            pOut.SetValue(value1, CALCULATED_V)
        elif result != None:
            p0.SetValue(result, CALCULATED_V)
            p1.SetValue(result, CALCULATED_V)
            
class Sqrt(Monadic):
    """OUT_PORT = sqrt(IN_PORT)"""
    # actually could be done by connecting a Square backwards
    precedence = 100

    def CalcResult(self, arg):
        return math.sqrt(arg)
    
    def CalcArgument(self, result):
        return result * result

class Log(Monadic):
    """OUT_PORT = ln(IN_PORT)"""
    precedence = 100

    def CalcResult(self, arg):
        return math.log(arg)
        
    def CalcArgument(self, result):
        return math.exp(result)
    
class Exp(Monadic):
    """OUT_PORT = exp(IN_PORT)"""
    precedence = 100

    def CalcResult(self, arg):
        return math.exp(arg)
    
    def CalcArgument(self, result):
        return math.log(result)

class Log10(Monadic):
    """OUT_PORT = log10(IN_PORT)"""
    precedence = 100

    def CalcResult(self, arg):
        return math.log10(arg)
        
    def CalcArgument(self, result):
        return math.pow(result, 10.0)
    
class Absolute(Monadic):
    """OUT_PORT = abs(IN_PORT)"""
    precedence = 100

    def CalcResult(self, arg):
        return math.fabs(arg)
    
    def CalcArgument(self, result):
        # can't know sign, so just return result
        return result

_reSignal = re.compile(r'[sS]ignal')
_reTypeDcl = re.compile(r'\w*\([\w, ]*\)')
_reEitherParen = re.compile(r'[\(\)]')
_reSpaceComma = re.compile(r'[ ,]')
_reTokenizeEqn = re.compile(r'[=*/+\-^()]|[\w.]+')

_operators = {
              '+' : Add,
              '-' : Subtract,
              '*' : Multiply,
              '/' : Divide,
              '^' : Power,
              '=' : Equal,
              'sqrt' : Sqrt,
              'ln'   : Log,
              'log10': Log10,
              'exp'  : Exp,
              'abs'  : Absolute
              }

class Equation(UnitOperations.UnitOperation):
    """
    implement a flowsheet of basic operators to calculate the equation
    given in EQUATION_PAR
    """
    
    def __init__(self, initScript = None):
        """
        create an empty equation parameter
        """
        super(Equation, self).__init__(initScript)
        self.installedOps = []  # operators installed
        self.SetParameterValue(EQUATION_PAR, '')
        self.operatorStack = []
        self.operandStack = []
        self.opCount = 0

    def CleanUp(self):
        self.installedOps = []  # operators installed
        self.operatorStack = []
        self.operandStack = []
        super(Equation, self).CleanUp()
        
    def SetParameterValue(self, name, value):
        """
        do the main work of parsing the equation and setting up the solution network
        """
        super(Equation, self).SetParameterValue(name, value)
        if name == EQUATION_PAR:
            # eliminate the old operators
            for op in self.installedOps:
                self.DeleteObject(op)
            self.installedOps = []
            self.opCount = 0
            
            # remove any clone ports from installed signal streams
            for name in self.GetPortNames(SIG):
                sig = self.GetChildUO(MakeSignalName(name))
                if sig:
                    nTimesUsed = sig.GetParameterValue(USEDCOUNT_PAR)
                    for i in range(1, nTimesUsed):
                        sig.DeletePortNamed('Clone_%d' % i)
                    sig.SetParameterValue(USEDCOUNT_PAR, 0)
            
            lines = re.split(r'\n', value)
            signals = []
            eqns = []
            for line in lines:
                line = string.strip(line)
                if _reSignal.match(line):
                    signals.append(line)
                else:
                    eqns.append(line)

            newNames = []
            for sigDcl in signals:
                # step over word signal
                sigDcl = string.lstrip(sigDcl[6:])
                dclTypes = _reTypeDcl.findall(sigDcl)
                for dclType in dclTypes:
                    (sigType, sigNames, junk) = _reEitherParen.split(dclType)
                    sigNames = _reSpaceComma.split(sigNames)
                    for name in sigNames:
                        if not name: continue
                        if name in newNames:
                            raise Error.SimError('EqnDuplicateSigName', (name, self.GetPath()))
                        newNames.append(name)
                        if name not in self.GetPortNames(SIG):
                            stream = Stream.Stream_Signal()
                            stream.SetParameterValue(SIGTYPE_PAR, sigType)
                            stream.SetParameterValue(USEDCOUNT_PAR, 0)

                            self.AddObject(stream, MakeSignalName(name))
                            self.BorrowChildPort(stream.GetPort(IN_PORT), name)
                            
            # any current ports not in new list need to be removed
            missingNames = []
            for name in self.GetPortNames(SIG):
                if name not in newNames:
                    missingNames.append(name)
                    
            for name in missingNames:
                stream = self.GetObject(MakeSignalName(name))
                port = self.GetPort(name)
                self.DelUnitOperation(MakeSignalName(portName))
                self.DeleteObject(port)
                    
            # now parse the equations
            for eqn in eqns:
                # transform string into list of tokens
                if not eqn: continue
                tokens = _reTokenizeEqn.findall(eqn)
                self.currentEqn = eqn   # for error reporting
                self.ParseEquation(tokens)

    def SyntaxError(self):
        raise Error.SimError('EqnSyntax', (self.currentEqn, self.GetPath()))
        
    def ProcessParen(self):
        """
        work back up operator stack until matching '(' is found
        """
        while 1:
            if len(self.operatorStack) == 0:
                raise Error.SimError(EqnParenMismatch, (self.currentEqn, self.GetPath()))
            op = self.operatorStack[-1]
            if op == '(':
                self.operatorStack.pop()  # just throw away matching paren
                return
            else:
                self.ProcessTopOperator()
                
    def ProcessTopOperator(self):
        """
        take the top operator off of the stack and connect it appropriately
        with its operand(s) then push it back onto operand stack
        """
        if len(self.operatorStack) == 0:
            self.SyntaxError()
            
        op = self.operatorStack.pop()
        if isinstance(op, Dyadic): argCount = 2
        else: argCount = 1
        
        for i in range(argCount-1, -1, -1):
            opPort = op.GetPort(IN_PORT + '%d' % i)
            try:
                arg = self.operandStack.pop()
            except IndexError:
                self.SyntaxError()
            if isinstance(arg, float):
                opPort.SetSignalType(GENERIC_VAR)
                opPort.SetValue(arg, FIXED_V)
            elif isinstance(arg, Stream.Stream_Signal):
                nTimesUsed = arg.GetParameterValue(USEDCOUNT_PAR)
                if nTimesUsed:
                    clonePort = Stream.ClonePort()
                    cloneName = 'Clone_%d' % nTimesUsed
                    arg.AddObject(clonePort, cloneName)
                    opPort.ConnectTo(arg.GetPort(cloneName))
                else:
                    opPort.ConnectTo(arg.GetPort(OUT_PORT))
                arg.SetParameterValue(USEDCOUNT_PAR, nTimesUsed + 1)
            elif isinstance(arg, UnitOperations.UnitOperation):
                opPort.SetSignalType(GENERIC_VAR)
                opPort.ConnectTo(arg.GetPort(OUT_PORT))
        self.operandStack.append(op)
        
    def ParseEquation(self, tokens):
        """
        tokens is list of tokens
        """
        if len(tokens) == 0: return
        
        self.operatorStack = ['(']  # start with paren to make end of input easy
        self.operandStack = []
        for token in tokens:
            # find first operand
            if token == '(':
                self.operatorStack.append(token)
                
            elif token == ')':
                self.ProcessParen()
     
            elif token in _operators:
                opClass = _operators[token]
                op = opClass()
                self.AddObject(op, '%s_%d' % (opClass.__name__, self.opCount))
                self.installedOps.append(op)
                self.opCount += 1
                prevOp = self.operatorStack[-1]
                while prevOp != '(' and prevOp.precedence >= op.precedence:
                    self.ProcessTopOperator()
                    prevOp = self.operatorStack[-1]
                self.operatorStack.append(op)
                
            elif token in self.GetPortNames(SIG):
                signal = self.GetChildUO(MakeSignalName(token))
                self.operandStack.append(signal)
                
            else:
                # should be a number
                try:
                    value = float(token)
                except ValueError:
                    raise Error.SimError('EqnUnknownToken', (token, self.currentEqn, self.GetPath()))
                self.operandStack.append(value)
        # process everything back to that initial paren
        self.ProcessParen()
        
        if len(self.operandStack) > 1 or len(self.operatorStack):
            self.SyntaxError()
            
                
       
               
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        attrNamesToClone = super(Equation, self)._RemoveFromCloneList(clone, attrNamesToClone)
        dontClone = ["installedOps", "operatorStack", "operandStack", "opCount"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone