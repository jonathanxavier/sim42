"""Grid renderers used in the GUI of the simulator

Classes:
NumberRenderer -- Generic renderer for numbers
PropRenderer -- Renderer for properties
CompRenderer -- Renderer for compositions
UnitRenderer -- Renderer for units

"""

from wxPython.wx import *
from wxPython.grid import *

from sim.solver.Variables import * 
from Preferences import prefs

#Note that these Renderers are highly related/dependant in its editor counterpart

class NumberRenderer(wxPyGridCellRenderer):
    """Renderer for properties"""    
    def __init__(self, grid):
        wxPyGridCellRenderer.__init__(self)

        self._grid = grid    
        self._decimals = prefs.GetPrefVal('decimals', 5)
        self._clrBk = self._defBk = wxWHITE
        self._clrTx = self._defTx = wxBLACK
        self._fnt = self._defFnt = wxFont(8, wxDEFAULT, wxNORMAL, wxNORMAL)

    def GetFont(self):
        """Renderer knows which is the appropriate font and the one in the grid attr could be wrong"""
        return self._fnt

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        """Draw"""

        clrBk = self._clrBk
        clrTx = self._clrTx

        dc.SetBackgroundMode(wxSOLID)
        if isSelected: dc.SetBrush(wxBrush(wxColour(0, 0, 128), wxSOLID))
        else: dc.SetBrush(wxBrush(clrBk, wxSOLID))
        dc.SetPen(wxTRANSPARENT_PEN)
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)
        dc.SetBackgroundMode(wxTRANSPARENT)
        
        dc.SetFont(self._fnt)
        if isSelected: dc.SetTextForeground(wxWHITE)
        else: dc.SetTextForeground(clrTx)

        text = grid.GetCellValue(row, col)
        format = '%.' + str(self._decimals) + 'f'
        try:
            text = format % float(text)
        except:
            text = str(None)
        x = rect.x + rect.width - 1
        y = rect.y + 1
        for i in range(len(text)-1,-1,-1):
            w, h = dc.GetTextExtent(text[i])
            x = x - w
            dc.DrawText(text[i], x, y)
            if x < rect.left + 5:
                break          

    def GetBestSize(self, grid, attr, dc, row, col):
        text = grid.GetCellValue(row, col)
        dc.SetFont(self._fnt)
        w, h = dc.GetTextExtent(text)
        return wxSize(w, h)

    def Clone(self):
        """Clone"""
        return NumberRenderer()


class PropRenderer(wxPyGridCellRenderer):
    """Renderer for properties"""    
    def __init__(self, grid):
        wxPyGridCellRenderer.__init__(self)

        self._grid = grid    
        self._status = 0
        self._decimals = prefs.GetPrefVal('decimals', 5)
        self._clrBk = self._defBk = wxWHITE
        self._clrTx = self._defTx = wxBLACK
        self._fnt = self._defFnt = wxFont(8, wxDEFAULT, wxNORMAL, wxNORMAL)
        self._clrBkWait = prefs.GetPrefVal('clrBkWait', self._defBk)
        self._clrTxWait = prefs.GetPrefVal('clrTxWait', self._defTx)
        
    def SetStatusFlag(self, status):
        """Load colors and fonts according to status"""

        if status & CALCULATED_V:
            self._clrBk = prefs.GetPrefVal('clrBkCalc', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxCalc', self._defTx)
            self._fnt = prefs.GetPrefVal('fntCalc', self._defFnt)
        elif status & PASSED_V: 
            self._clrBk = prefs.GetPrefVal('clrBkPass', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxPass', self._defTx)
            self._fnt = prefs.GetPrefVal('fntPass', self._defFnt)
        elif status & ESTIMATED_V: 
            self._clrBk = prefs.GetPrefVal('clrBkEst', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxEst', self._defTx)
            self._fnt = prefs.GetPrefVal('fntEst', self._defFnt)            
        elif status & FIXED_V: 
            self._clrBk = prefs.GetPrefVal('clrBkFixed', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxFixed', self._defTx)
            self._fnt = prefs.GetPrefVal('fntFixed', self._defFnt)
        elif status & UNKNOWN_V: 
            self._clrBk = prefs.GetPrefVal('clrBkUnk', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxUnk', self._defTx)
            self._fnt = prefs.GetPrefVal('fntUnk', self._defFnt)
        else:
            self._clrBk = self._defBk
            self._clrTx = self._defTx
            self._fnt = self._defFnt
            
        self._status = status


    def GetStatusFlag(self):
        """Status of the property (FIXED, CALCULATED, etc"""
        return self._status

    def GetFont(self):
        """Renderer knows which is the appropriate font and the one in the grid attr could be wrong"""
        return self._fnt

    def IsWaiting(self, row, col):
        """See if grid is waiting for something to happen in this cell"""
        if hasattr(self._grid, '_wait'):
            if self._grid._wait and row == self._grid._waitRow and col == self._grid._waitCol:
                return true
        return false

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        """Draw"""

        clrBk = self._clrBk
        clrTx = self._clrTx

        isWaiting = self.IsWaiting(row, col)
        if isWaiting:
            clrBk = self._clrBkWait
            clrTx = self._clrTxWait 

        dc.SetBackgroundMode(wxSOLID)
        if isSelected: dc.SetBrush(wxBrush(wxColour(0, 0, 128), wxSOLID))
        else: dc.SetBrush(wxBrush(clrBk, wxSOLID))
        dc.SetPen(wxTRANSPARENT_PEN)
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)
        dc.SetBackgroundMode(wxTRANSPARENT)
        
        dc.SetFont(self._fnt)
        if isSelected: dc.SetTextForeground(wxWHITE)
        else: dc.SetTextForeground(clrTx)

        text = grid.GetCellValue(row, col)
        format = '%.' + str(self._decimals) + 'f'
        try:
            text = format % float(text)
            if isWaiting: text += ' ...'
        except:
            text = str(None)
        x = rect.x + rect.width - 1
        y = rect.y + 1
        for i in range(len(text)-1,-1,-1):
            w, h = dc.GetTextExtent(text[i])
            x = x - w
            dc.DrawText(text[i], x, y)
            if x < rect.left + 5:
                break          

    def GetBestSize(self, grid, attr, dc, row, col):
        text = grid.GetCellValue(row, col)
        if self.IsWaiting(row, col): text += ' ...'
        dc.SetFont(self._fnt)
        w, h = dc.GetTextExtent(text)
        return wxSize(w, h)

    def Clone(self):
        """Clone"""
        return PropRenderer()

class CompRenderer(PropRenderer):
    """Renderer for compositions"""
    def __init__(self, grid):
        PropRenderer.__init__(self, grid)

    def IsWaiting(self, row, col):
        """See if grid is waiting for something to happen in this cell"""
        if hasattr(self._grid, '_wait'):
            if self._grid._wait:
                return true
        return false

    def Clone(self):
        """Clone"""
        return CompRenderer()


class UnitRenderer(wxPyGridCellRenderer):
    """Renderer for units"""    
    def __init__(self, grid):
        wxPyGridCellRenderer.__init__(self)

        self._grid = grid    
        self._status = 0
        self._clrBk = self._defBk = wxWHITE
        self._clrTx = self._defTx = wxBLACK
        self._fnt = self._defFnt = wxFont(8, wxDEFAULT, wxNORMAL, wxNORMAL)

        
    def SetStatusFlag(self, status):
        """Load colors and fonts according to status"""

        if status & CALCULATED_V:
            self._clrBk = prefs.GetPrefVal('clrBkCalc', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxCalc', self._defTx)
            self._fnt = prefs.GetPrefVal('fntCalc', self._defFnt)
        elif status & PASSED_V: 
            self._clrBk = prefs.GetPrefVal('clrBkPass', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxPass', self._defTx)
            self._fnt = prefs.GetPrefVal('fntPass', self._defFnt)
        elif status & ESTIMATED_V: 
            self._clrBk = prefs.GetPrefVal('clrBkEst', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxEst', self._defTx)
            self._fnt = prefs.GetPrefVal('fntEst', self._defFnt)            
        elif status & FIXED_V: 
            self._clrBk = prefs.GetPrefVal('clrBkFixed', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxFixed', self._defTx)
            self._fnt = prefs.GetPrefVal('fntFixed', self._defFnt)
        elif status & UNKNOWN_V: 
            self._clrBk = prefs.GetPrefVal('clrBkUnk', self._defBk)
            self._clrTx = prefs.GetPrefVal('clrTxUnk', self._defTx)
            self._fnt = prefs.GetPrefVal('fntUnk', self._defFnt)
        else:
            self._clrBk = self._defBk
            self._clrTx = self._defTx
            self._fnt = self._defFnt
            
        self._status = status


    def GetStatusFlag(self):
        """Status of the property (FIXED, CALCULATED, etc"""
        return self._status

    def GetFont(self):
        """Renderer knows which is the appropriate font and the one in the grid attr could be wrong"""
        return self._fnt

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        """Draw"""

        clrBk = self._clrBk
        clrTx = self._clrTx

        dc.SetBackgroundMode(wxSOLID)
        if isSelected: dc.SetBrush(wxBrush(wxColour(0, 0, 128), wxSOLID))
        else: dc.SetBrush(wxBrush(clrBk, wxSOLID))
        dc.SetPen(wxTRANSPARENT_PEN)
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)
        dc.SetBackgroundMode(wxTRANSPARENT)
        
        dc.SetFont(self._fnt)
        if isSelected: dc.SetTextForeground(wxWHITE)
        else: dc.SetTextForeground(clrTx)

        text = grid.GetCellValue(row, col)
        x = rect.x + 2
        y = rect.y + 1
        for ch in text:
            dc.DrawText(ch, x, y)
            w, h = dc.GetTextExtent(ch)
            x = x + w
            if x > rect.right - 12:
                break       

    def GetBestSize(self, grid, attr, dc, row, col):
        text = grid.GetCellValue(row, col)
        dc.SetFont(self._fnt)
        w, h = dc.GetTextExtent(text)
        return wxSize(w, h)

    def Clone(self):
        """Clone"""
        return UnitRenderer()


class SCellRendererTitle(wxPyGridCellRenderer):
    """Renderer for title like cells."""    
    def __init__(self):
        wxPyGridCellRenderer.__init__(self)
        self._clrBk = prefs.GetPrefVal('clrBkCellLbl')
        self._clrTx = prefs.GetPrefVal('clrTxCellLbl')
        self._fnt = prefs.GetPrefVal('fntCellLbl')
            
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):

        dc.SetBackgroundMode(wxSOLID)
        if isSelected: dc.SetBrush(wxBrush(wxColour(0, 0, 128), wxSOLID))
        else: dc.SetBrush(wxBrush(self._clrBk, wxSOLID))        
        dc.SetPen(wxTRANSPARENT_PEN)
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)
        dc.SetPen(wxWHITE_PEN)
        dc.DrawLine(rect.x, rect.y, rect.x + rect.width, rect.y)
        dc.DrawLine(rect.x, rect.y, rect.x, rect.y + rect.height)

        dc.SetPen(wxTRANSPARENT_PEN)
        dc.SetBackgroundMode(wxTRANSPARENT)
#        dc.SetFont(attr.GetFont())
        dc.SetFont(self._fnt)
        if isSelected: dc.SetTextForeground(wxWHITE)
        else: dc.SetTextForeground(self._clrTx)
        text = grid.GetCellValue(row, col)
        try: text = str(text)
        except: text = str(None)
        x = rect.x + 2
        y = rect.y + 1
        for ch in text:
            dc.DrawText(ch, x, y)
            w, h = dc.GetTextExtent(ch)
            x = x + w
            if x > rect.right - 12:
                break

    def GetBestSize(self, grid, attr, dc, row, col):
        text = grid.GetCellValue(row, col)
        #dc.SetFont(attr.GetFont())
        dc.SetFont(self._fnt)
        w, h = dc.GetTextExtent(text)
        return wxSize(w, h)

    def Clone(self):
        """Clone"""
        return SCellRendererTitle()

class SCellRendererTitleChoice(SCellRendererTitle):
    """Renderer for title like cells that have a choice ctrl as editor"""    
    def __init__(self):
        SCellRendererTitle.__init__(self)

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        SCellRendererTitle.Draw(self, grid, attr, dc, rect, row, col, isSelected)

        dc.SetBrush(wxBrush(wxBLACK, wxSOLID))
        if rect.width > 20:
            points=[wxPoint(rect.x + rect.width - 11, rect.y + 3),
                    wxPoint(rect.x + rect.width - 7, rect.y + 7),
                    wxPoint(rect.x + rect.width - 3, rect.y + 3)]
            dc.DrawPolygon(points)

    def Clone(self):
        """Clone"""
        return SCellRendererTitleChoice()

class GridRendererTest(wxGrid):
    def __init__(self, parent, log):      
        wxGrid.__init__(self, parent, -1, pos=wxPoint(0, 0),
                        size=wxSize(300, 300))
        self.log = log

        self.CreateGrid(10, 4)

        
        self.SetCellValue(1, 0, 'Unknown')
        self.SetCellRenderer(1, 1, PropRenderer(self))
        self.GetCellRenderer(1, 1).SetStatusFlag(UNKNOWN_V)
        self.SetCellValue(1, 1, '123.45')
        
        self.SetCellValue(2, 0, 'Fixed')
        self.SetCellRenderer(2, 1, PropRenderer(self))
        self.GetCellRenderer(2, 1).SetStatusFlag(FIXED_V)
        self.SetCellValue(2, 1, '1234.578')
        
        self.SetCellValue(3, 0, 'Calculated')        
        self.SetCellRenderer(3, 1, PropRenderer(self))
        self.GetCellRenderer(3, 1).SetStatusFlag(CALCULATED_V)
        self.SetCellValue(3, 1, '34.89')

        self.SetCellValue(4, 0, 'Passed')        
        self.SetCellRenderer(4, 1, PropRenderer(self))
        self.GetCellRenderer(4, 1).SetStatusFlag(PASSED_V)
        self.SetCellValue(4, 1, '4')        

        self.SetCellValue(5, 0, 'Estimated')        
        self.SetCellRenderer(5, 1, PropRenderer(self))
        self.GetCellRenderer(5, 1).SetStatusFlag(ESTIMATED_V)
        self.SetCellValue(5, 1, '12')               
        
        self.SetCellValue(6, 0, 'Title')        
        self.SetCellRenderer(6, 1, SCellRendererTitle())
        self.SetCellValue(6, 1, 'Title')  
        
        
        attr = wxGridCellAttr()
        attr.SetRenderer(PropRenderer(UNKNOWN_V))
        self.SetColAttr(3, attr)
        self.SetCellValue(1, 3, "234")

        self.SetColSize(0, 150)
        self.SetColSize(1, 150)
        self.SetColSize(2, 150)


class TestFrame(wxFrame):
    def __init__(self, parent, log):
        wxFrame.__init__(self, parent, -1, "Custom Grid Cell Renderer Test",
                         size=(640,480))
        grid = GridRendererTest(self, log)


if __name__ == '__main__':
    import sys
    app = wxPySimpleApp()
    frame = TestFrame(None, sys.stdout)
    frame.Show(true)
    app.MainLoop()
    