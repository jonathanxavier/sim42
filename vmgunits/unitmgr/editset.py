#!/bin/env python
#----------------------------------------------------------------------------
# Name:         editset.py
# Author:       XXXX
# Created:      XX/XX/XX
# Copyright:    
#----------------------------------------------------------------------------

from wxPython.wx import *
from unitmgr_wdr import *
import vmgunits

# WDR: classes

class EditSetDialog(wxDialog):
    def __init__(self, parent, id, title, set,
        pos = wxPyDefaultPosition, size = wxPyDefaultSize,
        style = wxDEFAULT_DIALOG_STYLE ):
        wxDialog.__init__(self, parent, id, title, pos, size, style)
        
        self.set = set
        self.unitmgr = parent
        self.units = parent.units
        self.typeID = None
        EditSetDlg( self, true )
        
        self.SetReturnCode(0)  # set failure mode
        self.LoadSetTypeList()
        
        # WDR: handler declarations for EditSetDialog
        EVT_CHOICE(self, ID_USE_UNIT, self.OnUseUnit)
        EVT_LISTBOX(self, ID_SETTYPELIST, self.OnSetTypeList)
        EVT_BUTTON(self, ID_CANCEL, self.OnCancel)
        EVT_BUTTON(self, ID_OK, self.OnOK)

    # WDR: methods for EditSetDialog

    def GetUseUnit(self):
        return wxPyTypeCast( self.FindWindowById(ID_USE_UNIT), "wxChoice" )

    def GetEditName(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDIT_NAME), "wxTextCtrl" )

    def GetSetTypeList(self):
        return wxPyTypeCast( self.FindWindowById(ID_SETTYPELIST), "wxListBox" )

    # WDR: handler implementations for EditSetDialog

    def OnUseUnit(self, event):
        """set the unit for the selected type"""
        choice = self.GetUseUnit()
        unitID = self.unitIDs[choice.GetSelection()]
        self.set[self.typeID] = unitID
        self.LoadSetTypeList()

    def OnSetTypeList(self, event):
        """reload the unit list when new type is selected"""
        lb = self.GetSetTypeList()
        sel = lb.GetSelection()
        self.typeID = self.setTypeIDs[sel]
        self.LoadUseUnit(self.typeID)

    def OnCancel(self, event):
        self.EndModal(ID_CANCEL)

    def OnOK(self, event):
        self.EndModal(ID_OK)        

    def LoadSetTypeList(self):
        """Load the type list with types and default units"""
        lb = self.GetSetTypeList()
        lb.Clear()
        set = self.set
        
        # map type name, unit id tuples from the set to types
        types = map(lambda x, u=self.units: (u.GetTypeName(x[0]),x[1]), set.items())
        #sort on the names
        types.sort(lambda x, y: cmp(x[0], y[0]))
        self.setTypeIDs = []
        for type in types:
            # get typeName and unit from the tuple
            typeName = type[0]
            unit = self.units.GetUnitWithID(type[1])
            pad = 20 - len(typeName)
            lb.Append(typeName + pad*' ' + unit.name)
            self.setTypeIDs.append(unit.typeID)

        if self.typeID:
            sel = self.setTypeIDs.index(self.typeID)
        else:
            sel = 0
            self.typeID = self.setTypeIDs[0]
        lb.SetSelection(sel)
        self.LoadUseUnit(self.setTypeIDs[sel])
        
    def LoadUseUnit(self, typeID):
        """load the use unit choice with the units with type typeID"""
        choice = self.GetUseUnit()
        choice.Clear()
        typeUnits = self.units.UnitsByType(typeID)
        typeUnits.sort(lambda x, y: cmp(x.name, y.name))
        self.unitIDs = []
        for unit in typeUnits:
            choice.Append(unit.name)
            self.unitIDs.append(unit.id)
        if self.set[typeID] in self.unitIDs:
            sel = self.unitIDs.index(self.set[typeID])
        else:
            sel = 0
        choice.SetSelection(sel)
        #self.OnTypeUnitList(None)


