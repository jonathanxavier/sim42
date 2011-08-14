from HTTPMethodServer import HTTPMethodHandler
import BaseHTTPServer, SocketServer
import sys, os, cgi, cgitb, random, re, time
import traceback
import sha
import threading
import cPickle
import numpy.oldnumeric
import webbrowser, urllib
import ConfigParser
from numpy.oldnumeric import zeros, ones, reshape, Float, Int, array

pickle = cPickle

from sim.cmd import CommandInterface
from sim.solver.Error import CallBackException, SimError
from sim.solver.Messages import MessageHandler
from sim.unitop import UnitOperations, Tower, Stream, Envelope, Properties, Heater
from sim.unitop import HydrateThermoBased, PipeSegment, Balance, KineticReactor, BaseForReactors
from sim.solver.Variables import *
from sim.solver import Ports, Flowsheet
from sim.thermo import ThermoAdmin
from sim42user import Sim42User
import simbapfd

simbaConfig = ConfigParser.ConfigParser()
try:
    if not os.path.exists('simba.conf'):
        raise IOError
    simbaConfig.read(('simba.conf'))
except:
    # create default config file
    simbaConfig.add_section('Paths')
    simbaConfig.add_section('Sessions')
    simbaConfig.add_section('Language')
    simbaConfig.set('Paths', 'localPath', os.path.abspath('users/localUser'))
    simbaConfig.set('Paths', 'basePath', os.path.abspath('users'))
    
    # won't use try so error is obvious
    f = open('simba.conf', 'w')
    simbaConfig.write(f)
    f.close()


import sim.simba.weblanguages
MessageHandler.AddMessageModule(sim.simba.weblanguages)

# see if we have graphics
try:
    import graph42
except:
    graph42 = None

# some coding shortcuts
msg = MessageHandler.RenderMessage
randgen = random.Random()

ServerAdmin = 'admin'
ServerUser  = 'user'

# some global constants
UnknownBGColor  = '#FFEFEF'
PassedFontColor = 'DarkGreen'
FixedFontColor = "Blue"
EqualFontColor = 'Black'
VarNameBGColor  = '#EFEFFF'
CommandBGColor  = '#FCF8D0'
ProcessBGColor  = '#FCF8D0'
TreeBGColor     = '#FCF8D0'
DisplayBGColor  = '#FFFFEF'
DialogWinColor = '#FFFFEF'
HypoWinColor    = '#FFFFEF'
FileWinColor    = '#FFFFEF'
DirRowColor     = '#EFFFEF'

CAN_ADDUSER = 1
CAN_SHUTDOWN = 2
CAN_UPLOAD = 4
CAN_SEE_SESSIONS = 8
CAN_RESTART_SESSION = 16
LOCAL_ADMIN = CAN_SHUTDOWN + CAN_ADDUSER + CAN_UPLOAD + CAN_SEE_SESSIONS + CAN_RESTART_SESSION

COMPMOLEFRAC = 1
COMPMASSFRAC = 2
COMPMOLEFLOW = 4
COMPMASSFLOW = 8
COMPVOLFRAC = 16
COMPSTDLVOLFLOW = 32

lastSessionName = '_lastsession.s42'

SIMBAINFO = 'Simba'
PORTTABLES = 'PortTables'
PFDOP = 'op'

PTAll = 'A'
PTAllMatIn = 'AMI'
PTAllMatOut = 'AMO'
PTAllEneIn = 'AEI'
PTAllEneOut = 'AEO'
PTAllSig = 'AS'
PTAllStrIn = 'ASMI'

# determine which mixin to use: prefer threading, fall back to forking.
try:
    import thread
    mixin = SocketServer.ThreadingMixIn
except ImportError:
    if not hasattr(os, 'fork'):
        print "ERROR: your platform does not support threading OR forking."
        sys.exit(1)
    mixin = SocketServer.ForkingMixIn

# Use mixin for multi threading - single threading makes debugging easier
#class Sim42Server(BaseHTTPServer.HTTPServer):
class Sim42Server(mixin, BaseHTTPServer.HTTPServer):
    """
    Web Server dedicated to Sim42 Application
    """
    def __init__(self, localOnly=1, port=80, runPath=''):
        """
        set up session stuff
        """
        if runPath:
            self.runPath = os.path.abspath(runPath)
        else:
            progPath = os.path.abspath(sys.argv[0])    
            lastSep = progPath.rfind(os.sep)
            self.runPath = progPath[:lastSep]

        CommandInterface.netServer = self
        self.localOnly = localOnly
        self.LoadConfig()
        
        self.imagePath = self.runPath + os.sep + 'images'
        self.sessionLog = self.runPath + os.sep + 'session.log'
        if localOnly:
            self.handlerLog = sys.stderr
        else:
            try:
                self.handlerLog = open(self.runPath + os.sep + 'handler.log', 'a')
            except:
                self.handlerLog = None
        
        self.imageCache = {}
            
        self.sessions = {}
        self.sessionsByRootOp = {}
        server_address = ('', port)
        self.continueLoop = 1
        
        if not localOnly and isinstance(self, mixin):
            thread.start_new_thread(Sim42Server.PruneSessions, (self,))
        
        BaseHTTPServer.HTTPServer.__init__(self, server_address, Sim42Handler)
        
    def LoadConfig(self):
        try:
            if self.localOnly and simbaConfig.has_option('Paths', 'localPath'):
                self.basePath = simbaConfig.get('Paths', 'localPath')
            else:
                self.basePath = simbaConfig.get('Paths', 'basePath')
        except: self.basePath = ''
        self.basePath = os.path.abspath(self.basePath)
            
        if not os.path.exists(self.basePath):
            os.makedirs(self.basePath, 0770)
        os.chdir(self.basePath)        
            
        try: self.defaultLanguage = simbaConfig.get('Language', 'defaultLanguage')
        except: self.defaultLanguage = 'English'
        MessageHandler.SetCurrentLanguage(self.defaultLanguage)
        MessageHandler.IgnoreMessage('DoneSolving')
        
        try: self.maxInactiveSessionTime = simbaConfig.getint('Sessions', 'maxInactiveSessionTime')
        except: self.maxInactiveSessionTime = 3600

        try: self.sessionPruneSleepTime = simbaConfig.getint('Sessions', 'sessionPruneSleepTime')
        except: self.sessionPruneSleepTime = 60

    def verify_request(self, request, client_address):
        """
        only allow local addresses for localOnly mode
        """
        if self.localOnly:
            if client_address[0].find('127.0.0') != 0:
                return 0
        return BaseHTTPServer.HTTPServer.verify_request(self, request, client_address)
    
    def ShutDown(self):
        """
        close all sessions and stop serving
        """
        for sessionId in self.sessions.keys():
            self.RemoveSession(sessionId)
        self.continueLoop = 0
        
    def AddSession(self, user, handler):
        """
        create a new session
        """
        newId = randgen.randrange(100000, 1000000, 1)
        while newId in self.sessions:
            newId = randgen.randrange(100000, 1000000, 1)
        session = self.sessions[newId] = Sim42Session(user, newId)
        self.sessionsByRootOp[session.CommandInterface().root] = session
        session.SetHandler(handler)
        
        if session.user.privilege & CAN_RESTART_SESSION:
            pass
            #Nothing for now until vmg bug for new security is fixed
            
            ##if self.localOnly:
                ##name = lastSessionName
            ##else:
                ##name = session.user.name + '/' + lastSessionName
            
            ##if os.path.exists(name):
                ##try:
                    ##oldRoot = session.CommandInterface().root
                    ##session.CommandInterface().Recall(name)
                    ##self.switchedRoot(oldRoot, session.CommandInterface().root)

                ##except:
                    ##pass  # it was worth a try
                
        return session

    def RemoveSession(self, sessionID):
        """
        remove a session from the session list, effectively logging that user out
        """
        try:
            session = self.sessions[sessionID]
            
            if not self.localOnly:
                # log shutdown
                try:
                    f = open(self.sessionLog, 'a')
                    f.write("%s" % time.asctime(time.gmtime(time.time())))
                    f.write("\t%s off" % session.user.name)
                    f.write("\t%d\n" % session.id)
                    f.close()                            
                except:
                    pass
                
            nullCallback = DoNothingCallBack()
            session.s42cmd.SetInfoCallBack(nullCallback)
            if session.user.privilege & CAN_RESTART_SESSION:
                pass
                #Nothing for now until vmg bug for new security is fixed
            
                ##if self.localOnly:
                    ##name = lastSessionName
                ##else:
                    ##name = session.user.name + '/' + lastSessionName
                ##session.CommandInterface().Store(name)
            del self.sessions[sessionID]
            
            rootOp = session.CommandInterface().root
            while rootOp.GetParent(): rootOp = rootOp.GetParent()
            del self.sessionsByRootOp[rootOp]
            
            session.CommandInterface().CleanUp()

        except:
            pass
        
    def GetSession(self, sessionID):
        """
        return the session corresponding with sessionID
        """
        session = self.sessions.get(sessionID, None)
        session.lastAccessed = time.time()
        return session

    def PruneSessions(self):
        """
        checks to see if any sessions have been inactive for more than
        self.maxInactiveSessionTime - if so, they are removed.  The method then
        sleeps for self.sessionPruneSleepTime and repeats
        Should only be called from an independent thread
        """
        print 'prune thread started', self.sessionPruneSleepTime, self.maxInactiveSessionTime
        while 1:
            currentTime = time.time()
            sessionsToRemove = []
            #f = open('c:\\junk.txt','a')
            for session in self.sessions.values():
                #f.write('%d %d %d\n' % (session.id, currentTime - session.lastAccessed, self.maxInactiveSessionTime))
                if currentTime - session.lastAccessed > self.maxInactiveSessionTime:
                    sessionsToRemove.append(session)

            for session in sessionsToRemove:
                #f.write('removing %d\n' % session.id)
                self.RemoveSession(session.id)
            #f.close()

            time.sleep(self.sessionPruneSleepTime)            
        
    def PermittedBasePath(self, rootOp):
        """
        return the base path for session with rootOp
        """
        if self.basePath:
            basePath = self.basePath
        else:
            basePath = os.path.abspath('.')

        if (not self.localOnly):
            # find deepest root
            while rootOp.GetParent(): rootOp = rootOp.GetParent()
            try:
                session = self.sessionsByRootOp[rootOp]
                userName = session.GetUser().name
                permittedPathRoot = basePath + os.sep + userName
            except:
                raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
        else:
            permittedPathRoot = basePath
            
        return permittedPathRoot

    def open(self, rootOp, name, mode):
        """
        looks up session using rootOp as the key - adds user name to basePath
        and only allows opening of files that are at that level or deeper in
        the file hierarchy.
        """
    
        permittedPathRoot = self.PermittedBasePath(rootOp)
        if not self.localOnly:
            try:
                # use abspath to avoid .. type tricks
                absPath = os.path.abspath(name)
                if absPath.find(permittedPathRoot) != 0:
                    raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            except:
                raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            
        try:
            return open(name, mode)
        except:
            raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)

    def mkdir(self, rootOp, name):
        """
        creates a directory honoring user permissions
        """
    
        permittedPathRoot = self.PermittedBasePath(rootOp)
        if not self.localOnly:
            try:
                # use abspath to avoid .. type tricks
                absPath = os.path.abspath(name)
                if absPath.find(permittedPathRoot) != 0:
                    raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            except:
                raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            
        try:
            return os.mkdir(name)
        except:
            raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)

    def rmdir(self, rootOp, name):
        """
        removes a directory honoring user permissions
        """
    
        permittedPathRoot = self.PermittedBasePath(rootOp)
        if not self.localOnly:
            try:
                # use abspath to avoid .. type tricks
                absPath = os.path.abspath(name)
                if absPath.find(permittedPathRoot) != 0:
                    raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            except:
                raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            
        try:
            return os.rmdir(name)
        except:
            raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)

    def remove(self, rootOp, name):
        """
        removes a file honoring user permissions
        """
    
        permittedPathRoot = self.PermittedBasePath(rootOp)
        if not self.localOnly:
            try:
                # use abspath to avoid .. type tricks
                absPath = os.path.abspath(name)
                if absPath.find(permittedPathRoot) != 0:
                    raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            except:
                raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            
        try:
            return os.remove(name)
        except:
            raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)

    def listdir(self, rootOp, name):
        """
        return a list of directory entries in the directory composed
        of the permitted base path plus name.
        """
        basePath = self.PermittedBasePath(rootOp)
        if name:
            path = basePath + os.sep + name
        else:
            path = basePath
        absPath = os.path.abspath(path)
        
        if (not self.localOnly):
            try:
                # use abspath to avoid .. type tricks
                if absPath.find(basePath) != 0:
                    raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            except:
                raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)
            
        try:
            return os.listdir(path)
        except:
            raise CommandInterface.CmdError('CMDCouldNotOpenFile', name)

    def switchedRoot(self, oldRoot, newRoot):
        """
        called when the CI has switched its root flowsheet
        """
        try:
            # find deepest root
            while oldRoot.GetParent(): oldRoot = oldRoot.GetParent()
            while newRoot.GetParent(): newRoot = newRoot.GetParent()
            self.sessionsByRootOp[newRoot] = self.sessionsByRootOp[oldRoot]
            del self.sessionsByRootOp[oldRoot]
        except:
            pass  # probably not a session CI
    
    def GetUserInfo(self, username):
        """
        return user info
        """
        try:
            basePath = os.path.abspath(simbaConfig.get('Paths', 'basePath'))
            userInfoPath = basePath + os.sep + 'userinfo'
            if not os.path.exists(userInfoPath):
                return None
        except:
            return None
        
        userInfoFile = os.path.abspath(userInfoPath + os.sep + username)

        # check that the path is valid (no .. tricks)
        if not userInfoFile.startswith(userInfoPath):
            return None
        
        try:
            f = open(userInfoFile, 'r')
            user = pickle.load(f)
            f.close()
            if not hasattr(user, 'language'): user.language = 'English'
            if not hasattr(user, 'units'): user.units = 'SI'
            if not hasattr(user, 'composition'): user.composition = 0
            return user
        except Exception, e:
            tb = str(e) + '\n'
            for i in traceback.format_tb(sys.exc_traceback):
                tb += i + '\n'

            return None
        
    def SaveUserInfo(self, user):
        """
        return user info
        """
        basePath = os.path.abspath(simbaConfig.get('Paths', 'basePath'))
        userInfoPath = basePath + os.sep + 'userinfo'
        if not os.path.exists(userInfoPath):
            os.makedirs(userInfoPath, 0770)
        
        userInfoFile = os.path.abspath(userInfoPath + os.sep + user.name)

        # check that the path is valid (no .. tricks)
        if not userInfoFile.startswith(userInfoPath):
            return
        
        f = open(userInfoFile, 'w')
        pickle.dump(user, f)
        f.close()
        
    def login(self, username, password, handler):
        """
        if username and password are valid, create and return session
        """
        user = self.GetUserInfo(username)
        if user and user.CheckPassword(password):
            return self.AddSession(user, handler)

    def RemoveUser(self, username):
        """
        remove a user
        """
        try:
            basePath = os.path.abspath(simbaConfig.get('Paths','basePath'))
            userInfoPath = basePath + os.sep + 'userinfo'
            userInfoFile = os.path.abspath(userInfoPath + os.sep + username)
            os.remove(userInfoFile)
        except:
            return msg('WebNoConfig')

        # should also remove the user directory and it subdirectories
        # and contents - for now leave that as a manual task
        
    def AddUser(self, user):
        """
        create password file and directory for user
        """
        try:
            username = user.name
            try:
                basePath = os.path.abspath(simbaConfig.get('Paths', 'basePath'))
            except:
                return msg('WebNoConfig')
            
            userInfoPath = basePath + os.sep + 'userinfo'
            if not os.path.exists(userInfoPath):
                os.mkdir(userInfoPath)
                
            userInfoFile = os.path.abspath(userInfoPath + os.sep + username)

            # check that the path is valid (no .. tricks)
            if not userInfoFile.startswith(userInfoPath) or username == 'userinfo':
                return msg('WebInvalidUsername')

            # see that user doesn't already exist
            #if os.path.exists(userInfoFile):
            #    return msg('WebUserAlreadyExists')

            # create user and pickle user into file
            f = open(userInfoFile, 'w')
            pickle.dump(user, f)
            f.close()
            
            # attempt to create user directory - if it doesn't already exist
            userPath = os.path.abspath(basePath + os.sep + username)
            if not os.path.exists(userPath):
                os.mkdir(userPath)

            return msg('WebUserAdded', username)
            
        except:
            return msg('WebUserAddFailed')

    def serve_forever(self):
        """Handle one request at a time as long as continueLoop is true"""
        while self.continueLoop:
            self.handle_request()
        if self.handlerLog:
            self.log_message("Shutting down at " + "%s\n" % time.asctime(time.gmtime(time.time())))
            self.handlerLog.close()

    def log_message(self, msg):
        self.handlerLog.write(msg)
        self.handlerLog.flush()
        
            
class Sim42Session(object):
    """
    keeps session information
    """
    def __init__(self, user, id):
        self.user = user
        self.id = id
        self.s42cmd = CommandInterface.CommandInterface()
        self.infoCallBack = SimbaCallBack(self)
        self.s42cmd.SetInfoCallBack(self.infoCallBack)
        self.s42cmd.session = self
        self.commandLog = []
        self.handler = None
        self.lastAccessed = time.time()
        self.errorMessages = []
        self.suggestions = False
        
        #Buffer available compounds
        self.avCmps = None
        self.avCmpsHtml = None
        
    def GetUser(self):
        """
        return the user object
        """
        return self.user
        
    def SetHandler(self, handler):
        """
        set the current handler
        """
        self.handler = handler
        
    def ClearHandler(self):
        """
        clear the current handler
        """
        self.handler = None

    def Handler(self):
        return self.handler
        
    def CommandInterface(self):
        return self.s42cmd

    def LogCommand(self, cmd):
        """
        add cmd to command log
        """
        if cmd:
            self.commandLog.append(cmd)
    def GetCommandLog(self):
        return self.commandLog
    
    def msg(self, msgKey, args=None):
        """
        local RenderMessage using session language dictionary
        """
        return MessageHandler.RenderMessage(msgKey, args, self.infoCallBack.GetLanguageDict())
        
    def ShowCurrentObject(self):
        """
        render the current object in html
        """
        obj = self.s42cmd.currentObj
        path = self.GetObjectPath(obj)
         
        print '''
            <script>
            function DeleteObject(path)
            {
                var cmdInput = window.parent.command.document.getElementById("cmd");
                cmdInput.focus();
                cmdInput.value='cd ..; delete ' + path + '; cd .';
                window.parent.command.document.command.submit();
            }
            </script>
        '''
        if self.errorMessages:
            print '<font color="red"><b>%s</b>' % msg('WebErrors')
            print '<br>%s<br>' % self.errorMessages[0]
            for error in self.errorMessages[1:]:
                print '<hr>%s<br>' % error
            print '</p></font>'
            self.errorMessages = []
            
        if self.suggestions:
            sug = self.GetSuggestion()
            if sug:
                print '<p><font color="black"><b>%s</b>' % msg('WebSuggestions')
                print '<br>%s<br>' % sug
                print '</p></font>'
            
            
        if not isinstance(obj, SimInfoDict):
            print '<hr><b>%s</b>\n' % self.GetPathLinks(obj)
            objtype = re.sub(' .*', '', repr(obj))[1:]
            print ' - %s: <b>%s</b>' % (self.msg('WebModule'), objtype)
            if path != '/':
                print ''' (<a href="javascript:DeleteObject('%s');">%s</a>)''' % (
                    path, self.msg('WebDelete'))
                
        if isinstance(obj, Ports.Port_Material):
            self.ShowMaterialPort(obj)
        elif isinstance(obj, Ports.Port_Signal):
            self.ShowSignalPort(obj)
        elif isinstance(obj, Ports.Port_Energy):
            self.ShowEnergyPort(obj)
        elif isinstance(obj, SimInfoDict):
           if obj.parent.GetName() == PORTTABLES:
               self.ShowPortTable(obj)
           elif obj.GetName() == simbapfd.PFDINFO:
               self.ShowPFD(obj)
           else:
               self.ClearMenus()
               print '<hr><b>%s</b>\n' % self.GetPathLinks(obj)
               print '''&nbsp;&nbsp;&nbsp;(<a href="javascript:DeleteObject('%s');">%s</a>)<br>''' % (
                    path, self.msg('WebDelete'))
        elif isinstance(obj, Tower.Tower):
            self.ShowTower(obj)
        elif isinstance(obj, Tower.Stage):
            self.ShowTowerStage(obj)
        elif isinstance(obj, Tower.Draw):
            self.ShowTowerDraw(obj)
        elif isinstance(obj, Tower.Feed):
            self.ShowTowerFeed(obj)
        elif isinstance(obj, Tower.EnergyFeed):
            self.ShowTowerQFeed(obj)
        elif isinstance(obj, Tower.MoleRatioSpec) or isinstance(obj, Tower.MassRatioSpec):
            self.ShowTowerRatioSpec(obj)
        elif isinstance(obj, Tower.ComponentSpec):
            self.ShowTowerComponentSpec(obj)
        elif isinstance(obj, Tower.DegSubCooling):
            self.ShowTowerFluidVariable(obj)
        elif isinstance(obj, Tower.FluidVariable):
            self.ShowTowerFluidVariable(obj)
        elif isinstance(obj, Envelope.PTEnvelope):
            self.ShowPTEnvelope(obj)
        elif isinstance(obj, Stream.Stream_Material):
            self.ShowMaterialStream(obj)
        elif isinstance(obj, Stream.Stream_Energy):
            self.ShowEnergyStream(obj)
        elif isinstance(obj, Stream.Stream_Signal):
            self.ShowSignalStream(obj)
        elif isinstance(obj, Properties.VectorProps):
            self.ShowVectorProps(obj)
        elif isinstance(obj, Heater.HeaterCooler):
            self.ShowHeaterCooler(obj)
        elif isinstance(obj, Heater.MultiSidedHeatExchangerOp):
            self.ShowHeatExchanger(obj)    
        elif isinstance(obj, PipeSegment.PipeSegment):
            self.ShowPipeSegment(obj)
        elif isinstance(obj, KineticReactor.CSTR):
            self.ShowCSTR(obj)
        elif isinstance(obj, BaseForReactors.Reaction):
            self.ShowReaction(obj)
        elif isinstance(obj, UnitOperations.UnitOperation):
            self.ShowUnitOp(obj)
        elif isinstance(obj, CompoundList):
            self.ShowCompoundList(obj)
        elif isinstance(obj, BasicProperty):
            self.ShowBasicProperty(obj)
        elif isinstance(obj, UnitOperations.OpParameter):
            self.ShowUnitOpParam(obj)
        elif isinstance(obj, ThermoAdmin.ThermoCase):
            self.ShowThermoCase(obj)
        elif isinstance(obj, ThermoAdmin.ThermoAdmin):
            self.ShowThermoAdmin(obj)
        else:
            self.ClearMenus()

    def ClearMenus(self):
        print '''
        <script>
        parent.command.document.menuform.createmenu1.options.length = 0;
        parent.command.document.menuform.createmenu1.menuMethod = undefined;
        parent.command.document.menuform.createmenu2.options.length = 0;
        parent.command.document.menuform.createmenu2.menuMethod = undefined;
        parent.command.document.menuform.createmenu3.options.length = 0;
        parent.command.document.menuform.createmenu3.menuMethod = undefined;
        </script>
        '''

    def ShowTree(self):
        """
        Output object tree
        """
        # create a Simba SimInfoDict if it doesn't already exist
        info = self.s42cmd.root.info
        if info.has_key(SIMBAINFO):
            simbaInfo = info[SIMBAINFO]
        else:
            simbaInfo = info[SIMBAINFO] = SimInfoDict(SIMBAINFO, info)
            
        if not info.has_key(simbapfd.PFDINFO):
            pfdInfo = info[simbapfd.PFDINFO] = SimInfoDict(simbapfd.PFDINFO, info)
            pfdInfo[PFDOP] = '/'
                        
        print '<table width="100%" border="0" cellspacing="0" cellpadding="1" class="tree">'

        # show port tables, if any
        if simbaInfo.has_key(PORTTABLES):
            for table in simbaInfo[PORTTABLES].items():
                print '<tr><td>', self.MakeCdRef(table[0], table[1]), '</td></tr>'
        #print '<tr><td>',  '$', '</td></tr>'
        
        #ThermoAdmin tree
        print '<tr><td>', self.MakeCdRef('$' + ' (' + self.msg('WebThermodynamics') + ')', self.s42cmd.thermoAdmin), '</td></tr>'
        #if self.s42cmd.currentObj == self.s42cmd.thermoAdmin:
        self.ShowTreeItems(self.s42cmd.thermoAdmin, 1)
        
        #Flowsheet tree
        print '<tr><td>', self.MakeCdRef('/' + '   (' + self.msg('WebFlowsheet') + ')', self.s42cmd.root), '</td></tr>'
        self.ShowTreeItems(self.s42cmd.root, 1)
        print '</table>'

    def ShowTreeItems(self, base, indent):
        """
        display tree items in object base with indent level
        """
        if hasattr(base, 'GetContents'):
            contents = base.GetContents()
        else:
            contents = []
        contents.sort()
        currentPath = self.s42cmd.currentObj.GetPath()
            
        for obj in contents:
            name = obj[0]
            item = obj[1]
            if hasattr(item, 'GetPath'):
                print '%s<tr><td nowrap>&nbsp;' % ('' * indent),
                for i in range(indent-1):
                    print '.',
                print self.MakeCdRef(name, item)
                print'</td></tr>'
                path = item.GetPath()
                if currentPath.find(path) == 0:
                    self.ShowTreeItems(item, indent + 1)
            
        
    def GetObjectPath(self, obj):
        """
        get object path or default string
        """
        if hasattr(obj, 'GetPath'):
            return obj.GetPath()
        else:
            return self.msg('WebNoGetPath')
        
    def GetObjectName(self, obj):
        """
        get object name or default string
        """
        if hasattr(obj, 'GetName'):
            return obj.GetName()
        else:
            return self.msg('NoGetName')
        
    def MakeCdRef(self, name, obj, color=None):
        """
        create anchor tag with cmd to cd to obj
        """
        path = self.GetObjectPath(obj)
        s = '<a href="docmd?cmd=%s&sid=%d" target="output">' %(
                        cgi.escape('cd ' + path,1),
                        self.id)
        escName = cgi.escape(name,1)
        if color:
            s += '<font color="%s">%s</font>' % (color, escName)
        else:
            s += '%s</a>' % escName
        return s
                        

    def ListMatPorts(self, op):
        """
        Print the ports and their contents
        """
        MoleFrac = None
        MassFrac = None
        VolFrac = None
        MoleFlow = None
        MassFlow = None  
        StdLVolFlow = None
        try:
            tableWidth = self.user.tablewidth
        except:
            tableWidth = 4
        
        allMatPorts = []
        allMatPortNames = op.GetPortNames(MAT|IN) + op.GetPortNames(MAT|OUT)
        allMatPortNames.sort()
        for portName in allMatPortNames:
            allMatPorts.append(op.GetPort(portName))
        nPorts = len(allMatPorts)
        startPort = 0
        rows = 0
        rowsperpage = 0
        while nPorts > startPort:
            nextStart = startPort + tableWidth
            matPorts = allMatPorts[startPort:nextStart]
            matPortNames = allMatPortNames[startPort:nextStart]
            startPort = nextStart
            try: 
                rowsperpage = self.user.rowsperpage
            except:
                rowsperpage = 0
                self.user.rowsperpage = 0
            rows += 1
            
            if (rowsperpage > 0 and rows % rowsperpage == 0):
                print '<div style="page-break-after:always">'
            else:
                print '<div>'
            print '<table><tr><td>&nbsp;</td>'
            props = self.s42cmd.defaultPropertyOrder
                    
            cnt = 0
            for portIdx in matPorts:
                print '<td colspan=4>%s</td>' % self.MakeCdRef(matPortNames[cnt], matPorts[cnt])
                cnt += 1
    
            print '</tr><td bgcolor="%s">%s</td>' % (VarNameBGColor, self.msg('WebConnectedTo'))
            thermoCases = []
            for port in matPorts:
                conn = port.GetConnection()
                print '<td colspan=4>' + self.ConnectToLink(port)
                if conn: print '%s</td>' % self.GetPathLinks(conn)
                else: print '________</td>'
                tCase = port.GetParent().GetThermo()
                if tCase not in thermoCases:
                    thermoCases.append(tCase)  # see if there are multiple cmpLists
       
            for propName in props:
                print '</tr><tr><td bgcolor="%s">%s</td>' % (VarNameBGColor, self.msg(propName))
                for port in matPorts:
                    try:
                        prop = port.GetProperty(propName)
                        relPath = '%s.%s' % (port.GetPath(), propName)
                        print self.RenderBasicObject(relPath, prop)
                    except:
                        print '<td>%s</td><td>&nbsp;</td><td>&nbsp;</td>' % self.msg('WebInvalid')
                    print '<td>&nbsp;</td>'
            print '</tr>'
            if self.user.composition and len(thermoCases) == 1:            
                cmpNames = port.GetCompoundNames()  
                if self.user.composition & COMPMOLEFRAC:                                    
                    print '<tr><td bgcolor=%s align=center><b><u>%s</u></b></td></tr>' % (UnknownBGColor, 
                                                                                            self.msg('WebMoleFraction'))
                    
                    for cmpIdx in range(len(cmpNames)):   
                        print '<tr><td>%s</td>' % cmpNames[cmpIdx]
                        if not cmpIdx:
                            cmpHtmlPerPort = []
                        cntPort = 0
                        for port in matPorts:
                            try:
                                relPath = port.GetPath()
                            except:
                                relPath = ''
                            if not cmpIdx:
                                cmpList = port.GetCompounds()  
                                cmpHtmlPerPort.append(self.FormatComposition(cmpList, COMPMOLEFRAC))
                            cmpHtml = cmpHtmlPerPort[cntPort]
                            cntPort += 1
                            print '%s<td>&nbsp;</td><td>&nbsp;</td>' % cmpHtml[cmpIdx]                                                   
                        
                if self.user.composition & COMPMASSFRAC:                                    
                    print '<tr><td bgcolor=%s align=center><b><u>%s</u></b></td></tr>' % (UnknownBGColor, 
                                                                                            self.msg('WebMassFraction'))
                    for cmpIdx in range(len(cmpNames)):  
                        print '<tr><td>%s</td>' % cmpNames[cmpIdx]
                        if not cmpIdx:
                            cmpHtmlPerPort = []
                        cntPort = 0
                        for port in matPorts:
                            try:
                                relPath = port.GetPath()
                            except:
                                relPath = ''
                            if not cmpIdx:
                                cmpList = port.GetCompounds()  
                                cmpHtmlPerPort.append(self.FormatComposition(cmpList, COMPMASSFRAC))
                            cmpHtml = cmpHtmlPerPort[cntPort]
                            cntPort += 1
                            print '%s<td>&nbsp;</td><td>&nbsp;</td>' % cmpHtml[cmpIdx]        
                        
                if self.user.composition & COMPVOLFRAC:                                    
                    print '<tr><td bgcolor=%s align=center><b><u>%s</u></b></td></tr>' % (UnknownBGColor, 
                                                                                            self.msg('WebVolFraction'))
                    for cmpIdx in range(len(cmpNames)):  
                        print '<tr><td>%s</td>' % cmpNames[cmpIdx]
                        if not cmpIdx:
                            cmpHtmlPerPort = []
                        cntPort = 0
                        for port in matPorts:
                            try:
                                relPath = port.GetPath()
                            except:
                                relPath = ''
                            if not cmpIdx:
                                cmpList = port.GetCompounds()  
                                cmpHtmlPerPort.append(self.FormatComposition(cmpList, COMPVOLFRAC))
                            cmpHtml = cmpHtmlPerPort[cntPort]
                            cntPort += 1
                            print '%s<td>&nbsp;</td><td>&nbsp;</td>' % cmpHtml[cmpIdx]
                            
                if self.user.composition & COMPMOLEFLOW:  
                    print '<tr><td bgcolor=%s align=center><b><u>%s</u></b></td></tr>' % (UnknownBGColor, 
                                                                                            self.msg('WebCmpMoleFlows'))
                    for cmpIdx in range(len(cmpNames)):  
                        print '<tr><td>%s</td>' % cmpNames[cmpIdx]
                        if not cmpIdx:
                            cmpHtmlPerPort = []
                        cntPort = 0
                        for port in matPorts:
                            try:
                                relPath = port.GetPath()
                            except:
                                relPath = ''
                            if not cmpIdx:
                                cmpList = port.GetCompounds()  
                                cmpHtmlPerPort.append(self.FormatComposition(cmpList, COMPMOLEFLOW))
                            cmpHtml = cmpHtmlPerPort[cntPort]
                            cntPort += 1
                            print '%s<td>&nbsp;</td><td>&nbsp;</td>' % cmpHtml[cmpIdx]       
                    
                if self.user.composition & COMPMASSFLOW:      
                    print '<tr><td bgcolor=%s align=center><b><u>%s</u></b></td></tr>' % (UnknownBGColor, 
                                                                                            self.msg('WebCmpMassFlows'))
                    for cmpIdx in range(len(cmpNames)):  
                        print '<tr><td>%s</td>' % cmpNames[cmpIdx]
                        if not cmpIdx:
                            cmpHtmlPerPort = []
                        cntPort = 0
                        for port in matPorts:
                            try:
                                relPath = port.GetPath()
                            except:
                                relPath = ''
                            if not cmpIdx:
                                cmpList = port.GetCompounds()  
                                cmpHtmlPerPort.append(self.FormatComposition(cmpList, COMPMASSFLOW))
                            cmpHtml = cmpHtmlPerPort[cntPort]
                            cntPort += 1
                            print '%s<td>&nbsp;</td><td>&nbsp;</td>' % cmpHtml[cmpIdx]  
                            
                if self.user.composition & COMPSTDLVOLFLOW:      
                    print '<tr><td bgcolor=%s align=center><b><u>%s</u></b></td></tr>' % (UnknownBGColor, 
                                                                                            self.msg('WebCmpStdLiqVolFlows'))
                    for cmpIdx in range(len(cmpNames)):  
                        print '<tr><td>%s</td>' % cmpNames[cmpIdx]
                        if not cmpIdx:
                            cmpHtmlPerPort = []
                        cntPort = 0
                        for port in matPorts:
                            try:
                                relPath = port.GetPath()
                            except:
                                relPath = ''
                            if not cmpIdx:
                                cmpList = port.GetCompounds()  
                                cmpHtmlPerPort.append(self.FormatComposition(cmpList, COMPSTDLVOLFLOW))
                            cmpHtml = cmpHtmlPerPort[cntPort]
                            cntPort += 1
                            print '%s<td>&nbsp;</td><td>&nbsp;</td>' % cmpHtml[cmpIdx]  
                            
                print '</table>'    
            else:
                print '<tr><td>&nbsp;</td>'
                for port in matPorts:
                    cmpList = port.GetCompounds()  
                    print '<td colspan=4>%s</td>' % self.MakeCdRef(self.msg('WebComposition') , cmpList)
                print '</tr>'
            print '</tr></table><hr>'
            print '</div>'
        
        if (rowsperpage > 0 and rows % rowsperpage != 0):
            print '<div style="page-break-before:always">'
        else:
            print '<div>'

        #print '<table>'
        #self.PortSummaryRow(op, op.GetPortNames(ENE|IN),  'WebEneIn')
        #self.PortSummaryRow(op, op.GetPortNames(ENE|OUT), 'WebEneOut')
        #self.PortSummaryRow(op, op.GetPortNames(SIG),     'WebSig')
        #print '</table></div>'
        
        
    def PortSummaryRow(self, op, ports, title):
        """
        print a unit op row of the port summary
        """
        
        firstRow = 1
        for portName in ports:
            port = op.GetPort(portName)
            conn = port.GetConnection()
            if conn:
                connText = self.GetPathLinks(conn)
            else:
                connText = '_______'
            
            if isinstance(port, Ports.Port_Energy):
                prop = port.GetProperty(ENERGY_VAR)
                path = prop.GetPath()
            elif isinstance(port, Ports.Port_Signal):
                type = port.GetType()
                if type:
                    prop = port.GetProperty(type.name)
                    path = prop.GetPath()
                else:
                    prop = None
            else:
                prop = None
            
            if prop:
                # energy or signal - indicate if unknown
                if prop.GetValue() == None:
                    known = 0
                else:
                    known = 1
            else:
                # material port - indicate if unknown
                if port.GetPropValue(ZFACTOR_VAR) == None or port.GetPropValue(MOLEFLOW_VAR) == None:
                    known = 0
                else:
                    known = 1

            if known:
                print '<tr>'
            else:
                print '<tr bgcolor="%s">' % UnknownBGColor

            if firstRow:
                firstRow = 0
                print '<td>%s</td>' % self.msg(title)
            else:
                print '<td>&nbsp;</td>'
                
            port = op.GetPort(portName)
            print '<td>%s</td>' % self.MakeCdRef(portName, port)
            print '<td>%s </td><td>%s</td>' % (self.ConnectToLink(port), connText)
            
            if prop:
                print self.RenderBasicObject(path, prop)
            else:
                print '<td>&nbsp;</td>'
            print '</tr>'

    def PortSummaryRow_Tower(self, op, objects, title=None):
        firstRow = 1
        #for portName in ports:
        portType = MAT
        for obj in objects:
            #port = op.GetPort(portName)
            nuStage = obj.stage.number
            name= obj.name
            port = obj.port
            conn = port.GetConnection()
            if conn:
                connText = self.GetPathLinks(conn)
            else:
                connText = '_______'
            
            if isinstance(port, Ports.Port_Energy):
                prop = port.GetProperty(ENERGY_VAR)
                path = prop.GetPath()
                portType = ENE
            elif isinstance(port, Ports.Port_Signal):
                type = port.GetType()
                portType = SIG
                if type:
                    prop = port.GetProperty(type.name)
                    path = prop.GetPath()
                else:
                    prop = None
            else:
                prop = None
            
            if prop:
                # energy or signal - indicate if unknown
                if prop.GetValue() == None:
                    known = 0
                else:
                    known = 1
            else:
                # material port - indicate if unknown
                if port.GetPropValue(ZFACTOR_VAR) == None or port.GetPropValue(MOLEFLOW_VAR) == None:
                    known = 0
                else:
                    known = 1

            if known:
                print '<tr>'
            else:
                print '<tr bgcolor="%s">' % UnknownBGColor

            #if firstRow:
                #firstRow = 0
                #print '<td>%s</td>' % self.msg(title)
            #else:
                #print '<td>&nbsp;</td>'
                
            print '<td>%s</td>' % self.MakeCdRef('%d'%(nuStage,), obj.stage)
            #if portType == SIG or portType == MAT:
                #print '<td>%s</td>' % self.MakeCdRef('%d'%(nuStage,), obj.stage)
            if portType == ENE:
                if obj.incoming:
                    print '<td>%s</td>' %('In',)
                else:
                    print '<td>%s</td>' %('Out',)
            
            #port = op.GetPort(portName)
            print '<td>%s</td>' % self.MakeCdRef(name, port)
            print '<td>%s </td><td>%s</td>' % (self.ConnectToLink(port), connText)
            
            if prop:
                print self.RenderBasicObject(path, prop)
            else:
                print '<td>&nbsp;</td>'
                    
            print '</tr>'
        
    def PortSummaryRow_UserVariables(self, op, objects, title=None):
        firstRow = 1
        portType = MAT
        for obj in objects:
            name= obj.name
            port = obj.port
            conn = port.GetConnection()
            if conn:
                connText = self.GetPathLinks(conn)
            else:
                connText = '_______'
            
            if isinstance(port, Ports.Port_Energy):
                prop = port.GetProperty(ENERGY_VAR)
                path = prop.GetPath()
                portType = ENE
            elif isinstance(port, Ports.Port_Signal):
                type = port.GetType()
                portType = SIG
                if type:
                    prop = port.GetProperty(type.name)
                    path = prop.GetPath()
                else:
                    prop = None
            else:
                prop = None
            
            if prop:
                # energy or signal - indicate if unknown
                if prop.GetValue() == None:
                    known = 0
                else:
                    known = 1
            else:
                # material port - indicate if unknown
                if port.GetPropValue(ZFACTOR_VAR) == None or port.GetPropValue(MOLEFLOW_VAR) == None:
                    known = 0
                else:
                    known = 1

            if known:
                print '<tr>'
            else:
                print '<tr bgcolor="%s">' % UnknownBGColor

            #if firstRow:
                #firstRow = 0
                #print '<td>%s</td>' % self.msg(title)
            #else:
                #print '<td>&nbsp;</td>'
                
            print '<td>%s</td>' % self.MakeCdRef('%d'%(nuStage,), obj.stage)
            #if portType == SIG or portType == MAT:
                #print '<td>%s</td>' % self.MakeCdRef('%d'%(nuStage,), obj.stage)
            if portType == ENE:
                if obj.incoming:
                    print '<td>%s</td>' %('In',)
                else:
                    print '<td>%s</td>' %('Out',)
            
            #port = op.GetPort(portName)
            print '<td>%s</td>' % self.MakeCdRef(name, port)
            print '<td>%s </td><td>%s</td>' % (self.ConnectToLink(port), connText)
            
            if prop:
                print self.RenderBasicObject(path, prop)
            else:
                print '<td>&nbsp;</td>'
            print '</tr>'        
        
            if isinstance(obj, BaseForReactors.ReactorObject):
                if isinstance(obj, BaseForReactors.ReactorConversion):
                    '<td>&nbsp;%s</td>' %self.msg('WebConversionObj', (obj.cmpName,))
                elif isinstance(obj, BaseForReactors.ReactorSelectivity):
                    '<td>&nbsp;%s</td>' %self.msg('WebSelectivityObj', (obj.dCmpName, obj.uCmpName))
                elif isinstance(obj, BaseForReactors.ReactorYield):
                    '<td>&nbsp;%s</td>' %self.msg('WebYieldObj', (obj.dCmpName, obj.bCmpName))
                    
            
    def PortSummary(self, op):
        """
        Print the ports as links and connections
        """
        print '<table border=0>'
        self.PortSummaryRow(op, op.GetPortNames(MAT|IN),  'WebMatIn')
        self.PortSummaryRow(op, op.GetPortNames(MAT|OUT), 'WebMatOut')
        self.PortSummaryRow(op, op.GetPortNames(ENE|IN),  'WebEneIn')
        self.PortSummaryRow(op, op.GetPortNames(ENE|OUT), 'WebEneOut')
        self.PortSummaryRow(op, op.GetPortNames(SIG),     'WebSig')
        print '</table>'
        
    def GetPathLinks(self, obj):
        """
        return a string with each item in the obj.GetPath() having a link
        """
        path= obj.GetPath()
        comesFrom = path[0]
        names = path[1:].split('.')
        lPath = '<a href="docmd?cmd=%s&sid=%d" target="output" onClick="PathClick();">%s</a>' % (
                        cgi.escape('cd %s' %comesFrom,1),
                        self.id,
                        cgi.escape(comesFrom,1))
        first = 1
        newPath = comesFrom
        for name in names:
            if not first:
                lPath += '.'
                newPath += '.'
            first = 0
            newPath += name
            lPath += '<a href="docmd?cmd=%s&sid=%d" target="output" onClick="PathClick();">%s</a>' % (
                        cgi.escape('cd ' + newPath,1),
                        self.id,
                        cgi.escape(name,1))
        return lPath
    
    def ConnectToLink(self, obj):
        """
        create link to open window for adding or changing a connection
        """
        if isinstance(obj, Ports.Port):
            return r'''<a href="javascript:OpenConnectWindow('%s',%d);">-&gt;</a>''' % (
                       obj.GetPath(), self.id)
        elif isinstance(obj, UnitOperations.UnitOperation):
            return r'''<a href="javascript:OpenConnectThermoWindow('%s',%d);">-&gt;</a>''' % (
                       obj.GetPath(), self.id)
    def SpecFromLink(self, obj):
        """
        creates a link to specify a port based on the values of another port
        """
        if isinstance(obj, Ports.Port):
            return r'''<a href="javascript:OpenSpecFromWindow('%s',%d);">&gt&gt;</a>''' % (
                       obj.GetPath(), self.id)
    
    def ShowParentLine(self, obj):
        """
        Show a line with parent and root links
        """
        parent = obj.GetParent()
        if parent:
            print '%s: %s' % (self.msg('WebParent'), self.MakeCdRef(self.GetObjectName(parent), parent))
            if parent.GetParent():
                print '<a href="docmd?cmd=%s&sid=%d" target="output">%s</a>' % (
                                                   cgi.escape('cd /'), self.id, self.msg('WebRoot'))
            print '<br>\n'


    def RenderNumber(self, v, status=CALCULATED_V, type=None):
        """Represent any number in proper units and as if it had a specific type """
        if type:
            unit = self.s42cmd.units.GetCurrentUnit(type.unitType)
            if unit: v = unit.ConvertFromSim42(v)
            scale = type.scaleFactor
        else:
            scale = None
            unit = None
            
        if scale > 1000.:
            format = '%0.8g'
        elif scale > 100.:
            format = '%1.8g'
        elif scale >= 1.0:
            format = '%2.8g'
        else:
            format = '%4.8g'
        v = format % v
        result = '<td>'
        if status & PASSED_V:
            v = '<font color="%s">%s</font>' % (PassedFontColor, v)
        result += v
        result += '</td>\n'
        
        if status & ESTIMATED_V: statChar = '~'
        elif status & FIXED_V: statChar = '*'
        elif status & PASSED_V: statChar = '|'
        elif status & ESTIMATED_V: statChar = '~'
        elif status & CALCULATED_V: statChar = '='
        else: statChar = ''
        result += '<td width=15>%s</td>' % statChar
        
        if unit:  unitName = unit.name
        else: unitName = '&nbsp;'
        result += '<td>%s</td>' % unitName

        return result
    
            
    def RenderBasicObject(self, name, obj, withUnits=True):
        """produce representation of obj with units"""
        if obj is None:  # must use is as __cmp__ is overloaded
            v = None
            status = 0
            path = name
        else:
            v = obj.GetValue()
            status = obj.GetCalcStatus()
            if obj.GetParent() == self.s42cmd.currentObj:
                path = name
            else:
                path = obj.GetPath()
            
        if v != None:
            unit = self.s42cmd.units.GetCurrentUnit(obj.GetType().unitType)
            if unit: v = unit.ConvertFromSim42(v)
            scale = obj.GetType().scaleFactor
            if scale > 1000.:
                format = '%0.8g'
            elif scale > 100.:
                format = '%1.8g'
            elif scale >= 1.0:
                format = '%2.8g'
            else:
                format = '%4.8g'
            v = format % v
            result = '<td>'
        else:
            v = '''<a href="javascript:SetCommand(window, '%s = ');">_______</a>''' % path
            unit = None
            result = '<td bgcolor="%s">' % UnknownBGColor

        if status & (ESTIMATED_V | FIXED_V | UNKNOWN_V):
            if status & ESTIMATED_V:
                prompt = '%s ~= ' % path
            else:
                prompt = '%s = ' % path
            result += '''<a href="javascript:SetCommand(window, '%s');">%s</a>''' % (prompt, v)
        else:
            if status & PASSED_V:
                v = '<font color="%s">%s</font>' % (PassedFontColor, v)
            result += v
        result += '</td>\n'
        
        if status & ESTIMATED_V: statChar = '~'
        elif status & FIXED_V: statChar = '*'
        elif status & PASSED_V: statChar = '|'
        elif status & ESTIMATED_V: statChar = '~'
        elif status & CALCULATED_V: statChar = '='
        else: statChar = ''
        result += '<td width=15>%s</td>' % statChar
        
        if withUnits:
            if unit:  unitName = unit.name
            else: unitName = '&nbsp;'
            result += '<td>%s</td>' % unitName

        return result

    def ShowBasicProperty(self, prop):
        """
        render a single property on page
        """
        self.ClearMenus()
        print '<p><table frame="border"><tr><td>%s</td><td>' % prop.GetName()
        print self.RenderBasicObject('.', prop)
        print '</td></tr></table></p>'

    def RenderUnitOpParameter(self, name, param, choices):
        if not choices:
            result = '''<a href="javascript:SetCommand(window, '%s = ');">''' % name
            if param != None:
                v = param.GetValue()
                result += '%s</a>' % str(v)
            else:
                result += '_______</a>'''
        else:
            result = """<select name='%s' onChange='SetParameterFromChoice("%s", this)'>""" %(name, name)
            if param != None:
                v = param.GetValue()
                if not v in choices:
                    result += "<option selected value=''></option>"
            if isinstance(choices, dict):
                for value, choice in choices.items():
                    if v == value:
                        result += "<option selected value='%s'>%s</option>" %(value, choice)
                    else:
                        result += "<option value='%s'>%s</option>" %(value, choice)
            else:
                for choice in choices:
                    if v == choice:
                        result += "<option selected value='%s'>%s</option>" %(choice, choice)
                    else:
                        result += "<option value='%s'>%s</option>" %(choice, choice)
            result += "</select>"
                    
        return result

    def ShowUnitOpParam(self, param):
        """
        render a unit operation parameter
        """
        self.ClearMenus()
        paramValue = param.GetValue()
        if paramValue == None:
            paramValue = ''
            
        print r"""
        <script>
        function AddCmd(form)
        {
            form.cmd.value = '%s = ' + form.cmd.value;
            return true;
        }
        </script>
        """ % param.GetPath()

        print '<p><table frame="border"><tr><td>%s</td><td>' % param.GetName()
        print '<form name="command" action="docmd" method="POST" target="output" onSubmit="return AddCmd(this);">'
        print '<input type="hidden" name="sid" value="%d">\n' % self.id
        print """
          <textarea name=cmd rows=16 cols=60>%s</textarea>
          <br>
          <input type=submit value="%s">
        </form>
        """ % (paramValue, msg('WebUpdate'))
        print '</td></tr></table></p>'

    def PutPortConnectLink(self, port):
        """
        put connection links
        """
        print '<p><table frame="border">\n'
        print '<tr><td>%s</td>' % self.msg('WebConnectedTo')
        conn = port.GetConnection()
        print '<td>%s ' % self.ConnectToLink(port)
        if conn: print '%s</td></tr>' % self.GetPathLinks(conn)
        else: print '________</td></tr>\n'

    def PortMenus(self, port):
        """
        set up menus for a port
        """
        self.ClearMenus()
        print '''
        <script>
function AddToPortTables(menu)
{
    // other wise do default add object
    var selected = menu.selectedIndex;
    if( selected == 0 ) return false;
    var addCmd = menu.options[selected].value;
    var cmdString = '';
    var infoPath = '/Info.Simba.PortTables.';
    var name = '';
    if( addCmd.charAt(0) == '{') {
        name = window.prompt(parent.command.nameMessage,"");
        if( name == null || name == '' ) {
            menu.selectedIndex = 0;
            return false;
        }
        cmdString += infoPath + name + ' = {}; ';
        addCmd = addCmd.substr(1);
    }
    else
        name = menu.options[selected].text;
    infoPath += name  + '.'

    cmdString += infoPath + addCmd.substr(1).replace(/\./g,'_') + ' = "%%' + addCmd + '"';
    parent.command.document.command.cmd.value = cmdString;
    parent.command.document.command.submit();
    
    menu.selectedIndex = 0;
    return false;
}

function DeleteFromPortTable(menu)
{
    // other wise do default add object
    var selected = menu.selectedIndex;
    if( selected == 0 ) return false;
    var rmPath = menu.options[selected].value;
    var cmdString = 'delete ';
    var infoPath = '/Info.Simba.PortTables.';
    infoPath += menu.options[selected].text + '.';

    cmdString += infoPath + rmPath.substr(1).replace(/\./g,'_');
    parent.command.document.command.cmd.value = cmdString;
    parent.command.document.command.submit();
    
    menu.selectedIndex = 0;
    return false;
}

        var menu = parent.command.document.menuform.createmenu1;

        menu.menuMethod = AddToPortTables;
        menu.options[0] = new Option('%s');
        i = 1;
        ''' % self.msg('WebAddToPortTable')
        
        print '''
        var delMenu = parent.command.document.menuform.createmenu2;
        delMenu.menuMethod = DeleteFromPortTable;
        delMenu.options[0] = new Option('%s');
        j = 1;
        ''' % self.msg('WebDeleteFromPortTable')
        
        info = self.s42cmd.root.info
        if info.has_key(SIMBAINFO):
            simbaInfo = info[SIMBAINFO]
        else:
            simbaInfo = info[SIMBAINFO] = SimInfoDict(SIMBAINFO, info)
            
        if simbaInfo.has_key(PORTTABLES):
            portTables = simbaInfo[PORTTABLES]
        else:
            portTables = simbaInfo[PORTTABLES] = SimInfoDict(PORTTABLES, simbaInfo)
            
        tables = portTables.keys()
        tables.sort()
        portKey = re.sub('\.','_', port.GetPath()[1:])
        for table in tables:
            if portTables[table].has_key(portKey):
                print "delMenu.options[j++] = new Option('%s', '%s');" % (table, port.GetPath())
            else:
                print "menu.options[i++] = new Option('%s', '%s');" % (table, port.GetPath())
                
        print "menu.options[i++] = new Option('%s', '{%s');" % (self.msg('WebNewPortTable'), port.GetPath())
        print "</script>"
        
    def PutPortSpecFromLink(self, port):
        """
        put a link to specify the port based on a different port
        """
        print '<p><table frame="border">\n'
        print '<tr><td>%s</td>' % self.msg('WebSpecFrom')
        conn = port.GetConnection()
        print '<td> %s <td>' % self.SpecFromLink(port)
        print '</p></table>\n'
        
    def ShowMaterialPort(self, port, showFlashResults=True):
        """
        render material port
        """
        self.PortMenus(port)
        self.PutPortSpecFromLink(port)
        self.PutPortConnectLink(port)
        
        if isinstance(port, Ports.Port_Material):
            props = self.s42cmd.defaultPropertyOrder
        else:
            props = port.GetPropNames()
            props.sort()

        for propName in props:
            try:
                prop = port.GetProperty(propName)
                print '<tr><td>%s</td>%s</tr>\n' % (msg(propName), self.RenderBasicObject(propName, prop))
            except:
                print '<tr><td>%s</td><td>%s</td></tr>\n' % (propName, self.msg('WebInvalid'))
        
        cmpList = port.GetCompounds()
        print '<tr><td>&nbsp;</td><td>%s</td></tr>' % self.MakeCdRef(self.msg('WebComposition'), cmpList)
        print '</table></p>'
        
        if showFlashResults:
            eqVals = self.GetFlashResults(port)
            if eqVals:
                print '<HR>'
                print '<p><table frame="border">'
                print '<tr><td><strong>%s</strong></td></tr>' % self.msg('WebFlashResults')
                liqPhases = port._parentOp.NumberLiqPhases()
                solPhases = port._parentOp.NumberSolidPhases()
                print '<tr><td>%s</td><td>%s</td><td></td><td></td><td>%s</td><td></td><td></td>' %( "", self.msg('WebBulk'), self.msg('WebVapour'))
                for i in range(liqPhases):
                    print '<td>%s%d</td><td></td><td></td>' %(self.msg('WebLiquid'), i)
                for i in range(solPhases):
                    print '<td>%s%d</td><td></td><td></td>' %(self.msg('WebSolid'), i)
                print '</tr>'
                print '<tr><td>%s</td>%s%s' % (
                                self.msg('WebFraction'), 
                                self.RenderNumber(1.0, CALCULATED_V),
                                self.RenderNumber(eqVals.phaseFractions[0], CALCULATED_V))
                for i in range(liqPhases):
                    print '%s' %self.RenderNumber(eqVals.phaseFractions[1+i], CALCULATED_V)
                for i in range(solPhases):
                    print '%s' %self.RenderNumber(eqVals.phaseFractions[1+liqPhases+i], CALCULATED_V)
                print '</tr>'  
                for i in range(len(eqVals.propNames)):
                    type = port.GetProperty(eqVals.propNames[i]).GetType()
                    print '<tr><td>%s</td>%s%s' % (
                                self.msg(eqVals.propNames[i]), 
                                self.RenderNumber(eqVals.bulkProps[i], CALCULATED_V, type),
                                self.RenderNumber(eqVals.phaseProps[0][i], CALCULATED_V, type))
                                                                         
                    for j in range(liqPhases):
                        print '%s' %self.RenderNumber(eqVals.phaseProps[1+j][i], CALCULATED_V, type)
                    for j in range(solPhases):
                        print '%s' %self.RenderNumber(eqVals.phaseProps[1+liqPhases+j][i], CALCULATED_V, type)
                    print '</tr>'                
                
                cmpNames = port.GetCompoundNames()
                nuCmps = len(cmpNames)
                if nuCmps:
                    for cmp in range(nuCmps):
                        print '<tr><td>%s</td>%s%s' %(cmpNames[cmp], 
                                                      self.RenderNumber(eqVals.bulkComposition[cmp], CALCULATED_V), 
                                                      self.RenderNumber(eqVals.phaseComposition[0][cmp], CALCULATED_V))
                        for j in range(liqPhases):
                            print '%s' %self.RenderNumber(eqVals.phaseComposition[1+j][cmp], CALCULATED_V)
                        for j in range(solPhases):
                            print '%s' %self.RenderNumber(eqVals.phaseComposition[1+liqPhases+j][cmp], CALCULATED_V)
                        print '</tr>'
                    
                    
                print '</table></p>'
        
    def GetFlashResults(self, port):
        """Get the flash results if available from wherever they are"""
        
        if port._flashResults: return port._flashResults
        if not port.AlreadyFlashed(): return None
        
        #If I'm in a material strem, then the flash results could be anywhere
        if isinstance(port, Stream.Stream_Material):
            uo = port.GetParent()
            for otherPort in uo.GetPorts(IN|OUT|MAT):
                if otherPort.GetParent() is uo: #In case it borrows ports from children
                    if otherPort._flashResults:
                        return otherPort._flashResults
        
        #See if the flash results are in a connection only if this port is not estimated
        if port.IsEstimated(): return None
        conn = port.GetConnection()
        if conn.IsEstimated(): return None
        
        #Do exactly the same to the connection
        if not conn: return None
        if conn._flashResults: return conn._flashResults
        if not conn.AlreadyFlashed(): return None
        
        if isinstance(conn, Stream.Stream_Material):
            uo = conn.GetParent()
            for otherPort in uo.GetPorts(IN|OUT|MAT):
                if otherPort.GetParent() is uo: #In case it borrows ports from children
                    if otherPort._flashResults:
                        return otherPort._flashResults
                    
        #Could do a fancier search but this is good enough
                    
        return None
                    
    def ShowEnergyPort(self, port):
        """
        render energy port
        """
        self.PortMenus(port)
        self.PutPortConnectLink(port)
        try:
            propName = port.GetSignalType()
            prop = port.GetProperty(propName)
            print '<tr><td>%s</td>%s</tr>\n' % (msg(propName), self.RenderBasicObject(propName, prop))
        except:
            print '<tr><td>%s</td><td>%s</td></tr>\n' % (propName, self.msg('WebInvalid'))
        print '</table></p>'
    
    def ShowSignalPort(self, port):
        """
        render signal port
        """
        self.PortMenus(port)
        self.PutPortConnectLink(port)
        try:
            propName = port.GetSignalType()
            prop = port.GetProperty(propName)
            print '<tr><td>%s</td>%s</tr>\n' % (msg(propName), self.RenderBasicObject(propName, prop))
        except:
            print '<tr><td>%s</td><td>%s</td></tr>\n' % (propName, self.msg('WebInvalid'))
        print '</table></p>'       

    def GetStatusSymbol(self, var):
        """
        return the symbol indicating calculation type for BasicProperty var
        """
        calcStatus = var.GetCalcStatus()
        if calcStatus & ESTIMATED_V: return '~'
        if calcStatus & FIXED_V: return '*'
        if calcStatus & CALCULATED_V: return '='
        if calcStatus & PASSED_V: return '|'
        
    def FormatComposition(self, cmps, fmtType):
        sValues = []
        formatSwitchSize = 0.0001
        
        if fmtType & COMPMOLEFRAC:
            for i in range(len(cmps)):
                cmp = cmps[i]
                value = cmp.GetValue()
                symbol = self.GetStatusSymbol(cmp)
                if symbol is '=':
                    colour = EqualFontColor       
                elif symbol is '|':
                    colour = PassedFontColor
                else:
                    colour = FixedFontColor
                    
                if value == None:
                    sVal = '_______'
                    symbol = ''
                    bgcolor = UnknownBGColor                    
                elif 0.0 < abs(value) < formatSwitchSize:
                    bgcolor = ''
                    sVal = '%0.5g' % value
                else:
                    bgcolor = ''
                    sVal = '%0.5f' % value
                sValues.append('<td bgcolor=%s>' % bgcolor + self.MakeCdRef(sVal , cmps, colour) + '</td><td>%s</td>' % symbol)   


        elif fmtType & COMPMASSFRAC:
            massCmps = MassCompoundList(cmps)
            massFracs = massCmps.GetValues()
            for i in range(len(cmps)):
                cmp = cmps[i]
                value = cmp.GetValue()
                symbol = self.GetStatusSymbol(cmp)
                if symbol is '=':
                    colour = EqualFontColor       
                elif symbol is '|':
                    colour = PassedFontColor
                else:
                    colour = FixedFontColor
                    
                if massFracs[i] == None:
                    sVal = '_______'
                    symbol = ''
                    bgcolor = UnknownBGColor                    
                elif 0.0 < abs(value) < formatSwitchSize:
                    bgcolor = ''                    
                    sVal = '%0.5g' %  massFracs[i]
                else:
                    bgcolor = ''                    
                    sVal = '%0.5f' %  massFracs[i]
                sValues.append('<td bgcolor=%s>' % bgcolor + self.MakeCdRef(sVal , cmps, colour) + '</td><td>%s</td>' % symbol)    

        elif fmtType & COMPVOLFRAC:
            volCmps = StdVolCompoundList(cmps)
            volFracs = volCmps.GetValues()
            for i in range(len(cmps)):
                cmp = cmps[i]
                value = cmp.GetValue()
                symbol = self.GetStatusSymbol(cmp)
                if symbol is '=':
                    colour = EqualFontColor       
                elif symbol is '|':
                    colour = PassedFontColor
                else:
                    colour = FixedFontColor
                    
                if volFracs[i] == None:
                    sVal = '_______'
                    symbol = ''
                    bgcolor = UnknownBGColor                    
                elif 0.0 < abs(value) < formatSwitchSize:
                    bgcolor = ''                    
                    sVal = '%0.5g' %  volFracs[i]
                else:
                    bgcolor = ''                    
                    sVal = '%0.5f' %  volFracs[i]
                sValues.append('<td bgcolor=%s>' % bgcolor + self.MakeCdRef(sVal , cmps, colour) + '</td><td>%s</td>' % symbol)    
                
        elif (fmtType & COMPMOLEFLOW):
            moleFlowProp = cmps.GetParent().GetProperty(MOLEFLOW_VAR)
            moleFlow = moleFlowProp.GetValue()
            moleFlowStatus = moleFlowProp.GetCalcStatus()
            moleFlowUnit = self.s42cmd.units.GetCurrentUnit(PropTypes[MOLEFLOW_VAR].unitType)
            for i in range(len(cmps)):
                cmp = cmps[i]
                value = cmp.GetValue()
                symbol = self.GetStatusSymbol(cmp)
                if symbol is '=':
                    colour = EqualFontColor       
                elif symbol is '|':
                    colour = PassedFontColor
                else:
                    colour = FixedFontColor
                    
                if (value == None) or (moleFlow == None):
                    sVal = '_______'
                    symbol = ''
                    bgcolor = UnknownBGColor                    
                elif 0.0 < abs(value) < formatSwitchSize:
                    bgcolor = ''                    
                    sVal = '%0.5g' % moleFlowUnit.ConvertFromSim42(moleFlow * value)
                else:
                    bgcolor = ''                    
                    sVal = '%0.5f' % moleFlowUnit.ConvertFromSim42(moleFlow * value)
                sValues.append('<td bgcolor=%s>' % bgcolor + self.MakeCdRef(sVal , cmps, colour) + '</td><td>%s</td>' % symbol)   

        elif (fmtType & COMPMASSFLOW):
            massCmps = MassCompoundList(cmps)
            massFracs = massCmps.GetValues()
    
            massFlowProp = cmps.GetParent().GetProperty(MASSFLOW_VAR)
            massFlow = massFlowProp.GetValue() 
            massFlowStatus = massFlowProp.GetCalcStatus()
            massFlowUnit = self.s42cmd.units.GetCurrentUnit(PropTypes[MASSFLOW_VAR].unitType)
            
            for i in range(len(cmps)):
                cmp = cmps[i]
                value = cmp.GetValue()
                symbol = self.GetStatusSymbol(cmp)
                if symbol is '=':
                    colour = EqualFontColor       
                elif symbol is '|':
                    colour = PassedFontColor
                else:
                    colour = FixedFontColor
                    
                if value == None or (massFlow == None):
                    sVal = '_______'
                    symbol = ''
                    bgcolor = UnknownBGColor
                elif 0.0 < abs(value) < formatSwitchSize:
                    bgcolor = ''
                    sVal = '%0.5g' % massFlowUnit.ConvertFromSim42(massFlow * massFracs[i])
                else:
                    bgcolor = ''
                    sVal = '%0.5f' % massFlowUnit.ConvertFromSim42(massFlow * massFracs[i])
                sValues.append('<td bgcolor=%s>' % bgcolor + self.MakeCdRef(sVal , cmps, colour) + '</font></td><td>%s</td>' % symbol)
                
        elif (fmtType & COMPSTDLVOLFLOW):
            volCmps = StdVolCompoundList(cmps)
            volFracs = volCmps.GetValues()
            
            stdLVolFlowProp = cmps.GetParent().GetProperty(STDVOLFLOW_VAR)
            if not stdLVolFlowProp:
                stdLVolFlow = None
                stdLVolFlowStatus = UNKNOWN_V
            else:
                stdLVolFlow = stdLVolFlowProp.GetValue()
                stdLVolFlowStatus = stdLVolFlowProp.GetCalcStatus()
            stdLVolFlowUnit = self.s42cmd.units.GetCurrentUnit(PropTypes[STDVOLFLOW_VAR].unitType)
            
            for i in range(len(cmps)):
                cmp = cmps[i]
                value = cmp.GetValue()
                symbol = self.GetStatusSymbol(cmp)
                if symbol is '=':
                    colour = EqualFontColor       
                elif symbol is '|':
                    colour = PassedFontColor
                else:
                    colour = FixedFontColor
                    
                if value == None or (stdLVolFlow == None):
                    sVal = '_______'
                    symbol = ''
                    bgcolor = UnknownBGColor
                elif 0.0 < abs(value) < formatSwitchSize:
                    bgcolor = ''
                    sVal = '%0.5g' % stdLVolFlowUnit.ConvertFromSim42(stdLVolFlow * volFracs[i])
                else:
                    bgcolor = ''
                    sVal = '%0.5f' % stdLVolFlowUnit.ConvertFromSim42(stdLVolFlow * volFracs[i])
                sValues.append('<td bgcolor=%s>' % bgcolor + self.MakeCdRef(sVal , cmps, colour) + '</font></td><td>%s</td>' % symbol)
                
        return sValues
        
    def ShowCompoundList(self, cmps):
        """
        render composition
        """
        self.ClearMenus()
        
        cmpNames = cmps.GetCompoundNames()
        port = cmps.GetParent()
        units = self.s42cmd.units
        
        moleFlowProp = port.GetProperty(MOLEFLOW_VAR)
        moleFlow = moleFlowProp.GetValue()
        moleFlowStatus = moleFlowProp.GetCalcStatus()
        moleFlowUnit = units.GetCurrentUnit(PropTypes[MOLEFLOW_VAR].unitType)
        
        massCmps = MassCompoundList(cmps)
        massFracs = massCmps.GetValues()
        massFlowProp = port.GetProperty(MASSFLOW_VAR)
        massFlow = massFlowProp.GetValue()
        massFlowStatus = massFlowProp.GetCalcStatus()
        massFlowUnit = units.GetCurrentUnit(PropTypes[MASSFLOW_VAR].unitType)
        
        volCmps = StdVolCompoundList(cmps)
        volFracs = volCmps.GetValues()
        stdLVolFlowProp = port.GetProperty(STDVOLFLOW_VAR)
        if stdLVolFlowProp:
            stdLVolFlow = stdLVolFlowProp.GetValue()
            stdLVolFlowStatus = stdLVolFlowProp.GetCalcStatus()
        else:
            stdLVolFlow = None
            stdLVolFlowStatus = UNKNOWN_V
        stdLVolFlowUnit = units.GetCurrentUnit(PropTypes[STDVOLFLOW_VAR].unitType)
        
        print '<form name="cmpform"><table border=1>'
        print '<tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th>' % (self.msg('WebComponent'), 
                                                                    self.msg('WebMoleFraction'), 
                                                                    self.msg('WebMassFraction'), 
                                                                    self.msg('WebVolFraction'))
        print '<th>%s<br>%s</th><th>%s<br>%s</th><th>%s<br>%s</th></tr>' % (self.msg('WebCmpMoleFlows'), moleFlowUnit.name,
                                                                            self.msg('WebCmpMassFlows'), massFlowUnit.name,
                                                                            self.msg('WebCmpStdLiqVolFlows'), stdLVolFlowUnit.name)
        sNone = ''
        fracInput = 0
        massFracInput = None   # None means not yet determined
        volFracInput = None
        moleFlowInput = None
        massFlowInput = None
        stdLVolFlowInput = None
        for i in range(len(cmps)):
            cmp = cmps[i]
            value = cmp.GetValue()
            valueStatus = cmp.GetCalcStatus()
            if valueStatus & ESTIMATED_V: symbol = '~'
            if valueStatus & FIXED_V: symbol = '*'
            if valueStatus & CALCULATED_V: symbol = '='
            if valueStatus & PASSED_V: symbol = '|'            
            if value == None:
                sValue    = sNone
                sMassFrac = sNone
                sVolFrac = sNone
                sMoleFlow = sNone
                sMassFlow = sNone
                sStdLVolFlow = sNone
            else:
                sValue = '%0.5g' % value
                
                if massFracs[i] != None:
                    sMassFrac = '%0.5g' % massFracs[i]
                else:
                    sMassFrac = sNone
                    
                if volFracs[i] != None:
                    sVolFrac = '%0.5g' % volFracs[i]
                else:
                    sVolFrac = sNone    

                if moleFlow != None:
                    sMoleFlow = '%g' % (moleFlowUnit.ConvertFromSim42(moleFlow * value))
                else:
                    sMoleFlow = sNone
                    
                if massFlow != None:
                    sMassFlow = '%g' % (massFlowUnit.ConvertFromSim42(massFlow * massFracs[i]))
                else:
                    sMassFlow = sNone
                    
                if stdLVolFlow != None:
                    sStdLVolFlow = '%g' % (stdLVolFlowUnit.ConvertFromSim42(stdLVolFlow * volFracs[i]))
                else:
                    sStdLVolFlow = sNone
                    
            print '<tr><td>%s</td>' % cmpNames[i] 
            if valueStatus & CALCULATED_V:
                print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td>%s</td><td align=right>%s</td></tr></table></td>' % (sValue, symbol)
                print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td>%s</td><td align=right>%s</td></tr></table></td>' % (sMassFrac, symbol)
                print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td>%s</td><td align=right>%s</td></tr></table></td>' % (sVolFrac, symbol)
                massFracInput = 0
                volFracInput = 0
                
            elif valueStatus & PASSED_V:
                print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td><font color="%s">%s</font></td><td align=right>%s</td></tr></table></td' % (PassedFontColor, sValue, symbol)
                print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td><font color="%s">%s</font></td><td align=right>%s</td></tr></table></td' % (PassedFontColor, sMassFrac, symbol)
                print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td><font color="%s">%s</font></td><td align=right>%s</td></tr></table></td' % (PassedFontColor, sVolFrac, symbol)
            else:
                print '<td><input type=text name="molefr%d" size=20 value="%s"' % (i, sValue)
                print ' onChange="ChangedMoleFrac()" tabindex=%d></td>' % i
                
                print '<td><input type=text name="massfr%d" size=20 value="%s"' % (i, sMassFrac)
                print ' onChange="ChangedMassFrac()" tabindex=%d></td>' % (i + 1000)
                
                print '<td><input type=text name="volfr%d" size=20 value="%s"' % (i, sVolFrac)
                print ' onChange="ChangedVolFrac()" tabindex=%d></td>' % (i + 2000)
                
                fracInput = 1
                if massFracInput == None: massFracInput = 1
                if volFracInput == None: volFracInput = 1

            if valueStatus & (CALCULATED_V | PASSED_V):
                if moleFlow != None:
                    if valueStatus & PASSED_V:
                        print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td><font color="%s">%s</font></td><td align=right>%s</td></tr></table></td>' % (PassedFontColor, sMoleFlow, symbol)
                    else:
                        print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td>%s</td><td align=right>%s</td></tr></table></td>' % (sMoleFlow, symbol)
                    moleFlowInput = 0
                else:
                    print '<td><input type=text name="molefl%d" size=20 value=""'
                    print ' onChange="ChangedMoleFlow()" tabindex=%d></td>' % (i+3000)
                    if moleFlowInput == None: moleFlowInput = 1
                    
                if massFlow != None:
                    if valueStatus & PASSED_V:
                        print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td><font color="%s">%s</font></td><td align=right>%s</td></tr></table></td>' % (PassedFontColor, sMassFlow, symbol)
                    else:
                        print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td>%s</td><td align=right>%s</td></tr></table></td>' % (sMassFlow, symbol)
                    massFlowInput = 0
                else:
                    print '<td><input type=text name="massfl%d" size=20 value=""'
                    print ' onChange="ChangedMassFlow()" tabindex=%d></td>' % (i+4000)
                    if massFlowInput == None: massFlowInput = 1
                    
                if stdLVolFlow != None:
                    if valueStatus & PASSED_V:
                        print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td><font color="%s">%s</font></td><td align=right>%s</td></tr></table></td>' % (PassedFontColor, sStdLVolFlow, symbol)
                    else:
                        print '<td><table width="100%%" cellspacing=0 cellpadding=0><tr><td>%s</td><td align=right>%s</td></tr></table></td>' % (sStdLVolFlow, symbol)
                    stdLVolFlowInput = 0
                else:
                    print '<td><input type=text name="massfl%d" size=20 value=""'
                    print ' onChange="ChangedStdLVolFlow()" tabindex=%d></td>' % (i+5000)
                    if stdLVolFlowInput == None: stdLVolFlowInput = 1
                    
            else:
                print '<td><input type=text name="molefl%d" size=20 value="%s"' % (i, sMoleFlow)
                print ' onChange="ChangedMoleFlow()" tabindex=%d></td>' % (i+3000)
                print '<td><input type=text name="massfl%d" size=20 value="%s"' % (i, sMassFlow)
                print ' onChange="ChangedMassFlow()" tabindex=%d></td>' % (i+4000)
                print '<td><input type=text name="stdlvolfl%d" size=20 value="%s"' % (i, sStdLVolFlow)
                print ' onChange="ChangedStdLVolFlow()" tabindex=%d></td></tr>' % (i+5000)
                moleFlowInput = massFlowInput = stdLVolFlowInput = 1
                

        # add update buttons
        print '<tr><td>&nbsp;</td>'

        if fracInput:
            print '<td><input type="button" name="molefrbtn" value="Specify"'
            print '''onClick="UpdateMoleFrac('%s', '')">''' % cmps.GetPath()
            print '<input type="button" name="molefrbtn" value="Estimate"'
            print '''onClick="UpdateMoleFrac('%s', '~')"></td>''' % cmps.GetPath()
        else:
            print '<td>&nbsp;</td>'

        if massFracInput:
            print '<td><input type="button" name="massfrbtn" value="Specify"'
            print '''onClick="UpdateMassFrac('%s', '')">''' % cmps.GetPath()
            print '<input type="button" name="massfrbtn" value="Estimate"'
            print '''onClick="UpdateMassFrac('%s', '~')"></td>''' % cmps.GetPath()
        else:
            print '<td>&nbsp;</td>'
            
        if volFracInput:
            print '<td><input type="button" name="volfrbtn" value="Specify"'
            print '''onClick="UpdateVolFrac('%s', '')">''' % cmps.GetPath()
            print '<input type="button" name="volfrbtn" value="Estimate"'
            print '''onClick="UpdateVolFrac('%s', '~')"></td>''' % cmps.GetPath()
        else:
            print '<td>&nbsp;</td>'    
        
        if moleFlowInput:
            print '<td><input type="button" name="moleflbtn" value="Specify"'
            print '''onClick="UpdateMoleFlow('%s', '')">''' % cmps.GetPath()
            print '<input type="button" name="moleflbtn" value="Estimate"'
            print '''onClick="UpdateMoleFlow('%s', '~')"></td>''' % cmps.GetPath()
            
        else:
            print '<td>&nbsp;</td>'
        
        if massFlowInput:
            print '<td><input type="button" name="massflbtn" value="Specify"'
            print '''onClick="UpdateMassFlow('%s', '')">''' % cmps.GetPath()
            print '<input type="button" name="massflbtn" value="Estimate"'
            print '''onClick="UpdateMassFlow('%s', '~')"></td>''' % cmps.GetPath()
        else:
            print '<td>&nbsp;</td>'
        
        if stdLVolFlowInput:
            print '<td><input type="button" name="stdlvolflbtn" value="Specify"'
            print '''onClick="UpdateStdLVolFlow('%s', '')">''' % cmps.GetPath()
            print '<input type="button" name="stdlvolflbtn" value="Estimate"'
            print '''onClick="UpdateStdLVolFlow('%s', '~')"></td></tr>''' % cmps.GetPath()
        else:
            print '<td>&nbsp;</td>'
            
        print '</form></table>'
        
        
        print '''<script>
        document.numberCmps = %d; ''' % len(cmps)
        print '''
        function ChangedMoleFrac() {
            document.cmpform.massfrbtn.disabled = 1;
            document.cmpform.moleflbtn.disabled = 1;
            document.cmpform.massflbtn.disabled = 1;
            document.cmpform.volfrbtn.disabled = 1;
            document.cmpform.stdlvolflbtn.disabled = 1;
            for( i = 0; i < document.numberCmps; i++ ) {
                document.cmpform['massfr' + i].disabled = 1
                document.cmpform['molefl' + i].disabled = 1
                document.cmpform['massfl' + i].disabled = 1
                document.cmpform['volfr' + i].disabled = 1
                document.cmpform['stdlvolfl' + i].disabled = 1
            }
        }
        function ChangedMassFrac() {
            document.cmpform.molefrbtn.disabled = 1;
            document.cmpform.moleflbtn.disabled = 1;
            document.cmpform.massflbtn.disabled = 1;
            document.cmpform.volfrbtn.disabled = 1;
            document.cmpform.stdlvolflbtn.disabled = 1;
            for( i = 0; i < document.numberCmps; i++ ) {
                document.cmpform['molefr' + i].disabled = 1;
                document.cmpform['molefl' + i].disabled = 1;
                document.cmpform['massfl' + i].disabled = 1;
                document.cmpform['volfr' + i].disabled = 1
                document.cmpform['stdlvolfl' + i].disabled = 1
            }
        }
        function ChangedVolFrac() {
            document.cmpform.molefrbtn.disabled = 1;
            document.cmpform.moleflbtn.disabled = 1;
            document.cmpform.massfrbtn.disabled = 1;
            document.cmpform.massflbtn.disabled = 1;
            document.cmpform.stdlvolflbtn.disabled = 1;
            for( i = 0; i < document.numberCmps; i++ ) {
                document.cmpform['molefr' + i].disabled = 1;
                document.cmpform['molefl' + i].disabled = 1;
                document.cmpform['massfl' + i].disabled = 1;
                document.cmpform['massfr' + i].disabled = 1;
                document.cmpform['stdlvolfl' + i].disabled = 1
            }
        }
        function ChangedMoleFlow() {
            document.cmpform.massfrbtn.disabled = 1;
            document.cmpform.molefrbtn.disabled = 1;
            document.cmpform.massflbtn.disabled = 1;
            document.cmpform.volfrbtn.disabled = 1;
            document.cmpform.stdlvolflbtn.disabled = 1;
            for( i = 0; i < document.numberCmps; i++ ) {
                document.cmpform['massfr' + i].disabled = 1;
                document.cmpform['molefr' + i].disabled = 1;
                document.cmpform['massfl' + i].disabled = 1;
                document.cmpform['volfr' + i].disabled = 1
                document.cmpform['stdlvolfl' + i].disabled = 1
            }
        }
        function ChangedMassFlow() {
            document.cmpform.massfrbtn.disabled = 1;
            document.cmpform.moleflbtn.disabled = 1;
            document.cmpform.molefrbtn.disabled = 1;
            document.cmpform.volfrbtn.disabled = 1;
            document.cmpform.stdlvolflbtn.disabled = 1;
            for( i = 0; i < document.numberCmps; i++ ) {
                document.cmpform['massfr' + i].disabled = 1;
                document.cmpform['molefl' + i].disabled = 1;
                document.cmpform['molefr' + i].disabled = 1;
                document.cmpform['volfr' + i].disabled = 1
                document.cmpform['stdlvolfl' + i].disabled = 1
            }
        }
        function ChangedStdLVolFlow() {
            document.cmpform.molefrbtn.disabled = 1;
            document.cmpform.moleflbtn.disabled = 1;
            document.cmpform.massfrbtn.disabled = 1;
            document.cmpform.massflbtn.disabled = 1;
            document.cmpform.volfrbtn.disabled = 1;
            for( i = 0; i < document.numberCmps; i++ ) {
                document.cmpform['molefr' + i].disabled = 1;
                document.cmpform['molefl' + i].disabled = 1;
                document.cmpform['massfl' + i].disabled = 1;
                document.cmpform['massfr' + i].disabled = 1;
                document.cmpform['volfr' + i].disabled = 1
            }
        }
        '''
        print '''
        function UpdateMoleFrac(path, estSymbol) {
            var cmdField = parent.command.document.command.cmd;
            var c = path + ' ' + estSymbol + '=';
            var setToZero = 0;
            var setToNone = 0;
            var numNonZero = 0;
            for(i = 0; i < document.numberCmps; i++) {
                value = document.cmpform['molefr' + i];
                if(value == undefined) {
                    sValue = '';    // some fields are calculated - set them to None
                    setToNone = 1;
                }
                else {
                    sValue = document.cmpform['molefr' + i].value;
                    if( sValue == '' ) {
                        if( setToZero )
                            sValue = '0.0';
                        else if( setToNone ) {
                            sValue = 'None';
                            numNonZero++;
                        }
                        else {
                            setToZero = confirm("%s");
                            if(setToZero)
                                sValue = '0.0';
                            else {
                                setToNone = 1;
                                sValue = 'None';
                                numNonZero++;
                            }
                        }
                    }
                    else
                        numNonZero++;
                }
                
                if( sValue == '' ) {
                    sValue = 'None';
                    numNonZero++;
                }
                
                c += ' ' + sValue
            }
            if( numNonZero == 0 ) {
                alert("%s");
                return false;
            }
            cmdField.value = c;
            parent.command.document.command.submit();
            return false;
        }
        ''' % (self.msg('WebZeroMoleFrac'), self.msg('WebAllCmpsZero'))
        print '''
        function UpdateMassFrac(path, estSymbol) {
            var cmdField = parent.command.document.command.cmd;
            var c = path.replace(/Fraction$/, 'MassFraction ' + estSymbol + '=');
            var setToZero = 0;
            var numNonZero = 0;
            for(i = 0; i < document.numberCmps; i++) {
                sValue = document.cmpform['massfr' + i].value;
                if( sValue == '' ) {
                    if( setToZero )
                        sValue = '0.0';
                    else {
                        setToZero = confirm("%s");
                        if(setToZero)
                            sValue = '0.0';
                        else
                            return false;
                    }
                }
                else
                    numNonZero++;
                c += ' ' + sValue
            }
            if( numNonZero == 0 ) {
                alert("%s");
                return false;
            }
            cmdField.value = c;
            parent.command.document.command.submit();
            return false;
        }
        ''' % (self.msg('WebZeroComponent'), self.msg('WebAllCompZero'))
        print '''
        function UpdateVolFrac(path, estSymbol) {
            var cmdField = parent.command.document.command.cmd;
            var c = path.replace(/Fraction$/, 'StdVolFraction ' + estSymbol + '=');
            var setToZero = 0;
            var numNonZero = 0;
            for(i = 0; i < document.numberCmps; i++) {
                sValue = document.cmpform['volfr' + i].value;
                if( sValue == '' ) {
                    if( setToZero )
                        sValue = '0.0';
                    else {
                        setToZero = confirm("%s");
                        if(setToZero)
                            sValue = '0.0';
                        else
                            return false;
                    }
                }
                else
                    numNonZero++;
                c += ' ' + sValue
            }
            if( numNonZero == 0 ) {
                alert("%s");
                return false;
            }
            cmdField.value = c;
            parent.command.document.command.submit();
            return false;
        }
        ''' % (self.msg('WebZeroComponent'), self.msg('WebAllCompZero'))
        print '''        
        function UpdateMoleFlow(path, estSymbol) {
            var cmdField = parent.command.document.command.cmd;
            var c = path + ' ' + estSymbol + '=';
            var sum = 0.0;
            var setToZero = 0;
            
            for(i = 0; i < document.numberCmps; i++) {
                sValue = document.cmpform['molefl' + i].value;
                if( sValue == '' ) {
                    if( setToZero )
                        sValue = '0.0';
                    else {
                        setToZero = confirm("%s");
                        if(setToZero)
                            sValue = '0.0';
                        else
                            return false;
                    }
                }
                else {
                    sum += Number(sValue);
                }
                c += ' ' + sValue;
            }
            if( sum != null ) {
                if( sum == 0.0 ) {
                    alert("%s");
                    return false;
                }

                flowPath = path.replace(/Fraction$/, 'MassFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'StdLiqVolumeFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'VolumeFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'MoleFlow ' + estSymbol + '= ');
                flowPath += String(sum);
                c += '; ' + flowPath;
            }
            
            cmdField.value = c;
            parent.command.document.command.submit();
            return false;
        }
        ''' % (self.msg('WebZeroComponent'), self.msg('WebAllCompZero'))
        print '''        
        function UpdateMassFlow(path, estSymbol) {
            var cmdField = parent.command.document.command.cmd;
            var c = path.replace(/Fraction$/, 'MassFraction ' + estSymbol + '= ');
            var sum = 0.0;
            var setToZero = 0;
            
            for(i = 0; i < document.numberCmps; i++) {
                sValue = document.cmpform['massfl' + i].value;
                if( sValue == '' ) {
                    if( setToZero )
                        sValue = '0.0';
                    else {
                        setToZero = confirm("%s");
                        if(setToZero)
                            sValue = '0.0';
                        else
                            return false;
                    }
                }
                else {
                    sum += Number(sValue);
                }
                c += ' ' + sValue;
            }
            if( sum != null ) {
                if( sum == 0.0 ) {
                    alert("%s");
                    return false;
                }

                flowPath = path.replace(/Fraction$/, 'MoleFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'StdLiqVolumeFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'VolumeFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'MassFlow ' + estSymbol + '= ');
                flowPath += String(sum);
                c += '; ' + flowPath;
            }
            
            cmdField.value = c;
            parent.command.document.command.submit();
            return false;
        }
        ''' % (self.msg('WebZeroComponent'), self.msg('WebAllCompZero'))
        print '''        
        function UpdateStdLVolFlow(path, estSymbol) {
            var cmdField = parent.command.document.command.cmd;
            var c = path.replace(/Fraction$/, 'StdVolFraction ' + estSymbol + '= ');
            var sum = 0.0;
            var setToZero = 0;
            
            for(i = 0; i < document.numberCmps; i++) {
                sValue = document.cmpform['stdlvolfl' + i].value;
                if( sValue == '' ) {
                    if( setToZero )
                        sValue = '0.0';
                    else {
                        setToZero = confirm("%s");
                        if(setToZero)
                            sValue = '0.0';
                        else
                            return false;
                    }
                }
                else {
                    sum += Number(sValue);
                }
                c += ' ' + sValue;
            }
            if( sum != null ) {
                if( sum == 0.0 ) {
                    alert("%s");
                    return false;
                }

                flowPath = path.replace(/Fraction$/, 'MoleFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'MassFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'VolumeFlow = None; ');
                flowPath += path.replace(/Fraction$/, 'StdLiqVolumeFlow ' + estSymbol + '= ');
                flowPath += String(sum);
                c += '; ' + flowPath;
            }
            
            cmdField.value = c;
            parent.command.document.command.submit();
            return false;
        }
        ''' % (self.msg('WebZeroComponent'), self.msg('WebAllCompZero'))
        print '''
        </script>'''
  
        
    def ShowThermoAdmin(self, thAdmin):
        self.ClearMenus()
        print '''
        <script>
'''

        print '''
        parent.command.document.menuform.createmenu3.options.length = 0;
        var menu = parent.command.document.menuform.createmenu1;
        menu.options.length = 0;
        //menu.menuMethod = CreateThermoCaseInThAdmin;
        menu.menuMethod = undefined;
        menu.conn = 0;
        menu.options[0] = new Option('%s');
        ''' % self.msg('WebAddThermo')
        
        thermo = self.s42cmd.thermoAdmin
        providers = thermo.GetAvThermoProviderNames()
        providers.sort()
        i = 0
        for provider in providers:
            pkgs = thermo.GetAvPropPkgNames(provider)
            pkgs.sort()
            for pkg in pkgs:
                i += 1
                print 'menu.options[%d] = new Option("%s.%s","%s.%s")' % (i,provider, pkg, provider, pkg)

                
        print r""" 
            function AddThermoCase(path) {
                var cmdField = parent.command.document.command.cmd;
                if( cmdField.value != '' && !window.confirm("%s")) return false;
                thWin = window.open('advthermo?sid=%d', 'thwindow',
                            'width=500,height=450,status=yes,resizable=yes');
                thWin.focus();
                window.path = path;
                if( thWin.opener == null ) {
                    thWin.opener = window;
                }
                return false;
            }

        """ % (self.msg('WebConfirmReplaceCmd'), self.id)                
                
        print '</script>'

        
        print """<p><input type=submit value="%s" onClick="AddThermoCase('%s')"></p>"""%(self.msg('WebAddAdvanced'), thAdmin.GetPath())

        print '<p><strong>%s</strong><br><table frame="border">' % self.msg('WebAdminThermoCases')
        print '<tr>'
        print '<td align="center">%s</td><td align="center">%s</td>' %(
                       self.msg('WebThermoName'), self.msg('WebThermoProvider'))
        print '<td align="center">%s</td><td align="center">%s</td><td align="center">%s</td>' %(
                       self.msg('WebVapPkg'), self.msg('WebLiqPkg'), self.msg('WebSolPkg'))
        print '</tr>'  
        for name, case in thAdmin.GetContents():
            vap = liq = sol = '---'
            pkgs = case.package.split()
            vap = pkgs[0]
            if len(pkgs) > 1: liq = pkgs[1]
            if len(pkgs) > 2: sol = pkgs[4]  #Solid pkg is in the 4th position. Will need to change as this is hard coded for VMG
            if liq == '---': liq = vap
            print '<tr>'
            print '<td>%s</td><td>%s</td>' %(self.MakeCdRef(name, case), case.provider)
            print '<td>%s</td><td>%s</td><td>%s</td>' %(vap, liq, sol)
            print '</tr>'                                                     
            
        print '</table></p>\n'    
       
    def ShowUnitOp(self, op):
        """
        render unit op
        """
        self.ShowUnitOp_MenuAddThermo(op)
        self.ShowUnitOp_MenuAddUnitOp(op)
        self.ShowUnitOp_Tags(op)
        self.ShowUnitOp_TopShortcuts(op)
        self.ShowUnitOp_Msg(op)
            
        #For now it is good enough adding these if statements for the special handling in these unit ops
        if isinstance(op, Properties.SpecialProps):
            self.ShowSelectSpecialProps(op)
        elif isinstance(op, Properties.VectorProps) and not isinstance(op, HydrateThermoBased.HydrateCurve):
            self.ShowSelectVectorProps(op)
        
        self.ShowUnitOp_Ports(op)
        self.ShowUnitOp_Thermo(op)
        self.ShowUnitOp_Parameters(op)
        self.ShowUnitOp_Children(op)
        
            
    def ShowUnitOp_MenuAddThermo(self, op, flag=None):
        print '''
        <script>
        parent.command.document.menuform.createmenu3.options.length = 0;
        var menu = parent.command.document.menuform.createmenu1;
        menu.menuMethod = parent.command.CreateThermoCase;
        menu.options.length = 0;
        menu.conn = 1;
        menu.options[0] = new Option('%s');
        ''' % self.msg('WebAddThermo')
        
        thermo = self.s42cmd.thermoAdmin
        providers = thermo.GetAvThermoProviderNames()
        providers.sort()
        i = 0
        for provider in providers:
            pkgs = thermo.GetAvPropPkgNames(provider)
            pkgs.sort()
            if provider == 'VirtualMaterials':
                providerName = 'VMG'
            else:
                providerName = provider
            for pkg in pkgs:
                i += 1
                print 'menu.options[%d] = new Option("%s.%s","%s.%s")' % (i,providerName, pkg, provider, pkg)
        print '</script>'
            
        
    def ShowUnitOp_MenuAddUnitOp(self, op, flag=None):
        print '''<script>
        var menu = parent.command.document.menuform.createmenu2;
        menu.options.length = 0;
        menu.menuMethod = undefined;

        menu.options[0] = new Option('%s');
        ''' % self.msg('WebAddUnitOp')

        #streams
        print '''
        var i = 1;
        menu.options[i++] = new Option('%s','%s')''' % (self.msg('WebMaterialStream'),'Stream.Stream_Material()')
        print "menu.options[i++] = new Option('%s', '%s')" % (self.msg('WebEnergyStream'), 'Stream.Stream_Energy()')
        print "menu.options[i++] = new Option('%s', '%s')" % (self.msg('WebSignalStream'), 'Stream.Stream_Signal()')
        
        
        #Balances
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebMixer'), "Mixer.Mixer()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebSplitter'), "Split.Splitter()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebBalance'), "Balance.BalanceOp()")
        

        #Heat exchange
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebHeater'), "Heater.Heater()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebCooler'), "Heater.Cooler()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebHeatExchanger'), "Heater.HeatExchangerUA()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebMultiHX'), "Heater.MultiSidedHeatExchangerOp()") 

        
        #Pressure change
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebValve'), "Valve.Valve()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebCompressor'), "Compressor.Compressor()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebCompressorWithCurve'), "Compressor.CompressorWithCurve()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebExpander'), "Compressor.Expander()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebExpanderWithCurve'), "Compressor.ExpanderWithCurve()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebPump'), "Pump.Pump()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebPumpWithCurve'), "Pump.PumpWithCurve()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebPipeSegment'), "PipeSegment.PipeSegment()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebEjector'), "Ejector.EjectorOp()")
        
        
        #Separation units
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebSeparator'), "Flash.SimpleFlash()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebComponentSplitter'), "ComponentSplitter.ComponentSplitter()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebAbsorber'), "Tower.Absorber()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebReboiledAbsorber'), "Tower.ReboiledAbsorber()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebRefluxedAbsorber'), "Tower.RefluxedAbsorber()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebDistillationColumn'), "Tower.DistillationColumn()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebTower'), "Tower.Tower()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebLiqLiqExt'), "LiqLiqExt.LiqLiqEx()")
        
        
        #Reactors
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebConversionReactor'), "ConvRxn.ConvReactor()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebEquilReactor'), "EquiliReactor.EquilibriumReactor()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebCSTR'), "KineticReactor.CSTR()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebPFR'), "KineticReactor.PFR()")

        
        #Properties
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebPTEnvelope'), "Envelope.PTEnvelope()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebSpecialProperties'), "Properties.SpecialProps()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebBoilingCurves'), "Properties.VectorProps()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebPropertyTable'), "Properties.PropertyTable()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebHydrate'), "HydrateThermoBased.Hydrate()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebHydrateCurve'), "HydrateThermoBased.HydrateCurve()")
        
        
        #Utilities
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebEquation'), "Equation.Equation()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebSet'), "Set.Set()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebCrossConnector'), "CrossConnector.CrossConnector()")
        print "menu.options[i++] = new Option('%s','%s')" % (self.msg('WebController'), "Controller.Controller()")
        

        
        scriptDir = 'scriptops'
        try:
            scripts = self.handler.server.listdir(self.s42cmd.root, scriptDir)
                
            for script in scripts:
                try:
                    if not self.handler.server.localOnly:
                        scriptPath = self.user.name + '/'
                    else:
                        scriptPath = ''
                    scriptPath += scriptDir + '/' + script
                    f = self.s42cmd.safeOpen('%s' % scriptPath, 'r')
                    line = f.readline()
                    f.close()
                    if line.startswith('##'):
                        unitop = line[2:].strip()
                        p = "menu.options[i++] = new Option('%s','%s(" % (script, unitop)
                        p += '"read %s"' % (scriptPath)
                        p += ")')"
                        print p
                except:
                    pass
        except:
            pass
            
        print '</script>'
    
    def ShowUnitOp_Tags(self, op, flag=None):
        if op.Solver().hold:
            print '<font color="red"><b>%s</b></font> ' % msg('WebHolding')
            print '(<a href="docmd?cmd=%s&sid=%d" target="output">%s</a>)' % ('go', self.id, msg('WebGo'))
        else:
            print '(<a href="docmd?cmd=%s&sid=%d" target="output">%s</a>) ' % (
                urllib.quote('Ignored = 1; Ignored = None'), self.id, msg('WebRecalc'))

        if op.GetChildUONames():
            pfdOpPath = '/Info.%s.%s' % (simbapfd.PFDINFO, PFDOP)
            cmdLine = 'delete %s; %s = %%%s; cd /Info.%s' % (pfdOpPath, pfdOpPath, op.GetPath(), simbapfd.PFDINFO)
            cmdLine = urllib.quote(cmdLine)
            print '(<a href="docmd?cmd=%s&sid=%d" target="output">%s</a>)<br>' % (cmdLine, self.id, msg('WebPFD'))
        
    def ShowUnitOp_TopShortcuts(self, op, flag=None):
        if isinstance(op, Tower.Tower):
            print '<p>%s: ' %self.msg('WebShortcuts')
            print '<a href="#parameters" class="content">%s</a> ' %self.msg('WebOpParameters')
            print ', '
            print '<a href="#stageview">%s</a> ' %self.msg('WebSummary')
            print ', '
            print '<a href="#degfreedom" class="content">%s</a> ' %self.msg('WebDegreesOfFreedom')
            print ', '
            print '<a href="#profiles" class="content">%s</a> ' %self.msg('WebTowerProfiles')
            print '</p>'
            
        elif isinstance(op, Heater.MultiSidedHeatExchangerOp) or isinstance(op, PipeSegment.PipeSegment):
            print '<p>%s: ' %self.msg('WebShortcuts')
            print '<a href="#parameters" class="content">%s</a> ' %self.msg('WebOpParameters')
            print ', '
            print '<a href="#segsview">%s</a> ' %self.msg('WebSummary')
            print ', '
            print '<a href="#profiles" class="content">%s</a> ' %self.msg('WebTowerProfiles')
            print '</p>'
        elif isinstance(op, KineticReactor.CSTR):
            print '<p>%s: ' %self.msg('WebShortcuts')
            print '<a href="#parameters" class="content">%s</a> ' %self.msg('WebOpParameters')
            print ', '
            print '<a href="#segsview">%s</a> ' %self.msg('WebSummary')
            print ', '
            print '<a href="#rxnformulas" class="content">%s</a> ' %self.msg('WebRxnFormulas')
            print '</p>'
        else:
            print '<p>%s: ' %self.msg('WebShortcuts')
            print '<a href="#parameters" class="content">%s</a> ' %self.msg('WebOpParameters')
            print '</p>'
            
    def ShowUnitOp_Msg(self, op, flag=None):
        if hasattr(op, 'unitOpMessage'):
            if op.unitOpMessage:
                try:
                    if len(op.unitOpMessage) == 1:
                        print '<p>Status: %s</p>' %str(op.unitOpMessage[0])
                    elif len(op.unitOpMessage) > 1:
                        print '<p>Status: %s</p>' %str(MessageHandler.RenderMessage(op.unitOpMessage[0], 
                                                                                    op.unitOpMessage[1], 
                                                                                    self.infoCallBack.languageDict))
                        #try:
                            #if len(op.unitOpMessage[1]) > 1:
                                #for data in op.unitOpMessage[1][:-1]:
                                    #print str(data) + ", "
                                #print str(op.unitOpMessage[1][-1])
                            #else:
                                #print str(op.unitOpMessage[1][0])
                            #print '</p>'
                        #except:
                            #print '</p>'
                except:
                    pass
                
    def ShowUnitOp_Thermo(self, op, flag=None):
        thCaseObj = op.thCaseObj
        print '<p>%s<br><table frame="border">' % self.msg('WebOpThermoCase')
        print '<tr><td>%s</td>' %self.ConnectToLink(op)
        if thCaseObj:
            if thCaseObj.provider == 'VirtualMaterials': prov = 'VMG'
            else: prov = thCaseObj.provider                
            print '<td>%s</td><td>%s</td></tr>' % (
                   self.MakeCdRef(thCaseObj.name, thCaseObj), 
                   prov + '.' + thCaseObj.package)
        else:
            thCaseObj = op.GetThermo()
            if thCaseObj == None:
                print '<td>______</td></tr>'
            else:
                if thCaseObj.provider == 'VirtualMaterials': prov = 'VMG'
                else: prov = thCaseObj.provider
                parentOp = thCaseObj.GetParent()
                if isinstance(parentOp, UnitOperations.UnitOperation):
                    print '<td>______ Using "%s" from "%s"</td></tr>' %(thCaseObj.name,
                                                                        parentOp.GetPath())
                else:
                    print '<td>______</td></tr>'
                
        print '</table></p>\n'            

            
    def ShowUnitOp_Ports(self, op, flag=None):
        if not len(op.GetPorts()): return
        
        if isinstance(op, Tower.Tower):
            feeds = []
            liqDraws = []
            liqClones = []
            vapDraws = []
            vapClones = []
            wDraws = []
            signals = []
            qFeeds = []
            estimates = []
            
            for stage in op.stages:
                if stage.waterDraw:
                    wDraws.append(stage.waterDraw)
                
                for spec in stage.specs.values():
                    signals.append(spec)
                    
                for estimate in stage.estimates.values():
                    estimates.append(estimate)
                    
                for qFeed in stage.qfeeds.values():
                    qFeeds.append(qFeed)
                    
                for feed in stage.feeds.values():
                    feeds.append(feed)
                    
                for draw in stage.liqDraws.values():
                    liqDraws.append(draw)
                    for spec in draw.drawSpecs.values():
                        signals.append(spec)
                    for estimate in draw.estimates.values():
                        estimates.append(estimate)
                    
                for draw in stage.vapDraws.values():
                    vapDraws.append(draw)
                    for spec in draw.drawSpecs.values():
                        signals.append(spec)
                    for estimate in draw.estimates.values():
                        estimates.append(estimate)
                        
                for draw in stage.liqClones.values():
                    liqClones.append(draw)
                    for spec in draw.drawSpecs.values():
                        signals.append(spec)
                    for estimate in draw.estimates.values():
                        estimates.append(estimate)
                        
                for draw in stage.vapClones.values():
                    vapClones.append(draw)
                    for spec in draw.drawSpecs.values():
                        signals.append(spec)
                    for estimate in draw.estimates.values():
                        estimates.append(estimate)
                        
            if signals: 
                print '<p>%s: ' % self.msg('Signals')
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, signals,  'Signals')
                print '</table>'
            
            if estimates: 
                print '<p>%s: ' % self.msg('Estimates')
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, estimates,  'Estimates')
                print '</table>'
                
            if qFeeds: 
                print '<p>%s: ' % self.msg('Energy')
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Type</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, qFeeds)
                print '</table>'                
                
            if feeds:             
                print '<p>%s: ' % self.msg('Feeds'),
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, feeds,  'Feeds')
                print '</table>'
            
            if wDraws: 
                print '<p>%s: ' % self.msg('WaterDraws'),
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, wDraws,  'WaterDraws')
                print '</table>'
            
            if liqDraws: 
                print '<p>%s: ' % self.msg('LiquidDraws'),
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, liqDraws,  'LiquidDraws')
                print '</table>'
            
            if vapDraws: 
                print '<p>%s: ' % self.msg('VapourDraws'),
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, vapDraws,  'VapourDraws')
                print '</table>'
            
            if liqClones: 
                print '<p>%s: ' % self.msg('LiquidClones'),
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, liqClones,  'LiquidClones')
                print '</table>'
            
            if vapClones: 
                print '<p>%s: ' % self.msg('VapourClones'),
                print '<table border=1>'
                print '<tr><td>Stage</td><td>Name</td></tr>'
                self.PortSummaryRow_Tower(op, vapClones,  'VapourClones')
                print '</table>'
            
            

        elif isinstance(op, KineticReactor.CSTR):
            sigPorts = op.GetPortNames(SIG)
            vars = op.signals.values()
            #Signals that are user variables will be displayed separately.
            #Remove them from sigPorts
            try:
                for s in vars:
                    sigPorts.pop(sigPorts.index(s.port.name))
            except:
                sigPorts = op.GetPortNames(SIG)
                
            
            print '<p>%s: ' % self.msg('WebPorts'),
            print '<table border=1><tr><td>'
            self.ListMatPorts(op)
            print '<table>'
            self.PortSummaryRow(op, op.GetPortNames(ENE|IN),  'WebEneIn')
            self.PortSummaryRow(op, op.GetPortNames(ENE|OUT), 'WebEneOut')
            self.PortSummaryRow(op, sigPorts, 'WebSig')
            print '</table></div>'
            print '</td></tr>'
            print '</table></p>'
            
            
            print '<p>%s: ' % self.msg('UserVariables')
            print '<table border=1>'
            print '<tr><td>Name</td><td>Type</td><td>Name</td></tr>'
            self.PortSummaryRow_UserVariables(op, vars)
            print '</table>'
            
            
        else:
            print '<p>%s: ' % self.msg('WebPorts'),
            print '<table border=1><tr><td>'
            self.ListMatPorts(op)
            print '<table>'
            self.PortSummaryRow(op, op.GetPortNames(ENE|IN),  'WebEneIn')
            self.PortSummaryRow(op, op.GetPortNames(ENE|OUT), 'WebEneOut')
            self.PortSummaryRow(op, op.GetPortNames(SIG),     'WebSig')
            print '</table></div>'
            print '</td></tr>'
            print '</table></p>'
            
            
            
    def ShowUnitOp_Parameters(self, op, flag=None, skipParams=[]):
        """This method is added such that ShowUnitOp can be broken down"""
        parameters = op.GetParameters()
        if not parameters: return
        
        
        print '<script>'
        print '''
        function SetParameterFromChoice(paramName, combo) {
            var cmd = parent.command.document.command.cmd;
            cmd.focus();
            cmd.value = '';
            var idx = combo.selectedIndex;
            cmd.value = paramName + ' = ' + combo.options[idx].value;
            parent.command.document.command.submit();
            return false;
        }
        </script>
        '''
        
        if isinstance(op, Properties.SpecialProps):
            names = parameters.keys()
            names.sort()
            print '<a name="parameters"></a><p>%s<br><table frame="border">' % self.msg('WebOpParameters')
            key = Properties.ACTIVE_KEY
            length = len(key)
            key2 = 'Available'
            length2 = len(key2)
            for p in names:
                param = op.GetObject(p)
                if p[-length:] != key and p[:length2] != key2:
                    print '<tr><td>%s</td><td>%s</td></tr>' % (
                        self.MakeCdRef(p, param), self.RenderUnitOpParameter(p, param))
            print '</table></p>\n'
        else:
            names = parameters.keys()
            names.sort()
            choices = {}
            print '<a name="parameters"></a><p>%s<br><table frame="border">' % self.msg('WebOpParameters')
            for name in names:
                skip = name in skipParams
                #If the name of a parameter starts with "Av" then assume it is a list of choices for its corresponding parameter
                #for exemple... AvSolveMethods works for SolveMethods
                if not skip and name[:2] == 'Av':
                    if parameters[name] != None:
                        if parameters.has_key(name[2:]):
                            choices[name[2:]] = parameters[name].split()
                            skip = 1
                        elif parameters.has_key(name[2:-1]):
                            choices[name[2:-1]] = parameters[name].split()
                            skip = 1
                if name == "CustomEquationUnitSet":
                    choices[name] = self.s42cmd.units.GetSetNames()
                elif name == 'BalanceType':
                    choices[name] = {1: "Mass Balance",
                                     2: "Mole Balance",
                                     4: "Energy Balance",
                                     6: "Mole and Energy Balance"}
                if not skip:
                    param = op.GetObject(name)
                    lst = choices.get(name, None)
                    print '<tr><td>%s</td><td>%s</td></tr>' % (
                        self.MakeCdRef(name, param), self.RenderUnitOpParameter(name, param, lst))
            print '</table></p>\n'
        
        
    def ShowUnitOp_Children(self, op, flag=None):
        children = op.GetChildUnitOps()
        children.sort()
        if len(children):
            print '<b>%s</b>\n' % self.msg('WebContainsUO')
            print '<table border=1>\n'
            print '<tr><td align="left" valign="top">%s</td><td align="left">%s</td></tr>\n' % (
                                                                       self.msg('WebName'), self.msg('WebPorts'))
            for child in children:
                (name, childObj) = child
                print '<tr><td valign=top>%s</td>\n' % self.MakeCdRef(name, childObj)
                print '<td align="left">'
                self.PortSummary(childObj)
                print '</td></tr>\n'
                
            print '</table>\n'
        
            
    def ShowDrawFlow(self, type, unit, draw):
        """
        draw flow for tower display
        """
        try:
            value = unit.ConvertFromSim42(draw.port.GetPropValue(MOLEFLOW_VAR))
            if value == None:
                sValue = '---'
            else:
                sValue = ' %7.1f' % value
            flow = self.MakeCdRef(type, draw) + self.MakeCdRef(sValue, draw.port) + '<br>'
        except:
            flow = '??<br>'
        return flow
        
    def ShowQFlow(self, type, unit, qfeed):
        """
        energy flow for tower display
        """
        try:
            value = unit.ConvertFromSim42(qfeed.port.GetPropValue(ENERGY_VAR))
            if value == None:
                sValue = '---'
            else:
                if not qfeed.incoming:
                    value = -value
                
                sValue = '%10.0f' % value
            qflow = self.MakeCdRef(type, qfeed) + self.MakeCdRef(sValue, qfeed.port) + '<br>'
        except:
            qflow = '??<br>'
        return qflow

    def SpecIndicator(self, obj):
        """
        return an indicator whether the obj has specs
        """
        nSpecs = obj.NumberOfUserSpecs()
        if nSpecs: return nSpecs * '*'
        else: return ''


    def ShowMaterialStream(self, stream):
        """
        render material stream
        """
        self.ShowUnitOp(stream)
        print '''
        <script>
        var menu3 = parent.command.document.menuform.createmenu3;
        menu3.options.length = 0;
        menu3.menuMethod = undefined;
        menu3.options[0] = new Option('%s');''' % self.msg('WebAddClonesMenu')
        print '''
        var i = 1;
        menu3.options[i++] = new Option('%s','%s')''' % (self.msg('WebAddInClonePort'),
                                                         'Stream.ClonePort()')
        print '''menu3.options[i++] = new Option('%s','%s')''' % (self.msg('WebAddOutClonePort'),
                                                         'Stream.ClonePort(0)')
        
        props = self.s42cmd.defaultPropertyOrder
        for propName in props:
            print '''menu3.options[i++] = new Option('%s',"%s")''' % (
                      self.msg('WebAddSensorPort',propName), "Stream.SensorPort('%s')" % propName)
        print '</script>'

    def ShowEnergyStream(self, stream):
        """
        render energy stream
        """
        self.ShowUnitOp(stream)
        print '''
        <script>
        var menu3 = parent.command.document.menuform.createmenu3;
        menu3.options.length = 0;
        menu3.menuMethod = undefined;
        menu3.options[0] = new Option('%s');''' % self.msg('WebAddClonesMenu')
        print '''
        var i = 1;
        menu3.options[i++] = new Option('%s','%s')''' % (self.msg('WebAddInClonePort'),
                                                         'Stream.ClonePort()')
        print '''menu3.options[i++] = new Option('%s','%s')''' % (self.msg('WebAddOutClonePort'),
                                                         'Stream.ClonePort(0)')
        
        print '''menu3.options[i++] = new Option('%s',"%s")''' % (
                      self.msg('WebAddSensorPort',ENERGY_VAR), "Stream.SensorPort('%s')" % ENERGY_VAR)
        print '</script>'

    def ShowSignalStream(self, stream):
        """
        render signal stream
        """
        self.ShowUnitOp(stream)
        print '''
        <script>
        var menu3 = parent.command.document.menuform.createmenu3;
        menu3.options.length = 0;
        menu3.menuMethod = undefined;
        menu3.options[0] = new Option('%s');''' % self.msg('WebAddSigCloneMenu')
        print '''
        menu3.options[1] = new Option('%s','%s')''' % (self.msg('WebAddSigClonePort'),
                                                         'Stream.ClonePort()')
        print '</script>'


        
    def ShowSelectSpecialProps(self, op):
        """render special props. Called automatically by ShowUnitOp"""
        
        #These come as space separated strings and are a subset of
        #Properties.SPECIAL_PROPS
        coldProps = Properties.COLD_PROPS.split()
        refProps = Properties.REFINERY_PROPS.split()
        
        print '<script>'
        print 'propList = Array('
        first = 1
        for prop in (coldProps + refProps):
            if first:
                first = 0
            else:
                print ',',
            print "'%s'" % prop
        print ');'

        print 'selectedProp = Array('
        first = 1
        for prop in (coldProps + refProps):
            if first:
                first = 0
            else:
                print ',',
            print "Boolean(%s)" % op.GetParameterValue(prop + Properties.ACTIVE_KEY)
        print ');'

        print '''
        function UpdateViewedProps(form) {
            var cmd = parent.command.document.command.cmd;
            cmd.focus();
            cmd.value = '';
                
            for(i = 0; i < propList.length; i++) {
                var fieldName = propList[i];
                if( Boolean(form[fieldName].checked) != selectedProp[i]) {
                    if(form[fieldName].checked){
                        cmd.value += fieldName + '%s = 1; ';
                    }
                    else {
                        cmd.value += fieldName + '%s = 0; ';
                    }
                }                
                
            }

            parent.command.document.command.submit();
            return false;
        }
        </script>
        ''' % (Properties.ACTIVE_KEY, Properties.ACTIVE_KEY)
        
        nuColdProps = len(coldProps)
        nuRefProps = len(refProps)
        
        #List cold properties
        print '<form name="updateprops" onSubmit="return UpdateViewedProps(this);"><p>'
        print '<table frame="box" rules="">'
        print '''
        <tr>
          <td><strong>%s</strong></td><td><strong>%s</strong></td>
          <td>&nbsp;&nbsp;&nbsp;</td>
          <td><strong>%s</strong></td><td><strong>%s</strong></td>

        </tr>

        ''' % (self.msg('WebColdProps'), self.msg('WebInclude'), 
               self.msg('WebRefineryProps'), self.msg('WebInclude'))
        
        for i in range(max(nuColdProps, nuRefProps)):
            print '<tr>'
            if i < nuColdProps:
                prop = coldProps[i]
                print '<td>%s</td>' % self.msg(prop)
                print '<td><input type="checkbox" name="%s"' % (prop,)
                if op.GetParameterValue(prop + Properties.ACTIVE_KEY):
                    print ' checked',
                print '></td>'
            else:
                print '<td>&nbsp;</td><td>&nbsp;</td>'
                
            print '<td>&nbsp;&nbsp;&nbsp;</td>'
            
            if i < nuRefProps:
                prop = refProps[i]
                print '<td>%s</td>' % self.msg(prop)
                print '<td><input type="checkbox" name="%s"' % (prop,)
                if op.GetParameterValue(prop + Properties.ACTIVE_KEY):
                    print ' checked',
                print '></td>'
            else:
                print '<td>&nbsp;</td><td>&nbsp;</td>'
                
            print '</tr>'
        print '<tr><td colspan=5 align="center">'
        print '<input type="submit" name="update" value="%s">' % self.msg('WebUpdate')
        print '</td></tr></table></p></form>'
        
    
    def ShowVectorProps(self, op):
        """Render the profiles"""

        #Check if it is a hydrate curve
        isHydrate = False
        try:
            if isinstance(op, HydrateThermoBased.HydrateCurve):
                isHydrate = True
        except:
            isHydrate = False
        self.isHydrate = isHydrate
        
        #This call automatically display the options for selecting which TBP curves to calculate
        self.ShowUnitOp(op)
        
        print '<a name="vecprops"></a>'
        #Grab the results directly
        profiles = op.results       #Dictionary with pairs of values
        curveNames = profiles.keys()
        if not curveNames: return
        curveNames.sort()
        
        #Make a copy of everything so we don't mess around with the unit op results
        copyProfiles = {}
        for key in profiles:
            copyProfiles[key] = array(profiles[key], Float)
        profiles = copyProfiles
        
        xVec = None
        units = self.s42cmd.units
        tUnit = units.GetCurrentUnit(PropTypes[T_VAR].unitType)
        pUnit = units.GetCurrentUnit(PropTypes[P_VAR].unitType)
            
        print '<hr><h3>%s</h3>' % msg('WebTowerProfiles')
        print '<p><table frame="box" rules="rows,cols">'
        
        # stage headers
        if isHydrate:
            print '<tr><th align=center>%s</th>' % self.msg(T_VAR)
            
        else:
            print '<tr><th align=center>%s</th>' % self.msg('WebPercentVol')
        for name in curveNames:
            if isHydrate:
                print '<th align=center>%s</th>' % self.msg(P_VAR)
            else:
                print '<th align=center>%s</th>' % name 

            #Load the percent vol vec in this loop. Assume all results will come with 
            #a TBP for the same % vol values
            if profiles[name] and not xVec:
                pairOfVals = profiles[name]
                xVec = pairOfVals[:, 0]
                
            
        print '</tr>'
        
        # units
        if isHydrate:
            print '<tr><td align=right>%s</td>'  % tUnit.name
            for name in curveNames:
                print '<td align=right>%s</td>' % pUnit.name
        else:
            print '<tr><td align=right>&nbsp;</td>' 
            for name in curveNames:
                print '<td align=right>%s</td>' % tUnit.name

        print '</tr>'
        
        if isHydrate:
            if xVec:
                for i in range(len(xVec)):
                    for name in curveNames:
                        try:
                            #It should only come in here once (for hydrate curve)
                            value = xVec[i]
                            value = tUnit.ConvertFromSim42(value)
                            profiles[name][i][0] = value
                            value = '%f' % value
                            print '<tr><td align=right>%s</td>' % value
                            
                            value = profiles[name][i][1]            #Row i col 1
                            value = pUnit.ConvertFromSim42(value)
                            profiles[name][i][1] = value
                            value = '%f' % value
                        except:
                            value = '-'
                        print '<td align=right>%s</td>' % value
                print '</tr>'            
        else:
            if xVec:
                for i in range(len(xVec)):
                    print '<tr><td>%s</td>' % str(xVec[i])
                    for name in curveNames:
                        try:
                            value = profiles[name][i][1]            #Row i col 1
                            value = tUnit.ConvertFromSim42(value)
                            profiles[name][i][1] = value
                            value = '%f' % value
                        except:
                            value = '-'
                        print '<td align=right>%s</td>' % value
                print '</tr>'
        print '</table></p>'
            
        if xVec:
            #Load this so the call for plotting can access the values
            #self.curves has a value depending in the context in which it is being called/used
            #Profiles are already converted in units
            self.curves = profiles
            if graph42:
                for name in curveNames:
                    if profiles[name]:
                        print '<p><img src="vecplot?sid=%d&curve=%s" border=1 align=center></p>' % (
                           self.id, name)
                           
                        
    def ShowVectorPropsPlots(self, curveName):
        self.handler.send_header("Content-type", "image/png")
        self.handler.end_headers()

        "a realistic line plot with actual data"
        
        
        #If loaded by vector props, then self.curves is a dictionary
        #Values are already convertec in units
        vals = self.curves.get(curveName, None)
        if not vals: return
        
        units = self.s42cmd.units
        tunit = units.GetCurrentUnit(PropTypes[T_VAR].unitType)
        punit = units.GetCurrentUnit(PropTypes[P_VAR].unitType)
            
        g = graph42.Graph()
        g.bottom = 400.0
        g.right = 590

        xVec = vals[:, 0]
        yVec = vals[:, 1]
        
        nVals = len(xVec)
        g.datasets.append(graph42.Dataset(vals))

        format0 = graph42.PointPlot()
        format0.lineStyle = graph42.LineStyle(width=2, color=graph42.red, kind=graph42.SOLID)
        format0.symbol = graph42.CircleSymbol
        
        g.formats = [format0]
        
        numberTics = 10
        if self.isHydrate:
            minValue, maxValue = min(xVec), max(xVec)
            g.axes[graph42.X].range = [minValue, maxValue]
            g.axes[graph42.X].tickMarks[0].spacing = (maxValue - minValue)/numberTics
            g.axes[graph42.X].tickMarks[0].labels = "%g"
            g.axes[graph42.X].label.text = '<b>%s (%s)</b>' % (self.msg(T_VAR), tunit.name)
        else:
            g.axes[graph42.X].range = [0,100.0]
            g.axes[graph42.X].tickMarks[0].spacing = 10
            g.axes[graph42.X].tickMarks[0].labels = "%d"
            g.axes[graph42.X].label.text = '<b>%s</b>' % self.msg('WebPercentVol')

        unitName = tunit.name
        
        numberTics = 10
        (minValue, maxValue) = graph42.ScaleValues(yVec, numberTics)
        g.axes[graph42.Y].range = [minValue, maxValue]
        g.axes[graph42.Y].tickMarks[0].spacing = (maxValue - minValue)/numberTics
        g.axes[graph42.Y].tickMarks[0].labels = "%g"
        if self.isHydrate:
            g.axes[graph42.Y].label.text = "<b>%s (%s)</b>" % (self.msg(P_VAR), punit.name)
        else:
            g.axes[graph42.Y].label.text = "<b>%s (%s)</b>" % (curveName, unitName)

        g.title.text = "<b>%s</b>" % curveName
        g.top = g.top + 40
        
        backend = 'piddlePIL'
        canvasname = "Profile"
        module = __import__(backend)
        canvasClass = getattr(module, "PILCanvas")
        size = (600,500)
        canvas = canvasClass(size,canvasname)
        # draw the graph
        g.draw(canvas)

        # do post-test cleanup
        canvas.flush()
        canvas.save(file=self.handler.wfile, format='png')      # save as a PNG file
        
    def ShowSelectVectorProps(self, op):
        """render vector props (boiling point curves). Called automatically by ShowUnitOp"""
        
        #These come as a list
        vecProps = Properties.VECTOR_PROPS #Boiling point curves
        
        print '<script>'
        print 'propList = Array('
        first = 1
        for prop in vecProps:
            if first:
                first = 0
            else:
                print ',',
            print "'%s'" % prop
        print ');'

        print 'selectedProp = Array('
        first = 1
        for prop in vecProps:
            if first:
                first = 0
            else:
                print ',',
            print "Boolean(%s)" % op.GetParameterValue(prop + Properties.ACTIVE_KEY)
        print ');'

        print '''
        function UpdateViewedProps(form) {
            var cmd = parent.command.document.command.cmd;
            cmd.focus();
            cmd.value = '';
                
            for(i = 0; i < propList.length; i++) {
                var fieldName = propList[i];
                if( Boolean(form[fieldName].checked) != selectedProp[i]) {
                    if(form[fieldName].checked){
                        cmd.value += fieldName + '%s = 1; ';
                    }
                    else {
                        cmd.value += fieldName + '%s = 0; ';
                    }
                }                
                
            }

            parent.command.document.command.submit();
            return false;
        }
        </script>
        ''' % (Properties.ACTIVE_KEY, Properties.ACTIVE_KEY)
        
        nuVecProps = len(vecProps)
        
        #List cold properties
        print '<form name="updateprops" onSubmit="return UpdateViewedProps(this);"><p>'
        print '<table frame="box" rules="">'
        print '''
        <tr>
          <td><strong>%s</strong></td><td><strong>%s</strong></td>
        </tr>

        ''' % (self.msg('WebBoilingCurves'), self.msg('WebInclude'))
        
        for i in range(nuVecProps):
            print '<tr>'
            if i < nuVecProps:
                prop = vecProps[i]
                print '<td>%s</td>' % self.msg(prop)
                print '<td><input type="checkbox" name="%s"' % (prop,)
                if op.GetParameterValue(prop + Properties.ACTIVE_KEY):
                    print ' checked',
                print '></td>'
            else:
                print '<td>&nbsp;</td><td>&nbsp;</td>'
                
            print '</tr>'
        print '<tr><td colspan=2 align="center">'
        print '<input type="submit" name="update" value="%s">' % self.msg('WebUpdate')
        print '</td></tr></table></p></form>'
        
        
    def GetConnString(self, typeDraw, conn):
        """
        Helper method to build a string to indicate of internal connections in a tower
        Used by ShowTower
        typeDraw refers to the local type of draw to use: F, L, V, W, etc
        conn is the connected port
        """
        connString = ''
        
        try:
            portName = conn.GetName()
            portName = portName.split('_', 3)
            stageNu = int(portName[1])
            if portName[0] == 'Feed':
                connString += '%s->F@%i%s' %(typeDraw, stageNu, '<br>')
            elif portName[0] == 'LiquidDraw':
                connString += '%s->L@%i%s' %(typeDraw, stageNu, '<br>')
            elif portName[0] == 'VapourDraw':
                connString += '%s->V@%i%s' %(typeDraw, stageNu, '<br>')
            elif portName[0] == 'LiquidPADraw':    
                connString += '%s->L@%i%s' %(typeDraw, stageNu, '<br>')
            elif portName[0] == 'LiquidPADraw':       
                connString += '%s->V@%i%s' %(typeDraw, stageNu, '<br>')
            elif portName[0] == 'InternalLiquid':    
                connString += '%s->LC@%i%s' %(typeDraw, stageNu, '<br>')
            elif portName[0] == 'InternalVapour':       
                connString += '%s->VC@%i%s' %(typeDraw, stageNu, '<br>')                
            elif portName[0] == 'WaterDraw':       
                connString += '%s->W@%i%s' %(typeDraw, stageNu, '<br>')       
            elif portName[0] == 'EnergyFeed':       
                connString += '%s->Q@%i%s' %(typeDraw, stageNu, '<br>')       
            else:
                pass
            return connString
        
        except:
            return ''
        
    def ShowCSTR(self, op):
        self.ShowUnitOp_MenuAddThermo(op)
        self.ShowUnitOp_Tags(op)
        self.ShowUnitOp_TopShortcuts(op)
        self.ShowUnitOp_Msg(op)
        self.ShowUnitOp_Ports(op)
        self.ShowUnitOp_Thermo(op)
        self.ShowUnitOp_Parameters(op)
        
        
        print '<a name="rxnformulas"></a><p>%s<br><table frame="border">' % self.msg('WebRxnFormulas')
        
        rxnOps = []
        for child in op.chUODict.values():
            if isinstance(child, BaseForReactors.Reaction):
                rxnOps.append(child)
        self.ShowUnitOp_RxnFormulas(op, rxnOps)
        
    def ShowUnitOp_RxnFormulas(self, op, rxnOps):
        cmpNames = op.GetCompoundNames()
        nuCmps = len(cmpNames)
        if not nuCmps: return
        
        nuRxns = len(rxnOps)
        if not nuRxns: return
        
        
        print '<form name="rxnformulas" onSubmit="return UpdateRxnFormulas(this);"><p>'
        print '<table frame="box" rules="">'
        print '<tr> <td><strong>%s</strong></td>' %self.msg('WebComponent')
        for nuRxn in range(nuRxns):
            print '<td><strong>%s</strong></td>' %self.MakeCdRef(rxnOps[nuRxn].rxnName, rxnOps[nuRxn])
            #print '<td><strong>%s %i</strong></td>' %(self.msg('WebReaction'), nuRxn+1)
        print '</tr>'
        
        for nuCmp in range(nuCmps):
            print '<tr><td>%s</td>' %cmpNames[nuCmp]
            for nuRxn in range(nuRxns):
                try:
                    print '<td align="right">%s</td>' %self.MakeCdRef(str(rxnOps[nuRxn].stoichCoeffs[nuCmp]), rxnOps[nuRxn])
                except:
                    print '<td align="right">%s<td>'%self.MakeCdRef("____", rxnOps[nuRxn])
            print '</tr>'
        print '</table></p></form>'
        
    def ShowReaction(self, op):
        
        print '''
        <script>
        function UpdateRxnFormulas(form) {
            var cmd = parent.command.document.command.cmd;
            cmd.focus();
            cmd.value = '';
                
            for(i = 0; i < propList.length; i++) {
                var fieldName = propList[i];
                if( Boolean(form[fieldName].checked) != selectedProp[i]) {
                    if(form[fieldName].checked){
                        cmd.value += fieldName + '%s = 1; ';
                    }
                    else {
                        cmd.value += fieldName + '%s = 0; ';
                    }
                }                
                
            }

            parent.command.document.command.submit();
            return false;
        }
        </script>
        '''
        
        cmpNames = op.GetCompoundNames()
        nuCmps = len(cmpNames)
        if not nuCmps: return
        
        #Just one reaction
        nuRxns = 1
        if not nuRxns: return
        
        print '<form name="rxnformulas" onSubmit="return UpdateRxnFormulas(this);"><p>'
        print '<table frame="box" rules="">'
        print '<tr> <td><strong>%s</strong></td>' %self.msg('WebComponent')
        for nuRxn in range(nuRxns):
            print '<td><strong><input align="right" type=text name="rxnname" size=20 value="%s" tabindex=1></strong></td>' %(op.rxnName,)
        print '</tr>'
        
        for nuCmp in range(nuCmps):
            print '<tr><td>%s</td>' %cmpNames[nuCmp]
            for nuRxn in range(nuRxns):
                try:
                    print '<td><input align="right" type=text name="coeff%d" size=20 value="%s" tabindex=%d></td>' % (nuCmp, op.stoichCoeffs[nuCmp], nuCmp+2)
                except:
                    print '<td><input align="reight" type=text name="coeff%d" size=20 value="" tabindex=%d></td>' % (nuCmp, nuCmp+2)
            print '</tr>'
        print '<tr><td colspan=2 align="center">'
        print '<input type="submit" name="update" value="%s">' % self.msg('WebUpdate')
        print '</td></tr></table></p></form>'
        
        
    def ShowHeaterCooler(self, hx):
        """
        render a heater or a cooler
        """
        self.ShowUnitOp(hx)
        print '''
        <script>
        function OpenHXProfileWindow(hxPath, sid) {
            profileWin = window.open('hxprofilereq?sid='+ sid + '&hx=' + hxPath, 'hxprofwindow',
                        'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
            profileWin.focus();
            if( profileWin.opener == null ) {
                profileWin.opener = window;
            }
        }
        
        </script>
        '''
        
        #Code was copied and paste from hx and it is easier to just use the same nomenclature
        counterCVec = [False]
        isColdVec = [True]
        nSides = 1
        nSegs = hx.GetParameterValue(Heater.NUSEGMENTS_PAR)
        if hx.GetPort(IN_PORT + 'Q'):
            isColdVec[0] = False
            
        units = self.s42cmd.units
        print '<a name="profiles"></a>'
        curves = hx.GetParameterValue('Profiles')
        if curves and nSegs:
            def makeCurves(curve):
                try:
                    #curve = curve.split()
                    
                    unitLst = []
                    for unitName in curve:
                        if unitName == 'EnergyAcum':
                            unitName = ENERGY_VAR
                        try:
                            tempUnitName = unitName.split('_', 1)
                            if len(tempUnitName) == 2:
                                if tempUnitName[0] == Tower.TOWER_VAP_PHASE:
                                    unitName = tempUnitName[1]
                                elif tempUnitName[0] == Tower.TOWER_LIQ_PHASE:
                                    unitName = tempUnitName[1]
                            unit = units.GetCurrentUnit(PropTypes[unitName].unitType)
                        except:
                            unit = None
                        unitLst.append(unit)
                    return [curve, unitLst, counterCVec, isColdVec]
                except:
                    return [[], [], counterCVec, isColdVec]
                
            propLst = curves.strip().split()
            curves = []
            cnt = 0
            while cnt < len(propLst)-1:
                curves.append([propLst[cnt],propLst[cnt+1]])
                cnt += 2
                              
            curves = map(makeCurves, curves)
            curveVals = {}
            
            print '<hr><h3>%s</h3>' % msg('WebTowerProfiles')
            print '<p><table frame="box" rules="rows,cols">'
    
            # stage headers
            propLst = []
            unitLst = []
            valsLst = []
            print '<tr><th align=center>%s</th>' % self.msg('WebSegmentNumber')
            for (props, propUnits, dummy, dummy2) in curves:
                for i in range(len(props)):
                    if not props[i] in propLst:
                        propName = props[i]
                        unit = propUnits[i]
                        propLst.append(propName)
                        unitLst.append(unit)
                        unitName = ''
                        if unit:
                            unitName = propUnits[i].name
                        print '<th align=center colspan=%i>%s (%s)</th>' % (nSides, props[i], unitName)
                        
                        #Use this loop to load the values
                        for nSide in range(nSides):                            
                            try:
                                values = Numeric.array(hx.GetObject(propName))
                                values = Numeric.reshape(values, (values.shape[0],))
                                valsLst.append(values)
                                curveVals[(nSide, propName)] = values
                            except:
                                valsLst.append(None)
                                curveVals[(nSide, propName)] = values
                        
            print '</tr>'
            
            # sides
            print '<tr><td align=center>&nbsp;</td>'
            for propName in propLst:
                for nSide in range(nSides):
                    print '<td align=center>%s %i</td>' %(self.msg('WebSide'), nSide)
            print '</tr>'
                
            #Label if counter current
            print '<tr><td align=center>&nbsp;</td>'
            for propName in propLst:
                for nSide in range(nSides):
                    print '<td align=center>--></td>'
            print '</tr>'
            
            
            #Loop to write the values in a table
            #Values come out of this loop with the current units
            for nSeg in range(nSegs+1):
                print '<tr><td align=center>%i</td>' %nSeg
                idxVals = 0
                for idxProp in range(len(propLst)):
                    for nSide in range(nSides):
                        try:
                            value = '-'
                            values = valsLst[idxVals]
                            idxVals += 1
                            if values != None:
                                value = values[nSeg]
                                if unitLst[idxProp]:
                                    value = unitLst[idxProp].ConvertFromSim42(value)
                                    values[nSeg] = value
                                value = '%f' %value
                        except:
                            value = '-'
                        print '<td align=center>%s</td>' %value
                print '</tr>'
            
            print '</table></p>'
            
            self.curves = curves
            self.curveVals = curveVals
            doPlots = True
            for vals in curveVals.values():
                if vals == None or None in vals:
                    doPlots = False
                    
            if doPlots and graph42:
                for idx in range(len(curves)):
                    print '<p><img src="hxplot?sid=%d&curve=%s" border=1 align=center></p>' % (
                           self.id, idx)
                        
                        
            profileLinkText = self.msg('WebChangeTwrProfile')
        else:
            profileLinkText = self.msg('WebAddProfile')

        print '''<a href="javascript:OpenHXProfileWindow('%s',%d);">%s</a>''' % (
            hx.GetPath(), self.id, profileLinkText)

        
        
    def ShowPipeSegment(self, pipe):
        """
        render pipe segment
        """        
        self.ShowUnitOp(pipe)
        print '''
        <script>
        function OpenTowerProfileWindow(twrPath, sid) {
            profileWin = window.open('twrprofilereq?sid='+ sid + '&tower=' + twrPath, 'twrprofwindow',
                        'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
            profileWin.focus();
            if( profileWin.opener == null ) {
                profileWin.opener = window;
            }
        }
        
        </script>
        '''
        
        nSegs = pipe.nuSections
        
        print '<a name="segsview"></a><p><table frame="box" rules="rows,cols">'
        units = self.s42cmd.units
        tunit = units.GetCurrentUnit(PropTypes[T_VAR].unitType)
        punit = units.GetCurrentUnit(PropTypes[P_VAR].unitType)
        qunit = units.GetCurrentUnit(PropTypes[ENERGY_VAR].unitType)
        uunit = units.GetCurrentUnit(PropTypes[U_VAR].unitType)
        lenunit = units.GetCurrentUnit(PropTypes[LENGTH_VAR].unitType)
        
        # segments headers
        print '<tr>'
        
        print '''<th align=center>%s</th>''' % (self.msg('WebSegmentNumber'))
        
        #Dimensions
        print '''<th align=center colspan=2>%s (%s)</th>
                 <th align=center colspan=2>%s (%s)</th>
                 <th align=center colspan=2>%s (%s)</th>
                 <th align=center colspan=2>%s</th>'''      % ('x', lenunit.name,
                                                               'y', lenunit.name, 
                                                               self.msg(LENGTH_VAR), lenunit.name,
                                                               'K')
        
        
        #Properties
        print '''<th align=center>%s (%s)</th>
                 <th align=center>%s (%s)</th>''' % (self.msg(T_VAR), tunit.name, 
                                                     self.msg(P_VAR), punit.name)
       
        #Heat transfer
        print '''<th align=center>%s (%s)</th>
                 <th align=center>%s (%s)</th>''' % (self.msg(ENERGY_VAR), qunit.name,
                                                     self.msg(U_VAR), uunit.name,)
        #Other stuff
        print '''<th align=center>%s</th>
                 <th align=center>%s</th>
                 <th align=center>%s</th>''' % ('Re',
                                                'Holdup',
                                                'FlowRegime')
        
        print '</tr>'
        
        
        xProfs = pipe.GetObject('x_Profile').GetProperties() #pipe.liveProfiles['x'].GetProperties()
        yProfs = pipe.GetObject('y_Profile').GetProperties()
        lenProfs = pipe.GetObject('%s_Profile' %PipeSegment.LENGTH_PORT).GetProperties()
        kProfs = pipe.GetObject('K_Profile').GetProperties()
        
        tArr = pipe.GetObject(T_VAR)
        pArr = pipe.GetObject(P_VAR)
        qArr = pipe.GetObject(ENERGY_VAR)
        uArr = pipe.GetObject('u')
        reArr = pipe.GetObject('Re')
        holArr = pipe.GetObject('Holdup')
        frArr = pipe.GetObject('FlowRegime')
        
        for nSeg in range(nSegs+1):
            x = y = length = k = "<td align=right>-</td><td align=right>-</td>"
            q = u = temp = press = re = holdup = flowRegime = '-'
            try:
                x = self.RenderBasicObject('??', xProfs[nSeg], False)
                y = self.RenderBasicObject('??', yProfs[nSeg], False)
                k = self.RenderBasicObject('??', kProfs[nSeg], False)
                if nSeg:
                    length = self.RenderBasicObject('??', lenProfs[nSeg-1], False)
                    if qArr != None: q = '%7.1f' % qunit.ConvertFromSim42(qArr[nSeg-1])
                    if uArr != None: u = '%g' % uunit.ConvertFromSim42(uArr[nSeg-1])
                    if reArr != None: re = '%7.1f' %reArr[nSeg-1]
                    if holArr != None: 
                        try: holdup = '%1.4f' %holArr[nSeg-1]
                        except: holdup = '-'
                    if frArr != None: flowRegime = frArr[nSeg-1]
                if tArr: temp  = '%7.2f' % tunit.ConvertFromSim42(tArr[nSeg])
                if pArr: press  = '%7.2f' % punit.ConvertFromSim42(pArr[nSeg])
                
            except:
                pass

            
            print '<tr><td>%i</td>' % nSeg
            print x
            print y
            print length
            print k
            print '<td align=right>%s</td>' % temp
            print '<td align=right>%s</td>' % press
            print '<td align=right>%s</td>' % q
            print '<td align=right>%s</td>' % u
            print '<td align=right>%s</td>' % re
            print '<td align=right>%s</td>' % holdup
            print '<td align=right>%s</td>' % flowRegime
            print '</tr>'
        print '</table></p>'
        
        #profileLinkText = self.msg('WebAddProfile')
        #print '''<a href="javascript:OpenTowerProfileWindow('%s',%d);">%s</a>''' % (
            #pipe.GetPath(), self.id, profileLinkText)
        
        
        
        
    def ShowHeatExchanger(self, hx):
        """
        render multisided heat exchanger
        """        
        self.ShowUnitOp(hx)
        print '''
        <script>
        function OpenHXProfileWindow(hxPath, sid) {
            profileWin = window.open('hxprofilereq?sid='+ sid + '&hx=' + hxPath, 'hxprofwindow',
                        'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
            profileWin.focus();
            if( profileWin.opener == null ) {
                profileWin.opener = window;
            }
        }
        
        </script>
        '''
        
        nSegs = hx.GetNumberOfSegments()
        nSides = hx.GetNumberOfSides()
        counterCVec = zeros(nSides, Int)
        isColdVec = zeros(nSides, Int)
        fntClrVec = [None] * nSides
        
        useHT = []
        for hTransfer in hx._hTransferList:
            if hTransfer.GetPort(UA_PORT).GetValue():
                useHT.append(hTransfer)
        nHT = len(useHT)
        
        print '<a name="segsview"></a><p><table frame="box" rules="rows,cols">'
        units = self.s42cmd.units
        tunit = units.GetCurrentUnit(PropTypes[T_VAR].unitType)
        punit = units.GetCurrentUnit(PropTypes[P_VAR].unitType)
        qunit = units.GetCurrentUnit(PropTypes[ENERGY_VAR].unitType)
        uaunit = units.GetCurrentUnit(PropTypes[UA_VAR].unitType)
        dtunit = units.GetCurrentUnit(PropTypes[DELTAT_VAR].unitType)
        
        # segments headers
        print '''<tr><th align=center>%s</th>
                     <th align=center colspan=%i>%s (%s)</th>
                     <th align=center colspan=%i>%s (%s)</th>
                     <th align=center colspan=%i>%s (%s)</th>''' % (self.msg('WebSegmentNumber'), 
                                                                    nSides, self.msg(T_VAR), tunit.name, 
                                                                    nSides, self.msg(P_VAR), punit.name,
                                                                    nSides, self.msg('%sAcum' %ENERGY_VAR), qunit.name)
        if useHT:
            print ''' <th align=center colspan=%i>%s (%s)</th>
                      <th align=center colspan=%i>%s (%s)</th>''' % (nHT, self.msg('UA'), uaunit.name,
                                                                     nHT, self.msg('LMTD'), dtunit.name)
        
        print '</tr>'
        
        
        #Gather all the info of the sides in a "convenient" format
        sides = hx._sides
        sideInfo = [None] * nSides
        tIdx, pIdx, qIdx, qPerSegIdx = range(4)
        
        for nSide in range(nSides):
            counterCVec[nSide] = sides[nSide].GetIsCounterCurrent()
            sideInfo[nSide] = [sides[nSide].GetObject(T_VAR), 
                               sides[nSide].GetObject(P_VAR),
                               sides[nSide].GetObject('%sAcum' %ENERGY_VAR),
                               sides[nSide].GetObject('%s' %ENERGY_VAR)]
            if sideInfo[nSide][qIdx]:
                try:
                    if not counterCVec[nSide]:
                        if sides[nSide].HArray[0] < sides[nSide].HArray[-1]:
                            isColdVec[nSide] = 1
                            fntClrVec[nSide] = 'darkblue'
                        else:
                            fntClrVec[nSide] = 'red'    
                        #if sideInfo[nSide][qPerSegIdx][1] > 0.0:
                            #isColdVec[nSide] = 1
                            #fntClrVec[nSide] = 'darkblue'
                        #else:
                            #fntClrVec[nSide] = 'red'
                    else:
                        if sides[nSide].HArray[0] > sides[nSide].HArray[-1]:
                            isColdVec[nSide] = 1
                            fntClrVec[nSide] = 'darkblue'
                        else:
                            fntClrVec[nSide] = 'red'   
                        #if sideInfo[nSide][qPerSegIdx][0] > 0.0:
                            #isColdVec[nSide] = 1
                            #fntClrVec[nSide] = 'darkblue'
                        #else:
                            #fntClrVec[nSide] = 'red'
                except:
                    fntClrVec[nSide] = 'red' 
                    pass

        #Gather all the info of the heat transfers in a "convenient" format
        htInfo = [None] * nHT
        uaIdx, lmtdIdx = range(2)
        for ht in range(nHT):
            htInfo[ht] = [useHT[ht].GetObject('ua'),
                          useHT[ht].GetObject('lmtd')]
                                  
        
        # sides
        print '<tr><td align=center>&nbsp;</td>'
        #Loop for T, P, EnergyAcum, UA and LMTD
        for cnt in range(3):
            for nSide in range(nSides):
                print '<td align=center><font color="%s">%s %i</font></td>' %(fntClrVec[nSide], self.msg('WebSide'), nSide)
        for cnt in range(2):
            for i in range(nHT):
                s1 = hx.GetIndexOfSide(useHT[i]._side1)
                s2 = hx.GetIndexOfSide(useHT[i]._side2)
                print '<td align=center>%s%i <--> %s%i</td>' %('S', s1, 'S', s2)
        print '</tr>'
            
        #Label if counter current
        print '<tr><td align=center>&nbsp;</td>'
        #Loop for T, P, EnergyAcum, UA and LMTD
        for cnt in range(3):
            for nSide in range(nSides):
                if counterCVec[nSide]:
                    print '<td align=center><font color="%s"><--</font></td>'%(fntClrVec[nSide],)
                else:
                    print '<td align=center><font color="%s">--></font></td>'%(fntClrVec[nSide],)
        for cnt in range(2):
            for i in range(nHT):
                print '<td align=center>&nbsp;</td>'
        print '</tr>'
                    
        for nSeg in range(nSegs+1):
            print '<tr><td align=center>%i</td>' %nSeg
            
            #T
            for nSide in range(nSides):
                info = sideInfo[nSide]
                if info[tIdx]:
                    try: temp = '%7.2f' % tunit.ConvertFromSim42(info[tIdx][nSeg])
                    except: temp = '-'
                else:
                    temp = '-'
                print '<td align=right>%s</td>' % (temp)
            
            #P
            for nSide in range(nSides):
                info = sideInfo[nSide]
                if info[pIdx]:
                    try: pres = '%7.2f' % punit.ConvertFromSim42(info[pIdx][nSeg])
                    except: pres = '-'
                else:
                    pres = '-'
                print '<td align=right>%s</td>' % (pres)    

            #Q
            for nSide in range(nSides):
                info = sideInfo[nSide]
                if info[qIdx]:
                    try: ene = '%7.2f' % qunit.ConvertFromSim42(info[qIdx][nSeg])
                    except: ene = '-'
                else:
                    ene = '-'
                print '<td align=right>%s</td>' % ( ene)
                
            #UA
            for ht in range(nHT):
                if nSeg:
                    info = htInfo[ht]
                    if info[uaIdx]:
                        try: ua = '%7.2f' % uaunit.ConvertFromSim42(info[uaIdx][nSeg-1])
                        except: ua = '-'
                    else:
                        ua = '-'
                else:
                    ua = '-'
                print '<td align=right>%s</td>' % ua
            
            #LMTD
            for ht in range(nHT):
                if nSeg:
                    info = htInfo[ht]
                    if info[lmtdIdx]:
                        try: lmtd = '%7.2f' % dtunit.ConvertFromSim42(info[lmtdIdx][nSeg-1])
                        except: lmtd = '-'
                    else:
                        lmtd = '-'
                else:
                    lmtd = '-'
                print '<td align=right>%s</td>' % lmtd 
            print '</tr>'
                
        print '</table></p>'
        
        hComp = hx.GetObject('HotComposite')
        cComp = hx.GetObject('ColdComposite')
        if nSides > 2 and hComp != None and cComp != None and hComp.T and hComp.Q and cComp.T and cComp.Q:
            print '<a name="compsideview"></a><p><table frame="box" rules="rows,cols">'
            # segments headers
            print '''<tr><th align=center>%s</th>
                         <th align=center colspan=%i>%s (%s)</th>
                         <th align=center colspan=%i>%s (%s)</th>''' % (self.msg('WebSegmentNumber'), 
                                                                        2, self.msg(T_VAR), tunit.name,
                                                                        2, self.msg('%sAcum' %ENERGY_VAR), qunit.name)
            print '</tr>'
            
            #Loop for Side headers in T, EnergyAcum
            print '<tr><td align=center>&nbsp;</td>'
            print '<td align=center><font color="%s">%s</font></td>' %('red', 'HotComposite')
            print '<td align=center><font color="%s">%s</font></td>' %('darkblue', 'ColdComposite')
            print '<td align=center><font color="%s">%s</font></td>' %('red', 'HotComposite')
            print '<td align=center><font color="%s">%s</font></td>' %('darkblue', 'ColdComposite')
            print '</tr>'
        
            hT, cT = hComp.T, cComp.T
            hQ, cQ = hComp.Q, cComp.Q
            length = max(len(hComp.T), len(cComp.T))
            for nSeg in range(length):
                print '<tr><td align=center>%i</td>' %nSeg
                
                #T
                try: temp0 = '%7.2f' % tunit.ConvertFromSim42(hT[nSeg])
                except: temp0 = '-'
                try: temp1 = '%7.2f' % tunit.ConvertFromSim42(cT[nSeg])
                except: temp1 = '-'
                print '<td align=right>%s</td><td align=right>%s</td>' % (temp0, temp1)
                
                #Q
                try: ene0 = '%7.2f' % qunit.ConvertFromSim42(hQ[nSeg])
                except: ene0 = '-'
                try: ene1 = '%7.2f' % qunit.ConvertFromSim42(cQ[nSeg])
                except: ene1 = '-'
                print '<td align=right>%s</td><td align=right>%s</td>' % (ene0, ene1)
                    
                print '</tr>'
                    
            print '</table></p>'
            
            
            
        print '<a name="profiles"></a>'
        curves = hx.GetParameterValue('Profiles')
        if curves:
            def makeCurves(curve):
                try:
                    #curve = curve.split()
                    
                    unitLst = []
                    for unitName in curve:
                        if unitName == 'EnergyAcum':
                            unitName = ENERGY_VAR
                        try:
                            tempUnitName = unitName.split('_', 1)
                            if len(tempUnitName) == 2:
                                if tempUnitName[0] == Tower.TOWER_VAP_PHASE:
                                    unitName = tempUnitName[1]
                                elif tempUnitName[0] == Tower.TOWER_LIQ_PHASE:
                                    unitName = tempUnitName[1]
                            unit = units.GetCurrentUnit(PropTypes[unitName].unitType)
                        except:
                            unit = None
                        unitLst.append(unit)
                    return [curve, unitLst, counterCVec, isColdVec]
                except:
                    return [[], [], counterCVec, isColdVec]
                
            propLst = curves.strip().split()
            curves = []
            cnt = 0
            while cnt < len(propLst)-1:
                curves.append([propLst[cnt],propLst[cnt+1]])
                cnt += 2
                              
            curves = map(makeCurves, curves)
            curveVals = {}
            
            print '<hr><h3>%s</h3>' % msg('WebTowerProfiles')
            print '<p><table frame="box" rules="rows,cols">'
    
            # stage headers
            propLst = []
            unitLst = []
            valsLst = []
            print '<tr><th align=center>%s</th>' % self.msg('WebSegmentNumber')
            for (props, propUnits, dummy, dummy2) in curves:
                for i in range(len(props)):
                    if not props[i] in propLst:
                        propName = props[i]
                        unit = propUnits[i]
                        propLst.append(propName)
                        unitLst.append(unit)
                        unitName = ''
                        if unit:
                            unitName = propUnits[i].name
                        print '<th align=center colspan=%i>%s (%s)</th>' % (nSides, props[i], unitName)
                        
                        #Use this loop to load the values
                        for nSide in range(nSides):                            
                            try:
                                values = Numeric.array(hx._sides[nSide].GetObject(propName))
                                values = Numeric.reshape(values, (values.shape[0],))
                                valsLst.append(values)
                                curveVals[(nSide, propName)] = values
                            except:
                                valsLst.append(None)
                                curveVals[(nSide, propName)] = values
                        
            print '</tr>'
            
            # sides
            print '<tr><td align=center>&nbsp;</td>'
            for propName in propLst:
                for nSide in range(nSides):
                    print '<td align=center>%s %i</td>' %(self.msg('WebSide'), nSide)
            print '</tr>'
                
            #Label if counter current
            print '<tr><td align=center>&nbsp;</td>'
            for propName in propLst:
                for nSide in range(nSides):
                    if hx._sides[nSide].GetIsCounterCurrent():
                        print '<td align=center><--</td>'
                    else:
                        print '<td align=center>--></td>'
            print '</tr>'
            
            
            #Loop to write the values in a table
            #Values come out of this loop with the current units
            for nSeg in range(nSegs+1):
                print '<tr><td align=center>%i</td>' %nSeg
                idxVals = 0
                for idxProp in range(len(propLst)):
                    for nSide in range(nSides):
                        try:
                            value = '-'
                            values = valsLst[idxVals]
                            idxVals += 1
                            if values != None:
                                value = values[nSeg]
                                if unitLst[idxProp]:
                                    value = unitLst[idxProp].ConvertFromSim42(value)
                                    values[nSeg] = value
                                value = '%f' %value
                        except:
                            value = '-'
                        print '<td align=center>%s</td>' %value
                print '</tr>'
            
            print '</table></p>'
            
            self.curves = curves
            self.curveVals = curveVals
            doPlots = True
            for vals in curveVals.values():
                if vals == None or None in vals:
                    doPlots = False
                    
            if doPlots and graph42:
                for idx in range(len(curves)):
                    print '<p><img src="hxplot?sid=%d&curve=%s" border=1 align=center></p>' % (
                           self.id, idx)
                        
                        
            profileLinkText = self.msg('WebChangeTwrProfile')
        else:
            profileLinkText = self.msg('WebAddProfile')

        print '''<a href="javascript:OpenHXProfileWindow('%s',%d);">%s</a>''' % (
            hx.GetPath(), self.id, profileLinkText)
            
        
    def ShowTower(self, tower):
        """
        render Tower op
        """
        
        self.ShowUnitOp(tower)
        print '''
        <script>
        function OpenTowerProfileWindow(twrPath, sid) {
            profileWin = window.open('twrprofilereq?sid='+ sid + '&tower=' + twrPath, 'twrprofwindow',
                        'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
            profileWin.focus();
            if( profileWin.opener == null ) {
                profileWin.opener = window;
            }
        }
        
        </script>
        '''

        nStages = tower.numStages
        print '<a name="stageview"></a><p><table frame="box" rules="rows,cols">'
        units = self.s42cmd.units
        tunit = units.GetCurrentUnit(PropTypes[T_VAR].unitType)
        punit = units.GetCurrentUnit(PropTypes[P_VAR].unitType)
        munit = units.GetCurrentUnit(PropTypes[MOLEFLOW_VAR].unitType)
        qunit = units.GetCurrentUnit(PropTypes[ENERGY_VAR].unitType)

        # stage headers
        print '<tr><th align=center>%s</th><th align=center>%s</th><th colspan=2>%s</th>' % (
                self.msg('WebStageNumber'), self.msg(T_VAR), self.msg(P_VAR))
                
        print '<th align=center>%s</th><th align=center>%s</th><th align=center>%s</th>' % (
            self.msg('WebTowerLiqFlow'), self.msg('WebTowerVapFlow'), self.msg('WebTowerFeedDraws'))
        print '<th align=center>%s</th>' % self.msg('WebTowerQFeeds')
        print '<th align=center>%s</th>' % self.msg('WebTowerIntConns')
        print '</tr>'
        # units
        print '<tr><td align=right>&nbsp;</td><td align=right>%s</td><td align=right colspan=2>%s</td>' % (
            tunit.name, punit.name)
        print '<td align=right>%s</td><td align=right>%s</td>' % (munit.name, munit.name)
        print '<td align=right>%s</td>' % munit.name
        print '<td align=right>%s</td>' % qunit.name
        print '<td align=right>&nbsp;</td>'
        print '</tr>'

        nRequiredSpecs = 0
        nUserSpecs = 0
        GetConnString = self.GetConnString
        pProps = tower.pProfile.GetProperties()
        T = tower.GetObject(T_VAR)
        for nStage in range(nStages):
            stage = tower.stages[nStage]
            try:
                temp  = '%7.1f' % tunit.ConvertFromSim42(T[nStage])
                
                #press = '%7.1f' % punit.ConvertFromSim42(tower.P[nStage])
                press = self.RenderBasicObject('??', pProps[nStage], False)
                lFlow = '%8.1f' % munit.ConvertFromSim42(tower.L[nStage])
                vFlow = '%8.1f' % munit.ConvertFromSim42(tower.V[nStage])
            except:
                temp = lFlow = vFlow = '-'
                press = "<td align=right>-</td><td align=right>-</td>"

            dFlow = ''
            connString = ''
            try:
                for draw in stage.liqDraws.values():
                    spec = self.SpecIndicator(draw)
                    if isinstance(draw, Tower.PumpAround):
                        dFlow += self.ShowDrawFlow('LP%s' % spec, munit, draw)
                        conn = draw.port.GetConnection()
                        if conn and conn.GetParent() is tower:
                            connString += GetConnString('LP', conn)
                    else:
                        dFlow += self.ShowDrawFlow('L%s' % spec, munit, draw)
                        conn = draw.port.GetConnection()
                        if conn and conn.GetParent() is tower:
                            connString += GetConnString('L', conn)

                for draw in stage.vapDraws.values():
                    spec = self.SpecIndicator(draw)
                    if isinstance(draw, Tower.PumpAround):
                        dFlow += self.ShowDrawFlow('VP%s' % spec, munit, draw)
                        conn = draw.port.GetConnection()
                        if conn and conn.GetParent() is tower:
                            connString += GetConnString('VP', conn)
                    else:
                        dFlow += self.ShowDrawFlow('V%s' % spec, munit, draw)
                        conn = draw.port.GetConnection()
                        if conn and conn.GetParent() is tower:
                            connString += GetConnString('V', conn)
                for draw in stage.liqClones.values():
                    spec = self.SpecIndicator(draw)
                    dFlow += self.ShowDrawFlow('LC%s' % spec, munit, draw)
                    conn = draw.port.GetConnection()
                    if conn and conn.GetParent() is tower:
                        connString += GetConnString('LC', conn)          
                for draw in stage.vapClones.values():
                    spec = self.SpecIndicator(draw)
                    dFlow += self.ShowDrawFlow('CV%s' % spec, munit, draw)
                    conn = draw.port.GetConnection()
                    if conn and conn.GetParent() is tower:
                        connString += GetConnString('VC', conn)
                if stage.waterDraw:
                    dFlow += self.ShowDrawFlow('W', munit, stage.waterDraw)
                    conn = stage.waterDraw.port.GetConnection()
                    if conn and conn.GetParent() is tower:
                        connString += GetConnString('W', conn)
                for feed in stage.feeds.values():
                    if isinstance(feed.pumpFromDraw, Tower.PumpAround):
                        dFlow += self.MakeCdRef('FP', feed)
                    else:
                        dFlow += self.MakeCdRef('F', feed)
                    value =  munit.ConvertFromSim42(feed.port.GetPropValue(MOLEFLOW_VAR))
                    if value == None:
                        sValue = '---'
                    else:
                        sValue = '%7.1f' % value
                    dFlow += self.MakeCdRef(sValue, feed.port) + '<br>'
                    conn = feed.port.GetConnection()
                    if conn and conn.GetParent() is tower:
                        if isinstance(feed.pumpFromDraw, Tower.PumpAround):
                            connString += GetConnString('FP', conn)
                        else:
                            connString += GetConnString('F', conn)
                if dFlow != '':
                    dFlow = dFlow[:-4]  # remove last <br>
                else:
                    dFlow = '&nbsp;'
                
            except:
                dFlow = '???'
            
            qFlow = ''
            for qfeed in stage.qfeeds.values():
                if qfeed.WasCalculated():
                    indicator = 'Q'
                else:
                    indicator = 'Q*'
                qFlow += self.ShowQFlow(indicator, qunit, qfeed)
                conn = qfeed.port.GetConnection()
                if conn and conn.GetParent() is tower:
                    connString += self.GetConnString('Q', conn)
            if qFlow != '':
                qFlow = qFlow[:-4]  # remove last <br>
            else:
                qFlow = '&nbsp;'
            
            spec = self.SpecIndicator(stage)
            if stage.type == Tower.TOP_STAGE and nStage:
                print '<tr><td colspan=8 align="center">%s</td></tr>' %self.msg('WebTowerNewSection')
            print '<tr><td>%s</td>' % self.MakeCdRef('%d%s' % (nStage, spec), stage)
            #print '<td align=right>%s</td><td align=right>%s</td>' % (temp, press)
            print '<td align=right>%s</td>' % temp
            print press
            print '<td align=right>%s</td><td align=right>%s</td>' % (lFlow, vFlow)
            print '<td align=right>%s</td><td align=right>%s</td>' % (dFlow, qFlow)
            print '<td align=center>%s</td>' %connString

            nRequiredSpecs += stage.NumberOfSpecsRequired()
            nUserSpecs += stage.NumberOfUserSpecs()
            print '</tr>'
        print '</table></p>'
        print '<a name="degfreedom"></a><p><table frame="box">'
        print '<tr><td>%s</td><td>%d</td></tr>' % (self.msg('WebTowerReqSpecs'), nRequiredSpecs)
        print '<tr><td>%s</td><td>%d</td></tr>' % (self.msg('WebTowerUserSpecs'), nUserSpecs)
        print '</table></p>'
        
        print '<a name="profiles"></a>'
        curves = tower.GetParameterValue('Profiles')
        if curves:
            def makeCurves(curve):
                try:
                    split = curve.split('_')
                    if len(split) > 1 and split[0] in (Tower.TOWER_LIQ_PHASE, Tower.TOWER_VAP_PHASE):
                        unitName = split[1]
                    else:
                        unitName = curve.split('.')[0]
                    if unitName in ('f','l','L','v','V','paLTerm','paVTerm'):
                        unitName = MOLEFLOW_VAR
                    return [curve, units.GetCurrentUnit(PropTypes[unitName].unitType)]
                except:
                    return [curve, None]
            curves = map(makeCurves, curves.split())
            
            print '<hr><h3>%s</h3>' % msg('WebTowerProfiles')
            print '<p><table frame="box" rules="rows,cols">'
    
            # stage headers
            print '<tr><th align=center>%s</th>' % self.msg('WebStageNumber')
            for (name, curveUnit) in curves:
                print '<th align=center>%s</th>' % name 
            print '</tr>'
            # units
            print '<tr><td align=right>&nbsp;</td>'
            for curve in curves:
                (name, curveUnit) = curve
                if curveUnit:
                    print '<td align=right>%s</td>' % curveUnit.name
                else:
                    print '<td>&nbsp;</td>'
                    
                try:
                    values = Numeric.array(self.s42cmd.GetObject(tower, name))
                    values = Numeric.reshape(values, (values.shape[0],))
                    curve.append(values)
                except:
                    curve.append(None)
                    
            print '</tr>'
            for nStage in range(nStages):
                stage = tower.stages[nStage]
                print '<tr><td>%s</td>' % self.MakeCdRef('%d' % nStage, stage)
                for name, curveUnit, values in curves:
                    try:
                        value = values[nStage]
                        if isinstance(value, Numeric.ArrayType):
                            value = value[0]
                        if curveUnit:
                            value = curveUnit.ConvertFromSim42(value)
                            values[nStage] = value
                        value = '%f' % value
                    except:
                        value = '-'
                    print '<td align=right>%s</td>' % value
            print '</tr>'
            print '</table></p>'
            
            self.curves = curves
            if graph42:
                for curve in curves:
                    if curve[2]:
                        print '<p><img src="twrplot?sid=%d&curve=%s" border=1 align=center></p>' % (
                           self.id, curve[0])
                           
            profileLinkText = self.msg('WebChangeTwrProfile')
        else:
            profileLinkText = self.msg('WebAddTwrProfile')

        print '''<a href="javascript:OpenTowerProfileWindow('%s',%d);">%s</a>''' % (
            tower.GetPath(), self.id, profileLinkText)

    def ShowTowerStage(self, stage):
        """
        render Tower stage
        """
        self.ClearMenus()
        print '''
        <script>
        var menu1 = parent.command.document.menuform.createmenu1;
        var menu2 = parent.command.document.menuform.createmenu2;
        var menu3 = parent.command.document.menuform.createmenu3;
        '''
        print "menu1.options[0] = new Option('%s'); " % self.msg('WebAddStageFeedDraw')
        print '''
        var i = 1;
        menu1.options[i++] = new Option('%s','%s')''' % (self.msg('WebAddFeed'),'Tower.Feed()')
        print "menu1.options[i++] = new Option('%s', '%s')" % (self.msg('WebAddLiquidDraw'), 'Tower.LiquidDraw()')
        print "menu1.options[i++] = new Option('%s', '%s')" % (self.msg('WebAddVapourDraw'), 'Tower.VapourDraw()')
        print "menu1.options[i++] = new Option('%s','%s')"      % (self.msg('WebAddEnergyFeed'), 'Tower.EnergyFeed(1)')
        print "menu1.options[i++] = new Option('%s','%s')"      % (self.msg('WebAddEnergyDraw'), 'Tower.EnergyFeed(0)')
        print "menu1.options[i++] = new Option('%s','%s')"      % (self.msg('WebInternalLiquid'), 'Tower.InternalLiquidClone()')
        print "menu1.options[i++] = new Option('%s','%s')"      % (self.msg('WebInternalVapour'), 'Tower.InternalVapourClone()')
        print "menu1.options[i++] = new Option('%s','%s')"      % (self.msg('WebWaterDraw'), 'Tower.WaterDraw()')

        print "menu2.options[0] = new Option('%s'); " % self.msg('WebAddSpecEst')
        print '''
        var i = 1;
        menu2.options[i++] = new Option('%s','%s')''' % (self.msg('WebAddRefluxSpec'),
                                                'Tower.StageSpecification("%s")' % Tower.REFLUX)
        print "menu2.options[i++] = new Option('%s', '%s')" % (self.msg('WebAddReboilSpec'),
                                                'Tower.StageSpecification("%s")' % Tower.REBOIL)
        print "menu2.options[i++] = new Option('%s', '%s')" % (self.msg('WebAddTempSpec'),
                                                'Tower.StageSpecification("%s")' % T_VAR)
        print "menu2.options[i++] = new Option('%s', '%s')" % (self.msg('WebAddRefluxEst'),
                                                'Tower.Estimate("%s")' % Tower.REFLUX)
        print "menu2.options[i++] = new Option('%s', '%s')" % (self.msg('WebAddTempEst'),
                                                'Tower.Estimate("%s")' % T_VAR)

        print "menu3.options[0] = new Option('%s'); " % self.msg('WebAddExtraObjects')
        if not stage.number:
            print '''
            var i = 1;
            menu3.options[i++] = new Option('%s','%s')''' % (self.msg('WebAddDegSubCool'),
                                                    'Tower.DegSubCooling()')
        
        print '''
        function AddStages(form) {
            try {
                var cmd = parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = '. + ' + Number(form.nstages.value);
                parent.command.document.command.submit();
            }
            catch (e) {}
            return false;
        }
        
        function RemoveStages(form) {
            try {
                var cmd = parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = '. - ' + Number(form.nstages.value);
                parent.command.document.command.submit();
            }
            catch (e) {}
            return false;
        }
        
        function AddPumpAround(form) {
            var cmd = parent.command.document.command.cmd;
            var cmdStr = form.paname.value + ' = Tower.';
            cmdStr += form.PAType.value + 'PumpAround(' + form.destStage.value;
            cmdStr += ',' + form.PAHeating.value + ')';
            cmd.value = cmdStr;
            cmd.focus();
            parent.command.document.command.submit();
            return false;
        }
        '''
        print '</script>'

        units = self.s42cmd.units
        tunit = units.GetCurrentUnit(PropTypes[T_VAR].unitType)
        punit = units.GetCurrentUnit(PropTypes[P_VAR].unitType)
        munit = units.GetCurrentUnit(PropTypes[MOLEFLOW_VAR].unitType)
        qunit = units.GetCurrentUnit(PropTypes[ENERGY_VAR].unitType)
        dtunits = units.GetCurrentUnit(PropTypes[DELTAT_VAR].unitType)
        
        try:
            tower = stage.tower
            T = tower.GetObject(T_VAR)
            temp  = '%7.1f' % tunit.ConvertFromSim42(T[stage.number])
            press = '%7.1f' % punit.ConvertFromSim42(tower.P[stage.number])
            lFlow = '%8.1f' % munit.ConvertFromSim42(tower.L[stage.number])
            vFlow = '%8.1f' % munit.ConvertFromSim42(tower.V[stage.number])
        except:
            temp = press = lFlow = vFlow = '-'

        print '<p><table frame="box" rules="rows">'
        print '<tr><td>%s</td><td>%d</td></tr>' % (self.msg('WebStageNumber'), stage.number)
        print '<tr><td>%s</td><td>%s %s</td></tr>' % (self.msg(T_VAR), temp, tunit.name) 
        print '<tr><td>%s</td><td>%s %s</td></tr>' % (self.msg(P_VAR), press, punit.name) 
        print '<tr><td>%s</td><td>%s %s</td></tr>' % (self.msg('WebTowerLiqFlow'), lFlow, munit.name) 
        print '<tr><td>%s</td><td>%s %s</td></tr>' % (self.msg('WebTowerVapFlow'), vFlow, munit.name)

        
        dFlow = ''
        try:
            for draw in stage.liqDraws.values():
                spec = self.SpecIndicator(draw)
                if isinstance(draw, Tower.PumpAround):
                    dFlow += self.ShowDrawFlow('LP%s' % spec, munit, draw)
                else:
                    dFlow += self.ShowDrawFlow('L%s' % spec, munit, draw)
                
            for draw in stage.vapDraws.values():
                spec = self.SpecIndicator(draw)
                if isinstance(draw, Tower.PumpAround):
                    dFlow += self.ShowDrawFlow('VP%s' % spec, munit, draw)
                else:
                    dFlow += self.ShowDrawFlow('V%s' % spec, munit, draw)
                                
            for draw in stage.liqClones.values():
                spec = self.SpecIndicator(draw)
                dFlow += self.ShowDrawFlow('LC%s' % spec, munit, draw)
                                
            for draw in stage.vapClones.values():
                spec = self.SpecIndicator(draw)
                dFlow += self.ShowDrawFlow('CV%s' % spec, munit, draw)
                                
            if stage.waterDraw:
                dFlow += self.ShowDrawFlow('W', munit, stage.waterDraw)

            for feed in stage.feeds.values():
                if isinstance(feed.pumpFromDraw, Tower.PumpAround):
                    dFlow += self.MakeCdRef('FP', feed)
                else:
                    dFlow += self.MakeCdRef('F', feed)
                value =  munit.ConvertFromSim42(feed.port.GetPropValue(MOLEFLOW_VAR))
                if value == None:
                    sValue = '---'
                else:
                    sValue = '%7.1f' % value
                dFlow += self.MakeCdRef(sValue, feed.port) + '<br>'
                    
            
            if dFlow != '':
                dFlow = dFlow[:-4]  # remove last <br>
            else:
                dFlow = '&nbsp;'
            
        except:
            dFlow = '???'
        
        qFlow = ''
        for qfeed in stage.qfeeds.values():
            value =  munit.ConvertFromSim42(qfeed.port.GetPropValue(ENERGY_VAR))
            if value == None:
                sValue = '---'
            else:
                if not qfeed.incoming:
                    value = -value
                
                sValue = '%10.0f' % value
            qFlow += self.MakeCdRef(sValue, qfeed.port) + '<br>'
            
        if qFlow != '':
            qFlow = qFlow[:-4]  # remove last <br>
        else:
            qFlow = '&nbsp;'

        print '<tr><td>%s</td><td>%s</td></tr>' % (self.msg('WebTowerFeedDraws'), dFlow)
        print '<tr><td>%s</td><td>%s</td></tr>' % (self.msg('WebTowerQFeeds'), qFlow)

        if stage.IsSubCooled():
            subCoolDT = stage.subCool.port.GetValue()
            if subCoolDT != None:
                subCoolDT = dtunits.ConvertFromSim42(subCoolDT)
                subCoolDT = '%7.3f' % subCoolDT
            else:
                subCoolDT = '---'
            subCoolDT = self.MakeCdRef(subCoolDT, stage.subCool)
            print '<tr><td>%s</td><td>%s</td></tr>' % (self.msg('WebTowerSubCool'), subCoolDT)
        
        print '</table></p>'

        if len(stage.estimates):
            print '<p><table frame="box" rules="rows">'
            print '<tr><th>%s</th><th>%s</th><th>%s</th></tr>' % (self.msg('WebEstName'),
                    self.msg('WebType'), self.msg('WebValue'))
                    
            for estName in stage.estimates:
                estimate = stage.estimates[estName]
                estType = self.msg(estimate.type)
                value = estimate.port.GetValue()
                if value == None:
                    estValue = '---'
                else:
                    try:
                        unit = units.GetCurrentUnit(PropTypes[estimate.type].unitType)
                        estValue = '%7.1f %s' % (unit.ConvertFromSim42(value), unit.name)
                    except:
                        estValue = '%f' % value
                print '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    self.MakeCdRef(estName, estimate), estType, estValue)
            print '</table></p>'
        
        if len(stage.specs):
            print '<p><table frame="box" rules="rows">'
            print '<tr><th>%s</th><th>%s</th><th>%s</th></tr>' % (self.msg('WebSpecName'),
                    self.msg('WebType'), self.msg('WebValue'))
                    
            for specName in stage.specs:
                spec = stage.specs[specName]
                specType = self.msg(spec.type)
                value = spec.port.GetValue()
                if value == None:
                    specValue = '---'
                else:
                    try:
                        unit = units.GetCurrentUnit(PropTypes[specType].unitType)
                        specValue = '%7.1f %s' % (unit.ConvertFromSim42(value), unit.name)
                    except:
                        specValue = '%f' % value
                print '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    self.MakeCdRef(specName, stage.specs[specName]), specType, specValue)
            print '</table></p>'
            
        print '<form onSubmit="return AddStages(this);">'
        print '<p><table frame="box" rules="" width=250>'
        print '<tr><td>%s</td></tr>' % self.msg('WebAddStages')
        print '<tr><td align=center><input type=text name="nstages" size=10></td></tr>'
        print '<tr><td align=center><input type=submit value="%s"></td></tr>' % self.msg('WebAdd')
        print '</table></form>'
        
        print '<form onSubmit="return RemoveStages(this);">'
        print '<p><table frame="box" rules="" width=250>'
        print '<tr><td>%s</td></tr>' % self.msg('WebRemoveStages')
        print '<tr><td align=center><input type=text name="nstages" size=10></td></tr>'
        print '<tr><td align=center><input type=submit value="%s"></td></tr>' % self.msg('WebRemove')
        print '</table></form>'        

        print '<form onSubmit="return AddPumpAround(this);">'
        print '<p><table frame="box" rules="" width=400>'
        print '<tr><td colspan=2 align=center><b>%s</b></td></tr>' % self.msg('WebAddPumpAround')

        print '<tr><td>%s</td><td><input type="text" name="paname" value="" size=20></td></tr>' % \
              self.msg('WebPAName')

        print '<tr><td>%s</td><td><input type="text" name="destStage" value="" size=20></td></tr>' % \
              self.msg('WebPADestinationStage')

        print '<tr><td>%s</td>' % self.msg('WebPAType')
        print '<td><select name="PAType">'
        print '<option value="Liquid">%s</option>' % self.msg('WebLiquid')
        print '<option value="Vapour">%s</option>' % self.msg('WebVapour')
        print '</select></td></tr>'

        print '<tr><td>%s</td><td><select name="PAHeating">' % self.msg('WebPAQType')
        print '<option value="0">%s</option>' % self.msg('WebPAWithCooling')
        print '<option value="1">%s</option></td><tr>' % self.msg('WebPAWithHeating')

        print '<tr><td colspan=2 align=center><input type="submit" value="%s"></td></tr>' % self.msg('WebEnter')
        print '</tr></table></form>'
        
        
    def ShowTowerDraw(self, draw):
        """
        render tower draw
        """
        path = draw.GetPath()
        print '<p><table frame="box" rules=""><tr><td>'
        print '<b>' + self.msg('WebDescription') + '</b>'
        print '</td></tr>'
        
        
        if isinstance(draw, Tower.PumpAround):
            print '<tr><td>' + self.msg('WebPAName') + '</td>'
            prompt = '%s.NewName = ' % path
            print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, draw.name)
            
            print '<tr><td>' + self.msg('WebStageNumber') + '</td>'
            prompt = '%s.ParentStage = ' % path
            print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, draw.stage.number)          
                      
            print '<tr><td>' + self.msg('WebPADestinationStage') + '</td>'
            prompt = '%s.ReturnStage = ' % path
            print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, draw.paFeed.stage.number)
        
        
        else:
            print '<tr><td>' + self.msg('WebName') + '</td>'
            prompt = '%s.NewName = ' % path
            print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, draw.name)
            print '<tr><td>' + self.msg('WebStageNumber') + '</td>'
            prompt = '%s.ParentStage = ' % path
            print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, draw.stage.number)
        print '</table></p>'
        
        print '<p><table frame="box" rules=""><tr><td>'
        print '<b>' + self.MakeCdRef(self.msg('WebPort'), draw.port) + '</b>'
        print '</td></tr><tr><td>'
        self.ShowMaterialPort(draw.port, False)
        print '</td></tr></table></p>'
        if not isinstance(draw, Tower.WaterDraw):
            
            #Property specs and estimates in menu1
            print '''
            <script>
            var menu = parent.command.document.menuform.createmenu1;
            menu.menuMethod = undefined;
            var i = 1;
            '''
            print "menu.options[0] = new Option('%s'); " % self.msg('WebPropSpecOrFlowEst')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                          self.msg('WebAddFlowEst'), 'Tower.Estimate("%s")' % MOLEFLOW_VAR)
            
            if isinstance(draw, Tower.PumpAround):
                print "menu.options[i++] = new Option('PA %s', '%s')" % (
                                           self.msg(DELTAT_VAR), 'Tower.PumpAroundDTSpec()')
                print "menu.options[i++] = new Option('PA Return %s', '%s')" % (
                                           self.msg(T_VAR), 'Tower.PumpAroundReturnTSpec()')
                for prop in TWR_PROP_TYPES[1:]:
                    print "menu.options[i++] = new Option('PA Return %s', '%s')" % (
                                               self.msg(prop), 'Tower.PumpAroundReturnPropSpec("%s")' % prop)
            
            for prop in TWR_PROP_TYPES:
                print "menu.options[i++] = new Option('%s', '%s')" % (
                    self.msg(prop), 'Tower.PropertySpec("%s")' % prop)

                    
            #Composition specs in menu 2
            print '''
            menu = parent.command.document.menuform.createmenu2;
            menu.menuMethod = undefined;
            i = 1;
            '''
            print "menu.options[0] = new Option('%s'); " % self.msg('WebDrawCmpSpec')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebMoleFractionSpec'), 'Tower.MoleFractionSpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebMassFractionSpec'), 'Tower.MassFractionSpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebVolFractionSpec'), 'Tower.VolFractionSpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebCmpMoleFlowSpec'), 'Tower.ComponentMoleFlowSpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebCmpMassFlowSpec'), 'Tower.ComponentMassFlowSpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebCmpStdVolFlowSpec'), 'Tower.ComponentStdVolFlowSpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebMoleRecoverySpec'), 'Tower.MoleRecoverySpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebMassRecoverySpec'), 'Tower.MassRecoverySpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebStdVolRecoverySpec'), 'Tower.StdVolRecoverySpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebMoleRatioSpec'), 'Tower.MoleRatioSpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebMassRatioSpec'), 'Tower.MassRatioSpec()')
            print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg('WebStdVolRatioSpec'), 'Tower.StdVolRatioSpec()')
            
            
            #Special property specs in menu 3
            print '''
            menu = parent.command.document.menuform.createmenu3;
            menu.menuMethod = undefined;
            i = 1;
            '''
            print "menu.options[0] = new Option('%s'); " % self.msg('WebSpecialPropSpec')
            for prop in Properties.SPECIAL_PROPS:
                
                print "menu.options[i++] = new Option('%s', '%s')" % (
                                       self.msg(prop), 'Tower.SpecialPropertySpec("%s")' % prop)       
                
            print '</script>'
            
        if len(draw.estimates):
            print '<p><table frame="box" rules="rows">'
            print '<tr><th>%s</th><th>%s</th><th>%s</th></tr>' % (self.msg('WebEstName'),
                    self.msg('WebType'), self.msg('WebValue'))
                    
            for estName in draw.estimates:
                estimate = draw.estimates[estName]
                estType = self.msg(estimate.type)
                value = estimate.port.GetValue()
                if value == None:
                    estValue = '---'
                else:
                    try:
                        unit = units.GetCurrentUnit(PropTypes[estType].unitType)
                        estValue = '%7.1f %s' % (unit.ConvertFromSim42(value), unit.name)
                    except:
                        estValue = '%f' % value
                print '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    self.MakeCdRef(estName, estimate), estType, estValue)
            print '</table></p>'
        
        if len(draw.drawSpecs):
            print '<p><table frame="box" rules="rows">'
            print '<tr><th>%s</th><th>%s</th><th>%s</td></th>' % (self.msg('WebSpecName'),
                    self.msg('WebType'), self.msg('WebValue'))
                    
            for specName in draw.drawSpecs:
                spec = draw.drawSpecs[specName]
                specType = self.msg(spec.varType)
                value = spec.port.GetValue()
                if value == None:
                    specValue = '---'
                else:
                    try:
                        unit = units.GetCurrentUnit(PropTypes[specType].unitType)
                        specValue = '%7.1f %s' % (unit.ConvertFromSim42(value), unit.name)
                    except:
                        specValue = '%f' % value
                print '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    self.MakeCdRef(specName, spec), specType, specValue)
            print '</table></p>'
       
    def ShowTowerFeed(self, feed):
        """
        render tower feed
        """
        path = feed.GetPath()
        print '<p><table frame="box" rules=""><tr><td>'
        print '<b>' + self.msg('WebDescription') + '</b>'
        print '</td></tr>'
        print '<tr><td>' + self.msg('WebName') + '</td>'
        prompt = '%s.NewName = ' % path
        print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, feed.name)
        print '<tr><td>' + self.msg('WebStageNumber') + '</td>'
        prompt = '%s.ParentStage = ' % path
        print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, feed.stage.number)
        print '</table></p>'
        
        print '<p><table frame="box" rules=""><tr><td>'
        print '<b>' + self.MakeCdRef(self.msg('WebPort'), feed.port) + '</b>'
        print '</td></tr><tr><td>'
        self.ShowMaterialPort(feed.port, False)
        self.ClearMenus()
        print '</td></tr></table></p>'

    def ShowTowerQFeed(self, feed):
        """
        render tower feed
        """
        
        path = feed.GetPath()
        print '<p><table frame="box" rules=""><tr><td>'
        print '<b>' + self.msg('WebDescription') + '</b>'
        print '</td></tr>'
        print '<tr><td>' + self.msg('WebName') + '</td>'
        prompt = '%s.NewName = ' % path
        print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, feed.name)
        print '<tr><td>' + self.msg('WebStageNumber') + '</td>'
        prompt = '%s.ParentStage = ' % path
        print '''<td><a href="javascript:SetCommand(window, '%s');">%s</a></td></tr>''' % (prompt, feed.stage.number)
        print '</table></p>'
        
        print '<p><table frame="box" rules=""><tr><td>'
        print '<b>' + self.MakeCdRef(self.msg('WebPort'), feed.port) + '</b>'
        print '</td></tr><tr><td>'
        self.ShowEnergyPort(feed.port)
        self.ClearMenus()
        print '</td></tr></table></p>'

    def ShowTowerFluidVariable(self, var):
        """
        render towr FluidVariable
        """
        print '<p><table frame="box" rules=""><tr><td>'
        print '<b>' + self.MakeCdRef(self.msg('WebPort'), var.port) + '</b>'
        print '</td></tr><tr><td>'
        self.ShowSignalPort(var.port)
        self.ClearMenus()
        print '</td></tr></table></p>'

    def ShowTowerComponentSpec(self, spec):
        """
        render a draw component spec
        """
        selectedCmps = spec.GetObject('Components')
        cmps = spec.stage.tower.GetCompoundNames()

        print '<script>'
        print 'selectedCmps = Array('
        first = 1
        for cmp in selectedCmps:
            if first:
                first = 0
            else:
                print ',',
            print "'%s'" % cmp
        print ');'

        print 'cmps = Array('
        first = 1
        for cmp in cmps:
            if first:
                first = 0
            else:
                print ',',
            print "'%s'" % cmp
        print ');'

        print '''
        function UpdateComponents(form) {
            var cmd = parent.command.document.command.cmd;
            cmd.focus();
            cmd.value = '';
            if( selectedCmps.length > 0 ) {
                // remove existing components
                cmd.value += '. - ';
                for(var i = 0; i < selectedCmps.length; i++) {
                    cmd.value += ' ' + selectedCmps[i];
                }
                cmd.value += ';';
            }

            cmd.value += '. + ';
            for(i = 0; i < cmps.length; i++) {
                var fieldName = 'cmp' + String(i);
                if( form[fieldName].checked) {
                    cmd.value += ' ' + cmps[i];
                }
            }

            parent.command.document.command.submit();
            return false;
        }
        </script>
        '''
        
        print '<p><form name="updatecmpspec" onSubmit="return UpdateComponents(this);">'
        print '<table frame="box" rules="">'
        print '<tr><td>%s</td><td>%s</td></tr>' % (self.msg('WebComponent'), self.msg('WebInclude'))
        for i in range(len(cmps)):
            cmp = cmps[i]
            print '<tr><td>%s</td>' % cmp
            print '<td><input type="checkbox" name="cmp%d"' % i,
            if cmp in selectedCmps:
                print ' checked',
            print '></td></tr>'
        print '<tr><td colspan=2 align="center">'
        print '<input type="submit" name="update" value="Update Components">'
        print '</td></tr></table></form></p>'

        self.ShowTowerFluidVariable(spec)        

    def ShowTowerRatioSpec(self, spec):
        """
        render a draw component ratio spec
        """
        selectedCmps = spec.GetObject('Components')
        if len(selectedCmps):
            slashIndex = selectedCmps.index('/')
            numeratorCmps = selectedCmps[:slashIndex]
            denominatorCmps = selectedCmps[slashIndex+1:]
        else:
            numeratorCmps = []
            denominatorCmps = []
        
        cmps = spec.stage.tower.GetCompoundNames()

        print '<script>'
        print 'selectedCmps = Array('
        first = 1
        for cmp in selectedCmps:
            if first:
                first = 0
            else:
                print ',',
            print "'%s'" % cmp
        print ');'

        print 'cmps = Array('
        first = 1
        for cmp in cmps:
            if first:
                first = 0
            else:
                print ',',
            print "'%s'" % cmp
        print ');'

        print '''
        function UpdateRatioComponents(form) {
            var cmd = parent.command.document.command.cmd;
            cmd.focus();
            cmd.value = '';
            if( selectedCmps.length > 0 ) {
                // remove existing components
                cmd.value += '. - ';
                for(var i = 0; i < selectedCmps.length; i++) {
                    cmd.value += ' ' + selectedCmps[i];
                }
                cmd.value += ' / ;';
            }

            cmd.value += '. + ';
            for(i = 0; i < cmps.length; i++) {
                var fieldName = 'num' + String(i);
                if( form[fieldName].checked) {
                    cmd.value += ' ' + cmps[i];
                }
            }

            cmd.value += ' / ';
            for(i = 0; i < cmps.length; i++) {
                var fieldName = 'den' + String(i);
                if( form[fieldName].checked) {
                    cmd.value += ' ' + cmps[i];
                }
            
            }

            parent.command.document.command.submit();
            return false;
        }
        </script>
        '''
        
        print '<p><form name="updateratiospec" onSubmit="return UpdateRatioComponents(this);">'
        print '<table frame="box" rules="">'
        print '<tr><th>%s</th><th>%s</th><th>%s</th></tr>' % (self.msg('WebNumerator'),
                                self.msg('WebComponent'), self.msg('WebDenominator'))
        for i in range(len(cmps)):
            cmp = cmps[i]
            print '<tr><td><input type="checkbox" name="num%d"' % i,
            if cmp in numeratorCmps:
                print ' checked',
            print '></td>'
            print '<td>%s</td>' % cmp
            print '<td><input type="checkbox" name="den%d"' % i,
            if cmp in denominatorCmps:
                print ' checked',
            print '></td></tr>'
        print '<tr><td colspan=3 align="center">'
        print '<input type="submit" name="update" value="Update Components">'
        print '</td></tr></table></form></p>'

        self.ShowTowerFluidVariable(spec)        

    def ShowTowerPlots(self, curveName):
        self.handler.send_header("Content-type", "image/png")
        self.handler.end_headers()

        "a realistic line plot with actual data"
        
        for curve in self.curves:
            if curve[0] == curveName:
                (name, curveUnit, values) = curve
                break
            
        g = graph42.Graph()
        g.bottom = 400.0
        g.right = 590

        nStage = len(values)
        valueMatrix = Numeric.transpose(Numeric.array([Numeric.arange(nStage), values]))
        g.datasets.append( graph42.Dataset(valueMatrix))

        format0 = graph42.PointPlot()
        format0.lineStyle = graph42.LineStyle(width=2, color=graph42.red, kind=graph42.SOLID)
        format0.symbol = graph42.CircleSymbol
        #ov0 = graph42.Text(self.msg('WebStageNumber'), pos=(0.7,0.92,0), font=graph42.Font(size=9) )
        
        g.formats = [format0]
        #g.overlays = (ov0)

        g.axes[graph42.X].range = [0,nStage-1]
        g.axes[graph42.X].tickMarks[0].spacing = 2
        g.axes[graph42.X].tickMarks[0].labels = "%d"
        g.axes[graph42.X].label.text = '<b>%s</b>' % self.msg('WebStageNumber')

        if curveUnit:
            unitName = curveUnit.name
        else:
            unitName = ''
        
        numberTics = 10
        (minValue, maxValue) = graph42.ScaleValues(values, numberTics)
        g.axes[graph42.Y].range = [minValue, maxValue]
        g.axes[graph42.Y].tickMarks[0].spacing = (maxValue - minValue)/numberTics
        g.axes[graph42.Y].tickMarks[0].labels = "%g"
        g.axes[graph42.Y].label.text = "<b>%s %s</b>" % (curveName, unitName)

        g.title.text = "<b>%s</b>" % curveName
        g.top = g.top + 40
        
        backend = 'piddlePIL'
        canvasname = "Profile"
        module = __import__(backend)
        canvasClass = getattr(module, "PILCanvas")
        size = (600,500)
        canvas = canvasClass(size,canvasname)
        # draw the graph
        g.draw(canvas)

        # do post-test cleanup
        canvas.flush()
        canvas.save(file=self.handler.wfile, format='png')      # save as a PNG file
        
        
    def ShowHXPlots(self, curveIdx):
        self.handler.send_header("Content-type", "image/png")
        self.handler.end_headers()

        
        try:
            #propLst contains the lit of properties to be plotted. The last property should go in the
            #x axis.
            curveIdx = int(curveIdx)
            propLst, unitLst, counterCVec, isColdVec = self.curves[curveIdx]
            nSides = len(counterCVec)
            if len(propLst) < 2:
                return
            yVals = []
            xVals = []
            for propName in propLst[:-1]:
                for nSide in range(nSides):
                    yVals.append(self.curveVals[(nSide, propName)])
            for nSide in range(nSides):
                xVals.append(self.curveVals[(nSide, propLst[-1])])
                             
        except:
            return

            
        g = graph42.Graph()
        g.bottom = 400.0
        g.right = 590
        
        formatLst = []
        nSegs = len(yVals[0])
        #cnt = 0
        for nSide in range(nSides):
        #for y in yVals:
            #cnt = 0
            #for x in xVals:
                #cnt += 1
                #valueMatrix = Numeric.transpose(Numeric.array([x, y]))
                valueMatrix = Numeric.transpose(Numeric.array([xVals[nSide], yVals[nSide]]))
                g.datasets.append( graph42.Dataset(valueMatrix))
                
                format = graph42.PointPlot()
                if isColdVec[nSide]:
                    format.lineStyle = graph42.LineStyle(width=2, color=graph42.blue, kind=graph42.SOLID)
                else:
                    format.lineStyle = graph42.LineStyle(width=2, color=graph42.red, kind=graph42.SOLID)
                format.symbol = graph42.CircleSymbol
                formatLst.append(format)
                
        #valueMatrix = Numeric.transpose(Numeric.array([Numeric.arange(nStage), values]))
        #g.datasets.append( graph42.Dataset(valueMatrix))

        
        ##format0 = graph42.PointPlot()
        ##format0.lineStyle = graph42.LineStyle(width=2, color=graph42.red, kind=graph42.SOLID)
        ##format0.symbol = graph42.CircleSymbol
        #ov0 = graph42.Text(self.msg('WebStageNumber'), pos=(0.7,0.92,0), font=graph42.Font(size=9) )
        
        g.formats = formatLst
        #g.overlays = (ov0)

        unit = unitLst[-1]
        if unit:
            unitName = unit.name
        else:
            unitName = ""
            
        numberTics = 10
        
        #(minValue, maxValue) = graph42.ScaleValues(xVals[0], numberTics)
        
        (minValue, maxValue) = min(xVals[0]), max(xVals[0])
        for nSide in range(1, nSides):
            minValue = min(minValue, min(xVals[nSide]))
            maxValue = max(maxValue, max(xVals[nSide]))
        #Nothing to plot ??
        if minValue == maxValue:
            if maxValue:
                maxValue *= 2.0
            else:
                maxValue = 1.0
        g.axes[graph42.X].range = [minValue, maxValue]
        g.axes[graph42.X].tickMarks[0].spacing = (maxValue - minValue)/numberTics
        g.axes[graph42.X].tickMarks[0].labels = "%g"
        g.axes[graph42.X].label.text = "<b>%s (%s)</b>" % (propLst[-1], unitName)

        unit = unitLst[0]
        if unit:
            unitName = unit.name
        else:
            unitName = ""
        
        numberTics = 10
        #(minValue, maxValue) = graph42.ScaleValues(yVals[0], numberTics)
        (minValue, maxValue) = min(yVals[0]), max(yVals[0])
        for nSide in range(1, nSides):
            minValue = min(minValue, min(yVals[nSide]))
            maxValue = max(maxValue, max(yVals[nSide]))
            
        #Nothing to plot ??
        if minValue == maxValue:
            if maxValue:
                maxValue *= 2.0
            else:
                maxValue = 1.0
                
        g.axes[graph42.Y].range = [minValue, maxValue]
        g.axes[graph42.Y].tickMarks[0].spacing = (maxValue - minValue)/numberTics
        g.axes[graph42.Y].tickMarks[0].labels = "%g"
        g.axes[graph42.Y].label.text = "<b>%s (%s)</b>" % (propLst[0], unitName)

        g.title.text = "<b>%s Vs %s</b>" % (propLst[0], propLst[-1])
        g.top = g.top + 40
        
        backend = 'piddlePIL'
        canvasname = "Profile"
        module = __import__(backend)
        canvasClass = getattr(module, "PILCanvas")
        size = (600,500)
        canvas = canvasClass(size,canvasname)
        # draw the graph
        g.draw(canvas)

        # do post-test cleanup
        canvas.flush()
        canvas.save(file=self.handler.wfile, format='png')      # save as a PNG file
        
        
    def ShowPTEnvelope(self, env):
        """
        render Pressure/Temperature phase envelope
        """
        self.ShowUnitOp(env)
        print '''
        <script>
        var menu3 = parent.command.document.menuform.createmenu3;
        menu3.options.length = 0;
        menu3.menuMethod = undefined;
        menu3.options[0] = new Option('%s');''' % self.msg('WebAddQualityLines')
        print '''
        var i;
        for( i = 0; i <= 10; i = i++) {
            var quality = i / 10.;
            var menuItem = '%s = ';
            menu3.options[++i] = new Option(menuItem + quality,'Envelope.QualityCurve('+ quality + ');');
        }
        ''' % (self.msg('WebQualityValue'))
        print '</script>'
        units = self.s42cmd.units
        unitP = units.GetCurrentUnit(PropTypes[P_VAR].unitType)
        unitT = units.GetCurrentUnit(PropTypes[T_VAR].unitType)
        print '<table border=1><tr>'


        for key in env.QualityLines.keys():
            qLine = env.QualityLines[key]
            result = qLine.results
            if result:
                plotData = []
                print '<td><h3>%s</h3><br>%s' % (key, result.returnMessage)
                print '<table border=1>'
                print '<tr><th>%s</th><th>%s</th>' % (self.msg('WebPointNumber'), self.msg('WebPointType'))
                print '<th>T %s</th><th>P %s</th></tr>' % (unitT.name, unitP.name)
                for i in range(result.pointCount):
                    p = unitP.ConvertFromSim42(result.pValues[i])
                    t = unitT.ConvertFromSim42(result.tValues[i])
                    plotData.append((p,t))
                    print '<tr><td>%d</td><td>%d</td>' %(i, result.pointTypes[i])
                    print '<td>%g</td><td>%g</td></tr>' % (t, p)
                print '</table></td>'
        print '</tr></table>'

        if graph42:
            print '<p><img src="envplot?sid=%d&env=%s" border=1 align=center></p>' % (
                           self.id, env.GetPath())
        
    def ShowEnvelopePlot(self, envPath):
        self.handler.send_header("Content-type", "image/png")
        self.handler.end_headers()
        if not graph42: return
        
        env = self.s42cmd.GetObject(self.s42cmd.root, envPath[1:])
        if not env: return
        
        units = self.s42cmd.units
        unitP = units.GetCurrentUnit(PropTypes[P_VAR].unitType)
        unitT = units.GetCurrentUnit(PropTypes[T_VAR].unitType)

        g = graph42.Graph()
        g.bottom = 400
        g.right = 590
        g.formats = []
        i = 0
        maxP = 0.0; maxT = -500.0; minP = 1.0e20; minT = 1.0e20
        lineColors = (graph42.blue, graph42.green, graph42.red, graph42.brown,
                      graph42.cyan, graph42.magenta, graph42.gold, graph42.navy)
        numColors = len(lineColors)
        lineNumber = 0
        for key in env.QualityLines.keys():
            qLine = env.QualityLines[key]
            result = qLine.results
            if result:
                plotData = []
                for i in range(result.pointCount):
                    p = unitP.ConvertFromSim42(result.pValues[i])
                    t = unitT.ConvertFromSim42(result.tValues[i])
                    plotData.append((t,p))
                    minP = min(p, minP); maxP = max(p, maxP)
                    minT = min(t, minT); maxT = max(t, maxT)
                g.datasets.append(graph42.Dataset(plotData))

            format = graph42.PointPlot()
            format.lineStyle = graph42.LineStyle(width=2,
                               color=lineColors[lineNumber % numColors], kind=graph42.SOLID)
            format.symbol = graph42.CircleSymbol
            g.formats.append(format)
            lineNumber += 1
            
        numberTics = 10
        (minValue, maxValue) = graph42.ScaleValues((minT, maxT), numberTics)
        g.axes[graph42.X].range = [minValue, maxValue]
        g.axes[graph42.X].tickMarks[0].spacing = (maxValue - minValue)/numberTics
        g.axes[graph42.X].tickMarks[0].labels = "%g"
        g.axes[graph42.X].label.text = "<b>T %s</b>" % unitT.name

        (minValue, maxValue) = graph42.ScaleValues((minP, maxP), numberTics)
        g.axes[graph42.Y].range = [minValue, maxValue]
        g.axes[graph42.Y].tickMarks[0].spacing = (maxValue - minValue)/numberTics
        g.axes[graph42.Y].tickMarks[0].labels = "%g"
        g.axes[graph42.Y].label.text = "<b>P %s</b>" % unitP.name
        
        g.title.text = "<b>%s</b>" % env.GetName()
        g.top = g.top + 40
        
        backend = 'piddlePIL'
        canvasname = "Profile"
        module = __import__(backend)
        canvasClass = getattr(module, "PILCanvas")
        size = (600,500)
        canvas = canvasClass(size,canvasname)
        # draw the graph
        g.draw(canvas)

        # do post-test cleanup
        canvas.flush()
        canvas.save(file=self.handler.wfile, format='png')      # save as a PNG file
        #f = open('junk.png', 'wb')
        #canvas.save(file=f, format='png')
        #f.close()
            
 
    def ShowThermoCase(self, case):
        """
        render the thermo case
        """
        print """
        <script>
            function ChangeCompoundFilter(menu) {
                var selected = menu.selectedIndex;
                if ( selected == 0 ) return false;
                var filterName = menu.options[selected].value;
                var cmpList = window.document.frmdispthcase.gascomps;
                cmpList.options.length = 0;
                switch (filterName) {
                """
        for filterName, cmpList in CMP_FILTERS.items():
            print "case '%s':" %filterName
            idx = 0
            print "cmpList.options[%d] = new Option('%s', '%s');" %(idx, self.msg(filterName), self.msg(filterName))
            idx += 1
            currentCmps = self.s42cmd.thermoAdmin.GetSelectedCompoundNames(case.provider, case.case)
            for cmpName in cmpList:
                if not cmpName in currentCmps:
                    print "cmpList.options[%d] = new Option('%s', '%s');" %(idx, cmpName, cmpName)
                    idx += 1
            print "break;"

        print """
                }
            }
        
            function SelectedCompound(path, menu) {
                var selected = menu.selectedIndex;
                if( selected == 0 ) return false;
                var cmdField = parent.command.document.command.cmd;
                cmdField.focus();
                var cmd = cmdField.value;
                if( cmd.search(new RegExp('\\\\' + path)) < 0 ) {
                    cmdField.value = path + ' +';
                }
                
                var cmpName = menu.options[selected].value;
                // replace spaces with under scores
                cmdField.value += ' ' + cmpName.replace(/ /g, '_');
                menu.options[selected] = null;
                return false;
            }

            function DeleteCompound(path, name) {
                var cmdField = parent.command.document.command.cmd;
                cmdField.focus();
                var cmd = cmdField.value;
                if( cmd.search(new RegExp('\\\\' + path)) < 0 ) {
                    cmdField.value = path + ' -';
                }
                cmdField.value += ' ' + name.replace(/ /g, '_');
            }

            function MoveCompound(name) {
                var cmdField = parent.command.document.command.cmd;
                cmdField.focus();
                cmdField.value = name.replace(/ /g, '_') + ' >> ';
            }

            function InsertCompName(name) {
                var cmdField = parent.command.document.command.cmd;
                cmdField.focus();
                cmdField.value += ' ' + name.replace(/ /g, '_') + ' ';
            }
        """
        print r""" 
            function AddHypo(path) {
                var cmdField = parent.command.document.command.cmd;
                if( cmdField.value != '' && !window.confirm("%s")) return false;
                hypoWin = window.open('hypowin?sid=%d', 'hypowindow',
                            'width=500,height=450,status=yes,resizable=yes');
                hypoWin.focus();
                window.path = path;
                if( hypoWin.opener == null ) {
                    hypoWin.opener = window;
                }
                return false;
            }

        """ % (self.msg('WebConfirmReplaceCmd'), self.id)
        
        print '</script>'
        self.ClearMenus()


        print '''
        <script>
'''

        print '''
        parent.command.document.menuform.createmenu3.options.length = 0;
        var menu = parent.command.document.menuform.createmenu1;
        menu.options.length = 0;
        menu.menuMethod = parent.command.ChangeThermoCase;
        menu.conn = 0;
        menu.options[0] = new Option('%s');
        ''' % self.msg('WebChangePropPkg')
        
        thermo = self.s42cmd.thermoAdmin
        providers = thermo.GetAvThermoProviderNames()
        providers.sort()
        i = 0
        for provider in providers:
            pkgs = thermo.GetAvPropPkgNames(provider)
            pkgs.sort()
            for pkg in pkgs:
                i += 1
                print 'menu.options[%d] = new Option("%s.%s","%s.%s")' % (i,provider, pkg, provider, pkg)

                
        print r""" 
            function ChangePropPkg(path) {
                var cmdField = parent.command.document.command.cmd;
                if( cmdField.value != '' && !window.confirm("%s")) return false;
                thWin = window.open('chngproppkg?sid=%d', 'thwindow',
                            'width=500,height=450,status=yes,resizable=yes');
                thWin.focus();
                window.path = path;
                if( thWin.opener == null ) {
                    thWin.opener = window;
                }
                return false;
            }

        """ % (self.msg('WebConfirmReplaceCmd'), self.id)                
                
        print '</script>'

        print '<form name="frmdispthcase">'
        print """<p><input type="button" value="%s" onClick="ChangePropPkg('%s')"></p>"""%(self.msg('WebChangePropPkg'), case.GetPath())

        print '<table frame="border"><tr>'
        print '<td align="center">%s</td><td align="center">%s</td>' %(
                       self.msg('WebThermoName'), self.msg('WebThermoProvider'))
        print '<td align="center">%s</td><td align="center">%s</td><td align="center">%s</td>' %(
                       self.msg('WebVapPkg'), self.msg('WebLiqPkg'), self.msg('WebSolPkg'))
        print '</tr>'
        name = case.GetName()
        vap = liq = sol = '---'
        pkgs = case.package.split()
        vap = pkgs[0]
        if len(pkgs) > 1: liq = pkgs[1]
        if len(pkgs) > 2: sol = pkgs[4]  #Solid pkg is in the 4th position. Will need to change as this is hard coded for VMG
        if liq == '---': liq = vap
        print '<tr>'
        print '<td>%s</td><td>%s</td>' %(self.MakeCdRef(name, case), case.provider)
        print '<td>%s</td><td>%s</td><td>%s</td>' %(vap, liq, sol)
        print '</tr>'                                                     
            
        print '</table></p>\n'

        
        
        print """
        <table border=0 cellpadding=5>
          <tr valign="top">
            <td>
        """
        print """
              <table frame="border" rules="rows" cellpadding=2>
                <tr><td colspan=3>%s</td></tr>
        """ % self.msg('WebCurrentCompounds')
        
        currentCmps = self.s42cmd.thermoAdmin.GetSelectedCompoundNames(case.provider, case.case)
        for cmp in currentCmps:
            print '<tr>'
            print '''<td><a href="javascript:InsertCompName('%s');">%s</a> </td>''' % (cmp, cmp)
            print '''<td><a href="javascript:DeleteCompound('%s', '%s');">%s</a> </td>''' % (
                    case.GetPath(), cmp, self.msg('WebDelete'))
            print '''<td><a href="javascript:MoveCompound('%s');">%s</a> </td>''' % (cmp, self.msg('WebMove'))
            print '</tr>'
        print '</table>'
        
        print """
            </td>
            <td width=20>&nbsp</td>
            <td>
              <table border=0>
                <tr><td>
                  <select name="cmpfilter" onChange="ChangeCompoundFilter(this)">
                    <option>%s</option>

                """ % self.msg('WebChangeFilter')

        keys = CMP_FILTERS.keys()
        keys.sort()
        for filter in keys:
            print '<option value="%s">%s</option>' % (filter, self.msg(filter))
        
        print """
                  </select>
                </td></tr>
                """
        
        print """
                <tr><td>
                  <select name="gascomps" onChange="SelectedCompound('%s', this)" multiple size=10>
                    <option>%s
        """ % (case.GetPath(), self.msg('WebGasProcComponents'))

        #gasComps = ['METHANE', 'ETHANE', 'PROPANE', 'ISOBUTANE',
                    #'n-BUTANE', 'ISOPENTANE', 'n-PENTANE', 'n-HEXANE',
                    #'n-HEPTANE', 'n-OCTANE', 'n-NONANE', 'n-DECANE',
                    #'NITROGEN', 'CARBON DIOXIDE', 'HYDROGEN SULFIDE',
                    #'WATER']
                    
                    
                    
        filterComps = CMP_FILTERS['WebGasProcComponents']
        for cmp in filterComps:
        #for cmp in gasComps:
            if not cmp in currentCmps:
                print '<option value="%s">%s' % (cmp, cmp)
            
        print """
                  </select>
                </td></tr>
                <tr><td>
                  <select name="allcomps" onChange="SelectedCompound('%s', this)">
                    <option>%s
        """ % (case.GetPath(), self.msg('WebAllComponents'))
        
        if self.avCmpsHtml == None:
            #Create a buffer of the compound list
            cmps = self.s42cmd.thermoAdmin.GetAvCompoundNames(case.provider)
            cmps.sort()
            avCmpsHtml = ''
            for cmp in cmps:
               avCmpsHtml += '<option value="%s">%s\n' % (cmp, cmp)
            self.avCmpsHtml = avCmpsHtml
            
        print self.avCmpsHtml
        print """
                  </select>
                </td></tr>
                <tr><td>
                  <input type="button" value="%s" onClick="AddHypo('%s')">
                </td></tr>
              </table>    
            </td>
          </tr>
        </table>
        """ % (self.msg('WebAddHypo'), case.GetPath())
        print '</form>'

    def ShowPortTable(self, table):
        """
        create a PortTable class from the names and display it
        """
        self.ClearMenus()
        portTable = PortTable(self, table)
        print '<hr><b>%s</b>\n' % self.GetPathLinks(table)
        print ''' &nbsp;&nbsp;&nbsp;(<a href="javascript:DeleteObject('%s');">%s</a>)<br>''' % (
                    self.GetObjectPath(table), self.msg('WebDelete'))
        self.ListMatPorts(portTable)
        print '<table>'
        self.PortSummaryRow(op, op.GetPortNames(ENE|IN),  'WebEneIn')
        self.PortSummaryRow(op, op.GetPortNames(ENE|OUT), 'WebEneOut')
        self.PortSummaryRow(op, op.GetPortNames(SIG),     'WebSig')
        print '</table></div>'

    def ShowPFD(self, pfdInfoDict):
        """
        create display pfd
        """
        self.ClearMenus()
        
        flowsheet = self.s42cmd.GetObject(self.s42cmd.root, pfdInfoDict[PFDOP][2:])
        if not flowsheet:
            flowsheet = session.s42cmd.root
                                          
        while not isinstance(flowsheet, UnitOperations.UnitOperation) or (
              len(flowsheet.GetChildUnitOps()) == 0 and flowsheet.GetParent()):
            if hasattr(flowsheet, 'GetParent'):
                flowsheet = flowsheet.GetParent()
            else:
                flowsheet = session.s42cmd.root
            
        self.pfd = simbapfd.SimbaPFD(flowsheet)
        print """
            <script>
            function DisplayUop(uopPath) {
                var cmd = parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = 'cd ' + uopPath;
                cmd.form.submit();
                opener.parent.focus();
            }
            //function PathClick() {
            //    opener.parent.focus()
            //}
            </script>
            """
        print self.GetPathLinks(flowsheet) + '<br>'
        print '<map name="uopmap">'
        self.pfd.CreateImage()
        print '<img src="pfdImage?sid=%d" usemap="#uopmap" border=0>' % self.id
        print "</map>"
        
    def GetSuggestion(self):
        """Inspect current status of the simulator and make development suggestions based on it"""
        root = self.s42cmd.root
        thCaseObj = root.GetThermo()
        if not thCaseObj:
            return SUGGESTED_INFO['ThCase']
        
        
        
class PortTable(object):
    """
    mimics a unit op enough to let ListMatPorts display its list of ports
    """
    def __init__(self, session, portDict):
        keys = portDict.keys()
        keys.sort()
        root = session.s42cmd.root
        self.name = portDict.GetName()
        self.Menus(session)
        self.ports = {}
        self.matInPorts = []
        self.matOutPorts = []
        self.qInPorts = []
        self.qOutPorts = []
        self.sigPorts = []
        for key in keys:
            path = portDict[key][2:]
            port = session.s42cmd.GetObject(root, path)
            if port:
                self.ports[port.GetPath()] = port
                type = port.GetPortType()
                if type & MAT:
                    if type & IN:
                        self.matInPorts.append(port.GetPath())
                    else:
                        self.matOutPorts.append(port.GetPath())
                elif type & ENE:
                    if type & IN:
                        self.qInPorts.append(port.GetPath())
                        
                    else:
                        self.qOutPorts.append(port.GetPath())
                elif type & SIG:
                    self.sigPorts.append(port.GetPath())
            else:
                # port doesn't exist - remove from dictionary
                del portDict[key]
                
    def Menus(self, session):
        print '''
        <script>
function AddPortTableOptions(menu)
{
    // other wise do default add object
    var selected = menu.selectedIndex;    
    if( selected == 0 ) return false;      
    parent.output.location  = 'addtoporttable?name=%s&sel=' + menu.options[selected].value + '&sid=%d';
    menu.selectedIndex = 0;    
    return false;
}
''' % (self.name, session.id)
        print '''
function DeletePortTableOptions(menu)
{
    // other wise do default add object
    var selected = menu.selectedIndex;    
    if( selected == 0 ) return false;         
    parent.output.location  = 'deletefromporttable?name=%s&sel=' + menu.options[selected].value + '&sid=%d';
    menu.selectedIndex = 0;    
    return false;
}
''' % (self.name, session.id)
        print '''        
function SelectPortTableOptions(menu)
{
    // other wise do default add object
    var selected = menu.selectedIndex;    
    if( selected == 0 ) return false;       
    addWin = window.open('selectporttable?sid=%d&name=%s&sel=' + menu.options[selected].value, 'selectporttablewindow',
       'width=740,height=570,status=yes,resizable=yes,scrollbars=yes');
    addWin.focus();          
    menu.selectedIndex = 0;    
    return false;
}
''' % (session.id, self.name)        

        print '''
        parent.command.document.menuform.createmenu3.options.length = 0;
        var menu = parent.command.document.menuform.createmenu1;
        menu.options.length = 0;
        menu.menuMethod = AddPortTableOptions;
        menu.conn = 0;
        menu.options[0] = new Option('%s');
        ''' % msg('WebAddToPortTable')
        print '''
        var i = 1;
        menu.options[i++] = new Option('%s', '%s')''' % (msg('WebActualAll'), PTAll)        
        print "menu.options[i++] = new Option('%s', '%s')" % (msg('WebAllMaterialIn'), PTAllMatIn)    
        print "menu.options[i++] = new Option('%s', '%s')" % (msg('WebAllMaterialOut'), PTAllMatOut)
        print "menu.options[i++] = new Option('%s', '%s')" % (msg('WebAllEnergyIn'), PTAllEneIn)  
        print "menu.options[i++] = new Option('%s', '%s')" % (msg('WebAllEnergyOut'), PTAllEneOut)  
        print "menu.options[i++] = new Option('%s', '%s')" % (msg('WebAllSignal'), PTAllSig)
        print "menu.options[i++] = new Option('%s', '%s')" % (msg('WebAllStreamIn'), PTAllStrIn)         
        
        print '''
        parent.command.document.menuform.createmenu3.options.length = 0;
        var delmenu = parent.command.document.menuform.createmenu2;
        delmenu.options.length = 0;
        delmenu.menuMethod = DeletePortTableOptions;
        delmenu.conn = 0;
        delmenu.options[0] = new Option('%s');
        ''' % msg('WebDeleteFromPortTable')
        print '''
        var j = 1;
        delmenu.options[j++] = new Option('%s', '%s')''' % (msg('WebActualAll'), PTAll)
        print "delmenu.options[j++] = new Option('%s', '%s')" % (msg('WebAllMaterialIn'), PTAllMatIn)    
        print "delmenu.options[j++] = new Option('%s', '%s')" % (msg('WebAllMaterialOut'), PTAllMatOut)
        print "delmenu.options[j++] = new Option('%s', '%s')" % (msg('WebAllEnergyIn'), PTAllEneIn)  
        print "delmenu.options[j++] = new Option('%s', '%s')" % (msg('WebAllEnergyOut'), PTAllEneOut)  
        print "delmenu.options[j++] = new Option('%s', '%s')" % (msg('WebAllSignal'), PTAllSig)   
        print "delmenu.options[j++] = new Option('%s', '%s')" % (msg('WebAllStreamIn'), PTAllStrIn)          
        
        print '''
        parent.command.document.menuform.createmenu3.options.length = 0;
        var selmenu = parent.command.document.menuform.createmenu3;
        selmenu.options.length = 0;
        selmenu.menuMethod = SelectPortTableOptions;
        selmenu.conn = 0;
        selmenu.options[0] = new Option('%s');
        ''' % msg('WebSelectPorts')
        print '''
        var k = 1;
        selmenu.options[k++] = new Option('%s', '%s')''' % (msg('WebActualAll'), PTAll)
        print "selmenu.options[k++] = new Option('%s', '%s')" % (msg('WebAllMaterialIn'), PTAllMatIn)    
        print "selmenu.options[k++] = new Option('%s', '%s')" % (msg('WebAllMaterialOut'), PTAllMatOut)
        print "selmenu.options[k++] = new Option('%s', '%s')" % (msg('WebAllEnergyIn'), PTAllEneIn)  
        print "selmenu.options[k++] = new Option('%s', '%s')" % (msg('WebAllEnergyOut'), PTAllEneOut)  
        print "selmenu.options[k++] = new Option('%s', '%s')" % (msg('WebAllSignal'), PTAllSig) 
        print "selmenu.options[k++] = new Option('%s', '%s')" % (msg('WebAllStreamIn'), PTAllStrIn)        
        
        print '</script>'           
        
        
    def GetPortNames(self, portType = IN|OUT|MAT|ENE|SIG):
        """
        return list of port names for ports whose type matches
        portType flags. Note MAT and ENE must also
        have IN and/or OUT flags
        """
        
        names = []
        if portType & MAT:
            if portType & IN:
                names.extend(self.matInPorts)
            if portType & OUT:
                names.extend(self.matOutPorts)
        if portType & ENE:
            if portType & IN:
                names.extend(self.qInPorts)
            if portType & OUT:
                names.extend(self.qOutPorts)
        if portType & SIG:
            names.extend(self.sigPorts)
        return names

    def GetPort(self, name):
        return self.ports[name]

class Sim42Handler(HTTPMethodHandler):
    """
    Request handler for web server dedicated to Sim42 application
    """
    
    def __init__(self, request, client_address, server):
        """
        set the routines available
        set up the command interface
        """
        self.server = server
        self.client_address = client_address
        self.session = None
        routines = {
                    "command":  Sim42Handler.Command,
                    "docmd":    Sim42Handler.DoCommand,
                    "display":  Sim42Handler.Display,
                    "sim42":    Sim42Handler.StartSession,
                    "tree":     Sim42Handler.Tree,
                    "filewin":  Sim42Handler.FileWindow,
                    "hypowin":  Sim42Handler.HypoWindow,
                    "connwin":  Sim42Handler.ConnectWindow,
                    "connthwin":  Sim42Handler.ConnectThermoWindow,
                    "specfromwin": Sim42Handler.SpecFromWindow,
                    "advthermo":  Sim42Handler.CreateThCaseWindow,
                    "chngproppkg": Sim42Handler.ChangePropPkgWindow,
                    "download": Sim42Handler.Download,
                    "upload":   Sim42Handler.Upload,
                    "users":    Sim42Handler.Users,
                    "sessions": Sim42Handler.Sessions,
                    "preferences": Sim42Handler.Preferences,
                    "twrplot":  Sim42Handler.TowerProfilePlot,
                    "envplot":  Sim42Handler.EnvelopePlot,
                    "vecplot":  Sim42Handler.VecPropsPlot,
                    "hxplot":  Sim42Handler.HXProfilePlot,
                    "twrprofilereq":  Sim42Handler.TowerProfileRequestWindow,
                    "hxprofilereq":  Sim42Handler.HXProfileRequestWindow,
                    "pfdImage": Sim42Handler.PFDImage,
                    "pfd":      Sim42Handler.PFD,
                    "image":    Sim42Handler.Image,
                    "addtoporttable":  Sim42Handler.AddToPortTable,
                    "deletefromporttable":  Sim42Handler.DeleteFromPortTable,            
                    "selectporttable":  Sim42Handler.SelectPortTable                 
                    }
                
        HTTPMethodHandler.__init__(self, request, client_address, server, routines)

    def address_string(self):
        """Return the client address formatted for logging.

        This version just returns the host IP for efficiency.
        """

        host, port = self.client_address
        return host

    def is_cgi(self):
        """
        overload to always return true to enhance security
        """
        return 1


    def log_request(self, code='-', size='-'):
        pass # normally skip request logging
    
    def log_message(self, format, *args):
        if format != "CGI script exited OK":
            self.server.log_message("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def SendTop(self, title):
        """
        Standard page top including any menu etc
        """
        self.send_header("Content-type", "text/html")
        self.end_headers()

        print '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">\n'
        print "<html><head>\n"
        print "<title>%s</title>\n" % title

    def SendBottom(self):
        """
        Standard page bottom including closing body tag
        """
        print '</body></html>'

    def StartForm(self, name, action, target):
        """
        output necessary form tag and hidden fields
        """
        print '<form name= %s action="%s" method="POST" target="%s">\n' % (name, action, target)
        print '<input type="hidden" name="sid" value="%d">\n' % self.session.id

    def GetSession(self, form):
        """
        check that there is a valid session and if not show login page
        """
        self.session = self.GetSessionHelper(form)
        if self.session:
            # tell session what current handler is
            self.session.SetHandler(self)
            
        return self.session
        
    def GetSessionHelper(self, form):
        """
        does most of the actual GetSession work
        """
        if form.has_key('sid'):
            try:
                id = form.getfirst('sid')
                return self.server.GetSession(int(id))
            except:
                return None
        elif self.server.localOnly:
            user = self.server.GetUserInfo('localUser')
            if user is None: 
                user = Sim42User('localUser', '', LOCAL_ADMIN)
                self.server.SaveUserInfo(user)
            return self.server.AddSession(user, self)

        errorMsg = ''
        if form.has_key('login'):
            # read in the password file
            username = form.getfirst('user')
            passwd = form.getfirst('passwd')
            session = self.server.login(username, passwd, self)
            if session:
                if not self.server.localOnly:
                    try:
                        f = open(self.server.sessionLog, 'a')
                        f.write("%s" % time.asctime(time.gmtime(session.lastAccessed)))
                        f.write("\t%s on" % session.user.name)
                        f.write("\t%d" % session.id)
                        f.write("\t%s\n" % self.client_address[0])
                        f.close()                            
                    except:
                        pass
        
                return session
            else:
                errorMsg = msg('WebIncorrectLogin')

        self.SendTop(title=msg('WebLoginTitle'))
        print """</head><body bgcolor=%s>  
        <form action="%s" method="POST">""" % (DisplayBGColor, self.path)
        if errorMsg:
            print "<h3>%s</h3>" % errorMsg
        print '<table border=3 bgcolor=%s align=center bordercolor=red><tr><td colspan=2 align=center><img src="image?file=sim42_small.png"></td></tr>' % (CommandBGColor)
        print "<tr><td colspan=2><h3>%s</h3></td></tr>" % msg('WebPleaseLogin')
        print '''
                <tr>
                    <td>%s</td>
                    <td><input name='user' size=40></td>
                </tr>
                <tr>
                    <td>%s</td>
                    <td><input type="password" name="passwd" size=40>
                </tr>
                <tr>
                    <td align='center' colspan=2>
                        <input type=submit name='login' value='%s'>
                    </td>
                </tr>
                <tr>
                <td colspan=2>
             %s
             </td></tr>
             </table>
        </form>
        ''' % (msg('WebName'), msg('WebPassword'), msg('WebLogin'), msg('WebTermsofUse'))
        self.SendBottom()
        return None
    
    def SaveFileDescriptors(self):
        self.save_argv = sys.argv
        self.save_stdin = sys.stdin
        self.save_stdout = sys.stdout
        self.save_stderr = sys.stderr

    def RestoreFileDescriptors(self):
        sys.argv = self.save_argv
        sys.stdin = self.save_stdin
        sys.stdout = self.save_stdout
        sys.stderr = self.save_stderr

    def UseMyFileDescriptors(self):
        sys.argv = self.myargv
        sys.stdout = self.wfile
        sys.stdin = self.rfile
        
        
    def DoRoutine(self, argvAppend, routine):
        """ threaded version of DoRoutine """
        globalLock.acquire()
        self.SaveFileDescriptors()

        self.myargv = [routine]
        if argvAppend:
            self.myargv.append(argvAppend)

        self.UseMyFileDescriptors()

        try:
            self.routines[routine](self)
            if (not self.session) and routine != 'sim42' and routine != 'hypowin':
                s = msg('WebNotLoggedIn')
                self.SendTop(s)
                print '<body bgcolor=%s>' % (CommandBGColor)
                print   '<img src="image?file=sim42_small.png"><br>'
                print '<h3>%s</h3>' % s
                print '<p><a href="sim42" target="_top">%s</a></p>' % msg('WebLoginTitle')
                print 'By clicking the link above you have accepted the Terms of Use stated <a href="http://sim42.org/license.html">here</a>'
                self.SendBottom()
                
        finally:
            if self.session:
                self.session.ClearHandler()
            self.RestoreFileDescriptors()
            globalLock.release()
        
    def GetForm(self):
        """
        returns a cgi.FieldStorage
        """
        cgitb.enable()
        form = cgi.FieldStorage()
        return form
         
    def Download(self):
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        try:
            path = form['path'].value
        except:
            self.send_error(404, "File not found")

        ctype = self.guess_type(path)
        if ctype.startswith('text/'):
            mode = 'r'
        else:
            mode = 'rb'

        try:
            f = self.server.open(session.CommandInterface().root, path,'rb')
        except:
            self.send_error(404, "File not found")
            return

        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.end_headers()
        self.copyfile(f, self.wfile)
        f.close()

    def Image(self):
        """
        return file from image directory
        """
        form = self.GetForm()

        name = form['file'].value
        if name.startswith('.'):
            self.send_error(404, "File not found")
            return
            
        ctype = self.guess_type(name)

        if name not in self.server.imageCache:
            # try and load file
            try:
                if ctype.startswith('text/'):
                    mode = 'r'
                else:
                    mode = 'rb'
                path = self.server.imagePath + os.sep + name
                f = open(path,mode)
                self.server.imageCache[name] = f.read()
                f.close()
            except:
                self.send_error(404, "File not found")
                return

        try:
            self.send_response(200)
            self.send_header("Content-type", ctype)
            self.end_headers()
            self.wfile.write(self.server.imageCache[name])
        except:
            return
        
    def Upload(self):
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None or not (session.user.privilege & CAN_UPLOAD): return

        upload = form['file']
        fileName = upload.filename
        fileType = upload.type
        contents = upload.value
        localPath = form['rootpath'].value
        if localPath:
            filePath = localPath + '/' + fileName
        else:
            filePath = fileName
        
        if fileType.startswith('text/'):
            mode = 'w'
        else:
            mode = 'wb'
            
        self.SendTop('')
        try:
            f = self.server.open(session.CommandInterface().root, filePath, mode)
            f.write(contents)
            f.close()
        except:
            print '<h3>%s %s</h3>' % (session.msg('WebCouldNotSaveFile'), filePath)
            
        print '<script>window.close();</script>'
        self.SendBottom()

    def Command(self):
        """
        Initial start page
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        self.SendTop(title="Web Interface")
        print """
        <style>
        <!--
        a {text-decoration: none}
        -->
        </style>
        """
        print """
<SCRIPT TYPE="text/javascript">
<!--
var sessionId = %d;
""" % session.id

        print """
function submitenter(myfield,e)
{
    var keycode;
    if (window.event) keycode = window.event.keyCode;
    else if (e) keycode = e.which;
    else return true;

    if (keycode == 13)
    {
        myfield.form.submit();
        return false;
    }
    else
        return true;
}

function CreateCmdHistoryList()
{
    document.cmdHistory = new Array();
    document.cmdNumber = 0;
}

function PreviousCommand()
{
    var cmds = document.cmdHistory;
    document.command.cmd.focus();
    var last = cmds.length;
    if( last > document.cmdNumber ) {
        document.cmdNumber++;
        document.command.cmd.value = cmds[last - document.cmdNumber];
     }
     return false;
}
        
function NextCommand()
{
    var cmds = document.cmdHistory;
    document.command.cmd.focus();
    var last = cmds.length;
    if( document.cmdNumber > 0) {
        document.cmdNumber--;
        if( document.cmdNumber > 0)
            document.command.cmd.value = cmds[last - document.cmdNumber];
        else
            document.command.cmd.value = '';
     }
     return false;
}

var nameMessage = "%s" """ % session.msg('WebEnterNewObjName')
        print """

function ChangeThermoCase(menu)
{
    var selected = menu.selectedIndex;
    if( selected == 0 ) return false;
    var createCmd = menu.options[selected].value;
    var parts = createCmd.split('.');
    var provider = parts[0];
    var pkg = parts[1];
    document.command.cmd.value = 'package = ' + pkg;
    document.command.submit();
    menu.selectedIndex = 0;
    return false;
}        
        
function CreateThermoCase(menu)
{
    var selected = menu.selectedIndex;
    if( selected == 0 ) return false;
    var createCmd = menu.options[selected].value;
"""
        print '    var name = window.prompt(nameMessage,"");'
        print """
    if( name != null && name != '')
    {
        var parts = createCmd.split('.');
        var provider = parts[0];
        var pkg = parts[1];

        //In this case, the name must be a globally unique name 
        //since it is created under the ThermoAdmin
        var thAdmin = '%s';""" % UnitOperations.TH_ADMIN_KEYWORD
        print """
        document.command.cmd.value = thAdmin + name + ' = ' + createCmd;
        //menu.conn = 0
        
        //if( createCmd.charAt(createCmd.length - 1) != ';')
        if( menu.conn == 1)
        {
            document.command.cmd.value += '; . -> ' + thAdmin + name;
        }
        
        if( createCmd.charAt(createCmd.length - 1) != ';')
        {
            //Add the newly created case into the current unit op
            document.command.cmd.value += ';cd ' + name;
        }
        document.command.submit();
    }

     menu.selectedIndex = 0;
     return false;
}        
        
        
function CreateMenuObject(menu)
{
    // check to see if a menu specific handler is defined
    if(menu.menuMethod != undefined)
        return menu.menuMethod(menu)
    
    // other wise do default add object
    var selected = menu.selectedIndex;
    if( selected == 0 ) return false;
    var createCmd = menu.options[selected].value;
"""
        print '    var name = window.prompt(nameMessage,"");'
        print """
    if( name != null && name != '')
    {
        document.command.cmd.value = name + ' = ' + createCmd;
        if( createCmd.charAt(createCmd.length - 1) != ';')
            document.command.cmd.value += ';cd ' + name;
        document.command.submit();
    }

     menu.selectedIndex = 0;
     return false;
}

function HandleFileMenu(menu)
{
    // handle the various file menu commands
    var selected = menu.selectedIndex;
    if( selected == 0 ) return false;
    var command = document.command;
    var option = menu.options[selected].value;
    switch( option ) {
        case 'clear':
        case 'quit':
        case 'logout':
            command.cmd.focus();
            command.cmd.value = option;
            command.submit();
            break;
        case 'recall':
        case 'read':
        case 'log':
        case 'store':
        case 'mkdir':
        case 'download':
        case 'upload':
            fileWin = window.open('filewin?sid=' + String(sessionId) + '&cmd=' + option,
                'filewindow', 'width=640,height=450,status=yes,resizable=yes,scrollbars=yes');
            fileWin.focus();
            if( fileWin.opener == null ) {
                fileWin.opener = window;
            }
        break;
        case 'users':
            addWin = window.open('users?sid=' + String(sessionId), 'userswindow',
                'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
            addWin.focus();
        break;
        case 'sessions':
            addWin = window.open('sessions?sid=' + String(sessionId), 'sessionswindow',
                'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
            addWin.focus();
        break;
        case 'preferences':
            addWin = window.open('preferences?sid=' + String(sessionId), 'preferenceswindow',
                'width=740,height=570,status=yes,resizable=yes,scrollbars=yes');
            addWin.focus();
        break;
    }

    menu.selectedIndex = 0;
    return false;
}

function HandleUnitMenu(menu)
{
    // handle the selection of units
    var selected = menu.selectedIndex;
    var command = document.command;
    var option = menu.options[selected].value;

    command.cmd.focus();
    document.command.cmd.value = 'units ' + option;
    document.command.submit();

    return false;
}

function HandleLangMenu(menu)
{
    // handle the selection of units
    var selected = menu.selectedIndex;
    var command = document.command;
    var option = menu.options[selected].value;

    command.cmd.focus();
    document.command.cmd.value = 'language ' + option;
    document.command.submit();

    return false;
}
"""
        print """
function PFD() {
    pfdWin = window.open('pfd?sid=%d', '%s',
                'width=800,height=600,status=yes,resizable=yes,scrollbars=yes,menubar=yes');
    pfdWin.focus();
    if( pfdWin.opener == null ) {
        pfdWin.opener = window;
    }
    return false;
}
""" % (session.id, msg("WebPfd"))

        try:
            historyNumber = session.user.historyNumber
        except:
            historyNumber = 50  
        try:
            session.user.historyAll
        except:
            session.user.historyAll = 0
        print """      
        function OutputHistory() {
        this.currentSlot = 0;"""
        if session.user.historyAll == 1:
            print """
            this.numberSlots = Number.POSITIVE_INFINITY
            """
        else:
            print """
            this.numberSlots = %d
            """ % int(historyNumber)
        print """;
        this.slots = Array();
}

OutputHistory.prototype.setNumberSlots = function(nSlots) {
    this.numberSlots = nSlots;"""
        if session.user.historyAll == 1:
            print """
            this.numberSlots = Number.POSITIVE_INFINITY
            """
        print r"""
}

OutputHistory.prototype.add = function(output) {
    this.slots.push(output);
    while( this.slots.length > this.numberSlots) this.slots.shift();
    this.nextSlot++;
    this.currentSlot = this.slots.length - 1;
}

OutputHistory.prototype.next = function( ) {
    var msg = '';
    if( this.currentSlot < this.slots.length - 1 )
        this.currentSlot++
    else
        msg = '<br>End of History';
    return this.slots[this.currentSlot] + msg;
}
OutputHistory.prototype.all = function( ) {
    var beginmsg = 'Beginning of History<br>';
    var endmsg = 'End of History';
    for( var i = 0; i < this.slots.length; i++) { beginmsg += this.slots[i] + '<br>'; }
    return beginmsg + endmsg;
}    
OutputHistory.prototype.prev = function( ) {
    var msg = '';
    if( this.currentSlot > 0 )
        this.currentSlot--;
    else
        msg = '<br>Beginning of History';
    return this.slots[this.currentSlot] + msg;
}
    
OutputHistory.prototype.first = function( ) {
    var msg = '';
    this.currentSlot = 0;
    msg = 'Beginning of History';
    return this.slots[this.currentSlot] + msg;
}

OutputHistory.prototype.last = function( ) {
    var msg = '';
    this.currentSlot = this.slots.length - 1;
    msg = 'End of History';
    return this.slots[this.currentSlot] + msg;
}

var outputHistory = new OutputHistory();

function SaveOutputContents() {
    var outWnd = parent.output;
    var contents = outWnd.document.getElementById('cmdOutput');
    if( contents ) outputHistory.add(contents.innerHTML.replace(/[\r]*\n/g, '<br>'));
}

//-->
</SCRIPT>
</head><body onload="CreateCmdHistoryList()" bgcolor="%s">
""" % (CommandBGColor)
        print """
  <table border="0">
  <tr><td width=200>
    <img src="image?file=sim42_small.png"><br>
    
"""
        print '<div align=center><b><a href="http://sim42.org/simba" target="_simba">'
        print '%s %s</a></b></div>' % (session.msg('WebAboutSimba'), Flowsheet.VERSION[1])
        print """</td><td>
  
  <table border="0" cellspacing="0" cellpadding="2">
  <form name="menuform">
    <tr>
      <td width="250">
        <select name="filemenu" onchange="HandleFileMenu(this)" style="WIDTH: 250px">
        </select>
        """
        print """
      </td>
      <td width="250">
        <select name="unitmenu" onchange="HandleUnitMenu(this)" style="WIDTH: 250px">
        """
        uSys = session.CommandInterface().units
        for u in uSys.GetSetNames():
             print '<option value="%s">%s</option>' %(u, u)

        print """
        </select>
      </td>
      <td width="250">
        <select name="langmenu" onchange="HandleLangMenu(this)" style="WIDTH: 250px">
        """
        dct = CommandInterface.MessageHandler.GetSupportedLanguages()
        lst = list(dct['languages'])
        for l in lst:
            print '<option value="%s">%s</option>' %(l, l)
        print """
        </select>
      </td>
    </tr>
    """
        self.languageFixups(session)
        print """
    <tr>
      <td width="100">
        <select name="createmenu1" onchange="CreateMenuObject(this)" style="WIDTH: 250px">
        </select>
        """
        print """
      </td>
      <td width= "100">
        <select name="createmenu2" onchange="CreateMenuObject(this)" style="WIDTH: 250px">
        </select>
      </td>
      <td width= "100">
        <select name="createmenu3" onchange="CreateMenuObject(this)" style="WIDTH: 250px">
        </select>
      </td>
    </tr>
  </form>
      
"""
        self.StartForm('command', 'docmd', 'output')
        print '<tr><td colspan=3 nowrap><input type="text" size=80 name="cmd" id="cmd"'
        prompt = form.getfirst('prompt')
        if prompt:
            print 'value="%s"' % prompt
        print '>\n'
        print '<input type="button" value="^" onclick="PreviousCommand();">';
        print '<input type="button" value="v" onclick="NextCommand();">';
        print '<input type="submit" name="docmd" value="Enter">'
        print '<input type="reset" value="Reset">'
        print '<input type="submit" value="%s" onClick="return PFD();">' % msg('WebPFD')
        
        print '</td></tr>'
        print '</form></table></td></tr></table>\n'
        self.SendBottom()
        
    def languageFixups(self, session):
        """
        fill the file menu with items in the current language and other fixups
        """
        # start by getting the current language
        
        print """
        <script>
        var menu = parent.command.document.menuform.filemenu;
        var i = 0;
        """
        print "menu.options[i++] = new Option('%s'); " % session.msg('WebFileMenu')
        print "menu.options[i++] = new Option('%s','%s');" % (session.msg('Web_clear'), 'clear')
        print "menu.options[i++] = new Option('%s','%s');" % (session.msg('Web_recall'), 'recall')
        print "menu.options[i++] = new Option('%s','%s');" % (session.msg('Web_store'), 'store')
        print "menu.options[i++] = new Option('%s','%s');" % (session.msg('Web_read'), 'read')
        print "menu.options[i++] = new Option('%s','%s');" % (session.msg('Web_log'), 'log')
        print "menu.options[i++] = new Option('%s','%s');" % (session.msg('Web_mkdir'), 'mkdir')
        print "menu.options[i++] = new Option('%s','%s');" % (session.msg('WebDownLoad'), 'download')
        if self.session.user.privilege & CAN_UPLOAD:
            print "menu.options[i++] = new Option('%s','%s');" % (session.msg('WebUpload'), 'upload')
        print "menu.options[i++] = new Option('%s','%s');" % (session.msg('WebLogout'), 'logout')
        if self.session.user.privilege & CAN_SHUTDOWN:
            print "menu.options[i++] = new Option('%s','%s');" % (session.msg('WebQuit'), 'quit')
        if self.session.user.privilege & CAN_ADDUSER:
            print "menu.options[i++] = new Option('%s','%s');" % (session.msg('WebUsers'), 'users')
        if self.session.user.privilege & CAN_SEE_SESSIONS:
            print "menu.options[i++] = new Option('%s','%s');" % (session.msg('WebSessions'), 'sessions')
        if self.session.user.privilege & CAN_UPLOAD:
            print "menu.options[i++] = new Option('%s','%s');" % (session.msg('WebPreferences'), 'preferences')
        
        # unit menu
        print 'menu = parent.command.document.menuform.unitmenu;'
        uSys = session.CommandInterface().units
        uDef = uSys.GetDefaultSet()
        i = uSys.GetSetNames().index(uDef)
        print 'menu.selectedIndex = %d;' % i
        
        # language menu
        language = session.infoCallBack.GetLanguage()
        dct = CommandInterface.MessageHandler.GetSupportedLanguages()
        i = list(dct['languages']).index(language)
        print 'menu = parent.command.document.menuform.langmenu;'
        print 'menu.selectedIndex = %d;' % i
        
        # other non file menu fixups
        print 'parent.command.nameMessage = "%s";' % session.msg('WebEnterNewObjName')
        print '</script>'

    def SelectPortTable(self):
        form = self.GetForm()
        session = self.GetSession(form)   
        infoPath = '/Info.Simba.PortTables.'        
        cmdline = ''
        info = session.s42cmd.root.info        
        if info.has_key(SIMBAINFO):
            simbaInfo = info[SIMBAINFO]
        else:
            simbaInfo = info[SIMBAINFO] = SimInfoDict(SIMBAINFO, info)
            
        if simbaInfo.has_key(PORTTABLES):
            portTables = simbaInfo[PORTTABLES]
        else:
            portTables = simbaInfo[PORTTABLES] = SimInfoDict(PORTTABLES, simbaInfo)             
        ports = {}        
        selected = form.getfirst("sel")        
        tableName = form.getfirst("name")   
        if selected == PTAll:
            self.GetPorts(session.s42cmd.root, ports, IN|OUT|MAT|ENE|SIG)
        elif selected == PTAllMatIn:
            self.GetPorts(session.s42cmd.root, ports, MAT|IN)
        elif selected == PTAllMatOut:
            self.GetPorts(session.s42cmd.root, ports, MAT|OUT)
        elif selected == PTAllEneIn:
            self.GetPorts(session.s42cmd.root, ports, ENE|IN)
        elif selected == PTAllEneOut:
            self.GetPorts(session.s42cmd.root, ports, ENE|OUT)
        elif selected == PTAllSig:
            self.GetPorts(session.s42cmd.root, ports, SIG)
        elif selected == PTAllStrIn:
            self.GetPorts(session.s42cmd.root, ports, MAT|IN)            
            
        if form.has_key('update'):
            if selected == PTAllStrIn:        
                paths = []
                for port in ports:
                    if isinstance(port.GetParent(), Stream.Stream_Material):   
                        paths.append(ports[port])
            else:
                paths = ports.values()    
            paths.sort()
            for path in paths:         
                portKey = re.sub('\.','_', path[1:])
                if form.has_key(path[1:].replace('.','_')):
                    if not portTables[tableName].has_key(portKey):
                        cmdline += infoPath + tableName + '.' + path[1:].replace('.','_') + ' = "%' + path + '";'
                else:
                    if portTables[tableName].has_key(portKey):
                        cmdline += ' delete ' + infoPath + tableName + '.' + path[1:].replace('.','_') + ';'
            self.SendTop(session.msg('WebCommandOutputTitle'))
            self.ProcessCommand(session, cmdline)
            self.SendBottom()
            return
        
        
        self.SendTop(session.msg('WebSelectPorts'))
        print '</head><body bgcolor="%s">' % DisplayBGColor    
        print '<h2 align=center>%s</h2>' % tableName
        print '<form action="selectporttable" name="selform" target="output" method="POST">'
        print '<input type=hidden value=%s name="sel">' % selected
        print '<input type=hidden value=%s name="name">' % tableName
        print '<input type=hidden value=%s name="sid">' % form.getfirst('sid')
        print '<table border=1 align=center bgcolor=#FFFFFF>' 

        if selected == PTAllStrIn:        
            paths = []
            for port in ports:
                if isinstance(port.GetParent(), Stream.Stream_Material):   
                    paths.append(ports[port])
        else:
            paths = ports.values()                    
        col = -1
        paths.sort()
        for path in paths:             
            portKey = re.sub('\.','_', path[1:])
            if col == -1:
                print '<tr>'
                col = 0
            print '<td><table width="100%%"><tr><td>%s</td><td align=right><input type=checkbox name="%s" ' % (path[1:].replace('.','_'), path[1:].replace('.','_'))
            if portTables[tableName].has_key(portKey):
                print 'CHECKED'
            print '></td></tr></table></td>'
            if col == 2:
                print '</tr><tr>'
                col = 0
            else:
                col = col + 1
        print '</tr><tr><td colspan=3 align=center><input type=submit name="update" value="%s">' % session.msg('WebUpdate')
        print '<input type=submit onclick="window.close();" value="%s"></td></tr></table></form>' % session.msg("WebClose")
            
    def DeleteFromPortTable(self):
        form = self.GetForm()
        session = self.GetSession(form)
        cmdline = ''
        infoPath = '/Info.Simba.PortTables.'
        info = session.s42cmd.root.info
        if info.has_key(SIMBAINFO):
            simbaInfo = info[SIMBAINFO]
        else:
            simbaInfo = info[SIMBAINFO] = SimInfoDict(SIMBAINFO, info)
            
        if simbaInfo.has_key(PORTTABLES):
            portTables = simbaInfo[PORTTABLES]
        else:
            portTables = simbaInfo[PORTTABLES] = SimInfoDict(PORTTABLES, simbaInfo)        
        if session is None: return
        selected = form.getfirst("sel")
        tableName = form.getfirst("name")
        ports = {}
        if selected == PTAll:
            self.GetPorts(session.s42cmd.root, ports, IN|OUT|MAT|ENE|SIG)
        elif selected == PTAllMatIn:
            self.GetPorts(session.s42cmd.root, ports, MAT|IN)
        elif selected == PTAllMatOut:
            self.GetPorts(session.s42cmd.root, ports, MAT|OUT)
        elif selected == PTAllEneIn:
            self.GetPorts(session.s42cmd.root, ports, ENE|IN)
        elif selected == PTAllEneOut:
            self.GetPorts(session.s42cmd.root, ports, ENE|OUT)
        elif selected == PTAllSig:
            self.GetPorts(session.s42cmd.root, ports, SIG) 
        elif selected == PTAllStrIn:
            self.GetPorts(session.s42cmd.root, ports, MAT|IN) 
            
        for port in ports:   
            if selected == PTAllStrIn:
                
                if isinstance(port.GetParent(), Stream.Stream_Material):
                    path = port.GetPath()
                    
                    portKey = re.sub('\.','_', path[1:])
                    if portTables[tableName].has_key(portKey):
                        cmdline += ' delete ' + infoPath + tableName + '.' + path[1:].replace('.','_') + ';'
                else:
                    pass
            else:
                path = port.GetPath()
                
                portKey = re.sub('\.','_', path[1:])
                if portTables[tableName].has_key(portKey):
                    cmdline += ' delete ' + infoPath + tableName + '.' + path[1:].replace('.','_') + ';'
                
        self.SendTop(session.msg('WebCommandOutputTitle'))
        self.ProcessCommand(session, cmdline)
        self.SendBottom()
        
    def AddToPortTable(self):
        form = self.GetForm()
        session = self.GetSession(form)
        cmdline = ''
        infoPath = '/Info.Simba.PortTables.'
        info = session.s42cmd.root.info
        if info.has_key(SIMBAINFO):
            simbaInfo = info[SIMBAINFO]
        else:
            simbaInfo = info[SIMBAINFO] = SimInfoDict(SIMBAINFO, info)
            
        if simbaInfo.has_key(PORTTABLES):
            portTables = simbaInfo[PORTTABLES]
        else:
            portTables = simbaInfo[PORTTABLES] = SimInfoDict(PORTTABLES, simbaInfo)        
        if session is None: return
        selected = form.getfirst("sel")
        tableName = form.getfirst("name")
        ports = {}
        if selected == PTAll:
            self.GetPorts(session.s42cmd.root, ports, IN|OUT|MAT|ENE|SIG)       
        elif selected == PTAllMatIn:
            self.GetPorts(session.s42cmd.root, ports, MAT|IN)
        elif selected == PTAllMatOut:
            self.GetPorts(session.s42cmd.root, ports, MAT|OUT)          
        elif selected == PTAllEneIn:
            self.GetPorts(session.s42cmd.root, ports, ENE|IN)  
        elif selected == PTAllEneOut:
            self.GetPorts(session.s42cmd.root, ports, ENE|OUT)         
        elif selected == PTAllSig:
            self.GetPorts(session.s42cmd.root, ports, SIG)   
        elif selected == PTAllStrIn:
            self.GetPorts(session.s42cmd.root, ports, MAT|IN) 
            
        for port in ports:   
            if selected == PTAllStrIn:
                
                if isinstance(port.GetParent(), Stream.Stream_Material):
                    path = port.GetPath()
                    
                    portKey = re.sub('\.','_', path[1:])
                    if not portTables[tableName].has_key(portKey):
                        cmdline += infoPath + tableName + '.' + path[1:].replace('.','_') + ' = "%' + path + '";'
                else:
                    pass
            else:
                path = port.GetPath()
                
                portKey = re.sub('\.','_', path[1:])
                if not portTables[tableName].has_key(portKey):
                    cmdline += infoPath + tableName + '.' + path[1:].replace('.','_') + ' = "%' + path + '";'
                
        self.SendTop(session.msg('WebCommandOutputTitle'))
        self.ProcessCommand(session, cmdline)
        self.SendBottom()

    def DoCommand(self):
        """
        process a command and output the results
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return
        cmdline = form.getfirst("cmd")
        self.SendTop(session.msg('WebCommandOutputTitle'))
        self.ProcessCommand(session, cmdline) 
        self.SendBottom()


    def ProcessCommand(self, session, cmdline):
        """
        process cmdLine for session
        """
        
        # note that the code=Math.random() in the url below is just to force the browser to actually reload
        # the page when it has used a named anchor with in the page
        print """
<SCRIPT TYPE="text/javascript">
<!--
sid = %d;

function DoDisplay()
{
    parent.display.location.replace('display?sid='+sid+'&code='+Math.random());
    var cmdInput = parent.command.document.command.cmd;
    cmdInput.focus();
    cmdInput.value='';
    parent.tree.location.reload();
}

function AddToCmdHistory(cmd)
{
    var cmdHistory = parent.command.document.cmdHistory;
    cmdHistory.push(cmd);
    parent.command.document.cmdNumber = 0;
}

function ScrollOutputWindow() {
    parent.output.scrollBy(0, 10000);
}

function next() {
   var history = parent.command.outputHistory;
   var contents = parent.output.document.getElementById('cmdOutput');
   contents.innerHTML = history.next();
}

function all() {
   var history = parent.command.outputHistory;
   var contents = parent.output.document.getElementById('cmdOutput');
   contents.innerHTML = history.all();
   scrollBy(0,10000);
}

function prev() {
   var history = parent.command.outputHistory;
   var contents = parent.output.document.getElementById('cmdOutput');
   contents.innerHTML = history.prev();
}

function first() {
   var history = parent.command.outputHistory;
   var contents = parent.output.document.getElementById('cmdOutput');
   contents.innerHTML = history.first();
}

function last() {
   var history = parent.command.outputHistory;
   var contents = parent.output.document.getElementById('cmdOutput');
   contents.innerHTML = history.last();
}
//-->
</SCRIPT>

</head><body onLoad="DoDisplay();" bgcolor="%s">
""" % (session.id, ProcessBGColor)

        cmdResult = ''
        if cmdline:
            if cmdline == 'quit':
                if self.server.localOnly or session.GetUser().GetPrivilege() & CAN_SHUTDOWN:
                    self.server.ShutDown()
                    return
            elif cmdline == 'logout':
                self.server.RemoveSession(session.id)
                
            try:
                if cmdline.find('\n') == -1:
                    print """<script>AddToCmdHistory('%s');
                    var intervalId = setInterval(ScrollOutputWindow, 200);
                    </script>""" % cmdline

                print '<pre id="cmdOutput">\n=> ' + cmdline + '\n'
                session.LogCommand(cmdline)
                
                self.RestoreFileDescriptors()
                globalLock.release()
                try:
                    cmdResult = session.CommandInterface().ProcessCommandString(cmdline)
                finally:
                    globalLock.acquire()
                    self.SaveFileDescriptors()
                    self.UseMyFileDescriptors()

                print '<script>clearInterval(intervalId);</script>'
                if cmdline.split()[0] in ['language', 'units', 'recall', 'read']:
                    self.languageFixups(session)
                
            except CallBackException, e:
                print '<script>clearInterval(intervalId);</script>'
                session.infoCallBack.handleMessage('CMDCallBackException', str(e))
            except Exception, e:
                print '<script>clearInterval(intervalId);</script>'
                tb = ''
                for i in traceback.format_tb(sys.exc_traceback):
                    tb += i + '\n'
                session.infoCallBack.handleMessage('CMDUnhandledError', (str(sys.exc_type), str(e), tb))
        print cmdResult,
        print '</pre>'

        print """
              <style>
              <!--
              a {text-decoration: none}
              -->
              </style>"""                 
        print '<a href="javascript:first();">%s</a>' % session.msg('WebFirst') 
        print '<a href="javascript:prev();">%s</a>' % session.msg('WebPrev') 
        print '<a href="javascript:all();">%s</a>' % session.msg('WebAll')      
        print '<a href="javascript:next();">%s</a>' % session.msg('WebNext') 
        print '<a href="javascript:last();">%s</a>' % session.msg('WebLast') 
        print '''
           <script>parent.command.SaveOutputContents();
            scrollBy(0,10000);</script>'''



    def Display(self):
        """
        display the current object in the display frame
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        self.SendTop(session.msg('WebCurrentObject'))
        print """
<style>
a {text-decoration: none}
table {background-color: white }
td    {padding: 3; vertical-align: top }
</style>

</head><body bgcolor="%s">
<SCRIPT TYPE="text/javascript">
<!--
function SetCommand(wnd, cmd)
{
    var cmdInput = wnd.parent.command.document.getElementById("cmd");
    cmdInput.focus();
    cmdInput.value=cmd;
}

function OpenConnectThermoWindow(uoPath, sid) {
    connectWin = window.open('connthwin?sid='+ sid + '&uo=' + uoPath, 'connectwindow',
                'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
    connectWin.focus();
    if( connectWin.opener == null ) {
        connectWin.opener = window;
    }
}

function OpenConnectWindow(portPath, sid) {
    connectWin = window.open('connwin?sid='+ sid + '&port=' + portPath, 'connectwindow',
                'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
    connectWin.focus();
    if( connectWin.opener == null ) {
        connectWin.opener = window;
    }
}

function OpenSpecFromWindow(portPath, sid) {
    connectWin = window.open('specfromwin?sid='+ sid + '&port=' + portPath, 'specfromwindow',
                'width=500,height=450,status=yes,resizable=yes,scrollbars=yes');
    connectWin.focus();
    if( connectWin.opener == null ) {
        connectWin.opener = window;
    }
}

function PathClick() {
    // just empty here
}
//-->
</SCRIPT>
""" % DisplayBGColor
        
        session.ShowCurrentObject()
        self.SendBottom()
        

    def Tree(self):
        """
        display the current object in the display frame
        """
        form = self.GetForm()
        session = self.GetSession(form)
        
        if session:
            self.SendTop(session.msg('WebCurrentObject'))
        else:
            self.SendTop(msg('WebCurrentObject'))
        print """
        <style>
        <!--
         a {text-decoration: none}
         -->
         </style>
         </head><body bgcolor="%s">
""" % TreeBGColor
        if session is None:
            self.SendBottom()
            return
        session.ShowTree()
        self.SendBottom()
    
    def FileWindow(self):
        """
        display files and perform basic commands
        """
        form = self.GetForm()
        session = self.GetSession(form)

        cmd = form['cmd'].value
        try: rootPath = form['root'].value
        except: rootPath = ''
            
        self.SendTop(session.msg('Web_' + cmd))
        
        if cmd == 'store':
            customLine1 = '''cmdField.value = cmd + ' "' + file + '" "z"';'''
        elif cmd == 'recall':
            customLine1 = '''cmdField.value = cmd + ' "' + file + '"';'''
        else:
            customLine1 = '''cmdField.value = cmd + ' ' + file;'''
            
        print '''
        <script>
        function SwitchDirTo(name) {
            var root = ''
            if( name != '' )
                root = '&root=' + name;
            window.location.href = "filewin?sid=%d&cmd=%s" + root;
        }
        
        function DoFileCommand( fileCmd) {
            cmdField = opener.parent.command.document.command.cmd;
            cmdField.focus();
            cmdField.value = fileCmd;
            cmdField.form.submit();
            window.close();
        }
        function DoFileInput( form, cmd, localPath) {
            cmdField = opener.parent.command.document.command.cmd;
            cmdField.focus();
            file = form.path.value;
            if( localPath != '' )
                file = localPath + '/' + file;
            %s
            cmdField.form.submit();
            window.close();
        }
        function DeleteFile(localPath) {
            cmdField = opener.parent.command.document.command.cmd;
            cmdField.focus();
            cmdField.value = 'rm' + ' ' + localPath;
            cmdField.form.submit();
            window.close();
        }
            
        function DeleteDir(localPath) {
            cmdField = opener.parent.command.document.command.cmd;
            cmdField.focus();
            cmdField.value = 'rmdir' + ' ' + localPath;
            cmdField.form.submit();
            window.close();
        }
            
        </script>
        ''' % (session.id, cmd, customLine1)
        
        print '</head><body bgcolor="%s">' % FileWinColor
        files = self.server.listdir(session.CommandInterface().root, rootPath)
        files.sort()
        currentPath = self.server.PermittedBasePath(session.CommandInterface().root)
        currentPath = re.sub(r'\\', '/', currentPath)
        currentDirPathLength = len(os.path.abspath('.')) + 1
        if rootPath:
            rootPath = re.sub(r'\\', '/', rootPath)
            currentPath += '/' + rootPath
        localPath = currentPath[currentDirPathLength:]
        
        if cmd == 'upload':
            print '<form enctype="multipart/form-data" method="post" action="upload">'
            print '<input type="hidden" name="rootpath" value="%s">' % localPath
            print '<input type="hidden" name="sid" value=%d>' % session.id
            print '<input type="file" size=40 name="file">'
            print '<input type="submit" value="OK"></form>'
        elif cmd != 'download':
            print '''<form onSubmit="DoFileInput(this, '%s', '%s');">''' % ( cmd, localPath)
            print '<table><tr><td><input type=text width=40 name="path"></td>'
            print '<td><input type=submit value="%s"></td></tr>' % session.msg('Web_' + cmd)
            print '</table></form>'

        print '<table>'
        if rootPath:
            # add parent
            lastSep = rootPath.rfind('/')
            if lastSep == -1:
                parentPath = ''
            else:
                parentPath = rootPath[:lastSep]
            print '<tr bgcolor="%s"><td colspan=4>' % DirRowColor
            print '''<a href="javascript:SwitchDirTo('%s');">..</a></td></tr>''' % parentPath
            
        for file in files:
            path = currentPath + '/' + file
            size = os.path.getsize(path)
            date = os.path.getmtime(path)
            userPath = currentPath[currentDirPathLength:]
            if userPath:
                userPath += '/' + file
            else:
                userPath = file
            if os.path.isdir(path):
                if cmd == 'download':
                    continue  # can't download directories
                
                if rootPath:
                    dirName = rootPath + '/' + file
                else:
                    dirName = file
                    
                print '<tr bgcolor="%s">' % DirRowColor
                print '''<td><a href="javascript:SwitchDirTo('%s');">''' % dirName
                print '%s</a></td>' % file
                delFunc = 'DeleteDir'
            else:
                if cmd == 'download':
                    ref = 'download?sid=%d&path=%s' % (session.id, userPath)
                elif cmd == 'upload':
                    ref = ''
                else:
                    if cmd == 'store':
                        #Zip the file by default
                        #The scape characters are sent to javascript to avoid confusion of quotes
                        fileCmd = cmd + r" \'" + userPath + r"\' \'z\'"
                    elif cmd == 'recall':
                        #Add quotes such that # are accepted
                        #The scape characters are sent to javascript to avoid confusion of quotes
                        fileCmd = cmd + r" \'" + userPath + r"\'"
                    else:
                        fileCmd = cmd + ' ' + userPath
                    ref = "javascript:DoFileCommand('%s');" % fileCmd
                    
                print '''<tr><td><a href="%s">%s</a></td>''' % ( ref, file)
                delFunc = 'DeleteFile'
            print '<td>%d</td><td>%s</td>' % (size, time.ctime(date))
            print '''<td><a href="javascript:%s('%s');"><b>%s</b></a></td></tr>''' % (
                    delFunc, userPath, session.msg('WebDelete'))
        print '</table>'
        self.SendBottom()
    
    def HypoWindow(self):
        """
        display a form to fill in hypo information
        """
        form = self.GetForm()
        session = self.GetSession(form)

        # Common fields - key is also key into msg base and field name
        fields = (
            ('WebMW', "MolecularWeight"),
            ('WebNBP', "NormalBoilingPoint"),
            ('WebDensity298', "LiquidDensity@298"),
            ('WebTc', "CriticalTemperature"),
            ('WebPc', "CriticalPressure"),
            ('WebVc', "CriticalVolume"),
            ('WebZc', "CriticalCompressibility"),
            ('WebAcentric', "AcentricFactor") )
        
        self.SendTop(session.msg('WebHypoWindowTitle'))
        print """
        <script>
        function AddHypo(form) {
            var cmd = opener.parent.command.document.command.cmd;
            path = opener.path;

            var fields = {
        """
        
        for field in fields:
            print "'%s' : '%s'," % (field[0], field[1])
            
        print r"""
            "":"" }

            var hyponame = form['hyponame'].value;
            if( hyponame == '' ) {
                alert("%s");
                return false;
            }
        """ % session.msg('WebHypoNeedsName')
        
        print r"""
            
            cmd.focus();
            cmd.value = path + '.' + hyponame + ' = HypoCompound ';
            var elements = form.elements;
            for( i = 0; i <elements.length; i++) {
                elementName = elements[i].name;
                if( elementName.substring(0,3) == 'Web' && elements[i].value) {
                    cmd.value += fields[elementName] + ' = ' + elements[i].value + ', '
                }
            }
            var otherText = form['hypother'].value;
            if( otherText != '') {
                otherText = otherText.replace(/\n/g, ';');
            }
            cmd.value += otherText;
            cmd.form.submit();
            window.close();
        }
        </script>
        
        """
        
        print """
        </head><body bgcolor="%s">
          <form onSubmit="return AddHypo(this);">
            <table border=1>
              <tr>
                <td>%s</td><td><input type=text name="hyponame" size=30></td>
              </tr>
        """ % (HypoWinColor, session.msg('WebName'))
        
        for prop in fields:
            print """
              <tr>
                <td>%s</td><td><input type=text name="%s" size=30></td>
              </tr>
            """ % (session.msg(prop[0]), prop[0])
        print """
              <tr>
                <td valign=top>%s</td><td><textarea name="hypother" rows=6 cols=30></textarea></td>
              </tr>
              <tr>
                <td colspan=2 align = center>
                  <input type=submit name="add" value="%s">
                </td>
              </tr>
            </table>
          </form>
        """ % (session.msg('WebHypoOther'), session.msg('WebAdd'))
        self.SendBottom()
    
    def GetPorts(self, startOp, ports, portType):
        """
        fill dictionary ports where the port is the key the paths are
        the values.  Only include the highest reference to the port that
        is of type portType
        """
        for port in startOp.GetPorts(portType):
            if not ports.has_key(port):
                ports[port] = port.GetPath()
        
        for child in startOp.GetChildUnitOps():
            self.GetPorts(child[1], ports, portType)
    
    def GetDisconnectedPorts(self, startOp, ports, portType, varType):
        """
        fill dictionary ports where the port is the key the paths are
        the values.  Only include the highest reference to the port that
        is of type portType and only disconnected
        """
        self.GetFilteredPorts(startOp, ports, portType, varType, 0)
            
    def GetFilteredPorts(self, startOp, ports, portType, varType, connStatus=0):
        """
        fill dictionary ports where the port is the key the paths are
        the values.  Only include the highest reference to the port that
        is of type portType.
        connStatus = 0 for disconnected
        connStatus = 1 for connected
        connStatus = 2 for both, connected and disconnected
        """
        #if connStatus == 0:
            #self.GetDisconnectedPorts(startOp, ports, portType, varType)
            #return
        #else:
        noneType = Ports.SIGNAL_TYPE_NONE
        for port in startOp.GetPorts(portType):
            conn = port.GetConnection()
            if not ports.has_key(port):
                if connStatus == 2 or (connStatus == 0 and not conn) or (connStatus == 1 and conn):
                    if not portType & SIG:
                        ports[port] = port.GetPath()
                    else:
                        thisType = port.GetSignalType()
                        if (varType == thisType and thisType != noneType) or \
                           (varType == noneType and thisType != noneType)or \
                           (varType != noneType and thisType == noneType):
                            ports[port] = port.GetPath()
        
        for child in startOp.GetChildUnitOps():
            self.GetFilteredPorts(child[1], ports, portType, varType, connStatus)
            
            
            
    def ChangePropPkgWindow(self):
        self.MainDialogForThCaseWindow(1)
            
    def CreateThCaseWindow(self):
        self.MainDialogForThCaseWindow(0)
        
    def MainDialogForThCaseWindow(self, usage=0):    
        """
        pop up window for changing prop pkg or creating thermo cases
        usage = 0 -> Create
        usage = 1 -> Change
        """
        
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        if usage: self.SendTop(session.msg('WebChangePropPkg'))
        else: self.SendTop(session.msg('WebCreateThermoCase'))
        
        print """
        <script>
        function AddThermoCase(form) {
            var cmd = opener.parent.command.document.command.cmd;
        """

        if not usage:
            print r"""
    
                var thname = form['thname'].value;
                if( thname == '' ) {
                    alert("%s");
                    return false;
                }
            """ % session.msg('WebNameNeeded')
        
        print r"""
            
            cmd.focus();
            """
        if not usage:
            print r"""
            cmd.value = '$' + thname + ' = ';
            var selected = form['thprov'].selectedIndex;
            cmd.value += form['thprov'].options[selected].value + '.';   
            """
        else:
            print r"""
            cmd.value = 'package = '
            """
        print r"""
            var selected = form['vappkg'].selectedIndex;
            var vappkg = form['vappkg'].options[selected].value;
            var selected = form['liqpkg'].selectedIndex;
            var liqpkg = form['liqpkg'].options[selected].value;
            var selected = form['solpkg'].selectedIndex;
            var solpkg = form['solpkg'].options[selected].value;
            
            if( vappkg != null && vappkg != '')
            {
                cmd.value += vappkg + ' ';
            }
            if( liqpkg != null && liqpkg != '')
            {
                cmd.value += liqpkg + ' ';
            }
            if( solpkg != null && solpkg != '')
            {
                cmd.value += solpkg;
            }
            """
        if not usage:
            print r"""
            cmd.value += ';cd ' + thname;
            """
        print r"""
            cmd.form.submit();
            window.close();
        }
        </script>
        
        """
        
        print """
        </head><body bgcolor="%s">
          <form onSubmit="return AddThermoCase(this);">
            <table border=1>
        """ % HypoWinColor
            
        if not usage:
            print r"""
              <tr>
                <td>%s</td><td><input type=text name="thname" size=30></td>
              </tr>
        """ % session.msg('WebName')
        thAdmin = session.CommandInterface().thermoAdmin
        providers = thAdmin.GetAvThermoProviderNames()
        
        #Right now do it this way
        provider = providers[0]        

        if not usage:
            thAdmin = session.CommandInterface().thermoAdmin
            providers = thAdmin.GetAvThermoProviderNames()
            
            #Right now do it this way
            provider = providers[0]
            
            print """
              <tr>
                <td>%s</td><td><select name="thprov" style="WIDTH: 250px">
                """ % (session.msg('WebThermoProvider'))
            for prov in providers:
                print '<option value=%s>%s</option>' %(prov, prov)
            
            print """
                </select></td>
              </tr>
            """ 
            
        pkgs = thAdmin.GetAvPropPkgNames(provider)
        pkgs.sort()
        pkgs.insert(0, '')
        
        print """
          <tr>
            <td>%s</td><td><select name="vappkg" style="WIDTH: 250px">
        """ % (session.msg('WebVapPkg'),)
        for pkg in pkgs:
            print """
            <option value="%s">%s</option>
            """ %(pkg, pkg)
            
        print """
            </select></td>
          </tr>
        """

        print """
          <tr>
            <td>%s</td><td><select name="liqpkg" style="WIDTH: 250px">
        """ % (session.msg('WebLiqPkg'),)
        for pkg in pkgs:
            print """
            <option value="%s">%s</option>
            """ %(pkg, pkg)
            
        print """
            </select></td>
          </tr>
        """

        print """
          <tr>
            <td>%s</td><td><select name="solpkg" style="WIDTH: 250px">
        """ % (session.msg('WebSolPkg'),)
        for pkg in pkgs:
            print """
            <option value="%s">%s</option>
            """ %(pkg, pkg)
            
        print """
            </select></td>
          </tr>
        """
        
        print """
              <tr>
                <td colspan=2 align = center>
                  <input type=submit name="add" value="%s">
                </td>
              </tr>
            </table>
          </form>
        """ % (session.msg('WebChange'),)
        
        
        self.SendBottom()     
            
    def ConnectThermoWindow(self):
        """
        pop up window for port connection
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        self.SendTop(session.msg('WebConnectThermoTitle'))
        print """
            <script>
            function ConnectThermoTo(uoPath, thermoPath) {
                var cmd = opener.parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = uoPath + ' -> ' + thermoPath;
                cmd.form.submit();
                window.close();
            }

            function DisconnectThermo(uoPath) {
                var cmd = opener.parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = uoPath + ' -> ';
                cmd.form.submit();
                window.close();
           }
        """
        print """
            </script>
            </head>
            <body bgcolor="%s">
        """ % DialogWinColor

        uoPath = form['uo'].value
        root = session.s42cmd.root
        uo = session.s42cmd.GetObject(root, uoPath[1:])
        conn = uo.thCaseObj
        if conn:
            print '<b>'
            print session.msg('WebUOConnectedTo', (uoPath, UnitOperations.TH_ADMIN_KEYWORD + conn.name))
            print '</b><br>'
            print '''<a href="javascript:DisconnectThermo('%s');">%s</a><br>''' % (
                    uoPath, session.msg('WebJustDisconnect'))
            print session.msg('WebOrReconnect')
        else:
            print '<b>'
            print session.msg('WebConnectUOTo', uoPath)
            print '</b>'
        
        availableCases = {}
        thAdmin = session.s42cmd.thermoAdmin
        if thAdmin:
            for name, thCase in thAdmin.GetContents():
                if isinstance(thCase, ThermoAdmin.ThermoCase):
                    availableCases[UnitOperations.TH_ADMIN_KEYWORD + thCase.name] = thCase
        
        print '<table border=0>'

        thCasePaths = availableCases.keys()
        thCasePaths.sort()
        for thCasePath in thCasePaths:
            print "<tr><td>"
            print '''<a href="javascript:ConnectThermoTo('%s', '%s');">%s</a>. %s.%s</td></tr>''' % (
                    (uoPath, thCasePath, thCasePath, availableCases[thCasePath].provider, availableCases[thCasePath].package))
        print '</table>'        
        
        
        self.SendBottom()            
            
    def ConnectWindow(self):
        """
        pop up window for port connection
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        self.SendTop(session.msg('WebConnectTitle'))
        print """
            <script>
            function ConnectPortTo(portPath, connPath) {
                var cmd = opener.parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = portPath + ' -> ' + connPath;
                cmd.form.submit();
                window.close();
            }

            function DisconnectPort(portPath) {
                var cmd = opener.parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = portPath + ' -> ';
                cmd.form.submit();
                window.close();
           }
        """
        print """
            </script>
            </head>
            <body bgcolor="%s">
        """ % DialogWinColor
        
        portPath = form['port'].value
        root = session.s42cmd.root
        port = session.s42cmd.GetObject(root, portPath[1:])
        conn = port.GetConnection()
        if conn:
            print '<b>'
            print session.msg('WebPortConnectedTo', (portPath, conn.GetPath()))
            print '</b><br>'
            print '''<a href="javascript:DisconnectPort('%s');">%s</a><br>''' % (
                    portPath, session.msg('WebJustDisconnect'))
            print session.msg('WebOrReconnect')
        else:
            print '<b>'
            print session.msg('WebConnectPortTo', portPath)
            print '</b>'
            
        type = port.GetPortType()
        matchingType = type
        if matchingType & (IN|OUT):
            matchingType ^= (IN|OUT)    # reverse in/out flags
        availablePorts = {}
        if type & SIG:
            varType = port.GetSignalType()
        else:
            varType = None
        self.GetDisconnectedPorts(root, availablePorts, matchingType, varType)
        
        print '<table border=0>'

        if availablePorts.has_key(port):
            del availablePorts[port]  # remove port if it is there - can't connect to itself

        connPaths = availablePorts.values()
        connPaths.sort()
        for connPath in connPaths:
            print "<tr><td>"
            print '''<a href="javascript:ConnectPortTo('%s', '%s');">%s</a></td></tr>''' % (
                    (portPath, connPath, connPath))
        print '</table>'
        
        self.SendBottom()

    def SpecFromWindow(self):
        """
        pop up window for specifying  material port based on another port
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        self.SendTop(session.msg('WebSpecFrom'))
        print """
            <script>
            function SpecPortFrom(portPath, connPath) {
                var cmd = opener.parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = connPath + ' >> ' + portPath;
                cmd.form.submit();
                window.close();
            }
        """
        print """
            </script>
            </head>
            <body bgcolor="%s">
        """ % DialogWinColor
        
        portPath = form['port'].value
        root = session.s42cmd.root
        port = session.s42cmd.GetObject(root, portPath[1:])

        print '<b>'
        print session.msg('WebSpecFrom', portPath)
        print '</b>'
            
        type = port.GetPortType()

        availablePorts = {}
        getConnAndDisconn = 2
        self.GetFilteredPorts(root, availablePorts, MAT|IN|OUT, None, getConnAndDisconn)
        
        print '<table border=0>'

        if availablePorts.has_key(port):
            del availablePorts[port]  # remove port if it is there - can't connect to itself

        connPaths = availablePorts.values()
        connPaths.sort()
        for connPath in connPaths:
            print "<tr><td>"
            print '''<a href="javascript:SpecPortFrom('%s', '%s');">%s</a></td></tr>''' % (
                    (portPath, connPath, connPath))
        print '</table>'
        
        self.SendBottom()


    def HXProfileRequestWindow(self):
        """
        pop up window requesting heat echxanger profiles
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        self.SendTop(session.msg('WebTowerProfiles'))
        print """
            <script>
            function SetProfiles(form, hxPath) {
                var cmd = opener.parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = hxPath + '.Profiles = ' + form.hxprofiles.value;
                cmd.form.submit();
                window.close();
            }
            </script>
            </head>
            <body bgcolor="%s">
        """ % DialogWinColor

        hxPath = form['hx'].value
        root = session.s42cmd.root
        hx = session.s42cmd.GetObject(root, hxPath[1:])
        profiles = hx.GetObject('Profiles')
        if profiles:
            profiles = profiles.unitOp.GetParameterValue('Profiles')
        else:
            profiles = ''
        print '''<form name="HXProfilesForm" onSubmit="return SetProfiles(this, '%s');">''' % hxPath
        print '<b>%s</b>' % session.msg('WebTowerProfiles')
        print '<input type=text name="hxprofiles" value="%s" size=60><br>' % profiles
        print '<input type=submit value="%s">' % session.msg('WebEnter')
        print '<p>%s</p>' % session.msg('WebHXProfileHelp')
        self.SendBottom()
        
    def TowerProfileRequestWindow(self):
        """
        pop up window requesting tower profiles
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        self.SendTop(session.msg('WebTowerProfiles'))
        print """
            <script>
            function SetProfiles(form, towerPath) {
                var cmd = opener.parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = towerPath + '.Profiles = ' + form.twrprofiles.value;
                cmd.form.submit();
                window.close();
            }
            </script>
            </head>
            <body bgcolor="%s">
        """ % DialogWinColor

        towerPath = form['tower'].value
        root = session.s42cmd.root
        tower = session.s42cmd.GetObject(root, towerPath[1:])
        profiles = tower.GetObject('Profiles')
        if profiles:
            profiles = profiles.unitOp.GetParameterValue('Profiles')
        else:
            profiles = ''
        print '''<form name="TwrProfilesForm" onSubmit="return SetProfiles(this, '%s');">''' % towerPath
        print '<b>%s</b>' % session.msg('WebTowerProfiles')
        print '<input type=text name="twrprofiles" value="%s" size=60><br>' % profiles
        print '<input type=submit value="%s">' % session.msg('WebEnter')
        print '<p>%s</p>' % session.msg('WebTowerProfileHelp')
        self.SendBottom()        

    def StartSession(self):
        """
        start session and set up frames
        """
        if self.server.continueLoop == -1:
            # this is a way to ensure shutdown by services and daemons
            self.server.ShutDown()
            return

        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return
        
        self.session.infoCallBack.SetLanguage(self.session.user.language)
        self.session.CommandInterface().ProcessCommand('units %s' % self.session.user.units)
        fLog = open

        self.send_header("Content-type", "text/html")
        self.end_headers()

        print '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">\n'
        print "<html><head>\n"
        print "<title>%s</title>\n" % session.msg('WebSessionTitle')
        print '<frameset name="mainframe" rows="100,*">\n'
        print '<frame src="command?sid=%s" name="command">\n' % session.id
        print '<frameset name="colframe" cols="200,*">'
        print '<frame src="tree?sid=%s" name="tree">' % session.id
        print '<frameset name="rowframe" rows="*,100">\n'
        print '<frame src="display?sid=%s" name="display">\n' % session.id
        print '<frame src="docmd?sid=%s" name="output">\n' % session.id
        print '</frameset>'
        print '</frameset>'
        print '</body></html>\n'

    def Users(self):
        """
        add user form - for admin users only
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None or not (session.user.privilege & CAN_ADDUSER): return
        
        try:
            basePath = os.path.abspath(simbaConfig.get('Paths', 'basePath'))
        except:
            self.SendTop(session.msg('WebUsers'))
            print msg('WebNoConfig')
            self.SendBottom()
            return
        
        userInfoPath = basePath + os.sep + 'userinfo'
        if not os.path.exists(userInfoPath):
            os.mkdir(userInfoPath)

        errorMsg = ''

                   
        
        if form.has_key('add'):
            adduser = 0
            shutdown = 0
            upload = 0
            seesession = 0
            savesession = 0
            
            if form.has_key('adduser'):
                adduser = 1
                    
            if form.has_key('shutdown'):
                shutdown = 2
                    
            if form.has_key('upload'):
                upload = 4         
                    
            if form.has_key('seesession'):
                seesession = 8         
                
            if form.has_key('savesession'):
                savesession = 16    
            
            try:
                username =  form['username'].value
                passwd =    form['passwd'].value
                # can't add a privilege you don't have
                privilege = adduser + shutdown + upload + seesession + savesession
                fullname =  form['fullname'].value
                group =     form['groupname'].value
                
                # create user and call server to create the necessary files
                user = Sim42User(username, passwd, privilege, fullname, group)
                errorMsg = self.server.AddUser(user)
            except:
                errorMsg = session.msg('WebUserAddFailed')
                
        elif form.has_key('delete'):
            try:
                username = form['delete'].value
                self.server.RemoveUser(username)
                errorMsg = session.msg('WebRemovedUser', username)
            except:
                errorMsg = session.msg('WebRemoveUserFailed', username)
            
        elif form.has_key('edit'):
            username = form['edit'].value
            user = self.server.GetUserInfo(username)
            if user:
                self.UserForm(session, user, session.msg('WebUpdate'))
            return
        
        elif form.has_key('new'):
            user = Sim42User('', '', 0, '', '')
            self.UserForm(session, user, session.msg('WebAdd'))
            return

        self.SendTop(session.msg('WebUsers'))

        if errorMsg:
            print '<h3>%s</h3>' % errorMsg
        print '<a href="users?sid=%d&new=new">%s</a><br>' % (session.id, session.msg('WebAddUser'))
        print '<table>'
        users = os.listdir(userInfoPath)
        for username in users:
            print '<tr><td>%s</td><td><a href="users?sid=%d&edit=%s">%s</a></td>' % (
                        username, session.id, username, session.msg('WebEdit'))
            print '<td><a href="users?sid=%d&delete=%s">%s</a></td></tr>' % (
                        session.id, username, session.msg('WebDelete'))
        print '</table>'
        self.SendBottom()
            
    def UserForm(self, session, user, submitMsg):
        """
        User information form
        """
        self.SendTop(session.msg('WebUser'))
        print '''
        <script>
        function checkpw(form) {
            if( form.passwd.value == '' || form.passwd.value != form.passwd2.value ) {
                alert('%s');
                return false;
            }
            return true;
        }
        </script>''' % session.msg('WebPasswordMatch')
            

        print '</head><body bgcolor="%s">' % DisplayBGColor
        self.StartForm('userform', 'users', '_top')

        print '<table width=100%>'
        print '<tr><td>%s</td><td><input type=text name="username" size=40 value="%s"></td></tr>' % (
                    session.msg('WebUserName'), user.name)
        print '<tr><td>%s</td><td><input type=text name="fullname" size=40 value="%s"></td></tr>' % (
                    session.msg('WebFullName'), user.fullname)
        print '<tr><td>%s</td><td><input type=text name="groupname" size=40 value="%s"></td></tr>' % (
                    session.msg('WebGroupName'), user.group)
        print '<tr><td>%s</td><td><input type=password name="passwd" size=40 value="%s"></td></tr>' % (
                    session.msg('WebPassword'), user.password)
        print '<tr><td>%s</td><td><input type=password name="passwd2" size=40 value="%s"></td></tr>' % (
                    session.msg('WebConfirmPassword'), user.password)   
        print '<tr><td>%s</td><td colspan=2><h3><u>%s</u></h3></td></tr>' % (session.msg('WebPrivilege'), session.msg('WebUserCan'))

        print '<tr><td>&nbsp;</td><td><input type=checkbox name="adduser" '
        if user.privilege & CAN_ADDUSER:        
            print 'CHECKED'
        print ' >%s</td></tr>' % session.msg('WebAddUser')
        
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="shutdown" '
        if user.privilege & CAN_SHUTDOWN:         
            print 'CHECKED'
        print '>%s</td></tr>' % session.msg('WebQuit')
            
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="upload" '
        if user.privilege & CAN_UPLOAD:         
            print 'CHECKED'
        print ' >%s</td></tr>' % session.msg('WebUpload')
 
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="seesession" '
        if user.privilege & CAN_SEE_SESSIONS:                 
            print 'CHECKED'
        print '>%s</td></tr>' % session.msg('WebSeeSessions')
        
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="savesession" '
        if user.privilege & CAN_RESTART_SESSION:         
            print 'CHECKED'
        print '>%s</td></tr>' % session.msg('WebSaveSessions') 
              
        print '<tr><td colspan=2 align="center"><input type=submit name="add" value="%s"></td></tr>' % submitMsg
        print '</table></form>'
        print '</body>'
        self.SendBottom()

    def Sessions(self):
        """
        shows and allows killing of self.StartForms
        """       
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None or not (session.user.privilege & CAN_SEE_SESSIONS): return
        
        if form.has_key('kill'):
            killId = int(form['kill'].value)
            self.server.RemoveSession(killId)

        self.SendTop('WebSessions')
        print '</head><body bgcolor="%s">' % DisplayBGColor
        print '<table>'
        for sId in self.server.sessions:
            s = self.server.sessions[sId]
            print '<tr><td>%d</td>' % sId
            print '<td>%s</td><td>%s</td>' % (s.user.name, time.ctime(s.lastAccessed))
            print '<td><a href="sessions?sid=%d&kill=%d">%s</a></td></tr>' % (
                                       session.id, sId, session.msg('WebKill'))
        print '</table>'
        self.SendBottom()

    def Preferences(self):
        form = self.GetForm()
        session = self.GetSession(form)
        username = session.GetUser().name
        historyAll = 0
        try:
            BasePath = os.path.abspath(simbaConfig.get('Paths', 'basePath'))
            userInfoPath = BasePath + os.sep + 'userinfo'
            if not os.path.exists(userInfoPath):
                return None
        except:
            return None
        
        userInfoFile = os.path.abspath(userInfoPath + os.sep + username)        
        
        if session is None or not (session.user.privilege & CAN_UPLOAD): return
        
        self.SendTop(session.msg('WebPreferences'))
        print '''
        <script>
        function checkpw(form) {
            if( form.passwd.value == '' || form.passwd.value != form.passwd2.value ) {
                alert('%s');
                return false;        session = self.GetSession(form)
            }
            return true;
        }   
        </script>''' % session.msg('WebPasswordMatch')
        
        print '</head><body bgcolor="%s">' % DisplayBGColor
        self.StartForm('prefform', 'preferences', '_top')
        try:localPath = simbaConfig.get('Paths', 'localPath')
        except: localPath = ''
        try: basePath = simbaConfig.get('Paths', 'basePath')
        except: basePath = ''
        try: sessionSleepTime = simbaConfig.get('Sessions', 'sessionPruneSleepTime')
        except: sessionSleepTime = '60' 
        try: maxInactiveSessionTime = simbaConfig.get('Sessions', 'maxInactiveSessionTime')
        except: maxInactiveSessionTime = '3600'
        try: langmenu = simbaConfig.get('Language', 'defaultLanguage')
        except: langmenu = 'English'
        
        if form.has_key('closewindow'):         
         print '<script>window.close()</script>'
         
        if form.has_key('change'):
            molefractions = 0
            massfractions = 0
            volfractions = 0
            moleflows = 0
            massflows = 0
            stdlvolflows = 0
        
            if form.has_key('molefractions'):
                molefractions = 1
            
            if form.has_key('massfractions'):
                massfractions = 2

            if form.has_key('moleflows'):
                moleflows = 4
                
            if form.has_key('massflows'):
                massflows = 8
                
            if form.has_key('volfractions'):
                volfractions = 16
                
            if form.has_key('stdlvolflows'):
                stdlvolflows = 32
                
            session.user.composition = molefractions + massfractions + moleflows + massflows + volfractions + stdlvolflows
        
            if session.user.privilege & CAN_SHUTDOWN:
                localPath = form['localpath'].value
                basePath = form['basepath'].value
                sessionsleeptime = form['sessionsleeptime'].value
                maxInactiveSessionTime = form['maxInactiveSessionTime'].value
                defaultLanguage = form['langmenu'].value
                if not simbaConfig.has_section('Paths'): simbaConfig.add_section('Paths')
                if not simbaConfig.has_section('Sessions'): simbaConfig.add_section('Sessions')
                if not simbaConfig.has_section('Language'): simbaConfig.add_section('Language')
                simbaConfig.set('Paths', 'localPath', os.path.abspath(localPath))
                simbaConfig.set('Paths', 'basePath', os.path.abspath(basePath))
                simbaConfig.set('Sessions', 'sessionPruneSleepTime', sessionsleeptime)
                simbaConfig.set('Sessions', 'maxInactiveSessionTime', maxInactiveSessionTime)
                simbaConfig.set('Language', 'defaultLanguage', defaultLanguage)             
                self.server.LoadConfig()
                
                f = open(self.server.runPath + os.sep + 'simba.conf', 'w')
                simbaConfig.write(f)
                f.close()
                
            try:
                session.user.tablewidth = int(form['tablewidth'].value)
            except:
                print "<script> alert('%s'); </script>" % session.msg('WebInvalidTableWidth')  
            try:
                session.user.historyNumber = int(form['historynumber'].value)
            except:
                print "<script> alert('%s'); </script>" % session.msg('WebInvalidTableWidth')     
            try:
                session.user.rowsperpage = int(form['rowsperpage'].value)
            except:
                print "<script> alert('%s'); </script>" % session.msg('WebInvalidTableWidth')                    
                
            if form.has_key('orall'):
                historyAll = 1
            session.user.historyAll = historyAll
                
            session.user.language = form['userlangmenu'].value
            session.user.units = form['unitmenu'].value
            self.server.SaveUserInfo(session.user)
            print '''<script>
                        opener.parent.command.outputHistory.setNumberSlots(%d);
                      </script>''' % session.user.historyNumber
            print '<b><center>%s</center></b><br>' % (session.msg('WebConfigUpdate', time.strftime('%H:%M %Z', time.localtime())))
        
        print '<b><center><u>%s %s</u></center></b><br>' % (session.msg('WebOptionsFor'), session.user.name)       
        print '<table align=center><tr><td><table>'
        try:
            tableWidth = session.user.tablewidth
        except:
            tableWidth = 4
            
        try: 
            rowsperpage = session.user.rowsperpage
        except:
            rowsperpage = 0  
            
        print '<tr><td>%s</td><td><input type=text name="tablewidth" size=20 value="%s"></td></tr>' % (session.msg('WebTableWidth'), tableWidth)        
        print '<tr><td>%s</td><td width="150"><select name="unitmenu" onchange="HandleUnitMenu(this)" style="WIDTH: 150px">'  % (session.msg('WebUserUnitSet'))
        uSys = session.CommandInterface().units
        for u in uSys.GetSetNames():
        
            print '<option value="%s"' % u,
            if u == session.user.units:
                print 'selected'
            
            print '>%s</option>' %(u)
        print '</select></td></tr>'
        print '<tr><td>%s</td><td width="150"><select name="userlangmenu" onchange="HandleLangMenu(this)" style="WIDTH: 150px">'  % (session.msg('WebUserLanguage'))
        dct = CommandInterface.MessageHandler.GetSupportedLanguages()
        lst = list(dct['languages'])
        for lang in lst:
            print '<option value="%s"' % lang,
            if session.user.language == lang:
                print 'selected'
            print '>%s</option>' %(lang)
        print '</select></td></tr>'
        try:
            historyNumber = session.user.historyNumber
        except:
            historyNumber = 50    
            
        try:
            session.user.historyAll
        except:
            session.user.historyAll = 0
            
        print '<tr><td>%s</td><td><input type=text name="historynumber" size=10 value="%s"> <input type=checkbox name="orall" ' % (session.msg('WebHistoryNumber'), historyNumber)     
        if session.user.historyAll == 1: 
            print 'CHECKED'
        print '>%s</td></tr></td>' % session.msg('WebOrAll')   
        
        print '<tr><td>%s</td><td><input type=text name="rowsperpage" size=10 value="%s"></td></tr></table></td>' % (session.msg('WebRowsPerPage'), rowsperpage)
        
        print '<td><table><tr><td>%s</td>' % session.msg('WebComposition')
        print '<td><input type=checkbox name="molefractions" ' 
        try:
            composition = session.user.composition
        except:
            composition = 0

        if composition & COMPMOLEFRAC: 
            print 'CHECKED'
        print '>%s</td></tr>' % (session.msg('WebMoleFraction'))
        
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="massfractions" ' 
        if composition & COMPMASSFRAC: 
            print 'CHECKED'
        print '>%s</td></tr>' % (session.msg('WebMassFraction'))
        
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="volfractions" ' 
        if composition & COMPVOLFRAC: 
            print 'CHECKED'
        print '>%s</td></tr>' % (session.msg('WebVolFraction'))
        
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="moleflows" ' 
        if composition & COMPMOLEFLOW: 
            print 'CHECKED'
        print '>%s</td></tr>' % (session.msg('WebCmpMoleFlows'))
        
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="massflows" ' 
        if composition & COMPMASSFLOW: 
            print 'CHECKED'
        print '>%s</td></tr>' % (session.msg('WebCmpMassFlows'))
        
        print '<tr><td>&nbsp;</td><td><input type=checkbox name="stdlvolflows" ' 
        if composition & COMPSTDLVOLFLOW: 
            print 'CHECKED'
        print '>%s</td></tr></table>' % (session.msg('WebCmpStdLiqVolFlows'))    
        
        if session.user.privilege & CAN_SHUTDOWN:
            print '</table>'
            print '<hr width=100%>'
            print '<b><center><u>%s</u></center></b><br>' % (session.msg('WebMultiUserOptions'))
            print '<table width= 100%>'
            print '<tr><td>%s</td><td><input type=text name="localpath" size=70 value="%s"></td></tr>' % (session.msg('WebLocalPath'), localPath)
            print '<tr><td>%s</td><td><input type=text name="basepath" size=70 value="%s"></td></tr>' % (session.msg('WebBasePath'), basePath)
            print '<tr><td>%s</td><td><input type=text name="sessionsleeptime" size=70 value="%s"></td></tr>' % (session.msg('WebSessionSleepTime'), sessionSleepTime)
            print '<tr><td>%s</td><td><input type=text name="maxInactiveSessionTime" size=70 value="%s"></td></tr>' % (session.msg('WebMaxInactiveTime'), maxInactiveSessionTime)
            print '<tr><td>%s</td><td width="150"><select name="langmenu" onchange="HandleLangMenu(this)" style="WIDTH: 150px">'  % (session.msg('WebDefaultLanguage'))
            dct = CommandInterface.MessageHandler.GetSupportedLanguages()
            lst = list(dct['languages'])
            for lang in lst:
                print '<option value="%s"' % lang,
                if langmenu == lang:
                    print 'selected'
                
                print '>%s</option>' %(lang)
            print '</select></td></tr>'

        print '<tr><td colspan=2 align="center"><input type=submit name="change" value="%s">' % session.msg('WebUpdate')
        print '<input type=submit name="closewindow" value="%s" onclick="window.close();"></td></tr>' % session.msg('WebClose')
        print '</table></form>'
        print '</body>'
        self.SendBottom()
        
    def HXProfilePlot(self):
        """
        output graph of hx profile
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return
        session.ShowHXPlots(form['curve'].value)        
        
        
    def TowerProfilePlot(self):
        """
        output graph of tower profile
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return
        session.ShowTowerPlots(form['curve'].value)
        
    def EnvelopePlot(self):
        """
        output graph of PT Envelope
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        session.ShowEnvelopePlot(form['env'].value)
        
    def VecPropsPlot(self):
        """
        output graph of boiling curve
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return
        session.ShowVectorPropsPlots(form['curve'].value)

    def PFD(self):
        """
        create display pfd
        """
        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return
        
        self.SendTop(session.msg('WebPFD'))
        import simbapfd
        flowsheet = session.s42cmd.currentObj
        while not isinstance(flowsheet, UnitOperations.UnitOperation) or (
              len(flowsheet.GetChildUnitOps()) == 0 and flowsheet.GetParent()):
            if hasattr(flowsheet, 'GetParent'):
                flowsheet = flowsheet.GetParent()
            else:
                flowsheet = session.sim42cmd.baseFlowSheet
            
        session.pfd = simbapfd.SimbaPFD(flowsheet)
        print """
            <script>
            function DisplayUop(uopPath) {
                var cmd = opener.parent.command.document.command.cmd;
                cmd.focus();
                cmd.value = 'cd ' + uopPath;
                cmd.form.submit();
                opener.parent.focus();
            }
            function PathClick() {
                opener.parent.focus()
            }
            </script>
            """
        print session.GetPathLinks(flowsheet) + '<br>'
        print '<map name="uopmap">'
        session.pfd.CreateImage()
        print '<img src="pfdImage?sid=%d" usemap="#uopmap" border=0>' % session.id
        print "</map>"

        self.SendBottom()

    def PFDImage(self):
        """
        produce image 
        """
        if not graph42: return

        form = self.GetForm()
        session = self.GetSession(form)
        if session is None: return

        session.pfd.OutputImage(session)    


class SimbaCallBack(CommandInterface.InfoCallBack):
    def __init__(self, session):
        self.session = session
        super(SimbaCallBack, self).__init__()

    def handleMessage(self, message, args, msgType=None):
        """thread safe (??) message handler"""
        if not MessageHandler.IsIgnored(message):
            globalLock.acquire()  # is this really needed?
            try:
                wf = self.session.handler.wfile
                msg = MessageHandler.RenderMessage(message, args, self.languageDict)
                wf.write('%s\n' % msg)
                if msgType == MessageHandler.errorMessage:
                    self.session.errorMessages.append(msg)
            finally:
                globalLock.release()

class DoNothingCallBack(CommandInterface.InfoCallBack):
    """
    used when killing sessions and message has no where to go
    """
    def handleMessage(self, message, args, msgType=None):
        """ignore messages"""
        return


globalLock = None

def StartServer(server):
    """
    create a global lock and start server
    """

    global globalLock
    globalLock = threading.RLock()
    CommandInterface.globalLock = globalLock

    #MessageHandler.IgnoreMessage('SolvingOp')
    MessageHandler.IgnoreMessage('BeforePortDisconnect')    
    MessageHandler.IgnoreMessage('AfterPortDisconnect')    
            
    
    sa = server.socket.getsockname()
    server.log_message("Serving HTTP on port %s ... %s\n" %
                       (sa[1], time.asctime(time.gmtime(time.time()))))

    if server.localOnly:
        # if run locally, try launching browser too
        try:
            webbrowser.open('http://127.0.0.1/sim42')
        except:
            pass

    server.serve_forever()


def run():
    """
    when run from the command line, the server by default runs in local user only mode
    from port 80.  The following flags can change that:
        -p nn  - use port number nn
        -m     - run in multiuser mode
    """
    port = 80
    localOnly = 1
    if sys.argv[1:]:
        lastArg = len(sys.argv)
        nArg = 1
        while nArg < lastArg:
            if sys.argv[nArg] == '-p':
                port = int(sys.argv[nArg + 1])
                nArg += 1
            elif sys.argv[nArg] == '-m':
                localOnly = 0
            nArg += 1
    
    server = Sim42Server(port=port, localOnly=localOnly)
    StartServer(server)

import gc    
def dump_garbage(  ):
    """
    show us what the garbage is about
    """
    # Force collection
    print "\nGARBAGE:"
    gc.collect(  )

    print "\nGARBAGE OBJECTS:"
    for x in gc.garbage:
        s = str(x)
        print type(x),
        if len(s) > 120: s = s[:117]+'...'
        try:
            print ' Path:%s ' % x.GetPath()
        except:
            try:
                print ' Name:%s ' % x.name
            except:
                print ' No Name'
                                
        print 'o="%s"' % s
        #for y in  gc.get_referrers(x):
            #s = str(y)
            #if len(s) > 120: s = s[:117]+'...'
            #print 'Referrer: ', type(y),
            #try:
                #print ' Path:%s ' % y.GetPath()
            #except:
                #try:
                    #print ' Name:%s ' % y.name
                #except:
                    #print ' No Name'
                
            #print 'o="%s"\n' % s

CMP_FILTERS = {}
CMP_FILTERS['WebGasProcComponents'] = ['METHANE', 'ETHANE', 'PROPANE', 'ISOBUTANE',
                                      'n-BUTANE', 'ISOPENTANE', 'n-PENTANE', 'n-HEXANE',
                                      'n-HEPTANE', 'n-OCTANE', 'n-NONANE', 'n-DECANE',
                                      'NITROGEN', 'CARBON DIOXIDE', 'HYDROGEN SULFIDE',
                                      'WATER']
CMP_FILTERS['EthanolProcessing'] = ['METHANOL', 'ETHANOL', 'WATER']
CMP_FILTERS['Air'] = ['OXYGEN', 'NITROGEN', 'CARBON DIOXIDE', 'WATER', 'AIR']
CMP_FILTERS['GasDehydration'] = ['WATER', 'NITROGEN', 'CARBON DIOXIDE', 'METHANE', 
                             'ETHANE', 'PROPANE', 'ISOBUTANE', 'N-BUTANE', 'ISOPENTANE',
                             'N-PENTANE', 'N-HEXANE', 'N-OCTANE', 'BENZENE', 'TOLUENE', 
                             'ETHYLBENZENE', 'O-XYLENE', 'TRIETHYLENE GLYCOL']            
CMP_FILTERS['MethanolRemoval'] = ['WATER', 'TOLUENE', 'n-HEPTANE', 'ACETONE', 'ETHYL_ACETATE', 'METHANOL']
CMP_FILTERS['UreaProd'] = ['WATER', 'CARBON DIOXIDE', 'AMMONIA', 'UREA']

SUGGESTED_INFO = {}
SUGGESTED_INFO['ThCase'] = "Create a thermodynamic case. To do it: select a property package from the Add Thermo Package menu"
SUGGESTED_INFO['Compounds'] = "Add compounds. Click on the list of compounds. If the compound is not there, try changing the filter of compouds or else use the complete list"
SUGGESTED_INFO['UO'] = "Add unit operations. Click on / (Flowsheet) from the tree in the left and then select Add Unit Operation"
SUGGESTED_INFO['PortInfo'] = "Connect port or add properties to it. To connect click on the -> link. To add properties click on the"

TWR_PROP_TYPES = [T_VAR, CP_VAR, CV_VAR, DPDVT_VAR, ENERGY_VAR, GIBBSFREEENERGY_VAR, H_VAR, HELMHOLTZENERGY_VAR,
                  IDEALGASCP_VAR, IDEALGASENTHALPY_VAR, IDEALGASENTROPY_VAR, IDEALGASFORMATION_VAR,
                  IDEALGASGIBBS_VAR, INTERNALENERGY_VAR, ISOTHERMALCOMPRESSIBILITY_VAR, KINEMATICVISCOSITY_VAR,
                  MASSDEN_VAR, MASSFLOW_VAR, MECHANICALZFACTOR_VAR, MOLARV_VAR, MOLEFLOW_VAR, MOLEWT_VAR,
                  PH_VAR, RESIDUALCP_VAR, RESIDUALCV_VAR, RESIDUALENTHALPY_VAR, RESIDUALENTROPY_VAR,
                  S_VAR, SPEEDOFSOUND_VAR, STDLIQVOL_VAR, STDVOLFLOW_VAR, SURFACETENSION_VAR,
                  THERMOCONDUCTIVITY_VAR, VISCOSITY_VAR, VOLFLOW_VAR, ZFACTOR_VAR]


if __name__ == "__main__":
    gc.enable(  )
    #gc.set_debug(gc.DEBUG_LEAK)
    
    optimize = 0
    if optimize:
        try:
            import psyco
            ##psyco.log("C:\\sim\\simba\\logpsyco.txt", 'w', 10000)
            #psyco.full()
            ##psyco.profile()
            #b = psyco.bind
            
            #psyco.bind(Tower.Tower.SolveFlowMatrix, 10)
            #psyco.bind(Tower.Tower.CalcJacobian, 10)
            #psyco.bind(Tower.Tower.InitOuterProperties, 10)
            #psyco.bind(Tower.Tower.SpecErrors, 10)
            
            psyco.bind(UnitOperations.UnitOperation.IsForgetting)
            psyco.bind(UnitOperations.UnitOperation.PushSolveOp)
            psyco.bind(UnitOperations.UnitOperation.PushForgetOp)
            psyco.bind(UnitOperations.UnitOperation.GetObject)
            psyco.bind(UnitOperations.UnitOperation.GetThermo)
            psyco.bind(UnitOperations.UnitOperation.GetParameterValue)
            psyco.bind(UnitOperations.UnitOperation.PushResetCalcPort)
            psyco.bind(UnitOperations.UnitOperation.ShortestPortPath)
            
            psyco.bind(Flowsheet.Flowsheet.IsForgetting)
            psyco.bind(Flowsheet.Flowsheet.PushSolveOp)
            psyco.bind(Flowsheet.Flowsheet.PushForgetOp)
            psyco.bind(Flowsheet.Flowsheet.Solver)
            psyco.bind(Flowsheet.Flowsheet.GetParameterValue)
            psyco.bind(Flowsheet.Flowsheet.PushResetCalcPort)
            psyco.bind(Flowsheet.Flowsheet.GetTolerance)
            
            psyco.bind(Ports.Port.GetParentOp)
            psyco.bind(Ports.Port.UpdateConnection)
            psyco.bind(Ports.Port.PropertyModified)
            psyco.bind(Ports.Port.GetLocalValue)
            psyco.bind(Ports.Port.SetPropValue)
            psyco.bind(Ports.Port.GetNuKnownProps)
            psyco.bind(Ports.Port.Forget)
            psyco.bind(Ports.Port.GetObject)
            
            psyco.bind(Ports.Port_Material.CalcFlows)
            psyco.bind(Ports.Port_Material.AssignFlashResults)
            psyco.bind(Ports.Port_Material.ReadyToFlash)
            
            psyco.bind(BasicProperty.Forget)
            psyco.bind(BasicProperty.GetValue)
            psyco.bind(BasicProperty.SetValue)
            psyco.bind(BasicProperty.GetCalcStatus)
            psyco.bind(BasicProperty.CheckTolerance)
            
            #psyco.bind(Balance.Balance.DoBalance)
            #psyco.bind(Balance.Balance.DoMoleBalance)
            

            
            
        except:
            pass
    
    #import profile
    run()
    
    #profile.run('run()', "C:\\sim\\simba\\logprof.txt")
    #dump_garbage(  )    
    
