#Comand simple comand interface for ollin thermo server
import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")
from ollin.Administrator.AdmOllin import AdmOllin

adm = AdmOllin()

CurrentObj = "OllinTS>"

com = 0

def AddTM(info=[]):
    x = len(info)
    if x== 0 or x>2:
        return 0
    if x== 1:
        info.append("Antoine")
    adm.AddModel("case",info[0],info[1])

def AddComp(info):
    adm.add(info,"case")
    
def AddCase(info):
    adm.AddCase(info[0])

def Dir(info):
    print "Thermo Models:"
    for i in adm.TheCase.keys():
        print "EOS:%s => %s"%(i,adm.TheCase[i].NameEOS)
        print "          PV:",adm.TheCase[i].NamePresureVap
        
    print "Case:"
    for i in adm.TheObj.keys():
        print "%s-->%s"%(i,adm.TheObj[i].Model)

def Solve(info):
    adm.Solve()

def Load(info):
    adm.LoadConst()
    
##
##def clean(info):
##    clear
##    
COMANDS={}

COMANDS["THERMO"] = AddTM
COMANDS["+"] = AddComp
COMANDS["CASE"]=AddCase
COMANDS["SOLVE"]=Solve
COMANDS["DIR"]= Dir
COMANDS["LOAD"]= Load
##COMANDS["CLEAR"]= clean

class class_cases:

    def __init__(self):
        self.Fuction ={}
        self.Fuction["FRACTION"]=self.Fraction
        self.Fuction["T"]=self.T
        self.Fuction["P"]=self.P
        self.Fuction["H"]=self.H
        self.Fuction["FRACVAP"]=self.FracVap

    def Select(self,case,info):
    
        if info == []:
            adm.TheObj[case].CasePrint()
            adm.TheObj[case].XPrint()
        elif info[0] in self.Fuction.keys():
                Current = info[0]
                info.remove(list_com[0])
                print list_com
                self.Fuction[Current](case,info)
    
    def Fraction(self,case,info):
        x= []
        for i in info:
            x.append(float(i))
        adm.TheObj[case].SetX(x)
    
    def T(self,case,info):
##        print info
        adm.TheObj[case].T(float(info[0]) )
    
    def P(self,case,info):
    
        adm.TheObj[case].P(float(info[0]) )
        
    def H(self,case,info):
    
        adm.TheObj[case].H(float(info[0]) )
    
    def FracVap(self,case,info):
        adm.TheObj[case].FracVap(float(info[0]) )

Classcase = class_cases()
cases = Classcase.Select
##    def Fraction(case,info):
##        adm.TheObj["Str"].XPrint()


while com !="EXIT":

    com = raw_input(CurrentObj)
    list_com = com.split()
    obj = adm.TheObj.keys()
    if len(list_com) != 0:
    
        if list_com[0] in COMANDS.keys():
            Current = list_com[0]
            list_com.remove(list_com[0])
            print list_com
            COMANDS[Current](list_com)
            
        elif list_com[0]  in adm.TheObj.keys():
            Current = list_com[0]
            list_com.remove(list_com[0])
            print list_com
            cases(Current,list_com)

    print com,list_com
    

##if __name__ == "main":
