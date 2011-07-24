"""Creates a frame for creating or updating a thermo case
        
Classes:
ThermoSelPanel -- Panel to select cmps and pkgs
IPSelPanel -- Panel for IPs
FlashSelPanel -- Panel for flash settings
MyFrame -- Main frame

Functions:
BuildThermo -- Returns an instance of MyFrame

"""

##import win32com.client
from wxPython.wx import *
from wxPython.grid import *

import string, os

import ComponentSelection
from ThermoPanels import ThermoSelection, IPSelection, FlashSelection
import GridEditors, GridRenderers
from sim.thermo.ThermoConstants import *
from sim.solver.Variables import *


GUI_PATH = os.getcwd()
IMG_FOLDER = 'images'
IMG_PATH  = os.path.join(GUI_PATH, IMG_FOLDER)
    

DEF_PROPPKG = 'Peng-Robinson'

class MainThermoFrame(wxDialog):
    """Main fram where all the panels sit"""
    def __init__(self, parent, title, interpParent=None, provider=None, thName=None):

        """Initializes the panel

        parent -- Parent of the object
        interpParent -- Parent of the interpreter
        provider -- Name of the thermo provider
        thName -- Name of the thermo case
        ID -- id
        title -- title of the frame
        pos -- pos
        size -- size

        """
        
        wxDialog.__init__(self, parent, -1, title, style=wxDEFAULT_DIALOG_STYLE|wxDIALOG_MODAL)
        
        self.thPanels = []
        self.inProvider = provider
        
        if not self.inProvider: #Create a sample simulation
            #Do the imports
            from sim.thermo import ThermoAdmin
            from sim.solver import Flowsheet
            from sim.unitop import Flash

            #Do a basic simulation
            provider = "VirtualMaterials"
            thName = "thCase1"
            self.thAdmin = ThermoAdmin.ThermoAdmin()
            self.parentFlowsh = Flowsheet.Flowsheet()
            self.parentFlowsh.SetThermoAdmin(self.thAdmin)
            thCaseObj = self.thAdmin.AddPkgFromName(provider, thName, "Peng-Robinson")
            self.parentFlowsh.SetThermo(thCaseObj)
            self.thAdmin.AddCompound(provider, thName, "METHANE")
            self.thAdmin.AddCompound(provider, thName, "PROPANE")
            self.thAdmin.AddCompound(provider, thName, "n-HEXANE")
            uOp = Flash.SimpleFlash()
            self.parentFlowsh.AddUnitOperation(uOp, "myFlash1")
            port = uOp.GetPort('In')
            port.SetCompositionValues((0.33, 0.33, 0.34), FIXED_V)

        if not interpParent: interpParent = self


        fileName = os.path.join(IMG_PATH, 'thermo.ico')
        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
        self.SetIcon(icon)
        
        self.panel = wxPanel(self, -1)
        
        mainSizer = wxBoxSizer( wxVERTICAL )
        
        #Notebook and its sizer adn pages
        self.nb = wxNotebook(self.panel, -1, wxDefaultPosition, wxDefaultSize, 0 )
        nbSizer = wxNotebookSizer(self.nb)
        self.thPanels.append(ThermoSelection(self.nb, -1, interpParent, provider, thName))
        self.nb.AddPage(self.thPanels[0], "Pkg-Cmp Selection")
        self.thPanels.append(IPSelection(self.nb, -1, interpParent, provider, thName))
        self.nb.AddPage(self.thPanels[1], "IP")
        self.thPanels.append(FlashSelection(self.nb, -1, interpParent, provider, thName))
        self.nb.AddPage(self.thPanels[2], "Flash Settings")
        EVT_NOTEBOOK_PAGE_CHANGED(self.nb, self.nb.GetId(), self.OnPageChanged)
        mainSizer.AddSizer(nbSizer, 0, wxALIGN_CENTER_VERTICAL, 5)
    
        #Sizer for rest of controls
        ctrlsSizer = wxFlexGridSizer( 0, 2, 0, 0 )
        btnClose = wxButton(self.panel, -1, "Close", wxDefaultPosition, wxDefaultSize, 0)
        EVT_BUTTON(self, btnClose.GetId(), self.OnCloseMe)
        ctrlsSizer.AddWindow(btnClose, 0, wxALL, 5 )
        txtThMsg = wxTextCtrl(self.panel, -1, "", wxDefaultPosition, wxSize(430,40), wxTE_MULTILINE )
        txtThMsg.Enable(false)
        ctrlsSizer.AddWindow(txtThMsg, 0, wxGROW|wxALIGN_CENTER_HORIZONTAL|wxLEFT, 35 )
        mainSizer.AddSizer(ctrlsSizer, 0, wxGROW|wxALIGN_CENTER_VERTICAL|wxALL, 5 )

        EVT_CLOSE(self, self.OnCloseWindow)
        
        #Last touches
        self.panel.SetAutoLayout( true )
        self.panel.SetSizer(mainSizer)
        mainSizer.Fit(self)
        mainSizer.SetSizeHints(self.panel)

    def CleanUp(self):
        """Required CleanUp"""
        for i in self.thPanels: 
            if hasattr(i, "CleanUp"): i.CleanUp()
        del self.thPanels
        del self.inProvider
        
    def UpdateView(self):
        """Updates the view of the panels"""
        for i in self.thPanels: 
            if hasattr(i, "UpdateView"): i.UpdateView()
        
    def OnPageChanged(self, event):
        """Page changed"""
        #Update the view with the newest info
        nuPage = event.GetSelection()
        if hasattr(self.thPanels[nuPage], "UpdateView"): self.thPanels[nuPage].UpdateView()
        event.Skip()
        
    def OnCloseWindow(self, event):
        if not self.inProvider: #If everything was created here, do a CleanUp
            self.thAdmin.CleanUp()
            self.parentFlowsh.CleanUp()
        self.CleanUp()
        self.Destroy()

    def OnCloseMe(self, event):
        self.Close(true)

#---------------------------------------------------------------------------

def BuildThermo(parent, interpParent, provider, thName):
    """Returns an instance of MainThermoFrame"""
    frameTitle = "Thermodynamics case builder --> " + provider + '-' + thName
    win = MainThermoFrame(parent, frameTitle, interpParent, provider, thName)
    win.Centre(wxBOTH)
    parent.otherWin = win
    win.Show(true)
    
class TestFrame(wxFrame):
    def __init__(self, parent, log, interpParent=None, provider=None, thName=None):
        wxFrame.__init__(self, parent, -1, "Sim42 Thermo test",
                          style=wxDEFAULT_FRAME_STYLE)
                          #style=wxDEFAULT_DIALOG_STYLE|wxDIALOG_MODAL)
        
        self.thPanels = []
        self.inProvider = provider
        
        if not self.inProvider: #Create a sample simulation
            #Do the imports
            from sim.thermo import ThermoAdmin
            from sim.solver import Flowsheet
            from sim.unitop import Flash

            #Do a basic simulation
            provider = "VirtualMaterials"
            thName = "thCase1"
            self.thAdmin = ThermoAdmin.ThermoAdmin()
            self.parentFlowsh = Flowsheet.Flowsheet()
            self.parentFlowsh.SetThermoAdmin(self.thAdmin)
            thCaseObj = self.thAdmin.AddPkgFromName(provider, thName, "Peng-Robinson")
            self.parentFlowsh.SetThermo(thCaseObj)
            self.thAdmin.AddCompound(provider, thName, "METHANE")
            self.thAdmin.AddCompound(provider, thName, "PROPANE")
            self.thAdmin.AddCompound(provider, thName, "n-HEXANE")
            uOp = Flash.SimpleFlash()
            self.parentFlowsh.AddUnitOperation(uOp, "myFlash1")
            port = uOp.GetPort('In')
            port.SetCompositionValues((0.33, 0.33, 0.34), FIXED_V)

        if not interpParent: interpParent = self
        self.interpParent = interpParent

        fileName = os.path.join(IMG_PATH, 'thermo.ico')
        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
        self.SetIcon(icon)
        
        self.panel = wxPanel(self, -1)
        
        mainSizer = wxBoxSizer( wxVERTICAL )
        
        #Notebook and its sizer adn pages
        self.nb = wxNotebook(self.panel, -1, wxDefaultPosition, wxDefaultSize, 0 )
        nbSizer = wxNotebookSizer(self.nb)
        self.thPanels.append(ThermoSelection(self.nb, -1, interpParent, provider, thName))
        self.nb.AddPage(self.thPanels[0], "Pkg-Cmp Selection")
        self.thPanels.append(IPSelection(self.nb, -1, interpParent, provider, thName))
        self.nb.AddPage(self.thPanels[1], "IP")
        self.thPanels.append(FlashSelection(self.nb, -1, interpParent, provider, thName))
        self.nb.AddPage(self.thPanels[2], "Flash Settings")
        EVT_NOTEBOOK_PAGE_CHANGED(self.nb, self.nb.GetId(), self.OnPageChanged)
        mainSizer.AddSizer(nbSizer, 0, wxALIGN_CENTER_VERTICAL, 5)
    
        #Sizer for rest of controls
        ctrlsSizer = wxFlexGridSizer( 0, 2, 0, 0 )
        btnClose = wxButton(self.panel, -1, "Close", wxDefaultPosition, wxDefaultSize, 0)
        EVT_BUTTON(self, btnClose.GetId(), self.OnCloseMe)
        ctrlsSizer.AddWindow(btnClose, 0, wxALL, 5 )
        txtThMsg = wxTextCtrl(self.panel, -1, "", wxDefaultPosition, wxSize(430,40), wxTE_MULTILINE )
        txtThMsg.Enable(false)
        ctrlsSizer.AddWindow(txtThMsg, 0, wxGROW|wxALIGN_CENTER_HORIZONTAL|wxLEFT, 35 )
        mainSizer.AddSizer(ctrlsSizer, 0, wxGROW|wxALIGN_CENTER_VERTICAL|wxALL, 5 )

        EVT_CLOSE(self, self.OnCloseWindow)
        
        #Last touches
        self.panel.SetAutoLayout( true )
        self.panel.SetSizer(mainSizer)
        mainSizer.Fit(self)
        mainSizer.SetSizeHints(self.panel)

    def CleanUp(self):
        """Required CleanUp"""
        for i in self.thPanels: 
            if hasattr(i, "CleanUp"): i.CleanUp()
        del self.thPanels
        del self.inProvider
        
    def UpdateView(self):
        """Updates the view of the panels"""
        for i in self.thPanels: 
            if hasattr(i, "UpdateView"): i.UpdateView()
        
    def OnPageChanged(self, event):
        """Page changed"""
        #Update the view with the newest info
        nuPage = event.GetSelection()
        if hasattr(self.thPanels[nuPage], "UpdateView"): self.thPanels[nuPage].UpdateView()
        event.Skip()
        
    def OnCloseWindow(self, event):
        self.interpParent.CloseFrameNotify(self)
        if not self.inProvider: #If everything was created here, do a CleanUp
            self.thAdmin.CleanUp()
            self.parentFlowsh.CleanUp()
        self.CleanUp()
        self.Destroy()

    def OnCloseMe(self, event):
        self.Close(true)
        

    #Dummy methods that simulate the behavior of the parent of PyCrust
    def CloseFrameNotify(self, frame):
        pass
    def SendAndExecCode(self, code):
        thAdmin = self.thAdmin
        parentFlowsh = self.parentFlowsh
        eval(code)
    def GetParentFlowsh(self):
        return self.parentFlowsh
    def GetThAdmin(self):
        return self.thAdmin
    def GetAutoSolveStatus(self):
        return 1
    def Solve(self):
        self.parentFlowsh.Solve()
        self.UpdateView()
    def Forget(self):
        self.parentFlowsh.SolverForget()
        self.UpdateView()


if __name__ == '__main__':
    import sys
    app = wxPySimpleApp()
    frame = TestFrame(None, sys.stdout)
    frame.Centre(wxBOTH)
    frame.Show(true)
    app.MainLoop()    
    
    
