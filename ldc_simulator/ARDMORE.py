# import packages
import pandas as pd
import numpy as np
import itertools
import pandapower as pp
import pandapower.networks as nw
from pandapower.plotting.plotly import simple_plotly, pf_res_plotly
from pandapower.plotting import simple_plot
import copy
from pandapower.pf.runpp_3ph import combine_X012
from pandapower.create import create_asymmetric_load, create_load
from pandapower.pf.runpp_3ph import runpp_3ph
from pandapower.pypower.makeYbus import makeYbus 
from pandapower.pf.runpp_3ph import I0_from_V012,I1_from_V012,I2_from_V012

import multiprocessing as mp

from LOAD import *


def create_ardmore_network():
    #### Create Network
    net = pp.create_empty_network()
    # create bus
    bus0 = pp.create_bus(net, vn_kv=0.4, name='bus0')  # trafo input
    bus1 = pp.create_bus(net, vn_kv=0.4, name='bus1')  # trafo output
    bus2 = pp.create_bus(net, vn_kv=0.4, name='bus2')  # house 2
    bus3 = pp.create_bus(net, vn_kv=0.4, name='bus3')  # house 3
    bus4 = pp.create_bus(net, vn_kv=0.4, name='bus4')  # house 4
    bus5 = pp.create_bus(net, vn_kv=0.4, name='bus5')  # house 5
    bus6 = pp.create_bus(net, vn_kv=0.4, name='bus6')  # house 1

    # create external grid
    pp.create_ext_grid(net, bus=bus0, vm_pu=1.02, name='Grid Connection')
    net.ext_grid["r0x0_max"] = 0.1
    net.ext_grid["x0x_max"] = 1.0
    net.ext_grid["s_sc_max_mva"] = 10000
    net.ext_grid["s_sc_min_mva"] = 8000
    net.ext_grid["rx_min"] = 0.1
    net.ext_grid["rx_max"] = 0.1
    

    # create new standards
    pp.create_std_type(net, {"sn_mva": 0.3,
                "vn_hv_kv": 0.4,
                "vn_lv_kv": 0.4,
                "vk_percent": 6,
                "vkr_percent": 0.78125,
                "pfe_kw": 2.7,
                "i0_percent": 0.16875,
                "shift_degree": 0,
                "vector_group": "YNyn",
                "tap_side": "hv",
                "tap_neutral": 0,
                "tap_min": -2,
                "tap_max": 2,
                "tap_step_degree": 0,
                "tap_step_percent": 2.5,
                "tap_phase_shifter": False,
                "vk0_percent": 6, 
                "vkr0_percent": 0.78125, 
                "mag0_percent": 100,
                "mag0_rx": 0.,
                "si0_hv_partial": 0.9,}, "YNyn", "trafo")

    # pp.create_std_type(net, 
    #     {
    #         "max_i_ka": 313,
    #         "r_ohm_per_km": 0.164,
    #         "x_ohm_per_km": 0.117,
    #         "c_nf_per_km": 406,
    #         "r0_ohm_per_km": 0.1,
    #         "x0_ohm_per_km": 0.4,
    #         "c0_nf_per_km": 230.6,
    #     }, 
    #     "NAVY-J 4x185 SE 0.6/1kV", "line")

    # add trafo to the network
    trafo = pp.create_transformer(net, hv_bus=bus0, lv_bus=bus1, std_type='YNyn', parallel=1, tap_pos=0)

    # create lines
    line_0_2 = pp.create_line(net, from_bus=bus1, to_bus=bus2, length_km=0.250, std_type='NA2XS2Y 1x185 RM/25 6/10 kV')
    line_2_3 = pp.create_line(net, from_bus=bus2, to_bus=bus3, length_km=0.0001, std_type='NA2XS2Y 1x185 RM/25 6/10 kV')
    line_3_4 = pp.create_line(net, from_bus=bus3, to_bus=bus4, length_km=0.0001, std_type='NA2XS2Y 1x185 RM/25 6/10 kV')
    line_4_5 = pp.create_line(net, from_bus=bus4, to_bus=bus5, length_km=0.0001, std_type='NA2XS2Y 1x185 RM/25 6/10 kV')
    line_5_1 = pp.create_line(net, from_bus=bus5, to_bus=bus6, length_km=0.010, std_type='NA2XS2Y 1x185 RM/25 6/10 kV')
    net.line["r0_ohm_per_km"] = 0.161
    net.line["x0_ohm_per_km"] = 0.11
    net.line["c0_nf_per_km"] = 406

    # create loads
    house1 = pp.create_asymmetric_load(net, bus=bus6, sn_mva=0.15,
                       p_A_mw=0.01, q_A_mvar=(0.015**2-0.01**2)**0.5,
                       p_B_mw=0, q_B_mvar=0,
                       p_C_mw=0, q_C_mvar=0
                       )
    house2 = pp.create_asymmetric_load(net, bus=bus2, sn_mva=0.15,
                       p_A_mw=0, q_A_mvar=0,
                       p_B_mw=0.01, q_B_mvar=(0.015**2-0.01**2)**0.5,
                       p_C_mw=0, q_C_mvar=0
                       )
    house3 = pp.create_asymmetric_load(net, bus=bus3, sn_mva=0.15,
                       p_A_mw=0, q_A_mvar=0,
                       p_B_mw=0, q_B_mvar=0,
                       p_C_mw=0.01, q_C_mvar=(0.015**2-0.01**2)**0.5
                       )
    house4 = pp.create_asymmetric_load(net, bus=bus4, sn_mva=0.15,
                       p_A_mw=0, q_A_mvar=0,
                       p_B_mw=0.01, q_B_mvar=(0.015**2-0.01**2)**0.5,
                       p_C_mw=0, q_C_mvar=0,
                       
                       )
    house5 = pp.create_asymmetric_load(net, bus=bus5, sn_mva=0.15,
                       p_A_mw=0, q_A_mvar=0,
                       p_B_mw=0, q_B_mvar=0,
                       p_C_mw=0.01, q_C_mvar=(0.015**2-0.01**2)**0.5,
                       )

    pp.add_zero_impedance_parameters(net)

    return net


def create_houses(ldc=1):
    ### create house loads
    # define the number of devices to run
    n = 5
    ldc_adoption = ldc
    dict_houses = {
            'House':{'n':int(n*1), 'ldc':ldc_adoption},
            'Hvac':{'n':int(n*1), 'ldc':ldc_adoption},
            'Heater':{'n':int(n*0), 'ldc':ldc_adoption},
            'Fridge':{'n':int(n*1), 'ldc':ldc_adoption},
            'Freezer':{'n':int(n*1), 'ldc':ldc_adoption},
            'Waterheater':{'n':int(n*1), 'ldc':ldc_adoption},
            'Clotheswasher':{'n':int(n*1), 'ldc':ldc_adoption},
            'Clothesdryer':{'n':int(n*1), 'ldc':ldc_adoption},
            'Dishwasher':{'n':int(n*1), 'ldc':ldc_adoption},
            'Ev':{'n':int(n*1), 'ldc':ldc_adoption, 'v2g':int(n*0.0)},
            'Storage':{'n':int(n*0), 'ldc':ldc_adoption},
            'Solar':{'n':int(n*0), 'ldc':ldc_adoption},
            'Wind':{'n':int(n*0), 'ldc':ldc_adoption},    
            }



    # create network of houses, main() is a function from LOAD 
    houses = make_devices(dict_devices = dict_houses,
                    idx = 0,
                    capacity = 30e3,
                    loading = 0.5,
                    start = int(time.time()),
                    step_size = 1,
                    realtime = True,
                    timescale = 1,
                    three_phase = True,
                    simulate = 1,
                    renew = 0,
                    latitude = -36.866590076725494,
                    longitude = 174.77534779638677,
                    mcast_ip_local = '238.173.254.147',
                    mcast_port_local = 12604,
                )

    
    return houses




class Ardmore():
    'Common base class for all aggregators'
    # Attributes
    
    def __init__(self):
        
        self.name = 'Ardmore'
        self.df_states_all = pd.DataFrame([])
        self.dict_states_all = {}
        self.q_states_all = queue.Queue(maxsize=120)

        

        # multicasting parameters
        self.local_ip = FUNCTIONS.get_local_ip()

        # with LDC
        self.net_with_ldc = create_ardmore_network()
        self.houses_with_ldc = create_houses(ldc=1)

        # no LDC
        self.net_no_ldc = create_ardmore_network()
        self.houses_no_ldc = create_houses(ldc=0)



        # run separate threads
        thread = threading.Thread(target=self.receive_mcast, args=())
        thread.daemon = True                         # Daemonize thread
        thread.start() 

        # thread1 = threading.Thread(target=self.receive_mcast_global, args=())
        # thread1.daemon = True                         # Daemonize thread
        # thread1.start() 

        # thread2 = threading.Thread(target=self.tcp_server, args=())
        # thread2.daemon = True                         # Daemonize thread
        # thread2.start() 

        # thread3 = threading.Thread(target=self.contact_gridserver, args=())
        # thread3.daemon = True                         # Daemonize thread
        # thread3.start()
        
        self.step()
        



    
    # define worker function for parallel simulation of different cases
    def step(net, houses):
        # initial target
        target_loading = 0
        signal = 50
        
        while True:
            try:
                # update network with LDC
                self.net_with_ldc.asymmetric_load.update(self.houses_with_ldc.step(ldc_signal=signal, loading=target_loading, report=False))
                runpp_3ph(self.net_with_ldc, numba=True, recycle={'_is_elements':True, 'ppc':True, 'Ybus':True}, max_iteration=100)

                # update network without LDC
                self.net_no_ldc.asymmetric_load.update(self.houses_no_ldc.step(ldc_signal=signal, loading=target_loading, report=False))
                runpp_3ph(self.net_no_ldc, numba=True, recycle={'_is_elements':True, 'ppc':True, 'Ybus':True}, max_iteration=100)


                # combine data from houses and transformer
                # df = pd.concat([net.res_trafo_3ph.head(1), houses.df_agg], axis=1)
                df_with_ldc = self.net_with_ldc.res_trafo_3ph.head(1)
                df_no_ldc = self.net_no_ldc.res_trafo_3ph.head(1)
           
                # get time of the calculation
                timestep = self.houses_with_ldc.__dict__['App'].unixtime - unixtime
                unixtime = self.houses_with_ldc.__dict__['App'].unixtime
                # isotime = self.houses_with_ldc.__dict__['App'].isotime
                # hour = isotime.split('T')[1].split(':')[0]
                
                
                ### update target_loading
                # p_latest = df[['p_A_hv_mw', 'p_B_hv_mw', 'p_C_hv_mw']].sum(axis=1).values[0]
                # q_latest = df[['q_A_hv_mvar', 'q_B_hv_mvar', 'q_C_hv_mvar']].sum(axis=1).values[0]
                # df['s_hv_mva'] = (((p_latest**2)+(q_latest**2))**0.5)
                
                latest_loading =  df_with_ldc['loading_percent'].values[0]/100 #df['s_hv_mva'].values[0] / net.trafo.sn_mva.values[0] #

                if target_loading==0:
                    target_loading = latest_loading # df['loading_percent'].values[0]/100
                else:
                    w = timestep/(3600*24*1)  # average of 1 day
                    target_loading = ((1-w)*target_loading)+(w*(latest_loading))
                    
                # adjust ldc_signal
                offset = (target_loading - latest_loading) #((grid_capacity * target_loading) - (xmer_mw)) / grid_capacity
                signal += offset * (timestep * 1e0)
                signal = np.clip(signal, a_min=0.01, a_max=100.0)
                
                print(df)
            except Exception as e:
                print("Error run_simulation:", e)
                break
            except KeyboardInterrupt:
                break


        
        # # extend history data
        # df_history = pd.concat([df_history, df], axis=0)
        
        # ### record data
        # if unixtime%900==0:
        #     try:
        #         df_history.index = pd.to_datetime(df_history['unixtime'], unit='s')
        #         df_history.index = df_history.index.tz_localize('UTC')
        #         df_history.index = df_history.index.tz_convert('Pacific/Auckland')

        #         df_history.to_hdf('./results/'+filename, key='records', mode='a', 
        #                           append=True, complib='blosc')
        #         dt_latest = df_history.index
        #         # empty the dataframe to reduce memory cost
        #         df_history = df_history.tail(0)

        #         print("{} Target{} Signal{} Offset{} {} {:2.1%}".format(dt_latest[-1], 
        #                          np.round(target_loading,3), 
        #                          np.round(signal,3), 
        #                          np.round(offset,3),
        #                          filename.split('.')[0], 
        #                          d / duration))
        #     except Exception as e:
        #         print("Error worker:", e)
        #         print(df_history)
        
        # # create backup in case of power failure to avoid file corruption
        # folder = filename.split('_')[0].lower()+'/'
        # if unixtime%(3600)==0:
        #     try:
        #         ### get the last row in the backup file
        #         last_row = pd.read_hdf('./results/backup/'+folder+filename, start=-1)
        #         last_index = last_row.index.values[-1]

        #         ### get the corresponding rows not yet written to the backup
        #         with pd.HDFStore('./results/'+filename, 'r') as store: 
        #             df = store.select('records', where='index > "{}"'.format(last_index))

        #     except:
        #         ### get all records from the primary file
        #         with pd.HDFStore('./results/'+filename, 'r') as store: 
        #             df = store.select('records')
            
            
        #     try:
        #         ### write the new records to the backup file
        #         df.to_hdf('./results/backup/'+folder+filename, key='records', mode='a',
        #                  append=True, complib='blosc')
        #     except:
        #         df.to_hdf('./results/backup/'+folder+filename, key='records', mode='w',
        #                  append=True, complib='blosc')
                
 
def main():
    net = create_ardmore()
    assert runpp_3ph(net)[3]["success"]

    houses = create_houses()
    run_simulation(net, houses)

    # ### plot network
    # # net = pp.plotting.create_generic_coordinates(net, mg=None, library='igraph', respect_switches=False)
    # # simple_plot(net, respect_switches=False, line_width=1.0, bus_size=0.50, 
    # #             ext_grid_size=1.0, trafo_size=2.0, plot_loads=True, 
    # #             plot_sgens=False, load_size=1.0, sgen_size=1.0, 
    # #             switch_size=1.0, switch_distance=1.0, plot_line_switches=False, 
    # #             scale_size=True, bus_color='k', line_color='grey', trafo_color='k', 
    # #             ext_grid_color='k', switch_color='k', library='igraph', show_plot=True, ax=None)

    

    # ### print initial results
    # print(net)
    # print(net.res_asymmetric_load_3ph.head(5))
    # for k in net.res_trafo_3ph:
    #     print(k)
    # print(net.res_trafo)
    # print(net.res_line_3ph)
    # print(net.res_bus_3ph)
    # print(net.bus)





if __name__ == '__main__':
    main()



# dict_stocks = {}

# for ldc_adoption in [0.0, 1.0]:
#     for a in [0,80,90]: #[10, 20, 30, 40, 50, 60, 70, 100]:
#         pv = a
#         ev = a
#         dict_devices = {
#             'House':{'n':int(n*1), 'ldc':ldc_adoption},
#             'Hvac':{'n':int(n*0.61), 'ldc':ldc_adoption},
#             'Heater':{'n':int(n*1.31), 'ldc':ldc_adoption},
#             'Fridge':{'n':int(n*1.31), 'ldc':ldc_adoption},
#             'Freezer':{'n':int(n*0.50), 'ldc':ldc_adoption},
#             'Waterheater':{'n':int(n*0.8), 'ldc':ldc_adoption},
#             'Clotheswasher':{'n':int(n*1.08*0.3), 'ldc':ldc_adoption},
#             'Clothesdryer':{'n':int(n*0.7816*0.3), 'ldc':ldc_adoption},
#             'Dishwasher':{'n':int(n*0.6931*1), 'ldc':ldc_adoption},
#             'Ev':{'n':int(n*ev/100), 'ldc':ldc_adoption, 'v2g':int(n*0.0)},
#             'Storage':{'n':int(n*0.03), 'ldc':ldc_adoption},
#             'Solar':{'n':int(n*pv/100), 'ldc':ldc_adoption},
#             'Wind':{'n':int(n*0.0), 'ldc':ldc_adoption},    
#             }


#         dict_stocks.update({'PV{}_EV{}_LDC{}'.format(pv, ev, int(ldc_adoption*100)):dict_devices})


# # copy network and houses for different cases

# list_net = []
# list_houses = []
# list_filenames = []
 
# for key in dict_stocks:
#     list_houses.append(copy.deepcopy(houses))
#     list_net.append(copy.deepcopy(net))
#     list_houses[-1] = add_device(list_houses[-1], dict_stocks[key])
#     f = "3P_WINTER_{}.h5".format(key)
#     list_filenames.append(f)
#     print(f)
#     ### verify load distribution and ldc adoption
#     loads = np.unique(list_houses[-1].App.__dict__['load_type'])
#     for l in loads:
#         idx = np.flatnonzero(list_houses[-1].App.__dict__['load_type']==l)
#         idx2 = np.flatnonzero((list_houses[-1].App.__dict__['load_type']==l)&(list_houses[-1].App.__dict__['ldc']==1))
#         print(l, len(idx), 'LDC:',len(idx2))
#     print("---")

# # initialize variables
# checkpoint = 60
# list_signal = np.ones(len(list_net)) * 50  # initialize signal to maximum, range[0..100]
# list_n_violation = np.zeros(len(list_net)) # number of violations
# list_violated = np.zeros(len(list_net))
# list_history = []
# list_duration = (np.ones(len(list_net)) * duration).astype(int)
# list_timestep = (np.ones(len(list_net)) * timestep).astype(int)

# for i in range(len(list_net)):
#     list_history.append(pd.DataFrame([]))

    
# ### Run cases in parallel using pooled multiprocessing
# iterable = zip(list_net, list_houses, list_filenames, 
#                list_signal, list_n_violation, list_history, 
#                list_duration, list_timestep)


# # run in parallel
# pool = mp.Pool(len(list_net))
# pool.starmap(worker, iterable)
# pool.close()
# pool.join()

# print("Done!")
