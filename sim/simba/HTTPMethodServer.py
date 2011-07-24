import CGIHTTPServer, BaseHTTPServer, SimpleHTTPServer, SocketServer
from StringIO import StringIO
import sys, os, urllib
import cgi, cgitb, select

# determine which mixin to use: prefer threading, fall back to forking.
try:
  import thread
  mixin = SocketServer.ThreadingMixIn
except ImportError:
  if not hasattr(os, 'fork'):
    print "ERROR: your platform does not support threading OR forking."
    sys.exit(1)
  mixin = SocketServer.ForkingMixIn

#class HTTPMethodHandler(mixin, CGIHTTPServer.CGIHTTPRequestHandler):
class HTTPMethodHandler(CGIHTTPServer.CGIHTTPRequestHandler):
    """
    http server using internal cgi methods
    """
    def __init__(self, request, client_address, server, routines=None):
        """
        set up the methods allowed as cgi scripts
        derived classes should pass routines - a list of acceptable cgi methods
        """
        
        if routines:
            self.routines = routines
        else:
            self.routines = {
                             "test": HTTPMethodHandler.test
                             }

            
        CGIHTTPServer.CGIHTTPRequestHandler.__init__(self, request, client_address, server)

    def is_cgi(self):
        """
        see whether self.path corresponds to one of the routines in
        self.routines.  Overload this to always return 1 if you don't want
        files served.
        """
        
        path = self.path[1:]
        for routine in self.routines:
            i = len(routine)
            if path[:i] == routine and (not path[i:] or path[i] == '?'):
                return 1
        return 0
    
    def run_cgi(self):
        """Execute a CGI script."""
        routine = self.path[1:]
        i = routine.rfind('?')
        if i >= 0:
            routine, query = routine[:i], routine[i+1:]
        else:
            query = ''

        if not self.routines.has_key(routine):
            self.send_error(404, "No such CGI script (%s)" % `routine`)
            return

        # Reference: http://hoohoo.ncsa.uiuc.edu/cgi/env.html
        # XXX Much of the following could be prepared ahead of time!
        env = {}
        env['SERVER_SOFTWARE'] = self.version_string()
        env['SERVER_NAME'] = self.server.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PROTOCOL'] = self.protocol_version
        env['SERVER_PORT'] = str(self.server.server_port)
        env['REQUEST_METHOD'] = self.command
        uqroutine = urllib.unquote(routine)
        env['PATH_INFO'] = uqroutine
        env['PATH_TRANSLATED'] = self.translate_path(uqroutine)
        env['SCRIPT_NAME'] = uqroutine
        if query:
            env['QUERY_STRING'] = query
        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host
        env['REMOTE_ADDR'] = self.client_address[0]
        # XXX AUTH_TYPE
        # XXX REMOTE_USER
        # XXX REMOTE_IDENT
        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader
        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        accept = []
        for line in self.headers.getallmatchingheaders('accept'):
            if line[:1] in "\t\n\r ":
                accept.append(line.strip())
            else:
                accept = accept + line[7:].split(',')
        env['HTTP_ACCEPT'] = ','.join(accept)
        ua = self.headers.getheader('user-agent')
        if ua:
            env['HTTP_USER_AGENT'] = ua
        co = filter(None, self.headers.getheaders('cookie'))
        if co:
            env['HTTP_COOKIE'] = ', '.join(co)
        # XXX Other HTTP_* headers

        # Since we're setting the env in the parent, provide empty
        # values to override previously set values
        for k in ('QUERY_STRING', 'REMOTE_HOST', 'CONTENT_LENGTH',
                  'HTTP_USER_AGENT', 'HTTP_COOKIE'):
            env.setdefault(k, "")

        self.send_response(200, "Script output follows")

        decoded_query = query.replace('+', ' ')

        os.environ.update(env)
        try:
            if '=' not in decoded_query:
                argvAppend = decoded_query
            else:
                argvAppend = None
            self.DoRoutine(argvAppend, routine)
        except SystemExit, sts:
            self.log_error("CGI script exit status %s", str(sts))
        else:
            self.log_message("CGI script exited OK")
        while select.select([self.rfile], [], [], 0)[0]:
            try:
                waste = self.rfile.read(1)
            except:
                break; # if there is a read error, just abandon conversation

    def DoRoutine(self, argvAppend, routine):
      """ separate method so it can be overloaded """
      save_argv = sys.argv
      save_stdin = sys.stdin
      save_stdout = sys.stdout
      save_stderr = sys.stderr

      sys.argv = [routine]
      if argvAppend:
          sys.argv.append(argvAppend)
      sys.stdout = self.wfile
      sys.stdin = self.rfile

      try:
          self.routines[routine](self)
      finally:
          sys.argv = save_argv
          sys.stdin = save_stdin
          sys.stdout = save_stdout
          sys.stderr = save_stderr
      
    def test(self):
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        cgitb.enable()
        form = cgi.FieldStorage()
        stuff = form.getfirst("stuff", "Unknown")
        name = form.getfirst("name", "Name")
        
        print "<html><head>\n"
        print "<title>Test script for %s</title>\n" % self.path
        print "</head><body>\n"
        print "<h2>Test script for for %s</h2>\n" % self.path
        print '''
        <form action="test" method="POST">
            <input type=text name="stuff" value="%s"><br>
            <input type=text name="name" value="%s"><br>
            <input type=submit name="done" value="OK">
        </form>
        <p>
        <a href="test?name=Joe">Click here to set name to Joe.</a><br>
        Contents:
        ''' % (stuff, name)
        print 'Stuff is %s<br>Name is %s\n' % (stuff, name)
            
        print "</body></html>\n"

def runserver(port=8000):
    server_address = ('', port)

    httpd = BaseHTTPServer.HTTPServer(server_address, HTTPMethodHandler)

    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()


if __name__ == '__main__':
    runserver()
    

