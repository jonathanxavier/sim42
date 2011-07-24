"""Creates a panel used to change settings of a flash

Classes:
FlashMainPanel -- Main panel for the flash

Functions:
UOWrapperPanel -- Creates the panel and passes it as a return value

"""
import string, sys

from wxPython.wx import *
from wxPython.grid import *
from wxPython.lib.buttons import wxGenToggleButton

from sim.solver.Variables import * 
import GridEditors, GridRenderers
import guiUnitOperations

class FlashMainPanel(guiUnitOperations.UOMainPanel):
    """This panel puts together all the req panels in the correct place"""
    def __init__(self, parent, interpParent, uOpName, pfd, panelId = -1):
        guiUnitOperations.UOMainPanel.__init__(self, parent, interpParent, uOpName, pfd, panelId)

    def CreatePanels(self, pfd):
        self.thPanel = guiUnitOperations.UOThermoPanel(self.nb, self.interpParent, self.uOpName)
        self.nb.AddPage(self.thPanel, "Thermodynamics")        

        self.matConnPanel = guiUnitOperations.UOConnectionPanel(self.nb, self.interpParent, self.uOpName, pfd, MAT)
        self.nb.AddPage(self.matConnPanel, "Mat Connections")       

        self.matInPanel = FlashMatSettings(self.nb, self.interpParent, self.uOpName, IN)
        self.nb.AddPage(self.matInPanel, "Mat Inlet")        

        self.matOutPanel = FlashMatSettings(self.nb, self.interpParent, self.uOpName, OUT)
        self.nb.AddPage(self.matOutPanel, "Mat Outlet")        

        self.paramPanel = guiUnitOperations.UOParametersPanel(self.nb, self.interpParent, self.uOpName)
        self.nb.AddPage(self.paramPanel, "Parameters")
        
        if self.HasEnergyPorts():
            self.eneConnPanel = guiUnitOperations.UOConnectionPanel(self.nb, self.interpParent, self.uOpName, pfd, ENE)
            self.nb.AddPage(self.eneConnPanel, "Ene Connections")        

            self.eneInPanel = guiUnitOperations.UOEneSettings(self.nb, self.interpParent, self.uOpName, IN)
            self.nb.AddPage(self.eneInPanel, "Ene_Inlet")        

            self.eneOutPanel = guiUnitOperations.UOEneSettings(self.nb, self.interpParent, self.uOpName, OUT)
            self.nb.AddPage(self.eneOutPanel, "Ene_Outlet")        

        self.nb.SetSelection(2)        

class FlashMatSettings(wxPanel):
    """Panel for selecting a port and adding a panel for mat props"""
    def __init__(self, parent, interpParent, uOpName, inOrOut, id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)

        self.interpParent = interpParent
        self.uOpName = uOpName
        parentFlowsh = self.interpParent.GetParentFlowsh()
        self.inOrOut = inOrOut
        self.currPanel = None

        self.portsBut = []

        portsNames = parentFlowsh.chUODict[self.uOpName].GetPortNames(MAT|self.inOrOut)

        for i in range(len(portsNames)):
            b = wxGenToggleButton(self, -1, portsNames[i], wxPoint(5, 25*i+10))
            self.portsBut.append(b)
            EVT_BUTTON(self, b.GetId(), self.PortSelect)
        
        if len(portsNames) > 0:
            self.portsBut[0].SetToggle(true)
            portName = self.portsBut[0].GetLabel()
        else:portName = ''
        self.UpdateFromPortSelect(portName)

    def UpdateView(self):
        if isinstance(self.currPanel, guiUnitOperations.PortMatSettings):
            self.currPanel.UpdateView()
            
    def PortSelect(self, event):
        b = event.GetButtonObj()
        if event.GetIsDown():
            portName = b.GetLabel()
        else: portName = ''
        for i in self.portsBut:
            if i != b: i.SetToggle(false)
        self.UpdateFromPortSelect(portName)
        self.Refresh()

    def UpdateFromPortSelect(self, portName):
        w, h =  self.GetSizeTuple()
        if self.currPanel: self.currPanel.Destroy()
        if portName != '':
            self.currPanel = guiUnitOperations.PortMatSettings(self, self.interpParent, self.uOpName,
                                             portName, -1, wxPoint(85, 0), wxSize(w-85, h-30))
        else:
            self.currPanel = wxPanel(self, -1, wxPoint(0, 35), wxSize(w, h-30), wxSIMPLE_BORDER)
        self.currPanel.Refresh()

def UOWrapperPanel(parent, interpParent, uOpName, pfd):
    """Creates the panel and passes it as a return value"""
    #Empty panel... Overload this function for each specific UO
    return FlashMainPanel(parent, interpParent, uOpName, pfd)