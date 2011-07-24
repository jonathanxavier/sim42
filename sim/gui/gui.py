"""Main GUI of the simulator

Classes:
wxSimulation -- Main frame where the simulation is created. Inh from wxFrame
wxEmptyPanel -- A panel with no info in it
MyApp --- Necessary to run a wxPython application

Functions:
main -- Runs the application

"""

import sys, os, string

from wxPython.lib import fancytext
from wxPython.wx import *

import SPyShell, SPyFilling
import guiThermoBuild
import guiPFD, MiscShapes, CustomTable


#Sim42 path will eventually be an environment variable
#For now, sim42 path should be one node above the gui folder
GUI_PATH = os.getcwd()
IMG_FOLDER = 'images'
IMG_PATH  = os.path.join(GUI_PATH, IMG_FOLDER)
from sim.solver.Variables import IN, OUT, MAT, ENE, SIG

##Eventually... code to administer the info in the following dictionaries could
##be implemented
#Orderofinfo: UONameInTree:(FileName,ClassName,GuiWrapperClassName,imageName)
createUOInfo = \
        {"Flash": ("Flash", "SimpleFlash", "guiUnitOperations", "flash.bmp"),
         "MixAndFlash": ("Flash", "MixAndFlash", "guiUnitOperations", "mixandflash.bmp"),
         "Mixer": ("Mixer", "Mixer", "guiUnitOperations", "mixer.bmp"),
         "Heater": ("Heater", "Heater", "guiUnitOperations", "heater.bmp"),
         "LiqLiqExt": ("LiqLiqExt", "LiqLiqEx", "guiUnitOperations", "liqliqext.bmp"),
         "DistColumn": ("DistCol", "SimpleDistCol", "guiUnitOperations", "distcol.bmp"),
        }
createStInfo = \
        {"MaterialStreams": ("Stream", "Stream_Material", "guiUnitOperations", "mstream.bmp"),
        "EnergyStreams": ("Stream", "Stream_Energy", "guiUnitOperations", "estream.bmp"),
        }


#Some id's used in the menus
ID_SAVE_HIST = wxNewId()
ID_SAVE_HISTAS = wxNewId()
ID_SOLVE = wxNewId()
ID_AUTOSOLVE = wxNewId()
ID_REFRESH = wxNewId()
ID_USE_CMD = wxNewId()
ID_VERB = wxNewId()
ID_RUN_CMD = wxNewId()
ID_AUTOCOMP = wxNewId()
ID_AUTOCOMP_SHOW = NewId()
ID_AUTOCOMP_INCLUDE_MAGIC = wxNewId()
ID_AUTOCOMP_INCLUDE_SINGLE = wxNewId()
ID_AUTOCOMP_INCLUDE_DOUBLE = wxNewId()
ID_CALLTIPS = wxNewId()
ID_CALLTIPS_SHOW = wxNewId()


class MainAppFrame(wxFrame):
    """Main frame of the simulator"""

    def __init__(self, parent, id, title):      
        wxFrame.__init__(self, parent, -1, title, size=(800, 600),
                         style=wxDEFAULT_FRAME_STYLE)

        self.autoSolve = true
        self.customTables = {}
        self.simFilePath = None
        self.histFilePath = None

        fileName = os.path.join(IMG_PATH, 'sim42.ico')
        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
        self.SetIcon(icon)
        
        if wxPlatform == '__WXMSW__':
            # setup a taskbar icon, and catch some events from it
            self.tbicon = wxTaskBarIcon()
            self.tbicon.SetIcon(icon, "Sim42")
            EVT_TASKBAR_LEFT_DCLICK(self.tbicon, self.OnTaskBarActivate)
            EVT_TASKBAR_RIGHT_UP(self.tbicon, self.OnTaskBarMenu)
            EVT_MENU(self.tbicon, self.TBMENU_RESTORE, self.OnTaskBarActivate)
            EVT_MENU(self.tbicon, self.TBMENU_CLOSE, self.OnTaskBarClose)

        self.otherWin = None
        EVT_IDLE(self, self.OnIdle)
        EVT_CLOSE(self, self.OnCloseWindow)

        self.Centre(wxBOTH)
        self.CreateStatusBar(1, wxST_SIZEGRIP)

        splitter = wxSplitterWindow(self, -1, style=wxNO_3D|wxSP_3D)
        self.splitter2 = wxSplitterWindow(splitter, -1, style=wxNO_3D|wxSP_3D)

        # Prevent TreeCtrl from displaying all items after destruction
        self.dying = false

        self.CreateMenus()

        # Create a TreeCtrl
        tID = wxNewId()
        self.tree = wxTreeCtrl(splitter, tID, style=wxTR_HAS_BUTTONS |
                               wxTR_HAS_VARIABLE_ROW_HEIGHT |
                               wxSUNKEN_BORDER)
        self.root = self.tree.AddRoot("Simulation")
        EVT_TREE_ITEM_ACTIVATED (self.tree, tID, self.OnSelectNode)

        # Create a Notebook
        self.nb = wxNotebook(self.splitter2, -1)

        # Set up a canvas for the flowsheet
        self.pfd = guiPFD.pfd(self.nb, self)
        self.nb.AddPage(self.pfd, "Simulation")
        
        #Set interactive python shell
        self.sPyShell = SPyShell.Sim42Shell(self.nb)
        self.nb.AddPage(self.sPyShell, "Interactive Interpreter")

        # Set up a TextCtrl to show the namespace info
        self.sPyFilling = SPyFilling.SPyFilling(self.nb,
                                    ingredients=self.GetInterpreterLocals())
        self.nb.AddPage(self.sPyFilling, "Namespace Navigator")

        self.paramPanel = wxEmptyPanel(self.splitter2)
        self.Show(true)
        self.splitter2.SplitHorizontally(self.nb, self.paramPanel)
        splitter.SplitVertically(self.tree, self.splitter2)
        self.splitter2.SetMinimumPaneSize(100)
        splitter.SetMinimumPaneSize(20)
        splitter.SetSashPosition(180, true)
        w, h = self.GetSizeTuple()
        self.splitter2.SetSashPosition(h/2, true)

        self.nb.SetSelection(0)
        self.tree.SelectItem(self.root)
        
        self.InitAnEmptySimulation()

        #Load nodes to the tree
        self.ndeTh = self.tree.AppendItem(self.root, "Thermodynamics")
        self.tree.EnsureVisible(self.ndeTh)
        self.ndeUOp = self.tree.AppendItem(self.root, "UnitOperations")
        self.ndeSt = self.tree.AppendItem(self.root, "Streams")
        self.ndeCustTab = self.tree.AppendItem(self.root, "CustomTables")
        
        self.UpdateSimulationView()
        self.nb.Refresh()

        #Add support for switching to cmd interface
        self.origInterp = self.sPyShell.interp
        #Make sure both interpreters have same stdin and stdout
        stdin = self.origInterp.stdin
        stdout = self.origInterp.stdout
        stderr = self.origInterp.stderr
        loc = self.GetInterpreterLocals()
        loc['guiParent'] = self
        self.sim42interp = SPyShell.Sim42Interpreter(loc, stdin, stdout, stderr)


    def CreateMenus(self):
        """Create the main menu of the simulator"""

        # Make a File menu
        m = fileMenu = wxMenu()
        m.Append(wxID_NEW, '&New \tCtrl+N', 'New Simulation')
        m.Append(wxID_OPEN, '&Open \tCtrl+O', 'Open Existing Simulation')
        m.AppendSeparator()
        m.Append(ID_RUN_CMD, '&Run Command Script...', 'Read a file with command interface instructions')
        m.AppendSeparator()
        m.Append(wxID_SAVE, 'Sa&ve \tCtrl+S', 'Save')
        m.Append(wxID_SAVEAS, 'Sav&e As...', 'Save simulatation as...')
        m.AppendSeparator()
        m.Append(ID_SAVE_HIST, 'Save &History', 'Save history of commands')
        m.Append(ID_SAVE_HISTAS, 'Save H&istory As...', 'Save history of commands as...')
        m.AppendSeparator()        
        m.Append(wxID_EXIT, 'E&xit \tCtrlQ', 'Adios!')

        # Make an Edit menu
        m = editMenu = wxMenu()
        m.Append(wxID_UNDO, '&Undo \tCtrl+Z', 'Undo the last action')
        m.Append(wxID_REDO, '&Redo \tCtrl+Y', 'Redo the last undone action')
        m.AppendSeparator()
        m.Append(wxID_CUT, 'Cu&t \tCtrl+X', 'Cut the selection')
        m.Append(wxID_COPY, '&Copy \tCtrl+C', 'Copy the selection')
        m.Append(wxID_PASTE, '&Paste \tCtrl+V', 'Paste')

        #Make a tools menu
        m = toolsMenu = wxMenu()
        m.Append(ID_SOLVE, '&Solve \tCtrl-L', 'Solve the Simulation')
        m.Append(ID_AUTOSOLVE, '&Auto Solve', 'Automatically solve the simulation after a change', true)
        m.Check(ID_AUTOSOLVE, self.autoSolve)
        m.AppendSeparator()
        m.Append(ID_REFRESH, '&Refresh View \tCtrl+R', 'Refreshes the gui with the latest info of the simulation')
        

        #Make an interpreter menu
        m = autocompMenu = wxMenu()
        m.Append(ID_AUTOCOMP_SHOW, 'Show Auto Completion','Show auto completion during dot syntax', 1)
        m.Append(ID_AUTOCOMP_INCLUDE_MAGIC, 'Include Magic Attributes', 'Include attributes visible to __getattr__ and __setattr__', 1)
        m.Append(ID_AUTOCOMP_INCLUDE_SINGLE, 'Include Single Underscores', 'Include attibutes prefixed by a single underscore', 1)
        m.Append(ID_AUTOCOMP_INCLUDE_DOUBLE, 'Include Double Underscores', 'Include attibutes prefixed by a double underscore', 1)

        m = calltipsMenu = wxMenu()
        m.Append(ID_CALLTIPS_SHOW, 'Show Call Tips', 'Show call tips with argument specifications', 1)

        m = interpMenu = wxMenu()
        m.Append(ID_USE_CMD, '&Active Cmd. Interface \tCtrl+F', 'Use the command interface as editor', true)
        m.Append(ID_VERB, '&Verbose', 'Display call back info to the shell', 1)
        m.AppendSeparator()        
        m.AppendMenu(ID_AUTOCOMP, '&Auto Completion', autocompMenu, 'Auto Completion Options')
        m.AppendMenu(ID_CALLTIPS, '&Call Tips', calltipsMenu, 'Call Tip Options')
        
        
        # Make a Help menu
        m = helpMenu = wxMenu()
        m.Append(wxID_ABOUT, '&About... ', 'About Sim42')

        #Putting everything together
        b = menuBar = wxMenuBar()
        b.Append(fileMenu, '&File')
        b.Append(editMenu, '&Edit')
        b.Append(toolsMenu, '&Tools')
        b.Append(interpMenu, '&Interpreter')
        b.Append(helpMenu, '&Help')
        self.SetMenuBar(b)
        
        
        #Event handling
        EVT_MENU(self, wxID_NEW, self.OnFileNew)   
        EVT_MENU(self, wxID_OPEN, self.OnFileOpen)
        EVT_MENU(self, ID_RUN_CMD, self.OnFileRunCmdFile)
        EVT_MENU(self, wxID_SAVE, self.OnFileSave)   
        EVT_MENU(self, wxID_SAVEAS, self.OnFileSaveAs)
        EVT_MENU(self, ID_SAVE_HIST, self.OnFileSaveHist)
        EVT_MENU(self, ID_SAVE_HISTAS, self.OnFileSaveHistAs)
        EVT_MENU(self, wxID_EXIT, self.OnFileExit)

        EVT_MENU(self, wxID_UNDO, self.OnEditUndo)
        EVT_MENU(self, wxID_REDO, self.OnEditRedo)
        EVT_MENU(self, wxID_CUT, self.OnEditCut)
        EVT_MENU(self, wxID_COPY, self.OnEditCopy)
        EVT_MENU(self, wxID_PASTE, self.OnEditPaste)

        EVT_MENU(self, ID_SOLVE, self.OnToolsSolve)
        EVT_MENU(self, ID_AUTOSOLVE, self.OnToolsAutoSolve)
        EVT_MENU(self, ID_REFRESH, self.OnToolsRefreshView)
        
        EVT_MENU(self, ID_USE_CMD, self.OnInterpChangeInterpreter)
        EVT_MENU(self, ID_VERB, self.OnInterpVerbose)
        EVT_MENU(self, ID_AUTOCOMP_SHOW,self.OnInterpAutoCompleteShow)
        EVT_MENU(self, ID_AUTOCOMP_INCLUDE_MAGIC,self.OnInterpAutoCompleteIncludeMagic)
        EVT_MENU(self, ID_AUTOCOMP_INCLUDE_SINGLE,self.OnInterpAutoCompleteIncludeSingle)
        EVT_MENU(self, ID_AUTOCOMP_INCLUDE_DOUBLE,self.OnInterpAutoCompleteIncludeDouble)
        EVT_MENU(self, ID_CALLTIPS_SHOW,self.OnInterpCallTipsShow)
        
        EVT_MENU(self, wxID_ABOUT, self.OnHelpAbout)

        EVT_UPDATE_UI(self, ID_AUTOSOLVE, self.OnUpdateMenu)
        EVT_UPDATE_UI(self, ID_USE_CMD, self.OnUpdateMenu)
        EVT_UPDATE_UI(self, ID_AUTOCOMP_SHOW, self.OnUpdateMenu)
        EVT_UPDATE_UI(self, ID_AUTOCOMP_INCLUDE_MAGIC, self.OnUpdateMenu)
        EVT_UPDATE_UI(self, ID_AUTOCOMP_INCLUDE_SINGLE, self.OnUpdateMenu)
        EVT_UPDATE_UI(self, ID_AUTOCOMP_INCLUDE_DOUBLE, self.OnUpdateMenu)
        EVT_UPDATE_UI(self, ID_CALLTIPS_SHOW, self.OnUpdateMenu)

    def OnSelectNode(self, event):
        """Called when a node in the tree is selected"""
        if self.dying:
            return
        item = event.GetItem()
        self.UpdateSimulationFromNodeSelect(item)

    def UpdateSimulationView(self):
        """Update the view of the GUI depending on the info of the simulator"""
        self.UpdateThView()
        self.UpdateUOView()

    def UpdateThView(self):
        """Update the thermo part of the tree"""
        #Delete
        cookie = 10
        nuCh = self.tree.GetChildrenCount(self.ndeTh, false)
        itemList = []
        for i in range(nuCh):
            if i == 0:
                item, cookie = self.tree.GetFirstChild(self.ndeTh, cookie)
            else: item, cookie = self.tree.GetNextChild(self.ndeTh, cookie)
            itemList.append(item)
        for i in range(len(itemList)): self.tree.Delete(itemList[i])

        #Load providers and th Cases
        thAdmin = self.GetThAdmin()
        providers = thAdmin.GetAvThermoProviderNames()
        for i in providers:
            chNdeProv = self.tree.AppendItem(self.ndeTh, i)
            for j in thAdmin.GetAvThCaseNames(i):
                chNdeTh = self.tree.AppendItem(chNdeProv, j)
        if len(providers): self.tree.EnsureVisible(chNdeProv)

    def UpdateUOView(self):
        """Update the canvas and the uo part of the tree"""
        #Clean canvas
        canvas = self.pfd
        dc = wxClientDC(canvas)
        canvas.PrepareDC(dc)
        redraw = false
        shapeList = canvas.GetDiagram().GetShapeList()
        toUnselect = []
        for s in shapeList:
            if s.Selected():
                toUnselect.append(s)
        if toUnselect:
            for s in toUnselect:
                s.Select(false, dc)
            canvas.Redraw(dc)
        for i in canvas.lines.keys():
            line = canvas.lines[i]
            line.Unlink()
            canvas.RemoveShape(line)
            del canvas.lines[i]
            line.Destroy()       
        for i in canvas.imgsUO.keys():
            shape = canvas.imgsUO[i]
            canvas.RemoveShape(shape)
            del canvas.imgsUO[i]
            shape.Destroy()
        canvas.Refresh()
        
        #Delete UOs from tree
##      Deleting nodes in a tree shouldn't be this hard (too many lines)!!!!
        cookie = 10
        nuCh = self.tree.GetChildrenCount(self.ndeUOp, false)
        itemList = []
        for i in range(nuCh):
            if i == 0:
                item, cookie = self.tree.GetFirstChild(self.ndeUOp, cookie)
            else: item, cookie = self.tree.GetNextChild(self.ndeUOp, cookie)
            itemList.append(item)
        for i in range(len(itemList)): self.tree.Delete(itemList[i])

        #Delete streams from tree
        cookie = 11
        nuCh = self.tree.GetChildrenCount(self.ndeSt, false)
        itemList = []
        for i in range(nuCh):
            if i == 0:
                item, cookie = self.tree.GetFirstChild(self.ndeSt, cookie)
            else: item, cookie = self.tree.GetNextChild(self.ndeSt, cookie)
            itemList.append(item)
        for i in range(len(itemList)): self.tree.Delete(itemList[i])

        #Load nodes
##      Weird and long code, but good enough for now
        parentFlowsh = self.GetParentFlowsh()
        uOps = parentFlowsh.GetChildUnitOps()
        glob = self.GetInterpreterGlobals()
        loc = self.GetInterpreterLocals()
        loc['uOps'] = uOps
        for i in createUOInfo.items():
            ndeChUOp = self.tree.AppendItem(self.ndeUOp, i[0])
            instance = i[1][0] + '.' + i[1][1]
            for j in range(len(uOps)):
                if eval('isinstance(uOps[' + str(j) + '][1], ' + instance + \
                        ')', glob, loc):
                    nde = self.tree.AppendItem(ndeChUOp, uOps[j][0])
                    self.AddToPfd(uOps[j][0], i[0], IMG_PATH + i[1][3])
        for i in createStInfo.items():
            ndeChSt= self.tree.AppendItem(self.ndeSt, i[0])
            instance = i[1][0] + '.' + i[1][1]
            for j in range(len(uOps)):
                if eval('isinstance(uOps[' + str(j) + '][1], ' + instance + \
                        ')', glob, loc):
                    nde = self.tree.AppendItem(ndeChSt, uOps[j][0])
                    self.AddToPfd(uOps[j][0], i[0], IMG_PATH + i[1][3])
        #Clean up locals
        del loc['uOps']

        #Update connections - don't want outlet or will get duplicates
        conns = parentFlowsh.GetAllChildConnections(IN|MAT)
        for i in conns:
            lineName = string.join(i, '-')
            self.pfd.MyAddLine(wxBLACK_PEN, wxBLACK_BRUSH, '', i[0], i[2],
                               lineName)
        conns = parentFlowsh.GetAllChildConnections(IN|ENE)
        for i in conns:
            lineName = string.join(i, '-')
            self.pfd.MyAddLine(wxBLACK_PEN, wxBLACK_BRUSH, '', i[0], i[2],
                               lineName)
        
    def UpdateSimulationFromNodeSelect(self, item):
        """Do whatever needed to the simulation after a node is selected"""
        itemText = self.tree.GetItemText(item)
        os.chdir(GUI_PATH)

        parentItem = self.tree.GetItemParent(item)
        parentText = self.tree.GetItemText(parentItem)
        granpaText = None
        if self.root != parentItem:
            granpaText = self.tree.GetItemText(self.tree.GetItemParent(parentItem))

        #If within thermo node...........
        thAdmin = self.GetThAdmin()
        parentFlowsh = self.GetParentFlowsh()        
        if itemText == 'Thermodynamics':
            pass #perhaps, add another thermo servers
        elif parentText == 'Thermodynamics':
            title = 'Add Thermo Case --> ' + itemText
            defName = 'thCase'
            invalidNames = thAdmin.GetAvThCaseNames(itemText)
            name = self.CreateNewName(title, defName, invalidNames)
            if not name: return
            self.tree.AppendItem(item, name)
            win = guiThermoBuild.BuildThermo(self, self, itemText, name)
            
            #Add a default thermo case to the flowsheet if needed
            if not parentFlowsh.GetThermo():
                thNames = thAdmin.GetAvThCaseNames(itemText)
                if len(thNames) > 0:
                    propPkg = thAdmin.GetPropPkgString(itemText, thNames[0])
                    code = 'thCaseObj = ThermoAdmin.ThermoCase(thAdmin, "' + itemText + '", "'
                    code += thNames[0] + '", "' + propPkg + '")'
                    self.SendAndExecCode(code)
                    
                    code = 'parentFlowsh.SetThermo(thCaseObj)'
                    self.SendAndExecCode(code)

                    code = 'del thCaseObj'
                    self.SendAndExecCode(code)
            self.ChangeActiveParamPanel(None, None)
            
        elif granpaText == 'Thermodynamics':
            win = guiThermoBuild.BuildThermo(self, self, parentText, itemText)
            self.ChangeActiveParamPanel(None, None)
        #If within uo node...........  
        elif itemText == 'UnitOperations':
            #perhaps, add another UOp
            pass
        elif parentText == 'UnitOperations' or parentText == 'Streams':
            title = 'Add New Unit --> ' + itemText
            defName = 'my' + itemText
            invalidNames = parentFlowsh.GetChildUONames()
            name = self.CreateNewName(title, defName, invalidNames)
            if not name: return
            self.tree.AppendItem(item, name)
            if createUOInfo.has_key(itemText):
                modName = createUOInfo[itemText][0]
                className = createUOInfo[itemText][1]
                bmpPath = os.path.join(IMG_PATH, createUOInfo[itemText][3])
            elif createStInfo.has_key(itemText):
                modName = createStInfo[itemText][0]
                className = createStInfo[itemText][1]
                bmpPath = os.path.join(IMG_PATH, createStInfo[itemText][3])
            else: return
            #Module should have been imported before
            code = 'uOp = ' + modName + '.' + className + '()'
            self.SendAndExecCode(code)
            code = 'parentFlowsh.AddUnitOperation(uOp, "' + name + '")'
            self.SendAndExecCode(code)

            #Don't leave any dandling variables even though a clean up
            #function might still be implemented
            code = 'del uOp'
            self.SendAndExecCode(code)

            self.AddToPfd(name, itemText, bmpPath)
            shape = self.pfd.imgsUO[name]
            shape.SelectShape()
            self.ChangeActiveParamPanel(name, itemText)
            
        elif granpaText == 'UnitOperations' or granpaText == 'Streams':
            shape = self.pfd.imgsUO[itemText]
            shape.SelectShape()
            self.ChangeActiveParamPanel(itemText, shape.type)
            
        #If within CustomTables node...........  
        elif itemText == 'CustomTables':
            title = 'Add New Custom Table'
            defName = 'myTable'
            invalidNames = self.customTables.keys()
            name = self.CreateNewName(title, defName, invalidNames)
            if not name: return
            self.tree.AppendItem(item, name)
            self.customTables[name] = CustomTable.CustomTableInfo()
            self.ChangeActiveParamPanel(name, None, true)
        elif parentText == 'CustomTables':
            self.ChangeActiveParamPanel(itemText, None, true)

    def IsValidName(self, name, invalidNames):
        #Function just in case a more robust validation is needed
        """Validate a name to be different from names in a list"""
        if name in invalidNames: return false
        if name == '': return false
        return true
        
    def CreateNewName(self, title, defName, invalidNames):
        """Creates a new name different from names in a list"""
        valid = false
        dlgTxt = 'Name'
        while not valid:
            dlg = wxTextEntryDialog(self, dlgTxt, title,
                                    defName + str(len(invalidNames) + 1))
            if dlg.ShowModal() == wxID_OK:
                name = dlg.GetValue()
                name = string.strip(name)
                valid = self.IsValidName(name, invalidNames)
                if not valid:
                    dlgTxt = 'Invalid name, use another one'
                    name = None
            else:
                valid = true
                name = None
            dlg.Destroy()
        return name

    def AddToPfd(self, name, type, bmpPath):
        """Add a uo to the canvas"""
        bmp = wxBitmap(bmpPath, wxBITMAP_TYPE_BMP)
        s = MiscShapes.UnitOperationShape(name, type)        
        s.SetBitmap(bmp)
        self.pfd.MyAddShape(s, 100, 100, None, None, name, name)

    def ChangeActiveParamPanel(self, uOpName, uOpType, isCustTable=false):
        """Change the active panel for changing uo settings"""
        oldPanel = self.paramPanel
        if isCustTable:
            self.paramPanel = CustomTable.CustomTable(self.splitter2, self,
                                                      self.customTables[uOpName])
        elif not uOpName:
            self.paramPanel = wxEmptyPanel(self.splitter2)
        else:
            try:
                if createUOInfo.has_key(uOpType): modName = createUOInfo[uOpType][2]
                elif createStInfo.has_key(uOpType): modName = createStInfo[uOpType][2]
                module = __import__(modName, globals())
                uOp = self.GetParentFlowsh().GetChildUO(uOpName)
                self.paramPanel = module.UOWrapperPanel(self.splitter2, self, uOp, self.pfd)
            except:
                self.paramPanel = wxEmptyPanel(self.splitter2)
        self.splitter2.ReplaceWindow(oldPanel, self.paramPanel)
        
        self.nb.Refresh()

    #---------------------------------------------
    # Menu methods

    def OnFileNew(self, event):
        """New simulation"""
        self.ChangeActiveParamPanel(None, None)
        self.CloseFileAndCleanUpShell()
        self.InitAnEmptySimulation()
        self.UpdateSimulationView()

    def OnFileOpen(self, event):
        """Open a simulation"""
        path = self.PromptPathOpenSim()
        if not path: return
        self.Open(path)
        self.UpdateSimulationView()

    def OnFileRunCmdFile(self, event):
        """Run command interface file"""
        path = self.PromptPathOpenCmd()
        if not path: return
        self.RunCmdFile(path)
        
    def OnFileSave(self, event):
        """Save a simulation"""
        self.Save()        
    
    def OnFileSaveAs(self, event):
        """Save simulation as..."""
        path = self.PromptPathSaveAs()
        if not path: return
        else: self.simFilePath = path
        self.Save()
        
    def OnFileSaveHist(self, event):
        """Saves history"""
        self.SaveHistory()
    
    def OnFileSaveHistAs(self, event):
        """Save history as..."""
        path = self.PromptPathSaveHistAs()
        if not path: return
        else: self.histFilePath = path
        self.SaveHistory()
    
    def OnFileExit(self, event):
        """Exit"""
        self.Close()

    def OnEditUndo(self, event): pass
    def OnEditRedo(self, event): pass        
    def OnEditCut(self, event): pass
    def OnEditCopy(self, event): pass   
    def OnEditPaste(self, event): pass

    def OnToolsSolve(self, event):
        """Solve the flowsheet"""
        self.Solve()
        
    def OnToolsAutoSolve(self, event):
        """Auto solve selected"""
        self.autoSolve = event.IsChecked()
        
    def OnToolsRefreshView(self, event): 
        """Refreshes the view of the simulator with the latest info"""
        self.UpdateSimulationView()


    def OnInterpChangeInterpreter(self, event):
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
            self.sPyShell.run("print '*************** Changed to Sim42 Command Interface ***************' ", prompt=0, verbose=0)
                
            #Change
            self.sPyShell.interp = self.sim42interp

        else:
            #change prompt
            sys.ps1 = '>>> '
            sys.ps2 = '... '

            #Change
            self.sPyShell.interp = self.origInterp    
            
            #Say hello
            self.sPyShell.run("print '*************** Back to python ***************' ", prompt=0, verbose=0)
            

        self.sPyShell.autoCompleteKeys = self.sPyShell.interp.getAutoCompleteKeys()

    def OnInterpVerbose(self, event):
        """Display call back info in the shell"""
        self.verbose = event.IsChecked()
        if self.verbose:
            cb = ShellInfoCallBack()
            self.sim42interp.cmd.SetInfoCallBack(cb)
        else:
            self.sim42interp.cmd.SetInfoCallBack(SPyShell.guicmd.CommandInterface.infoCallBack)
    
    def SaveHistory(self):
        """Saves history to a file"""
        if not self.histFilePath:
            path = self.PromptPathSaveHistAs()
            if not path: return
            else: self.histFilePath = path
            
        f = open(self.histFilePath, 'w')
        size = len(self.shell.history)
        for idx in range(size-1, -1, -1):
            f.write(self.sPyShell.history[idx] + os.linesep)
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

    def PromptPathOpenCmd(self):
        """Propmts for a path for opening a command interface file"""
        defaultPath = "."
        defaultName = ""
            
        dlgSave = wxFileDialog(self, "Run Command File", defaultPath, defaultName,
                               "*.tst|*.*", wxOPEN|wxCHANGE_DIR)
        if dlgSave.ShowModal() == wxID_OK:
            path = dlgSave.GetPath()
        else:
            path = None
        dlgSave.Destroy()
        return path

    def PromptPathOpenSim(self):
        """Propmts for a path for opening a command interface file"""
        defaultPath = "."
        defaultName = ""
            
        dlgSave = wxFileDialog(self, "Open Simulation", defaultPath, defaultName,
                               "*.sft|*.*", wxOPEN|wxCHANGE_DIR)
        if dlgSave.ShowModal() == wxID_OK:
            path = dlgSave.GetPath()
        else:
            path = None
        dlgSave.Destroy()
        return path

    def RunCmdFile(self, path):
        """Run command interface file"""
        if not self.sim42interp == self.sPyShell.interp:
            self.UseCommandInterface(true)
        self.sPyShell.run("read " + path, prompt=0, verbose=0)
    
    def OnInterpAutoCompleteShow(self, event):
        self.sPyShell.autoComplete = event.IsChecked()

    def OnInterpAutoCompleteIncludeMagic(self, event):
        self.sPyShell.autoCompleteIncludeMagic = event.IsChecked()

    def OnInterpAutoCompleteIncludeSingle(self, event):
        self.sPyShell.autoCompleteIncludeSingle = event.IsChecked()

    def OnInterpAutoCompleteIncludeDouble(self, event):
        self.sPyShell.autoCompleteIncludeDouble = event.IsChecked()

    def OnInterpCallTipsShow(self, event):
        self.sPyShell.autoCallTip = event.IsChecked()

        
    def OnHelpAbout(self, event):
        """About sim42"""
        title = 'About Sim42'
        text = 'Sim42 version %s\n\n' % self.GetParentFlowsh().VERSION + \
               'Open source process simulator \n\n' + \
               'Python Version: %s\n' % sys.version.split()[0] + \
               'wxPython Version: %s\n' % wx.__version__ + \
               'Platform: %s\n' % sys.platform               

        dialog = wxMessageDialog(self, text, title, wxOK | wxICON_INFORMATION)
        dialog.ShowModal()
        dialog.Destroy()

    def OnUpdateMenu(self, event):
        """Update menu items based on current status."""
        id = event.GetId()
        if id == ID_AUTOSOLVE:
            event.Check(self.autoSolve)
        elif id == ID_USE_CMD:
            event.Check(self.sim42interp == self.sPyShell.interp)
        elif id == ID_AUTOCOMP_SHOW:
            event.Check(self.sPyShell.autoComplete)
        elif id == ID_AUTOCOMP_INCLUDE_MAGIC:
            event.Check(self.sPyShell.autoCompleteIncludeMagic)
        elif id == ID_AUTOCOMP_INCLUDE_SINGLE:
            event.Check(self.sPyShell.autoCompleteIncludeSingle)
        elif id == ID_AUTOCOMP_INCLUDE_DOUBLE:
            event.Check(self.sPyShell.autoCompleteIncludeDouble)
        elif id == ID_CALLTIPS_SHOW:
            event.Check(self.sPyShell.autoCallTip)

    def Solve(self):
        code = 'parentFlowsh.Solve()'
        self.SendAndExecCode(code)
        self.paramPanel.UpdateView()
        
    def Forget(self):
        code = 'parentFlowsh.SolverForget()'
        self.SendAndExecCode(code)
        self.paramPanel.UpdateView()

    def GetAutoSolveStatus(self):
        return self.autoSolve
    
    #---------------------------------------------
    def OnIdle(self, event):
        if self.otherWin:
            self.otherWin.Raise()
            self.window = self.otherWin
            self.otherWin = None

    #---------------------------------------------
    def OnTaskBarActivate(self, evt):
        if self.IsIconized():
            self.Iconize(false)
        if not self.IsShown():
            self.Show(true)
        self.Raise()

    #---------------------------------------------

    TBMENU_RESTORE = 1000
    TBMENU_CLOSE   = 1001

    def OnTaskBarMenu(self, evt):
        menu = wxMenu()
        menu.Append(self.TBMENU_RESTORE, "Restore Simulation")
        menu.Append(self.TBMENU_CLOSE,   "Close")
        self.tbicon.PopupMenu(menu)
        menu.Destroy()

    #---------------------------------------------
    def OnTaskBarClose(self, evt):
        self.Close()
        # because of the way wxTaskBarIcon.PopupMenu is implemented we have to
        # prod the main idle handler a bit to get the window to actually close
        wxGetApp().ProcessIdle()

    #---------------------------------------------
    def OnCloseWindow(self, event):
        """Before closing, prompts to save the simulation"""

        #Propmt to save to a new file
        msg = "Do you want to save the simulation?"
        title = "Save Simulation"
        answer = wxMessageBox(msg, title, wxYES_NO | wxCANCEL);
        if answer == wxCANCEL: return
        if answer == wxYES: self.Save()
        self.CloseSimulator()

    def CloseSimulator(self, event=None): #event is optional so it can be hooked directly to an event
        """Close the simulation. Performs all the required cleanup beforhand"""
        #Avoid the crash in windows for the lost focus thing
        win = wxWindow_FindFocus() 
        if win != None: win.Disconnect(-1, -1, wxEVT_KILL_FOCUS)
        
        #make sure the param panel is killed
        self.ChangeActiveParamPanel(None, None)
        
        self.CloseFileAndCleanUpShell()
        self.dying = true
        self.window = None
        self.mainmenu = None
        if hasattr(self, "tbicon"): del self.tbicon
        del self.pfd
        self.Destroy()

    def CloseFileAndCleanUpShell(self):
        """Delete the simulation variables, the shell has been working with"""
        code = 'parentFlowsh.CleanUp()'
        self.SendAndExecCode(code)
        code = 'thAdmin.CleanUp()'
        self.SendAndExecCode(code)
        code = 'del locals()["thAdmin"]'
        self.SendAndExecCode(code)
        code = 'del locals()["parentFlowsh"]'
        self.SendAndExecCode(code)
        self.sim42interp.CleanUp()
        self.sPyShell.ClearOutput()

    def InitAnEmptySimulation(self):
        """Init an empty simulation"""
        self.SetTitle('Simulation --> ' + str(self.simFilePath))     
        #Import necesary files in interpreter
##      This code could be a lot better
        code = 'from sim.thermo import ThermoAdmin'
        self.SendAndExecCode(code)
        code = 'from sim.solver import Flowsheet'
        self.SendAndExecCode(code)
        for i in createUOInfo.values():
            code = 'from sim.unitop import ' + i[0]
            self.SendAndExecCode(code)
        for i in createStInfo.values():
            code = 'from sim.unitop import ' + i[0]
            self.SendAndExecCode(code)

        #Create the two main objects for the simulation...
        code = 'thAdmin = ThermoAdmin.ThermoAdmin()'
        self.SendAndExecCode(code)
        code = 'parentFlowsh = Flowsheet.Flowsheet()'
        self.SendAndExecCode(code)
        code = 'parentFlowsh.SetThermoAdmin(thAdmin)'
        self.SendAndExecCode(code)

        #Clear paths and shell history
        self.simFilePath = self.histFilePath = None
        self.sPyShell.history = []
        self.sPyShell.historyIndex = -1

    def Open(self, path):
        """Opens a simulation"""

        self.CloseFileAndCleanUpShell()
       
        #Why bother doing new code if the cmd interface does it already
        self.sim42interp.cmd.Recall(path)
        #Calling the cmd interface originates the needs for the next call
        self.UpdateLocalsFromCmd()

        self.SetTitle('Simulation --> ' + path)
        self.simFilePath = path
        
    def UpdateLocalsFromCmd(self):
        """Makes sure the locals dictionary has the current thAdmin and baseFlowsh from cmd interface"""
        self.origInterp.locals["parentFlowsh"] = self.sim42interp.cmd.root
        self.origInterp.locals["thAdmin"] = self.sim42interp.cmd.thermoAdmin

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
        self.sim42interp.cmd.Store(self.simFilePath)

        self.SetTitle('Simulation --> ' + self.simFilePath)
        
    def SendAndExecCode(self, code):
        """Writes a command to the interpreter"""
        try:
            if self.sim42interp == self.sPyShell.interp:
                self.UseCommandInterface(false)        
        finally:
            return self.sPyShell.ExecFromTextInput(code)  

    def GetInterpreterGlobals(self):
        """Pass the interpreter's globals"""
        return self.sPyShell.GetGlobals()

    def GetInterpreterLocals(self):
        """Pass the interpreter's locals"""        
        return self.sPyShell.GetLocals()

    def GetThAdmin(self):
        """Pass the instance of the thermo admin used by the interperter"""  
        sLocals = self.GetInterpreterLocals()
        return sLocals['thAdmin']

    def GetParentFlowsh(self):
        """Pass the instance of the flowsheet used by the interperter""" 
        sLocals = self.GetInterpreterLocals()
        return sLocals['parentFlowsh']

class wxEmptyPanel(wxScrolledWindow):
    """Empty panel used when none uo is selected"""
    def __init__(self, parent, id=-1):
        wxScrolledWindow.__init__(self, parent, id, size=wxDefaultSize)
        
        maxW = 1000
        maxH = 1000
        self.SetScrollbars(20, 20, maxW/20, maxH/20)

        self.txt = '<font family="swiss" color="black" size="24">'
        self.txt += "SIM42, "
        self.txt += '</font>'

        self.txt2 = '<font family="swiss" color="black" size="15">'
        self.txt2 += "not quite there yet....!!!"
        self.txt2 += '</font>'

        EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, evt):
        dc = wxPaintDC(self)
        fancytext.renderToDC(self.txt, dc, 50, 50)
        fancytext.renderToDC(self.txt2, dc, 50, 105)

    def UpdateView(self):
        pass

class MyApp(wxApp):
    def OnInit(self):
        frame = MainAppFrame(None, -1, "Sim42")
        frame.Show(true)
        self.SetTopWindow(frame)
        import sys
        sys.application = self
        return true

class ShellInfoCallBack(object):
    """
    call back object with at least a handleMessage method
    """
    def handleMessage(self, message, args, msgType=None):
        """most basic of call backs"""
        if not SPyShell.guicmd.CommandInterface.MessageHandler.IsIgnored(message):
            self.sim42interp.stdout.write('%s\n' %
               (SPyShell.guicmd.CommandInterface.MessageHandler.RenderMessage(message, args)))        

def main():
    try:
        currentPath = os.path.split(__file__)[0]
        os.chdir(currentPath)
    except:
        pass
    app = MyApp(0)
    app.MainLoop()

if __name__ == '__main__':
    main()
    