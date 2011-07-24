from wxPython.wx import *
from wxPython.grid import *

import ComponentSelection
import GridEditors, GridRenderers
from sim.solver.Variables import *
from sim.solver import S42Glob
from sim.thermo.ThermoConstants import *

import string

VALUE_COL = 0
UNITS_COL = 1
DEF_PROPPKG = 'Peng-Robinson'

class ThermoSelection(wxPanel):
    """Panel to select cmps and pkgs"""
    def __init__(self, parent, ID, interpParent, provider, thName):
        """Initializes the panel

        parent -- Parent of the object
        ID -- id for the panel
        interpParent -- Parent of the interpreter
        provider -- Name of the thermo provider
        thName -- Name of the thermo case

        """        
        wxPanel.__init__(self, parent, ID, style=wxWANTS_CHARS)

        self.interpParent = interpParent
        self.provider = provider
        self.thName = thName
        thAdmin = self.interpParent.GetThAdmin()
        self.openCmpViews = {}
        
        
        #Create all the controls
        ThermoSelectionBase(self, true, true)
        
        
        #Load some controls to variables
        self.cbPkgForPhase = self.GetControl(ID_CB_PkgForPhase, "wxCheckBox")
        self.lblVapPkg = self.GetControl(ID_LBL_VapPkg, "wxStaticText")
        self.chVapPkg = self.GetControl(ID_CH_VapPkg, "wxChoice")
        self.lblLiqPkg = self.GetControl(ID_LBL_LiqPkg, "wxStaticText")
        self.chLiqPkg = self.GetControl(ID_CH_LiqPkg, "wxChoice")
        self.txtCmp = self.GetControl(ID_TXT_Cmp, "wxTextCtrl")
        self.btnAdvanced = self.GetControl(ID_BTN_Advanced, "wxButton")
        self.lstCmp = self.GetControl(ID_LST_CmpList, "wxListCtrl")
        self.btnAddCmp = self.GetControl(ID_BTN_AddCmp, "wxButton")
        self.btnRemCmp = self.GetControl(ID_BTN_RemCmp, "wxButton")
        self.btnViewCmp = self.GetControl(ID_BTN_ViewCmp, "wxButton")
        self.btnCloneCmp = self.GetControl(ID_BTN_CloneCmp, "wxButton")
        self.lstbSelCmp= self.GetControl(ID_LSTB_CmpList, "wxListBox")
        
        
        #Object for filtering compounds
        self.cmpSelOb = ComponentSelection.ComponentSelection()
        cmpNames = thAdmin.GetAvCompoundNames(self.provider)
        for i in cmpNames: self.cmpSelOb.AddComponent(i, 1, "Not Avail", -1, i)
        
        
        #Prop pkg stuff
        self.cbPkgForPhase.SetValue(false)
        EVT_CHECKBOX(self, self.cbPkgForPhase.GetId(), self.OnCheckBox)

        pkgNames = thAdmin.GetAvPropPkgNames(self.provider)
        for i in pkgNames: self.chVapPkg.Append(i)
        EVT_CHOICE(self, self.chVapPkg.GetId(), self.OnChoicePkg)

        for i in pkgNames: self.chLiqPkg.Append(i)
        self.chLiqPkg.Show(false)
        EVT_CHOICE(self, self.chLiqPkg.GetId(), self.OnChoicePkg)

        
        #Cmp selection stuff
        self.txtCmp.SetInsertionPoint(0)
        EVT_TEXT(self, self.txtCmp.GetId(), self.OnText)
        EVT_CHAR(self.txtCmp, self.OnChar)

        self.lstCmp.InsertColumn(0, "Name")
        self.lstCmp.InsertColumn(1, "Formula")
        self.BuildCmpList("")
        self.lstCmp.SetColumnWidth(0, wxLIST_AUTOSIZE)
        self.lstCmp.SetColumnWidth(1, wxLIST_AUTOSIZE)
        EVT_LIST_ITEM_ACTIVATED(self, self.lstCmp.GetId(), self.OnItemActivated)

        EVT_BUTTON(self, self.btnAdvanced.GetId(), self.OnClickAdvanced)
        EVT_BUTTON(self, self.btnAddCmp.GetId(), self.OnClickAddCmp)
        EVT_BUTTON(self, self.btnRemCmp.GetId(), self.OnClickRemoveCmp)
        EVT_BUTTON(self, self.btnViewCmp.GetId(), self.OnClickViewCmp)
        EVT_BUTTON(self, self.btnCloneCmp.GetId(), self.OnClickCloneCmp)
        
        
        #Select a default prop pkg
        if not self.thName in thAdmin.GetAvThCaseNames(self.provider):
            if DEF_PROPPKG in pkgNames: self.chVapPkg.SetStringSelection(DEF_PROPPKG)
            else: self.chVapPkg.SetStringSelection(1)
            code = 'thAdmin.AddPkgFromName("'
            code += self.provider + '", "'
            code += self.thName + '", "'
            code += self.chVapPkg.GetStringSelection() + '")'
            self.interpParent.SendAndExecCode(code)

        #Update view from existing Th case
        else:
            pkgStr = thAdmin.GetPropPkgString(self.provider, self.thName)
            pkgList = string.split(pkgStr)
            self.chVapPkg.SetStringSelection(pkgList[0])
            if ' ' in pkgStr and (pkgList[0] not in pkgList[1:]):
                self.chLiqPkg.SetStringSelection(pkgList[1])
                self.cbPkgForPhase.SetValue(true)
                self.UpdateFromDifPPkgCheckBox()
            self.UpdateSelectedCmps()

        
        self.SetFocus()
        self.txtCmp.SetFocus()

    def CleanUp(self):
        """Clean up the panel"""
        pass

    def OnCheckBox(self, event):
        """Select diff prop pkg for each phase"""
        self.UpdateFromDifPPkgCheckBox()
    
    def OnChoicePkg(self, event):
        """Select a prop pkg"""
        self.UpdateFromPkgSelection()
        
    def OnText(self, event):
        self.BuildCmpList(event.GetString())

    def OnChar(self, event):
        k = event.GetKeyCode()
        if self.lstCmp.GetItemCount() > 0:
            if k == WXK_RETURN:
                self.SelectCmp()
            elif k == WXK_UP or k == WXK_DOWN:
                self.lstCmp.SetFocus()
        event.Skip()

    def OnItemActivated(self, event):
        """Doesn't work"""
        self.SelectCmp()
        self.lstCmp.SetFocus()
        
    def OnClickAdvanced(self, event):
        self.AdvancedCmpSelection()

    def OnClickAddCmp(self, event):
        self.SelectCmp()

    def OnClickRemoveCmp(self, event):
        self.RemoveCmp()

    def OnClickViewCmp(self, event):
        self.ViewCmp()
    
    def OnClickCloneCmp(self, event):
        pass

    def UpdateFromDifPPkgCheckBox(self):
        if self.cbPkgForPhase.GetValue():
            self.lblVapPkg.SetLabel("Vapor phase:")
            self.lblLiqPkg.SetLabel("Liquid phase:")
            self.chLiqPkg.Show(true)
        else:
            self.lblVapPkg.SetLabel("Property package:")
            self.lblLiqPkg.SetLabel("")
            self.chLiqPkg.Show(false)
        self.Refresh()
    
    def UpdateFromPkgSelection(self):
        pkg = self.chVapPkg.GetStringSelection()
        if self.cbPkgForPhase.GetValue(): pkg = pkg + ' ' + self.chLiqPkg.GetStringSelection()
        code = 'thAdmin.AddPkgFromName("'
        code += self.provider + '", "'
        code += self.thName + '", "'
        code += pkg + '")'
        self.interpParent.SendAndExecCode(code)
        self.UpdateSelectedCmps()

    def BuildCmpList(self, match):
        """Build main av cmp list"""
        self.cmpSelOb.SetMatch(match)
        self.cmpSelOb.Sort()
        self.lstCmp.DeleteAllItems()
        cnt = self.cmpSelOb.GetComponentCount()
        for i in range(cnt):
            success, name, isMainName, fmla, bitAtts, usedID = self.cmpSelOb.GetComponent(i)
            self.lstCmp.InsertStringItem(i, name)
            self.lstCmp.SetStringItem(i, 1, fmla)
            self.lstCmp.SetItemData(i, i)
        if cnt > 0: self.lstCmp.SetItemState(0, wxLIST_STATE_SELECTED, wxLIST_STATE_SELECTED)

    def AdvancedCmpSelection(self):
        #Can it be generalized to any prop pkg??
        """Do advanced selection of compounds"""
        pass
    
    def SelectCmp(self):
        """Add the slected compounds"""
        itm = -1
        while 1:
            itm = self.lstCmp.GetNextItem(itm, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED)
            if itm == -1: break
            code = 'thAdmin.AddCompound("'
            code += self.provider + '", "'
            code += self.thName + '", "'
            code += self.lstCmp.GetItemText(itm) + '")'
            self.interpParent.SendAndExecCode(code)
            
        self.UpdateSelectedCmps()
        self.txtCmp.SetValue('')
            
    def RemoveCmp(self):
        """Remove the selected compounds"""
        selCmps = self.lstbSelCmp.GetSelections()
        for i in range(len(selCmps)-1, -1, -1): 
            code = 'thAdmin.DeleteCompound("'
            code += self.provider + '", "'
            code += self.thName + '", "'     
            code += self.lstbSelCmp.GetString(selCmps[i]) + '")'
            self.interpParent.SendAndExecCode(code)
            self.lstbSelCmp.Delete(selCmps[i])
            
    def ViewCmp(self):
        itm = -1
        itm = self.lstCmp.GetNextItem(itm, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED)
        if itm == -1: return
        cmpName = self.lstCmp.GetItemText(itm)
        cmpView = CmpViewFrame(self, self.interpParent, self.provider, self.thName, cmpName)
        cmpView.Show(true)

    def UpdateView(self):
        """Update values in controls"""
        self.UpdateSelectedCmps()
            
    def UpdateSelectedCmps(self):
        """Update list with selected cmps"""
        thAdmin = self.interpParent.GetThAdmin()
        selCmps = thAdmin.GetSelectedCompoundNames(self.provider, self.thName)
        self.lstbSelCmp.Clear()
        for i in selCmps:(self.lstbSelCmp.Append(i))

    def GetControl(self, id, type):
        return wxPyTypeCast(self.FindWindowById(id), type)



ID_CB_PkgForPhase = 10003
ID_LBL_VapPkg = 10004
ID_CH_VapPkg = 10005
ID_LBL_LiqPkg = 10006
ID_CH_LiqPkg = 10007
ID_LBL_Match = 10008
ID_TXT_Cmp = 10009
ID_BTN_Advanced = 10010
ID_LST_CmpList = 10011
ID_BTN_AddCmp = 10012
ID_BTN_RemCmp = 10013
ID_BTN_ViewCmp = 10014
ID_BTN_CloneCmp = 10015
ID_LBL_SelCmp = 10016
ID_LSTB_CmpList = 10017

def ThermoSelectionBase( parent, call_fit = true, set_sizer = true ):
    item0 = wxBoxSizer( wxVERTICAL )
    
    item1 = wxFlexGridSizer( 2, 0, 0, 0 )
    
    item3 = wxStaticBox( parent, -1, "Property Package" )
    item3.SetFont( wxFont( 10, wxROMAN, wxNORMAL, wxBOLD ) )
    item2 = wxStaticBoxSizer( item3, wxVERTICAL )
    
    item4 = wxFlexGridSizer( 2, 0, 0, 0 )
    
    item5 = wxCheckBox( parent, ID_CB_PkgForPhase, "Set a Pkg for each phase", wxDefaultPosition, wxSize(300,30), 0 )
    item4.AddWindow( item5, 0, wxALL|wxSHAPED, 0 )

    item6 = wxFlexGridSizer( 0, 2, 0, 0 )
    
    item7 = wxStaticText( parent, ID_LBL_VapPkg, "Property Package:", wxDefaultPosition, wxDefaultSize, 0 )
    item6.AddWindow( item7, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    item8 = wxChoice( parent, ID_CH_VapPkg, wxDefaultPosition, wxSize(270,-1), [] , 0 )
    item6.AddWindow( item8, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    item9 = wxStaticText( parent, ID_LBL_LiqPkg, "", wxDefaultPosition, wxDefaultSize, 0 )
    item6.AddWindow( item9, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    item10 = wxChoice( parent, ID_CH_LiqPkg, wxDefaultPosition, wxSize(270,-1), [], 0 )
    item6.AddWindow( item10, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    item4.AddSizer( item6, 0, wxALIGN_CENTER_HORIZONTAL|wxALL, 5 )

    item2.AddSizer( item4, 0, wxALIGN_CENTRE, 5 )

    item1.AddSizer( item2, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    item12 = wxStaticBox( parent, -1, "Compounds" )
    item12.SetFont( wxFont( 10, wxROMAN, wxNORMAL, wxBOLD ) )
    item11 = wxStaticBoxSizer( item12, wxVERTICAL )
    
    item13 = wxFlexGridSizer( 0, 3, 0, 0 )
    
    item14 = wxFlexGridSizer( 2, 0, 0, 0 )
    
    item15 = wxBoxSizer( wxHORIZONTAL )
    
    item16 = wxStaticText( parent, ID_LBL_Match, "Match:", wxDefaultPosition, wxDefaultSize, wxTE_PROCESS_ENTER)
    item15.AddWindow( item16, 0, wxALIGN_CENTRE|wxALL, 5 )

    item17 = wxTextCtrl( parent, ID_TXT_Cmp, "", wxDefaultPosition, wxSize(190,-1), 0 )
    item15.AddWindow( item17, 0, wxALIGN_CENTRE|wxALL, 5 )

    item18 = wxButton( parent, ID_BTN_Advanced, "Advanced", wxDefaultPosition, wxDefaultSize, 0 )
    item15.AddWindow( item18, 0, wxALIGN_CENTRE|wxLEFT, 40 )

    item14.AddSizer( item15, 0, wxALIGN_CENTER_VERTICAL|wxLEFT|wxRIGHT|wxTOP, 5 )

    item19 = wxListCtrl( parent, ID_LST_CmpList, wxDefaultPosition, wxSize(370,230), wxLC_REPORT|wxSUNKEN_BORDER|wxWANTS_CHARS)
    item14.AddWindow( item19, 0, wxALIGN_CENTER_VERTICAL|wxLEFT|wxRIGHT, 5 )

    item13.AddSizer( item14, 0, wxALIGN_CENTRE|wxALL, 5 )

    item20 = wxBoxSizer( wxVERTICAL )
    
    item21 = wxButton( parent, ID_BTN_AddCmp, "Add", wxDefaultPosition, wxDefaultSize, 0 )
    item20.AddWindow( item21, 0, wxALIGN_CENTRE|wxALL, 5 )

    item22 = wxButton( parent, ID_BTN_RemCmp, "Remove", wxDefaultPosition, wxDefaultSize, 0 )
    item20.AddWindow( item22, 0, wxALIGN_CENTRE|wxALL, 5 )

    item23 = wxButton( parent, ID_BTN_ViewCmp, "View", wxDefaultPosition, wxDefaultSize, 0 )
    item20.AddWindow( item23, 0, wxALIGN_CENTRE|wxALL, 5 )

    item24 = wxButton( parent, ID_BTN_CloneCmp, "Clone", wxDefaultPosition, wxDefaultSize, 0 )
    item20.AddWindow( item24, 0, wxALIGN_CENTRE|wxALL, 5 )

    item13.AddSizer( item20, 0, wxALIGN_CENTER_HORIZONTAL|wxTOP, 45 )

    item25 = wxBoxSizer( wxVERTICAL )
    
    item26 = wxStaticText( parent, ID_LBL_SelCmp, "Selected Compounds", wxDefaultPosition, wxDefaultSize, 0 )
    item25.AddWindow( item26, 0, wxALIGN_CENTRE|wxALL, 5 )

    item27 = wxListBox( parent, ID_LSTB_CmpList, wxDefaultPosition, wxSize(190,230), 
        [] , wxLB_EXTENDED|wxLB_HSCROLL|wxLB_NEEDED_SB )
    item25.AddWindow( item27, 0, wxALIGN_CENTRE|wxLEFT|wxRIGHT, 5 )

    item13.AddSizer( item25, 0, wxALIGN_CENTER_HORIZONTAL|wxTOP, 20 )

    item11.AddSizer( item13, 0, wxALIGN_CENTER_VERTICAL, 5 )

    item1.AddSizer( item11, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    item0.AddSizer( item1, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    if set_sizer == true:
        parent.SetAutoLayout( true )
        parent.SetSizer( item0 )
        if call_fit == true:
            item0.Fit( parent )
            item0.SetSizeHints( parent )
    
    return item0




class IPSelection(wxPanel):
    """Panel for editing IPs"""
    def __init__(self, parent, ID, interpParent, provider, thName):
        """Initializes the panel

        parent -- Parent of the object
        ID -- id for the panel
        interpParent -- Parent of the interpreter
        provider -- Name of the thermo provider
        thName -- Name of the thermo case

        """   
        wxPanel.__init__(self, parent, ID, style=wxWANTS_CHARS)

        self.interpParent = interpParent
        self.provider = provider
        self.thName = thName

        
        #Create all the controls
        IPSelectionBase(self, true, true)
        
        
        #Load some controls to variables
        self.lblPropPkgDesc = self.GetControl(ID_LBL_PropPkgDesc, "wxStaticText")
        self.chIPMatrix = self.GetControl(ID_CH_IPMatrix, "wxChoice")
        self.chIPPane = self.GetControl(ID_CH_IPPane, "wxChoice")
        self.ipGrid = self.GetControl(ID_GRID, "wxGrid")

        
        #Rest of code
        EVT_CHOICE(self, self.chIPMatrix.GetId(), self.OnIPMatrixSelect)
        EVT_CHOICE(self, self.chIPPane.GetId(), self.OnIPPaneSelect)

        self.ipGrid.SetDefaultCellBackgroundColour(wxLIGHT_GREY)
        EVT_GRID_CELL_LEFT_DCLICK(self.ipGrid, self.OnCellLeftDClick)
        EVT_GRID_CELL_CHANGE(self.ipGrid, self.OnCellChange)

        self.UpdateView()

    def UpdateView(self):
        """Update what the controls show"""
        
        #Get the termo info
        thAdmin = self.interpParent.GetThAdmin()
        selCmps = thAdmin.GetSelectedCompoundNames(self.provider, self.thName)
        pkgStr = thAdmin.GetPropPkgString(self.provider, self.thName)
        
        #Resize the grid
        r = self.ipGrid.GetNumberRows()
        c = self.ipGrid.GetNumberCols()
        nuCmps = len(selCmps)
        if nuCmps < r: self.ipGrid.DeleteRows(0, r - nuCmps)
        elif nuCmps > r: self.ipGrid.AppendRows(nuCmps - r)
        if nuCmps < c: self.ipGrid.DeleteCols(0, c - nuCmps)
        elif nuCmps > c: self.ipGrid.AppendCols(nuCmps - c)
        for i in range(nuCmps):
            self.ipGrid.SetColLabelValue(i, selCmps[i])
            self.ipGrid.SetRowLabelValue(i, selCmps[i])
            self.ipGrid.SetCellValue(i, i, '--')
            self.ipGrid.SetReadOnly(i, i)
            for j in range(nuCmps):
                if i != j:
                    self.ipGrid.SetCellEditor(i, j, GridEditors.NumberEditor(self.ipGrid))
                    self.ipGrid.SetCellRenderer(i, j, GridRenderers.NumberRenderer(self.ipGrid))
        self.ipGrid.ForceRefresh()

        
        #Fill in the prop pkg name, the choice boxes and the grid
        self.chIPMatrix.Clear()
        self.lblPropPkgDesc.SetLabel(pkgStr)
        ipMatrNames = thAdmin.GetIPMatrixNames(self.provider, self.thName)
        if ipMatrNames:
            for i in ipMatrNames: self.chIPMatrix.Append(i)
            self.chIPMatrix.SetStringSelection(ipMatrNames[0])
        self.UpdateFromIPMatrixSelect()

        
    def OnIPMatrixSelect(self, event):
        """An IP matrix was selected"""
        self.UpdateFromIPMatrixSelect()

    def UpdateFromIPMatrixSelect(self):
        """Changes the data in the affected ctrls when the IP matrix changes"""
        ipMatrName = self.chIPMatrix.GetStringSelection()
        self.chIPPane.Clear()
        if ipMatrName == '':
            self.UpdateFromIPPaneSelect()
            return
        thAdmin = self.interpParent.GetThAdmin()
        nuPanes = thAdmin.GetNuIPPanes(self.provider, self.thName, ipMatrName)
        if nuPanes:
            for i in string.letters[:nuPanes]: self.chIPPane.Append(i + 'ij')
            self.chIPPane.SetStringSelection('aij') #Hopefully it'll be there
        self.UpdateFromIPPaneSelect()
        
    def OnIPPaneSelect(self, event):
        """An IP pane was selected"""
        self.UpdateFromIPPaneSelect()

    def UpdateFromIPPaneSelect(self):
        """Changes the data in the affected ctrls when the IP pane changes"""
        self.UpdateIPGrid()

    def UpdateIPGrid(self):
        """Puts values to the IP grid"""
        thAdmin = self.interpParent.GetThAdmin()
        selCmps = thAdmin.GetSelectedCompoundNames(self.provider, self.thName)
        self.currIPMatrix = self.chIPMatrix.GetStringSelection()
        self.currIPPane = self.chIPPane.GetSelection()
        ready = true
        if self.currIPMatrix == '' or self.currIPPane == -1: ready = false
        nuCmps = len(selCmps)
        for i in range(nuCmps):
            for j in range(nuCmps):
                if i != j:
                    if ready: 
                        val = thAdmin.GetIPValue(self.provider, self.thName,
                                                 self.currIPMatrix, selCmps[i],
                                                  selCmps[j], self.currIPPane)
                    else: val = None
                    self.ipGrid.SetCellValue(i, j, str(val))
        
    def OnCellChange(self, event):
        """An IP value changed"""
        if self.currIPMatrix == '' or self.currIPPane == -1:
            return
        thAdmin = self.interpParent.GetThAdmin()
        selCmps = thAdmin.GetSelectedCompoundNames(self.provider, self.thName)
        r = event.GetRow()
        c = event.GetCol()
        value = self.ipGrid.GetCellValue(r, c)
        try: value = str(float(value))
        except: value = str(None)
        code = 'thAdmin.SetIPValue("'
        code += self.provider + '", "'
        code += self.thName + '", "'
        code += self.currIPMatrix + '", "' + selCmps[r] + '", "'
        code += selCmps[c] + '", ' + str(self.currIPPane) + ', ' + value + ')'
        self.interpParent.SendAndExecCode(code)
        
    def OnCellLeftDClick(self, event):
        """Begin editing"""
        if event.GetRow() != event.GetCol(): 
            grid = event.GetEventObject()
            grid.EnableCellEditControl()
        event.Skip()
        
    def GetControl(self, id, type):
        return wxPyTypeCast(self.FindWindowById(id), type)
    

ID_LBL_PropPkg = 10018
ID_LBL_PropPkgDesc = 10019
ID_LBL_IPMatrix = 10020
ID_CH_IPMatrix = 10021
ID_LBL_IPPane = 10022
ID_CH_IPPane = 10023
ID_GRID = 10024

def IPSelectionBase( parent, call_fit = true, set_sizer = true ):
    item0 = wxBoxSizer( wxVERTICAL )
    
    item1 = wxBoxSizer( wxHORIZONTAL )
    
    item2 = wxStaticText( parent, ID_LBL_PropPkg, "Property Package:", wxDefaultPosition, wxDefaultSize, 0 )
    item2.SetFont( wxFont( 12, wxROMAN, wxNORMAL, wxBOLD ) )
    item1.AddWindow( item2, 0, wxALIGN_CENTRE|wxALL, 5 )

    item3 = wxStaticText( parent, ID_LBL_PropPkgDesc, "Peng-Robinson", wxDefaultPosition, wxDefaultSize, 0 )
    item3.SetFont( wxFont( 12, wxROMAN, wxNORMAL, wxNORMAL ) )
    item1.AddWindow( item3, 0, wxALIGN_CENTRE|wxALL, 5 )

    item0.AddSizer( item1, 0, wxGROW|wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    item5 = wxStaticBox( parent, -1, "IP" )
    item5.SetFont( wxFont( 10, wxROMAN, wxNORMAL, wxBOLD ) )
    item4 = wxStaticBoxSizer( item5, wxVERTICAL )
    
    item6 = wxBoxSizer( wxHORIZONTAL )
    
    item7 = wxStaticText( parent, ID_LBL_IPMatrix, "IP Matrix:", wxDefaultPosition, wxDefaultSize, 0 )
    item6.AddWindow( item7, 0, wxALIGN_CENTRE|wxALL, 5 )

    item8 = wxChoice( parent, ID_CH_IPMatrix, wxDefaultPosition, wxSize(180,-1), [], 0 )
    item6.AddWindow( item8, 0, wxALIGN_CENTRE|wxALL, 5 )

    item9 = wxStaticText( parent, ID_LBL_IPPane, "IP Pane:", wxDefaultPosition, wxDefaultSize, 0 )
    item6.AddWindow( item9, 0, wxALIGN_CENTRE|wxLEFT, 50 )

    item10 = wxChoice( parent, ID_CH_IPPane, wxDefaultPosition, wxSize(100,-1), [], 0 )
    item6.AddWindow( item10, 0, wxALIGN_CENTRE|wxALL, 5 )

    item4.AddSizer( item6, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    item0.AddSizer( item4, 0, wxALIGN_CENTER_VERTICAL|wxALL|wxSHAPED, 5 )

    item12 = wxStaticBox( parent, -1, "Values" )
    item12.SetFont( wxFont( 10, wxROMAN, wxNORMAL, wxBOLD ) )
    item11 = wxStaticBoxSizer( item12, wxHORIZONTAL )
    
    item13 = wxGrid( parent, ID_GRID, wxDefaultPosition, wxSize(650,270), wxWANTS_CHARS )
    item13.CreateGrid( 10, 10 )
    item11.AddWindow( item13, 0, wxALIGN_CENTER_HORIZONTAL|wxALL, 5 )

    item0.AddSizer( item11, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    if set_sizer == true:
        parent.SetAutoLayout( true )
        parent.SetSizer( item0 )
        if call_fit == true:
            item0.Fit( parent )
            item0.SetSizeHints( parent )
    
    return item0

    
class FlashSelection(wxPanel):
    """Panel for editing FlashSettings"""
    def __init__(self, parent, ID, interpParent, provider, thName):
        """Initializes the panel

        parent -- Parent of the object
        ID -- id for the panel
        interpParent -- Parent of the interpreter
        provider -- Name of the thermo provider
        thName -- Name of the thermo case

        """   
        wxPanel.__init__(self, parent, ID, style=wxWANTS_CHARS)

        self.interpParent = interpParent
        self.provider = provider
        self.thName = thName

        
        #Create all the controls
        FlashSelectionBase(self, true, true)
        
        
        #Load some controls to variables
        self.btnReset = self.GetControl(ID_BTN_Reset, "wxButton")
        self.grid = self.GetControl(ID_GRID_FlashSet, "wxGrid")

        
        #Rest of code
        EVT_BUTTON(self, self.btnReset.GetId(), self.OnReset)
        EVT_GRID_CELL_LEFT_DCLICK(self.grid, self.OnCellLeftDClick)
        EVT_GRID_CELL_CHANGE(self.grid, self.OnCellChange)

        self.UpdateView()
    

    def OnReset(self, event):
        self.Reset()
        
        
    def Reset(self):
        thAdmin = self.interpParent.GetThAdmin()
        info = thAdmin.GetFlashSettingsInfo(self.provider, self.thName)
        nuSettings = len(info)
        for key in info:
            code = 'thAdmin.SetFlashSetting("' + self.provider + '", "' + self.thName
            if type('s') == type(info[key].defValue):
                code += '", "' + key + '", "' + info[key].defValue + '")'
            else:
                code += '", "' + key + '", ' + str(info[key].defValue) + ')'
            self.interpParent.SendAndExecCode(code)
##        if self.interpParent.GetAutoSolveStatus(): self.interpParent.Solve()
##        else: self.interpParent.Forget()
        
        
    def UpdateView(self):
        """Update what the controls show"""
        
        #Get the termo info
        thAdmin = self.interpParent.GetThAdmin()
        info = thAdmin.GetFlashSettingsInfo(self.provider, self.thName)
        nuSettings = len(info)
        
        #Resize the grid
        r = self.grid.GetNumberRows()
        if nuSettings < r: self.grid.DeleteRows(0, r - nuSettings)
        elif nuSettings > r: self.grid.AppendRows(nuSettings - r)
        self.grid.SetColLabelValue(0, "Setting")
        self.grid.SetColLabelValue(1, "Units")
        self.grid.SetRowLabelSize(220)
        
        #Fill it up
        i = 0
        for key in info:
            self.grid.SetRowLabelValue(i, key)
            val = thAdmin.GetFlashSetting(self.provider, self.thName, key)
            
            self.grid.SetCellValue(i, 0, str(val))
            
            if info[key].options:
                myLst = []
                for j in info[key].options: myLst.append(str(j))
                self.grid.SetCellEditor(i, 0, wxGridCellChoiceEditor(myLst))
            else:
                self.grid.SetCellEditor(i, 0, GridEditors.NumberEditor(self.grid))

            if info[key].unit:
                self.grid.SetCellValue(i, 1, info[key].unit.name)
                unitType = info[key].unit.typeID
                unitList = []
                for j in S42Glob.unitSystem.UnitsByType(unitType):
                    unitList.append(j.name)
                if len(unitList):
                    ed = GridEditors.UnitEditor(self.grid)
                    ed.SetUnitList(unitList)
                    self.grid.SetCellEditor(i, 1, ed)
                    self.grid.SetReadOnly(i, 1, false)
                else:
                    self.grid.SetReadOnly(i, 1, true)
            else:
                self.grid.SetCellValue(i, 1, "")
                self.grid.SetReadOnly(i, 1, true)
                
            i += 1
        self.grid.ForceRefresh()

    def OnCellChange(self, event):
        row = event.GetRow()
        col = event.GetCol()
        if col == VALUE_COL:
            settingName = self.grid.GetRowLabelValue(row)
            unitName = self.grid.GetCellValue(row, UNITS_COL)
            try: gridValue = float(self.grid.GetCellValue(row, VALUE_COL))
            except: gridValue = self.grid.GetCellValue(row, VALUE_COL)
            thAdmin = self.interpParent.GetThAdmin()
            info = thAdmin.GetFlashSettingsInfo(self.provider, self.thName)
            if info[settingName].unit:
                units = S42Glob.unitSystem.UnitsByPartialName(unitName, info[settingName].unit.typeID)
                unit = units[0]
                value = unit.ConvertToSim42(gridValue)
            else:
                value = gridValue
                  
            code = 'thAdmin.SetFlashSetting("' + self.provider + '", "' + self.thName
            if type('s') == type(value):
                code += '", "' + settingName + '", "' + value + '")'
            else:
                code += '", "' + settingName + '", ' + str(value) + ')'
            self.interpParent.SendAndExecCode(code)
##            if self.interpParent.GetAutoSolveStatus(): self.interpParent.Solve()
##            else: self.interpParent.Forget()
        elif col == UNITS_COL:
            unitName = self.grid.GetCellValue(row, UNITS_COL)
            #self.SetUnit(row, unitName)
        
    def OnCellLeftDClick(self, event):
        """Begin editing"""
        grid = event.GetEventObject()
        if not grid.IsCurrentCellReadOnly(): grid.EnableCellEditControl()
        event.Skip()
        
    def GetControl(self, id, type):
        return wxPyTypeCast(self.FindWindowById(id), type)

ID_BTN_Reset = 10025
ID_GRID_FlashSet = 10026

def FlashSelectionBase( parent, call_fit = true, set_sizer = true ):
    item0 = wxBoxSizer( wxVERTICAL )
    
    item2 = wxStaticBox( parent, -1, "Flash Settings" )
    item2.SetFont( wxFont( 10, wxROMAN, wxNORMAL, wxBOLD ) )
    item1 = wxStaticBoxSizer( item2, wxVERTICAL )
    
    item3 = wxButton( parent, ID_BTN_Reset, "Reset", wxDefaultPosition, wxDefaultSize, 0 )
    item1.AddWindow( item3, 0, wxALIGN_CENTER_VERTICAL|wxLEFT|wxTOP, 15 )

    item4 = wxGrid( parent, ID_GRID_FlashSet, wxDefaultPosition, wxSize(390,360), wxWANTS_CHARS )
    item4.CreateGrid(10, 2)
    item1.AddWindow( item4, 0, wxALIGN_CENTER_VERTICAL|wxALL, 15 )

    item0.AddSizer( item1, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5 )

    if set_sizer == true:
        parent.SetAutoLayout( true )
        parent.SetSizer( item0 )
        if call_fit == true:
            item0.Fit( parent )
            item0.SetSizeHints( parent )
    
    return item0


class CmpViewFrame(wxDialog):
    """Frame to view the properties of a selected compound"""
    def __init__(self, parent, interpParent, provider, thName, cmpName):
        style = wxDEFAULT_DIALOG_STYLE
        w, h = (550, 400)
        wxDialog.__init__(self, parent, -1, cmpName, wxDefaultPosition, wxSize(w, h), style)

        self.interpParent = interpParent
        self.provider = provider
        self.thName = thName
        self.cmpName = cmpName
        
        thAdmin = self.interpParent.GetThAdmin()

        #Label panel
        labelPanel =  wxPanel(self, -1, wxPoint(0, 0), wxSize(w, 70))
        
        style = wxSUNKEN_BORDER|wxST_NO_AUTORESIZE
        lblName = wxStaticText(labelPanel, -1, "Name:", wxPoint(5, 7), wxSize(50, 20))
        lblNameVal = wxStaticText(labelPanel, -1, self.cmpName, wxPoint(55, 5), wxSize(300, 20), style)
        lblNameVal.SetBackgroundColour(wxLIGHT_GREY)
        
        lblForm = wxStaticText(labelPanel, -1, "Formula:", wxPoint(5, 27), wxSize(50, 20))
        lblFormVal = wxStaticText(labelPanel, -1, "Not yet", wxPoint(55, 25), wxSize(300, 20), style)
        lblFormVal.SetBackgroundColour(wxLIGHT_GREY)
        
        lblCASN = wxStaticText(labelPanel, -1, "CASN:", wxPoint(5, 47), wxSize(50, 20))
        lblCASNVal = wxStaticText(labelPanel, -1, "Not yet", wxPoint(55, 45), wxSize(300, 20), style)
        lblCASNVal.SetBackgroundColour(wxLIGHT_GREY)
        
        button = wxButton(labelPanel, -1, "Close", wxPoint(w-100, 10))
        EVT_BUTTON(self, button.GetId(), self.OnCloseMe)
        
        #Notebook
        self.nb = wxNotebook(self, -1, wxPoint(0, 70), wxSize(w, h-70))

        #Here id refers to any type of data used for identifying the compound 
        idPropNames = thAdmin.GetCompoundPropertyNames(self.provider, CMP_ID_GRP)
        idPanel = wxPanel(self.nb, -1)
        self.nb.AddPage(idPanel, "ID")        
        self.idGrid = wxGrid(idPanel, -1, wxPoint(10, 0), wxSize(350, 200))
        self.idGrid.CreateGrid(len(idPropNames), 1) #Whatever value for rows
        self.idGrid.SetColLabelValue(0, "Value")
        self.idGrid.SetRowLabelSize(170)
        for i in range(len(idPropNames)):
            self.idGrid.SetRowLabelValue(i, idPropNames[i])
            val = str(thAdmin.GetCompoundProperties(self.provider, self.thName, self.cmpName, idPropNames[i]))
            self.idGrid.SetCellValue(i, 0, val)

        #Properties that don't depend on an equation
        propNames = thAdmin.GetCompoundPropertyNames(self.provider, CMP_NO_EQDEP_GRP)
        propPanel = wxPanel(self.nb, -1)
        self.nb.AddPage(propPanel, "Properties")        
        self.propGrid = wxGrid(propPanel, -1, wxPoint(10, 0), wxSize(350, 250))
        self.propGrid.CreateGrid(len(propNames), 1) #Whatever value for rows
        self.propGrid.SetColLabelValue(0, "Value")
        self.propGrid.SetRowLabelSize(170)
        vals = thAdmin.GetCompoundProperties(self.provider, self.thName, self.cmpName, propNames)
        for i in range(len(propNames)):
            self.propGrid.SetRowLabelValue(i, propNames[i])
            self.propGrid.SetCellValue(i, 0, str(vals[i]))

        EVT_CLOSE(self, self.OnCloseWindow)
        
    def OnCloseWindow(self, event):
        """Destroy"""
        self.Destroy()

    def OnCloseMe(self, event):
        self.Close(true)

