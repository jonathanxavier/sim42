"""Implements a very simple command driven interface to the simulator"""

try:
    import psyco
except:
    pass

import sys, os, re, string, cPickle, time, errno
sys.path.append("/Users/jonathanxavier/Developer/sim42")
import StringIO, types, copy, zipfile, tempfile
pickle = cPickle
#import pickle
import gc    
import numpy
import traceback
import sim.cmd.cmdlanguages

from HelperClasses import VersionedOutputFile

from sim.thermo.Hypo import *
from sim.thermo.ThermoAdmin import ThermoAdmin, ThermoCase, PureCompoundProperty, EnvelopeResults
try:
    from sim.thermo.vmg import VMGerror
    from sim.thermo.vmg import VMGwarning
except:
    VMGerror = None
    VMGwarning = None
    
from sim.unitop import *
from sim.unitop.UnitOperations import TH_CASE_KEYWORD, TH_ADMIN_KEYWORD

from sim.design import *

from sim.solver import Flowsheet, Ports
from sim.solver.Error import CallBackException, SimError
from sim.solver.Variables import *
from sim.solver.Messages import MessageHandler

import vmgunits
from vmgunits import units


## look for local or private packages
try:
    import localsiminfo
    for pkg in localsiminfo.packages:
        exec("from %s import *" % pkg)
except:
    pass
    

class CmdError(Exception):
    def __init__(self, messageKey, extraData=None):
        self.messageKey = messageKey
        self.extraData = extraData
        self.args = str(self)
    def __str__(self):
        return MessageHandler.RenderMessage(self.messageKey, self.extraData)
    

#Regular expression used by tokenizer
quo = ["'''.*'''",     #Find expression in single triple quotes
       "|'[^']*'",     #Or single simple quotes
       '|""".*"""',    #Or triple double quotes
       '|"[^"]*"']     #Or single double quotes
quo = ''.join(quo)               #Put it into a single expression
QUO_REGEX = re.compile(quo)      #Compile it
del quo

ZIPFILENAME = '__s42z__.s42'
SIMSTORE_INFO = 'StoreInfo'

MessageHandler.AddMessageModule(sim.cmd.cmdlanguages)
    
class CommandInterface(object):
    """Simple command line interpretor to drive the simuulator.
    Each command is essentially of the form
    
       lhs operator rhs
       
    where each term is separated by white space.
    The lhs defines the target object and is of the form
    
      dist/feed.In.T
      
     In each case the first part is a child of the current operation.
     A slash indicates the next part will be a child of that operation
     A dot indicates the next part will be a port if the expansion up to
     that point is a unit op.  If it is already a port, then the next part
     will be a property or composition
     A colon indicates that the next part will be a parameter
     
     The operators are:
       
       = assign the rhs to the target
       ~= estimate the target using the rhs
       -> connect the lhs port to the rhs port
       
     If the rhs is missing the target is emptied or disconnected.
     """
  
    def __init__(self, baseFlowsheet=None, infoCallBack=None, optimizeCode=0):
        """ create a base flowsheet and other initialization"""
        self.EnsureUnitSystem()
        if optimizeCode:
            SetUpCodeOptimization(optimizeCode)
        if not baseFlowsheet:
            # create root flowsheet
            baseFlowsheet = Flowsheet.Flowsheet()
            if infoCallBack:
                self.infoCallBack = infoCallBack
            else:
                self.infoCallBack = InfoCallBack()
            baseFlowsheet.infoCallBack = self.infoCallBack

            #give the main flowsheet the name of "/"
            baseFlowsheet.name = '/'
            self.thermoAdmin = ThermoAdmin()
            baseFlowsheet.SetThermoAdmin(self.thermoAdmin)
            msgStack = self.thermoAdmin.GetMsgStack()
            if msgStack:
                stay = True
                while stay:
                    msg, args, msgType = msgStack.pop(0)
                    baseFlowsheet.InfoMessage(msg, args, msgType)
                    if not msgStack:
                        stay = False
            #baseFlowsheet.SetThermoAdmin(self.thermoAdmin)

            self.createdRoot = 1
        else:
            self.thermoAdmin = baseFlowsheet.GetThermoAdmin()
            if not self.thermoAdmin:
                baseFlowsheet.SetThermoAdmin(self.thermoAdmin)
            self.createdRoot = 0

        self.currentObj = self.root = baseFlowsheet
                
        self.output = sys.stdout
        self.input = sys.stdin
        #self.errorFile = sys.stderr
        self.errorFile = sys.__stdout__
        self.logFile = None
        self.hold = 0   # if true, then solve won't be called
        
        #How many versions of each case to keep?
        #a new version is created each time a case is stored
        self.maxCaseVersions = 1
        
        #Keep this onein case it is needed
        self.lastStoredPath = ''
        
        #Some member varaibles used when logging commands
        self.iswaiting = 0
        self.idxForQuote = None
        self.quote = None
        
        self.defaultPropertyOrder = [VPFRAC_VAR, T_VAR, P_VAR, MOLEFLOW_VAR, MASSFLOW_VAR, VOLFLOW_VAR, STDVOLFLOW_VAR,
                                     H_VAR, ENERGY_VAR, MOLE_WT, ZFACTOR_VAR ]
        
        
        # modules from which objects can be created - subclasses might want to append to this
        self.createableModules = ['sim.unitop', 'sim.thermo', 'sim.solver', 'sim.design']
        # add localsiminfo packages to createableModules
        try:
            for pkg in localsiminfo.packages:
                self.createableModules.append(pkg)
        except:
            pass
        
        self.commandInProcess = ''

        # Check all the thermo provider versions
        # Trap the error here so i may proceed as wrong version
        #    may only limit my access to certain functionalites
        try:
            if self.createdRoot:
                self.thermoAdmin.CheckThermoVersion()
        except (SimError, CmdError), e:
            self.root.InfoMessage(e.messageKey, e.extraData, MessageHandler.errorMessage)
            
        self.clipboard = Clipboard()
        
    def CleanUp(self):
        if self.createdRoot and self.root:
            self.root.CleanUp()
            self.root.SetInfoCallBack(None)
            self.clipboard.Clear()
            if self.thermoAdmin:
                self.thermoAdmin.CleanUp()
                self.thermoAdmin = None
            self.root = None
        self.units.CleanUp()
        self.units = None

        if self.logFile:
            try:
                self.logFile.close()
                self.logFile = None
            except: pass
        
        
    def EnsureUnitSystem(self):
        """Make sure there is a unit system"""
        #__Init__ calls this method.
        #It was originally creating the unit system over and over after each "clear" call
        #Was it neccessary??
        if not hasattr(self, 'units'):
            self.units = None
        if self.units == None:
            self.units = units.UnitSystem()

    def SetUnitSystem(self, unitSystem):
        """Sets the unit system"""
        try:
            if self.units:
                self.units.CleanUp()
        except:
            pass            
            
        self.units = unitSystem
    def GetUnitSystem(self):
        """Return the instance of the unitSystem"""
        return self.units
        
    def safeOpen(self, name, mode, keepVersions=False):
        """
        if global variable netServer is defined, then use its open function
        """
        if netServer:
            if mode == 'w' and keepVersions and self.maxCaseVersions != 0:
                return netServer.open(self.root, name, mode)
            else:
                return netServer.open(self.root, name, mode)
        else:
            if mode == 'w' and keepVersions and self.maxCaseVersions != 0:
                try:
                    return VersionedOutputFile(name, self.maxCaseVersions)
                except:
                    return open(name, mode)
            else:
                return open(name, mode)

    def GetNextTerm(self, text):
        """
        get white space delimited next term and remaining text
        return (firstterm, remaining)
        """
        if text and text[0] in '\'"':
            terms = re.split(text[0], text[1:], 1)
        else:
            terms = re.split(r'\s', text, 1)
        if len(terms) == 0: return  ('','')
        if len(terms) == 1: return (string.strip(terms[0]), '')
        else: return (string.strip(terms[0]), string.strip(terms[1]))

    def ReadLine(self, inFile, outFile):
        """read a single line - prompt if tty"""
        try:
            if hasattr(outFile,'isatty') and outFile.isatty():
                if self.currentObj and hasattr(self.currentObj, 'GetPath'):
                    if not self.iswaiting:
                        outFile.write(self.currentObj.GetPath() + '> ')
                    else:
                        outFile.write('... ')
                else:
                    outFile.write('Illegal current object> ')
        except:
            if self.currentObj and hasattr(self.currentObj, 'GetPath'):
                if not self.iswaiting:
                    outFile.write(self.currentObj.GetPath() + '> ')
                else:
                    outFile.write('... ')
        return inFile.readline()

    def ProcessCommandStream(self, inFile, outFile, errFile=sys.stdout):
        """
        reads commands from inFile, process them and write the output
        to outFile.
        """
        locked = 0
        try:
            if globalLock:
                globalLock.acquire()
                locked = 1
                
            savedIn = self.input
            savedOut = self.output
            savedErr = self.errorFile
            self.input = inFile
            self.output = outFile
            self.errorFile = errFile
            
            cmd = self.ReadLine(inFile, outFile)
            while cmd:
                self.idxForQuote = None
                if len(cmd) > 3 and (cmd[-4:-1] == "'''" or cmd[-4:-1] == '"""'):
                    quote = self.quote = cmd[-4:-1]
                    cmd = cmd[:-4]
                    self.idxForQuote = len(cmd)  #Used to log the command properly
                    self.iswaiting = 1
                    line = self.ReadLine(inFile, outFile)
                    while line and line[:3] != quote:
                        cmd += line
                        line = self.ReadLine(inFile, outFile)
                    self.iswaiting = 0
                try:
                    if not inFile.isatty():
                        outFile.write('>> ' + cmd)
                        if cmd[-1] != '\n':
                            outFile.write('\n')
                except:
                    pass
                
                if globalLock:
                    globalLock.release()
                    locked = 0
                    
                cmd = string.strip(cmd)
                if cmd == 'quit': break
                cmdResult = self.ProcessCommandString(cmd)
                
                if globalLock:
                    globalLock.acquire()
                    locked = 1
                    
                if cmdResult:
                    try:
                        outFile.write(cmdResult + '\n')
                    except:
                        pass
                
                cmd = self.ReadLine(inFile, outFile)
        finally:
            self.input = savedIn
            self.output = savedOut
            if locked:
                globalLock.release()
            
    def ProcessCommand(self, rawCmd):
        """parses and acts upon a single command"""
        
        try:
            cmd = RemoveComments(rawCmd)
        except:
            #Do old code
            cmd = re.sub('#.*', '', rawCmd)  # remove comments
            cmd = string.strip(cmd)
            
        self.commandInProcess = rawCmd
        
        # get lhs description
        (lhsDesc, remaining) = self.GetNextTerm( cmd )

        if self.logFile and lhsDesc != 'log' and lhsDesc != 'read':
            logCmd = rawCmd
            if self.idxForQuote != None and self.quote:
                #Log the quotes
                logCmd = ''.join((rawCmd[:self.idxForQuote], self.quote, '\n', rawCmd[self.idxForQuote:], '\n', self.quote))
            self.idxForQuote = None
            self.logFile.write(logCmd + '\n')
            self.logFile.flush()
            
        if not cmd:
            return ''
            
        if commands.has_key(lhsDesc):
            if not lhsDesc in readOnlyCommands:
                if self.root and (self.root.IsForgetting() or self.root.IsSolving()):
                    self.root.InfoMessage('CMDCantProcess', (cmd, ))
                    return ''
            if not lhsDesc in ['store', 'export', 'import', 'recall']:
                remaining = dequote(remaining)
            return commands[lhsDesc](self, remaining)
        else:
            c = lhsDesc[0]
            if c == '/':
                lhsObj = self.GetObject(self.root, lhsDesc[1:])
            elif c == TH_ADMIN_KEYWORD:
                lhsObj = self.GetObject(self.thermoAdmin, lhsDesc[1:])
            else:
                lhsObj = self.GetObject(self.currentObj, lhsDesc)

            # get the operator
            (operator, remaining) = self.GetNextTerm(remaining)
            if not operator:
                #if type(lhsObj) == type(()):
                #    lhsObj = lhsObj[0]
                return self.RenderObject(lhsObj)
            if self.root and (self.root.IsForgetting() or self.root.IsSolving()):
                self.root.InfoMessage('CMDCantProcess', (cmd, ))
                return ''
            if operators.has_key(operator):
                return operators[operator](self, lhsObj, dequote(remaining))
            else:
                raise CmdError('CMDBadOperator', operator)

        self.commandInProcess = ''
        return ''

    def ProcessCommandString(self, rawCmd):
        """Gets a string with a command, process it and returns an output as string"""
        
        retVal = None
        try:
            if rawCmd:
                #chack if we are going to have problems with semi colons put in between quotes?
                #This is VERY long code and there must be a quicker way of doing it

                if ('"' in rawCmd or "'" in rawCmd) and (';' in rawCmd):
                    cmds = Tokenize(rawCmd, ';', False)
                    
                else:
                    #do the normal thing
                    cmds = rawCmd.split(';')
                retVal = ''
                for cmd in cmds:
                    if cmd != None:
                        cmdResult = self.ProcessCommand(cmd)
                        if not self.root:
                            return retVal  # probably logged out
                        
                        
                        ##Don't add this code yet until it is needed#######
                        #Make sure, the forget is done properly in a solver (flowsheet)
                        #remember that self.root can be different from a flowsheet
                        #when running as an initScript.
                        #solver = self.root.Solver()
                        #if solver:
                        #    solver.SolverForget()
                        ####################################################
                        
                        self.root.SolverForget()  # not solving, but should still forget
                        if cmdResult:
                            retVal += str(cmdResult)
                
                ####################################################
                #solver.Solve()        
                ####################################################
                
                
                self.root.Solve()
                     
        except (SimError, CmdError), e:
            self.root.InfoMessage(e.messageKey, e.extraData, MessageHandler.errorMessage)
        except VMGerror, e:
            self.root.InfoMessage('CMDVMGError', (rawCmd, str(sys.exc_type), str(e)), MessageHandler.errorMessage)
        except VMGwarning, e:
            self.root.InfoMessage('CMDVMGWarning', (str(e),), MessageHandler.infoMessage)
    
        except ConsistencyError, e:
            self.root.InfoMessage(str(e), None, MessageHandler.errorMessage)

        return retVal

    def Cd(self, toDesc):
        currentObj = self.currentObj
        
        if not toDesc:
            obj = currentObj
        else:
            if toDesc[0] == '/':
                obj = currentObj = self.currentObj = self.root
                toDesc = toDesc[1:]
            elif toDesc[0] == '$':
                obj = currentObj = self.currentObj = self.thermoAdmin
                toDesc = toDesc[1:]
                
            if toDesc == '..' or toDesc[0:3] == '../':
                if hasattr(currentObj, 'GetParent'):
                    obj = currentObj.GetParent()
                else:
                    obj = None
                if obj == None:
                    obj = self.currentObj
                elif toDesc[0:3] == '../':
                    self.currentObj = obj
                    return self.Cd(toDesc[3:])
            else:
                obj = self.GetObject(currentObj, toDesc)
                if not obj or type(obj) == type(()) or not hasattr(obj, 'GetPath')\
                   or isinstance(obj, CreateObject):
                    raise CmdError('CMDCDInvalidObject', toDesc)
            
        self.currentObj = obj
        return obj.GetPath()
            
    def Log(self, toDesc):
        """
        log all commands to file described by toDesc.
        If toDesc begins with +, then append, otherwise overwrite
        """
        if self.logFile:
            try:
                self.logFile.close()
                self.logFile = None
            except: pass
            
        toDesc = string.strip(toDesc)
        if toDesc:
           if toDesc[0] == '+':
               mode = 'a'
               toDesc = string.strip(toDesc[1:])
           else:
               mode = 'w'
        
           logFile = self.safeOpen(toDesc, mode)
           self.logFile = logFile
           
        return ''
    
    def Read(self, inDesc):
        """Process commands from file inDesc"""

        try:
            inFile = self.safeOpen(inDesc, 'r')
        except IOError:
            self.root.InfoMessage('CMDCouldNotOpenFile', inDesc)
            return
        
        try:
            self.root.InfoMessage ('CMDNotifyBeforeReadFile', inDesc)
            self.ProcessCommandStream(inFile, self.output)
        except CallBackException, e:
            self.root.InfoMessage('CMDCallBackException', str(e))
        except Exception, e:
            str_e = str(e)
            tb = ''
            for i in traceback.format_tb(sys.exc_traceback):
                tb += i + '\n'
            self.root.InfoMessage('CMDUnhandledError', (str(sys.exc_type), str_e, tb))

        inFile.close()
        self.root.InfoMessage ('CMDNotifyReadFile', inDesc)
        return ''
    
    def Export(self, remaining):
        
        #Disect parameters
        #parameters = remaining.split()
        parameters = Tokenize(remaining, dequote=True)
        try:
            objDesc = parameters[0]
            path = parameters[1]
            flag = parameters[2]
            rest = parameters[3:]
        except:
            self.root.InfoMessage ('CMDExportObjNotUOp', (remaining,))
            return
        
        #First get the object on which stuff will be done
        if objDesc == '/':
            obj = self.root
        elif objDesc[0] == '/':
            obj = self.GetObject(self.root, objDesc[1:])
        else:
            obj = self.GetObject(self.currentObj, objDesc)
        if not isinstance(obj, UnitOperations.UnitOperation):
            self.root.InfoMessage ('CMDExportObjNotUOp', (objDesc,))
            return

        #if obj == self.root and flag == 'Full':
            #objCopy = obj
        #else:
            #objCopy = copy.deepcopy(obj)
        

        if flag == 'Blank':
            objCopy = copy.deepcopy(obj)
            objCopy.parentUO = None
            
            #Delete connections of port being 
            ports = objCopy.GetPorts(IN|OUT|MAT|ENE|SIG)
            for port in ports:
                port._connection = None
                
            #Define a method that clears a unit op
            def MakeBlank(uo):
                
                if isinstance(uo, Flowsheet):
                    #Clear stacks
                    uo._solveStack = []
                    uo._forgetStack = []
                    uo._resetNewCalcStack = []
                    uo._resetNewFixedStack = []
                    uo._iterationStack = []
                    uo._consistencyErrorStack = []
                    uo._isForgetting = 0                    
 
                uo.thermoAdmin = None
                uo.thCaseObj= None
                uo._stackStatus = 0
                uo._pushBlocked = 0
                ports = uo.GetPorts(IN|OUT|MAT)
                for port in ports:
                    port._estimated = 0
                    port._stackStatus = 0
                    port._flashResults = None
                    for prop in port._properties.values():
                        prop._value = None
                        prop._calcStatus = UNKNOWN_V
                    for propLst in port._arrProperties.values():
                        for prop in propLst:
                            prop._value = None
                            prop._calcStatus = UNKNOWN_V
                    for prop in self._compounds:
                        prop._value = None
                        prop._calcStatus = UNKNOWN_V                        
        
                ports = uo.GetPorts(IN|OUT|ENE)
                for port in ports:
                    port._stackStatus = 0
                    port._estimated = 0
                    for prop in port._properties.values():
                        prop._value = None
                        prop._calcStatus = UNKNOWN_V
                        
                ports = uo.GetPorts(SIG)
                for port in ports:
                    port._estimated = 0
                    port._stackStatus = 0
                    port._prop._value = None
                    port._prop._calcStatus = UNKNOWN_V
                    
            #Walk the method into every child unitop of the copy
            objCopy.walk(MakeBlank)
        elif flag == 'Full':
            objCopy = obj
            pass
        else:
            foreignMod = flag
            if foreignMod:
                try: 
                    module = __import__(foreignMod, {}, {})
                finally:
                    try:
                        if rest:
                            retVal = eval('%s.ExportHandler(self, path, obj, *rest)' %foreignMod)
                            return retVal
                        else:
                            retVal = eval('%s.ExportHandler(self, path, obj)' %foreignMod)
                            return retVal
                    except:
                        self.root.InfoMessage ('CMDExportUnkModule', (foreignMod,) )
                        return
                #try:
                    #if rest:
                        #return module.ExportHandler(self, path, obj, *rest)
                    #else:
                        #return module.ExportHandler(self, path, obj)
                #except:
                    #self.root.InfoMessage ('CMDExportUndMeth', (foreignMod, 'ExportHandler') )
                    #return
                return
            else:
                self.root.InfoMessage ('CMDExportUnkFlag', (flag,) )
                return
        
        
        #Now get the file path
        rlimit = sys.getrecursionlimit()
        sys.setrecursionlimit(5000)
        f = self.safeOpen(path, 'w')
        f.write('REL_%d\n' % Flowsheet.VERSION[0])
        objCopy.SetInfoCallBack(None)
        pickle.dump((objCopy, Flowsheet.revertToVersion), f)
        f.close()
        sys.setrecursionlimit(rlimit)
        self.root.InfoMessage ('CMDNotifyExport', (objDesc, path, flag) )
        
    def Import(self, parameters):
        """The import command has the following format:
            import fromPath nameOfObject dirForExtraFiles
        
            IMPORTANT: the import always imports into the current object
            and nameOfObject is not a path but only a name. Future implementations
            might change this but not now
        
            sample calls are as follows"
            no quotes. Old format. Only two parameters allowed
            import C:\mydir\my file name.s42 myobjname
               imports the file "C:\mydir\my file name.s42" into the object "myobjname"
            
            with quotes. New way. Quotes can be " or '
            import "C:\mydir\my file name.s42" "myobjname"
               imports the file "C:\mydir\my file name.s42" into the object "myobjname"
            
            import "C:\mydir\my file name.s42" "myobjname" "C:\my appdir"
               imports the file "C:\mydir\my file name.s42" into the object "myobjname" 
               and if there are extra files, they are put in "C:\my appdir"
            
        """
        
        rlimit = sys.getrecursionlimit()
        sys.setrecursionlimit(10000)        
        
        
        iszip = False
        tempFile = ''     #Name of temporary file
        try:
            
            #Disect parameters
            
            fromFile = ''          #Source file
            uncompressToDir = ''   #Directory where to uncompress files to
            if '"' in parameters or "'" in parameters:
                tokens = Tokenize(parameters, ' ', True)
                fromFile = tokens.pop(0)
                newObjName = tokens.pop(0)
                if tokens:
                    uncompressToDir = tokens.pop(0)
                    if os.path.isdir(uncompressToDir):
                        uncompressToDir = os.path.abspath(uncompressToDir)
                    elif os.path.isfile(uncompressToDir):
                        uncompressToDir = os.path.abspath(uncompressToDir)
                        uncompressToDir, dummy = os.path.split(uncompressToDir)
                        
            else:
                #Old working code. Do not mess with it
                tokens = parameters.split()
                fromFile = string.join(tokens[:-1])
                newObjName = tokens[-1]
                
                
            fromFile = os.path.abspath(fromFile)
            if not uncompressToDir:
                uncompressToDir = os.path.abspath(fromFile)
                uncompressToDir, dummy = os.path.split(uncompressToDir)
            
            
            #see if it is a zip file
            iszip = zipfile.is_zipfile(fromFile)
            
            #Make sure it can be opened
            f = self.safeOpen(fromFile, 'r')
            
            if iszip:
                f.close()
                
                #Extract sim42 info into a temporary file
                
                z = zipfile.ZipFile(fromFile)
                if z.testzip(): 
                    raise CmdError('CMDCouldNotOpenFile', (fromFile,))  #Troubles !!
                fileLst = z.namelist()
                idx = fileLst.index(ZIPFILENAME)                   #will raise error if not there
                #Can't pass this message since there is nobody to receive it
                #self.root.InfoMessage ('CMDExtracting', ZIPFILENAME)
                try:
                    #Try creating a temporary file right where the file is being opened
                    f = self.safeOpen('%s.temp' %fromFile, 'wb', False)
                    tempFile = '%s.temp' %fromFile
                except:
                    try:
                        #Try a temporary folder
                        tempFile = tempfile.mktemp()
                        f = self.safeOpen(tempFile, 'wb', False)
                    except:
                        tempFile = ''
                        f = StringIO.StringIO()
                    
                f.write(z.read(ZIPFILENAME))
                f.flush()
                fileLst.pop(idx)
                if not isinstance(f, StringIO.StringIO):
                    f.close()
                    #Open the temporary file for the unpickle part
                    f = self.safeOpen(tempFile, 'r', False)
            
            
            
            relLine = f.readline()
            if relLine[:4] == 'REL_':
                relNumber = int(relLine[4:-1])
            else:
                relNumber = 0
                f.seek(0)
            
            if relNumber < 5:
                # check for old DistCol modules
                f2 = StringIO.StringIO()
                line = f.readline()
                while line:
                    if line == 'csim.unitop.DistCol\n':
                        f2.write('cNumeric\n')
                    else:
                        f2.write(line)
                    line = f.readline()
                f.close()
                f2.seek(0)
                f = f2
                    
            try:
                (uo, revertFunction) = pickle.load(f)            
            except ValueError:
                #Check if the problem was because of a huge float value
                f.seek(0)
                relLine = f.readline()
                if not relLine[:4] == 'REL_':
                    f.seek(0)
                
                f2 = StringIO.StringIO()
                line = f.readline()
                while line:
                    check = ''
                    label = ''
                    if line[0] == 'F':
                        label = line[0]
                        check = line[1:]
                    elif line[0:2] == 'aF':
                        label = line[:2]
                        check = line[2:]
                     
                    if check:
                        if check == '-1.#INF\n':
                            f2.write('%s-1.0e308\n' %label)
                        elif check == '1.#INF\n':
                            f2.write('%s1.0e308\n' %label)    
                        elif check == '-1.#IND\n':
                            f2.write('%s0.0\n' %label)
                        elif check == '1.#IND\n':
                            f2.write('%s0.0\n' %label)
                        elif check == '1.#QNAN\n':
                            f2.write('%s0.0\n' %label)
                        elif check == '-1.#QNAN\n':
                            f2.write('%s0.0\n' %label)
                        else:
                            idx = check.find('e')
                            if idx > -1:
                                try:
                                    expVal = int(check[idx+1:-1])
                                    if expVal > 307:
                                        f2.write('%s%s+307\n' %(label, check[:idx+1]))
                                    elif expVal < -307:
                                        f2.write('%s%s-307\n' %(label, check[:idx+1]))
                                    else:
                                        f2.write(line)
                                except:
                                    f2.write(line)
                            else:
                                f2.write(line)
                                                        
                    else:
                        f2.write(line)
                    line = f.readline()
                f.close()
                f2.seek(0)
                relLine = f2.readline()
                if not relLine[:4] == 'REL_':
                    f2.seek(0)
                f = f2
                (uo, revertFunction) = pickle.load(f)            
            
            f.close()
            
            # make any necessary changes for different versions
            if hasattr(uo, 'adjustVersion'):
                uo.adjustVersion(revertFunction)
                #Set a temporary callback
                uo.SetInfoCallBack(self.infoCallBack)
                #Trigger a solve in case it was needed
                uo.Solve()
                uo.SetInfoCallBack(None)
           
            self.currentObj.AddUnitOperation(uo, newObjName)
                
            thAdmin = uo.GetThermoAdmin()
            self.thermoAdmin.MergeThermoAdmin(thAdmin)
            #thAdmin.CleanUp()
            if iszip:
                #Force for this directory to exist
                if not os.path.isdir(uncompressToDir): MakeDirs(uncompressToDir)
                
                for filePath in fileLst:
                    #For some reason, the zip module returns the file paths
                    # with / instead of being plattform dependant
                    #This hack fixes it for windows
                    if '/' in filePath: fixedPath = filePath.replace('/', '\\')
                    else: fixedPath = filePath
                    if os.path.isabs(fixedPath): raise CmdError('CMDCouldNotOpenFile', fixedPath)
                    
                    #Now make sure that the folder exists
                    dirName, fileName = os.path.split(fixedPath)
                    if dirName:
                        dirName = os.path.join(uncompressToDir, dirName)
                        if not os.path.isdir(dirName): MakeDirs(dirName)
                        fileName = os.path.join(dirName, fileName)
                    else:
                        fileName = os.path.join(uncompressToDir, fileName)
                    
                    f = self.safeOpen(fileName, 'wb')
                    self.root.InfoMessage ('CMDExtracting', (fixedPath, uncompressToDir))
                    f.write(z.read(filePath))
                    f.close()
                z.close()
            
            
        except CmdError, e:
            sys.setrecursionlimit(rlimit)
            self.root.SetInfoCallBack(self.infoCallBack)
            if tempFile:
                try: os.remove(tempFile)
                except: pass
            sys.setrecursionlimit(rlimit)
            raise e
        except StandardError, e:
            sys.setrecursionlimit(rlimit)
            self.root.SetInfoCallBack(self.infoCallBack)
            self.root.InfoMessage ('CMDRecallError', (fromFile, str(e)))
            sys.setrecursionlimit(rlimit)
            raise e
        
        if tempFile:
            try: os.remove(tempFile)
            except: pass
            
        sys.setrecursionlimit(rlimit)
        
        
    def MaxCaseVersions(self, maxCaseVersions):
        """Returns or sets the max amount of versions of each case to keep. A negative
        value does not delete any version (i.e. backs up everything"""
        
        #Return the current val
        if maxCaseVersions == '':
            return self.maxCaseVersions
        
        #Update the value
        else:
            try:
                val = maxCaseVersions.split()
                val = int(val[-1])
                self.maxCaseVersions = val
            except:
                pass
        
        
    def Store(self, parameters):
        """pickle the root flowsheet and thermo admin to toFile
        parameters can be a simple unquoted string with the name of the destiny file
        or a complex string with tokens separated with spaces and delimited by quotes if
        necessary. If the last parameter is "z" then it compresses the files together
        if it is "n" then it just stores without compressing. 
        
        NOTE: "z" and "n" always have to be quoted !
        NOTE2: " and ' are both accepted quotes
        NOTE3: if "z" or "n" are not given, the it just stores the file normally
        Examples:
        No quotes needed for just one parameter
        C:\My Files\sim.s42  -> stores the file normally
        
        Quotes needed for more than one parameter and spaces in the names
        store "C:\My Files\sim.s42" "n" 
           stores the file normally
        store "C:\My Files\sim.s42" "z" 
           stores the file compressing it
        store "C:\My Files\sim.s42" "z"
           stores the file compressing it
        
        Quotes not needed if there are no spaces in the parameters
        store C:\Files\sim.s42 "z"
           stores the file compressing it
        
        Groups of files
        store C:\Files\sim.s42 "C:\P\file 2.txt" 'C:\P\file 3.txt' "z" -> 
            stores all the files together compressing them
            
        store C:\Files\sim.s42 "C:\P\file 2.txt" 'C:\P\file 3.txt' "n" -> 
            stores all the files together as zip file,but no compression
            
        store C:\Files\sim.s42 "C:\P\file 2.txt" 'C:\P\file 3.txt' -> 
            stores all the files together as zip file (even though "n" was not given),but no compression
            
        store "C:\My Files\sim.42" "C:\P\file 2.txt" "C:\folder1\folder2" "z" -> 
            zips the files together including all the files contained in folder2
            The unzipped structure will be, file 2.txt and folder2 at the same level
            
            
        """
        createdTempFile = False
        try:
            toFile = parameters
            dozip = False
            tokens = []
            
            #See if the files should get zipped
            if '"' in parameters or "'" in parameters:
                tokens = Tokenize(parameters, ' ', True)
                toFile = tokens.pop(0)
                if not tokens:
                    dozip = False
                else:
                    dozip = tokens.pop()
                    if dozip == "z":
                        dozip = True
                    elif dozip == "n":
                        dozip = False
                    else:
                        #Not a parameter. Put it back in the list
                        tokens.append(dozip)
                        dozip = False
                        

            
            Flowsheet.rootPathName = toFile
            if dozip or tokens:
                #First validation
                if ZIPFILENAME in tokens or '%s.temp' %toFile in tokens:
                    raise SimError('CMDCantUseFileName', ('%s, %s' %(ZIPFILENAME, '%s.temp' %toFile)))
                
                #Validate and build tree structure of extra files
                fileLstAbs = []  #Find files by absolute paths
                fileLstRel = []  #Zip files by relative paths
                #Tokens contains only the "extra" files
                for name in tokens:
                    levelDown = False
                    if name[-2:] == "\*" or name[-2:] == "/*":
                        levelDown = True
                        name = name[:-2]
                    if os.path.isdir(name):
                        #A directory... get all the files from inside of that directory
                        #  except those such as __xx
                        #Only take the name of the folder as the root
                        #C:\\folder1\\folder2 would only take folder2 for the structure
                        absPath = os.path.abspath(name)
                        rootPath, storeFolder = os.path.split(absPath)
                        tempDir = os.getcwd()  
                        try:
                            os.chdir(rootPath)
                            tempLst = []
                            os.path.walk(storeFolder, AppendFileNames, tempLst)
                            for fName in tempLst:
                                #exclude those wirh names starting with __
                                if fName[:len(storeFolder)+3] != storeFolder + '\\__':
                                    #Make sure it can be opened
                                    f = self.safeOpen(fName, 'r', False)
                                    f.close()
                                    relName = fName
                                    if levelDown:
                                        if relName[:len(storeFolder)] == storeFolder:
                                            relName = relName.split('\\', 1)
                                            if len(relName) > 1:
                                                relName = relName[1]
                                            else:
                                                break
                                    fileLstRel.append(relName)
                                    fileLstAbs.append(os.path.join(rootPath, fName))
                        finally:
                            os.chdir(tempDir)
                        
                    elif os.path.isfile(name):
                        #Make sure it can be opened
                        f = self.safeOpen(name, 'r', False)
                        f.close()
                        #Assume loose files always go at the top in hierarchy
                        fileLstAbs.append(os.path.abspath(name))
                        fileLstRel.append(os.path.split(name)[1])
                    else:
                        raise CmdError('CMDCouldNotOpenFile', name)
                    
                
                #open and close the file so it makes a backup of it (if maxversions > 0)
                #This will also raise an error if the file was not meant to be opened
                f = self.safeOpen(toFile, 'w', True)
                f.close()
                
                
                #open a temporary file for doing the pickle. Do not use the temp files support
                #because zip only accepts closed valid files
                f = self.safeOpen('%s.temp' %toFile, 'w', False)
                createdTempFile = True
            else:
                f = self.safeOpen(toFile, 'w', True)
                
            
            #This is neede by pickle so it doesn't crash in large simulations
            rlimit = sys.getrecursionlimit()
            sys.setrecursionlimit(10000)
            
            
            #Prepare for storing
            
            #Clear info callback
            self.root.SetInfoCallBack(None)
            
            #Keep prop types (scaling factors)
            self.root.PropTypes = PropTypes   # so this instance is stored and recalled
            
            #Keep unit set if it is not a default one
            setName = self.units.GetDefaultSet()
            #Store the surrent set name as an info object
            infoDict = self.root.info
            if not infoDict.has_key(SIMSTORE_INFO):
                infoDict[SIMSTORE_INFO] = SimInfoDict(SIMSTORE_INFO, infoDict)
            storeinfo = infoDict[SIMSTORE_INFO]
            storeinfo['UnitSetName'] = self.units.GetDefaultSet()
            if not setName in self.units.GetBaseSetNames():
                #The set is a custom dictionary.
                #Store it as a plain dictionary such that we don't pollute the sim42 object
                unitSet = self.units.GetUnitSet(setName)
                setAsRawDict = {}
                setAsRawDict.update(unitSet)
                
                storeinfo['DefCustomSet'] = (setName, setAsRawDict)
            else:
                if storeinfo.has_key('DefCustomSet'):
                    del storeinfo['DefCustomSet']
            
            #Write the info into the file
            f.write('REL_%d\n' % Flowsheet.VERSION[0])
            pickle.dump((self.root, Flowsheet.revertToVersion), f)
            #import gnosis.xml.pickle
            #gnosis.xml.pickle.dump((self.root, Flowsheet.revertToVersion), f)            
            
            #Recover 
            del self.root.PropTypes
            self.root.SetInfoCallBack(self.infoCallBack)
            f.close()            
            
            #now zip files
            if tokens or dozip:
                mode = zipfile.ZIP_DEFLATED
                if not dozip:
                    #I was given extra files but I don't want to zip them???
                    #Put them together with zip, but don't compress them
                    mode = zipfile.ZIP_STORED
                
                z = zipfile.ZipFile(toFile, 'w', mode)
                self.root.InfoMessage ('CMDCompressing', ZIPFILENAME)
                z.write('%s.temp' %toFile, ZIPFILENAME)
                for i in range(len(fileLstAbs)):
                    self.root.InfoMessage ('CMDCompressing', fileLstRel[i])
                    z.write(fileLstAbs[i], fileLstRel[i])
                z.close()
                
            
            #Leaving
            sys.setrecursionlimit(rlimit)
            self.lastStoredPath = toFile
            self.root.InfoMessage ('CMDNotifyStore', toFile)
            
        finally:
            try:
                f.close()
                if createdTempFile and os.path.isfile('%s.temp' %toFile):
                    os.remove('%s.temp' %toFile)
            except:
                pass
        
    def Recall(self, parameters):
        """unpickle the root flowsheet from fromFile
        parameters can be a simple unquoted string with the name/path of the source file. 
        
        parameters could also be a complex string with two tokens separated with 
        spaces and delimited by quotes if necessary. The first token is the name of the
        source file and the second token (if given) is the path where the extra files 
        (if any) will be put. The extra files can come when the sim42 case was stored as a
        group of zip files, the uncompressed s42 file itself does not need to be kept anywhere in the disk
        but the extra files should always be uncompressed and put on the disk.
        
        In case a second token is not given but the file is a compressed group of multiple files
        then the extra files will be uncompressed wherever the compressed files resides
        """
        
        # get rid of old case
        oldRoot = self.root
        self.CleanUp()
        self.root = oldRoot  # need to have this in case something goes wrong.
            
        #self.units = units.UnitSystem()
        self.EnsureUnitSystem()
        
        rlimit = sys.getrecursionlimit()
        sys.setrecursionlimit(10000)        
        
        iszip = False
        tempFile = ''     #Name of temporary file
        try:
            fromFile = ''          #Source file
            uncompressToDir = ''   #Directory where to uncompress files to
            if '"' in parameters or "'" in parameters:
                tokens = Tokenize(parameters, ' ', True)
                fromFile = tokens.pop(0)
                if tokens:
                    uncompressToDir = tokens.pop(0)
                    if os.path.isdir(uncompressToDir):
                        uncompressToDir = os.path.abspath(uncompressToDir)
                    elif os.path.isfile(uncompressToDir):
                        uncompressToDir = os.path.abspath(uncompressToDir)
                        uncompressToDir, dummy = os.path.split(uncompressToDir)
                    else:
                        MakeDirs(uncompressToDir)
            else:
                fromFile = parameters
                
            fromFile = os.path.abspath(fromFile)
            if not uncompressToDir:
                uncompressToDir = os.path.abspath(fromFile)
                uncompressToDir, dummy = os.path.split(uncompressToDir)
            
            Flowsheet.rootPathName = fromFile
            
            #see if it is a zip file
            iszip = zipfile.is_zipfile(fromFile)
            
            #Make sure it can be opened
            f = self.safeOpen(fromFile, 'r')
            
            if iszip:
                f.close()
                
                #Extract sim42 info into a temporary file
                
                z = zipfile.ZipFile(fromFile)
                if z.testzip(): 
                    raise CmdError('CMDCouldNotOpenFile', (fromFile,))  #Troubles !!
                fileLst = z.namelist()
                idx = fileLst.index(ZIPFILENAME)                   #will raise error if not there
                #Can't pass this message since there is nobody to receive it
                #self.root.InfoMessage ('CMDExtracting', ZIPFILENAME)
                try:
                    #Try creating a temporary file right where the file is being opened
                    f = self.safeOpen('%s.temp' %fromFile, 'wb', False)
                    tempFile = '%s.temp' %fromFile
                except:
                    try:
                        #Try a temporary folder
                        tempFile = tempfile.mktemp()
                        f = self.safeOpen(tempFile, 'wb', False)
                    except:
                        tempFile = ''
                        f = StringIO.StringIO()
                    
                f.write(z.read(ZIPFILENAME))
                f.flush()
                fileLst.pop(idx)
                if not isinstance(f, StringIO.StringIO):
                    f.close()
                    #Open the temporary file for the unpickle part
                    f = self.safeOpen(tempFile, 'r', False)
                
            relLine = f.readline()
            if relLine[:4] == 'REL_':
                relNumber = int(relLine[4:-1])
            else:
                relNumber = 0
                f.seek(0)
            
            if relNumber < 5:
                # check for old DistCol modules
                f2 = StringIO.StringIO()
                line = f.readline()
                while line:
                    if line == 'csim.unitop.DistCol\n':
                        f2.write('cNumeric\n')
                    else:
                        f2.write(line)
                    line = f.readline()
                f.close()
                f2.seek(0)
                f = f2
                    
            self.root = self.currentObj = self.thermoAdmin = None
            try:
                (self.root, revertFunction) = pickle.load(f)
            except ValueError:
                #Check if the problem was because of a huge float value
                f.seek(0)
                relLine = f.readline()
                if not relLine[:4] == 'REL_':
                    f.seek(0)
                
                f2 = StringIO.StringIO()
                line = f.readline()
                while line:
                    check = ''
                    label = ''
                    if line[0] == 'F':
                        label = line[0]
                        check = line[1:]
                    elif line[0:2] == 'aF':
                        label = line[:2]
                        check = line[2:]
                     
                    if check:
                        if check == '-1.#INF\n':
                            f2.write('%s-1.0e308\n' %label)
                        elif check == '1.#INF\n':
                            f2.write('%s1.0e308\n' %label)    
                        elif check == '-1.#IND\n':
                            f2.write('%s0.0\n' %label)
                        elif check == '1.#IND\n':
                            f2.write('%s0.0\n' %label)
                        elif check == '1.#QNAN\n':
                            f2.write('%s0.0\n' %label)
                        elif check == '-1.#QNAN\n':
                            f2.write('%s0.0\n' %label)
                        else:
                            idx = check.find('e')
                            if idx > -1:
                                try:
                                    expVal = int(check[idx+1:-1])
                                    if expVal > 307:
                                        f2.write('%s%s+307\n' %(label, check[:idx+1]))
                                    elif expVal < -307:
                                        f2.write('%s%s-307\n' %(label, check[:idx+1]))
                                    else:
                                        f2.write(line)
                                except:
                                    f2.write(line)
                            else:
                                f2.write(line)
                                                        
                    else:
                        f2.write(line)
                    line = f.readline()
                f.close()
                f2.seek(0)
                relLine = f2.readline()
                if not relLine[:4] == 'REL_':
                    f2.seek(0)
                f = f2
                (self.root, revertFunction) = pickle.load(f)
                
                
            #import gnosis.xml.pickle
            #gnosis.xml.pickle.setParanoia(0)
            #(self.root, revertFunction) = gnosis.xml.pickle.load(f)
            if hasattr(self.root, 'PropTypes'):
                # replace global PropertyTypes with the stored ones - this affects future cases though
                #for key in self.root.PropTypes.keys():
                    #PropTypes[key] = self.root.PropTypes[key]
                PropTypes.update(self.root.PropTypes)
                #Make sure these guys did not get corrupted
                for key in (H_VAR, T_VAR, P_VAR):
                    PropTypes[key].calcType=INTENSIVE_PROP|CANFLASH_PROP
                    
                del self.root.PropTypes
                
                if self.root.version[0] < 77:
                    if PropTypes.has_key(SURFACETENSION_VAR):
                        PropTypes[SURFACETENSION_VAR].scaleFactor = -1.0
                    if PropTypes.has_key(SPEEDOFSOUND_VAR):
                        PropTypes[SPEEDOFSOUND_VAR].scaleFactor = -1.0
                    if PropTypes.has_key(THERMOCONDUCTIVITY_VAR):
                        PropTypes[THERMOCONDUCTIVITY_VAR].scaleFactor = -1.0
                    if PropTypes.has_key(VISCOSITY_VAR):
                        PropTypes[VISCOSITY_VAR].scaleFactor = -1.0
            #f.flush()
            f.close()
            
            
            if netServer:
                netServer.switchedRoot(oldRoot, self.root)
            
            # make any necessary changes for different versions
            self.root.adjustVersion(revertFunction)
            
            # the infoCallBack is not saved
            self.root.SetInfoCallBack(self.infoCallBack)
            
            #Restore unit set
            #import wingdbstub
            infoDict = self.root.info
            if infoDict.has_key(SIMSTORE_INFO):
                if infoDict[SIMSTORE_INFO].has_key('DefCustomSet'):
                    setName, setAsRawDict = infoDict[SIMSTORE_INFO]['DefCustomSet']
                    if not setName in self.units.GetSetNames():
                        #Update the custom UnitSet dictionary with the info from the raw dictionary
                        tempSet = vmgunits.units.UnitSet()
                        tempSet.update(setAsRawDict)
                        self.units.unitSets[setName] = tempSet
                if infoDict[SIMSTORE_INFO].has_key('UnitSetName'):
                    setName = infoDict[SIMSTORE_INFO]['UnitSetName']
                    if setName != None:
                        self.units.SetDefaultSet(setName)
            
            # update my members
            self.thermoAdmin = self.root.GetThermoAdmin()
            self.currentObj = self.root
            # the stored case may not have property package yet.
            if self.thermoAdmin == None:
                self.thermoAdmin = ThermoAdmin()
                self.currentObj.SetThermoAdmin(self.thermoAdmin)
 
            if iszip:
                for filePath in fileLst:
                    #For some reason, the zip module returns the file paths
                    # with / instead of being plattform dependant
                    #This hack fixes it for windows
                    if '/' in filePath: fixedPath = filePath.replace('/', '\\')
                    else: fixedPath = filePath
                    if os.path.isabs(fixedPath): raise CmdError('CMDCouldNotOpenFile', fixedPath)
                    
                    #Now make sure that the folder exists
                    dirName, fileName = os.path.split(fixedPath)
                    if dirName:
                        dirName = os.path.join(uncompressToDir, dirName)
                        if not os.path.isdir(dirName): MakeDirs(dirName)
                        fileName = os.path.join(dirName, fileName)
                    else:
                        fileName = os.path.join(uncompressToDir, fileName)
                    
                    f = self.safeOpen(fileName, 'wb')
                    self.root.InfoMessage ('CMDExtracting', (fixedPath, uncompressToDir))
                    f.write(z.read(filePath))
                    f.close()
                z.close()
            self.root.InfoMessage ('CMDFinishedRecall', fromFile)
 
        except CmdError, e:
            sys.setrecursionlimit(rlimit)
            self.CleanUp()
            #self.units = units.UnitSystem()
            self.EnsureUnitSystem()

            self.currentObj = self.root = Flowsheet.Flowsheet()
            self.root.name = '/'
            self.root.SetInfoCallBack(self.infoCallBack)
            self.thermoAdmin = ThermoAdmin()
            if tempFile:
                try: os.remove(tempFile)
                except: pass
            raise e
        except Exception, e:
            self.CleanUp()
            #self.units = units.UnitSystem()
            self.EnsureUnitSystem()
            self.currentObj = self.root = Flowsheet.Flowsheet()
            self.root.name = '/'
            self.root.SetInfoCallBack(self.infoCallBack)
            self.thermoAdmin = ThermoAdmin()
            self.root.InfoMessage ('CMDRecallError', (fromFile, str(e)), MessageHandler.errorMessage)
            
        if tempFile:
            try: os.remove(tempFile)
            except: pass
            
        sys.setrecursionlimit(rlimit)
        

        
    def Clear(self, desc=None):
        """reset the flowsheet to a new copy - argument is ignored"""
        infoCallBack = self.infoCallBack
        oldRoot = self.root
        # find deepest root
        while oldRoot.GetParent(): oldRoot = oldRoot.GetParent()
        
        self.CleanUp()
        out = self.output
        InitPropTypes(PropTypes)
        self.__init__(infoCallBack=infoCallBack)
        self.output = out
        if netServer:
            netServer.switchedRoot( oldRoot, self.root)
        self.root.InfoMessage ('CMDNotifyClear')
        
    def Units(self, unitSet):
        """set the default unit set to the one described by unitSet"""
        try:
            if not unitSet:
                return self.units.GetDefaultSet()
            response = self.units.SetDefaultSet(unitSet)
            if response == 1:
                self.root.InfoMessage ('CMDNotifyUnits', unitSet)
            else:
                raise CmdError('CMDInvalidUnitSet', unitSet)                
        except:
            raise CmdError('CMDInvalidUnitSet', unitSet)
        
    def SetLanguage(self, language):
        """
        set the language for messages
        """
        try:
            self.infoCallBack.SetLanguage(language)
        except:
            raise SimError('CouldNotLoadLanguage', language)
        

    def SetPropertyOrder(self, propList):
        """
        Set the properties and order to be displayed for material ports
        """
        result = ''
        if propList != '':
            props = string.split(propList)
            if props and props[0] == '+':
                self.defaultPropertyOrder = list(self.defaultPropertyOrder)
                self.defaultPropertyOrder.extend(props[1:])
            elif props and props[0] == '-':
                self.defaultPropertyOrder = list(self.defaultPropertyOrder)
                for prop in props[1:]:
                    if prop in self.defaultPropertyOrder:
                        self.defaultPropertyOrder.remove(prop)
                
            else:
                self.defaultPropertyOrder = props
        else:
            for i in self.defaultPropertyOrder:
                result += i + ' '
        return result

    def SetCommonProperties(self, propList):
        """
        Set the properties to be calculated for material ports
        """
        result = ''
        if not self.thermoAdmin: return
        providers = self.thermoAdmin.GetAvThermoProviderNames()
        
        #This will apply to all the providers
        usedList = []
        for provider in providers:
            if provider:
                if propList != '':
                    props = string.split(propList)
                    if props and props[0] == '+':
                        currentList = list(self.thermoAdmin.GetCommonPropertyNames(provider))
                        currentList.extend(props[1:])
                        self.thermoAdmin.SetCommonPropertyNames(provider, currentList)
                        self.root.ForgetAllCalculations()
                    elif props and props[0] == '-':
                        currentList = list(self.thermoAdmin.GetCommonPropertyNames(provider))
                        for prop in props[1:]:
                            if prop in currentList:
                                currentList.remove(prop)
                        self.thermoAdmin.SetCommonPropertyNames(provider, currentList)
                    else:
                        self.thermoAdmin.SetCommonPropertyNames(provider, props)
                        self.root.ForgetAllCalculations()
                else:
                    for i in self.thermoAdmin.GetCommonPropertyNames(provider):
                        if not i in usedList:
                            result += i + ' '
                            usedList.append(i)
                        
        #Finally make sure that all ports have and will get creted with all the necessary variables
        #to match the commonproperties
        
                            
        return result
        
    def SupportedProperties(self, dummy):
        """
        display the properties supported by provider
        """
        thermo = self.root.GetThermo()
        if thermo: provider = thermo.provider
        else: provider = None
        
        result = ''
        if provider:
            for i in self.thermoAdmin.GetPropertyNames(provider):
                result += i + '\n'
        return result

    def Contents(self, objDesc):
        """list contents of object described by objDesc"""   
        if not objDesc:
            obj = self.currentObj
        else:
            c = objDesc[0]
            if c == '/':
                obj = self.GetObject(self.root, objDesc[1:])
            elif c == TH_ADMIN_KEYWORD:
                obj = self.GetObject(self.thermoAdmin, objDesc[1:])
            else:
                obj = self.GetObject(self.currentObj, objDesc)
            if not obj or type(obj) == type(()):
                raise CmdError('CMDInvalidContentsObject', objDesc)
        result = ''
        if hasattr(obj, 'GetContents'):
            for i in obj.GetContents():
                #Hack to display units of this parameter properly
                if i[0] == 'StdLiqVolRefT':
                    myType = i[1].GetType()
                    value = i[1].GetValue()
                    unitName = ''
                    if myType and value != None:
                        unit = self.units.GetCurrentUnit(myType.unitType)
                        if unit:
                            unitName = unit.name
                            value = unit.ConvertFromSim42(value)
                    if unitName:
                        result += '\n%s: %s = %g %s' % (i[0], i[0], value, unitName)
                    else:
                        result += '\n%s: %s' % (i[0], str(i[1]))
                else:
                    result += '\n%s: %s' % (i[0], str(i[1]))
        return result
                
    def Add(self, lhsObj, remaining):
        """take the appropriate add action with respect to whatever lhsObj is"""
        if hasattr(lhsObj, 'Add'):            
            if isinstance(lhsObj, ThermoCase):
                response = lhsObj.Add(remaining)
                if str(response) != '':
                    self.root.InfoMessage ('CMDNotifyAddCompound', (lhsObj.case, remaining))
            else:
                self.root.InfoMessage ('CMDNotifyBeforeAdd', (PathOf(lhsObj), remaining))
                response = lhsObj.Add(remaining)
                if str(response) != '':
                    self.root.InfoMessage ('CMDNotifyAdd', (PathOf(lhsObj), remaining))
            return response


    def MoveCompound(self, lhsObj, remaining):
        # to be implemented.
        if isinstance(lhsObj, CreateObject):
            parentObj = lhsObj.parent
            cmp1Name = lhsObj.description
            cmp2Name = remaining
            if isinstance(parentObj, ThermoCase):
                ret = parentObj.MoveCompound(cmp1Name, cmp2Name)
                self.root.InfoMessage ('CMDNotifyMoveCompound', (parentObj.case, cmp1Name, cmp2Name))
                return ret
            
        elif isinstance(lhsObj, Ports.Port):
            fromPort = lhsObj
            c = remaining[0]
            if c == '/':
                toPort = self.GetObject(self.root, remaining[1:])
            elif c == TH_ADMIN_KEYWORD:
                return None
            else:
                toPort = self.GetObject(self.currentObj, remaining)
            
            if isinstance(toPort, Ports.Port):
                SpecPortFromPort((fromPort, toPort), self)
                
                
        return None            
            

    def Minus(self, lhsObj, remaining):
        """take the appropriate add action with respect to whatever lhsObj is"""
        if hasattr(lhsObj, 'Minus'):            
            if isinstance(lhsObj, ThermoCase):
                lhsObj.Minus(remaining)
                self.root.InfoMessage ('CMDNotifyDeleteCompound', (lhsObj.case, remaining))
            else:
                self.root.InfoMessage ('CMDNotifyBeforeMinus', (PathOf(lhsObj), remaining))
                lhsObj.Minus(remaining)
                self.root.InfoMessage ('CMDNotifyMinus', (PathOf(lhsObj), remaining))
                

    def CreateObject(self, parent, name, opTypeDesc):
        '''create an object of type opTypeDesc and add it to parent'''
        #handle hypo
        if isinstance(parent, ThermoCase):            
            if opTypeDesc[0:12] == 'HypoCompound':
                hypoProps = opTypeDesc[12:]
                if not hypoProps: 
                    return
                ret = parent.AddHypo(name, hypoProps, self.units)
                if ret != None:
                    self.root.InfoMessage ('CMDNotifyAddHypo', (parent.case, ret))
                return ret
            elif opTypeDesc[0:len('UpdateProperties')] == 'UpdateProperties':
                hypoProps = opTypeDesc[len('UpdateProperties'):]
                if not hypoProps: 
                    return
                ret = parent.EditCompound(name, hypoProps, self.units)
                if ret != None:
                    self.root.InfoMessage ('CMDNotifyEditHypo', (parent.case, ret))
                return ret
 
        #ThermoCase(provider, pkg)
        if opTypeDesc[:11] == 'ThermoCase(':
            params = re.sub('"', '', opTypeDesc[11:-1])
            params = re.sub("'", '', params)
            params = params.split(',')
            
            #Create and add
            if isinstance(parent, ThermoAdmin):
                thCaseObj = self.thermoAdmin.AddPkgFromName(params[0], name, params[1])
                self.root.InfoMessage ('CMDNotifyCreateThermo', (name, params[1]))
                return thCaseObj
            
            #Ensure a unique name create, add and add to unitop
            elif isinstance(parent, UnitOperations.UnitOperation):
                self.root.InfoMessage('CMDObsoleteCommand', (self.commandInProcess, '$thermoname = opTypeDesc'))
                #Make it a unique global name (at least try to)
                avThCases = self.thermoAdmin.GetAvThCaseNames(provider)
                if name in avThCases:
                    raise CmdError('CMDCouldNotAssign', opTypeDesc)
                    
                thCaseObj = self.thermoAdmin.AddPkgFromName(params[0], name, params[1])
                parent.AddObject(thCaseObj, name)
                self.root.InfoMessage ('CMDNotifyCreateThermo', (name, pkgName))
                return thCaseObj
                
            else:
               raise CmdError('CMDCouldNotAssign', opTypeDesc) 
                    
        #Obsolete way of creating thermo cases
        # is it a thermo provider
        if '.' in opTypeDesc and (isinstance(parent, UnitOperations.UnitOperation) or isinstance(parent, ThermoAdmin)):
            (provider, pkgName) = re.split(r'\.', opTypeDesc, 1)
            if self.thermoAdmin and provider in self.thermoAdmin.GetAvThermoProviderNames():
                #Make it a unique global name (at least try to)
                avThCases = self.thermoAdmin.GetAvThCaseNames(provider)
                if name in avThCases:
                    raise CmdError('CMDCouldNotAssign', opTypeDesc) 
                    
                thCaseObj = self.thermoAdmin.AddPkgFromName(provider, name, pkgName)
                if isinstance(parent, UnitOperations.UnitOperation):
                    self.root.InfoMessage('CMDObsoleteCommand', (self.commandInProcess, '$thermoname = opTypeDesc'))
                    parent.AddObject(thCaseObj, name)
                self.root.InfoMessage ('CMDNotifyCreateThermo', (name, pkgName))
                return thCaseObj
 
                
        # create object - hopefully
        # can't use eval for security reasons
        objDescParts = opTypeDesc.split('.',1)
        moduleName = objDescParts[0]
        modules = sys.modules.keys()
        m = None
        for p in self.createableModules:
            p2 = p + '.' + moduleName
            if p2 in modules:
                m = sys.modules[p2]
                break
        
        if not m:
            try:
                # see if we can just add string to parent
                parent.AddObject(opTypeDesc, name)
                return opTypeDesc
            except:
                raise CmdError('CMDCouldNotAssign', opTypeDesc)
        
        classNameParts = objDescParts[1].split('(',1)
        classObj = getattr(m, classNameParts[0])
        argString = classNameParts[1]
        if len(argString) and argString[-1] == ')':
            argString = argString[:-1]
        # argStrings = argString.split(',')
        #argStrings = re.findall('".*"|[^,]+', argString)

        #argStrings = []
        # first break out single quotes
        #for s in re.findall("'.*?'|[^,].*", argString):
            #if s[0] == "'":
                #argStrings.append(s)
            #else:
                ## now double quotes
                #for s2 in re.findall('".*?"|[^,].*', s):
                    #if s2[0] == '"':
                        #argStrings.append(s2)
                    #else:
                        ## unquoted - split on commas
                        #argStrings.extend(s2.split(','))
                                     
        #Tokenize here
        argStrings = Tokenize(argString, ",", 1)
        argStrings = map(string.strip, argStrings)
        
        
        args = []
        for s in argStrings:
            if s:
                if s[0] == '"' or s[0] == "'":
                    args.append(s[1:-1])
                else:
                    try:
                        args.append(int(s))
                    except:
                        try:
                            args.append(float(s))
                        except:
                            if s == 'None':
                                args.append(None)
                            else:
                                args.append(s)
            else:
                args.append("")
                
        newObj = apply(classObj, args)
        
        if hasattr(parent, 'AddObject'):
            parent.AddObject(newObj, name)
            self.root.InfoMessage ('CMDNotifyCreateObj', (PathOf(parent), name, opTypeDesc))
        else:
            raise CmdError('CMDInvalidObject', name)
        return newObj
        
    def Equal(self, lhsObj, rhsDesc, calcStatus=FIXED_V):
        """ add whatever is described by remaining to lhsObj"""
        rhsObj = None
        if rhsDesc:
            c = rhsDesc[0]
            if isinstance(lhsObj, CreateObject):
                parentObj = lhsObj.parent
                createName = lhsObj.description
                if not rhsDesc:
                    raise CmdError('CMDUnknownObject', lhsDesc)
                
                #See if a new property is being created in a material port
                if isinstance(parentObj, Ports.Port_Material):
                    if createName in PropTypes.keys():
                        #This should be enough to create the variable with no value
                        parentObj.SetPropValue(createName, None, UNKNOWN_V)
                        
                        #Change the lhsObj to be the newly created variable
                        lhsObj = parentObj.GetObject(createName)
                else:
                    # see if rhs already exists
    
                    #Check for the case of an obj created with the name of a module
                    if '.' in rhsDesc and '(' in rhsDesc:
                        try:
                            retObj = self.CreateObject(parentObj, createName, rhsDesc)
                            return
                        except:
                            pass
    
                    try:
                        if createName != 'NewName':
                            if c == '/':
                                rhsObj = self.GetObject(self.root, rhsDesc[1:])
                            elif c == TH_ADMIN_KEYWORD:
                                rhsObj = self.GetObject(self.thermoAdmin, rhsDesc[1:])
                            else:
                                try:
                                    #If the value is a number, then keep it as is
                                    #This is to avoid problems in the cases of objects being called as integers
                                    val = int(rhsDesc)
                                    rhsObj = CreateObject(self.currentObj, rhsDesc)
                                except:
                                    rhsObj = self.GetObject(self.currentObj, rhsDesc)
                        else:
                            #Do a bunch of validation for new names
                            if not rhsDesc or ' ' in rhsDesc or ';' in rhsDesc:
                                self.root.InfoMessage('CMDInvalidNameSyntax', (rhsDesc, ))
                                return
                            elif rhsDesc[0] == '/' or rhsDesc == '$':
                                self.root.InfoMessage('CMDInvalidNameSyntax', (rhsDesc, ))
                                return
                            elif rhsDesc in commands or rhsDesc in operators:
                                self.root.InfoMessage('CMDInvalidNameSyntax', (rhsDesc, ))
                                return
                            rhsObj = CreateObject(self.currentObj, rhsDesc)
                                
                        # if we found rhsObj - see if we can get its value and add it to parentObj
                        # lhsdesc stores the original command of the lhs.  Stores the original port name when moving tower feeds
                        lhsDesc = PathOf(lhsObj)
                        if rhsObj:
                            if isinstance(rhsObj, CreateObject):
                                parentObj.AddObject(rhsObj.description, createName)
                            else:
                                parentObj.AddObject(rhsObj, createName)
                            # mostly parameters
                            self.root.InfoMessage ('CMDNotifyAddObj', (PathOf(parentObj), createName, rhsDesc, lhsDesc))
                            return
                    except:
                        pass  # that didn't work - try creating object
                    if createName != 'NewName':
                        self.CreateObject(parentObj, createName, rhsDesc)
                    return

            elif isinstance(lhsObj, ThermoCase) and rhsDesc: 
                if lhsObj.name[:2] == '__':
                    return

                ##Get the obj where the ThermoCase is being set
                #(lhsDesc, remaining) = self.GetNextTerm( self.commandInProcess )
                
                ##Don't overwrite in the thermo admin
                #c = lhsDesc[0]
                #if c == TH_ADMIN_KEYWORD:
                    #raise CmdError('CMDCouldNotAssign', rhsDesc)
                
                ##Get the parent of the lhsThermoCase
                #parentDesc = string.join(lhsDesc.split('.')[:-1], '.')
                #if c == '/':
                    #parentObj = self.GetObject(self.root, parentDesc[1:])
                #else:
                    #parentObj = self.GetObject(self.currentObj, parentDesc)    
                
                ##See if the thcase comes from a thermocase
                #try:
                    #c = rhsDesc[0]
                    #if c == '/':
                        #rhsObj = self.GetObject(self.root, rhsDesc[1:])
                    #elif c == TH_ADMIN_KEYWORD:
                        #rhsObj = self.GetObject(self.thermoAdmin, rhsDesc[1:])
                    #else:
                        #rhsObj = self.GetObject(self.currentObj, rhsDesc)
                #except:
                    #rhsObj = None

                    
                #if isinstance(parentObj, UnitOperations.UnitOperation):
                    #createName = lhsObj.name        #If overwriting, then just use the same name
                    #parentObj.DeleteObject(lhsObj)
                    #if isinstance(rhsObj, ThermoCase):
                        #if createName != TH_CASE_KEYWORD:
                            #self.root.InfoMessage('CMDObsoleteWay', (createName, TH_CASE_KEYWORD))
                        #parentObj.AddObject(rhsObj, createName)
                        #self.root.InfoMessage ('CMDNotifyAddObj', (PathOf(parentObj), createName, rhsDesc, lhsDesc))
                    #else:
                        #self.CreateObject(parentObj, createName, rhsDesc)
                    
                #return

            # If i have a SetValues method, use it
            if hasattr(lhsObj, 'SetValues'):
                if rhsDesc != 'None':
                    vals = string.split(rhsDesc)
                    if hasattr(lhsObj,'GetType'):
                        unitType = lhsObj.GetType().unitType
                    else:
                        unitType = None
                    if unitType:
                        lastVal = vals[-1]
                        if not lastVal[0] in r'.-+0123456789' and lastVal != 'None':
                            units = self.units.UnitsByPartialName(lastVal, unitType)
                            if len(units) > 1:
                                # multiple partial match, get the item with exact match
                                uLast = string.upper(lastVal)
                                units = filter(lambda u: string.upper(u.name) == uLast, units)
                                if len(units) != 1:
                                    raise CmdError('CMDAmbiguousUnit', lastVal)
                            elif len(units) == 0:
                                raise CmdError('CMDUnknownUnit', lastVal)
                            unit = units[0]
                            vals = vals[:-1]
                        else:
                            unit = self.units.GetCurrentUnit(unitType)
    
                        for i in range(len(vals)):
                            if vals[i] != 'None':
                                vals[i] = unit.ConvertToSim42(float(vals[i]))
                else:
                    vals = None

                # Handling spec port composition from installed oil
                if isinstance(lhsObj, CompoundList) and vals and len(vals) == 1:
                    try:
                        tmp = float(vals[0])   # check if it is a numeric number
                    except:
                        if rhsDesc[0] == '/':
                            rhsObj = self.GetObject(self.root, rhsDesc[1:])
                        else:
                            rhsObj = self.GetObject(self.currentObj, rhsDesc)
                        if hasattr(rhsObj, 'GetFraction'):
                            vals = rhsObj.GetFraction()
                            lhsObj.SetValues(vals, calcStatus)
                            lhsObj.GetParent().AttachToObject(rhsObj)
                            self.root.InfoMessage ('CMDNotifySetValue', (PathOf(lhsObj), rhsDesc))
                            return

                lhsObj.SetValues(vals, calcStatus)
                self.root.InfoMessage ('CMDNotifySetValue', (PathOf(lhsObj), rhsDesc))
                return

            if isinstance(lhsObj, list):
                fracs = string.split(rhsDesc)
                if len(fracs) != len(lhsObj):
                    raise CmdError('CMDListSizeMismatch')
                
                for i in range(len(lhsObj)):
                    lhsObj[i].SetValue(float(fracs[i]), calcStatus)
                    self.root.InfoMessage ('CMDNotifySetValue', (PathOf(lhsObj[i]), str(fracs[i])))
                return                
            
            if c in r'.-+0123456789':
                try:
                    rhsParts = string.split(rhsDesc)
                    number = rhsParts[0]
                    if '.' in number or 'e' in number or 'E' in number:
                        rhsObj = float(number)
                    else:
                        rhsObj = int(number)

                    if len(rhsParts) > 1:
                        try:
                            unitType = lhsObj.GetType().unitType
                        except:
                            unitType = None
                            
                        units = self.units.UnitsByPartialName(rhsParts[1], unitType)
                        if len(units) > 1:
                            # multiple partial match, get the item with exact match
                            uLast = string.upper(rhsParts[1])
                            units = filter(lambda u: string.upper(u.name) == uLast, units)
                            if len(units) != 1:
                               raise CmdError('CMDAmbiguousUnit', rhsParts[1])
                        elif len(units) == 0:
                            raise CmdError('CMDUnknownUnit', rhsParts[1])
                        unit = units[0]
                    else:
                        if hasattr(lhsObj,'GetType'):
                            unit = self.units.GetCurrentUnit(lhsObj.GetType().unitType)
                        else:
                            unit = None
                    if unit:
                        rhsObj = unit.ConvertToSim42(rhsObj)

                    # if lhsObj does not have a SetValue method, an exception will
                    # be raised
                    lhsObj.SetValue(rhsObj, calcStatus)
                    self.root.InfoMessage ('CMDNotifySetValue', (PathOf(lhsObj), str(rhsObj)))
                    return
                except CmdError, e:
                    raise e
                except:
                    pass
                    
            try:
                if c == '/':
                    rhsObj = self.GetObject(self.root, rhsDesc[1:])
                elif c == TH_ADMIN_KEYWORD:
                    rhsObj = self.GetObject(self.thermoAdmin, rhsDesc[1:])
                else:
                    rhsObj = self.GetObject(self.currentObj, rhsDesc)

                # if we found rhsObj - see if we can get its value and assign it to lhsObj
                if rhsObj:
                    lhsObj.SetValue(rhsObj.GetValue(), calcStatus)
                    self.root.InfoMessage ('CMDNotifySetValue', (PathOf(lhsObj), str(rhsObj.GetValue())))
                    return
            except:
                pass  # that didn't work - try assigning string
            
            if rhsDesc == 'None':
                try:
                    lhsObj.SetValue(None, calcStatus)
                    self.root.InfoMessage ('CMDNotifySetValue', (PathOf(lhsObj), rhsDesc))
                    return
                except:
                    raise CmdError('CMDCouldNotAssign', rhsDesc)

            # could not find object - see if lhsObj will just accept string
            try:
                lhsObj.SetValue(rhsDesc, calcStatus)
                self.root.InfoMessage ('CMDNotifySetValue', (PathOf(lhsObj), rhsDesc))
            except SimError, e:
                raise e
            except:
                raise CmdError('CMDCouldNotAssign', rhsDesc)
            return

        # No rhs, so see if parent can delete lhsObj
        try:
            if isinstance(lhsObj, ThermoCase) and self.commandInProcess[0] == TH_ADMIN_KEYWORD:
                parent = lhsObj.thermoAdmin
            else:
                parent = lhsObj.GetParent()
                name = lhsObj.GetName()
            if parent:
                if isinstance(parent, Ports.Port) and isinstance(lhsObj, BasicProperty):
                    isVariable = 1
                else:                
                    isVariable = 0
                    self.root.InfoMessage ('CMDNotifyBeforeDeleteObj', (PathOf(parent), PathOf(lhsObj)))
                lhsPath = PathOf(lhsObj)
                parent.DeleteObject(lhsObj)
                if (isVariable):
                    self.root.InfoMessage ('CMDNotifySetValue', (PathOf(lhsObj), None))
                else:
                    self.root.InfoMessage ('CMDNotifyDeleteObj', (PathOf(parent), lhsPath))
        except:
            raise CmdError('CMDCanNotDelete')
        
    def Estimate(self, lhsObj, rhsDesc):
        self.Equal(lhsObj, rhsDesc, calcStatus=FIXED_V|ESTIMATED_V)
    def Calculate(self, lhsObj, rhsDesc):
        self.Equal(lhsObj, rhsDesc, calcStatus=CALCULATED_V)

    def Connect(self, lhsObj, rhsDesc):
        """connect the port lhsObj to the port described by rhsDesc"""

        #ThermoCases
        if isinstance(lhsObj, UnitOperations.UnitOperation) or isinstance(lhsObj, ThermoCase):
    
            if rhsDesc:
                try:
                    if rhsDesc[0] == '/':
                        rhsObj = self.GetObject(self.root, rhsDesc[1:])
                    elif rhsDesc[0] == TH_ADMIN_KEYWORD:
                        rhsObj = self.GetObject(self.thermoAdmin, rhsDesc[1:])
                    else:
                        rhsObj = self.GetObject(self.currentObj, rhsDesc)
                except:
                    raise CmdError('CMDCannotConnectTo', rhsDesc)
                
                if isinstance(lhsObj, UnitOperations.UnitOperation):
                    if not isinstance(rhsObj, ThermoCase):
                        raise CmdError('CMDCannotConnectTo', rhsDesc)
                    #if lhsObj.thCaseObj:
                        #lhsObj.DeleteObject(lhsObj.thCaseObj)
                    lhsObj.SetThermo(rhsObj)
                    self.root.InfoMessage('CMDThermoConnected', (lhsObj.GetPath(), rhsObj.GetPath()))
                elif isinstance(lhsObj, ThermoCase):
                    if not isinstance(rhsObj, UnitOperations.UnitOperation):
                        raise CmdError('CMDCannotConnectTo', rhsDesc)
                    #if rhsObj.thCaseObj:
                        #rhsObj.DeleteObject(rhsObj.thCaseObj)
                    rhsObj.SetThermo(lhsObj)
                    self.root.InfoMessage('CMDThermoConnected', (lhsObj.GetPath(), rhsObj.GetPath()))
                else:
                    raise CmdError('CMDCannotConnectTo', rhsDesc)
            else:
                rhsObj = None
                if isinstance(lhsObj, UnitOperations.UnitOperation):
                    if lhsObj.thCaseObj:
                        name = lhsObj.thCaseObj.GetPath()
                        lhsObj.DeleteObject(lhsObj.thCaseObj)
                        self.root.InfoMessage('CMDThermoDisconnected', (lhsObj.GetPath(), name))
                    
            return
            
                
        elif not isinstance(lhsObj, Ports.Port):
            raise CmdError('CMDConnectNonPort', lhsObj.GetPath())

        if rhsDesc:
            try:
                if rhsDesc[0] == '/':
                    rhsObj = self.GetObject(self.root, rhsDesc[1:])
                else:
                    rhsObj = self.GetObject(self.currentObj, rhsDesc)
            except:
                raise CmdError('CMDCannotConnectTo', rhsDesc)
        else:
            rhsObj = None
            
        if type(rhsObj) == type(()):
            raise CmdError('CMDCannotConnectTo', rhsDesc)
        
        if rhsObj == None:
            connObj = lhsObj._connection
            self.root.InfoMessage ('CMDNotifyBeforeDisconnect', (PathOf(lhsObj), PathOf(connObj)))
            
            lhsObj.Disconnect()
            self.root.InfoMessage ('CMDNotifyDisconnect', (PathOf(lhsObj), PathOf(connObj)))

        else:
            if type(rhsObj) != type(lhsObj):
                raise CmdError('CMDConnectTypeMismatch', rhsDesc)
            lhsObj.ConnectTo(rhsObj)
            self.root.InfoMessage ('CMDNotifyConnect', (PathOf(lhsObj), PathOf(rhsObj)))

    def Alias(self, lhsObj, rhsDesc):
        """
        create alias for lhsObj using name rhsDesc
        for now this means that the lhsObj must be a port and the
        rhsDesc is a path to a parent 'borrowed' port
        """
        if not isinstance(lhsObj, Ports.Port):
            raise CmdError('CMDAliasNotPort', lhsObj.GetPath())
        
        lastDot = string.rfind(rhsDesc, '.')
        if lastDot == -1:
            parentObj = self.currentObj
            name = rhsDesc
        else:
            try:
                if rhsDesc[0] == '/':
                    parentObj = self.GetObject(self.root, rhsDesc[:lastDot])
                else:
                    parentObj = self.GetObject(self.currentObj, rhsDesc[:lastDot])
            except:
                raise CmdError('CMDUnknownObject', rhsDesc[:lastDot])
            name = rhsDesc[lastDot+1:]
        
        if not isinstance(parentObj, UnitOperations.UnitOperation):
            raise CmdError('CMDAliasNotForUO', parentObj.GetPath())
        
        parentObj.BorrowChildPort(lhsObj, name)
        
    def GetObject(self, startObj, objDesc):
        """
        return the object described by objDesc relative to the startObj
        if the object does not exist return a CreateObject object
        """
        if len(objDesc) == 0: return startObj

        c = objDesc[0]   # child type designator
        if c == '.':
            if len(objDesc) == 1:
                return startObj
            elif objDesc[1] == '.':
                if hasattr(startObj, 'GetParent'):
                    startObj = startObj.GetParent()
                else:
                    return None
                if len(objDesc) == 2:
                    return startObj
                objDesc = objDesc[2:]
            else:
                # see if it might be a number
                try:
                    f = float(objDesc)
                    # made it, so return a CreateObject
                    return CreateObject(startObj, objDesc)
                except ValueError:
                    # assume redundant current object dor
                    objDesc = objDesc[1:]
                
        #split off first name from description
        parts = re.split(r'\.', objDesc, 1)
        if len(parts[0]) == 0:
            return startObj  # if just dot return current

        if len(parts) > 1:
            (name, remaining) = parts
        else:
            (name, remaining) = (parts[0], '')
        
        if hasattr(startObj, 'GetObject'):
            obj = startObj.GetObject(name)
        elif isinstance(startObj, Numeric.ArrayType) and name == 'T':
            obj = Numeric.transpose(startObj)
        else: # see if it is some sort of list
            try:
                obj = startObj[int(name)]
            except:
                try:
                    obj = startObj[name]
                except:
                    obj = None
            
        if not obj is None:
           if remaining:
               return self.GetObject(obj, remaining)
           else:
               return obj
        else:
            if remaining:
                raise CmdError('CMDNoSuchName', remaining)
            # if obj does not exist return parent and name of object in tuple
            return CreateObject(startObj, name)

    def Delete(self, objDesc):
        """
        ask the parent of object described by objDesc to delete it
        """
        c = objDesc[0]
        if c == '/':
            obj = self.GetObject(self.root, objDesc[1:])
        elif c == TH_ADMIN_KEYWORD:
            obj = self.GetObject(self.thermoAdmin, objDesc[1:])
        else:
            obj = self.GetObject(self.currentObj, objDesc)
            
        if isinstance(obj, ThermoCase) and c == TH_ADMIN_KEYWORD:
            parent = self.thermoAdmin
        elif hasattr(obj, 'GetParent'):
            parent = obj.GetParent()
        else:
            parentDesc = string.join(objDesc.split('.')[:-1], '.')
            if c == '/':
                parent = self.GetObject(self.root, parentDesc[1:])
            elif c == TH_ADMIN_KEYWORD:
                parent = self.GetObject(self.thermoAdmin, parentDesc[1:])
            else:
                parent = self.GetObject(self.currentObj, parentDesc)
                
        if parent:
            self.root.InfoMessage ('CMDNotifyBeforeDeleteObj', (PathOf(parent), PathOf(obj)))
            objPath = PathOf(obj)
            parent.DeleteObject(obj)
            self.root.InfoMessage ('CMDNotifyDeleteObj', (PathOf(parent), objPath))

    def RenderEnvelopeResult(self, obj):
        unitType = self.units.GetTypeID('Pressure')
        unitP = self.units.GetCurrentUnit(unitType)
        unitType = self.units.GetTypeID('Temperature')
        unitT = self.units.GetCurrentUnit(unitType)
        unitType = self.units.GetTypeID('MolarEnthalpy')
        unitH = self.units.GetCurrentUnit(unitType)
        
        result = obj.type + ': ' + obj.returnMessage
        result += '\nTotal %s points: pointType, P %s, T %s' % (obj.pointCount, unitP.name, unitT.name)
        if obj.type == 'TH': result += ', H %s' % (unitH.name)
        for i in range(obj.pointCount):
            p = unitP.ConvertFromSim42(obj.pValues[i])
            t = unitT.ConvertFromSim42(obj.tValues[i])
            result += ('\n Point %d: ' %i) + ('\t %d ' % obj.pointTypes[i]) + '\t '
            result += str(p) + '\t ' + str(t)
            if obj.type == 'TH':
                h = unitH.ConvertFromSim42(obj.kValues[i])
                result += '\t ' + str(h)
        return result
        

    def RenderBasicObject(self, obj):
        """produce representation of obj with units"""
        v = obj.GetValue()
        if v == None: return 'None'

        unit = self.units.GetCurrentUnit(obj.GetType().unitType)
        if unit: v = unit.ConvertFromSim42(v)
        result = str(v)

        status = obj.GetCalcStatus()
        if status & ESTIMATED_V: result += ' ~ '
        elif status & FIXED_V: result += ' * '
        elif status & PASSED_V: result += ' | '
        elif status & ESTIMATED_V: result += ' ~ '
        elif status & CALCULATED_V: result += ' = '
        else: result += ' \t'
        
        if unit:  result += unit.name

        #if status & NEW_V:
            #result += ' New'
            
        return result
        
    def RenderObject(self, obj):
        """produce an appropriate string for obj"""
        if type(obj) == type([]) or type(obj) == type(()):
            result = '[ ...\n'
            for i in obj:
                result += self.RenderObject(i)
                if result[-1] != ']n': result += '\n'
            result += ' ... ]\n'
        elif isinstance(obj, BasicProperty):
            result = obj.GetPath() + '= ' + self.RenderBasicObject(obj)

        elif isinstance(obj, PureCompoundProperty):
            result = obj.GetPath() + '= ' + str(obj.GetValue())
            
        elif isinstance(obj, EnvelopeResults):
            result = self.RenderEnvelopeResult(obj)
            
        elif isinstance(obj, BasicArrayProperty):
            result = "Profile: %s\n" % obj.GetName()
            vals = self.ConvertArrayToCurrentUnits(obj)
            result += str(vals)
            
#        elif isinstance(obj, UnitOperations.OpParameter):
#            result = obj.GetPath() + '= ' + str(obj.GetValue())
        elif isinstance(obj, Ports.Port):
            result = 'Port: ' + obj.GetPath() + ' + ' + str(obj)

            result += '\nConnected to: '
            conn = obj.GetConnection()
            if conn: result += conn.GetPath() + '\n'
            else: result += 'None\n'

            if isinstance(obj, Ports.Port_Material):
                props = self.defaultPropertyOrder
            else:
                props = obj.GetPropNames()
                props.sort()

            # figure out longest name
            maxLength = 0
            for propName in props: maxLength = max(maxLength, len(propName))
            if isinstance(obj, Ports.Port_Signal):
                cmpName = ""
                if hasattr(obj, '_cmpName'):
                    if obj._cmpName:
                        cmpName = obj._cmpName
                        maxLength += len(cmpName)+1
                for propName in props:
                    try:
                        prop = obj.GetProperty(propName)
                        if cmpName:
                            dispName = '%s_%s' %(propName, cmpName)
                        else:
                            dispName = propName
                        result += dispName + ' ' * (maxLength - len(dispName) + 3) \
                               + '= ' + self.RenderBasicObject(prop) + '\n'
                    except:
                        result += propName + ' is invalid\n'
                           
            else:
                for propName in props:
                    try:
                        prop = obj.GetProperty(propName)
                        result += propName + ' ' * (maxLength - len(propName) + 3) \
                               + '= ' + self.RenderBasicObject(prop) + '\n'
                    except:
                        result += propName + ' is invalid\n'

            if isinstance(obj, Ports.Port_Material):
                result += self.RenderComposition(obj.GetCompounds(), maxLength)

        elif isinstance(obj, CompoundList):
            result = self.RenderComposition(obj)
            
        elif isinstance(obj, UnitOperations.UnitOperation):
            result = 'Operation: ' + str(obj)
            if obj.__dict__.has_key('thCaseObj'):
                if obj.thCaseObj:
                    result += '\nThermo: ' + obj.thCaseObj.package
                
            for name, port in obj.GetPortItems():
                result += '\nPort: ' + name
                result += ' = ' + str(port)
                if port.GetName() != name:
                    result += ' (' + port.GetPath() + ')'

            children = [str(c[1]) for c in obj.GetChildUnitOps()]
            children.sort()
            for child in children:
                result += '\nChild: ' + child

            params = obj.GetParameters()
            for p in params.keys():
                myType = obj.GetParameterProperty(p)
                value = params[p]
                unitName = ''
                if myType and value != None:
                    unit = self.units.GetCurrentUnit(myType.unitType)
                    if unit:
                        unitName = unit.name
                        value = unit.ConvertFromSim42(value)
                if unitName:
                    result += '\nParameter: ' + p + ' = %g %s' % (value, unitName)
                else:
                    result += '\nParameter: ' + p + ' = ' + str(value)

            if isinstance(obj, Envelope.PTEnvelope):
                result += '\nDataSeries: ' + str(obj.pSet)
                for key in obj.QualityLines.keys():
                    result += '\nQualityCurve: ' + key
                if obj.thEnvelope:
                    result += '\nTH Envelope: ' + str(obj.thEnvelope.name)
                    for key in obj.thEnvelope.QualityLines.keys():
                        result += '\n   Isobars: ' + key
                if obj.phEnvelope:
                    result += '\nPH Envelope: ' + str(obj.phEnvelope.name)
                    for key in obj.phEnvelope.QualityLines.keys():
                        result += '\n   Isotherms: ' + key

            for designObj in obj.GetDesignObjects():
                result += '\nDesign: ' + str(designObj)

        elif isinstance(obj, ThermoCase):
            result = 'Name: ' + obj.case + '\nPropPkg: ' + obj.provider + '.' +obj.package + '\nUsing:'
            for name in obj.thermoAdmin.GetSelectedCompoundNames(obj.provider, obj.case):
                result += '\n' + name

        elif isinstance(obj, ThermoAdmin):
            providers = obj.GetAvThermoProviderNames() 
            providers = string.join(providers, ', ')
            result = 'Providers: %s' %providers
            for thName, thCase in obj.GetContents():
                result += '\nThermoCase: %s; PropPkg - %s.%s' %(thName, thCase.provider, thCase.package)
                
        elif isinstance(obj, CreateObject):
            parent = obj.parent
            description = obj.description
            if isinstance(parent, ThermoCase):
                result = self.RenderCompound(parent, description)
            else:            
                result = 'None'
        elif isinstance(obj, UnitOperations.OpParameter):
            myType = obj.GetType()
            value = obj.GetValue()
            unitName = ''
            if myType and value != None:
                unit = self.units.GetCurrentUnit(myType.unitType)
                if unit:
                    unitName = unit.name
                    value = unit.ConvertFromSim42(value)
            return '%s = %s %s' % (obj.GetPath(), str(value), unitName)
        else:
            result = str(obj)
        return result
        
    def RenderComposition(self, cmps, charOffset=25):
        """
        returns character rendering of composition of cmps which should
        be a CompoundList. charOffset is the minimum character position for
        the value
        """
        result = ''
        cmpNames = cmps.GetParent().GetParent().GetCompoundNames()
        for i in range(len(cmps)):
            cmp = cmpNames[i]
            result += cmp
            pad = max(charOffset - len(cmp) + 3, 1)
            result += ' ' * pad + '= ' \
                   + self.RenderBasicObject(cmps[i]) + '\n'

        return result
 

    def Hold(self, remaining): self.root.hold = 1
    
    def Go(self, remaining):
        self.root.hold = 0
        self.root.Solve()
        
    def ValueOf(self, rawCmd):
        """
        Method to get the Value of a variable or an object
        command format is 'object.keyword'.  If keyword =
           'key':          returns the keys if object is a collection
           'processvalue': returns the process value if object
                           is a basicVariable or parameter
           'path':         returns the path of the object
        """
        result = None
        try:
            cmd = re.sub('#.*', '', rawCmd)  # remove comments
            cmd = string.strip(cmd)
            pos = cmd.rfind('.')
            if (pos <= 0):
                obj = self.currentObj
                last = cmd
            else:            
                # extract the last token
                first = cmd[0:pos]
                last = cmd[pos+1:]
                c = first[0]
                if c == '/':
                    obj = self.GetObject(self.root, first[1:])
                elif c == TH_ADMIN_KEYWORD:
                    obj = self.GetObject(self.thermoAdmin, first[1:])
                else:
                    obj = self.GetObject(self.currentObj, first)
                if isinstance(obj, CreateObject):
                    parent = obj.parent
                    description = obj.description

                    # compound properties
                    # expecting command valueOf thermo.methane.values
                    #                           thermo.methane.keys
                    #                           thermo.methane.unitTypes
                    #                           thermo.methane.CriticalPressure
                    if isinstance(parent, ThermoCase):
                        return self.CompoundValues(parent, description, last)                        
                    
                    if parent.__dict__.has_key(description):
                        obj = parent.__dict__[description]
                    elif parent.__dict__.has_key('_' + description):
                        obj = parent.__dict__['_' + description]
                if not obj: return None

            # return specified values
            if last == "key" :
                if (isinstance(obj, dict) or type(obj) == type({})):
                    result = obj.keys()
                    result.sort()
            elif last == "path":
                if isinstance(obj, Ports.Port):
                    portParent = obj.GetParent()
                    if portParent:
                        result = portParent.ShortestPortPath(obj)
                    else:
                        result = ''
                elif hasattr(obj, 'GetPath'): result = obj.GetPath()
            elif last == "type":
                result = str(obj)
            elif last == "compoundNames":
                if isinstance(obj, Ports.Port):
                    result = obj.GetParent().GetCompoundNames()
                elif isinstance(obj, UnitOperations.UnitOperation):
                    result = obj.GetCompoundNames()
                else:
                   result = ''
            elif last ==  "processValue" or last == "convertedValue":
                #use the get value method (for BasicProperty and Parameter)
                if isinstance(obj, CompoundList):
                    result = []
                    for cmp in obj:
                       result.append(cmp.GetValue())                    
                elif hasattr(obj, 'GetValue'):    
                    result = obj.GetValue()
                    if (last == "convertedValue"):
                        unit = self.units.GetCurrentUnit(obj.GetType().unitType)
                        if unit: result = unit.ConvertFromSim42(result)
                elif hasattr(obj, 'GetValues'):    
                    result = obj.GetValues()
                else:
                    try: result = float(obj)
                    except: pass
            elif last ==  "convertedValues":
                #use the get values method
                if isinstance(obj, BasicArrayProperty):
                    result = self.ConvertArrayToCurrentUnits(obj)
                elif hasattr(obj, 'GetValues'):
                    result = obj.GetValues()
                    unit = self.units.GetCurrentUnit(obj.GetType().unitType)
                    if unit:
                        result = map(lambda x: unit.ConvertFromSim42(x), result)
 
            elif last == 'profile':
                if isinstance(obj, CreateObject):
                    result = None
                elif isinstance(obj, BasicArrayProperty):
                    result = obj.GetValue()
                else:
                    result = obj
            elif last == 'convertedProfile':
                if isinstance(obj, CreateObject):
                    result = None
                elif isinstance(obj, BasicArrayProperty):
                    result = self.ConvertArrayToCurrentUnits(obj)
                else:
                    if hasattr(obj, 'ConvertToCurrentSet'):
                        #Convert myself to a set of unit
                        #Ugly hack and should be done differently at some point
                        obj.ConvertToCurrentSet(self.units)
                    
                    result = obj
                    
            elif last == 'arrayRep':
                if hasattr(obj, 'GetArrayRepresentation'):
                    result = obj.GetArrayRepresentation()
            
            elif last == 'convertedArrayRep':
                if hasattr(obj, 'GetConvertedArrayRepresentation'):
                    result = obj.GetConvertedArrayRepresentation(self.units)
                    
            else:
                if obj.__dict__.has_key(last):
                    result = obj.__dict__[last]
                elif obj.__dict__.has_key('_' + last):
                    result = obj.__dict__['_' + last]
                elif obj.__dict__.has_key("_type"):   #handling of basic object
                    if obj._type.__dict__.has_key(last):
                        result = obj._type.__dict__[last]
                elif hasattr(obj, last):
                    result = getattr(obj, last)()
                elif isinstance(obj, dict):
                    if obj.has_key(last):
                        result = obj[last]
                if isinstance(result, UnitOperations.UnitOperation):
                    result = str(result)
        except:
            pass
        return result

    def CreatePort(self, remaining):
        """
        Method allowing extension unit op's to create ports
        """
        (portType, portDesc) = self.GetNextTerm(remaining)
        pos = portDesc.rfind('.')
        if (pos < 0):
            #handling createPort sig portName
            obj = self.currentObj
            portName = portDesc
        elif (pos == 0):
            #handling createPort sig .portName
            obj = self.currentObj
            portName = portDesc[1:]
        else:
            #handling createPort sig obj.portName            
            portName = portDesc[pos+1:]
            objDesc = portDesc[0:pos]
            c = objDesc[0]
            if c == '/':
                obj = self.GetObject(self.root, objDesc[1:])
            else:
                obj = self.GetObject(self.currentObj, objDesc)
            if type(obj) == type(()) and len(obj) > 0:
                obj = obj[0]
        if (obj == None):
            return
        elif isinstance(obj, UnitOperations.UnitOperation):
            portType = string.upper(portType)
            if (portType == 'MATERIALIN'):
                portTypeID = MAT|IN
            elif (portType == 'MATERIALOUT'):
                portTypeID = MAT|OUT
            elif (portType == 'ENERGYIN'):
                portTypeID = ENE|IN
            elif (portType == 'ENERGYOUT'):
                portTypeID = ENE|OUT
            else:
                portTypeID = SIG
            #should probably check whether the obj allows extra ports
            obj.CreatePort(portTypeID, portName)
            obj.PushSolveOp(obj)

    def CompoundValues(self, thCase, cmpName, type):
        cmps = self.thermoAdmin.GetSelectedCompoundNames(thCase.provider, thCase.case)
        if type == 'values':
            if cmpName == '' or not cmpName in cmps:
                return None
            idx = cmps.index(cmpName)
            thKeys = GetSimHypoStrings()
            thKeys.extend(GetSimHypoLongs())
            thKeys.extend(GetSimHypoDoubles())
            vals = []
            for i in thKeys:
                try:
                    thProp = [i]
                    thVal = self.thermoAdmin.GetSelectedCompoundProperties(thCase.provider, thCase.case, idx, thProp)
                    vals.append(thVal[0])
                except:
                    vals.append(None)
            return vals
        elif type == 'keys':
            # returns the string property names followed by the double property names
            thKey = GetSimHypoStrings()
            thKey.extend(GetSimHypoLongs())
            thKey.extend(GetSimHypoDoubles())
            return thKey
        elif type == 'units':
            unitTypeIds = []
            strs = GetSimHypoStrings()            
            # flag no units for the string properties
            for i in range(len(strs)):
                unitTypeIds.append(-1)
            lngs = GetSimHypoLongs()
            for i in range(len(lngs)):
                unitTypeIds.append(-1)
            #get the units for the double properties
            unitTypes = GetSimHypoDoubleUnitTypes()
            for i in unitTypes:
                try:
                    if i != '':
                        unitTypeIds.append(self.units.GetTypeID(i))
                    else:
                        unitTypeIds.append(-1)
                except:
                    unitTypeIds.append(-1)
            return unitTypeIds
        else:
            # single compound property
            if cmpName == '' or not cmpName in cmps:
                return None
            try:
                idx = cmps.index(cmpName)
                thProp = str(type)
                thVal = self.thermoAdmin.GetSelectedCompoundProperties(thCase.provider, thCase.case, idx, thProp)[0]
            except:
                thVal = None
            return thVal
            
        
    def RenderCompound(self, thCase, cmpName):
        result = ''
        vals = self.CompoundValues(thCase, cmpName, 'values')
        keys = self.CompoundValues(thCase, cmpName, 'keys')
        unitIds = self.CompoundValues(thCase, cmpName, 'units')
        if vals == None or keys == None or unitIds == None:
            return ''
        for i in keys:
            idx = keys.index(i)
            if vals[idx] and str(vals[idx]) != '':
                result += '\n ' + i + ' \t= ' + str(vals[idx])
                if unitIds[idx] >= 0:
                    unit = self.units.GetSim42Unit(unitIds[idx])
                    result += ' ' + unit.name
        return result        
            
    def SetInfoCallBack(self, obj):
        """Sets the info call back obj"""
        old = self.infoCallBack
        self.infoCallBack = obj
        self.root.SetInfoCallBack(obj)
        return old

    def ListFiles(self, objDesc):
        """
        list files in objDesc or the current directory if objDesc is empty
        """
        if not objDesc:
            objDesc = '.'
        if netServer:
            files = netServer.listdir(self.root, objDesc)
        else:
            files = os.listdir(objDesc)

        result = ''
        files.sort()
        for file in files:
            if objDesc != '.':
                file = objDesc + os.sep + file
            result += file
            try:
                path = os.path.abspath(file)
                size = os.path.getsize(path)
                date = os.path.getmtime(path)
                result += '\t%d\t%s' %(size, time.ctime(date))
                if os.path.isdir(path):
                    result += '\t<Dir>'
            except:
                pass
            result += '\n'
        return result

    def MakeDirectory(self, name):
        """
        create the directory name
        """
        if netServer:
            try:
                return netServer.mkdir(self.root, name)
            except:
                return None
        else:
            try:
                return os.mkdir(name)
            except:
                return None

    def DeleteFile(self, name):
        """
        delete file name
        """
        if netServer:
            return netServer.remove(self.root, name)
        else:
            return os.remove(name)

    def DeleteDirectory(self, name):
        """
        delete the file directory name
        """
        if netServer:
            return netServer.rmdir(self.root, name)
        else:
            return os.rmdir(name)

    def Tree(self, objDesc, level=1):
        try:
            # decode the level, objDesc format
            # syntax: objName [, level = levelValue]
            #    e.g. tree mixer; or tree mixer, level = 0
            terms = re.split(',', objDesc, 1)
            if len(terms) > 1:
                objDesc = terms[0]
                level = int(re.sub('level.*=', '', terms[1]))
        except:
            pass
            
        if not objDesc:
            obj = self.currentObj
        else:
            c = objDesc[0]
            if c == '/':
                obj = self.GetObject(self.root, objDesc[1:])
            elif c == TH_ADMIN_KEYWORD:
                obj = self.GetObject(self.thermoAdmin, objDesc[1:])
            else:
                obj = self.GetObject(self.currentObj, objDesc)
            if not obj or type(obj) == type(()):
                raise CmdError('CMDInvalidContentsObject', objDesc)
        return self.ObjData(obj, level)
        
    def ObjData(self, obj, specLevel):
        result = []
        if obj == None:
            return result
        level = specLevel - 1
        if hasattr(obj, 'GetContents'):
            for i in obj.GetContents():
                typeI1 = type(i[1])
                if typeI1 == type(None):
                    # no data, return None
                    result.append ((str(i[0]), None))
                elif (typeI1 == types.IntType or typeI1 == types.LongType or typeI1 == types.FloatType or typeI1 == types.StringTypes or typeI1 == types.ListType):
                    # for primary types, return as is
                    result.append ((str(i[0]), i[1]))
                else:
                    # likely an object
                    done = 0
                    t = re.sub(' .*', '', repr(i[1]))[1:]
                    if level != 0:
                        # recursive to get the object contents                        
                        data = self.ObjData(i[1], level)
                        if len(data) > 0:
                            # write a class instance indicator '<class>'
                            data.insert(0, ('<Class>', str(i[1])))
                            result.append ((str(i[0]), data))
                            done = 1
                    if not done:
                        # at the tip or last requested level, return the object description.
                        result.append ((str(i[0]), str(i[1])))
        return result

    def UpdatePropertyType(self, remaining):
        #Tokenize
        tokens = remaining.split(' ')
        nuTokens = len(tokens)
        if not nuTokens:
            return
        
        #The first token should have the format T.Min
        objDesc = tokens[0]
        tempLst = objDesc.split('.')
        propType = PropTypes.get(tempLst[0], None)
        if not propType:
            return
        
        #Just render
        if nuTokens == 1:
            if len(tempLst) == 1:
                return str(propType)
            
            unitType = propType.unitType
            typeName = None
            if unitType: typeName = self.units.GetTypeName(unitType)
            #If getting scale and using T, then use deltaT
            if len(tempLst) > 1:
                if tempLst[1] == 'Scale' and typeName:
                    if typeName == 'Temperature':
                        unitType = self.units.GetTypeID('DeltaT')
                    elif typeName == 'Pressure':
                        unitType = self.units.GetTypeID('DeltaP')
            unit = self.units.GetCurrentUnit(unitType)
            
            if tempLst[1] == 'Min':
                val = propType.minValue
                if unit and val != None:
                    val = unit.ConvertFromSim42(val)
                    return str(val) + ' ' + unit.name
                return str(val)
            elif tempLst[1] == 'Max':
                val = propType.maxValue
                if unit and val != None:
                    val = unit.ConvertFromSim42(val)
                    return str(val) + ' ' + unit.name
                return str(val)
            elif tempLst[1] == 'Scale':
                val = propType.scaleFactor
                if unit and val != None:
                    val = unit.ConvertFromSim42(val)
                    return str(val) + ' ' + unit.name
                return str(val)
            
        #Set the value
        elif nuTokens > 2 and tokens[1] == '=':
            try:
                val = float(tokens[2])
            except:
                return
            
            unitType = propType.unitType
            typeName = None
            if unitType: typeName = self.units.GetTypeName(unitType)
            #If setting scale and using T, then use deltaT
            if len(tempLst) > 1:
                if tempLst[1] == 'Scale' and typeName:
                    if typeName == 'Temperature':
                        unitType = self.units.GetTypeID('DeltaT')
                    elif typeName == 'Pressure':
                        unitType = self.units.GetTypeID('DeltaP')
            if nuTokens > 3:
                unitName = tokens[3]
                units = self.units.UnitsByPartialName(unitName, unitType)
                if len(units) > 1:
                    # multiple partial match, get the item with exact match
                    uLast = string.upper(unitName)
                    units = filter(lambda u: string.upper(u.name) == uLast, units)
                    if len(units) != 1:
                        raise CmdError('CMDAmbiguousUnit', unitName)
                elif len(units) == 0:
                    raise CmdError('CMDUnknownUnit', unitName)
                unit = units[0]
                val = unit.ConvertToSim42(val)
                            
            else:
                unit = self.units.GetCurrentUnit(unitType)
                if unit: val = unit.ConvertToSim42(val)
                
            if len(tempLst) > 1:
                if tempLst[1] == 'Min':
                    propType.minValue = val
                elif tempLst[1] == 'Max':
                    propType.maxValue = val
                elif tempLst[1] == 'Scale':
                    propType.scaleFactor = val
            return
        
        
        
        
    def OptimizeCode(self, optimize):
        try:
            optimize = int(optimize)
        except:
            optimize = 0
            
        SetUpCodeOptimization(optimize)
        
# constants

    def ConvertArrayToCurrentUnits(self, obj):
        if not isinstance(obj, BasicArrayProperty):
            return obj
        else:
            vals = obj.GetValue()
            rank = obj.GetRank()
            types = obj.GetType()
            
            #scalar
            if not rank:
                unit = self.units.GetCurrentUnit(types[0].unitType)
                if unit: vals = unit.ConvertFromSim42(vals)
                return vals
                
            #vector
            if rank == 1:
                unit = self.units.GetCurrentUnit(types[0].unitType)
                if unit:
                    vals = map(lambda val: unit.ConvertFromSim42(val), vals)
                return vals
            
            #array
            if rank == 2:
                myShape = obj.GetShape()
                if len(types) == 1:
                    unit = self.units.GetCurrentUnit(types[0].unitType)
                    if unit:
                        for r in range(myShape[0]):
                            for c in range(myShape[1]):
                                vals[r, c] = unit.ConvertFromSim42(vals[r, c])
                else:
                    for r in range(myShape[0]):
                        unit = self.units.GetCurrentUnit(types[r].unitType)
                        if unit:
                            for c in range(myShape[1]):
                                vals[r, c] = unit.ConvertFromSim42(vals[r, c])
                return vals
                
         
    def About(self, objDesc):
        """Displays (if available) any relevant information about the object, 
        for example version or build number"""
        if not objDesc:
            obj = self.currentObj
        else:
            c = objDesc[0]
            if c == '/':
                obj = self.GetObject(self.root, objDesc[1:])
            elif c == TH_ADMIN_KEYWORD:
                obj = self.GetObject(self.thermoAdmin, objDesc[1:])
            else:
                obj = self.GetObject(self.currentObj, objDesc)
            if not obj or type(obj) == type(()):
                return
        result = ''
        
        #Perhaps it should use a fixed method which could be overloaded by any object
        #but just hard code for now
        if isinstance(obj, UnitOperations.UnitOperation):
            result = 'Version = %s' %str(Flowsheet.VERSION)
                
        elif isinstance(obj, ThermoAdmin):
            providers = obj.GetAvThermoProviderNames() 
            for providerName in providers:
                result += '\nProvider %s:' %providerName
                (retCode, providerInfo) = obj.CustomCommand(providerName, None, 'Pkg.Info')
                # assuming the info is of the format 'a=x; b=y; c=ww; etc.'
                info = string.split(providerInfo, ';')
                for i in info:
                    result += '\n   %s' %i
        else:
            result = '---'
            
        return result
    
    def CanClone(self, op):
        """Validate if a unit op can be cloned"""
        if isinstance(op, UnitOperations.UnitOperation): return True
        return False
        
    def Copy(self, remaining, deleteAfter=0):
        remaining = remaining.strip()
        tokens = remaining.split()
        self.clipboard.Clear()
        #try:
        toClone = []
        toCloneFull = []
        clonesFull = []
        tag = []
        
        #Clone each unit op
        for token in tokens:
            if token[0] == '/':
                obj = self.GetObject(self.root, token[1:])
            else:
                obj = self.GetObject(self.currentObj, token)
            if self.CanClone(obj):
                try:
                    clone = obj.Clone()
                except:
                    clone = None
                if clone != None:
                    self.clipboard.AppendItem((clone, obj.GetName()))
                    tag.append(obj.GetPath())
                    
                    toClone.append(obj)
                        
                    #Traverse children and put them in a list
                    temp0 = [obj]
                    temp1 = [clone]
                    ListSortedChildren(obj, temp0)
                    ListSortedChildren(clone, temp1)
                    if len(temp0) == len(temp1):
                        #Quick safety check
                        toCloneFull.extend(temp0)
                        clonesFull.extend(temp1)
                else:
                    self.root.InfoMessage('CMDFailedClone', obj.GetPath())
            else:
                self.root.InfoMessage('CMDFailedClone', token)
                
        tag = ' '.join(tag)
        self.clipboard.SetTag(tag)
        
        #Restore connections
        idx = 0
        for op in toCloneFull:
            cloneOp = clonesFull[idx]
            ports = op.GetPorts(IN|OUT|MAT|ENE|SIG)
            for port in ports:
                if port.GetParent() is op:
                    conn = port.GetConnection()
                    if conn != None:
                        connOp = conn.GetParent()
                        if connOp in toCloneFull:
                            connIdx = toCloneFull.index(connOp)
                            connCloneOp = clonesFull[connIdx]
                            clonePort = cloneOp.GetPort(port.GetName())
                            connClonePort = connCloneOp.GetPort(conn.GetName())
                            clonePort.ConnectTo(connClonePort)
            idx += 1
            
        if deleteAfter:
            for op in toClone:
                self.Delete(op.GetPath())
            self.root.InfoMessage('CMDAfterCut', (tag, ))
        else:
            if tag == "" :
                tag = "Nothing"
            self.root.InfoMessage('CMDAfterCopy', (tag, ))
            
        self.clipboard.SetNeedCleanUp(1)
        #except:
        #self.clipboard = []
        
    def Cut(self, remaining):
        """Cut is just like copy, but deleting the source objects"""
        self.Copy(remaining, True)
        
    def Paste(self, remaining):
        remaining = remaining.strip()
        if not remaining:
            parentObj = self.currentObj
        else:
            token = remaining.split()[0]
            if token[0] == '/':
                parentObj = self.GetObject(self.root, token[1:])
            else:
                parentObj = self.GetObject(self.currentObj, token)
                
        if parentObj != None:
            unitOpNames = parentObj.GetChildUONames()
            tag = self.clipboard.GetTag()
            pasteTag = []
            if len(self.clipboard.GetContents()) == 0:
                self.root.InfoMessage('CMDClipboardEmpty', ())
                return
            self.root.InfoMessage('CMDBeforePaste', (tag,))
            for obj, name in self.clipboard.GetContents():
                newName = name
                if newName == '/':
                    newName = 'Root'
                    idx = 1
                    tryName = 'RootClone'
                else:
                    idx = 0
                    tryName = newName
                while tryName in unitOpNames:
                    if idx == 0:
                        tryName = newName + 'Clone'
                    else:
                        tryName = newName + 'Clone' + '_' + str(idx)
                    idx += 1
                newName = tryName
                    
                parentObj.AddObject(obj, newName)
                unitOpNames.append(newName)
                pasteTag.append(obj.GetPath())
            pasteTag = ' '.join(pasteTag)
            self.root.InfoMessage('CMDAfterPaste', (tag, pasteTag))
            
        self.clipboard.SetNeedCleanUp(0)
        self.clipboard.Clear()
        
        
def ListSortedChildren(op, opList):
    children = op.GetChildUnitOps()
    children.sort()
    for name, child in children:
        opList.append(child)
        ListSortedChildren(child, opList)
        
    
def dequote(s):
    """ remove quotes from string s """
    if s and s[0] in '\'"':
        return re.split(s[0], s[1:],1)[0]
    else:
        return s

def AppendFileNames(fileLst, dirName, fNames):
    """Loads the file names into files lst by appending"""
    for fName in fNames:
        if os.path.isfile(os.path.join(dirName, fName)):
            fileLst.append(os.path.join(dirName, fName))
        
def MakeDirs(newdir, mode=0777):
    """Silently force the existance of newdir. Do not raise error if newdir already exists"""
    #From Python cookbook
    #Creating Directories Including Necessary Parent Directories
    try: os.makedirs(newdir, mode)
    except OSError, err:
        # Reraise the error unless it's about an already existing directory
        if err.errno != errno.EEXIST or not os.path.isdir(newdir):
            raise
    
    
def PathOf(desc):
    try:
        if isinstance(desc, Ports.Port):
            portParent = desc.GetParent()
            return portParent.ShortestPortPath(desc)
        elif isinstance(desc, CreateObject):
            return  desc.parent.GetPath() + '.' + desc.description
        elif hasattr(desc, 'GetPath'):
            return desc.GetPath()
        else:
            return str(desc)
    except:
        return str(desc)
        


def SpecPortFromPort(fromPort_toPort, cli):
    #Comes in as a stuple so it is user to implement with a map call
    fromPort, toPort = fromPort_toPort
    props = fromPort.GetProperties()
    toProps = toPort.GetProperties()
    toPath = toPort.GetPath()
    
    def SetValueIfPossible(propName, value):
        toStat = toProps.get(propName, None)
        if toStat:
            toStat = toStat.GetCalcStatus()
        if toStat == None or toStat & FIXED_V or toStat & UNKNOWN_V:
            toPort.SetPropValue(propName, value, FIXED_V)
            #unit = cli.units.GetCurrentUnit(PropTypes.get(propName, PropTypes[GENERIC_VAR]).unitType)
            #if unit: value = unit.ConvertFromSim42(value)
            #cli.ProcessCommand('%s.%s = %f' %(toPath, propName, value))
            
    if isinstance(fromPort, Ports.Port_Material):
        if isinstance(toPort, Ports.Port_Material):
            #Get the most common flash properties 
            valP = valVF = valT = None
            propP = props.get(P_VAR, None)
            if propP:
                valP, statP = propP.GetValue(), propP.GetCalcStatus()
            propVF = props.get(VPFRAC_VAR, None)
            if propVF:
                valVF, statVF = propVF.GetValue(), propVF.GetCalcStatus()
            propT = props.get(T_VAR, None)
            if propT:
                valT, statT = propT.GetValue(), propT.GetCalcStatus()
            propH = props.get(H_VAR, None)
            if propH:
                valH, statH = propH.GetValue(), propH.GetCalcStatus()
            
            #Now take some decisions to set the values
            if valP and valT:
                SetValueIfPossible(P_VAR, valP)
                SetValueIfPossible(T_VAR, valT)
                
            elif valP and valH != None:
                SetValueIfPossible(P_VAR, valP)
                SetValueIfPossible(H_VAR, valH)
            
            elif valP and valVF != None:
                SetValueIfPossible(P_VAR, valP)
                SetValueIfPossible(VPFRAC_VAR, valVF)
        
            elif valT and valVF != None:
                SetValueIfPossible(T_VAR, valT)
                SetValueIfPossible(VPFRAC_VAR, valVF)
                
                
            #Now do extensive props
            stay = True
            propName = MOLEFLOW_VAR
            prop = props.get(propName, None)
            if prop:
                val = prop.GetValue()
                if val != None:
                    stay = False
                    SetValueIfPossible(propName, val)
            if stay:
                propName = MASSFLOW_VAR
                prop = props.get(propName, None)
                if prop:
                    val = prop.GetValue()
                    if val != None:
                        stay = False
                        SetValueIfPossible(propName, val)
            if stay:
                propName = VOLFLOW_VAR
                prop = props.get(propName, None)
                if prop:
                    val = prop.GetValue()
                    if val != None:
                        stay = False
                        SetValueIfPossible(propName, val)

            if stay:
                propName = STDVOLFLOW_VAR
                prop = props.get(propName, None)
                if prop:
                    val = prop.GetValue()
                    if val != None:
                        stay = False
                        SetValueIfPossible(propName, val)        
                
                
            #Now do the compositions
            cmps = fromPort.GetCompounds()
            toCmps = toPort.GetCompounds()
            cmpNames = toPort.GetCompoundNames()
            lenCmps = len(cmps)
            lenToCmps = len(toCmps)
            if lenCmps == lenToCmps:
                for i in range(lenCmps):
                    cmp = cmps[i]
                    val = cmp.GetValue()
                    toCmp = toCmps[i]
                    status = toCmp.GetCalcStatus()
                    if val != None and (status & FIXED_V or status & UNKNOWN_V):
                        #cmpName = re.sub(' ', '_', cmpNames[i])
                        #cli.ProcessCommand('%s.Fraction.%s = %f' %(toPath, cmpName, val))
                        toCmp.SetValue(val, FIXED_V)
                        
                        
def RemoveComments(rawCmd):
    """Removes the comments when the # is not in quotes"""
    
    cmd = rawCmd.strip()
    if not cmd: return ""
    
    #If there are no quotes, then just remove the comments blindly
    if not "'" in rawCmd and not '"' in rawCmd:
        cmd = re.sub('#.*', '', rawCmd)
        return cmd.strip()
    
    #Check every line one by one
    lines = cmd.split('\n')
    fixedLines = []
    for line in lines:
        #Initialize like this
        fixedLine = line
        
        if not "'" in line and not '"' in line:
            #No quotes... then just cut right away
            fixedLine = re.sub('#.*', '', line)
            
        else:
            #Check for every # to see if it is between quotes
            limits = []
            for term in QUO_REGEX.finditer(line):
                limits.append((term.span()[0],term.span()[1]-1))
            pounds = []
            for term in re.finditer("#", line):
                pounds.append(term.span()[0])
            
            quit = False
            for pound in pounds:
                isInside = False
                for start, end in limits:
                    if pound < start:
                        #Cut from there on and finish the line
                        fixedLine = line[:pound]
                        quit = True
                        break
                    elif pound >= start and pound <= end:
                        #The # is inside of quotes, just skip this one
                        isInside = True
                        break
                if quit:
                    break
                elif not isInside:
                    #This # could not be found anywhere. Just cut it there
                    fixedLine = line[:pound]
                    break
                
        fixedLines.append(fixedLine)
        
    cmd = '\n'.join(fixedLines)
    cmd = cmd.strip()
        
    return cmd


def Tokenize(rawCmd, defSep=' ', dequote=False):
    """Breaks rawCmd into a list of items depending on how it is quoted.
    Unquoted stuff is separated by defSep
    
    Examples (assuming defSep = ' ':
        "asd" "asdf" "jd d "       -> ["asd", "asdf", "jd d "]
        'asd' '''asdf''' "jd d "   -> ["asd", "asdf", "jd d "]
        C:ssd dsa "C:ssd dsa"      -> ["C:ssd", "dsa", "C:ssd dsa"]
        
        
    """
    limits = []
    for term in QUO_REGEX.finditer(rawCmd):
        limits.append((term.span()[0],term.span()[1]-1))
    oldIdx = -1
    idx = -1
    cmds = []
    end = len(rawCmd)
    #Parse the string form the beginning
    while idx < (end-1):
        idx = rawCmd.find(defSep, idx+1)              #find the separator
        if idx != -1:                                 #Found the separator
            isInside = False
            for span in limits:
                if idx >= span[0] and idx <= span[1]: #The separator is inside quotes
                    isInside = True
                    break
            if not isInside:
                cmds.append(rawCmd[oldIdx+1:idx])     
                oldIdx = idx
        else:
            cmds.append(rawCmd[oldIdx+1:])
            
            break
        
    if dequote:
        for i in range(len(cmds)):
            cmds[i] = cmds[i].split("'")
            cmds[i] = ''.join(cmds[i])
            cmds[i] = cmds[i].split('"')
            cmds[i] = ''.join(cmds[i])
        
    return cmds
    
class Clipboard(object):
    def __init__(self):
        self.contents = []
        self.tag = ""
        self.needCleanUp = 0
        
    def SetTag(self, tag):
        self.tag = tag
        
    def SetNeedCleanUp(self, needCleanUp):
        self.needCleanUp = needCleanUp
        
    def GetNeedCleanUp(self):
        return self.needCleanUp
    
        
    def GetTag(self):
        return self.tag
        
    def GetContents(self):
        return self.contents
    
    def SetContents(self, contents):
        self.contents = contents
        
    def AppendItem(self, item):
        self.contents.append(item)
        
    def CleanUp(self):
        """Cleans up everything in the clipboard and then clears it"""
        for obj, name in self.contents:
            if hasattr(obj, 'CleanUp'):
                try:
                    obj.CleanUp()
                except:
                    pass
        
    def Clear(self):
        if self.needCleanUp:
            self.CleanUp()
        self.contents = []
        self.tag = ""
        
class CreateObject:
    """wraps the parent object and the child description together"""
    def __init__(self, parent, description):
        self.parent = parent
        self.description = description
        

    def GetPath(self):
        """
        sort of place holder - just return description for error messages
        """
        return self.description
        

class InfoCallBack(object):
    """
    call back object with at least a handleMessage method
    """
    def __init__(self):
        """
        set up language for rendering
        """
        self.language = MessageHandler.GetCurrentLanguage()
        self.languageDict = MessageHandler.GetLanguageDict(self.language)
        
    def SetLanguage(self, language):
        """
        change the rendering dictionary to correspond with language
        """
        try:
            newDict = MessageHandler.GetLanguageDict(language)
            if newDict:
                self.languageDict = newDict
                self.language = language
        except:
            pass
        
    def GetLanguageDict(self):
        return self.languageDict
    
    def GetLanguage(self):
        return self.language
        
    def handleMessage(self, message, args, msgType=MessageHandler.infoMessage):
        """most basic of call backs"""
        if not MessageHandler.IsIgnored(message):
            sys.stdout.write('%s\n' %
               (MessageHandler.RenderMessage(message, args, self.languageDict)))
            
objSeparators = './:'
operators = {
             '+': CommandInterface.Add,
             '-': CommandInterface.Minus,
             '=': CommandInterface.Equal,
             '~=': CommandInterface.Estimate,
             '=>': CommandInterface.Calculate,
             '->': CommandInterface.Connect,
             '@': CommandInterface.Alias,
             '>>': CommandInterface.MoveCompound
            }
commands = {
            'cd':                  CommandInterface.Cd,
            'read':                CommandInterface.Read,
            'log':                 CommandInterface.Log,
            'clear':               CommandInterface.Clear,
            'dir':                 CommandInterface.Contents,
            'delete':              CommandInterface.Delete,
            'valueOf':             CommandInterface.ValueOf,
            'createPort':          CommandInterface.CreatePort,
            'units':               CommandInterface.Units,
            'store':               CommandInterface.Store,
            'recall':              CommandInterface.Recall,
            'hold':                CommandInterface.Hold,
            'go':                  CommandInterface.Go,
            'language':            CommandInterface.SetLanguage,
            'displayproperties':   CommandInterface.SetPropertyOrder,
            'commonproperties':    CommandInterface.SetCommonProperties,
            'supportedproperties': CommandInterface.SupportedProperties,
            'tree':                CommandInterface.Tree,
            'ls':                  CommandInterface.ListFiles,
            'mkdir':               CommandInterface.MakeDirectory,
            'rm':                  CommandInterface.DeleteFile,
            'rmdir':               CommandInterface.DeleteDirectory,
            'export':              CommandInterface.Export,
            'import':              CommandInterface.Import,
            'propertytype':        CommandInterface.UpdatePropertyType,
            'maxversions':         CommandInterface.MaxCaseVersions,
            'about':               CommandInterface.About,
            'optimizecode':        CommandInterface.OptimizeCode,
            'copy':                CommandInterface.Copy,
            'cut':                 CommandInterface.Cut,
            'paste':               CommandInterface.Paste
            }

#Commands that can be processed while solving or forgetting
readOnlyCommands = ['valueOf', 'dir']

# normally the global lock is None and ignored, but if a CI is used by a multithreaded
# application, that app should set this lock and the CI will acquire it before reading and writing
# and release it when done (to ensure no conflict in file descriptors)
globalLock = None

# base path above which files cannot be opened
globalBasePath = None

# if netServer is assigned, it should be to an object which supports the
# following methods

# open(rootOp, name, mode)
# this mimics the system open, with possible security etc checks.  The CI root is used as
# the key so that it can be traced back to a common ancestor and thus session when new CIs
# are created in a session (i.e. scriptops)

# switchedRootOp( oldRootOp, newRootOp)
# tells the net server when the CI has acquired a new root flowsheet, such as during a 
# recall or clear operation
netServer = None

def run(optimize=0):
    MessageHandler.IgnoreMessage('SolvingOp')
    MessageHandler.IgnoreMessage('DoneSolving')
    MessageHandler.IgnoreMessage('BeforePortDisconnect')    
    MessageHandler.IgnoreMessage('AfterPortDisconnect')  
    MessageHandler.IgnoreMessage('BeforeControllerDisconnect')
    # ignore the callback messages
    MessageHandler.IgnoreMessage('CMDNotifyReadFile')
    MessageHandler.IgnoreMessage('CMDNotifyStore')
    MessageHandler.IgnoreMessage('CMDNotifyClear')
    MessageHandler.IgnoreMessage('CMDNotifyUnits')
    MessageHandler.IgnoreMessage('CMDNotifyAddCompound')
    MessageHandler.IgnoreMessage('CMDNotifyAddHypo')
    MessageHandler.IgnoreMessage('CMDNotifyCreateThermo')    
    MessageHandler.IgnoreMessage('CMDNotifyCreateObj')
    MessageHandler.IgnoreMessage('CMDNotifyBeforeDeleteObj')
    MessageHandler.IgnoreMessage('CMDNotifyDeleteObj')
    MessageHandler.IgnoreMessage('CMDNotifyConnect')
    MessageHandler.IgnoreMessage('CMDNotifyBeforeDisconnect')
    MessageHandler.IgnoreMessage('CMDNotifyDisconnect')
    MessageHandler.IgnoreMessage('CMDNotifyAddObj')
    MessageHandler.IgnoreMessage('CMDNotifySetValue')
    MessageHandler.IgnoreMessage('CMDNotifyDeleteCompound')
    MessageHandler.IgnoreMessage('CMDNotifyMoveCompound')
    MessageHandler.IgnoreMessage('CMDNotifyAdd')    
    MessageHandler.IgnoreMessage('CMDNotifyMinus')
    MessageHandler.IgnoreMessage('CMDNotifyBeforeAdd')
    MessageHandler.IgnoreMessage('CMDNotifyBeforeMinus')
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '1':
            MessageHandler.IgnoreMessage('TowerCalcJacobian')
            MessageHandler.IgnoreMessage('TowerInnerError')
            MessageHandler.IgnoreMessage('TowerOuterError')
            
    interface = CommandInterface(optimizeCode=optimize)
    while 1:
        try:
            interface.ProcessCommandStream(sys.stdin, sys.stdout, sys.stdout)
            break
        except CallBackException, e:
            interface.infoCallBack.handleMessage('CMDCallBackException', str(e))
        except Exception, e:
            tb = ''
            for i in traceback.format_tb(sys.exc_traceback):
                tb += i + '\n'
            interface.infoCallBack.handleMessage('CMDUnhandledError', (str(sys.exc_type), str(e), tb))

    interface.CleanUp()

def dump_garbage(  ):
    """
    show us what the garbage is about
    """
    # Force collection
    print "\nGARBAGE:"
    gc.collect(  )

    print "\nGARBAGE OBJECTS:"
    for x in gc.garbage:
        s = str(x)
        print type(x),
        if len(s) > 120: s = s[:117]+'...'
        try:
            print ' Path:%s ' % x.GetPath()
        except:
            try:
                print ' Name:%s ' % x.name
            except:
                print ' No Name'
                                
        print 'o="%s"' % s
        #for y in  gc.get_referrers(x):
            #s = str(y)
            #if len(s) > 120: s = s[:117]+'...'
            #print 'Referrer: ', type(y),
            #try:
                #print ' Path:%s ' % y.GetPath()
            #except:
                #try:
                    #print ' Name:%s ' % y.name
                #except:
                    #print ' No Name'
                
            #print 'o="%s"\n' % s
            
        
def SetUpCodeOptimization(optimize):
    try:
        
        methodLst = [(UnitOperations.UnitOperation.IsForgetting, None),
                     (UnitOperations.UnitOperation.FlashAllPorts, 1),
                     (UnitOperations.UnitOperation.PushSolveOp, None),
                     (UnitOperations.UnitOperation.PushForgetOp, None),
                     (UnitOperations.UnitOperation.GetObject, None),
                     (UnitOperations.UnitOperation.GetThermo, None),
                     (UnitOperations.UnitOperation.GetParameterValue, None),
                     (UnitOperations.UnitOperation.PushResetCalcPort, None),
                     (UnitOperations.UnitOperation.ShortestPortPath, None),
                     (UnitOperations.UnitOperation.Solver, None),
                     (Ports.Port.ShareWith, None),
                     (Ports.Port.GetParentOp, None),
                     (Ports.Port.UpdateConnection, None),
                     (Ports.Port.PropertyModified, None),
                     (Ports.Port.GetLocalValue, None),
                     (Ports.Port.SetPropValue, None),
                     (Ports.Port.GetNuKnownProps, None),
                     (Ports.Port.Forget, None),
                     (Ports.Port.GetObject, None),
                     (Ports.Port_Material.ShareWith, None),
                     (Ports.Port_Material.CalcFlows, None),
                     (Ports.Port_Material.AssignFlashResults, None),
                     (Ports.Port_Material.ReadyToFlash, None),
                     (BasicProperty.Forget, None),
                     (BasicProperty.GetValue, None),
                     (BasicProperty.SetValue, None),
                     (BasicProperty.GetCalcStatus, None),
                     (BasicProperty.CheckTolerance, None)]#,
                     #(Balance.Balance.DoBalance, 1),
                     #(Balance.Balance.DoMoleBalance, 1)]
        
        if optimize:
            for method, param in methodLst:
                if param != None:
                    psyco.bind(method, param)
                else:
                    psyco.bind(method)
        else:
            for method, param in methodLst:
                psyco.unbind(method)
                
                
    except:
        print 'failed to set up code optimization';
    
    


if __name__ == '__main__':
    
    gc.enable(  )
    gc.set_debug(gc.DEBUG_LEAK)

    optimize = 1
    run(optimize)

    
    #import profile
    #profile.run('run()', "C:\\temp\\logprof.txt")
    
    #import pstats
    #p = pstats.Stats("C:\\temp\\logprof3.txt")
    #p.sort_stats('time', 'cum')
    #p.print_stats()
    

    #A better profiler
    ##import hotshot, hotshot.stats
    ##prof = hotshot.Profile("C:\\temp\\logprof2.txt")
    ##prof.runcall(run)
    ##prof.close()

    #Lines used to display info
    #import hotshot, hotshot.stats
    #stats = hotshot.stats.load("C:\\temp\\logprof.txt")
    #stats.strip_dirs()
    #stats.sort_stats('time', 'calls')
    #stats.print_stats(20)
    
    dump_garbage(  )    

