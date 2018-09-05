import pickle
from scipy import interpolate
from scipy.optimize import fsolve
import numpy as np

def params(Re, kappa, s):
	
	rho = 8.0
	r = 5.0
	R = r / kappa
	
	c = np.sqrt(0.1 * 80 * 8)
	M = 0.206
	uavg = c*M/(2*kappa)
	
	uavg = 3.9
	
	mu = 2*R*uavg*rho / Re
	#print mu
	
	gamma = fsolve(lambda g : s(g)-mu, mu)[0]	
	f = 8.0*uavg*mu / (rho * R**2)
	
	return gamma, f

#s = pickle.load(open('../data/visc_80.0_0.5_backup.pckl', 'rb'))
s = pickle.load(open('../data/visc_160.0_0.5_backup.pckl', 'rb'))


for kappa in [0.15, 0.22, 0.3]:
	for Re in [50.0, 100.0, 200.0]:
		gamma, f = params(Re, kappa, s)
		print '"160 %7.4f 3.0  %.5f"' % (gamma, f)
