import sys, string, code, traceback, os, re
from wxPython.wx import *

from sim import unitop
from sim.unitop import UnitOperations
from sim.PyCrust import shell
import guicmd

DEFAULT_PATH_TST_FILES = "."
DEFAULT_PATH_S42_FILES = "."

class Sim42Shell(shell.Shell):
    def __init__(self, parent, id=-1, pos=wxDefaultPosition, \
                 size=wxDefaultSize, style=wxCLIP_CHILDREN, introText='', \
                 locals=None, InterpClass=None, *args, **kwds):
        shell.Shell.__init__(self, parent, id, pos, size, \
                                     style, introText, locals, \
                                     InterpClass, *args, **kwds)
                
    def ClearOutput(self):
        self.clear()
        
    def ExecFromTextInput(self, command):
        self.run(command, prompt=0, verbose=1)

    def GetLocals(self):
        return self.interp.locals

    def GetGlobals(self):
        return globals()

class Sim42Interpreter(object):
    def __init__(self, locals=None, rawin=None, \
                 stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
        """Create an interactive interpreter object."""

        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        #Used for the cmd interface
        self.morecmd = 0
        self.command = ''
        self.quote = '"""'
        
        if locals:
            self.locals = locals
            guiParent = locals.get('guiParent', None)
            baseFlowsheet = locals.get('parentFlowsh', None)
        else:
            self.locals = {}
            guiParent = None
            baseFlowsheet = None
            
        self.cmd = guicmd.guiCommandInterface(baseFlowsheet=baseFlowsheet, guiParent=guiParent)

        self.locals['guiParent'] = guiParent
        self.locals['parentFlowsh'] = self.cmd.root
        self.locals['thAdmin'] = self.cmd.thermoAdmin

        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = '>>> '
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = '... '

        #Not used by the cmd interface, but must be there
        self.more = 0
        self.revision = '(1/0) * 0'
        self.startupScript = None
        self.introText = 'Wellcome to the Command Interface of sim42. Have fun !'
        

    def push(self, command):
        """Send command to the interpreter to be executed."""
        command = str(command)
        #Is it not waitng for more stuff ???
        if not self.morecmd:
            #Does it want to start waitng for stuff ???
            if len(command) > 3 and (command[-3:] == "'''" or command[-3:] == '"""'):
                self.morecmd = 1
                self.quote = self.cmd.quote = command[-3:]
                self.command = command[:-3]
                self.cmd.idxForQuote = len(self.command)
            else:
                self.command = command
        else:
            #Should it stop waiting??
            if command[-3:] == self.quote:
                self.morecmd = 0
                self.command += os.linesep + command[:-3]
            else:
                self.command += os.linesep + command

        if not self.morecmd:
                out = self.cmd.ProcessCommandString(self.command)
                if out: self.stdout.write(out)
                if self.cmd.currentObj and hasattr(self.cmd.currentObj, 'GetPath'):
                    sys.ps1 = self.cmd.currentObj.GetPath() + '> '
                else:
                    sys.ps1 = 'Illegal current object> '
                self.command = ''
                self.cmd.idxForQuote = None
        else:
            sys.ps1 = '... '
        
        return 0

    def getAutoCompleteKeys(self):
        """Return list of auto-completion keycodes."""
        return [ord('.'), ord(' '), ord('/')]

    def getAutoCompleteList(self, rawCmd='', *args, **kwds):
        """Return list of auto-completion options for a command.
        
        The list of options will be based on the locals namespace."""
        try:
            actKey = rawCmd[-1]     #Was it activated by a '/', '.' or ' ' ?
            cmd = re.sub('#.*', '', rawCmd)  # remove comments
            cmd = string.strip(cmd)
            if not cmd: return None      
            
            # get lhs description
            (lhsDesc, remaining) = self.cmd.GetNextTerm( cmd )    
    
            lst = []
            
            #Get contents from the root
            if actKey == '/':
                if hasattr(self.cmd.root, 'GetContents'):
                    lst = []
                    for i in self.cmd.root.GetContents():
                        lst.append(i[0])
                        
            #Try different options
            elif actKey == '.':
                myDesc = string.split(cmd, ' ')[-1][:-1]                
                if myDesc[0] == '/': lhsObj = self.cmd.GetObject(self.cmd.root, myDesc[1:])
                else: lhsObj = self.cmd.GetObject(self.cmd.currentObj, myDesc)
                
                #Object with get contents attr
                if hasattr(lhsObj, 'GetContents'):
                    lst = []
                    for i in lhsObj.GetContents():
                        lst.append(i[0])
                
                #If it is a thermo provider, return available prop pkgs
                elif myDesc in self.cmd.thermoAdmin.GetAvThermoProviderNames():
                    thAd = self.cmd.thermoAdmin
                    lst = thAd.GetAvPropPkgNames(myDesc)
                    
                #If a folder with unit ops, then retun av u ops
                elif myDesc in unitop.__all__:
                    uop = guicmd.CommandInterface.__dict__.get(myDesc, None)
                    if hasattr(uop, 'VALID_UNIT_OPERATIONS'):
                        lst = uop.VALID_UNIT_OPERATIONS
                    
            #Is it a command?
            elif guicmd.CommandInterface.commands.has_key(lhsDesc):
                cmdActOnObj = ('cd', 'view', 'delete', 'dir', 'valueOf')
                lst = []
                if lhsDesc == 'units':
                    if actKey == ' ' and remaining == '':
                        lst = self.cmd.units.GetSetNames()
                elif lhsDesc in cmdActOnObj:
                    if actKey == ' ' and remaining == '':
                        lst = ['..', '/']
                        if hasattr(self.cmd.currentObj, 'GetContents'):
                            for i in self.cmd.currentObj.GetContents():
                                lst.append(i[0])
                elif lhsDesc == 'language':
                    if actKey == ' ' and remaining == '':
                        dct = guicmd.CommandInterface.MessageHandler.GetSupportedLanguages()
                        #dct['languages'] should have the main languages supported
                        lst = list(dct['languages'])
                        
            lst.sort()
            return lst
            
        except:
            return []


    def getCallTip(self, command='', *args, **kwds):
        """Don't return anything for the command interface"""
        return ('', '', '')
    
    def CleanUp(self):
        """Clean up the command interface"""
        self.cmd.CleanUp()


ID_USE_CMD = wxNewId()
ID_VERB = wxNewId()
ID_RUN_CMD = wxNewId()
ID_RUN_CMDDUMP = wxNewId()
ID_SAVE_HIST = wxNewId()
ID_SAVE_HISTAS = wxNewId()
ID_RECALC = wxNewId()

class ShellFrame(wxFrame, shell.ShellMenu):
    """Frame containing the PyCrust shell component."""
    
    name = 'PyCrust Sim42Shell Frame'
    revision = shell.__revision__
    
    def __init__(self, parent=None, id=-1, title='Sim42Shell', \
                 pos=wxDefaultPosition, size=wxDefaultSize, \
                 style=wxDEFAULT_FRAME_STYLE, locals=None, \
                 InterpClass=None, *args, **kwds):
        """Create a PyCrust ShellFrame instance."""
        wxFrame.__init__(self, parent, id, title, pos, size, style)
        intro = 'Powered by PyCrust %s - The Flakiest Python Shell' % shell.VERSION
        self.CreateStatusBar()
        self.SetStatusText(intro.replace('\n', ', '))
        if wxPlatform == '__WXMSW__':
            #currPath = os.getcwd()
            #filename = os.path.join(os.path.dirname(currPath), 'gui', 'images', 'sim42.ico')
            filename = os.path.join('images', 'sim42.ico')
            icon = wxIcon(filename, wxBITMAP_TYPE_ICO)
            self.SetIcon(icon)
        locals['guiParent'] = self
        self.shell = Sim42Shell(parent=self, id=-1, introText=intro, \
                                              locals=locals, InterpClass=InterpClass, \
                                              *args, **kwds)
        # Override the shell so that status messages go to the status bar.
        self.shell.setStatusText = self.SetStatusText
        self.createMenus()

        self.origInterp = self.shell.interp
        #Make sure both interpreters have same stdin and stdout
        stdin = self.origInterp.stdin
        stdout = self.origInterp.stdout
        stderr = self.origInterp.stderr
        self.sim42interp = Sim42Interpreter(self.shell.interp.locals, stdin, stdout, stderr)
        self.sim42interp.cmd.output = self.shell
        
        self.verbose = false
        self.histFilePath = None
        self.simFilePath = None
        
        EVT_CLOSE(self, self.OnCloseWindow)
        if len(sys.argv) > 1:
            try:
                fileName = sys.argv[1]
                path = os.path.join(currPath, fileName)
                file = None
                #If file's not empty, run its commands
                try:
                    self.shell.runfile(path)
                except:
                    print "Error trying to read commands from file"
                    if file: file.close()
                self.shell.StartSavingToFile(path, true)
            except:
                print "Error trying to write to file"

        self.UseCommandInterface(True)                
                
    def Eval(self, rawCmd):
        self.shell.run(rawCmd)
        
    def createMenus(self):
        """Overloaded method """
        shell.ShellMenu.createMenus(self)
        
        m = self.sim42Menu = wxMenu()
        m.Append(ID_USE_CMD, '&Sim42 Interpreter \tCtrl+F', 'Changes to the command interface of Sim42', 1)
        m.Append(ID_VERB, '&Verbose', 'Display call back info to the shell', 1)
        m.AppendSeparator()
        m.Append(ID_RUN_CMD, '&Run Command Script...', 'Read a file with command interface instructions')
        m.Append(ID_RUN_CMDDUMP, 'R&un Command Script Dump to File...', 'Read a file with command interface instructions and dump output to a file')
        m.AppendSeparator()
        m.Append(wxID_NEW, '&New \tCtrl+N', 'New Simulation')
        m.Append(wxID_OPEN, '&Open \tCtrl+O', 'Open Existing Simulation')
        m.AppendSeparator()
        m.Append(wxID_SAVE, 'Sa&ve \tCtrl+S', 'Save')
        m.Append(wxID_SAVEAS, 'Save &As...', 'Save simulatation as...')
        m.AppendSeparator()
        m.Append(ID_SAVE_HIST, 'Save &History', 'Save history of commands')
        m.Append(ID_SAVE_HISTAS, 'Save H&istory As...', 'Save history of commands as...')
        m.Append(ID_RECALC, 'R&ecalculate Op \tCtrl+R', 'Recalculate current unit op')
        
        self.menuBar.Append(self.sim42Menu, '&Sim42')
        
        EVT_MENU(self, ID_USE_CMD, self.OnSim42ChangeInterpreter)
        EVT_MENU(self, ID_VERB, self.OnSim42Verbose)
        EVT_MENU(self, ID_RUN_CMD, self.OnSim42RunCmdFile)
        EVT_MENU(self, ID_RUN_CMDDUMP, self.OnSim42RunCmdFileDump)
        EVT_MENU(self, wxID_NEW, self.OnFileNew)   
        EVT_MENU(self, wxID_OPEN, self.OnFileOpen)
        EVT_MENU(self, wxID_SAVE, self.OnFileSave)   
        EVT_MENU(self, wxID_SAVEAS, self.OnFileSaveAs)
        EVT_MENU(self, ID_SAVE_HIST, self.OnSim42SaveHist)
        EVT_MENU(self, ID_SAVE_HISTAS, self.OnSim42SaveHistAs)
        EVT_MENU(self, ID_RECALC, self.OnSim42RecalcCurrent)

        EVT_UPDATE_UI(self, ID_USE_CMD, self.OnUpdateMenu)
        EVT_UPDATE_UI(self, ID_VERB, self.OnUpdateMenu)

    def OnSim42RecalcCurrent(self, event):
        if isinstance(self.sim42interp.cmd.currentObj, UnitOperations.UnitOperation):
            if self.shell.interp != self.sim42interp:
                self.UseCommandInterface(True)
            self.shell.run('Ignored = 1; Ignored = None')
        
    def OnFileNew(self, event):
        """New simulation"""
        self.UseCommandInterface(false)
        self.sim42interp.cmd.Clear(None)
        self.UpdateLocalsFromCmd()
        self.shell.clear()
        self.shell.prompt()
        self.SetTitle('Simulation --> None')

    def OnFileOpen(self, event):
        """Open a simulation"""
        path = self.PromptPathOpenSim()
        if not path: return
        self.Open(path)

    def PromptPathOpenSim(self):
        """Propmts for a path for opening a command interface file"""
        defaultPath = DEFAULT_PATH_S42_FILES
        defaultName = ""
            
        dlgSave = wxFileDialog(self, "Open Simulation", defaultPath, defaultName,
                               "*.s42|*.*", wxOPEN|wxCHANGE_DIR)
        if dlgSave.ShowModal() == wxID_OK:
            path = dlgSave.GetPath()
        else:
            path = None
        dlgSave.Destroy()
        return path

    def Open(self, path):
        """Opens a simulation"""
        if self.sim42interp == self.shell.interp:
            self.UseCommandInterface(false)
        self.shell.clear()
        self.shell.prompt()
       
        if self.shell.interp != self.sim42interp:
            self.UseCommandInterface(True)
        self.shell.run('recall %s' %path)

        #self.sim42interp.cmd.Recall(path)
        #Calling the cmd interface originates the needs for the next call
        self.UpdateLocalsFromCmd()

        self.SetTitle('Simulation --> ' + path)
        self.simFilePath = path
        
    def UpdateLocalsFromCmd(self):
        """Makes sure the locals dictionary has the current thAdmin and baseFlowsh from cmd interface"""
        self.origInterp.locals["parentFlowsh"] = self.sim42interp.cmd.root
        self.origInterp.locals["thAdmin"] = self.sim42interp.cmd.thermoAdmin
        
    def OnFileSave(self, event):
        """Save a simulation"""
        self.Save()        
    
    def OnFileSaveAs(self, event):
        """Save simulation as..."""
        path = self.PromptPathSaveAs()
        if not path: return
        else: self.simFilePath = path
        self.Save()

    def PromptPathSaveAs(self):
        """Propmts for a path for saving a file"""
        path = self.simFilePath
        if path:
            defaultPath = os.path.dirname(path)
            defaultName = os.path.basename(path)[:-4]
        else:
            defaultPath = "."
            defaultName = ""
            
        dlgSave = wxFileDialog(self, "Save Simulation As", defaultPath, defaultName,
                               "*.s42", wxSAVE|wxOVERWRITE_PROMPT|wxCHANGE_DIR)
        if dlgSave.ShowModal() == wxID_OK:
            path = dlgSave.GetPath()
        else:
            path = None
        dlgSave.Destroy()
        return path
   
    def Save(self):
        """Saves the simulation to a file"""
        if not self.simFilePath:
            path = self.PromptPathSaveAs()
            if not path: return
            else: self.simFilePath = path
            
        #Why bother doing new code if the cmd interface does it already
        if self.shell.interp != self.sim42interp:
            self.UseCommandInterface(True)
        self.shell.run('store %s' %self.simFilePath)
        #self.sim42interp.cmd.Store(self.simFilePath)

        self.SetTitle('Simulation --> ' + self.simFilePath)

    def OnSim42ChangeInterpreter(self, event):
        """Changes the python interpreter for the command interface of sim42"""
        self.UseCommandInterface(event.IsChecked())

    def UseCommandInterface(self, option):
        """option = true if user wants command interface active"""
        if option:
            #change prompt
            if self.sim42interp.cmd.currentObj and hasattr(self.sim42interp.cmd.currentObj, 'GetPath'):
                sys.ps1 = self.sim42interp.cmd.currentObj.GetPath() + '> '
            else:
                sys.ps1 = 'Illegal current object> '            
            
            #Say good bye
            self.shell.run("print '*************** Changed to Sim42 Command Interface ***************' ", prompt=0, verbose=0)
                
            #Change
            self.shell.interp = self.sim42interp

        else:
            #change prompt
            sys.ps1 = '>>> '
            sys.ps2 = '... '

            #Change
            self.shell.interp = self.origInterp    
            
            #Say hello
            self.shell.run("print '*************** Back to python ***************' ", prompt=0, verbose=0)
            

        self.shell.autoCompleteKeys = self.shell.interp.getAutoCompleteKeys()

    def OnSim42Verbose(self, event):
        """Display call back info in the shell"""
        self.verbose = event.IsChecked()
        if self.verbose:
            cb = ShellInfoCallBack(self.sim42interp)
            self.sim42interp.cmd.SetInfoCallBack(cb)
        else:
            self.sim42interp.cmd.SetInfoCallBack(self.sim42interp.cmd.infoCallBack)

    def OnSim42SaveHist(self, event):
        """Saves history"""
        self.SaveHistory()
            
    def OnSim42SaveHistAs(self, event): 
        """Save history as..."""
        path = self.PromptPathSaveHistoryAs()
        if not path: return
        else: self.histFilePath = path
        self.SaveHistory()
    
    def SaveHistory(self):
        """Saves history to a file"""
        if not self.histFilePath:
            path = self.PromptPathSaveHistAs()
            if not path: return
            else: self.histFilePath = path
            
        f = open(self.histFilePath, 'w')
        size = len(self.shell.history)
        for idx in range(size-1, -1, -1):
            f.write(self.shell.history[idx] + os.linesep)
        f.close
        
    def PromptPathSaveHistAs(self):
        """Propmts for a path for saving a file"""
        path = self.histFilePath
        if path:
            defaultPath = os.path.dirname(path)
            defaultName = os.path.basename(path)[:-4]
        else:
            defaultPath = "."
            defaultName = ""
            
        dlgSave = wxFileDialog(self, "Save History As", defaultPath, defaultName,
                               "*.hst", wxSAVE|wxOVERWRITE_PROMPT|wxCHANGE_DIR)
        if dlgSave.ShowModal() == wxID_OK:
            path = dlgSave.GetPath()
        else:
            path = None
        dlgSave.Destroy()
        return path

    def PromptPathSaveCmd(self):
        """Propmts for a path for saving the output of a cmd script"""
        defaultPath = "."
        defaultName = ""
            
        dlgSave = wxFileDialog(self, "Save Script As", defaultPath, defaultName,
                               "*.out", wxSAVE|wxOVERWRITE_PROMPT|wxCHANGE_DIR)
        if dlgSave.ShowModal() == wxID_OK:
            path = dlgSave.GetPath()
        else:
            path = None
        dlgSave.Destroy()
        return path


    def PromptPathOpenCmd(self):
        """Propmts for a path for opening a command interface file"""
        defaultPath = DEFAULT_PATH_TST_FILES
        defaultName = ""
            
        dlgSave = wxFileDialog(self, "Run Command File", defaultPath, defaultName,
                               "*.tst|*.*", wxOPEN|wxCHANGE_DIR)
        if dlgSave.ShowModal() == wxID_OK:
            path = dlgSave.GetPath()
        else:
            path = None
        dlgSave.Destroy()
        return path

    def OnSim42RunCmdFile(self, event):
        """Run command interface file"""
        path = self.PromptPathOpenCmd()
        if not path: return
        self.RunCmdFile(path)

    def OnSim42RunCmdFileDump(self, event):
        """Run command interface file and dump output to a file"""
        path = self.PromptPathOpenCmd()
        if not path: return
        pathOut = self.PromptPathSaveCmd()
        if not pathOut: return
        f = open(pathOut, 'w')
        oldOut = self.sim42interp.cmd.output
        oldOutSys = sys.stdout
        self.sim42interp.cmd.output = f
        sys.stdout = f
        self.IgnoreMessages()
        self.RunCmdFile(path)
        self.UnIgnoreMessages()
        f.close()
        self.sim42interp.cmd.output = oldOut
        sys.stdout = oldOutSys

    def RunCmdFile(self, path):
        """Run command interface file"""
        if not self.sim42interp == self.shell.interp:
            self.UseCommandInterface(True)
        self.shell.run("read " + path, prompt=0, verbose=0)
        
    
    def OnUpdateMenu(self, event):
        """Update menu items based on current status."""
        shell.ShellMenu.OnUpdateMenu(self, event)
        id = event.GetId()
        if id == ID_VERB:
            event.Check(self.verbose)
        elif id == ID_USE_CMD:
            event.Check(self.sim42interp == self.shell.interp)
        
    def OnCloseWindow(self, event):
        """Some clean up"""
        self.sim42interp.CleanUp()
        self.shell.destroy()
        self.Destroy()
        
    def IgnoreMessages(self):
        """Ignore some messages (Used to do same output as main() in CommandInterface.py)"""
        MessageHandler = guicmd.CommandInterface.MessageHandler
        
        MessageHandler.IgnoreMessage('SolvingOp')
        MessageHandler.IgnoreMessage('DoneSolving')
        MessageHandler.IgnoreMessage('BeforePortDisconnect')    
        MessageHandler.IgnoreMessage('AfterPortDisconnect')    
        
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

    def UnIgnoreMessages(self):
        """UnIgnore some messages"""
        MessageHandler = guicmd.CommandInterface.MessageHandler
        
        MessageHandler.UnIgnoreMessage('SolvingOp')
        MessageHandler.UnIgnoreMessage('DoneSolving')
        MessageHandler.UnIgnoreMessage('BeforePortDisconnect')    
        MessageHandler.UnIgnoreMessage('AfterPortDisconnect')    
        
        # ignore the callback messages
        MessageHandler.UnIgnoreMessage('CMDNotifyReadFile')
        MessageHandler.UnIgnoreMessage('CMDNotifyStore')
        MessageHandler.UnIgnoreMessage('CMDNotifyClear')
        MessageHandler.UnIgnoreMessage('CMDNotifyUnits')
        MessageHandler.UnIgnoreMessage('CMDNotifyAddCompound')
        MessageHandler.UnIgnoreMessage('CMDNotifyAddHypo')
        MessageHandler.UnIgnoreMessage('CMDNotifyCreateThermo')    
        MessageHandler.UnIgnoreMessage('CMDNotifyCreateObj')
        MessageHandler.UnIgnoreMessage('CMDNotifyBeforeDeleteObj')
        MessageHandler.UnIgnoreMessage('CMDNotifyDeleteObj')
        MessageHandler.UnIgnoreMessage('CMDNotifyConnect')
        MessageHandler.UnIgnoreMessage('CMDNotifyBeforeDisconnect')
        MessageHandler.UnIgnoreMessage('CMDNotifyDisconnect')
        MessageHandler.UnIgnoreMessage('CMDNotifyAddObj')
        MessageHandler.UnIgnoreMessage('CMDNotifySetValue')
        MessageHandler.UnIgnoreMessage('CMDNotifyDeleteCompound')
        MessageHandler.UnIgnoreMessage('CMDNotifyMoveCompound')
        MessageHandler.UnIgnoreMessage('CMDNotifyAdd')    
        MessageHandler.UnIgnoreMessage('CMDNotifyMinus')    
        MessageHandler.UnIgnoreMessage('CMDNotifyBeforeAdd')
        MessageHandler.UnIgnoreMessage('CMDNotifyBeforeMinus')

class App(wxApp):
    """PyShell standalone application."""
    
    def OnInit(self):
        locals = {'__app__': 'PyShell Standalone Application'}
        self.shellFrame = ShellFrame(locals=locals)#, InterpClass=Sim42Interpreter
        self.shellFrame.Show(true)
        self.SetTopWindow(self.shellFrame)
        # Add the application object to the sys module's namespace.
        # This allows a shell user to do:
        # >>> import sys
        # >>> sys.application.whatever
        import sys
        sys.application = self
        return true

class ShellInfoCallBack(object):
    def __init__(self, sim42interp):
        self.sim42interp = sim42interp
        self.language = guicmd.CommandInterface.MessageHandler.GetCurrentLanguage()
        self.languageDict = guicmd.CommandInterface.MessageHandler.GetLanguageDict(self.language)
        
    def SetLanguage(self, language):
        """
        change the rendering dictionary to correspond with language
        """
        try:
            newDict = guicmd.CommandInterface.MessageHandler.GetLanguageDict(language)
            if newDict:
                self.languageDict = newDict
                self.language = language
        except:
            pass
        
    def GetLanguageDict(self):
        return self.languageDict
    
    def GetLanguage(self):
        return self.language
    
    def handleMessage(self, message, args, msgType=None):
        """most basic of call backs"""
        if not guicmd.CommandInterface.MessageHandler.IsIgnored(message):
            self.sim42interp.stdout.write('%s\n' %
               (guicmd.CommandInterface.MessageHandler.RenderMessage(message, args)))        


def main():
    application = App(0)
    application.MainLoop()

if __name__ == '__main__':
    main()
    