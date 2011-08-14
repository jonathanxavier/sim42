''' A module of tables and graphs for constants
'''

# Available methods in this module
#   1) GTable  - gives the allowable downflow (baffle liquid load) in gph/ft2, usually used for vertical vessel 
#   2) HNATable  - cylindrical height and area conversions 
#   3) VesselWeightAndWallThickness - a method to find vessel weight and wall thickness
#   4) FinalValue - used to finalize the dimension to the next/highest 0.5 units
#   5) LowLiqLevelHeight - Table to obtain Hlll for two-phase separators
#   6) Kvalue - to calculate K-constant in Stoke's Law


import numpy.oldnumeric
from math import log, pi, ceil

# need to change sim42 units to field units to be able to use all the methods in here

def GTable(DRho, Hlr):
# DRho = density difference between light liquid and vapor
# Hlr = height of liquid level above the interphase of light liquid and heavy liquid

    A = {}  
    B = {} 
    C = {}
    D = {}

    if Hlr > 30.0:
        Hlr = 30.0
    
    if Hlr < 18.0:
        Hlr = 18.0
    
    if DRho > 50.0:
        DRho = 50.0
    
    if DRho < 10.0:
        DRho = 10.0
# all the ifs will have error messege later coz it goes outside range
  
    Hlr = round(Hlr, 0)
            
    A[18] = -9000.0
    B[18] = 1275.4
    C[18] = -31.3571
    D[18] = 0.255556

    A[19] = -4690.0
    B[19] = 900.117
    C[19] = -20.5252
    D[19] = 0.157254
       
    A[20] = -9980.0
    B[20] = 1367.91
    C[20] = -33.0163
    D[20] = 0.26476
        
    A[21] = -8120.0
    B[21] = 1147.46
    C[21] = -25.3
    D[21] = 0.184444
        
    A[22] = -16800.0
    B[22] = 1964.89
    C[22] = -48.8627
    D[22] = 0.399498
        
    A[23] = -7900.0
    B[23] = 1255.35
    C[23] = -29.9142
    D[23] = 0.235632
        
    A[24] = -11200.0
    B[24] = 1561.48
    C[24] = -38.7335
    D[24] = 0.318511
        
    A[25] = -11100.0
    B[25] = 1554.66
    C[25] = -38.0313
    D[25] = 0.308026
        
    A[26] = -7410.0
    B[26] = 1274.0
    C[26] = -30.8013
    D[26] = 0.246585
        
    A[27] = -12700.0
    B[27] = 1709.78
    C[27] = -42.1048
    D[27] = 0.342222
        
    A[28] = -10200.0
    B[28] = 1507.78
    C[28] = -36.422
    D[28] = 0.291221
        
    A[29] = -10700.0
    B[29] = 1553.51
    C[29] = -37.5721
    D[29] = 0.300279
        
    A[30] = -9830.0
    B[30] = 1513.11
    C[30] = -37.1907
    D[30] = 0.30379

    G = A[Hlr] + (B[Hlr] * DRho) + (C[Hlr] * DRho ** 2) + (D[Hlr] * DRho ** 3)

    return round(G, 2)


def HNATable(Type, X):
# Type = 1 is where H/D is known, find A/At, Type = 2 is where A/At is known, find H/D 
    if (Type == 1):
        a = -0.0000475593
        b = 3.924091
        c = 0.174875
        d = -6.358805
        e = 5.668973
        f = 4.018448
        g = -4.916411
        h = -1.801705
        i = -0.145348
        Y = (a + c * X + e * X ** 2 + g * X ** 3 + i * X ** 4) / (1.0 + b * X + d * X ** 2 + f * X ** 3 + h * X ** 4)
    else:
        a = 0.00153756
        b = 26.787101
        c = 3.299201
        d = -22.923932
        e = 24.353518
        f = -14.844824
        g = -36.999376
        h = 10.529572
        i = 9.892851
        Y = (a + c * X + e * X ** 2 + g * X ** 3 + i * X ** 4) / (1.0 + b * X + d * X ** 2 + f * X ** 3 + h * X ** 4)
    
    return Y

def VesselWeightAndWallThickness(Pressure, Diameter, VesselLength):
    S = 17500.0     # Vessel material stress value (assume carbon-steel)
    Ca = 1.0/16.0   # Corrosion Allowance in inches
    Je = 0.85        # Joint efficiency = 1.0 for X-Rayed joints
    
    P1 = (Pressure - 14.7) + 30.0
    P2 = (Pressure - 14.7)*1.1
    if P1 > P2:
        PT = P1
    else:
        PT = P2

    # Calculate the wall thickness and surface area
    # Shell
    SWT = (PT * Diameter*12.0) / (2.0 * S * Je - 1.2 * PT) + Ca
    SSA = pi * Diameter * VesselLength
    if Diameter < 15.0 and PT > (100 - 14.7):
        # Elliptical Heads
        HWT = (PT * Diameter*12.0) / (2.0 * S * Je - 0.2 * PT) + Ca
        HSA = 1.09 * Diameter ** 2
    elif Diameter > 15.0:
        # Hemispherical Heads
        HWT = (PT * Diameter*12.0) / (4.0 * S * Je - 0.4 * PT) + Ca
        HSA = 1.571 * Diameter ** 2
    else:
        # Dished Heads
        HWT = 0.885 * (PT * Diameter*12.0) / (S * Je - 0.1 * PT) + Ca
        HSA = 0.842 * Diameter ** 2
   
    # Approximate the vessel wall thickness in ft, whichever is larger
    if SWT > HWT:
        VWT = SWT/12.0
    else:
        VWT = HWT/12.0
   
    # Vessel Weight 490 lb/ft3 is the density of for the material of construction of the vessel
    VW = 490.0 * VWT * (SSA + 2.0 * HSA)   #' in lb
    VW = round(VW, 2)
        
    return VW, VWT

def LowLiqLevelHeight(Type, P, D):
# Type 1 is vertical, 2 is horizontal
    if Type == 1:
        Hlll = 0.5
        if P < 300:
            Hlll = 1.25

    elif Type == 2:
        if D <= 4.0:
            Hlll = 9.0/12.0
        elif D > 4.0 and D <= 7.0:
            Hlll = 10.0/12.0
        elif D > 7.0 and D <= 9.0:
            Hlll = 11.0/12.0
        elif D > 9.0 and D <= 11.0:
            Hlll = 1.0
        elif D > 11.0 and D <= 15.0:
            Hlll = 13.0/12.0
        else:
            Hlll = 15.0/12.0

    return Hlll     #in ft

    
def Kvalue(P):      # York-Demister eqn.
    if P >= 1.0 and P <= 15.0:
        K = 0.1821+(0.0029*P)+(0.046*log(P))
    if P > 15.0 and P <= 40.0:
        K = 0.35
    if P > 40.0 and P <= 5500.0:
        K = 0.43 - 0.023*log(P)

    return K 
        
def FinalValue(Var):
    for I in range(1, 101):
        if Var < I * 0.5 and Var > (I - 1) * 0.5:
            Var = I * 0.5

    return Var


##if __name__ == '__main__':
    
##    D = 5.0
##    L = 29.5
##    P = 975 + 14.7
##    HeadType = 'Elliptical'
##    VW, VWT = VesselWeightAndWallThickness(P, D, L, HeadType)
##    print ""
##    print ' VW = ', VW
##    print ' VWT = ', VWT
##    print '================================================================='       