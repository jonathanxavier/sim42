from numpy.oldnumeric import sqrt,array,power

def Molar(fraction, proper):
    """
    this fuction return sum(Xi*pi)
    """
    return sum(fraction*proper)

def MolarK(fraction, proper, k = 0):
    """
    This fuction return a
    special property of mix
    """
    lo = len(proper)
    temp = 0
##    print fraction,proper
    for i in range(lo):
##            print i
            temp += sum( ( 1-k )*sqrt( proper[i]*proper )*( fraction[i]*fraction) )
    return temp

def MolarK2(x, a, k = 0):
    """
    This fuction return a
    special property of mix
    """
    temp = []
    for i in range( len(a) ):
            Aij= sum(  x * sqrt(  a[i]*a )* (1-k)  )
            temp.append(Aij)
    
    temp = array(temp) 
    ##print "2k",fraction,proper,temp
    return temp
