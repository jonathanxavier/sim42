'''
This module is an attempt to implement the simba server as a Win32 service

You must create a module called serviceconfig with path and port defined.
The path variable should be the path to the folder containing the simba.conf file

Then run this file with the parameter install

   python simbaservice.py install
   
You will probably have to use the services tool in Windows to designate the appropriate log on
for the service and start the service.

Note that if a user has shut down privilege and shuts the server down, the service will stop

The service can be uninstalled, once stopped, by

   python simbaservice.py remove
'''

import os, sys
import win32serviceutil
import win32service
import urllib

try:
    from serviceconfig import *
except:
    print 'Could not find serviceconfig.py file'
    sys.exit(1)

os.chdir(path)
from sim.simba import simba

class SimbaServiceServer(simba.Sim42Server):
    """
    Override the log_message handler
    """
    def log_message(self, message):
        import servicemanager
        servicemanager.LogInfoMsg(message)

class SimbaService(win32serviceutil.ServiceFramework):
    '''
    Simple server mechanism for NT
    '''
    _svc_name_ = "Simba"
    _svc_display_name_ = "Simba Server"
    def __init__(self, args):            
        win32serviceutil.ServiceFramework.__init__(self, args)

    def SvcStop(self):
        # Before we do anything, tell the SCM we are starting the stop process.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.httpd.continueLoop = -1

        f = urllib.urlopen('http://localhost:%d/sim42' % port)
        lines = f.read()
        f.close()
    
    def SvcDoRun(self):
        self.httpd = SimbaServiceServer(port=port, localOnly=0, runPath=path)
        import servicemanager
        servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE, 
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ''))
        simba.StartServer(self.httpd)
        servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE, 
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ''))
    
if __name__=='__main__':
    win32serviceutil.HandleCommandLine(SimbaService)
    #server = SimbaServiceServer()
    #u = server.GetUserInfo('craig')
    #print u
    

    
