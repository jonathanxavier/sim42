import sys, os

from wxPython.wx import *

from sim.cmd import CommandInterface
import guiThermoBuild
from SimGrids import MaterialPortFrame, EnergyPortFrame
from SimGrids import PropertyFrame, CompositionFrame
from Flowsheet import FlowsheetFrame
from sim.solver.Variables import *
from sim.unitop import *
from sim.solver import *
        
class guiCommandInterface(CommandInterface.CommandInterface):
    def __init__(self, baseFlowsheet=None, guiParent=None, infoCallBack=None):
        CommandInterface.CommandInterface.__init__(self, baseFlowsheet, infoCallBack)

        self.guiParent = guiParent
        self.frames = {}
        self.locals = {'thAdmin': self.root.GetThermoAdmin(), 'parentFlowsh': self.root}

    def Eval(self, rawCmd):
        """Dummy method for calling ProcessCommandString in case pre processing is needed"""
        
        #If there is a gui parent, then let it process the command on its own
        #this is wrong but works for now
        if self.guiParent and hasattr(self.guiParent, 'Eval'):
            self.guiParent.Eval(rawCmd)
        else:
            self.ProcessCommandString(rawCmd)
            
        for frame in self.frames.values():
            if hasattr(frame, 'UpdateView'):
                frame.UpdateView()            
            
        
    def View(self, objDesc):
        """Interactive wxPython view of an object"""
        currentObj = self.currentObj
        if not objDesc:
            obj = currentObj
        elif objDesc == '/':
            obj = self.root
        else:
            if objDesc[0] == '/':
                obj = currentObj = self.currentObj = self.root
                objDesc = objDesc[1:]
                
            if objDesc == '..' or objDesc[0:3] == '../':
                if hasattr(currentObj, 'GetParent'):
                    obj = currentObj.GetParent()
                else:
                    obj = None
                if obj == None:
                    obj = self.currentObj
                elif objDesc[0:3] == '../':
                    self.currentObj = obj
                    return self.Cd(objDesc[3:])
            else:
                obj = self.GetObject(currentObj, objDesc)


        #Create a wxProcess if not in one already 
        if not self.guiParent: app = MyApp(0)
        
        #Create a unique name        
        if hasattr(obj, 'GetPath'): name = obj.GetPath()
        else: name = 'frame' + str(len(self.frames))
        if name in self.frames.keys(): return
        
        #Create frame        
        frame = self.CreateFrame(obj)
        if not frame: return "Not view available for this object"
        self.frames[name] = frame
        frame.name = name
        
        #Show frame
        frame = self.frames[name]
        frame.Centre(wxBOTH)
        if not self.guiParent:
            app.SetTopWindow(frame)
            frame.Show(true)
            frame.Raise()                  
            app.MainLoop()
        else:
            frame.Show(true)
            frame.Raise()

    def CreateFrame(self, obj):
        """Try to create a frame according to the type of object"""
        if isinstance(obj, CommandInterface.Ports.Port_Material):
            return MaterialPortFrame(self.guiParent, sys.stdout, self, obj)
        
        if isinstance(obj, CommandInterface.Ports.Port_Energy):
            return EnergyPortFrame(self.guiParent, sys.stdout, self, obj)
        
        elif isinstance(obj, CommandInterface.ThermoCase):
            return guiThermoBuild.TestFrame(self.guiParent, sys.stdout, self, obj.provider, obj.case)
        
        elif isinstance(obj, CommandInterface.BasicProperty):
            return PropertyFrame(self.guiParent, sys.stdout, self, obj.GetParent())
        
        elif isinstance(obj, CommandInterface.CompoundList):
            return CompositionFrame(self.guiParent, sys.stdout, self, obj.GetParent())
        
        elif isinstance(obj, CommandInterface.MassCompoundList):
            return CompositionFrame(self.guiParent, sys.stdout, self, obj.GetParent())

        elif isinstance(obj, CommandInterface.Flowsheet.Flowsheet):
            return FlowsheetFrame(self.guiParent, sys.stdout, self, obj)

        elif isinstance(obj, CommandInterface.UnitOperations.UnitOperation):
            return FlowsheetFrame(self.guiParent, sys.stdout, self, obj, 1)
        
        else:
            return None

    def ProcessCommandString(self, rawCmd):
        """Gets a string with a command, process it and returns an output as string"""
        retVal = CommandInterface.CommandInterface.ProcessCommandString(self, rawCmd)
        try:
            for frame in self.frames.values():
                if hasattr(frame, 'UpdateView'):
                    frame.UpdateView()
        except:
            pass
        return retVal

    def Clear(self, desc):
        """reset the flowsheet to a new copy - argument is ignored"""
        for frame in self.frames.values():
            frame.Close()
        guiParent = self.guiParent
        frames = self.frames
        CommandInterface.CommandInterface.Clear(self, desc)
        self.guiParent = guiParent
        self.frames = frames
        self.locals = {'thAdmin': self.root.GetThermoAdmin(), 'parentFlowsh': self.root}

    #Dummy methods that simulate the behavior of the parent of PyCrust
    def CloseFrameNotify(self, frame):
        name = frame.name
        if name in self.frames.keys():
            del self.frames[name]

    def SendAndExecCode(self, code):
        self.locals.update({'thAdmin': self.root.GetThermoAdmin(), 'parentFlowsh': self.root})
        exec(code, globals(), self.locals)
        
        if self.GetAutoSolveStatus(): code = 'parentFlowsh.Solve()'
        else: code = 'parentFlowsh.SolverForget()'
        exec(code, globals(), self.locals)
        for frame in self.frames.values():
            if hasattr(frame, 'UpdateView'):
                frame.UpdateView()
            
    def GetParentFlowsh(self):
        return self.root

    def GetThAdmin(self):
        return self.root.GetThermoAdmin()

    def GetAutoSolveStatus(self):
        return not self.hold


CommandInterface.commands['view'] = guiCommandInterface.View
CommandInterface.commands['clear'] = guiCommandInterface.Clear

class MyApp(wxApp):
    def OnInit(self):
        """ Inherits from wxApp """
        return true

if __name__ == '__main__':
    CommandInterface.MessageHandler.IgnoreMessage('SolvingOp')
    interface = guiCommandInterface()
    while 1:
        try:
            interface.ProcessCommandStream(sys.stdin, sys.stdout, sys.stdout)
            break
        except CommandInterface.CallBackException, e:
            interface.infoCallBack.handleMessage('CMDCallBackException', str(e))
        except Exception, e:
            tb = ''
            for i in CommandInterface.traceback.format_tb(sys.exc_traceback):
                tb += i + '\n'
            interface.infoCallBack.handleMessage('CMDUnhandledError', (str(sys.exc_type), str(e), tb))

    interface.CleanUp()        
    