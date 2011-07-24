"""
simbapfd attempts to generate a navigation quality pfd for use with simba
"""
import sim.solver.Ports
from sim.solver.Variables import *
import piddlePIL
from piddlePIL import PILCanvas, Color, Font, red, green, blue, white, seashell
from sim.unitop.Compressor import EFFICIENCY_PORT

PFDINFO = 'SimbaPFD'
POSITION = 'pos'
RECURSION = 'recursion'
BOUNDINGBOX = 'boundingbox'

UP = 'Up'
DOWN = 'Down'
LEFT = 'Left'
RIGHT = 'Right'

DrawUnit = 5
UnitOpWidth = 20 * DrawUnit
UnitOpHeight = 20 * DrawUnit
ConnectorSeparation = DrawUnit
PortLength = ConnectorSeparation
StreamTrackWidth = 2 * DrawUnit    # number of stream tracks available vertically
StreamTrackHeight = 2 * DrawUnit   # number of stream tracks available horizontally
UnitOpCellTopOffset = StreamTrackHeight * ConnectorSeparation
UnitOpCellLeftOffset = StreamTrackWidth * ConnectorSeparation

UnitOpCellWidth = UnitOpWidth + 2 * PortLength + UnitOpCellLeftOffset
UnitOpCellHeight = UnitOpHeight + UnitOpCellTopOffset
 
MaxNameChars = 12
MaxTypeChars = 12

UopNameFont = Font(face='helvetica',size=10,bold=1)
UopTypeFont = Font(face='helvetica',size=10,bold=1)
UopNameColor = blue
UopTypeColor = green
UopFillColor = seashell
BackGroundColor = white

MaterialConnectionColor = blue
EnergyConnectionColor = red
SignalConnectionColor = green

class UopPositionMatrix(object):
    """
    matrix containing position of unit ops
    """
    def __init__(self):
        self.rows = []
        
    def AddRow(self, uop):
        self.rows.append([uop])
        #uopInfo.SetPosition((len(self.rows) - 1, 0))
        uop.info[PFDINFO][POSITION] = (len(self.rows) - 1, 0)
        
    def GetCell(self, pos):
        """
        return unit op info for position (row, col) pos
        """
        row, col = pos
        if row >= len(self.rows):
            return None
        if col >= len(self.rows[row]):
            return None
        return self.rows[row][col]
    
    def SetCell(self, pos, uop):
        """
        assign uopInfo to cell at position (row, col) pos
        """
        row, col = pos
        while row >= len(self.rows):
            self.rows.append([])
        while col >= len(self.rows[row]):
            self.rows[row].append(None)
        self.rows[row][col] = uop
        #uopInfo.SetPosition(pos)
        uop.info[PFDINFO][POSITION] = pos
        
    def GetMaxDimensions(self):
        rows = len(self.rows)
        cols = 0
        for row in self.rows:
            cols = max(cols, len(row))
        return (rows, cols)

class ConnectionIcon(object):
    def __init__(self, input, direction, point):
        """
        input is true or false
        direction is UP, DOWN, LEFT or RIGHT
        """
        self.input = input
        self.direction = direction
        (x,y) = self.point = point
        if input:
            step = -PortLength
        else:
            step = PortLength
        if   direction is LEFT:  x += step
        elif direction is RIGHT: x -= step
        elif direction is UP:    y -= step
        else:                    y += step
        
        self.point2 = (x,y)
        
    def VerticalLineLimits(self, verticalTrial):
        """
        set limits on verticalTrial so it doesn't cross icon
        """
        x,y = self.point
        x2,y2 = self.point2
        if self.direction is LEFT or self.direction is RIGHT:
            left = min(x, x2)
            right = max(x, x2)
            if verticalTrial.ptOrigin[0] >= left and verticalTrial.ptOrigin[0] <= right and \
               verticalTrial.topBound <= y and verticalTrial.bottomBound >= y:
                if verticalTrial.ptOrigin[1] < y:
                    verticalTrial.bottomBound = y - ConnectorSeparation
                    verticalTrial.bottomLeft = left - ConnectorSeparation
                    verticalTrial.bottomRight = right + ConnectorSeparation
                else:
                    verticalTrial.topBound = y + ConnectorSeparation
                    verticalTrial.topLeft = left - ConnectorSeparation
                    verticalTrial.topRight = right + ConnectorSeparation
        elif verticalTrial.ptOrigin[0] == x:
            top = min(y, y2)
            bottom = max(y, y2)
            if verticalTrial.bottomBound >= top and verticalTrial.topBound <= bottom:
                if verticalTrial.ptOrigin[1] < top:
                    verticalTrial.bottomBound = top - ConnectorSeparation
                    verticalTrial.bottomLeft = x - ConnectorSeparation
                    verticalTrial.bottomRight = x + ConnectorSeparation
                else:
                    verticalTrial.topBound = bottom + ConnectorSeparation
                    verticalTrial.topLeft = x - ConnectorSeparation
                    verticalTrial.topRight = x + ConnectorSeparation
                    
    def HorizontalLineLimits(self, horizontalTrial):
        """
        set limits on horizontalTrial so it doesn't cross icon
        """
        x,y = self.point
        x2,y2 = self.point2
        if self.direction is UP or self.direction is DOWN:
            top = min(y, y2)
            bottom = max(y, y2)
            if horizontalTrial.ptOrigin[1] >= top and horizontalTrial.ptOrigin[1] <= bottom and \
               horizontalTrial.leftBound <= x and horizontalTrial.rightBound >= x:
                if horizontalTrial.ptOrigin[0] < x:
                    horizontalTrial.rightBound = x - ConnectorSeparation
                    horizontalTrial.rightTop = top - ConnectorSeparation
                    horizontalTrial.rightBottom = bottom + ConnectorSeparation
                else:
                    horizontalTrial.leftBound = x + ConnectorSeparation
                    horizontalTrial.leftTop = top - ConnectorSeparation
                    horizontalTrial.leftBottom = bottom + ConnectorSeparation
        elif horizontalTrial.ptOrigin[1] == y:
            left = min(x, x2)
            right = max(x, x2)
            if horizontalTrial.rightBound >= left and horizontalTrial.leftBound <= right:
                if horizontalTrial.ptOrigin[0] < left:
                    horizontalTrial.rightBound = left - ConnectorSeparation
                    horizontalTrial.rightTop = y - ConnectorSeparation
                    horizontalTrial.rightBottom = y + ConnectorSeparation        
        
    def Draw(self, color, canvas):
        """
        render the connection
        """
        x, y = self.point
        if self.direction is LEFT:
            if self.input: x += PortLength
            points = ((x,y), (x-PortLength, y-PortLength/2), (x-PortLength, y+PortLength/2))
        elif self.direction is RIGHT:
            if self.input: x -= PortLength
            points = ((x,y), (x+PortLength, y-PortLength/2), (x+PortLength, y+PortLength/2))
        elif self.direction is UP:
            if self.input: y -= PortLength
            points = ((x,y), (x-PortLength/2, y+PortLength), (x+PortLength/2, y+PortLength))
        else:
            if self.input: y += PortLength
            points = ((x,y), (x-PortLength/2, y-PortLength), (x+PortLength/2, y-PortLength))
            
        canvas.drawPolygon(pointlist=points, closed=1, fillColor=color)
    


class LineSegment(object):
    """
    segment of line connecting two ports
    """
    def __init__(self, origin, destination):
        """
        line from point origin to point destination
        """
        self.origin = origin
        self.destination = destination
        
    def BottomBound(self):
        return max(self.origin[1], self.destination[1])
    
    def TopBound(self):
        return min(self.origin[1], self.destination[1])
    
    def LeftBound(self):
        return min(self.origin[0], self.destination[0])
    
    def RightBound(self):
        return max(self.origin[0], self.destination[0])

    def Draw(self, canvas, color):
        if self.origin[1] == self.destination[1]:
            # blank vertical crossings
            left, right = (self.origin[0], self.destination[0])
            if left > right:
                left, right = (right, left)
            left += 1
            right -= 1
            top = self.origin[1]
            bottom = top + 1
            top -= 1
            canvas.drawLine(left, top, right, top, BackGroundColor)
            canvas.drawLine(left, bottom, right, bottom, BackGroundColor)
            top -= 1; bottom += 1
            canvas.drawLine(left, top, right, top, BackGroundColor)
            canvas.drawLine(left, bottom, right, bottom, BackGroundColor)
        
        canvas.drawLine(self.origin[0], self.origin[1],
                        self.destination[0], self.destination[1],
                        color)

class HorizontalTrial(object):
    """
    attempt to create horizontal segment
    """
    def __init__(self, ptOrigin, connection):
        """
        ptOrigin is the starting point for connection
        """
        self.ptOrigin = ptOrigin
        self.connection = connection
        self.leftBound   = 0
        self.leftTop     = None
        self.leftBottom  = None
        self.rightBound  = connection.rightBound
        self.rightTop    = None
        self.rightBottom = None

    def OverlapsLine(self, trialSegment):
        if (trialSegment.leftBound < self.rightBound and
            trialSegment.rightBound > self.leftBound):
            return True
        else:
            return False

    def UopLineLimits(self, uop):
        """
        set limits to avoid uop
        """
        (left, top, right, bottom) = uop.info[PFDINFO][BOUNDINGBOX]
        (x, y) = self.ptOrigin

        if y < (top - ConnectorSeparation) or y > (bottom + ConnectorSeparation):
            return

        if x > right and self.leftBound < right + ConnectorSeparation:
            self.leftBound = right + ConnectorSeparation
            self.leftTop = top
            self.leftBottom = bottom
            
        if x < left and self.rightBound > left - ConnectorSeparation:
            self.rightBound = left - ConnectorSeparation
            self.rightTop = top
            self.rightBottom = bottom            
        
class VerticalTrial(object):
    """
    attempt to create a vertical segment
    """
    def __init__(self, ptOrigin, connection):
        """
        ptOrigin is the starting point for connection
        """
        self.ptOrigin = ptOrigin
        self.connection = connection
        self.topBound    = 0
        self.topLeft     = None
        self.topRight    = None
        self.bottomBound = connection.bottomBound
        self.bottomLeft  = None
        self.bottomRight = None

    def UopLineLimits(self, uop):
        """
        set limits to avoid uop
        """
        (left, top, right, bottom) = uop.info[PFDINFO][BOUNDINGBOX]
        (x, y) = self.ptOrigin

        if x < (left - ConnectorSeparation) or x > (right + ConnectorSeparation):
            return

        if y > bottom and self.topBound < bottom + ConnectorSeparation:
            self.topBound = bottom + ConnectorSeparation
            self.topLeft = left
            self.topRight = right
            
        if y < top and self.bottomBound > top - ConnectorSeparation:
            self.bottomBound = top - ConnectorSeparation
            self.bottomLeft = left
            self.bottomRight = right            
        

class Connection(object):
    """
    represents connection between two ports
    """
    def __init__(self, point, icon, color):
        """
        point is the connection point and icon is what to draw
        """
        self.point = point
        self.icon = icon
        self.color = color
        self.connectedPoint = None
        self.connectedIcon = None
        self.rightPt = (None, None)
        self.leftPt = (None, None)

        self.verticalSegments = []
        self.horizontalSegments = []        

    def Route(self, pfd):
        """
        find a route of horizontal and vertical lines between the connection points in pfd
        """
        if not self.connectedPoint:
            return  # nothing to route
        
        self.rightBound = pfd.rightBound
        self.bottomBound = pfd.bottomBound
        self.pfd = pfd

        if self.point[0] > self.connectedPoint[0]:
            self.rightPt = self.point
            self.leftPt = self.connectedPoint
        else:
            self.rightPt = self.connectedPoint
            self.leftPt = self.point
            
        self.verticalSegments = []
        self.horizontalSegments = []        
        
        rightHTrial = HorizontalTrial(self.rightPt, self)
        rightHTrial.leftBound = 0
        rightHTrial.rightBound = pfd.rightBound
        
        pfd.HorizontalLineLimits(rightHTrial)
        if self.leftPt[1] == self.rightPt[1] and rightHTrial.leftBound <= self.leftPt[0]:
            # single horizontal line will work
            self.horizontalSegments.append(LineSegment(self.leftPt, self.rightPt))
            return True
        
        leftHTrial = HorizontalTrial(self.leftPt, self)
        leftHTrial.leftBound = 0
        leftHTrial.rightBound = self.rightBound
        
        pfd.HorizontalLineLimits(leftHTrial)
        if leftHTrial.rightBound >= rightHTrial.leftBound:
            verticalTrial = self.FindVerticalTrial(leftHTrial, rightHTrial)
            if verticalTrial:
                # found path with one vertical line and two horizontal
                self.AddOneVertical(verticalTrial)
                return True
            
        # look for solution with 3 horizontal lines
        middleHTrial = self.FindMiddleBetween(leftHTrial, rightHTrial)
        if middleHTrial:
            # found solution
            self.AddMiddleHorizontal(middleHTrial, leftHTrial, rightHTrial)
            return True
        
        # everything has failed - just link with a line
        self.horizontalSegments.append(LineSegment(self.leftPt, self.rightPt))
        return False

    def FindVerticalTrial(self, leftHTrial, rightHTrial):
        # tries to find an unobstructed vertical line joining the
        # horizontal line from the right terminal and the horizontal line
        # from the left terminal
        # answers with a VerticalTrial if found, else None
        if leftHTrial.rightBound < rightHTrial.leftBound:
            return None  # no overlap
        
        leftBound = max(leftHTrial.leftBound, rightHTrial.leftBound)
        rightBound = min(leftHTrial.rightBound, rightHTrial.rightBound)
        
        lowerY = max(leftHTrial.ptOrigin[1], rightHTrial.ptOrigin[1])
        upperY = min(leftHTrial.ptOrigin[1], rightHTrial.ptOrigin[1])
        
        if rightBound >= rightHTrial.ptOrigin[0] and leftBound <= rightHTrial.ptOrigin[0]:
            answer = VerticalTrial((rightHTrial.ptOrigin[0], lowerY), self)
            if self.CheckVerticalLine(answer, lowerY, upperY):
                return answer
            
        if leftBound <= leftHTrial.ptOrigin[0] and rightBound >= leftHTrial.ptOrigin[0]:
            answer = VerticalTrial((leftHTrial.ptOrigin[0], lowerY), self)
            if self.CheckVerticalLine(answer, lowerY, upperY):
                return answer
            
        xPoint = min(max(leftBound, leftHTrial.ptOrigin[0]), rightBound)
        while xPoint <= rightBound:
            answer = VerticalTrial((xPoint, lowerY), self)
            if self.CheckVerticalLine(answer, lowerY, upperY):
                return answer
            # step past obstruction
            answerRight = max(answer.topRight, answer.bottomRight, xPoint)
            xPoint = self.SnapPoint((answerRight, lowerY))[0] + ConnectorSeparation
                
        if leftBound < leftHTrial.ptOrigin[0] and rightBound >= leftHTrial.ptOrigin[0]:
            xPoint = leftHTrial.ptOrigin[0] - ConnectorSeparation
            while xPoint >= leftBound:
                answer = VerticalTrial((xPoint, lowerY), self)
                if self.CheckVerticalLine(answer, lowerY, upperY):
                    return answer
                
                # jump over obstruction
                answerLeft = min(answer.topLeft, answer.bottomLeft, xPoint)
                if answerLeft == None: answerLeft = xPoint
                xPoint = self.SnapPoint((answerLeft, lowerY))[0] - ConnectorSeparation
        return None
        
    def CheckVerticalLine(self, trialSegment, lowerY, upperY):
        """
        return true if trialSegment can extend between lowerY and upperY
        """
        self.pfd.VerticalLineLimits(trialSegment)
        if trialSegment.bottomBound >= lowerY and trialSegment.topBound <= upperY:
            return True
        else:
            return False
        
    def SnapPoint(self, point):
        """
        return point closest to point that is on mulitple of ConnectorSeparation and ConnectorSeparation
        """
        x = ((int(point[0]) + ConnectorSeparation / 2 ) / ConnectorSeparation ) * ConnectorSeparation
        y = ((int(point[1]) + ConnectorSeparation / 2 ) / ConnectorSeparation ) * ConnectorSeparation
        return (x, y)
        

    def FindMiddleBetween(self, leftHTrial, rightHTrial):
        """
        try to find another horizontal line between existing horizontal lines
        and connected to them by vertical lines
        """
        if leftHTrial.ptOrigin[1] >= rightHTrial.ptOrigin[1]:
            middleHTrial = self.FindMiddleAbove(leftHTrial, rightHTrial)
            if not middleHTrial:
                middleHTrial = self.FindMiddleBelow(leftHTrial, rightHTrial)
        else:
            middleHTrial = self.FindMiddleBelow(leftHTrial, rightHTrial)
            if not middleHTrial:
                middleHTrial = self.FindMiddleAbove(leftHTrial, rightHTrial)
        return middleHTrial

    def FindMiddleAbove(self, leftHTrial, rightHTrial):
        """
        looks for a middle line above the left horiz line - returns HorizontalTrial if found
        """
        middleY = leftHTrial.ptOrigin[1] - ConnectorSeparation
        while middleY >= 0:
            middleHTrial = HorizontalTrial((leftHTrial.rightBound, middleY), self)
            self.pfd.HorizontalLineLimits(middleHTrial)
            
            if middleHTrial.OverlapsLine(rightHTrial):
                vLeftTrial = self.FindVerticalTrial(leftHTrial, middleHTrial)
                if vLeftTrial:
                    vRightTrial = self.FindVerticalTrial(middleHTrial, rightHTrial)
                    if vRightTrial:
                        middleHTrial.leftBound = vLeftTrial.ptOrigin[0]
                        middleHTrial.rightBound = vRightTrial.ptOrigin[0]
                        return middleHTrial
                    
            if middleHTrial.rightTop == None:
                middleY -= ConnectorSeparation
            else:
                point = self.SnapPoint((middleHTrial.rightTop, middleY))
                middleY = point[1] - 2*ConnectorSeparation

        return None
    
    def FindMiddleBelow(self, leftHTrial, rightHTrial):
        """
        looks for a middle line below the left horiz line - returns True if found
        """
        middleY = leftHTrial.ptOrigin[1] + ConnectorSeparation
        while middleY <= self.bottomBound:
            middleHTrial = HorizontalTrial((leftHTrial.rightBound, middleY), self)
            self.pfd.HorizontalLineLimits(middleHTrial)
            
            if middleHTrial.OverlapsLine(rightHTrial):
                vLeftTrial = self.FindVerticalTrial(leftHTrial, middleHTrial)
                if vLeftTrial:
                    vRightTrial = self.FindVerticalTrial(middleHTrial, rightHTrial)
                    if vRightTrial:
                        middleHTrial.leftBound = vLeftTrial.ptOrigin[0]
                        middleHTrial.rightBound = vRightTrial.ptOrigin[0]
                        return middleHTrial
                    
            if middleHTrial.rightTop == None:
                middleY += ConnectorSeparation
            else:
                point = self.SnapPoint((middleHTrial.rightBottom, middleY))
                middleY = point[1] + 2*ConnectorSeparation

        return None            

    def VerticalLineLimits(self, trialSegment):
        """
        check to see if any of my segments conflict
        """
        # check connection icons first
        if trialSegment.connection is not self:
            self.icon.VerticalLineLimits(trialSegment)
            if self.connectedIcon:
                self.connectedIcon.VerticalLineLimits(trialSegment)

        ptOrigin = trialSegment.ptOrigin
        trialTop = trialSegment.topBound
        trialBottom = trialSegment.bottomBound
        for segment in self.verticalSegments:
            if ptOrigin[0]  < segment.RightBound() + ConnectorSeparation and \
               ptOrigin[0] > segment.LeftBound() - ConnectorSeparation:
                # origin overlaps horizontally
                if ptOrigin[0] > segment.TopBound():
                    trialSegment.topBound = max(segment.BottomBound() + ConnectorSeparation,
                                                trialTop)
                    trialSegment.rightTop = segment.TopBound()
                    trialSegment.rightBottom = segment.BottomBound()

                if ptOrigin[1] < segment.BottomBound():
                    trialSegment.bottomBound = min(segment.TopBound() - ConnectorSeparation,
                                                   trialBottom)
                    trialSegment.bottomLeft = segment.LeftBound()
                    trialSegment.bottomRight = segment.RightBound()

    def HorizontalLineLimits(self, trialSegment):
        """
        check to see if any of my segments conflict
        """
        # check connection icons first
        if trialSegment.connection is not self:
            self.icon.HorizontalLineLimits(trialSegment)
            if self.connectedIcon:
                self.connectedIcon.HorizontalLineLimits(trialSegment)

        ptOrigin = trialSegment.ptOrigin
        trialLeft = trialSegment.leftBound
        trialRight = trialSegment.rightBound
        for segment in self.horizontalSegments:
            if ptOrigin[1] > segment.TopBound() - ConnectorSeparation and \
               ptOrigin[1] < segment.BottomBound() + ConnectorSeparation:
                # origin overlaps vertically
                if ptOrigin[0] > segment.LeftBound():
                    trialSegment.leftBound = max(segment.RightBound() + ConnectorSeparation,
                                                 trialLeft)
                    trialSegment.leftTop = segment.TopBound()
                    trialSegment.leftBottom = segment.BottomBound()

                if ptOrigin[0] < segment.RightBound():
                    trialSegment.rightBound = min(segment.LeftBound() - ConnectorSeparation,
                                                  trialRight)
                    trialSegment.rightTop = segment.TopBound()
                    trialSegment.rightBottom = segment.BottomBound()

    def AddOneVertical(self, verticalTrial):
        """
        adds the segments when a single vertical line solution has been found
        """
        x = verticalTrial.ptOrigin[0]
        if x != self.leftPt[0]:
            self.horizontalSegments.append(LineSegment(self.leftPt, (x, self.leftPt[1])))
            
        if self.leftPt[1] != self.rightPt[1]:
            self.verticalSegments.append(LineSegment((x,self.leftPt[1]), (x, self.rightPt[1])))
            
        if x != self.rightPt[0]:
            self.horizontalSegments.append(LineSegment((x,self.rightPt[1]), self.rightPt))
            
    def AddMiddleHorizontal(self, middleHLine, leftHLine, rightHLine):
        """
        adds the segments for a solution with two vertical and three horizontal lines
        """
        leftX = middleHLine.leftBound
        rightX = middleHLine.rightBound
        y = middleHLine.ptOrigin[1]
        
        if leftHLine.ptOrigin[0] != leftX:
            self.horizontalSegments.append(LineSegment(leftHLine.ptOrigin, (leftX, leftHLine.ptOrigin[1])))
            
        self.verticalSegments.append(LineSegment((leftX, leftHLine.ptOrigin[1]), (leftX, y)))
        self.horizontalSegments.append(LineSegment((leftX,y), (rightX,y)))
        self.verticalSegments.append(LineSegment((rightX,y), (rightX, rightHLine.ptOrigin[1])))
        
        if rightHLine.ptOrigin[0] != rightX:
            self.horizontalSegments.append(LineSegment((rightX, rightHLine.ptOrigin[1]), rightHLine.ptOrigin))

    def SetOtherPoint(self, point, icon):
        """
        set the point and icon for the other end
        """
        self.connectedPoint = point
        self.connectedIcon = icon
        
    def DrawVertical(self, canvas):
        """
        Draw the icons and vertical segments of the connection on the canvas
        """
        self.icon.Draw(self.color, canvas)
        if self.connectedPoint:
            self.connectedIcon.Draw(self.color, canvas)
            for segment in self.verticalSegments:
                segment.Draw(canvas, self.color)

    def DrawHorizontal(self, canvas):
        """
        Draw the horizontal segments of the connection on the canvas
        """
        for segment in self.horizontalSegments:
            segment.Draw(canvas, self.color)        
    
class SimbaPFD(object):
    def __init__(self, flowsheet):
        self.flowsheet = flowsheet
        self.uopMatrix = UopPositionMatrix()
        
        
        self.uopDrawMethods = {
                              'Absorber':            SimbaPFD.DrawTower,
                              'Cooler':              SimbaPFD.DrawCooler,
                              'Compressor':          SimbaPFD.DrawCompressor,
                              'IdealCompressor':     SimbaPFD.DrawCompressor,
                              #'CompressorWithCurve': SimbaPFD.DrawCompressor,
                              'DistillationColumn':  SimbaPFD.DrawTower,
                              'Expander':            SimbaPFD.DrawExpander,
                              'IdealExpander':       SimbaPFD.DrawExpander,
                              #'ExpanderWithCurve':   SimbaPFD.DrawExpander,
                              'HeatExchanger':       SimbaPFD.DrawHeatEx,
                              'Heater':              SimbaPFD.DrawHeater,
                              'Mixer':               SimbaPFD.DrawMixer,
                              'Pump':                SimbaPFD.DrawPump,
                              #'PumpWithCurve':       SimbaPFD.DrawPump,
                              'IdealPump':           SimbaPFD.DrawPump,
                              #'IsenthalpicPump':     SimbaPFD.DrawPump,
                              'ReboiledAbsorber':    SimbaPFD.DrawTower,
                              'RefluxedAbsorber':    SimbaPFD.DrawTower,
                              'SimpleFlash':         SimbaPFD.DrawFlash,
                              'Stream_Material':     SimbaPFD.DrawStream,
                              'Stream_Energy':       SimbaPFD.DrawStream,
                              'Stream_Signal':       SimbaPFD.DrawStream,
                              'PropertySensor':      SimbaPFD.DrawStream,
                              'EnergySensor':        SimbaPFD.DrawStream,
                              'Splitter':            SimbaPFD.DrawSplitter,
                              'Tower':               SimbaPFD.DrawTower,
                              'Valve':               SimbaPFD.DrawValve
                              }
        self.connectionDir = {}
        
    def CreateImage(self):
        """
        create the pfd image
        """
        self.Position()
        self.DrawUops()
        for conn in self.connectionDir.values():
            conn.Route(self)
            
        for conn in self.connectionDir.values():
            conn.DrawVertical(self.canvas)
            
        for conn in self.connectionDir.values():
            conn.DrawHorizontal(self.canvas)
            
    def Position(self):
        uops = self.flowsheet.chUODict.values()
        uops.sort(lambda a, b:cmp(a.creationTime, b.creationTime))
        for uop in uops:
            uop.info[PFDINFO] = SimInfoDict(PFDINFO, uop.info)
        for uop in uops:
            if not uop.info[PFDINFO].get(POSITION, None):
                self.PositionUOP(uop)
            
    def PositionUOP(self, uop):
        """
        find best spot for uop
        """
        pfdInfo = uop.info[PFDINFO]
            
        inputs = uop.GetPorts(IN|MAT|ENE|SIG) 
        leftMostConn = None
        leftMostCol = None
        hasConnection = 0
        for input in inputs:
            connection = input.GetConnection()
            if connection:
                hasConnection = 1
                connectedOp = connection.GetParent()
                while connectedOp and connectedOp.GetParent() != self.flowsheet:
                    connectedOp = connectedOp.GetParent()
                 
                if connectedOp and connectedOp != uop:
                    connInfo = connectedOp.info[PFDINFO]
                    creationTime = connectedOp.creationTime
                    if not connInfo.get(POSITION, None):
                        # cyclical configurations could be a problem - put in recursion break
                        if connInfo.has_key(RECURSION):
                            continue
                        connInfo[RECURSION] = 1
                        self.PositionUOP(connectedOp)
                        del connInfo[RECURSION]
                        
                        if pfdInfo.get(POSITION, None):
                            # uop was positioned during recursion
                            return
                        
                        if not connInfo.get(POSITION, None):
                            # connection did not position itself
                            continue
                    
                    connRow, connCol = connInfo[POSITION]
                    if not leftMostConn or connCol < leftMostCol:
                        leftMostConn = connectedOp
                        leftMostCol = connCol
                        
        if leftMostConn:
            connInfo = leftMostConn.info[PFDINFO]
            connRow, connCol = connInfo[POSITION]
            while self.uopMatrix.GetCell((connRow, connCol + 1)):
                connRow += 1
            self.uopMatrix.SetCell((connRow, connCol + 1), uop)
        elif not pfdInfo.has_key(RECURSION) or hasConnection == 0:
            # if called recursively, wait to be called again
            self.uopMatrix.AddRow(uop)
 

    def HorizontalLineLimits(self, trialSegment):
        """
        set limits of segment so it doesn't conflict with anything
        """
        for conn in self.connectionDir.values():
            conn.HorizontalLineLimits(trialSegment)
            
        uops = self.flowsheet.chUODict.values()
        for uop in uops:
            trialSegment.UopLineLimits(uop)
            
    def VerticalLineLimits(self, trialSegment):
        """
        set limits of segment so it doesn't conflict with anything
        """
        for conn in self.connectionDir.values():
            conn.VerticalLineLimits(trialSegment)
            
        uops = self.flowsheet.chUODict.values()
        for uop in uops:
            trialSegment.UopLineLimits(uop)
            
    def DrawUops(self):
        """
        create a canvas and draw the unit operations on it
        """
        rows, cols = self.uopMatrix.GetMaxDimensions()
        self.bottomBound = rows * UnitOpCellHeight + StreamTrackHeight * ConnectorSeparation
        self.rightBound = cols * UnitOpCellWidth + StreamTrackWidth * ConnectorSeparation
        self.canvas = PILCanvas((self.rightBound, self.bottomBound))
        uops = self.flowsheet.chUODict.values()
        uops.sort(lambda a, b:cmp(a.creationTime, b.creationTime))
        for uop in uops:
            uopTypeName = str(type(uop)).split('.')[-1][:-2]
            method = self.uopDrawMethods.get(uopTypeName, SimbaPFD.DrawGenericOp)
            method(self, uop)
            print '<area shape="RECT" COORDS="%d,%d,%d,%d"' % uop.info[PFDINFO][BOUNDINGBOX]
            print '''href="javascript:DisplayUop('%s');">''' % uop.GetPath()
   
    def AddConnection(self, position, direction, port):
        """
        check to see if a connection exists already for the other end
        if not create a new one
        """
        if isinstance(port,sim.solver.Ports.Port_Signal):
            color = SignalConnectionColor
            input = 0
        else:
            if isinstance(port,sim.solver.Ports.Port_Material):
                color = MaterialConnectionColor
            else:
                color = EnergyConnectionColor # better be energy
            if port.GetPortType() & IN:
                input = 1
            else:
                input = 0
        icon = ConnectionIcon(input, direction, position)
            
        portConn = port.GetConnection()
        if portConn and self.connectionDir.has_key(portConn):
            self.connectionDir[portConn].SetOtherPoint(position, icon)
        else:
            self.connectionDir[port] = Connection(position, icon, color)
            
    def OutputImage(self, session):
        """
        output the image to the session handler
        """
        session.handler.send_header("Content-type", "image/png")
        session.handler.end_headers()
        self.canvas.save(file=session.handler.wfile, format='png')


    def UopXY(self, uop):
        """
        return the x, y coordinates for uop
        """
        row, col = uop.info[PFDINFO][POSITION]
        x = col * UnitOpCellWidth + PortLength + UnitOpCellLeftOffset
        y = row * UnitOpCellHeight + UnitOpCellTopOffset
        return (x, y)

    def DrawGenericOp(self, uop):
        """
        just a basic box for unknown op type
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)
        
        inputs = uop.GetPorts(IN|MAT|ENE)
        outputs = uop.GetPorts(OUT|MAT|ENE)
        signals = uop.GetPorts(SIG)
        neededHeight = max(len(inputs), len(outputs), 6)
        height = neededHeight * ConnectorSeparation
        top = y + (UnitOpHeight - height)/2
        bottom = top +height
        
        canvas.drawRect(x, top, x + UnitOpWidth, bottom, fillColor=UopFillColor)
        canvas.drawString(uop.GetName()[:MaxNameChars], x+5, top + 10,
                          UopNameFont, color=UopNameColor)
        canvas.drawString(str(type(uop)).split('.')[-1][:-2][:MaxTypeChars], x + 1, top + 25,
                          UopTypeFont, color=UopTypeColor)

        connY = top + ConnectorSeparation
        for port in inputs:
            self.AddConnection((x - PortLength, connY), LEFT, port)
            connY += ConnectorSeparation
            
        connY = top + ConnectorSeparation
        for port in outputs:
            self.AddConnection((x + UnitOpWidth + PortLength, connY), LEFT, port)
            connY += ConnectorSeparation

        connX = x + ConnectorSeparation
        for port in signals:
            if port.GetConnection():
                # to keep clutter down, only show connected signals
                self.AddConnection((connX, top - PortLength), UP, port)
                connX += ConnectorSeparation

        uop.info[PFDINFO][BOUNDINGBOX] = (x, top, x + UnitOpWidth, top + height)

    def DrawCompressor(self, uop):
        """
        Compressor representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)
        
        width = 4 * ConnectorSeparation
        height = 8 * ConnectorSeparation
        
        top = y + (UnitOpHeight - height)/2
        bottom = top + height
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        middle = height/2
        
        points = ((left, top),
                  (right, top + middle/2),
                  (right, bottom - middle/2),
                  (left, bottom))

        canvas.drawPolygon(pointlist=points, closed=1, fillColor=UopFillColor) 

        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 - DrawUnit,
                          bottom + DrawUnit * 2, UopNameFont, color=UopNameColor)

        self.AddConnection((left - PortLength, top), LEFT, uop.GetPort(IN_PORT))
        self.AddConnection((right + PortLength, top+middle/2), LEFT, uop.GetPort(OUT_PORT))
        self.AddConnection((left - PortLength, bottom - middle/2), LEFT, uop.GetPort(IN_PORT + 'Q'))
        
        sigPort = uop.GetPort(EFFICIENCY_PORT )
        if sigPort.GetConnection():
            self.AddConnection((left, top - PortLength), UP, sigPort)

        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)
        
    def DrawCooler(self, uop):
        """
        cooler representation
        """
        self.DrawCoolerHeater(uop, isCooler=True)
        

    def DrawHeater(self, uop):
        """
        heater representation
        """
        self.DrawCoolerHeater(uop, isCooler=False)
        
    def DrawCoolerHeater(self, uop, isCooler):
        """
        representation for coolers and heaters
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)
        
        width = height = 8 * DrawUnit
        top = y + (UnitOpHeight - height)/2
        bottom = top + height
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        middle = height/2
        
        canvas.drawArc(left, top, right, bottom, fillColor=UopFillColor)
        points = ((left, top + middle/2),
                  (right - middle/2, top + middle/2),
                  (left + middle/2, bottom - middle/2),
                  (right, bottom - middle/2))
        if isCooler:
            coilColor = blue
        else:
            coilColor = red
        canvas.drawPolygon(pointlist=points, edgeColor=coilColor) 

        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 - DrawUnit,
                          bottom + DrawUnit * 1, UopNameFont, color=UopNameColor)

        self.AddConnection((left - PortLength, top+middle), LEFT, uop.GetPort(IN_PORT))
        self.AddConnection((right + PortLength, top+middle), LEFT, uop.GetPort(OUT_PORT))
        if isCooler:
            self.AddConnection((right + PortLength, bottom - middle/2), LEFT, uop.GetPort(OUT_PORT + 'Q'))
        else:
            self.AddConnection((left - PortLength, top + middle/2), LEFT, uop.GetPort(IN_PORT + 'Q'))
        
        sigPort = uop.GetPort(DELTAP_PORT )
        if sigPort.GetConnection():
            self.AddConnection((left + ConnectorSeparation, bottom + PortLength), DOWN, sigPort)

        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)

    def DrawExpander(self, uop):
        """
        Expander representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)
        
        width = 4 * ConnectorSeparation
        height = 8 * ConnectorSeparation
        
        top = y + (UnitOpHeight - height)/2
        bottom = top + height
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        middle = height/2
        
        points = ((left, top + middle/2),
                  (right, top),
                  (right, bottom),
                  (left, bottom - middle/2))

        canvas.drawPolygon(pointlist=points, closed=1, fillColor=UopFillColor) 

        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 - DrawUnit,
                          bottom + DrawUnit * 2, UopNameFont, color=UopNameColor)

        self.AddConnection((left - PortLength, top+middle/2), LEFT, uop.GetPort(IN_PORT))
        self.AddConnection((right + PortLength, top), LEFT, uop.GetPort(OUT_PORT))
        self.AddConnection((right + PortLength, bottom - middle/2), LEFT, uop.GetPort(OUT_PORT + 'Q'))
        
        sigPort = uop.GetPort(EFFICIENCY_PORT )
        if sigPort.GetConnection():
            self.AddConnection((left, top - PortLength), UP, sigPort)

        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)

    def DrawFlash(self, uop):
        """
        flash drum representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)

        outputs = uop.GetPorts(OUT|MAT)
        numOutputs = len(outputs)
        height = 14 * ConnectorSeparation
        width  = 4 * ConnectorSeparation
        top = y + UnitOpHeight/2 - height/2
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        bottom = top + height
        mid = top + height/2
        
        canvas.drawArc(left, top, right, top + width,
                       startAng=0, extent=180, fillColor=UopFillColor)

        canvas.drawArc(left, bottom - width, right, bottom,
                       startAng=180, extent=180, fillColor=UopFillColor)
        
        canvas.drawRect(left, top + width/2,
                        right, bottom - width/2,
                        fillColor=UopFillColor)

        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), left + width/2, bottom - width/2,
                          font=UopNameFont, color=UopNameColor, angle=90)

        self.AddConnection((left - PortLength, top+height/2), LEFT, uop.GetPort(IN_PORT))
        self.AddConnection((left+width/2, top - PortLength), UP, uop.GetPort(V_PORT))
        self.AddConnection((left+width/2, bottom + PortLength), DOWN, uop.GetPort(L_PORT + '0'))
        nPorts = uop.GetNumberPorts(MAT|OUT)
        if nPorts > 2:
            connY = bottom - width
            for i in range(2,nPorts):
                self.AddConnection((right + PortLength, connY), LEFT, uop.GetPort(L_PORT + str(i-1)))
                connY -= ConnectorSeparation
                
        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)

    def DrawHeatEx(self, uop):
        """
        just a basic box for unknown op type
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)
        
        width = height = 8 * DrawUnit
        top = y + (UnitOpHeight - height)/2
        bottom = top + height
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        middle = height/2
        
        canvas.drawArc(left, top, right, bottom, fillColor=UopFillColor)
        points = ((left, top + middle),
                  (left + middle, top + middle/2),
                  (left + middle, bottom - middle/2),
                  (right, top + middle))
        canvas.drawPolygon(pointlist=points, edgeColor=red) 

        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 - DrawUnit,
                          bottom + DrawUnit * 3, UopNameFont, color=UopNameColor)

        self.AddConnection((left - PortLength, top+middle), LEFT, uop.GetPort(IN_PORT + 'H'))
        self.AddConnection((right + PortLength, top+middle), LEFT, uop.GetPort(OUT_PORT + 'H'))
        self.AddConnection((left + middle, top - PortLength), DOWN, uop.GetPort(IN_PORT + 'C'))
        self.AddConnection((left + middle, bottom + PortLength), DOWN, uop.GetPort(OUT_PORT + 'C'))
        
        sigPort = uop.GetPort(DELTAP_PORT + 'H')
        if sigPort.GetConnection():
            self.AddConnection((left + ConnectorSeparation, bottom + PortLength), DOWN, sigPort)
            
        sigPort = uop.GetPort(DELTAP_PORT + 'C')
        if sigPort.GetConnection():
            self.AddConnection((right - ConnectorSeparation, bottom + PortLength), DOWN, sigPort)
        
        sigPort = uop.GetPort(DELTAT_PORT + 'HI')
        if sigPort.GetConnection():
            self.AddConnection((left + ConnectorSeparation, top - PortLength), UP, sigPort)
        
        sigPort = uop.GetPort(DELTAT_PORT + 'HO')
        if sigPort.GetConnection():
            self.AddConnection((right - ConnectorSeparation, top - PortLength), UP, sigPort)

        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)

    def DrawStream(self, uop):
        """
        material stream representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)

        setBack = DrawUnit * 2
        height = 2 * setBack
        top = y + UnitOpHeight/2 - setBack
        
        points = ((x, top + height/2),
                  (x + setBack, top),
                  (x + UnitOpWidth - setBack, top),
                  (x + UnitOpWidth, top + height/2),
                  (x + UnitOpWidth - setBack, top + height),
                  (x + setBack, top + height))
        
        canvas.drawPolygon(pointlist=points, closed=1, fillColor=UopFillColor)
        canvas.drawString(uop.GetName()[:MaxNameChars], x+5, y + (UnitOpHeight + setBack)/2,
                          UopNameFont, color=UopNameColor)

        inPort = uop.GetPort(IN_PORT)
        outPort = uop.GetPort(OUT_PORT)
        self.AddConnection((x - PortLength, top+height/2), LEFT, inPort)
        self.AddConnection((x + UnitOpWidth + PortLength, top+height/2), LEFT, outPort)
        
        # look for clones
        connX = x + 2 * ConnectorSeparation
        connY = top + height + PortLength
        for port in uop.GetPorts(IN|MAT|ENE):
            if port is not inPort:
                self.AddConnection((connX, connY), UP, port)
                connX += ConnectorSeparation
                
        for port in uop.GetPorts(OUT|MAT|ENE):
            if port is not outPort:
                self.AddConnection((connX, connY), DOWN, port)
                connX += ConnectorSeparation
                                  
        # signals across the top
        connX = x + 2 * ConnectorSeparation
        connY = top - PortLength
        for port in uop.GetPorts(SIG):
            if port.GetConnection():
                # to keep clutter down, only show connected signals
                self.AddConnection((connX, connY), UP, port)
                connX += ConnectorSeparation
            
        uop.info[PFDINFO][BOUNDINGBOX] = (x, top, x + UnitOpWidth, top + height)


    def DrawMixer(self, uop):
        """
        mixer representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)

        inputs = uop.GetPorts(IN|MAT)
        numInputs = len(inputs)
        neededHeight = max(numInputs, 6)
        height = neededHeight * ConnectorSeparation
        width  =  6 * ConnectorSeparation

        top = y + (UnitOpHeight - height)/2
        bottom = top + height
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        mid = top + height/2

        points = ((left, top),
                  (right, mid),
                  (left, bottom))
        
        canvas.drawPolygon(pointlist=points, closed=1, fillColor=UopFillColor)
        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 - DrawUnit,
                          bottom + DrawUnit * 2, UopNameFont, color=UopNameColor)

        connY = top + ConnectorSeparation
        if numInputs > 1:
            portToPortY = ((neededHeight - 1) / (numInputs - 1)) * ConnectorSeparation
        else:
            portToPortY = ConnectorSeparation
            
        for port in inputs:
            self.AddConnection((left - PortLength, connY), LEFT, port)
            connY += portToPortY
        self.AddConnection((right + PortLength, top+height/2), LEFT, uop.GetPort(OUT_PORT))
        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)
                
    def DrawPump(self, uop):
        """
        Pump representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)
        
        width = height = 6 * ConnectorSeparation
        
        top = y + (UnitOpHeight - height)/2
        bottom = top + height
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        middle = height/2
        
        canvas.drawArc(left, top, right, bottom, fillColor=UopFillColor)
        setBack = 0.42 * middle
        points = ((left + setBack, bottom - setBack),
                  (left, bottom),
                  (right, bottom),
                  (right - setBack, bottom - setBack))

        canvas.drawLine(left + middle, top, right, top)
        canvas.drawLine(left, top + middle, left + middle, top + middle)
        canvas.drawPolygon(pointlist=points, closed=1, fillColor=UopFillColor)

        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 - DrawUnit,
                          bottom + DrawUnit * 2, UopNameFont, color=UopNameColor)

        self.AddConnection((left - PortLength, top + middle), LEFT, uop.GetPort(IN_PORT))
        self.AddConnection((right + PortLength, top), LEFT, uop.GetPort(OUT_PORT))
        self.AddConnection((left - PortLength, bottom - ConnectorSeparation), LEFT, uop.GetPort(IN_PORT + 'Q'))
        
        signals = uop.GetPorts(SIG)
        connX = left + ConnectorSeparation
        for port in signals:
            if port.GetConnection():
                # to keep clutter down, only show connected signals
                self.AddConnection((connX, bottom + PortLength), DOWN, port)
                connX += ConnectorSeparation

        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)
        
    def DrawSplitter(self, uop):
        """
        splitter representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)

        outputs = uop.GetPorts(OUT|MAT)
        numOutputs = len(outputs)
        neededHeight = max(numOutputs, 6)
        height = neededHeight * ConnectorSeparation
        width  =  6 * ConnectorSeparation

        top = y + (UnitOpHeight - height)/2
        bottom = top + height
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        mid = top + height/2

        points = ((right, top),
                  (left, mid),
                  (right, bottom))
        
        canvas.drawPolygon(pointlist=points, closed=1, fillColor=UopFillColor)
        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 - DrawUnit,
                          bottom + DrawUnit * 2, UopNameFont, color=UopNameColor)

        connY = top + ConnectorSeparation
        if numOutputs > 1:
            portToPortY = ((neededHeight - 1) / (numOutputs - 1)) * ConnectorSeparation
        else:
            portToPortY = ConnectorSeparation
            
        for port in outputs:
            self.AddConnection((right + PortLength, connY), LEFT, port)
            connY += portToPortY
        self.AddConnection((left - PortLength, top+height/2), LEFT, uop.GetPort(IN_PORT))
        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)
                
    def DrawTower(self, uop):
        """
        tower representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)

        height = 18 * ConnectorSeparation
        width  = 6 * ConnectorSeparation
        top = y + UnitOpHeight/2 - height/2
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        bottom = top + height
        
        #canvas.drawArc(left, top, right, top + width,
                       #startAng=0, extent=180, fillColor=UopFillColor)

        #canvas.drawArc(left, bottom - width, right, bottom,
                       #startAng=180, extent=180, fillColor=UopFillColor)
        
        #canvas.drawRect(left, top + width/2,
                        #right, bottom - width/2,
                        #fillColor=UopFillColor)

        canvas.drawRoundRect(left, top, right, bottom, fillColor=UopFillColor)
        canvas.drawPolygon(((left, top + ConnectorSeparation),
                            (right, top + ConnectorSeparation),
                            (left, bottom - ConnectorSeparation),
                            (right, bottom - ConnectorSeparation)),
                           closed=1)

        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 - DrawUnit,
                          bottom + DrawUnit * 3, UopNameFont, color=UopNameColor)

        numStages = uop.numStages
        nSideSlots = height/ConnectorSeparation - 1

        feedPortNames = uop.GetPortNames(IN|MAT|ENE|SIG)
        feedPorts = map(PortStageFromName, feedPortNames)
        feedPorts.sort()
        nSlotsRequired = len(feedPorts)
        nextFreeSlot = 0
        for stageNo, portName  in feedPorts:
            port = uop.GetPort(portName)
            if isinstance(port, sim.solver.Ports.Port_Signal):
                if not port.GetConnection():
                    nSlotsRequired -= 1
                    continue
                direction = RIGHT
            else:
                direction = LEFT
            bestSlot = int(nSideSlots * float(stageNo)/numStages)
            if bestSlot > nSideSlots - nSlotsRequired:
                bestSlot = nSideSlots - nSlotsRequired
            elif bestSlot < nextFreeSlot:
                bestSlot = nextFreeSlot
                
            nextFreeSlot = bestSlot + 1
            nSlotsRequired -= 1
            connY = top + (bestSlot + 1) * ConnectorSeparation
            self.AddConnection((left - PortLength, connY), direction, port)

        outPortNames = uop.GetPortNames(OUT|MAT|ENE)
        outPorts = map(PortStageFromName, outPortNames)
        outPorts.sort()
        nSlotsRequired = len(outPorts)
        nextFreeSlot = 0
        ovhdSlotFree = True
        btmSlotFree = True
        for stageNo, portName  in outPorts:
            port = uop.GetPort(portName)
            if isinstance(port, sim.solver.Ports.Port_Signal):
                #if not port.GetConnection():
                #    nSlotsRequired -= 1
                #    continue
                direction = RIGHT
            else:
                direction = LEFT
                
            if stageNo == 0 and ovhdSlotFree and portName.startswith('VapourDraw'):
                self.AddConnection((left + width/2, top - PortLength), UP, port)
                nSlotsRequired -= 1
                ovhdSlotFree = False
            elif stageNo == numStages - 1 and btmSlotFree and portName.startswith('LiquidDraw'):
                self.AddConnection((left + width/2, bottom + PortLength), DOWN, port)
                nSlotsRequired -= 1
                btmSlotFree = False
            else:
                bestSlot = int(nSideSlots * float(stageNo)/numStages)
                if bestSlot > nSideSlots - nSlotsRequired:
                    bestSlot = nSideSlots - nSlotsRequired
                elif bestSlot < nextFreeSlot:
                    bestSlot = nextFreeSlot
                    
                nextFreeSlot = bestSlot + 1
                nSlotsRequired -= 1
                connY = top + (bestSlot + 1) * ConnectorSeparation
                self.AddConnection((right + PortLength, connY), direction, port)
            
        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)

    def DrawValve(self, uop):
        """
        valve representation
        """
        canvas = self.canvas
        x, y = self.UopXY(uop)

        height = 2 * ConnectorSeparation
        width  =  4 * ConnectorSeparation
        top    = y + UnitOpHeight/2 - ConnectorSeparation
        left   = x + (UnitOpWidth - width)/2
        right  = x + (UnitOpWidth + width)/2
        bottom = top + height
        
        points = ((left, top),
                  (right, bottom),
                  (right, top),
                  (left, bottom))
        canvas.drawPolygon(pointlist=points, closed=1, fillColor=UopFillColor)
        name = uop.GetName()[:MaxNameChars]
        nameWidth = (len(name) * width) / MaxNameChars
        canvas.drawString(uop.GetName(), x + (UnitOpWidth - nameWidth)/2 -ConnectorSeparation,
                          bottom + ConnectorSeparation * 2, UopNameFont, color=UopNameColor)
        
        self.AddConnection((left - PortLength, top+height/2), LEFT, uop.GetPort(IN_PORT))
        self.AddConnection((right + PortLength, top+height/2), LEFT, uop.GetPort(OUT_PORT))
        dpPort = uop.GetPort(DELTAP_PORT)
        if dpPort and dpPort.GetConnection():
            canvas.drawLine(left + width/2, top+height/2,left + width/2, top)
            self.AddConnection((left + width/2, top - PortLength), UP, dpPort)
            
        uop.info[PFDINFO][BOUNDINGBOX] = (left, top, right, bottom)

def PortStageFromName(portName):
    """
    return a stageNo, portName tuple based on the Name
    """
    index1 = portName.index('_') + 1
    index2 = portName[index1:].index('_') + index1
    stageNo = int(portName[index1:index2])
    return (stageNo, portName)        