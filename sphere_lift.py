#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Jan  8 10:47:40 2018

@author: alexeedm
"""

import glob
import itertools
import numpy as np
import matplotlib.pyplot as plt
import math
import re
import pickle

def coefficient(frc, rho, u, r):
    return frc / (0.5 * rho * u**2 * math.pi * r**2)

def mean_err_cut(vals):
    npvals = np.array(vals[10:]).astype(np.float)
    
    m = np.mean(npvals)
    v = np.var(npvals) / math.sqrt(npvals.size)
    
    return m,v

def dump_plots(Res, Cds, Cls, err_Cds, err_Cls,  ref_Cd, ref_Cl):
    nrows = 1
    ncols = 2
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(4*ncols,4*nrows), facecolor='white')
    
    def plot_one(ax, x, y, err, ref_x, ref_y, label, ylabel):

        ax.plot(ref_x, ref_y,       '--o',   markeredgewidth=1,   markeredgecolor='black', color='C1', ms=5, label=label, zorder=-1)
        ax.errorbar(x, y, yerr=err, fmt='D', markeredgewidth=1.5, markeredgecolor='black', color='C2', ms=6, label="Present")
    
        ax.set_xscale("log", nonposx='clip')
        ax.set_yscale("log", nonposy='clip')
        plt.xlabel(r'$Re$', fontsize=16)
        plt.ylabel(ylabel,  fontsize=16)
        
        plt.tick_params(axis='both', which='major', labelsize=12)

        plt.grid()
        plt.grid(which='minor', linewidth=0.1)


    plot_one(plt.subplot(nrows, ncols, 1), Res, Cds, err_Cds,  ref_Cd[:,0], ref_Cd[:,1], "Zeng, Balachandar, Fisher. JFM (2015)", r'$C_d$')
    plot_one(plt.subplot(nrows, ncols, 2), Res, Cls, err_Cls,  ref_Cl[:,0], ref_Cl[:,1], "Zeng, Balachandar, Fisher. JFM (2015)", r'$C_l$')

#    plt.subplots_adjust(wspace=0.3)
#    plt.subplots_adjust(hspace=0.3)
    
    #handles, labels = ax.get_legend_handles_labels()
    #fig.legend(handles, labels, loc = 'upper center')

    fig.tight_layout()
    plt.show()
    fig.savefig("/home/alexeedm/udevicex-scripts/media/sphere_wall.pdf", bbox_inches='tight')

    

prefix = "/home/alexeedm/extern/daint/project/alexeedm/sphere_lift/"

cases = ["case_160_245.9982_3.0_1.0_8__5_10_0.40",
         "case_160_55.5787_3.0_1.0_8__5_10_0.40",
         "case_160_42.3792_3.0_1.0_8__10_20_0.80",
         "case_160_9.3198_3.0_1.0_8__10_20_0.80",
#        "case_160_308.6053_3.0_1.0_8__5_10_0.50",
#            "case_160_71.9017_3.0_1.0_8__5_10_0.50",
#            "case_160_22.1100_3.0_1.0_8__10_20_0.50",
#            "case_160_15.1207_3.0_1.0_8__10_20_1.00",
           "case_160_3.0186_3.0_1.0_8__12_24_1.00"
         ]

ref_Cd = np.array([0.5007949732809864, 67.64969589692508,
                   1.9982776154233817, 18.03153585707591,
                   10.011230678539672, 4.75216613975808,
                   25.008201813649492, 2.5332670924014864,
                   50.02561850176654,  1.6675769733794847,
                   100.07087556166645, 1.1441598600267808])[0:-2].reshape([-1, 2])

ref_Cl = np.array([0.5000485844558078, 1.0881064085007515,
                   1.999805681058529,  0.8501158984643172,
                   10.013388298280564, 0.3567970463999039,
                   25.07185800326606,  0.13822085586876326,
                   50.00485844558088,  0.06534806346334243,
                   100.0000000000001,  0.04826051071404796])[0:-2].reshape([-1, 2])

Res = []
Cds = []
Cls = []
err_Cds = []
err_Cls = []

for folder in cases:
    full_folder = prefix + folder
    files = sorted(glob.glob(full_folder + "/pinning_force/sphere*"))
    lines = list(itertools.chain.from_iterable([open(f).readlines() for f in files]))
    
    fx = [ x.split()[2] for x in lines ]
    fz = [ x.split()[4] for x in lines ]
    
    (mx, vx) = mean_err_cut(fx)
    (mz, vz) = mean_err_cut(fz)
    
    m = re.search(r'case_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)__(.*?)_.*?_(.*)', folder.split('/')[-1])
    print(m.groups())
    a, gamma, kbt, power, rho,  r, vel = [ float(v) for v in m.groups() ]
    
    s = pickle.load( open('data/viscosity/visc_' + str(a) + '_' + str(power) + '_backup.pckl', 'rb') )
    visc = s(gamma)

    Res.append(2*r*rho*vel/visc)
    Cds.append(coefficient(mx, rho, vel, r))
    Cls.append(coefficient(mz, rho, vel, r))
    
    err_Cds.append(coefficient(2.0*math.sqrt(vx), rho, vel, r))
    err_Cls.append(coefficient(2.0*math.sqrt(vz), rho, vel, r))

    
print(Cds)
print(Cls)
#Res = [0.5, 2.0236686390532546, 10.118343195266274, 25.295857988165682, 50.591715976331365]
#Cds = [75.613929460608148, 20.350170175353473, 5.1657902601960055, 2.6854762430789747, 1.7323429175589575]
#err_Cds = [7.274614042556217, 3.455479948726347, 0.13351391903959192, 0.020534230923650566, 0.006940364244007037]
#Cls = [1.7683917126204929, 1.0176979864499454, 0.42339109183413848, 0.1522418165592605, 0.070806029418869321]
#err_Cls = [1.6587011544460017, 3.2902631054810696, 0.1301135458279146, 0.022877688503616562, 0.008419711005885155]

pickle.dump((Res, Cds, Cls, err_Cds, err_Cls, ref_Cd, ref_Cl), open('/home/alexeedm/papers/udevicex-cpc-paper/data/sphere_lift/data.pckl', 'wb'))

plt.switch_backend('Qt5Agg')
#set_pgf_backend()
dump_plots(Res, Cds, Cls, err_Cds, err_Cls, ref_Cd, ref_Cl)





