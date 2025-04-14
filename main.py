#%%
from elements import *
from system import *
import time
#%%
Air_coefficient = [0,0,0,0,0,0]
LASF46B_coefficient = [2.17988922,0.306495184,1.56882437,0.012580538,0.056719137,105.316538]    #1.9
Air = Material('Air',Air_coefficient)
LASF46B = Material('LASF46B',LASF46B_coefficient)

kdom = K_domain(LASF46B)
kdom.set_source({'fov':[-20,20,-15,15],
                 'wavelength_list':[0.525],
                 'fov_grid':(11,11)})
#Doe1
kdom.add_element(Grating,{'name': 'G1',
                          'periods': [[0.3795,11]]})
#Doe2
kdom.add_element(Grating,{'name': 'G2',
                          'periods': [[0.2772,-122.2]]})
#Doe3
kdom.add_element(Grating,{'name': 'G3',
                          'periods': [[0.3795,104.6]]})

kdom.add_sequence([[1,[1,0]],
                   [2,[1,0]],
                   [3,[1,0]]])

kdom.report()
kdom.tracing()
kdom.draw()

#%%
#%matplotlib qt5
eye_relief = 20
eyebox_shape = [[6,4.5],[-6,4.5],[-6,-4.5],[6,-4.5],[6,4.5]]
IC_shape = [-38,12,1]

s2d = System_2D(kdom)
s2d.set_eyebox(eye_relief,eyebox_shape)
s2d.set_input(IC_shape)
s2d.estimate()
s2d.draw()
res = s2d.check(wid = 0)

#%%
s3d = System3D()
s3d.add_source(-1,[-38,12,0],
               {'fov':[-20,20,-15,15],
                'wavelength_list':[0.525],
                'fov_grid':(3,3),
                'spatial_grid':(10,10),
                'direct':1})
#Doe1
s3d.add_element(0.6,Grating,s2d.element_area[1],
                {'name': 'G1',
                 'periods': kdom.elements[1].periods,
                 'index':[LASF46B,Air], 
                 'diffract_order':{ 1:[[-1,1,0],[-1,0,0]]}})
#Doe2
s3d.add_element(0.6,Grating,s2d.element_area[2],
                {'name': 'G2',
                 'periods': kdom.elements[2].periods,
                 'index':[LASF46B,Air], 
                 'mode': 'T&TIR',
                 'diffract_order':{1:[[-1,0,0],[-1,1,0],[-1,-1,0]]}})
#Doe3
s3d.add_element(0.6,Grating,s2d.element_area[3],
                {'name': 'G3',
                 'periods': kdom.elements[3].periods,
                 'index':[LASF46B,Air],
                 'mode': 'T&TIR',
                 'diffract_order':{1:[[-1,0,0],[-1,1,0]]}})

waveguide_shape = s3d.max_area()
#Surface1
s3d.add_element(0.1,Fresnel_loss,waveguide_shape,
                {'name': 'S1',
                 'index':[Air,LASF46B]})
#Surface2
s3d.add_element(0.6,Fresnel_loss,waveguide_shape,
                {'name': 'S2',
                 'index':[LASF46B,Air]})

#Eyebox
s3d.add_element(-20,Receiver,s2d.eyebox,
                      {'name': 'R1',})

# s3d.add_element(20,Receiver,s2d.eyebox,
#                       {'name': 'eyeglow',})

s3d.add_path({'G1':{1:[[-1,1,0],[-1,0,0]]},
              'G2':{1:[[-1,0,0],[-1,1,0],[-1,-1,0]]},
              'G3':{1:[[-1,0,0],[-1,1,0]]}})

# s3d.add_path({'G1':{1:[[-1,1,0],[-1,0,0]]},
#               'G2':{1:[[-1,0,0],[-1,1,0],[-1,-1,0]]},
#               'G3':{1:[[-1,0,0],[1,1,0]]}})

#Transmittion IC
# s3d.add_path({'G1':{-1:[[-1,1,0]], 1:[[-1,0,0],[-1,-1,0]]},
#               'G2':{1:[[-1,0,0],[-1,1,0],[-1,-1,0]]},
#               'G3':{1:[[-1,0,0],[-1,1,0]]}})


# %%
s3d.tracing(max_iter = 300)
s3d.draw()
# %%
t0 = time.time()
s3d.generate_graph()
print(time.time()-t0)
#%%
#%matplotlib qt5
s3d.draw_graph(0)
# %%

# %%
DG = s3d.graph[0.525]
subg = DG.subgraph(DG.subcomponent(12, mode='out')[:10])
subg = subg.as_undirected(mode="collapse").as_directed(mode="arbitrary")
ig.plot(subg)
# %%
