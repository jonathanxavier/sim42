#Play with consistency errors


s = Stream.Stream_Material()
s2 = Stream.Stream_Material()
s3 = Stream.Stream_Material()

s.In.T = 11
s.In.P = 11
s.In.MoleFlow = 3

s2.In.T = 22
s2.In.P = 222

#Create a Consist error
s.Out -> s2.In
s.In.MoleFlow =
s.In.MoleFlow = 4

#Get rid of Consist error
s.Out ->

#Shouldn't make a difference the order of connections
s2.In -> s.Out
s.Out ->


#A solve will not be triggered in both sides, but the const error should still be passed on
s.In.MoleFlow =
s2.In -> s.Out

#Anythins should still pass the message of consist errors
cd /s
cd /


#This should clear the consist error message
s2.In -> 


#Put it back
s.Out -> s2.In

#Reconnect. Consist error message should go away
s.Out -> s3.In

#Put it back
s.Out -> s2.In

s3.Out.T = 33
s3.Out.P = 333


#Reconnect, but now a new consist error should get created
s.Out -> s3.In


#The consistency error messages should get stored too
store consisterrs.s42

#Clear and errors should go away
clear

#recall and errors should come back
recall consisterrs.s42
cd /
