"""
Graphing tool - this is essentially the graphite package with some additions and fixes
"""

from graphite import *
import graphite
import numpy.oldnumeric

class Text(graphite.Text):
    """
    override graphite Text class which does not correctly initialize TextStyle
    """

    def __init__(self, text='?', pos=(0,0,0), style=None, angle=0, font=None):
        "Constructor: creates a text object at the given location"
        self.text = str(text)
        self.points = [pos]
        self.angle = angle
        if style is not None: self.style = style
        else: self.style = TextStyle(font=font)
        
class Graph(graphite.Graph):
    """
    override the draw method which has an extraneous print statement
    """

    def draw(self,canvas):
        "Draw this graph into the given SPING canvas."
        # Steps:
        #	1. break the axes and all elements into a big list of drawing primitives
        #		in 3D data coordinates, handled by the submit call
        #	2. transform to 3D view coordinates and sort by Z (i.e., distance
        #		from the camera)
        #	3. transform again to screen coordinates, and draw each one
        
        primitives = []

        self.submit(primitives)
            
        # transform by the frame (world to view) transformation
        viewtrans = self.getViewTrans()
        #print viewtrans
        for item in primitives:
                item.transform4x4(viewtrans)
        # ... we'll skip the sorting for now...
        
        # finally, transform to screen coordinates and draw
        scaleX = self.right - self.left
        offsetX = self.left + scaleX/2
        scaleY = -(self.bottom - self.top)
        offsetY = self.bottom + scaleY/2
        # build a 4x4 matrix that implements both scaling and translation of X and Y
        transformation = Numeric.array(
                                [ (scaleX,0,0,offsetX),
                                  (0,scaleY,0,offsetY),
                                  (0,0,1,0),
                                  (0,0,0,1)	] );
        for item in primitives:
            item.transform4x4(transformation)
            item.projectTo2D()
            item.draw(canvas)


            
def ScaleValues(values, numIncrements=10.0):
    '''
    figure out some reasonable axis scaling and return (minValue, maxValue)
    '''
    numIncrements = float(numIncrements)
    minValue = min(values)
    maxValue = max(values)
    deltaStep = (maxValue - minValue) / (numIncrements - 1)
    logStep = Numeric.floor(Numeric.log10(deltaStep))
    scaleFactor = numIncrements ** logStep
    scaledDelta = deltaStep / scaleFactor
    if scaledDelta < 1.25:
        scaledDelta = 1.25
    elif scaledDelta < 1.5:
        scaledDelta = 1.5
    elif scaledDelta < 2.0:
        scaledDelta = 2.0
    elif scaledDelta < 2.5:
        scaledDelta = 2.5
    elif scaledDelta < 5.0:
        scaledDelta = 5.0
    else:
        scaledDelta = 10.
        
    scaledMin = minValue / scaleFactor
    minValue = scaleFactor * scaledDelta * Numeric.floor( scaledMin / scaledDelta)
    maxValue = minValue + numIncrements * scaledDelta * scaleFactor
    return (minValue, maxValue)

