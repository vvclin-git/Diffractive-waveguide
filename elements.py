#%%
import numpy as np
import matplotlib.path as mpath
from copy import deepcopy

class Material:
    def __init__(self, name, coefficient):
        self.name = name
        self.coefficient = coefficient

    def sellmeier_equation(self,b1,b2,b3,c1,c2,c3,wavelength):
        square_n = 1+b1*wavelength**2/(wavelength**2-c1)+b2*wavelength**2/(wavelength**2-c2)+b3*wavelength**2/(wavelength**2-c3)
        return np.sqrt(square_n)
    
    def __call__(self,wavelength):
        if len(self.coefficient) > 1:
            return self.sellmeier_equation(*self.coefficient,wavelength)
        else: # ideal (non-dispersive) material
            return self.coefficient

class Rays_convert_tool:
    def __init__(self,material = Material('Air',[0,0,0,0,0,0]), 
                 input_format = 'hv',
                 output_format = 'k'):
        '''format: 
                hv: horizontal,vertical
                sp: spherical coord
                k: k_vector
        '''
        self.index = material
        self.input_format = input_format
        self.output_format = output_format

    def convert(self, ray):
        ray = np.asarray(ray)
        index = self.index(ray[:,0])
        if self.input_format =='hv':
            h,v,z = np.deg2rad(ray[:,1:4]).T
            z = np.where(z>=0,1,-1)
            kx = index*np.tan(h)/np.sqrt(1+np.tan(h)**2+np.tan(v)**2)
            ky = index*np.tan(v)/np.sqrt(1+np.tan(h)**2+np.tan(v)**2)
            kz = z*np.sqrt(index**2-kx**2-ky**2)
            
        elif self.input_format == 'sp':
            theta,phi = np.deg2rad(ray[:,1:3]).T
            kx = index*np.sin(theta)*np.cos(phi)
            ky = index*np.sin(theta)*np.sin(phi)
            kz = index*np.cos(theta)
        
        elif self.input_format == 'k':
            index = np.sqrt(np.sum(ray[:,1:4]**2,axis = 1))
            kx,ky,kz = ray[:,1:4].T
            
        else:
            print('format error')
            return None

        ray_output = deepcopy(ray)
        if self.output_format =='hv':
            ray_output[:,1] = np.rad2deg(np.arctan(kx/np.sqrt(index**2-kx**2-ky**2)))
            ray_output[:,2] = np.rad2deg(np.arctan(ky/np.sqrt(index**2-kx**2-ky**2)))
            ray_output[:,3] = np.where(kz>0,1,-1)
            return ray_output

        elif self.output_format =='sp':
            ray_output[:,1] = np.rad2deg(np.arcsin(np.sqrt(kx**2+ky**2)/index))
            ray_output[:,2] = np.rad2deg(np.arctan2(ky,kx))
            ray_output[:,3] = np.where(kz>0,1,-1)
            return ray_output
             
        elif self.output_format =='k':
            ray_output[:,1] = kx
            ray_output[:,2] = ky
            ray_output[:,3] = kz
            return ray_output
        else:
            print('format error')
            return None
        
class Source:
    def __init__(self,fov,wavelength_list,
                 fov_grid = (5,5),spatial_grid = (1,1), shape = [], z = 0, direct = 1):
        self.name = 'source'
        self.fov = np.asarray(fov)
        self.wavelength_list = np.asarray(wavelength_list)
        self.fgrid = np.asarray(fov_grid)
        self.sgrid = np.asarray(spatial_grid)
        self.z = z

        x,y,h,v,w = np.meshgrid(np.linspace(0,1,self.sgrid[0]),
                                np.linspace(0,1,self.sgrid[1]),
                                np.linspace(*self.fov[:2],self.fgrid[0]),
                                np.linspace(*self.fov[2:],self.fgrid[1]),
                                self.wavelength_list)
        self.field = np.vstack((w.reshape(-1),
                                h.reshape(-1),
                                v.reshape(-1), 
                                direct*np.ones_like(h.reshape(-1)),
                                x.reshape(-1),
                                y.reshape(-1),
                                z*np.ones_like(h.reshape(-1)))).T
        
        if len(shape) != 0:
            shape = np.asarray(shape)
            self.polygon = mpath.Path.circle(shape[:2], shape[2]) if shape.ndim == 1 else mpath.Path(shape)

    def launch(self):
        tool = Rays_convert_tool()
        self.rays = deepcopy(self.field)
        if hasattr(self,'polygon'):
            box = np.vstack((self.polygon.vertices.min(axis = 0),
                             self.polygon.vertices.max(axis = 0))).T
            wx,wy = np.max(box,axis = 1) - np.min(box,axis = 1)
            xc,yc = (np.max(box,axis = 1) + np.min(box,axis = 1))/2
            self.rays[:,4] = wx*self.rays[:,4]- wx/2 + xc
            self.rays[:,5] = wy*self.rays[:,5]- wy/2 + yc
            self.rays[:,4:7] = np.round(self.rays[:,4:7],4)
            if wx!=0 and wy != 0 and np.all(self.sgrid != [1,1]):
                mask = self.polygon.contains_points(self.rays[:,4:6], radius=1E-3)
                self.rays = self.rays[mask]
        return tool.convert(self.rays)
        
class Grating:
    def __init__(self, name, periods, index,
                 mode = 'All',
                 diffract_order = { 1:[[ 1,-1,0],[ 1,0,0],[ 1,1,0],
                                       [-1,-1,0],[-1,0,0],[-1,1,0]],
                                   -1:[[ 1,-1,0],[ 1,0,0],[ 1,1,0],
                                       [-1,-1,0],[-1,0,0],[-1,1,0]]}):
        ''' 
        # periods
        'periods': [[period, grating vector]]
        period: grating pitch (unit µm)
        grating vector: the angle between grating vector and k_x axis (±180° or 0°-360°)

        # index
        [Material_1,material_2]
        if the ray's direction is positive, the ray propagates from Material_1 to Material_2
        if the ray's direction is negative, the ray propagates from Material_2 to Material_1
        
        # diffract_order
        {in-direct:[[out-direct,m_order,n_order]]}
        in-direct:  +z=1, -z=-1
        out-direct: +z=1, -z=-1
        if in-direct = out-direct, diffractive mode is transmission mode
        if in-direct != out-direct, diffractive mode is reflection mode
        
        # mode
        All: (default) Calculate all diffraction behavior if it is set in 'diffract_order'.
        T&TIR: Only calculate T-order diffraction behavior unless the R-order diffraction behavior is within the TIR region..
        '''
        self.name = name
        self.index = index
        self.periods = np.asarray(periods)
        self.diffract_order = diffract_order
        self.mode = mode

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name == 'periods':
            if self.periods.shape != (2,2):
                self.periods = np.vstack((self.periods.reshape((1,2)),[np.inf,0]))
            g_phi = np.deg2rad(self.periods[:,1])
            self.g_vectors = (1/self.periods[:,0]*np.array([np.cos(g_phi),np.sin(g_phi)])).T

    def launched(self, k_in):
        #k_in: [[wavelength,kx,ky,kz,x,y,z]]
        k_out = []
        for in_direct in self.diffract_order.keys():
            kray = deepcopy(k_in[np.where(k_in[:,3]>0,1,-1) == in_direct])
            if kray.size != 0:
                diff_order = np.asarray(self.diffract_order[in_direct])
                order_gv = diff_order[:,-2:] @ self.g_vectors
                kray,order_gv,out_direct= (np.repeat(kray,len(order_gv),axis = 0),
                                          np.tile(order_gv,(len(kray),1)),
                                          np.tile(diff_order[:,0],(len(kray))))
                
                if self.mode == 'T&TIR':
                    TIR = (kray[:,1]**2+kray[:,2]**2) >= 1
                    Transmission = out_direct == in_direct
                    
                n_out = np.where(out_direct>0,self.index[1](kray[:,0]),self.index[0](kray[:,0]))
                kray[:,1:3] += kray[:,0:1]*order_gv
                k2xy = kray[:,1]**2+kray[:,2]**2
                k2z = n_out**2-k2xy
                exist = k2z>0
                if self.mode == 'T&TIR':
                    exist[np.all([~TIR,~Transmission],axis = 0)] = False 
                kray[exist,3] = np.where(out_direct[exist]>0,1,-1)*np.sqrt(k2z[exist])
                k_out += [kray[exist]]
        k_out = np.asarray(k_out).reshape(-1,k_in.shape[1])
        k_out = np.unique(k_out,axis = 0)
        return k_out
    
    def launched_k(self,k_in,order,material_i):
        kray = deepcopy(k_in[:,:4])
        diff_order = np.asarray(order)[np.newaxis]
        order_gv = diff_order[:,-2:] @ self.g_vectors
        kray,order_gv= (np.repeat(kray,len(order_gv),axis = 0),
                        np.tile(order_gv,(len(kray),1)))
        
        n_out = self.index[material_i](kray[:,0])
        kray[:,1:3] += kray[:,0:1]*order_gv
        k2xy = kray[:,1]**2+kray[:,2]**2
        k2z = n_out**2-k2xy
        with np.errstate(invalid='ignore'):
            kray[~np.isnan(kray[:,3]),3] = np.sqrt(k2z[~np.isnan(kray[:,3])])
        if material_i == 1:
            kray[k2xy<=1,3] = np.nan
        return kray#np.unique(kray,axis = 0)
        

class Fresnel_loss:
    def __init__(self, name, index):
        self.name = name
        self.index = index

    # def _fresnel_k(self,n_in,n_out,k_in):
    #     kx,ky,kz = k_in.astype(complex).T
    #     kz = np.abs(kz)
    #     SQRT = np.sqrt(n_out**2-(kx**2+ky**2))
    #     rs = (kz-SQRT)/(kz+SQRT)
    #     rp = (-n_out**2*kz+n_in**2*SQRT)/(n_out**2*kz+n_in**2*SQRT)
    #     ts = 2*kz/(kz+SQRT)
    #     tp = 2*n_out*n_in*kz/(n_out**2*kz+n_in**2*SQRT)
    #     zero = np.zeros_like(rp)
    #     r_matrix = np.array([[-rp,zero],[zero,rs]])
    #     t_matrix = np.array([[ tp,zero],[zero,ts]])
    #     return np.hstack((r_matrix,t_matrix)).T.reshape((-1,2,2,2))

    def launched(self,k_in):
        n_out = np.where(k_in[:,3]>0,self.index[1](k_in[:,0]),self.index[0](k_in[:,0]))
        n_in = np.where(k_in[:,3]>0,self.index[0](k_in[:,0]),self.index[1](k_in[:,0]))
        Tkz2 = n_out**2-(k_in[:,1]**2+k_in[:,2]**2)
        Rkz2 = n_in**2-(k_in[:,1]**2+k_in[:,2]**2)
        Rk_out, Tk_out = k_in[Tkz2<0], k_in[Tkz2>0]
        Tk_out[:,3] = (np.where(k_in[:,3]>0,1,-1)[Tkz2>0]*np.sqrt(Tkz2[Tkz2>0]))
        Rk_out[:,3] = (-np.where(k_in[:,3]>0,1,-1)[Tkz2<0]*np.sqrt(Rkz2[Tkz2<0]))
        k_out = np.vstack((Rk_out,Tk_out))
        k_out = np.unique(k_out,axis = 0)
        return k_out

class ColorFilter:
    def __init__(self,name,stop_wavelength):
        self.name = name
        self.stop_wavelength = stop_wavelength

    def launched(self, k_in):
        if k_in.size>0:
            k_out = k_in[k_in[:,0]!=self.stop_wavelength]
        else:
            k_out = np.empty((0, k_in.shape[1]))
        return k_out

class Receiver:
    def __init__(self,name):
        self.name = name
        self.store = []

    def launched(self, k_in):
        if k_in.size>0:
            self.store += [k_in]
        return np.empty((0, k_in.shape[1]))

# %%
