# Simple distilation column test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

col = Tower.Tower()
col.Stage_0 + 20  # twenty two stages`

/col.MaxOuterLoops = 50
/col.Damping = 0.9
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
l.Port.P = 720
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


cd /

#Create streams
s_feed = Stream.Stream_Material()
s_liqdraw_0 = Stream.Stream_Material()
s_liqdraw_21 = Stream.Stream_Material()
s_vapdraw_0 = Stream.Stream_Material()
ene_cond = Stream.Stream_Energy()
ene_reb = Stream.Stream_Energy()
s_intvap_1 = Stream.Stream_Material()
s_intliq_0 = Stream.Stream_Material()



#Create clones in streams
cd /s_feed
clone = Stream.ClonePort(0)
cd /s_liqdraw_0
clone = Stream.ClonePort()
cd /s_liqdraw_21
clone = Stream.ClonePort()
cd /s_vapdraw_0
clone = Stream.ClonePort()
cd /ene_cond
clone = Stream.ClonePort()
cd clone
cd /ene_reb
clone = Stream.ClonePort(0)
cd /s_intvap_1
clone = Stream.ClonePort(0)
cd /s_intliq_0
clone = Stream.ClonePort()
cd /s_liqdraw_0
clone2 = Stream.ClonePort()
cd /ene_cond
clone2 = Stream.ClonePort()

#Create clones in tower
cd /col.Stage_1
vaporclone = Tower.InternalVapourClone()
cd /col.Stage_0
liquidclone = Tower.InternalLiquidClone()



#Create a balance for the overall tower
cd /
bal = Balance.BalanceOp()
cd bal
NumberStreamsInMat = 1
NumberStreamsOutMat = 2
NumberStreamsInEne = 1
NumberStreamsOutEne = 2
BalanceType = 4


#Create a balance for the top stage
cd /
stagebalance = Balance.BalanceOp()
cd stagebalance
BalanceType = 4
NumberStreamsInMat = 1
NumberStreamsOutMat = 2
NumberStreamsOutEne = 2



#Connect the streams to the tower and the clones to the balance
/s_feed.Out -> /col.Feed_10_f
/s_liqdraw_0.In -> /col.LiquidDraw_0_l
/s_liqdraw_21.In -> /col.LiquidDraw_21_l
/ene_cond.In -> /col.EnergyFeed_0_cond
/ene_reb.Out -> /col.EnergyFeed_21_reb

/bal.In0 -> /s_feed.clone
/bal.Out0 -> /s_liqdraw_0.clone
/bal.Out1 -> /s_liqdraw_21.clone
/bal.InQ0 -> /ene_reb.clone
/bal.OutQ0 -> /ene_cond.clone

/stagebalance.In0 -> /s_intvap_1.clone
/stagebalance.Out0 -> /s_intliq_0.clone
/stagebalance.Out1 -> /s_liqdraw_0.clone2
/stagebalance.OutQ0 -> /ene_cond.clone2

/s_intliq_0.In -> /col.InternalLiquid_0_liquidclone
/s_intvap_1.In -> /col.InternalVapour_1_vaporclone



cd /col
MaxOuterError = 1e-6
MaxInnerError = 1e-6
TryToRestart = 1
/col.LiquidDraw_0_l


#Add degrees of subcooling
cd /col.Stage_0
degsubcool = Tower.DegSubCooling()


/col.DegSubCool_0_degsubcool.DT = 2
/col.LiquidDraw_0_l
/bal.OutQ1
/stagebalance.OutQ1


/col.DegSubCool_0_degsubcool.DT = 4
/col.LiquidDraw_0_l
/bal.OutQ1
/stagebalance.OutQ1

/col.DegSubCool_0_degsubcool.DT = 0
/col.LiquidDraw_0_l
/bal.OutQ1
/stagebalance.OutQ1


/col.DegSubCool_0_degsubcool.DT = 
/col.LiquidDraw_0_l.T = 18
/col.DegSubCool_0_degsubcool
/bal.OutQ1
/stagebalance.OutQ1


/col.LiquidDraw_0_l.MoleFlow = 
/col.DegSubCool_0_degsubcool.DT = 2
/col.DegSubCool_0_degsubcool
/col.LiquidDraw_0_l
/bal.OutQ1
/stagebalance.OutQ1


#Now add a vapour draw and make sure it doesnt break anything
/col.TryToSolve = 0
/col.TryToRestart = 0
cd /col.Stage_0
vap = Tower.VapourDraw()
cd /

#Should solve fine even for vap flow > 0.0
/col.DegSubCool_0_degsubcool.DT = 0
/col.TryToSolve = 1
/col.VapourDraw_0_vap.MoleFlow = 1
/bal.OutQ1
/stagebalance.OutQ1


#Solve with an inconcistency
/col.LiquidDraw_0_l.T = 
/col.LiquidDraw_0_l.MoleFlow = 5
/col.DegSubCool_0_degsubcool.DT = 1
/bal.OutQ1
/stagebalance.OutQ1

#Solve fine again
/col.DegSubCool_0_degsubcool.DT = 0


#Should attempt to solve for vapour draw even if TryToSolve = 0
/col.DegSubCool_0_degsubcool.DT =
/col.TryToSolve = 0
/col.DegSubCool_0_degsubcool.DT = 1
/col.VapourDraw_0_vap.MoleFlow =
/col.VapourDraw_0_vap.MoleFlow
/col.TryToSolve = 1


#Solve fine. A DegSubcooling > 0.0 puts a zero lfow in the vap flow
/col.VapourDraw_0_vap.MoleFlow = 
/bal.OutQ1
/stagebalance.OutQ1


# Can not solve because the liquid is subcooled and the vap is > 0.0
/col.DegSubCool_0_degsubcool.DT = 
/col.LiquidDraw_0_l.T = 18 C
/col.VapourDraw_0_vap.MoleFlow = 1
/bal.OutQ1
/stagebalance.OutQ1


#Solve fine
/col.VapourDraw_0_vap.MoleFlow = 0
/bal.OutQ1
/stagebalance.OutQ1



#Get rid of the vapour draw wich should not have been there at all to begin with
delete /col.Stage_0.vap
/bal.OutQ1
/stagebalance.OutQ1

copy /
paste /









