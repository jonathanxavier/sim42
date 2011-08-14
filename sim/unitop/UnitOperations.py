"""Base class for all the unit operations

Classes:
UnitOperationDict -- Dict with instances of UnitOperation
UnitOperation -- Base class for all unit operations

"""

from sim.solver import Ports
from sim.solver.Variables import *
from sim.solver import Variables
from sim.solver import Error
from sim.solver.Messages import MessageHandler

from sim.thermo.ThermoAdmin import ThermoCase, ThermoAdmin

from sim.design import Design

import re, StringIO, time, os, sys, cPickle, copy
from Numeric import array, Int, Float

SIMINFO = 'Info'
TH_ADMIN_KEYWORD = '$'
TH_CASE_KEYWORD = 'ThCase'


PARAMS_DONOTTRIGGER_SOLVE = ['RecycleDetails']
PARAMS_IGNORE_IFEQUAL = [NULIQPH_PAR, NUSOLPH_PAR, STDVOLREFT_PAR]
    
class UnitOperationDict(dict):
    """Dictionary of unit operations. Inherits from UserDict

    keys -- Name of the unit operation
    values -- Instance of UnitOperation

    """
    def __init__(self):
        """Init an empty dictionary"""        
        dict.__init__(self)

    def __setitem__(self, key, item):
        """Only unit operations, no repetitions of values"""
        if not isinstance(item, UnitOperation): return
        if self.has_key(key): return
        if item in self.values(): return
        dict.__setitem__(self, key, item)


class UnitOperation(object):
    """Base class for all unit operations

    Its behaviour can be grouped in some groups of methods:
    1) Port creation and administration
    2) Port information administration
    3) Contained unit operations (child uops) administration
    4) Thermodynamics administration
    5) Uo parameters administration
    6) Connection administration
    7) Solver
    8) Save and load

    """
    
    def __init__(self, initScript = None):
        """
        Init port, parameters, thermo and connections with no info
        If initScript is not None, then a CommandInterface will be created
        and this script passed to it to run in the new ops context after the
        op has been added to its parent
        """
        self.ports_mat_IN = Ports.PortDict()
        self.ports_mat_OUT = Ports.PortDict()
        self.ports_ene_IN = Ports.PortDict()
        self.ports_ene_OUT = Ports.PortDict()
        self.ports_sig = Ports.PortDict()

        self.parameters = ParameterDict()
        self.parameters[IGNORED_PAR] = None   # if not None, this operation won't be solved
        self.parameterPropertyTypes = {}   # holds type if any - if not assume GENERIC_VAR

        self.thermoAdmin = None
        self.thCaseObj = None

        self.chUODict = UnitOperationDict()
        self.parentUO = None
        self.initScript = initScript  # this won't actually be run until after the parent adds the unitop
        self.name = ''
        self.infoCallBack = None
        self._unsentMsgStack = []    #Top most unit op stacks messages while an infoCallBack is not available

        self._stackStatus = 0  # keeps track of when on stack
        self._pushBlocked = 0  # set to prevent being put on solver stacks
        self.creationTime = time.time()
        self.info = SimInfoDict(SIMINFO, self)

        #these objects contain algorithms for sizing and design of the unit operations that they are contained in
        self.designObjects = {}
        self.associatedObjs = []
        
        #these are temporary variables that will be used when changing themo packages in order
        #to attempt the change in compositions more consistant
        self._tempCmpNames = None
        self._tempMapCmps = None
        

    def __str__(self):
        t = re.sub(' .*', '', repr(self))[1:]
        return '%s = %s' % (self.name, t)
    
    def SetInfoCallBack(self, infoCallBack):
        """Sets a new infoCallBack and passes any unsent msg to it"""
        self.infoCallBack = infoCallBack
        if self.infoCallBack:
            for msg, args, msgType in self._unsentMsgStack:
                self.InfoMessage(msg, args, msgType)
            self._unsentMsgStack = []
    
    def GetInfoCallBack(self):
        """Returns the info call back"""
        return self.infoCallBack
            
    def ObjectMessage(self):
        if hasattr(self, 'unitOpMessage'):
            return self.unitOpMessage
        else:
            return ('NoMessage',)
        
    def GetName(self):
        return self.name
    
    def GetPath(self):
        """return this unit ops name from parent, if available.
        Should produce a path for nested unit ops - return empty
        string if no parent"""
        
        if self.parentUO == None:
            return self.name
        
        try:
            parentName = self.parentUO.GetPath()
        except:
            parentName = None  # to avoid infinite recursion in error messages
            
        if parentName:
            if parentName == '/':
                return parentName + self.name
            else:
                return parentName + '.' + self.name
        else:
            return self.name
        

    def GetParent(self):
        return self.parentUO
    
    def GetObject(self, name):
        """returns contained object based on name"""
        obj = self.GetChildUO(name)
        if not obj:
            obj = self.GetPort(name)
        if not obj:
            if self.GetParameters().has_key(name):
                obj = OpParameter(self, name)
                
        #if not obj and name == TH_ADMIN_KEYWORD:
            #obj = self.thermoAdmin    
        if name == TH_CASE_KEYWORD:
            return self.thCaseObj 
            
        thObj = self.thCaseObj 
        if not obj and thObj:
            if thObj.name == name:
                obj = thObj
        
        if not obj and name == SIMINFO:
            if hasattr(self, 'info'):
                obj = self.info
                
        if obj == None:
            obj = self.GetDesignObject(name)
        return obj    

    def AddObject(self, obj, name):
        """
        generic add object routine
        calls AddUnitOperation if obj is a UnitOperation
        other types would have to be handled by derived classes
        """
        
        #Do not use the reserved keywords to name stuff
        if name == TH_ADMIN_KEYWORD:
            raise SimError('CantAddObject', (name, self.name))
        elif name == TH_CASE_KEYWORD and not isinstance(obj, ThermoCase):
            raise SimError('CantAddObject', (name, self.name))
        
        #Add it
        if isinstance(obj, UnitOperation):
            self.AddUnitOperation(obj, name)
        elif isinstance(obj, ThermoCase):
            if self.thCaseObj:
                self.DeleteObject(self.thCaseObj)
            self.SetThermo(obj)
        elif name == 'NewName':
            #remove me from parent's unit op dict
            del self.parentUO.chUODict[self.name]
            self.name = obj
            #add me back with a new key
            self.parentUO.chUODict[obj] = self
        elif isinstance(obj, str):
            # try adding it as a parameter
            # see if it can be a number
            try:
                obj = int(obj)
            except ValueError:
                try:
                    obj = float(obj)
                except ValueError:
                    pass  # leave it as string
            self.SetParameterValue(name, obj)
        elif isinstance(obj, Design.DesignMain):
            self.AddDesignObject(obj, name)
        else:
            raise Error.SimError('CantAddObject', (name, self.name))                 
                
    def DeleteObject(self, obj):
        """
        try to delete the object obj as appropriate
        """
        if isinstance(obj, Ports.Port):
            self.DeletePort(obj)
        elif isinstance(obj, UnitOperation):
            self.DelUnitOperation(obj.name)
        elif isinstance(obj, OpParameter):
            paramName = obj.name
            del self.parameters[paramName]
            if paramName == NULIQPH_PAR:
                self.NumberLiquidPhasesChanged(self.NumberLiqPhases())
            elif paramName == NUSOLPH_PAR:
                self.NumberSolidPhasesChanged(self.NumberSolidPhases())
        elif isinstance(obj, ThermoCase):
            if obj == self.thCaseObj:  # only delete if this is the case this unitop uses
                
                #Load the current list of compounds temporarily
                #self._tempCmpNames = None
                #self._tempMapCmps = None
                #self._tempCmpNames = self.thCaseObj.GetSelectedCompoundNames()
                self.SetThermo(None)
                #self._tempCmpNames = None
                #self._tempMapCmps = None
                
                #self.thCaseObj.UnLinkUnitOp(self)
                #self.thCaseObj = None

        elif isinstance(obj, Design.DesignMain):
            self.DeleteDesignObject(obj)
            
                
    def GetContents(self):
        """return list of (description, obj) tuples of contained objects"""
        result = []
        
        #Only pass thCaseObj if I own it
        if self.thCaseObj:
            #result.append((TH_CASE_KEYWORD, self.thCaseObj))
            result.append((self.thCaseObj.name, self.thCaseObj))
        
        for key in self.chUODict.keys():
            result.append((key, self.chUODict[key]))
            
        for i in self.GetPortItems():
            result.append(i)
            
        for key in self.parameters.keys():
            p = OpParameter(self, key)
            result.append((key, p))

        for i in self.designObjects.items():
            result.append(i) 
            
        return result
    
    def AddAssociatedObj(self, obj):
        if obj in self.associatedObjs:
            return
        if not hasattr(obj, 'DeleteObject'):
            return
        if not hasattr(obj, 'NotifySolved'):
            return
        self.associatedObjs.append(obj)
        
    def RemoveFromAssociatedObj(self, obj):
        if obj in self.associatedObjs:
            idx = self.associatedObjs.index(obj)
            del self.associatedObjs[idx]
        
    #Only the parent UOp needs to call this method
    def CleanUp(self):
        """Needs to be called by the parent uo to avoid memory leaks"""
        #print "cleaning up", self.name
        try:
            for obj in self.associatedObjs:
                obj.DeleteObject(self)
            self.associatedObjs = []
                
            for port in self.GetPorts():
                #Only cleanup (which also dicconnects) the ports that I own
                if port.GetParent() == self:
                    try:
                        port.CleanUp()
                    except:
                        self.InfoMessage('ErrInCleanUp', (port.GetPath(),), MessageHandler.errorMessage)
            for i in self.chUODict.keys():
                self.chUODict[i].CleanUp()
            self.chUODict.clear()
    
            self.ports_mat_IN.clear()
            self.ports_mat_OUT.clear()
            self.ports_ene_IN.clear()
            self.ports_ene_OUT.clear()
            self.ports_sig.clear()
    
            self.parameters.clear()
            self._unsentMsgStack = None
            
            #If I own the thermo, the unlink all the children as well
            if self.thCaseObj:
                thAdmin = self.thCaseObj.thermoAdmin
                for uo in self.thCaseObj.GetUnitOps():
                    thAdmin.UnlinkUO(uo)
                self.thCaseObj.UnLinkUnitOp(self)
            else:
               thCaseObj = self.GetThermo()
               if thCaseObj:
                   thAdmin = thCaseObj.thermoAdmin
                   thAdmin.UnlinkUO(self)
                
            self.thermoAdmin = None
            self.thCaseObj = None
    
            if hasattr(self, 'designObjects'):
                for obj in self.designObjects.values():
                    obj.CleanUp()
                del self.designObjects
                
            try:
                self.info.CleanUp()
            except:
                self.InfoMessage('ErrInCleanUp', (self.info.GetPath(),), MessageHandler.errorMessage)
    
            self.RemoveOpFromForgetStack(self)
            self.RemoveOpFromSolveStack(self)
            
        except:
            self.InfoMessage('ErrInCleanUp', (self.GetPath(),), MessageHandler.errorMessage)
        
    #Ports
    def CreatePort(self, portType, name):
        """
        Create a port of portType where portType is a bit flag field
        combination of IN, OUT, MAT, ENE, SIG. IN or OUT must be combined
        with MAT or ENE, but SIG would appear by itself
        """
        
        #Can not repeat names
        if self.GetPort(name):
            raise Error.SimError('CreatePortTypeError', (name, self.GetPath()))
        
        if portType & MAT:
            port = Ports.Port_Material(portType, self, name)
            if portType & IN:
                self.ports_mat_IN[name] = port
            elif portType & OUT:
                self.ports_mat_OUT[name] = port
            else:
                raise Error.SimError('NoPortDirection', (name, self.GetPath()))

            cmps = self.GetCompoundNames()
            thCaseObj = self.GetThermo()
            if thCaseObj:
                thermoAdmin = thCaseObj.thermoAdmin
                provider = thCaseObj.provider
                thCase = thCaseObj.case
                flashProps = thermoAdmin.GetPropNamesCapableOfFlash(provider, thCase)
                port.SetAsFlashProps(flashProps)
            if cmps:
                for j in cmps: port.AppendCompound(j)
            return port
        elif portType & ENE:
            port = Ports.Port_Energy(portType, self, name)
            if portType & IN:
                self.ports_ene_IN[name] = port
            elif portType & OUT:
                self.ports_ene_OUT[name] = port
            else:
                raise Error.SimError('NoPortDirection', (name, self.GetPath()))
            return port
        elif portType & SIG:
            port = self.ports_sig[name] = Ports.Port_Signal(SIG, self, name)
            return port
        else:
            raise Error.SimError('CreatePortTypeError', (name, self.GetPath()))

    def GetPort(self, name):
        """return the port named name - counts on unique names"""
        port = self.ports_mat_IN.get(name, None)
        if port: return port
        port = self.ports_mat_OUT.get(name, None)
        if port: return port
        port = self.ports_ene_IN.get(name, None)
        if port: return port
        port = self.ports_ene_OUT.get(name, None)
        if port: return port
        port = self.ports_sig.get(name, None)
        return port

    def DeletePortNamed(self, name):
        """delete the port named name - counts on unique names"""
        self.DeletePort(self.GetPort(name))
        
    def DeletePort(self, port):
        """delete port from operation"""

        ptype = port.GetPortType()
        portName = port.GetName()
        
        needFullForget = 1
        if port.GetParentOp() == self:
            if port.GetLocked():
                #raise Error.SimError('DeletePortError', (portName, self.GetPath()))
                return
            
            #First remove it from every unitop where it was borrowed
            for unitop in port.GetBorrowedIn():
                unitop.DeleteObject(port)
            
            port.CleanUp()
            
        else:
            #Remove the unitop from the list of of unit ops where the port is borrowed
            needFullForget = 0
            port.RemoveFromBorrowedIn(self)

            #It is borrowed, therefore the name is probably wrong. Find the correct name
            portName = None
            if ptype & MAT:
                if ptype & IN:
                    for k, v in self.ports_mat_IN.items():
                        if v == port:
                            portName = k
                            break
                elif ptype & OUT:
                    for k, v in self.ports_mat_OUT.items():
                        if v == port:
                            portName = k
                            break
                
            elif ptype & ENE:
                if ptype & IN:
                    for k, v in self.ports_ene_IN.items():
                        if v == port:
                            portName = k
                            break
                elif ptype & OUT:
                    for k, v in self.ports_ene_OUT.items():
                        if v == port:
                            portName = k
                            break

            elif ptype & SIG:
                for k, v in self.ports_sig.items():
                    if v == port:
                        portName = k
                        break

        if portName:
            if ptype & MAT:
                if ptype & IN:
                    del self.ports_mat_IN[portName]
                elif ptype & OUT:
                    del self.ports_mat_OUT[portName]
                else:
                    raise Error.SimError('DeletePortError', (portName, self.GetPath()))
            elif ptype & ENE:
                if ptype & IN:
                    del self.ports_ene_IN[portName]
                elif ptype & OUT:
                    del self.ports_ene_OUT[portName]
                else:
                    raise Error.SimError('DeletePortError', (portName, self.GetPath()))
            elif ptype & SIG:
                del self.ports_sig[portName]
            else:
                raise Error.SimError('DeletePortError', (portName, self.GetPath()))

        if needFullForget:            
            self.ForgetAllCalculations()


    def RenamePort(self, fromName, toName):
        """ rename port """
        if self.GetPort(toName):
            raise Error.SimError('RenamePortNameExists', (toName, fromName))
            
        port = self.GetPort(fromName)
        ptype = port.GetPortType()
        if ptype & MAT:
            if ptype & IN:
                del self.ports_mat_IN[fromName]
                self.ports_mat_IN[toName] = port
            elif ptype & OUT:
                del self.ports_mat_OUT[fromName]
                self.ports_mat_OUT[toName] = port
            else:
                raise Error.SimError('RenamePortError', (fromName, toName))
        elif ptype & ENE:
            if ptype & IN:
                del self.ports_ene_IN[fromName]
                self.ports_ene_IN[toName] = port
            elif ptype & OUT:
                del self.ports_ene_OUT[fromName]
                self.ports_ene_OUT[toName] = port
            else:
                raise Error.SimError('RenamePortError', (fromName, toName))
        elif ptype & SIG:
            del self.ports_sig[fromName]
            self.ports_sig[toName] = port
        else:
            raise Error.SimError('RenamePortError', (fromName, toName))

        #Only unit ops that own the port can change the actual name of the port
        #Ports that are borrowed here should not be changing the name of the port
        if self is port.GetParent():
            port.Rename(toName)
        
        connectedOpPath = ''
        if port.IsPortConnected():
            obj = port.IsPortConnected().GetParent()
            if obj and hasattr(obj, 'GetPath'):
                connectedOpPath = obj.GetPath()
        self.InfoMessage('RenamePort', (self.GetPath(), fromName, toName, connectedOpPath))
        #self.ForgetAllCalculations()        
  
    def GetPorts(self, portType = IN|OUT|MAT|ENE|SIG):
        """
        return list of ports whose type matches
        portType flags. Note MAT and ENE must also
        have IN and/or OUT flags
        """
        ports = []
        if portType & MAT:
            if portType & IN:
                ports.extend(self.ports_mat_IN.values())
            if portType & OUT:
                ports.extend(self.ports_mat_OUT.values())
        if portType & ENE:
            if portType & IN:
                ports.extend(self.ports_ene_IN.values())
            if portType & OUT:
                ports.extend(self.ports_ene_OUT.values())
        if portType & SIG:
            ports.extend(self.ports_sig.values())
        return ports

    def GetPortNames(self, portType = IN|OUT|MAT|ENE|SIG):
        """
        return list of port names for ports whose type matches
        portType flags. Note MAT and ENE must also
        have IN and/or OUT flags
        """
        names = []
        if portType & MAT:
            if portType & IN:
                names.extend(self.ports_mat_IN.keys())
            if portType & OUT:
                names.extend(self.ports_mat_OUT.keys())
        if portType & ENE:
            if portType & IN:
                names.extend(self.ports_ene_IN.keys())
            if portType & OUT:
                names.extend(self.ports_ene_OUT.keys())
        if portType & SIG:
            names.extend(self.ports_sig.keys())
        return names

    def GetPortItems(self, portType = IN|OUT|MAT|ENE|SIG):
        """
        return list of port (name, port) tuples for ports whose type matches
        portType flags. Note MAT and ENE must also
        have IN and/or OUT flags
        """
        items = []
        if portType & MAT:
            if portType & IN:
                items.extend(self.ports_mat_IN.items())
            if portType & OUT:
                items.extend(self.ports_mat_OUT.items())
        if portType & ENE:
            if portType & IN:
                items.extend(self.ports_ene_IN.items())
            if portType & OUT:
                items.extend(self.ports_ene_OUT.items())
        if portType & SIG:
            items.extend(self.ports_sig.items())
        return items
        
    def GetNumberPorts(self, portType = IN|OUT|MAT|ENE|SIG):
        """
        return number of ports whose type matches
        portType flags. Note MAT and ENE must also
        have IN and/or OUT flags
        """
        n = 0
        if portType & MAT:
            if portType & IN:
                n += len(self.ports_mat_IN)
            elif portType & OUT:
                n += len(self.ports_mat_OUT)
        elif portType & ENE:
            if portType & IN:
                n += len(self.ports_ene_IN)
            elif portType & OUT:
                n += len(self.ports_ene_OUT)
        elif portType & SIG:
            n += len(self.ports_sig)
        return n


    def ConnectPorts(self, uOpName1, portName1, uOpName2, portName2):
        """
        Makes a connection between two ports
        they must be the same kind of ports and if they are flow ports,
        one must be an inlet and the other must be an outlet

        uOpName1, portName1 -- Name of uo and port of first port
        uOpName2, portName2 -- Name of uo and port to connect to

        """
        uOp1 = self.GetChildUO(uOpName1)
        uOp2 = self.GetChildUO(uOpName2)
        if not uOp1 or not uOp2:
            raise Error.SimError('ConnectErrorNoUop',
                            (uOpName1, portName1, uOpName2, portName2))

        port1 = uOp1.GetPort(portName1)
        port2 = uOp2.GetPort(portName2)
        if not port1 or not port2:
            raise Error.SimError('ConnectErrorNoPort',
                            (uOpName1, portName1, uOpName2, portName2))
        
        port1.ConnectTo(port2)
        return 1
        
    def DisconnectPort(self, uOpName, portName):
        """Disconnect a port from whatever it is connected to

        uOpName  -- Name of uo with port out
        portName -- Name of port out

        """ 
        uOp = self.GetChildUO(uOpName)
        if not uOp: return
        port = uOp.GetPort(portName)
        if not port: return
        port.Disconnect()

    def GetAllChildConnections(self, portType = IN|OUT|MAT|ENE|SIG):
        """Tuple of tuples with connections info
       Order of info -- (uOpNameOut, portNameOut, uOpNameIn, portNameIn)
        """        
        conns = []
        for uOp in self.chUODict.values():
            for port in uOp.GetPorts(portType):
                connection = port.GetConnection()
                if connection:
                    conns.append((connection.GetParentOp().GetName(),
                                 connection.GetName(),
                                 port.GetParentOp().GetName(),
                                 port.GetName()))
        return conns

    def GetChildConnections(self, uOpName, portType = IN|OUT|MAT|ENE|SIG):
        """List of tuples with mat connections out of a uo

        uOpName -- Name of a the uo from which the info is required
        Order of info -- (uOpNameOut, portNameOut, uOpNameIn, portNameIn)

        """           
        conns = []
        uOp = self.GetChildUO(uOpName)
        if uOp:
            for port in uOp.GetPorts(portType):
                connection = port.GetConnection()
                if connection:
                    conns.append((port.GetParentOp().GetName(),
                                 port.GetName(),
                                 connection.GetParentOp().GetName(),
                                 connection.GetName()))
        return conns

    def UpdateConnection(self, portName):
        """Update information flow through the named port"""
        port = self.GetPort(portName)
        if not port:
            raise Error.SimError('UpdateInvalidPort', (portName, self.GetPath()))
        port.UpdateConnection()
        
    def UpdateConnections(self, portType = IN|OUT|MAT|ENE|SIG):
        """Update information flow in all of ports matching portType"""
        ports = self.GetPorts(portType)
        for port in ports:
            port.UpdateConnection()
            
    def UpdateChildConnections(self, childName, portType = IN|OUT|MAT|ENE|SIG):
        """
        Update information flow in all of ports matching portType for
        child unit op childName
        """
        uOp = self.GetChildUO(childName)
        if uOp: uOp.UpdateConnections(portType)
            

    def BorrowChildPort(self, port, name):
        """
        add a child port to my port list
        """

        #This breaks the ComponeneSplitter
        #Do not borrow with a repeated name
        #if self.GetPort(name):
            #raise Error.SimError('CreatePortTypeError', (name, self.GetPath()))        
        
        #get port type
        portType = port.GetPortType()
        if portType & MAT:
            if portType & IN:
                self.ports_mat_IN[name] = port
            elif portType & OUT:
                self.ports_mat_OUT[name] = port
            else:
                raise Error.SimError('NoPortDirection', (name, self.GetPath()))
            
            
        elif portType & ENE:
            if portType & IN:
                self.ports_ene_IN[name] = port
            elif portType & OUT:
                self.ports_ene_OUT[name] = port
            else:
                raise Error.SimError('NoPortDirection', (name, self.GetPath()))
        elif portType & SIG:
            self.ports_sig[name] = port
        else:
            raise Error.SimError('BorrowPortTypeError', (name, self.GetPath()))
        port.AddToBorrowedIn(self)
        
    
    def ShortestPortPath(self, port):
        """
        return the shortest path for a possibly borrowed port
        """
        if self.parentUO:
            path = self.parentUO.ShortestPortPath(port)
            if path: return path

        if port.GetParent() == self:
            return port.GetPath()
        
        # define helper function
        def GetPathOfPortFrom(self, port, portDict):
            """
            return path of port in portDict or None if not there
            """
            try:
                i = portDict.values().index(port)
                return self.GetPath() + '.' + portDict.keys()[i]
            except ValueError:
                return None
            
        portType = port.GetPortType()
        if portType & MAT:
            if portType & IN: return GetPathOfPortFrom(self, port, self.ports_mat_IN)
            if portType & OUT: return GetPathOfPortFrom(self, port, self.ports_mat_OUT)
                    
        if portType & ENE:
            if portType & IN: return GetPathOfPortFrom(self, port, self.ports_ene_IN)
            if portType & OUT: return GetPathOfPortFrom(self, port, self.ports_ene_OUT)

        if portType & SIG: return GetPathOfPortFrom(self, port, self.ports_sig)

    def MakingPortConnection(self, myPort, otherPort):
        """
        Notification from myPort that it is connecting to otherPort
        Ignored here, it can be overridden by derived classes that want the notice
        Called before actual connection is made
        """
        pass
    

    #Properties and compounds
    def GetPropNames(self, portName):
        """
        Get the names of available properties for the port named portName
        """
        return self.GetPort(portName).GetPropNames()
    
    def GetPropInfo(self, portName, propName=None):
        """Gets list of property info from port"""
        return self.GetPort(portName).GetPropInfo(propName)
        
    def GetPropValue(self, portName, propName):
        """return the value of propName for portName"""
        return self.GetPort(portName).GetPropValue(propName)
    
#    def SetPropValue(self, portName, propName, value, calcStatus=FIXED_V):
#        """set the value of propName for portName"""
#        self.GetPort(portName).SetPropValue(propName, value, calcStatus)
        
    def DelPropValue(self, portName, propName):
        """set propName of portName to unknown"""
        self.GetPort(portName).DelPropValue(propName)
        

    def AppendCompound(self, cmpIdx=-1):
        """
        called when a compound is added to the thermo for this operation
        Pass the index of the compound as seen by the thermo case. This is needed in the 
        case of a prop pkg adding automatically a bunch of compounds in one shot. For
        example, installing an oil created usually more than one compound in one calle, 
        and the compounds are appended to the acutal simulation case one by one.
        -1 refers to the very last compound of the cmp list in the thermo case
        """
        self.ForgetAllCalculations()
        
        for port in self.GetPorts(MAT|IN|OUT):
            if port.GetParent() == self:  # skip borrowed ports
                port.AppendCompound(cmpIdx)

    def MoveCompound(self, cmp1Idx, cmp2Idx):
        """
        move compound 1 before compound 2
        """
        self.ForgetAllCalculations()
        
        for port in self.GetPorts(MAT|IN|OUT):
            if port.GetParent() == self:  # skip borrowed ports
                port.MoveCompound(cmp1Idx, cmp2Idx)
        
    def DeleteCompound(self, cmp):
        """
        called when a compound is deleted to the thermo for this operation
        called before the actual delete
        """
        self.ForgetAllCalculations()
        
        for port in self.GetPorts(MAT|IN|OUT):
            if port.GetParent() == self:  # skip borrowed ports
                port.DeleteCompound(cmp)
        
    def AfterCompoundDeleted(self, cmp):
        """
        called when deleting a compound to the thermo for this operation
        called after the actual delete
        """
                
    def SetCompositionValues(self, portName, values, calcStatus=FIXED_V):
        """set the port mole fractions to values (alphabetically sorted by name)"""
        self.GetPort(portName).SetCompositionValues(values, calcStatus)

    def SetCompositionValue(self, portName, cmpName, value, calcStatus=FIXED_V):
        """sets a specific mole fraction for port"""
        self.GetPort(portName).SetCompositionValue(cmpName, value, calcStatus)
        
    def GetCompositionValues(self, portName):
        """get mole fractions from port in order of compounds"""
        return self.GetPort(portName).GetCompositionValues()

    def NumberLiqPhases(self):
        """ return the number of liquid phases used for this operation"""
        nPhases = self.GetParameterValue(NULIQPH_PAR)
        if nPhases != None: return nPhases
        return 1

    def NumberSolidPhases(self):
        """ return the number of solid phases used for this operation"""
        nPhases = self.GetParameterValue(NUSOLPH_PAR)
        if nPhases != None: return nPhases
        return 0    
    
    def ShareProperties(self, v, p1, p2):
        """set property v for port p1 equal to that property for p2 and 
        vice versa.
        v is a string name for the property
        v can be an list of properties and p1 and/or p2 can be lists of
        ports. 
        """
        
        if type(v) != type(""): # if v isn't string then should be sequence
            for i in v:
                self.ShareProperties(i, p1, p2) # ain't recursion wonderful
        elif not isinstance(p1, Ports.Port_Material):  # if not port then sequence
            for i in p1:
                self.ShareProperties(v, i, p2)
        elif not isinstance(p2, Ports.Port_Material):
            for i in p2:
                self.ShareProperties(v, p1, i)
        else:
            x = p1.GetPropValue(v)
            if x != None:
                p2.SetPropValue(v, x, CALCULATED_V)
            else:
                x = p2.GetPropValue(v)
                if x != None:
                    p1.SetPropValue(v, x, CALCULATED_V)
                    
    def ShareCompositions(self, p1, p2):
        """set composition for port p1 equal to that for p2 and vice versa.
        p1 and/or p2 can be lists of ports. 
        """
        
        if not isinstance(p1, Ports.Port_Material):  # if not port then sequence
            for i in p1:
                self.ShareCompositions(i, p2)
        elif not isinstance(p2, Ports.Port_Material):
            for i in p2:
                self.ShareCompositions(v, p1, i)
        else:
            c1 = p1.GetCompounds()
            c2 = p2.GetCompounds()
            for i in range(len(c1)):
                x = c1[i].GetValue()
                c2[i].SetValue(x, CALCULATED_V)
            for i in range(len(c2)):
                x = c2[i].GetValue()
                c1[i].SetValue(x, CALCULATED_V)
                                
    def Flash(self, port, calcStatus=CALCULATED_V):
        """ if the material port needs flashing, call the thermo to do so
        returns 1 if a flash was done, 0 if not"""
        assert(isinstance(port, Ports.Port_Material))
        
        return port.Flash(calcStatus)

    def FlashAllPorts(self, calcStatus=CALCULATED_V):
        """call Flash for all material ports
        returns count of ports actually flashed
        status is used such that a flag CALCULATED_V|PARENT_V can also be passed
        """
        
        nuFlashed = 0
        for port in self.GetPorts(MAT|IN|OUT):
            nuFlashed += port.Flash(calcStatus)
        return nuFlashed

    #Inner Unit Ops
    ##  The dictionary should check for additions and deletions 
    def AddUnitOperation(self, uOp, name):
        """Adds a child unit operation
        
        uOp -- Instance of UnitOperation
        name -- Name of the unit operation 

        """

        uOp.AddedToParent(self, name)
        self.chUODict[name] = uOp
        self.PushSolveOp(uOp)

        thCaseObj = self.GetThermo()
        if thCaseObj and not uOp.thCaseObj:
            uOp.ThermoChanged(thCaseObj)
            #The compounds maybe came with some temporary objects loaded. Clear them
            self._tempCmpNames = None
            self._tempMapCmps = None

        if Variables.SETCURRENTPATH:
            #Make the current working directory be:
            #1) The dir of the global variable SIMGLOBALPATH
            cwd = os.getcwd()
            try:
                if Variables.SIMGLOBALPATH and os.path.exists(Variables.SIMGLOBALPATH):
                    os.chdir(Variables.SIMGLOBALPATH)
            except:
                pass

        if uOp.initScript:
            from sim.cmd.CommandInterface import CommandInterface
            cmdproc = CommandInterface(uOp)
            inString = StringIO.StringIO(uOp.initScript)
            outString = StringIO.StringIO()
            cmdproc.ProcessCommandStream(inString, outString, outString)
            self.InfoMessage("RawOutput", outString.getvalue())
            cmdproc.CleanUp()

        if Variables.SETCURRENTPATH:
            #Put it back to what it was
            os.chdir(cwd)
        
    def AddedToParent(self, parentUO, name):
        """
        default version just sets self.parentUO and self.name,
        but class could override for initialization that can only occur
        when parent is known
        """
        
        self.parentUO = parentUO
        self.name = name
        self.creationNumber = len(parentUO.chUODict)
        
    def GetChildName(self, child):
        """ return the name of the child - iterative for now"""
        for name in self.chUODict.keys():
            if self.chUODict[name] is child: return name
            
    def GetChildUONames(self):
        """Names of the child uos"""
        return self.chUODict.keys()

    def GetChildUO(self, name):
        """ return child with name name"""
        return self.chUODict.get(name, None)
        
    def GetChildUnitOps(self):
        """Instance of all the children UO"""
        return self.chUODict.items()
        
    def DelUnitOperation(self, name):
        """Delete a uo by giving its name"""
##        This could be a major headache as it is possible for instance of
##        the uo to exist somewhere else, so the uo would disappear from the
##        parent uo, but not from that other instance
##      Needs to disconnect all the ports before deleting it
        if not self.chUODict.has_key(name): return
        self.chUODict[name].CleanUp()
        del self.chUODict[name]


    #Thermo
    def _GetPreviousCompoundNames(self):
        """The list of compound names will be kept temprarily when changing prop pkg such that
        composition specs cna be kept"""
        if hasattr(self, "_tempCmpNames"):
            if self._tempCmpNames != None:
                return self._tempCmpNames
        if self.parentUO != None:
            return self.parentUO._GetPreviousCompoundNames()
        return None
    
    def _GetCompoundsMap(self):
        """These method return an object that is used to map new compounds and old compounds when a prop pkg changes"""
        if hasattr(self, "_tempMapCmps"):
            if self._tempMapCmps != None:
                return self._tempMapCmps
        if self.parentUO != None:
            return self.parentUO._GetCompoundsMap()
        return None
        
    
    def SetThermo(self, thCaseObj):
        """Sets the thermo for the unit op"""

        ## Don't set if there is already a thermo case
        #if self.thCaseObj:
            #self.InfoMessage('CantOverwriteThermo', (self.GetPath(), str(self.thCaseObj)))
            #return

        self._tempCmpNames = None
        self._tempMapCmps = None
        if self.thCaseObj:
            if self.thCaseObj != thCaseObj:
                self.thCaseObj.UnLinkUnitOp(self)
            else:
                return
        oldThCaseObj = self.GetThermo()
        if oldThCaseObj != None:
            #Store this temporarily
            self._tempCmpNames = oldThCaseObj.GetSelectedCompoundNames()
            
        self.thCaseObj = thCaseObj
        if thCaseObj:
            thCaseObj.LinkUnitOp(self)

        self.ThermoChanged(thCaseObj)
        
        self._tempCmpNames = None
        self._tempMapCmps = None
        
        
    def SetThermoAdmin(self, thermoAdmin):
        if self.thermoAdmin and thermoAdmin != thermoAdmin:
            raise AssertionError
        self.thermoAdmin = thermoAdmin
        
    def GetThermoAdmin(self):
        if self.thermoAdmin:
            return self.thermoAdmin
        if self.parentUO:
            return self.parentUO.GetThermoAdmin()
        else:
            return None
        #thCaseObj = self.GetThermo()
        #if thCaseObj:
            #return thCaseObj.thermoAdmin
    
    def GetThermo(self):
        """returns local ThermoCase object or the one from parent"""
        if self.thCaseObj:
            return self.thCaseObj
        
        if self.parentUO:
            return self.parentUO.GetThermo()
        else:
            return None

    def GetCompoundNames(self):
        """Names (id's) of the selected compounds """
        thCaseObj = self.GetThermo()
        if not thCaseObj: 
            return []
        thermoAdmin = thCaseObj.thermoAdmin
        provider = thCaseObj.provider
        case = thCaseObj.case
        return thermoAdmin.GetSelectedCompoundNames(provider, case)
    
    def ThermoChanged(self, thCaseObj):
        """
        Notify children of change
        """
        
        #No matter what I'm being specifically sent. It should also check if I have a thermo
        #to inherit from parent
        thermoInUse = self.GetThermo()
        if thermoInUse:
            thermoAdmin = thermoInUse.thermoAdmin
            provider = thermoInUse.provider
            thCase = thermoInUse.case
            
            if thermoAdmin == None: 
                self.InfoMessage('ERRSettingThermo', (self.GetPath(), str(thCaseObj)), MessageHandler.errorMessage)
                return
            if not thermoAdmin.SupportsProvider(provider): 
                self.InfoMessage('ERRSettingThermo', (self.GetPath(), str(thCaseObj)), MessageHandler.errorMessage)
                return
            
            thermoAdmin.LinkUO(self)
    
            #By default, load the compounds to the ports in and out
            cmps = thermoAdmin.GetSelectedCompoundNames(provider, thCase)
            newCmpNames = cmps
            newCompoundCount = len(cmps)
            flashProps = thermoAdmin.GetPropNamesCapableOfFlash(provider, thCase)

        else:
            self.GetThermoAdmin().UnlinkUO(self)
            newCompoundCount = 0
            newCmpNames = []
            flashProps = []

        #Check if we can map compounds
        doMapping = False
        oldCmpNames = self._GetPreviousCompoundNames()
        if oldCmpNames != newCmpNames:
            if oldCmpNames != None and newCompoundCount > 0:
                mapCmps = self._GetCompoundsMap()
                if mapCmps == None:
                    mapCmps = self._tempMapCmps = MapCompounds(oldCmpNames, newCmpNames)
                doMapping = True
            
        for port in self.GetPorts(MAT|IN|OUT):
            #Only operate on ports directly owned (prevents rework and fix to cross conn)
            if not port.GetParent() is self: continue 
            
            port.ForgetAllCalculations()
            port.SetAsFlashProps(flashProps)
            compounds = port.GetCompounds()
            
            oldCompoundCount = len(compounds)
            oldValues = compounds.GetValues()
            if oldCompoundCount > newCompoundCount:
                port.DeleteCompounds(oldCompoundCount - newCompoundCount, newCompoundCount)
            elif newCompoundCount > oldCompoundCount:
                port.AppendCompounds(newCompoundCount - oldCompoundCount)
            
            if oldValues != None and doMapping and not None in oldValues:
                setValues = True
                status = zeros(newCompoundCount, Int)
                aStatus = status[0] = compounds[0]._calcStatus & ~NEW_V
                if aStatus & FIXED_V:
                    for i in range(1, newCompoundCount):
                        status[i] = compounds[i]._calcStatus & ~NEW_V
                        if aStatus != status[i]:
                            setValues = False
                else:
                    setValues = False
                    
                if setValues:
                    newValues = mapCmps.FromOldToNew(oldValues, 0.0)
                    if newValues != None and not None in newValues:
                        compounds.SetValues(newValues, aStatus)
                        compounds.Normalize()
                        
                        
            
            
            # current list structure does not let me know what compounds were removed
            # or added, so I can only adjust length of port compoundlists
            ##oldCompoundCount = len(i.GetCompounds())
            ##while oldCompoundCount > newCompoundCount:
                ##i.DeleteCompoundNumber(oldCompoundCount - 1)  # delete last compound
                ##oldCompoundCount -= 1
            ##while oldCompoundCount < newCompoundCount:
                ##i.AppendCompound()
                ##oldCompoundCount += 1
                
        for op in self.chUODict.values():
            try:
                if op.thCaseObj == None:
                    #The children that do not directly use a the case will be inheriting this th case
                    op.ThermoChanged(thCaseObj)
            except:
                caseName = str(None)
                if thCaseObj:
                    caseName = thCaseObj.case
                self.InfoMessage('ErrNotifyThChange', (op.GetPath(), caseName), MessageHandler.errorMessage)
                
    #Parameters
    def GetListOfReqParam(self):  #Overload
        """List of parameter that need a value to solve the UO"""
        return ()
    
    def GetParameters(self):
        return self.parameters
    
    def SetParameterValue(self, paramName, value):
        """Set the value of a parameter"""
        if not self.ValidateParameter(paramName, value):
            raise Error.SimError('CantSetParameter', (paramName,str(value)))
            return 0
        
        if paramName == Design.TRY_SOLVE_DESIGN_PAR and value:
            self.SolveDesign()
            self.parameters[paramName] = False
            return True
        
        if paramName in PARAMS_IGNORE_IFEQUAL:
            if self.parameters.has_key(paramName):
                if self.parameters[paramName] == value:
                    return
        
        self.parameters[paramName] = value
        if not paramName in PARAMS_DONOTTRIGGER_SOLVE:
            self.ForgetAllCalculations()
        
        if paramName == NULIQPH_PAR:
            self.NumberLiquidPhasesChanged(value)

        if paramName == NUSOLPH_PAR:
            self.NumberSolidPhasesChanged(value)
            
        if paramName == STDVOLREFT_PAR:
            self.SetParameterProperty(paramName, T_VAR)
            
        self.ParameterChanged(paramName, value)
            
        #Return one if succeeded
        return True

    def ParameterChanged(self, paramName, value):
        """Notify all the child that use this parameter about the change"""
        for uo in self.chUODict.values():
            if not uo.parameters.has_key(paramName):
                try:
                    uo.ParameterChanged(paramName, value)
                except:
                    self.InfoMessage('ErrNotifyParChange', (uo.GetPath(), paramName, value), MessageHandler.errorMessage)
    
    def ValidateParameter(self, paramName, value):
        """Validates the value of a parameter. Return 1 if vaidated properly"""
        if paramName == NULIQPH_PAR:
            #Not number or negative
            if not type(value) in (type(1), type(1.0)) or value < 1:
                return False
        for uo in self.chUODict.values():
            if not uo.parameters.has_key(paramName):
                if not uo.ValidateParameter(paramName, value):
                    return False
            
        return True
        

    def GetParameterValue(self, paramName):
        """Get the value of a parameter"""
        result = self.parameters.get(paramName, None)
        if result == None and self.parentUO:
            result = self.parentUO.GetParameterValue(paramName)
        return result
    
    def GetStdVolRefT(self):
        """Make sure it always return a value. Default is 273.15 + 15.0"""
        refT = self.GetParameterValue(STDVOLREFT_PAR)
        if refT == None:
            return 273.15 + 15.0
        return refT
        
    def NumberLiquidPhasesChanged(self, value):
        """
        Notify children of change
        """
        for op in self.chUODict.values():
            try:
                op.NumberLiquidPhasesChanged(value)
            except:
                self.InfoMessage('ErrNotifyLiqChange', (op.GetPath(), value), MessageHandler.errorMessage)

    def NumberSolidPhasesChanged(self, value):
        """
        Notify children of change
        """
        for op in self.chUODict.values():
            try:
                op.NumberSolidPhasesChanged(value)
            except:
                self.InfoMessage('ErrNotifySolChange', (op.GetPath(), value), MessageHandler.errorMessage)
            
    def SetParameterProperty(self, paramName, varType):
        """varType is variable type used to reference property type"""
        self.parameterPropertyTypes[paramName] = PropTypes.get(varType, PropTypes[GENERIC_VAR])

    def GetParameterProperty(self, paramName):
        """return property type or the generic property if non defined"""
        return self.parameterPropertyTypes.get(paramName, PropTypes[GENERIC_VAR])
        
    #Solve
    def Solve(self):
        """Solve the unit operation"""
        #Validate
        #GuessWhatever
        #BeginSolvingLoop
        pass

    def SolverForget(self):
        """
        Dummy routine - flowsheet implements this
        """
        pass
    
    def Solver(self):
        """return the flowsheet solver for this op"""
        if self.parentUO: return self.parentUO.Solver()
        
    def GetTolerance(self):
        if self.parameters.has_key(MAXERROR_PAR):
            return self.parameters[MAXERROR_PAR]
        elif self.parentUO: return self.parentUO.GetTolerance()
        else: return 0.0001

    def PushSolveOp(self, op):
        """add unit operation to stack to be solved"""
        if self.parentUO:
            self.parentUO.PushSolveOp(self)
            self.parentUO.PushSolveOp(op)

    def PopSolveOp(self):
        """pop unit operation from stack to be solved"""
        if self.parentUO: return self.parentUO.PopSolveOp()
        else: return None
    
    def RemoveOpFromSolveStack(self, op):
        """remove op from solve stack, regardless of its location"""
        if self.parentUO:
            self.parentUO.RemoveOpFromSolveStack(op)
            
    def PushForgetOp(self, op):
        """add unit operation to stack to be forgotten"""
        if self.parentUO:
            self.parentUO.PushForgetOp(self)
            self.parentUO.PushForgetOp(op)
        
    def PopForgetOp(self):
        """pop unit operation from stack to be forgotten"""
        if self.parentUO: return self.parentUO.PopForgetOp()
        else: return None
        
    def RemoveOpFromForgetStack(self, op):
        """remove op from forget stack, regardless of its location"""
        if self.parentUO:
            self.parentUO.RemoveOpFromForgetStack(op)
            
    def PushResetCalcPort(self, port):
        """add port to stack of calculated to have new cleared"""
        if self.parentUO: self.parentUO.PushResetCalcPort(port)

    def PopResetCalcPort(self):
        """pop port from stack calculated to have new cleared"""
        if self.parentUO: return self.parentUO.PopResetCalcPort()
        else: return None

    def PushResetFixedPort(self, port):
        """add port to stack of fixed to have new cleared"""
        if self.parentUO: self.parentUO.PushResetFixedPort(port)

    def PopResetFixedPort(self):
        """pop port from stack of fixed to have new cleared"""
        if self.parentUO: return self.parentUO.PopResetFixedPort()
        else: return None

    def PushIterationProperty(self, prop, value):
        """add BasicProperty prop to stack of estimated properties
        that have with new values available"""
        if self.parentUO: self.parentUO.PushIterationProperty(prop, value)

    def PopIterationProperty(self):
        """pop BasicProperty prop from stack of estimated properties
        that have with new values available
        returns tuple (prop, value) """
        if self.parentUO: return self.parentUO.PopIterationProperty()
        else: return None

    def PushConsistencyError(self, prop, value):
        """add BasicProperty prop to the inconsistency list
        value is the conflicting value calculated"""
        if self.parentUO: self.parentUO.PushConsistencyError(prop, value)

    def PopConsistencyError(self):
        """pop BasicProperty (prop, value) tuple from list of
        consistency errors - value is the conflicting value for prop"""
        if self.parentUO: return self.parentUO.PopConsistencyError()
        else: return None

    def IsOnStack(self, flag):
        return self._stackStatus & flag

    def AddStackStatus(self, flag):
        self._stackStatus |= flag

    def DelStackStatus(self, flag):
        self._stackStatus &= ~flag

    def BlockPush(self, block):
        """ if block is true then op will not get put on solver stacks"""
        self._pushBlocked = block
        
    def IsPushBlocked(self):
        """ returns true if op blocked from solver stacks"""
        return self._pushBlocked
    
    def IsForgetting(self):
        if self.parentUO: return self.parentUO.IsForgetting()
    def IsSolving(self):
        if self.parentUO: return self.parentUO.IsSolving()
    def Forget(self):
        """ called on a forget pass to get rid of any newly calculated values"""

        for port in self.GetPorts():
            if port.GetParentOp() == self:
                port.Forget()           # normal forget on my ports
            else:
                port.Forget(PARENT_V)   # only forget what I calculated on borrowed ports

    def ForgetAllCalculations(self):
        """ called to for the forgetting of all calculated values"""
        # if there are contained unit ops, have them forget
        
        for op in self.chUODict.values():
            op.ForgetAllCalculations()
            
        # now empty port properties
        for port in self.GetPorts():
            port.ForgetAllCalculations()
            
        if self.parentUO:
            self.parentUO.PushSolveOp(self)        
       
    def ValidateOk(self):
        """True if the uo is ready to be calculated"""
        return 1


    def InfoMessage(self, message=None, args=None, msgType=MessageHandler.infoMessage, addToUnitOpMsg=0):
        """
        If there is a callback function use it to pass info to interface
        if the return value is any but None, may raise a CallBackException
        If message is None, then this is just a check to see if it is okay to continue
        """
        reply = None
        if addToUnitOpMsg:
            self.unitOpMessage = (message, args)
        if self.infoCallBack:
            reply = self.infoCallBack.handleMessage(message, args, msgType)
        elif self.parentUO:
           reply = self.parentUO.InfoMessage(message, args, msgType, 0)
        else:
            self._unsentMsgStack.append((message, args, msgType))
        if reply:
            raise Error.CallBackException(reply)
        

    def walk(self, func, args=()):
        """Runs func in itself andall child uops"""
        lst = [self]
        lst.extend(list(args))
        apply(func, tuple(lst))
        for uop in self.chUODict.values():
            uop.walk(func, args)
        
    def AdjustOldCase(self, version):
        """apply any necessary fixups to a recalled operation"""
              
        #add locked attribute to ports
        if version[0] < 5:
            for p in self.GetPorts(IN|OUT|MAT|ENE|SIG):
                if not hasattr(p, '_locked'):
                    p._locked = 0

        if version[0] < 8:
            self.creationTime = time.time()
            self.info = SimInfoDict(SIMINFO, self)

        if version[0] < 15:
            self.info.name = SIMINFO
            self.info.parent = self
            
        #Potentially any unit op can have a wrong list in _borrowedIn
        if version[0] < 16:
            for p in self.GetPorts(IN|OUT|MAT|ENE|SIG):
                if not hasattr(p, '_borrowedIn'):
                    p._borrowedIn = []
                else:
                    if self != p.GetParent():
                        p.AddToBorrowedIn(self)

        if version[0] < 20:
            if not hasattr(self, 'designObjects'):
                self.designObjects = {}

            ##Keep only the thermo admin from the root unit op
            if hasattr(self, 'thermoAdmin'):
                if self.parentUO:
                    self.thermoAdmin = None
                                                           
            #If the local thermo is the same as the parent, then delete
            if self.thCaseObj:
                parent = self.parentUO
                if parent:
                    parentThermo = parent.GetThermo()
                    if parentThermo:
                        if (parentThermo.provider == self.thCaseObj.provider) and (parentThermo.case == self.thCaseObj.case):
                            self.thCaseObj = None
                        
            #If the thCaseObj in the provider and the one from the unit op point to the
            #same thing, then copy the one from the provider into the unit op but keep the name
            if self.thCaseObj:
                provCase = self.thCaseObj.thermoAdmin.GetObject(self.thCaseObj.case)
                if provCase:
                    name = self.thCaseObj.name
                    self.thCaseObj = provCase
                    self.thCaseObj.name = name
                if not hasattr(self.thCaseObj, 'linkedUnitOps'):
                    self.thCaseObj.linkedUnitOps = []
                if hasattr(self.thCaseObj, 'unitop'):
                    del self.thCaseObj.unitop
                self.thCaseObj.LinkUnitOp(self)
        
        if version[0] > 18 and version[0] < 23:
            if not hasattr(self, 'thermoAdmin'):
                self.thermoAdmin = None
                
                
        for uop in self.chUODict.values():
            uop.AdjustOldCase(version)
                        
        if version[0] < 45:
            thCaseObj = self.GetThermo()
            if thCaseObj != None:
                thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
                hypos = thAdmin.GetHypoteticalCompoundNames(prov, case)
                #The property package previous to this version had a bug in the H of hypoteticals
                #If the unit op has hypos, then resolve it
                if len(hypos):
                    self.ForgetAllCalculations()
                    
            
        if version[0] < 60:
            for p in self.GetPorts(SIG):
                if not hasattr(p, '_cmpName'):
                    p._cmpName = None
                    
                #Lets clean up any left over mess...
                if p._prop == None and (p._properties or p._varType or p._cmpName):
                   p.DeleteProperty()
                   
                if p._cmpName:
                    #Make sure _varType does not include the name of the compound
                    type = p.GetType()
                    if type:
                        typeName = type.name
                        if typeName == CMPMOLEFRAC_VAR or typeName == CMPMASSFRAC_VAR or typeName == STDVOLFRAC_VAR:
                            p._varType = typeName
                            
                if not p._cmpName:
                    #Make sure it is a none if not there
                    p._cmpName = None
                    
                if len(p._properties) > 1:
                    type = p.GeType()
                    if type:
                        typeName = type.name
                        for k, v in p._properties.items():
                            if k != typeName:
                                del p._properties[k]
                        if not p._properties:
                            cmpName = ""
                            if p._cmpName: cmpName = p._cmpName
                            p.CreateProperty(typeName + '_' + cmpName)
                    else:
                        p.DeleteProperty()
                        
        if version[0] < 61:
            for p in self.GetPorts(ENE|IN|OUT):
                if not hasattr(p, '_varType'):
                    p._varType = ENERGY_VAR
                if not hasattr(p, '_prop'):
                    p._prop = p._properties[ENERGY_VAR]
                    
        if version[0] < 62:
            for p in self.GetPorts(MAT|IN|OUT):
                if not hasattr(p, '_attachedObj'):
                    p._attachedObj = None
                    
        if not hasattr(self, 'associatedObjs'):
            self.associatedObjs = []
            
        if version[0] < 63:
            for p in self.GetPorts(MAT|ENE|SIG|IN|OUT):
                p.forceEstimates = 0
                    
        if version[0] < 76:
            for p in self.GetPorts(MAT|ENE|SIG|IN|OUT):
                if hasattr(p, 'forceEstimates'):
                    if p.forceEstimates == 0:
                        p.state = Ports.FIXALL_STATE
                    else:
                        p.state = Ports.ESTIMATEALL_STATE
                    del p.forceEstimates
                
                if p.IsEstimated():
                    for prop in p._properties.values():
                        if prop._calcStatus & FIXED_V:
                            prop._calcStatus |= ESTIMATED_V
                        if isinstance(self, Ports.Port_Material):
                            for prop in self._compounds:
                                prop._calcStatus |= ESTIMATED_V
                    p.state = Ports.ESTIMATEALL_STATE
                else:
                    p.state = Ports.FIXALL_STATE
                    
                
        #A redundant check to make sure that this flag is cleared. 
        #This need arised from a unit op that for some strange reason got recalled
        #with this flag as 1.
        self._pushBlocked = 0
        
        
    #Design object methods
    def GetDesignObject(self, name):
        """Returns the design object based on its name"""
        if hasattr(self, 'designObjects'):
            return self.designObjects.get(name, None)

    def AddDesignObject(self, obj, name):
        """Adds a design object with the specified name"""
        self.designObjects[name] = obj
        obj.SetParent(self)
        obj.SetName(name)

    def DeleteDesignObjectNamed(self, name):
        """Deletes a design object by a name specified"""
        obj = self.GetDesignObject(name)
        if obj:
            if hasattr(obj, 'CleanUp'):
                obj.CleanUp()
            del self.designObjects[name]

    def DeleteDesignObject(self, obj):
        """Deletes a design object by an instance specified"""
        self.DeleteDesignObjectNamed(obj.name)

    def SolveDesign(self):
        """Solve the design objects"""
        for obj in self.designObjects.values():
            self.InfoMessage('SolvingDesign', (obj.GetPath(),))
            try:
                obj.Solve()
            except:
                self.InfoMessage('ErrorSolvingDesign', (obj.GetPath(),))

    def GetDesignObjects(self):
        """Get the instances of all the design objects"""
        return self.designObjects.values()

    def GetDesignItems(self):
        """Get tuples of (name, obj) of the design object"""
        return self.designObjects.items()
        
    
    #Clone methods
    def Clone(self):
        """Clone the unit operation. This method is broken down in other sub methods for easier subclassing"""
        clone = self._CloneCreate()
        
        self.CloneContents(clone)
        
        #Keep a temporary reference list of what the compounds were being used
        if clone.thCaseObj == None:
            cmpNames = self.GetCompoundNames()
            if cmpNames:
                clone._tempCmpNames = cmpNames
        
        return clone
    
    def CloneContents(self, clone):
        """Clone the contents of self into clone"""
        attrNamesToClone = self.__dict__.keys()
        
        #try:
        attrNamesToClone = self._RemoveFromCloneList(clone, attrNamesToClone)
        attrNamesToClone = self._CloneParameters(clone, attrNamesToClone)
        attrNamesToClone = self._CloneThermo(clone, attrNamesToClone)
        attrNamesToClone = self._CloneChildrenOps(clone, attrNamesToClone)
        attrNamesToClone = self._ClonePorts(clone, attrNamesToClone)
        attrNamesToClone = self._CloneRemainingAttr(clone, attrNamesToClone)
    
        #except:
            #try:
                #clone.CleanUp()
            #except:
                #pass
            #clone = None
            
    def _CloneCreate(self):
        """By default just clone with the __class__ call"""
        clone = self.__class__()
        return clone
    
    
    def _RemoveFromCloneList(self, clone, attrNamesToClone):
        """Default attributes that should not be cloned"""
        dontClone = ["initScript", "parentUO", "name", "_unsentMsgStack", "_stackStatus",
                     "_pushBlocked", "creationTime", "designObjects", "associatedObjs",
                     "creationNumber", "unitOpMessage"]
        
        for name in dontClone:
            if name in attrNamesToClone:
                attrNamesToClone.remove(name)
        
        return attrNamesToClone
    
    def _CloneParameters(self, clone, attrNamesToClone):
        #Clone parameters
        for paramName in self.parameters:
            #Do a copy just in case
            clone.SetParameterValue(paramName, copy.deepcopy(self.parameters[paramName]))
            
        for paramName in self.parameterPropertyTypes:
            #Can safely point to the same thing as they are global types
            clone.parameterPropertyTypes[paramName] = self.parameterPropertyTypes[paramName]
            
        if "parameters" in attrNamesToClone: attrNamesToClone.remove("parameters")
        if "parameterPropertyTypes" in attrNamesToClone: attrNamesToClone.remove("parameterPropertyTypes") 
        
        return attrNamesToClone
            
    def _CloneThermo(self, clone, attrNamesToClone):
        #Clone Thermo. Point to the same objects and notify them
        clone.thermoAdmin = self.thermoAdmin
        thCaseObj = clone.thCaseObj = self.thCaseObj
        thermoAdmin = self.GetThermoAdmin()
        
        if thermoAdmin != None:
            thermoAdmin.LinkUO(clone)
        if thCaseObj != None:
            #Only link the unit ops that have a direct instance of it. Do not link the ones that
            #"inherit" the thermo case
            thCaseObj.LinkUnitOp(clone)
        
        if "thermoAdmin" in attrNamesToClone: attrNamesToClone.remove("thermoAdmin")
        if "thCaseObj" in attrNamesToClone: attrNamesToClone.remove("thCaseObj")
        
        return attrNamesToClone
            
    def _CloneChildrenOps(self, clone, attrNamesToClone):        
        #Clone Children Ops.
        for childName in self.chUODict:
            child =  self.chUODict[childName]
            if clone.chUODict.get(childName, None) != None:
                #Already there, skip
                child.CloneContents(clone.chUODict.get(childName, None))
            else:
                childClone = child.Clone()
                if childClone != None:
                    clone.AddUnitOperation(childClone, childName)
                else:
                    raise SimError('FailedCloning', child.GetPath())
            clone._tempCmpNames = None
            clone._tempMapCmps = None
        if "chUODict" in attrNamesToClone: attrNamesToClone.remove("chUODict")
        
        return attrNamesToClone
                    
    def _ClonePorts(self, clone, attrNamesToClone):
            #Clone ports
        portDictList = [(self.ports_mat_IN, clone.ports_mat_IN),
                        (self.ports_mat_OUT, clone.ports_mat_OUT),
                        (self.ports_ene_IN, clone.ports_ene_IN),
                        (self.ports_ene_OUT, clone.ports_ene_OUT),
                        (self.ports_sig, clone.ports_sig)]
        for myPorts, clonedPorts in portDictList:
            for portName in myPorts:
                port = myPorts[portName]
                
                clonePort = clonedPorts.get(portName, None)
                if clonePort != None:
                    #Make sure it is the right port
                    portParent = port.GetParent()
                    clonePortParent = clonePort.GetParent()
                    if self is portParent and clone is clonePortParent:
                        pass
                    else:
                        #Find the matchin parent
                        match = _FindMatchingChildOp(self, clone, portParent)
                        if not clonePortParent is match:
                            #Delete the port and clone it from scratch
                            clone.DeletePortNamed(portName)
                        
                if clonedPorts.get(portName, None) == None:
                    portParent = port.GetParent()
                    if port.GetParent() is self:
                        #A direct parent
                        
                        #Blindly clone the port. 
                        #This is very DANGEROUS as the 
                        # thermo case of the destiny parent may be different and the compound list
                        # will end up being different.
                        portClone = port.Clone()
                        if portClone != None:
                            clonedPorts[portName] = portClone
                            #Do not forget to assign the parent
                            portClone._parentOp = clone
                        else:
                            raise SimError('FailedCloning', port.GetPath())
                        
                    else:
                        #A borrowed port
                        
                        #Just look for it in the children and add it
                        #This should be a safe call since this cloning is a recursive fashion
                        #and all the children have already been cloned and borrowing only should happen 
                        #from children to parents
                        portClone = _FindMatchingClonedPort(self, clone, port)
                        if portClone != None:
                            clonedPorts[portName] = portClone
                            #Notify about the borrowing
                            portClone.AddToBorrowedIn(clone)
                        else:
                            raise SimError('FailedCloning', port.GetPath())
                else:
                    portClone = clonedPorts.get(portName, None)
                    if portClone.GetParent() is clone:
                        port.CloneContents(portClone)
                    
        if "ports_mat_IN" in attrNamesToClone:  attrNamesToClone.remove("ports_mat_IN")
        if "ports_mat_OUT" in attrNamesToClone: attrNamesToClone.remove("ports_mat_OUT")
        if "ports_ene_IN" in attrNamesToClone:  attrNamesToClone.remove("ports_ene_IN")
        if "ports_ene_OUT" in attrNamesToClone: attrNamesToClone.remove("ports_ene_OUT")
        if "ports_sig" in attrNamesToClone:     attrNamesToClone.remove("ports_sig")
                        
        return attrNamesToClone
    
    
    def _CloneRemainingAttr(self, clone, attrNamesToClone):
        #Restore the connections of all the children
        #... not for now
        import Balance
                        
        #Keep on cloning the rest of the attributes
        attrName = attrNamesToClone.pop()
        while attrName:
            
            attr = self.__dict__[attrName]
            
            if isinstance(attr, Ports.Port):
                #Do not clone ports. Instead, look for them and link them
                attrClone = _FindMatchingClonedPort(self, clone, attr, 1)
                currentClone = clone.__dict__.get(attrName, None)
                if attrClone == None and currentClone != None:
                    #If could not clone but there is already a value there, then keep the
                    #value that is already there
                    attrClone = currentClone
                    
            elif isinstance(attr, UnitOperation):
                #Do not clone unit ops. Instead, look for them and link them
                attrClone = _FindMatchingChildOp(self, clone, attr)
                currentClone = clone.__dict__.get(attrName, None)
                if attrClone == None and currentClone != None:
                    #If could not clone but there is already a value there, then keep the
                    #value that is already there
                    attrClone = currentClone
                    
            elif hasattr(attr, 'Clone'):
                attrClone = attr.Clone()

            elif isinstance(attr, list):
                #Check one level down to see if they are objects that can be cloned
                #Do not create an instance directly, rather call the __class__ method in case this is a subclass
                attrClone = attr.__class__()
                for obj in attr:
                    if hasattr(obj, 'Clone'):
                        innerClone = obj.Clone()
                        attrClone.append(innerClone)
                        if hasattr(innerClone, 'SetParent'):
                            innerClone.SetParent(clone)
                    else:
                        attrClone.append(_SafeClone(obj))
            elif isinstance(attr, tuple):
                #Check one level down to see if they are objects that can be cloned
                #Do list and then cast to tuple
                attrClone = []
                for obj in attr:
                    if hasattr(obj, 'Clone'):
                        innerClone = obj.Clone()
                        attrClone.append(innerClone)
                        if hasattr(innerClone, 'SetParent'):
                            innerClone.SetParent(clone)
                    else:
                        attrClone.append(_SafeClone(obj))
                attrClone = tuple(attrClone)
            elif isinstance(attr, dict):
                #Check one level down to see if they are objects that can be cloned
                #Do not create an instance directly, rather call the __class__ method in case this is a subclass
                attrClone = attr.__class__()
                for objName in attr:
                    if hasattr(attr[objName], 'Clone'):
                        innerClone = attr[objName].Clone()
                        attrClone[objName] = innerClone
                        if hasattr(innerClone, 'SetParent'):
                            innerClone.SetParent(clone)
                    else:
                        attrClone[objName] = _SafeClone(attr[objName])
            elif isinstance(attr, Balance.Balance):
                #Balances must be cloned manually by one of the clone methods
                attrClone = clone.__dict__.get(attrName, None)
            else:
                attrClone = _SafeClone(attr)
                currentClone = clone.__dict__.get(attrName, None)
                if attrClone == None and currentClone != None:
                    #If safe clone could not clone but there is already a value there, then keep the
                    #value that is already there
                    attrClone = currentClone
                        
            if hasattr(attrClone, 'SetParent'):
                attrClone.SetParent(clone)
            clone.__dict__[attrName] = attrClone
            
            if not len(attrNamesToClone):
                break
            else:
                attrName = attrNamesToClone.pop()
            
    
    
class MapCompounds(object):
    """Utility object to map compounds from one compound list to the other"""
    def __init__(self, oldCmps, newCmps):
        self.oldCmps = oldCmps
        self.newCmps = newCmps
        self.rulesOldToNew = {}
        self.rulesNewToOld = {}
        
        self.newNotInOld = []
        self.oldToNewMap = {}
        self.newToOldMap = {}
        
        self.UpdateMaps()
        
    def SetOldCompounds(self, oldCmps):
        self.oldCmps = oldCmps
        self.UpdateMaps()
        
    def SetNewCompounds(self, newCmps):
        self.newCmps = newCmps
        self.UpdateMaps()
        
    def FromOldToNew(self, oldVals, missingVal=None):
        """Translate values in "old" to values in "new". The values that do not have match will use 'missingVal' """
        newVals = []
        
        newToOldMap = self.newToOldMap
        newCmps = self.newCmps
        for newIdx in range(len(newCmps)):
            oldIdx = newToOldMap.get(newIdx, [])
            if oldIdx == None or oldIdx == []:
                newVals.append(missingVal)
            elif isinstance(oldIdx, list):
                val = None
                for idx in oldIdx:
                    if oldVals[idx] != None:
                        if val == None:
                            val = oldVals[idx]
                        else:
                            val += oldVals[idx]
                newVals.append(val)
                    
            else:
                newVals.append(oldVals[oldIdx])
                
        return newVals
        
    
    def UpdateMaps(self):
        """Update the mapping of compounds"""
        newCmps = self.newCmps
        oldCmps = self.oldCmps
        
        newNotInOld = self.newNotInOld = list(newCmps)
        oldToNewMap = self.oldToNewMap = {}
        newToOldMap = self.newToOldMap = {}
        
        for i in range(len(oldCmps)):
            if oldCmps[i] in newCmps:
                #A one to one relationship
                newIdx = newCmps.index(oldCmps[i])
                oldToNewMap[i] = newIdx
                newToOldMap[newIdx] = i
                newNotInOld.remove(oldCmps[i])
                
            else:
                #See if there is a rule for this compound
                newIdxs = []
                mapNewCmps = self.rulesOldToNew.get(oldCmps[i], [])
                for newCmp in mapNewCmps:
                    if newCmp in newCmps:
                        newIdxs.append(newCmps.index(newCmp))
                oldToNewMap[i] = newIdxs
        
        #Check for rules in newToOld mapping
        for newCmp in self.rulesNewToOld:
            if not newCmp in newCmps: break
            oldIdxs = []
            mapOldCmps = self.rulesNewToOld[newCmp]
            for oldCmp in mapOldCmps:
                if oldCmp in oldCmps:
                    oldIdxs.append(oldCmps.index(oldCmp))
            newToOldMap[newCmps.index(newCmp)] = oldIdxs
                
    def DelRuleForOld(self, oldCmpName):
        if self.rulesNewToOld.has_key(oldCmpName):
            del self.rulesNewToOld[oldCmpName]
            self.UpdateMaps()
        
    def SetRuleForOld(self, oldCmpName, equivalentTo):
        """Set a new equivalency rule"""
        self.rulesOldToNew[oldCmpName] = equivalentTo
        self.UpdateMaps()
        
    def DelRuleForNew(self, newCmpName):
        if self.rulesOldToNew.has_key(newCmpName):
            del self.rulesOldToNew[newCmpName]
            self.UpdateMaps()
        
    def SetRuleForNew(self, newCmpName, equivalentTo):
        """Set a new equivalency rule"""
        self.rulesNewToOld[newCmpName] = equivalentTo
        self.UpdateMaps()
        
                
class OpParameter:
    """wrapper for unit op parameters so they can be referenced as objects"""
    def __init__(self, unitOp, name):
        self.unitOp = unitOp
        self.name = name
    
    def __str__(self):
        return '%s = %s' % (self.name, str(self.GetValue()))

    def GetContents(self):
        return [('Value', self.GetValue()),
                ('Type', self.GetType())]    
                        
    def GetValue(self):
        return self.unitOp.GetParameterValue(self.name)
    
    def SetValue(self, value, dummy=None):
        """the dummy is just to make it match the BasicProperty call"""
        self.unitOp.SetParameterValue(self.name, value)
        
    def GetObject(self, desc):
        if desc == 'Value':
            return self.GetValue()
        elif desc == 'Type':
            return self.GetType()

    def GetType(self):
        return self.unitOp.GetParameterProperty(self.name)
    
    def GetPath(self):
        parentPath = self.unitOp.GetPath()
        if parentPath: return parentPath  + '.' + self.name
        else: return self.name
        
    def GetName(self):
        return self.name
    def GetParent(self):
        return self.unitOp

def _FindMatchingClonedPort(uOp, uOpClone, port, startAtTopLevel=0):
    """"Assuming port exists in uOp... find the matching port in uOpClone"""
    type = port.GetPortType()
    portParent = port.GetParent()
    portClone = None
    
    if startAtTopLevel:
        if uOp is portParent:
            if type == MAT|IN:
                return uOpClone.ports_mat_IN[port.GetName()]
            elif type == MAT|OUT:
                return uOpClone.ports_mat_OUT[port.GetName()]
            elif type == ENE|IN:
                return uOpClone.ports_ene_IN[port.GetName()]
            elif type == ENE|OUT:
                return uOpClone.ports_ene_OUT[port.GetName()]
            elif type == SIG:
                return uOpClone.ports_sig[port.GetName()]
    
    for childName in uOp.chUODict:
        child = uOp.chUODict[childName]
        childClone = uOpClone.chUODict[childName]
        if child is portParent:
            if type == MAT|IN:
                return childClone.ports_mat_IN[port.GetName()]
            elif type == MAT|OUT:
                return childClone.ports_mat_OUT[port.GetName()]
            elif type == ENE|IN:
                return childClone.ports_ene_IN[port.GetName()]
            elif type == ENE|OUT:
                return childClone.ports_ene_OUT[port.GetName()]
            elif type == SIG:
                return childClone.ports_sig[port.GetName()]
            
        else:
            if len(child.chUODict) > 0:
                #Call recursively if this child has children
                portClone = _FindMatchingClonedPort(child, childClone, port)
                if portClone != None:
                    #Found it !
                    return portClone
                
    return portClone
        
def _FindMatchingChildOp(uOp, uOpClone, childToFind, startAtTopLevel=0):
    """"Assuming childToFind exists in uOp... find the matching childOp in uOpClone"""
    for childName in uOp.chUODict:
        child = uOp.chUODict[childName]
        childClone = uOpClone.chUODict[childName]
        if child is childToFind:
            return childClone
        else:
            if len(child.chUODict) > 0:
                #Call recursively if this child has children
                childClone = _FindMatchingChildOp(child, childClone, childToFind)
                if childClone != None:
                    #Found it !
                    return childClone
                
    return None

def _SafeClone(item):
    """Only clone known Python objcts"""
    
    if isinstance(item, float):
        return float(item)
    elif isinstance(item, int):
        return int(item)
    elif isinstance(item, complex):
        return complex(item)
    elif isinstance(item, str):
        return str(item)
    elif isinstance(item, unicode):
        return unicode(item)
    elif isinstance(item, list):
        clone = []
        for content in item:
            clone.append(_SafeClone(content))
        return clone
    elif isinstance(item, tuple):
        clone = []
        for content in item:
            clone.append(_SafeClone(content))
        return clone
    elif isinstance(item, dict):
        clone = {}
        for key, content in item.items():
            clone[_SafeClone(key)] = _SafeClone(content)
        return clone
    elif type(array([1], Float)) == type(item) and hasattr(item, 'copy'):
        return item.copy()
        
        
    else:
        return None
        
        


def CalculateNonSupportedFlash(unitOp, frac, knownTargetProp, knownFlashProp, iterProp, lastSoln=None, min=None, max=None):
    """Complementary method that attempts to calculate flashes that are not supported by the prop pkg
    by iterating with supported flashes

    thCaseObject - Thermo object of the parent unit op
    frac - Compositions
    knownTargetProp - Tuple with (PropType, PropValue, ScaleFactor). This property will be used as convergence value
    knownFlashProp - Tuple with (PropType, PropValue, ScaleFactor). This property will be used with iterProp to calc flashes
    iterProp - Tuple with (PropType, PropEstimatedValue, ScaleFactor). This is the property that needs to be found
    lastSoln - Value of the last converged solution if available

    returns - Tuple with (LastPropValue, ConvergedBoolean)

    """

    #Main convergence parameters    
    tolerance = 0.00001 #unitOp.GetParameterValue(MAXERROR_PAR)
    maxIter   = 40
    maxStep = 1
    minStep = 0.0001

    #Load variables in a convenient way
    thCaseObj = unitOp.GetThermo()
    thAdmin, prov, case = thCaseObj.thermoAdmin, thCaseObj.provider, thCaseObj.case
    lstIterProp = list(iterProp)
    propList, target, scaleFactor = [knownTargetProp[0]], knownTargetProp[1], knownTargetProp[2]

    #See if last converged value is better than the estimate
    tempError = None
    try:
        if lastSoln !=None:
            tempLstIterProp = list(lstIterProp)
            tempLstIterProp[1] = lastSoln
            tempVals = thAdmin.GetProperties(prov, case, knownFlashProp, tempLstIterProp, OVERALL_PHASE, frac, propList)
            tempError = (tempVals[0] - target) / scaleFactor
    except:
        tempError = None

    couldInit = 0
    #Calculate the targetProp with the given initial estimate
    try:
        vals = thAdmin.GetProperties(prov, case, knownFlashProp, lstIterProp, OVERALL_PHASE, frac, propList)
        couldInit = 1
    except:
        couldInit = 0
        step = (max-min)/20.0
        lstIterProp[1] = min
        while lstIterProp[1] < max:
            lstIterProp[1] += step
            try:
                vals = thAdmin.GetProperties(prov, case, knownFlashProp, lstIterProp, OVERALL_PHASE, frac, propList)
                couldInit = 1
                break
            except:
                pass
            

    if not couldInit: 
        return None, 0
            
    #Check for errors
    error = (vals[0] - target) / scaleFactor
    if tempError != None:
        if abs(tempError) < abs(error):
            vals = tempVals
            error = tempError
            lstIterProp[1] = lastSoln
        
    if abs(error/tolerance) <= 1.0:
        return lstIterProp[1], 1

    # calculate rate of change. The jacobian Jr :)
    delta = 0.05
    sign = 1
    couldInit = 0
    newLstIterProp = list(lstIterProp)
    while abs(delta) > minStep:
        try:
            newLstIterProp[1] = lstIterProp[1]+lstIterProp[2]*sign*delta
            newVals = thAdmin.GetProperties(prov, case, knownFlashProp, newLstIterProp, OVERALL_PHASE, frac, propList)
            couldInit = 1
            break
        except:
            sign *= -1
            delta /= 2.0
        
    if not couldInit: 
        return None, 0
    
    
    newError = (newVals[0] - target) / scaleFactor
    dF_dx = (newError - error) / (sign*delta)
    dx_dF = 1.0 / dF_dx

    iter = 0
    while iter < maxIter:
        iter += 1
        adjustment = -error * dx_dF
        stepLength = 2.0

        #print 'iter', iter

        #Loop until the new iter value leads to a reduction in the error
        while 1:
            actualAdjustment = stepLength * adjustment
            newLstIterProp[1] = lstIterProp[1]+lstIterProp[2]*actualAdjustment
            try:
                newVals = thAdmin.GetProperties(prov, case, knownFlashProp, newLstIterProp, OVERALL_PHASE, frac, propList)
                newError = (newVals[0] - target) / scaleFactor
    
                if abs(newError) < abs(error):
                    break

            except:
                pass
            
            # errors did not go down - back down step size
            if stepLength < minStep:
                # step size too small - bail
                break

            stepLength /= 4.0
            
        if abs(newError/tolerance) <= 1.0:
            return newLstIterProp[1], 1

        if abs(newError) > abs(error):
            #Don't get fancy. Just leave 
            break
        else:
            # update rate of change
            dF = newError-error
            dx = actualAdjustment
            try:
                dx_dF = dx / dF
            except:
                break
            #dx2_dF = (dx * dx_dF)
            #dx2 = dx2_dF * dF
            #if abs(dx2) < 1.e-100:
            #    pass
            #else:
            #    dx_dF += ((dx - dF * dx_dF)  *  dx2_dF) / dx2
        error = newError
        lstIterProp = list(newLstIterProp)
                
    #Just return the last value used flagged as not converged.
    #Do not raise any errors or messages
    return newLstIterProp[1], 0


def test():
    
    #Test mapping object
    
    #Identical match
    o = ['A', 'E', 'I', 'O']
    n = ['A', 'E', 'I', 'O']
    m = MapCompounds(o, n)
    x = ['A', 'E', 'I', 'O']
    print m.FromOldToNew(x)
    
    #Smaller n in order
    n = ['A', 'E', 'I']
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    #Longer n in order
    n = ['A', 'E', 'I', 'O', 'U']
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    #Same size same cmps, not ordered
    n = ['E', 'O', 'I', 'A']
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    #Same size diff cmps, not ordered
    n = ['E', 'O', 'U', 'A']
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    #Smaller size same cmps, not ordered
    n = ['E', 'O', 'A']
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    #Smaller size diff cmps, not ordered
    n = ['E', 'U', 'A']
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    
    #Bigger size not ordered
    n = ['E', 'O', 'I', 'A', 'U']
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    #Bigger size diff cmps, not ordered
    n = ['E', 'U', 'A', 'I', 'V']
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    #Test rules
    #Redundant in A, E and I
    n = ['E', 'U', 'A', 'I', 'V']
    m.SetRuleForNew('V', ['A', 'I'])
    m.SetRuleForNew('U', ['E'])
    x = [1, 2, 3, 4]
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    #Remove redundancies
    n = ['U', 'V']
    x = [1, 2, 3, 4]
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    n = ['U', 'V', 'O']
    x = [1, 2, 3, 4]
    m.SetNewCompounds(n)
    print m.FromOldToNew(x)
    
    
    
    
if __name__ == '__main__':
    test()