#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 17 11:39:29 2018

@author: alexeedm
"""
import glob
import itertools
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import re
import pickle
import scipy.optimize as scopt
import scipy.integrate as scintegr
import scipy.interpolate as scinterp
import thesis_plot as myplt

from sklearn.gaussian_process import GaussianProcessRegressor
import sklearn.gaussian_process.kernels as kr

def coefficient(frc, rho, u, r, H):
    return frc / (rho * u**2 * (2*r)**4 / H**2)

def pois_square_velocity(x, y, H, dp, mu):
    
    def term(n):
        a = (2*n+1) ** 3;
        s = np.sin((2*n+1)*np.pi*y/H);

        top = np.cosh((2*n+1)*np.pi*x/H);
        bot = np.cosh((2*n+1)*np.pi*H/(2*H));

        return (1-top/bot) * s / a;
    
    nterms = 20
    
    total = 0.0
    for n in range(nterms):
        total += term(n)

    return 4.0*H*H * dp / (np.pi**3 * mu) * total

def pois_square_velocity_gradient(x, y, H, dp, mu):
    
    def term(n):
        a = (2*n+1) ** 3;
        s = np.sin((2*n+1)*np.pi*y/H);

        top = np.cosh((2*n+1)*np.pi*x/H);
        bot = np.cosh((2*n+1)*np.pi*H/(2*H));

        return (1-top/bot) * s / a;
    
    nterms = 20
    
    total = np.zeros((2))
    for n in range(nterms):
        total += term(n)

    return 4.0*H*H * dp / (np.pi**3 * mu) * total


def process_force(raw,  y, z,  rho, u, r, H, f, mu):
    res = []
    for component in raw:
        res.append( coefficient(component, rho, u, r, H) )
        
    return res

def process_rotation(raw,  y, z,  rho, u, r, H, f, mu):
    res = []
    for component in raw:
        res.append( component / (u/H) )
        
    return res

def process_velocity(raw,  y, z,  rho, u, r, H, f, mu):
    dp = f * rho
    
    urel = raw[0] - pois_square_velocity(y,z, H, dp, mu)
    
    Re_p = urel / u#rho * 2*r * urel / mu
    Re_p_err = raw[1] / u#rho * 2*r * raw[1] / mu
    
    return [ Re_p, Re_p_err ]

def mean_err_cut(vals):
    npvals = np.array(vals[20:]).astype(np.float)
    
    m = np.mean(npvals)
    v = np.sqrt( np.var(npvals) / npvals.size )
        
    return m,v

def read_one(fnames, columns):
    
    lines = list(itertools.chain.from_iterable([open(f).readlines() for f in fnames]))

    resv = []
    reserr = []
    for c in columns:
        
        val = []
        for l in lines:
            try:
                t = float( l.split()[1] )
                ##if t > 100.0:
                val += [ l.split()[c] ]
            except:
                print('Reading error!!!')
                continue
            
        (mean, err) = mean_err_cut(val)
        resv += [mean]
        reserr += [err]
        
        if np.isnan(mean):
            print(val)
    
    return resv + reserr

def rotate(v, phi):
    return np.matmul(
            np.array(v).reshape(-1, 2),
            np.array(
                    [[np.cos(phi), -np.sin(phi)],
                     [np.sin(phi),  np.cos(phi)]] )
        ).flatten()

def symmetry_2d(alldata, ry, rz, values, mirror):
    
    if ry == rz:
        if mirror:
            esym = 0.5*(values[0] + values[1])
            fsym = 0.5*(values[2] + values[3])
            entry = np.array([ry, rz,  esym, esym, fsym, fsym])
        else:
            entry = np.array([ry, rz] + values)
        
        for phi in np.linspace(0, 1.5*np.pi, 4):
            if alldata is not None:
                alldata = np.vstack( (alldata, rotate(entry, phi)) )        
            else:
                alldata = rotate(entry, phi)
            
    else:
        e1 = np.array([ry, rz] + values)
        if mirror:
            e2 = np.array([rz, ry,  values[1], values[0], values[3], values[2]])
        else:
            e2 = np.array([rz, ry,  -values[1], -values[0], values[3], values[2]])

        
        for phi in np.linspace(0, 1.5*np.pi, 4):
            if alldata is not None:
                alldata = np.vstack( (alldata, rotate(e1, phi), rotate(e2, phi)) )
            else:
                alldata = np.vstack( (rotate(e1, phi), rotate(e2, phi)) )
                
    return alldata

def symmetry_1d(alldata, ry, rz, values):
    
    entry = np.array([ry, rz])
    
    for phi in np.linspace(0, 1.5*np.pi, 4):
        res = np.hstack( (rotate(entry, phi), values) )
        if alldata is not None:
            alldata = np.vstack( (alldata, res) )        
        else:
            alldata = res
        

    if ry != rz:
        entry = np.array([rz, ry])
        
        for phi in np.linspace(0, 1.5*np.pi, 4):
            res = np.hstack( (rotate(entry, phi), values) )
            alldata = np.vstack( (alldata, res) )        


    return alldata
    
def _read_data(prefix, fname, columns, process, mirror, _1d):
    cases = sorted(glob.glob(prefix))
        
    print(prefix)
    
    rho = 8
    r = 5
    kappa = 0.22
    H = 2*r / kappa
    
    alldata = None
    for case in cases:
        
        lastdir = case.split('/')[-1]
        if re.search(r'\.txt', lastdir):
            continue
        
        print(lastdir)
        
        raw = read_one( sorted(glob.glob(case + '/' + fname + '/*.txt')), columns )
        m = re.search(r'case_(.*?)_(.*?)_(.*?)_.*?__(.*?)_(.*?)_.*?__(.*?)x(.*)', lastdir)
        if m is not None:
            f, lbd, Y, a, gamma, ry, rz = [ float(v) for v in m.groups() ]
        else:
            m = re.search(r'case_(.*?)_(.*?)_.*?__(.*?)_(.*?)_.*?__(.*?)x(.*)', lastdir)
            if m is not None:
                f, rot, a, gamma, ry, rz = [ float(v) for v in m.groups() ]
            else:
                f, rot, a, gamma, ry, rz = [ float( re.search('_' + nm + r'_([^_]+)', lastdir).group(1) )
                                            for nm in ['f', 'rotation', 'a', 'gamma', 'ry', 'rz'] ]
                
        if ry > 0.7 or rz > 0.7:
            continue
        
        s = pickle.load( open('data/viscosity/visc_' + str(a) + '_0.5_backup.pckl', 'rb') )
        mu = s(gamma)
        
        u = 0.3514425374e-1 * H**2 * rho*f / mu
        #print(u)
                
        values = process(raw, ry*H/2, (1+rz)*H/2,  rho, u, r, H, f, mu)
                
        # in case of NaNs set the error to something big
        if np.isnan(values[0]) or np.isnan(values[1]):
            print("NaNs found in this case")
            print(raw)
            continue
        
        if _1d:
            alldata = symmetry_1d(alldata, ry, rz, values)
        else:
            alldata = symmetry_2d(alldata, ry, rz, values, mirror)
            
    
    return np.array(alldata)
    
def read_force_data(prefix):
    return  _read_data(prefix, 'pinning_force', [3, 4], process_force, True, False)

def read_rotation_data(prefix):
    return  _read_data(prefix, 'pos', [13, 14], process_rotation, False, False)

def read_velocity_data(prefix):
    return  _read_data(prefix, 'pos', [9], process_velocity, False, True)


def val_along_curve(gpY, gpZ, coo, normal=True):
    
    vy, sy = gpY.predict( np.atleast_2d(coo), return_std=True )
    vz, sz = gpZ.predict( np.atleast_2d(coo), return_std=True )
    
    res = np.empty(vy.shape)
    res[0] = 0.0
    res[-1] = 0.0
    
    err = np.empty(vy.shape)
    err[0] = 0.0
    err[-1] = 0.0
    
    
    for i in range(1, res.shape[0] - 1):
        direction = 0.5 * ( (coo[i] - coo[i-1]) + (coo[i+1] - coo[i]) )
        direction /= np.linalg.norm(direction)        
        vector = np.array([vy[i], vz[i]])


        if normal:
            res[i] = np.dot(vector, direction )
        else:
            res[i] = np.linalg.norm( vector - np.dot( vector, direction ) * direction )

        err[i] = np.sqrt( sy[i]**2 + sz[i]**2 )
        
    return res, err

def fit_gaussian(x, y, err):
    
#    kernel = kr.RBF(length_scale=10.0)
    #kernel = kr.ConstantKernel(1) * kr.Matern(length_scale=0.3, nu=2.5)
#    kernel = kr.Matern(length_scale=0.3, nu=2.5)
    kernel = kr.RBF(length_scale=0.3)
    gp = GaussianProcessRegressor(kernel=kernel, alpha=err**2, n_restarts_optimizer=10)
    
    gp.fit(x, y)
    print(gp.kernel_)
    
    return gp

def gaussian_fit2d(data, columns=[2,3,4,5]):
    
    coos = data[:, 0:2]
    valy, valz,  ey, ez = [ data[:, columns[i]] for i in range(4) ]

    return ( fit_gaussian(coos, valy, ey), fit_gaussian(coos, valz, ez) )

def draw_quiver(data):
    
    ry = data[:,0].copy()
    rz = data[:,1].copy()
    Fy = data[:,2].copy()
    Fz = data[:,3].copy()

    
    lengths = np.sqrt(Fy*Fy + Fz*Fz)
    Fy = Fy / lengths
    Fz = Fz / lengths
    
    norm = matplotlib.colors.LogNorm()
    norm.autoscale(lengths)
    cm = plt.cm.rainbow
    
    sm = matplotlib.cm.ScalarMappable(cmap=cm, norm=norm)
    sm.set_array([])
    
    #plt.colorbar(sm)
    plt.quiver(ry, rz, Fy, Fz, color=cm(norm(lengths)), width=0.006, headwidth=4, scale=20)
#    plt.quiver(ry, rz, _Fy, _Fz, minlength=0)#, scale=1000, width=0.004)
    
    return norm, cm

    
def draw_gp(grid, gpY, gpZ, norm, cm):
    
    Fy = gpY.predict(grid)
    Fz = gpZ.predict(grid)
        
    ry = grid[:,0]
    rz = grid[:,1]
    
    #print F

    lengths = np.sqrt(Fy*Fy + Fz*Fz)
    Fy = Fy / lengths
    Fz = Fz / lengths
    
    plt.quiver(ry, rz, Fy, Fz, alpha=0.5, color=cm(norm(lengths)))
#    plt.colorbar(sm)
    
def curve_normal(curve):
    # https://stackoverflow.com/questions/28269379/curve-curvature-in-numpy
    
    dx_dt = np.gradient(curve[:, 0])
    dy_dt = np.gradient(curve[:, 1])
    velocity = np.array([ [dx_dt[i], dy_dt[i]] for i in range(dx_dt.size)])
    
    ds_dt = np.sqrt(dx_dt * dx_dt + dy_dt * dy_dt)
    
    tangent = np.array([1/ds_dt] * 2).transpose() * velocity
    
    tangent_x = tangent[:, 0]
    tangent_y = tangent[:, 1]

    deriv_tangent_x = np.gradient(tangent_x)
    deriv_tangent_y = np.gradient(tangent_y)
    
    dT_dt = np.array([ [deriv_tangent_x[i], deriv_tangent_y[i]] for i in range(deriv_tangent_x.size)])
    
    length_dT_dt = np.sqrt(deriv_tangent_x * deriv_tangent_x + deriv_tangent_y * deriv_tangent_y)
    
    normal = np.array([1/length_dT_dt] * 2).transpose() * dT_dt
    
    return normal

def point_in_triangle2(A,B,C,P):
    v0 = C-A
    v1 = B-A
    v2 = P-A
    cross = lambda u,v: u[0]*v[1]-u[1]*v[0]
    u = cross(v2,v0)
    v = cross(v1,v2)
    d = cross(v1,v0)
    if d<0:
        u,v,d = -u,-v,-d
    return u>=0 and v>=0 and (u+v) <= d

def find_equilibria(gpx, gpy, lo, hi, tolerance):
    
    # http://sci.utah.edu/~hbhatia/pubs/2014_TopoInVis_robustCP.pdf
    
    npts = 50
    
    x = np.linspace(lo[0], hi[0], npts)
    y = np.linspace(lo[1], hi[1], npts)
    X,Y = np.meshgrid(x,y)
    grid = np.array([X.flatten(),Y.flatten()]).T
        
    vx = gpx.predict(grid).reshape((npts, npts, -1))
    vy = gpy.predict(grid).reshape((npts, npts, -1))
        
    h = (hi - lo) / (npts-1)
    
    coarse = []
    
    for i in range(npts-1):
        for j in range(npts-1):
            
            a = np.array( [vx[i, j], vy[i, j]] ).flatten()
            b = np.array( [vx[i+1, j], vy[i+1, j]] ).flatten()
            c = np.array( [vx[i, j+1], vy[i, j+1]] ).flatten()
            d = np.array( [vx[i+1, j+1], vy[i+1, j+1]] ).flatten()
            
            test1 = point_in_triangle2(a, b, c, [0.0,0.0])
            test2 = point_in_triangle2(c, b, d, [0.0,0.0])
            
            if test1:
                coarse.append( lo + h*np.array([j,i]) + h/3.0 )
                
            if test2:
                coarse.append( lo + h*np.array([j,i]) + 2.0*h/3.0 )
    
    
    if h[0] > tolerance or h[1] > tolerance:
        
        fine = []
        for pt in coarse:
            fine += find_equilibria(gpx, gpy, pt-h, pt+h, tolerance)
            
        return fine
    
    else:
        return coarse


def streamline(gpY, gpZ, start):
    
    func = lambda t, x : np.array([ gpY.predict(np.atleast_2d(x)), gpZ.predict(np.atleast_2d(x)) ]).flatten()
    
    sol = scintegr.solve_ivp(func, t_span=[0, 50], y0=start, atol=1e-10, rtol=1e-7)
    
    return sol.t, sol.y

def mindist(targets, pt):
    
    # with symmetric copies
    dist = 1000.0;
    for t in targets:
        dist = min(np.linalg.norm(t - pt), dist)
        dist = min(np.linalg.norm(t*np.array([1.0, -1.0]) - pt), dist)
        dist = min(np.linalg.norm(np.array([t[1], t[0]]) - pt), dist)
        
    return dist

def separatrix_cloud(gpY, gpZ):
    
    r = 0.005
    
    print("Looking for critical points")
    
    raw = np.array( find_equilibria(gpY, gpZ, np.array([-0.1, -0.1]), np.array([0.7, 0.7]), 1e-4) )
        
    # do a correction
    multiple = raw[ (raw[:,0] - raw[:,1] > -0.1) ]

    for i in range(multiple.shape[0]):
        multiple[i,:] = [ np.max(multiple[i,:]), np.min(multiple[i,:]) ]
            
    multiple = multiple[ ((multiple[:,0] > 0.1) | (multiple[:,0] > 0.1)) ]
    multiple = multiple[ multiple[:,0].argsort(), : ]    
    
    equilibria = np.array(multiple[0])
    for i in range(1, multiple.shape[0]):
        diff = np.linalg.norm(multiple[i] - multiple[i-1])
        
        if diff > r:
            equilibria = np.vstack((equilibria, multiple[i]))
    
    print("Equilibrium points identified:")
    print(equilibria)

    points = np.empty((2, 0))
    

    for eq in equilibria:
        print("Shooting from point ", eq)
        for phi in np.linspace(0, 2*np.pi, 10):
            print("    phi = ", phi)
            start = r*np.array([ np.sin(phi), np.cos(phi) ]) + eq
            t, y = streamline(gpY, gpZ, start)
            points = np.hstack((points, y))

            d = mindist(equilibria, y[:,-1])
            tries=0
            while d > r and tries < 20:
                tries += 1
                print("    restarting from ", y[:,-1])
                t, y = streamline(gpY, gpZ, y[:,-1])
                points = np.hstack((points, y))
                d = mindist(equilibria, y[:,-1])
                
        print("")
            
    
    return np.atleast_2d(equilibria), np.atleast_2d(points)

def separatrix(points, resolution):
    
    phi = np.arctan2(points[1, :], points[0, :])    
    
    sx = scinterp.Rbf(phi, points[0], smooth=200.0)
    sy = scinterp.Rbf(phi, points[1], smooth=200.0)
    
    x = np.linspace(0, np.pi / 4.0, resolution)
    sep = np.vstack( (sx(x), sy(x)) ).T
    
    lengths = np.empty(sep.shape[0])
    lengths[0] = 0.0
    for i in range(1, sep.shape[0]):
        lengths[i] = lengths[i-1] + np.sqrt( np.dot(sep[i-1] - sep[i], sep[i-1] - sep[i]) )
        
    return lengths, sep

def draw_value_along_curve(t, f, sigma, limits, fname, title, save):
    
    fig = plt.figure()
    plt.plot(t / np.max(t), f, color='black')
    plt.fill_between(t / np.max(t), f - sigma, f + sigma, color='red', alpha=0.5, linewidth=0)
    #plt.title(title)
    
    plt.axes().set_ylim(limits)
    
    plt.ylabel(r'$C_l^{||}$')
    plt.xlabel(r'$t$')
    
    myplt.set_font_sizes(plt.gca())
    myplt.make_grid(plt.gca())
    
    if save:
        myplt.save_figure(fig, 3.5, fname)
        #fig.savefig(fname, bbox_inches='tight')
        plt.close(fig)
    else:
        plt.show()
    
def draw_cross_section(alldata, gpY, gpZ, sep, equilibria, points, title, fname, save, rotation=True):
    
    fig = plt.figure()

    #plt.title(title)
    plt.xlabel('$y / (H/2)$')
    plt.ylabel('$z / (H/2)$')
    myplt.set_font_sizes(plt.gca())

    plt.axes().set_xlim([-0.02, 0.72])
    plt.axes().set_ylim([-0.02, 0.72])

    plt.axes().set_aspect('equal', 'box', anchor='SW')
    
    
    norm, cmap = draw_quiver(alldata)
    
    x = np.linspace(0, 0.7, 40)
    y = np.linspace(0, 0.7, 40)
    X,Y = np.meshgrid(x,y)
    grid = np.array([X.flatten(),Y.flatten()]).T
    #draw_gp(grid, gpY, gpZ, norm, cmap)
    
    plt.plot( sep[:, 0], sep[:, 1], color='grey', linewidth=2 )
    
    if rotation:
        plt.scatter( sep[:,0][0], sep[:,1][0], color='C3', linewidth=1.5, s=25.0, zorder=5)
        plt.scatter( sep[:,0][-1], sep[:,1][-1], facecolors='none', edgecolors='C3', linewidth=1.5, s=25.0, zorder=5)
#    plt.scatter( points[0,:], points[1,:], color='C3', s=5.0, zorder=5)
    
    if save:
        myplt.save_figure(fig, 4.5, fname)
        #fig.savefig(fname, bbox_inches='tight')
        plt.close(fig)
    else:
        plt.show()
    
    return fig
    
def read_cache(func, folder, fname, override_cache=False):
    try:
        res = pickle.load(open(folder + fname + '.pckl', 'rb'))
        success = True
    except:
        success = False
    
    if not success or override_cache:
        res = func()
        pickle.dump(res, open(folder + fname + '.pckl', 'wb'))
    else:
        print('Successfully got cached values')
        
    return res

#%%
    
override_cache = False
generate = False
save_refine = False
save_figures = True

pickle_folder = 'data/focusing/'
figure_folder = 'square/'

#if save_figures:
#    myplt.set_pgf_backend()
#else:
myplt.set_qt_backend()
    
kappa = 0.22

fint = None
for Re in [50, 100, 200]:
    for lbd in [1.0, 5.0, 25.0]:
        for Ca in [1.0, 0.1, 0.01]:
                                    
            folder = '/home/alexeedm/extern/daint/project/alexeedm/focusing_square_massive/casenew_' + str(int(Re)) + '_' + str(kappa) + '/'
            case = 'case_*_' + str(lbd) + '_' + str(Ca) + '_' + str(kappa) + '__160_*_3.0__*'
            
            fname = 'Re_' + str(Re) + '_kappa_' + str(kappa) + '__lambda_' + str(lbd) + '_Ca_' + str(Ca)
            title = r'$Re = ' + str(Re) + r',\kappa = ' + str(kappa) + r', \lambda = ' + str(lbd) + r', Ca = ' + str(Ca) + r'$'
            

            print('Reading force values')
            force_data    = read_cache( lambda : read_force_data(folder + case),  pickle_folder, 'forcedata_' + fname, override_cache)
                
            #%%
            print('Fitting forces')
            fy, fz = read_cache( lambda : gaussian_fit2d(force_data), pickle_folder, 'force_'+fname, generate )
            
            print('Finding separatrix')
            equilibria, points = read_cache( lambda : separatrix_cloud(fy, fz), pickle_folder, 'equilibria_'+fname, generate )
            t, sep = read_cache( lambda : separatrix(points, 106), pickle_folder, 'separatrix_'+fname, generate )
    
    #%%
            if Re == 50:
                flimits = [-0.05, 0.02]
                wlimits = [-0.05, 0.5]
                ulimits = [-0.9, -0.75]
            if Re == 100:
                flimits = [-0.08, 0.02]
            if Re == 200:
                flimits = [-0.1, 0.02]
                wlimits = [-0.05, 1.0]
                ulimits = [-3.75, -1.5]
    
                        
            f, fsigma = val_along_curve(fy, fz, sep)
            
            if fint is None:
                fint = [[Re, lbd, Ca, scintegr.trapz(f, sep[:,1]), scintegr.trapz(f+fsigma, sep[:,1]), scintegr.trapz(f-fsigma, sep[:,1]) ], ]
            else:
                fint.append([Re, lbd, Ca, scintegr.trapz(f, sep[:,1]), scintegr.trapz(f+fsigma, sep[:,1]), scintegr.trapz(f-fsigma, sep[:,1]) ]) 
           
            
            #draw_value_along_curve(sep[:,1], f, fsigma, flimits, figure_folder + 'force_' + fname + '.pdf', title, save_figures)
            #fig = draw_cross_section(force_data, fy, fz, sep, equilibria, points, title,
            #                         figure_folder + 'cross_' + fname + '.pdf', save_figures)
            
            #u = alsdjflaks
            
##%%
#            normals = curve_normal(sep)
#            
#            if Re == 50 or Re == 100:
#                every = 15
#            if Re == 200:
#                every = 21
#                
#            coarse_orbit   = sep    [::every]
#            coarse_normals = normals[::every]
#                
#            h = 0.02
#            refname = folder+case+'refine.txt'
#            refname = re.sub(r'\*', 'XXX', fname)
#            f = open(refname, 'w')
#            for p in np.linspace(-h, h, 4):
#                coo = coarse_orbit + coarse_normals*p
#                plt.scatter( coo[:,0], coo[:,1], color='black' )
#                
#                for c in coo:
#                    f.write('%f  %f\n' % (c[0], c[1]))
#            
#            f.close()
#        
#            fig.savefig('/home/alexeedm/udevicex/media/square/' + 'refine__' + fname + '.pdf', bbox_inches='tight')
#            plt.close(fig)
    
#            plt.show()
#        
#                    
#            plt.plot(sep[:,0], sep[:,1])
#            plt.quiver(sep[:,0], sep[:,1], normals[:,0], normals[:,1])
#            plt.show()            

print(fint)
pickle.dump(fint, open(pickle_folder + 'energies_soft_square.pckl', 'wb'))

a = kdjsfhakjdh
#%%


kappa = 0.22
for Re in [50, 100, 200]:
    for rot in [0, 1]:
        
                
#        if rot == 1:
#            continue
                
#%%
        root_scratch     = '/home/alexeedm/extern/daint/scratch/focusing_square_rigid_massive/'
        root_scratch1600 = '/home/alexeedm/extern/daint/scratch1600/focusing_square_rigid_massive/'
        root_project = '/home/alexeedm/extern/daint/project/alexeedm/focusing_square_rigid_massive/'
        folder = 'case_' + str(int(Re)) + '_' + str(kappa) + '/'
        case = 'case_*_' + str(rot) + '_' + str(kappa) + '__160_*_3.0__*'
        
        newfolder = '/newcode/case___Re_' + str(int(Re)) + '__kappa_' + str(kappa) + '*' + '_rotation_' + str(int(rot)) + '*'

        
        fname = 'Re_' + str(Re) + '_kappa_' + str(kappa) + '__rotation_' + str(rot)
        
        if rot == 1:
            title = r'$Re = ' + str(Re) + r',\kappa = ' + str(kappa) + r'$, inhibited rotation'
        else:
            title = r'$Re = ' + str(Re) + r',\kappa = ' + str(kappa) + r'$, free rotation'
            
        
        def read_old_new(func):
            return np.vstack( (func(root_project + folder+case), func(root_scratch + newfolder)) )
        
        print('Reading force values')
        force_data    = read_cache( lambda : read_old_new(read_force_data),
                                   pickle_folder, 'forcedata_' + fname, override_cache)
            
        print('Reading rotation values')
        rotation_data = read_cache( lambda : read_old_new(read_rotation_data),
                                   pickle_folder, 'rotationdata_' + fname, override_cache)   
    
        print('Reading velocity values')
        velocity_data = read_cache( lambda : read_old_new(read_velocity_data),
                                   pickle_folder, 'velocitydata_' + fname, override_cache)   
            
        #%%
        print('Fitting forces')
        fy, fz = read_cache( lambda : gaussian_fit2d(force_data), pickle_folder, 'force_'+fname, generate )

        print('Fitting rotations')
        rotation_data[:, 4:] *= 10000
        omegay, omegaz = read_cache( lambda : gaussian_fit2d(rotation_data), pickle_folder, 'omega_'+fname, generate )
    
        print('Fitting slip velocity')
        slip = read_cache( lambda : fit_gaussian(velocity_data[:,0:2], velocity_data[:,2], 1e4*velocity_data[:,3]),
                           pickle_folder, 'slip_'+fname, generate )
        
        print('Finding separatrix')
        equilibria, points = read_cache( lambda : separatrix_cloud(fy, fz), pickle_folder, 'equilibria_'+fname, generate )
        t, sep = read_cache( lambda : separatrix(points, 106), pickle_folder, 'separatrix_'+fname, generate )

#%%
        if Re == 50:
            flimits = [-0.05, 0.02]
            wlimits = [-0.05, 0.5]
            ulimits = [-0.9, -0.75]
        if Re == 100:
            flimits = [-0.08, 0.02]
        if Re == 200:
            flimits = [-0.1, 0.02]
            wlimits = [-0.05, 1.0]
            ulimits = [-3.75, -1.5]

                    
        f, fsigma = val_along_curve(fy, fz, sep)
        w, wsigma = val_along_curve(omegay, omegaz, sep, normal=False)
        u, usigma = slip.predict(np.atleast_2d(sep), return_std=True)
       
        
        draw_value_along_curve(sep[:,1], f, fsigma, flimits, figure_folder + 'force_' + fname + '.pdf', title, save_figures)
#        draw_value_along_curve(t, w, wsigma, wlimits, figure_folder + 'omega_' + fname + '.pdf', title, save_figures)
#        draw_value_along_curve(t, u, usigma, ulimits, figure_folder + 'slip_'  + fname + '.pdf', title, save_figures)
      
#%%
        r = 5
        H = 2*r / kappa
#        fig = plt.figure()
#        
#        cl = f
#        
#        def norm(x):
#            return np.abs(x) / np.max(np.abs(x))
##        plt.plot(t, np.abs(f) / np.max(np.abs(f)))
##        plt.plot(t, np.abs(w) / np.max(np.abs(w)))
##        plt.plot(t, np.abs(u) / np.max(np.abs(u)))
#        
        #plt.plot(t, f / w / u)
#        
#        plt.plot(t, norm(f / (u)**2))
#        plt.plot(t, norm(f))
#        plt.plot(t, norm(w / u))
#        plt.title(title)
        
        sigma = np.abs(fsigma/w / (u))
#        plt.fill_between(-u, cl - sigma, cl + sigma, color='red', alpha=0.5, linewidth=0)
#        plt.title(title)
#        plt.ylim([-0.05, 0.25])
        
        #plt.show()
        #%%
                   
        fig = draw_cross_section(force_data, fy, fz, sep, equilibria, points, title,
                                 figure_folder + 'cross_' + fname + '.pdf', save_figures,
                                 True if rot==0 else False)
        
#        print(sep[-1])
#        refname = root_scratch1600 + '/newcode/' + 'free_' + str(int(Re)) + '_' + str(int(rot)) + '.txt'
#        f = open(refname, 'w')
#        for i in range(5):
#            f.write('%f  %f    %f  %f\n' % (sep[-1,0], sep[-1,1], 0,0))
#        f.close()
#        
#        fig = draw_cross_section(rotation_data, omegay, omegaz, sep, equilibria, points, title,
#                         figure_folder + 'vprofile_' + fname + '.pdf', save_figures)
        
#        rho = 8
#        r = 5
#        mu = 6.36360435
#        zeros = np.zeros( (velocity_data.shape[0], 2) )
#        velocity_data[:, 2:] /= (rho * 2*r / mu)
#        fig = draw_cross_section( np.hstack( (velocity_data, zeros) ), slip, slip, sep, equilibria, points, title, 
#                                 figure_folder + 'velocity_' + fname + '.pdf', save_figures)
        
##%%
        normals = curve_normal(sep)
        
        #a = dafdfa
        
        if save_refine:
            
            r = 5.0
            H = 2*r/kappa
            u = 3.5
            
#            if Re == 50 or Re == 100:
#                every = 15
#            if Re == 200:
#                every = 21
            
            every = 4
                
            coarse_orbit   = sep    [::every]
            coarse_normals = normals[::every]
            coarse_rotations = w[::every]
            
            corrected_rotations =  np.vstack( (omegay.predict( np.atleast_2d(coarse_orbit) ),
                                               omegaz.predict( np.atleast_2d(coarse_orbit) )) ).T
            
            corrected_rotations -= np.sum(np.multiply(coarse_normals, corrected_rotations), axis=1)[:, np.newaxis] * coarse_normals #coarse_rotations[:, np.newaxis]*coarse_normals
            corrected_rotations *= 0.0
#            fig=plt.figure()
#            plt.plot(sep[:,0], sep[:,1])
#            plt.quiver(coarse_orbit[:,0], coarse_orbit[:,1], corrected_rotations[:,0], corrected_rotations[:,1])
#            plt.axes().set_aspect('equal', 'datalim')
#            plt.show()
            
        
            h = 0.02
            refname = root_scratch1600 + '/newcode/' + 'test_0rotations__' + str(int(Re)) + '_' + str(int(rot)) + '.txt'
            print('Saving refinement data to ' + refname)
            f = open(refname, 'w')
            
            for c,r  in zip(coarse_orbit, corrected_rotations):
                f.write('%f  %f    %f  %f\n' % (c[0], c[1], r[0]*u/H, r[1]*u/H))
                    
#            for p in np.linspace(-h, h, 4):
#                coo = coarse_orbit + coarse_normals*p
#                plt.scatter( coo[:,0], coo[:,1], color='black' )
#                
#                for c in coo:
#                    f.write('%f  %f\n' % (c[0], c[1]))
            
            f.close()
    
        #fig.savefig('/home/alexeedm/udevicex/media/square/' + 'refine__' + fname + '.pdf', bbox_inches='tight')
        #plt.close(fig)
        #plt.show()
    
                

            
            
            

