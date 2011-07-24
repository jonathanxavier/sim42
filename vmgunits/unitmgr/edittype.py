#!/bin/env python
#----------------------------------------------------------------------------
# Name:         edittype.py
# Author:       XXXX
# Created:      XX/XX/XX
# Copyright:    
#----------------------------------------------------------------------------

from wxPython.wx import *
from unitmgr_wdr import *

# WDR: classes

class EditTypeDialog(wxDialog):
    def __init__(self, parent, id, title,
        pos = wxPyDefaultPosition, size = wxPyDefaultSize,
        style = wxDEFAULT_DIALOG_STYLE ):
        wxDialog.__init__(self, parent, id, title, pos, size, style)
        EditTypeDlg(self, true)
        
        # WDR: handler declarations for EditTypeDialog
        EVT_BUTTON(self, ID_CANCEL, self.OnCancel)
        EVT_BUTTON(self, ID_OK, self.OnOK)

    # WDR: methods for EditTypeDialog

    def GetEditTypeBase(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDITTYPEBASE), "wxTextCtrl" )

    def GetEditTypeName(self):
        return wxPyTypeCast( self.FindWindowById(ID_EDITTYPENAME), "wxTextCtrl" )

    # WDR: handler implementations for EditTypeDialog
    

    def OnCancel(self, event):
        self.EndModal(ID_CANCEL)

    def OnOK(self, event):
        self.EndModal(ID_OK)        


