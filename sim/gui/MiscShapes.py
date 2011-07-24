"""Module with shapes used in the simulator canvas

Classes:
UnitOperationShape -- Shape for a uo. Inherits from wxBitmapShape

"""

from wxPython.wx import *
from wxPython.ogl import *

class UnitOperationShape(wxBitmapShape):
    """Shape for a uo. Inherits from wxBitmapShape"""
    def __init__(self, name, type):
        wxBitmapShape.__init__(self)
        self.name = name
        self.type = type

    def SelectShape(self):
        """Selects the shape"""
        canvas = self.GetCanvas()
        dc = wxClientDC(canvas)
        canvas.PrepareDC(dc)
        redraw = false
        shapeList = canvas.GetDiagram().GetShapeList()
        toUnselect = []
        for s in shapeList:
            if s.Selected():
                # If we unselect it now then some of the objects in
                # shapeList will become invalid (the control points are
                # shapes too!) and bad things will happen...
                toUnselect.append(s)
        if toUnselect:
            for s in toUnselect:
                s.Select(false, dc)
            canvas.Redraw(dc)
        self.Select(true, dc)
