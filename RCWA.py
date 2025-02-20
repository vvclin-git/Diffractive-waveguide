#%%
import re
import numpy as np

def save_dat(file_name,header,order_list,value):
    with open(file_name, 'w') as file:
        file.write(header + '\n')
        for order in order_list:
            if isinstance(order, list):
                file.write(f'{order[0],order[1]}')
            else:
                file.write(f'{order}')
            file.write(' ')
        file.write('\n')
        for val in value:
            file.write(f"{val} ")

def fake_rsoft(command):
    'command: dfmod file.ind prefix=run1 symbol1= symbol2='
    '''output_setting is a dictionary
    #launch
        free_space_wavelength
        rcwa_primary_direction=, 0(+x), 1(-x), 2(+y), 3(-y), 4(+z), 5(-z)
        launch_angle
        launch_theta
        rcwa_launch_pol
        rcwa_launch_delta_phase
    #output_setting
        rcwa_output_e_coef_format=1,2,3(ReIm),4(AmpPhase)
        rcwa_output_option=,1(single value), 2(vs wavelength),3(vs phi),4(vs theta)
        rcwa_output_total_refl=,0(enable),1(disable)
        rcwa_output_total_trans=,0(enable),1(disable)
        rcwa_output_absorption=,0(enable),1(disable)
        rcwa_output_diff_refl=,0(enable),1(disable)
        rcwa_output_diff_trans=,0(enable),1(disable)
        rcwa_ref_order_x
        rcwa_ref_order_y
        rcwa_tra_order_x
        rcwa_tra_order_y
        rcwa_variation_max
        rcwa_variation_min
        rcwa_variation_step
    '''
    #time.sleep(1)
    pattern = r'prefix=(\S+).*?'
    #harmonics_x=(\S+).*?harmonics_y=(\S+).*?
    matches = re.search(pattern, command)
    if matches:
        prefix, = matches.groups()
        harmonics_x, harmonics_y = 5,0
        #harmonics_x, harmonics_y = int(float(harmonics_x)), int(float(harmonics_y))
        header = '#'+ command
        order_list = ['none']+np.mgrid[-harmonics_x:harmonics_x+1, -harmonics_y:harmonics_y+1].T.reshape((-1,2)).tolist()
        for suffix in ['_ep_ref_coef.dat','_es_ref_coef.dat','_ep_tra_coef.dat','_es_tra_coef.dat']:
            value = np.zeros((len(order_list)-1)*2+1)
            value[0] = 1
            realimag = np.random.random(size=4)
            A = np.sum(realimag**2)
            A = np.sqrt([np.sum(realimag[:2]**2)/A,np.sum(realimag[2:]**2)/A])
            P = np.arctan2(realimag[[1,3]],realimag[[0,2]])
            AP = 0.5*A*np.exp(1j*P)
            real = np.real(AP)
            imag = np.imag(AP)
            n = (2*harmonics_x+1)*(2*harmonics_y+1)
            value[n:n+4] = [real[0],imag[0],real[1],imag[1]]
            save_dat(f'{prefix}{suffix}',header,order_list,value)
    return None

def compute_jones(indfile,wavelength,direct,theta,phi,variable):
    prefix = 'temp'
    pol = {'p':0,'s':90}
    variable_cmd = ''
    for var in variable.keys():
        variable_cmd += ' '+var+'='+'%.4f'%(variable[var])

    for p in ['p','s']:
        cmd = f'dfmod -hide {indfile}.ind prefix={prefix}_{p} wait=0 '
        laubch_cmd = f'free_space_wavelength={wavelength} rcwa_primary_direction={direct} launch_angle={theta} launch_theta={phi} rcwa_launch_pol={pol[p]}'
        print(cmd+laubch_cmd+variable_cmd)
        fake_rsoft(cmd+laubch_cmd+variable_cmd)


    p_ep_r = np.loadtxt(prefix+f"_p_ep_ref_coef.dat",skiprows=2)[1:].reshape((-1,2))
    p_es_r = np.loadtxt(prefix+f"_p_es_ref_coef.dat",skiprows=2)[1:].reshape((-1,2))
    p_ep_t = np.loadtxt(prefix+f"_p_ep_tra_coef.dat",skiprows=2)[1:].reshape((-1,2))
    p_es_t = np.loadtxt(prefix+f"_p_es_tra_coef.dat",skiprows=2)[1:].reshape((-1,2))
    s_ep_r = np.loadtxt(prefix+f"_s_ep_ref_coef.dat",skiprows=2)[1:].reshape((-1,2))
    s_es_r = np.loadtxt(prefix+f"_s_es_ref_coef.dat",skiprows=2)[1:].reshape((-1,2))
    s_ep_t = np.loadtxt(prefix+f"_s_ep_tra_coef.dat",skiprows=2)[1:].reshape((-1,2))
    s_es_t = np.loadtxt(prefix+f"_s_es_tra_coef.dat",skiprows=2)[1:].reshape((-1,2))

    p_ep_r = p_ep_r[:,0]+p_ep_r[:,1]*1j
    p_es_r = p_es_r[:,0]+p_es_r[:,1]*1j
    p_ep_t = p_ep_t[:,0]+p_ep_t[:,1]*1j
    p_es_t = p_es_t[:,0]+p_es_t[:,1]*1j
    s_ep_r = s_ep_r[:,0]+s_ep_r[:,1]*1j
    s_es_r = s_es_r[:,0]+s_es_r[:,1]*1j
    s_ep_t = s_ep_t[:,0]+s_ep_t[:,1]*1j
    s_es_t = s_es_t[:,0]+s_es_t[:,1]*1j

    mask = ((np.abs(p_ep_r)>0)+(np.abs(p_es_r)>0)+(np.abs(p_ep_t)>0)+(np.abs(p_es_t)>0)+
            (np.abs(s_ep_r)>0)+(np.abs(s_es_r)>0)+(np.abs(s_ep_t)>0)+(np.abs(s_es_t)>0))>0
    p_ep_r = p_ep_r[mask]
    p_es_r = p_es_r[mask]
    p_ep_t = p_ep_t[mask]
    p_es_t = p_es_t[mask]
    s_ep_r = s_ep_r[mask]
    s_es_r = s_es_r[mask]
    s_ep_t = s_ep_t[mask]
    s_es_t = s_es_t[mask]

    return np.vstack((p_ep_r,p_es_r,p_ep_t,p_es_t)),np.vstack((s_ep_r,s_es_r,s_ep_t,s_es_t))


# %%
res = compute_jones('file',0.525,4,0,0,{'Height':0.1,'Duty':0.5})
# %%

    # for j,mn in enumerate(order[mask]):
    #     r_matrix = sqlite3.Binary(np.array([[p_ep_r[j],s_ep_r[j]],[p_es_r[j],s_es_r[j]]]).tobytes())
    #     t_matrix = sqlite3.Binary(np.array([[p_ep_t[j],s_ep_t[j]],[p_es_t[j],s_es_t[j]]]).tobytes())
    #     output += [[*var,int(mn[0]), int(mn[1]),r_matrix,t_matrix]]
    
    # else:
    #     output = np.asarray(output,dtype = object)
    #     variable_list = np.asarray(variable_list)
    #     indices = np.any(np.all(output[:, :-2][:, None, :].astype(float) == variable_list, axis=-1),axis = 1)
    #     output = [[np.frombuffer(out[-2], dtype=np.complex128).reshape((2, 2)),
    #                 np.frombuffer(out[-1], dtype=np.complex128).reshape((2, 2))] for out in output[indices]]