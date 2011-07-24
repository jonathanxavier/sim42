class Sim42User(object):
    """
    user login information
    """
    def __init__(self, name, password, privilege, fullname='', group=''):
        self.name = name
        #self.password = sha.new(password).digest()
        self.password = password
        self.privilege = privilege
        self.fullname = fullname
        self.group = group
        self.units = 'SI'
        self.language = 'English'
        self.composition = 0
 
    def GetPrivilege(self):
        return self.privilege
    
    def CheckPassword(self, password):
        """
        check that password matches the stored hash
        """
        #if sha.new(password).digest() == self.password:
        if password and password == self.password:
            return 1
        else:
            return 0

