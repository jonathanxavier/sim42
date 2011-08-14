##import sys
##sys.path.append("/Users/jonathanxavier/Developer/sim42")
from pysqlite2 import dbapi2 as sq
from ollin.DataBase.SysData import DataBaseVars
from numpy.oldnumeric import array

class DataBase:
    """
    Fuction to acces to current data base"
    """
    def __init__(self):
        """load dates"""
        self.SupportVars = DataBaseVars()
        self.CurrentPath = self.SupportVars["BasePath"]
        self.CurrentDataBase = self.SupportVars["DataBase"]
        self.Cursor = self.LoadDataBase( self.CurrentPath,self.CurrentDataBase )

    def LoadDataBase(self,Path,Name):
        SELECT = Path + Name
        print "\nLoading Data Base %s"%(Name)
        con = sq.connect(SELECT)
        cur = con.cursor()
        print "\.........."
        del SELECT
        return cur

    def comp(self):
        SysDic = self.SupportVars
        SELECT = " ".join(["select",SysDic["IdKey"],",",SysDic["Name"],",",SysDic["TB"],"from",SysDic["TableComp"],";"])
        self.Cursor.execute(SELECT)
        print "<<Number>>       <<Name>>       <<Boiling Point>>"
        print "_____________________________________________"
        for x in self.Cursor.fetchall():
            print "%-10d>> %-20s >> %-10f"%(x[0],x[1],x[2])

        del SysDic ,SELECT

    def Dates(self,items,key):
        """
        Return a list of list items
        """
        if type(items) == (str):
            items = list((items,))
        else:
            items = list(items)
        if type(key) == (str):
            key   = list((key,))
        else:
            key   = list(key)
        
        result = []
        
        for x_items in items:
            
            #print x_items
            temp= []
            SELECT  = "SELECT " + self.SupportVars[x_items] + " FROM " + self.SupportVars["TableComp"]+" " + "WHERE" + " "+self.SupportVars["Name"]+"=:item;"

            for x_key in key:
        
                self.Cursor.execute(SELECT,{"item":x_key})
                #print x_key
                #print SELECT
                temporal = self.Cursor.fetchone()
                #print temporal

                if temporal ==None:
                    
                    print "Any date in data base"
                    print "Can be anyone of this"
                    if self.find(x_key) == 0:
                        print "Dont have reference of %s"%x_key
                    key.remove(x_key)
                    
                else:
                    
                    temp.append(temporal[0])
                    
            if temp ==[]:
                
                print "Any date to  add"

            else:

                result.append(temp)
            
        return result

    def find(self,key):
        
        SysDic = self.SupportVars
        key = "%"+ key + "%"
        SELECT = " ".join(["SELECT",SysDic["IdKey"],",",SysDic["Name"],"FROM",SysDic["TableComp"],"WHERE",SysDic["Name"],"LIKE :key",";"])
        self.Cursor.execute(SELECT,{"key":key})
        temp = self.Cursor.fetchall()
        i = 1
        if temp == (None or []):
            return 0
        else:
            for x in temp:
                print " %d .- %d = %s"%(i,x[0],x[1])
                i += 1
            return 1
