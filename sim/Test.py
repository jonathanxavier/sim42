import sys, os, cPickle
from sim.thermo import ThermoAdmin
from sim.unitop import Flash
from sim.unitop import Stream
from sim.solver import Flowsheet
from sim.unitop import Mixer
from sim.unitop import LiqLiqExt
from sim.unitop import Heater
from sim.unitop import Split
from sim.unitop import Balance
from sim.solver import Ports
from sim.solver.Variables import *
from sim.solver.Error import SimError
from sim.thermo.vmg import VMGerror

def TestSimpleFlash():
    print """
Init SimpleFlash ++++++++++++++++++++++++++++++"""
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    ##Load vals    
    flash = Flash.SimpleFlash() 
    flash.SetThermoAdmin(thAdmin)
    flash.SetThermo(thermo) 
    cmps = flash.GetCompoundNames()
    flash.SetParameterValue(NULIQPH_PAR, 1) #Should be NULIQPH_PAR
    print 'Cmps: ', cmps
    portsIn = flash.GetPortNames(MAT|IN)
    print 'Names Ports In: ', portsIn
    portsOut = flash.GetPortNames(MAT|OUT)
    print 'Names Ports Out: ', portsOut
    comps = [0.25, 0.25, 0.25, 0.25]
    flash.SetCompositionValues(portsIn[0], comps)
    flash.GetPort(portsIn[0]).SetPropValue(T_VAR, 273.15, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(P_VAR, 101.325, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)
    print 'Return value from Solve()', flash.Solve()
    print ''

    #Print some info in    
    for i in portsIn:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of port in "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port in "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''
        
        port = flash.GetPort(i)
        print 'Array properties available: ', port.GetArrPropNames()
        props = port.GetArrPropValue(LNFUG_VAR)     #LNFUG_VAR,
        print 'Array of ', LNFUG_VAR, ' of port in "', i, '":'
        if props:
            for j in range(len(props)): print 'ln fug of ', cmpNames[j], ': ', props[j]
        print ''
        
    #Print some info out
    for i in portsOut:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of port out "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port out "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''

        port = flash.GetPort(i)
        print 'Array properties available: ', port.GetArrPropNames()
        props = port.GetArrPropValue(LNFUG_VAR)     #LNFUG_VAR,
        print 'Array of ', LNFUG_VAR, ' of port out "', i, '":'        
        if props:
            for j in range(len(props)): print 'ln fug of ', cmpNames[j], ': ', props[j]
        print ''

    print """Finished SimpleFlash ++++++++++++++++++++++++++++++
    """

    flash.CleanUp()
    thAdmin.CleanUp()

def TestSimpleFlash2LPhase():
    print """
Init SimpleFlash2LPhase ++++++++++++++++++++++++++++++"""
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE", "WATER")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    ##Load vals    
    flash = Flash.SimpleFlash() 
    flash.SetThermoAdmin(thAdmin)
    flash.SetThermo(thermo)
    flash.SetParameterValue(NULIQPH_PAR, 2) #Should be NULIQPH_PAR
    cmps = flash.GetCompoundNames()
    print 'Cmps: ', cmps
    portsIn = flash.GetPortNames(MAT|IN)
    print 'Names Ports In: ', portsIn
    portsOut = flash.GetPortNames(MAT|OUT)
    print 'Names Ports Out: ', portsOut
    
    flash.SetCompositionValue(portsIn[0], "PROPANE", 0.20)
    flash.SetCompositionValue(portsIn[0], "n-BUTANE", 0.20)
    flash.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.20)
    flash.SetCompositionValue(portsIn[0], "n-PENTANE", 0.20)
    flash.SetCompositionValue(portsIn[0], "WATER", 0.20)
    flash.GetPort(portsIn[0]).SetPropValue(T_VAR, 273.15, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(P_VAR, 101.325, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)
    print 'Return value from Solve()', flash.Solve()
    print ''

    #Print some info in    
    for i in portsIn:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of port in "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port in "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''  

    #Print some info out
    for i in portsOut:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of port out "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port out "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''        

    print """Finished SimpleFlash2LPhase ++++++++++++++++++++++++++++++
    """

    flash.CleanUp()
    thAdmin.CleanUp()
    
def TestMixAndFlash():
    print """
Init MixAndFlash ++++++++++++++++++++++++++++++"""
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    flowsheet = Flowsheet.Flowsheet()
    flowsheet.SetThermoAdmin(thAdmin)
    flowsheet.SetThermo(thermo) 
    
    ##Load vals    
    flash = Flash.MixAndFlash()
    flowsheet.AddUnitOperation(flash, 'Flash')
    cmps = flash.GetCompoundNames()
    print 'Cmps: ', cmps
    portsIn = flash.GetPortNames(MAT|IN)
    print 'Names Ports In: ', portsIn
    portsOut = flash.GetPortNames(MAT|OUT)
    print 'Names Ports Out: ', portsOut
    flash.SetParameterValue(NULIQPH_PAR, 1)
    flash.SetParameterValue(NUSTIN_PAR, 2)
    flash.SetCompositionValue(portsIn[0], "PROPANE", 0.5)
    flash.SetCompositionValue(portsIn[0], "n-BUTANE", 0.5)
    flash.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.0)
    flash.SetCompositionValue(portsIn[0], "n-PENTANE", 0.0)
    flash.GetPort(portsIn[0]).SetPropValue(T_VAR, 460.15, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(P_VAR, 700.325, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)

    flash.SetCompositionValue(portsIn[1], "PROPANE", 0.0)
    flash.SetCompositionValue(portsIn[1], "n-BUTANE", 0.0)
    flash.SetCompositionValue(portsIn[1], "ISOBUTANE", 0.5)
    flash.SetCompositionValue(portsIn[1], "n-PENTANE", 0.5)
    flash.GetPort(portsIn[1]).SetPropValue(T_VAR, 200.15, FIXED_V)
    flash.GetPort(portsIn[1]).SetPropValue(P_VAR, 700.325, FIXED_V)
    flash.GetPort(portsIn[1]).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)

    print 'Return value from Solve()', flowsheet.Solve()
    print ''

    #Print some info in    
    for i in portsIn:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of port in "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port in "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''  

    #Print some info out
    for i in portsOut:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of port out "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port out "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''        

    print """Finished MixAndFlash ++++++++++++++++++++++++++++++
    """

    flash.CleanUp()
    thAdmin.CleanUp()

def TestLiqLiqEx():
    print """
Init LiqLiqEx ++++++++++++++++++++++++++++++"""
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("n-HEPTANE", "BENZENE", "TRIETHYLENE GLYCOL")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    ##Load vals    
    lle = LiqLiqExt.LiqLiqEx() 
    lle.SetThermoAdmin(thAdmin)
    lle.SetThermo(thermo) 
    cmps = lle.GetCompoundNames()
    print 'Cmps: ', cmps
    portsIn = lle.GetPortNames(MAT|IN)
    print 'Names Ports In: ', portsIn
    portsOut = lle.GetPortNames(MAT|OUT)
    print 'Names Ports Out: ', portsOut
    lle.SetParameterValue(LIQ_MOV, "BENZENE")
## Next line has a bug... so don't change the default    
    #lle.SetParameterValue(NUSTAGES_PAR, 10)
    
    lle.SetCompositionValue(FEED_PORT, "n-HEPTANE", 0.5)
    lle.SetCompositionValue(FEED_PORT, "BENZENE", 0.5)
    lle.SetCompositionValue(FEED_PORT, "TRIETHYLENE GLYCOL", 0.0)
    lle.GetPort(FEED_PORT).SetPropValue(T_VAR, 273.15, FIXED_V)
    lle.GetPort(FEED_PORT).SetPropValue(P_VAR, 101.325, FIXED_V)
    lle.GetPort(FEED_PORT).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)

    lle.SetCompositionValue(SOLV_PORT, "n-HEPTANE", 0.0)
    lle.SetCompositionValue(SOLV_PORT, "BENZENE", 0.0)
    lle.SetCompositionValue(SOLV_PORT, "TRIETHYLENE GLYCOL", 1.0)
    lle.GetPort(SOLV_PORT).SetPropValue(T_VAR, 273.15, FIXED_V)
    lle.GetPort(SOLV_PORT).SetPropValue(P_VAR, 101.325, FIXED_V)
    lle.GetPort(SOLV_PORT).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)

    print 'Return value from Solve()', lle.Solve()
    print ''

    #Print some info in    
    for i in portsIn:
        comp = lle.GetCompositionValues(i)        
        print 'Composition of port in "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port in "', i, '":'
        print T_VAR, ': ', lle.GetPropValue(i, T_VAR)
        print H_VAR, ': ', lle.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', lle.GetPropValue(i, MOLEFLOW_VAR)
        print ''  

    #Print some info out
    for i in portsOut:
        comp = lle.GetCompositionValues(i)        
        print 'Composition of port out "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port out "', i, '":'
        print T_VAR, ': ', lle.GetPropValue(i, T_VAR)
        print H_VAR, ': ', lle.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', lle.GetPropValue(i, MOLEFLOW_VAR)
        print ''

    print """Finished LiqLiqEx ++++++++++++++++++++++++++++++
    """

    lle.CleanUp()
    thAdmin.CleanUp()

def TestHeater():
    print """
Init Heater ++++++++++++++++++++++++++++++"""
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    ##Load vals    
    heater = Heater.Heater() 
    heater.SetThermoAdmin(thAdmin)
    heater.SetThermo(thermo) 
    cmps = heater.GetCompoundNames()
    print 'Cmps: ', cmps
    portsIn = heater.GetPortNames(MAT|IN)
    print 'Names Ports In: ', portsIn
    portsOut = heater.GetPortNames(MAT|OUT)
    print 'Names Ports Out: ', portsOut
    heater.SetParameterValue(NULIQPH_PAR, 1)    
    heater.SetCompositionValue(portsIn[0], "PROPANE", 0.25)
    heater.SetCompositionValue(portsIn[0], "n-BUTANE", 0.25)
    heater.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.25)
    heater.SetCompositionValue(portsIn[0], "n-PENTANE", 0.25)
    heater.GetPort(portsIn[0]).SetPropValue(H_VAR, -7200, FIXED_V)
    heater.GetPort(portsIn[0]).SetPropValue(P_VAR, 101.325, FIXED_V)
    heater.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)

    heater.GetPort(IN_PORT + 'Q').SetPropValue(ENERGY_VAR, 1000000.0, FIXED_V)
    heater.GetPort(DELTAP_PORT).SetValue(0.0, FIXED_V)
    
    print 'Return value from Solve()', heater.Solve()
    print ''

    #Print some info in    
    for i in portsIn:
        comp = heater.GetCompositionValues(i)        
        print 'Composition of port in "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port in "', i, '":'
        print T_VAR, ': ', heater.GetPropValue(i, T_VAR)
        print P_VAR, ': ', heater.GetPropValue(i, P_VAR)
        print H_VAR, ': ', heater.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', heater.GetPropValue(i, MOLEFLOW_VAR)
        print ''  

    #Print some info out
    for i in portsOut:
        comp = heater.GetCompositionValues(i)        
        print 'Composition of port out "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of port out "', i, '":'
        print T_VAR, ': ', heater.GetPropValue(i, T_VAR)
        print P_VAR, ': ', heater.GetPropValue(i, P_VAR)
        print H_VAR, ': ', heater.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', heater.GetPropValue(i, MOLEFLOW_VAR)
        print ''        

    print """Finished Heater ++++++++++++++++++++++++++++++
    """

    heater.CleanUp()
    thAdmin.CleanUp()

def TestHeatEx():
    print """
Init Heat Exchanger ++++++++++++++++++++++++++++++"""
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    # parent flowsheet
    flowsheet = Flowsheet.Flowsheet()
    flowsheet.SetThermoAdmin(thAdmin)
    flowsheet.SetThermo(thermo)
    
    hotInlet = Stream.Stream_Material()
    flowsheet.AddUnitOperation(hotInlet, 'HotIn')
    
    coldInlet = Stream.Stream_Material()
    flowsheet.AddUnitOperation(coldInlet, 'ColdIn')
    
    hotOutlet = Stream.Stream_Material()
    flowsheet.AddUnitOperation(hotOutlet, 'HotOut')
    
    coldOutlet = Stream.Stream_Material()
    flowsheet.AddUnitOperation(coldOutlet, 'ColdOut')
    
    hotInPort = hotInlet.GetPort(IN_PORT)
    hotInPort.SetCompositionValue("PROPANE", 0.25, FIXED_V)
    hotInPort.SetCompositionValue("n-BUTANE", 0.25, FIXED_V)
    hotInPort.SetCompositionValue("ISOBUTANE", 0.25, FIXED_V)
    hotInPort.SetCompositionValue("n-PENTANE", 0.25, FIXED_V)
    hotInPort.SetPropValue(T_VAR, 375.0, FIXED_V)
    hotInPort.SetPropValue(P_VAR, 500.0, FIXED_V)
    hotInPort.SetPropValue(MOLEFLOW_VAR, 800.0, FIXED_V)
    
    coldInPort = coldInlet.GetPort(IN_PORT)
    coldInPort.SetCompositionValue("PROPANE", 0.95, FIXED_V)
    coldInPort.SetCompositionValue("n-BUTANE", 0.05, FIXED_V)
    coldInPort.SetCompositionValue("ISOBUTANE", 0.0, FIXED_V)
    coldInPort.SetCompositionValue("n-PENTANE", 0.0, FIXED_V)
    coldInPort.SetPropValue(VPFRAC_VAR, 0.0, FIXED_V)
    coldInPort.SetPropValue(P_VAR, 300.0, FIXED_V)
    coldInPort.SetPropValue(MOLEFLOW_VAR, 1000.0, FIXED_V)
    
    exch = Heater.HeatExchanger()
    flowsheet.AddUnitOperation(exch, 'Exchanger')
    exch.GetPort(DELTAP_PORT + 'H').SetValue(50.0, FIXED_V)
    exch.GetPort(DELTAP_PORT + 'C').SetValue(10.0, FIXED_V)
    exch.GetPort(DELTAT_PORT + 'HO').SetValue(5.0, FIXED_V)
    exch.SetParameterValue(Heater.COUNTER_CURRENT_PAR, 1)
    
    flowsheet.ConnectPorts('HotIn',OUT_PORT,'Exchanger',IN_PORT + 'H')
    flowsheet.ConnectPorts('ColdIn',OUT_PORT,'Exchanger',IN_PORT + 'C')
    flowsheet.ConnectPorts('Exchanger',OUT_PORT + 'H','HotOut',IN_PORT)
    flowsheet.ConnectPorts('Exchanger',OUT_PORT + 'C','ColdOut',IN_PORT)
    
    flowsheet.Solve()

    for s in (hotInlet, hotOutlet, coldInlet, coldOutlet):
        port = s.GetPort(OUT_PORT)
        comp = port.GetCompositionValues()
        print 'Stream', s.GetPath()
        print T_VAR, ': ', port.GetPropValue(T_VAR)
        print P_VAR, ': ', port.GetPropValue(P_VAR)
        print H_VAR, ': ', port.GetPropValue(H_VAR)
        print MOLEFLOW_VAR, ': ', port.GetPropValue(MOLEFLOW_VAR)
        print ''  

        print 'Composition'
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

    print """Finished Heat Exchanger ++++++++++++++++++++++++++++++
    """

    flowsheet.CleanUp()
    thAdmin.CleanUp()
    

def TestFlowsh1():
    print """
Init Flowsh1 ++++++++++++++++++++++++++++++"""    
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    #Create unit Operations
    stream = Stream.Stream_Material()
    stream2 = Stream.Stream_Material()
    mixer = Mixer.Mixer()
    flash = Flash.SimpleFlash()
    
    #Add all the units to a flowsheet and connect them
    flsheet = Flowsheet.Flowsheet()
    flsheet.AddUnitOperation(flash, 'myFlash1')
    flsheet.AddUnitOperation(stream, 'myStream1')
    flsheet.AddUnitOperation(stream2, 'myStream2')
    flsheet.AddUnitOperation(mixer, 'myMixer')
    flsheet.SetParameterValue(NULIQPH_PAR, 1)
    flsheet.SetThermoAdmin(thAdmin)
    flsheet.SetThermo(thermo)

    #SetStream    
    portsIn = stream.GetPortNames(MAT|IN)
    #I know in advance there's only one port in
    stream.SetCompositionValue(portsIn[0], "PROPANE", 0.5)
    stream.SetCompositionValue(portsIn[0], "n-BUTANE", 0.5)
    stream.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.0)
    stream.SetCompositionValue(portsIn[0], "n-PENTANE", 0.0)
    stream.GetPort(portsIn[0]).SetPropValue(T_VAR, 460.15, FIXED_V)
    stream.GetPort(portsIn[0]).SetPropValue(P_VAR, 715.0, FIXED_V)
    stream.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 3000.0, FIXED_V)
    #stream.Solve() --- Could be done, but not yet

    #Set second Stream
    portsIn = stream2.GetPortNames(MAT|IN)
    #I know in advance there's only one port in    
    stream2.SetCompositionValue(portsIn[0], "PROPANE", 0.0)
    stream2.SetCompositionValue(portsIn[0], "n-BUTANE", 0.0)
    stream2.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.5)
    stream2.SetCompositionValue(portsIn[0], "n-PENTANE", 0.5)
    stream2.GetPort(portsIn[0]).SetPropValue(T_VAR, 200.15, FIXED_V)
    stream2.GetPort(portsIn[0]).SetPropValue(P_VAR, 715.0, FIXED_V)
    stream2.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 3000.0, FIXED_V)
    #stream.Solve() --- Could be done, but not yet

    #Set a mixer 
    mixer.SetParameterValue(NUSTIN_PAR, 2)

    #Set Flash UO

    #I already know the names of the ports
    uOpNameOut = 'myStream1'
    portNameOut = 'Out'
    uOpNameIn = 'myMixer'
    portNameIn = 'In0'
    print 'conn', flsheet.ConnectPorts(uOpNameOut, portNameOut, uOpNameIn, portNameIn)
    uOpNameOut = 'myStream2'
    portNameOut = 'Out'
    uOpNameIn = 'myMixer'
    portNameIn = 'In1'
    print 'conn2', flsheet.ConnectPorts(uOpNameOut, portNameOut, uOpNameIn, portNameIn)
    uOpNameOut = 'myMixer'
    portNameOut = 'Out'
    uOpNameIn = 'myFlash1'
    portNameIn = 'In'
    print 'conn3', flsheet.ConnectPorts(uOpNameOut, portNameOut, uOpNameIn, portNameIn)

    flsheet.Solve()

    portsIn = flash.GetPortNames(MAT|IN)
    portsOut = flash.GetPortNames(MAT|OUT)
    #Print some info in    
    for i in portsIn:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of port in "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of flash port in "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''  

    #Print some info out
    for i in portsOut:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of flash port out "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of flash port out "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''

    print """Finished Flowsh1 ++++++++++++++++++++++++++++++
    """

    flsheet.CleanUp()
    thAdmin.CleanUp()

def TestFlowsh2():
    print """
Init Flowsh2 ++++++++++++++++++++++++++++++"""    
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    #SetStream    
    stream = Stream.Stream_Material()
    stream2 = Stream.Stream_Material()
    mixer = Mixer.Mixer()
    flash = Flash.SimpleFlash() 
    
    #Add all the units to a flowsheet and connect them
    flsheet = Flowsheet.Flowsheet()
    flsheet.AddUnitOperation(flash, 'myFlash1')
    flsheet.AddUnitOperation(stream, 'myStream1')
    flsheet.AddUnitOperation(stream2, 'myStream2')
    flsheet.AddUnitOperation(mixer, 'myMixer')
    flsheet.SetParameterValue(NULIQPH_PAR, 1)
    
    flsheet.SetThermoAdmin(thAdmin)
    flsheet.SetThermo(thermo)
    
    portsIn = stream.GetPortNames(MAT|IN)
    #I know in advance there's only one port in
    stream.SetCompositionValue(portsIn[0], "PROPANE", 0.5)
    stream.SetCompositionValue(portsIn[0], "n-BUTANE", 0.5)
    stream.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.0)
    stream.SetCompositionValue(portsIn[0], "n-PENTANE", 0.0)
    stream.GetPort(portsIn[0]).SetPropValue(T_VAR, 460.15, FIXED_V)
    stream.GetPort(portsIn[0]).SetPropValue(P_VAR, 715.0, FIXED_V)
    stream.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 3000.0, FIXED_V)
    #stream.Solve() --- Could be done, but not yet

    #Set second Stream
    portsIn = stream2.GetPortNames(MAT|IN)
    #I know in advance there's only one port in    
    stream2.SetCompositionValue(portsIn[0], "PROPANE", 0.0)
    stream2.SetCompositionValue(portsIn[0], "n-BUTANE", 0.0)
    stream2.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.5)
    stream2.SetCompositionValue(portsIn[0], "n-PENTANE", 0.5)
    stream2.GetPort(portsIn[0]).SetPropValue(T_VAR, 200.15, FIXED_V)
    stream2.GetPort(portsIn[0]).SetPropValue(P_VAR, 715.0, FIXED_V)
    stream2.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 3000.0, FIXED_V)
    #stream.Solve() --- Could be done, but not yet

    #Set a mixer  
    mixer.SetParameterValue(NUSTIN_PAR, 2)

    #Set Flash UO

    #I already know the names of the ports
    uOpNameOut = 'myStream1'
    portNameOut = 'Out'
    uOpNameIn = 'myMixer'
    portNameIn = 'In0'
    print 'conn', flsheet.ConnectPorts(uOpNameOut, portNameOut, uOpNameIn, portNameIn)
    uOpNameOut = 'myStream2'
    portNameOut = 'Out'
    uOpNameIn = 'myMixer'
    portNameIn = 'In1'
    print 'conn2', flsheet.ConnectPorts(uOpNameOut, portNameOut, uOpNameIn, portNameIn)
    uOpNameOut = 'myMixer'
    portNameOut = 'Out'
    uOpNameIn = 'myFlash1'
    portNameIn = 'In'
    print 'conn3', flsheet.ConnectPorts(uOpNameOut, portNameOut, uOpNameIn, portNameIn)

    flsheet.Solve()

    portsIn = flash.GetPortNames(MAT|IN)
    portsOut = flash.GetPortNames(MAT|OUT)
    #Print some info in    
    for i in portsIn:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of port in "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of flash port in "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''  

    #Print some info out
    for i in portsOut:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of flash port out "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmpNames[j], ': ', comp[j]
        print ''

        print 'Some props of flash port out "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''

    print """Now lets add two cmps and delete one ++++++++++++++++++++++++++++++
    """
    thAdmin.AddCompound(provider, thCase, 'n-HEXANE')
    thAdmin.AddCompound(provider, thCase, 'n-DODECANE')
    thAdmin.DeleteCompound(provider, thCase, 'n-PENTANE')
    
    portsIn = stream.GetPortNames(MAT|IN)    
    stream.SetCompositionValue(portsIn[0], 'n-HEXANE', 0.25)
    stream.SetCompositionValue(portsIn[0], 'n-DODECANE', 0.25)

    portsIn = stream.GetPortNames(MAT|IN)    
    stream2.SetCompositionValue(portsIn[0], 'n-HEXANE', 0.3)
    stream2.SetCompositionValue(portsIn[0], 'n-DODECANE', 0.2)    

    flsheet.Solve()

    cmps = flash.GetCompoundNames()

    portsIn = flash.GetPortNames(MAT|IN)
    portsOut = flash.GetPortNames(MAT|OUT)
    #Print some info in    
    for i in portsIn:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of flash port in "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmps[j], ': ', comp[j]
        print ''

        print 'Some props of flash port in "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''  

    #Print some info out
    for i in portsOut:
        comp = flash.GetCompositionValues(i)        
        print 'Composition of flash port out "', i, '":'        
        for j in range(len(comp)): print 'fraction of ', cmps[j], ': ', comp[j]
        print ''

        print 'Some props of flash port out "', i, '":'
        print T_VAR, ': ', flash.GetPropValue(i, T_VAR)
        print H_VAR, ': ', flash.GetPropValue(i, H_VAR)
        print MOLEFLOW_VAR, ': ', flash.GetPropValue(i, MOLEFLOW_VAR)
        print ''


    print """Finished Flowsh2 ++++++++++++++++++++++++++++++
    """

    flsheet.CleanUp()
    thAdmin.CleanUp()
    

def TestRecycle():
    print """
Init TestRecycle ++++++++++++++++++++++++++++++"""   
    ##Set Thermo
    pkgName = "Peng-Robinson"
##    cmpNames = ("n-HEPTANE", "BENZENE", "TRIETHYLENE GLYCOL")
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-NONANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    #Create a flowsheet to contain all the units
    flsheet = Flowsheet.Flowsheet()
    flsheet.SetParameterValue(NULIQPH_PAR, 1)
    
    #SetStream    
    stream = Stream.Stream_Material()
    flsheet.AddUnitOperation(stream, 'Feed')

    stream.SetThermoAdmin(thAdmin)
    stream.SetThermo(thermo)
    portsIn = stream.GetPortNames(MAT|IN)
    #I know in advance there's only one port in
    stream.SetCompositionValue(portsIn[0], "PROPANE", 0.25)
    stream.SetCompositionValue(portsIn[0], "n-BUTANE", 0.25)
    stream.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.25)
    stream.SetCompositionValue(portsIn[0], "n-NONANE", 0.25)
    stream.GetPort(portsIn[0]).SetPropValue(T_VAR, 360.15, FIXED_V)
    stream.GetPort(portsIn[0]).SetPropValue(P_VAR, 715.0, FIXED_V)
    stream.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 3000.0, FIXED_V)

    recycle = Stream.Stream_Material()
    flsheet.AddUnitOperation(recycle, 'Recycle')

    recycle.SetThermoAdmin(thAdmin)
    recycle.SetThermo(thermo)
    portsIn = recycle.GetPortNames(MAT|IN)
    fixedGuess = FIXED_V | ESTIMATED_V
    #I know in advance there's only one port in
    recycle.SetCompositionValue(portsIn[0], "PROPANE", 0.0, fixedGuess)
    recycle.SetCompositionValue(portsIn[0], "n-BUTANE", 0.0, fixedGuess)
    recycle.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.5, fixedGuess)
    recycle.SetCompositionValue(portsIn[0], "n-NONANE", 0.5, fixedGuess)
    recycle.GetPort(portsIn[0]).SetPropValue(T_VAR, 460.15, fixedGuess)
    recycle.GetPort(portsIn[0]).SetPropValue(P_VAR, 715.0, fixedGuess)
    recycle.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 300.0, fixedGuess)

    #Set a mixer
    mixer = Mixer.Mixer()
    flsheet.AddUnitOperation(mixer, 'Mixer')    
    mixer.SetThermoAdmin(thAdmin)
    mixer.SetThermo(thermo)    
    mixer.SetParameterValue(NUSTIN_PAR, 2)    

    flsheet.ConnectPorts('Feed', 'Out', 'Mixer', 'In0')    
    flsheet.ConnectPorts('Recycle', 'Out', 'Mixer', 'In1')
    
    #Set Flash UO
    flash = Flash.SimpleFlash() 
    flsheet.AddUnitOperation(flash, 'Flash')
    flash.SetThermoAdmin(thAdmin)
    flash.SetThermo(thermo) 

    flsheet.ConnectPorts('Mixer', 'Out', 'Flash', 'In')
        
    #Set a splitter
    splitter = Split.Splitter()
    flsheet.AddUnitOperation(splitter, 'Splitter')    
    splitter.SetThermoAdmin(thAdmin)
    splitter.SetThermo(thermo)    
    splitter.SetParameterValue(NUSTOUT_PAR, 2)    

    flsheet.ConnectPorts('Flash', 'Liq0', 'Splitter', 'In')
    
    splitter.GetPort('Out1').SetPropValue(MOLEFLOW_VAR, 200.0, FIXED_V)
    
    # close recycle
    flsheet.ConnectPorts('Splitter','Out1','Recycle','In')
    
    flsheet.Solve()
    print '***************'
    cmps = splitter.GetCompositionValues('Out0')
    for j in range(len(cmps)): print 'fraction of ', cmpNames[j], ': ', cmps[j]
    print '***************'       
    print 'Some properties of splitter Out0'
    print T_VAR, ': ', splitter.GetPropValue('Out0', T_VAR)
    print P_VAR, ': ', splitter.GetPropValue('Out0', P_VAR)
    print H_VAR, ': ', splitter.GetPropValue('Out0', H_VAR)
    print MOLEFLOW_VAR, ': ', splitter.GetPropValue('Out0', MOLEFLOW_VAR)

    print '****reset pressure***'
    stream.GetPort(portsIn[0]).SetPropValue(P_VAR, 800.0, FIXED_V)
    flsheet.Solve()
    print '*************** splitter out1'       
    cmps = splitter.GetCompositionValues('Out0')
    for j in range(len(cmps)): print 'fraction of ', cmpNames[j], ': ', cmps[j]
    print '***************'
    print 'Some properties of splitter Out0'
    print T_VAR, ': ', splitter.GetPropValue('Out0', T_VAR)
    print P_VAR, ': ', splitter.GetPropValue('Out0', P_VAR)
    print H_VAR, ': ', splitter.GetPropValue('Out0', H_VAR)
    print MOLEFLOW_VAR, ': ', splitter.GetPropValue('Out0', MOLEFLOW_VAR)

    print """Finished TestRecycle ++++++++++++++++++++++++++++++
    """
    
    flsheet.CleanUp()
    thAdmin.CleanUp()
    

def TestRecycle2():
    print """
Init TestRecycle2 ++++++++++++++++++++++++++++++"""   
    ##Set Thermo
    pkgName = "Peng-Robinson"
##    cmpNames = ("n-HEPTANE", "BENZENE", "TRIETHYLENE GLYCOL")
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-NONANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    #Create a flowsheet to contain all the units
    flsheet = Flowsheet.Flowsheet()
    flsheet.SetThermoAdmin(thAdmin)
    flsheet.SetThermo(thermo)    
    flsheet.SetParameterValue(NULIQPH_PAR, 1)
    
    #SetStream    
    stream = Stream.Stream_Material()
    flsheet.AddUnitOperation(stream, 'Feed')

    portsIn = stream.GetPortNames(MAT|IN)
    #I know in advance there's only one port in
    stream.SetCompositionValue(portsIn[0], "PROPANE", 0.25)
    stream.SetCompositionValue(portsIn[0], "n-BUTANE", 0.25)
    stream.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.25)
    stream.SetCompositionValue(portsIn[0], "n-NONANE", 0.25)
    stream.GetPort(portsIn[0]).SetPropValue(T_VAR, 360.15, FIXED_V)
    stream.GetPort(portsIn[0]).SetPropValue(P_VAR, 715.0, FIXED_V)

    recycle = Stream.Stream_Material()
    flsheet.AddUnitOperation(recycle, 'Recycle')

    portsIn = recycle.GetPortNames(MAT|IN)
    #I know in advance there's only one port in

    #Set a mixer
    mixer = Mixer.Mixer()
    flsheet.AddUnitOperation(mixer, 'Mixer')    
    mixer.SetParameterValue(NUSTIN_PAR, 2)    

    flsheet.ConnectPorts('Feed', 'Out', 'Mixer', 'In0')    
    flsheet.ConnectPorts('Recycle', 'Out', 'Mixer', 'In1')

    #Set mixed Stream    
    mixed = Stream.Stream_Material()
    flsheet.AddUnitOperation(mixed, 'Mixed')

    fixedGuess = FIXED_V | ESTIMATED_V
    portsIn = mixed.GetPortNames(MAT|IN)

    #Set Flash UO
    flash = Flash.SimpleFlash() 
    flsheet.AddUnitOperation(flash, 'Flash')

    # to start, just guess same as feed
    flash.SetCompositionValue(portsIn[0], "PROPANE", 0.25, fixedGuess)
    flash.SetCompositionValue(portsIn[0], "n-BUTANE", 0.25, fixedGuess)
    flash.SetCompositionValue(portsIn[0], "ISOBUTANE", 0.25, fixedGuess)
    flash.SetCompositionValue(portsIn[0], "n-NONANE", 0.25, fixedGuess)
    flash.GetPort(portsIn[0]).SetPropValue(T_VAR, 360.15, fixedGuess)    
    
    flsheet.ConnectPorts('Mixer', 'Out', 'Mixed', 'In')    
    
    flsheet.ConnectPorts('Mixed', 'Out', 'Flash', 'In')
        
    #Set a splitter
    splitter = Split.Splitter()
    flsheet.AddUnitOperation(splitter, 'Splitter')
    splitter.SetParameterValue(NUSTOUT_PAR, 2)

    flsheet.ConnectPorts('Flash', 'Liq0', 'Splitter', 'In')
    
    splitter.GetPort('Out1').SetPropValue(MOLEFLOW_VAR, 200.0, FIXED_V)
    splitter.GetPort('Out1').SetPropValue(P_VAR, 715.0, FIXED_V)
    flash.GetPort('Vap').SetPropValue(MOLEFLOW_VAR, 1652.682, FIXED_V)
    
    # close recycle
    flsheet.ConnectPorts('Splitter','Out1','Recycle','In')
    
    # add balance to back calculate flow
    bal = Balance.BalanceOp()
    flsheet.AddUnitOperation(bal, 'Balance')
    bal.SetParameterValue(NUSTIN_PAR + Balance.S_MAT, 2)
    bal.SetParameterValue(NUSTOUT_PAR + Balance.S_MAT, 1)
    bal.SetParameterValue('BalanceType', Balance.MOLE_BALANCE)
    flsheet.ConnectPorts('Balance', 'In1', 'Flash', 'Vap')
    flsheet.ConnectPorts('Balance', 'In0', 'Splitter', 'Out0')
    flsheet.ConnectPorts('Balance', 'Out0', 'Feed', 'In')    
    
    flsheet.Solve()
    print '***************'
    cmps = splitter.GetCompositionValues('Out0')
    for j in range(len(cmps)): print 'fraction of ', cmpNames[j], ': ', cmps[j]
    print '***************'       
    print 'Some properties of splitter Out0'
    print T_VAR, ': ', splitter.GetPropValue('Out0', T_VAR)
    print P_VAR, ': ', splitter.GetPropValue('Out0', P_VAR)
    print H_VAR, ': ', splitter.GetPropValue('Out0', H_VAR)
    print MOLEFLOW_VAR, ': ', splitter.GetPropValue('Out0', MOLEFLOW_VAR)

    print 'Some properties of mixed Out'
    print T_VAR, ': ', mixed.GetPropValue('Out', T_VAR)
    print P_VAR, ': ', mixed.GetPropValue('Out', P_VAR)
    print H_VAR, ': ', mixed.GetPropValue('Out', H_VAR)
    print MOLEFLOW_VAR, ': ', mixed.GetPropValue('Out', MOLEFLOW_VAR)

    print 'Some properties of stream Out'
    print T_VAR, ': ', stream.GetPropValue('Out', T_VAR)
    print P_VAR, ': ', stream.GetPropValue('Out', P_VAR)
    print H_VAR, ': ', stream.GetPropValue('Out', H_VAR)
    print MOLEFLOW_VAR, ': ', stream.GetPropValue('Out', MOLEFLOW_VAR)

    print '****reset pressure***'
    #stream.GetPort(portsIn[0]).SetPropValue(P_VAR, 800.0, FIXED_V)
    stream.GetPort(portsIn[0]).SetPropValue(T_VAR, 400.0, FIXED_V)
    
    flsheet.Solve()
    print '*************** splitter out1'       
    cmps = splitter.GetCompositionValues('Out0')
    for j in range(len(cmps)): print 'fraction of ', cmpNames[j], ': ', cmps[j]
    print '***************'
    print 'Some properties of splitter Out0'
    print T_VAR, ': ', splitter.GetPropValue('Out0', T_VAR)
    print P_VAR, ': ', splitter.GetPropValue('Out0', P_VAR)
    print H_VAR, ': ', splitter.GetPropValue('Out0', H_VAR)
    print MOLEFLOW_VAR, ': ', splitter.GetPropValue('Out0', MOLEFLOW_VAR)

    print """Finished TestRecycle2 ++++++++++++++++++++++++++++++
    """
    
    flsheet.CleanUp()
    thAdmin.CleanUp()


def TestMoleBalance():
    print """
Init TestMoleBalance ++++++++++++++++++++++++++++++"""
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = 'myTh'
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)

    flowSh = Flowsheet.Flowsheet()
    flowSh.SetThermoAdmin(thAdmin)
    flowSh.SetThermo(thermo)    
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    pIn1 = flowSh.CreatePort(IN|MAT, 'pIn1')
    pIn2 = flowSh.CreatePort(IN|MAT, 'pIn2')
    pOut1 = flowSh.CreatePort(OUT|MAT, 'pOut1')
    pOut2 = flowSh.CreatePort(OUT|MAT, 'pOut2')

    pIn1.SetCompositionValue("PROPANE", .3, FIXED_V)
    pIn1.SetCompositionValue("n-BUTANE", .7, FIXED_V)

    pIn2.SetCompositionValue("PROPANE", .4, FIXED_V)
    pIn2.SetCompositionValue("n-BUTANE", .6, FIXED_V)

    pOut1.SetCompositionValue("PROPANE", .6, FIXED_V)
    pOut1.SetCompositionValue("n-BUTANE", .4, FIXED_V)

    pOut2.SetCompositionValue("PROPANE", .8, FIXED_V)
    pOut2.SetCompositionValue("n-BUTANE", .2, FIXED_V)

    pIn1.SetPropValue(MOLEFLOW_VAR, 1000, FIXED_V)
    pOut1.SetPropValue(MOLEFLOW_VAR, 1500, FIXED_V)

    myBalance = Balance.Balance(Balance.MOLE_BALANCE)
    myBalance.AddInput(pIn1)
    myBalance.AddInput(pIn2)
    myBalance.AddOutput(pOut1)
    myBalance.AddOutput(pOut2)

    myBalance.DoBalance()

    print 'moleFlowIn1', pIn1.GetPropValue(MOLEFLOW_VAR)
    print 'moleFlowIn2', pIn2.GetPropValue(MOLEFLOW_VAR)
    print 'moleFlowOut1', pOut1.GetPropValue(MOLEFLOW_VAR)
    print 'moleFlowOut2', pOut2.GetPropValue(MOLEFLOW_VAR)
    print 'moleBalance', (pIn1.GetPropValue(MOLEFLOW_VAR) + pIn2.GetPropValue(MOLEFLOW_VAR)) \
          - (pOut1.GetPropValue(MOLEFLOW_VAR) + pOut2.GetPropValue(MOLEFLOW_VAR))

    print """Finished TestMoleBalance ++++++++++++++++++++++++++++++
    """
    flowSh.CleanUp()
    thAdmin.CleanUp()
    

##def TestSimpleExcelDistCol():
##    print """
##Init SimpleExcelDistCol ++++++++++++++++++++++++++++++"""
##    ##Set Thermo
##    pkgName = "Peng-Robinson"
##    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE")
##    thAdmin = ThermoAdmin.ThermoAdmin()
##    ExcelModName = 'ExcelThermo'
##    ExcelClassName = 'ThermoInterfase'    
##    err = thAdmin .SetNewThermoProvider(ExcelModName, ExcelClassName)
##    providers = thAdmin.GetAvThermoProviderNames()
##    provider = providers[1] #Should be the Excel thing
##    thCase = 'myTh'
##    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
##    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)
##
##    ##Load vals    
##    distCol = DistCol.SimpleDistCol() 
##    distCol.SetThermoAdmin(thAdmin)
##    distCol.SetThermo(thermo) 
##    cmps = distCol.GetCompoundNames()
##    print 'Cmps: ', cmps
##    portsIn = distCol.GetPortNames(MAT|IN)
##    print 'Names Ports In: ', portsIn
##    portsOut = distCol.GetPortNames(MAT|OUT)
##    print 'Names Ports Out: ', portsOut
##    distCol.SetParameterValue(R_PAR, 1)
##    distCol.SetCompositionValue(IN_PORT + str(10), "PROPANE", 0.05)
##    distCol.SetCompositionValue(IN_PORT + str(10), "n-BUTANE", 0.40)
##    distCol.SetCompositionValue(IN_PORT + str(10), "ISOBUTANE", 0.40)
##    distCol.SetCompositionValue(IN_PORT + str(10), "n-PENTANE", 0.15)
##    distCol.GetPort().SetPropValue(IN_PORT + str(10), T_VAR, 303.15)
##    distCol.GetPort().SetPropValue(IN_PORT + str(10), P_VAR, 720.0)
##    distCol.GetPort().SetPropValue(IN_PORT + str(10), MOLEFLOW_VAR, 10.0)
##
##    #Specify P and dist flow on top 
##    distCol.GetPort().SetPropValue(L_PORT + str(0), P_VAR, 700.0)
##    distCol.GetPort().SetPropValue(L_PORT + str(0), MOLEFLOW_VAR, 5.0)
##
##    #Specify P on bottom
##    distCol.GetPort().SetPropValue(L_PORT + str(21), P_VAR, 720.0)
##
##    print 'Return value from Solve()', distCol.Solve()
##    print ''
##
##    #Print some info in    
##    comp = distCol.GetCompositionSafe(IN_PORT + str(10))        
##    print 'Composition of port in "', IN_PORT + str(10), '":'        
##    for j in comp: print 'fraction of ', j[0], ': ', j[1].GetValue()
##    print ''
##
##    print 'Some props of port in "', IN_PORT + str(10), '":'
##    print T_VAR, ': ', distCol.GetPropValue(IN_PORT + str(10), T_VAR)
##    print H_VAR, ': ', distCol.GetPropValue(IN_PORT + str(10), H_VAR)
##    print MOLEFLOW_VAR, ': ', distCol.GetPropValue(IN_PORT + str(10), MOLEFLOW_VAR)
##    print ''  
##
##    #Print some info out
##    comp = distCol.GetCompositionSafe(L_PORT + str(0))        
##    print 'Composition of port out "', L_PORT + str(0), '":'        
##    for j in comp: print 'fraction of ', j[0], ': ', j[1].GetValue()
##    print ''
##    
##    print 'Some props of port out "', L_PORT + str(0), '":'
##    print T_VAR, ': ', distCol.GetPropValue(L_PORT + str(0), T_VAR)
##    print H_VAR, ': ', distCol.GetPropValue(L_PORT + str(0), H_VAR)
##    print MOLEFLOW_VAR, ': ', distCol.GetPropValue(L_PORT + str(0), MOLEFLOW_VAR)
##    print ''        
##
##    comp = distCol.GetCompositionSafe(L_PORT + str(21))        
##    print 'Composition of port out "', L_PORT + str(21), '":'        
##    for j in comp: print 'fraction of ', j[0], ': ', j[1].GetValue()
##    print ''
##
##    print 'Some props of port out "', L_PORT + str(21), '":'
##    print T_VAR, ': ', distCol.GetPropValue(L_PORT + str(21), T_VAR)
##    print H_VAR, ': ', distCol.GetPropValue(L_PORT + str(21), H_VAR)
##    print MOLEFLOW_VAR, ': ', distCol.GetPropValue(L_PORT + str(21), MOLEFLOW_VAR)
##    print ''    
##
##    print """Finished SimpleDistCol ++++++++++++++++++++++++++++++
##    """
##
##    distCol.CleanUp()

def TestThAdminSaveLoad():
    print """
Init ThAdminSaveLoad ++++++++++++++++++++++++++++++"""
    ##Set Thermo
    pkgName = "Peng-Robinson"
    cmpNames = ("PROPANE", "n-BUTANE", "ISOBUTANE", "n-PENTANE")
    thAdmin = ThermoAdmin.ThermoAdmin()
    
    #saveInfo = thAdmin.GetSaveInfo()
    #print "saveInfo before doing anything: ", saveInfo, "\n"
    
    providers = thAdmin.GetAvThermoProviderNames()
    provider = providers[0] #Should be Virt Mat
    thCase = "thCase1"
    thermo = thAdmin.AddPkgFromName(provider, thCase, pkgName)
    for i in cmpNames: thAdmin.AddCompound(provider, thCase, i)

    parentFlowsh = Flowsheet.Flowsheet()
    parentFlowsh.SetThermoAdmin(thAdmin)
    parentFlowsh.SetThermo(thermo) 
    
    flash = Flash.SimpleFlash()
    parentFlowsh.AddUnitOperation(flash, "myFlash1")

    portsIn = flash.GetPortNames(MAT|IN)
    comps = [0.25, 0.25, 0.25, 0.25]
    flash.SetCompositionValues(portsIn[0], comps)
    flash.GetPort(portsIn[0]).SetPropValue(T_VAR, 273.15, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(P_VAR, 101.325, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)
    
    f = open('myTemp.out', 'w')
    cPickle.dump(parentFlowsh, f)
    f.close()

    
    thAdmin.CleanUp()
    parentFlowsh.CleanUp()
    del thAdmin
    del parentFlowsh
    del flash

    f = open('myTemp.out', 'r')
    parentFlowsh = cPickle.load(f)
    f.close()
    thAdmin = parentFlowsh.GetThermoAdmin()
    flash = parentFlowsh.GetChildUO("myFlash1")
    os.remove('myTemp.out')

    parentFlowsh.Solve()

    print "Just saved an loaded a flowsheet with a separator. Now solve.. \n"
    h = flash.GetPropValue('Vap', H_VAR)
    print "H value = ", h
     
    thCases = thAdmin.GetAvThCaseNames(provider)
    print "Th cases:", thCases

    propPkg = thAdmin.GetPropPkgString(provider, thCases[0])
    print "Prop pkg for", str(thCases[0]), ":", propPkg
    
    cmps = thAdmin.GetSelectedCompoundNames(provider, thCases[0])
    print "Compounds for", str(thCases[0]), ":", cmps, "\n"
    
    parentFlowsh.CleanUp()
    thAdmin.CleanUp()
    
    print """Finished ThAdminSaveLoad ++++++++++++++++++++++++++++++
    """

def PropertiesHandling():
    print """
Init PropertiesHandling ++++++++++++++++++++++++++++++"""

    thAdmin = ThermoAdmin.ThermoAdmin()
    providers = thAdmin.GetAvThermoProviderNames()
    print "Thermo providers: ", providers, "\n"
    if len(providers) < 1:
        print "Error"
        return 0
    thermo = thAdmin.AddPkgFromName(providers[0], "thCase1", "Peng-Robinson")
    thAdmin.AddCompound(providers[0], "thCase1", "METHANE")
    thAdmin.AddCompound(providers[0], "thCase1", "PROPANE")

    parentFlowsh = Flowsheet.Flowsheet()
    parentFlowsh.SetThermoAdmin(thAdmin)
    parentFlowsh.SetThermo(thermo) 

    commonProps = thAdmin.GetCommonPropertyNames(providers[0])
    print "Initial common properties: ", commonProps, "\n"

    suppProps = thAdmin.GetPropertyNames(providers[0])
    print "Supported properties: ", suppProps, "\n"
    
    flash = Flash.SimpleFlash()
    parentFlowsh.AddUnitOperation(flash, "myFlash1")

    portsIn = flash.GetPortNames(MAT|IN)
    comps = [0.25, 0.25]
    flash.SetCompositionValues(portsIn[0], comps)
    flash.GetPort(portsIn[0]).SetPropValue(T_VAR, 273.15, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(P_VAR, 101.325, FIXED_V)
    flash.GetPort(portsIn[0]).SetPropValue(MOLEFLOW_VAR, 10.0, FIXED_V)

    print "A separator was added, now let's request Viscosity from one of its ports"
    parentFlowsh.Solve()
    visc = flash.GetPropValue(portsIn[0], VISCOSITY_VAR)
    print "Viscosity value = ", visc, ". It is None, because it ain't there :) \n"

    commonProps = list(commonProps)
    commonProps.append('Viscosity')
    print "Now lets set the following as commonProps", commonProps, "\n"
    #thAdmin.SetCommonPropertyNames(providers[0], commonProps)
    thAdmin.SetCommonPropertyNames(providers[0], suppProps)
    commonProps = thAdmin.GetCommonPropertyNames(providers[0])
    print "These are the new common properties: ", commonProps, "\n"

    print "Let's solve again and get viscosity again"
    flash.GetPort(portsIn[0]).SetPropValue(T_VAR, 300.15, FIXED_V)
    parentFlowsh.Solve()
    visc = flash.GetPropValue(portsIn[0], VISCOSITY_VAR)
    print "Viscosity value = ", visc, "\n"
    
    parentFlowsh.CleanUp()
    thAdmin.CleanUp()
    
    print """PropertiesHandling ++++++++++++++++++++++++++++++
    """

# Order --> key: (MethodName, Description) 
TEST_MAP = {10: ('TestSimpleFlash', 'Test to a flash'),
           11: ('TestSimpleFlash2LPhase', 'Tests a two liquid phase flash'),
           20: ('TestMixAndFlash', 'Tests the unit op MixAndFlash'),
           30: ('TestLiqLiqEx', 'Tests the Liquid Liquid extraction'),
           50: ('TestHeater', 'Tests the heater'),
           51: ('TestHeatEx', 'Test the heat exchanger'),
           60: ('TestFlowsh1', 'Flowsheet: 2 streams --> mixer --> flash'),
           61: ('TestFlowsh2', 'Flowsheet: 2 streams --> mixer --> flash. Then changes cmps and calc again'),
           70: ('TestRecycle', 'stream --> mixer --> recycle --> flash'),
           71: ('TestRecycle2', 'stream --> mixer --> recycle --> flash with back calc'),
           80: ('TestMoleBalance', 'Tests the mole balance from Balance.Balance'),
           100: ('TestThAdminSaveLoad', 'Tests the save and load methods of thAdmin'),
           110: ('PropertiesHandling', 'Tests setting and getting common and supported properties')}
##           90: ('TestSimpleExcelDistCol', 'Tests the mole balance from Balance.Balance') }
    
def RunTest(testNu=-1):
    if testNu == -1:
        tests = TEST_MAP.keys()
        tests.sort()
        for test in tests:
            try: exec(TEST_MAP[test][0] + '()')
            except:
                print 'Error in:', test, ';', TEST_MAP[test][0]
    elif TEST_MAP.has_key(testNu):
        try: exec(TEST_MAP[testNu][0] + '()')
        except SimError, e:
            print e.args
        except VMGerror, e:
            print str(e)
        except Exception, e:
            print 'Error in:', testNu, ';', TEST_MAP[testNu][0]
            print sys.exc_type
            print e
            import traceback
            traceback.print_tb(sys.exc_traceback)

class OutputToFile:
    def __init__(self, filePath=None):
        if not filePath: self.filePath = os.getcwd() + os.sep + 'Test.out'
        else: self.filePath = filePath
        mode = 'w'
        self.file = open(self.filePath, mode)
        print self.filePath
    
    def __del__(self):
        try: self.file.close()
        except: pass

    def write(self, str):
        self.file.write(str)

def GetTestMap():
    """Returns a copy of TEST_MAP"""
    return TEST_MAP.copy()

def GetTestInfo(testNu=-1):
    """Returns a tuple (MethodName, Description)"""
    return TEST_MAP.get(testNu, None)
    
if __name__ == '__main__':

    #This will be the default if no  arguments are given
    defTestNu = -1
    try: testNu = int(sys.argv[1])
    except: testNu = defTestNu

    #Change output to file if necessary    
    toFile = 0 #Change the value to 0 if output is wanted in the interpreter
    oldstdout = sys.stdout
    output = None
    if toFile:
        output = OutputToFile()
        sys.stdout = output

    try: RunTest(testNu)
    except: sys.stdout = oldstdout
    sys.stdout = oldstdout
    del output

    