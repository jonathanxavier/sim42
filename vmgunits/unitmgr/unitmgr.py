#!/bin/env python
#----------------------------------------------------------------------------
# Name:         unitmgr.py
# Author:       XXXX
# Created:      XX/XX/XX
# Copyright:    
#----------------------------------------------------------------------------

import os, sys

from wxPython.wx import *

from unitmgr_wdr import *
from copy import copy
from vmgunits import units
import edititem, editset, edittype

# WDR: classes

class UnitMgrFrame(wxFrame):
    def __init__(self, parent, id, title,
        pos = wxPyDefaultPosition, size = wxPyDefaultSize,
        style = wxDEFAULT_DIALOG_STYLE | wxCAPTION | wxMINIMIZE_BOX |
                    wxMAXIMIZE_BOX | wxTHICK_FRAME ):
        wxFrame.__init__(self, parent, id, title, pos, size, style)
 
        self.CreateMyMenuBar()
        
        self.CreateStatusBar(1)
        self.SetStatusText("Units Manager")

        statusBar = self.GetStatusBar()   # need to get colour scheme bg colour
        bgColour = statusBar.GetBackgroundColour()
        self.SetBackgroundColour(bgColour)
                
        # insert main window here
        ManagerDialog( self, true )

        self.units = units.UnitSystem()
        
        self.Changed(0)
        self.currentSetName = 'SI'
        self.displayUnit = None
        self.currentToType = None
        self.currentToSet = 'SI'
        self.UpdateLists()
        self.GetConvertFromValue().SetValue('1')
        self.Convert()
        
        setList = self.GetSetList()
        unitList = self.GetItemsList()
        typeList = self.GetTypeList()
        typeUnitList = self.GetTypeUnitList()
        setUnitList = self.GetSetUnitList()
        
        if len(sys.argv) > 1 and sys.argv[1] == '-m':
            self.editMaster = 1
        else:
            self.editMaster = 0
        
        # WDR: handler declarations for UnitMgrFrame
        EVT_RIGHT_UP(setList, self.OnSetListRightUp)
        EVT_RIGHT_UP(unitList, self.OnUnitListRightUp)
        EVT_RIGHT_UP(typeList, self.OnTypeListRightUp)
        EVT_RIGHT_UP(typeUnitList, self.OnTypeUnitListRightUp)
        EVT_RIGHT_UP(setUnitList, self.OnSetUnitListRightUp)
        
        EVT_TEXT(self, ID_CONVERT_FROM_VALUE, self.OnConvertFromValue)
        EVT_CHOICE(self, ID_TO_UNIT_ITEM_CHOICE, self.OnToUnitItem)
        EVT_CHOICE(self, ID_TO_UNIT_SET_CHOICE, self.OnToUnitSet)
        EVT_NOTEBOOK_PAGE_CHANGED(self, ID_NOTEBOOK, self.OnNoteBook)
        EVT_LISTBOX(self, ID_SETUNITLIST, self.OnSetUnitList)
        EVT_LISTBOX(self, ID_SETLIST, self.OnSetList)
        EVT_LISTBOX(self, ID_TYPEUNITLIST, self.OnTypeUnitList)
        EVT_LISTBOX(self, ID_TYPELIST, self.OnTypeList)
        EVT_LISTBOX(self, ID_ITEMSLIST, self.OnItemsList)
        EVT_MENU(self, ID_ABOUT, self.OnAbout)
        EVT_MENU(self, ID_QUIT, self.OnQuit)
        EVT_MENU(self, ID_SAVE, self.OnSave)
        EVT_MENU(self, ID_CHANGE_USER, self.OnChangeUserDir)
        EVT_CLOSE(self, self.OnCloseWindow)
        EVT_SIZE(self, self.OnSize)
        EVT_UPDATE_UI(self, -1, self.OnUpdateUI)
        EVT_BUTTON(self, ID_QUIT, self.OnQuit)
        EVT_BUTTON(self, ID_SAVE, self.OnSave)
        
    # WDR: methods for UnitMgrFrame

    def GetToUnitItemChoice(self):
        return wxPyTypeCast( self.FindWindowById(ID_TO_UNIT_ITEM_CHOICE), "wxChoice" )

    def GetToUnitSetChoice(self):
        return wxPyTypeCast( self.FindWindowById(ID_TO_UNIT_SET_CHOICE), "wxChoice" )

    def GetToUnitName(self):
        return wxPyTypeCast( self.FindWindowById(ID_TO_UNIT_NAME), "wxStaticText" )

    def GetFromUnitName(self):
        return wxPyTypeCast( self.FindWindowById(ID_FROM_UNIT_NAME), "wxStaticText" )

    def GetConvertedValue(self):
        return wxPyTypeCast( self.FindWindowById(ID_CONVERTED_VALUE), "wxStaticText" )

    def GetConvertFromValue(self):
        return wxPyTypeCast( self.FindWindowById(ID_CONVERT_FROM_VALUE), "wxTextCtrl" )

    def GetNotebook(self):
        return wxPyTypeCast( self.FindWindowById(ID_NOTEBOOK), "wxNotebook" )

    def GetSetUnitList(self):
        return wxPyTypeCast( self.FindWindowById(ID_SETUNITLIST), "wxListBox" )

    def GetSetList(self):
        return wxPyTypeCast( self.FindWindowById(ID_SETLIST), "wxListBox" )

    def GetTypeUnitList(self):
        return wxPyTypeCast( self.FindWindowById(ID_TYPEUNITLIST), "wxListBox" )

    def GetTypeList(self):
        return wxPyTypeCast( self.FindWindowById(ID_TYPELIST), "wxListBox" )

    def GetNote(self):
        return wxPyTypeCast( self.FindWindowById(ID_NOTE), "wxTextCtrl" )

    def GetOperation(self):
        return wxPyTypeCast( self.FindWindowById(ID_OPERATION), "wxTextCtrl" )

    def GetUnitOffset(self):
        return wxPyTypeCast( self.FindWindowById(ID_UNIT_OFFSET), "wxTextCtrl" )

    def GetUnitScale(self):
        return wxPyTypeCast( self.FindWindowById(ID_UNIT_SCALE), "wxTextCtrl" )

    def GetUnitType(self):
        return wxPyTypeCast( self.FindWindowById(ID_UNIT_TYPE), "wxTextCtrl" )

    def GetUnitName(self):
        return wxPyTypeCast( self.FindWindowById(ID_UNIT_NAME), "wxTextCtrl" )

    def GetItemsList(self):
        return wxPyTypeCast( self.FindWindowById(ID_ITEMSLIST), "wxListBox" )

    def GetSave(self):
        return wxPyTypeCast( self.FindWindowById(ID_SAVE), "wxButton" )

    def BeenChangedWarning(self):
        """
        Warn that units have been changed but not saved
        return 1 if okay to proceed, otherwise 0
        """
        msgDlg = wxMessageDialog(self,
            'Unsaved changes have been made and will be lost\nDo you wish to proceed?',
            'Unsaved Changes',
            wxYES_NO | wxNO_DEFAULT )
        if msgDlg.ShowModal() == wxID_YES: return 1
        else: return 0
        
    def Changed(self, modified=1):
        """set modified flag"""
        self.hasBeenModified = modified
        self.GetSave().Enable(modified)
        self.GetMenuBar().GetMenu(0).Enable(ID_SAVE, modified)

    def UpdateLists(self):
        """Clear and update all list boxes"""
        self.UpdateItemsList()
        self.UpdateTypeList()
        self.UpdateSetList()
        
    def UpdateItemsList(self):
        """Clear items list box and load it with values"""
        listBox = self.GetItemsList()
        listBox.Clear()
        units = self.units.GetUnits()
        units.sort(lambda x, y: cmp(x.name, y.name))
        self.itemsListIDs = []
        for unit in units:
            name = unit.name
            pad = 25 - len(name)
            listBox.Append(name + pad*' ' + '(%s)' % unit.id)
            self.itemsListIDs.append(unit.id)
            
        if self.displayUnit:
            sel = self.itemsListIDs.index(self.displayUnit.id)
        else:
            sel = 0
        listBox.SetSelection(sel)
        self.OnItemsList(None)

    def UpdateTypeList(self):
        """Clear types list box and reload it"""
        lb = self.GetTypeList()
        lb.Clear()
        types = self.units.GetTypes()
        types.sort(lambda x, y: cmp(x.name, y.name))
        self.typeListIDs = []
        for type in types:
            pad = 20 - len(type.name)
            lb.Append(type.name + pad*' ' + '(%s)' % type.id)
            self.typeListIDs.append(type.id)
            
        if self.displayUnit:
            sel = self.typeListIDs.index(self.displayUnit.typeID)
        else:
            sel = 0
        lb.SetSelection(sel)
        self.OnTypeList(None)
    
    def SetChoiceType(self, newType):
        """
        update the unit conversion type and item choices to reflect
        the current displayUnit.
        """
        if self.currentToType == self.displayUnit.typeID: return
        self.currentToType = newType
        
        choice = self.GetToUnitItemChoice()
        choice.Clear()
        typeUnits = self.units.UnitsByType(newType)
        typeUnits.sort(lambda x, y: cmp(x.name, y.name))
        self.typeToUnitIDs = []
        for unit in typeUnits:
            choice.Append(unit.name)
            self.typeToUnitIDs.append(unit.id)
            
        try:
            set = self.units.GetUnitSet(self.currentToSet)
            setUnit = self.units.GetUnit(set, newType)
            sel = self.typeToUnitIDs.index(setUnit.id)
        except:
            sel = 0
        choice.SetSelection(sel)
    
    def LoadTypeUnitList(self, typeID):
        """Load the type unit list and to choice with units for type typeID"""
        lb = self.GetTypeUnitList()
        lb.Clear()
        typeUnits = self.units.UnitsByType(typeID)
        typeUnits.sort(lambda x, y: cmp(x.name, y.name))
        self.typeUnitListIDs = []
        for unit in typeUnits:
            pad = 20 - len(unit.name)
            lb.Append(unit.name + pad*' ' + '(%s)' % unit.id)
            self.typeUnitListIDs.append(unit.id)
        if self.displayUnit.id in self.typeUnitListIDs:
            sel = self.typeUnitListIDs.index(self.displayUnit.id)
        else:
            sel = 0
        lb.SetSelection(sel)
        self.OnTypeUnitList(None)

    def UpdateSetList(self):
        """Clear set list box and to choice and reload them"""
        lb = self.GetSetList()
        lb.Clear()
        choice = self.GetToUnitSetChoice()
        choice.Clear()
        setNames = self.units.GetSetNames()
        setNames.sort()
        for name in setNames:
            lb.Append(name)
            choice.Append(name)
        if self.currentSetName:
            sel = lb.FindString(self.currentSetName)
        else:
            sel = 0
        lb.SetSelection(sel)
        choice.SetSelection(sel)
        self.currentToSet = self.currentSetName

        self.OnSetList(None)
    
    def LoadSetUnitList(self):
        """Load the type unit list with units for type typeID"""
        lb = self.GetSetUnitList()
        lb.Clear()
        set = self.units.GetUnitSet(self.currentSetName)
        
        # map type name, unit id tuples from the set to types
        types = map(lambda x, u=self.units: (u.GetTypeName(x[0]),x[1]), set.items())
        #sort on the names
        types.sort(lambda x, y: cmp(x[0], y[0]))
        self.setTypeListIDs = []
        for type in types:
            # get typeName and unit from the tuple
            typeName = type[0]
            unit = self.units.GetUnitWithID(type[1])
            pad = 20 - len(typeName)
            lb.Append(typeName + pad*' ' + unit.name)
            self.setTypeListIDs.append(unit.typeID)
        try:
            sel = self.setTypeListIDs.index(self.displayUnit.typeID)
        except:
            sel = 0
        lb.SetSelection(sel)
        self.OnSetUnitList(None)        
        
    def SetDisplayUnitID(self, id):
        """set the unit whose properties are displayed"""
        unit = self.units.GetUnitWithID(id)
        self.displayUnit = unit
        self.GetUnitName().SetValue(unit.name + '   (%s)' % id)
        self.GetUnitType().SetValue(self.units.GetTypeName(unit.typeID))
        self.GetUnitScale().SetValue(str(unit.scale))
        self.GetUnitOffset().SetValue(str(unit.offset))
        self.GetOperation().SetValue(unit.RenderOperation())
        self.GetNote().SetValue(unit.notes)
        
        self.GetFromUnitName().SetLabel(unit.name)
        self.SetChoiceType(self.displayUnit.typeID)
        self.Convert()
        
    def Convert(self):
        """perform the appropriate conversion"""
        fromUnit = self.displayUnit
        sel = self.GetToUnitItemChoice().GetSelection()
        toUnit = self.units.GetUnitWithID(self.typeToUnitIDs[sel])
        self.GetToUnitName().SetLabel(toUnit.name)
        fromValue = self.GetConvertFromValue().GetValue()
        if fromValue:
            try:
                fromValue = float(fromValue)
                baseValue = fromUnit.ConvertToBase(fromValue)
                toValue = toUnit.ConvertFromBase(baseValue)
                self.GetConvertedValue().SetLabel(str(toValue))
            except:
                self.GetConvertedValue().SetLabel('---')
        
                    
    def CreateMyMenuBar(self):
        self.SetMenuBar( MyMenuBarFunc() )
    
    def CreatePopup(self, canEdit):
        """
        create the right click popup for list panes
        if canEdit is false, then edit and delete are disabled
        """
        popup = wxMenu('')
        popup.Append(1, "Add(Clone) ...", "")
        popup.Append(2, "Edit ...", "")
        popup.Append(3, "Delete ...", "")
        if not canEdit:
            popup.Enable(2, 0)
            popup.Enable(3, 0)
        return popup
    
    # WDR: handler implementations for UnitMgrFrame
    
    def OnSetListRightUp(self, event):
        """process right mouse click"""
        lb = event.GetEventObject()
        if self.editMaster ^ (not self.units.GetUnitSet(self.currentSetName).isMaster):
            canEdit = 1
        else:
            canEdit = 0
            
        popup = self.CreatePopup(canEdit)
        EVT_MENU(popup, 1, self.OnCloneSet)
        EVT_MENU(popup, 2, self.OnEditSet)
        EVT_MENU(popup, 3, self.OnDeleteSet)
        lb.PopupMenu(popup,event.GetPosition())
    
    def OnUnitListRightUp(self, event):
        """process right mouse click"""
        lb = event.GetEventObject()
        if self.editMaster ^ (self.displayUnit.id < 0):
            canEdit = 1
        else:
            canEdit = 0
        popup = self.CreatePopup(canEdit)
        EVT_MENU(popup, 1, self.OnCloneUnit)
        EVT_MENU(popup, 2, self.OnEditUnit)
        EVT_MENU(popup, 3, self.OnDeleteUnit)
        lb.PopupMenu(popup,event.GetPosition())
    
    def OnTypeListRightUp(self, event):
        """process right mouse click"""
        lb = event.GetEventObject()
        if self.editMaster ^ (self.displayUnit.typeID < 0):
            canEdit = 1
        else:
            canEdit = 0
        popup = self.CreatePopup(canEdit)
        EVT_MENU(popup, 1, self.OnCloneType)
        EVT_MENU(popup, 2, self.OnEditType)
        EVT_MENU(popup, 3, self.OnDeleteType)
        lb.PopupMenu(popup,event.GetPosition())

    def OnTypeUnitListRightUp(self, event):
        """process right mouse click"""
        lb = event.GetEventObject()
        if self.editMaster ^ (self.displayUnit.id < 0):
            canEdit = 1
        else:
            canEdit = 0
        popup = self.CreatePopup(canEdit)
        EVT_MENU(popup, 1, self.OnCloneUnit)
        EVT_MENU(popup, 2, self.OnEditUnit)
        EVT_MENU(popup, 3, self.OnDeleteUnit)
        lb.PopupMenu(popup,event.GetPosition())

    def OnSetUnitListRightUp(self, event):
        """process right mouse click"""
        lb = event.GetEventObject()
        if self.editMaster ^ (self.displayUnit.id < 0):
            canEdit = 1
        else:
            canEdit = 0
        popup = self.CreatePopup(canEdit)
        EVT_MENU(popup, 1, self.OnCloneUnit)
        EVT_MENU(popup, 2, self.OnEditUnit)
        EVT_MENU(popup, 3, self.OnDeleteUnit)
        lb.PopupMenu(popup,event.GetPosition())

    def OnCloneSet(self, event):
        """make a copy of the current unit set"""
        currentSet = self.units.GetUnitSet(self.currentSetName)
        clone = copy(currentSet)
        clone.isMaster = self.editMaster
        cloneName = self.currentSetName + '-clone'
        title = 'New Unit Set (Clone of %s)' % cloneName
        dlg = editset.EditSetDialog(self, -1, title, clone)
        dlg.GetEditName().SetValue(cloneName)
        while dlg.ShowModal() == ID_OK:
            name = dlg.GetEditName().GetValue()
            if not name in self.units.GetSetNames():
                self.units.AddSet(name, clone)
                self.currentSetName = name
                self.Changed()
                self.UpdateSetList()
                break
            alert = wxMessageDialog(self, "Set name '%s' is already used" % name,
            "Duplicate Set Name", wxOK|wxICON_ERROR )
            alert.CentreOnParent()
            alert.ShowModal()
            alert.Destroy()
            
    
    def OnCloneType(self, event):
        """more a create than a clone"""
        currentType = self.units.GetType(self.displayUnit.typeID)
        dlg = edittype.EditTypeDialog(self, -1, 'Unit Set')
        dlg.GetEditTypeBase().SetValue(currentType.name + '-base')
        dlg.GetEditTypeName().SetValue(currentType.name + '-clone')
        if dlg.ShowModal() == ID_OK:
            newName = dlg.GetEditTypeName().GetValue()
            newBase = dlg.GetEditTypeBase().GetValue()
            newType = units.UnitType()
            newType.name = newName
            if self.editMaster:
                newTypeID = self.units.AddMasterType(newType)
            else:
                newTypeID = self.units.AddUserType(newType)
            self.Changed()
            self.UpdateTypeList()
        
    def OnCloneUnit(self, event):
        """create a clone unit and call the edit dialog"""
        clone = copy(self.displayUnit)
        clone.name += '-clone'
        clone.id = 0  # impossible value
        title = 'New Unit (Clone of %s)' % clone.name
        dlg = edititem.EditItemDialog(self, -1, title, self.units, clone)
        if dlg.ShowModal() == ID_OK:
            if self.editMaster:
                self.units.AddMasterUnit(clone)
            else:
                self.units.AddUserUnit(clone)
            self.Changed()
            self.UpdateItemsList()
    
    def OnEditSet(self, event):
        """create a clone of the currently selected set and pass it
        to the edit dialog.  If dialog returns OK replace the current set
        with the clone"""        
        currentSet = self.units.GetUnitSet(self.currentSetName)
        clone = copy(currentSet)
        clone.isMaster = 0
        title = 'Editting Unit Set %s' % self.currentSetName
        dlg = editset.EditSetDialog(self, -1, title, clone)
        dlg.GetEditName().SetValue(self.currentSetName)
        while dlg.ShowModal() == ID_OK:
            name = dlg.GetEditName().GetValue()
            if name == self.currentSetName or not name in self.units.GetSetNames():
                self.units.DeleteSet(self.currentSetName)
                self.units.AddSet(name, clone)
                self.currentSetName = name
                self.Changed()
                self.UpdateSetList()
                break
            alert = wxMessageDialog(self, "Set name '%s' is already used" % name,
            "Duplicate Set Name", wxOK|wxICON_ERROR )
            alert.CentreOnParent()
            alert.ShowModal()
            alert.Destroy()
    
    def OnEditType(self, event):
        currentType = self.units.GetType(self.displayUnit.typeID)
        dlg = edittype.EditTypeDialog(self, -1, 'Unit Set')
        dlg.GetEditTypeName().SetValue(currentType.name)
        dlg.GetEditTypeBase().SetValue('---')
        dlg.GetEditTypeBase().Enable(0)
        if dlg.ShowModal() == ID_OK:
            currentType.name = dlg.GetEditTypeName().GetValue()
            self.Changed()
            self.UpdateTypeList()
    
    def OnEditUnit(self, event):
        """
        create a clone of the displayUnit and pass it to the edit dialog
        If dialog returns OK, replace displayUnit with the updated one in units
        """
        clone = copy(self.displayUnit)
        title = 'Edit Unit %s' % clone.name
        dlg = edititem.EditItemDialog(self, -1, title, self.units, clone)
        if dlg.ShowModal():
            self.units.ReplaceUnit(clone)
            self.Changed()
            self.UpdateItemsList()
            self.UpdateTypeList()
    
    def OnDeleteSet(self, event):
        """delete current unit set - ask for confirmation"""
        msg = 'Are you sure you wish to delete %s' % self.currentSetName
        dlg = wxMessageDialog(self, msg, "Confirm Delete", wxYES_NO)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wxID_YES:
            self.units.DeleteSet(self.currentSetName)
            self.currentSetName = None
            self.Changed()
            self.UpdateSetList()
        dlg.Destroy()
    
    def OnDeleteType(self, event):
        """delete current unit type - ask for confirmation"""
        currentType = self.units.GetType(self.displayUnit.typeID)
        msg = 'Are you sure you wish to delete type %s' % currentType.name
        dlg = wxMessageDialog(self, msg, "Confirm Delete", wxYES_NO)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wxID_YES:
            self.units.DeleteType(currentType.id)
            self.displayUnit = None
            self.Changed()
            self.UpdateItemsList()
            self.UpdateTypeList()
        dlg.Destroy()
    
    def OnDeleteUnit(self, event):
        """delete displayUnit - ask for confirmation"""
        msg = 'Are you sure you wish to delete %s' % self.displayUnit.name
        dlg = wxMessageDialog(self, msg, "Confirm Delete", wxYES_NO)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wxID_YES:
            self.units.DeleteUnit(self.displayUnit.id)
            self.displayUnit = None
            self.Changed()
            self.UpdateItemsList()
            self.UpdateTypeList()
        dlg.Destroy()
    
    def OnConvertFromValue(self, event):
        self.Convert()
        
    def OnToUnitItem(self, event):
        self.Convert()        

    def OnToUnitSet(self, event):
        """new to unit set chosen"""
        choice = self.GetToUnitSetChoice()
        self.currentToSet = choice.GetStringSelection()

        choice = self.GetToUnitItemChoice()
        set = self.units.GetUnitSet(self.currentToSet)
        setUnit = self.units.GetUnit(set, self.currentToType)
        if setUnit:
            sel = self.typeToUnitIDs.index(setUnit.id)
        else:
            sel = 0
        choice.SetSelection(sel)
        self.Convert()
        
    def OnNoteBook(self, event):
        if self.displayUnit:
            nb = self.GetNotebook()
            page = nb.GetSelection()
            if page == 0:
                lb = self.GetItemsList()
                try:
                    sel = self.itemsListIDs.index(self.displayUnit.id)
                except:
                    sel = 0
                lb.SetSelection(sel)
            elif page == 1:
                self.UpdateTypeList()                
            elif page == 2:
                if self.displayUnit:
                    typeID = self.displayUnit.typeID
                    unitID = self.displayUnit.id
                    
                    set = self.units.GetUnitSet(self.currentSetName)
                    if unitID not in set.values():
                        # not in current set - try to find set containing displayUnit
                        setNames = self.units.GetSetNames()
                        for name in setNames:
                            set = self.units.GetUnitSet(name)
                            if unitID in set.values():
                                self.currentSetName = name
                                break

                    lb = self.GetSetList()
                    sel = lb.FindString(self.currentSetName)
                    lb.SetSelection(sel)
                    self.LoadSetUnitList()
                
                    lb = self.GetSetUnitList()
                    sel = self.setTypeListIDs.index(typeID)    
                    lb.SetSelection(sel)            

    def OnSetUnitList(self, event):
        lb = self.GetSetUnitList()
        typeID = self.setTypeListIDs[lb.GetSelection()]
        set = self.units.GetUnitSet(self.currentSetName)
        unit = self.units.GetUnit(set, typeID)
        self.SetDisplayUnitID(unit.id)        

    def OnSetList(self, event):
        lb = self.GetSetList()
        self.currentSetName = lb.GetString(lb.GetSelection())         
        self.LoadSetUnitList()        

    def OnTypeUnitList(self, event):
        lb = self.GetTypeUnitList()
        id = self.typeUnitListIDs[lb.GetSelection()]
        self.SetDisplayUnitID(id)

    def OnTypeList(self, event):
        lb = self.GetTypeList()
        id = self.typeListIDs[lb.GetSelection()]
        self.LoadTypeUnitList(id)

    def OnItemsList(self, event):
        lb = self.GetItemsList()
        id = self.itemsListIDs[lb.GetSelection()]
        self.SetDisplayUnitID(id)

    def OnAbout(self, event):
        dialog = wxMessageDialog(self, "VMG Unit Manager 1.0\n(C)opyright Virtual Materials Group",
            "About Unit Manager", wxOK|wxICON_INFORMATION )
        dialog.CentreOnParent()
        dialog.ShowModal()
        dialog.Destroy()
    
    def OnSave(self, event):
        """save the changes to file"""
        try:
            self.units.Write(self.editMaster)
            self.Changed(0)
        except:
            dialog = wxMessageDialog(self, "Error saving - check permissions",
                "Error Saving!", wxOK|wxICON_ERROR )
            dialog.CentreOnParent()
            dialog.ShowModal()
            dialog.Destroy()
    
    def OnQuit(self, event):
        if self.hasBeenModified:
            dlg = wxMessageDialog(self, "Quit without saving?", "Quit without saving?", wxYES_NO)
            dlg.CentreOnParent()
            result = dlg.ShowModal()
            dlg.Destroy()
            if result != wxID_YES:
                return
           
        self.Close(true)
    
    def OnCloseWindow(self, event):
        self.Destroy()
    
    def OnSize(self, event):
        event.Skip(true)
    
    def OnUpdateUI(self, event):
        event.Skip(true)
    
    def OnChangeUserDir(self, event):
        """get the module path for vmgunits"""

        if self.hasBeenModified:
            if not self.BeenChangedWarning():
                return
        fileDlg = wxDirDialog(self,'Select the user data directory',
                                self.units.GetUserDir())
        fileDlg.ShowModal()
        userDir = fileDlg.GetPath()
        self.units.SetUserDir(userDir)
        self.Changed(0)
        self.UpdateLists()
        

#----------------------------------------------------------------------------

class UnitMgrApp(wxApp):
    
    def OnInit(self):
        frame = UnitMgrFrame(None, -1, "Unit System Manager")
        frame.Show(true)
        
        return true

#----------------------------------------------------------------------------

app = UnitMgrApp(1)
app.MainLoop()

