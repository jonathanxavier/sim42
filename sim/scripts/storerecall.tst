units = Field

$thermo = VirtualMaterials.RK
/ -> $thermo
thermo + METHANE ETHANE PROPANE n-HEXANE

s = Stream.Stream_Material()
h = Heater.Heater()

s.Out -> h.In

cd /s.In
T = 10 C
P = 101.325 kPa
MoleFlow = 1.0
Fraction = 1.0 1.0 1.0 1.0

cd /

h.DeltaP = 1.0
h.Out.T = 50 C

h.In
h.Out

#lets create a directoy right here with a space in its name
mkdir test directory


#normal store
store test directory\storerecall.s42
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out

#normal recall
recall test directory\storerecall.s42
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out

#compressed store
#Needs quotes in name of file as there are more than one parameter
store "test directory\storerecall zip.s42" "z"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out


#compressed recall
#Doesnt really need quotes. 
#No need to specify that it is a zip file
recall "test directory\storerecall zip.s42"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out



#compressed store with "n' flag. (Useless I think)
store "test directory\storerecall zipn.s42" "n"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out

#compressed recall with "n' flag
recall "test directory\storerecall zipn.s42"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out


#compressed store with extra files and "z' flag
store "test directory\storerecall zipwfiles.s42" "storerecalldummy1.txt" "storerecall dir" "storerecalldummy2.txt" "z"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out

#compressed recall with extra files and put the extra files into a new directory
recall "test directory\storerecall zipwfiles.s42" "storerecall temp dir"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out

#compressed recall with extra files and let the files be put back into the same place
recall "test directory\storerecall zipwfiles.s42"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out


#compressed store with extra files and "n' flag
store "test directory\storerecall zipnwfiles.s42" "storerecalldummy1.txt" "storerecalldummy2.txt" "n"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out

#compressed recall with extra files and put the extra files into a new directory
recall "test directory\storerecall zipnwfiles.s42" "storerecall temp dir"
s.In.T = 11 C
s.In.T = 10 C
h.In
h.Out



#Could delete files from cli but lets leave them for manually looking at sizes








