units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + propane isobutane n-butane isopentane n-pentane n-hexane

Feed = Stream.Stream_Material()
Feed.In.T = 20
Feed.In.P = 3000
Feed.In.MoleFlow = 100
Feed.In.Fraction = 1 2 3 4 5 6 


pump = Flowsheet.SubFlowsheet('read mechengpump.sop')
Feed.Out -> pump.In
pump.Out.P = 5000
pump.Efficiency = .75

pump.Out
pump.InQ

# try Efficiency / Q test
pump.Out.P = None
pump.InQ = 8000
pump.Out

# backwards
Feed.In.P = None
Feed.In.T = None
pump.Out.P = 5000
pump.Out.T = 20
Feed.In

# compare to isentropic pump
spump = Pump.Pump()
Feed.clone = Stream.ClonePort(0)
Feed.clone -> spump.In
spump.Out.P = 5000
spump.Efficiency = .75
spump.InQ

copy /
paste /