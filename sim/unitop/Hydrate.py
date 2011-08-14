"""Model of Hydrate Calculation

Class:
Hydrate -- Which inherits from UnitOperations.UnitOperation

"""

#This unit operatio was contributed by Shahrul and Norfaizah
#April 14th 2003
#Bug fix to trap errors contributed by Norfaizah
#April 19th 2003


from sim.solver.Variables import *
from sim.unitop import UnitOperations, Sensor, Stream
from sim.solver import Ports

import numpy.oldnumeric 

THYDRATE_PORT = 'HydrateTemp'


class Hydrate(UnitOperations.UnitOperation):
    def __init__ (self, initScript =  None):
        UnitOperations.UnitOperation.__init__(self, initScript)

        # Add a standalone Hydrate temperature Signal port
        self.myStream = Stream.Stream_Material()
        self.AddUnitOperation(self.myStream, 'myStream')

        #Add A signal Port
        self.Thydrate = self.CreatePort(SIG, THYDRATE_PORT)
        self.Thydrate.SetSignalType(T_VAR)

        #Load database
        LoadDB() 

        #Connects externally
        self.BorrowChildPort(self.myStream.GetPort(IN_PORT), IN_PORT)
        self.BorrowChildPort(self.myStream.GetPort(OUT_PORT), OUT_PORT)
        
    def CleanUp(self):
        self.myStream = self.Thydrate = None
        super(Hydrate, self).CleanUp()
        
    def Solve(self):        

        # Get Property Values i.e. pressure and mole fractions        
        p = self.GetPort(IN_PORT)
        Press = p.GetPropValue(P_VAR)
        CompValues = []
        CompValues = p.GetCompositionValues()
        CompNames = []
        CompNames = self.GetCompoundNames()

        #Validate available info
        if Press == None: return
        if not CompNames: return
        if None in CompValues: return

        # This is to assign the available compounds in the stream as the dominant component in Hydrate.py by Hieraki
        if "ETHANE" in CompNames:
            NN = 3
        elif "PROPANE" in CompNames:
            NN = 4
        elif "ISOBUTANE" in CompNames:
            NN = 5
        elif "CARBON_DIOXIDE" in CompNames:
            NN = 7
        elif "HYDROGEN_SULFIDE" in CompNames:
            NN = 8
        else:
            self.InfoMessage('NonHydrateFormerFound', (self.GetPath(),))# Need to add in the english library
            return None

        #This is to assign components index and its mole fraction values to Hydrate.py
        n2Idx = 1
        methIdx = 2
        ethIdx = 3
        propIdx = 4
        ibutIdx = 5
        nc4Idx = 6
        co2Idx = 7
        h2sIdx = 8
        waterIdx = 9
 
        #Initialise the y[] as zero if the component does not exist
        y = {}
        if not "METHANE" in CompNames :
            y[methIdx] = 0.0
        if not "ETHANE" in CompNames:
            y[ethIdx] = 0.0 
        if not "PROPANE" in CompNames:
            y[propIdx] = 0.0
        if not  "ISOBUTANE" in CompNames:
            y[ibutIdx] = 0.0 
        if not  "CARBON_DIOXIDE" in CompNames:
            y[co2Idx] = 0.0
        if not  "HYDROGEN_SULFIDE" in CompNames:
            y[h2sIdx] = 0.0

        #Iteration to find mol fraction of the Hydrate components
        cnt = 0         
        for CompName in CompNames:
            if CompName == "METHANE":
                y[methIdx] = CompValues[cnt]
            elif CompName == "ETHANE":
                y[ethIdx] = CompValues[cnt]
            elif CompName == "PROPANE":
                y[propIdx] = CompValues[cnt]
            elif CompName == "ISOBUTANE":
                y[ibutIdx] = CompValues[cnt]
            elif CompName == "CARBON_DIOXIDE":
                y[co2Idx] = CompValues[cnt]
            elif CompName == "HYDROGEN_SULFIDE":
                y[h2sIdx] = CompValues[cnt]
            cnt += 1
            
        sum = Numeric.sum(y.values())
        sum1 = 1 - sum # Lump the non-hydrate components as sum1
        y[n2Idx] = sum1
        y[nc4Idx] = 0.0
        y[waterIdx] = 0.0

        #Used the available properties to calculate Thyd
        tolerance = self.GetParameterValue(MAXERROR_PAR)
        maxIter   = self.GetParameterValue(MAXITER_PAR)

        #No hydrate solid can be form for pressure low than 7.5 bar
        if Press < 750:
            self.InfoMessage('HydrateLowP', (str(Press), self.GetPath()))
        else:
            try:
                Thyd = CalculateHydrateTemperature(Press, y, NN, tolerance, maxIter)
            except:
                Thyd = None
            if Thyd == None:
                ThydFinal = None
                self.InfoMessage('HydrateCouldNotCalc', (self.GetPath(), str(Press), str(CompValues)))
            else:
                ThydFinal = Thyd + 273.15
                #Assign Thyd to the Signal port
                self.Thydrate.SetPropValue(T_VAR, ThydFinal, CALCULATED_V) 
        



################DATA BASE INFORMATION##################
        

#Loaded from DB
N = 9
PC = {}  #Pressure curves
NOP = {} #Number of points
K = {}
NOPMX = {}
NOPMN = {}
T_DB = {}
P_DB = {}
PL = {}


#Used while solving
IKCalc = {}
KCalc = {}
KJ = {}
Y = {}
YOK = {}
KNew = {}
TCalc = {}

def CalculateHydrateTemperature(Press, y, NN, tol=0.001, maxIter=20, scaleFactor=1.0, Temp=20.0):
    # Initialisation
    eps = tol
    sum = 0.0
    cnt = 0
    converged = False

    # Let's nail these guys....
    for i in range(1, 10):
        IKCalc[i] = {}
        KCalc[i] = {}
        KJ[i] = {}
        

        for j in range(0, 16):
            IKCalc[i][j] = {}
            KJ[i][j] = {}
            

##            for L in range(0, 32):  This is wrong since this will create a dictionary of L and overwrite assign value in the LoadDB()
##                IKCalc[i][j][L]= {}
    
    while cnt < maxIter and not converged:

        # This loop is for Exact P and Exact T        
        cnt +=1
        for i in range(1, N+1):
            for j in range(1, PC[i]+1):
                for L in range(0, NOP[i]+1):
                    if (Press == P_DB[i][j]) and (Temp == T_DB[i][j][L]):
                        IKCalc[i][j][L] = K[i][j][L]
                        KCalc[i] = IKCalc[i][j][L]
                        
        # This loop is for Exact P and Interpolated T            
        for i in range(1, N+1):
            for j in range(1, PC[i]+1):
                for L in range(0, NOP[i]+1):
                    if (Press == P_DB[i][j]) and (Temp > T_DB[i][j][L]) and (Temp < T_DB[i][j][L+1]):
                        IKCalc[i][j][L] = (K[i][j][L+1] - K[i][j][L]) / (T_DB[i][j][L+1] - T_DB[i][j][L]) * (Temp - T_DB[i][j][L]) + K[i][j][L]
                        KCalc[i] = IKCalc[i][j][L]
    
##        for i in range(1, N+1):
##            for j in range(1, PC[i]+1):
##                for L in range(0, NOP[i]+1):
##                    if (Press > P_DB[i][j]) and (Press < P_DB[i][j+1]) and (Temp == T_DB[i][j][L]):
##                        IKCalc[i][j][L] = (K[i][j+1][L] - K[i][j][L]) / (P_DB[i][j+1] - P_DB[i][j]) * (Press - P_DB[i][j]) + K[i][j][L]
##                        KCalc[i] = IKCalc[i][j][L]

#-------------------------------------------------------------------------------------------------------
        # Initialise: Calculate the K[i][0][L] and  K[i][15][L] values

        for i in range(1, N+1):        
            for j in range(1, PC[i]+1):
                for L in range(0, NOP[i]+1):
                    if not K[i].has_key(0):
                        K[i][0] = {}
                    if not T_DB[i].has_key(0):
                        T_DB[i][0] = {}
                    
                    if (Press < P_DB[i][1]):
                        K[i][0][L] = (K[i][1][L] - K[i][2][L]) / (P_DB[i][1] - P_DB[i][2]) * (Press - P_DB[i][1]) + K[i][1][L]
                        T_DB[i][0][L] = L
                        if K[i][0][L] <= 0.0:
                            K[i][0][L] = 0.00001
                        
                    if (Press > P_DB[i][PC[i]]):
                        K[i][0][L] = (K[i][PC[i]-1][L] - K[i][PC[i]][L]) / (P_DB[i][PC[i]-1] - P_DB[i][PC[i]]) * (Press - P_DB[i][PC[i]]) + K[i][PC[i]][L]
                        T_DB[i][0][L] = L
                        if K[i][0][L] <= 0.0:
                            K[i][0][L] = 0.00001

                    # We need this guys for the Dominant Reference Curve
                    if (Press > P_DB[i][j]) and (Press < P_DB[i][j+1]):
                        K[i][15][L] = (K[i][j+1][L] - K[i][j][L]) / (P_DB[i][j+1] - P_DB[i][j]) * (Press - P_DB[i][j]) + K[i][j][L]      
                        T_DB[i][15][L] = L
 
                    
                        
#---------------------------------------------------------------------------------------------------------               
        # The imaginary pressure lines(j = 15) for all components
                        
        for i in range(1, N+1):
            for j in range(1, PC[i]+1):
                for L in range(0, NOP[i]+1):
                    if (Press > P_DB[i][j]) and (Press < P_DB[i][j+1]) and (Temp == T_DB[i][j][L]):
                        K[i][15][L] = (K[i][j+1][L] - K[i][j][L]) / (P_DB[i][j+1] - P_DB[i][j]) * (Press - P_DB[i][j]) + K[i][j][L]
                        KCalc[i] = K[i][15][L]       
                        T_DB[i][15][L] = L
                          
        for i in range(1, N+1):
            for j in range(1, PC[i]+1):
                for L in range(0, NOP[i]+1):
                    if (Press > P_DB[i][j]) and (Press < P_DB[i][j+1]) and (Temp > T_DB[i][j][L]) and (Temp < T_DB[i][j][L+1]):
##                        if not IKCalc[i].has_key(15):
##                            IKCalc[i][15] = {}
##                        if not KJ[i].has_key(15):
##                            KJ[i][15] = {}
                        IKCalc[i][15][L] = (K[i][j][L + 1] - K[i][j][L]) / (T_DB[i][j][L+1] - T_DB[i][j][L]) * (Temp - T_DB[i][j][L]) + K[i][j][L]
                        KJ[i][15][L] = (K[i][j+1][L+1] - K[i][j+1][L]) / (T_DB[i][j+1][L + 1] - T_DB[i][j+1][L]) * (Temp - T_DB[i][j + 1][L]) + K[i][j+1][L]
                        IKCalc[i][15][L] = (KJ[i][15][L] - IKCalc[i][15][L]) / (P_DB[i][j+1] - P_DB[i][j]) * (Press - P_DB[i][j]) + IKCalc[i][15][L]
                        KCalc[i] = IKCalc[i][15][L]
                        T_DB[i][15][L] = L



                        
#-----------------------------------------------------------------------------------------------------------

        # The imaginary pressure lines(j = 0) for all components
        
        for i in range(1, N+1):
            for j in range(1, PC[i]+1):
                for L in range(0, NOP[i]+1):
                    if (Press < P_DB[i][1]) and (Temp == T_DB[i][j][L]) :
                        if not K[i].has_key(0):
                            K[i][0] = {}
                        if not T_DB[i].has_key(0):
                            T_DB[i][0] = {}
                        K[i][0][L] = (K[i][1][L] - K[i][2][L]) / (P_DB[i][1] - P_DB[i][2]) * (Press - P_DB[i][1]) + K[i][1][L]
                        KCalc[i] = K[i][0][L]
                        T_DB[i][0][L] = L
                        
                    if (Press < P_DB[i][1]) and (Temp > T_DB[i][j][L]) and (Temp < T_DB[i][j][L+1]) :
                        if not K[i].has_key(0):
                            K[i][0] = {}
                        if not T_DB[i].has_key(0):
                            T_DB[i][0] = {}
                        T_DB[i][0][L] = L
                        K[i][0][L] = (K[i][1][L] - K[i][2][L]) / (P_DB[i][1] - P_DB[i][2]) * (Press - P_DB[i][1]) + K[i][1][L]
                        K[i][0][L] = (K[i][0][L+1] - K[i][0][L]) / (T_DB[i][0][L+1] - T_DB[i][0][L]) * (Temp - T_DB[i][0][L]) + K[i][0][L]
                        KCalc[i] = K[i][0][L]

                    if (Press > P_DB[i][PC[i]]) and (Temp == T_DB[i][j][L]) :
                        if not K[i].has_key(0):
                            K[i][0] = {}
                        if not T_DB[i].has_key(0):
                            T_DB[i][0] = {}
                        K[i][0][L] = (K[i][PC[i]-1][L] - K[i][PC[i]][L]) / (P_DB[i][PC[i]-1] - P_DB[i][PC[i]]) * (Press - P_DB[i][PC[i]]) + K[i][PC[i]][L]
                        KCalc[i] = K[i][0][L]
                        T_DB[i][0][L] = L

                    if (Press > P_DB[i][PC[i]]) and (Temp > T_DB[i][j][L]) and (Temp < T_DB[i][j][L+1]):
                        if not K[i].has_key(0):
                            K[i][0] = {}
                        if not T_DB[i].has_key(0):
                            T_DB[i][0] = {}
                        T_DB[i][0][L] = L
                        K[i][0][L] = (K[i][PC[i]-1][L] - K[i][PC[i]][L]) / (P_DB[i][PC[i]-1] - P_DB[i][PC[i]]) * (Press - P_DB[i][PC[i]]) + K[i][PC[i]][L]
                        K[i][0][L] = (K[i][0][L+1] - K[i][0][L]) / (T_DB[i][0][L+1] - T_DB[i][0][L]) * (Temp - T_DB[i][0][L]) + K[i][0][L]
                        KCalc[i] = K[i][0][L]

#----------------------------------------------------------------------------------------------------
    #Fine tuning of the KCalc[i] value when less than zero
                        
        if KCalc[2] <= 0.00:
            KCalc[2] = 0.05

        if KCalc[3] <= 0.00:
            KCalc[3] = 0.05

        if KCalc[4] <= 0.00:
            KCalc[4] = 0.005

        if KCalc[5] <= 0.00:
            KCalc[5] = 0.006

        if KCalc[7] <= 0.00:
            KCalc[7] = 0.25

        if KCalc[8] <= 0.00:
            KCalc[8] = 0.01

#-------------------------------------------------------------------------------------------------------
            

                        
        for i in range(1, N+1):
##          Y[i] = y[cnt]
            Y = y
            YOK[i] = Y[i] / KCalc[i]

        sum = Numeric.sum(YOK.values())
        sum1 = Numeric.sum(Y.values())


#--------------------------------------------------------------------------------------------------------
# Taking Ethane as dominant component
#        NN = 3
        KNew[NN] = sum * KCalc[NN]
        for i in range(1, PC[NN]+1):
            if (Press == P_DB[NN][i]) :
               for j in range(0, NOP[NN]+1):
                   if (KNew[NN] > K[NN][i][j] and KNew[NN] < K[NN][i][j + 1]) :
                      II = j
                      TCalc[NN] = (KNew[NN] - K[NN][i][II]) / (K[NN][i][II + 1] - K[NN][i][II]) * (T_DB[NN][i][II + 1] - T_DB[NN][i][II]) + T_DB[NN][i][II]

#------------------------------------------------------------------------------------------------------------
# At Imaginary Pressure Line
        for i in range(1, PC[NN]+1):
            if (Press > P_DB[NN][i]) and (Press < P_DB[NN][i+1]) :
                for j in range(0, NOP[NN]+1):
                    if (KNew[NN] > K[NN][15][j] and KNew[NN] < K[NN][15][j + 1]):
                        II = j
                        TCalc[NN] = (KNew[NN] - K[NN][15][II]) / (K[NN][15][II + 1] - K[NN][15][II]) * (T_DB[NN][15][II + 1] - T_DB[NN][15][II]) + T_DB[NN][15][II]

         
            if (Press < P_DB[NN][1]) :
                for j in range(0, NOP[NN]+1):
                    if (KNew[NN] > K[NN][0][j] and KNew[NN] < K[NN][0][j + 1]) :
                        II = j
                        TCalc[NN] = (KNew[NN] - K[NN][0][II]) / (K[NN][0][II + 1] - K[NN][0][II]) * (T_DB[NN][0][II + 1] - T_DB[NN][0][II]) + T_DB[NN][0][II]

        
            if (Press > P_DB[NN][PC[NN]]) :
                for j in range(0, NOP[NN]+1):
                    if (KNew[NN] > K[NN][0][j] and KNew[NN] < K[NN][0][j + 1]) :
                        II = j
                        TCalc[NN] = (KNew[NN] - K[NN][0][II]) / (K[NN][0][II + 1] - K[NN][0][II]) * (T_DB[NN][0][II + 1] - T_DB[NN][0][II]) + T_DB[NN][0][II]
#------------------------------------------------------------------------------------------------------------

        if abs(1 - sum)/scaleFactor <= eps:
##            converged = True
            return TCalc[NN] #converged
        else:
            Temp = TCalc[NN]
##            print 'No. of Iteration:', cnt
##            print 'Summation:', sum
##            print 'New Initial Temperature:', TCalc[NN]

def LoadDB():
    
    PC[1] = 14
    PC[2] = 13
    PC[3] = 13
    PC[4] = 14
    PC[5] = 9
    PC[6] = 14
    PC[7] = 7
    PC[8] = 7
    PC[9] = 14
    
    for i in range(1, 10): # To make a bigger house for the components
        NOPMX[i] = {}
        NOPMN[i] ={}
        T_DB[i] = {}
        P_DB[i] ={}
        K[i] = {}

        for j in range(0, 16): # To make a bigger house for the Pressure Curves (PC)
            NOPMX[i][j] = {}
            NOPMN[i][j] ={}
            T_DB[i][j] = {}
            P_DB[i][j] = {}
            K[i][j] = {}

      
        P_DB[i][PC[i]+1] = 0.0   # This is to trap the end pressure curve
            

            
##            for L in range(0, 32): # To make a bigger house for the Temperature Extrapolation
##                T_DB[i][j][L] = {}
##                P_DB[i][j][L] ={}
##                K[i][j][L] = {}

                
# Methane index as 2
    methIdx = 2

    #Make all the main dictionaries to contain nested dictionaries for methane
    NOP[methIdx] = 15
##    NOPMX[methIdx] = {}
##    NOPMN[methIdx] = {}
##    T_DB[methIdx] = {}
##    P_DB[methIdx] = {}
##    K[methIdx] = {}

##    
    for j in range(1, PC[methIdx]+1):
        NOPMX[methIdx][j] = 15
        NOPMN[methIdx][j] = 0
##        T_DB[methIdx][j] = {}
##        K[methIdx][j] = {}
        for i in range(0, NOP[methIdx]+1):
            T_DB[methIdx][j][i] = i
            
        
    P_DB[methIdx][1] = 700.0
    PL[methIdx] = 1
    K[methIdx][1][0] = 2.95
    K[methIdx][1][1] = 3.0
    K[methIdx][1][2] = 3.05
    K[methIdx][1][3] = 3.1
    K[methIdx][1][4] = 3.2
    K[methIdx][1][5] = 3.25
    K[methIdx][1][6] = 3.3
    K[methIdx][1][7] = 3.32
    K[methIdx][1][8] = 3.38
    K[methIdx][1][9] = 3.4
    K[methIdx][1][10] = 3.415
    K[methIdx][1][11] = 3.45
    K[methIdx][1][12] = 3.49
    K[methIdx][1][13] = 3.5
    K[methIdx][1][14] = 3.51
    K[methIdx][1][15] = 3.52

    P_DB[methIdx][2] = 1000.0
    PL[2] = 2
    K[methIdx][2][0] = 2.4
    K[methIdx][2][1] = 2.49
    K[methIdx][2][2] = 2.55
    K[methIdx][2][3] = 2.6
    K[methIdx][2][4] = 2.68
    K[methIdx][2][5] = 2.72
    K[methIdx][2][6] = 2.8
    K[methIdx][2][7] = 2.83
    K[methIdx][2][8] = 2.88
    K[methIdx][2][9] = 2.92
    K[methIdx][2][10] = 2.97
    K[methIdx][2][11] = 3.0
    K[methIdx][2][12] = 3.02
    K[methIdx][2][13] = 3.05
    K[methIdx][2][14] = 3.09
    K[methIdx][2][15] = 3.1

    P_DB[methIdx][3] = 1500.0
    PL[2] = 3
    K[methIdx][3][0] = 1.78
    K[methIdx][3][1] = 1.85
    K[methIdx][3][2] = 1.93
    K[methIdx][3][3] = 2.0
    K[methIdx][3][4] = 2.05
    K[methIdx][3][5] = 2.07
    K[methIdx][3][6] = 2.1
    K[methIdx][3][7] = 2.14
    K[methIdx][3][8] = 2.16
    K[methIdx][3][9] = 2.18
    K[methIdx][3][10] = 2.2
    K[methIdx][3][11] = 2.25
    K[methIdx][3][12] = 2.3
    K[methIdx][3][13] = 2.31
    K[methIdx][3][14] = 2.33
    K[methIdx][3][15] = 2.35

    P_DB[methIdx][4] = 2000.0
    PL[2] = 4
    K[methIdx][4][0] = 1.3
    K[methIdx][4][1] = 1.4
    K[methIdx][4][2] = 1.5
    K[methIdx][4][3] = 1.6
    K[methIdx][4][4] = 1.7
    K[methIdx][4][5] = 1.78
    K[methIdx][4][6] = 1.85
    K[methIdx][4][7] = 1.9
    K[methIdx][4][8] = 1.95
    K[methIdx][4][9] = 2.0
    K[methIdx][4][10] = 2.025
    K[methIdx][4][11] = 2.05
    K[methIdx][4][12] = 2.06
    K[methIdx][4][13] = 2.075
    K[methIdx][4][14] = 2.085
    K[methIdx][4][15] = 2.1

    P_DB[methIdx][5] = 2500.0
    PL[2] = 5
    K[methIdx][5][0] = 1.13
    K[methIdx][5][1] = 1.2
    K[methIdx][5][2] = 1.28
    K[methIdx][5][3] = 1.36
    K[methIdx][5][4] = 1.45
    K[methIdx][5][5] = 1.54
    K[methIdx][5][6] = 1.62
    K[methIdx][5][7] = 1.69
    K[methIdx][5][8] = 1.75
    K[methIdx][5][9] = 1.8
    K[methIdx][5][10] = 1.84
    K[methIdx][5][11] = 1.89
    K[methIdx][5][12] = 1.9
    K[methIdx][5][13] = 2.0
    K[methIdx][5][14] = 2.01
    K[methIdx][5][15] = 2.02

    P_DB[methIdx][6] = 3000.0
    PL[2] = 6
    K[methIdx][6][0] = 0.92
    K[methIdx][6][1] = 1.02
    K[methIdx][6][2] = 1.09
    K[methIdx][6][3] = 1.17
    K[methIdx][6][4] = 1.24
    K[methIdx][6][5] = 1.33
    K[methIdx][6][6] = 1.4
    K[methIdx][6][7] = 1.48
    K[methIdx][6][8] = 1.55
    K[methIdx][6][9] = 1.6
    K[methIdx][6][10] = 1.65
    K[methIdx][6][11] = 1.7
    K[methIdx][6][12] = 1.74
    K[methIdx][6][13] = 1.77
    K[methIdx][6][14] = 1.8
    K[methIdx][6][15] = 1.82

    P_DB[methIdx][7] = 3500.0
    PL[2] = 7
    K[methIdx][7][0] = 0.76
    K[methIdx][7][1] = 0.87
    K[methIdx][7][2] = 0.96
    K[methIdx][7][3] = 1.02
    K[methIdx][7][4] = 1.11
    K[methIdx][7][5] = 1.19
    K[methIdx][7][6] = 1.25
    K[methIdx][7][7] = 1.325
    K[methIdx][7][8] = 1.37
    K[methIdx][7][9] = 1.44
    K[methIdx][7][10] = 1.49
    K[methIdx][7][11] = 1.53
    K[methIdx][7][12] = 1.57
    K[methIdx][7][13] = 1.6
    K[methIdx][7][14] = 1.64
    K[methIdx][7][15] = 1.66

    P_DB[methIdx][8] = 4000.0
    PL[2] = 8
    K[methIdx][8][0] = 0.61
    K[methIdx][8][1] = 0.71
    K[methIdx][8][2] = 0.8
    K[methIdx][8][3] = 0.88
    K[methIdx][8][4] = 0.98
    K[methIdx][8][5] = 1.03
    K[methIdx][8][6] = 1.11
    K[methIdx][8][7] = 1.17
    K[methIdx][8][8] = 1.25
    K[methIdx][8][9] = 1.3
    K[methIdx][8][10] = 1.37
    K[methIdx][8][11] = 1.41
    K[methIdx][8][12] = 1.45
    K[methIdx][8][13] = 1.47
    K[methIdx][8][14] = 1.5
    K[methIdx][8][15] = 1.53

    P_DB[methIdx][9] = 5000.0
    PL[2] = 9
    K[methIdx][9][0] = 0.41
    K[methIdx][9][1] = 0.51
    K[methIdx][9][2] = 0.6
    K[methIdx][9][3] = 0.75
    K[methIdx][9][4] = 0.85
    K[methIdx][9][5] = 0.94
    K[methIdx][9][6] = 1.01
    K[methIdx][9][7] = 1.07
    K[methIdx][9][8] = 1.14
    K[methIdx][9][9] = 1.19
    K[methIdx][9][10] = 1.23
    K[methIdx][9][11] = 1.26
    K[methIdx][9][12] = 1.3
    K[methIdx][9][13] = 1.34
    K[methIdx][9][14] = 1.36
    K[methIdx][9][15] = 1.38

    P_DB[methIdx][10] = 5500.0
    PL[2] = 10
    K[methIdx][10][0] = 0.4
    K[methIdx][10][1] = 0.48
    K[methIdx][10][2] = 0.56
    K[methIdx][10][3] = 0.625
    K[methIdx][10][4] = 0.7
    K[methIdx][10][5] = 0.77
    K[methIdx][10][6] = 0.85
    K[methIdx][10][7] = 0.94
    K[methIdx][10][8] = 1.02
    K[methIdx][10][9] = 1.065
    K[methIdx][10][10] = 1.13
    K[methIdx][10][11] = 1.17
    K[methIdx][10][12] = 1.22
    K[methIdx][10][13] = 1.25
    K[methIdx][10][14] = 1.28
    K[methIdx][10][15] = 1.301

    P_DB[methIdx][11] = 7000.0
    PL[2] = 11
    K[methIdx][11][0] = 0.22
    K[methIdx][11][1] = 0.27
    K[methIdx][11][2] = 0.33
    K[methIdx][11][3] = 0.385
    K[methIdx][11][4] = 0.47
    K[methIdx][11][5] = 0.555
    K[methIdx][11][6] = 0.64
    K[methIdx][11][7] = 0.75
    K[methIdx][11][8] = 0.83
    K[methIdx][11][9] = 0.92
    K[methIdx][11][10] = 1.0
    K[methIdx][11][11] = 1.025
    K[methIdx][11][12] = 1.06
    K[methIdx][11][13] = 1.1
    K[methIdx][11][14] = 1.13
    K[methIdx][11][15] = 1.15

    P_DB[methIdx][12] = 10000.0
    PL[2] = 12
    K[methIdx][12][0] = 0.135
    K[methIdx][12][1] = 0.175
    K[methIdx][12][2] = 0.22
    K[methIdx][12][3] = 0.27
    K[methIdx][12][4] = 0.305
    K[methIdx][12][5] = 0.35
    K[methIdx][12][6] = 0.4
    K[methIdx][12][7] = 0.43
    K[methIdx][12][8] = 0.5
    K[methIdx][12][9] = 0.63
    K[methIdx][12][10] = 0.69
    K[methIdx][12][11] = 0.77
    K[methIdx][12][12] = 0.83
    K[methIdx][12][13] = 0.9
    K[methIdx][12][14] = 0.965
    K[methIdx][12][15] = 1.02

    P_DB[methIdx][13] = 15000.0
    PL[2] = 13
    K[methIdx][13][0] = 0.073
    K[methIdx][13][1] = 0.09
    K[methIdx][13][2] = 0.15
    K[methIdx][13][3] = 0.128
    K[methIdx][13][4] = 0.161
    K[methIdx][13][5] = 0.188
    K[methIdx][13][6] = 0.23
    K[methIdx][13][7] = 0.255
    K[methIdx][13][8] = 0.282
    K[methIdx][13][9] = 0.34
    K[methIdx][13][10] = 0.41
    K[methIdx][13][11] = 0.49
    K[methIdx][13][12] = 0.585
    K[methIdx][13][13] = 0.68
    K[methIdx][13][14] = 0.75
    K[methIdx][13][15] = 0.83
   
   
# Ethane index as 3

    ethIdx = 3

    #Make all the main dictionaries to contain nested dictionaries
    NOP[ethIdx] = 13
##    NOPMX[ethIdx] = {}
##    NOPMN[ethIdx] = {}
##    T_DB[ethIdx] = {}
##    P_DB[ethIdx] = {}
##    K[ethIdx] = {}
##
##    
##    for j in range(1, PC[ethIdx]+1):
##        T_DB[ethIdx][j] = {}
##        K[ethIdx][j] = {}
    for i in range(0, NOP[ethIdx]+1):
        T_DB[ethIdx][j][i] = i
            
    
    NOPMX[ethIdx][1] = 13
    NOPMN[ethIdx][1] = 0
    P_DB[ethIdx][1] = 700.0
    PL[ethIdx] = 1
    K[ethIdx][1][0] = 0.68
    K[ethIdx][1][1] = 0.73
    K[ethIdx][1][2] = 0.88
    K[ethIdx][1][3] = 0.95
    K[ethIdx][1][4] = 1.09
    K[ethIdx][1][5] = 1.2
    K[ethIdx][1][6] = 1.32
    K[ethIdx][1][7] = 1.45
    K[ethIdx][1][8] = 1.62
    K[ethIdx][1][9] = 1.77
    K[ethIdx][1][10] = 1.95
    K[ethIdx][1][11] = 2.05
    K[ethIdx][1][12] = 2.1
    K[ethIdx][1][13] = 2.17
    
    NOPMX[ethIdx][2] = 13
    NOPMN[ethIdx][2] = 0
    P_DB[ethIdx][2] = 1000.0
    PL[ethIdx] = 2
    K[ethIdx][2][0] = 0.39
    K[ethIdx][2][1] = 0.455
    K[ethIdx][2][2] = 0.55
    K[ethIdx][2][3] = 0.65
    K[ethIdx][2][4] = 0.75
    K[ethIdx][2][5] = 0.85
    K[ethIdx][2][6] = 0.95
    K[ethIdx][2][7] = 1.07
    K[ethIdx][2][8] = 1.2
    K[ethIdx][2][9] = 1.35
    K[ethIdx][2][10] = 1.55
    K[ethIdx][2][11] = 1.75
    K[ethIdx][2][12] = 1.95
    K[ethIdx][2][13] = 2.07
    
    NOPMX[ethIdx][3] = 13
    NOPMN[ethIdx][3] = 0
    P_DB[ethIdx][3] = 1500.0
    PL[ethIdx] = 3
    K[ethIdx][3][0] = 0.14
    K[ethIdx][3][1] = 0.18
    K[ethIdx][3][2] = 0.25
    K[ethIdx][3][3] = 0.317
    K[ethIdx][3][4] = 0.38
    K[ethIdx][3][5] = 0.47
    K[ethIdx][3][6] = 0.565
    K[ethIdx][3][7] = 0.67
    K[ethIdx][3][8] = 0.81
    K[ethIdx][3][9] = 0.96
    K[ethIdx][3][10] = 1.15
    K[ethIdx][3][11] = 1.35
    K[ethIdx][3][12] = 1.6
    K[ethIdx][3][13] = 1.8
    
    NOPMX[ethIdx][4] = 13
    NOPMN[ethIdx][4] = 0
    P_DB[ethIdx][4] = 2000.0
    PL[ethIdx] = 4
    K[ethIdx][4][0] = 0.03
    K[ethIdx][4][1] = 0.05
    K[ethIdx][4][2] = 0.09
    K[ethIdx][4][3] = 0.13
    K[ethIdx][4][4] = 0.19
    K[ethIdx][4][5] = 0.25
    K[ethIdx][4][6] = 0.315
    K[ethIdx][4][7] = 0.41
    K[ethIdx][4][8] = 0.515
    K[ethIdx][4][9] = 0.67
    K[ethIdx][4][10] = 0.81
    K[ethIdx][4][11] = 0.95
    K[ethIdx][4][12] = 1.1
    K[ethIdx][4][13] = 1.25
   
    NOPMX[ethIdx][5] = 15
    NOPMN[ethIdx][5] = 4
    P_DB[ethIdx][5] = 2500.0
    PL[ethIdx] = 5
    K[ethIdx][5][4] = 0.12
    K[ethIdx][5][5] = 0.17
    K[ethIdx][5][6] = 0.23
    K[ethIdx][5][7] = 0.3
    K[ethIdx][5][8] = 0.385
    K[ethIdx][5][9] = 0.48
    K[ethIdx][5][10] = 0.6
    K[ethIdx][5][11] = 0.73
    K[ethIdx][5][12] = 0.88
    K[ethIdx][5][13] = 1.01
    K[ethIdx][5][14] = 1.15
    K[ethIdx][5][15] = 1.3
    
    NOPMX[ethIdx][6] = 16
    NOPMN[ethIdx][6] = 4
    P_DB[ethIdx][6] = 3000.0
    PL[ethIdx] = 6
    K[ethIdx][6][4] = 0.1
    K[ethIdx][6][5] = 0.135
    K[ethIdx][6][6] = 0.175
    K[ethIdx][6][7] = 0.23
    K[ethIdx][6][8] = 0.3
    K[ethIdx][6][9] = 0.37
    K[ethIdx][6][10] = 0.41
    K[ethIdx][6][11] = 0.57
    K[ethIdx][6][12] = 0.7
    K[ethIdx][6][13] = 0.83
    K[ethIdx][6][14] = 0.96
    K[ethIdx][6][15] = 1.12
    K[ethIdx][6][16] = 1.35
    
    NOPMX[ethIdx][7] = 18
    NOPMN[ethIdx][7] = 6
    P_DB[ethIdx][7] = 4000.0
    PL[ethIdx] = 7
    K[ethIdx][7][6] = 0.1
    K[ethIdx][7][7] = 0.128
    K[ethIdx][7][8] = 0.17
    K[ethIdx][7][9] = 0.225
    K[ethIdx][7][10] = 0.29
    K[ethIdx][7][11] = 0.37
    K[ethIdx][7][12] = 0.46
    K[ethIdx][7][13] = 0.58
    K[ethIdx][7][14] = 0.7
    K[ethIdx][7][15] = 0.85
    K[ethIdx][7][16] = 1.0
    K[ethIdx][7][17] = 1.15
    K[ethIdx][7][18] = 1.3
    
    NOPMX[ethIdx][8] = 19
    NOPMN[ethIdx][8] = 7
    P_DB[ethIdx][8] = 5000.0
    PL[ethIdx] = 8
    K[ethIdx][8][7] = 0.09
    K[ethIdx][8][8] = 0.12
    K[ethIdx][8][9] = 0.155
    K[ethIdx][8][10] = 0.202
    K[ethIdx][8][11] = 0.26
    K[ethIdx][8][12] = 0.33
    K[ethIdx][8][13] = 0.41
    K[ethIdx][8][14] = 0.52
    K[ethIdx][8][15] = 0.65
    K[ethIdx][8][16] = 0.8
    K[ethIdx][8][17] = 0.94
    K[ethIdx][8][18] = 1.06
    K[ethIdx][8][19] = 1.21
    
    NOPMX[ethIdx][9] = 21
    NOPMN[ethIdx][9] = 9
    P_DB[ethIdx][9] = 7000.0
    PL[ethIdx] = 9
    K[ethIdx][9][9] = 0.107
    K[ethIdx][9][10] = 0.145
    K[ethIdx][9][11] = 0.19
    K[ethIdx][9][12] = 0.25
    K[ethIdx][9][13] = 0.32
    K[ethIdx][9][14] = 0.4
    K[ethIdx][9][15] = 0.49
    K[ethIdx][9][16] = 0.61
    K[ethIdx][9][17] = 0.72
    K[ethIdx][9][18] = 0.84
    K[ethIdx][9][19] = 0.97
    K[ethIdx][9][20] = 1.1
    K[ethIdx][9][21] = 1.2
    
    NOPMX[ethIdx][10] = 24
    NOPMN[ethIdx][10] = 10
    P_DB[ethIdx][10] = 10000.0
    PL[ethIdx] = 10
    K[ethIdx][10][10] = 0.11
    K[ethIdx][10][11] = 0.15
    K[ethIdx][10][12] = 0.195
    K[ethIdx][10][13] = 0.25
    K[ethIdx][10][14] = 0.32
    K[ethIdx][10][15] = 0.4
    K[ethIdx][10][16] = 0.48
    K[ethIdx][10][17] = 0.58
    K[ethIdx][10][18] = 0.68
    K[ethIdx][10][19] = 0.79
    K[ethIdx][10][20] = 0.9
    K[ethIdx][10][21] = 1.0
    K[ethIdx][10][22] = 1.1
    K[ethIdx][10][23] = 1.2
    K[ethIdx][10][24] = 1.3
    
    NOPMX[ethIdx][11] = 25
    NOPMN[ethIdx][11] = 11
    P_DB[ethIdx][11] = 15000.0
    PL[ethIdx] = 11
    K[ethIdx][11][11] = 0.106
    K[ethIdx][11][12] = 0.14
    K[ethIdx][11][13] = 0.185
    K[ethIdx][11][14] = 0.24
    K[ethIdx][11][15] = 0.3
    K[ethIdx][11][16] = 0.37
    K[ethIdx][11][17] = 0.46
    K[ethIdx][11][18] = 0.56
    K[ethIdx][11][19] = 0.65
    K[ethIdx][11][20] = 0.75
    K[ethIdx][11][21] = 0.87
    K[ethIdx][11][22] = 0.98
    K[ethIdx][11][23] = 1.08
    K[ethIdx][11][24] = 1.2
    K[ethIdx][11][25] = 1.3
    
    NOPMX[ethIdx][12] = 26
    NOPMN[ethIdx][12] = 12
    P_DB[ethIdx][12] = 20000.0
    PL[ethIdx] = 12
    K[ethIdx][12][12] = 0.125
    K[ethIdx][12][13] = 0.155
    K[ethIdx][12][14] = 0.2
    K[ethIdx][12][15] = 0.251
    K[ethIdx][12][16] = 0.31
    K[ethIdx][12][17] = 0.38
    K[ethIdx][12][18] = 0.46
    K[ethIdx][12][19] = 0.56
    K[ethIdx][12][20] = 0.66
    K[ethIdx][12][21] = 0.76
    K[ethIdx][12][22] = 0.88
    K[ethIdx][12][23] = 0.97
    K[ethIdx][12][24] = 1.07
    K[ethIdx][12][25] = 1.19
    K[ethIdx][12][26] = 1.25
    
    NOPMX[ethIdx][13] = 27
    NOPMN[ethIdx][13] = 12
    P_DB[ethIdx][13] = 25000.0
    PL[ethIdx] = 13
    K[ethIdx][13][12] = 0.11
    K[ethIdx][13][13] = 0.14
    K[ethIdx][13][14] = 0.18
    K[ethIdx][13][15] = 0.23
    K[ethIdx][13][16] = 0.29
    K[ethIdx][13][17] = 0.36
    K[ethIdx][13][18] = 0.43
    K[ethIdx][13][19] = 0.53
    K[ethIdx][13][20] = 0.62
    K[ethIdx][13][21] = 0.715
    K[ethIdx][13][22] = 0.81
    K[ethIdx][13][23] = 0.92
    K[ethIdx][13][24] = 1.03
    K[ethIdx][13][25] = 1.11
    K[ethIdx][13][26] = 1.2
    K[ethIdx][13][27] = 1.3

   
# Propane index as 4

    propIdx = 4

    #Make all the main dictionaries to contain nested dictionaries
    NOP[propIdx] = 15
##    NOPMX[propIdx] = {}
##    NOPMN[propIdx] = {}
##    T_DB[propIdx] = {}
##    P_DB[propIdx] = {}
##    K[propIdx] = {}
##
##    
##    for j in range(1, PC[propIdx]+1):
##        T_DB[propIdx][j] = {}
##        K[propIdx][j] = {}
    for i in range(0, NOP[propIdx]+1):
        T_DB[propIdx][j][i] = i

    
    NOPMX[propIdx][1] = 8
    NOPMN[propIdx][1] = 0
    P_DB[propIdx][1] = 700.0
    PL[propIdx] = 1
    K[propIdx][1][0] = 0.068
    K[propIdx][1][1] = 0.085
    K[propIdx][1][2] = 0.105
    K[propIdx][1][3] = 0.133
    K[propIdx][1][4] = 0.215
    K[propIdx][1][5] = 0.23
    K[propIdx][1][6] = 0.335
    K[propIdx][1][7] = 0.65
    K[propIdx][1][8] = 3.1
        
    NOPMX[propIdx][2] = 10
    NOPMN[propIdx][2] = 0
    P_DB[propIdx][2] = 1000.0
    PL[propIdx] = 2
    K[propIdx][2][0] = 0.0385
    K[propIdx][2][1] = 0.048
    K[propIdx][2][2] = 0.06
    K[propIdx][2][3] = 0.075
    K[propIdx][2][4] = 0.095
    K[propIdx][2][5] = 0.122
    K[propIdx][2][6] = 0.16
    K[propIdx][2][7] = 0.22
    K[propIdx][2][8] = 0.35
    K[propIdx][2][9] = 0.75
    K[propIdx][2][10] = 1.3
        
    NOPMX[propIdx][3] = 13
    NOPMN[propIdx][3] = 0
    P_DB[propIdx][3] = 1500.0
    PL[propIdx] = 3
    K[propIdx][3][0] = 0.018
    K[propIdx][3][1] = 0.022
    K[propIdx][3][2] = 0.028
    K[propIdx][3][3] = 0.035
    K[propIdx][3][4] = 0.0435
    K[propIdx][3][5] = 0.055
    K[propIdx][3][6] = 0.07
    K[propIdx][3][7] = 0.09
    K[propIdx][3][8] = 0.117
    K[propIdx][3][9] = 0.155
    K[propIdx][3][10] = 0.215
    K[propIdx][3][11] = 0.33
    K[propIdx][3][12] = 0.54
    K[propIdx][3][13] = 0.83
    
    NOPMX[propIdx][4] = 15
    NOPMN[propIdx][4] = 0
    P_DB[propIdx][4] = 2000.0
    PL[propIdx] = 4
    K[propIdx][4][0] = 0.013
    K[propIdx][4][1] = 0.015
    K[propIdx][4][2] = 0.018
    K[propIdx][4][3] = 0.0215
    K[propIdx][4][4] = 0.0295
    K[propIdx][4][5] = 0.0355
    K[propIdx][4][6] = 0.045
    K[propIdx][4][7] = 0.05
    K[propIdx][4][8] = 0.074
    K[propIdx][4][9] = 0.0974
    K[propIdx][4][10] = 0.12
    K[propIdx][4][11] = 0.165
    K[propIdx][4][12] = 0.215
    K[propIdx][4][13] = 0.31
    K[propIdx][4][14] = 0.42
    K[propIdx][4][15] = 0.715
    
    NOPMX[propIdx][5] = 18
    NOPMN[propIdx][5] = 0
    P_DB[propIdx][5] = 2500.0
    PL[propIdx] = 5
    K[propIdx][5][0] = 0.0095
    K[propIdx][5][1] = 0.0115
    K[propIdx][5][2] = 0.0143
    K[propIdx][5][3] = 0.0175
    K[propIdx][5][4] = 0.022
    K[propIdx][5][5] = 0.027
    K[propIdx][5][6] = 0.034
    K[propIdx][5][7] = 0.043
    K[propIdx][5][8] = 0.053
    K[propIdx][5][9] = 0.068
    K[propIdx][5][10] = 0.087
    K[propIdx][5][11] = 0.115
    K[propIdx][5][12] = 0.15
    K[propIdx][5][13] = 0.2
    K[propIdx][5][14] = 0.29
    K[propIdx][5][15] = 0.4
    K[propIdx][5][16] = 0.58
    K[propIdx][5][17] = 0.83
    K[propIdx][5][18] = 1.2
    
    NOPMX[propIdx][6] = 18
    NOPMN[propIdx][6] = 0
    P_DB[propIdx][6] = 3000.0
    PL[propIdx] = 6
    K[propIdx][6][0] = 0.0074
    K[propIdx][6][1] = 0.009
    K[propIdx][6][2] = 0.011
    K[propIdx][6][3] = 0.0135
    K[propIdx][6][4] = 0.0165
    K[propIdx][6][5] = 0.0205
    K[propIdx][6][6] = 0.026
    K[propIdx][6][7] = 0.032
    K[propIdx][6][8] = 0.04
    K[propIdx][6][9] = 0.051
    K[propIdx][6][10] = 0.065
    K[propIdx][6][11] = 0.083
    K[propIdx][6][12] = 0.107
    K[propIdx][6][13] = 0.14
    K[propIdx][6][14] = 0.185
    K[propIdx][6][15] = 0.27
    K[propIdx][6][16] = 0.37
    K[propIdx][6][17] = 0.54
    K[propIdx][6][18] = 0.8
        
    NOPMX[propIdx][7] = 19
    NOPMN[propIdx][7] = 0
    P_DB[propIdx][7] = 3500.0
    PL[propIdx] = 7
    K[propIdx][7][0] = 0.0058
    K[propIdx][7][1] = 0.0072
    K[propIdx][7][2] = 0.009
    K[propIdx][7][3] = 0.011
    K[propIdx][7][4] = 0.0135
    K[propIdx][7][5] = 0.017
    K[propIdx][7][6] = 0.021
    K[propIdx][7][7] = 0.0262
    K[propIdx][7][8] = 0.033
    K[propIdx][7][9] = 0.041
    K[propIdx][7][10] = 0.052
    K[propIdx][7][11] = 0.066
    K[propIdx][7][12] = 0.085
    K[propIdx][7][13] = 0.11
    K[propIdx][7][14] = 0.145
    K[propIdx][7][15] = 0.195
    K[propIdx][7][16] = 0.27
    K[propIdx][7][17] = 0.38
    K[propIdx][7][18] = 0.53
    K[propIdx][7][19] = 0.76
    
    NOPMX[propIdx][8] = 20
    NOPMN[propIdx][8] = 0
    P_DB[propIdx][8] = 4000.0
    PL[propIdx] = 8
    K[propIdx][8][0] = 0.0053
    K[propIdx][8][1] = 0.0065
    K[propIdx][8][2] = 0.0082
    K[propIdx][8][3] = 0.01
    K[propIdx][8][4] = 0.0125
    K[propIdx][8][5] = 0.015
    K[propIdx][8][6] = 0.0185
    K[propIdx][8][7] = 0.0235
    K[propIdx][8][8] = 0.029
    K[propIdx][8][9] = 0.036
    K[propIdx][8][10] = 0.045
    K[propIdx][8][11] = 0.057
    K[propIdx][8][12] = 0.073
    K[propIdx][8][13] = 0.092
    K[propIdx][8][14] = 0.12
    K[propIdx][8][15] = 0.155
    K[propIdx][8][16] = 0.212
    K[propIdx][8][17] = 0.3
    K[propIdx][8][18] = 0.402
    K[propIdx][8][19] = 0.57
    K[propIdx][8][20] = 0.8
    
    NOPMX[propIdx][9] = 20
    NOPMN[propIdx][9] = 0
    P_DB[propIdx][9] = 5000.0
    PL[propIdx] = 9
    K[propIdx][9][0] = 0.0051
    K[propIdx][9][1] = 0.0064
    K[propIdx][9][2] = 0.0073
    K[propIdx][9][3] = 0.00925
    K[propIdx][9][4] = 0.01325
    K[propIdx][9][5] = 0.0137
    K[propIdx][9][6] = 0.016
    K[propIdx][9][7] = 0.021
    K[propIdx][9][8] = 0.0251
    K[propIdx][9][9] = 0.031
    K[propIdx][9][10] = 0.038
    K[propIdx][9][11] = 0.0475
    K[propIdx][9][12] = 0.06
    K[propIdx][9][13] = 0.07
    K[propIdx][9][14] = 0.095
    K[propIdx][9][15] = 0.125
    K[propIdx][9][16] = 0.165
    K[propIdx][9][17] = 0.3
    K[propIdx][9][18] = 0.43
    K[propIdx][9][19] = 0.61
    K[propIdx][9][20] = 0.88
    
    NOPMX[propIdx][10] = 22
    NOPMN[propIdx][10] = 0
    P_DB[propIdx][10] = 7000.0
    PL[propIdx] = 9
    K[propIdx][10][0] = 0.005
    K[propIdx][10][1] = 0.006
    K[propIdx][10][2] = 0.0071
    K[propIdx][10][3] = 0.0084
    K[propIdx][10][4] = 0.0098
    K[propIdx][10][5] = 0.0115
    K[propIdx][10][6] = 0.014
    K[propIdx][10][7] = 0.0165
    K[propIdx][10][8] = 0.02
    K[propIdx][10][9] = 0.0245
    K[propIdx][10][10] = 0.03
    K[propIdx][10][11] = 0.036
    K[propIdx][10][12] = 0.046
    K[propIdx][10][13] = 0.058
    K[propIdx][10][14] = 0.075
    K[propIdx][10][15] = 0.095
    K[propIdx][10][16] = 0.125
    K[propIdx][10][17] = 0.165
    K[propIdx][10][18] = 0.22
    K[propIdx][10][19] = 0.3
    K[propIdx][10][20] = 0.41
    K[propIdx][10][21] = 0.58
    K[propIdx][10][22] = 0.8
    
    NOPMX[propIdx][11] = 23
    NOPMN[propIdx][11] = 0
    P_DB[propIdx][11] = 10000.0
    PL[propIdx] = 11
    K[propIdx][11][0] = 0.0041
    K[propIdx][11][1] = 0.005
    K[propIdx][11][2] = 0.0058
    K[propIdx][11][3] = 0.007
    K[propIdx][11][4] = 0.0082
    K[propIdx][11][5] = 0.0096
    K[propIdx][11][6] = 0.0115
    K[propIdx][11][7] = 0.014
    K[propIdx][11][8] = 0.0167
    K[propIdx][11][9] = 0.0202
    K[propIdx][11][10] = 0.025
    K[propIdx][11][11] = 0.031
    K[propIdx][11][12] = 0.039
    K[propIdx][11][13] = 0.048
    K[propIdx][11][14] = 0.063
    K[propIdx][11][15] = 0.082
    K[propIdx][11][16] = 0.106
    K[propIdx][11][17] = 0.14
    K[propIdx][11][18] = 0.185
    K[propIdx][11][19] = 0.26
    K[propIdx][11][20] = 0.34
    K[propIdx][11][21] = 0.47
    K[propIdx][11][22] = 0.665
    K[propIdx][11][23] = 0.95
    
    NOPMX[propIdx][12] = 23
    NOPMN[propIdx][12] = 0
    P_DB[propIdx][12] = 15000.0
    PL[propIdx] = 12
    K[propIdx][12][0] = 0.0033
    K[propIdx][12][1] = 0.004
    K[propIdx][12][2] = 0.0047
    K[propIdx][12][3] = 0.0058
    K[propIdx][12][4] = 0.0069
    K[propIdx][12][5] = 0.0083
    K[propIdx][12][6] = 0.01
    K[propIdx][12][7] = 0.012
    K[propIdx][12][8] = 0.0145
    K[propIdx][12][9] = 0.0175
    K[propIdx][12][10] = 0.0215
    K[propIdx][12][11] = 0.027
    K[propIdx][12][12] = 0.033
    K[propIdx][12][13] = 0.042
    K[propIdx][12][14] = 0.054
    K[propIdx][12][15] = 0.068
    K[propIdx][12][16] = 0.087
    K[propIdx][12][17] = 0.103
    K[propIdx][12][18] = 0.145
    K[propIdx][12][19] = 0.185
    K[propIdx][12][20] = 0.285
    K[propIdx][12][21] = 0.37
    K[propIdx][12][22] = 0.525
    K[propIdx][12][23] = 0.8
    
    NOPMX[propIdx][13] = 24
    NOPMN[propIdx][13] = 0
    P_DB[propIdx][13] = 20000.0
    PL[propIdx] = 13
    K[propIdx][13][0] = 0.0031
    K[propIdx][13][1] = 0.0036
    K[propIdx][13][2] = 0.0043
    K[propIdx][13][3] = 0.0052
    K[propIdx][13][4] = 0.0062
    K[propIdx][13][5] = 0.0075
    K[propIdx][13][6] = 0.0091
    K[propIdx][13][7] = 0.0109
    K[propIdx][13][8] = 0.013
    K[propIdx][13][9] = 0.016
    K[propIdx][13][10] = 0.0195
    K[propIdx][13][11] = 0.024
    K[propIdx][13][12] = 0.029
    K[propIdx][13][13] = 0.036
    K[propIdx][13][14] = 0.046
    K[propIdx][13][15] = 0.057
    K[propIdx][13][16] = 0.072
    K[propIdx][13][17] = 0.092
    K[propIdx][13][18] = 0.117
    K[propIdx][13][19] = 0.15
    K[propIdx][13][20] = 0.21
    K[propIdx][13][21] = 0.28
    K[propIdx][13][22] = 0.4
    K[propIdx][13][23] = 0.6
    K[propIdx][13][24] = 0.935
    
    NOPMX[propIdx][14] = 24
    NOPMN[propIdx][14] = 0
    P_DB[propIdx][14] = 25000.0
    PL[propIdx] = 14
    K[propIdx][14][0] = 0.0026
    K[propIdx][14][1] = 0.0031
    K[propIdx][14][2] = 0.0036
    K[propIdx][14][3] = 0.0045
    K[propIdx][14][4] = 0.0055
    K[propIdx][14][5] = 0.0065
    K[propIdx][14][6] = 0.0082
    K[propIdx][14][7] = 0.00965
    K[propIdx][14][8] = 0.012
    K[propIdx][14][9] = 0.0145
    K[propIdx][14][10] = 0.018
    K[propIdx][14][11] = 0.022
    K[propIdx][14][12] = 0.027
    K[propIdx][14][13] = 0.033
    K[propIdx][14][14] = 0.042
    K[propIdx][14][15] = 0.052
    K[propIdx][14][16] = 0.066
    K[propIdx][14][17] = 0.085
    K[propIdx][14][18] = 0.105
    K[propIdx][14][19] = 0.14
    K[propIdx][14][20] = 0.18
    K[propIdx][14][21] = 0.25
    K[propIdx][14][22] = 0.35
    K[propIdx][14][23] = 0.52
    K[propIdx][14][24] = 0.78

        
# I-Butane index as 5

    iButIdx = 5

    #Make all the main dictionaries to contain nested dictionaries
    NOP[iButIdx] = 18
##    NOPMX[iButIdx] = {}
##    NOPMN[iButIdx] = {}
##    T_DB[iButIdx] = {}
##    P_DB[iButIdx] = {}
##    K[iButIdx] = {}
##
##    
##    for j in range(1, PC[iButIdx]+1):
##        T_DB[iButIdx][j] = {}
##        K[iButIdx][j] = {}
    for i in range(0, NOP[iButIdx]+1):
        T_DB[iButIdx][j][i] = i

    
    NOPMX[iButIdx][1] = 8
    NOPMN[iButIdx][1] = 0
    P_DB[iButIdx][1] = 400.0
    PL[iButIdx] = 1
    K[iButIdx][1][0] = 0.08
    K[iButIdx][1][1] = 0.102
    K[iButIdx][1][2] = 0.12
    K[iButIdx][1][3] = 0.16
    K[iButIdx][1][4] = 0.21
    K[iButIdx][1][5] = 0.32
    K[iButIdx][1][6] = 0.44
    K[iButIdx][1][7] = 0.58
    K[iButIdx][1][8] = 0.78
        
    NOPMX[iButIdx][2] = 12
    NOPMN[iButIdx][2] = 0
    P_DB[iButIdx][2] = 700.0
    PL[iButIdx] = 2
    K[iButIdx][2][0] = 0.026
    K[iButIdx][2][1] = 0.035
    K[iButIdx][2][2] = 0.046
    K[iButIdx][2][3] = 0.059
    K[iButIdx][2][4] = 0.076
    K[iButIdx][2][5] = 0.102
    K[iButIdx][2][6] = 0.14
    K[iButIdx][2][7] = 0.19
    K[iButIdx][2][8] = 0.25
    K[iButIdx][2][9] = 0.33
    K[iButIdx][2][10] = 0.46
    K[iButIdx][2][11] = 0.62
    K[iButIdx][2][12] = 0.82
        
    NOPMX[iButIdx][3] = 15
    NOPMN[iButIdx][3] = 0
    P_DB[iButIdx][3] = 1000.0
    PL[iButIdx] = 3
    K[iButIdx][3][0] = 0.014
    K[iButIdx][3][1] = 0.0175
    K[iButIdx][3][2] = 0.022
    K[iButIdx][3][3] = 0.028
    K[iButIdx][3][4] = 0.037
    K[iButIdx][3][5] = 0.047
    K[iButIdx][3][6] = 0.0625
    K[iButIdx][3][7] = 0.086
    K[iButIdx][3][8] = 0.115
    K[iButIdx][3][9] = 0.155
    K[iButIdx][3][10] = 0.205
    K[iButIdx][3][11] = 0.28
    K[iButIdx][3][12] = 0.365
    K[iButIdx][3][13] = 0.5
    K[iButIdx][3][14] = 0.66
    K[iButIdx][3][15] = 0.9
        
    NOPMX[iButIdx][4] = 18
    NOPMN[iButIdx][4] = 0
    P_DB[iButIdx][4] = 1500.0
    PL[iButIdx] = 4
    K[iButIdx][4][0] = 0.0072
    K[iButIdx][4][1] = 0.0088
    K[iButIdx][4][2] = 0.0108
    K[iButIdx][4][3] = 0.01305
    K[iButIdx][4][4] = 0.017
    K[iButIdx][4][5] = 0.0215
    K[iButIdx][4][6] = 0.029
    K[iButIdx][4][7] = 0.037
    K[iButIdx][4][8] = 0.048
    K[iButIdx][4][9] = 0.062
    K[iButIdx][4][10] = 0.084
    K[iButIdx][4][11] = 0.116
    K[iButIdx][4][12] = 0.16
    K[iButIdx][4][13] = 0.21
    K[iButIdx][4][14] = 0.29
    K[iButIdx][4][15] = 0.4
    K[iButIdx][4][16] = 0.52
    K[iButIdx][4][17] = 0.72
    K[iButIdx][4][18] = 0.98
    
    NOPMX[iButIdx][5] = 18
    NOPMN[iButIdx][5] = 0
    P_DB[iButIdx][5] = 2000.0
    PL[iButIdx] = 5
    K[iButIdx][5][0] = 0.0041
    K[iButIdx][5][1] = 0.005
    K[iButIdx][5][2] = 0.0061
    K[iButIdx][5][3] = 0.0076
    K[iButIdx][5][4] = 0.0092
    K[iButIdx][5][5] = 0.012
    K[iButIdx][5][6] = 0.015
    K[iButIdx][5][7] = 0.0192
    K[iButIdx][5][8] = 0.026
    K[iButIdx][5][9] = 0.035
    K[iButIdx][5][10] = 0.045
    K[iButIdx][5][11] = 0.06
    K[iButIdx][5][12] = 0.08
    K[iButIdx][5][13] = 0.11
    K[iButIdx][5][14] = 0.15
    K[iButIdx][5][15] = 0.2
    K[iButIdx][5][16] = 0.28
    K[iButIdx][5][17] = 0.38
    K[iButIdx][5][18] = 0.47
    
    NOPMX[iButIdx][6] = 21
    NOPMN[iButIdx][6] = 0
    P_DB[iButIdx][6] = 2500.0
    PL[iButIdx] = 6
    K[iButIdx][6][0] = 0.00325
    K[iButIdx][6][1] = 0.0038
    K[iButIdx][6][2] = 0.0048
    K[iButIdx][6][3] = 0.0059
    K[iButIdx][6][4] = 0.0073
    K[iButIdx][6][5] = 0.009
    K[iButIdx][6][6] = 0.0118
    K[iButIdx][6][7] = 0.015
    K[iButIdx][6][8] = 0.019
    K[iButIdx][6][9] = 0.024
    K[iButIdx][6][10] = 0.032
    K[iButIdx][6][11] = 0.042
    K[iButIdx][6][12] = 0.056
    K[iButIdx][6][13] = 0.072
    K[iButIdx][6][14] = 0.096
    K[iButIdx][6][15] = 0.13
    K[iButIdx][6][16] = 0.18
    K[iButIdx][6][17] = 0.245
    K[iButIdx][6][18] = 0.33
    K[iButIdx][6][19] = 0.445
    K[iButIdx][6][20] = 0.62
    K[iButIdx][6][21] = 0.86
    
    NOPMX[iButIdx][7] = 23
    NOPMN[iButIdx][7] = 0
    P_DB[iButIdx][7] = 3500.0
    PL[iButIdx] = 7
    K[iButIdx][7][0] = 0.0022
    K[iButIdx][7][1] = 0.0027
    K[iButIdx][7][2] = 0.0034
    K[iButIdx][7][3] = 0.004
    K[iButIdx][7][4] = 0.005
    K[iButIdx][7][5] = 0.0062
    K[iButIdx][7][6] = 0.0078
    K[iButIdx][7][7] = 0.0097
    K[iButIdx][7][8] = 0.0122
    K[iButIdx][7][9] = 0.016
    K[iButIdx][7][10] = 0.02
    K[iButIdx][7][11] = 0.025
    K[iButIdx][7][12] = 0.033
    K[iButIdx][7][13] = 0.042
    K[iButIdx][7][14] = 0.057
    K[iButIdx][7][15] = 0.077
    K[iButIdx][7][16] = 0.101
    K[iButIdx][7][17] = 0.14
    K[iButIdx][7][18] = 0.19
    K[iButIdx][7][19] = 0.26
    K[iButIdx][7][20] = 0.35
    K[iButIdx][7][21] = 0.47
    K[iButIdx][7][22] = 0.66
    K[iButIdx][7][23] = 0.9
    
    NOPMX[iButIdx][8] = 25
    NOPMN[iButIdx][8] = 0
    P_DB[iButIdx][8] = 5500.0
    PL[iButIdx] = 8
    K[iButIdx][8][0] = 0.00155
    K[iButIdx][8][1] = 0.002
    K[iButIdx][8][2] = 0.0024
    K[iButIdx][8][3] = 0.0031
    K[iButIdx][8][4] = 0.0039
    K[iButIdx][8][5] = 0.0048
    K[iButIdx][8][6] = 0.006
    K[iButIdx][8][7] = 0.0076
    K[iButIdx][8][8] = 0.0094
    K[iButIdx][8][9] = 0.012
    K[iButIdx][8][10] = 0.015
    K[iButIdx][8][11] = 0.019
    K[iButIdx][8][12] = 0.024
    K[iButIdx][8][13] = 0.031
    K[iButIdx][8][14] = 0.04
    K[iButIdx][8][15] = 0.052
    K[iButIdx][8][16] = 0.07
    K[iButIdx][8][17] = 0.09
    K[iButIdx][8][18] = 0.12
    K[iButIdx][8][19] = 0.155
    K[iButIdx][8][20] = 0.2
    K[iButIdx][8][21] = 0.27
    K[iButIdx][8][22] = 0.35
    K[iButIdx][8][23] = 0.47
    K[iButIdx][8][24] = 0.615
    K[iButIdx][8][25] = 0.8
    
    NOPMX[iButIdx][9] = 27
    NOPMN[iButIdx][9] = 0
    P_DB[iButIdx][9] = 10000.0
    PL[iButIdx] = 9
    K[iButIdx][9][0] = 0.00135
    K[iButIdx][9][1] = 0.00165
    K[iButIdx][9][2] = 0.0021
    K[iButIdx][9][3] = 0.0027
    K[iButIdx][9][4] = 0.0033
    K[iButIdx][9][5] = 0.0041
    K[iButIdx][9][6] = 0.0052
    K[iButIdx][9][7] = 0.0065
    K[iButIdx][9][8] = 0.0082
    K[iButIdx][9][9] = 0.0101
    K[iButIdx][9][10] = 0.013
    K[iButIdx][9][11] = 0.016
    K[iButIdx][9][12] = 0.02
    K[iButIdx][9][13] = 0.0255
    K[iButIdx][9][14] = 0.033
    K[iButIdx][9][15] = 0.041
    K[iButIdx][9][16] = 0.0515
    K[iButIdx][9][17] = 0.066
    K[iButIdx][9][18] = 0.082
    K[iButIdx][9][19] = 0.105
    K[iButIdx][9][20] = 0.132
    K[iButIdx][9][21] = 0.17
    K[iButIdx][9][22] = 0.22
    K[iButIdx][9][23] = 0.285
    K[iButIdx][9][24] = 0.365
    K[iButIdx][9][25] = 0.48
    K[iButIdx][9][26] = 0.62
    K[iButIdx][9][27] = 0.8
        
    
# Carbon Dioxide index as 7
    co2Idx = 7

    #Make all the main dictionaries to contain nested dictionaries
    NOP[co2Idx] = 10
##    NOPMX[co2Idx] = {}
##    NOPMN[co2Idx] = {}
##    T_DB[co2Idx] = {}
##    P_DB[co2Idx] = {}
##    K[co2Idx] = {}
##    
##    for j in range(1, PC[co2Idx]+1):
##        T_DB[co2Idx][j] = {}
##        K[co2Idx][j] = {}
    for i in range(0, NOP[co2Idx]+1):
        T_DB[co2Idx][j][i] = i

    
    NOPMX[co2Idx][1] = 8
    NOPMN[co2Idx][1] = 0
    P_DB[co2Idx][1] = 1300.0
    PL[co2Idx] = 1
    K[co2Idx][1][0] = 0.7
    K[co2Idx][1][1] = 0.78
    K[co2Idx][1][2] = 0.9
    K[co2Idx][1][3] = 1.05
    K[co2Idx][1][4] = 1.25
    K[co2Idx][1][5] = 1.6
    K[co2Idx][1][6] = 2.0
    K[co2Idx][1][7] = 2.5
    K[co2Idx][1][8] = 3.15
        
    NOPMX[co2Idx][2] = 10
    NOPMN[co2Idx][2] = 0
    P_DB[co2Idx][2] = 2000.0
    PL[co2Idx] = 2
    K[co2Idx][2][0] = 0.6
    K[co2Idx][2][1] = 0.68
    K[co2Idx][2][2] = 0.78
    K[co2Idx][2][3] = 0.9
    K[co2Idx][2][4] = 0.95
    K[co2Idx][2][5] = 1.2
    K[co2Idx][2][6] = 1.45
    K[co2Idx][2][7] = 1.7
    K[co2Idx][2][8] = 2.0
    K[co2Idx][2][9] = 2.4
    K[co2Idx][2][10] = 2.9
   
    NOPMX[co2Idx][3] = 11
    NOPMN[co2Idx][3] = 0
    P_DB[co2Idx][3] = 2500.0
    PL[co2Idx] = 3
    K[co2Idx][3][0] = 0.52
    K[co2Idx][3][1] = 0.56
    K[co2Idx][3][2] = 0.62
    K[co2Idx][3][3] = 0.68
    K[co2Idx][3][4] = 0.8
    K[co2Idx][3][5] = 0.92
    K[co2Idx][3][6] = 1.1
    K[co2Idx][3][7] = 1.3
    K[co2Idx][3][8] = 1.55
    K[co2Idx][3][9] = 1.9
    K[co2Idx][3][10] = 2.35
    K[co2Idx][3][11] = 2.9
    
    NOPMX[co2Idx][4] = 12
    NOPMN[co2Idx][4] = 0
    P_DB[co2Idx][4] = 3500.0
    PL[co2Idx] = 4
    K[co2Idx][4][0] = 0.45
    K[co2Idx][4][1] = 0.485
    K[co2Idx][4][2] = 0.53
    K[co2Idx][4][3] = 0.58
    K[co2Idx][4][4] = 0.66
    K[co2Idx][4][5] = 0.72
    K[co2Idx][4][6] = 0.82
    K[co2Idx][4][7] = 0.95
    K[co2Idx][4][8] = 1.1
    K[co2Idx][4][9] = 1.35
    K[co2Idx][4][10] = 1.62
    K[co2Idx][4][11] = 2.05
    K[co2Idx][4][12] = 2.5
    
    NOPMX[co2Idx][5] = 14
    NOPMN[co2Idx][5] = 0
    P_DB[co2Idx][5] = 4000.0
    PL[co2Idx] = 5
    K[co2Idx][5][0] = 0.325
    K[co2Idx][5][1] = 0.36
    K[co2Idx][5][2] = 0.39
    K[co2Idx][5][3] = 0.43
    K[co2Idx][5][4] = 0.47
    K[co2Idx][5][5] = 0.53
    K[co2Idx][5][6] = 0.585
    K[co2Idx][5][7] = 0.67
    K[co2Idx][5][8] = 0.765
    K[co2Idx][5][9] = 0.9
    K[co2Idx][5][10] = 1.105
    K[co2Idx][5][11] = 1.3
    K[co2Idx][5][12] = 1.65
    K[co2Idx][5][13] = 2.25
    K[co2Idx][5][14] = 3.1
    
    NOPMX[co2Idx][6] = 14
    NOPMN[co2Idx][6] = 0
    P_DB[co2Idx][6] = 6000.0
    PL[co2Idx] = 6
    K[co2Idx][6][0] = 0.2
    K[co2Idx][6][1] = 0.225
    K[co2Idx][6][2] = 0.26
    K[co2Idx][6][3] = 0.3
    K[co2Idx][6][4] = 0.34
    K[co2Idx][6][5] = 0.39
    K[co2Idx][6][6] = 0.45
    K[co2Idx][6][7] = 0.5
    K[co2Idx][6][8] = 0.58
    K[co2Idx][6][9] = 0.66
    K[co2Idx][6][10] = 0.76
    K[co2Idx][6][11] = 0.9
    K[co2Idx][6][12] = 1.08
    K[co2Idx][6][13] = 1.47
    K[co2Idx][6][14] = 2.25
    
    NOPMX[co2Idx][7] = 15
    NOPMN[co2Idx][7] = 0
    P_DB[co2Idx][7] = 7000.0
    PL[co2Idx] = 7
    K[co2Idx][7][0] = 0.18
    K[co2Idx][7][1] = 0.2
    K[co2Idx][7][2] = 0.225
    K[co2Idx][7][3] = 0.25
    K[co2Idx][7][4] = 0.285
    K[co2Idx][7][5] = 0.325
    K[co2Idx][7][6] = 0.36
    K[co2Idx][7][7] = 0.415
    K[co2Idx][7][8] = 0.46
    K[co2Idx][7][9] = 0.53
    K[co2Idx][7][10] = 0.6
    K[co2Idx][7][11] = 0.68
    K[co2Idx][7][12] = 0.815
    K[co2Idx][7][13] = 1.0
    K[co2Idx][7][14] = 1.45
    K[co2Idx][7][15] = 3.0


    
# H2S index as 8

    h2sIdx = 8

    #Make all the main dictionaries to contain nested dictionaries
    NOP[h2sIdx] = 30
##    NOPMX[h2sIdx] = {}
##    NOPMN[h2sIdx] = {}
##    T_DB[h2sIdx] = {}
##    P_DB[h2sIdx] = {}
##    K[h2sIdx] = {}
##    
##    for j in range(1, PC[h2sIdx]+1):
##        T_DB[h2sIdx][j] = {}
##        K[h2sIdx][j] = {}
    for i in range(0, NOP[h2sIdx]+1):
        T_DB[h2sIdx][j][i] = i
            
    
    NOPMX[h2sIdx][1] = 19
    NOPMN[h2sIdx][1] = 0
    P_DB[h2sIdx][1] = 700.0
    PL[h2sIdx] = 1
    K[h2sIdx][1][0] = 0.22
    K[h2sIdx][1][1] = 0.24
    K[h2sIdx][1][2] = 0.27
    K[h2sIdx][1][3] = 0.29
    K[h2sIdx][1][4] = 0.33
    K[h2sIdx][1][5] = 0.37
    K[h2sIdx][1][6] = 0.4
    K[h2sIdx][1][7] = 0.43
    K[h2sIdx][1][8] = 0.46
    K[h2sIdx][1][9] = 0.5
    K[h2sIdx][1][10] = 0.54
    K[h2sIdx][1][11] = 0.58
    K[h2sIdx][1][12] = 0.62
    K[h2sIdx][1][13] = 0.66
    K[h2sIdx][1][14] = 0.72
    K[h2sIdx][1][15] = 0.77
    K[h2sIdx][1][16] = 0.82
    K[h2sIdx][1][17] = 0.87
    K[h2sIdx][1][18] = 0.92
    K[h2sIdx][1][19] = 0.98
        
    NOPMX[h2sIdx][2] = 22
    NOPMN[h2sIdx][2] = 0
    P_DB[h2sIdx][2] = 1000.0
    PL[h2sIdx] = 2
    K[h2sIdx][2][0] = 0.15
    K[h2sIdx][2][1] = 0.17
    K[h2sIdx][2][2] = 0.19
    K[h2sIdx][2][3] = 0.215
    K[h2sIdx][2][4] = 0.24
    K[h2sIdx][2][5] = 0.265
    K[h2sIdx][2][6] = 0.3
    K[h2sIdx][2][7] = 0.33
    K[h2sIdx][2][8] = 0.35
    K[h2sIdx][2][9] = 0.37
    K[h2sIdx][2][10] = 0.42
    K[h2sIdx][2][11] = 0.45
    K[h2sIdx][2][12] = 0.49
    K[h2sIdx][2][13] = 0.52
    K[h2sIdx][2][14] = 0.56
    K[h2sIdx][2][15] = 0.61
    K[h2sIdx][2][16] = 0.66
    K[h2sIdx][2][17] = 0.71
    K[h2sIdx][2][18] = 0.76
    K[h2sIdx][2][19] = 0.81
    K[h2sIdx][2][20] = 0.88
    K[h2sIdx][2][21] = 0.92
    K[h2sIdx][2][22] = 0.98
        
    NOPMX[h2sIdx][3] = 24
    NOPMN[h2sIdx][3] = 0
    P_DB[h2sIdx][3] = 1300.0
    PL[h2sIdx] = 3
    K[h2sIdx][3][0] = 0.096
    K[h2sIdx][3][1] = 0.11
    K[h2sIdx][3][2] = 0.13
    K[h2sIdx][3][3] = 0.15
    K[h2sIdx][3][4] = 0.17
    K[h2sIdx][3][5] = 0.188
    K[h2sIdx][3][6] = 0.208
    K[h2sIdx][3][7] = 0.23
    K[h2sIdx][3][8] = 0.26
    K[h2sIdx][3][9] = 0.29
    K[h2sIdx][3][10] = 0.31
    K[h2sIdx][3][11] = 0.34
    K[h2sIdx][3][12] = 0.375
    K[h2sIdx][3][13] = 0.41
    K[h2sIdx][3][14] = 0.45
    K[h2sIdx][3][15] = 0.48
    K[h2sIdx][3][16] = 0.52
    K[h2sIdx][3][17] = 0.56
    K[h2sIdx][3][18] = 0.62
    K[h2sIdx][3][19] = 0.66
    K[h2sIdx][3][20] = 0.72
    K[h2sIdx][3][21] = 0.78
    K[h2sIdx][3][22] = 0.84
    K[h2sIdx][3][23] = 0.9
    K[h2sIdx][3][24] = 0.955
        
    NOPMX[h2sIdx][4] = 30
    NOPMN[h2sIdx][4] = 0
    P_DB[h2sIdx][4] = 2000.0
    PL[h2sIdx] = 4
    K[h2sIdx][4][0] = 0.052
    K[h2sIdx][4][1] = 0.067
    K[h2sIdx][4][2] = 0.08
    K[h2sIdx][4][3] = 0.093
    K[h2sIdx][4][4] = 0.11
    K[h2sIdx][4][5] = 0.13
    K[h2sIdx][4][6] = 0.15
    K[h2sIdx][4][7] = 0.17
    K[h2sIdx][4][8] = 0.19
    K[h2sIdx][4][9] = 0.215
    K[h2sIdx][4][10] = 0.23
    K[h2sIdx][4][11] = 0.26
    K[h2sIdx][4][12] = 0.28
    K[h2sIdx][4][13] = 0.31
    K[h2sIdx][4][14] = 0.34
    K[h2sIdx][4][15] = 0.37
    K[h2sIdx][4][16] = 0.4
    K[h2sIdx][4][17] = 0.44
    K[h2sIdx][4][18] = 0.46
    K[h2sIdx][4][19] = 0.5
    K[h2sIdx][4][20] = 0.54
    K[h2sIdx][4][21] = 0.58
    K[h2sIdx][4][22] = 0.62
    K[h2sIdx][4][23] = 0.67
    K[h2sIdx][4][24] = 0.72
    K[h2sIdx][4][25] = 0.77
    K[h2sIdx][4][26] = 0.83
    K[h2sIdx][4][27] = 0.88
    K[h2sIdx][4][28] = 0.94
    K[h2sIdx][4][29] = 0.98
    K[h2sIdx][4][30] = 1.1
    
    NOPMX[h2sIdx][5] = 27
    NOPMN[h2sIdx][5] = 0
    P_DB[h2sIdx][5] = 3000.0
    PL[h2sIdx] = 5
    K[h2sIdx][5][0] = 0.029
    K[h2sIdx][5][1] = 0.036
    K[h2sIdx][5][2] = 0.045
    K[h2sIdx][5][3] = 0.053
    K[h2sIdx][5][4] = 0.07
    K[h2sIdx][5][5] = 0.09
    K[h2sIdx][5][6] = 0.105
    K[h2sIdx][5][7] = 0.1205
    K[h2sIdx][5][8] = 0.1402
    K[h2sIdx][5][9] = 0.16
    K[h2sIdx][5][10] = 0.1805
    K[h2sIdx][5][11] = 0.21
    K[h2sIdx][5][12] = 0.23
    K[h2sIdx][5][13] = 0.25
    K[h2sIdx][5][14] = 0.27
    K[h2sIdx][5][15] = 0.3
    K[h2sIdx][5][16] = 0.33
    K[h2sIdx][5][17] = 0.36
    K[h2sIdx][5][18] = 0.39
    K[h2sIdx][5][19] = 0.43
    K[h2sIdx][5][20] = 0.46
    K[h2sIdx][5][21] = 0.495
    K[h2sIdx][5][22] = 0.52
    K[h2sIdx][5][23] = 0.55
    K[h2sIdx][5][24] = 0.58
    K[h2sIdx][5][25] = 0.62
    K[h2sIdx][5][26] = 0.66
    K[h2sIdx][5][27] = 0.715
    
    NOPMX[h2sIdx][6] = 27
    NOPMN[h2sIdx][6] = 0
    P_DB[h2sIdx][6] = 5000.0
    PL[h2sIdx] = 6
    K[h2sIdx][6][0] = 0.0084
    K[h2sIdx][6][1] = 0.0105
    K[h2sIdx][6][2] = 0.015
    K[h2sIdx][6][3] = 0.018
    K[h2sIdx][6][4] = 0.025
    K[h2sIdx][6][5] = 0.03
    K[h2sIdx][6][6] = 0.04
    K[h2sIdx][6][7] = 0.054
    K[h2sIdx][6][8] = 0.07
    K[h2sIdx][6][9] = 0.095
    K[h2sIdx][6][10] = 0.117
    K[h2sIdx][6][11] = 0.14
    K[h2sIdx][6][12] = 0.165
    K[h2sIdx][6][13] = 0.19
    K[h2sIdx][6][14] = 0.22
    K[h2sIdx][6][15] = 0.25
    K[h2sIdx][6][16] = 0.275
    K[h2sIdx][6][17] = 0.3
    K[h2sIdx][6][18] = 0.34
    K[h2sIdx][6][19] = 0.365
    K[h2sIdx][6][20] = 0.4
    K[h2sIdx][6][21] = 0.43
    K[h2sIdx][6][22] = 0.455
    K[h2sIdx][6][23] = 0.485
    K[h2sIdx][6][24] = 0.52
    K[h2sIdx][6][25] = 0.56
    K[h2sIdx][6][26] = 0.59
    K[h2sIdx][6][27] = 0.635
    
    NOPMX[h2sIdx][7] = 27
    NOPMN[h2sIdx][7] = 0
    P_DB[h2sIdx][7] = 15000.0
    PL[h2sIdx] = 7
    K[h2sIdx][7][0] = 0.0013
    K[h2sIdx][7][1] = 0.00175
    K[h2sIdx][7][2] = 0.0023
    K[h2sIdx][7][3] = 0.003
    K[h2sIdx][7][4] = 0.004
    K[h2sIdx][7][5] = 0.005
    K[h2sIdx][7][6] = 0.007
    K[h2sIdx][7][7] = 0.0091
    K[h2sIdx][7][8] = 0.013
    K[h2sIdx][7][9] = 0.016
    K[h2sIdx][7][10] = 0.021
    K[h2sIdx][7][11] = 0.028
    K[h2sIdx][7][12] = 0.036
    K[h2sIdx][7][13] = 0.047
    K[h2sIdx][7][14] = 0.066
    K[h2sIdx][7][15] = 0.085
    K[h2sIdx][7][16] = 0.115
    K[h2sIdx][7][17] = 0.16
    K[h2sIdx][7][18] = 0.2
    K[h2sIdx][7][19] = 0.25
    K[h2sIdx][7][20] = 0.29
    K[h2sIdx][7][21] = 0.335
    K[h2sIdx][7][22] = 0.37
    K[h2sIdx][7][23] = 0.42
    K[h2sIdx][7][24] = 0.46
    K[h2sIdx][7][25] = 0.49
    K[h2sIdx][7][26] = 0.52
    K[h2sIdx][7][27] = 0.56

        
# Nitrogen index as 1
    nIdx = 1

    #Make all the main dictionaries to contain nested dictionaries
    NOP[nIdx] = 30
##    NOPMX[nIdx] = {}
##    NOPMN[nIdx] = {}
##    T_DB[nIdx] = {}
##    P_DB[nIdx] = {}
##    K[nIdx] = {}

    for j in range(1, 15 +1):
##        T_DB[nIdx][j] = {}
##        K[nIdx][j] = {}
        NOPMX[nIdx][j] = 30
        NOPMN[nIdx][j] = 0
        PL[nIdx] = j
        
        for i in range(0, NOP[nIdx]+1):
            T_DB[nIdx][j][i] = i
            K[nIdx][j][i] = 1000000000.0

    P_DB[nIdx][1] = 400.0
    P_DB[nIdx][2] = 700.0
    P_DB[nIdx][3] = 1000.0
    P_DB[nIdx][4] = 1500.0
    P_DB[nIdx][5] = 2000.0
    P_DB[nIdx][6] = 2500.0
    P_DB[nIdx][7] = 3000.0
    P_DB[nIdx][8] = 4000.0
    P_DB[nIdx][9] = 5000.0
    P_DB[nIdx][10] = 7000.0
    P_DB[nIdx][11] = 10000.0
    P_DB[nIdx][12] = 15000.0
    P_DB[nIdx][13] = 20000.0
    P_DB[nIdx][14] = 25000.0
        


 # n-C4 index as 6

    nC4Idx = 6

    #Make all the main dictionaries to contain nested dictionaries
    NOP[nC4Idx] = 30
##    NOPMX[nC4Idx] = {}
##    NOPMN[nC4Idx] = {}
##    T_DB[nC4Idx] = {}
##    P_DB[nC4Idx] = {}
##    K[nC4Idx] = {}
    
    for j in range(1, 15 +1):
##        T_DB[nC4Idx][j] = {}
##        K[nC4Idx][j] = {}
        NOPMX[nC4Idx][j] = 30
        NOPMN[nC4Idx][j] = 0
        PL[nC4Idx] = j
        
        for i in range(0, NOP[nC4Idx]+1):
            T_DB[nC4Idx][j][i] = i
            K[nC4Idx][j][i] = 1000000000.0

    P_DB[nC4Idx][1] = 400.0
    P_DB[nC4Idx][2] = 700.0
    P_DB[nC4Idx][3] = 1000.0
    P_DB[nC4Idx][4] = 1500.0
    P_DB[nC4Idx][5] = 2000.0
    P_DB[nC4Idx][6] = 2500.0
    P_DB[nC4Idx][7] = 3000.0
    P_DB[nC4Idx][8] = 4000.0
    P_DB[nC4Idx][9] = 5000.0
    P_DB[nC4Idx][10] = 7000.0
    P_DB[nC4Idx][11] = 10000.0
    P_DB[nC4Idx][12] = 15000.0
    P_DB[nC4Idx][13] = 20000.0
    P_DB[nC4Idx][14] = 25000.0
    

    
# Water index as 9

    waterIdx = 9

    #Make all the main dictionaries to contain nested dictionaries
    NOP[waterIdx] = 30
##    NOPMX[waterIdx] = {}
##    NOPMN[waterIdx] = {}
##    T_DB[waterIdx] = {}
##    P_DB[waterIdx] = {}
##    K[waterIdx] = {}
    
    for j in range(1, 15 +1):
##        T_DB[waterIdx][j] = {}
##        K[waterIdx][j] = {}
        NOPMX[waterIdx][j] = 30
        NOPMN[waterIdx][j] = 0
        PL[waterIdx] = j
        
        for i in range(0, NOP[waterIdx]+1):
            T_DB[waterIdx][j][i] = i
            K[waterIdx][j][i] = 1000000000.0

    P_DB[waterIdx][1] = 400.0
    P_DB[waterIdx][2] = 700.0
    P_DB[waterIdx][3] = 1000.0
    P_DB[waterIdx][4] = 1500.0
    P_DB[waterIdx][5] = 2000.0
    P_DB[waterIdx][6] = 2500.0
    P_DB[waterIdx][7] = 3000.0
    P_DB[waterIdx][8] = 4000.0
    P_DB[waterIdx][9] = 5000.0
    P_DB[waterIdx][10] = 7000.0
    P_DB[waterIdx][11] = 10000.0
    P_DB[waterIdx][12] = 15000.0
    P_DB[waterIdx][13] = 20000.0
    P_DB[waterIdx][14] = 25000.0
    

    
    
    #Extrapolation work

    for i in range(1, N+1):
        for j in range(0, PC[i]+1):
            if not T_DB[i].has_key(j):
                T_DB[i][j] = {}
            for L in range(0, 30+1):
                T_DB[i][j][L] = L


      # Extrapolation down to 0 celsius
    for i in range(1, N+1):
        for KK in range(1, PC[i]+1):
            if NOPMN[i][KK] > 0.0:
                for j in range(NOPMN[i][KK]-1, -1, -1):
                    T_DB[i][KK][j] = j
                    baseIdx = NOPMN[i][KK]
                    K0 = K[i][KK][baseIdx]
                    K1 = K[i][KK][baseIdx+1]
                    T0 = T_DB[i][KK][baseIdx]
                    T1 = T_DB[i][KK][baseIdx + 1]
                    K[i][KK][j] = K0 - (K0-K1)/(T1-T0) * (T0-j)
        NOP[i] = 30


        
    # Extrapolation up to 30 celsius

    for i in range(1, N+1):
        for KK in range(1, PC[i]+1):
            if NOPMX[i][KK] < 30.0:
                for j in range(NOPMX[i][KK]+1, 35+1):
                    T_DB[i][KK][j] = j
                    baseIdx = NOPMX[i][KK]
                    K0 = K[i][KK][baseIdx]
                    K1 = K[i][KK][baseIdx-1]
                    T0 = T_DB[i][KK][baseIdx]
                    T1 = T_DB[i][KK][baseIdx-1]
                    K[i][KK][j] = (K0-K1)/(T0-T1) * (j-T0) + K0

        NOP[i] = 30
