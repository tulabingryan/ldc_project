
from MODELS import *

# def send_msgs(conn, msgs)
#   for msg in msgs:
#     conn.send(msg)
#   conn.close()

# def recv_msg(conn):
#   while 1:
#     msg = conn.recv()
#     if msg=='END':
#       break
#     print(msg)

# parent_conn, child_conn = multiprocessing.Pipe()


class Aggregator(object):
  """Aggregator for all objects of the system"""
  n = 0
  def __init__(self, dict_devices, timestamp, latitude, longitude, idx, local_ip, device_ip, step_size=1, 
    simulation=0, endstamp=None, case=None, casefolder='assorted', network=None, 
    algorithm='no_ldc', target='auto', distribution='per_house', ranking='static', 
    resolution=3, ki=5, save_history=True, tcl_control='direct', delay=0.0, report=False):
    super(Aggregator, self).__init__()
    multiprocessing.Process.__init__(self)
    self.daemon = False

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
    self.dict_injector = manager.dict()
    self.dict_common_manager = manager.dict()

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
    self.pipe_agg_valve0, self.pipe_agg_valve1 = multiprocessing.Pipe()
    self.pipe_agg_window0, self.pipe_agg_window1 = multiprocessing.Pipe()
    self.pipe_agg_door0, self.pipe_agg_door1 = multiprocessing.Pipe()
    self.pipe_agg_grainy0, self.pipe_agg_grainy1 = multiprocessing.Pipe()
    self.pipe_agg_comm0, self.pipe_agg_comm1 = multiprocessing.Pipe()
    self.pipe_agg_meter0, self.pipe_agg_meter1 = multiprocessing.Pipe()
    self.pipe_agg_udp0, self.pipe_agg_udp1 = multiprocessing.Pipe()
    self.pipe_agg_tcp0, self.pipe_agg_tcp1 = multiprocessing.Pipe()

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
    self.ki = ki

    if self.simulation:
      self.realtime = False
      self.timestamp = timestamp
      self.step_size = step_size
      self.endstamp = endstamp
      self.network_grid = network 
      self.casefolder = casefolder
      self.target = target
      if target in ['auto', 'tou']:
        self.target_loading = 30
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
    
    self.dict_common.update({'unixtime': self.timestamp, 'previous_error':0, 'previous_i_term':0, 'tcl_control':tcl_control,
      'case':self.case, 'algorithm':self.algorithm, 'ranking':self.ranking, 'distribution':self.distribution,
      'resolution':self.resolution, 'target':target, 'target_percent':self.target_loading})
    self.dict_common.update(clock(unixtime=self.dict_common['unixtime'], step_size=self.step_size, realtime=self.realtime))
    self.pause = 1e-64  # pause time used in thread interrupts
    self.save_interval = 10000

    self.dict_startcode = {
      'heater':3,
      'dishwasher':4,
      'clothesdryer':5,
      'clotheswasher':6,
      'storage':7,
      'ev':8,
      'fridge':9,  # always ON
      'freezer':10,  # always ON
      'heatpump':11,
      'waterheater':12,  # always ON
      'valve':13,
      'humidifier':16,
      'window':18,
      'door':23,
      'human':27
    }

    self.add_device(dict_new_devices=dict_devices)
    self.autorun()
    

  def add_device(self, dict_new_devices):
    self.factor = 1
    for load_type in dict_new_devices.keys():
      n_units = dict_new_devices[load_type]['n_units']  # new devices
      n_ldc = dict_new_devices[load_type]['n_ldc']
      if load_type in self.dict_devices.keys():
        idx = self.idx + self.dict_devices[load_type]['n_units']  # exisiting number of devices
        self.dict_devices[load_type].update({
          'n_units': self.dict_devices[load_type]['n_units'] + n_units,
          'n_ldc': self.dict_devices[load_type]['n_ldc'] + n_ldc,
          })
      else:
        idx = self.idx
        self.dict_devices.update({load_type:{ 'n_units': n_units, 'n_ldc': n_ldc }
          })  # update number of devices

    ### create house data
    if 'house' in self.dict_devices.keys():
      n_house = self.dict_devices['house']['n_units']
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
    ### run common threads
    self.list_processes = [] 
    self.common_observer = []
    self.agg_observer = []
    
    if self.simulation==1:
      self.list_processes.append(multiprocessing.Process(target=self.network, args=()))
      # self.list_processes.append(multiprocessing.Process(target=self.udp_comm, args=()))
      # create separate list_processes for each type of appliance
      for k in self.loads_to_run:
        if self.dict_devices[k]['n_units']:
          eval('self.list_processes.append(multiprocessing.Process(target=self.{}, args=()))'.format(k))
          eval(f'self.common_observer.append(self.pipe_agg_{k}0)')

    else:   
      ### threading is used in raspi implementation since only one processor is available
      self.list_processes.append(threading.Thread(target=self.udp_comm, args=()))
      self.list_processes.append(threading.Thread(target=self.ldc_listener, args=()))
      self.common_observer.extend([self.pipe_agg_listener0, self.pipe_agg_udp0, self.pipe_agg_tcp0])

      if self.device_ip==100:
        self.list_processes.append(threading.Thread(target=self.drive_grainy, args=()))
        self.agg_observer.append(self.pipe_agg_grainy0)
      if self.device_ip==101:
        self.list_processes.append(threading.Thread(target=self.meter, args=()))
        self.common_observer.append(self.pipe_agg_meter0)
      if self.device_ip in [113, 114]:
        self.list_processes.append(threading.Thread(target=self.valve, args=()))
        self.common_observer.append(self.pipe_agg_valve0)
      if self.device_ip in [118, 119, 120, 121, 122]:
        self.list_processes.append(threading.Thread(target=self.window, args=()))
        self.common_observer.append(self.pipe_agg_window0)
      if self.device_ip in [123, 124, 125]:
        self.list_processes.append(threading.Thread(target=self.door, args=()))
        self.common_observer.append(self.pipe_agg_door0)

      # create separate list_processes for each type of appliance
      for k in self.loads_to_run:
        if self.dict_devices[k]['n_units']:
          eval('self.list_processes.append(threading.Thread(target=self.{}, args=()))'.format(k))
          eval(f'self.common_observer.append(self.pipe_agg_{k}0)')

    ### setup the profiles
    try:
      print('Running schedules...')
      df_schedules = pd.read_csv('./specs/schedules.csv')      
      self.dict_schedule["schedule_profile"] =  self.dict_house["schedule"]
      '''All appliances have the same schedule_profile for each house.'''
    except Exception as e:
      print(f'Error schedules setup:{e}')
      self.dict_schedule['schedule_profile'] = [f'P{(self.idx%5) + 1}']

    # run list_processes
    self.dict_common.update({'is_alive': True, 'ldc_signal':10.0})
    for t in self.list_processes:
      t.daemon = True
      t.start()

    agg_data = {}
    factor = 0.013333  # regression factor to predict percent_loss
    pfe_mw = 2.7*1e-3
    sn_mva = 0.3
    pf = 0.9
    list_latest = []
    actual_loading = 0
    list_signal = []
    while True:
      try:
        t1 = time.perf_counter()
        ### update clock
        self.dict_common.update(clock(unixtime=self.dict_common['unixtime'],
          step_size=self.step_size, realtime=self.realtime))
        ### update weather
        self.dict_common.update(self.weather.get_weather(self.dict_common['unixtime']))
        ### update tasks
        self.dict_common['current_task'] = df_schedules.iloc[self.dict_common['weekminute']]
        '''
        NOTE: current_task values are floats wherein the integer part denotes the type of appliance, 
        and the decimal part denotes the duration. Refer to CREATOR.py for the codes of specific appliance.
        '''
        ### send common info to all device simulators
        # for k in self.loads_to_run:
        #   eval(f'self.pipe_agg_{k}0.send(self.dict_common)')

        for p in self.common_observer:
          p.send(self.dict_common)

        ### gather data from the device simulators
        for k in self.loads_to_run:
          # if eval(f'self.pipe_agg_{k}0.poll()'):
          d = eval(f'self.pipe_agg_{k}0.recv()')
          self.dict_summary_demand[f'{k}'] = [d['actual_demand'][d['house']==h].sum() for h in self.dict_house['name']]
          self.dict_summary_status[f'{k}'] = d['actual_status'].tolist()
          self.dict_summary_mode[f'{k}'] = d['mode'].tolist()
          self.dict_summary_flexibility[f'{k}'] = d['flexibility'].tolist()
          d_prep = prepare_data(states=d, common=self.dict_common)
          for t in d_prep.keys():
            for p, v in d_prep[t].items():
              self.dict_state.update({f'{k}_{p}':v})

        for p in self.agg_observer:
          p.send({'summary_demand':self.dict_summary_demand, 'common':self.dict_common})
        
        if self.simulation==1:
          p_mw = np.sum(list(self.dict_summary_demand.values()), axis=0) * 1e-6
          # p_a_mw = np.multiply(p_mw, (self.dict_house['phase']=='AN')*1)
          # p_b_mw = np.multiply(p_mw, (self.dict_house['phase']=='BN')*1)
          # p_c_mw = np.multiply(p_mw, (self.dict_house['phase']=='CN')*1)


          nogrid_percent = np.sum(p_mw)*100/(sn_mva * pf)
          loss_percent = np.power(nogrid_percent,2) * factor # factors are derived using regression as compared with pandapower simulation
          self.dict_common['loading_percent'] = nogrid_percent+loss_percent

          ### send data to network simulator
          # self.pipe_agg_network0.send({'summary_demand':{'p_mw':p_mw, 'p_a_mw':p_a_mw, 'p_b_mw': p_b_mw, 'p_c_mw': p_c_mw}, 'common':self.dict_common})
          self.pipe_agg_network0.send({'summary_demand':{'p_mw':p_mw}, 'common':self.dict_common})
          if self.pipe_agg_network0.poll():
            d = self.pipe_agg_network0.recv()
            factor = (factor*0.99) + (np.mean(d['factor']) * 0.01)
            sn_mva = np.mean(d['sn_mva'])
            pf = np.mean(d['pf'])
            pfe_mw = (0.9*pfe_mw) + (0.1*(d['loss_percent'] - (nogrid_percent*factor)))
            actual_loading = np.mean(d['loading_percent'])

          # while self.pipe_agg_network0.poll()==False: time.sleep(self.pause) ## wait till data is available  
          # d = self.pipe_agg_network0.recv()
          # factor = (factor*0.9) + (np.mean(d['factor']) * 0.1)
          # sn_mva = np.mean(d['sn_mva'])
          # pf = np.mean(d['pf'])
          # pfe_mw = (0.9*pfe_mw) + (0.1*(d['loss_percent'] - (nogrid_percent*factor)))
          # actual_loading = np.mean(d['loading_percent'])
          # self.dict_common['loading_percent'] = np.mean(d['loading_percent'])
            

          if self.target=='auto': 
            w = (self.step_size/(24*3600))
            self.target_loading = (self.dict_common['loading_percent']*w) + (self.target_loading*(1-w)) 
            # list_latest.append(self.dict_common['loading_percent'])
            # if (self.dict_common['minute']%30==1)&(self.dict_common['second']<1):  # update target every 30 minutes
            #   list_latest = list_latest[-int(3600*24/self.step_size):]
            #   self.target_loading = np.mean(list_latest)  # mean demand for the last 24 hours
          elif self.target=='tou':
            if self.dict_common['minute']<15:
              self.target_loading = 40
            elif self.dict_common['minute']>=15 and self.dict_common['minute']<30:
              self.target_loading = 60
            elif self.dict_common['minute']>=30 and self.dict_common['minute']<45:
              self.target_loading = 20
            elif self.dict_common['minute']>=45 and self.dict_common['minute']<60:
              self.target_loading = 60
            
            # if (self.dict_common['hour']>=23)|(self.dict_common['hour']<7):
            #   self.target_loading = 75
            # else:
            #   self.target_loading = 10
          self.dict_common['target_percent'] = self.target_loading
          d = ldc_injector(ldc_signal=self.dict_common['ldc_signal'], 
            latest_watt=self.dict_common['loading_percent']*1e-2*sn_mva*1e6,
            target_watt=self.target_loading*1e-2*sn_mva*1e6, 
            step_size=self.dict_common['step_size'],
            algorithm=self.algorithm,
            hour=self.dict_common['hour'],
            minute=self.dict_common['minute'],
            previous_error=self.dict_common['previous_error'],
            previous_i_term=self.dict_common['previous_i_term'],
            Ki=self.ki)
          delayed_signal = d['ldc_signal'] - (self.delay*(d['ldc_signal']-self.dict_common['ldc_signal'])/self.dict_common['step_size'])
          self.dict_common.update(d)
          
          print(self.dict_common['isotime'], 
            'ldc_signal:', np.round(self.dict_common['ldc_signal'],3), 
            'delayed_signal:', np.round(delayed_signal, 3), 
            'timeit:', np.round((time.perf_counter()-t1),4), 
            'target:', np.round(self.target_loading,3), 
            'latest:', np.round(self.dict_common['loading_percent'],3), 
            # 'factor:', np.round(factor,6), 
            # 'pf:', np.round(pf, 4),
            'tcl_control:', self.dict_common['tcl_control'],
            'case:', self.case
            )
          

          if self.dict_common['unixtime'] >= self.endstamp: raise KeyboardInterrupt          
        else:
          ### Retrieve data from IOs
          ### door
          if self.pipe_agg_door0.poll():
            dev_state = self.pipe_agg_door0.recv()
            self.dict_agg.update({'door':dev_state})
            for k in dev_state.keys():
              if k.startswith('door'):
                self.dict_state.update({f'{k}_actual_status': dev_state[k]['actual_status'][0]})
          ### window
          if self.pipe_agg_window0.poll():
            dev_state = self.pipe_agg_window0.recv()
            self.dict_agg.update({'window':dev_state})
            for k in dev_state.keys():
              if k.startswith('window'):
                self.dict_state.update({f'{k}_actual_status': dev_state[k]['actual_status'][0]})
          ### valve
          if self.pipe_agg_valve0.poll():
            dev_state = self.pipe_agg_valve0.recv()
            self.dict_agg.update({'valve':dev_state})
            for k in dev_state.keys():
              if k.startswith('valve'):
                self.dict_state.update({f'{k}_actual_status': dev_state[k]['actual_status'][0]})
              
          ### spi ldc_signal sensor
          if self.pipe_agg_listener0.poll():  
            self.dict_common.update(self.pipe_agg_listener0.recv())

          ### meter
          if self.pipe_agg_meter0.poll():
            self.dict_state.update(self.pipe_agg_meter0.recv())

          ### update dict_cmd
          try:
            self.dict_common.update(read_json('/home/pi/ldc_project/ldc_simulator/dict_cmd.txt'))
          except:
            pass

        self.dict_agg.update({
          'summary':{
              'demand': self.dict_summary_demand,
              'status': self.dict_summary_status,
              'mode': self.dict_summary_mode,
              'flexibility': self.dict_summary_flexibility},
          'states': self.dict_state,
          'common': self.dict_common
            })

        if self.report: print(self.dict_agg)
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error AGGREGATOR.autorun:{e}')
        raise KeyboardInterrupt
      except KeyboardInterrupt:
        ### send stop signal to device simulators
        for c in self.common_observer:
          c.send({'is_alive':False})
        for g in self.agg_observer:
          g.send({'summary_demand':{}, 'common':{'is_alive':False}})
        if self.simulation==1:
          self.pipe_agg_network0.send({'summary_demand':{},'common':{'is_alive':False}})
        
        for t in self.list_processes:
          t.join()

        ### close all pipes
        for c in self.common_observer:
          c.close()
        for g in self.agg_observer:
          g.close()

        if self.simulation==1:
          self.pipe_agg_network0.close()
        
        break



  def network(self):
    '''Model for electrical network'''
    print("Starting grid simulator...")
    if self.simulation:
      import pandapower as pp
      import pandapower.networks as nw
      from pandapower.pf.runpp_3ph import runpp_3ph
      
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
                    "vkr_percent": 0.78125, "pfe_kw": 2.7, "i0_percent": 0.16875,
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
        net.line.length_km = np.round(np.random.normal(0.040, 0.005, len(net.line.length_km)), 4)
     
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

      capacity = (self.dict_devices['house']['n_units'] * 5e3) * 1e-6
      self.dict_network = {'ldc_signal':100}
    

      factor = np.ones(self.dict_devices['house']['n_units'])
      pf = 0.9 # assumed powerfactor

      dict_agg = {}
      dict_save_trafo = {}
      dict_save_bus = {}
      dict_save_line = {}
      dict_save_load = {}
      while True:
        try:
          ### receive data from main routine
          while self.pipe_agg_network1.poll():
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
          runpp_3ph(net, numba=True, # recycle={'_is_elements':True, 'ppc':True, 'Ybus':True}, 
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
          trafo_data['nogrid_percent'] = np.divide(np.sum(self.dict_summary_demand['p_mw'])*100, np.multiply(trafo_data['pf'],trafo_data['sn_mva']))
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

            if (len(dict_save_trafo.keys())>=self.save_interval) and (self.case!=None):
              dict_save_trafo = save_data(dict_save_trafo, case=self.case,  folder=self.casefolder, filename=f'{self.network_grid}_trafo.h5')
              dict_save_bus = save_data(dict_save_bus, case=self.case,  folder=self.casefolder, filename=f'{self.network_grid}_bus.h5')
              dict_save_line = save_data(dict_save_line, case=self.case,  folder=self.casefolder, filename=f'{self.network_grid}_line.h5')
              dict_save_load = save_data(dict_save_load, case=self.case,  folder=self.casefolder, filename=f'{self.network_grid}_load.h5')
            
          time.sleep(self.pause)
        except Exception as e:
          print("Error AGGREGATOR.network:{}".format(e))
        except KeyboardInterrupt:
          if self.simulation==1 and self.save_history:
            dict_save_trafo = save_data(dict_save_trafo, case=self.case,  folder=self.casefolder, filename=f'{self.network_grid}_trafo.h5')
            dict_save_bus = save_data(dict_save_bus, case=self.case,  folder=self.casefolder, filename=f'{self.network_grid}_bus.h5')
            dict_save_line = save_data(dict_save_line, case=self.case,  folder=self.casefolder, filename=f'{self.network_grid}_line.h5')
            dict_save_load = save_data(dict_save_load, case=self.case,  folder=self.casefolder, filename=f'{self.network_grid}_load.h5')
            
          print(f'Terminating grid simulator...')
          self.pipe_agg_network1.close()
          break
      


  def ldc_listener(self):
    ''' Get ldc_signal'''
    print("Running ldc_listener...")
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
          self.dict_common.update(self.pipe_agg_listener1.recv())
          if self.dict_common['is_alive']==False:
            raise KeyboardInterrupt
          # read ldc_signal from spi
          s = float(self.spi.readbytes(1)[0])
          t = time.time()
          if (s>0.0):
            if self.device_ip==102:
              d.update({datetime.datetime.now():{'ldc_signal':s, 'unixtime':t}})
              if len(d.keys())>100:
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                d = save_hdf(dict_data=d, path=f'/home/pi/ldc_project/history/h{self.house_num}_dongle_{today}.h5')
            self.dict_injector.update({
              'ldc_signal':s,
              'ldc_signal_spi':s
              })
            self.pipe_agg_listener1.send(self.dict_injector)
            

          else:
            dict_s = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, 
              ip='224.0.2.0', port=17000, timeout=0.1, hops=1)
            if dict_s:
              s = dict_s["ldc_signal_spi"]
              self.dict_injector.update({
                'ldc_signal':np.array([s])
                }) 
              self.pipe_agg_listener1.send(self.dict_injector)
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
          self.dict_common.update(self.pipe_agg_listener1.recv())
          if self.dict_common['is_alive']==False:
            raise KeyboardInterrupt
          ### update data by asking peers
          dict_s = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, 
              ip='224.0.2.0', port=17000, timeout=0.1, hops=1)
          if dict_s:
            s = dict_s["ldc_signal_spi"]
            self.dict_injector.update({
              'ldc_signal':np.array([s])
              })
            self.pipe_agg_listener1.send(self.dict_injector)
          time.sleep(self.pause)
        except Exception as e:
          print("Error AGGREGATOR.ldc_listener:{}".format(e))
        except KeyboardInterrupt:
          print("Terminating ldc_listener...")
          break
        
        

  def baseload(self):
    print('Running house baseloads...')
    self.dict_baseload = self.dict_house
    df, validity = fetch_baseload(self.dict_common['season'])
    self.dict_baseload['mode'] = np.zeros(self.dict_devices['house']['n_units'])
    self.dict_baseload['flexibility'] = np.zeros(self.dict_devices['house']['n_units'])

    dict_save = {}
    while True:
      try:
        self.dict_common.update(self.pipe_agg_baseload1.recv())
        if self.dict_common['is_alive']==False:
          raise KeyboardInterrupt
        ### update baseload
        # sk = np.add(self.dict_baseload['schedule_skew'], self.dict_common['unixtime'])
        # self.dict_baseload['actual_demand'] = np.array([df.loc[x, y] for x, y in zip(sk.astype(int), self.dict_baseload['profile'])])
        if self.case.startswith('ramp') or self.case.startswith('ideal'):
          self.dict_baseload['actual_demand'] = np.ones(self.dict_devices['house']['n_units']) * 100  # set each house baseload to constant
        else:
          sk = np.mod(np.add(np.divide(self.dict_baseload['schedule_skew'], 60), self.dict_common['weekminute']), 10080)  # 10080 minutes in a week
          self.dict_baseload['actual_demand'] = np.array([df.loc[x, y] for x, y in zip(sk.astype(int), self.dict_baseload['schedule'])]) + np.random.normal(0,1,self.dict_devices['house']['n_units'])
        ### send update to main
        self.pipe_agg_baseload1.send(self.dict_baseload)
        ### fetch next batch of data
        # if (self.dict_common['unixtime']>=validity['end']):
        #   df, validity = fetch_baseload(int(self.dict_common['unixtime']), n_seconds=3600)
        if (self.dict_common['season']!=validity['season']):
          df, validity = fetch_baseload(self.dict_common['season'])
        ### save data
        if self.simulation==1 and self.save_history:
          # dict_save.update({int(self.dict_common['unixtime']):self.dict_baseload})
          dict_save.update(prepare_data(states=self.dict_baseload, common=self.dict_common))
          if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
            dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='house.h5')
          
        time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.baseload:", e)
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history:
          save_data(dict_save, case=self.case,  folder=self.casefolder, filename='house.h5')
        print('Baseload simulation stopped...')
        self.pipe_agg_baseload1.close()
        break

    

  def heatpump(self):
    print('Running heatpump...')
    n_units = self.dict_devices['heatpump']['n_units']
    self.dict_heatpump.update(initialize_load(load_type='heatpump', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))

    if (self.simulation==0)&(self.device_ip==111):
      while True:
        try:
          import SENSIBO
          dict_a_mode = {'cool':0, 'heat':1, 'fan':2, 'dry':3, 'auto':4}  # actual mode
          self.sensibo_api = SENSIBO.SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
          devices = self.sensibo_api.devices()
          self.uid = devices['ldc_heatpump_h{}'.format(int(self.house_num))]
          self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
          self.sensibo_history = self.sensibo_api.pod_history(self.uid)
          break
        except Exception as e:
          print(f"Error AGGREGATOR.heatpump.setup_sensibo:{e}")


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
          print("Error AGGREGATOR.heatpump.setup_gpio:", e)

    
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

        ### update window status
        self.dict_window.update(update_device(n_device=1, 
          device_type='window', 
          dict_startcode=self.dict_startcode, 
          dict_self=self.dict_window, 
          dict_parent=self.dict_heatpump, 
          dict_common=self.dict_common))

        ### update mass_flow, air density = 1.225 kg/m^3
        self.dict_heatpump['mass_flow'] = np.clip(np.multiply(self.dict_window['window0']['actual_status'], 
            np.random.normal(1.225*0.001*0.1, 1e-6, n_units)), a_min=1e-6, a_max=0.01225)  # 0.1 liter/s

        # ### update unixstart and unixend
        self.dict_heatpump.update(make_schedule(unixtime=self.dict_common['unixtime'],
            current_task=self.dict_common['current_task'][self.dict_heatpump['schedule']].values,
            load_type_id=self.dict_startcode['heatpump'], 
            unixstart=self.dict_heatpump['unixstart'],
            unixend=self.dict_heatpump['unixend'],
            schedule_skew=self.dict_heatpump['schedule_skew']))
        ### update if connected
        self.dict_heatpump.update(is_connected(unixtime=self.dict_common['unixtime'],
            unixstart=self.dict_heatpump['unixstart'],
            unixend=self.dict_heatpump['unixend']))      
        ### force all ldc-enabled devices to be connected
        # self.dict_heatpump['connected'] = ((self.dict_heatpump['connected']==1)|(self.dict_heatpump['with_dr']==True))*1
        ### update device proposed mode, status, priority, and demand
        self.dict_heatpump.update(device_heatpump(mode=self.dict_heatpump['mode'], 
          temp_in=self.dict_heatpump['temp_in'], 
          temp_min=self.dict_heatpump['temp_min'], 
          temp_max=self.dict_heatpump['temp_max'],
          temp_out=self.dict_common['temp_out'], 
          temp_target=self.dict_heatpump['temp_target'],
          cooling_setpoint=self.dict_heatpump['cooling_setpoint'], 
          heating_setpoint=self.dict_heatpump['heating_setpoint'],
          tolerance=self.dict_heatpump['tolerance'], 
          cooling_power=self.dict_heatpump['cooling_power'], 
          heating_power=self.dict_heatpump['heating_power'],
          cop=self.dict_heatpump['cop'],
          standby_power=self.dict_heatpump['standby_power'],
          ventilation_power=self.dict_heatpump['ventilation_power'],
          proposed_status=self.dict_heatpump['proposed_status'],
          actual_status=self.dict_heatpump['actual_status'],
          tcl_control=self.dict_common['tcl_control'])
        )
        ### update ldc_signal
        self.dict_heatpump.update(read_signal(ldc_signal=self.dict_heatpump['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'],
          resolution=self.resolution, 
          n_units=n_units,
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))

        ### update ldc_dongle approval for the proposed status and demand
        self.dict_heatpump.update(ldc_dongle(self.dict_heatpump, self.dict_common))
        ### update environment
        self.dict_heatpump['temp_out'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['temp_out'])
        self.dict_heatpump['humidity'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['humidity'])
        self.dict_heatpump['windspeed'] = np.add(np.random.normal(0, 0.01, n_units), self.dict_common['windspeed'])
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
        ### update heat from all sources
        self.dict_heatpump.update(sum_heat_sources(solar_heat=self.dict_heatpump['solar_heat'], 
          heating_power_thermal=self.dict_heatpump['heating_power_thermal'], 
          cooling_power_thermal=self.dict_heatpump['cooling_power_thermal']))
        ### update device states, e.g., temp_in, temp_mat, through simulation
        self.dict_heatpump.update(
          enduse_tcl(
            heat_all=self.dict_heatpump['heat_all'],
            temp_in=self.dict_heatpump['temp_in'],
            temp_out=self.dict_heatpump['temp_out'],
            temp_fill=self.dict_heatpump['temp_out'],
            Ua=self.dict_heatpump['Ua'],
            Cp=self.dict_heatpump['Cp'],
            Ca=self.dict_heatpump['Ca'],
            mass_flow= self.dict_heatpump['mass_flow'],
            step_size=self.dict_common['step_size'],
            )
          )

        ### temporary calculation for indoor humidity
        self.dict_heatpump['humidity_in'] = np.random.normal(1, 0.001, len(self.dict_heatpump['temp_in'])) * self.dict_common['humidity'] * 100

        if self.simulation==0:
          ### get actual sensibo state every 30 seconds
          self.dict_heatpump['charging_counter'] = np.subtract(self.dict_heatpump['charging_counter'], self.dict_common['step_size'])
          if self.dict_common['second']%30==0:
            try:
              self.sensibo_api = SENSIBO.SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
              devices = self.sensibo_api.devices()
              self.uid = devices['ldc_heatpump_h{}'.format(int(self.house_num))]
              self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
              self.sensibo_history = self.sensibo_api.pod_history(self.uid)
              self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
              self.sensibo_history = self.sensibo_api.pod_history(self.uid)
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
                ### change mode if needed 
                if self.dict_heatpump['mode'][0]==1 and self.sensibo_state['mode']=='cool':
                    self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "mode", "heat")  # change to heating
                elif self.dict_heatpump['mode'][0]==0 and self.sensibo_state['mode']=='heat':
                    self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "mode", "cool")  # change to cooling
                ### implement targetTemperature adjustment
                if (self.sensibo_state['targetTemperature']!=int(self.dict_heatpump['temp_target'][0])):
                  self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "targetTemperature", int(self.dict_heatpump['temp_target'][0]))
            except Exception as e:
              print(f"Error AGGREGATOR.heatpump.sensibo_operation:{e}")

          ### update device states, e.g., temp_in, temp_mat, actual reading
          self.dict_heatpump['temp_in'] = np.array([self.sensibo_history['temperature'][-1]['value']])
          self.dict_heatpump['temp_mat'] = np.array([self.sensibo_history['temperature'][-1]['value']])
          self.dict_heatpump['temp_in_active'] = np.array([self.sensibo_history['temperature'][-1]['value']])
          ### indoor humidity (actual reading)
          self.dict_heatpump['humidity_in'] = np.array([self.sensibo_history['humidity'][-1]['value']])
          ### additional data
          # self.dict_heatpump['mode'] = np.array([dict_a_mode[self.sensibo_state['mode']]])
          # self.dict_heatpump['temp_target'] = np.array([self.sensibo_state['targetTemperature']])
          
          
        else:

          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_heatpump})
            dict_save.update(prepare_data(states=self.dict_heatpump, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='heatpump.h5')

        ### send data to main
        self.pipe_agg_heatpump1.send(self.dict_heatpump)
        time.sleep(self.pause)  # to give way to other threads
      except Exception as e:
        print(f'Error AGGREGATOR.heatpump:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='heatpump.h5')
        print('Terminating heatpump...')
        self.pipe_agg_heatpump1.close()
        break



  def heater(self):
    print('Running electric heater...')
    self.dict_heater.update(initialize_load(load_type='heater', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))
    
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

        ### update window status
        self.dict_window.update(update_device(n_device=1, 
          device_type='window', 
          dict_startcode=self.dict_startcode, 
          dict_self=self.dict_window, 
          dict_parent=self.dict_heater, 
          dict_common=self.dict_common))

        ### update mass_flow, air density = 1.225 kg/m^3 at 15 degC 101.325kPa (sea level)
        self.dict_heater['mass_flow'] = np.clip(np.multiply(self.dict_window['window0']['actual_status'], 
            np.random.normal(1.225*0.001*0.1, 1e-6, n_units)), a_min=1e-6, a_max=0.01225) # 0.1L/s
            
        ### update unixstart and unixend
        self.dict_heater.update(
          make_schedule(unixtime=self.dict_common['unixtime'],
            current_task=self.dict_common['current_task'][self.dict_heater['schedule']].values,
            load_type_id=self.dict_startcode['heater'], # code for heaters
            unixstart=self.dict_heater['unixstart'],
            unixend=self.dict_heater['unixend'],
            schedule_skew=self.dict_heater['schedule_skew'])
          )
        ## update if connected
        self.dict_heater.update(
          is_connected(unixtime=self.dict_common['unixtime'],
            unixstart=self.dict_heater['unixstart'],
            unixend=self.dict_heater['unixend'])
          )
        ### force all ldc-enabled devices to be connected
        # self.dict_heater['connected'] = ((self.dict_heater['connected']==1)|(self.dict_heater['with_dr']==True))*1
        ### update device proposed mode, status, priority, and demand
        self.dict_heater.update(
          device_heating_resistance(mode=self.dict_heater['mode'],
            temp_in=self.dict_heater['temp_in'], 
            temp_min=self.dict_heater['temp_min'], 
            temp_max=self.dict_heater['temp_max'], 
            heating_setpoint=self.dict_heater['heating_setpoint'], 
            tolerance=self.dict_heater['tolerance'], 
            heating_power=self.dict_heater['heating_power'],
            cop=self.dict_heater['cop'],
            standby_power=self.dict_heater['standby_power'],
            ventilation_power=self.dict_heater['ventilation_power'],
            proposed_status=self.dict_heater['proposed_status'],
            actual_status=self.dict_heater['actual_status'],
            tcl_control=self.dict_common['tcl_control'])
          )
        ### update ldc_signal
        self.dict_heater.update(read_signal(ldc_signal=self.dict_heater['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=n_units),
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation
          )
        ### update ldc_dongle approval for the proposed status and demand
        self.dict_heater.update(ldc_dongle(self.dict_heater, self.dict_common))
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
        ### update heat from all sources
        self.dict_heater.update(sum_heat_sources(solar_heat=self.dict_heater['solar_heat'], 
          heating_power_thermal=self.dict_heater['heating_power_thermal'], 
          cooling_power_thermal=self.dict_heater['cooling_power_thermal']))

        ### update device states, e.g., temp_in, temp_mat, through simulation
        self.dict_heater.update(
          enduse_tcl(
            heat_all=self.dict_heater['heat_all'],
            temp_in=self.dict_heater['temp_in'],
            temp_out=self.dict_heater['temp_out'],
            temp_fill=self.dict_heater['temp_out'],
            Ua=self.dict_heater['Ua'],
            Cp=self.dict_heater['Cp'],
            Ca=self.dict_heater['Ca'],
            mass_flow= self.dict_heater['mass_flow'],
            step_size=self.dict_common['step_size'],
            )
          )


        ### temporary calculation for indoor humidity
        self.dict_heater['humidity_in'] = np.random.normal(1, 0.001, len(self.dict_heater['temp_in'])) * self.dict_common['humidity'] * 100
        
        if self.simulation==0:
          ### read actual sensor readings 
          pass
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_heater})
            dict_save.update(prepare_data(states=self.dict_heater, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='heater.h5')
          
        ### send data to main  
        self.pipe_agg_heater1.send(self.dict_heater)
        time.sleep(self.pause)  # to give way to other threads
      except Exception as e:
        print(f'Error heater:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='heater.h5')
        print('Terminating heater...')
        self.pipe_agg_heater1.close()
        break       
    

  def waterheater(self):
    print('Running waterheater...')
    self.dict_waterheater.update(initialize_load(load_type='waterheater', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))
    
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

        ### update weather
        self.dict_waterheater['temp_out'] = np.add(np.random.normal(0,0.01,n_units), self.dict_common['temp_out'])
        ### update valve status
        self.dict_valve.update(update_device(n_device=1, 
          device_type='valve', 
          dict_startcode=self.dict_startcode, 
          dict_self=self.dict_valve, 
          dict_parent=self.dict_waterheater, 
          dict_common=self.dict_common))

        ### update mass_flow, water density = 999.1 kg/m^3 (or 0.999 kg/liter) at 15 degC 101.325kPa (sea level)
        self.dict_waterheater['mass_flow'] = np.multiply(self.dict_valve['valve0']['actual_status'], 
            np.clip(np.random.normal(999.1*0.001*0.2, 0.01, n_units), a_min=0.01, a_max=0.25))  # assumed 0.2 L/s
        # self.dict_waterheater['mass_flow'] = np.add(self.dict_waterheater['mass_flow'], np.random.choice([0, 0.01], n_units, p=[0.9, 0.1]))
        ### update device proposed mode, status, priority, and demand
        self.dict_waterheater.update(
          device_heating_resistance(mode=self.dict_waterheater['mode'],
            temp_in=self.dict_waterheater['temp_in'], 
            temp_min=self.dict_waterheater['temp_min'], 
            temp_max=self.dict_waterheater['temp_max'], 
            heating_setpoint=self.dict_waterheater['heating_setpoint'], 
            tolerance=self.dict_waterheater['tolerance'], 
            heating_power=self.dict_waterheater['heating_power'],
            cop=self.dict_waterheater['cop'],
            standby_power=self.dict_waterheater['standby_power'],
            ventilation_power=self.dict_waterheater['ventilation_power'],
            proposed_status=self.dict_waterheater['proposed_status'],
            actual_status=self.dict_waterheater['actual_status'],
            tcl_control=self.dict_common['tcl_control'])
          )
        ### update ldc_signal
        self.dict_waterheater.update(read_signal(ldc_signal=self.dict_waterheater['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=n_units,
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))

        ### update ldc_dongle approval for the proposed status and demand
        self.dict_waterheater.update(ldc_dongle(self.dict_waterheater, self.dict_common))
        
        ### update device states, e.g., temp_in, temp_mat, through simulation
        self.dict_waterheater['heat_all'] = self.dict_waterheater['heating_power_thermal']
        self.dict_waterheater.update(
          enduse_tcl(
            heat_all=self.dict_waterheater['heat_all'],
            temp_in=self.dict_waterheater['temp_in'],
            temp_out=self.dict_waterheater['temp_out'],
            temp_fill=self.dict_waterheater['temp_out'],
            Ua=self.dict_waterheater['Ua'],
            Cp=self.dict_waterheater['Cp'],
            Ca=self.dict_waterheater['Ca'],
            mass_flow=self.dict_waterheater['mass_flow'],
            step_size=self.dict_common['step_size'],
            )
          )


        ### send data to main
        self.pipe_agg_waterheater1.send(self.dict_waterheater)

          
        if self.simulation==0:
          ### get actual readings
          self.dict_waterheater.update(MULTICAST.send(dict_msg={"pcsensor":"temp_in"}, ip='224.0.2.0', port=17000, timeout=0.1, hops=1))
          time.sleep(1)
          ### execute status
          # print('temp_in:', self.dict_waterheater['temp_in'], 'status:', self.dict_waterheater['actual_status'])
          execute_state(int(self.dict_waterheater['actual_status'][0]), 
            device_id=self.device_ip, report=True)
          
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_waterheater})
            dict_save.update(prepare_data(states=self.dict_waterheater, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='waterheater.h5')
            
          
        time.sleep(self.pause) # to give way to other threads
      except Exception as e:
        print(f'Error AGGREGATOR.waterheater:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='waterheater.h5')
        print('Terminating waterheater...')
        self.pipe_agg_waterheater1.close()
        break
  

  def fridge(self):
    print('Running fridge...')
    self.dict_fridge.update(initialize_load(load_type='fridge', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))

    dict_save = {}    

    while True:
      try:
        self.dict_common.update(self.pipe_agg_fridge1.recv())
        if self.dict_common['is_alive']==False:
          raise KeyboardInterrupt

        ### update device proposed mode, status, priority, and demand
        self.dict_fridge.update(
          device_cooling_compression(mode=self.dict_fridge['mode'],
            temp_in=self.dict_fridge['temp_in'], 
            temp_min=self.dict_fridge['temp_min'], 
            temp_max=self.dict_fridge['temp_max'], 
            temp_target=self.dict_fridge['temp_target'], 
            tolerance=self.dict_fridge['tolerance'], 
            cooling_power=self.dict_fridge['cooling_power'],
            cop=self.dict_fridge['cop'], 
            standby_power=self.dict_fridge['standby_power'],
            ventilation_power=self.dict_fridge['ventilation_power'],
            proposed_status=self.dict_fridge['proposed_status'],
            actual_status=self.dict_fridge['actual_status'],
            tcl_control=self.dict_common['tcl_control'])
          )
        ### update ldc_signal
        self.dict_fridge.update(read_signal(ldc_signal=self.dict_fridge['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=self.dict_devices['fridge']['n_units'],
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))
        ### update ldc_dongle approval for the proposed status and demand
        self.dict_fridge.update(ldc_dongle(self.dict_fridge, self.dict_common))
        
        ### update device states, e.g., temp_in, temp_mat, through simulation
        self.dict_fridge['mass_flow'] = np.clip(np.random.normal(1.2041e-6, 1e-10, self.dict_devices['fridge']['n_units']), a_min=0, a_max=1.2041e-5) #1.2041*0.001*0.001*np.random.choice([0.01,1], self.dict_devices['fridge']['n_units'], p=[0.9,0.1]), # 10mL/s
        self.dict_fridge['heat_all'] = self.dict_fridge['cooling_power_thermal']
        self.dict_fridge.update(
          enduse_tcl(
            heat_all=self.dict_fridge['heat_all'],
            temp_in=self.dict_fridge['temp_in'],
            temp_out=self.dict_fridge['temp_out'],
            temp_fill=self.dict_fridge['temp_out'],
            Ua=self.dict_fridge['Ua'],
            Cp=self.dict_fridge['Cp'],
            Ca=self.dict_fridge['Ca'],
            mass_flow=self.dict_fridge['mass_flow'],
            step_size=self.dict_common['step_size'],
            )
          )

        if self.simulation==0:
          ### read actual sensors in the device
          pass
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_fridge})
            dict_save.update(prepare_data(states=self.dict_fridge, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
                dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='fridge.h5')
        
        ### send data to main
        self.pipe_agg_fridge1.send(self.dict_fridge)
        time.sleep(self.pause)  # to give way to other threads
      except Exception as e:
        print(f'Error AGGREGATOR.fridge:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='fridge.h5')
        print('Terminating fridge...')
        self.pipe_agg_fridge1.close()
        break

    


  def freezer(self):
    print('Running freezer...')
    dict_save = {}
    self.dict_freezer.update(initialize_load(load_type='freezer', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))
    
    while True:
      try:
        self.dict_common.update(self.pipe_agg_freezer1.recv())
        if self.dict_common['is_alive']==False:
          raise KeyboardInterrupt

        ### update data
        ### update device proposed mode, status, priority, and demand
        self.dict_freezer.update(
          device_cooling_compression(mode=self.dict_freezer['mode'],
            temp_in=self.dict_freezer['temp_in'], 
            temp_min=self.dict_freezer['temp_min'], 
            temp_max=self.dict_freezer['temp_max'], 
            temp_target=self.dict_freezer['temp_target'], 
            tolerance=self.dict_freezer['tolerance'], 
            cooling_power=self.dict_freezer['cooling_power'],
            cop=self.dict_freezer['cop'],
            standby_power=self.dict_freezer['standby_power'],
            ventilation_power=self.dict_freezer['ventilation_power'],
            proposed_status=self.dict_freezer['proposed_status'],
            actual_status=self.dict_freezer['actual_status'],
            tcl_control=self.dict_common['tcl_control'])
          )
        ### update ldc_signal
        self.dict_freezer.update(read_signal(ldc_signal=self.dict_freezer['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=self.dict_devices['freezer']['n_units'],
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))
        ### update ldc_dongle approval for the proposed status and demand
        self.dict_freezer.update(ldc_dongle(self.dict_freezer, self.dict_common))
        
        ### update device states, e.g., temp_in, temp_mat, through simulation
        self.dict_freezer['mass_flow'] = np.clip(np.random.normal(1.2041e-6, 1e-10, self.dict_devices['freezer']['n_units']), a_min=0, a_max=1.2041e-5) #1.2041*0.001*0.001*np.random.choice([0.01,1], self.dict_devices['freezer']['n_units'], p=[0.9,0.1]), # 10mL/s
        self.dict_freezer['heat_all'] = self.dict_freezer['cooling_power_thermal']
        self.dict_freezer.update(
          enduse_tcl(
            heat_all=self.dict_freezer['heat_all'],
            temp_in=self.dict_freezer['temp_in'],
            temp_out=self.dict_freezer['temp_out'],
            temp_fill=self.dict_freezer['temp_out'],
            Ua=self.dict_freezer['Ua'],
            Cp=self.dict_freezer['Cp'],
            Ca=self.dict_freezer['Ca'],
            mass_flow=self.dict_freezer['mass_flow'],
            step_size=self.dict_common['step_size'],
            )
          )

        if self.simulation==0:
          ### read actual sensors
          pass
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_freezer})
            dict_save.update(prepare_data(states=self.dict_freezer, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case, folder=self.casefolder, filename='freezer.h5')
          
        ### send data to main
        self.pipe_agg_freezer1.send(self.dict_freezer)  
        time.sleep(self.pause)  # to give way to other threads
      except Exception as e:
        print(f'Error freezer:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='freezer.h5')
        print('Terminating freezer...')
        self.pipe_agg_freezer1.close()
        break
    

  def clotheswasher(self):
    print('Running clotheswasher...')
    self.dict_clotheswasher.update(initialize_load(load_type='clotheswasher', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))

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

        ### update unixstart and unixend
        self.dict_clotheswasher.update(
          make_schedule(unixtime=self.dict_common['unixtime'],
            current_task=self.dict_common['current_task'][self.dict_clotheswasher['schedule']].values,
            load_type_id=self.dict_startcode['clotheswasher'], 
            unixstart=self.dict_clotheswasher['unixstart'],
            unixend=self.dict_clotheswasher['unixend'],
            schedule_skew=self.dict_clotheswasher['schedule_skew'])
          )
        ## update if connected
        self.dict_clotheswasher.update(
          is_connected(unixtime=self.dict_common['unixtime'],
            unixstart=self.dict_clotheswasher['unixstart'],
            unixend=self.dict_clotheswasher['unixend'])
          )
        ### update device proposed mode, status, priority, and demand
        self.dict_clotheswasher.update(
          device_ntcl(len_profile=self.dict_clotheswasher['len_profile'],
            unixtime=self.dict_common['unixtime'], 
            unixstart=self.dict_clotheswasher['unixstart'],
            unixend=self.dict_clotheswasher['unixend'],
            connected=self.dict_clotheswasher['connected'],
            progress=self.dict_clotheswasher['progress'],
            actual_status=self.dict_clotheswasher['actual_status'],
            # proposed_demand=np.array([np.interp(x*y, np.arange(y), dict_data[k]) for k, x, y in zip(self.dict_clotheswasher['profile'], self.dict_clotheswasher['len_profile'], self.dict_clotheswasher['progress'])]).flatten()
            proposed_demand=np.array([dict_data[k][int((x*y)%x)] for k, x, y in zip(self.dict_clotheswasher['profile'], self.dict_clotheswasher['len_profile'], self.dict_clotheswasher['progress'])]).flatten()
            )
          )
        ### update ldc_signal
        self.dict_clotheswasher.update(read_signal(ldc_signal=self.dict_clotheswasher['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=self.dict_devices['clotheswasher']['n_units'],
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))
        ### update ldc_dongle approval for the proposed status and demand
        self.dict_clotheswasher.update(ldc_dongle(self.dict_clotheswasher, self.dict_common))
        
        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_clotheswasher.update(
          enduse_ntcl(len_profile=self.dict_clotheswasher['len_profile'],
            progress=self.dict_clotheswasher['progress'],
            step_size=self.dict_common['step_size'],
            actual_status=self.dict_clotheswasher['actual_status'],
            unixtime=self.dict_common['unixtime'],
            connected=self.dict_clotheswasher['connected'])
          )
        if self.simulation==0:
          ### read actual sensors
          pass
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_clotheswasher})
            dict_save.update(prepare_data(states=self.dict_clotheswasher, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='clotheswasher.h5')
          
        ### send data to main
        self.pipe_agg_clotheswasher1.send(self.dict_clotheswasher)  
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error clotheswasher run:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='clotheswasher.h5')
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
    print('Running clothesdryer...')
    self.dict_clothesdryer.update(initialize_load(load_type='clothesdryer', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))

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

        ### update unixstart and unixend
        self.dict_clothesdryer.update(
          make_schedule(unixtime=self.dict_common['unixtime'],
            current_task=self.dict_common['current_task'][self.dict_clothesdryer['schedule']].values,
            load_type_id=self.dict_startcode['clothesdryer'],
            unixstart=self.dict_clothesdryer['unixstart'],
            unixend=self.dict_clothesdryer['unixend'],
            schedule_skew=self.dict_clothesdryer['schedule_skew'])
          )
        ### update if connected
        self.dict_clothesdryer.update(
          is_connected(unixtime=self.dict_common['unixtime'],
            unixstart=self.dict_clothesdryer['unixstart'],
            unixend=self.dict_clothesdryer['unixend'])
          )
        ### update device proposed mode, status, priority, and demand
        self.dict_clothesdryer.update(
          device_ntcl(len_profile=self.dict_clothesdryer['len_profile'],
            unixtime=self.dict_common['unixtime'], 
            unixstart=self.dict_clothesdryer['unixstart'],
            unixend=self.dict_clothesdryer['unixend'],
            connected=self.dict_clothesdryer['connected'],
            progress=self.dict_clothesdryer['progress'],
            actual_status=self.dict_clothesdryer['actual_status'],
            proposed_demand=np.array([dict_data[k][int((x*y)%x)] for k, x, y in zip(self.dict_clothesdryer['profile'], self.dict_clothesdryer['len_profile'], self.dict_clothesdryer['progress'])]).flatten()
            )
          )
        ### update ldc_signal
        self.dict_clothesdryer.update(read_signal(ldc_signal=self.dict_clothesdryer['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=self.dict_devices['clothesdryer']['n_units'],
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))
        ### update ldc_dongle approval for the proposed status and demand
        self.dict_clothesdryer.update(ldc_dongle(self.dict_clothesdryer, self.dict_common))
        
        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_clothesdryer.update(
          enduse_ntcl(len_profile=self.dict_clothesdryer['len_profile'],
            progress=self.dict_clothesdryer['progress'],
            step_size=self.dict_common['step_size'],
            actual_status=self.dict_clothesdryer['actual_status'],
            unixtime=self.dict_common['unixtime'],
            connected=self.dict_clothesdryer['connected'])
          )
        if self.simulation==0:
          ### read actual sensors
          pass
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_clothesdryer})
            dict_save.update(prepare_data(states=self.dict_clothesdryer, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='clothesdryer.h5')
          
        ### send data to main
        self.pipe_agg_clothesdryer1.send(self.dict_clothesdryer)
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error clothesdryer run:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='clothesdryer.h5')
        print('Terminating clothesdryer...')
        self.pipe_agg_clothesdryer1.close()
        break 
    
    


  def dishwasher(self):
    print('Running dishwasher...')
    self.dict_dishwasher.update(initialize_load(load_type='dishwasher', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))

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

        ### update unixstart and unixend
        self.dict_dishwasher.update(
          make_schedule(unixtime=self.dict_common['unixtime'],
            current_task=self.dict_common['current_task'][self.dict_dishwasher['schedule']].values,
            load_type_id=self.dict_startcode['dishwasher'],
            unixstart=self.dict_dishwasher['unixstart'],
            unixend=self.dict_dishwasher['unixend'],
            schedule_skew=self.dict_dishwasher['schedule_skew'])
          )
        ## update if connected
        self.dict_dishwasher.update(
          is_connected(unixtime=self.dict_common['unixtime'],
            unixstart=self.dict_dishwasher['unixstart'],
            unixend=self.dict_dishwasher['unixend'])
          )
        ### update device proposed mode, status, priority, and demand
        self.dict_dishwasher.update(
          device_ntcl(len_profile=self.dict_dishwasher['len_profile'],
            unixtime=self.dict_common['unixtime'], 
            unixstart=self.dict_dishwasher['unixstart'],
            unixend=self.dict_dishwasher['unixend'],
            connected=self.dict_dishwasher['connected'],
            progress=self.dict_dishwasher['progress'],
            actual_status=self.dict_dishwasher['actual_status'],
            proposed_demand=np.array([dict_data[k][int((x*y)%x)] for k, x, y in zip(self.dict_dishwasher['profile'], self.dict_dishwasher['len_profile'], self.dict_dishwasher['progress'])]).flatten(),
            )
          )
        ### update ldc_signal
        self.dict_dishwasher.update(read_signal(ldc_signal=self.dict_dishwasher['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=self.dict_devices['dishwasher']['n_units'],
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))
        ### update ldc_dongle approval for the proposed status and demand
        self.dict_dishwasher.update(ldc_dongle(self.dict_dishwasher, self.dict_common))
        
        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_dishwasher.update(
          enduse_ntcl(len_profile=self.dict_dishwasher['len_profile'],
            progress=self.dict_dishwasher['progress'],
            step_size=self.dict_common['step_size'],
            actual_status=self.dict_dishwasher['actual_status'],
            unixtime=self.dict_common['unixtime'],
            connected=self.dict_dishwasher['connected'])
          )
        if self.simulation==0:
          ### read actual sensors
          pass
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_dishwasher})
            dict_save.update(prepare_data(states=self.dict_dishwasher, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='dishwasher.h5')
            
        ### send data to main
        self.pipe_agg_dishwasher1.send(self.dict_dishwasher)
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error dishwasher run:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='dishwasher.h5')
        print('Terminating dishwasher...')
        self.pipe_agg_dishwasher1.close()
        break
    


  def ev(self):
    print('Running electric vehicle model...')
    self.dict_ev.update(initialize_load(load_type='ev', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))
    
    ### setup the profiles
    try:
      with pd.HDFStore('/home/pi/ldc_project/ldc_simulator/profiles/ev_battery.h5', 'r') as store:
        df = store.select('records')  
    except Exception as e:
      print(f'Error electric_vehicle setup:{e}')

    dict_save = {}
    ### run profiles
    while True:
      try:
        self.dict_common.update(self.pipe_agg_ev1.recv())
        if self.dict_common['is_alive']==False:
          raise KeyboardInterrupt 

        ### update unixstart and unixend
        self.dict_ev.update(
          make_schedule(unixtime=self.dict_common['unixtime'],
            current_task=self.dict_common['current_task'][self.dict_ev['schedule']].values,
            load_type_id=self.dict_startcode['ev'], 
            unixstart=self.dict_ev['unixstart'],
            unixend=self.dict_ev['unixend'],
            schedule_skew=self.dict_ev['schedule_skew'])
          )
        ### update if connected
        self.dict_ev.update(
          is_connected(unixtime=self.dict_common['unixtime'],
            unixstart=self.dict_ev['unixstart'],
            unixend=self.dict_ev['unixend'])
          )
        ### update device proposed mode, status, priority, and demand
        self.dict_ev.update(
          device_battery(unixtime=self.dict_common['unixtime'], 
            unixstart=self.dict_ev['unixstart'],
            unixend=self.dict_ev['unixend'],
            soc=self.dict_ev['soc'],
            charging_power=self.dict_ev['charging_power'],
            target_soc=self.dict_ev['target_soc'],
            capacity=self.dict_ev['capacity'],
            connected=self.dict_ev['connected'],
            progress=self.dict_ev['progress'],
            actual_status=self.dict_ev['actual_status'],
            proposed_demand=self.dict_ev['proposed_demand'])

          # device_charger_ev(unixtime=self.dict_ev['unixtime'], 
          #   unixstart=self.dict_ev['unixstart'],
          #   unixend=self.dict_ev['unixend'],
          #   soc=self.dict_ev['soc'],
          #   charging_power=self.dict_ev['charging_power'],
          #   target_soc=self.dict_ev['target_soc'],
          #   capacity=self.dict_ev['capacity'],
          #   connected=self.dict_ev['connected'],
          #   progress=self.dict_ev['progress'],
          #   actual_status=self.dict_ev['actual_status'])
          #   proposed_demand=np.diag(df.loc[self.dict_ev['soc'].round(3), self.dict_ev['profile']].interpolate()),
          )
        ### update ldc_signal
        self.dict_ev.update(read_signal(ldc_signal=self.dict_ev['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=self.dict_devices['ev']['n_units'],
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))
        ### update ldc_dongle approval for the proposed status and demand
        self.dict_ev.update(ldc_dongle(self.dict_ev, self.dict_common))
        
        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_ev.update(
          enduse_ev(soc=self.dict_ev['soc'],
            target_soc=self.dict_ev['target_soc'],
            capacity=self.dict_ev['capacity'],
            actual_demand=self.dict_ev['actual_demand'],
            connected=self.dict_ev['connected'],
            unixtime=self.dict_common['unixtime'],
            step_size=self.dict_common['step_size'])
          )
        if self.simulation==0:
          ### read actual sensors
          pass
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_ev})
            dict_save.update(prepare_data(states=self.dict_ev, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='ev.h5')
          
        ### send data to main
        self.pipe_agg_ev1.send(self.dict_ev)  
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error ev run:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='ev.h5')
        print('Terminating electric vehicle...')
        self.pipe_agg_ev1.close()
        break 
    


  def storage(self):
    print('Running battery storage model...')
    self.dict_storage.update(initialize_load(load_type='storage', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))

    dict_save = {}
    while True:
      try:
        self.dict_common.update(self.pipe_agg_storage1.recv())
        if self.dict_common['is_alive']==False:
          raise KeyboardInterrupt

        self.dict_storage.update(self.dict_common)
        ### update unixstart and unixend
        self.dict_storage.update(
          make_schedule(unixtime=self.dict_common['unixtime'],
            current_task=self.dict_common['current_task'][self.dict_storage['schedule']].values,
            load_type_id=self.dict_startcode['storage'], 
            unixstart=self.dict_storage['unixstart'],
            unixend=self.dict_storage['unixend'],
            schedule_skew=self.dict_storage['schedule_skew'])
          )
        ## update if connected
        self.dict_storage.update(
          is_connected(unixtime=self.dict_common['unixtime'],
            unixstart=self.dict_storage['unixstart'],
            unixend=self.dict_storage['unixend'])
          )
        ### update device proposed mode, status, priority, and demand
        self.dict_storage.update(
          device_battery(unixtime=self.dict_common['unixtime'], 
            unixstart=self.dict_storage['unixstart'],
            unixend=self.dict_storage['unixend'],
            soc=self.dict_storage['soc'],
            charging_power=self.dict_storage['charging_power'],
            target_soc=self.dict_storage['target_soc'],
            capacity=self.dict_storage['capacity'],
            connected=self.dict_storage['connected'],
            progress=self.dict_storage['progress'],
            actual_status=self.dict_storage['actual_status'],
            proposed_demand=self.dict_storage['proposed_demand'])

          # device_charger_storage(unixtime=self.dict_storage['unixtime'], 
          #   unixstart=self.dict_storage['unixstart'],
          #   unixend=self.dict_storage['unixend'],
          #   soc=self.dict_storage['soc'],
          #   charging_power=self.dict_storage['charging_power'],
          #   target_soc=self.dict_storage['target_soc'],
          #   capacity=self.dict_storage['capacity'],
          #   connected=self.dict_storage['connected'],
          #   progress=self.dict_storage['progress'],
          #   actual_status=self.dict_storage['actual_status'],
          #   proposed_demand=self.dict_storage['charging_power'])
          )
        ### update ldc_signal
        self.dict_storage.update(read_signal(ldc_signal=self.dict_storage['ldc_signal'], 
          new_signal=self.dict_common['ldc_signal'], 
          resolution=self.resolution,
          n_units=self.dict_devices['storage']['n_units'],
          delay=self.delay, 
          step_size=self.dict_common['step_size'],
          simulation=self.simulation))
        ### update ldc_dongle approval for the proposed status and demand
        self.dict_storage.update(ldc_dongle(self.dict_storage, self.dict_common))
        
        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_storage.update(
          enduse_storage(soc=self.dict_storage['soc'],
            target_soc=self.dict_storage['target_soc'],
            capacity=self.dict_storage['capacity'],
            actual_demand=self.dict_storage['actual_demand'],
            connected=self.dict_storage['connected'],
            unixtime=self.dict_common['unixtime'],
            step_size=self.dict_common['step_size'])
          )
        if self.simulation==0:
          ### read actual sensors
          pass
        else:
          ### save data
          if self.save_history:
            # dict_save.update({int(self.dict_common['unixtime']):self.dict_storage})
            dict_save.update(prepare_data(states=self.dict_storage, common=self.dict_common))
            if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
              dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='storage.h5')
          
        ### send data to main
        self.pipe_agg_storage1.send(self.dict_storage)
        time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.storage:{}".format(e))
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='storage.h5')
        print("Terminating battery storage...")
        self.pipe_agg_storage1.close()
        break
    

  def solar(self):
    print('Running solar panel model...')
    self.dict_solar.update(initialize_load(load_type='solar', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))

    dict_save = {}
    while True:
      try:
        self.dict_common.update(self.pipe_agg_solar1.recv())
        if self.dict_common['is_alive']==False:
          raise KeyboardInterrupt

        self.dict_solar = {**self.dict_solar, **dict(zip(['irradiance_roof', 
          'irradiance_wall1' , 'irradiance_wall2', 'irradiance_wall3', 
          'irradiance_wall4', 
          'actual_demand'], 
          [solar.get_irradiance(
              unixtime=self.dict_common['unixtime'],
              humidity=self.dict_common['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=self.dict_solar['roof_tilt'],
              azimuth=self.dict_solar['azimuth'],
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_common['isotime']),
          solar.get_irradiance(
              unixtime=self.dict_common['unixtime'],
              humidity=self.dict_common['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=np.ones(len(self.dict_solar['azimuth']))*90,
              azimuth=self.dict_solar['azimuth'],
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_common['isotime']),
          solar.get_irradiance(
              unixtime=self.dict_common['unixtime'],
              humidity=self.dict_common['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=np.ones(len(self.dict_solar['azimuth']))*90,
              azimuth=self.dict_solar['azimuth']+90,
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_common['isotime']),
          solar.get_irradiance(
              unixtime=self.dict_common['unixtime'],
              humidity=self.dict_common['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=np.ones(len(self.dict_solar['azimuth']))*90,
              azimuth=self.dict_solar['azimuth']-90,
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_common['isotime']),
          solar.get_irradiance(
              unixtime=self.dict_common['unixtime'],
              humidity=self.dict_common['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=np.ones(len(self.dict_solar['azimuth']))*90,
              azimuth=self.dict_solar['azimuth']+180,
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_common['isotime']),
          np.multiply(np.multiply(self.dict_solar['capacity'], 
              self.dict_solar['irradiance_roof']*1e-3), 
              self.dict_solar['inverter_efficiency'])*-1
          ]
          ))}
        ### send data to main
        self.pipe_agg_solar1.send(self.dict_solar)
        ### save data
        if self.simulation==1 and self.save_history:
          # dict_save.update({int(self.dict_common['unixtime']):self.dict_solar})
          dict_save.update(prepare_data(states=self.dict_solar, common=self.dict_common))
          if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
            dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='solar.h5')
          
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error solar:{e}')
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='solar.h5')
        print('Terminating solar PV')
        self.pipe_agg_solar1.close()
        break
    


  def wind(self):
    print('Running wind turbine model...')
    self.dict_wind.update(initialize_load(load_type='wind', 
      dict_devices=self.dict_devices,
      dict_house=self.dict_house, 
      idx=self.idx, distribution=self.distribution))

    dict_save = {}
    while True:
      try:
        self.dict_common.update(self.pipe_agg_wind1.recv())
        if self.dict_common['is_alive']==False:
          raise KeyboardInterrupt
        ### send data to main
        self.pipe_agg_wind1.send(self.dict_wind)
        ### save data
        if self.simulation==1 and self.save_history:
          # dict_save.update({int(self.dict_common['unixtime']):self.dict_wind})
          dict_save.update(prepare_data(states=self.dict_wind, common=self.dict_common))
          if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
            dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='wind.h5')
          
        time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.wind:{}".format(e))
      except KeyboardInterrupt:
        if self.simulation==1 and self.save_history: save_data(dict_save, case=self.case,  folder=self.casefolder, filename='wind.h5')
        print("Terminating wind turbine...")
        self.pipe_agg_wind1.close()
        break
    


  def valve(self):
    # opening and closing of water valves
    print('Emulating valves opening/closing...')
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
    while True:
      try:
        self.dict_common.update(self.pipe_agg_valve1.recv())
        if self.dict_common['is_alive']==False: 
          raise KeyboardInterrupt
        ### update data
        self.dict_valve.update(update_device(n_device=3, 
          device_type='valve', 
          dict_startcode=self.dict_startcode, 
          dict_self=self.dict_valve, 
          dict_parent=self.dict_house, 
          dict_common=self.dict_common))
        ### read temperature
        if self.device_ip==113:
          try:
            a = read_temp_sensor()
            if a: water_temp = float(re.findall("[-.\d]+", a.split()[-1])[0])
            if water_temp in [None, -0.00]:
              pass
            else:
              self.dict_valve['valve0'].update({'temp_in':water_temp})
          except:
            results = pcsensor.read()
            if len(results)>0: self.dict_valve['valve0'].update({'temp_in':results[0]['internal temperature']})
            
        ### send data to main
        self.pipe_agg_valve1.send(self.dict_valve)
        ### execute status
        if self.device_ip==113:  # only execute on hot valve to conserve water
          execute_state(int(self.dict_valve[f'valve{self.device_ip-113}']['actual_status'][0]), 
            device_id=self.device_ip, report=True)
        
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error valve loop:{e}')
      except KeyboardInterrupt:
        print('Terminating watervalve...')
        self.pipe_agg_valve1.close()
        break      
    

  def window(self):
    ### this method affects the opening and closing of windows, impacts the air change per hour
    print('Emulating window opening / closing...')
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
        self.dict_common.update(self.pipe_agg_window1.recv())
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
        self.pipe_agg_window1.send(self.dict_window)
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
    print('Emulating door opening / closing...')
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
        self.dict_common.update(self.pipe_agg_door1.recv())
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
        self.pipe_agg_door1.send(self.dict_door)
        ### execute status
        execute_state(int(self.dict_door[f'door{self.device_ip-123}']['actual_status'][0]), 
          device_id=self.device_ip, report=True)  
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error door:{e}')
      except KeyboardInterrupt:
        print('Door simulation stopped...')
        self.pipe_agg_door1.close()
        break
       


        

  def drive_grainy(self):
    # initialization to drive the pifacedigital
    try:
      import serial
      import pifacedigitalio
      import RPi.GPIO as GPIO
      GPIO.setmode(GPIO.BOARD)
      GPIO.setwarnings(False)
      self.pins = [0,0,0,0,0,0,0,0]
      self.pf = pifacedigitalio.PiFaceDigital()
      
      dict_agg = {}
      self.df_relay, self.df_states = FUNCTIONS.create_states(report=False)  # create power levels based on resistor bank
      while True:
        try:
          ### get data from local process
          while self.pipe_agg_grainy1.poll():
            dict_agg = self.pipe_agg_grainy1.recv()
          if len(dict_agg.keys())==0: continue
          self.dict_common.update(dict_agg['common'])
          if self.dict_common['is_alive']==False: 
            raise KeyboardInterrupt
          self.dict_summary_demand = (dict_agg['summary_demand'])
          ### get data from network devices
          d = MULTICAST.send(dict_msg={"summary":"demand"}, ip='224.0.2.0', port=17000, timeout=0.5, hops=1)
          if d: self.dict_summary_demand.update(d)
          ### add all demand
          total = 0.0
          for p in self.dict_summary_demand.keys():
            if p in ['heatpump', 'waterheater']: 
              pass
            else:
              total = np.add(np.sum(self.dict_summary_demand[p]), total)
          
          
          total = min([total, 10e3]) #limit to 10kW

          ### convert total load value into 8-bit binary to drive 8 pinouts of piface
          newpins, grainy, chroma = FUNCTIONS.relay_pinouts(total, self.df_relay, self.df_states, report=False)
          # newpins, grainy, chroma = FUNCTIONS.pinouts(total, self.df_states, report=False)
          '''Note: chroma load does the finer load emulation, i.e., <50W'''
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

          
          time.sleep(self.pause)
        except KeyboardInterrupt:
          print("Terminating grainy load driver...")
          self.pipe_agg_grainy1.close()
          for i in range(len(self.pins)):
            self.pf.output_pins[i].turn_off()
          break
        except Exception as e:
          print("Error drive_grainy:", e, dict_agg, self.dict_common)
    except Exception as e:
      print("Error setting up piface:{}".format(e))
    
  
  def meter(self):
    from METER import EnergyMeter
    EM1 =  EnergyMeter(house=f'H{self.house_num}', IDs=[0])
    while True:
      try:
        self.dict_common = self.pipe_agg_meter1.recv()
        if self.dict_common['is_alive']==False:
          raise KeyboardInterrupt 
        self.dict_meter = EM1.get_meter_data(report=self.report)
        if self.dict_meter:
          self.pipe_agg_meter1.send(self.dict_meter)
        time.sleep(self.pause)
      except KeyboardInterrupt:
        print("meter stopped...")
        del EM1
        self.pipe_agg_meter1.close()
        break
      except Exception as e:
        print(f'Error meter:{e}')

  def multicast_server(self):
    # Receive multicast message from the group
    while True:
      try:
        try:
          multicast_ip = '224.0.2.0'
          port = 17000
          multicast_group = (multicast_ip, port)
          sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
          sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          sock.bind(multicast_group)
          group = socket.inet_aton(multicast_ip)
          mreq = struct.pack('4sL', group, socket.INADDR_ANY)
          sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,mreq)
          print(f'H{self.house_num} multicast:', multicast_group)
        except Exception as e:
          print("Error in udp_comm binding socket:",e)
          print("Retrying...")
          time.sleep(10)
        except KeyboardInterrupt:
          raise KeyboardInterrupt

        # Receive/respond loop
        while True:
          ### receive data from main routine
          self.dict_common = self.pipe_agg_udp1.recv()
          if self.dict_common['is_alive']==False:
            raise KeyboardInterrupt 
          ### receive message from network
          data, address = sock.recvfrom(1024)
          msg_in = data.decode("utf-8").replace("'", "\"")
          if msg_in:
            try:
              dict_msg = json.loads(msg_in)
              rcv_keys = dict_msg.keys()
              agg_keys = self.dict_agg.keys()
              
              if ('states' in rcv_keys) and ('states' in agg_keys):
                if dict_msg['states']=="all":
                  sock.sendto(str(self.dict_agg['states']).encode(), address)  
                else:
                  dict_to_send.update()
                  sock.sendto(str({dict_msg['states']:self.dict_agg['states'][dict_msg['states']]}).encode(), address)
                
              if ('summary' in rcv_keys) and ('summary' in agg_keys):
                sock.sendto(str(self.dict_agg['summary'][dict_msg['summary']]).encode(), address)   
                
              if 'injector' in rcv_keys:
                if dict_msg['injector'] in self.dict_injector.keys():
                  sock.sendto(str({dict_msg['injector']:self.dict_injector[dict_msg['injector']]}).encode(), address)

              if ('pcsensor' in rcv_keys) and ('valve' in self.dict_agg.keys()):
                if 'valve0' in self.dict_agg['valve'].keys():
                  if 'temp_in' in self.dict_agg['valve']['valve0'].keys():
                    sock.sendto(str({'temp_in':self.dict_agg['valve']['valve0']['temp_in']}).encode(), address)            
              
              time.sleep(self.pause) 
            except Exception as e:
              print("Error in udp_comm respond loop:", e, dict_msg)
            except KeyboardInterrupt:
              self.pipe_agg_comm1.close()
              sock.close()
              raise KeyboardInterrupt
              
      except Exception as e:
        print(f"Error AGGREGATOR.udp_comm:{e}")
        time.sleep(1)
      except KeyboardInterrupt:
        ### inform main of stoppage
        print("multicast receiver stopped...")   
        break
    
  def udp_comm(self):
    # Receive multicast message from the group
    while True:
      try:
        try:
          multicast_group = (self.local_ip, 10000)
          sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
          sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          sock.bind(multicast_group)
          group = socket.inet_aton(self.local_ip)
          mreq = struct.pack('4sL', group, socket.INADDR_ANY)
          sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,mreq)
          print(f'H{self.house_num} multicast:', multicast_group)
        except Exception as e:
          print("Error in udp_comm binding socket:",e)
          print("Retrying...")
          time.sleep(10)
        except KeyboardInterrupt:
          raise KeyboardInterrupt

        # Receive/respond loop
        while True:
          ### receive data from main routine
          self.dict_common = self.pipe_agg_udp1.recv()
          if self.dict_common['is_alive']==False:
            raise KeyboardInterrupt 
          ### receive message from network
          data, address = sock.recvfrom(1024)
          msg_in = data.decode("utf-8").replace("'", "\"")
          if msg_in:
            try:
              dict_msg = json.loads(msg_in)
              rcv_keys = dict_msg.keys()
              agg_keys = self.dict_agg.keys()
              
              if ('states' in rcv_keys) and ('states' in agg_keys):
                if dict_msg['states']=="all":
                  sock.sendto(str(self.dict_agg['states']).encode(), address)  
                else:
                  dict_to_send.update()
                  sock.sendto(str({dict_msg['states']:self.dict_agg['states'][dict_msg['states']]}).encode(), address)
                
              if ('summary' in rcv_keys) and ('summary' in agg_keys):
                sock.sendto(str(self.dict_agg['summary'][dict_msg['summary']]).encode(), address)   
                
              if 'injector' in rcv_keys:
                if dict_msg['injector'] in self.dict_injector.keys():
                  sock.sendto(str({dict_msg['injector']:self.dict_injector[dict_msg['injector']]}).encode(), address)

              if ('pcsensor' in rcv_keys) and ('valve' in self.dict_agg.keys()):
                if 'valve0' in self.dict_agg['valve'].keys():
                  if 'temp_in' in self.dict_agg['valve']['valve0'].keys():
                    sock.sendto(str({'temp_in':self.dict_agg['valve']['valve0']['temp_in']}).encode(), address)            
              
              time.sleep(self.pause) 
            except Exception as e:
              print("Error in udp_comm respond loop:", e, dict_msg)
            except KeyboardInterrupt:
              self.pipe_agg_comm1.close()
              sock.close()
              raise KeyboardInterrupt
              
      except Exception as e:
        print(f"Error AGGREGATOR.udp_comm:{e}")
        time.sleep(1)
      except KeyboardInterrupt:
        ### inform main of stoppage
        print("multicast receiver stopped...")   
        break
    

  def tcp_comm(self):
    try:
      # Create a TCP/IP socket
      tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      # Bind the socket to the port
      server_address = (self.local_ip, 10001)
      print('starting tcp_comm on {} port {}'.format(*server_address))
      tcp_sock.bind(server_address)
      # Listen for incoming connections
      tcp_sock.listen(100)
      
      ### receive data from main routine
      while True:
        try:
          self.dict_common = self.pipe_agg_udp1.recv()
          if self.dict_common['is_alive']==False:
            raise KeyboardInterrupt 
          client, address = tcp_sock.accept()  # wait for connection
          client.settimeout(sec)  # close client if inactive for 60 seconds
          threading.Thread(target=self.listen_to_client, args=(client, address)).start()
              
        except KeyboardInterrupt:
          break
        except Exception as e:
          print("Error in tcp_server receive_msg:", e)
        finally:
          connection.close()
    except Exception as e:
      print(time.time(), "Error in tcp_server connect:",e)
    finally:
      tcp_sock.shutdown(socket.SHUT_RDWR)
      tcp_sock.close()


  def listen_to_client(self, client, address):
    size = 2**16
    while True:
      try:
        data = client.recv(size)
        if data:
          # If data is received
          message = data.decode("utf-8")
          dict_msg = ast.literal_eval(message)
          if list(dict_msg)[0] in ['A0', 'A1', 'A2', 'A3', 'A4']:
            client.sendall(str(self.dict_agg).encode())
          else:
            # send ldc command as response
            self.dict_cmd = self.get_cmd()
            client.sendall(str(self.dict_cmd).encode())
        else:
          raise Exception('Client disconnected')
      except Exception as e:
          print("Error:", e)
          client.close()
          return False
      finally:
          client.close()

    
                       
    
  
  def history(self):
    time.sleep(5)
    while self.dict_common['is_alive']:
      try:
        filename = '/home/pi/studies/results/{}_{}_{}.h5'.format(self.dict_common['year'],
          self.dict_common['month'], self.dict_common['day'])
        ### loads
        df_data = pd.DataFrame.from_dict(self.dict_state, orient='index').transpose().fillna(0)
        df_data.index = pd.to_datetime(df_data['unixtime'], unit='s')
        
        # df_data = pd.melt(df_data.astype(str), 
        #   id_vars=["unixtime", "group"], var_name="parameter", value_name="value")
        # with open(filename, 'a') as f:
        #   df_data.to_csv(f, mode='a', header=f.tell()==0, index=False)
        
        ### network
        # df_data = pd.DataFrame.from_dict(self.dict_network, orient='index').transpose().fillna(0)
        # df_data = pd.melt(df_data.astype(str), 
        #   id_vars=["unixtime", "group"], var_name="parameter", value_name="value")
        # with open(filename, 'a') as f:
        #   df_data.to_csv(f, mode='a', header=f.tell()==0, index=False)
        

        # time.sleep(self.pause)
      except IOError:
        break
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error history:{e}')
        
    ### feedback
    print('History stopped...')


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








'''
  def data_collector(self):
    # This is the only method that edits dict_state
    # to avoid updating dict with expired instance data
    print("Collecting data...")
    factor = np.ones(self.factor)
    # delay data collection to let the models run
    if self.simulation==0: 
      time.sleep(20)  
    else:
      time.sleep(5)

    while self.dict_common['is_alive']:
      try:
        self.dict_state = {**self.dict_state, **dict(zip(['unixtime'], 
          [np.multiply(factor, self.dict_common["unixtime"])]
          ))}
        if self.dict_injector:
          self.dict_state = {**self.dict_state, **dict(zip(['ldc_signal'], 
            [np.multiply(np.random.normal(1,1e-3,self.factor), self.dict_injector['ldc_signal']).flatten()]
            ))}

        if self.dict_house:
          self.dict_state = {**self.dict_state, **dict(zip(['baseload_demand',
            'group'], 
            [self.dict_house["actual_demand"],
            self.dict_house["name"],
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['baseload'], 
            [self.dict_house["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['baseload'], 
            [self.dict_house["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['baseload'], 
            [self.dict_house["mode"]]
            ))}
          

        if self.dict_heatpump:
          self.dict_state = {**self.dict_state, **dict(zip(['heatpump_humidity_in', 
            'heatpump_temp_in', 'heatpump_temp_out', 'heatpump_mode', 
            'heatpump_status', 'heatpump_demand', 'heatpump_cooling_setpoint', 
            'heatpump_heating_setpoint', 'heatpump_priority'], 
            [self.dict_heatpump['humidity_in'], 
            self.dict_heatpump["temp_in"], 
            self.dict_heatpump['temp_out'], 
            self.dict_heatpump['mode'], 
            self.dict_heatpump['actual_status'], 
            self.dict_heatpump['actual_demand'], 
            self.dict_heatpump['cooling_setpoint'], 
            self.dict_heatpump['heating_setpoint'],
            self.dict_heatpump['priority'],
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['heatpump'], 
            [self.dict_heatpump["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['heatpump'], 
            [self.dict_heatpump["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['heatpump'], 
            [self.dict_heatpump["mode"]]
            ))}
          if self.simulation==0:
            self.dict_state = {**self.dict_state, **dict(zip(['heatpump_a_mode', 
              'heatpump_temp_target'], 
              [self.dict_heatpump['heatpump_a_mode'], 
              self.dict_heatpump['heatpump_temp_target']]
              ))}
          

        if self.dict_heater:
          self.dict_state = {**self.dict_state, **dict(zip(['heater_humidity_in', 
            'heater_temp_in', 'heater_temp_out', 'heater_mode', 
            'heater_status', 'heater_demand', 'heater_cooling_setpoint', 
            'heater_heating_setpoint', 'heater_priority'], 
            [self.dict_heater['humidity_in'], 
            self.dict_heater["temp_in"], 
            self.dict_heater['temp_out'], 
            self.dict_heater['mode'], 
            self.dict_heater['actual_status'], 
            self.dict_heater['actual_demand'], 
            self.dict_heater['cooling_setpoint'], 
            self.dict_heater['heating_setpoint'],
            self.dict_heater['priority'],
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['heater'], 
            [self.dict_heater["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['heater'], 
            [self.dict_heater["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['heater'], 
            [self.dict_heater["mode"]]
            ))}
          

        if self.dict_waterheater:
          self.dict_state = {**self.dict_state, **dict(zip(['waterheater_temp_in', 
            'waterheater_temp_out', 'waterheater_status', 'waterheater_demand', 
            'waterheater_heating_setpoint', 'waterheater_priority'], 
            [self.dict_waterheater["temp_in"], 
            self.dict_waterheater['temp_out'], 
            self.dict_waterheater['actual_status'],
            self.dict_waterheater['actual_demand'], 
            self.dict_waterheater['heating_setpoint'],
            self.dict_waterheater['priority']
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['waterheater'], 
              [self.dict_waterheater["actual_demand"]]
              ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['waterheater'], 
              [self.dict_waterheater["actual_status"]]
              ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['waterheater'], 
              [self.dict_waterheater["mode"]]
              ))}
          

        if self.dict_fridge:
          self.dict_state = {**self.dict_state, **dict(zip(['fridge_temp_in', 
            'fridge_temp_out', 'fridge_mode', 'fridge_status', 
            'fridge_demand', 'fridge_cooling_setpoint', 
            'fridge_heating_setpoint', 'fridge_priority'], 
            [self.dict_fridge["temp_in"], 
            self.dict_fridge['temp_out'], 
            self.dict_fridge['mode'], 
            self.dict_fridge['actual_status'],
            self.dict_fridge['actual_demand'], 
            self.dict_fridge['cooling_setpoint'], 
            self.dict_fridge['heating_setpoint'],
            self.dict_fridge['priority']
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['fridge'], 
            [self.dict_fridge["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['fridge'], 
            [self.dict_fridge["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['fridge'], 
            [self.dict_fridge["mode"]]
            ))}
          
          
        if self.dict_freezer:
          self.dict_state = {**self.dict_state, **dict(zip(['freezer_temp_in', 
            'freezer_temp_out', 'freezer_mode', 'freezer_status', 
            'freezer_demand', 'freezer_cooling_setpoint', 
            'freezer_heating_setpoint', 'freezer_priority'], 
            [self.dict_freezer["temp_in"], 
            self.dict_freezer['temp_out'], 
            self.dict_freezer['mode'], 
            self.dict_freezer['actual_status'],
            self.dict_freezer['actual_demand'], 
            self.dict_freezer['cooling_setpoint'], 
            self.dict_freezer['heating_setpoint'],
            self.dict_freezer['priority']
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['freezer'], 
            [self.dict_freezer["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['freezer'], 
            [self.dict_freezer["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['freezer'], 
            [self.dict_freezer["mode"]]
            ))}
          
          
        if self.dict_clotheswasher:
          self.dict_state = {**self.dict_state, **dict(zip(['clotheswasher_mode', 
            'clotheswasher_status', 'clotheswasher_demand', 
            'clotheswasher_progress', 'clotheswasher_priority'], 
            [self.dict_clotheswasher['mode'], 
            self.dict_clotheswasher['actual_status'],
            self.dict_clotheswasher['actual_demand'], 
            self.dict_clotheswasher['progress'],
            self.dict_clotheswasher['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['clotheswasher'], 
            [self.dict_clotheswasher["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['clotheswasher'], 
            [self.dict_clotheswasher["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['clotheswasher'], 
            [self.dict_clotheswasher["mode"]]
            ))}
          
          
        if self.dict_clothesdryer:
          self.dict_state = {**self.dict_state, **dict(zip(['clothesdryer_mode', 
            'clothesdryer_status', 'clothesdryer_demand', 
            'clothesdryer_progress', 'clothesdryer_priority'], 
            [self.dict_clothesdryer['mode'], 
            self.dict_clothesdryer['actual_status'],
            self.dict_clothesdryer['actual_demand'], 
            self.dict_clothesdryer['progress'],
            self.dict_clothesdryer['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['clothesdryer'], 
            [self.dict_clothesdryer["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['clothesdryer'], 
            [self.dict_clothesdryer["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['clothesdryer'], 
            [self.dict_clothesdryer["mode"]]
            ))}
          
          
        if self.dict_dishwasher:
          self.dict_state = {**self.dict_state, **dict(zip(['dishwasher_mode', 
            'dishwasher_status', 'dishwasher_demand', 
            'dishwasher_progress', 'dishwasher_priority'], 
            [self.dict_dishwasher['mode'], 
            self.dict_dishwasher['actual_status'],
            self.dict_dishwasher['actual_demand'], 
            self.dict_dishwasher['progress'],
            self.dict_dishwasher['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['dishwasher'], 
            [self.dict_dishwasher["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['dishwasher'], 
            [self.dict_dishwasher["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['dishwasher'], 
            [self.dict_dishwasher["mode"]]
            ))}
          
          
        if self.dict_ev:
          self.dict_state = {**self.dict_state, **dict(zip(['ev_mode', 
            'ev_status', 'ev_demand', 'ev_progress', 'ev_priority'], 
            [self.dict_ev['mode'], 
            self.dict_ev['actual_status'],
            self.dict_ev['actual_demand'], 
            self.dict_ev['progress'],
            self.dict_ev['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['ev'], 
            [self.dict_ev["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['ev'], 
            [self.dict_ev["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['ev'], 
            [self.dict_ev["mode"]]
            ))}
          
          
        if self.dict_storage:
          self.dict_state = {**self.dict_state, **dict(zip(['storage_mode', 
            'storage_status', 'storage_demand', 
            'storage_progress', 'priority'], 
            [self.dict_storage['mode'], 
            self.dict_storage['actual_status'],
            self.dict_storage['actual_demand'], 
            self.dict_storage['progress'],
            self.dict_storage['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['storage'], 
            [self.dict_storage["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['storage'], 
            [self.dict_storage["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['storage'], 
            [self.dict_storage["mode"]]
            ))}
          
          
        if self.dict_solar:
          self.dict_state = {**self.dict_state, **dict(zip(['solar_demand', 'solar_status'], 
            [self.dict_solar["actual_demand"], self.dict_solar["actual_status"]]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['solar'], 
            [self.dict_solar["actual_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['solar'], 
            [self.dict_solar["actual_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['solar'], 
            [self.dict_solar["mode"]]
            ))}
          
          
        if self.dict_window:
          for i in range(5):
            self.dict_state = {**self.dict_state, **dict(zip([f'window{i}_status'], 
              [self.dict_window[f'window{i}_connected']]
              ))}
          for i in range(5):
            self.dict_summary_status = {**self.dict_summary_status, **dict(zip([f'window{i}'], 
              [self.dict_window[f'window{i}_connected']]
              ))}
          for i in range(5):
            self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip([f'window{i}'], 
              [self.dict_window[f'window{i}_connected']]
              ))}

        if self.dict_door:
          self.dict_state = {**self.dict_state, **dict(zip([f'door{i}_status' for i in range(3)], 
            [self.dict_door[f'door{i}_connected'] for i in range(3)]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip([f'door{i}' for i in range(3)], 
            [self.dict_door[f'door{i}_connected'] for i in range(3)]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip([f'door{i}' for i in range(3)], 
            [self.dict_door[f'door{i}_connected'] for i in range(3)]
            ))}

        if self.dict_meter:
          self.dict_state.update(self.dict_meter)

        ### collect data from online
        # if self.simulation==0:
        #   dict_all = MULTICAST.send(dict_msg={"states":"all"}, ip='224.0.2.0', port=17000, timeout=1, hops=1)
        #   self.dict_state = {**self.dict_state, **dict(zip([dict_all.keys()], 
        #     [np.array(dict_all[k]) for k in dict_all.keys()]
        #     ))}

        
        time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.data_collector:{}".format(e))
      except KeyboardInterrupt:
        break
    
    print("Collecting data stopped...")
'''