import sim.solver.languages
import imp, sys, re

class Messages:
    """
    Message handling class
    """
    def __init__(self, language = 'English'):
        """
        load the message dictionaries
        """
        self.messageModules = []
        self.ignored = {}
        self.languages = {}
        self.LoadMessageModule(sim.solver.languages, self.languages)
        self.SetCurrentLanguage(language)
        self.infoMessage = 'Info'
        self.errorMessage = 'Error'

    def GetCurrentLanguage(self):
        """Gets the current language"""
        return self.language

    def SetCurrentLanguage(self, language):
        """
        make language the default
        """
        self.language = language
        
    def AddMessageModule(self, module):
        """
        Add module to directory of language messages to be added
        to message base - so interfaces can add their own
        """
        self.messageModules.append(module)
        self.LoadMessageModule(module, self.languages)
            
    def LoadMessageModule(self, module, languages):
        """
        load the language for module and add it to dictionary
        """
        modpath = module.__path__
        for language in module.__all__:
            fullName = module.__name__ + '.' + language
            if fullName in sys.modules:
                lang = sys.modules[fullName]
            else:
                file, path, description = imp.find_module(language, modpath)
                try: lang = imp.load_module(language,file,path,description)
                finally: file.close()
            
            if languages.has_key(language):
                languages[language].update(lang.Messages())
            else:
                languages[language] = lang.Messages()
       
    def IgnoreMessage(self, msg):
        """
        add msg to the list of message keys to ignore
        """
        self.ignored[msg] = 1
        
    def UnIgnoreMessage(self, msg):
        """remove msg key from ignored list"""
        try:
            del self.ignored[msg]
        except KeyError:
            pass

    def IsIgnored(self, msg):
        return msg in self.ignored
    
    def RenderMessage(self, msg, args=None, dictionary=None):
        """
        render the message using the appropriate dictionary
        """
        try:
            if dictionary:
                d = dictionary
            else:
                d = self.languages[self.language]
                
            if msg in d:
                if args: out = d[msg] % args
                else:    out = d[msg]
            else:
                try:
                    format = self.languages['English'][msg]
                    if args: out = format % args
                    else:    out = format
                except:
                    out = msg
                    if args:
                        out += ' ' + str(args)
        except:
            out = msg
            if args:
                out += ' ' + str(args)
        return out

    def GetLanguageDict(self, language):
        try:
            return self.languages[language]
        except:
            pass
        
    def GetSupportedLanguages(self):
        d = {'languages': tuple(sim.solver.languages.__all__)}
        for module in self.messageModules:
            try:
                d[module.__name__] = tuple(module.__all__)
            except:
                pass
        return d

MessageHandler = Messages()    
    
    
