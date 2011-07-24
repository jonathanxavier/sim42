"""Base class for creating custom tables"""

from wxPython.wx import *
from wxPython.grid import *

from sim.solver.Variables import *
from sim.thermo.ThermoConstants import *
import GridEditors, GridRenderers

class CustomTable(wxPanel):
    """Panel with custom table"""
    def __init__(self, parent, interpParent, tableInfo, id=-1, pos=None, size=None):
        w, h =  parent.GetSizeTuple()
        if not pos: pos = wxPoint(0,0)
        if not size: size = wxSize(w, h)
        wxPanel.__init__(self, parent, id, pos, size)

        #Rows and columns used for titles
        self._rOffset = 2
        self._cOffset = 1

        #Basic info
        self.tableInfo = tableInfo
        self.interpParent = interpParent
        parentFlowsh = self.interpParent.GetParentFlowsh()

        #Available props for selection        
        thAdmin = self.interpParent.GetThAdmin()
        providers = thAdmin.GetAvThermoProviderNames()
        self.avProps = []
        if len(providers) > 0:
            self.avProps.extend([MOLEFLOW_VAR, MASSFLOW_VAR, ENERGY_VAR])
            self.avProps.extend(thAdmin.GetPropertyNames(providers[0]))
        else:
            self.avProps.extend(GetCommonProps())
        self.avProps.sort()
        
        parentFlowsh = self.interpParent.GetParentFlowsh()
        uoNames = parentFlowsh.GetChildUONames()
        
        button = wxButton(self, -1, "Add Port", wxPoint(5, 5))
        EVT_BUTTON(self, button.GetId(), self.OnAddPort)
        if len(uoNames) <= 0: button.Enable(false)
        
        button = wxButton(self, -1, "Add Prop", wxPoint(145, 5))
        EVT_BUTTON(self, button.GetId(), self.OnAddProp)       

        #Create grid
        self.grid = wxGrid(self, -1, wxPoint(10, 40), wxSize(500, 250))
        self.grid.SetDefaultCellBackgroundColour(wxLIGHT_GREY)
        self.grid.CreateGrid(self._rOffset, self._cOffset)
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)
        self.grid.SetGridLineColour(wxBLACK)
        
        #Block the top left cells
        self.grid.SetCellRenderer(0, 0, GridRenderers.SCellRendererTitle())
        self.grid.SetReadOnly(0, 0, true)
        self.grid.SetCellRenderer(1, 0, GridRenderers.SCellRendererTitle())
        self.grid.SetReadOnly(1, 0, true)

        #Events        
##        EVT_MOTION(self.grid.GetGridWindow(), self.OnMouseMotion)   
        EVT_GRID_CELL_LEFT_DCLICK(self.grid, self.OnCellLeftDClick)
        EVT_GRID_CELL_CHANGE(self.grid, self.OnCellChange)
        #Pop up editing control with a single click
        self.__enableEdit = 0
        EVT_IDLE(self.grid, self.__OnIdle)
##        EVT_GRID_CELL_LEFT_CLICK(self.grid, self.__OnSelectCell)
        EVT_GRID_CELL_RIGHT_CLICK(self.grid, self.OnDoPopup)
        EVT_GRID_SELECT_CELL(self.grid, self.OnGridSelectCell)
        EVT_GRID_RANGE_SELECT(self.grid, self.OnRangeSelect)
        
        self.UpdateView()

    def OnGridSelectCell(self, event):
        """ Track cell selections """
        # Save the last cell coordinates
        self._lastRow, self._lastCol = event.GetRow(), event.GetCol()
        event.Skip()
        
    def OnRangeSelect(self, event):
        """ Track which cells are selected so that copy/paste behavior can be implemented """
        # If a single cell is selected, then Selecting() returns false (0)
        # and range coords are entire grid.  In this case cancel previous selection.
        # If more than one cell is selected, then Selecting() is true (1)
        # and range accurately reflects selected cells.  Save them.
        # If more cells are added to a selection, selecting remains true (1)
        self._selected = None
        if event.Selecting():
            self._selected = ((event.GetTopRow(), event.GetLeftCol()),
                              (event.GetBottomRow(), event.GetRightCol()))
        event.Skip()
        
    def OnDoPopup(self, event):
    
        self._currRow = event.GetRow()
        self._currCol = event.GetCol()

        if self._currRow == -1 or self._currCol == -1:
            event.Skip()
            return
        if self._currRow < self._rOffset and self._currCol < self._cOffset:
            event.Skip()
            return
        
        menu = wxMenu()

        if self.grid.IsSelection():
            id = wxNewId()
            menu.AppendItem(wxMenuItem(menu, id, "Copy"))
            EVT_MENU(self, id, self.OnCopy)
#        self.grid.ClearSelection()
        else:
            if self._currCol >= self._cOffset:
                self.grid.SelectCol(self._currCol, false)            
                id = wxNewId()
                menu.AppendItem(wxMenuItem(menu, id, "Insert Col at " + str(self._currCol)))
                EVT_MENU(self, id, self.OnInsertCol)
            if self._currRow >= self._rOffset:
                self.grid.SelectRow(self._currRow, true)
                id = wxNewId()
                menu.AppendItem(wxMenuItem(menu, id, "Insert Row at " + str(self._currRow)))
                EVT_MENU(self, id, self.OnInsertRow)
                
            menu.AppendSeparator()

            if self._currCol >= self._cOffset:
                id = wxNewId()
                menu.AppendItem(wxMenuItem(menu, id, "Del Col " + str(self._currCol)))
                EVT_MENU(self, id, self.OnDelCol)
            if self._currRow >= self._rOffset:
                id = wxNewId()
                menu.AppendItem(wxMenuItem(menu, id, "Del Row " + str(self._currRow)))
                EVT_MENU(self, id, self.OnDelRow)

        x, y = event.GetPosition()

        self.PopupMenu(menu, wxPoint(x+30, y))
        menu.Destroy()

        self.grid.ForceRefresh()
        
        event.Skip()

    def OnInsertCol(self, event): self.InsertPort(self._currCol - self._cOffset)
    def OnInsertRow(self, event): self.InsertProp(self._currRow - self._rOffset)
    def OnDelCol(self, event): self.DelPort(self._currCol - self._cOffset)
    def OnDelRow(self, event): self.DelProp(self._currRow - self._rOffset)
    def OnAddPort(self, event): self.AddPort()
    def OnAddProp(self, event): self.AddProp()
    def OnCopy(self, event): self.Copy()

    def Copy(self):
        clipData = wxTextDataObject()
        cols = self.grid.GetNumberCols()
        rows = self.grid.GetNumberRows()
        #print lCol, rTrow, rCol, bRow
        init = true
        myStr = ''
        for r in range(0, rows):
            if init: lCol = 0
            something = false
            for c in range(lCol, cols):
                if self.grid.IsInSelection(r, c):
                    if not something: something = true
                    if init:
                        lCol = c
                        init = false
                    myStr += self.grid.GetCellValue(r, c) 
                if something: myStr += chr(WXK_TAB)
            if something:
                myStr = myStr[0:len(myStr)-1]
                myStr += '\n'
        myStr = myStr[0:len(myStr)-1]
        clipData.SetText(myStr)
        wxTheClipboard.Open()
        wxTheClipboard.SetData(clipData)
        wxTheClipboard.Close()
        
    def InsertPort(self, idx):
        parentFlowsh = self.interpParent.GetParentFlowsh()
        uoNames = parentFlowsh.GetChildUONames()
        if len(uoNames) <= 0: return
        portNames = parentFlowsh.chUODict[uoNames[0]].GetPortNames(MAT|ENE|IN|OUT)
        self.tableInfo.InsertPort(uoNames[0], portNames[0], idx)
        self.UpdateView()

    def InsertProp(self, idx):
        self.tableInfo.InsertProp(self.avProps[0], idx)
        self.UpdateView()
    
    def DelPort(self, idx):
        self.tableInfo.DelPort(idx)
        self.UpdateView()

    def DelProp(self, idx):
        self.tableInfo.DelProp(idx)
        self.UpdateView()

    def __OnIdle(self, event):
        if self.__enableEdit:
            if self.grid.CanEnableCellControl():
                self.grid.EnableCellEditControl()
            self.__enableEdit = 0
        event.Skip()

    def __OnSelectCell(self, event):
        row = event.GetRow()
        col = event.GetCol()
        if (row < self._rOffset and col >= self._cOffset) or \
           (row >= self._rOffset and col < self._cOffset): 
            self.__enableEdit = 1
        else:
            self.__enableEdit = 0
        event.Skip()

#To be implemented for tool tip
##    def OnMouseMotion(self, event):
##        x, y = event.GetPosition()
##        #print 'moving', x, y
##        row = self.grid.YToRow(y)
##        col = self.grid.XToCol(x)
##        #print row, col
##        #self.grid.GetGridWindow().SetToolTipString("Here is the ToolTip for (%d, %d)" % (row, col))
##        event.Skip()

    def AddPort(self):
        cols = self.grid.GetNumberCols()
        self.InsertPort(cols - self._cOffset)

    def AddProp(self):
        rows = self.grid.GetNumberRows()
        self.InsertProp(rows - self._rOffset)
                
    def UpdateView(self):
        uos, ports = self.tableInfo.GetUOPortLists()
        parentFlowsh = self.interpParent.GetParentFlowsh()
        uoNames = parentFlowsh.GetChildUONames()

        #Make sure uos are still there
        toDel = []
        for i in range(len(uos)):
            if uos[i] not in uoNames:
                toDel.append(i)
        toDel.reverse()
        for i in toDel: tableInfo.DelPort(i)

        #Update nu of rows
        props = self.tableInfo.GetPropList()
        r = self.grid.GetNumberRows() - self._rOffset
        nuProps = len(props)
        #Weird bug in wxPython where for some reason, the last row HAS
        #to be deleted and recreated to prevent a crash if a change
        #last occured in the last row
        if r:
            self.grid.DeleteRows(r-1+self._rOffset, 1)
            r = r - 1
        if nuProps < r: self.grid.DeleteRows(self._rOffset, r - nuProps)
        elif nuProps > r: self.grid.AppendRows(nuProps - r)

        #Update nu of cols
        c = self.grid.GetNumberCols() - self._cOffset
        nuUO = len(uos)
        if nuUO < c: self.grid.DeleteCols(self._cOffset, c - nuUO)
        elif nuUO > c: self.grid.AppendCols(nuUO - c)

        #Set values of props
        for i in range(nuProps):
            self.grid.SetCellValue(self._rOffset + i, 0, props[i])
            ed = wxGridCellChoiceEditor(list(self.avProps), false)
            self.grid.SetCellEditor(self._rOffset + i, 0, ed)
            self.grid.SetCellRenderer(self._rOffset + i, 0, GridRenderers.SCellRendererTitleChoice())
        
        #Now do the ports
        if not len(uos):
            #If there is nothing there, init with two ports
            if len(uoNames) > 0:
                for i in range(2):
                    self.grid.AppendCols(1)
                    self.grid.SetCellValue(0, self._cOffset + i, uoNames[0])
                    self.UpdateFromUOSelect(self._cOffset + i, uoNames[0])
                    ed = wxGridCellChoiceEditor(uoNames, false)
                    self.grid.SetCellEditor(0, self._cOffset + i, ed)
                    self.grid.SetCellRenderer(0, self._cOffset + i, GridRenderers.SCellRendererTitleChoice())
        else:
            cols = self.grid.GetNumberCols()
            toDel = []
            count = 0
            for i in range(len(uos)):
                portsNames = parentFlowsh.chUODict[uos[i]].GetPortNames(MAT|ENE|IN|OUT)
                #First check that the port is still there
                if not ports[i] in portsNames:
                    toDel.append(i)
                else:
                    if count >= self.grid.GetNumberCols() - self._cOffset: self.grid.AppendCols(1)
                    self.grid.SetCellValue(0, count + self._cOffset, uos[i])
                    ed = wxGridCellChoiceEditor(uoNames, false)
                    self.grid.SetCellEditor(0, count + self._cOffset, ed)
                    self.grid.SetCellRenderer(0, count + self._cOffset, GridRenderers.SCellRendererTitleChoice())

                    self.grid.SetCellValue(1, count + self._cOffset, ports[i])
                    ed = wxGridCellChoiceEditor(portsNames, false)
                    self.grid.SetCellEditor(1, count + self._cOffset, ed)
                    self.grid.SetCellRenderer(1, count + self._cOffset, GridRenderers.SCellRendererTitleChoice())
                    self.UpdateColVals(count + self._cOffset, uos[i], ports[i])
                    count += 1
            toDel.reverse()
            for i in toDel: tableInfo.DelPort(i)
                                        
    def UpdateFromUOSelect(self, col, uoName):
        parentFlowsh = self.interpParent.GetParentFlowsh()
        portsNames = parentFlowsh.chUODict[uoName].GetPortNames(MAT|ENE|IN|OUT)
        self.grid.SetCellValue(1, col, portsNames[0])
        ed = wxGridCellChoiceEditor(portsNames, false)
        self.grid.SetCellEditor(1, col, ed)
        self.grid.SetCellRenderer(1, col, GridRenderers.SCellRendererTitleChoice())
        self.UpdateFromPortSelect(col, uoName, portsNames[0])

    def UpdateFromPortSelect(self, col, uoName, portName):
        self.tableInfo.SetPort(uoName, portName, col-1)
        self.UpdateColVals(col, uoName, portName)

    def UpdateFromPropSelect(self, row, propName):
        self.tableInfo.SetProp(propName, row-self._rOffset)
        self.UpdateRowVals(row, propName)
        
    def UpdateColVals(self, col, uoName, portName):
        rows = self.grid.GetNumberRows()
        for i in range(rows - 2):
            parentFlowsh = self.interpParent.GetParentFlowsh()
            uo = parentFlowsh.chUODict[uoName]
            propName = self.grid.GetCellValue(i + self._rOffset, 0)
            propInfo = uo.GetPropInfo(portName, propName)
            if len(propInfo) > 0:
                self.grid.SetCellValue(i + self._rOffset, col, str(propInfo[0][1]))
                self.DefineEditorAndRenderer(propInfo[0][2], self.grid, i + 2, col)
            else:
                self.grid.SetCellValue(i + self._rOffset, col, str(None))
                self.DefineEditorAndRenderer(UNKNOWN_V, self.grid, i + 2, col)
                self.grid.SetReadOnly(i + self._rOffset, col,  true)
        self.grid.ForceRefresh()
        
    def UpdateRowVals(self, row, propName):
        cols = self.grid.GetNumberCols()
        uos, ports = self.tableInfo.GetUOPortLists()
        for i in range(cols - 1):
            parentFlowsh = self.interpParent.GetParentFlowsh()
            uo = parentFlowsh.chUODict[uos[i]]
            portName = ports[i]
            propInfo = uo.GetPropInfo(portName, propName)
            if len(propInfo) > 0:
                self.grid.SetCellValue(row, i + self._cOffset, str(propInfo[0][1]))
                self.DefineEditorAndRenderer(propInfo[0][2], self.grid, row, i + self._cOffset)
            else:
                self.grid.SetCellValue(row, i + self._cOffset, str(None))
                self.DefineEditorAndRenderer(UNKNOWN_V, self.grid, row, i + self._cOffset)
                self.grid.SetReadOnly(row, i + self._cOffset, true)
        self.grid.ForceRefresh()
        
    def DefineEditorAndRenderer(self, status, grid, row, col):
        grid.SetCellRenderer(row, col, GridRenderers.PropRenderer(status))
        if status & (CALCULATED_V | PASSED_V):
            grid.SetReadOnly(row, col, true)
        elif status & FIXED_V:
            grid.SetCellEditor(row, col, GridEditors.PropEditor(grid))
            grid.SetReadOnly(row, col, false)
        else :
            grid.SetCellEditor(row, col, GridEditors.PropEditor(grid))
            grid.SetReadOnly(row, col, false)

    def OnCellChange(self, event):
        row = event.GetRow()
        col = event.GetCol()
        uoName = self.grid.GetCellValue(0, col)
        portName = self.grid.GetCellValue(1, col)
        if row == 0 and col > 0: self.UpdateFromUOSelect(col, uoName)
        elif row == 1 and col > 0: self.UpdateFromPortSelect(col, uoName, portName)
        elif col >= self._cOffset:
            propName = self.grid.GetCellValue(row, 0)
            value = self.grid.GetCellValue(row, col)
            try: value = str(float(value))
            except: value = str(None)
            
            code = 'parentFlowsh.GetChildUO("' + uoName
            code += '").GetPort("' + portName + '").SetPropValue("' + propName
            code += '", ' + value + ', ' + str(FIXED_V) + ')'
            self.interpParent.SendAndExecCode(code)

            if self.interpParent.GetAutoSolveStatus(): self.interpParent.Solve()
            else:
                parentFlowsh = self.interpParent.GetParentFlowsh()
                uOp = parentFlowsh.chUODict[uoName]
                prop = uOp.GetPropInfo(portName, propName)
                self.DefineEditorAndRenderer(prop[0][2], self.propGrid, row, col)
        elif col == 0 and row >= self._rOffset:
            propName = self.grid.GetCellValue(row, 0)
            self.UpdateFromPropSelect(row, propName)
            
    def OnCellLeftDClick(self, event):
        grid = event.GetEventObject()
        grid.EnableCellEditControl()
        event.Skip()
        
class CustomTableInfo(object):
    """Holds the basic info to re-create a custom table"""
    def __init__(self):
        self._uos = []
        self._ports = []
        self._props = []
        for i in GetReqExtensivePropertyNames(): self.AddProp(i)
        for i in GetReqIntensivePropertyNames(): self.AddProp(i)

    def GetUOPortLists(self):
        return list(self._uos), list(self._ports)

    def SetPort(self, uoName, portName, idx):
        if idx+1 > len(self._uos):
            self.AddPort(uoName, portName)
        else:
            self._uos[idx] = uoName
            self._ports[idx] = portName

    def InsertPort(self, uoName, portName, idx):
        if idx+1 > len(self._uos):
            self.AddPort(uoName, portName)
        else:
            self._uos.insert(idx, uoName)
            self._ports.insert(idx, portName)

    def AddPort(self, uoName, portName):
        self._uos.append(uoName)
        self._ports.append(portName)

    def DelPort(self, idx):
        if idx >=0 and idx < len(self._uos):
            del self._uos[idx]
            del self._ports[idx]

    def GetPropList(self):
        return list(self._props)

    def AddProp(self, propName):
        self._props.append(propName)

    def SetProp(self, propName, idx):
        if idx+1 > len(self._props):
            self.AddProp(propName)
        else:
            self._props[idx] = propName

    def InsertProp(self, propName, idx):
        if idx+1 > len(self._props):
            self.AddProp(propName)
        else:
            self._props.insert(idx, propName)

    def DelProp(self, idx):
        if idx >= 0 and idx < len(self._props):
            del self._props[idx]
