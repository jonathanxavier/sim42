# Simple set test
units SI
$thermo = VirtualMaterials.Peng-Robinson
/ -> $thermo
thermo + PROPANE n-BUTANE ISOBUTANE n-PENTANE

h1 = Heater.Heater()
h1.DeltaP.DP = 10
h2 = Heater.Heater()
set = Set.Set()
set.SignalType = DP  # must be set before addition
set.multiplier = 2.
set.addition = 0.
h1.DeltaP -> set.Signal0
sig = Stream.Stream_Signal()
sig.In -> set.Signal1
sig.Out -> h2.DeltaP

h2.DeltaP
set.addition = None
h2.DeltaP

h2.DeltaP = 30
set.addition

set.multiplier = None
set.addition = 5

set.multiplier

sig.clonePort = Stream.ClonePort()
sig.clonePort


