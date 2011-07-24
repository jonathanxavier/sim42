$thermo = VirtualMaterials.NRTL/Ideal/HC
 . -> $thermo

/thermo + 1,2-PROPYLENE_OXIDE METHANOL WATER 1,2-PROPYLENE_GLYCOL SULFURIC_ACID

mycstr = KineticReactor.CSTR()
mycstr.NumberRxn = 1
/mycstr.Rxn0.Formula = theRxn:1.0*'1,2-PROPYLENE GLYCOL'-1.0*!'1,2-PROPYLENE OXIDE'-1.0*WATER
/mycstr.CustomEquationUnitSet = British
/mycstr.Rxn0.ReactionRateEq = """
R = 1.987
k = 16.96E12*exp(-32400.0/(R*T))
r = k*rxnCmp['1,2-PROPYLENE_OXIDE'].Concentration/3600.0
"""

units British
/mycstr.In.T = 75 F

/mycstr.In.Fraction = 43.04 71.87 802.8 0 0
/mycstr.In.MassFlow = None
/mycstr.In.MoleFlow = 917.7099999999999
/mycstr.Out.T = 613 R
/mycstr.DeltaP.DP = 0
/mycstr.Volume.Volume = 300 gallon
/mycstr.In.P = 200 kPa

mycstr.Out
mycstr.OutQ

#Solve for energy now
/mycstr.Out.T = None
/mycstr.OutQ.Energy = 0

mycstr.Out
mycstr.OutQ

copy /mycstr
paste /
mycstrClone.Out
mycstrClone.OutQ