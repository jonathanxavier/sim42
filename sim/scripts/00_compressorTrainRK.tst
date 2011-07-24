
$thermo = VirtualMaterials.RK
/ -> $thermo
/thermo + NITROGEN CARBON_DIOXIDE METHANE ETHANE  PROPANE
/thermo + ISOBUTANE  n-BUTANE  ISOPENTANE n-PENTANE n-HEXANE
/thermo.BP120* = HypoCompound """
MolecularWeight = 120.00
NormalBoilingPoint = 408.2
LiquidDensity@298 = 756.2597
"""
/thermo.BP260* = HypoCompound """
MolecularWeight = 200.00
NormalBoilingPoint = 533.2
LiquidDensity@298 = 835.1824
"""
/thermo.BP500* = HypoCompound """
MolecularWeight = 500.00
NormalBoilingPoint = 773.2
LiquidDensity@298 = 949.0709
"""

S1 = Stream.Stream_Material()
/S1.NewName = Inlet_Gas
units SI
'/Inlet_Gas.In.T' = 45
'/Inlet_Gas.In.P' = 450
'/Inlet_Gas.In.Fraction' =  2.55740021193924E-03 2.71282232426704E-02 0.205086541858001 0.128180854821618 0.102578594136348 0.010879547862946 3.97032850582833E-02 0.013465206640763 2.30731190392088E-02 2.17873542917697E-02 0.169198163193218 0.128180854821618 0.128180854821618
'/Inlet_Gas.In.MassFlow' = None
'/Inlet_Gas.In.MoleFlow' = 70775

M1 = Mixer.Mixer("NumberStreamsIn = 2")
/Inlet_Gas.Out -> /M1.In0
'/M1.In1.T' ~= 25
'/M1.In1.P' ~= 1000
'/M1.In1.MoleFlow' ~= 0
'/M1.In1.Fraction' ~=  0 0 0 0 0 0 0 0 0 1 0 0 0
S1 = Stream.Stream_Material()
/M1.Out -> /S1.In
Sep1 = Flash.SimpleFlash("LiquidPhases = 1")
/S1.Out -> /Sep1.In
S2 = Stream.Stream_Material()
/Sep1.Vap -> /S2.In
S3 = Stream.Stream_Material()
/Sep1.Liq0 -> /S3.In
CP1 = Compressor.Compressor()
/S2.Out -> /CP1.In
'/CP1.Efficiency.Generic' = .78
S4 = Stream.Stream_Material()
/CP1.Out -> /S4.In
'/S4.In.P' = 1100
C1 = Heater.Cooler()
/S4.Out -> /C1.In
S5 = Stream.Stream_Material()
/C1.Out -> /S5.In
'/C1.DeltaP.DP' = 100
'/S5.In.T' = 60
'/S5.In.T' = 20
'/S5.In.T' = 60
M2 = Mixer.Mixer("NumberStreamsIn = 2")
/S5.Out -> /M2.In0
'/M2.In1.T' ~= 25
'/M2.In1.P' ~= 2600
'/M2.In1.MoleFlow' ~= 0
'/M2.In1.Fraction' ~=  0 0 0 0 0 0 0 0 0 1 0 0 0
S6 = Stream.Stream_Material()
/M2.Out -> /S6.In
Sep2 = Flash.SimpleFlash("LiquidPhases = 1")
/S6.Out -> /Sep2.In
S7 = Stream.Stream_Material()
/Sep2.Vap -> /S7.In
S8 = Stream.Stream_Material()
/Sep2.Liq0 -> /S8.In
CP2 = Compressor.Compressor()
/S7.Out -> /CP2.In
'/CP2.Efficiency.Generic' = .75
S9 = Stream.Stream_Material()
/CP2.Out -> /S9.In
'/S9.In.P' = 2600
C2 = Heater.Cooler()
/S9.Out -> /C2.In
S10 = Stream.Stream_Material()
/C2.Out -> /S10.In
'/C2.DeltaP.DP' = 100
'/S10.In.T' = 60
CP3 = Compressor.Compressor()
M3 = Mixer.Mixer("NumberStreamsIn = 2")
/S10.Out -> /M3.In0
'/M3.In1.T' ~= 25
'/M3.In1.P' ~= 6200
'/M3.In1.MoleFlow' ~= 0
'/M3.In1.Fraction' ~=  0 0 0 0 0 0 0 0 0 1 0 0 0
S11 = Stream.Stream_Material()
/M3.Out -> /S11.In
Sep3 = Flash.SimpleFlash("LiquidPhases = 1")
/S11.Out -> /Sep3.In
S12 = Stream.Stream_Material()
/Sep3.Vap -> /S12.In
S13 = Stream.Stream_Material()
/Sep3.Liq0 -> /S13.In
/S12.Out -> /CP3.In
S14 = Stream.Stream_Material()
/CP3.Out -> /S14.In
'/CP3.Efficiency.Generic' = .72
'/S14.In.P' = 6300
C3 = Heater.Cooler()
/S14.Out -> /C3.In
S15 = Stream.Stream_Material()
/C3.Out -> /S15.In
'/S15.In.T' = 60
'/C3.DeltaP.DP' = 100
Sep4 = Flash.SimpleFlash("LiquidPhases = 1")
/S15.Out -> /Sep4.In
S16 = Stream.Stream_Material()
/Sep4.Vap -> /S16.In
S17 = Stream.Stream_Material()
/Sep4.Liq0 -> /S17.In
/S16.NewName = Compressed_Gas
/S17.Out -> /M3.In1
/S13.Out -> /M2.In1
/S8.Out -> /M1.In1
/S3.NewName = Condensate

