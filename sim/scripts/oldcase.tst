# test ability to recall old cases
# oldcase_v1 is a gas plant created with an old version of VMGSim
# and is a file version 1 case
recall oldcase_v1.s42

#print a couple of product streams
units Field
/S6.Out
/T1.LiquidDraw_9_reboilerL

# change feed temperature - HX1 has temp cross
S1.In.T = 55
/S6.Out
/T1.LiquidDraw_9_reboilerL

# Fix temp cross
/Hx1.DeltaTHO = None
/Hx1.DeltaTHI = 5

/S6.Out
/T1.LiquidDraw_9_reboilerL

clear
# oldcase_v1 is the gasplant.tst case stored at file version 8
recall oldcase_v8.s42
/overhead.Out
/bottoms.Out
/Gas-Gas.OutC

# change feed temp
/Feed.In.T = 60
/overhead.Out
/bottoms.Out
/Gas-Gas.OutC

copy /
paste /

/RootClone.overhead.Out