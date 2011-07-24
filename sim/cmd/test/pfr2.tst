
$thermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $thermo

thermo + n-BUTANE ISOBUTANE

pfr = KineticReactor.PFR()
pfr.In.T = 330 K
pfr.In.P = 3000 kPa
pfr.In.Fraction = 0.9 0.1
pfr.In.MoleFlow = 163

pfr.Length = 12.9 m
pfr.Diameter = 0.6 m
pfr.OutQ = 0
pfr.NumberSections = 40

pfr.NumberRxn = 1
pfr.Rxn0.Formula = theRxn0:1.0*ISOBUTANE-1.0*!'n-BUTANE'
pfr.CustomEquationUnitSet = sim42

pfr.Rxn0.ReactionRateEq = """

#The following are plain Python lines with the final goal of defining a variable called r
#which will be interpreted as the reaction rate in the CustomEquationUnitSet units.

#Define some constants
E = 65700.0                           #J/mol = kJ/kmol
T1 = 360.0                            #K
kRef = 31.1                           #1/h


#R is automatically loaded in sim42 units as kJ/kmolK
k = kRef*exp( (E/R)*(1.0/T1 - 1/T) )  #1/h

T2 = 60.0 + 273.15                    #K
KcRef = 3.03
Kc = KcRef*exp( (-6900.0/R)*(1/T2 - 1/T) )

#The unit set defined is sim42, hence concentration comes in kmol/m3
r = k*(rxnCmp['n-BUTANE'].Concentration - rxnCmp['ISOBUTANE'].Concentration/Kc)

#The unit set defined is sim42, hence r has to be returned in kmol/(s*m3)
r = r/3600.0                          #kmol/(s*m3)

"""

pfr.DeltaP = 0.0

pfr.T
pfr.f
pfr.r

pfr.Ignored = 1

#Now solve it by providing r in different units

pfr.CustomEquationUnitSet = Field

pfr.Rxn0.ReactionRateEq = """

#The following are plain Python lines with the final goal of defining a variable called r
#which will be interpreted as the reaction rate in the CustomEquationUnitSet units.

#Define some constants
E = 65700.0 * 0.43                    #Btu/lbmol
T1 = 360.0 * 1.8                      #R
kRef = 31.1                           #1/h

#T came in F. Make it R
T = T + 459.67                        #R


#R is automatically loaded in Field units as psia-ft3/lbmolR
R = 1.987                         #Btu/lbmolR
k = kRef*exp( (E/R)*(1.0/T1 - 1/T) )  #1/h

T2 = (60.0 + 273.15) * 1.8            #R
KcRef = 3.03
Kc = KcRef*exp( ((-6900.0*0.43)/R)*(1/T2 - 1/T) )

#The unit set defined is sim42, hence concentration comes in lbmol/ft3
r = k*(rxnCmp['n-BUTANE'].Concentration - rxnCmp['ISOBUTANE'].Concentration/Kc)

#The unit set defined is Field, hence r has to be returned in lbmol/(s*ft3)
r = r/3600.0                          #lbmol/(s*ft3)

"""
pfr.Ignored = None

pfr.T
pfr.f
pfr.r

copy /pfr
paste /
pfrClone.T
pfrClone.f
pfrClone.r


