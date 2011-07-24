"""Models a Cross flowsheet connector

Classes:
XFlowsheetConnector -- Common class for the cross flowsheet connector. Inherits from UnitOperation

"""

import UnitOperations
from sim.solver import Error
from sim.solver.Variables import *
from sim.solver import Ports

PORTTYPE_PAR = 'PortType'
INTENSIVE1_PAR = 'IntensiveVar1'
INTENSIVE2_PAR = 'IntensiveVar2'

NODE_PORT = 'NodePort'

class ConnectorNode(UnitOperations.UnitOperation):
    """
    A port bearing child operation of CrossConnector which takes its thermo from
    its ports connection
    """
    def __init__(self):
        """
        set up the port
        portType is bit map of MAT ENE SIG IN OUT
        """
        super(ConnectorNode, self).__init__()
        self.port = None
        
    def CleanUp(self):
        self.port = None
        super(ConnectorNode, self).CleanUp()
        
    def SetParameterValue(self, paramName, value):
        """
        Set parameter value - if paramName = PORTTYPE_PAR then recreate
        port with that type
        """
        super(ConnectorNode, self).SetParameterValue(paramName, value)

        if paramName == PORTTYPE_PAR:
            #Check if it is already there
            port = self.GetPort(NODE_PORT)
            if port != None:
                type = port.GetPortType()
                if type == value:
                    #nothing has changed, just quit
                    self.port = port
                    return
                else:
                    #Delete it
                    self.DeletePort(port)
                    self.port = None
            if self.port:
                oldConnection = self.port.GetConnection()
                if oldConnection:
                    self.port.Disconnect()
            else:
                oldConnection = None

            self.port = self.CreatePort(value, NODE_PORT)
            if oldConnection:
                self.port.ConnectTo(oldConnection)

    def MakingPortConnection(self, myPort, otherPort):
        """
        check the state of the operation port is connected to.
        ensure this op uses same thermo and solver as that op
        """

        if otherPort:
            #see what the connecting guy has
            newThermo = otherPort.GetParent().GetThermo()
            if newThermo:
                #Delete the current one if it is different
                if self.thCaseObj and self.thCaseObj != newThermo:
                    self.DeleteObject(self.thCaseObj)

                #Put the new thermo directly into this node
                if not self.thCaseObj:
                    self.SetThermo(newThermo)
                    
        else:
            # disconnecting, delete local thermo
            if self.thCaseObj:
                self.DeleteObject(self.thCaseObj)

        
class CrossConnector(UnitOperations.UnitOperation):
    """Base class for the cross flowsheet connector. Inherits from UnitOperation"""
    def __init__(self, initScript = None):
        """Init the CrossConnector
        portType is bit map of MAT ENE SIG IN OUT
        """          
        super(CrossConnector, self).__init__(initScript)
        
        self.inNode = ConnectorNode()
        self.AddUnitOperation(self.inNode, 'InletNode')
        
        self.outNode = ConnectorNode()
        self.AddUnitOperation(self.outNode, 'OutletNode')
        
        # by default assume material ports
        self.SetParameterValue(PORTTYPE_PAR, MAT)

        # use T and P as the default intensive variables
        self.SetParameterValue(INTENSIVE1_PAR, T_VAR)
        self.SetParameterValue(INTENSIVE2_PAR, P_VAR)
        
    def CleanUp(self):
        self.inNode = self.outNode = None
        super(CrossConnector, self).CleanUp()
        
    def GetListOfReqParam(self): return (PORTTYPE_PAR)

    def SetParameterValue(self, paramName, value):
        """
        Set parameter value
        - if paramName = PORTTYPE_PAR then set inOp and outOp as appropriate
        """
        super(CrossConnector, self).SetParameterValue(paramName, value)

        if paramName == NULIQPH_PAR:
            self.inNode.SetParameterValue(paramName, value)
            self.outNode.SetParameterValue(paramName, value)
        elif paramName == PORTTYPE_PAR:
            self.inNode.SetParameterValue(paramName, value | IN)
            self.outNode.SetParameterValue(paramName, value | OUT)
            self.BorrowChildPort(self.inNode.GetPort(NODE_PORT), IN_PORT)
            self.BorrowChildPort(self.outNode.GetPort(NODE_PORT), OUT_PORT)
            
            
    def Solve(self):
        """Solve"""

        inPort = self.inNode.GetPort(NODE_PORT)
        outPort = self.outNode.GetPort(NODE_PORT)
        
        #Make sure the thermo cases are correct
        if inPort._connection:
            if inPort.GetParent().thCaseObj != inPort._connection.GetParent().GetThermo():
                self.inNode.MakingPortConnection(inPort, inPort._connection)
        if outPort._connection:
            if outPort.GetParent().thCaseObj != outPort._connection.GetParent().GetThermo():
                self.outNode.MakingPortConnection(outPort, outPort._connection)
        
        if not isinstance(inPort, Ports.Port_Material):
            inPort.ShareWith(outPort, None, CALCULATED_V | PARENT_V)
            return 1
        
        if inPort.GetParent().GetThermo() == outPort.GetParent().GetThermo():
            while 1:
                # share between in and out again
                inPort.ShareWith(outPort, None, CALCULATED_V | PARENT_V)
    
                inPort.CalcFlows()
                outPort.CalcFlows()
                # only have to check one flash since everything was shared
                if not self.Flash(outPort):
                    break
        else:
            #inPort.SharePropWith(outPort, self.GetParameterValue(INTENSIVE1_PAR))
            #inPort.SharePropWith(outPort, self.GetParameterValue(INTENSIVE2_PAR))
            varType = self.GetParameterValue(INTENSIVE1_PAR)
            inPort.SetPropValue(varType, outPort.GetLocalValue(varType), CALCULATED_V| PARENT_V)
            outPort.SetPropValue(varType, inPort.GetLocalValue(varType), CALCULATED_V| PARENT_V)
            varType = self.GetParameterValue(INTENSIVE2_PAR)
            inPort.SetPropValue(varType, outPort.GetLocalValue(varType), CALCULATED_V| PARENT_V)
            outPort.SetPropValue(varType, inPort.GetLocalValue(varType), CALCULATED_V| PARENT_V)

            x = inPort.GetCompositionValues()
            cmpNames = inPort.GetCompoundNames()
            inDict = {}
            i = 0
            for name in cmpNames:
                inDict[name] = (i, x[i])
                i += 1

            x = outPort.GetCompositionValues()
            cmpNames = outPort.GetCompoundNames()
            outDict = {}
            i = 0
            for name in cmpNames:
                outDict[name] = (i, x[i])
                i += 1

            sumOut = sumIn = 0.0
            for cmp in inDict:
                if cmp in outDict:
                    # common component
                    x = inDict[cmp][1]
                    if x != None:
                        if sumIn != None: sumIn += x
                    else: sumIn = None
                    
                    x = outDict[cmp][1]
                    if x != None:
                        if sumOut != None: sumOut += x
                    else: sumOut = None
            
            if sumIn:
                x = [0.0] * len(outDict)
                for cmp in inDict:
                    if cmp in outDict:
                        x[outDict[cmp][0]] = inDict[cmp][1] / sumIn
                        
                outPort.SetCompositionValues(x, CALCULATED_V | PARENT_V)
                inFlow = inPort.GetPropValue(MOLEFLOW_VAR)
                if inFlow != None:
                    outPort.SetPropValue(MOLEFLOW_VAR, inFlow * sumIn, CALCULATED_V | PARENT_V)
                else:
                    outFlow = outPort.GetPropValue(MOLEFLOW_VAR)
                    if outFlow != None:
                        inPort.SetPropValue(MOLEFLOW_VAR, outFlow / sumIn, CALCULATED_V | PARENT_V)
            elif sumOut:
                x = [0.0] * len(inDict)
                for cmp in outDict:
                    if cmp in inDict:
                        x[inDict[cmp][0]] = outDict[cmp][1] / sumOut
                
                inPort.SetCompositionValues(x, CALCULATED_V | PARENT_V)
                if inFlow != None:
                    outPort.SetPropValue(MOLEFLOW_VAR, inFlow / sumOut, CALCULATED_V | PARENT_V)
                else:
                    outFlow = outPort.GetPropValue(MOLEFLOW_VAR)
                    if outFlow != None:
                        inPort.SetPropValue(MOLEFLOW_VAR, outFlow * sumOut, CALCULATED_V | PARENT_V)
                
            if not self.IsForgetting():
                self.CheckLosses(inPort, outPort)
            
            self.FlashAllPorts()
            
        return 1
    
    def CheckLosses(self, inPort, outPort):
        """Check if there are losses of compounds accross a connection"""
        inMoleFlow = inPort.GetPropValue(MOLEFLOW_VAR)
        outMoleFlow = outPort.GetPropValue(MOLEFLOW_VAR)
        if inMoleFlow and outMoleFlow:
            #PropTypes is a global dictionary
            tol = self.GetParameterValue(MAXERROR_PAR)
            if not tol:
                tol = 0.0001
            diff = inMoleFlow - outMoleFlow
            if abs(diff) > PropTypes[MOLEFLOW_VAR].scaleFactor*tol:
                self.InfoMessage('CrossConnMoleLoss', (diff, self.GetPath()))
                
                