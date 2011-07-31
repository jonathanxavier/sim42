#plot diagram 
from ollin.pvt import antoine
from pylab import *
    
def tool(self,case,data,pre):
    a = []
    b = []
    c = []
    t = []
    p1 = []
    p2 = []
    
    for i in case.library.keys():
        SELECT = " ".join(["select",ANT_A,",",ANT_B,",",ANT_C,"from","where",Name,"=:item;"])
        data.cur.execute(SELECT,{"key":case.library[i][0]})
        temp = data.cur.fetchall()
        a.append( temp[0] )
        b.append( temp[1] )
        c.append( temp[2] )

     #   t.append( antoine.pre( a[0], b[0], c[0], pre) )
     #  t.append( antoine.pre( a[1], b[1], c[1], pre) )
        
