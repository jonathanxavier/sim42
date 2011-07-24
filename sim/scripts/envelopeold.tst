units SI
# test 2-phase VL envelope
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + methane propane n-hexane water
env = Envelope.PTEnvelope()
env.In.Fraction = 0.15 0.15 0.2 0.5
# I need temperatures at these pressure values
env.Pressures = 101.325 202.65 303.975 405.3 506.625 kPa
# add a bubble/dew point curve
env.bubble = Envelope.QualityCurve(0.0)
# add a quality curve
env.q4 = Envelope.QualityCurve(0.4)
# examine results
env
env.bubble.Results
env.q4.Results
# test deleting curve
delete env.q4
env
# examine the critical point
env.Crit_T
env.Crit_P

copy /env
paste /
/envClone.Crit_T
/envClone.Crit_P
/envClone.bubble.Results