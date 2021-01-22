
from models import *

class Aggregator(multiprocessing.Process):
    """Aggregator for all objects of the system"""
    n = 0
    def __init__(self, dict_devices, timestamp, latitude, longitude, idx, local_ip, device_ip, step_size=1, 
        simulation=0, endstamp=None, case=None, casefolder='assorted', network=None, 
        algorithm='no_ldc', target='auto', distribution='per_house', ranking='static', 
        resolution=3, ki=32, save_history=True, tcl_control='direct', delay=0.0, 
        report=False, flex_percent=50, summary=False):
        super(Aggregator, self).__init__()
        multiprocessing.Process.__init__(self)
        self.daemon = True

        self.name = 'Aggregator_{}'.format(self.n+1)

        ### data holders
        self.dict_devices = {} # manager.dict()
        self.dict_common = {} #manager.dict()
        self.dict_network = {} #manager.dict()
        self.dict_house = {} #manager.dict()
        self.dict_baseload = {}  # set another name for dict_house
        self.dict_heatpump = {}#manager.dict()
        self.dict_heater = {}#manager.dict()
        self.dict_waterheater = {} #manager.dict()
        self.dict_freezer = {} #manager.dict()
        self.dict_fridge = {} #manager.dict()
        self.dict_clothesdryer = {} #manager.dict()
        self.dict_clotheswasher = {} #manager.dict()
        self.dict_dishwasher = {} #manager.dict()
        self.dict_ev = {} #manager.dict()
        self.dict_storage = {} #manager.dict()
        self.dict_solar = {} #manager.dict()
        self.dict_wind = {} #manager.dict()
        self.dict_dongle = {} #manager.dict()
        self.dict_schedule = {} #manager.dict()
        self.dict_valve = {} #manager.dict()
        self.dict_window = {} #manager.dict()
        self.dict_door = {} #manager.dict()
        self.dict_blind = {} #manager.dict()
        self.dict_emulation_value = {} #manager.dict()
        self.dict_summary_demand = {}
        self.dict_summary_mode = {}
        self.dict_summary_status = {}
        self.dict_summary_flexibility = {}
        self.dict_state = {}
        self.ac_state = {}
        self.dict_meter = {}
        manager = multiprocessing.Manager()
        self.dict_agg = manager.dict()
        self.dict_injector = {}
        self.dict_config = read_json('/home/pi/ldc_project/config_self.json')
        
        ### communication pipes for other processes
        self.pipe_agg_baseload0, self.pipe_agg_baseload1 = multiprocessing.Pipe()
        self.pipe_agg_heatpump0, self.pipe_agg_heatpump1 = multiprocessing.Pipe()
        self.pipe_agg_heater0, self.pipe_agg_heater1 = multiprocessing.Pipe()
        self.pipe_agg_waterheater0, self.pipe_agg_waterheater1 = multiprocessing.Pipe()
        self.pipe_agg_fridge0, self.pipe_agg_fridge1 = multiprocessing.Pipe()
        self.pipe_agg_freezer0, self.pipe_agg_freezer1 = multiprocessing.Pipe()
        self.pipe_agg_clotheswasher0, self.pipe_agg_clotheswasher1 = multiprocessing.Pipe()
        self.pipe_agg_clothesdryer0, self.pipe_agg_clothesdryer1 = multiprocessing.Pipe()
        self.pipe_agg_dishwasher0, self.pipe_agg_dishwasher1 = multiprocessing.Pipe()
        self.pipe_agg_ev0, self.pipe_agg_ev1 = multiprocessing.Pipe()
        self.pipe_agg_storage0, self.pipe_agg_storage1 = multiprocessing.Pipe()
        self.pipe_agg_solar0, self.pipe_agg_solar1 = multiprocessing.Pipe()
        self.pipe_agg_wind0, self.pipe_agg_wind1 = multiprocessing.Pipe()
        self.pipe_agg_schedule0, self.pipe_agg_schedule1 = multiprocessing.Pipe()
        self.pipe_agg_network0, self.pipe_agg_network1 = multiprocessing.Pipe()
        self.pipe_agg_listener0, self.pipe_agg_listener1 = multiprocessing.Pipe()
        self.pipe_agg_ouput0, self.pipe_agg_ouput1 = multiprocessing.Pipe()

        ### communication pipes for IO-bound processes
        self.pipe_agg_history0, self.pipe_agg_history1 = multiprocessing.Pipe()
        self.pipe_agg_valve0, self.pipe_agg_valve1 = multiprocessing.Pipe()
        self.pipe_agg_window0, self.pipe_agg_window1 = multiprocessing.Pipe()
        self.pipe_agg_door0, self.pipe_agg_door1 = multiprocessing.Pipe()
        self.pipe_agg_grainy0, self.pipe_agg_grainy1 = multiprocessing.Pipe()
        self.pipe_agg_comm0, self.pipe_agg_comm1 = multiprocessing.Pipe()
        self.pipe_agg_meter0, self.pipe_agg_meter1 = multiprocessing.Pipe()
        self.pipe_agg_multicast0, self.pipe_agg_multicast1 = multiprocessing.Pipe()
        self.pipe_agg_udp0, self.pipe_agg_udp1 = multiprocessing.Pipe()
        self.pipe_agg_tcp0, self.pipe_agg_tcp1 = multiprocessing.Pipe()
        
        # self.q_states = multiprocessing.Queue(maxsize=32)

        self.idx = idx
        self.house_num = idx + 1
        self.local_ip = local_ip
        self.device_ip = device_ip
        self.q_id = str(self.device_ip)
        self.simulation = simulation
        self.save_history = save_history
        self.report = report

        self.case = case
        self.algorithm = algorithm  # algorithm used
        self.ranking = ranking  # prioritization scheme, static vs dynamic
        self.distribution = distribution  # distribution of ldc-enabled devices, per_house vs per_device
        self.delay = delay
        self.resolution = resolution
        self.sampling = 1 # [s] saving sample rate
        self.injector_gain = ki
        self.summary = summary

        if self.simulation:
            self.realtime = False
            self.timestamp = timestamp
            self.step_size = step_size
            self.endstamp = endstamp
            self.network_grid = network 
            self.casefolder = casefolder
            self.target = target
            if target in ['auto', 'tou']:
                self.target_loading = 30.0
            else:
                self.target_loading = float(target)
        else:
            self.realtime = True
            self.timestamp = time.time()
            self.step_size = None
            self.endstamp = None
            self.network_grid = None
            self.target_loading = 100

        ### create globl objects
        self.weather = Weather(latitude=latitude, longitude=longitude, timestamp=self.timestamp, realtime=self.realtime)
        
        self.dict_common.update({
            'local_ip':local_ip, 
            'unixtime': self.timestamp, 
            'previous_error':0, 
            'previous_i_term':0, 
            'derivative': 0.0, 
            'max_d': 0.0,
            'min_d': 0.0,
            'tcl_control':tcl_control,
            'case':self.case, 
            'algorithm':self.algorithm, 
            'ranking':self.ranking, 
            'distribution':self.distribution, 
            'delay':delay,
            'resolution':self.resolution, 
            'target':target, 
            'target_percent':self.target_loading, 
            'simulation':simulation, 
            'ldc_signal':0.0, 
            'flex':flex_percent/100, 
            'loading_percent':0.0, 
            'injector_gain': self.injector_gain,
            })
        self.dict_common.update(clock(unixtime=self.dict_common['unixtime'], step_size=self.step_size, realtime=self.realtime))
        self.pause = 1e-64  # pause time used in thread interrupts
        self.save_interval = 3600
        self.start_unixtime = self.dict_common['unixtime']

        self.dict_startcode = {
            'heater':3,
            'dishwasher':4,
            'clothesdryer':5,
            'clotheswasher':6,
            'storage':7, # always connected
            'ev':8,
            'fridge':9,  # always ON
            'freezer':10,  # always ON
            'heatpump':11,
            'waterheater':12,  # always ON
            'valve':13,
            'humidifier':16,
            'window':18,
            'door':23,
            'human':27,
            'solar':28,
        }

        self.add_device(dict_new_devices=dict_devices)
        self.autorun()
        

    def add_device(self, dict_new_devices):
        print("Adding devices...")
        self.factor = 1
        for load_type in dict_new_devices.keys():
            n_units = dict_new_devices[load_type]['n_units']  # new devices
            n_ldc = dict_new_devices[load_type]['n_ldc']
            n_b2g = dict_new_devices[load_type]['n_b2g']
            if load_type in self.dict_devices.keys():
                idx = self.idx + self.dict_devices[load_type]['n_units']  # exisiting number of devices
                self.dict_devices[load_type].update({
                    'n_units': self.dict_devices[load_type]['n_units'] + n_units,
                    'n_ldc': self.dict_devices[load_type]['n_ldc'] + n_ldc,
                    'n_b2g': self.dict_devices[load_type]['n_b2g'] + n_b2g,
                    })
            else:
                idx = self.idx
                self.dict_devices.update({load_type:{ 'n_units': n_units, 'n_ldc': n_ldc, 'n_b2g': n_b2g}
                    })  # update number of devices

        ### create house data
        if 'house' in self.dict_devices.keys():
            n_units = self.dict_devices['house']['n_units']
            idx = self.idx
            with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
                df = store.select('house', where='index>={} and index<{}'.format(idx, idx+n_units))
            self.dict_house.update(df.to_dict(orient='list'))
            for k, v in self.dict_house.items():
                self.dict_house[k] = np.array(v)
            del df

        ### loads to run
        self.loads_to_run = [str(a) for a in self.dict_devices.keys() if a!='house']
        self.loads_to_run.sort()
        return


    def autorun(self):
        print("Running autorun...")
        ### run common threads
        self.list_processes = [] 
        self.common_observer = []
        self.agg_observer = []
        self.load_pipes = []

        # create separate list_processes for each type of appliance
        for k in self.loads_to_run:
            if self.dict_devices[k]['n_units']:
                eval(f'self.list_processes.append(multiprocessing.Process(target=self.{k}, args=(), name="{k}"))')
                eval(f'self.load_pipes.append(self.pipe_agg_{k}0)')
        
        if self.simulation==1:
            self.list_processes.append(multiprocessing.Process(target=self.network, args=(), name='network'))
        else:   
            ### threading is used in raspi implementation since only one processor is available
            self.list_processes.append(multiprocessing.Process(target=self.udp_server, args=(), name='udp_server'))
            self.list_processes.append(multiprocessing.Process(target=self.multicast_server, args=(), name='multicast_server'))
            self.list_processes.append(multiprocessing.Process(target=self.ldc_listener, args=(), name='ldc_listener'))
            self.agg_observer.extend([self.pipe_agg_listener0]) #, self.pipe_agg_multicast0, self.pipe_agg_udp0])

            if self.device_ip==100:
                self.list_processes.append(multiprocessing.Process(target=self.drive_grainy, args=(), name='drive_grainy'))
                self.agg_observer.append(self.pipe_agg_grainy0)
            if self.device_ip==101:
                self.list_processes.append(multiprocessing.Process(target=self.meter, args=(), name='meter'))
                self.agg_observer.append(self.pipe_agg_meter0)
            if self.device_ip in [113, 114]:
                self.list_processes.append(multiprocessing.Process(target=self.valve, args=(), name='valve'))
                self.agg_observer.append(self.pipe_agg_valve0)
            if self.device_ip in [118, 119, 120, 121, 122]:
                self.list_processes.append(multiprocessing.Process(target=self.window, args=(), name='window'))
                self.agg_observer.append(self.pipe_agg_window0)
            if self.device_ip in [123, 124, 125]:
                self.list_processes.append(multiprocessing.Process(target=self.door, args=(), name='door'))
                self.agg_observer.append(self.pipe_agg_door0)

        ### initialize ready pipes
        self.ready_loads = self.load_pipes
        self.ready_agg = self.agg_observer

        ### setup the profiles
        print('Running schedules...')
        df_schedules = pd.read_csv('./specs/schedules.csv')      
        self.dict_schedule["schedule_profile"] =  self.dict_house["schedule"]
    
        ### update clock
        self.dict_common.update(clock(unixtime=self.dict_common['unixtime'], step_size=self.step_size, realtime=self.realtime))
        ### update weather
        self.dict_common.update(self.weather.get_weather(self.dict_common['unixtime']))
        

        # run list_processes
        self.dict_common.update({'is_alive': True, 'ldc_signal': 30.0})
        for t in self.list_processes:
            t.daemon = True
            t.start()
            print(f"Running {t.name}...")

        # agg_data = {}
        factor = 0.005 #0.01333  # regression factor to predict percent_loss
        pfe_mw = 0 #2.7*1e-3
        sn_mva = 0.3
        pf = 0.9
        # list_latest = []
        # actual_loading = 0
        # list_signal = []
        # tprint = 0
        t1 = time.perf_counter()
        # tt = 0
        # f0 = 0
        # f1 = 0
        # p0 = 0
        # p1 = 0
        # dpdf = 0
        # ewma = 80 # [kw]
        ### Loop for the main process
        while True:
            try:
                ### update clock
                self.dict_common.update(clock(unixtime=self.dict_common['unixtime'], step_size=self.step_size, realtime=self.realtime))
                ### update weather
                self.dict_common.update(self.weather.get_weather(self.dict_common['unixtime']))
                ### update tasks
                self.dict_common['current_task'] = df_schedules.iloc[self.dict_common['weekminute']]
                '''
                NOTE: current_task values are floats wherein the integer part denotes the type of appliance, 
                and the decimal part denotes the duration. Refer to CREATOR.py for the codes of specific appliance.
                '''
                ### send common info to all device simulators
                [p.send(self.dict_common) for p in self.load_pipes]
                [p.send(self.dict_common) for p in self.common_observer]

                ### gather data from the device simulators
                # self.ready_loads = multiprocessing.connection.wait(self.load_pipes, timeout=0.1)
                for p in self.load_pipes:
                    new = p.recv()
                    k = new['load_type'][0]
                    
                    self.dict_summary_demand[f'{k}'] = [new['actual_demand'][new['house']==h].sum() for h in self.dict_house['name']]  # sum up loads per house
                    self.dict_summary_status[f'{k}'] = new['actual_status'].tolist()
                    self.dict_summary_mode[f'{k}'] = new['mode'].tolist()
                    self.dict_summary_flexibility[f'{k}'] = new['flexibility'].tolist()
                    
                    d_prep = prepare_data(states=new, common=self.dict_common)
                    
                    ### update dict_state
                    [[self.dict_state.update({f'{k}_{p}':v}) for p, v in d_prep[t].items()] for t in d_prep.keys()]

                self.dict_agg.update({
                    'summary': {
                        'demand': self.dict_summary_demand,
                        'status': self.dict_summary_status,
                        'mode': self.dict_summary_mode,
                        'flexibility': self.dict_summary_flexibility},
                    'states': self.dict_state,
                    'common': self.dict_common
                        })
                
                # for k, v in self.dict_agg.items():
                #     print(k, v)

                # if self.q_states.full():
                #     self.q_states.get()
                # self.q_states.put({int(self.dict_common['unixtime']): self.dict_state})

                [p.send(self.dict_agg) for p in self.ready_agg]


                if self.simulation==1:
                    # decay = np.exp(-self.dict_common['step_size']/3)
                    p_mw = np.sum(np.array(list(self.dict_summary_demand.values())), axis=0) * 1e-6 
                    nogrid_percent = (np.sum(p_mw)+ pfe_mw)*100/(sn_mva * pf)
                    # loss_percent = np.power(nogrid_percent,2) * factor # factors are derived using regression as compared with pandapower simulation
                    self.dict_common['loading_percent'] = nogrid_percent # + loss_percent #(nogrid_percent*(1-decay)) + (decay*self.dict_common['loading_percent'])  #+ loss_percent


                    ### send data to network simulator
                    if not self.pipe_agg_network1.poll():
                        self.pipe_agg_network0.send({'summary_demand':{'p_mw':p_mw}, 'common':self.dict_common})       
                        # self.pipe_agg_network0.send({'summary_demand':{'p_mw':p_mw, 'p_a_mw':p_a_mw, 'p_b_mw': p_b_mw, 'p_c_mw': p_c_mw}, 'common':self.dict_common})

                    if self.pipe_agg_network0.poll():
                        grid_data = self.pipe_agg_network0.recv()  # to empty pipe
                        # factor = (factor*0.99) + (np.mean(grid_data['factor']) * 0.01)
                        # sn_mva = np.mean(grid_data['sn_mva'])
                        # pf = np.mean(grid_data['pf'])
                        # pfe_mw = (0.9*pfe_mw) + (0.1*(np.mean(grid_data['loss_percent']) - (nogrid_percent*factor)))
                        # actual_loading = np.mean(grid_data['loading_percent'])
                        # self.dict_common['loading_percent'] = grid_data['loading_percent']
                
                    
                    if self.target=='auto': 
                        w = self.dict_common['step_size'] / (3600) # 1 - np.exp(-self.dict_common['step_size']/(3600)) #
                        self.target_loading = np.clip((self.dict_common['loading_percent']*(w)) + (self.target_loading*(1-w)), a_min=0.1, a_max=90.0)


                    elif self.target=='tou':
                        if (self.dict_common['hour']>=18) and (self.dict_common['hour']<=21):
                            self.target_loading = 20.0
                        else:
                            self.target_loading = 33.0

                        # if self.dict_common['minute']<15:
                        #     self.target_loading = 5.0
                        # elif self.dict_common['minute']>=15 and self.dict_common['minute']<30:
                        #     self.target_loading = 10.0
                        # elif self.dict_common['minute']>=30 and self.dict_common['minute']<45:
                        #     self.target_loading = 15.0
                        # elif self.dict_common['minute']>=45 and self.dict_common['minute']<60:
                        #     self.target_loading = 10.0

                    

                    self.dict_common['target_percent'] = self.target_loading
                    injector_data = ldc_injector(ldc_signal=self.dict_common['ldc_signal'], 
                        latest=self.dict_common['loading_percent']*1e-2,
                        target=self.target_loading*1e-2, 
                        step_size=self.dict_common['step_size'],
                        algorithm=self.algorithm,
                        hour=self.dict_common['hour'],
                        minute=self.dict_common['minute'],
                        previous_error=self.dict_common['previous_error'],
                        previous_i_term=self.dict_common['previous_i_term'],
                        derivative=self.dict_common['derivative'], 
                        max_d=self.dict_common['max_d'],
                        min_d=self.dict_common['min_d'],
                        K=self.injector_gain)
                    
                    self.dict_common.update(injector_data)
                    
                    print(self.dict_common['isotime'], 
                        'ldc_signal:', np.round(self.dict_common['ldc_signal'],3), 
                        'timeit:', np.round((time.perf_counter()-t1), 5), 
                        'target:', np.round(self.target_loading,3), 
                        'latest:', np.round(self.dict_common['loading_percent'],3), 
                        'factor:', np.round(factor,6), 
                        'tcl_control:', self.dict_common['tcl_control'],
                        'case:', self.case
                        )
                
                    t1 = time.perf_counter()


                    if self.dict_common['unixtime'] >= self.endstamp: # end simulation
                        raise KeyboardInterrupt          
                else:
                    ### Retrieve data from IOs
                    self.ready_agg = multiprocessing.connection.wait(self.agg_observer, timeout=0)
                    for g in self.ready_agg:
                        dev_state = g.recv()
                        self.dict_agg.update(dev_state)
                        for key, value in dev_state.items():
                            if key in ['valve', 'door', 'window']:
                                self.dict_state.update(value)
                            elif key=='meter':
                                self.dict_state.update(self.dict_agg['meter'])
                            elif key in ['injector']:
                                self.dict_common.update(self.dict_agg['injector'])

                    ### update dict_cmd
                    try:
                        self.dict_common.update(read_json('/home/pi/ldc_project/ldc_simulator/dict_cmd.txt'))
                        response = MULTICAST.send(dict_msg={'states':'algorithm'}, ip='192.168.1.3', port=10000, timeout=0.5, data_bytes=8192, hops=1)
                        for k, v in response.items():
                            self.dict_common.update(v)
                    except:
                        pass

                if self.report: print(self.dict_agg)
                time.sleep(self.pause)
            except Exception as e:
                print(f'Error AGGREGATOR.autorun:{e}')
                
            except KeyboardInterrupt:
                ### send stop signal to device simulators
                for c in self.common_observer:
                    c.send({'is_alive':False})
                for p in self.load_pipes:
                    p.send({'is_alive':False})
                for g in self.agg_observer:
                    g.send({'summary_demand':{}, 'common':{'is_alive':False}})
                if self.simulation==1:
                    self.pipe_agg_network0.send({'summary_demand':{},'common':{'is_alive':False}})
                    # self.pipe_agg_history0.send({'states':{},'common':{'is_alive':False}})
                
                for t in self.list_processes:
                    t.join(timeout=3)

                ### close all pipes
                for c in self.common_observer:
                    c.close()
                for p in self.load_pipes:
                    p.close()
                for g in self.agg_observer:
                    g.close()

                if self.simulation==1:
                    self.pipe_agg_network0.close()
                
                for t in self.list_processes:
                    if t.is_alive():
                        t.terminate()
                
                break



    def network(self):
        '''Model for electrical network'''
        # print("Starting grid simulator...")
        if self.simulation:
            import pandapower as pp
            import pandapower.networks as nw
            from pandapower.pf.runpp_3ph import runpp_3ph
            self.save_interval += np.random.randint(0,60)
            def convert_to_3ph(net, sn_mva=0.4):
                ### update external grid
                net.ext_grid["r0x0_max"] = 0.1
                net.ext_grid["x0x_max"] = 1.0
                net.ext_grid["s_sc_max_mva"] = 10000
                net.ext_grid["s_sc_min_mva"] = 8000
                net.ext_grid["rx_min"] = 0.1
                net.ext_grid["rx_max"] = 0.1
                
                ### update transformer
                net.trafo = net.trafo.head(0)
                pp.create_std_type(net, {"sn_mva": sn_mva, "vn_hv_kv": 20, "vn_lv_kv": 0.4, "vk_percent": 6,
                                        "vkr_percent": 0.78125, "pfe_kw": 2.7*0, "i0_percent": 0.16875,
                                        "shift_degree": 0, "vector_group": "YNyn",
                                        "tap_side": "hv", "tap_neutral": 0, "tap_min": -2, "tap_max": 2,
                                        "tap_step_degree": 0, "tap_step_percent": 2.5, "tap_phase_shifter": False,
                                        "vk0_percent": 6, "vkr0_percent": 0.78125, "mag0_percent": 100,
                                        "mag0_rx": 0., "si0_hv_partial": 0.9,}, 
                                        "YNyn", "trafo")
                
                pp.create_transformer(net, 0, 1, std_type="YNyn", parallel=1,tap_pos=0, index=pp.get_free_id(net.trafo))
                net.trafo.reset_index()
                
                ### add zero sequence for lines
                net.line["r0_ohm_per_km"] = 0.0848
                net.line["x0_ohm_per_km"] = 0.4649556
                net.line["c0_nf_per_km"] = 230.6
                
                ### convert loads to asymmetric loads
                for i in net.load.index:
                    row = net.load.iloc[i]
                    phases = [0,0,0]
                    p = i % 3
                    phases[p] = 1
                    pp.create_asymmetric_load(net, row['bus'], 
                        p_a_mw=0*phases[0], q_a_mvar=0*phases[0], 
                        p_b_mw=0*phases[1], q_b_mvar=0*phases[1],
                        p_c_mw=0*phases[2], q_c_mvar=0*phases[2], 
                        sn_mva=row['sn_mva']
                        )
                    
                net.load['p_mw'] = 0
                net.load['q_mvar'] = 0
                pp.add_zero_impedance_parameters(net)
                return net

            if self.network_grid=='dickert_lv_long':
                net = nw.create_dickert_lv_network(feeders_range='long', 
                    linetype='C&OHL', customer='multiple', case='good', 
                    trafo_type_name='0.4 MVA 20/0.4 kV', trafo_type_data=None)
                net.line.length_km = np.round(np.random.normal(0.100, 0.005, len(net.line.length_km)), 4)
         
            elif self.network_grid=='ieee_european_lv':
                net = nw.ieee_european_lv_asymmetric("off_peak_1")
                net.trafo.sn_mva = 0.3
            elif self.network_grid=='lv_1':
                net = nw.create_dickert_lv_network(feeders_range='short', 
                    linetype='cable', customer='single', case='good', 
                    trafo_type_name='0.25 MVA 20/0.4 kV', # to ba changed in convert_to_3ph
                    trafo_type_data=None)
                net = convert_to_3ph(net, sn_mva=0.03)
            elif self.network_grid=='lv_5':
                net = nw.create_dickert_lv_network(feeders_range='short', 
                    linetype='cable', customer='multiple', case='good', 
                    trafo_type_name='0.25 MVA 20/0.4 kV', # to ba changed in convert_to_3ph
                    trafo_type_data=None)
                net = convert_to_3ph(net, sn_mva=0.03)
                net.asymmetric_load = net.asymmetric_load.head(5)
            elif self.network_grid=='lv_60':
                net = nw.create_dickert_lv_network(feeders_range='long', 
                    linetype='C&OHL', customer='multiple', case='good', 
                    trafo_type_name='0.4 MVA 20/0.4 kV', trafo_type_data=None)
                net.line.length_km = np.round(np.random.normal(0.040, 0.005, len(net.line.length_km)), 4)
                net = convert_to_3ph(net)
                net.asymmetric_load = net.asymmetric_load.head(60)

            # capacity = (self.dict_devices['house']['n_units'] * 5e3) * 1e-6
            self.dict_network = {'ldc_signal':100}
        

            # factor = np.ones(self.dict_devices['house']['n_units'])
            pf = 0.9 # assumed powerfactor

            
            dict_agg = {}
            dict_save_trafo = {}
            dict_save_bus = {}
            dict_save_line = {}
            dict_save_load = {}
            while True:
                try:
                    ### receive data from main routine
                    dict_agg = self.pipe_agg_network1.recv()
                    if len(dict_agg.keys())==0: continue
                    self.dict_common.update(dict_agg['common'])
                    if self.dict_common['is_alive']==False: 
                        raise KeyboardInterrupt

                    self.dict_summary_demand.update(dict_agg['summary_demand'])
                    
                    ### update network load
                    net.asymmetric_load['p_a_mw'] = np.multiply(self.dict_summary_demand['p_mw'], (self.dict_house['phase']=='AN')*1)
                    net.asymmetric_load['p_b_mw'] = np.multiply(self.dict_summary_demand['p_mw'], (self.dict_house['phase']=='BN')*1)
                    net.asymmetric_load['p_c_mw'] = np.multiply(self.dict_summary_demand['p_mw'], (self.dict_house['phase']=='CN')*1)
                    net.asymmetric_load['q_a_mvar'] = np.multiply(net.asymmetric_load['p_a_mw'], np.sin(np.arccos(pf)))
                    net.asymmetric_load['q_b_mvar'] = np.multiply(net.asymmetric_load['p_b_mw'], np.sin(np.arccos(pf)))
                    net.asymmetric_load['q_c_mvar'] = np.multiply(net.asymmetric_load['p_c_mw'], np.sin(np.arccos(pf)))
                    
                    ### simulate network
                    runpp_3ph(net, numba=True, #recycle={'_is_elements':True, 'ppc':True, 'Ybus':True}, 
                        max_iteration=10)
                    
                    ### send result to main routine
                    trafo_data = net.res_trafo_3ph.to_dict(orient='records')[0]
                    bus_data = net.res_bus_3ph.loc[net.trafo['lv_bus'], :].to_dict(orient='list')
                    line_data = net.res_line_3ph.nlargest(1, 'loading_percent').to_dict(orient='list')
                    load_data = net.res_asymmetric_load_3ph.to_dict(orient='list')
                    # for k, v in trafo_data.items():
                    #   trafo_data[k] = np.array(v)
                    
                    trafo_data['sn_mva'] = net.trafo.sn_mva.values[0]
                    trafo_data['pf_a'] = np.divide(trafo_data['p_a_hv_mw'], np.sqrt(np.add(np.power(trafo_data['p_a_hv_mw'],2), np.power(trafo_data['q_a_hv_mvar'],2))))
                    trafo_data['pf_b'] = np.divide(trafo_data['p_b_hv_mw'], np.sqrt(np.add(np.power(trafo_data['p_b_hv_mw'],2), np.power(trafo_data['q_b_hv_mvar'],2))))
                    trafo_data['pf_c'] = np.divide(trafo_data['p_c_hv_mw'], np.sqrt(np.add(np.power(trafo_data['p_c_hv_mw'],2), np.power(trafo_data['q_c_hv_mvar'],2))))
                    trafo_data['pf'] = np.mean([trafo_data['pf_a'], trafo_data['pf_b'], trafo_data['pf_c']]) #np.divide(np.add(trafo_data['pf_a'], np.add(trafo_data['pf_b'], trafo_data['pf_c'])), 3)
                    trafo_data['ldc_signal'] = self.dict_common['ldc_signal']
                    trafo_data['injector_gain'] = self.dict_common['injector_gain']
                    trafo_data['nogrid_percent'] = np.clip(np.divide(np.sum(self.dict_summary_demand['p_mw'])*100, np.multiply(trafo_data['pf'],trafo_data['sn_mva'])), a_min=0.1, a_max=100)
                    trafo_data['loss_percent'] = np.subtract(trafo_data['loading_percent'], trafo_data['nogrid_percent'])
                    trafo_data['factor'] = np.divide(trafo_data['loss_percent'], np.power(trafo_data['nogrid_percent'], 2))
                
                    trafo_data['target_percent'] = self.dict_common['target_percent']
                    trafo_data['offset'] = self.dict_common['previous_error']
                    
                    ### send data to main
                    self.pipe_agg_network1.send(trafo_data)
                    
                 
                    ### collect data for saving
                    if self.save_history:
                        # dict_save_trafo.update({int(self.dict_common['unixtime']):trafo_data})
                        # dict_save_bus.update({int(self.dict_common['unixtime']):bus_data})
                        # dict_save_line.update({int(self.dict_common['unixtime']):line_data})
                        # dict_save_load.update({self.dict_common['unixtime']:load_data})

                        dict_save_trafo.update({self.dict_common['unixtime']:trafo_data})                        
                        dict_save_bus.update({self.dict_common['unixtime']:{
                                # 'vm_a_pu': ','.join(np.char.zfill(np.round(bus_data['vm_a_pu'], 6).astype(str), 10)),
                                # 'vm_b_pu': ','.join(np.char.zfill(np.round(bus_data['vm_b_pu'], 6).astype(str), 10)),
                                # 'vm_c_pu': ','.join(np.char.zfill(np.round(bus_data['vm_c_pu'], 6).astype(str), 10)),
                                # 'va_a_degree': ','.join(np.char.zfill(np.round(bus_data['va_a_degree'], 6).astype(str), 10)),
                                # 'va_b_degree': ','.join(np.char.zfill(np.round(bus_data['va_b_degree'], 6).astype(str), 10)),
                                # 'va_c_degree': ','.join(np.char.zfill(np.round(bus_data['va_c_degree'], 6).astype(str), 10)),
                                'unbalance_percent': ','.join(np.char.zfill(np.round(bus_data['unbalance_percent'], 6).astype(str), 10)),
                                }})

                        
                        dict_save_line.update({self.dict_common['unixtime']:{
                            # 'loading_percentA': ','.join(np.char.zfill(np.round(line_data['loading_percentA'], 6).astype(str), 10)),
                            # 'loading_percentB': ','.join(np.char.zfill(np.round(line_data['loading_percentB'], 6).astype(str), 10)),
                            # 'loading_percentC': ','.join(np.char.zfill(np.round(line_data['loading_percentC'], 6).astype(str), 10)),
                            'loading_percent': ','.join(np.char.zfill(np.round(line_data['loading_percent'], 6).astype(str), 10)),
                            }})
                        
                        dict_save_load.update({self.dict_common['unixtime']:{
                            'p_a_mw': ','.join(np.char.zfill(np.round(load_data['p_a_mw'], 6).astype(str), 10)),
                            'p_b_mw': ','.join(np.char.zfill(np.round(load_data['p_b_mw'], 6).astype(str), 10)),
                            'p_c_mw': ','.join(np.char.zfill(np.round(load_data['p_c_mw'], 6).astype(str), 10)),
                            'q_a_mvar': ','.join(np.char.zfill(np.round(load_data['q_a_mvar'], 6).astype(str), 10)),
                            'q_b_mvar': ','.join(np.char.zfill(np.round(load_data['q_b_mvar'], 6).astype(str), 10)),
                            'q_c_mvar': ','.join(np.char.zfill(np.round(load_data['q_c_mvar'], 6).astype(str), 10)),
                            }})

                        if ((self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval) and (self.case!=None):
                            # dict_save_trafo = save_pickle(dict_save_trafo, path=f'/home/pi/studies/results/{self.casefolder}/{self.case}/trafo.pkl')
                            # dict_save_bus = save_pickle(dict_save_bus, path=f'/home/pi/studies/results/{self.casefolder}/{self.case}/bus.pkl')
                            # dict_save_line = save_pickle(dict_save_line, path=f'/home/pi/studies/results/{self.casefolder}/{self.case}/line.pkl')
                            # dict_save_load = save_pickle(dict_save_load, path=f'/home/pi/studies/results/{self.casefolder}/{self.case}/load.pkl')

                            dict_save_trafo = save_data(dict_save_trafo, case=self.case,  folder=self.casefolder, filename=f'trafo.h5')
                            dict_save_bus = save_data(dict_save_bus, case=self.case,  folder=self.casefolder, filename=f'bus.h5')
                            dict_save_line = save_data(dict_save_line, case=self.case,  folder=self.casefolder, filename=f'line.h5')
                            dict_save_load = save_data(dict_save_load, case=self.case,  folder=self.casefolder, filename=f'load.h5')
                            self.start_unixtime = self.dict_common['unixtime']

                    time.sleep(self.pause)
                except Exception as e:
                    print("Error AGGREGATOR.network:{}".format(e))
                except KeyboardInterrupt:
                    if self.simulation==1 and self.save_history:
                        # dict_save_trafo = save_pickle(dict_save_trafo, path=f'/home/pi/studies/results/{self.casefolder}/{self.case}/trafo.pkl.xz')
                        # dict_save_bus = save_pickle(dict_save_bus, path=f'/home/pi/studies/results/{self.casefolder}/{self.case}/bus.pkl.xz')
                        # dict_save_line = save_pickle(dict_save_line, path=f'/home/pi/studies/results/{self.casefolder}/{self.case}/line.pkl.xz')
                        # dict_save_load = save_pickle(dict_save_load, path=f'/home/pi/studies/results/{self.casefolder}/{self.case}/load.pkl.xz')

                        dict_save_trafo = save_data(dict_save_trafo, case=self.case,  folder=self.casefolder, filename=f'trafo.h5')
                        dict_save_bus = save_data(dict_save_bus, case=self.case,  folder=self.casefolder, filename=f'bus.h5')
                        dict_save_line = save_data(dict_save_line, case=self.case,  folder=self.casefolder, filename=f'line.h5')
                        dict_save_load = save_data(dict_save_load, case=self.case,  folder=self.casefolder, filename=f'load.h5')
                        
                    print(f'Terminating grid simulator...')
                    self.pipe_agg_network1.close()
                    break
            

    def ldc_listener(self):
        ''' Get ldc_signal'''
        ip = '224.0.2.0'
        port = 17000
        timeout = 0.5
        try:
            ### 
            import spidev
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)  # (bus, device)
            self.spi.bits_per_word = 8
            self.spi.max_speed_hz = 500000
            self.spi.mode = 3
            d = {}
            while True:
                try:
                    ### receive data from main routine
                    dict_agg = self.pipe_agg_listener1.recv()
                    if len(dict_agg.keys())==0: continue
                    self.dict_common.update(dict_agg['common'])
                    if self.dict_common['is_alive']==False: 
                        raise KeyboardInterrupt
                    
                    # read ldc_signal from spi
                    s = float(self.spi.readbytes(1)[0])
                    if (s>0.0):
                        self.dict_injector.update({'ldc_signal':s, 'ldc_signal_spi':s})
                    else:
                        response = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, ip=ip, port=port, timeout=timeout, hops=1)
                        if response:
                            for k, v in response.items():
                                ip = k
                                port = 17001
                                timeout = 0.1
                                self.dict_injector.update({'ldc_signal': np.array([v])})
                        else:
                            ip = '224.0.2.0'
                            port = 17000
                            timeout = 0.5
                    self.pipe_agg_listener1.send({'injector': self.dict_injector})
                    time.sleep(self.pause)
                except Exception as e:
                    print("Error AGGREGATOR.ldc_listener:{}".format(e))
                    time.sleep(1)
                except KeyboardInterrupt:
                    print("Terminating ldc_listener...")
                    self.pipe_agg_listener1.close()
                    break

        except Exception as e:
            print("Error AGGREGATOR.ldc_listener spidev setup:{}".format(e))
            while True:
                try:
                    dict_agg = self.pipe_agg_listener1.recv()
                    if len(dict_agg.keys())==0: continue
                    self.dict_common.update(dict_agg['common'])
                    if self.dict_common['is_alive']==False: 
                        raise KeyboardInterrupt
                    ### update data by asking peers
                    response = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, ip=ip, port=port, timeout=timeout, hops=1)
                    if response:
                        for k, v in response.items():
                            ip = k
                            port = 17001
                            timeout = 0.1
                            self.dict_injector.update({'ldc_signal': np.array([v])})
                    else:
                        ip = '224.0.2.0'
                        port = 17000
                        timeout = 0.5
                    self.pipe_agg_listener1.send({'injector': self.dict_injector})
                    time.sleep(self.pause)
                except Exception as e:
                    print("Error AGGREGATOR.ldc_listener:{}".format(e))
                except KeyboardInterrupt:
                    print("Terminating ldc_listener...")
                    break
                
                

    def baseload(self):
        # print('Running house baseloads...')
        self.dict_baseload = self.dict_house
        df, validity = fetch_baseload(self.dict_common['season'])
        n_units = self.dict_devices['house']['n_units']
        self.dict_baseload['mode'] = np.zeros(n_units)
        self.dict_baseload['flexibility'] = np.zeros(n_units)
        self.save_interval += np.random.randint(0,60)
        
        dict_save = {}
        while True:
            try:
                self.dict_common.update(self.pipe_agg_baseload1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt
            
                ### update common variables
                update_from_common(self.dict_baseload, self.dict_common)

                ### update baseload
                sk = np.mod(np.add(np.divide(self.dict_baseload['schedule_skew'], 60), self.dict_common['weekminute']), 10080)  # 10080 minutes in a week
                self.dict_baseload['actual_demand'] = np.array([df.loc[x, y] for x, y in zip(sk.astype(int), self.dict_baseload['schedule'])]) + np.abs(np.random.normal(0,10,n_units))
            
                ### send update to main
                self.pipe_agg_baseload1.send(self.dict_baseload)
                
                ### fetch next batch of data
                if (self.dict_common['season']!=validity['season']):
                    df, validity = fetch_baseload(self.dict_common['season'])

                ### save data
                if self.simulation==1 and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_baseload, common=self.dict_common))
                    else:  
                        dict_save.update(prepare_data(states=self.dict_baseload, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='house.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                
                time.sleep(self.pause)
            except Exception as e:
                print("Error AGGREGATOR.baseload:", e)
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history:
                    save_data(dict_save, case=self.case,  folder=self.casefolder, filename='house.h5', summary=self.summary)
                print('Baseload simulation stopped...')
                self.pipe_agg_baseload1.close()
                break

        

    def heatpump(self):
        # print('Running heatpump...')
        n_units = self.dict_devices['heatpump']['n_units']
        self.dict_heatpump.update(
            initialize_load(
                load_type='heatpump', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        
        self.save_interval += np.random.randint(0,60)

        if (self.simulation==0):
            try:
                import SENSIBO
                dict_a_mode = {'cool':0, 'heat':1, 'fan':2, 'dry':3, 'auto':4}  # actual mode
                self.sensibo_api = SENSIBO.SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
                self.sensibo_devices = self.sensibo_api.devices()
                self.uid = self.sensibo_devices[f'ldc_heatpump_h{int(self.house_num)}']
                #self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
                # self.sensibo_history = self.sensibo_api.pod_history(self.uid)
                self.sensibo_measurement = self.sensibo_api.pod_measurement(self.uid)
                
            except Exception as e:
                print(f"Error AGGREGATOR.heatpump.setup_sensibo:{e}")
                # time.sleep(3)

            # while True:
            #     try:
            #         import RPi.GPIO as GPIO
            #         GPIO.setmode(GPIO.BOARD)
            #         GPIO.setwarnings(False)
            #         # put in closed status initially
            #         setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
            #         GPIO.output([15, 32, 36, 38, 40], [0, 0, 0, 0, 0])
            #         break
            #     except Exception as e:
            #         print("Error AGGREGATOR.heatpump.setup_gpio:", e)

        
        dict_save = {}

        
        ### initialize windows
        self.dict_window.update(initialize_device(n_parent=n_units, 
            n_device=1, device_type='window', schedule=self.dict_heatpump['schedule']))
        
        while True:
            try:
                ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
                self.dict_common.update(self.pipe_agg_heatpump1.recv())
                if self.dict_common['is_alive']==False: 
                    raise KeyboardInterrupt
                
                ### update common variables
                update_from_common(self.dict_heatpump, self.dict_common)
                
                ### update environment
                self.dict_heatpump['temp_out'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['temp_out'])
                self.dict_heatpump['humidity'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['humidity'])
                self.dict_heatpump['windspeed'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['windspeed'])
                

                ### update schedules
                update_schedules(self.dict_heatpump, self.dict_common)


                ### update window status
                self.dict_window.update(update_device(n_device=1, 
                    device_type='window', 
                    dict_startcode=self.dict_startcode, 
                    dict_self=self.dict_window, 
                    dict_parent=self.dict_heatpump, 
                    dict_common=self.dict_common))

                
                
                ### update device proposed mode, status, priority, and demand
                device_tcl(self.dict_heatpump, self.dict_common, inverter=False)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_heatpump, self.dict_common)

                ### send data to main
                self.pipe_agg_heatpump1.send(self.dict_heatpump)                    
                
                ### update solar heat
                self.dict_heatpump.update(get_solar(unixtime=self.dict_common['unixtime'], 
                    isotime=self.dict_common['isotime'], 
                    humidity=self.dict_common['humidity'], 
                    latitude=self.dict_heatpump['latitude'], 
                    longitude=self.dict_heatpump['longitude'], 
                    elevation=self.dict_heatpump['elevation'],
                    roof_tilt=self.dict_heatpump['roof_tilt'], 
                    azimuth=self.dict_heatpump['azimuth'], 
                    albedo=self.dict_heatpump['albedo'], 
                    roof_area=self.dict_heatpump['roof_area'], 
                    wall_area=self.dict_heatpump['wall_area'], 
                    window_area=self.dict_heatpump['window_area'], 
                    skylight_area=self.dict_heatpump['skylight_area']))
                

                ### update mass_flow, air density = 1.225 kg/m^3
                self.dict_heatpump['mass_flow'] = np.clip(np.multiply(self.dict_window['window0']['actual_status'], 
                        np.random.normal(1.225*0.001*0.1, 1e-6, n_units)), a_min=1e-6, a_max=0.01225)  # 0.1 liter/s

                ### update device states, e.g., temp_in, through simulation
                enduse_tcl(self.dict_heatpump)
                    

                ### temporary calculation for indoor humidity
                self.dict_heatpump['humidity_in'] = np.random.normal(1, 0.001, len(self.dict_heatpump['temp_in'])) * self.dict_common['humidity'] * 100

                if self.simulation==0 and self.dict_common['unixtime']%30<1:
                    ### get actual sensibo state every 30 seconds
                    self.dict_heatpump['charging_counter'] = np.subtract(self.dict_heatpump['charging_counter'], self.dict_common['step_size'])
                    
                    try:
                        ### query sensibo state and history
                        self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
                        # self.sensibo_history = self.sensibo_api.pod_history(self.uid)
                        self.sensibo_measurement = self.sensibo_api.pod_measurement(self.uid)

                        ### update device states, e.g., temp_in, temp_mat, actual reading
                        self.dict_heatpump['temp_in'] = np.asarray([self.sensibo_measurement['measurements']['temperature']]).reshape(-1)
                        self.dict_heatpump['temp_mat'] = np.asarray([self.sensibo_measurement['measurements']['temperature']]).reshape(-1)
                        self.dict_heatpump['temp_in_active'] = np.asarray([self.sensibo_measurement['measurements']['temperature']]).reshape(-1)
                        ### indoor humidity (actual reading)
                        self.dict_heatpump['humidity_in'] = np.asarray([self.sensibo_measurement['measurements']['humidity']]).reshape(-1)
                        
                        ### Actions
                        self.dict_heatpump['connected'] = np.ones(n_units)  ### ardmore heatpumps are always ON
                        # print(self.sensibo_state, self.dict_heatpump['temp_max'], self.dict_heatpump['temp_min'], self.dict_heatpump['tolerance'], self.dict_heatpump['temp_target'])
                        ### change status ON/OFF
                        if self.dict_heatpump['charging_counter']<=0:
                            self.dict_heatpump['charging_counter'] = self.dict_heatpump['min_chargingtime']
                            if self.dict_heatpump['connected'][0]==1 and self.sensibo_state['on']==False:
                                self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "on", True) 
                            elif self.dict_heatpump['connected'][0]==0 and self.sensibo_state['on']==True:
                                self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "on", False)
                            # ### change mode if needed 
                            # if self.dict_heatpump['mode'][0]==1 and self.sensibo_state['mode']=='cool':
                            #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "mode", "heat")  # change to heating
                            # elif self.dict_heatpump['mode'][0]==0 and self.sensibo_state['mode']=='heat':
                            #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "mode", "cool")  # change to cooling
                            ### implement targetTemperature adjustment
                            if (self.sensibo_state['targetTemperature']!=int(self.dict_heatpump['temp_target'][0])):
                                self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "targetTemperature", int(self.dict_heatpump['temp_target'][0]))
                        
                        
                        ### additional data
                        self.dict_heatpump['mode'] = np.asarray(dict_a_mode[self.sensibo_state['mode']]).reshape(-1)
                        self.dict_heatpump['temp_target'] = np.asarray(self.sensibo_state['targetTemperature']).reshape(-1)
    
                    except Exception as e:
                        print(f"Error AGGREGATOR.heatpump.sensibo_operation:{e}")
                        # time.sleep(5)
                        ### reconnect to sensibo database
                        self.sensibo_api = SENSIBO.SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
                        self.sensibo_devices = self.sensibo_api.devices()
                        self.uid = self.sensibo_devices[f'ldc_heatpump_h{int(self.house_num)}']
                        
                            
                    
                
                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_heatpump, common=self.dict_common))
                    else:  
                        dict_save.update(prepare_data(states=self.dict_heatpump, common=self.dict_common))
                    
                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='heatpump.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)  # to give way to other threads
            except Exception as e:
                print(f'Error AGGREGATOR.heatpump:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='heatpump.h5', summary=self.summary)
                print('Terminating heatpump...')
                self.pipe_agg_heatpump1.close()
                break



    def heater(self):
        # print('Running electric heater...')
        self.dict_heater.update(
            initialize_load(
                load_type='heater', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        
        self.save_interval += np.random.randint(0,60)

        dict_save = {}
        
        ### initialize windows 
        n_units = self.dict_devices['heater']['n_units']   
        self.dict_window.update(initialize_device(n_parent=n_units, 
                n_device=1, device_type='window', schedule=self.dict_heater['schedule']))
                
        if self.simulation==0:
            while True:
                try:
                    import RPi.GPIO as GPIO
                    GPIO.setmode(GPIO.BOARD)
                    GPIO.setwarnings(False)
                    # put in closed status initially
                    setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
                    GPIO.output([15, 32, 36, 38, 40], [0, 0, 0, 0, 0])
                    break
                except Exception as e:
                    print("Error AGGREGATOR.heater.setup_gpio:", e)

        while True:
            try:
                self.dict_common.update(self.pipe_agg_heater1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt
                
                ### update common variables
                update_from_common(self.dict_heater, self.dict_common)
                
                ### update schedules
                update_schedules(self.dict_heater, self.dict_common)

                ### update window status
                self.dict_window.update(update_device(n_device=1, 
                    device_type='window', 
                    dict_startcode=self.dict_startcode, 
                    dict_self=self.dict_window, 
                    dict_parent=self.dict_heater, 
                    dict_common=self.dict_common))

                                       
                
                ### update device proposed mode, status, priority, and demand
                device_tcl(self.dict_heater, self.dict_common, inverter=False)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_heater, self.dict_common)

                ### send data to main  
                self.pipe_agg_heater1.send(self.dict_heater)
                
                ### update weather
                self.dict_heater['temp_out'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['temp_out'])
                self.dict_heater['humidity'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['humidity'])
                self.dict_heater['windspeed'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['windspeed'])
                
                ### update solar heat
                self.dict_heater.update(get_solar(unixtime=self.dict_common['unixtime'], 
                    isotime=self.dict_common['isotime'], 
                    humidity=self.dict_common['humidity'], 
                    latitude=self.dict_heater['latitude'], 
                    longitude=self.dict_heater['longitude'], 
                    elevation=self.dict_heater['elevation'],
                    roof_tilt=self.dict_heater['roof_tilt'], 
                    azimuth=self.dict_heater['azimuth'], 
                    albedo=self.dict_heater['albedo'], 
                    roof_area=self.dict_heater['roof_area'], 
                    wall_area=self.dict_heater['wall_area'], 
                    window_area=self.dict_heater['window_area'], 
                    skylight_area=self.dict_heater['skylight_area']))

                
                ### update mass_flow, air density = 1.225 kg/m^3 at 15 degC 101.325kPa (sea level)
                self.dict_heater['mass_flow'] = np.clip(np.multiply(self.dict_window['window0']['actual_status'], 
                        np.random.normal(1.225*0.001*0.1, 1e-6, n_units)), a_min=1e-6, a_max=0.01225) # 0.1L/s
                
                ### update device states, e.g., temp_in, temp_mat, through simulation
                enduse_tcl(self.dict_heater)
                

                
                ### temporary calculation for indoor humidity
                self.dict_heater['humidity_in'] = np.random.normal(1, 0.001, len(self.dict_heater['temp_in'])) * self.dict_common['humidity'] 

                

                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_heater, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_heater, common=self.dict_common))
                    
                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='heater.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                # to give way to other threads
                time.sleep(self.pause)  
            except Exception as e:
                print(f'Error heater:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='heater.h5', summary=self.summary)
                print('Terminating heater...')
                self.pipe_agg_heater1.close()
                break       
        

    def waterheater(self):
        # print('Running waterheater...')
        self.dict_waterheater.update(
            initialize_load(
                load_type='waterheater', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        
        self.save_interval += np.random.randint(0,60)

        ip = f"{'.'.join(self.local_ip.split('.')[:-1])}.113"
        port = 17001
        timeout = 0.2
        ### initialize water valves    
        n_units = self.dict_devices['waterheater']['n_units']
        self.dict_valve.update(initialize_device(n_parent=n_units, 
                n_device=1, device_type='valve', schedule=self.dict_waterheater['schedule']))

        
        if self.simulation==0:
            while True:
                try:
                    import RPi.GPIO as GPIO
                    GPIO.setmode(GPIO.BOARD)
                    GPIO.setwarnings(False)
                    # put in closed status initially
                    setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
                    GPIO.output([15, 32, 36, 38, 40], [0, 0, 0, 0, 0])
                    break
                except Exception as e:
                    print("Error AGGREGATOR.waterheater.setup_gpio:", e)

            
        dict_save = {}
        while True:
            try:
                self.dict_common.update(self.pipe_agg_waterheater1.recv())
                if self.dict_common['is_alive']==False: 
                    raise KeyboardInterrupt
                
                ### update common variables
                update_from_common(self.dict_waterheater, self.dict_common)
                
                ### update weather
                self.dict_waterheater['temp_out'] = np.add(np.random.normal(0,0.01,n_units), self.dict_common['temp_out'])
                
                ### update valve status
                self.dict_valve.update(update_device(n_device=1, 
                    device_type='valve', 
                    dict_startcode=self.dict_startcode, 
                    dict_self=self.dict_valve, 
                    dict_parent=self.dict_waterheater, 
                    dict_common=self.dict_common))

                
                ### update device proposed mode, status, priority, and demand
                device_tcl(self.dict_waterheater, self.dict_common, inverter=False)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_waterheater, self.dict_common)

                ### send data to main
                self.pipe_agg_waterheater1.send(self.dict_waterheater)
                
                ### update mass_flow, water density = 999.1 kg/m^3 (or 0.999 kg/liter) at 15 degC 101.325kPa (sea level)
                self.dict_waterheater['mass_flow'] = np.multiply(self.dict_valve['valve0']['actual_status'], 
                        np.clip(np.random.normal(999.1*0.001*0.1, 0.01, n_units), a_min=0.01, a_max=0.25))  # assumed 0.1 L/s
                # self.dict_waterheater['mass_flow'] = np.add(self.dict_waterheater['mass_flow'], np.random.choice([0, 0.01], n_units, p=[0.9, 0.1]))
                
                ### update device states, e.g., temp_in, temp_mat, through simulation
                enduse_tcl(self.dict_waterheater)
                    


                ### get actual readings
                if self.simulation==0 and self.dict_common['unixtime']%3<1:
                    response = MULTICAST.send(dict_msg={"pcsensor":"temp_in"}, ip=ip, port=port, timeout=timeout, hops=1)
                    if response:
                        self.dict_waterheater['temp_in'] = np.asarray(response[ip]).reshape(-1)
                    ### execute status
                    execute_state(int(self.dict_waterheater['actual_status']), device_id=self.device_ip, report=True)
                    
                                        
                ### save data
                if self.simulation and self.save_history:
                    ### for waterheaters, both summary and individual states are recorded to check the legal compliance
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_waterheater, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_waterheater, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='waterheater.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause) # to give way to other threads
            except Exception as e:
                print(f'Error AGGREGATOR.waterheater:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: 
                    save_data(dict_save, case=self.case,  folder=self.casefolder, filename='waterheater.h5', summary=self.summary)

                print('Terminating waterheater...')
                self.pipe_agg_waterheater1.close()
                break
    

    def fridge(self):
        # print('Running fridge...')
        self.dict_fridge.update(
            initialize_load(
                load_type='fridge', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )

        self.save_interval += np.random.randint(0,60)

        dict_save = {}    

        while True:
            try:
                self.dict_common.update(self.pipe_agg_fridge1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt

                ### update common variables
                update_from_common(self.dict_fridge, self.dict_common)
                
                ### update device proposed mode, status, priority, and demand
                device_tcl(self.dict_fridge, self.dict_common, inverter=False)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_fridge, self.dict_common)

                ### send data to main
                self.pipe_agg_fridge1.send(self.dict_fridge)
                
                ### update device states, e.g., temp_in, temp_mat, through simulation
                self.dict_fridge['mass_flow'] = np.clip(np.random.normal(1.2041e-6, 1e-10, self.dict_devices['fridge']['n_units']), a_min=0, a_max=1.2041e-5) #1.2041*0.001*0.001*np.random.choice([0.01,1], self.dict_devices['fridge']['n_units'], p=[0.9,0.1]), # 10mL/s
                enduse_tcl(self.dict_fridge)
                    
                
                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_fridge, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_fridge, common=self.dict_common))
                    
                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='fridge.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)  # to give way to other threads
            except Exception as e:
                print(f'Error AGGREGATOR.fridge:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='fridge.h5', summary=self.summary)
                print('Terminating fridge...')
                self.pipe_agg_fridge1.close()
                break

        


    def freezer(self):
        # print('Running freezer...')
        dict_save = {}
        self.dict_freezer.update(
            initialize_load(
                load_type='freezer', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        
        self.save_interval += np.random.randint(0,60)

        while True:
            try:
                self.dict_common.update(self.pipe_agg_freezer1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt

                ### update common variables
                update_from_common(self.dict_freezer, self.dict_common)
                
                ### update device proposed mode, status, priority, and demand
                device_tcl(self.dict_freezer, self.dict_common, inverter=False)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_freezer, self.dict_common)

                ### send data to main
                self.pipe_agg_freezer1.send(self.dict_freezer) 
                
                ### update device states, e.g., temp_in, temp_mat, through simulation
                self.dict_freezer['mass_flow'] = np.clip(np.random.normal(1.2041e-6, 1e-10, self.dict_devices['freezer']['n_units']), a_min=0, a_max=1.2041e-5) #1.2041*0.001*0.001*np.random.choice([0.01,1], self.dict_devices['freezer']['n_units'], p=[0.9,0.1]), # 10mL/s
                enduse_tcl(self.dict_freezer)
                    

                 
                
                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_freezer, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_freezer, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case, folder=self.casefolder, filename='freezer.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)  # to give way to other threads
            except Exception as e:
                print(f'Error freezer:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='freezer.h5', summary=self.summary)
                print('Terminating freezer...')
                self.pipe_agg_freezer1.close()
                break
        

    def clotheswasher(self):
        # print('Running clotheswasher...')
        self.dict_clotheswasher.update(
            initialize_load(
                load_type='clotheswasher', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )

        self.save_interval += np.random.randint(0,60)

        ### setup the profiles
        try:
            with open('./profiles/nntcl.json') as f:
                nntcl = json.load(f)
                dict_data = nntcl['Clotheswasher']
                self.dict_clotheswasher['len_profile'] = np.array([len(dict_data[k]) for k in self.dict_clotheswasher['profile']])
            del nntcl  # free up the memory
        except Exception as e:
            print(f'Error clotheswasher setup:{e}')
        
        dict_save = {}
        ### run profiles
        while True:
            try:
                self.dict_common.update(self.pipe_agg_clotheswasher1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt
                
                ### update common variables
                update_from_common(self.dict_clotheswasher, self.dict_common)
                
                ### update schedules
                update_schedules(self.dict_clotheswasher, self.dict_common)

                ### update device proposed mode, status, priority, and demand
                device_ntcl(self.dict_clotheswasher, dict_data)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_clotheswasher, self.dict_common)
                
                ### send data to main
                self.pipe_agg_clotheswasher1.send(self.dict_clotheswasher)
                
                ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
                enduse_ntcl(self.dict_clotheswasher)

                
                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_clotheswasher, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_clotheswasher, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='clotheswasher.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)
            except Exception as e:
                print(f'Error clotheswasher run:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='clotheswasher.h5', summary=self.summary)
                print('Terminating clotheswasher...')
                self.pipe_agg_clotheswasher1.close()
                break
        

    # def clothesdryer(self):
    #     print('Running clothesdryer...')    
    #     '''
    #     g = (25 + (19*v)) * A (x_s - x)/3600  # v = air velocity on water surface, 
    #     A = exposed water surface area, x_s = kg_h20/ kg_dryair of sturated air in same temp, x = kg_h20/kg_dry air for given air temp
    #     g =  evaporation rate [kg/s]
    #     '''


    def clothesdryer(self):
        # print('Running clothesdryer...')
        self.dict_clothesdryer.update(
            initialize_load(
                load_type='clothesdryer', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )

        self.save_interval += np.random.randint(0,60)

        ### setup the profiles
        try:
            with open('./profiles/nntcl.json') as f:
                nntcl = json.load(f)
                dict_data = nntcl['Clothesdryer']
                del nntcl
            self.dict_clothesdryer['len_profile'] = np.array([len(dict_data[k]) for k in self.dict_clothesdryer['profile']])
        except Exception as e:
            print(f'Error clothesdryer setup:{e}')

        dict_save = {}
        ### run the profiles
        while True:
            try:
                ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
                self.dict_common.update(self.pipe_agg_clothesdryer1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt 
                
                ### update common variables
                update_from_common(self.dict_clothesdryer, self.dict_common)
                
                ### update schedules
                update_schedules(self.dict_clothesdryer, self.dict_common)

                ### update device proposed mode, status, priority, and demand
                device_ntcl(self.dict_clothesdryer, dict_data)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_clothesdryer, self.dict_common)
                
                ### send data to main
                self.pipe_agg_clothesdryer1.send(self.dict_clothesdryer)

                ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
                enduse_ntcl(self.dict_clothesdryer)

                
                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_clothesdryer, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_clothesdryer, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='clothesdryer.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)
            except Exception as e:
                print(f'Error clothesdryer run:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='clothesdryer.h5', summary=self.summary)
                print('Terminating clothesdryer...')
                self.pipe_agg_clothesdryer1.close()
                break 
        
        


    def dishwasher(self):
        # print('Running dishwasher...')
        self.dict_dishwasher.update(
            initialize_load(
                load_type='dishwasher', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        self.save_interval += np.random.randint(0,60)

        ### setup the profiles
        try:
            with open('./profiles/nntcl.json') as f:
                nntcl = json.load(f)  
                dict_data = nntcl['Dishwasher']
                del nntcl
            self.dict_dishwasher['len_profile'] = np.array([len(dict_data[k]) for k in self.dict_dishwasher['profile']])
        except Exception as e:
            print(f'Error dishwasher setup:{e}')

        dict_save = {}
        ### run the profiles
        while True:
            try:
                ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
                self.dict_common.update(self.pipe_agg_dishwasher1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt
                
                ### update common variables
                update_from_common(self.dict_dishwasher, self.dict_common)

                ### update schedules
                update_schedules(self.dict_dishwasher, self.dict_common)

                ### update device proposed mode, status, priority, and demand
                device_ntcl(self.dict_dishwasher, dict_data)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_dishwasher, self.dict_common)
                
                ### send data to main
                self.pipe_agg_dishwasher1.send(self.dict_dishwasher)

                ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
                enduse_ntcl(self.dict_dishwasher)

                
                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_dishwasher, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_dishwasher, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='dishwasher.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)
            except Exception as e:
                print(f'Error dishwasher run:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='dishwasher.h5', summary=self.summary)
                print('Terminating dishwasher...')
                self.pipe_agg_dishwasher1.close()
                break
        


    def ev(self):
        # print('Running electric vehicle model...')
        self.dict_ev.update(
            initialize_load(
                load_type='ev', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        self.save_interval += np.random.randint(0,60)
        ### setup the profiles
        try:
            with pd.HDFStore('/home/pi/ldc_project/ldc_simulator/profiles/ev_battery.h5', 'r') as store:
                df = store.select('records')  
        except Exception as e:
            print(f'Error electric_vehicle setup:{e}')

        n_units = self.dict_devices['ev']['n_units']
        dict_save = {}
        ### run profiles
        while True:
            try:
                self.dict_common.update(self.pipe_agg_ev1.recv())
                self.dict_ev['unixtime'] = np.ones(n_units)*self.dict_common['unixtime']
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt 
                
                ### update common variables
                update_from_common(self.dict_ev, self.dict_common)
                
                ### update schedules
                update_schedules(self.dict_ev, self.dict_common)

                ### update device proposed mode, status, priority, and demand
                device_battery(self.dict_ev)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_ev, self.dict_common)
                
                ### send data to main
                self.pipe_agg_ev1.send(self.dict_ev)

                ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
                enduse_battery(self.dict_ev)
                
                
                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_ev, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_ev, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='ev.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)
            except Exception as e:
                print(f'Error ev run:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='ev.h5', summary=self.summary)
                print('Terminating electric vehicle...')
                self.pipe_agg_ev1.close()
                break 
        


    def storage(self):
        # print('Running battery storage model...')
        self.dict_storage.update(
            initialize_load(
                load_type='storage', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        self.save_interval += np.random.randint(0,60)
        dict_save = {}
        while True:
            try:
                self.dict_common.update(self.pipe_agg_storage1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt
                
                ### update common variables
                update_from_common(self.dict_storage, self.dict_common)
                
                ### update device proposed mode, status, priority, and demand
                device_battery(self.dict_storage)

                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_storage, self.dict_common)
                
                ### send data to main
                self.pipe_agg_storage1.send(self.dict_storage)

                ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
                enduse_battery(self.dict_storage)

                

                
                ### save data
                if self.simulation and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_storage, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_storage, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='storage.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)
            except Exception as e:
                print("Error AGGREGATOR.storage:{}".format(e))
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='storage.h5', summary=self.summary)
                print("Terminating battery storage...")
                self.pipe_agg_storage1.close()
                break
        

    def solar(self):
        # print('Running solar panel model...')
        self.dict_solar.update(
            initialize_load(
                load_type='solar', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        df_clearness = pd.read_pickle('/home/pi/ldc_project/ldc_simulator/profiles/clearness.pkl.xz', compression='infer')
        
        self.save_interval += np.random.randint(0,60)
        dict_save = {}
        while True:
            try:
                self.dict_common.update(self.pipe_agg_solar1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt

                ### update common variables
                update_from_common(self.dict_solar, self.dict_common)
                
                self.dict_solar['irradiance_roof'] = solar.get_irradiance(
                            unixtime=self.dict_common['unixtime'],
                            humidity=self.dict_common['humidity'],
                            latitude=self.dict_solar['latitude'],
                            longitude=self.dict_solar['longitude'],
                            elevation=self.dict_solar['elevation'],
                            tilt=self.dict_solar['roof_tilt'],
                            azimuth=self.dict_solar['azimuth'],
                            albedo=self.dict_solar['albedo'],
                            isotime=self.dict_common['isotime']
                            )

                self.dict_solar['irradiance_roof'] = self.dict_solar['irradiance_roof'] * np.random.normal(df_clearness.loc[self.dict_common['weekminute'], 'clearness'], 0.003)

                
                self.dict_solar['actual_demand'] = np.multiply(np.multiply(self.dict_solar['capacity'], self.dict_solar['irradiance_roof']/1e3), self.dict_solar['inverter_efficiency'])  * -1
                # Note:  irradiance is divided by 1000 since pv rating is based on standard 1000W/m2 irradiance
                
                ### update ldc_dongle approval for the proposed status and demand
                ldc_dongle(self.dict_solar, self.dict_common)

                self.dict_solar['actual_demand'] = np.multiply(self.dict_solar['actual_demand'], 1.0-(np.clip(self.dict_solar['priority_offset']*0.1, a_min=0.0, a_max=1.0))).round(3)
                

                ### send data to main
                self.pipe_agg_solar1.send(self.dict_solar)

                ### save data
                if self.simulation==1 and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_solar, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_solar, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='solar.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)
            except Exception as e:
                print(f'Error solar:{e}')
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='solar.h5', summary=self.summary)
                print('Terminating solar PV')
                self.pipe_agg_solar1.close()
                break
        


    def wind(self):
        # print('Running wind turbine model...')
        self.dict_wind.update(
            initialize_load(
                load_type='wind', 
                dict_devices=self.dict_devices,
                dict_house=self.dict_house, 
                idx=self.idx, 
                distribution=self.distribution,
                common=self.dict_common,
                )
            )
        self.save_interval += np.random.randint(0,60)
        dict_save = {}
        while True:
            try:
                self.dict_common.update(self.pipe_agg_wind1.recv())
                if self.dict_common['is_alive']==False:
                    raise KeyboardInterrupt
                
                ### update common variables
                update_from_common(self.dict_wind, self.dict_common)
                
                ### send data to main
                self.pipe_agg_wind1.send(self.dict_wind)

                ### save data
                if self.simulation==1 and self.save_history:
                    if self.summary:
                        dict_save.update(prepare_summary(states=self.dict_wind, common=self.dict_common))
                    else:
                        dict_save.update(prepare_data(states=self.dict_wind, common=self.dict_common))

                    if (self.dict_common['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
                        dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='wind.h5', summary=self.summary)
                        self.start_unixtime = self.dict_common['unixtime']

                time.sleep(self.pause)
            except Exception as e:
                print("Error AGGREGATOR.wind:{}".format(e))
            except KeyboardInterrupt:
                if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='wind.h5', summary=self.summary)
                print("Terminating wind turbine...")
                self.pipe_agg_wind1.close()
                break
        


    def valve(self):
        # opening and closing of water valves
        # print('Emulating valves opening/closing...')
        while True:
            try:
                import temper
                import RPi.GPIO as GPIO
                import re
                pcsensor = temper.Temper()
                GPIO.setmode(GPIO.BOARD)
                GPIO.setwarnings(False)
                # put in closed status initially
                setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
                GPIO.output([15, 32, 36, 38, 40], [0, 0, 0, 0, 0])
                break
            except Exception as e:
                print("Error AGGREGATOR.window.setup_gpio:", e)

        self.dict_valve.update(initialize_device(n_parent=1, 
                n_device=3, device_type='valve', schedule=self.dict_house['schedule']))
        water_temp = None
        dict_pcsensor = {}
        while True:
            try:
                dict_agg = self.pipe_agg_valve1.recv()
                if len(dict_agg.keys())==0: continue
                self.dict_common.update(dict_agg['common'])
                if self.dict_common['is_alive']==False: 
                    raise KeyboardInterrupt
                
                ### update data
                self.dict_valve.update(update_device(n_device=3, 
                    device_type='valve', 
                    dict_startcode=self.dict_startcode, 
                    dict_self=self.dict_valve, 
                    dict_parent=self.dict_house, 
                    dict_common=self.dict_common))
                
                    
                ### execute status
                if self.device_ip==113:  # only execute on hot valve to conserve water
                    execute_state(int(self.dict_valve[f'valve{self.device_ip-113}']['actual_status'][0]), device_id=self.device_ip, report=True)
                    ### read temperature
                    try:
                        results = read_temp_sensor()
                        if results: 
                            water_temp = float(re.findall("[-.\d]+", results.split()[-1])[0])
                    except:
                        results = pcsensor.read()
                        if results:
                            water_temp = results[0]['internal temperature']
                        
                    if water_temp:
                        dict_pcsensor.update({'temp_in': water_temp})
                
                ### send data to main
                self.pipe_agg_valve1.send({'valve': dict([(f'{k}_actual_status', v['actual_status'][0]) for k, v in self.dict_valve.items() if k.startswith('valve')]), 'pcsensor': dict_pcsensor})        
                time.sleep(self.pause)
            except Exception as e:
                print(f'Error valve loop:{e}')
            except KeyboardInterrupt:
                print('Terminating watervalve...')
                self.pipe_agg_valve1.close()
                break      
        

    def window(self):
        ### this method affects the opening and closing of windows, impacts the air change per hour
        # print('Emulating window opening / closing...')
        while True:
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BOARD)
                GPIO.setwarnings(False)
                # put in closed status initially
                setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
                GPIO.output([15, 32, 36, 38, 40], [0, 0, 0, 0, 0])
                break
            except Exception as e:
                print("Error AGGREGATOR.window.setup_gpio:", e)

        self.dict_window.update(initialize_device(n_parent=1, 
                n_device=5, device_type='window', schedule=self.dict_house['schedule']))

        while True:
            try:
                dict_agg = self.pipe_agg_window1.recv()
                if len(dict_agg.keys())==0: continue
                self.dict_common.update(dict_agg['common'])
                if self.dict_common['is_alive']==False: 
                    raise KeyboardInterrupt
                
                ### update data
                self.dict_window.update(update_device(n_device=5, 
                    device_type='window', 
                    dict_startcode=self.dict_startcode, 
                    dict_self=self.dict_window, 
                    dict_parent=self.dict_house, 
                    dict_common=self.dict_common))

                ### send data to main
                self.pipe_agg_window1.send({'window': dict([(f'{w}_actual_status', self.dict_window[w]['actual_status'][0]) for w in self.dict_window.keys() if w.startswith('window')])})
                ### execute status
                execute_state(int(self.dict_window[f'window{self.device_ip-118}']['actual_status'][0]), 
                    device_id=self.device_ip, report=True)  
                time.sleep(self.pause)
            except Exception as e:
                print(f'Error window:{e}')
            except KeyboardInterrupt:
                print('Window simulation stopped...')
                self.pipe_agg_window1.close()
                break

    def door(self):
        ### this method affects the opening and closing of doors, impacts the air change per hour
        # print('Emulating door opening / closing...')
        while True:
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BOARD)
                GPIO.setwarnings(False)
                # put in closed status initially
                setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
                GPIO.output([15, 32, 36, 38, 40], [0, 0, 0, 0, 0])
                break
            except Exception as e:
                print("Error AGGREGATOR.door.setup_gpio:", e)

        ### setup variables
        self.dict_door.update(initialize_device(n_parent=1, 
                n_device=3, device_type='door', schedule=self.dict_house['schedule']))
        
        while True:
            try:
                dict_agg = self.pipe_agg_door1.recv()
                if len(dict_agg.keys())==0: continue
                self.dict_common.update(dict_agg['common'])
                if self.dict_common['is_alive']==False: 
                    raise KeyboardInterrupt
                
                ### update data
                self.dict_door.update(update_device(n_device=3, 
                    device_type='door', 
                    dict_startcode=self.dict_startcode, 
                    dict_self=self.dict_door, 
                    dict_parent=self.dict_house, 
                    dict_common=self.dict_common))
                
                ### send data to main
                self.pipe_agg_door1.send({'door': dict([(f'{w}_actual_status', self.dict_door[w]['actual_status'][0]) for w in self.dict_door.keys() if w.startswith('door')])})
                ### execute status
                execute_state(int(self.dict_door[f'door{self.device_ip-123}']['actual_status'][0]), device_id=self.device_ip, report=True)
                time.sleep(self.pause)
            except Exception as e:
                print(f'Error door:{e}')
            except KeyboardInterrupt:
                print('Door simulation stopped...')
                self.pipe_agg_door1.close()
                break
             


                

    def drive_grainy(self):
        # initialization to drive the pifacedigital
        while True:
            try:
                ### setup raspi
                import serial
                import pifacedigitalio
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BOARD)
                GPIO.setwarnings(False)
                self.pins = [0,0,0,0,0,0,0,0]
                self.pf = pifacedigitalio.PiFaceDigital()
                self.df_relay, self.df_states = FUNCTIONS.create_states(report=False)  # create power levels based on resistor bank
                print('piface setup successfull...')
                
                ### declare variables 
                self.dict_history = {}
                dict_agg = {}
                last_day = datetime.datetime.now().strftime("%Y_%m_%d")
                subnet = '.'.join(self.local_ip.split('.')[:-1])

                ### scan for peers
                peer_states = {}
                [peer_states.update(MULTICAST.send(dict_msg={'states':'all'}, ip=f'{subnet}.{x}', port=17001, timeout=0.5, data_bytes=4096, hops=1)) for x in range(100, 114)]
                peer_address = [k for k, v in peer_states.items() if (v and not (k.endswith('.100') or k.endswith('.101')))]
                print(f"Peers:{peer_address}")
                break
            except Exception as e:
                print(f"Error AGGREGATOR.drive_grainy.setup:{e}")
                time.sleep(30)
            except KeyboardInterrupt:
                break

        while True:
            try:
                ### get data from local process
                dict_agg = self.pipe_agg_grainy1.recv()
                if len(dict_agg.keys())==0: 
                    continue
                
                self.dict_common.update(dict_agg['common'])
                if self.dict_common['is_alive']==False: 
                    raise KeyboardInterrupt
                
                self.dict_summary_demand = dict_agg['summary']['demand'] 
                ### get peer states
                self.dict_state = dict_agg['states']
                [peer_states.update(MULTICAST.send(dict_msg={'states':'all'}, ip=ip, port=17001, timeout=0.2, data_bytes=4096, hops=1)) for ip in peer_address]
                for address, state in peer_states.items():
                    self.dict_state.update(state)
                    for k, v in state.items():
                        if k.endswith('actual_demand'):
                            self.dict_summary_demand.update({k:np.sum(v)})

                ### add all demand except heatpump and waterheater demand
                total = np.sum([np.sum(self.dict_summary_demand[k]) for k in self.dict_summary_demand.keys() if not (k.startswith('heatpump') or k.startswith('waterheater'))])
                total = min([total, 10e3]) #limit to 10kW

                ### convert total load value into 8-bit binary to drive 8 pinouts of piface
                newpins, grainy, chroma = FUNCTIONS.relay_pinouts(total, self.df_relay, self.df_states, report=False)
                
                ### execute piface command
                for i in range(len(self.pins)):
                    if self.pins[i]==0 and newpins[i]==1:
                        self.pf.output_pins[i].turn_on()
                    elif self.pins[i]==1 and newpins[i]==0:
                        self.pf.output_pins[i].turn_off()
                self.pins = newpins  # store updated pin states

                ### execute chroma emulation, send through rs232
                rs232 = serial.Serial(
                    port='/dev/ttyUSB0',
                    baudrate = 57600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=1)
                if chroma<=0:
                    rs232.write(b'LOAD OFF\r\n')
                else:    
                    rs232.write(b'CURR:PEAK:MAX 28\r\n')
                    rs232.write(b'MODE POW\r\n')
                    cmd = 'POW '+ str(chroma) +'\r\n'
                    rs232.write(cmd.encode())
                    rs232.write(b'LOAD ON\r\n')

                
                ### update meter reading
                peer_states.update(MULTICAST.send(dict_msg={'states':'all'}, ip=f'{subnet}.101', port=17001, timeout=0.2, data_bytes=4096, hops=1))
                for address, state in peer_states.items():
                    self.dict_state.update(state)
                    
                ### save all states
                self.dict_state.update({"unixtime": self.dict_common['unixtime'] })
                self.dict_history.update({self.dict_common['unixtime']: {k: np.asarray(v).reshape(-1)[0] for k, v in self.dict_state.items()}})
                
                # self.dict_history = self.save_pickle(dict_data=self.dict_history, path=f'/home/pi/ldc_project/history/H{self.house_num}_{self.dict_common["today"]}.pkl')
                ### compress saved data at start of new day
                # if self.dict_common['today']!=last_day:
                #     self.compress_pickle(path=f'/home/pi/ldc_project/history/H{self.house_num}_{last_day}.pkl')
                # last_day = self.dict_common['today']

                self.dict_history = self.save_pickle(dict_data=self.dict_history, path=f'/home/pi/ldc_project/history/H{self.house_num}_{int(time.time()*1000)}.pkl.xz')

                ### update peer address
                if (self.dict_common['unixtime']%60 < 1):
                    peer_states = {}
                    [peer_states.update(MULTICAST.send(dict_msg={'states':'all'}, ip=f'{subnet}.{x}', port=17001, timeout=0.2, data_bytes=4096, hops=1)) for x in range(100, 114)]
                    peer_address = [k for k, v in peer_states.items() if (v and not (k.endswith('.100') or k.endswith('.101')))]
                    
                ### update state of other devices, e.g., doors, windows
                if (self.dict_common['unixtime'] % 15 < 1) and (self.house_num==1):
                    [peer_states.update(MULTICAST.send(dict_msg={'states':'all'}, ip=f'192.168.11.{x}', port=17001, timeout=0.2, data_bytes=4096, hops=1)) for x in range(114, 126)]
                    
                self.pipe_agg_grainy1.send({'emulated_demand': {'grainy': grainy, 'chroma': chroma}})
                time.sleep(self.pause)
            except KeyboardInterrupt:
                print("Terminating grainy load driver...")
                self.pipe_agg_grainy1.close()
                for i in range(len(self.pins)):
                    self.pf.output_pins[i].turn_off()
                break
            except Exception as e:
                print("Error drive_grainy:", e)
                self.pipe_agg_grainy1.send({})
            

    @staticmethod
    def save_pickle(dict_data, path='history/data.pkl.xz'):
        'Save data as pickle file.'
        try:
            df_all = pd.DataFrame.from_dict(dict_data, orient='index')#.reset_index(drop=True)#.astype(float)
            # try:
            #     on_disk = pd.read_pickle(path, compression='infer').reset_index(drop=True)
            #     df_all = pd.concat([on_disk, df_all], axis=0, sort=False).reset_index(drop=True)
            #     df_all['unixtime'] = df_all['unixtime'].astype(int)
            #     df_all = df_all.groupby('unixtime').mean().reset_index(drop=False)
            # except Exception as e:
            #     pass


            df_all.to_pickle(path, compression='infer')
            return {}
        except Exception as e:
            print("Error save_pickle:", e)
            return {} #dict_data 

    @staticmethod
    def compress_pickle(path):
        '''
        Convert feather file to pkl.xz to reduce size 
        '''
        try:
            df_all = pd.read_pickle(path, compression='infer').reset_index(drop=True)
            df_all.to_pickle(f'{path}.xz', compression='infer')
            # if not df_all.empty:
            #     os.remove(path)
        except Exception as e:
            print("Error compress_pickle:", e)
            


    def meter(self):
        meters = []  # holder of all meter instances

        from METER import EnergyMeter
        meters.append(EnergyMeter(house=f'H{self.house_num}', IDs=[0]))
        
        if self.house_num in [4, 5]:
            from pvcom import SolarMonitor
            meters.append(SolarMonitor(house_id=f'H{self.house_num}'))

        self.dict_meter = {}
        dict_history = {}
        while True:
            try:
                dict_agg = self.pipe_agg_meter1.recv()
                if len(dict_agg.keys())==0: continue
                self.dict_common.update(dict_agg['common'])
                if self.dict_common['is_alive']==False: 
                    raise KeyboardInterrupt
                
                
                ### get meter data
                for m in meters:
                    self.dict_meter.update(m.get_meter_data(report=self.report))  
                

                self.pipe_agg_meter1.send({'meter': self.dict_meter})

                time.sleep(self.pause)
            except KeyboardInterrupt:
                print("meter stopped...")
                del EM1
                self.pipe_agg_meter1.close()
                break
            except Exception as e:
                print(f'Error meter:{e}')


    def connect_udp_socket(self, ip, port, multicast=True):
        'Setup socket connection'
        while True:
            try:
                udp_address_port = (ip, port)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # sock.settimeout(60)  
                sock.bind(udp_address_port)
                if multicast:
                    group = socket.inet_aton(ip)
                    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,mreq)
                print(f'socket created: {udp_address_port}')
                return sock
            except Exception as e:
                print("Error in AGGREGATOR.connect_udp_socket:",e)
                print("Retrying...")
                time.sleep(3)

    def receive_respond(self, sock, multicast=True):
        'Receive and respond to clients'
        self.dict_config = read_json('/home/pi/ldc_project/config_self.json')
        while True:
            ### receive message from network
            data, address = sock.recvfrom(4096)
            msg_in = data.decode("utf-8").replace("'", "\"")
            if msg_in:
                try:
                    # t = time.perf_counter()
                    ### receive data from main routine
                    # if multicast:
                    #     self.pipe_agg_multicast1.send({'multicast': msg_in})
                    #     self.dict_agg = self.pipe_agg_multicast1.recv()
                    # else:
                    #     self.pipe_agg_udp1.send({'multicast': msg_in})
                    #     self.dict_agg = self.pipe_agg_udp1.recv()

                    if len(self.dict_agg.keys())==0: 
                        continue

                    # self.dict_common.update(self.dict_agg['common'])

                    # if self.dict_common['is_alive']==False: 
                    #     raise KeyboardInterrupt

                    if not self.dict_agg['common']['is_alive']:
                        raise KeyboardInterrupt

                    ### interpret packet and respond
                    dict_msg = json.loads(msg_in)
                    rcv_keys = dict_msg.keys()
                    agg_keys = self.dict_agg.keys()

                    for k, v in dict_msg.items():
                        if k in agg_keys:
                            if v=='all':
                                sock.sendto(str(self.dict_agg[k]).encode("utf-8"), address)
                            elif v in self.dict_agg[k].keys():
                                sock.sendto(str(self.dict_agg[k][dict_msg[k]]).encode("utf-8"), address)
                        if k=='config':
                            sock.sendto(str(self.dict_config).encode("utf-8"), address)

    
                    # print(dict_msg, time.perf_counter()-t)
                    time.sleep(self.pause) 
                except socket.timeout as err:
                    raise err
                except Exception as e:
                    raise Exception
                except KeyboardInterrupt:
                    raise KeyboardInterrupt
        
    def multicast_server(self):
        'Receive multicast message from the group'
        while True:
            try:
                sock = self.connect_udp_socket(ip='224.0.2.0', port=17000, multicast=True)
                # Receive/respond loop
                self.receive_respond(sock, multicast=True)  
            except socket.timeout as err:
                print(f"Error socket timeout:{err}")
            except Exception as e:
                print(f"Error AGGREGATOR.multicast_server:{e}")
            except KeyboardInterrupt:
                ### inform main of stoppage
                print("multicast receiver stopped...")   
                sock.close()
                break
            

    def udp_server(self):
        'Receive multicast message from the group'
        while True:
            try:
                sock = self.connect_udp_socket(ip=self.local_ip, port=17001, multicast=False)
                # Receive/respond loop
                self.receive_respond(sock, multicast=False)
            except socket.timeout as err:
                print(f"Error socket timeout:{err}")
            except Exception as e:
                print(f"Error AGGREGATOR.udp_server:{e}")
            except KeyboardInterrupt:
                ### inform main of stoppage
                print("udp server stopped...")   
                sock.close()
                break

            # ready_to_read, ready_to_write, in_error = \
            #          select.select(
            #             potential_readers,
            #             potential_writers,
            #             potential_errs,
            #             timeout)


    # def tcp_server(self):
    #   try:
    #     # Create a TCP/IP socket
    #     tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     # Bind the socket to the port
    #     tcp_address_port = (self.local_ip, 17002)
    #     print('starting tcp_comm on {} port {}'.format(*tcp_address_port))
    #     tcp_sock.bind(tcp_address_port)
    #     # Listen for incoming connections
    #     tcp_sock.listen(100)  # listen to up to 100 clients
            
    #     ### receive data from main routine
    #     while True:
    #       try:
    #         dict_agg = self.pipe_agg_tcp1.recv()
    #         if len(dict_agg.keys())==0: continue
    #         self.dict_common.update(dict_agg['common'])
    #         if self.dict_common['is_alive']==False: 
    #           raise KeyboardInterrupt
                    
    #         self.pipe_agg_tcp1.send({'tcp':{}})
    #         client, address = tcp_sock.accept()  # wait for connection
    #         client.settimeout(sec)  # close client if inactive for 60 seconds
    #         threading.Thread(target=self.listen_to_client, args=(client, address)).start()
                            
    #       except KeyboardInterrupt:
    #         break
    #       except Exception as e:
    #         print("Error in tcp_server receive_msg:", e)
    #       finally:
    #         connection.close()
    #   except Exception as e:
    #     print(time.time(), "Error in tcp_server connect:",e)
    #   finally:
    #     tcp_sock.shutdown(socket.SHUT_RDWR)
    #     tcp_sock.close()


    # def listen_to_client(self, client, address):
    #   size = 2**16
    #   while True:
    #     try:
    #       data = client.recv(size)
    #       if data:
    #         # If data is received
    #         message = data.decode("utf-8")
    #         dict_msg = ast.literal_eval(message)
    #         if list(dict_msg)[0] in ['A0', 'A1', 'A2', 'A3', 'A4']:
    #           client.sendall(str(self.dict_agg).encode())
    #         else:
    #           # send ldc command as response
    #           self.dict_cmd = self.get_cmd()
    #           client.sendall(str(self.dict_cmd).encode())
    #       else:
    #         raise Exception('Client disconnected')
    #     except Exception as e:
    #         print("Error:", e)
    #         client.close()
    #         return False
    #     finally:
    #         client.close()

        
                                             
        
    
    # def history(self):
    #   dict_save = {
    #     'baseload':{}, 
    #     'clothesdryer':{}, 
    #     'clotheswasher':{}, 
    #     'dishwasher':{}, 
    #     'freezer':{}, 
    #     'fridge':{}, 
    #     'heater':{}, 
    #     'heatpump':{}, 
    #     'waterheater':{}
    #   }
    #   while True:
    #     try:
    #       dict_agg = self.pipe_agg_history1.recv()
    #       if len(dict_agg.keys())==0: continue
    #       if dict_agg['common']['is_alive']==False: 
    #         raise KeyboardInterrupt
                
    #       for k in dict_agg['states'].keys():
    #         if self.summary:
    #           dict_save[k].update(prepare_summary(states=dict_agg['states'][k], common=dict_agg['common']))
    #         else:
    #           dict_save[k].update(prepare_data(states=dict_agg['states'][k], common=dict_agg['common']))

    #         if (len(dict_save[k].keys())>=self.save_interval) and (self.case!=None):
    #           dict_save[k] = save_data(dict_agg['states'][k], case=self.case,  folder=self.casefolder, filename=f'{k}.h5', summary=self.summary)

    #       self.pipe_agg_history1.send({'history':{}})
    #       time.sleep(self.pause)
    #     except IOError:
    #       break
    #     except KeyboardInterrupt:
    #       for k in dict_agg['states'].keys():
    #         save_data(dict_agg['states'][k], case=self.case,  folder=self.casefolder, filename=f'{k}.h5', summary=self.summary)
    #       print('History stopped...')
    #       self.pipe_agg_history1.close()
    #       break
    #     except Exception as e:
    #       print(f'Error AGGREGATOR.history:{e}')
                



    def __del__(self):
        print('All processes are terminated...')
        if self.simulation==0:
            try:
                print('Reseting IOs...')
                GPIO.cleanup()         # clean up the GPIO to reset mode
                if self.device_ip in list(range(100)):
                    for i in range(len(self.pins)):
                        self.pf.output_pins[i].turn_off()
            except Exception as e:
                print(f'Error reseting IOs:{e}')







