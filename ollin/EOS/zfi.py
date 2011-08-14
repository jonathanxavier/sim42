from numpy.oldnumeric import array

def ZFI(Zo, A, B):
    list_temp = []

    for j  in range(len(A)) :
        Ai = A[j]
        Bi = B[j]
        i = 1
        Fz = 1
        a = (1 + Bi - pow(Bi,2))
        b = (Ai - Bi - pow(Bi,2))
        c = Ai*Bi
        Z = Zo
        while i<=50 or abs(Fz)>=1e-16:
        
            Fz  = pow(Z,3) - a*pow(Z,2) + b*Z - c
            dFz = 3*pow(Z,2) - 2*a*Z + b
            Zz = Fz/dFz
#            print i,Fz,Zo,Ai,Bi            
            Z=Z-Zz
            if Z <=0:
                Z = 1
            i +=1

        list_temp.append(Z)
    return array(list_temp)
