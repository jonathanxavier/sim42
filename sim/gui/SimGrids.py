import string, sys, os

from wxPython.wx import *
from wxPython.grid import *

from sim.solver.Variables import *
from sim.solver import S42Glob
import vmgunits.units
import GridEditors, GridRenderers
from Misc import BaseInterpreterParent, BaseObjectFrame, PortDisplayInfo

try: 
    from sim.gui import IMG_PATH
except:
    GUI_PATH = os.getcwd()
    IMG_FOLDER = 'images'
    IMG_PATH  = os.path.join(GUI_PATH, IMG_FOLDER)

VALUE_COL = 0
UNITS_COL = 1
DEF_UNIT = '--'

SHOW_MOLFRAC = 1
SHOW_MASSFRAC = 2
SHOW_VOLFRAC = 4

class PropertyGrid(wxGrid):
    def __init__(self, parent, interpParent, port, dispInfo=None, id=-1, pos=None, size=None):
        #w, h =  parent.GetSizeTuple()
        if not pos: pos = wxDefaultPosition
        if not size: size = wxSize(300, 300)
        wxGrid.__init__(self, parent, id, pos, size)
        
        self._wait = 0
        self._waitRow = None
        self._waitCol = None
        self._waitOldVal = None

        self.interpParent = interpParent
        if not dispInfo: dispInfo = PortDisplayInfo()
        self.info = dispInfo
        
        self.unitSystem = S42Glob.unitSystem

        self.CreateGrid(1, 2) #One row to begin with
        self.SetCellEditor(0, VALUE_COL, GridEditors.PropEditor(self))
        self.SetCellRenderer(0, VALUE_COL, GridRenderers.PropRenderer(self))
        self.SetCellEditor(0, UNITS_COL, GridEditors.UnitEditor(self))
        self.SetCellRenderer(0, UNITS_COL, GridRenderers.UnitRenderer(self))
        
        self.SetRowLabelSize(120)
        self.SetColLabelValue(0, "Value")
        self.SetColLabelValue(1, "Units")
        
        EVT_LEFT_DOWN(self.GetGridWindow(), self.OnLeftDown) 
        EVT_GRID_CELL_LEFT_DCLICK(self, self.OnCellLeftDClick)
        EVT_GRID_CELL_CHANGE(self, self.OnCellChange)

        self.SetPort(port) #This updates the view

    def OnLeftDown(self, event):
        self.GetGridWindow().SetFocus()
        event.Skip()
            
    def UpdateView(self):
        #Don't update if it is on wait
        if self._wait: return #Leave!!!!
        
        propNames = self.info.GetPropList()
        units = self.info.GetUnitList()
        portProps = self.port.GetProperties()
        nuProps = len(propNames)

        r = self.GetNumberRows()
        if nuProps < r: self.DeleteRows(nuProps, r - nuProps)
        elif nuProps > r: self.AppendRows(nuProps - r)
        for i in range(r, nuProps):
            self.SetCellEditor(i, VALUE_COL, GridEditors.PropEditor(self))
            self.SetCellRenderer(i, VALUE_COL, GridRenderers.PropRenderer(self))
            self.SetCellEditor(i, UNITS_COL, GridEditors.UnitEditor(self))
            self.SetCellRenderer(i, UNITS_COL, GridRenderers.UnitRenderer(self))
        for i in range(nuProps):
            propName = propNames[i]
            unit = units[i]
            self.UpdateRow(i, portProps[propName], unit)
        self.ForceRefresh()

    def UpdateRow(self, row, prop, unit):
        """Update property at row"""
        #Prop Name
        self.SetRowLabelValue(row, prop.GetName())

        #Prop value
        if not unit: gridValue = prop.GetValue()
        else: gridValue = unit.ConvertFromSim42(prop.GetValue())        
        self.SetCellValue(row, VALUE_COL, str(gridValue))

        #Format prop
        status = prop.GetCalcStatus()
        rend = self.GetCellRenderer(row, VALUE_COL)
        if hasattr(rend, 'SetStatusFlag'):
            rend.SetStatusFlag(status)
            fnt = rend.GetFont()
            self.SetCellFont(row, VALUE_COL, fnt)
        if status & (CALCULATED_V | PASSED_V): self.SetReadOnly(row, VALUE_COL, true)
        else: self.SetReadOnly(row, VALUE_COL, false)

        #Units value
        if not unit: unitName = DEF_UNIT
        else: unitName = unit.name
        self.SetCellValue(row, UNITS_COL, unitName)

        #Format unit
        rend = self.GetCellRenderer(row, UNITS_COL)
        if hasattr(rend, 'SetStatusFlag'):
            rend.SetStatusFlag(status)
            fnt = rend.GetFont()
            self.SetCellFont(row, UNITS_COL, fnt)
        self.UpdateUnitEditor(row, UNITS_COL, unit)


    def UpdateUnitEditor(self, row, col, unit):
        """Update the list of the unit editor"""
        if not unit: unitType = None
        else: unitType = unit.typeID
        unitList = []
        for i in self.unitSystem.UnitsByType(unitType):
            unitList.append(i.name)
        if len(unitList):
            ed = self.GetCellEditor(row, col)
            ed.SetUnitList(unitList)
            self.SetReadOnly(row, col, false)
        else:
            self.SetReadOnly(row, col, true)


    def OnCellChange(self, event):
        row = event.GetRow()
        col = event.GetCol()

        #Don't wait for units        
        if not self._wait:
            if col == VALUE_COL:
                self.PassPropValueToPort(row)
            elif col == UNITS_COL:
                self.UpdatePropDisplayFromUnitChange(row)

        #Wait for units
        elif col == VALUE_COL:
            pass
        elif col == UNITS_COL:
            self.PassPropValueToPort(row)

    def PassPropValueToPort(self, row):                             
        """Updates the value of a port from its value in the grid with the current units from the grid"""

        self._wait = 0      #Not waiting anymore
        
        propName, unit = self.info.GetPropUnitTuple(row)

        #Check if units in grid are different to units in self.info.
        #If so... update self.info from grid
        if unit:
            unitName = self.GetCellValue(row, UNITS_COL)
            if unitName != unit.name:       
                self.info.SetUnit(row, unitName)
                propName, unit = self.info.GetPropUnitTuple(row)
        
        try:
            gridValue = float(self.GetCellValue(row, VALUE_COL))
            if not unit: sim42Value = gridValue
            else: sim42Value = unit.ConvertToSim42(gridValue)
        except: sim42Value = None

        status = FIXED_V
        if hasattr(self.GetCellEditor(row, VALUE_COL), 'IsEstimate'):
            if self.GetCellEditor(row, VALUE_COL).IsEstimate():
                status |= ESTIMATED_V
        code = 'parentFlowsh'
        for uo in self.uOpNames: code += '.GetChildUO("' + uo + '")'
        code += '.GetPort("' + self.portName + '").SetPropValue("' + propName
        code += '", ' + str(sim42Value) + ', ' + str(status) + ')'
        #self.interpParent.SendAndExecCode(code)
        
        est = ""
        if self.GetCellEditor(row, VALUE_COL).IsEstimate(): est = "~"
        unitTxt = ""
        
        cmd = "%s.%s %s= %s %s" %(self.port.GetPath(), propName, est, str(sim42Value), unitTxt)
        self.interpParent.Eval(cmd)
        

    def UpdatePropDisplayFromUnitChange(self, row):
        """Units changed but value in port is still the same"""
        unitName = self.GetCellValue(row, UNITS_COL)
        self.info.SetUnit(row, unitName)
        propName, unit = self.info.GetPropUnitTuple(row)
        prop = self.port.GetProperties()[propName]
        self.UpdateRow(row, prop, unit)

    def OnCellLeftDClick(self, event):
        grid = event.GetEventObject()
        if not grid.IsCurrentCellReadOnly(): grid.EnableCellEditControl()
        event.Skip()

    def SetPort(self, port):
        self.port = port
        #path is something like: /comp.Ideal.In
        path = self.port.GetPath()
        if path[0] == '/': path = path[1:]
        objs = string.split(path, ".")
        self.uOpNames = objs[:-1]           #List of uops
        self.portName = objs[-1:]   
        self.portName = self.portName[0]    #String with name of port
        
        self.UpdateView()
        
    def GetPort(self):
        return self.port
        
    def CleanUp(self):
        del self.port
      

class CompositionGrid(wxGrid):
    def __init__(self, parent, interpParent, port, fracType=SHOW_MOLFRAC, id=-1, pos=None, size=None):
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(300, 300)
        wxGrid.__init__(self, parent, id, pos, size)

        self._wait = 0        
        self.interpParent = interpParent
        
        self.LBL_MOLFRAC = "Mol Fraction"
        self.LBL_MASSFRAC = "Mass Fraction"
        self.LBL_VOLFRAC = "Vol Fraction"
                
        if not fracType: fracType = SHOW_MOLFRAC
        self.fracType = fracType
        self.edit = FRAC_VAR
        self.editCol = -1
        self.redoCols = true    #Flag
        self.colsOrder = []
        
        self.CreateGrid(0, 1)
        self.SetRowLabelSize(120)


        EVT_LEFT_DOWN(self.GetGridWindow(), self.OnLeftDown) 
        EVT_GRID_CELL_LEFT_DCLICK(self, self.OnCellLeftDClick)
        EVT_GRID_CELL_CHANGE(self, self.OnCellChange)
        EVT_SET_FOCUS(self.GetGridWindow(), self.OnSetFocus)
        EVT_KILL_FOCUS(self.GetGridWindow(), self.OnKillFocus)
        
        self.SetPort(port)

    def OnLeftDown(self, event):
        self.GetGridWindow().SetFocus()
        event.Skip()

    def OnSetFocus(self, event):
        pass

    def OnKillFocus(self, event):
        if not self._wait:
            event.Skip()
            return
        if not hasattr(self, 'port'):
            event.Skip()
            return
        try:
            if not self.GetGridWindow() == wxWindow_FindFocus().GetParent():
                self.UpdateValues()
        except:
            self.UpdateValues()

        event.Skip()

    def UpdateView(self):

        #Don't update if it is on wait
        if self._wait: return #Leave!!!!
        
        cmpNames = self.port.GetCompoundNames()
        nuCmps = len(cmpNames)
        
        #Let's work on the columns first
        if self.redoCols:

            if self.edit == FRAC_VAR: self.fracType |= SHOW_MOLFRAC
            elif self.edit == MASSFRAC_VAR: self.fracType |= SHOW_MASSFRAC
            
            self.colsOrder = []
            if self.fracType & SHOW_MOLFRAC: self.colsOrder.append(SHOW_MOLFRAC)
            if self.fracType & SHOW_MASSFRAC: self.colsOrder.append(SHOW_MASSFRAC)
            if self.fracType & SHOW_VOLFRAC: self.colsOrder.append(SHOW_VOLFRAC)
            
            if self.edit == FRAC_VAR: self.editCol = self.colsOrder.index(SHOW_MOLFRAC)
            elif self.edit == MASSFRAC_VAR: self.editCol = self.colsOrder.index(SHOW_MASSFRAC)

            nuCols = len(self.colsOrder)
            c = self.GetNumberCols()
            if nuCols < c: self.DeleteCols(nuCols, c - nuCols)
            elif nuCols > c: self.AppendCols(nuCols - c)
            for row in range(self.GetNumberRows()):
                for col in range(c, nuCols):
                    self.SetCellEditor(row, col, GridEditors.CompEditor(self))
                    self.SetCellRenderer(row, col, GridRenderers.CompRenderer(self))
        
            for i in range(nuCols):
                if self.colsOrder[i] == SHOW_MOLFRAC: lbl = self.LBL_MOLFRAC
                elif self.colsOrder[i] == SHOW_MASSFRAC: lbl = self.LBL_MASSFRAC
                elif self.colsOrder[i] == SHOW_VOLFRAC: lbl = self.LBL_VOLFRAC
                self.SetColLabelValue(i, lbl)
                self.SetColSize(i, 90)
            self.redoCols = false

        r = self.GetNumberRows()
        if nuCmps < r: self.DeleteRows(nuCmps, r - nuCmps)
        elif nuCmps > r: self.AppendRows(nuCmps - r)

        for i in range(r, nuCmps):
            for col in range(len(self.colsOrder)):
                self.SetCellEditor(i, col, GridEditors.CompEditor(self))
                self.SetCellRenderer(i, col, GridRenderers.CompRenderer(self))

        #Set the values
        molFracs = self.port.GetObject(FRAC_VAR)
        for cmp in range(nuCmps): 
            self.SetRowLabelValue(cmp, cmpNames[cmp])
        for col in range(len(self.colsOrder)):
            if self.colsOrder[col] == SHOW_MOLFRAC: fracs = molFracs.GetValues()
            elif self.colsOrder[col] == SHOW_MASSFRAC: fracs = self.port.GetObject(MASSFRAC_VAR).GetValues()
            elif self.colsOrder[col] == SHOW_VOLFRAC: fracs = self.port.GetObject(FRAC_VAR).GetValues()
            for cmp in range(nuCmps): 
                self.SetCellValue(cmp, col, str(fracs[cmp]))

                status = molFracs[cmp].GetCalcStatus()
                rend = self.GetCellRenderer(cmp, col)
                if hasattr(rend, 'SetStatusFlag'):
                    rend.SetStatusFlag(status)
                    fnt = rend.GetFont()
                    self.SetCellFont(cmp, col, fnt)
                if status & (CALCULATED_V | PASSED_V): self.SetReadOnly(cmp, col, true)
                else: self.SetReadOnly(cmp, col, false)
                if col != self.editCol: self.SetReadOnly(cmp, col, true)

        self.ForceRefresh()

    def SetDisplayInfo(self, fracType):
        """Sets which fractions are displayed among SHOW_MOLFRAC | SHOW_MASSFRAC | SHOW_VOLFRAC"""
        if not fracType: fracType = SHOW_MOLFRAC
        self.fracType = fracType
        self.redoCols = true
        self.UpdateView()

    def GetDisplayInfo(self):
        """Returns which fractions are displayed among SHOW_MOLFRAC | SHOW_MASSFRAC | SHOW_VOLFRAC"""
        return self.fracType
        
    def SetEditable(self, edit=FRAC_VAR):
        """Sets which fractions are the editable one. (FRAC_VAR or MASSFRAC_VAR)"""
        if edit not in (FRAC_VAR, MASSFRAC_VAR): edit = FRAC_VAR
        self.edit = edit
        self.redoCols = true
        self.UpdateView()
        
    def GetEditable(self):
        """Returns which fractions are the editable one. (FRAC_VAR or MASSFRAC_VAR)"""
        return self.edit
    
    def OnCellChange(self, event):
        """If any value chanes, put it on wait"""
        self._wait = 1
        self.ForceRefresh()

    def OnCellLeftDClick(self, event):
        grid = event.GetEventObject()
        if not grid.IsCurrentCellReadOnly(): grid.EnableCellEditControl()
        event.Skip()

    def UpdateValues(self):
        """Pass values to the port"""

        
        self._wait = 0 #Not waiting anymore
        cmpNames = self.port.GetCompoundNames()
        nuCmps = len(cmpNames)
        col = self.editCol
        for i in range(nuCmps):
            if self.IsReadOnly(i, col): return
            
        fracs = []
        status = FIXED_V
        for row in range(nuCmps):
            try: fracs.append(float(self.GetCellValue(row, col)))
            except: fracs.append(None)
            if hasattr(self.GetCellEditor(row, col), 'IsEstimate'):
                if self.GetCellEditor(row, col).IsEstimate():
                    status |= ESTIMATED_V

        code = 'parentFlowsh'
        for uo in self.uOpNames: code += '.GetChildUO("' + uo + '")'
        code += '.GetPort("' + self.portName + '").GetObject("' + self.edit
        code += '").SetValues(' + str(fracs) + ', ' + str(status) + ')'
        #self.interpParent.SendAndExecCode(code)
        
        est = ""
        if self.GetCellEditor(0, col).IsEstimate(): est = "~"
        
        vals = ' '.join(map(str, fracs))
        
        cmd = "%s.Fraction %s= %s" %(self.port.GetPath(), est, vals)
        self.interpParent.Eval(cmd)
        
    def GetPort(self):
        return self.port
        
    def SetPort(self, port):
        self.port = port
        #path is something like: /comp.Ideal.In
        path = self.port.GetPath()
        if path[0] == '/': path = path[1:]
        objs = string.split(path, ".")
        self.uOpNames = objs[:-1]           #List of uops
        self.portName = objs[-1:]   
        self.portName = self.portName[0]    #String with name of port
        
        self.UpdateView()
        
    def CleanUp(self):
        del self.port
        
class MaterialPortPanel(wxPanel):
    def __init__(self, parent, interpParent, port, pos=wxDefaultPosition):
        wxPanel.__init__(self, parent, -1, pos=pos)

##        splitter = wxSplitterWindow(self, -1, style=wxNO_3D|wxSP_3D)

##        mainSizer = wxBoxSizer(wxVERTICAL)    
        #panelSizer = wxBoxSizer(wxHORIZONTAL)
        self.panels = []

        panel0 = PropertyPanel(self, interpParent, port)
        self.panels.append(panel0)
##        mainSizer.Add(self.panels[0], 1, wxEXPAND|wxALIGN_LEFT)

        #Spacer between props and compositions
##        mainSizer.AddSpacer(20, 20, 0, wxALIGN_CENTRE)

##        panel1 = CompositionPanel(splitter, interpParent, port)
##        self.panels.append(panel1)
##        mainSizer.Add(panel, 1, wxEXPAND|wxALIGN_LEFT)

##        splitter.Initialize(panel0)
##        splitter.SetMinimumPaneSize(40)
####        splitter.SplitHorizontally(panel0, panel1, 100)
##        splitter.p0 = panel0
####        splitter.p1 = panel1
##
##        EVT_SPLITTER_SASH_POS_CHANGED(splitter, splitter.GetId(), self.OnSashChanged)
##        EVT_SPLITTER_SASH_POS_CHANGING(splitter, splitter.GetId(), self.OnSashChanging)


        
        #mainSizer.AddSizer(panelSizer, 1, wxEXPAND|wxALIGN_LEFT)
##        self.SetAutoLayout(true)
##        self.SetSizer(mainSizer)
##        mainSizer.SetSizeHints(self)
##        mainSizer.Fit(parent)
        self.Refresh()

    def OnSashChanged(self, evt):
        pass

    def OnSashChanging(self, evt):
        pass


    def CleanUp(self):
        for i in self.panels: i.CleanUp()

    def UpdateView(self):
        for i in self.panels: i.UpdateView()

    
class PropertyPanel(wxPanel):
    def __init__(self, parent, interpParent, port, pos=wxDefaultPosition, size=wxDefaultSize):
        wxPanel.__init__(self, parent, -1, pos=pos, size=size)
        
        #Properties box
        propBox = wxStaticBox(self, -1, "Properties")
        propBox.SetFont(wxFont(10, wxROMAN, wxNORMAL, wxBOLD))
        propBoxSizer = wxStaticBoxSizer(propBox, wxVERTICAL)
    
        #Properties grid
        self.grids = []
        self.grids.append(PropertyGrid(self, interpParent, port, size=size))
        propBoxSizer.Add(self.grids[0], 1, wxEXPAND|wxALL, 1)
##        EVT_SIZE(self.grids[0], self.OnSize)
    
        self.SetAutoLayout(true)
        self.SetSizer(propBoxSizer)
        propBoxSizer.Fit(parent)
        self.Refresh()

##    def OnSize(self, event):
##        print event.GetSize()
##        print 'a', self.grids[0].GetSize()
##        print 'b', self.grids[0].GetGridWindow().GetSize()
        
    def CleanUp(self):
        for i in self.grids: i.CleanUp()

    def UpdateView(self):
        for i in self.grids: i.UpdateView()

    def SetPort(self, port):
        for i in self.grids: i.SetPort(port)


class CompositionPanel(wxPanel):
    def __init__(self, parent, interpParent, port, pos=wxDefaultPosition):
        wxPanel.__init__(self, parent, -1, pos=pos)

        self.grids = []
        
        mainSizer = wxBoxSizer(wxVERTICAL)

        #Composition box
        compBox = wxStaticBox(self, -1, "Composition")
        compBox.SetFont(wxFont( 10, wxROMAN, wxNORMAL, wxBOLD ))
        compBoxSizer = wxStaticBoxSizer(compBox, wxVERTICAL)

        #Composition display box
        dispBox = wxStaticBox(self, -1, "Display")
        dispBoxSizer = wxStaticBoxSizer(dispBox, wxHORIZONTAL)

        #Display options
        self.cbMol = wxCheckBox(self, -1, "Mol Fraction", wxDefaultPosition, wxDefaultSize, 0)
        self.cbMol.SetValue(true)
        dispBoxSizer.AddWindow(self.cbMol, 0, wxALIGN_CENTRE|wxALL, 5)
        
        self.cbMass = wxCheckBox(self, -1, "Mass Fraction", wxDefaultPosition, wxDefaultSize, 0)
        self.cbMass.SetValue(true)
        dispBoxSizer.AddWindow(self.cbMass, 0, wxALIGN_CENTRE|wxALL, 5)
        
        self.cbVol = wxCheckBox( self, -1, "Vol Fraction", wxDefaultPosition, wxDefaultSize, 0 )
        dispBoxSizer.AddWindow(self.cbVol, 0, wxALIGN_CENTRE|wxALL, 5)

        compBoxSizer.AddSizer(dispBoxSizer, 0, wxALIGN_CENTER_VERTICAL|wxALL, 2)
     

        #Edit stuff (mol or mass)
        editSizer = wxBoxSizer( wxHORIZONTAL )
        
        self.rbEdit = wxRadioBox( self, -1, "Editable", wxDefaultPosition, wxDefaultSize, 
                    ["Mole Frac","Mass Frac"] , 2, wxRA_SPECIFY_COLS )
        editSizer.AddWindow(self.rbEdit, 0, wxALIGN_CENTER_HORIZONTAL|wxALL, 5)
        self.btnLoadVals = wxButton(self, -1, "Load Vals", wxDefaultPosition, wxDefaultSize)
        editSizer.AddWindow(self.btnLoadVals, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5)

        compBoxSizer.AddSizer(editSizer, 0, wxALIGN_CENTER_VERTICAL|wxALL, 0)

        #Composition grid
        self.grids.append(CompositionGrid(self, interpParent, port, fracType=SHOW_MOLFRAC|SHOW_MASSFRAC, id=-1))
        compBoxSizer.AddWindow(self.grids[0], 1, wxEXPAND|wxALL, 0)

        mainSizer.AddSizer(compBoxSizer, 1, wxEXPAND)

        self.SetAutoLayout(true)
        self.SetSizer(mainSizer)
##        mainSizer.SetSizeHints(self)
        mainSizer.Fit(parent)
        self.Refresh()

        EVT_IDLE(self, self.OnIdle)
        EVT_RADIOBOX(self, self.rbEdit.GetId(), self.OnChangeEdit)
        EVT_CHECKBOX(self, self.cbMol.GetId(), self.OnShowMol)
        EVT_CHECKBOX(self, self.cbMass.GetId(), self.OnShowMass)
        EVT_CHECKBOX(self, self.cbVol.GetId(), self.OnShowVol)
        EVT_BUTTON(self, self.btnLoadVals.GetId(), self.OnLoadVals)

    def OnLoadVals(self, event):
        """Force loading of fractions"""
        self.grids[0].UpdateValues()
        
    def OnChangeEdit(self, event):
        """Make mol or mass fractions editable"""
        sel = event.GetInt()
        if sel == 0: self.grids[0].SetEditable(FRAC_VAR)
        elif sel == 1: self.grids[0].SetEditable(MASSFRAC_VAR)
            
    def OnShowMol(self, event):
        """Display mol fractions"""
        if event.Checked():
            self.grids[0].SetDisplayInfo(self.grids[0].GetDisplayInfo() | SHOW_MOLFRAC)
        else:
            self.grids[0].SetDisplayInfo(self.grids[0].GetDisplayInfo() & ~SHOW_MOLFRAC)
            
    def OnShowMass(self, event):
        """Display mass fractions"""
        if event.Checked():
            self.grids[0].SetDisplayInfo(self.grids[0].GetDisplayInfo() | SHOW_MASSFRAC)
        else:
            self.grids[0].SetDisplayInfo(self.grids[0].GetDisplayInfo() & ~SHOW_MASSFRAC)
            
    def OnShowVol(self, event):
        """Display volume fractions"""
        if event.Checked():
            self.grids[0].SetDisplayInfo(self.grids[0].GetDisplayInfo() | SHOW_VOLFRAC)
        else:
            self.grids[0].SetDisplayInfo(self.grids[0].GetDisplayInfo() & ~SHOW_VOLFRAC)

    def OnIdle(self, event):
        """Update de values of the controls according to info in the composition grid"""
        fracType = self.grids[0].GetDisplayInfo()
        self.cbMol.SetValue(fracType & SHOW_MOLFRAC)
        self.cbMass.SetValue(fracType & SHOW_MASSFRAC)
        self.cbVol.SetValue(fracType & SHOW_VOLFRAC)
            
    def CleanUp(self):
        for i in self.grids: i.CleanUp()

    def UpdateView(self):
        for i in self.grids: i.UpdateView()

    def SetPort(self, port):
        for i in self.grids: i.SetPort(port)

        
class EnergyPortPanel(wxPanel):
    def __init__(self, parent, interpParent, port, pos=wxDefaultPosition):
        wxPanel.__init__(self, parent, -1, pos=pos)
        
        mainSizer = wxBoxSizer(wxHORIZONTAL)
    
        #Properties box
        propBox = wxStaticBox(self, -1, "Energy")
        propBox.SetFont(wxFont(10, wxROMAN, wxNORMAL, wxBOLD))
        propBoxSizer = wxStaticBoxSizer(propBox, wxVERTICAL)
    
        #Properties grid
        self.grids = []
        dispInfo = PortDisplayInfo([ENERGY_VAR])
        self.grids.append(PropertyGrid(self, interpParent, port, dispInfo, id=-1, size=wxSize(300, 70)))
        propBoxSizer.Add(self.grids[0].Get, 1, wxEXPAND|wxALL, 1)

        mainSizer.Add(propBoxSizer, 1, wxEXPAND|wxALL, 5)
    
        self.SetAutoLayout(true)
        self.SetSizer(mainSizer)
        mainSizer.SetSizeHints(self)
        mainSizer.Fit(parent)
        self.Refresh()
        
    def CleanUp(self):
        for i in self.grids: i.CleanUp()

    def UpdateView(self):
        for i in self.grids: i.UpdateView()

    def SetPort(self, port):
        for i in self.grids: i.SetPort(port)

##class SignalPortPanel(wxPanel):
##    def __init__(self, parent, interpParent, port, pos=wxDefaultPosition):
##        wxPanel.__init__(self, parent, -1, pos=pos)
##        
##        mainSizer = wxBoxSizer(wxHORIZONTAL)
##    
##        #Properties box
##        propBox = wxStaticBox(self, -1, "Signal")
##        propBox.SetFont(wxFont(10, wxROMAN, wxNORMAL, wxBOLD))
##        propBoxSizer = wxStaticBoxSizer(propBox, wxVERTICAL)
##    
##        #Properties grid
##        self.grids = []
##        t = port.GetSignalType()
##        dispInfo = PortDisplayInfo([t])
##        self.grids.append(SignalGrid(self, interpParent, port, dispInfo, id=-1, size=wxSize(300, 70)))
##        propBoxSizer.Add(self.grids[0].Get, 1, wxEXPAND|wxALL, 1)
##
##        mainSizer.Add(propBoxSizer, 1, wxEXPAND|wxALL, 5)
##    
##        self.SetAutoLayout(true)
##        self.SetSizer(mainSizer)
##        mainSizer.SetSizeHints(self)
##        mainSizer.Fit(parent)
##        self.Refresh()
##        
##    def CleanUp(self):
##        for i in self.grids: i.CleanUp()
##
##    def UpdateView(self):
##        for i in self.grids: i.UpdateView()
##
##    def SetPort(self, port):
##        for i in self.grids: i.SetPort(port)



class MaterialPortFrame(BaseObjectFrame):
    def __init__(self, parent, log, interpParent=None, obj=None):
        BaseObjectFrame.__init__(self, parent, log, interpParent, obj)

        if not self.inObj:
            uOps = self.parentFlowsh.GetChildUnitOps() #List of tuples (name, uop)
            obj = uOps[0][1].GetPort('In')

        self.SetSize(wxSize(330, 600))

##        self.panels.append(MaterialPortPanel(self, self.interpParent, obj))
        splitter = wxSplitterWindow(self, -1, style=wxNO_3D|wxSP_3D)
        
        panel0 = PropertyPanel(splitter, self.interpParent, obj, size=wxSize(330, 245))
        self.panels.append(panel0)
        panel1 = CompositionPanel(splitter, self.interpParent, obj)
        
        splitter.Initialize(panel0)
        splitter.SetMinimumPaneSize(1)
        splitter.SplitHorizontally(panel0, panel1, 245)
        splitter.p0 = panel0
        splitter.p1 = panel0


        #"""Set icon"""
        fileName = os.path.join(IMG_PATH, 'sim42.ico')
        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
        self.SetIcon(icon)

        #"""Set title"""
        port = obj
        uOpName = port.GetParent().GetName()
        portName = port.GetName()
        self.SetTitle('Port "' + portName + '" of unit operation "' + uOpName + '"')

class EnergyPortFrame(BaseObjectFrame):
    def __init__(self, parent, log, interpParent=None, obj=None):
        BaseObjectFrame.__init__(self, parent, log, interpParent, obj)

        if not self.inObj:
            uOps = self.parentFlowsh.GetChildUnitOps() #List of tuples (name, uop)
            obj = uOps[0][1].GetPort('In')

        self.panels.append(EnergyPortPanel(self, self.interpParent, obj))

        #"""Set icon"""
        fileName = os.path.join(IMG_PATH, 'sim42.ico')
        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
        self.SetIcon(icon)

        #"""Set title"""
        port = obj
        uOpName = port.GetParent().GetName()
        portName = port.GetName()
        self.SetTitle('Port "' + portName + '" of unit operation "' + uOpName + '"')
        
        
##class SignalPortFrame(BaseObjectFrame):
##    def __init__(self, parent, log, interpParent=None, obj=None):
##        BaseObjectFrame.__init__(self, parent, log, interpParent, obj)
##
##        if not self.inObj:
##            uOps = self.parentFlowsh.GetChildUnitOps() #List of tuples (name, uop)
##            obj = uOps[0][1].GetPort('In')
##
##        self.panels.append(SignalPortPanel(self, self.interpParent, obj))
##
##        #"""Set icon"""
##        fileName = os.path.join(IMG_PATH, 'sim42.ico')
##        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
##        self.SetIcon(icon)
##
##        #"""Set title"""
##        port = obj
##        uOpName = port.GetParent().GetName()
##        portName = port.GetName()
##        self.SetTitle('Port "' + portName + '" of unit operation "' + uOpName + '"')


class PropertyFrame(BaseObjectFrame):
    def __init__(self, parent, log, interpParent=None, obj=None):
        BaseObjectFrame.__init__(self, parent, log, interpParent, obj)

        if not self.inObj:
            uOps = self.parentFlowsh.GetChildUnitOps() #List of tuples (name, uop)
            obj = uOps[0][1].GetPort('In')

        self.panels.append(PropertyPanel(self, self.interpParent, obj))

        #"""Set icon"""
        fileName = os.path.join(IMG_PATH, 'sim42.ico')
        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
        self.SetIcon(icon)

        #"""Set title"""
        port = obj
        uOpName = port.GetParent().GetName()
        portName = port.GetName()
        self.SetTitle('Properties of Port "' + portName + '" of unit operation "' + uOpName + '"')

class CompositionFrame(BaseObjectFrame):
    def __init__(self, parent, log, interpParent=None, obj=None):
        BaseObjectFrame.__init__(self, parent, log, interpParent, obj)

        if not self.inObj:
            uOps = self.parentFlowsh.GetChildUnitOps() #List of tuples (name, uop)
            obj = uOps[0][1].GetPort('In')

        self.panels.append(CompositionPanel(self, self.interpParent, obj))

        #"""Set icon"""
        fileName = os.path.join(IMG_PATH, 'sim42.ico')
        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
        self.SetIcon(icon)

        #"""Set title"""
        port = obj
        uOpName = port.GetParent().GetName()
        portName = port.GetName()
        self.SetTitle('Properties of Port "' + portName + '" of unit operation "' + uOpName + '"')


if __name__ == '__main__':
    import sys
    app = wxPySimpleApp()
    frame = MaterialPortFrame(None, sys.stdout)
##    frame = PropertyFrame(None, sys.stdout)
    frame.Centre(wxBOTH)
    frame.Show(true)
    app.MainLoop()
