import sys
sys.path.append("/Users/jonathanxavier/Developer/sim42")
from numpy.oldnumeric import power,array
from ollin.Tools.tools import lagrange
##kk= 
xx=array([0.021816,0.614,0.13974,0.076043,0.015103,0.026015,0.028254,0.079035])
yy=array([0.012954,0.8885,0.069839,0.01834,0.002254,0.0031603,0.0018852,0.0030934])
z=[0.0139,0.8592,0.0773,0.0245,0.0036,0.0056,0.0047,0.0112]


ki=yy/xx#array([ 5.85789009,2.99441671,1.58239488,0.88726921,0.51283227])
zi=z#[0.05,0.15,0.25,0.20,0.35]

F1=sum(ki*zi)-1
F2=2*sum( (ki-1)*zi/( 1+ki ) )
F=F2/(F2-F1)
F3=2*sum( zi/(1+ki) )
F4=sum(zi/ki)-1
fra= (F4-0.5*F4)/(F3-F4)
print F1,F2,F,F3,F4,fra

fr= 0.4
xx=array([0.021816,0.614,0.13974,0.076043,0.015103,0.026015,0.028254,0.079035])
yy=array([0.012954,0.8885,0.069839,0.01834,0.002254,0.0031603,0.0018852,0.0030934])
k = yy/xx
f = 0.5*(1+1/fr)*(sum(xx)-1)
print f
fr = 0.89
f = 0.5*(1+1/fr)*(sum(xx)-1)
print f
fr = 0.99
f = 0.5*(1+1/fr)*(sum(xx)-1)
print f,sum(xx)
