"""Administers the canvas of the simulator

Classes:
pfdEventHandler -- Handles events of a shape. Inherits from wxShapeEvtHandler
pfd -- Canvas where the uos as drawn. Inherits from wxShapeCanvas
__Cleanup -- Necessary class when wxShapeCanvas is used

"""

from wxPython.wx import *
from wxPython.ogl import *

wxOGLInitialize()

class pfdEventHandler(wxShapeEvtHandler):
    """Class that handles the events of the uo on the canvas"""
    def __init__(self, statbarFrame, pfdParent, uOpName):
        """Init the class"""
        wxShapeEvtHandler.__init__(self)
        self.statbarFrame = statbarFrame
        self.pfdParent = pfdParent
        self.uOpName = uOpName
        
    def UpdateStatusBar(self, shape):
        """Updates the data on the status bar"""
        x,y = shape.GetX(), shape.GetY()
        width, height = shape.GetBoundingBoxMax()
        self.statbarFrame.SetStatusText("Pos: (%d,%d)  Size: (%d, %d)" %
                                        (x, y, width, height))

    def OnLeftClick(self, x, y, keys = 0, attachment = 0):
        """Selects the shape"""
        myshape = self.pfdParent.pfd.imgsUO[self.uOpName]
        myshape.SelectShape()
        self.UpdateStatusBar(myshape)
        self.pfdParent.ChangeActiveParamPanel(myshape.name, myshape.type)
##        Really weird bug... if I print shape and myshape, they have exactly 
##        the same address but shape can't run the method SelectShape()
##        shape = self.GetShape()
##        print 'shape', shape        
##        print 'myshape', myshape
        
    def OnEndDragLeft(self, x, y, keys = 0, attachment = 0):
        """On end drag"""
        shape = self.GetShape()
        self.base_OnEndDragLeft(x, y, keys, attachment)
        if not shape.Selected():
            self.OnLeftClick(x, y, keys, attachment)
        self.UpdateStatusBar(shape)

    def OnSize(self, x, y):
        """On size"""
        self.base_OnSize(x, y)
        self.UpdateStatusBar(self.GetShape())


class pfd(wxShapeCanvas):
    """Canvas where all the uo are drawn"""
    def __init__(self, parent, mainFrame):
        """Init the canvas"""
        wxShapeCanvas.__init__(self, parent)
        maxWidth  = 1000
        maxHeight = 1000
        self.SetScrollbars(20, 20, maxWidth/20, maxHeight/20)
        self.mainFrame = mainFrame
        self.SetBackgroundColour(wxWHITE)
        self.diagram = wxDiagram()
        self.SetDiagram(self.diagram)
        self.diagram.SetCanvas(self)
        self.imgsUO = {}
        self.lines = {}
        self.save_gdi = []

    def GetMainObjectHolder(self):
        """Returns instance of the top most parent of the application"""
##      I don't think this is used anymore at all        
        return self.mainFrame

    def MyAddShape(self, shape, x, y, pen, brush, text, uOpName):
        """Adds a shape to the canvas"""
        shape.SetDraggable(true, true)
        shape.SetCanvas(self)
        shape.SetX(x)
        shape.SetY(y)
        if pen:    shape.SetPen(pen)
        if brush:  shape.SetBrush(brush)
        if text:   shape.AddText(text)
        #shape.SetShadowMode(SHADOW_RIGHT)
        self.diagram.AddShape(shape)
        shape.Show(true)

        evthandler = pfdEventHandler(self.mainFrame, self.mainFrame, uOpName)
        evthandler.SetShape(shape)
        evthandler.SetPreviousHandler(shape.GetEventHandler())
        shape.SetEventHandler(evthandler)
        dc = wxClientDC(self)
        self.PrepareDC(dc)        
        shape.Move(dc, shape.GetX(), shape.GetY())
        
        self.imgsUO[uOpName] = shape
        del dc

    def MyAddLine(self, pen, brush, text, fromUO, toUO, lineName):
        """Adds a line conectingo two uos"""
        line = wxLineShape()
        #shape.SetDraggable(true, true)
        line.SetCanvas(self)
        if pen:    line.SetPen(pen)
        if brush:  line.SetBrush(brush)
        if text:   line.AddText(text)
        
        fromShape = self.imgsUO[fromUO]
        toShape = self.imgsUO[toUO]
        
        line.AddArrow(ARROW_ARROW)
        line.MakeLineControlPoints(2)
        fromShape.AddLine(line, toShape)
        
        self.diagram.AddShape(line)
        line.Show(true)        
        dc = wxClientDC(self)
        self.PrepareDC(dc)        
        fromShape.Move(dc, fromShape.GetX(), fromShape.GetY())
        
        self.lines[lineName] = line
        del dc

    def CleanDiagram(self):
        """not implemented"""
        pass

    def __del__(self):
        """Get rid of everything"""
        for shape in self.diagram.GetShapeList():
            if shape.GetParent() == None:
                shape.SetCanvas(None)
                shape.Destroy()
        self.diagram.Destroy()

class __Cleanup:
    cleanup = wxOGLCleanUp
    def __del__(self):
        self.cleanup()

# when this module gets cleaned up then wxOGLCleanUp() will get called
__cu = __Cleanup()        