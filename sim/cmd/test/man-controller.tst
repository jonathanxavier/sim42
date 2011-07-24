units SI
$thermo = VirtualMaterials.SRK
/ -> $thermo
thermo + Methane Ethane Propane n-Butane n-Pentane n-Hexane n-Heptane n-Octane n-Nonane n-Decane

S1 = Stream.Stream_Material()
S1.In.T = 25
S1.In.P = 200
S1.In.MoleFlow = 1000
S1.In.Fraction = 100 10 7 5 4 3 2 1 1 1
S1.In

Sep = Flash.SimpleFlash()

S2 = Stream.Stream_Material()
S3 = Stream.Stream_Material()

S1.Out -> Sep.In
Sep.Vap -> S2.In
Sep.Liq0 -> S3.In

S1.In
S2.In
S3.In

S3.FlowSig = Stream.SensorPort("MoleFlow")

S1.TempSig = Stream.SensorPort("T")

S3.FlowSig
S1.TempSig

ctr = Controller.Controller()
ctr.In -> S3.FlowSig

# before connecting the Outlet, we should get rid of the value downstream of the controlled
# port.  The controller changes the fixed values in this port and everything else must be
# calculated from it or an inconsistancy will occur
S1.In.T = None

ctr.Out -> S1.TempSig
ctr.Out = 25
# note that you could not have assigned ctr.Out until the connection was made as the type of
# signal was not known

ctr.Target = 300
ctr.StepSize = 30

ctr.In
ctr.Out

copy /
paste /

cd /RootClone
ctr.In
ctr.Out