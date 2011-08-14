from numpy.oldnumeric import array

def lagrange(x,y,x_nw):
    n=range(len(x))
##    print n
    y_nw = 0.0
##    print x,y,x_nw
    for i in n:
        p=1.0
        for j in n:
##            print "j",x[j]
            if i!=j:
                p = p*( x_nw - x[j] ) / ( x[i] - x[j] )
        y_nw = y_nw + y[i]*p
    del n
##    print y_nw
    return y_nw

def lagrangeL(x,y,x_nw):
    n=range(len(y[0]))
    m=range(len(x))
##    print n
    y_tmp = []
##    print x,y,x_nw
    for i in n:
        ytemp =[]
        xtemp =[]
        for j in m:
            xtemp.append(x[j][i])
            ytemp.append(y[j][i])
##        print "temp",temp
        ytemp=lagrange(xtemp,ytemp,x_nw)
        y_tmp.append(ytemp)
    del n
##    print y_nw
    return array(y_tmp)
    
def lagrangeLL(x,y,x_nw):
    n=range(len(y[0]))
    m=range(len(x))
##    print n
    y_tmp = []
##    print x,y,x_nw
    for i in n:
        ytemp =[]
        xtemp =[]
        for j in m:
            xtemp.append(x[j][i])
            ytemp.append(y[j][i])
##        print "temp",temp
        ytemp=lagrange(xtemp,ytemp,x_nw[i])
        y_tmp.append(ytemp)
    del n
##    print y_nw
    return array(y_tmp)
