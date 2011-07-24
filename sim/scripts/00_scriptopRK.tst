units SI
$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + Methane Ethane Propane

Feed = Stream.Stream_Material()
Feed.In.T = 20
Feed.In.P = 3000
Feed.In.MoleFlow = 100
Feed.In.Fraction = 70 20 10


valve = Flowsheet.SubFlowsheet('read cv_valve.sop')
Feed.Out -> valve.In
Outlet = Stream.Stream_Material()
valve.Out -> Outlet.In
valve.Cv = 0.05

Outlet.Out
Feed.In.MoleFlow = 200
Outlet.Out

hx = Heater.HeatExchanger('read heatexdp.sop')

hx.InC -> Outlet.Out
hx.InC.P
hx.OutC.P
hx.CvC = .01
hx.OutC.P
hx.CvC = None
hx.OutC.P = 800
hx.CvC

