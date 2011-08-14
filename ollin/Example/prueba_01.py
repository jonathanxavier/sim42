from ollin.Administrator.AdmOllin import Ollin
from numpy.oldnumeric import array

RK=Ollin.AddModel("PR","PR","ANTOINE")
Ollin.Add(["METHANOL","HYDROGEN","CARBON MONOXIDE","CARBON DIOXIDE","WATER","METHANE"],"PR")

S1=Ollin.AddCase("S1")#Alimentacion al compresor
S1.SetX([0,69,21,7,0,3])
S1.T(25+273.15)
S1.P(101.325*1)

Ollin.Solve("S1")#Caculamos S1
Ollin.Resumen("S1")
##print S1.Get("H")
S2=Ollin.AddCase("S2")#salida del compresor
S2.SetX(S1.Get("x"))
S2.H(S1.Get("H")) #Considerando que es adiabatico dQ=0
S2.P(101.325*20)
Ollin.Solve("S2")#Caculamos S2
Ollin.Resumen("S2")

#Salida del calentador
S3=Ollin.AddCase("S3")#Alimentacion al ractor
S3.SetX(S2.Get("x"))
S3.T(400+273.15)
S3.P(S2.Get("P"))
Ollin.Solve("S3")
#La reaccion se realiza en fase gas adiabaticamente dQ=0
S4 = Ollin.AddCase("S4")#Salida del reactor
S4.H(S3.Get("H")) #Considerando que es adiabatico dQ=0
S4.P(101.325*20)
Frac_V = S3.Get("yf")
Frac_L = S3.Get("xf")
FracVap = S3.Get("FracVap")

CO = Frac_V[2]
H2 = Frac_V[1]
CO2 = Frac_V[3]
CH4 = Frac_V[5]
#Reaction 1: CO + 2H2 --> C1OH conversion de CO = 30%
C1OH= CO*0.3 #Methanol
H2 = H2 - 2*C1OH
CO =CO*0.7
#Reaction 1: CO2 + 3H2 --> C1OH+H2O conversion de CO = 20%
C1OH= C1OH + CO2*0.2 #Methanol
H2 = H2 - 3*CO2*0.2
H2O = C1OH
CO2 =CO2*0.8

##Frac = FracVap*array([C1OH,H2,CO,CO2,H2O,CH4])+Frac_L*(1-FracVap)
Frac = array([C1OH,H2,CO,CO2,H2O,CH4])
print "Fration compo",Frac
S4.SetX(list(Frac))

Ollin.Solve("S4")
##Ollin.Resumen("S4")

#Salida del enfriador y flash
S5=Ollin.AddCase("S5")#salida del compresor
S5.SetX( S4.Get("x") )
S5.P( 101.325*(20-0.6-0.6) )
S5.T(60+273.15)
Ollin.Solve("S5")#Caculamos S2

Ollin.Resumen("S5")


