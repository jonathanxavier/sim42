import string, sys, os, math

from wxPython.wx import *

from sim.unitop import *
from sim.solver.Variables import *
from sim.solver import Flowsheet, Ports

from Misc import BaseInterpreterParent, BaseObjectFrame, PortDisplayInfo
from SimGrids import MaterialPortFrame, EnergyPortFrame#, SignalPortFrame
from Preferences import prefs


GUI_PATH = os.getcwd()
IMG_FOLDER = 'images'
IMG_PATH  = os.path.join(GUI_PATH, IMG_FOLDER)

#Constants
AH = 10 #arrow height
AB = 8 #arrow base
NDH = 4 #node def height
NDW = 4 #node def width
PDW = 5 #port width
PDH = 5 #port height
LPDW = 8 #Lumped port width
LPDH = 8 #Lumped port height
PM = 2 #margin of port from uo   
UODW = 32 #uo default width
UODH = 32 #uo default height
TM = 0 #margin between uo and text box with name
TIM = 3 #inner margin of text with boundaries of text box

BOTH = 0
HORIZ = 1
VERT = 2

LEFT_LOC = 0
RIGHT_LOC = 1
TOP_LOC = 2
BOTTOM_LOC = 3
BOTTOMLEFT_LOC = 4
TOPRIGHT_LOC = 5
BOTTOMRIGHT_LOC = 6
TOPLEFT_LOC = 7

def GetImageFileName(obj):
    """Gets the path of a file name for the unit operation"""
    fName = None
    
    if not isinstance(obj, UnitOperations.UnitOperation):
        return None
    if isinstance(obj, Balance.BalanceOp):
        fName = 'balance.bmp'
    elif isinstance(obj, ComponentSplitter.ComponentSplitter):
        fName = 'splitter.bmp'
    elif isinstance(obj, Controller.Controller):
        fName = 'controller.bmp'
    elif isinstance(obj, ConvRxn.ConvReactor):
        fName = 'convreactor.bmp'
    elif isinstance(obj, Heater.Cooler):
        fName = 'cooler.bmp'
    elif isinstance(obj, CrossConnector.CrossConnector):
        fName = 'crossconn.bmp'
    elif isinstance(obj, Compressor.Compressor):
        fName = 'compressor.bmp'
    elif isinstance(obj, Compressor.Expander):
        fName = 'compressor.bmp'
    elif isinstance(obj, Equation.Equation):
        fName = 'equation.bmp'

    elif isinstance(obj, Equation.Equation):
        fName = 'equation.bmp'
    elif isinstance(obj, Equation.Add):
        fName = 'add.bmp'
    elif isinstance(obj, Equation.Subtract):
        fName = 'substract.bmp'
    elif isinstance(obj, Equation.Multiply):
        fName = 'multiply.bmp'
    elif isinstance(obj, Equation.Divide):
        fName = 'divide.bmp'
    elif isinstance(obj, Equation.Power):
        fName = 'power.bmp'
    elif isinstance(obj, Equation.Equal):
        fName = 'equal.bmp'
    elif isinstance(obj, Equation.Sqrt):
        fName = 'sqrt.bmp'


    elif isinstance(obj, Flowsheet.Flowsheet):
        fName = 'flowsheet.bmp'            
    elif isinstance(obj, Heater.Heater):
        fName = 'heater.bmp'
    elif isinstance(obj, Heater.HeatExchanger):
        fName = 'heatexchanger.bmp'
    elif isinstance(obj, Mixer.Mixer):
        fName = 'mixer.bmp'
    elif isinstance(obj, Pump.Pump):
        fName = 'pump.bmp'
    elif isinstance(obj, Set.Set):
        fName = 'set.bmp'
    elif isinstance(obj, Flash.SimpleFlash):
        fName = 'separator.bmp'
    elif isinstance(obj, Split.Splitter):
        fName = 'splitter.bmp'
    elif isinstance(obj, Flowsheet.SubFlowsheet):
        fName = 'sflowsheet.bmp'
    elif isinstance(obj, Tower.DistillationColumn):
        fName = 'distcol.bmp'
    elif isinstance(obj, Tower.RefluxedAbsorber):
        fName = 'distcol.bmp'            
    elif isinstance(obj, Tower.ReboiledAbsorber):
        fName = 'distcol.bmp'
    elif isinstance(obj, Tower.Absorber):
        fName = 'distcol.bmp'
    elif isinstance(obj, Tower.Tower):
        fName = 'distcol.bmp'
    elif isinstance(obj, Valve.Valve):
        fName = 'valve.bmp'
    elif isinstance(obj, Stream.Stream_Material):
        fName = 'stream_material.bmp'
    elif isinstance(obj, Stream.Stream_Energy):
        fName = 'stream_energy.bmp' 
    elif isinstance(obj, Stream.Stream_Signal):
        fName = 'stream_signal.bmp' 
    else:
        fName = 'generic.bmp'

    return os.path.join(IMG_PATH, fName)        


def GetPortPosition(viewParent, port):
    """Customize positioning of ports"""
    if not isinstance(viewParent, UnitOperations.UnitOperation): return None
    if not isinstance(port, Ports.Port): return None

    path = viewParent.ShortestPortPath(obj)
    pName = path.split('.')[-1]

    if isinstance(obj, Balance.BalanceOp):
        fName = 'balance.bmp'
    
    

class ConnMenu(wxMenu):
    """Pop up menu for connection selected"""
    def __init__(self, pfd, obj):
        wxMenu.__init__(self)
        if not isinstance(obj, PfdConnection): return
        
        self.pfd = pfd
        self.obj = obj
        
        s = obj.GetDisplayName()
        
        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'Disconnect %s' %s))
        EVT_MENU(self, id, self.OnDelete)

    def OnDelete(self, event):
        self.pfd.DeleteObject(self.obj)


class PfdMenu(wxMenu):
    """Generic menu for the pfd"""
    def __init__(self, pfd):
        wxMenu.__init__(self)
        
        self.pfd = pfd

        s = self.pfd.flowsh.GetPath()
        
        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'Add unit op to %s' %s))
        EVT_MENU(self, id, self.OnAddUnitOp)

        #If its in a split window...
        parent = pfd.GetParent()
        if isinstance(parent, wxSplitterWindow):
            
            id = wxNewId()
            m = wxMenuItem(self, id, 'View Unit Op Palette', 'View the palette with unit operations', wxITEM_CHECK)
            self.AppendItem(m)
            m.Check(parent.IsSplit())
            EVT_MENU(self, id, self.OnViewDragSource)
        

    def OnAddUnitOp(self, event):
        pass

    def OnViewDragSource(self, event):
        parent = self.pfd.GetParent()
        isSplit = parent.IsSplit()
        if event.IsChecked() and isSplit:
            parent.Unsplit(parent.p0)
        elif not event.IsChecked() and not isSplit:
            parent.SplitVertically(parent.p0, parent.p1, 400)
            parent.p0.Show(1)
        
class PortMenu(wxMenu):
    """Pop up menu for a port selected"""
    def __init__(self, pfd, obj):
        wxMenu.__init__(self)
        if not isinstance(obj, Ports.Port): return
        fPath = pfd.flowsh.GetPath()
        self.pfd = pfd
        self.obj = obj

        s = obj.pfdInfoDict[fPath].GetDisplayName()
        
        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'View %s' %s))
        EVT_MENU(self, id, self.OnView)

        parent = obj.GetParent()
        if isinstance(parent, Stream.Stream_Material) or \
           isinstance(parent, Stream.Stream_Energy) or \
           isinstance(parent, Stream.Stream_Signal):
            id = wxNewId()
            self.AppendItem(wxMenuItem(self, id, 'Clone... %s' %s))
            EVT_MENU(self, id, self.OnClone)

        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'Connect... %s' %s))
        EVT_MENU(self, id, self.OnConnect)


    def OnView(self, event):
        self.pfd.View(self.obj)
        
    def OnClone(self, event):
        self.pfd.ClonePort(self.obj)

    def OnConnect(self, event):
        """Prompt for the other port"""
        parentFlowsh = self.interpParent.root
        selDefault = self.pfd.flowsh
        title = 'Select port to connect to'
        d = SelectPortGenericDialog(self.pfd, parentFlowsh, selDefault, title)
        if d.ShowModal() == wxID_OK:
            p = d.GetSelectedPort()
            if not p: return
            self.pfd.ConnectPorts(self.obj, p)
        else:
            return

class LumpedPortMenu(wxMenu):
    """Pop up menu for a port selected"""
    def __init__(self, pfd, obj):
        wxMenu.__init__(self)
        if not isinstance(obj, LumpedPort): return
        fPath = pfd.flowsh.GetPath()
        self.pfd = pfd
        self.obj = obj

        s = obj.pfdInfoDict[fPath].GetDisplayName()
        
        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'View...'))
        EVT_MENU(self, id, self.OnView)

        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'Clone...'))
        EVT_MENU(self, id, self.OnClone)

        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'Connect...'))
        EVT_MENU(self, id, self.OnConnect)


    def OnView(self, event):
        """View port"""
        self.pfd.View(self.obj)
        
    def OnClone(self, event):
        """Clone port"""
        self.pfd.ClonePort(self.obj)

    def OnConnect(self, event):
        """Prompt for the other port"""
        parentFlowsh = self.interpParent.root
        selDefault = self.pfd.flowsh
        title = 'Select port to connect to'
        d = SelectPortGenericDialog(self.pfd, parentFlowsh, selDefault, title)
        if d.ShowModal() == wxID_OK:
            p = d.GetSelectedPort()
            if not p: return
            self.pfd.ConnectPorts(self.obj, p)
        else:
            return

class UnitOpMenu(wxMenu):
    """Pop up menu for a port selected"""
    def __init__(self, pfd, obj):
        wxMenu.__init__(self)
        if not isinstance(obj, UnitOperations.UnitOperation): return
        fPath = pfd.flowsh.GetPath()
        self.pfd = pfd
        self.obj = obj

        s = obj.pfdInfoDict[fPath].GetDisplayName()
        
        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'View %s' %s))
        EVT_MENU(self, id, self.OnView)

        if isinstance(obj, Stream.Stream_Material) or \
           isinstance(obj, Stream.Stream_Energy) or \
           isinstance(obj, Stream.Stream_Signal):
            id = wxNewId()
            self.AppendItem(wxMenuItem(self, id, 'Clone... %s' %s))
            EVT_MENU(self, id, self.OnClone)

        id = wxNewId()
        self.AppendItem(wxMenuItem(self, id, 'Delete %s' %s))
        EVT_MENU(self, id, self.OnDelete)


    def OnView(self, event):
        self.pfd.View(self.obj)
        
    def OnClone(self, event):
        self.pfd.ClonePort(self.obj)

    def OnDelete(self, event):
        self.pfd.DeleteObject(self.obj)

class LumpedPort(object):
    """Object used when a port is viewed as one Lumped Port. Wraps basic methods of a real port"""
    def __init__(self, parent, type, fPath='/'):

        if not isinstance(parent, UnitOperations.UnitOperation):
            raise ValueError, "viewParent must be a unit operation"
        
        self._parent = parent
        self._type = type
        self._ports = []
        self.pfdInfoDict = {}
        self.pfdInfoDict[fPath] = PfdPortInfoHolder(self, parent, fPath)
        
        if not hasattr(self._parent, 'pfdInfoDict'):
            self._parent.pfdInfoDict = {}
        if not self._parent.pfdInfoDict.get(fPath, None):
            self._parent.pfdInfoDict[fPath] = PfdUOInfoHolder(self._parent, None, fPath)
        self._parent.pfdInfoDict[fPath].SetLumpedPort(self, type)

    def GetParent(self):
        """Emulates the normal call of a port"""
        return self._parent

    def AddPort(self, port):
        """Adds a port simulated by this 'fake' port"""
        if not port in self._ports:
            self._ports.append(port)

    def ClearPort(self):
        """Clears the list of ports"""
        self._ports = []

    def GetPorts(self):
        """Returns the list of ports"""
        return self._ports

    def SetPorts(self, ports):
        """Sets a list of ports"""
        self._ports = ports

    def GetPortType(self):
        """Type of ports contained here"""
        return self._type

    def SetPortType(self, type):
        """Type of ports contained here"""
        self._type = type

    def GetName(self):
        return self._parent.GetName() + str(self._type)
        

class PfdInfoHolder(object):
    """This object holds the neccessary info to represent and obj in the pfd"""
    def __init__(self, obj, viewParent, fPath='/'):
        self._position = None
        self._displayName = ''
        self._bmp = None
        self._pfdConn = None
        self._obj = obj
        self._viewParent = viewParent
        self.fPath = fPath
        bmpPath = GetImageFileName(obj)
        if bmpPath: self._bmp = wxBitmap(bmpPath, wxBITMAP_TYPE_BMP)

    def GetViewParent(self):
        """Gets the parent of the object that the user views"""
        return self._viewParent

    def GetObject(self):
        """Gets the object upon which events occur"""
        return self._obj

    def GetPfdConn(self):
        """Returns an instance of an object with connection info"""
        return self._pfdConn

    def SetPfdConn(self, pfdConn):
        """Sets an instance of an object with connection info"""
        self._pfdConn = pfdConn

    def WasPositionSet(self):
        """Tells if position was set at any time or it is using the default value of (0, 0)"""
        return self._position

    def ClearPosition(self):
        self._position = None

    def GetPosition(self):
        """Position relative to parent"""
        if not self._position: return (0, 0)
        return self._position

    def SetPosition(self, pos):
        """Position relative to parent as a tuple (x, y)"""
        if type(pos) != type(()) or len(pos) != 2 or type(pos[0]) != type(0) or type(pos[1]) != type(0):
            raise ValueError, "pos is not a position tuple"
        self._position = pos

    def GetAbsPosition(self):
        """Get absolute position based on parent"""
        x, y = self.GetPosition()
        if self._viewParent:
            px, py = self._viewParent.pfdInfoDict[self.fPath].GetPosition()
            x, y = x + px, y + py
        return (x, y)

    def GetHeight(self):
        """Get height"""
        if self._bmp: return self._bmp.GetHeight()
        return 3

    def GetWidth(self):
        """Get width"""
        if self._bmp: return self._bmp.GetWidth()
        return 3
        
    def GetDisplayName(self):
        """Gets name for display in pfd"""
        return self._displayName

    def SetDisplayName(self, name):
        """Name for display in a pfd"""
        if type(name) not in (type(""), type(u"")):
            raise ValueError, "name is not a string"
        self._displayName = name

    def GetBmp(self):
        """wxBitmap of the obj"""
        return self._bmp

    def SetBmp(self, bmp):
        """set a valid wxBitmap to represent the obj in the pfd"""
        if not isinstance(bmp, wxBitmap):
            raise ValueError, "bmp is not a wxBitmap obj"
        self._bmp = bmp

    def SetBmpFromPath(self, bmpPath):
        """Load a bmp file to represent the obj"""
        self._bmp = wxBitmap(bmpPath, wxBITMAP_TYPE_BMP)
        

class PfdUOInfoHolder(PfdInfoHolder):
    def __init__(self, obj, viewParent, fPath='/'):
        PfdInfoHolder.__init__(self, obj, viewParent, fPath)
        
        self._displayName = obj.GetPath()
        if not self._displayName: self._displayName = obj.GetName()

        self._inMatLumped = None
        self._outMatLumped = None
        self._inEneLumped = None
        self._outEneLumped = None
        self._sigLumped = None
        
        self._portList = [] #Ports from child uops that are not borrowed but yet connected outside

    def GetHeight(self):
        """Get height"""
        if self._bmp: return self._bmp.GetHeight()
        else: return UODH

    def GetWidth(self):
        """Get width"""
        if self._bmp: return self._bmp.GetWidth()
        else: return UODW

    def GetLumpedPort(self, type):
        """If the ports where visually lumped, then it returns not None"""
        if type == IN|MAT: return self._inMatLumped
        elif type == OUT|MAT: return self._outMatLumped
        elif type == IN|ENE: return self._inEneLumped
        elif type == OUT|ENE: return self._outEneLumped
        elif type == SIG: return self._sigLumped

    def SetLumpedPort(self, lPort, type):
        """Ports can be visually lumped"""
        if type == IN|MAT: self._inMatLumped = lPort
        elif type == OUT|MAT: self._outMatLumped = lPort
        elif type == IN|ENE: self._inEneLumped = lPort
        elif type == OUT|ENE: self._outEneLumped = lPort
        elif type == SIG: self._sigLumped = lPort
            

    def AddToPortList(self, port):
        """Ports from child uops that are not borrowed but yet connected outside"""
        if not port in self._portList:
            self._portList.append(port)

    def RemoveFromPortList(self, port):
        """Ports from child uops that are not borrowed but yet connected outside"""
        if port in self._portList:
            self._portList.remove(port)

    def GetPortList(self):
        return self._portList
        

class PfdPortInfoHolder(PfdInfoHolder):
    def __init__(self, obj, viewParent, fPath='/'):
        PfdInfoHolder.__init__(self, obj, viewParent, fPath)

        if isinstance(obj, Ports.Port):
            realParent = obj.GetParent()
            self._displayName = realParent.ShortestPortPath(obj)
            if not self._displayName: self._displayName = obj.GetName()
        else:
            self._displayName = obj.GetName()

    def GetHeight(self):
        """Get height"""
        if self._bmp:
            return self._bmp.GetHeight()
        else:
            if isinstance(self._obj, Ports.Port): return PDH
            else: return LPDH

    def GetWidth(self):
        """Get width"""
        if self._bmp:
            return self._bmp.GetWidth()
        else:
            if isinstance(self._obj, Ports.Port): return PDW
            else: return LPDW

class PfdConnection(object):
    """Has info about the connection of two ports"""
    def __init__(self, fPath='/'):
        self._displayName = ' : '
        self._nodes = [PfdConnectionNode(self, (0,0)), PfdConnectionNode(self, (0, 0))]
        self._inPort = None
        self._outPort = None
        self.fPath=fPath

    def __str__(self):
        cnt = self.GetNodeCount()
        n = self.GetDisplayName()
        t = 'Connection of %d nodes with name: %s' %(cnt, n)
        return t

    def GetPortIn(self):
        """Gets the in port"""
        return self._inPort
    
    def SetPortIn(self, pIn):
        """Sets the in port"""
        self._inPort = pIn

    def GetPortOut(self):
        """Gets the out port"""
        return self._outPort

    def SetPortOut(self, pOut):
        """Sets the out port"""
        self._outPort = pOut

    def GetNodeCount(self):
        return len(self._nodes)

    def Move(self, dxdy):
        """Move all nodes"""
        cnt = self.GetNodeCount()
        dx, dy = dxdy
        for i in range(cnt):
            n = self.GetNode(i)
            if n:
                x, y = n.GetPosition()
                n.SetPosition((x + dx, y + dy))

    def InitNodes(self):
        """Whatever to initialize the nodes"""
        if hasattr(self._outPort, 'pfdInfoDict'):
            if self._outPort.pfdInfoDict.get(self.fPath, None):
                info = self._outPort.pfdInfoDict[self.fPath]
                ox, oy = info.GetAbsPosition()
                ow, oh = info.GetWidth(), info.GetHeight()
                ox, oy = ox + ow/2, oy + oh/2
                self._nodes[0] = PfdConnectionNode(self, (ox, oy))
            else:
                raise ValueError, "Can't set connection, outPort has no positions"
        else:
            raise ValueError, "Can't set connection, outPort has no positions"
        
        if hasattr(self._inPort, 'pfdInfoDict'):
            if self._inPort.pfdInfoDict.get(self.fPath, None):
                info = self._inPort.pfdInfoDict[self.fPath]
                ix, iy = info.GetAbsPosition()
                iw, ih = info.GetWidth(), info.GetHeight()
                ix, iy = ix + iw/2, iy + ih/2
                self._nodes[-1] = PfdConnectionNode(self, (ix, iy))
            else:
                raise ValueError, "Can't set connection, inPort has no positions"
        else:
            raise ValueError, "Can't set connection, inPort has no positions"
        
        if oy != iy and ox != ix:
            self._nodes.insert(1, PfdConnectionNode(self, ((ox+ix)/2, oy)))
            self._nodes.insert(2, PfdConnectionNode(self, ((ox+ix)/2, iy)))


    def VerifyNodeIntegrity(self):
        """Deletes redundant nodes and add nodes for non 90 degrees angles"""
        
        #Add nodes if needed
        node = self.GetNode(0)
        while node:
            idx = self.GetNodeIndex(node)
            next = self.GetNode(idx+1)
            if not next: break
            x, y = node.GetPosition()
            nextx, nexty = next.GetPosition()
            if x != nextx and y != nexty:
                node = PfdConnectionNode(self, ((nextx+x)/2, y))
                self.InsertNode(idx+1, node)
                node = PfdConnectionNode(self, ((nextx+x)/2, nexty))
                self.InsertNode(idx+2, node)                              
            else:
                node = next

        #Redundant nodes
        if self.GetNodeCount() > 2:
            node = self.GetNode(1)
            while node:
                idx = self.GetNodeIndex(node)
                prev = self.GetNode(idx-1)
                next = self.GetNode(idx+1)
                if not next: break
                x, y = node.GetPosition()
                if prev:
                    prevx, prevy = prev.GetPosition()
                    nextx, nexty = next.GetPosition()
                    if prevx == x == nextx:
                        self.RemoveNode(idx)
                    elif prevy == y == nexty:
                        self.RemoveNode(idx)                    
                node = next

        #First node
        if hasattr(self._outPort, 'pfdInfoDict'):
            if self._outPort.pfdInfoDict.get(self.fPath, None):
                info = self._outPort.pfdInfoDict[self.fPath]
                ox, oy = info.GetAbsPosition()
                ow, oh = info.GetWidth(), info.GetHeight()
                ox, oy = ox + ow/2, oy + oh/2
                node = self.GetNode(0)
                if (ox, oy) != node.GetPosition():
                    node = PfdConnectionNode(self, (ox, oy))
                    self.InsertNode(0, node)

        #Last node
        if hasattr(self._inPort, 'pfdInfo'):
            if self._inPort.pfdInfoDict.get(self.fPath, None):
                info = self._inPort.pfdInfoDict[self.fPath]
                ix, iy = info.GetAbsPosition()
                iw, ih = info.GetWidth(), info.GetHeight()
                ix, iy = ix + iw/2, iy + ih/2
                node = self.GetNode(-1)
                if (ix, iy) != node.GetPosition():
                    node = PfdConnectionNode(self, (ix, iy))
                    self.InsertNode(len(self._nodes), node)

    def RemoveNode(self, idx):
        """Remove a node"""
        try: del self._nodes[idx]
        except: pass
        
    def InsertNode(self, idx, node):
        """Tries to insert a new node"""
        if not isinstance(node, PfdConnectionNode):
            raise ValueError, "node is not a PfdConnection obj"
        self._nodes.insert(idx, node)

    def AppendNode(self, node):
        """Tries to append a new node"""
        if not isinstance(node, PfdConnectionNode):
            raise ValueError, "node is not a PfdConnection obj"
        self._nodes.append(node)
        
    def GetNode(self, idx):
        """Nodes of connecting line"""
        try: return self._nodes[idx]
        except: return None

    def GetNodeIndex(self, node):
        """Returns the index of a given node"""
        if node in self._nodes:
            return self._nodes.index(node)
        return None

    def GetNext(self, node):
        """Passes the next node"""
        idx = self.GetNodeIndex(node)
        if idx + 1 < len(self._nodes):
            return self._nodes[idx+1]
        return None

    def GetPrevious(self, node):
        """Returns the previous node"""
        idx = self.GetNodeIndex(node)
        if idx:
            return self._nodes[idx-1]
        return None

    def GetDisplayName(self):
        """Gets name for display in pfd"""
        return self._displayName

    def SetDisplayName(self, name):
        """Name for display in a pfd"""
        if type(name) not in (type(""), type(u"")):
            raise ValueError, "name is not a string"
        self._displayName = name


class PfdConnectionNode(object):
    def __init__(self, conn, pos):
        """conn = PfdConnection obj; fromJoint = idx of joint where segment comes from"""
        self._conn = conn
        self._position = pos
        self._canMove = BOTH
        self._underMouse = 0
        self._locked = 0

    def __str__(self):
        idx = self._conn.GetNodeIndex(self)
        if idx == None: idx = -1
        t = 'Node with index %d of conn: %s' %(idx, str(self._conn))
        return t

    def GetConnection(self):
        """Connection object"""
        return self._conn

    def GetPosition(self):
        """Origin joint"""
        return self._position

    def Lock(self):
        self._locked = 1

    def Unlock(self):
        self._locked = 0

    def IsLocked(self):
        return self._locked

    def SetPosition(self, pos):
        """Origin joint"""
        self._position = pos

    def Move(self, dxdy):
        """Move node with mouse"""
        if self.IsLocked(): return
        cnt = self._conn.GetNodeCount()
        idx = self._conn.GetNodeIndex(self)
        if idx == None: return
        if idx > 0: prev = self._conn.GetNode(idx-1)
        else: prev = None
        next = self._conn.GetNode(idx+1)

        dx, dy = dxdy
        x, y = self.GetPosition()
        self.SetPosition((x + dx, y + dy))

        if next and not next.IsLocked():
            nextx, nexty = next.GetPosition()
            if idx+2 == cnt:
                #Do not move last node. Add a new node
                self._conn.AppendNode(PfdConnectionNode(self._conn, (nextx, nexty)))
            if nextx == x and nexty != y:
                next.SetPosition((nextx + dx, nexty))
                next._canMove = HORIZ
            elif nextx != x and nexty == y:
                next.SetPosition((nextx, nexty + dy))
                next._canMove = VERT
            else:
                if next._canMove == HORIZ:
                    next.SetPosition((nextx + dx, nexty))
                elif next._canMove == VERT:
                    next.SetPosition((nextx, nexty + dy))
                else:
                    next.SetPosition((nextx + dx, nexty + dy))
                    next._canMove = BOTH

        if prev and not prev.IsLocked():
            prevx, prevy = prev.GetPosition()
            if idx == 1:
                #Do not move source node. Add a new node
                prev = PfdConnectionNode(self._conn, (prevx, prevy))
                self._conn.InsertNode(idx, prev)
            if prevx == x and prevy != y:
                prev.SetPosition((prevx + dx, prevy))
                prev._canMove = HORIZ
            elif prevx != x and prevy == y:
                prev.SetPosition((prevx, prevy + dy))
                prev._canMove = VERT
            else:
                if prev._canMove == HORIZ:
                    prev.SetPosition((prevx + dx, prevy))
                elif prev._canMove == VERT:
                    prev.SetPosition((prevx, prevy + dy))
                else:
                    prev.SetPosition((prevx + dx, prevy + dy))
                    prev._canMove = BOTH


    def GetNext(self):
        """Get next node"""
        return self._conn.GetNext(self)
    
    def GetPrevious(self):
        """Get previous node"""
        return self._conn.GetPrevious(self)

class PfdConnectionSegment(object):
    """Just wraps an existing node so it can be located as a segment"""
    def __init__(self, node, canMove):
        self._node = node
        self._canMove = canMove

    def GetCanMoveType(self):
        return self._canMove
        
    def GetConnection(self):
        """Connection object"""
        return self._node.GetConnection()

    def GetPosition(self):
        """Origin joint"""
        return self._node.GetPosition()

    def SetPosition(self, pos):
        """Origin joint"""
        self._node.SetPosition(pos)
        
    def Move(self, dxdy):
        dx, dy = dxdy
        if self._canMove == HORIZ: dy = 0
        elif self._canMove == VERT: dx = 0
        dxdy = (dx, dy)
        self._node.Move(dxdy)
            
    def GetNext(self):
        """Get next node"""
        return self._node.GetNext()
    
    def GetPrevious(self):
        """Get previous node"""
        return self._node.GetPrevious()
        
class ConnectPortDialog(wxDialog):
    def __init__(self, parent, pFrom, pTo, fPath='/'):
        wx.wxDialog.__init__(self, parent, -1, "Choose ports to connect", size = (384, 288))
        self.SetClientSize((384, 288))

        self.fPath = fPath

        t = pFrom.GetPortType()
        self.t = t
        
        if t & IN:
            self.outPort, self.inPort = pTo, pFrom
        else:
            self.outPort, self.inPort = pFrom, pTo

        if t & MAT:
            outtxt = 'Port type: OUT - MATERIAL'
            intxt = 'Port type: IN - MATERIAL'
        elif t & ENE:
            outtxt = 'Port type: OUT - ENERGY'
            intxt = 'Port type: IN - ENERGY'
        elif t & SIG:
            outtxt = 'Port type: OUT - SIGNAL'
            intxt = 'Port type: IN - SIGNAL'
        else:
            outtxt = ''
            intxt = ''
            
        #Out port controls
        wxStaticText(self, -1, outtxt, style = wx.wxALIGN_CENTRE, pos =wxPoint(0, 8), size =wxSize(192, 32))
        self.outParent = self.outPort.pfdInfoDict[self.fPath].GetViewParent()
        if isinstance(self.outParent, Flowsheet.Flowsheet):
            outUONames = self.outParent.GetChildUONames()
        else:
            outUONames = [self.outParent.GetName()]
            self.outParent = self.outParent.GetParent()
        self.outUOLst = wxChoice(self, -1, wxPoint(8, 40), wxSize(180, 32), choices=outUONames)
        self.outPLst = wxListBox(self, -1, wxPoint(8, 64), wxSize(180, 186), [], wxLB_SINGLE)
        self.outUOLst.SetSelection(0)
        self.OutUOSelect(None)
        if isinstance(self.outPort, Ports.Port):
            self.outUOLst.Enable(0)
            self.outPLst.Enable(0)
        else:
            if self.outPLst.GetCount():
                self.outPLst.SetSelection(0)
        EVT_CHOICE(self, self.outUOLst.GetId(), self.OutUOSelect)


        #In port controls
        wxStaticText(self, -1, intxt, style = wx.wxALIGN_CENTRE, pos =wxPoint(192, 8), size =wxSize(192, 32))
        self.inParent = self.inPort.pfdInfoDict[self.fPath].GetViewParent()
        if isinstance(self.inParent, Flowsheet.Flowsheet):
            inUONames = self.inParent.GetChildUONames()
        else:
            inUONames = [self.inParent.GetName()]
            self.inParent = self.inParent.GetParent()
        self.inUOLst = wxChoice(self, -1, wxPoint(196, 40), wxSize(180, 32), choices=inUONames)
        EVT_CHOICE(self, self.inUOLst.GetId(), self.InUOSelect)
        self.inPLst = wxListBox(self, -1, wxPoint(196, 64), wxSize(180, 186), [], wxLB_SINGLE)
        self.inUOLst.SetSelection(0)
        self.InUOSelect(None)
        if isinstance(self.inPort, Ports.Port):
            self.inUOLst.Enable(0)
            self.inPLst.Enable(0)
        else:
            if self.inPLst.GetCount():
                self.inPLst.SetSelection(0)

        #Buttons
        self.cancel = wxButton(self, wxID_CANCEL, "Cancel", pos=wxPoint(220, 258))
        self.ok = wxButton(self, wxID_OK, "Ok", pos=wxPoint(300, 258))


    def OutUOSelect(self, event):
        uoName = self.outUOLst.GetStringSelection()
        uo = self.outParent.GetChildUO(uoName)
        if uo:
            if self.t & MAT:
                pNames = uo.GetPortNames(OUT|MAT)
            elif self.t & ENE:
                pNames = uo.GetPortNames(OUT|ENE)
            else:
                pNames = uo.GetPortNames(SIG)
        else:
            pNames = []
        self.outPLst.Set(pNames)
        if isinstance(self.outPort, Ports.Port):
            path = uo.ShortestPortPath(self.outPort)
            path = path.split('.')
            if path[-1] in pNames:
                self.outPLst.SetStringSelection(path[-1])
            

    def InUOSelect(self, event):
        uoName = self.inUOLst.GetStringSelection()
        uo = self.inParent.GetChildUO(uoName)
        if uo:
            if self.t & MAT:
                pNames = uo.GetPortNames(IN|MAT)
            elif self.t & ENE:
                pNames = uo.GetPortNames(IN|ENE)
            else:
                pNames = uo.GetPortNames(SIG)
        else:
            pNames = []
        self.inPLst.Set(pNames)
        if isinstance(self.inPort, Ports.Port):
            path = uo.ShortestPortPath(self.inPort)
            path = path.split('.')
            if path[-1] in pNames:
                self.inPLst.SetStringSelection(path[-1])

                
    def GetSelectedPorts(self):
        """tuple with both selected ports"""
        uoName = self.outUOLst.GetStringSelection()
        uo = self.outParent.GetChildUO(uoName)
        if isinstance(self.outPort, Ports.Port):
            outP = self.outPort
        elif uo:
            pName = self.outPLst.GetStringSelection()
            outP = uo.GetPort(pName)
        else:
            outP = None

        uoName = self.inUOLst.GetStringSelection()
        uo = self.inParent.GetChildUO(uoName)
        if isinstance(self.inPort, Ports.Port):
            inP = self.inPort
        if uo:
            pName = self.inPLst.GetStringSelection()
            inP = uo.GetPort(pName)
        else:
            inP = None

        return (outP, inP)

class SelectPortDialog(wxDialog):
    def __init__(self, parent, p, fPath='/'):
        wx.wxDialog.__init__(self, parent, -1, "Choose port", size = (196, 288))
        self.SetClientSize((196, 288))

        self.fPath = fPath
        self.t = p.GetPortType()
        self.p = p

        #Port controls
        if self.t == IN|MAT:
            txt = 'Port type: IN - MATERIAL'
        elif self.t == OUT|MAT:
            txt = 'Port type: OUT - MATERIAL'
        elif self.t == IN|ENE:
            txt = 'Port type: IN - ENERGY'
        elif self.t == OUT|ENE:
            txt = 'Port type: OUT - ENERGY'
        elif self.t == SIG:
            txt = 'Port type: SIGNAL'
        else:
            txt = ''
        wxStaticText(self, -1, txt, style = wx.wxALIGN_CENTRE, pos = (0, 8), size = (192, 32))
        
        self.pParent = self.p.pfdInfoDict[self.fPath].GetViewParent()
        if isinstance(self.pParent, Flowsheet.Flowsheet):
            uoNames = self.pParent.GetChildUONames()
        else:
            uoNames = [self.pParent.GetName()]
            self.pParent = self.pParent.GetParent()
        self.uoLst = wxChoice(self, -1, wxPoint(8, 40), wxSize(180, 32), choices=uoNames)
        self.pLst = wxListBox(self, -1, wxPoint(8, 64), wxSize(180, 186), [], wxLB_SINGLE)
        self.uoLst.SetSelection(0)
        self.UOSelect(None)
        if isinstance(self.p, Ports.Port):
            self.uoLst.Enable(0)
            self.pLst.Enable(0)
        else:
            if self.pLst.GetCount():
                self.pLst.SetSelection(0)
        EVT_CHOICE(self, self.uoLst.GetId(), self.UOSelect)

        #Buttons
        self.cancel = wxButton(self, wxID_CANCEL, "Cancel", pos=wxPoint(32, 258))
        self.ok = wxButton(self, wxID_OK, "Ok", pos=wxPoint(112, 258))


    def UOSelect(self, event):
        uoName = self.uoLst.GetStringSelection()
        uo = self.pParent.GetChildUO(uoName)
        if uo: pNames = uo.GetPortNames(self.t)
        else: pNames = []
        self.pLst.Set(pNames)
        if isinstance(self.p, Ports.Port):
            path = uo.ShortestPortPath(self.p)
            path = path.split('.')
            if path[-1] in pNames:
                self.pLst.SetStringSelection(path[-1])
                
    def GetSelectedPort(self):
        """return selected port"""
        uoName = self.uoLst.GetStringSelection()
        uo = self.pParent.GetChildUO(uoName)
        if isinstance(self.p, Ports.Port):
            p = self.p
        elif uo:
            pName = self.pLst.GetStringSelection()
            p = uo.GetPort(pName)
        else:
            p = None

        return p

class ClonePortDialog(wxDialog):
    def __init__(self, parent, s, t=None):
        wx.wxDialog.__init__(self, parent, -1, "Clone name and type", size = (365, 131))
        self.SetClientSize((365, 131))

        wxStaticText(self, -1, "Clone settings for stream " + s.GetPath(), wxPoint(5, 5), wxDefaultSize, 0)
        
        wxStaticText(self, -1, "Clone Name: ", wxPoint(5, 37), wxSize(100, 32), 0)
        self.cname = wxTextCtrl(self, -1, "Clone", wxPoint(75, 37), wxSize(250,-1), 0)

        wxStaticText(self, -1, "Clone IN port:", wxPoint(5, 69), wxSize(100, 32), 0)
        self.ctype = wxCheckBox(self, -1, "", wxPoint(75, 69), wxDefaultSize, 0)
        if t != None:
            if t: self.ctype.SetValue(1)
            else: self.ctype.SetValue(0)
            self.ctype.Enable(0)

        #Buttons
        self.cancel = wxButton(self, wxID_CANCEL, "Cancel", wxPoint(32, 101))
        self.ok = wxButton(self, wxID_OK, "Ok", wxPoint(112, 101))

    def GetCloneType(self):
        """Returns if it's an IN port"""
        return self.ctype.GetValue()
                
    def GetCloneName(self):
        """return name of the clone"""
        return self.cname.GetValue()


class FlowsheetPanel(wxWindow):
    NONE = 0
    DRAGGING_OBJS = 1
    DRAGGING_SELECTION_BOX = 2
    CONNECTING_PORTS = 3

    def __init__(self, parent, frameParent, interpParent, flowsh, pos=wxDefaultPosition):
        id = -1
        size = wxDefaultSize
        style = wxSUNKEN_BORDER
        name = "PfdCtrl"
        wxWindow.__init__(self, parent, id, pos, size, style, name)

        #Sim stuff        
        self.interpParent = interpParent
        self.flowsh = flowsh
        self.frames = {}
        self.parent = frameParent

        #Admin pfd stuff        
        self._state = self.NONE
        self._selection = []
        self._selectRegions = []
        self._dragSource = (0, 0)
        self._dragPos = (0, 0)
        self._xorSelection = 0
        self._connectionFrom = None
        self._extent = [0, 0, 0, 0]
        self._drawBase = [0, 0]
        self._drawnUOs = []
        self._drawnPortConn = []
        self._selConns = []        
        self._holdRefresh = 0
        self._viewNodes = 0

        #Drag and drop
        self._drop = PfdDropTarget(self)
        self.SetDropTarget(self._drop)

        #Preferences
        self._clrLineMat = wxColour(0, 128, 225) #Blue
        self._clrLineEne = wxColour(255, 0, 0)  #Red
        self._clrLineSig = wxColour(225, 255, 0) #Yellow
        self._sLineMat = wxSOLID
        self._sLineEne = wxSOLID
        self._sLineSig = wxLONG_DASH
        self._clrPortMat = wxColour(240, 220, 0)#(0, 128, 225)
        self._clrPortEne = wxColour(255, 0, 0)  #Orange
        self._clrPortSig = wxColour(225, 255, 0) #Yellow
        self._fntUOName = wxFont(8, wxSWISS, wxNORMAL, wxNORMAL)
        self._clrUOName = wxColour(0, 0, 0) #Black
        self._clrPfd = wxColour(255, 255, 255)
        self.LoadPrefs()

        #Last steps
        self.SetBackgroundColour(self._clrPfd)
##        self.SetToolTip(wxToolTip(""))
##        self.wxToolTip_Enable(0)

        #Event handling        
        EVT_PAINT(self, self.OnPaint)
        EVT_MOUSE_EVENTS(self, self.OnMouse)
        EVT_CHAR(self, self.OnChar)
        EVT_SCROLLWIN(self, self.OnScroll)
        EVT_SIZE(self, self.OnSize)

        #Temporary error handling
        self.errOnPaint = False

        #Variables created so Refresh(0) consumes less resources most of the time        
        self._forcePositonActive = True
        self._uoBuffer = None
        self._firstTime = 1

    def GetSimObject(self):
        return self.flowsh

    def LoadPrefs(self):
        """keep all prefs in a local var to avoid seraching all the time"""

        #Line clrs
        self._clrLineMat = prefs.GetPrefVal('clrLineMat', self._clrLineMat)
        self._clrLineEne = prefs.GetPrefVal('clrLineEne', self._clrLineEne)
        self._clrLineSig = prefs.GetPrefVal('clrLineSig', self._clrLineSig)

        #Line style
        self._sLineMat = prefs.GetPrefVal('sLineMat', self._sLineMat)
        self._sLineEne = prefs.GetPrefVal('sLineEne', self._sLineEne)
        self._sLineSig = prefs.GetPrefVal('sLineSig', self._sLineSig)
        
        #Port clrs
        self._clrPortMat = prefs.GetPrefVal('clrPortMat', self._clrPortMat)
        self._clrPortEne = prefs.GetPrefVal('clrPortEne', self._clrPortEne)
        self._clrPortSig = prefs.GetPrefVal('clrPortSig', self._clrPortSig)
        
        #Text
        self._fntUOName = prefs.GetPrefVal('fntUOName', self._fntUOName)
        self._clrUOName = prefs.GetPrefVal('clrUOName', self._clrUOName)

        #Pfd
        self._clrPfd = prefs.GetPrefVal('clrPfd', self._clrPfd)

        
    def SetFlowsheet(self, flowsh):
        """Sets a new flowsheet to the ctrl"""
        if not isinstance(flowsh, Flowsheet.Flowsheet):
            raise ValueError, "flowsh is not a valid flowsheet"
        self.flowsh = flowsh
        self._selection = []
        self.Refresh(0)

    def GetFlowsheet(self):
        return self.flowsh

    def OnPaint(self, event):
##        if self.errOnPaint: return
##        try:

        self._drawBase[0] = self.GetScrollPos(wxHORIZONTAL) + self._extent[0]
        self._drawBase[1] = self.GetScrollPos(wxVERTICAL) + self._extent[1]
        self._extent = [0, 0, 0, 0]

        dc = wxPaintDC(self)
        
        w, h = self.GetClientSize()
        bmp = wxEmptyBitmap(w, h)

        mdc = wxMemoryDC()
        mdc.SelectObject(bmp)
        mdc.SetBackground(wxBrush(self._clrPfd, wxSOLID))
        mdc.Clear()
        mdc.SetDeviceOrigin(-self._drawBase[0], -self._drawBase[1])
                          
        self._newSelectRegions = []
        self._drawnUOs = []

        #Get all uos to be drawn
        ##Cheating!! Should use a method instead of directly accessing the dictioanry
        uos = self.flowsh.chUODict.values()
        parent = self.flowsh.GetParent()
        while parent:
            uos.append(parent)            
            parent = parent.GetParent()


        #Force positions
        if self._forcePositonActive: self._ForceUOsPosition(uos)
        
        #Draw child uops
        myDict = {}
        for uo in uos:
            if self._firstTime:
                self._firstTime = 1
                self._DrawUO(mdc, uo)
            ports = uo.GetPorts(IN|OUT|MAT|ENE|SIG)
            self._drawnUOs.append(uo)
            myDict[uo] = ports
            

        #Draw connections
        self._drawnPortConn = []
        for uo in myDict.keys():
            ports = myDict[uo]
            if len(ports): port = ports.pop()
            else: port = None
            while port:
                if not port in self._drawnPortConn:
                    self._DrawConnection(mdc, uo, port)
                if len(ports): port = ports.pop()
                else: port = None

        del self._uoBuffer
        self._uoBuffer = bmp
        del mdc
        
        dc.DrawBitmap(bmp, 0, 0, 0)
        dc.SetDeviceOrigin(-self._drawBase[0], -self._drawBase[1])
        
        if self._state == self.CONNECTING_PORTS:
            self._DrawNewConnection(dc)

        if self._state == self.DRAGGING_SELECTION_BOX:
            self._DrawSelectionBox(dc)
        self._selectRegions = self._newSelectRegions

        self._AddExtent(self._drawBase[0] + 48, self._drawBase[1] + 48)
        self._AddExtent(self._drawBase[0] + w - 48, self._drawBase[1] + h - 48)
        self.SetScrollbar(wxHORIZONTAL, self._drawBase[0] - self._extent[0], w, self._extent[2] - self._extent[0])
        self.SetScrollbar(wxVERTICAL, self._drawBase[1] - self._extent[1], h, self._extent[3] - self._extent[1])


##        except Exception, e:
##            self.errOnPaint = True
##            print sys.exc_type
##            print e
##            import traceback
##            traceback.print_tb(sys.exc_traceback)
##            event.Skip()

    def OnMouse(self, event):
        pos = (event.m_x, event.m_y)
        pos = (pos[0] + self._drawBase[0], pos[1] + self._drawBase[1])
        fPath = self.flowsh.GetPath()
        if event.GetEventType() == wxEVT_MOTION:
            
            
            if self._state == self.DRAGGING_OBJS:
                diff = (pos[0] - self._dragSource[0], pos[1] - self._dragSource[1])
                self._locked = []
                for obj in self._selection:
                    self._MoveObjBy(obj, diff)
                for obj in self._locked:
                    if hasattr(object, 'Unlock'):
                        obj.Unlock()
                self._locked = []
                self._dragSource = pos
                self._forcePositonActive = False
                self.Refresh(0)
                self._forcePositonActive = True
            elif self._state == self.DRAGGING_SELECTION_BOX:

##                print 'pos as seen by the mouse ', event.m_x, ' ', event.m_y
##                print 'pos wit offset ', pos[0], ' ', pos[1]
##                print 'drawBases ', self._drawBase[0], ' ', self._drawBase[1]
                
                oldDragPos = self._dragPos
                self._dragPos = pos
                self._forcePositonActive = False
                self.Refresh(0)
                self._forcePositonActive = True
                
##                if not self._uoBuffer:
##                    self._forcePositonActive = False
##                    self.Refresh(0)
##                    self._forcePositonActive = True
##                else:
##                    dc = wxClientDC(self)
##                    x = min((oldDragPos[0], self._dragSource[0]))
##                    y = min((oldDragPos[1], self._dragSource[1]))
##                    w = abs(oldDragPos[0] - self._dragSource[0])
##                    h = abs(oldDragPos[1] - self._dragSource[1])
##                    
##                    bmp = self._uoBuffer.GetSubBitmap(wxRect(0, 0, 300, 300))
##                    dc.SetDeviceOrigin(-self._drawBase[0], -self._drawBase[1])
##                    dc.DrawBitmap(bmp, x, y, 0)
##                    
##                    self._DrawSelectionBox(dc)
##                    del dc
            elif self._state == self.CONNECTING_PORTS:
                obj = self._ObjUnder(pos)
                self._dragPos = pos
                self._connectionTo = None
                if isinstance(obj, Ports.Port) or isinstance(obj, LumpedPort):
                    tTo = obj.GetPortType()
                    tFrom = self._connectionFrom.GetPortType()
                    if (tFrom & ENE and tTo & ENE) or (tFrom & MAT and tTo & MAT):
                        if not (tFrom == tTo):
                            self._connectionTo = obj
                    elif (tFrom & SIG and tTo & SIG):
                        self._connectionTo = obj
                self._forcePositonActive = False
                self.Refresh(0)
                self._forcePositonActive = True
            elif self._state == self.NONE:
                
                obj = self._ObjUnder(pos)
                if isinstance(obj, PfdConnectionNode):
##                    obj._underMouse = 1
                    self.SetCursor(wxSTANDARD_CURSOR)
                    s = obj.GetConnection().GetDisplayName()
                    self.parent.SetStatusText('Connection: %s' %s)
##                    tip = self.GetToolTip()
##                    tip.Enable()
##                    tip.SetTip(obj.GetConnection().GetDisplayName())
                elif isinstance(obj, PfdConnectionSegment):
                    if obj.GetCanMoveType() == HORIZ:
                        self.SetCursor(wxStockCursor(wxCURSOR_SIZEWE))
                    else:
                        self.SetCursor(wxStockCursor(wxCURSOR_SIZENS))
                    s = obj.GetConnection().GetDisplayName()
                    self.parent.SetStatusText('Connection: %s' %s)
##                    tip = self.GetToolTip()
##                    tip.Enable()
##                    tip.SetTip(obj.GetConnection().GetDisplayName())
                elif isinstance(obj, Ports.Port):
                    s = obj.pfdInfoDict[fPath].GetDisplayName()
                    self.parent.SetStatusText('Port: %s' %s)
                    self.SetCursor(wxSTANDARD_CURSOR)
                elif isinstance(obj, LumpedPort):
                    s = obj.pfdInfoDict[fPath].GetDisplayName()
                    self.parent.SetStatusText('Lumped Port: %s' %s)
                    self.SetCursor(wxSTANDARD_CURSOR)
                elif isinstance(obj, UnitOperations.UnitOperation):
                    s = obj.pfdInfoDict[fPath].GetDisplayName()
                    self.parent.SetStatusText('Unit Operation: %s' %s)
                    self.SetCursor(wxSTANDARD_CURSOR)
                else:
                    self.SetCursor(wxSTANDARD_CURSOR)
                    self.parent.SetStatusText('')
##                    tip = self.GetToolTip()
##                    tip.Enable()
##                    tip.SetTip('')
 
        elif event.GetEventType() == wxEVT_LEFT_DOWN:
            obj = self._ObjUnder(pos)
            self._selConns = []
            if isinstance(obj, Ports.Port) or isinstance(obj, LumpedPort):
                self._state = self.CONNECTING_PORTS
                self._connectionFrom = obj
                self._dragPos = pos
                self._connectionTo = None
                self.CaptureMouse()
            elif isinstance(obj, UnitOperations.UnitOperation):
                if event.ControlDown():
                    if obj in self._selection:
                        self._selection.remove(obj)
                    else:
                        self._selection.append(obj)
                elif event.ShiftDown():
                    if obj not in self._selection:
                        self._selection.append(obj)
                    self._state = self.DRAGGING_OBJS
                    self._dragSource = pos
                    self.CaptureMouse()
                else:
                    if obj not in self._selection:
                        self._selection = [obj]
                    self._state = self.DRAGGING_OBJS
                    self._dragSource = pos
                    self.CaptureMouse()
            elif obj:
                self._selection = [obj]
                if hasattr(obj, 'GetConnection'):
                    conn = obj.GetConnection()
                    if conn: self._selConns = [conn]
                self._state = self.DRAGGING_OBJS
                self._dragSource = pos
                self.CaptureMouse()
            else:
                if not (event.ControlDown() or event.ShiftDown()):
                    self._selection = []
                self._state = self.DRAGGING_SELECTION_BOX
                self._dragSource = pos
                self._dragPos = pos
                self._xorSelection = event.ControlDown()
                self.CaptureMouse()
                
            self._forcePositonActive = False
            self.Refresh(0)
            self._forcePositonActive = True
            
        elif event.GetEventType() == wxEVT_LEFT_DCLICK:
            obj = self._ObjUnder(pos)
            self.View(obj)
            
        elif event.GetEventType() == wxEVT_LEFT_UP:
            if self._state == self.DRAGGING_SELECTION_BOX:
                inBox = self._ObjsInSelectionBox()
                for obj in inBox:
                    if isinstance(obj, UnitOperations.UnitOperation):
                        if obj not in self._selection:
                            self._selection.append(obj)
                        elif self._xorSelection:
                            self._selection.remove(obj)

            if self._state == self.DRAGGING_OBJS:
                conns = []
                for obj in self._selection:
                    if isinstance(obj, PfdConnectionNode):
                        c = obj.GetConnection()
                        if not c in conns:
                            c.VerifyNodeIntegrity()
                            conns.append(c)
                    elif isinstance(obj, PfdConnectionSegment):
                        c = obj.GetConnection()
                        if not c in conns:
                            c.VerifyNodeIntegrity()
                            conns.append(c)
                    elif isinstance(obj, UnitOperations.UnitOperation):
                        ports = obj.GetPorts(IN|OUT|MAT|ENE|SIG)
                        lP = obj.pfdInfoDict[fPath].GetLumpedPort(IN|MAT)
                        if lP: ports.extend(lP.GetPorts())
                        lP = obj.pfdInfoDict[fPath].GetLumpedPort(OUT|MAT)
                        if lP: ports.extend(lP.GetPorts())
                        lP = obj.pfdInfoDict[fPath].GetLumpedPort(IN|ENE)
                        if lP: ports.extend(lP.GetPorts())
                        lP = obj.pfdInfoDict[fPath].GetLumpedPort(OUT|ENE)
                        if lP: ports.extend(lP.GetPorts())
                        lP = obj.pfdInfoDict[fPath].GetLumpedPort(SIG)
                        if lP: ports.extend(lP.GetPorts())
                        for p in ports:
                            if hasattr(p, 'pfdInfoDict'):
                                if p.pfdInfoDict.get(fPath, None):
                                    c = p.pfdInfoDict[fPath].GetPfdConn()
                                    if c and not c in conns:
                                        c.VerifyNodeIntegrity()
                                        conns.append(c)

            if self._state:
                self.ReleaseMouse()
            
            oldstate = self._state
            self._state = self.NONE
            
            if oldstate == self.CONNECTING_PORTS and self._connectionTo:
                pFrom, pTo = self._connectionFrom, self._connectionTo
                self.ConnectPorts(pFrom, pTo)
                
            self._forcePositonActive = False
            self.Refresh(0)
            self._forcePositonActive = True

        elif event.GetEventType() == wxEVT_RIGHT_UP:
            self._selConns = []
            self._selection = []

            menu = None            
            obj = self._ObjUnder(pos)

            if not obj:
                menu = PfdMenu(self)
            elif isinstance(obj, PfdConnectionNode) or isinstance(obj, PfdConnectionSegment):
                conn = obj.GetConnection()
                self._selConns = [conn]
                menu = ConnMenu(self, conn)
            elif isinstance(obj, Ports.Port):
                self._selection = [obj]
                menu = PortMenu(self, obj)
            elif isinstance(obj, LumpedPort):
                self._selection = [obj]
                menu = LumpedPortMenu(self, obj)
            elif isinstance(obj, UnitOperations.UnitOperation):
                self._selection = [obj]
                menu = UnitOpMenu(self, obj)

            if menu:
                self.Refresh(0)
                x, y = event.GetPosition()
                self.PopupMenu(menu, wxPoint(x, y))
                menu.Destroy()
                
            self._selConns = []
            self._selection = []

            #Leave forcePosition active as the amount of ports could have changed            
            self.Refresh(0)


    def OnChar(self, event):
        if event.GetKeyCode() == 127:
            self.DeleteSelection()

    def ClonePort(self, obj):
        """Clone port. Obj can be a port or a stream"""
        fPath = self.flowsh.GetPath()
        if isinstance(obj, LumpedPort):
            d = SelectPortDialog(self, obj, fPath)
            if d.ShowModal() == wxID_OK:
                obj = d.GetSelectedPort()
            else:
                return
        if isinstance(obj, Ports.Port):
            s = obj.GetParent()
            t = obj.GetPortType()
            if t & IN: t = 1
            else: t = 0
        else:
            s = obj
            t = None

        if not (isinstance(s, Stream.Stream_Material) or \
           isinstance(s, Stream.Stream_Energy) or \
           isinstance(s, Stream.Stream_Signal)):
            return
        d = ClonePortDialog(self, s, t)
        if d.ShowModal() == wxID_OK:
            n = d.GetCloneName()
            t = d.GetCloneType()
        else:
            return
        
        #code = 'clone = Stream.ClonePort(' + str(t) + ')'
        #self.interpParent.SendAndExecCode(code)
        
        #path = s.GetPath()
        #if path[0] == '/': path = path[1:]
        #objs = string.split(path, ".")
        
        #code = 'parentFlowsh'
        #for uo in objs: code += '.GetChildUO("' + uo + '")'
        #code += '.AddObject(clone, "'+ str(n) + '")'
        #self.interpParent.SendAndExecCode(code)

        #code = 'del clone'
        #self.interpParent.SendAndExecCode(code)
        
        cmd = '%s.%s = Stream.ClonePort(%s)' %(path, n, t)
        self.interpParent.Eval(cmd)
        

    def ConnectPorts(self, pFrom, pTo):
        """Connect two ports (no matter order)"""
        fPath = self.flowsh.GetPath()
        if isinstance(pFrom, LumpedPort) or isinstance(pTo, LumpedPort):
            d = ConnectPortDialog(self, pFrom, pTo, fPath)
            if d.ShowModal() == wxID_OK:
                pFrom, pTo = d.GetSelectedPorts()
                if not pFrom or not pTo: return
            else:
                return
        if hasattr(pFrom, 'pfdInfoDict'):
            if pFrom.pfdInfoDict.get(fPath, None):
                pFrom.pfdInfoDict[fPath].SetPfdConn(None)
        if hasattr(pTo, 'pfdInfoDict'):
            if pTo.pfdInfoDict.get(fPath, None):
                pTo.pfdInfoDict[fPath].SetPfdConn(None)

        #path = pFrom.GetPath()
        #if path[0] == '/': path = path[1:]
        #objs = string.split(path, ".")
        #uOpNames1 = objs[:-1]           #List of uops 
        #portName1 = objs[-1]    #String with name of port

        #path = pTo.GetPath()
        #if path[0] == '/': path = path[1:]
        #objs = string.split(path, ".")
        #uOpNames2 = objs[:-1]           #List of uops 
        #portName2 = objs[-1]    #String with name of port
        
        #code = 'parentFlowsh'
        #for uo in uOpNames1: code += '.GetChildUO("' + uo + '")'
        #code += '.GetPort("' + portName1 + '").ConnectTo(parentFlowsh'
        #for uo in uOpNames2: code += '.GetChildUO("' + uo + '")'
        #code += '.GetPort("' + portName2 + '"))'
        #self.interpParent.SendAndExecCode(code)
        
        cmd = '%s -> %s' %(pFrom.GetPath(), pTo.GetPath())
        self.interpParent.Eval(cmd)
        

    def View(self, obj):
        """View an object if it has a valid frame"""
        fPath = self.flowsh.GetPath()
        frame = None
        if isinstance(obj, UnitOperations.UnitOperation):
            frame = FlowsheetFrame(self, sys.stdout, self.interpParent, obj, split=1)
        
        elif isinstance(obj, Ports.Port) or isinstance(obj, LumpedPort):
            if isinstance(obj, LumpedPort):
                d = SelectPortDialog(self, obj, fPath)
                if d.ShowModal() == wxID_OK:
                    obj = d.GetSelectedPort()
                    if not obj: return
                else:
                    return
            pt = obj.GetPortType()
            frame = None
            if pt & MAT:        
                frame = MaterialPortFrame(self, sys.stdout, self.interpParent, obj)
            elif pt & ENE:        
                frame = EnergyPortFrame(self, sys.stdout, self.interpParent, obj)
            elif pt & SIG:
                pass
                #frame = SignalPortFrame(self, sys.stdout, self.interpParent, obj)

        if frame:
            #Create a unique name        
            if hasattr(obj, 'GetPath'): name = obj.GetPath()
            else: name = 'frame' + str(len(self.frames))        
            self.frames[name] = frame
            frame.name = name
            
            #Show frame
            frame = self.frames[name]
            frame.Centre(wxBOTH)
            frame.Show(1)
            frame.Raise()

    def DeleteSelection(self):
        """Delete things that are selected"""
        self._holdRefresh = 1
        for obj in self._selConns: self.DeleteObject(obj)
        for obj in self._selection: self.DeleteObject(obj)
        self._selection = []                    
        self.holdRefresh = 0
        self.Refresh(0)        

    def DeleteObject(self, obj):        
        """Delete an object"""
        if isinstance(obj, PfdConnection):
            port = obj.GetPortIn()
            
            #path = port.GetPath()
            #if path[0] == '/': path = path[1:]
            #objs = string.split(path, ".")
            #uOpNames1 = objs[:-1]           #List of uops 
            #portName1 = objs[-1]    #String with name of port
            
            #code = 'parentFlowsh'
            #for uo in uOpNames1: code += '.GetChildUO("' + uo + '")'
            #code += '.GetPort("' + portName1 + '").Disconnect()'
            #self.interpParent.SendAndExecCode(code)
            
            cmd = '%s -> ' % (port.GetPath(),)
            self.interpParent.Eval(cmd)
    
        if isinstance(obj, UnitOperations.UnitOperation):

            #path = obj.GetPath()
            #if path[0] == '/': path = path[1:]
            #uos = string.split(path, ".")
            
            #code = 'parentFlowsh'
            #for uo in uos[:-1]: code += '.GetChildUO("' + uo + '")'
            #code += '.DeleteObject(parentFlowsh'
            #for uo in uos: code += '.GetChildUO("' + uo + '")'
            #code += ')'
            
            #self.interpParent.SendAndExecCode(code)
            
            cmd = 'delete %s' % (obj.GetPath(),)
            self.interpParent.Eval(cmd)


    def OnScroll(self, event):
        pos = self.GetScrollPos(event.GetOrientation())
        self.SetScrollPos(event.GetOrientation(), event.GetPosition())

        dim = 0
        if event.GetOrientation() == wxVERTICAL:
            dim = 1
            
        if event.GetEventType() == wxEVT_SCROLLWIN_TOP:
            self.SetScrollPos(event.GetOrientation(), 0)
        if event.GetEventType() == wxEVT_SCROLLWIN_BOTTOM:
            self.SetScrollPos(event.GetOrientation(), event.GetScrollRange(event.GetOrientation()))
        if event.GetEventType() == wxEVT_SCROLLWIN_LINEUP:
            self.SetScrollPos(event.GetOrientation(), pos - 96)
        if event.GetEventType() == wxEVT_SCROLLWIN_LINEDOWN:
            self.SetScrollPos(event.GetOrientation(), pos + 96)
        if event.GetEventType() == wxEVT_SCROLLWIN_PAGEUP:
            self.SetScrollPos(event.GetOrientation(), pos - self.GetClientSize()[dim])
        if event.GetEventType() == wxEVT_SCROLLWIN_PAGEDOWN:
            self.SetScrollPos(event.GetOrientation(), pos + self.GetClientSize()[dim])
        
        self.Refresh(0)

    def OnSize(self, event):
        self.Refresh(0)

    def _ObjUnder(self, pos):
        
        for region in self._selectRegions:
            ((x1, y1, x2, y2), item) = region
            if pos[0] >= x1 and pos[0] <= x2 and pos[1] >= y1 and pos[1] <= y2:
                return item

    def _ObjsInSelectionBox(self):
        def in_span(b1, e1, b2, e2):
            if b1 > e1:
                (b1, e1) = (e1, b1)
            if b2 > e2:
                (b2, e2) = (e2, b2)

            in_count = 0
            if b1 >= b2 and b1 <= e2:
                in_count += 1
            if e1 >= b2 and e1 <= e2:
                in_count += 1
            if b2 >= b1 and b2 <= e1:
                in_count += 1
            if e2 >= b1 and e2 <= e1:
                in_count += 1

            return in_count >= 2

        ret = []
        if self._state != self.DRAGGING_SELECTION_BOX:
            return []
        
        for region in self._selectRegions:
            ((x1, y1, x2, y2), item) = region

            if (in_span(x1, x2, self._dragSource[0], self._dragPos[0]) and
                    in_span(y1, y2, self._dragSource[1], self._dragPos[1])):
                if item not in ret:
                    ret.append(item)

        return ret

    def _MoveObjBy(self, obj, diff):
        fPath = self.flowsh.GetPath()
        if isinstance(obj, UnitOperations.UnitOperation):
            x, y = obj.pfdInfoDict[fPath].GetPosition()
            obj.pfdInfoDict[fPath].SetPosition((x + diff[0], y + diff[1]))

            ports = obj.GetPorts(IN|OUT|MAT|ENE|SIG)
            lP = obj.pfdInfoDict[fPath].GetLumpedPort(IN|MAT)
            if lP: ports.extend(lP.GetPorts())
            lP = obj.pfdInfoDict[fPath].GetLumpedPort(OUT|MAT)
            if lP: ports.extend(lP.GetPorts())
            lP = obj.pfdInfoDict[fPath].GetLumpedPort(IN|ENE)
            if lP: ports.extend(lP.GetPorts())
            lP = obj.pfdInfoDict[fPath].GetLumpedPort(OUT|ENE)
            if lP: ports.extend(lP.GetPorts())
            lP = obj.pfdInfoDict[fPath].GetLumpedPort(SIG)
            if lP: ports.extend(lP.GetPorts())

            #Get ports from flowsheet that are not borrowed out
            if isinstance(obj, Flowsheet.Flowsheet):
                tempPorts = obj.pfdInfoDict[fPath].GetPortList()
                for p in tempPorts:
                    if p not in ports:
                        ports.append(p)
            
            for p in ports:
                if hasattr(p, 'pfdInfoDict'):
                    if p.pfdInfoDict.get(fPath, None):
                        pfdConn = p.pfdInfoDict[fPath].GetPfdConn()
                        if pfdConn and not pfdConn in self._locked:
                            try: uo = p.GetConnection().pfdInfoDict[fPath].GetViewParent()
                            except: uo = None
                            if uo and uo in self._selection:
                                pfdConn.Move(diff)
                                self._locked.append(pfdConn)
                            else:
                                t = p.GetPortType()
                                if t & SIG:
                                    if p == pfdConn.GetPortOut():
                                        node = pfdConn.GetNode(0)
                                    else:
                                        node = pfdConn.GetNode(-1)
                                elif t & OUT:
                                    node = pfdConn.GetNode(0)
                                else:
                                    node = pfdConn.GetNode(-1)
                                if node and not node in self._selection and not node in self._locked:
                                    node.Move(diff)
    ##                                node.Lock()
    ##                                self._locked.append(node)
    ##                                prev = node.GetPrevious()
    ##                                if prev:
    ##                                    prev.Lock()
    ##                                    self._locked.append(prev)
    ##                                next = node.GetNext()
    ##                                if next:
    ##                                    next.Lock()
    ##                                    self._locked.append(next)


        elif isinstance(obj, PfdConnectionNode):
            obj.Move(diff)

        elif isinstance(obj, PfdConnectionSegment):
            obj.Move(diff)
            
    def _AddExtent(self, x, y):
        margin = 48
        
        if x - margin < self._extent[0]:
            self._extent[0] = x - margin
        if x + margin > self._extent[2]:
            self._extent[2] = x + margin
        if y - margin < self._extent[1]:
            self._extent[1] = y - margin
        if y + margin > self._extent[3]:
            self._extent[3] = y + margin


    def _DrawUO(self, dc, uo):
        """Draws uo and ports"""

##        #Make sure it has a position
##        self._ForcePosition(uo, self)
        fPath = self.flowsh.GetPath()
        #Check if selected        
        in_box = self._ObjsInSelectionBox()
        selected = uo in self._selection or uo in in_box
        if self._xorSelection and uo in self._selection and uo in in_box:
            selected = 0
        if selected:
            brush = wxBrush(wxColour(10, 20, 192))
            dc.SetTextForeground(wxColour(255, 255, 255))
        else:
            brush = wxBrush(wxColour(210, 200, 192))
            dc.SetTextForeground(self._clrUOName)
        dc.SetBrush(brush)
        dc.SetFont(self._fntUOName)

        #Draw uo
        x, y = uo.pfdInfoDict[fPath].GetPosition()
        self._AddExtent(x, y)
        bmp = uo.pfdInfoDict[fPath].GetBmp()
        if bmp:
            if selected: pass
            uow, uoh = bmp.GetWidth(), bmp.GetHeight()  #p height and width
##            mask = wxMaskColour(bmp, self._clrPfd)
##            bmp.SetMask(mask)
##            del mask
            dc.DrawBitmap(bmp, x, y, 1)
        else:
            uow, uoh = UODW, UODH
            pts = [ (x, y), (x + uow, y), (x + uow, y + uoh), (x, y + uoh) ]
            dc.DrawPolygon(map(lambda(arg): apply(wxPoint, arg), pts))
        self._newSelectRegions.append(((x, y, x + uow, y + uoh), uo))

        #Draw text
        tw, th = dc.GetTextExtent(uo.pfdInfoDict[fPath].GetDisplayName()) #Text height and width
        cx = x + uow/2 #center in the x axes
        if selected:
            pts = [ (cx - tw/2 - TIM, y + uoh + TM), (cx + tw/2 + TIM, y + uoh + TM), (cx + tw/2 + TIM, y + uoh + TM + th + 2*TIM), (cx - tw/2 - TIM, y + uoh + TM + th + 2*TIM) ]
            dc.DrawPolygon(map(lambda(arg): apply(wxPoint, arg), pts))
            
        dc.DrawText(uo.pfdInfoDict[fPath].GetDisplayName(), cx - tw/2, y + uoh + TM + TIM)
        #self._newSelectRegions.append(((cx - tw/2 - TIM, y + uoh + TM, cx + tw/2 + TIM, y + uoh + TM + th + 2*TIM), uo))

        #Draw ports
        if self._forcePositonActive: self._ForcePortsPosition(uo)
        self._DrawPorts(dc, uo.GetPorts(IN|MAT), IN|MAT, uo)
        self._DrawPorts(dc, uo.GetPorts(OUT|MAT), OUT|MAT, uo)
        self._DrawPorts(dc, uo.GetPorts(IN|ENE), IN|ENE, uo)
        self._DrawPorts(dc, uo.GetPorts(OUT|ENE), OUT|ENE, uo)
        self._DrawPorts(dc, uo.GetPorts(SIG), SIG, uo)


        del dc
        
    def _DrawPorts(self, dc, ports, type, uo):

        fPath = self.flowsh.GetPath()

        if type & MAT:
            dc.SetBrush(wxBrush(self._clrPortMat))    
        elif type & ENE:
            dc.SetBrush(wxBrush(self._clrPortEne))
        elif type & SIG:
            dc.SetBrush(wxBrush(self._clrPortSig))   
        else:
            dc.SetBrush(wxBrush(self._clrPortMat))   

        addRegion = 1

        port = uo.pfdInfoDict[fPath].GetLumpedPort(type)
        if port:
            px, py = port.pfdInfoDict[fPath].GetAbsPosition()
            bmp = port.pfdInfoDict[fPath].GetBmp()
            if bmp:
                if selected: pass
                pw, ph = bmp.GetWidth(), bmp.GetHeight()  #p height and width
                dc.DrawBitmap(bmp, px, py, 1)
            else:
                pw, ph = LPDW, LPDH
                pts = [ (px, py), (px + pw, py), (px + pw, py + ph), (px, py + ph) ]
                dc.DrawPolygon(map(lambda(arg): apply(wxPoint, arg), pts))
            self._newSelectRegions.append(((px, py, px + pw, py + ph), port))            

        else:
            for port in ports:
                #Draw
                px, py = port.pfdInfoDict[fPath].GetAbsPosition()
                bmp = port.pfdInfoDict[fPath].GetBmp()
                if bmp:
                    if selected: pass
                    pw, ph = bmp.GetWidth(), bmp.GetHeight()  #p height and width
                    dc.DrawBitmap(bmp, px, py, 1)
                else:
                    pw, ph = PDW, PDH
                    pts = [ (px, py), (px + pw, py), (px + pw, py + ph), (px, py + ph) ]
                    dc.DrawPolygon(map(lambda(arg): apply(wxPoint, arg), pts))
                self._newSelectRegions.append(((px, py, px + pw, py + ph), port))            

        del dc
        
    def _ForceUOsPosition(self, uos):
        """Forces a position for all the unit operations"""
        fPath = self.flowsh.GetPath()
        uosWPos = []
        uosWOPos = []
        usedAreas = []
        margin = 55
        xMin, yMin, xMax, yMax = None, None, None, None
        for uo in uos:
            if not hasattr(uo, 'pfdInfoDict'):
                uo.pfdInfoDict = {}
            pfdInfo = uo.pfdInfoDict.get(fPath, None)
            if not pfdInfo:
                pfdInfo = uo.pfdInfoDict[fPath] = PfdUOInfoHolder(uo, None, fPath)
            if not pfdInfo.WasPositionSet():
                uosWOPos.append(uo)
            else:
                uosWPos.append(uo)
                x, y = pfdInfo.GetPosition()
                w, h = pfdInfo.GetWidth(), pfdInfo.GetHeight()
                usedAreas.append((x, y, x+w, y+h))
                if xMin == None: xMin, yMin, xMax, yMax = x, y, x+w, y+h
                if x < xMin: xMin = x
                if y < yMin: yMin = y
                if x+w > xMax: xMax = x+w
                if y+h > yMax: yMax = y+h

        if not uosWOPos: return        

        def MyIsThereObjUnderRegion(region):
            l1, t1, r1, b1 = region #left, top, right, bottom
            for l2, t2, r2, b2 in usedAreas:
                if not (r1 < l2 or t1 > b2 or l1 > r2 or b1 < t2):
                    return True    
            return False

        if not uosWPos and uosWOPos: 
            uo = uosWOPos.pop()
            x, y = 100, 200
            w, h = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()
            uo.pfdInfoDict[fPath].SetPosition((x, y))
            uosWPos.append(uo)
            if xMin == None: xMin, yMin, xMax, yMax = x, y, x+w, y+h
            if x < xMin: xMin = x
            if y < yMin: yMin = y
            if x+w > xMax: xMax = x+w
            if y+h > yMax: yMax = y+h
            usedAreas.append((x, y, x+w, y+h))

        if uosWPos: uo = uosWPos.pop()
        else: uo = None

        while uo:
##            print '******************************************'
##            print 'uo', uo
            uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()
            uox, uoy = uo.pfdInfoDict[fPath].GetPosition()
##            print 'This uo is in  x, y, w, h:', uox, uoy, uow, uoh
            for p in uo.GetPorts(IN|OUT|MAT|ENE|SIG):
##                print 'usedAreas', usedAreas
                pos = None
##                print 'in port', p.GetPath()
                conn = p.GetConnection()
                if conn:
                    #Find parent
                    uoconn = conn.GetParent()
                    while uoconn:
                        if uoconn in uos: break
                        else: uoconn = uoconn.GetParent()
                        
##                    print 'connected to', uoconn.GetPath()

                    if uoconn and (uoconn in uosWOPos):
                        uoconnw, uoconnh = uoconn.pfdInfoDict[fPath].GetWidth(), uoconn.pfdInfoDict[fPath].GetHeight()
                        if p.GetPortType() & IN:
                            c = 1
                            while c <= 6 and not pos:
                                rLst = [0, -1, 1, 2, 3, 4, -2, -3]
                                for r in rLst:
                                    x, y = uox-(margin+uoconnw)*c, uoy + (margin+uoconnh)*r
                                    sex, sey = x + uoconnw, y + uoconnh
                                    if not MyIsThereObjUnderRegion((x, y, sex, sey)):
                                        pos = (x, y)
                                        break
                                c += 1
                        else:
                            c = 0
                            while c <= 6 and not pos:
                                rLst = [0, -1, 1, 2, 3, 4, -2, -3]
                                for r in rLst:
                                    x, y = uox+uow+(margin+uoconnw)*c, uoy+(margin+uoconnh)*r
                                    sex, sey = x + uoconnw, y + uoconnh
                                    if not MyIsThereObjUnderRegion((x, y, sex, sey)):
                                        pos = (x, y)
                                        break
                                c += 1
##                        print 'Position found', pos
                        if not pos: pos = (xMax + margin, yMax + margin)
                        uoconn.pfdInfoDict[fPath].SetPosition(pos)
                        idx = uosWOPos.index(uoconn)
                        del uosWOPos[idx]
                        uosWPos.append(uoconn)
                        usedAreas.append((pos[0], pos[1], pos[0]+uoconnw, pos[1]+uoconnh))
                        if pos[0] < xMin: xMin = pos[0]
                        if pos[1] < yMin: yMin = pos[1]
                        if pos[0]+uoconnw > xMax: xMax = pos[0]+uoconnw
                        if pos[1]+uoconnh > yMax: yMax = pos[1]+uoconnh
            if uosWOPos:
                if uosWPos:
                    uo = uosWPos.pop()
                else:
                    uo = uosWOPos.pop()
                    pos = (xMax + margin, yMax + margin)
                    uo.pfdInfoDict[fPath].SetPosition(pos)
                    uosWPos.append(uo)
                    w, h = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()
                    usedAreas.append((pos[0], pos[1], pos[0]+uow, pos[1]+uoh))
                    if pos[0] < xMin: xMin = pos[0]
                    if pos[1] < yMin: yMin = pos[1]
                    if pos[0]+w > xMax: xMax = pos[0]+w
                    if pos[1]+h > yMax: yMax = pos[1]+h
            else:
                uo = None

    def _ForcePortsPosition(self, uo):
        """Makes sure all ports of a certain unit op have position"""

        fPath = self.flowsh.GetPath()

        #Lets do the ports now...
        pDict = {}
        pDict[IN|MAT] = uo.GetPorts(IN|MAT)
        pDict[OUT|MAT] = uo.GetPorts(OUT|MAT)
        pDict[IN|ENE] = uo.GetPorts(IN|ENE)
        pDict[OUT|ENE] = uo.GetPorts(OUT|ENE)
        pDict[SIG] = uo.GetPorts(SIG)


        for lst in pDict.values():
            for p in lst:
                if not hasattr(p, 'pfdInfoDict'):
                    p.pfdInfoDict = {}
                if not p.pfdInfoDict.get(fPath, None):
                    p.pfdInfoDict[fPath] = PfdPortInfoHolder(p, uo, fPath)


        #Units that always have lumped ports...
        if isinstance(uo, Balance.BalanceOp) or isinstance(uo, Controller.Controller) or \
           isinstance(uo, Equation.Equation) or isinstance(uo, Equation.Add) or \
           isinstance(uo, Equation.Subtract) or isinstance(uo, Equation.Multiply) or \
           isinstance(uo, Equation.Divide) or isinstance(uo, Equation.Power) or \
           isinstance(uo, Equation.Equal) or isinstance(uo, Equation.Sqrt) or \
           isinstance(uo, CrossConnector.CrossConnector) or isinstance(uo, Set.Set):
            for t in pDict.keys():
                lP = uo.pfdInfoDict[fPath].GetLumpedPort(t)
                if pDict[t]:
                    if not lP: lP = LumpedPort(uo, t, fPath)
                    if not lP.pfdInfoDict[fPath].WasPositionSet():
                        pw, ph = lP.pfdInfoDict[fPath].GetWidth(), lP.pfdInfoDict[fPath].GetHeight()      #p height and width                 
                        uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                        if t == IN|MAT: pos = (-pw - PM, 15 - ph/2)
                        elif t == OUT|MAT: pos = (uow + PM, 15 - ph/2)
                        elif t == IN|ENE: pos = (-pw - PM, 31 - ph/2)
                        elif t == OUT|ENE: pos = (uow + PM, 31 - ph/2)
                        elif t == SIG: pos = (-pw - PM, 47 - ph/2)
                        lP.pfdInfoDict[fPath].SetPosition(pos)
                        for p in pDict[t]:
                            p.pfdInfoDict[fPath].SetPosition(pos)
                else:
                    if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)

        elif isinstance(uo, Flowsheet.Flowsheet) or isinstance(uo, Flowsheet.SubFlowsheet):
            for t in pDict.keys():
                lP = uo.pfdInfoDict[fPath].GetLumpedPort(t)
                if not lP: lP = LumpedPort(uo, t, fPath)
                if not lP.pfdInfoDict[fPath].WasPositionSet():
                    pw, ph = lP.pfdInfoDict[fPath].GetWidth(), lP.pfdInfoDict[fPath].GetHeight()      #p height and width                 
                    uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                    if t == IN|MAT: pos = (-pw - PM, 15 - ph/2)
                    elif t == OUT|MAT: pos = (uow + PM, 15 - ph/2)
                    elif t == IN|ENE: pos = (-pw - PM, 31 - ph/2)
                    elif t == OUT|ENE: pos = (uow + PM, 31 - ph/2)
                    elif t == SIG: pos = (-pw - PM, 47 - ph/2)
                    lP.pfdInfoDict[fPath].SetPosition(pos)
                    for p in pDict[t]:
                        p.pfdInfoDict[fPath].SetPosition(pos)
                        
        elif isinstance(uo, ComponentSplitter.ComponentSplitter) or isinstance(uo, Split.Splitter):
            t = IN|MAT
            self._DistributePorts(uo, pDict[t], t, 1, LEFT_LOC)
            
            t = OUT|MAT
            names, ports = uo.GetPortNames(t), []
            names.sort()
            for name in names: ports.append(uo.GetPort(name))
            self._DistributePorts(uo, ports, t, 5, RIGHT_LOC)

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOM_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 1, TOP_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)


        elif isinstance(uo, ConvRxn.ConvReactor):
            t = IN|MAT
            names, ports = uo.GetPortNames(t), []
            names.sort()
            for name in names: ports.append(uo.GetPort(name))
            self._DistributePorts(uo, ports, t, 5, LEFT_LOC)
            
            t = OUT|MAT
            names, ports = uo.GetPortNames(t), []
            names.sort()
            for name in names: ports.append(uo.GetPort(name))
            self._DistributePorts(uo, ports, t, 5, RIGHT_LOC)

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 2, BOTTOM_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 2, TOP_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)


        elif isinstance(uo, Heater.Cooler):
            t = IN|MAT        
            self._DistributePorts(uo, pDict[t], t, 1, LEFT_LOC)
            
            t = OUT|MAT
            self._DistributePorts(uo, pDict[t], t, 1, RIGHT_LOC)

            t = IN|ENE
            lP = uo.pfdInfoDict[fPath].GetLumpedPort(t)
            ports = pDict[t]
            nuPorts = len(ports)
            if nuPorts:
                p = ports[0]
                pw, ph = p.pfdInfoDict[fPath].GetWidth(), p.pfdInfoDict[fPath].GetHeight()      #p height and width
                uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                pos = (uow - 1 - pw/2, -ph - PM)
                if nuPorts == 1:
                    if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)
                    ports[0].pfdInfoDict[fPath].SetPosition(pos)
                else:
                    if not lP: lP = LumpedPort(uo, t, fPath)
                    lP.pfdInfoDict[fPath].SetPosition(pos)
                    for p in ports:
                        p.pfdInfoDict[fPath].SetPosition(pos)
            else:
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)         

            t = OUT|ENE
            lP = uo.pfdInfoDict[fPath].GetLumpedPort(t)
            ports = pDict[t]
            nuPorts = len(ports)
            if nuPorts:
                p = ports[0]
                pw, ph = p.pfdInfoDict[fPath].GetWidth(), p.pfdInfoDict[fPath].GetHeight()      #p height and width
                uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                pos = (4 - pw/2, uoh + PM)
                if nuPorts == 1:
                    if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)
                    ports[0].pfdInfoDict[fPath].SetPosition(pos)
                else:
                    if not lP: lP = LumpedPort(uo, t, fPath)
                    lP.pfdInfoDict[fPath].SetPosition(pos)
                    for p in ports:
                        p.pfdInfoDict[fPath].SetPosition(pos)
            else:
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)

            
        elif isinstance(uo, Compressor.Compressor):
            t = IN|MAT
            self._DistributePorts(uo, pDict[t], t, 2, LEFT_LOC)
            
            t = OUT|MAT
            self._DistributePorts(uo, pDict[t], t, 2, RIGHT_LOC)          

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 2, BOTTOM_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 2, TOP_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)

            
        elif isinstance(uo, Compressor.Expander):
            t = IN|MAT
            self._DistributePorts(uo, pDict[t], t, 2, LEFT_LOC)
            
            t = OUT|MAT
            self._DistributePorts(uo, pDict[t], t, 2, RIGHT_LOC)          

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 2, BOTTOM_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 2, TOP_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)

           
        elif isinstance(uo, Heater.Heater):
            t = IN|MAT        
            self._DistributePorts(uo, pDict[t], t, 1, LEFT_LOC)
            
            t = OUT|MAT
            self._DistributePorts(uo, pDict[t], t, 1, RIGHT_LOC)

            t = IN|ENE
            lP = uo.pfdInfoDict[fPath].GetLumpedPort(t)
            ports = pDict[t]
            nuPorts = len(ports)
            if nuPorts:
                p = ports[0]
                pw, ph = p.pfdInfoDict[fPath].GetWidth(), p.pfdInfoDict[fPath].GetHeight()      #p height and width
                uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                pos = (1 - pw/2, uoh + PM)
                if nuPorts == 1:
                    if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)
                    ports[0].pfdInfoDict[fPath].SetPosition(pos)
                else:
                    if not lP: lP = LumpedPort(uo, t, fPath)
                    lP.pfdInfoDict[fPath].SetPosition(pos)
                    for p in ports:
                        p.pfdInfoDict[fPath].SetPosition(pos)
            else:
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)         

            t = OUT|ENE
            lP = uo.pfdInfoDict[fPath].GetLumpedPort(t)
            ports = pDict[t]
            nuPorts = len(ports)
            if nuPorts:
                p = ports[0]
                pw, ph = p.pfdInfoDict[fPath].GetWidth(), p.pfdInfoDict[fPath].GetHeight()      #p height and width
                uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                pos = (uow - 4 - pw/2, -ph - PM)
                if nuPorts == 1:
                    if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)
                    ports[0].pfdInfoDict[fPath].SetPosition(pos)
                else:
                    if not lP: lP = LumpedPort(uo, t, fPath)
                    lP.pfdInfoDict[fPath].SetPosition(pos)
                    for p in ports:
                        p.pfdInfoDict[fPath].SetPosition(pos)
            else:
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, t)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)

            
        elif isinstance(uo, Heater.HeatExchanger):
            pIC, pIH = uo.GetPort(IN_PORT + 'C'), uo.GetPort(IN_PORT + 'H')
            pOC, pOH = uo.GetPort(OUT_PORT + 'C'), uo.GetPort(OUT_PORT + 'H')
            prob = 0
            if None in (pIC, pIH, pOC, pOH): prob = 1
            if len(pDict[IN|MAT]) != 2 or len(pDict[OUT|MAT]) != 2: prob = 1

            if not prob:
                lP = uo.pfdInfoDict[fPath].GetLumpedPort(IN|MAT)
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, IN|MAT)
                lP = uo.pfdInfoDict[fPath].GetLumpedPort(OUT|MAT)
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, OUT|MAT)
                pw, ph = pIC.pfdInfoDict[fPath].GetWidth(), pIC.pfdInfoDict[fPath].GetHeight()      #p height and width
                uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                
                pos = (-pw - PM, uoh/2 - ph/2)
                pIC.pfdInfoDict[fPath].SetPosition(pos)
                pos = (uow + PM, uoh/2 - ph/2)
                pOC.pfdInfoDict[fPath].SetPosition(pos)
                
                pos = (21 - pw/2, uoh + PM)
                pIH.pfdInfoDict[fPath].SetPosition(pos)
                pos = (49 - pw/2, -ph - PM)
                pOH.pfdInfoDict[fPath].SetPosition(pos)
                
            else:
                t = IN|MAT
                self._DistributePorts(uo, pDict[t], t, 3, LEFT_LOC)
                
                t = OUT|MAT
                self._DistributePorts(uo, pDict[t], t, 3, RIGHT_LOC)          

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOM_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 1, TOP_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)

            
            
        elif isinstance(uo, Mixer.Mixer):
            t = IN|MAT
            names, ports = uo.GetPortNames(t), []
            names.sort()
            for name in names: ports.append(uo.GetPort(name))            
            self._DistributePorts(uo, ports, t, 5, LEFT_LOC)
            
            t = OUT|MAT
            self._DistributePorts(uo, pDict[t], t, 1, RIGHT_LOC)

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOM_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 1, TOP_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)



        elif isinstance(uo, Pump.Pump):
            pI, pO = uo.GetPort(IN_PORT), uo.GetPort(OUT_PORT)
            prob = 0
            if None in (pI, pO): prob = 1
            if len(pDict[IN|MAT]) != 1 or len(pDict[OUT|MAT]) != 1: prob = 1

            if not prob:
                lP = uo.pfdInfoDict[fPath].GetLumpedPort(IN|MAT)
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, IN|MAT)
                lP = uo.pfdInfoDict[fPath].GetLumpedPort(OUT|MAT)
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, OUT|MAT)
                pw, ph = pI.pfdInfoDict[fPath].GetWidth(), pI.pfdInfoDict[fPath].GetHeight()      #p height and width
                uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                
                pos = (-pw - PM, uoh/2 - ph/2)
                pI.pfdInfoDict[fPath].SetPosition(pos)
                pos = (uow + PM, 3 - ph/2)
                pO.pfdInfoDict[fPath].SetPosition(pos)
                
            else:
                t = IN|MAT
                self._DistributePorts(uo, pDict[t], t, 3, LEFT_LOC)
                
                t = OUT|MAT
                self._DistributePorts(uo, pDict[t], t, 3, RIGHT_LOC)          

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 2, BOTTOM_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 2, TOP_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)


            
        elif isinstance(uo, Flash.SimpleFlash):
            pI = uo.GetPort(IN_PORT)
            nLPh = uo.NumberLiqPhases()
            pV, pL1, pL2 = uo.GetPort(V_PORT), uo.GetPort(L_PORT + '0'), uo.GetPort(L_PORT + '1')
            
            prob = 0
            if None in (pI, pV, pL1): prob = 1
            if len(pDict[IN|MAT]) != 1 or len(pDict[OUT|MAT]) != nLPh+1 or nLPh > 2: prob = 1
            if not prob:
                lP = uo.pfdInfoDict[fPath].GetLumpedPort(IN|MAT)
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, IN|MAT)
                lP = uo.pfdInfoDict[fPath].GetLumpedPort(OUT|MAT)
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, OUT|MAT)
                pw, ph = pI.pfdInfoDict[fPath].GetWidth(), pI.pfdInfoDict[fPath].GetHeight()      #p height and width
                uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width
                
                pos = (-pw - PM, uoh/2 - ph/2)
                pI.pfdInfoDict[fPath].SetPosition(pos)
                pos = (36 - pw/2, -ph - PM)
                pV.pfdInfoDict[fPath].SetPosition(pos)
                pos = (uow + PM, 51 - ph/2)
                pL1.pfdInfoDict[fPath].SetPosition(pos)
                if pL2:
                    pos = (36 - pw/2, uoh + PM)
                    pL2.pfdInfoDict[fPath].SetPosition(pos)
                
            else:
                t = IN|MAT
                self._DistributePorts(uo, pDict[t], t, 3, LEFT_LOC)
                
                t = OUT|MAT
                self._DistributePorts(uo, pDict[t], t, 4, RIGHT_LOC)    

            
            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMRIGHT_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 1, TOPLEFT_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)



##        elif isinstance(uo, Tower.DistillationColumn):
##            fName = 'distcol.bmp'
##        elif isinstance(uo, Tower.RefluxedAbsorber):
##            fName = 'distcol.bmp'            
##        elif isinstance(uo, Tower.ReboiledAbsorber):
##            fName = 'distcol.bmp'
##        elif isinstance(uo, Tower.Absorber):
##            fName = 'distcol.bmp'
##        elif isinstance(uo, Tower.Tower):
##            fName = 'distcol.bmp'

        elif isinstance(uo, Stream.Stream_Material) or isinstance(uo, Valve.Valve):
            t = IN|MAT
            self._DistributePorts(uo, pDict[t], t, 1, LEFT_LOC)
            
            t = OUT|MAT
            self._DistributePorts(uo, pDict[t], t, 1, RIGHT_LOC)

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 1, TOPRIGHT_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, TOP_LOC)

            
        elif isinstance(uo, Stream.Stream_Energy):
            t = IN|MAT
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)
            
            t = OUT|MAT
            self._DistributePorts(uo, pDict[t], t, 1, TOPRIGHT_LOC)

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 1, LEFT_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 1, RIGHT_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, TOP_LOC)



        elif isinstance(uo, Stream.Stream_Signal):
            t = IN|MAT
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)
            
            t = OUT|MAT
            self._DistributePorts(uo, pDict[t], t, 1, TOPRIGHT_LOC)

            t = IN|ENE
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOM_LOC)

            t = OUT|ENE
            self._DistributePorts(uo, pDict[t], t, 1, TOPLEFT_LOC)

            t = SIG
            lst0 = [uo.GetPort(IN_PORT)]
            self._DistributePorts(uo, lst0, t, 1, LEFT_LOC)
            lst1 = [uo.GetPort(OUT_PORT)]
            self._DistributePorts(uo, lst1, t, 1, RIGHT_LOC)
            if len(pDict[t]) > 2:
                pDict[t].remove(lst0[0])
                pDict[t].remove(lst1[0])
                self._DistributePorts(uo, pDict[t], t, 1, TOP_LOC)
            

            
        else:
            t = IN|MAT
            names, ports = uo.GetPortNames(t), []
            names.sort()
            for name in names: ports.append(uo.GetPort(name))
            self._DistributePorts(uo, ports, t, 5, LEFT_LOC)
            
            t = OUT|MAT
            names, ports = uo.GetPortNames(t), []
            names.sort()
            for name in names: ports.append(uo.GetPort(name))
            self._DistributePorts(uo, ports, t, 5, RIGHT_LOC)

            t = IN|ENE
            names, ports = uo.GetPortNames(t), []
            names.sort()
            for name in names: ports.append(uo.GetPort(name))
            self._DistributePorts(uo, ports, t, 3, BOTTOM_LOC)

            t = OUT|ENE
            names, ports = uo.GetPortNames(t), []
            names.sort()
            for name in names: ports.append(uo.GetPort(name))
            self._DistributePorts(uo, ports, t, 3, TOP_LOC)

            t = SIG
            self._DistributePorts(uo, pDict[t], t, 1, BOTTOMLEFT_LOC)

            

    def _DistributePorts(self, uo, ports, type, max, loc):
        """Sets the position of ports by distributing then in one side of the uo.
            Lumps the ports if they are more than max
            If ports go in the corner, then max <=1
        """
        fPath = self.flowsh.GetPath()
        lP = uo.pfdInfoDict[fPath].GetLumpedPort(type)
        nuPorts = len(ports)
        if nuPorts:
            p = ports[0]
            pw, ph = p.pfdInfoDict[fPath].GetWidth(), p.pfdInfoDict[fPath].GetHeight()      #p height and width                 
            uow, uoh = uo.pfdInfoDict[fPath].GetWidth(), uo.pfdInfoDict[fPath].GetHeight()  #uo height and width

            #Separate ports
            if loc == TOPRIGHT_LOC or loc == BOTTOMLEFT_LOC or loc == TOPLEFT_LOC or loc == BOTTOMRIGHT_LOC:
                max = 1
            if nuPorts <= max:
                if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, type)
                for i in range(nuPorts):
                    if loc == LEFT_LOC:
                        step = uoh/(nuPorts+1)
                        pos = (-pw - PM, step*(i+1) - ph/2)
                    elif loc == RIGHT_LOC:
                        step = uoh/(nuPorts+1)
                        pos = (uow + PM, step*(i+1) - ph/2)
                    elif loc == BOTTOM_LOC:
                        step = uow/(nuPorts+1)
                        pos = (step*(i+1) - pw/2, uoh + PM)
                    elif loc == TOP_LOC:
                        step = uow/(nuPorts+1)
                        pos = (step*(i+1) - pw/2, -ph - PM)
                    elif loc == TOPRIGHT_LOC:
                        pos = (uow + PM, 0)
                    elif loc == BOTTOMLEFT_LOC:
                        pos = (-pw - PM, uoh - ph)
                    elif loc == TOPLEFT_LOC:
                        pos = (-pw - PM, 0)
                    elif loc == BOTTOMRIGHT_LOC:
                        pos = (uow + PM, uoh - ph)
                        
                    ports[i].pfdInfoDict[fPath].SetPosition(pos)
                    
            #Lumped ports
            else:
                if not lP: lP = LumpedPort(uo, type, fPath)
                if loc == LEFT_LOC:
                    pos = (-pw - PM, uoh/2 - ph/2)
                elif loc == RIGHT_LOC:
                    pos = (uow + PM, uoh/2 - ph/2)
                elif loc == BOTTOM_LOC:
                    pos = (uow/2 - pw/2, uoh + PM)
                elif loc == TOP_LOC:
                    pos = (uow/2 - pw/2, -ph - PM)
                elif loc == TOPRIGHT_LOC:
                    pos = (uow + PM, 0)
                elif loc == BOTTOMLEFT_LOC:
                    pos = (-pw - PM, uoh - ph)
                elif loc == TOPLEFT_LOC:
                    pos = (-pw - PM, 0)
                elif loc == BOTTOMRIGHT_LOC:
                    pos = (uow + PM, uoh - ph)
                lP.pfdInfoDict[fPath].SetPosition(pos)
                for p in ports:
                    p.pfdInfoDict[fPath].SetPosition(pos)
                    
        else:
            if lP: uo.pfdInfoDict[fPath].SetLumpedPort(None, type)


    def _DrawConnection(self, dc, uo, port):
        """Draws a connection of a port"""
        fPath = self.flowsh.GetPath()
        in_box = self._ObjsInSelectionBox()
        selected = port in self._selection or port in in_box
        if self._xorSelection and port in self._selection and port in in_box:
            selected = 0

        conn = port.GetConnection()
        if not conn: return
        self._drawnPortConn.append(conn)

        pt = port.GetPortType()
        ct = conn.GetPortType()
        pName = port.GetPath()
        cName = conn.GetPath()
        
        #Find parent
        uoconn = conn.GetParent()
        while uoconn:
            if uoconn in self._drawnUOs:
                break
            else:
                uoconn = uoconn.GetParent()

        if not uoconn: return #Should raise error

        #Check who is "in" and who is "out" and check if they are lumped
        if not hasattr(conn, 'pfdInfoDict'):
            conn.pfdInfoDict = {}
        if not conn.pfdInfoDict.get(fPath, None):
            conn.pfdInfoDict[fPath] = PfdInfoHolder(conn, uoconn, fPath)
        if isinstance(uoconn, Flowsheet.Flowsheet):
            pTemp = uoconn.pfdInfoDict[fPath].GetLumpedPort(ct)
            conn.pfdInfoDict[fPath].SetPosition(pTemp.pfdInfoDict[fPath].GetPosition())
            uoconn.pfdInfoDict[fPath].AddToPortList(conn)
##        self._ForcePosition(conn, uoconn)        
        
        if pt & IN:
            pIn, pOut = port, conn
            displayName = cName + " : " + pName
        else:
            pIn, pOut = conn, port
            displayName = pName + " : " + cName


        #Set a connection object if needed
    
        pfdConn = pIn.pfdInfoDict[fPath].GetPfdConn()
        if not pfdConn:
            pfdConn = PfdConnection(fPath)        
            pIn.pfdInfoDict[fPath].SetPfdConn(pfdConn)
            pOut.pfdInfoDict[fPath].SetPfdConn(pfdConn)
            pfdConn.SetPortIn(pIn)
            pfdConn.SetPortOut(pOut)
            pfdConn.InitNodes()
        else:
            pfdConn.SetPortIn(pIn)
            pfdConn.SetPortOut(pOut)            
            
        pfdConn.SetDisplayName(displayName)


        #Set joints of connections
        px, py = pOut.pfdInfoDict[fPath].GetAbsPosition()
        pw, ph = pOut.pfdInfoDict[fPath].GetWidth(), pOut.pfdInfoDict[fPath].GetHeight()        
        cx, cy = pIn.pfdInfoDict[fPath].GetAbsPosition()
        cw, ch = pIn.pfdInfoDict[fPath].GetWidth(), pIn.pfdInfoDict[fPath].GetHeight()   
        displayName = pfdConn.GetDisplayName()
            
        self._AddExtent(px, py)
        self._AddExtent(cx, cy)

        #Draw line
        #Blue
        thick = 1
        if pfdConn in self._selConns: thick = 2
        if pt & MAT and ct & MAT: clr = self._clrLineMat
        elif pt & ENE and ct & ENE: clr = self._clrLineEne
        elif pt & SIG or ct & SIG: clr = self._clrLineSig
        else: clr = clr = wxColour(64, 128, 128) #Whatever so I know there is something wrong
        dc.SetPen(wxPen(clr, thick, self._sLineMat))
        dc.SetBrush(wxBrush(clr))

        fx, fy = px + pw/2, py + ph/2 #from x, y
        cnt = pfdConn.GetNodeCount()
        txtidx = cnt/2
        for i in range(cnt):
            node = pfdConn.GetNode(i)
            tx, ty = node.GetPosition()
            dc.DrawLine(fx, fy, tx, ty)
            if i == cnt-1:
                if fx == tx and not pt & SIG:
                    if fy <= ty:
                        pts = [ (tx, ty), (tx + AB/2, ty - AH), (tx - AB/2, ty - AH) ]
                    else:
                        pts = [ (tx, ty), (tx + AB/2, ty + AH), (tx - AB/2, ty + AH) ]
                elif fy == ty and not pt & SIG:
                    if fx <= tx:
                        pts = [ (tx, ty), (tx  - AH, ty + AB/2), (tx - AH, ty - AB/2) ]
                    else:
                        pts = [ (tx, ty), (tx  + AH, ty + AB/2), (tx + AH, ty - AB/2) ]
                else:
                    pts = [ (tx - NDW/2, ty - NDH/2), (tx + NDW/2, ty - NDH/2), (tx + NDW/2, ty + NDH/2), (tx - NDW/2, ty + NDH/2) ]
                dc.DrawPolygon(map(lambda(arg): apply(wxPoint, arg), pts))
            else:
                if self._viewNodes or node._underMouse:
                    pts = [ (tx - NDW/2, ty - NDH/2), (tx + NDW/2, ty - NDH/2), (tx + NDW/2, ty + NDH/2), (tx - NDW/2, ty + NDH/2) ]
                    dc.DrawPolygon(map(lambda(arg): apply(wxPoint, arg), pts))
                    node._underMouse = 0
            
                       
            if i > 0 and i < cnt-1:
                self._newSelectRegions.append(((tx - NDW/2, ty - NDH/2, tx + NDW/2, ty + NDH/2), node))

            if i > 0 and i <= cnt-1:
                if fy == ty and abs(tx - fx) > NDW:
                    if i == cnt-1: seg = PfdConnectionSegment(oldNode, VERT)
                    else: seg = PfdConnectionSegment(node, VERT)
                    if tx > fx:
                        self._newSelectRegions.append(((fx + NDW/2, fy - 1, tx - NDW/2, fy + 1), seg))
                    else:
                        self._newSelectRegions.append(((tx + NDW/2, fy - 1, fx - NDW/2, fy + 1), seg))
                elif fx == tx and abs(ty - fy) > NDH:
                    if i == cnt-1: seg = PfdConnectionSegment(oldNode, HORIZ)
                    else: seg = PfdConnectionSegment(node, HORIZ)
                    if ty > fy:
                        self._newSelectRegions.append(((fx - 1, fy + NDH/2, fx + 1, ty - NDH/2), seg))
                    else:
                        self._newSelectRegions.append(((fx - 1, ty + NDH/2, fx + 1, fy - NDH/2), seg))
                                   
            oldNode = node
            fx, fy = tx, ty

        tx, ty = cx + cw/2, cy + ch/2
        dc.DrawLine(fx, fy, tx, ty)

    def _DrawNewConnection(self, dc):
        """Draw a potential connection from port to mouse pointer or nearby port"""
        fPath = self.flowsh.GetPath()
        info = self._connectionFrom.pfdInfoDict[fPath]
        px, py = info.GetAbsPosition()
        pw, ph = info.GetWidth(), info.GetHeight()

        drx, dry = self._dragPos                    #drag x and y

        if self._connectionTo:
            info = self._connectionTo.pfdInfoDict[fPath]
            drx, dry = info.GetAbsPosition()
            cw, ch = info.GetWidth(), info.GetHeight()
            drx, dry = (drx + cw/2, dry + ch/2)
            dc.SetPen(wxPen(wxColour(0, 0, 0), 1, wxSOLID))
        else:
            dc.SetPen(wxPen(wxColour(0, 0, 0), 1, wxDOT))
            
        dc.DrawLine(px + pw/2, py + ph/2, drx, dry)

    def _DrawSelectionBox(self, dc):
        pen = wxPen(wxColour(0, 0, 0), 1, wxDOT)
        dc.SetPen(pen)
        
        dc.DrawLine(self._dragSource[0], self._dragSource[1], self._dragPos[0], self._dragSource[1])
        dc.DrawLine(self._dragPos[0], self._dragSource[1], self._dragPos[0], self._dragPos[1])
        dc.DrawLine(self._dragSource[0], self._dragPos[1], self._dragPos[0], self._dragPos[1])
        dc.DrawLine(self._dragSource[0], self._dragSource[1], self._dragSource[0], self._dragPos[1])

    def CleanUp(self):
        del self.frames

    def UpdateView(self):
        if not self._holdRefresh:
            self.Refresh(0)
        try:
            for frame in self.frames.values():
                if hasattr(frame, 'UpdateView'):
                    frame.UpdateView()
        except:
            pass

class PfdDropTarget(wxPyDropTarget):
    def __init__(self, ctrl):
        wxPyDropTarget.__init__(self)
        self.data = wxCustomDataObject(wxCustomDataFormat("UnitOp"))
        self.SetDataObject(self.data)

        self.ctrl = ctrl
        
##    def OnEnter(self, x, y, d):
##        return d
##
##    def OnLeave(self):
##        pass
##
##    def OnDrop(self, x, y):
##        return true
##
##    def OnDragOver(self, x, y, d):
##        return d
    
    def OnData(self, x, y, d):
        if self.GetData():
            uoInfo = self.data.GetData()

            name, fileName, className = tuple(string.split(uoInfo, ' '))

            import random
            name = 'name' + str(random.randint(0, 1000))
            
            #code = 'uOp = ' + className + '()'
            #self.ctrl.interpParent.SendAndExecCode(code)
            
            #path = self.ctrl.flowsh.GetPath()
            #if path[0] == '/' and len(path) > 1:
                #path = path[1:]
                #uOpNames = string.split(path, ".")
            #else:
                #uOpNames = []

            #code = 'parentFlowsh'
            #for uo in uOpNames: code += '.GetChildUO("' + uo + '")'
            #code += '.AddUnitOperation(uOp, "' + name + '")'
            #self.ctrl.interpParent.SendAndExecCode(code)
            
            #code = 'del uOp'
            #self.ctrl.interpParent.SendAndExecCode(code)

            obj = self.ctrl.GetSimObject()
            objPath = obj.GetPath()
            if objPath != '/':
                objPath += '.'
            cmd = '%s%s = %s()' %(objPath, name, className)
            self.ctrl.interpParent.Eval(cmd)
            
            self.ctrl.Refresh(0)
            
        return d


class UnitOpDragSource(wxWindow):
    def __init__(self, parent, frameParent, id,
                 pos = wxDefaultPosition, size = wxDefaultSize,
                 style = 0, name = "UnitOpDragSource"):
        wxWindow.__init__(self, parent, id, pos = pos, size = size, style = style, name = name)
        self.SetBackgroundColour(wxColour(255, 255, 255))

        self.frameParent = frameParent
        self.__uops = UOps
        self.__draggable = []

        EVT_PAINT(self, self.on_paint)
        EVT_MOUSE_EVENTS(self, self.on_mouse)
        EVT_SIZE(self, self.on_resize)
        EVT_SCROLLWIN(self, self.on_scroll)


    def on_paint(self, evt):
        dc = wxPaintDC(self)
        dc.SetDeviceOrigin(0, -self.GetScrollPos(wxVERTICAL))
        dc.SetFont(wxFont(8, wxSWISS, wxNORMAL, wxNORMAL))

        pos = (32, 32)
        self.__draggable = []
        for uo in self.__uops:
            name = uo.name
            bmp = uo.bmp
            
            self.__draggable.append(((pos[0] - 32, pos[1] - 32), uo))
            dc.DrawBitmap(bmp, pos[0], pos[1], 1)
            bmph, bmpw = bmp.GetHeight(), bmp.GetWidth()
            (w, h) = dc.GetTextExtent(name)
            dc.DrawText(name, pos[0] + (bmpw - w) / 2, pos[1] + bmph+2)

            pos = (pos[0] + 96, pos[1])
            if pos[0] >= self.GetSize()[0] - 64:
                pos = (32, pos[1] + 96)

        width = self.GetSize()[0] / 96
        if width < 1:
            width = 1
        height = 96 * int(math.ceil(len(self.__uops) / float(width)))
        self.SetScrollbar(wxVERTICAL, self.GetScrollPos(wxVERTICAL), self.GetSize()[1], height)

    def on_scroll(self, evt):
        pos = self.GetScrollPos(evt.GetOrientation())
        self.SetScrollPos(evt.GetOrientation(), evt.GetPosition())

        if evt.GetEventType() == wxEVT_SCROLLWIN_TOP:
            self.SetScrollPos(evt.GetOrientation(), 0)
        if evt.GetEventType() == wxEVT_SCROLLWIN_BOTTOM:
            self.SetScrollPos(evt.GetOrientation(), evt.GetScrollRange(evt.GetOrientation()))
        if evt.GetEventType() == wxEVT_SCROLLWIN_LINEUP:
            self.SetScrollPos(evt.GetOrientation(), pos - 96)
        if evt.GetEventType() == wxEVT_SCROLLWIN_LINEDOWN:
            self.SetScrollPos(evt.GetOrientation(), pos + 96)
        if evt.GetEventType() == wxEVT_SCROLLWIN_PAGEUP:
            self.SetScrollPos(evt.GetOrientation(), pos - self.GetClientSize()[1])
        if evt.GetEventType() == wxEVT_SCROLLWIN_PAGEDOWN:
            self.SetScrollPos(evt.GetOrientation(), pos + self.GetClientSize()[1])
        
        self.Refresh(1)        

    def on_resize(self, evt):
        self.Refresh(1)

    def on_mouse(self, evt):
        pos = (evt.m_x, evt.m_y + self.GetScrollPos(wxVERTICAL))

        if evt.GetEventType() == wxEVT_LEFT_DOWN:
            for (region, uo) in self.__draggable:
                (x, y) = pos
                if x >= region[0] and x < region[0] + 96 and y >= region[1] and y < region[1] + 96:
                    data = wxCustomDataObject(wxCustomDataFormat("UnitOp"))
                    uotuple = uo.name + ' ' + uo.imageFile + ' ' + uo.className
                    data.SetData(uotuple)

                    bmp = wxBitmap(os.path.join(IMG_PATH, uo.imageFile), wxBITMAP_TYPE_BMP)
                    
                    dropSource = UnitOpDragWindowSource(self, bmp)
                    dropSource.SetData(data)
                    result = dropSource.DoDragDrop(1)


class UnitOpDragWindowSource (wxDropSource):
    def __init__(self, win, bmp):
        wxDropSource.__init__(self, win)

        self.bmp = bmp
        self.drag = wxDragImage(self.bmp, wxSTANDARD_CURSOR)
        self.drag.BeginDrag((16, 16), win, 1)
        self.base = win.ClientToScreen((0, 0))

    def __del__(self):
        self.drag.Hide()
        self.drag.EndDrag()

    def GiveFeedback(self, effect):
        if effect > 1:
            wxSetCursor(wxSTANDARD_CURSOR)
            pos = wxGetMousePosition()
            self.drag.Move((pos[0] - self.base[0], pos[1] - self.base[1]))
            self.drag.Show()
        else:
            wxSetCursor(wxStockCursor(wxCURSOR_NO_ENTRY))
            self.drag.Hide()


class FlowsheetFrame(BaseObjectFrame):
    def __init__(self, parent, log, interpParent=None, obj=None, split=1):
        """If obj = None, then it creates a test simulation"""
        BaseObjectFrame.__init__(self, parent, log, interpParent, obj)
##        self.SetSize(wxSize(850, 600))
        self.CreateStatusBar()

        if not self.inObj:
            obj = self.parentFlowsh

        splitter = wxSplitterWindow(self, -1, style=wxNO_3D|wxSP_3D)
    
        dragSource = UnitOpDragSource(splitter, self, -1, size=wxSize(200, 600))
        self.panels.append(dragSource)
        
        pfd = FlowsheetPanel(splitter, self, self.interpParent, obj)
        pfd.SetSize(wxSize(600, 600))
        self.panels.append(pfd)

        splitter.Initialize(pfd)
        splitter.SetMinimumPaneSize(180)
        if split:
            splitter.SplitVertically(dragSource, pfd, 400)
        splitter.p0 = dragSource
        splitter.p1 = pfd

        EVT_SPLITTER_SASH_POS_CHANGED(splitter, splitter.GetId(), self.OnSashChanged)
        EVT_SPLITTER_SASH_POS_CHANGING(splitter, splitter.GetId(), self.OnSashChanging)


        
        #"""Set icon"""
        fileName = os.path.join(IMG_PATH, 'sim42.ico')
        icon = wxIcon(fileName, wxBITMAP_TYPE_ICO)
        self.SetIcon(icon)

        #"""Set title"""
        name = obj.GetName()
        self.SetTitle('Flowsheet "' + name + '"')



    def OnSashChanged(self, evt):
        pass

    def OnSashChanging(self, evt):
        pass

    
class UnitOpSourceFrame(wxFrame):
    def __init__(self, parent, log):
        """If obj = None, then it creates a test simulation"""
        wxFrame.__init__(self, parent, -1, "Source of unit ops", style=wxDEFAULT_FRAME_STYLE, size=wxSize(250, 550))
        
        self.CreateStatusBar()
        self.panels = []

        

class UnitOpGuiInfo(object):
    def __init__(self, name, imageFile, className):
        self.name = name
        self.imageFile = imageFile
        self.className = className
        self.initScript = ''
        self.bmp = wxBitmap(os.path.join(IMG_PATH, self.imageFile), wxBITMAP_TYPE_BMP)


UOps = [UnitOpGuiInfo('StreamMaterial', 'stream_material.bmp', 'Stream.Stream_Material'),
        UnitOpGuiInfo('StreamEnergy', 'stream_energy.bmp' , 'Stream.Stream_Energy'),
        UnitOpGuiInfo('StreamSignal', 'stream_signal.bmp' , 'Stream.Stream_Signal'),
        
        UnitOpGuiInfo('Mixer', 'mixer.bmp', 'Mixer.Mixer'),
        UnitOpGuiInfo('Splitter', 'splitter.bmp', 'Split.Splitter'),
        
        UnitOpGuiInfo('Cooler', 'cooler.bmp', 'Heater.Cooler'),
        UnitOpGuiInfo('Heater', 'heater.bmp', 'Heater.Heater'),
        UnitOpGuiInfo('HeatExchanger', 'heatexchanger.bmp', 'Heater.HeatExchanger'),

        UnitOpGuiInfo('Separator', 'separator.bmp', 'Flash.SimpleFlash'),  
        UnitOpGuiInfo('ComponentSplitter', 'splitter.bmp', 'ComponentSplitter.ComponentSplitter'),

        UnitOpGuiInfo('Pump', 'pump.bmp', 'Pump.Pump'),
        UnitOpGuiInfo('Expander', 'compressor.bmp', 'Compressor.Expander'),
        UnitOpGuiInfo('Compressor', 'compressor.bmp', 'Compressor.Compressor'),
        UnitOpGuiInfo('Valve', 'valve.bmp', 'Valve.Valve'),
  
        UnitOpGuiInfo('Tower', 'generic.bmp', 'Tower.Tower'),
        UnitOpGuiInfo('Absorber', 'generic.bmp', 'Tower.Absorber'),
        UnitOpGuiInfo('RebAbsorber', 'generic.bmp', 'Tower.ReboiledAbsorber'),
        UnitOpGuiInfo('RefAbsorber', 'generic.bmp', 'Tower.RefluxedAbsorber'),
        UnitOpGuiInfo('DistCol', 'generic.bmp', 'Tower.DistillationColumn'),

        UnitOpGuiInfo('ConvReactor', 'convreactor.bmp', 'ConvRxn.ConvReactor'),

        UnitOpGuiInfo('Controller', 'controller.bmp', 'Controller.Controller'),
        UnitOpGuiInfo('Balance', 'balance.bmp', 'Balance.BalanceOp'),
        UnitOpGuiInfo('XConnector', 'crossconn.bmp', 'CrossConnector.CrossConnector'),
        UnitOpGuiInfo('Set', 'set.bmp', 'Set.Set'),


        UnitOpGuiInfo('Flowsheet', 'flowsheet.bmp', 'Flowsheet.Flowsheet'),
        UnitOpGuiInfo('SubFlowsheet', 'sflowsheet.bmp', 'Flowsheet.SubFlowsheet')]
        

if __name__ == '__main__':
    import sys
    app = wxPySimpleApp()
    frame = FlowsheetFrame(None, sys.stdout)    
    frame.Centre(wxBOTH)
    frame.Show(true)
    app.MainLoop()