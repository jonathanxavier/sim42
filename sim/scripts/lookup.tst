# Test lookup table

lkp = Pump.LookupTable()

# setup table
lkp.NumberSeries = 3
lkp.NumberTables = 1
lkp.TableType = P
lkp.SpecTagValue = 100.0		# specified table tag value
lkp.Extrapolate0 = 0		# do not extrapolate series 0

lkp.SeriesType0 = P
lkp.SeriesType1 = T
lkp.SeriesType2 = H

lkp.Table0.TagValue = 32.0	# tag value for the input table 0
lkp.Table0.Series0 =  1.0 2.0 3.0 4.0  5.0  6.0  7.0
lkp.Table0.Series1 =  2.0 4.0 6.0 8.0 10.0 12.0 14.0 
lkp.Table0.Series2 = 10.0 9.5 9.0 8.5  8.0  7.5  7.0

lkp

# interpolate the table
# expecting: 5.75, 11.5, 7.625
lkp.Signal1 = 11.5
lkp.Signal0
lkp.Signal1
lkp.Signal2

# extrapolate down the table
# Expecting: 1.0, 0.0, 10.5
lkp.Signal1 = 0.0
lkp.Signal0
lkp.Signal1
lkp.Signal2

# extrapolate up the table
# expecting: 7.0, 16.0, 6.5
lkp.Signal1 = 16.0
lkp.Signal0
lkp.Signal1
lkp.Signal2

# try specifying Signal0 instead of Signal1
# expecting 1.5, 3.0, 9.75
lkp.Signal1 = None
lkp.Signal0 = 1.5
lkp.Signal0
lkp.Signal1
lkp.Signal2

# multiple entry, input both Signal0 and Signal1
# expecting 1.5, (4.0 vs 3.0), 9.75 with inconsistency for signal1
lkp.Signal1 = 4.0
lkp.Signal0
lkp.Signal1
lkp.Signal2
