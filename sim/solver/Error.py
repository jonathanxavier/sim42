"""Contains error classes"""
from sim.solver.Messages import MessageHandler

class SimError(Exception):
    def __init__(self, messageKey, extraData=None):
        self.messageKey = messageKey
        self.extraData = extraData
        self.args = str(self)
    def __str__(self):
        """just simple message for now"""
        return MessageHandler.RenderMessage(self.messageKey, self.extraData)
        
class ConsistencyError(Exception):
    def __init__(self, property):
        self.property = property
        self.args = str(self)
    def __str__(self):
        """just simple message for now"""
        s = 'ConsistencyError: '
        p = self.property
        if p._myPort:
            path = p._myPort._parentOp.ShortestPortPath(p._myPort)
            s += path + ' - '
        s += p._type.name + ' ' + str(p._consistencyError) + ' vs ' + str(p._value)
        return s

class CallBackException(Exception):
    def __init__(self, reply):
        self.reply = reply
        
    def __str__(self):
        if type(self.reply) == type(()):
            return MessageHandler.RenderMessage(self.reply[0], self.reply[1])
        else:
            return MessageHandler.RenderMessage(self.reply)