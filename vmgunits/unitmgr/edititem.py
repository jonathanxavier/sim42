#!/bin/env python
#----------------------------------------------------------------------------
# Name:         edititem.py
# Author:       XXXX
# Created:      XX/XX/XX
# Copyright:    
#----------------------------------------------------------------------------

from wxPython.wx import *
from unitmgr_wdr import *
import vmgunits

# WDR: classes

class EditItemDialog(wxDialog):
    def __init__(self, parent, id, title, units, unit,
        pos = wxPyDefaultPosition, size = wxPyDefaultSize,
        style = wxDEFAULT_DIALOG_STYLE ):
        wxDialog.__init__(self, parent, id, title, pos, size, style)
        
        self.units = units   # passed unit system
        self.unit = unit     # passed unit
        
        EditUnitDialog( self, true )
        
        # set name
        self.GetEditUnitName().SetValue(unit.name)
        
        # set unit type
        lb = self.GetEditUnitType()
        lb.Clear()
        types = units.GetTypes()
        types.sort(lambda x, y: cmp(x.name, y.name))
        self.typeListIDs = []
        for type in types:
            lb.Append(type.name)
            self.typeListIDs.append(type.id)
            
        sel = self.typeListIDs.index(unit.typeID)
        lb.SetSelection(sel)
        
        # set scale, offset and note
        self.GetEditUnitScale().SetValue(str(unit.scale))
        self.GetEditUnitOffset().SetValue(str(unit.offset))
        self.GetEditUnitNote().SetValue(unit.notes)
        
        # set operation
        self.GetEditUnitOp().SetSelection(unit.operation - 1)

        # WDR: handler declarations for EditItemDialog
        EVT_BUTTON(self, ID_OK, self.OnOK)
        EVT_BUTTON(self, ID_CANCEL, self.OnCancel)

    # WDR: methods for EditItemDialog

    def GetEditUnitNote(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDIT_UNIT_NOTE), "wxTextCtrl" )

    def GetEditUnitOp(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDIT_UNIT_OP), "wxChoice" )

    def GetEditUnitOffset(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDIT_UNIT_OFFSET), "wxTextCtrl" )

    def GetEditUnitScale(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDIT_UNIT_SCALE), "wxTextCtrl" )

    def GetEditUnitType(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDIT_UNIT_TYPE), "wxChoice" )

    def GetEditUnitName(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDIT_UNIT_NAME), "wxTextCtrl" )

    def GetEditUnitName(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDIT_UNIT_NAME), "wxTextCtrl" )

    # WDR: handler implementations for EditItemDialog

    def OnOK(self, event):
        unit = self.unit
        unit.name = self.GetEditUnitName().GetValue()
        typeSel = self.GetEditUnitType().GetSelection()
        unit.typeID = self.typeListIDs[typeSel]
        
        try:
            unit.scale = float(self.GetEditUnitScale().GetValue())
        except:
            msg = wxMessageBox(self, 'Illegal scale value', 'Error', wxOK)
            msg.ShowModal()
            return

        try:
            unit.offset = float(self.GetEditUnitOffset().GetValue())
        except:
            msg = wxMessageBox(self, 'Illegal offset value', 'Error', wxOK)
            msg.ShowModal()
            return
        
        unit.operation = self.GetEditUnitOp().GetSelection() + 1
        unit.notes = self.GetEditUnitNote().GetValue()
        self.EndModal(ID_OK)

    def OnCancel(self, event):
        self.EndModal(ID_CANCEL)

        



