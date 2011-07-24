# Depeopanizer test (from old Hysim manual)
units Field
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + Methane Ethane PROPANE
thermo + ISOBUTANE n-BUTANE ISOPENTANE n-PENTANE n-Hexane
thermo + n-Heptane n-Octane

deprop = Tower.Tower()
deprop.Stage_0 + 9  # eleven stages`

cd deprop.Stage_0

v = Tower.VapourDraw()
v.Port.P = 200
v.Port.Fraction.ISOBUTANE = .01

# add estimate of overhead
v.FlowEst = Tower.Estimate('MoleFlow')
v.FlowEst.Value = 400

cond = Tower.EnergyFeed(0)

estT = Tower.Estimate('T')
estT.Value = 25

cd ../Stage_5
f = Tower.Feed()
f.Port.T = 50
f.Port.P = 480
f.Port.MoleFlow = 1000
f.Port.Fraction = .1702 .1473 .1132 .1166 .1066 .0963 .0829 .0694 .0558 .0417
f.Port

cd ../Stage_10
l = Tower.LiquidDraw()
l.Port.P = 205
l.Port.Fraction.PROPANE = .02

reb = Tower.EnergyFeed(1)
estT = Tower.Estimate('T')
estT.Value = 250

# add two stage reboiler
. + 2

cd ../Stage_11
SSLiqFeed = Tower.Feed()
SSRetVap = Tower.VapourDraw()
SSRetVap.Port.P = 200

cd ../Stage_12
SSBtms = Tower.LiquidDraw()
SSBtms.Port.P = 200

SSVapFeed = Tower.Feed()
cd SSVapFeed.Port
T = 250
P = 200
MoleFlow = 22
Fraction = 0 1 10 10 1 0 0 0 0 0

cd /deprop.Stage_6
SSRet = Tower.Feed()
SSRet.Port -> /deprop.Stage_11.SSRetVap.Port

cd ../Stage_7
LiqToSS = Tower.LiquidDraw()
#LiqToSS.Port.MoleFlow = 20
LiqToSS.Port.MassFlow = 1250
LiqToSS.Port -> /deprop.Stage_11.SSLiqFeed.Port

cd /deprop
TryToSolve = 1  # start calculation

/deprop.Stage_0.v.Port
/deprop.Stage_10.l.Port
/deprop.Stage_11.SSLiqFeed.Port
/deprop.Stage_11.SSRetVap.Port
/deprop.Stage_12.SSBtms.Port

/deprop.L
/deprop.V
/deprop.T


#Add some pressure profile handling
cd /
/deprop.P_Profile.Values

#Get rid of the P in the last SS draw
/deprop.Stage_12.SSBtms.Port.P =
/deprop.P_Profile.Values


#Get rid of the P in the first SS draw
#The P in this stage is an average of the P of the connected stages
/deprop.Stage_11.SSRetVap.Port.P =
/deprop.P_Profile.Values


#Get rid of the P at the top
/deprop.Stage_0.v.Port.P =
/deprop.P_Profile.Values


#Get rid of the P at the bottom of main section
/deprop.Stage_10.l.Port.P =
/deprop.P_Profile.Values


#Put a pressure in the side stripper
#It should not solve as there is no P in the main section yet
/deprop.Stage_11.SSRetVap.Port.P = 210
/deprop.P_Profile.Values


#Put a pressure in a stage
/deprop.P_Profile.Item2 = 205.0
/deprop.P_Profile.Values


#Add a stage to the side stripper and see if it does an  independent interpolation of P
/deprop.Stage_11 + 1
/deprop.P_Profile.Values
/deprop.TryToSolve = 0
/deprop.P_Profile.Item13 = 215.0
/deprop.TryToSolve = 1
/deprop.P_Profile.Values

copy /deprop
paste /

/depropClone.Stage_0.v.Port
/depropClone.Stage_10.l.Port
/depropClone.Stage_11.SSLiqFeed.Port
/depropClone.Stage_11.SSRetVap.Port
/depropClone.Stage_13.SSBtms.Port

