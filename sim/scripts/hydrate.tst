units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + NITROGEN WATER METHANE ETHANE PROPANE ISOBUTANE CARBON_DIOXIDE HYDROGEN_SULFIDE n-BUTANE

Feed = Stream.Stream_Material()
Out = Stream.Stream_Material()
Hydrate = Hydrate.Hydrate()

Feed.Out -> Hydrate.In
Hydrate.Out -> Out.In

Feed.In.T = 40
Feed.In.P = 2000 kPa
Feed.In.Fraction = 0.094 0.0 0.784 0.06 0.036 0.005 0.002 0.0 0.019
Feed.In.MoleFlow = 100


# Results
Feed.In
Out.Out
Hydrate.HydrateTemp

copy /Feed /Out /Hydrate
paste /
FeedClone.In
OutClone.Out
HydrateClone.HydrateTemp