from ollin.Administrator.AdmOllin import Ollin
from numpy.oldnumeric import array,power,pi

PR=Ollin.AddModel("PR","PR")
Ollin.Add(["HYDROGEN","METHANE","BENZENE","TOLUENE","DIPHENYL",],"PR")

S1=Ollin.AddCase("S1")#Alimentacion al compresor
S1.SetX([0.366021,0.548913,0.062618,0.021503,0.000945])
S1.T(38+273.15)
##S1.FracVap(0.9)
S1.P(3206.062)
Ollin.Solve("S1")#Caculamos S1
Ollin.Resumen("S1")

L = (1-S1.Get("FracVap"))*1919.605
Gv = (L*S1.Get("MolWt_l"))/( S1.Get("LiqDen")*60 )
Vr = Gv*5
Lon = power((256*Vr/pi),0.333333)
Dia = Lon/4
print "Longuitud", Lon
print "Diametro",Dia

