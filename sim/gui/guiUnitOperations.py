"""Base class for editing uos in the gui

Classes:
UOMainPanel -- Main panel for the flash
UOTitlePanel -- Panel, with the general info about the UO being edited
UOThermoPanel -- Panel for thermo settings
UOConnectionPanel -- Panel for mat or ene connection settings
UOMatSettings -- Panel for selecting a port and adding a panel fmat props&comps
UOEneSettings -- Panel for selecting a port and adding a panel ene settings
PortEneSettings -- Panel for ene settings
UOParametersPanel -- Panel for parameters settings

Functions:
UOWrapperPanel -- Creates the panel and passes it as a return value

This file is the provider of base classes to be inherited by specific UOps in 
case something special is needed

"""

import string, sys

from wxPython.wx import *
from wxPython.grid import *

from sim.solver.Variables import * 
import GridEditors, GridRenderers
from SimGrids import MaterialPortPanel, EnergyPortPanel

class UOMainPanel(wxScrolledWindow):
    """Puts together all the requiered panels in the correct place"""
    def __init__(self, parent, interpParent, uOp, pfd, panelId = -1):
        w, h = (1000, 1000)
        wxScrolledWindow.__init__(self, parent, panelId, wxPoint(0, 0))
        self.SetScrollbars(20, 20, w/20, h/20)
        
        self.panels = []
        self.interpParent = interpParent
        self.uOp = uOp
        #path is something like: /comp.Ideal
        path = self.uOp.GetPath()
        if path[0] == '/': path = path[1:]
        self.uOpNames = string.split(path, ".")
        
        mainSizer = wxBoxSizer(wxVERTICAL)
        
        titlePanel = UOTitlePanel(self, self.uOp, -1, pos=wxPoint(0, 0), size=wxSize(1000,30))
        mainSizer.AddWindow(titlePanel, 0, wxALIGN_CENTER_VERTICAL|wxALL, 1 )
    
        self.nb = wxNotebook(self, -1, wxPoint(0, 30), size=wxSize(w, h - 30))
        nbSizer = wxNotebookSizer(self.nb)
        mainSizer.AddSizer(nbSizer, 0, wxGROW|wxALIGN_CENTER_VERTICAL|wxALL, 1 )
        
        self.CreatePanels(pfd)
        
        titlePanel.Refresh()
        self.nb.Refresh()

        EVT_NOTEBOOK_PAGE_CHANGED(self.nb, self.nb.GetId(), self.OnPageChanged)
    
        self.SetAutoLayout(true)
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        mainSizer.SetSizeHints(self)

    def CreatePanels(self, pfd):
        #thPanel
        self.panels.append(UOThermoPanel(self.nb, self.interpParent, self.uOp))
        self.nb.AddPage(self.panels[0], "Thermodynamics")        

        #connPanel
        self.panels.append(UOConnectionPanel(self.nb, self.interpParent, self.uOp, pfd, MAT))
        self.nb.AddPage(self.panels[1], "Mat Connections")        

        #matInPanel
        self.panels.append(UOSettings(self.nb, self.interpParent, self.uOp, MAT|IN))
        self.nb.AddPage(self.panels[2], "Mat Inlet")        

        #matOutPanel
        self.panels.append(UOSettings(self.nb, self.interpParent, self.uOp, MAT|OUT))
        self.nb.AddPage(self.panels[3], "Mat Outlet")        

        #paramPanel
        self.panels.append(UOParametersPanel(self.nb, self.interpParent, self.uOp))
        self.nb.AddPage(self.panels[4], "Parameters")   

        if len(self.uOp.GetPortNames(ENE|IN|OUT)):
            #eneConnPanel
            self.panels.append(UOConnectionPanel(self.nb, self.interpParent, self.uOp, pfd, ENE))
            self.nb.AddPage(self.panels[5], "Ene Connections")        

            #eneInPanel
            self.panels.append(UOSettings(self.nb, self.interpParent, self.uOp, ENE|IN))
            self.nb.AddPage(self.panels[6], "Ene_Inlet")        

            #eneOutPanel
            self.panels.append(UOSettings(self.nb, self.interpParent, self.uOp, ENE|OUT))
            self.nb.AddPage(self.panels[7], "Ene_Outlet")

        self.nb.SetSelection(2)

    def UpdateView(self, page=-1):
        if page < 0: nuPage = self.nb.GetSelection()
        else: nuPage = page
        self.panels[nuPage].UpdateView()

    def OnPageChanged(self, event):
        #Update the view with the newest info
        #Not implemented yet for every panel
        self.UpdateView(event.GetSelection())
        event.Skip()

class UOTitlePanel(wxPanel):
    """Panel in the top, with the general info about the UO being edited"""
    
    def __init__(self, parent, uOp, id=-1, pos=wxDefaultPosition, size=wxDefaultSize):
        wxPanel.__init__(self, parent, id, pos, size)

        str = "Editing... " + uOp.GetPath() + "  !!!!!"
        text = wxStaticText(self, -1, str, wxPoint(10, 0))
        font = wxFont(10, wxDEFAULT, wxNORMAL, wxBOLD, false, "Verdana")
        w, h, d, e = self.GetFullTextExtent(str, font)
        text.SetFont(font)
        text.SetSize(wxSize(w, h))
        text.SetBackgroundColour(wxColour(255, 255, 0))
        self.SetBackgroundColour(wxColour(255, 255, 0))

class UOThermoPanel(wxPanel):
    """Panel for thermo settings"""
    def __init__(self, parent, interpParent, uOp,id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)
        
        self.interpParent = interpParent
        self.uOp = uOp
        path = self.uOp.GetPath()
        if path[0] == '/': path = path[1:]
        self.uOpNames = string.split(path, ".")
        thAdmin = self.interpParent.GetThAdmin()
        
        myw = 300 #(w - 20) / 2
        myh = (h - 40)

        #Build selection panel --------------------------------------------
        self.selPanel = wxPanel(self, -1, wxPoint(5, 10), wxSize(myw,myh), wxSIMPLE_BORDER)
        
        wxStaticText(self.selPanel, -1, "Th. Providers:", wxPoint(5, 5), wxSize(100, 20))
        providers = thAdmin.GetAvThermoProviderNames()
        self.provList = wxChoice(self.selPanel, -1, wxPoint(105, 5), wxSize(150, 125), choices=providers)
        EVT_CHOICE(self, self.provList.GetId(), self.ProviderSelect)

        wxStaticText(self.selPanel, -1, "Th. Case Names:", wxPoint(5, 35), wxSize(250, 20))
        self.thCases = wxListBox(self.selPanel, -1, wxPoint(5, 55), wxSize(250, 120), [], wxLB_SINGLE)
        EVT_LISTBOX(self, self.thCases.GetId(), self.CaseSelect)


        #Build info panel ------------------------------------------------- 
        self.infoPanel = wxPanel(self, -1, wxPoint(myw + 10, 10), wxSize(myw,myh), wxSIMPLE_BORDER)

        wxStaticText(self.infoPanel, -1, "Vapor Package:", wxPoint(5, 5), wxSize(100, 20))
        self.lblVapPkg = wxStaticText(self.infoPanel, -1, "", wxPoint(105, 5), wxSize(150, 20),
                                      style=wxSUNKEN_BORDER|wxST_NO_AUTORESIZE)
        self.lblVapPkg.SetBackgroundColour(wxLIGHT_GREY)
        
        wxStaticText(self.infoPanel, -1, "Liquid Package:", wxPoint(5, 35), wxSize(100, 20))
        self.lblLiqPkg = wxStaticText(self.infoPanel, -1, "", wxPoint(105, 35), wxSize(150, 20),
                                      style=wxSUNKEN_BORDER|wxST_NO_AUTORESIZE)
        self.lblLiqPkg.SetBackgroundColour(wxLIGHT_GREY)

        wxStaticText(self.infoPanel, -1, "Selected Compounds:", wxPoint(5, 75), wxSize(250, 20))
        self.cmpNames = wxListBox(self.infoPanel, -1, wxPoint(5, 95), wxSize(250, 120), [], wxLB_SINGLE)
        self.cmpNames.SetBackgroundColour(wxLIGHT_GREY)

        self.UpdateView()


    def UpdateView(self):
        """Reloads all the info from the simulation objects"""
        thermo = self.uOp.GetThermo()
        if thermo:
            self.provList.SetStringSelection(thermo.provider)
            self.UpdateFromProviderSelect()
        elif self.provList.Number() > 0:
            self.provList.SetSelection(0)
            self.UpdateFromProviderSelect()
            
        if thermo:
            self.thCases.SetStringSelection(thermo.provider, true)
            self.UpdatePkgInfo()        
        elif self.thCases.Number() > 0:
            self.thCases.SetSelection(0)
            self.UpdateFromThCaseSelect()

    def ProviderSelect(self, event):
        self.UpdateFromProviderSelect()

    def UpdateFromProviderSelect(self):
        provider = self.provList.GetStringSelection()
        if provider != '':
            thAdmin = self.interpParent.GetThAdmin()
            thNames = thAdmin.GetAvThCaseNames(provider)
        else: thNames = ()
        self.thCases.Clear()
        self.thCases.InsertItems(thNames, 0)

    def CaseSelect(self, event):        
        self.UpdateFromThCaseSelect()

    def UpdateFromThCaseSelect(self):
        provider = self.provList.GetStringSelection()
        thName = self.thCases.GetStringSelection()
        if thName == '' or provider == '': return
        code = 'parentFlowsh'
        for uo in self.uOpNames: code += '.GetChildUO("' + uo + '")'
        code += '.SetThermoProvider("' + provider + '", "' + thName + '")'
        self.interpParent.SendAndExecCode(code)
        self.UpdatePkgInfo()

    def UpdatePkgInfo(self):
        thermo = self.uOp.GetThermo()
        if not thermo: return
        provider = thermo.provider
        thName = thermo.case
        thAdmin = self.interpParent.GetThAdmin()
        propPkg = thAdmin.GetPropPkgString(provider, thName)
        pkgSplit = string.split(propPkg)
        if len(pkgSplit) == 0:
            self.lblVapPkg.SetLabel('')
            self.lblLiqPkg.SetLabel('')
        if len(pkgSplit) > 0: self.lblVapPkg.SetLabel(pkgSplit[0])
        if len(pkgSplit) == 1: self.lblLiqPkg.SetLabel(pkgSplit[0])            
        if len(pkgSplit) > 1: self.lblLiqPkg.SetLabel(pkgSplit[1])
        names = thAdmin.GetSelectedCompoundNames(provider, thName)
        self.cmpNames.Clear()
        self.cmpNames.InsertItems(names, 0)

class UOConnectionPanel(wxPanel):
    """Panel for connection settings"""
    def __init__(self, parent, interpParent, uOp, pfd, portType, id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)

        self.interpParent = interpParent
        self.portType = portType
        self.uOp = uOp
        self.uOpName = self.uOp.GetName()
        self.pfd = pfd
        parentFlowsh = self.interpParent.GetParentFlowsh()
        
        uOpNames = parentFlowsh.GetChildUONames()
        uOpNames.remove(self.uOpName)        
        portsInNames = self.uOp.GetPortNames(self.portType|IN)
        portsOutNames = self.uOp.GetPortNames(self.portType|OUT)
        connsIn = parentFlowsh.GetChildConnections(self.uOpName, self.portType|IN)
        connsOut = parentFlowsh.GetChildConnections(self.uOpName, self.portType|OUT)
        
        myw = 400 #(w - 20) / 2
        myh = (h - 40)

        boldFont = wxFont(8, wxDEFAULT, wxNORMAL, wxBOLD, false)

        #Build conn in panel --------------------------------------------
        self.connInPanel = wxPanel(self, -1, wxPoint(5, 10), wxSize(myw,myh), wxSIMPLE_BORDER)
        txt = wxStaticText(self.connInPanel, -1, "Ports In", wxPoint(5, 5), wxSize(80, 20),
                           style=wxALIGN_CENTRE|wxST_NO_AUTORESIZE)
        txt.SetFont(boldFont)
        txt = wxStaticText(self.connInPanel, -1, "From UO", wxPoint(90, 5), wxSize(140, 20),
                           style=wxALIGN_CENTRE|wxST_NO_AUTORESIZE)
        txt.SetFont(boldFont)        
        txt = wxStaticText(self.connInPanel, -1, "From port", wxPoint(235, 5), wxSize(140, 20),
                           style=wxALIGN_CENTRE|wxST_NO_AUTORESIZE)
        txt.SetFont(boldFont)

        self.portsInDict = {}
        self.fromUODict = {}
        self.fromPortDict = {}
        count = 0
        for i in portsInNames:
            y = 40 + count * 30
            lbl = ''
            self.portsInDict[i] = wxStaticText(self.connInPanel, -1, lbl + i, wxPoint(5, y + 5), wxSize(80, 20),
                                               wxALIGN_RIGHT|wxST_NO_AUTORESIZE)
            
            self.fromUODict[i] = wxChoice(self.connInPanel, -1, wxPoint(90, y), wxSize(140, 60), choices=uOpNames, name=i)
            EVT_CHOICE(self, self.fromUODict[i].GetId(), self.FromUOSelect)

            self.fromPortDict[i] = wxChoice(self.connInPanel, -1, wxPoint(235, y), wxSize(140, 60), choices=[], name=i)
            EVT_CHOICE(self, self.fromPortDict[i].GetId(), self.FromPortSelect)

            for j in connsIn:
                if i == j[1]:
                    self.fromUODict[i].SetStringSelection(j[2])
                    self.UpdateFromFromUOSelect(i)
                    self.fromPortDict[i].SetStringSelection(j[3])
            count += 1

        #Build conn out panel --------------------------------------------
        self.connOutPanel = wxPanel(self, -1, wxPoint(myw + 10, 10), wxSize(myw,myh),
                                    style=wxSIMPLE_BORDER)
        txt = wxStaticText(self.connOutPanel, -1, "Ports Out", wxPoint(5, 5), wxSize(80, 20),
                           style=wxALIGN_CENTRE|wxST_NO_AUTORESIZE)
        txt.SetFont(boldFont)
        txt = wxStaticText(self.connOutPanel, -1, "To UO", wxPoint(90, 5), wxSize(140, 20),
                           style=wxALIGN_CENTRE|wxST_NO_AUTORESIZE)
        txt.SetFont(boldFont)
        txt = wxStaticText(self.connOutPanel, -1, "To port", wxPoint(235, 5), wxSize(140, 20),
                           style=wxALIGN_CENTRE|wxST_NO_AUTORESIZE)
        txt.SetFont(boldFont)

        self.portsOutDict = {}
        self.toUODict = {}
        self.toPortDict = {}
        count = 0
        for i in portsOutNames:
            y = 40 + count * 30
            self.portsOutDict[i] = wxStaticText(self.connOutPanel, -1, i, wxPoint(5, y + 5),
                                            wxSize(80, 20), wxALIGN_RIGHT|wxST_NO_AUTORESIZE)
            self.toUODict[i] = wxChoice(self.connOutPanel, -1, wxPoint(90, y),
                                        wxSize(140, 60),choices=uOpNames, name=i)
            EVT_CHOICE(self, self.toUODict[i].GetId(), self.ToUOSelect)
            self.toPortDict[i] = wxChoice(self.connOutPanel, -1, wxPoint(235, y),
                                          wxSize(140, 60), choices=[], name=i)
            EVT_CHOICE(self, self.toPortDict[i].GetId(), self.ToPortSelect)
            for j in connsOut:
                if i == j[1]:
                    self.toUODict[i].SetStringSelection(j[2])
                    self.UpdateFromToUOSelect(i)
                    self.toPortDict[i].SetStringSelection(j[3])

            count += 1

    def __del__(self):
        del self.pfd

    def UpdateView(self):
        #To be implemented
        pass
    
    def FromUOSelect(self, event):
        ctrl = event.GetEventObject()
        portName = ctrl.GetName()        
        self.UpdateFromFromUOSelect(portName)

    def UpdateFromFromUOSelect(self, portName):
        uOpName = self.fromUODict[portName].GetStringSelection()
        if uOpName != '':
            parentFlowsh = self.interpParent.GetParentFlowsh()            
            portsOutNames = parentFlowsh.GetChildUO(uOpName).GetPortNames(self.portType|OUT)
        else: portsOutNames = ()
        self.fromPortDict[portName].Clear()
        for i in portsOutNames: self.fromPortDict[portName].Append(i)
            
    def FromPortSelect(self, event):
        ctrl = event.GetEventObject()
        portName = ctrl.GetName()            
        self.UpdateFromFromPortSelect(portName)

    def UpdateFromFromPortSelect(self, portName):
        uOpOutName = self.fromUODict[portName].GetStringSelection()
        portOutName = self.fromPortDict[portName].GetStringSelection()
        if uOpOutName == '' or portOutName == '': return
        parentFlowsh = self.interpParent.GetParentFlowsh()

        #Delete previous connection in pfd    
        conns = parentFlowsh.GetAllChildConnections(self.portType|IN)
        for i in conns:
            if ((self.uOpName == i[2] and portName == i[3]) or \
                (uOpOutName == i[0] and portOutName == i[1])):
                str = string.join(i, '-')
                line = self.pfd.lines[str]
                line.Unlink()
                self.pfd.RemoveShape(line)
                del self.pfd.lines[str]
                line.Destroy()
                self.pfd.Refresh()                
                break

        #Connect 
        code = 'parentFlowsh.ConnectPorts("'
        code += uOpOutName + '", "' + portOutName + '", "'
        code += self.uOpName + '", "' + portName + '")'
        self.interpParent.SendAndExecCode(code)
        lineName = string.join((uOpOutName, portOutName, self.uOpName, portName), '-')
        self.pfd.MyAddLine(wxBLACK_PEN, wxBLACK_BRUSH, '', uOpOutName, self.uOpName, lineName)

        if self.interpParent.GetAutoSolveStatus(): self.interpParent.Solve()

    def ToUOSelect(self, event):
        ctrl = event.GetEventObject()
        portName = ctrl.GetName()            
        self.UpdateFromToUOSelect(portName)

    def UpdateFromToUOSelect(self, portName):
        uOpName = self.toUODict[portName].GetStringSelection()
        if uOpName != '':
            parentFlowsh = self.interpParent.GetParentFlowsh() 
            portsInNames = parentFlowsh.GetChildUO(uOpName).GetPortNames(self.portType|IN)
        else: portsInNames = ()
        self.toPortDict[portName].Clear()
        for i in portsInNames: self.toPortDict[portName].Append(i)

    def ToPortSelect(self, event):
        ctrl = event.GetEventObject()
        portName = ctrl.GetName()         
        self.UpdateFromToPortSelect(portName)

    def UpdateFromToPortSelect(self, portName):
        uOpInName = self.toUODict[portName].GetStringSelection()
        portInName = self.toPortDict[portName].GetStringSelection()
        if uOpInName == '' or portInName == '': return
        parentFlowsh = self.interpParent.GetParentFlowsh()

        #Delete destiny connection if already in use
        conns = parentFlowsh.GetAllChildConnections(self.portType|IN)
        for i in conns:
            if ((self.uOpName == i[0] and portName == i[1]) or \
                (uOpInName == i[2] and portInName == i[3])):
                str = string.join(i, '-')
                line = self.pfd.lines[str]
                line.Unlink()
                self.pfd.RemoveShape(line)
                del self.pfd.lines[str]
                line.Destroy()
                self.pfd.Refresh()
                break

        #Connect
        code = 'parentFlowsh.ConnectPorts("'
        code += self.uOpName + '", "' + portName + '", "'
        code += uOpInName + '", "' + portInName + '")'
        self.interpParent.SendAndExecCode(code)
        lineName = string.join((self.uOpName, portName, uOpInName, portInName), '-')
        self.pfd.MyAddLine(wxBLACK_PEN, wxBLACK_BRUSH, '', self.uOpName, uOpInName, lineName)
        
        if self.interpParent.GetAutoSolveStatus(): self.interpParent.Solve()

        
class UOSettings(wxPanel):
    """Panel for selecting a port and adding a panel for updating props"""
    def __init__(self, parent, interpParent, uOp, portType, id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)
        
        self.interpParent = interpParent
        self.uOp = uOp
        self.portType = portType
        self.currPanel = None
        
        #Main sizers
        mainSizer = wxBoxSizer( wxVERTICAL )
        self.innerSizer = wxBoxSizer( wxVERTICAL )
        
        
        #Choice of port
        choiceSizer = wxBoxSizer( wxHORIZONTAL )
        
        lblPort = wxStaticText(self, -1, "View Port:", wxDefaultPosition, wxDefaultSize, wxALIGN_LEFT)
        lblPort.SetFont(wxFont( 10, wxROMAN, wxNORMAL, wxBOLD ))
        choiceSizer.AddWindow(lblPort, 0, wxALIGN_CENTRE|wxALL, 1 )

        portsNames = self.uOp.GetPortNames(self.portType)
        self.portList = wxChoice(self, -1, wxDefaultPosition, wxSize(170,-1), portsNames, 0 )
        choiceSizer.AddWindow(self.portList, 0, wxALIGN_CENTER_VERTICAL|wxALL, 1)
        EVT_CHOICE(self, self.portList.GetId(), self.PortSelect)
    
        self.innerSizer.AddSizer(choiceSizer, 0, wxALIGN_CENTER_VERTICAL|wxALL, 1)
    
        
        #Panel with port info
        if len(portsNames) > 0: 
            self.portList.SetSelection(0)
            portName = self.portList.GetStringSelection()
            port = self.uOp.GetPort(portName)
            if self.portType & MAT:
                self.currPanel = MaterialPortPanel(self, self.interpParent, port, pos=wxPoint(0, 35))
            else:
                self.currPanel = EnergyPortPanel(self, self.interpParent, port, pos=wxPoint(0, 35))
            self.innerSizer.AddWindow(self.currPanel, 0, wxADJUST_MINSIZE|wxGROW|wxALIGN_CENTER_VERTICAL|wxALL, 5 )
            
            
        #Finally
        mainSizer.AddSizer(self.innerSizer, 0, wxGROW|wxALIGN_CENTER_VERTICAL|wxALL, 5 )
    
        self.SetAutoLayout(true)
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        mainSizer.SetSizeHints(self)
    
    def UpdateView(self):
        if hasattr(self.currPanel, 'UpdateView'): self.currPanel.UpdateView()
            
    def PortSelect(self, event):
        self.UpdateFromPortSelect()

    def UpdateFromPortSelect(self):
        portName = self.portList.GetStringSelection()
        if portName != '':
            port = self.uOp.GetPort(portName)
            self.currPanel.SetPort(port)
            self.currPanel.Refresh()
        
        
class UOMatSettings(wxPanel):
    """Panel for selecting a port and adding a panel for mat props"""
    def __init__(self, parent, interpParent, uOp, inOrOut, id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)
        
        self.interpParent = interpParent
        self.uOp = uOp
        self.inOrOut = inOrOut
        self.currPanel = None
        
        #Main sizers
        mainSizer = wxBoxSizer( wxVERTICAL )
        self.innerSizer = wxBoxSizer( wxVERTICAL )
        
        
        #Choice of port
        choiceSizer = wxBoxSizer( wxHORIZONTAL )
        
        lblPort = wxStaticText(self, -1, "View Port:", wxDefaultPosition, wxDefaultSize, wxALIGN_LEFT)
        lblPort.SetFont(wxFont( 10, wxROMAN, wxNORMAL, wxBOLD ))
        choiceSizer.AddWindow(lblPort, 0, wxALIGN_CENTRE|wxALL, 1 )

        portsNames = self.uOp.GetPortNames(MAT|self.inOrOut)
        self.portList = wxChoice(self, -1, wxDefaultPosition, wxSize(170,-1), portsNames, 0 )
        choiceSizer.AddWindow(self.portList, 0, wxALIGN_CENTER_VERTICAL|wxALL, 1)
        EVT_CHOICE(self, self.portList.GetId(), self.PortSelect)
    
        self.innerSizer.AddSizer(choiceSizer, 0, wxALIGN_CENTER_VERTICAL|wxALL, 1)
    
        
        #Panel with port info
        if len(portsNames) > 0: 
            self.portList.SetSelection(0)
            portName = self.portList.GetStringSelection()
            port = self.uOp.GetPort(portName)
            self.currPanel = MaterialPortPanel(self, self.interpParent, port, pos=wxPoint(0, 35))
            self.innerSizer.AddWindow(self.currPanel, 0, wxADJUST_MINSIZE|wxGROW|wxALIGN_CENTER_VERTICAL|wxALL, 5 )
            
            
        #Finally
        mainSizer.AddSizer(self.innerSizer, 0, wxGROW|wxALIGN_CENTER_VERTICAL|wxALL, 5 )
    
        self.SetAutoLayout(true)
        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        mainSizer.SetSizeHints(self)
    
    def UpdateView(self):
        if hasattr(self.currPanel, 'UpdateView'): self.currPanel.UpdateView()
            
    def PortSelect(self, event):
        self.UpdateFromPortSelect()

    def UpdateFromPortSelect(self):
        portName = self.portList.GetStringSelection()
        if portName != '':
            port = self.uOp.GetPort(portName)
            self.currPanel.SetPort(port)
            self.currPanel.Refresh()

            
class UOEneSettings(wxPanel):
    """Panel for selecting a port and adding a panel ene settings"""
    def __init__(self, parent, interpParent, uOp, inOrOut, id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)

        self.interpParent = interpParent
        self.uOp = uOp
        self.inOrOut = inOrOut
        self.currPanel = None

        wxStaticText(self, -1, "View Port:", wxPoint(5, 5), wxSize(50, 20))
        portsNames = self.uOp.GetPortNames(ENE|self.inOrOut)
            
        self.portList = wxChoice(self, -1, wxPoint(105, 5), wxSize(150, 125), choices=portsNames)
        EVT_CHOICE(self, self.portList.GetId(), self.PortSelect)

        w, h =  parent.GetSizeTuple()
        if len(portsNames) == 0:
            self.currPanel = wxPanel(self, -1, wxPoint(0, 35), wxSize(w, h-30), wxSIMPLE_BORDER)
        else:
            self.portList.SetSelection(0)
            self.UpdateFromPortSelect()

    def UpdateView(self):
        #Could be just self.UpdateFromPortSelect(),
        #but it has to do things that are not needed
        if isinstance(self.currPanel, PortEneSettings): self.currPanel.UpdateView()
            
    def PortSelect(self, event):       
        self.UpdateFromPortSelect()

    def UpdateFromPortSelect(self):
        portName = self.portList.GetStringSelection()
        w, h = self.GetSizeTuple()
        if self.currPanel: self.currPanel.Destroy()
        if portName != '':
            self.currPanel = PortEneSettings(self, self.interpParent, self.uOp, portName,
                                            -1, wxPoint(0, 35), wxSize(w, h-30))
        else:
            self.currPanel = wxPanel(self, -1, wxPoint(0, 35), wxSize(w, h-30), wxSIMPLE_BORDER)
        self.currPanel.Refresh()

class PortEneSettings(wxPanel):
    """Panel for ene settings"""
    def __init__(self, parent, interpParent, uOp, portName, id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)
    
        self.propPanel = PropertiesPanel(self, interpParent, uOp, portName)

    def UpdateView(self):
        self.propPanel.UpdateView()

class UOParametersPanel(wxPanel):
    """Panel for parameters settings"""
    def __init__(self, parent, interpParent, uOp, id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)

        self.interpParent = interpParent
        self.uOp = uOp
        path = self.uOp.GetPath()
        if path[0] == '/': path = path[1:]
        self.uOpNames = string.split(path, ".")
        reqParams = self.uOp.GetListOfReqParam()
        self.currValue = (None, None) #Param name, value

        count = 0
        self.paramValDict = {} #Is it necessary ???
        for i in reqParams:
            y = 20 + count * 30
            txt = wxStaticText(self, -1, i, wxPoint(20, y), wxSize(80, 20),
                               wxALIGN_RIGHT|wxST_NO_AUTORESIZE)
            val = uOp.GetParameterValue(i)
            self.paramValDict[i] = wxTextCtrl(self, -1, str(val), pos=wxPoint(105, y),
                                              size=wxSize(100, 20), name=i)
            #validator=wxMyValidator
            EVT_SET_FOCUS(self.paramValDict[i], self.OnParamFocusGained) 
            EVT_KILL_FOCUS(self.paramValDict[i], self.OnParamFocusLost)
            count += 1

    def UpdateView(self):
        #To be implemented
        pass

    def OnParamFocusGained(self, event):
        ctrl = event.GetEventObject()
        ctrl.SetSelection(0, ctrl.GetLineLength(1))
        self.oldValue = ctrl.GetValue()
        event.Skip()

    def OnParamFocusLost(self, event):
        ctrl = event.GetEventObject()
        value = ctrl.GetValue()
        if self.oldValue == value:
            return
        paramName = ctrl.GetName()
        ##When I finish the validators for different type of values the code here could be,
        ##parent.validate(), so all the text controls get validated or something like that
        code = 'parentFlowsh'
        for uo in self.uOpNames: code += '.GetChildUO("' + uo + '")'
        code += '.SetParameterValue("' + paramName + '", ' + value + ')'
        self.interpParent.SendAndExecCode(code)


#All gui wrapper files for UOps are expected to implement this function that
#returns a valid instance of a wxPanel
def UOWrapperPanel(parent, interpParent, uOpName, pfd):
    """Creates the panel and passes it as a return value"""    
    #Empty panel... Overload this function for each specific UO if neccesary
    return UOMainPanel(parent, interpParent, uOpName, pfd)

