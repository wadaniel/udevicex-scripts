#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 17 11:39:29 2018

@author: alexeedm
"""
import glob
import itertools
import numpy as np
import matplotlib.pyplot as plt
import math
import subprocess


def coefficient(frc, rho, u, r, R):
    #return 0.25 * frc / (rho * u**2 * r**4 / R**2)
    return frc / ( rho * u**2 * (2*r)**2 )

def mean_err_cut(vals):
    npvals = np.array(vals[20:]).astype(np.float)
    
    m = np.mean(npvals)
    v = np.var(npvals) / npvals.size
    
    return m,v

def dump_plots(positions, alldata, r1, r2):
    
    plt.plot(r1[:,0], r1[:,1], "o", ms=6, markeredgewidth=1.5, markeredgecolor='black', label="Nakagawa et al., J. Fluid Mech (2015)")
    plt.plot(r2[:,0], r2[:,1], "s", ms=6, markeredgewidth=1.5, markeredgecolor='black', label="Di Carlo et al., Phys Rev Lett (2009)")
        
    for data, err, label, fmt in alldata:
        plt.errorbar(positions, data, yerr=err, markeredgewidth=1.5, markeredgecolor='black', fmt=fmt, ms=10, linewidth=2, label=label)

    plt.xlabel('y/R', fontsize=16)
    plt.ylabel('Cl', fontsize=16)
    plt.grid()
    plt.legend(fontsize=14)

    plt.rc('xtick', labelsize=14)
    plt.rc('ytick', labelsize=14)

    plt.tight_layout()
    plt.show()
#    figpath = "%s/profiles.png" % (resdir)
#    plt.savefig(figpath, bbox_inches='tight')
#    plt.close(fig)

## ratio = 0.166
nakagawa = np.array([
0, 0.00032573289902280284,
0.04, 0.005618892508143333,
0.08, 0.011237785016286653,
0.12, 0.017100977198697083,
0.16, 0.022394136807817606,
0.2, 0.027117263843648216,
0.24, 0.031433224755700345,
0.28, 0.03444625407166125,
0.32, 0.036726384364820855,
0.36, 0.037214983713355056,
0.4, 0.03566775244299676,
0.44, 0.03184039087947884,
0.48, 0.024674267100977212,
0.52, 0.014739413680781771,
0.56, 0.0014657980456026162,
0.60, -0.015472312703583055,
0.64, -0.03526058631921823,
0.68, -0.062377850162866455,
0.72, -0.10171009771986969
]).reshape([-1, 2])
    
dicarlo = np.array([
0.72, -0.3841135334839302,
0.68, -0.23312591687502587,
0.64, -0.1251716842593535,
0.6, -0.033796060595775446,
0.56, 0.008196721311475419,
0.52, 0.053364483514162786,
0.48, 0.08336419438819054,
0.44, 0.12606269508146442,
0.4, 0.1341934202471147,
0.36, 0.14091283354766365,
0.320, 0.17126527810775855,
0.28, 0.17022505314261077,
0.24, 0.17024265211483083,
0.20, 0.16990739169403937,
0.16, 0.12548079763570383,
0.12, 0.0891667012360764,
0.08, 0.06907848010247636,
0.04, 0.026415303060587036,
-0, 0.005621740261797292        
]).reshape([-1, 2])
    
cubism4 = np.array([
0.1, 1.09349e-06,
0.2, 1.95439e-06,
0.3, 2.62226e-06,
0.4, 2.64473e-06,
0.5, 8.26858e-07,
0.6, -6.12644e-06,
0.7, -1.38004e-05
]).reshape([-1, 2])
    
cubism8 = np.array([
0.1, 1.02796e-06,
0.2, 1.99567e-06,
0.3, 2.61481e-06,
0.4, 2.45607e-06,
0.5, 7.39905e-07,
0.6, -6.40721e-06,
0.7, -1.36804e-05
]).reshape([-1, 2])

cubism4[:,0] = cubism4[:,0] * 0.1875 / (0.3030303030 / 2)
cubism8[:,0] = cubism8[:,0] * 0.1875 / (0.3030303030 / 2)

cubism4[:,1] = coefficient(cubism4[:,1], 1.0, 0.13200, 0.0333333, 0.3030303030)
cubism8[:,1] = coefficient(cubism8[:,1], 1.0, 0.13200, 0.0333333, 0.3030303030)
    
dicarlo[:,1] = dicarlo[:,1] * 2.096**2 * 0.22**2

## ratio = 0.15
#ref = np.array([0.0004303640088072491, 0.00040587219343701797,
#                0.10036231090273762, 0.06927461139896374,
#                0.20029809177447455, 0.1451554404145082,
#                0.3005244333928515, 0.1724525043177897,
#                0.40010050498964855, 0.17044905008635639,
#                0.5002811127299022, 0.11410189982728863,
#                0.6001194010231242, 0.011675302245250485,
#                0.6999018227825918, -0.19292746113989645    ]).reshape([8, 2])

def get_forces(case, U):
    prefix = ""    
    rho = 8.0
    r = 5.0
    R = 23.0
    
    positions = np.linspace(0.0, 0.72, 19)
    
    Cls = [0]
    err_Cls = [0]
    
    
    for pos in positions:
        if pos < 0.0001:
            continue
        
        strpos = "%.2g" % pos
        full_folder = prefix + case + strpos + "x0"
        
        print(full_folder)
        
                
        files = sorted(glob.glob(full_folder + "/pinning_force/*.txt"))
        lines = list(itertools.chain.from_iterable([open(f).readlines() for f in files]))
            
        fy = [ x.split()[3] for x in lines ]
        
        (my, vy) = mean_err_cut(fy)
        
        my *= np.sqrt(2)
        
        Cls.append(coefficient(my, rho, U, r, R))
        err_Cls.append(coefficient(3.0*math.sqrt(vy), rho, U, r, R))
        
    return Cls, err_Cls

def get_forces_cubism(case):
    U = 0.13200
    rho = 1.0
    r = 0.0333333
    R = 0.3030303030
    
    positions = np.arange(0.0, 0.8, 0.1)
    
    Cls = [0]
    err_Cls = [0]
    
    
    for pos in positions:
        if pos < 0.0001:
            continue
        
        try:
            strpos = "%.2g" % pos
            full_folder = case + strpos + "x0.0"
            
            print(full_folder)
            
                    
            fname = full_folder + "/diagnosticsForces_0.dat"
            #fname = full_folder + "/forceValues_0.dat"
            line = subprocess.check_output(['tail', '-1', fname])
            
            my = float(line.split()[4])
            Cls.append(coefficient(my, rho, U, r, R))
        
        except:
            Cls.append(0)
            
        err_Cls.append(0)
        
    return Cls, err_Cls

alldata = []
#alldata.append( get_forces("/home/alexeedm/extern/daint/scratch/focusing_square/case_5_0.08__80_20_1.5__") + ("Present", "o") )
#alldata.append( get_forces("/home/alexeedm/extern/daint/scratch/focusing_square/case_5_0.0788__160_20_3.0__", 2.3) + ("Present", "D") ) # 2244!
#alldata.append( get_forces_cubism("/home/alexeedm/extern/daint/scratch/cubism-square-lift-2d/case_4_0_") + ("Present", "o") )
#alldata.append( get_forces_cubism("/home/alexeedm/extern/daint/scratch/cubism-square-lift-2d/case_4_0_") + ("Present", "o") )
alldata.append( get_forces_cubism("/home/alexeedm/extern/daint/scratch/cubism-square-lift-2d/case_yetwider_8_0_") + ("Present", "o") )
#alldata.append( get_forces("/home/alexeedm/extern/daint/scratch/focusing_square/case_5_0.02144__80_10_1.5__", 1.1704) + ("Present", "o") )

print(alldata)
#print Cls
#print err_Cls

fig = plt.figure()
#positions = np.linspace(0.0, 0.72, 19)
positions = np.arange(0.0, 0.8, 0.1)

dump_plots(positions, alldata, nakagawa, dicarlo)
fig.savefig("/home/alexeedm/udevicex/media/duct_lift_coefficients.pdf", bbox_inches='tight')





