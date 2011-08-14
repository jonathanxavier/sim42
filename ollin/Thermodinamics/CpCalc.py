from math import pow
from numpy.oldnumeric import array


def CapG(case):
    """
    This Module Calc
    Cp for Gas"""
    Cp_temp = case.aCp + case.bCp*case.t + case.cCp*pow(case.t,2)+ case.dCp*pow(case.t,3)
    return Cp_temp
