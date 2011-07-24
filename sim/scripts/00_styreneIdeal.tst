units VMG
$thermo = VirtualMaterials.IdealLiquid/Ideal/HC
/ -> $thermo
/LiquidPhases = 2 
/thermo + TOLUENE ETHYLBENZENE STYRENE MESITYLENE alpha-METHYLSTYRENE n-PROPYLBENZENE 
 
#Feed 
S1 = Stream.Stream_Material() 
/S1.In.T = 317.75 K 
/S1.In.P = 220 mmHg 
/S1.In.Fraction = 0.80 51.00 47.77 0.06 0.13 0.20 
/S1.In.MoleFlow = 99.96 kgmole/h 
 
#Tower 1 
T1 = Tower.DistillationColumn() 
/T1.TryToSolve = 0 
/S1.Out -> /T1.Feed_1_feed 
/T1.Stage_0 + 49 
/T1.Stage_50.feed.ParentStage = 9 
 
#Total cond and P prof 
delete /T1.Stage_0.condenserV 
/T1.LiquidDraw_0_condenserL.P = 40 mmHg 
/T1.LiquidDraw_51_reboilerL.P = 270 mmHg 
 
#More specs and solve 
/T1.LiquidDraw_0_condenserL.MoleFlow = 52 kgmole/h 
/T1.Variable_0_Reflux.Generic = 2.5 
/T1.TryToRestart = 0 
/T1.TryToSolve = 1 
/T1.TryToRestart = 1 
/T1.TryToSolve = 0 
 
#Add liquid draw and solve 
/T1.Stage_20.L = Tower.LiquidDraw() 
/T1.LiquidDraw_20_L.MoleFlow = 11 kgmole/h 
/T1.TryToRestart = 1 /T1.TryToSolve = 1 
 
#Energy, distillate, draw and bottoms streams for T1 
S2 = Stream.Stream_Material() 
/T1.LiquidDraw_0_condenserL -> /S2.In 
S3 = Stream.Stream_Material() 
/T1.LiquidDraw_20_L -> /S3.In 
S4 = Stream.Stream_Material() 
/T1.LiquidDraw_51_reboilerL -> /S4.In 
Q1 = Stream.Stream_Energy() 
/T1.EnergyFeed_0_condenserQ -> /Q1.In 
Q2 = Stream.Stream_Energy() 
/Q2.Out -> /T1.EnergyFeed_51_reboilerQ 
 
#Tower2 
T2 = Tower.DistillationColumn() 
/T2.TryToSolve = 0 
/S4.Out -> /T2.Feed_1_feed 
/T2.Stage_0 + 49 
/T2.Stage_50.feed.ParentStage = 30 
 
#Total cond and P prof 
delete /T2.Stage_0.condenserV 
/T2.LiquidDraw_0_condenserL.P = 40 mmHg 
/T2.LiquidDraw_51_reboilerL.P = 250 mmHg 
 
#more specs and solve 
/T2.LiquidDraw_0_condenserL.MoleFlow = 16 kgmole/h 
/T2.Variable_0_Reflux.Generic = 2.5 
/T2.TryToRestart = 0 
/T2.TryToSolve = 1 
/T2.TryToRestart = 1 
/T2.TryToSolve = 0 
 
#Add liquid draw and solve 
/T2.Stage_20.L = Tower.LiquidDraw() 
/T2.LiquidDraw_20_L.MoleFlow = 7 kgmole/h 
/T2.TryToRestart = 0 
/T2.TryToSolve = 1 
/T2.TryToRestart = 1 
/T2.TryToSolve = 0 
 
#Energy, distillate, draw and bottoms streams for T2 
S5 = Stream.Stream_Material() 
/T2.LiquidDraw_0_condenserL -> /S5.In 
S6 = Stream.Stream_Material() 
/T2.LiquidDraw_20_L -> /S6.In 
S7 = Stream.Stream_Material() 
/T2.LiquidDraw_51_reboilerL -> /S7.In 
Q3 = Stream.Stream_Energy() 
/Q3.Out -> /T2.EnergyFeed_51_reboilerQ 
Q4 = Stream.Stream_Energy() 
/T2.EnergyFeed_0_condenserQ -> /Q4.In 
 
#Connect recycle and spec estimates 
/T2.LiquidDraw_0_condenserL -> 
/T1.Stage_44.feed = Tower.Feed() 
/T1.Feed_44_feed -> /S5.Out 
/S5.In.T ~= 350 K 
/S5.In.P ~= 26.6644 
/S5.In.MoleFlow ~= 0 
/S5.In.Fraction ~= 1 0 0 0 0 0 
/T2.LiquidDraw_0_condenserL -> /S5.In 
 
#Final solve 
/T1.TryToRestart = 1 
/T1.TryToSolve = 1 
/T2.TryToRestart = 1 
/T2.TryToSolve = 1
