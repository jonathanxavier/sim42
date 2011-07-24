units PureSI

$th = VirtualMaterials.Peng-Robinson
/ -> $th
th + WATER

ejector = Ejector.EjectorOp()


cd /ejector.Process
P = 20270.58558 Pa
T = 333.3333336 K
Fraction = 1.0
MoleFlow = 4.5359244127 kgmole/h

cd /ejector.Motive
P = 689475.7 Pa
T = 333.3333336 K
Fraction = 1.0
MoleFlow = 45.359244127 kgmole/h

cd /ejector.Discharge
#P = 81107.4142866 Pa
#T = 333.3333354 K
#Fraction = 1.0
#MoleFlow = 49.8951685397 kgmole/h

cd /
ejector.NozzleDiameter = 0.48639
ejector.ThroatDiameter = 1.613175


ejector.Process
ejector.Motive
ejector.Discharge
ejector.NozzleDiameter
ejector.ThroatDiameter

ejector.NozzleDiameter = None
ejector.Discharge.P = 81107.2733997
ejector.Process
ejector.Motive
ejector.Discharge
ejector.NozzleDiameter
ejector.ThroatDiameter

copy /ejector
paste /
ejectorClone.Process
ejectorClone.Motive
ejectorClone.Discharge
ejectorClone.NozzleDiameter
ejectorClone.ThroatDiameter