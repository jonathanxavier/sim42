# Simple distilation column test
units SI
$thermo = VirtualMaterials.Advanced_Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

col = Tower.Tower()
col.Stage_0 + 20  # twenty two stages`

cd col.Stage_10
f = Tower.Feed()
f.Port.T = 30
f.Port.P = 720
f.Port.MoleFlow = 10
f.Port.Fraction = .4 .05 .4 .15
f.Port

cd ../Stage_0
l = Tower.LiquidDraw()
l.Port.P = 700

l.Port.MoleFlow = 5

cond = Tower.EnergyFeed(0)

reflux = Tower.StageSpecification('Reflux')
reflux.Value = 1

cd ../Stage_21
l = Tower.LiquidDraw()
l.Port.P = 730
reb = Tower.EnergyFeed(1)

cd ..
TryToSolve = 1  # start calculation

# since there was little output here, I will put some profile stuff here
L_MassFraction.PROPANE
V_MoleFraction.ISOBUTANE
L_MassFlow
L_Viscosity
L_StdVolFraction.PROPANE
V_StdVolFraction.PROPANE
L_VolumeFlow
L_StdLiqVolumeFlow
V_StdLiqVolumeFlow


#Now lets test efficiencies
Efficiencies

#Make sure it works for zero flow in vap
/col.Stage_0.v = Tower.VapourDraw()
/col.Stage_0.v.Port.MoleFlow = 0.0

Efficiencies = 0.9
V_MoleFraction.PROPANE



Efficiencies = 0.5
V_MoleFraction.PROPANE

Efficiencies = :0 .3 1 .5 2 .7 3-19 .5 20-21 .8
V_MoleFraction.PROPANE

#Per compound
Efficiencies = :-2 .32 4 .18 8 .91 @PROPANE 0 .2 1 .4 2 .6 3-7 .7 @n-BUTANE 1 .3 4-5 .8 6- .4 @CARBON_DIOXIDE -3 .2 4 .6
V_MoleFraction.PROPANE

#Switching compounds should not affect
$thermo.PROPANE >> n-PENTANE
Efficiencies = :-2 .32 4 .18 8 .91 @PROPANE 0 .2 1 .4 2 .6 3-7 .7 @n-BUTANE 1 .3 4-5 .8 6- .4 @CARBON_DIOXIDE -3 .2 4 .6
V_MoleFraction.PROPANE

#Get rid of the generic efficiencies
Efficiencies = :@PROPANE 0 .2 1 .4 2 .6 3-7 .7 17 .9 18 .9 @n-BUTANE 1 .3 4-5 .8 6- .4 @CARBON_DIOXIDE -3 .2 4 .6
V_MoleFraction.PROPANE

#Delete a compound
$thermo - ISOBUTANE
V_MoleFraction.PROPANE

#Now play with removing and adding stages
Efficiencies = 1.0
/col.Stage_10 - 2
Efficiencies

Efficiencies = :0 .9 1 .8 2 .9 3 .87 4 .98 5 .76 6 .9 7-14 .93 15- 1.0
/col.Stage_13 - 2
Efficiencies

/col.Stage_3 - 2
Efficiencies

#/col.Stage_3 + 2
#Efficiencies 


Efficiencies = :-2 .32 4 .18 8 .91 @PROPANE 0 .2 1 .4 2 .6 3-7 .7 @n-BUTANE 1 .3 4-5 .8 6- .4 @CARBON_DIOXIDE -3 .2 4 .6
/col.Stage_4 - 2
Efficiencies

/col.Stage_0 - 2
Efficiencies


#Now lets play with the P_Profile object
Efficiencies = 1.0
TryToSolve = 0

/col.P_Profile.Values

/col.LiquidDraw_0_l.P = 
/col.P_Profile.Values

/col.P_Profile.Item0 = 700
/col.LiquidDraw_0_l.P
/col.P_Profile.Values

TryToSolve = 1
/col.LiquidDraw_0_l.P
/col.P_Profile.Values

TryToSolve = 0
/col.P_Profile.Item4 = 701
TryToSolve = 1
/col.LiquidDraw_0_l.P
/col.P_Profile.Values

/col.P_Profile.Item0 = 
cd /col.Stage_2
. + 2
cd /col
/col.LiquidDraw_0_l.P
/col.P_Profile.Values

/col.LiquidDraw_13_l.P = 
/col.P_Profile.Item6 = 
/col.LiquidDraw_0_l.P
/col.LiquidDraw_13_l.P
/col.P_Profile.Values

TryToSolve = 0
/col.P_Profile.Item0 = 700
/col.P_Profile.Item13 = 720
TryToSolve = 1
/col.LiquidDraw_0_l.P
/col.LiquidDraw_13_l.P
/col.P_Profile.Values


#Degrees of subcooling
/col.Stage_0.dsc = Tower.DegSubCooling()
/col.Stage_0.l.Port
/col.Stage_0.dsc.Port = 3
/col.Stage_0.l.Port
/col.Stage_0.v = Tower.VapourDraw()
/col.Stage_0.v.MoleFlow = 0.0
/col.Stage_0.v.Port
/col.Stage_0.dsc.Port = 0
/col.Stage_0.v.Port
/col.Stage_0.l.Port
/col.Stage_0.dsc.Port = 2
/col.Stage_0.v.Port
/col.Stage_0.l.Port

copy /col
paste /

/col.LiquidDraw_0_l
/colClone.LiquidDraw_0_l


delete /col.Stage_0.dsc
/col.Stage_0.v.Port
/col.Stage_0.l.Port




