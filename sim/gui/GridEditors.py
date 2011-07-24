"""Grid editors used in the GUI of the simulator

Classes:
PropEditor -- Editor for properties
CompEditor -- Editor for compositions
UnitEditor -- Editor for units
GridEditorTest -- Grid for testing purposes
TestFrame -- Frame for GridEditorTest

"""

#!/usr/bin/env python

from wxPython.wx import *
from wxPython.grid import *
import math, string

class NumberEditor(wxPyGridCellEditor):
    """Generic editor for numbers"""
    def __init__(self, grid):
        wxPyGridCellEditor.__init__(self)
        self._grid = grid

    def Create(self, parent, id, evtHandler):
        """Called to create the control, which must derive from wxControl.

        *Must Override*
        
        """
        self._tc = wxTextCtrl(parent, id, "", style=wxTE_PROCESS_ENTER)
        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)
        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

        EVT_SET_FOCUS(self._tc, self.OnSetFocus)
        EVT_KILL_FOCUS(self._tc, self.OnKillFocus)
        
    def OnSetFocus(self, event):
        event.Skip()

    def OnKillFocus(self, event):
        if not self._grid.GetGridWindow() == wxWindow_FindFocus():
            self._grid.EnableCellEditControl(false)
            if hasattr(self._grid, 'UpdateValues'):
                self._grid.UpdateValues()
        event.Skip()
        
    def SetSize(self, rect):
        """Called to position/size the edit control within the cell rectangle.
        
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.

        """
        if rect.y == -1: y = 0
        else: y = rect.y        
        self._tc.SetDimensions(rect.x, y, rect.width+2, rect.height+2)

    def BeginEdit(self, row, col, grid):
        """

        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        *Must Override*

        """
        self.startValue = grid.GetTable().GetValue(row, col)
        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()
        self._tc.SetFocus()

        # Select the whole text
        self._tc.SetSelection(0, self._tc.GetLastPosition())
        
        self.row = row
        self.col = col


    def EndEdit(self, row, col, grid):
        """Complete the editing of the current cell.
        
        Returns true if the value
        has changed.  If necessary, the control may be destroyed.
        *Must Override*
        
        """

        changed = false
        val = self._tc.GetValue()
        if val != self.startValue:
            changed = true            
            try:
                val = str(eval(val, {}, globals()['math'].__dict__))
                float(val)
            except:
                val = str(None)
            grid.GetTable().SetValue(row, col, val) # update the table

        self.startValue = ''
        self._tc.SetValue('')
        return changed

    def StartingKey(self, evt):
        """
        
        If the editor is enabled by pressing keys on the grid, this will be
        called to let the editor do something about that first key if desired.

        """
        key = evt.GetKeyCode()
        ch = None
        if key in [WXK_NUMPAD0, WXK_NUMPAD1, WXK_NUMPAD2, WXK_NUMPAD3, 
                   WXK_NUMPAD4, WXK_NUMPAD5, WXK_NUMPAD6, WXK_NUMPAD7,
                   WXK_NUMPAD8, WXK_NUMPAD9]:
            ch = chr(ord('0') + key - WXK_NUMPAD0)

        elif key < 256 and key >= 0 and chr(key) in string.printable:
            ch = chr(key)
            if not evt.ShiftDown():
                ch = string.lower(ch)
                #395 =.   46 = '.'
        elif key == 395: ch = '.'
        if ch == ' ': ch = None
        if ch is not None:
            self._tc.SetValue(ch)
            self._tc.SetInsertionPoint(1)
        else:
            evt.Skip()

    def Reset(self):
        """Reset the value in the control back to its starting value"""
        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def Destroy(self):
        """final cleanup"""
        self.base_Destroy()

    def Clone(self):
        """Clone"""
        return NumberEditor()

class PropEditor(wxPyGridCellEditor):
    """Editor for floating point numbers."""
    def __init__(self, grid):
        wxPyGridCellEditor.__init__(self)
        self._grid = grid
        self._estimate = 0

    def IsEstimate(self):
        """Is cell an estimate value?"""
        return self._estimate
    
    def Create(self, parent, id, evtHandler):
        """Called to create the control, which must derive from wxControl.

        *Must Override*
        
        """
        self._tc = wxTextCtrl(parent, id, "", style=wxTE_PROCESS_ENTER)
        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)
        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

        EVT_SET_FOCUS(self._tc, self.OnSetFocus)
        EVT_KILL_FOCUS(self._tc, self.OnKillFocus)
        EVT_KEY_DOWN(self._tc, self.OnKeyDown)
        
    def OnSetFocus(self, event):
        event.Skip()

    def OnKillFocus(self, event):
        if not self._grid.GetGridWindow() == wxWindow_FindFocus():
            self._grid.EnableCellEditControl(false)
            if hasattr(self._grid, 'UpdateValues'):
                self._grid.UpdateValues()
        event.Skip()
        
    def OnKeyDown(self, evt):
        """If space bar was pressed... could be interpreted as a request for units"""
        self._wait = 0
        if evt.KeyCode() != WXK_SPACE:
            evt.Skip()
            return

        if evt.ControlDown():   # the edit control needs this key
            evt.Skip()
            return

        g = self._grid
        r = g.GetGridCursorRow()
        c = g.GetGridCursorCol()
        if g.IsReadOnly(r, c+1):
            evt.Skip()
            return

        g._wait = 1
        g._waitRow = r
        g._waitCol = c
        g._waitOldVal = g.GetTable().GetValue(r, c)

        g.EnableCellEditControl(false)
        success = g.MoveCursorRight(false)
        if not success:
            g._wait = 0
        else:
            g.MakeCellVisible(r, c+1)
            g.EnableCellEditControl(true)
            

    def SetSize(self, rect):
        """Called to position/size the edit control within the cell rectangle.
        
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.

        """
        if rect.y == -1: y = 0
        else: y = rect.y        
        self._tc.SetDimensions(rect.x, y, rect.width+2, rect.height+2)

    def BeginEdit(self, row, col, grid):
        """

        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        *Must Override*

        """
        self.startValue = grid.GetTable().GetValue(row, col)
        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()
        self._tc.SetFocus()

        # Select the whole text
        self._tc.SetSelection(0, self._tc.GetLastPosition())
        
        self.row = row
        self.col = col


    def EndEdit(self, row, col, grid):
        """Complete the editing of the current cell.
        
        Returns true if the value
        has changed.  If necessary, the control may be destroyed.
        *Must Override*
        
        """

        changed = false
        val = self._tc.GetValue()
        if val[0:1] == '~':
            val = val[1:]
            self._estimate = 1
        else:
            self._estimate = 0
        if val != self.startValue:
            changed = true            
            try:
                val = str(eval(val, {}, globals()['math'].__dict__))
                float(val)
            except:
                val = str(None)
            grid.GetTable().SetValue(row, col, val) # update the table

        self.startValue = ''
        self._tc.SetValue('')
        return changed

    def StartingKey(self, evt):
        """
        
        If the editor is enabled by pressing keys on the grid, this will be
        called to let the editor do something about that first key if desired.

        """
        key = evt.GetKeyCode()
        ch = None
        if key in [WXK_NUMPAD0, WXK_NUMPAD1, WXK_NUMPAD2, WXK_NUMPAD3, 
                   WXK_NUMPAD4, WXK_NUMPAD5, WXK_NUMPAD6, WXK_NUMPAD7,
                   WXK_NUMPAD8, WXK_NUMPAD9]:
            ch = chr(ord('0') + key - WXK_NUMPAD0)

        elif key < 256 and key >= 0 and chr(key) in string.printable:
            ch = chr(key)
            if not evt.ShiftDown():
                ch = string.lower(ch)
                #395 =.   46 = '.'
        elif key == 395: ch = '.'
        if ch == ' ': ch = None
        if ch is not None:
            self._tc.SetValue(ch)
            self._tc.SetInsertionPoint(1)
        else:
            evt.Skip()

    def Reset(self):
        """Reset the value in the control back to its starting value

        *Must Override*
        
        """
        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()

    def Destroy(self):
        """final cleanup"""
        self.base_Destroy()

    def Clone(self):
        """Clone"""
        return PropEditor()


class CompEditor(PropEditor):
    """Editor for floating point numbers."""
    def __init__(self, grid):
        PropEditor.__init__(self, grid)

    def Clone(self):
        """Clone"""
        return CompEditor()

class UnitEditor(wxPyGridCellEditor):
    """Editor for units"""
    def __init__(self, grid, unitList=[]):
        wxPyGridCellEditor.__init__(self)
        self._grid = grid
        self._unitList = unitList

    def SetUnitList(self, unitList):
        """Sets the list of units to be displayed"""
        self._unitList = unitList

    def GetUnitList(self, unitList):
        """Sets the list of units to be displayed"""
        return self._unitList
        
    def Create(self, parent, id, evtHandler):
        """Called to create the control, which must derive from wxControl.

        *Must Override*
        
        """
        self._ch = wxChoice(parent, id, choices=self._unitList)
        #EVT_CHOICE(parent, id, self.OnChoice)

        self.SetControl(self._ch)
        if evtHandler:
            self._ch.PushEventHandler(evtHandler)
            
        EVT_SET_FOCUS(self._ch, self.OnSetFocus)
        EVT_KILL_FOCUS(self._ch, self.OnKillFocus)
        
    def OnSetFocus(self, event):
        event.Skip()

    def OnKillFocus(self, event):
        if not self._grid.GetGridWindow() == wxWindow_FindFocus():
            self._grid.EnableCellEditControl(false)
            if hasattr(self._grid, 'UpdateValues'):
                self._grid.UpdateValues()
        event.Skip()
        
    def SetSize(self, rect):
        """Called to position/size the edit control within the cell rectangle.
        
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.

        """
        if rect.y == -1: y = 0
        else: y = rect.y        
        self._ch.SetDimensions(rect.x, y, rect.width+2, rect.height+2)

    def BeginEdit(self, row, col, grid):
        """

        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        *Must Override*

        """
        self.startValue = grid.GetTable().GetValue(row, col)
        idx = self._ch.FindString(self.startValue)
        if idx ==-1: idx = 0
        self._ch.SetSelection(idx)
        self._ch.SetFocus()


    def EndEdit(self, row, col, grid):
        """Complete the editing of the current cell.
        
        Returns true if the value
        has changed.  If necessary, the control may be destroyed.
        *Must Override*
        
        """
        changed = false
        val = self._ch.GetStringSelection()
        if val != self.startValue:
            changed = true
            grid.GetTable().SetValue(row, col, val) # update the table
        elif hasattr(self._grid, '_wait'):
            if grid._wait:
                changed = true

        self.startValue = ''
        return changed


    def Reset(self):
        """Reset the value in the control back to its starting value

        *Must Override*
        
        """
        idx = self._ch.FindString(self.startValue)
        if idx ==-1: idx = 0
        self._ch.SetSelection(idx)

    def Destroy(self):
        """final cleanup"""
        self.base_Destroy()

    def Clone(self):
        """Create a new object which is the copy of this one
        
        *Must Override*
        
        """
        return UnitEditor()


class GridEditorTest(wxGrid):
    def __init__(self, parent, log):      
        wxGrid.__init__(self, parent, -1, pos=wxPoint(0, 0),
                        size=wxSize(300, 300))
        self.log = log

        self.CreateGrid(10, 3)

        self.SetCellValue(1, 0, "Double")
        self.SetCellEditor(1, 1, PropEditor(self))
        self.SetCellValue(1, 1, "Try to edit this box")
        self.SetCellEditor(1, 2, UnitEditor(self, ['a','b','c']))

        self.SetCellValue(2, 0, "Double")
        self.SetCellEditor(2, 1, PropEditor(self))
        self.SetCellValue(2, 1, "Try to edit this box")
        self.SetCellEditor(2, 2, UnitEditor(self, ['a','b','c']))


        self.SetColSize(0, 150)
        self.SetColSize(1, 150)
        self.SetColSize(2, 150)


            
##            newRow = self.GetGridCursorRow() + 1
##            if newRow < self.GetTable().GetNumberRows():
##                self.SetGridCursor(newRow, 0)
##                self.MakeCellVisible(newRow, 0)
##            else:
##                # this would be a good place to add a new row if your app
##                # needs to do that
##                pass


class TestFrame(wxFrame):
    def __init__(self, parent, log):
        wxFrame.__init__(self, parent, -1, "Custom Grid Cell Editor Test",
                         size=(640,480))
        grid = GridEditorTest(self, log)


if __name__ == '__main__':
    import sys
    app = wxPySimpleApp()
    frame = TestFrame(None, sys.stdout)
    frame.Show(true)
    app.MainLoop()