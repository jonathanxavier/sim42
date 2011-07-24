import sys, string, code, traceback, os
from wxPython.wx import *
from sim.PyCrust import filling

class SPyFilling(filling.Filling):
    def __init__(self, parent, id=-1, pos=wxDefaultPosition, \
                 size=wxDefaultSize, style=wxSP_3D, name='Filling Window', \
                 ingredients=None, rootLabel=None):
        filling.Filling.__init__(self, parent, id, pos, size, \
                                     style, name, ingredients, \
                                     rootLabel)
        self.SetMinimumPaneSize(1)
