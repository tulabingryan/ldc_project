
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
  def __init__(self, dict_devices, timestamp, latitude, longitude, idx, device_ip, step_size=1, 
    simulation=0, endstamp=None, case=None):
    super(Aggregator, self).__init__()
    multiprocessing.Process.__init__(self)
    self.daemon = True

    self.name = 'Aggregator_{}'.format(self.n+1)

    ### common dictionary available in all threads
    manager = multiprocessing.Manager()
    self.dict_devices = manager.dict()
    self.dict_environment = manager.dict()
    self.dict_network = manager.dict()
    self.dict_house = manager.dict()
    self.dict_baseload = self.dict_house  # set another name for dict_house
    self.dict_heatpump = manager.dict()
    self.dict_heater = manager.dict()
    self.dict_waterheater = manager.dict()
    self.dict_freezer = manager.dict()
    self.dict_fridge = manager.dict()
    self.dict_clothesdryer = manager.dict()
    self.dict_clotheswasher = manager.dict()
    self.dict_dishwasher = manager.dict()
    self.dict_ev = manager.dict()
    self.dict_storage = manager.dict()
    self.dict_solar = manager.dict()
    self.dict_wind = manager.dict()
    self.dict_dongle = manager.dict()
    self.dict_injector = manager.dict()
    self.dict_schedule = manager.dict()
    self.dict_valve = manager.dict()
    self.dict_window = manager.dict()
    self.dict_door = manager.dict()
    self.dict_blind = manager.dict()
    self.dict_summary_demand = manager.dict()
    self.dict_emulation_value = manager.dict()
    self.dict_state = manager.dict()
    self.dict_summary_mode = manager.dict()
    self.dict_summary_status = manager.dict()
    self.ac_state = manager.dict()
    self.dict_meter = manager.dict()
    

    # ### prepare queue
    # self.q_devices = multiprocessing.Queue(maxsize=3)
    # self.q_environment = multiprocessing.Queue(maxsize=3)
    # self.q_network = multiprocessing.Queue(maxsize=3)
    # self.q_house = multiprocessing.Queue(maxsize=3)
    # self.q_baseload = multiprocessing.Queue(maxsize=3)
    # self.q_heatpump = multiprocessing.Queue(maxsize=3)
    # self.q_heater = multiprocessing.Queue(maxsize=3)
    # self.q_waterheater = multiprocessing.Queue(maxsize=3)
    # self.q_freezer = multiprocessing.Queue(maxsize=3)
    # self.q_fridge = multiprocessing.Queue(maxsize=3)
    # self.q_clothesdryer = multiprocessing.Queue(maxsize=3)
    # self.q_clotheswasher = multiprocessing.Queue(maxsize=3)
    # self.q_dishwasher = multiprocessing.Queue(maxsize=3)
    # self.q_ev = multiprocessing.Queue(maxsize=3)
    # self.q_storage = multiprocessing.Queue(maxsize=3)
    # self.q_solar = multiprocessing.Queue(maxsize=3)
    # self.q_wind = multiprocessing.Queue(maxsize=3)
    # self.q_dongle = multiprocessing.Queue(maxsize=3)
    # self.q_injector = multiprocessing.Queue(maxsize=3)
    # self.q_schedule = multiprocessing.Queue(maxsize=3)
    # self.q_valve = multiprocessing.Queue(maxsize=3)
    # self.q_window = multiprocessing.Queue(maxsize=3)
    # self.q_door = multiprocessing.Queue(maxsize=3)
    # self.q_blind = multiprocessing.Queue(maxsize=3)
    # self.q_summary_demand = multiprocessing.Queue(maxsize=3)
    # self.q_emulation_value = multiprocessing.Queue(maxsize=3)
    # self.q_state = multiprocessing.Queue(maxsize=3)
    # self.q_summary_mode = multiprocessing.Queue(maxsize=3)
    # self.q_summary_status = multiprocessing.Queue(maxsize=3)
    # self.q_meter = multiprocessing.Queue(maxsize=3)
    # self.q_counter = multiprocessing.Queue(maxsize=3)
        

    self.idx = idx
    self.house_num = idx + 1
    self.device_ip = device_ip
    self.q_id = str(self.device_ip)
    self.simulation = simulation
    if self.simulation:
      self.realtime = False
      self.timestamp = timestamp
      self.step_size = step_size
      self.endstamp = endstamp
      self.case = case
    else:
      self.realtime = True
      self.timestamp = time.time()
    
    ### create globl objects
    self.weather = Weather(latitude=latitude, longitude=longitude, timestamp=self.timestamp)
    
    self.dict_environment['unixtime'] = self.timestamp
    self.df_history = pd.DataFrame([], columns=self.dict_devices.keys())
    self.pause = 1e-64  # pause time used in thread interrupts

    self.setup()
    self.add_device(dict_new_devices=dict_devices)
    self.autorun()

  def setup(self):
    ### initialize dictionaries
    # clock
    self.dict_environment = {**self.dict_environment, **dict(zip(['unixtime', 
      'step_size', 'year', 'month', 'day', 'yearweek', 'weekday', 'hour', 
      'minute', 'second', 'microsecond', 'isotime'], 
      clock(unixtime=self.dict_environment['unixtime'], realtime=self.realtime)
      ))}
    # weather
    self.dict_environment = {**self.dict_environment, **dict(zip(['temp_out', 
      'humidity', 'windspeed'], 
      self.weather.get_weather(self.dict_environment['unixtime'])
      ))}
    # network
    capacity = 30e-3  # ardmore capacity for 5 houses
    self.dict_network = {self.dict_environment['unixtime'].mean():dict(zip(['capacity', 'target_mw',
        'p_mw', 'p_a_mw', 'p_b_mw', 'p_c_mw'],
        [capacity, 0.7*capacity, 0, 0, 0]
        ))}
      
    # injector
    self.dict_injector = {**self.dict_injector, **dict(zip(['ldc_signal'],
      [np.array([0.0])]
      ))}
    # emulation value
    self.dict_emulation_value.update({'grainy_load':0, 'chroma_load':0})

    

  def add_device(self, dict_new_devices):
    self.factor = 1
    for load_type in dict_new_devices:
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

      self.factor = max([self.factor, self.dict_devices[load_type]['n_units']])
      f = np.ones(int(self.dict_devices[load_type]['n_units']))
      if n_units:   
        with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
          df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
          if 'with_dr' in df.columns:
            idxs = np.arange(n_units)
            if self.case=='per_device': np.random.shuffle(idxs)
            df.loc[idxs[0:n_ldc], 'with_dr'] = True
            df.loc[idxs[n_ldc:], 'with_dr'] = False

        if load_type=='heatpump':
          [self.dict_heatpump.update({p:df[p].values}) for p in df.columns]
          self.dict_heatpump.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='heater':
          [self.dict_heater.update({p:df[p].values}) for p in df.columns]
          self.dict_heater.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='waterheater':
          [self.dict_waterheater.update({p:df[p].values}) for p in df.columns]
          self.dict_waterheater.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='freezer':
          [self.dict_freezer.update({p:df[p].values}) for p in df.columns]
          self.dict_freezer.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='fridge':
          [self.dict_fridge.update({p:df[p].values}) for p in df.columns]
          self.dict_fridge.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='clothesdryer':
          [self.dict_clothesdryer.update({p:df[p].values}) for p in df.columns]
          self.dict_clothesdryer.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='clotheswasher':
          [self.dict_clotheswasher.update({p:df[p].values}) for p in df.columns]
          self.dict_clotheswasher.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='dishwasher':
          [self.dict_dishwasher.update({p:df[p].values}) for p in df.columns]
          self.dict_dishwasher.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='house':
          [self.dict_house.update({p:df[p].values}) for p in df.columns]
          self.dict_house.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='ev':
          [self.dict_ev.update({p:df[p].values}) for p in df.columns]
          self.dict_ev.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='storage':
          [self.dict_storage.update({p:df[p].values}) for p in df.columns]
          self.dict_storage.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='solar':
          [self.dict_solar.update({p:df[p].values}) for p in df.columns]
          self.dict_solar.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        elif load_type=='wind':
          [self.dict_wind.update({p:df[p].values}) for p in df.columns]
          self.dict_wind.update({'unixtime':np.multiply(f, self.dict_environment['unixtime'])})
        del df
    return


  def autorun(self):
    ### run common threads
    self.threads = [threading.Thread(target=self.environment, args=())]
    self.threads.append(threading.Thread(target=self.schedules, args=()))
    self.threads.append(threading.Thread(target=self.waterusage, args=()))
    self.threads.append(threading.Thread(target=self.window, args=()))
    self.threads.append(threading.Thread(target=self.door, args=()))
    self.threads.append(threading.Thread(target=self.ldc_injector, args=()))
    self.threads.append(threading.Thread(target=self.data_collector, args=()))

    # create separate threads for each type of appliance
    for k in self.dict_devices.keys():
      if self.dict_devices[k]['n_units']:
        eval('self.threads.append(threading.Thread(target=self.{}, args=()))'.format(k))

    if self.device_ip==100:
      self.threads.append(threading.Thread(target=self.drive_piface, args=()))
      self.threads.append(threading.Thread(target=self.drive_chroma, args=()))
    
    if self.device_ip==101:
      self.threads.append(threading.Thread(target=self.meter, args=()))

    if self.device_ip in list(range(103, 130)):
      self.threads.append(threading.Thread(target=self.drive_relay, args=()))
    
    if self.simulation==1: # only run history for simulation not on raspi
      self.threads.append(threading.Thread(target=self.history, args=()))
      self.threads.append(threading.Thread(target=self.network, args=()))

    # if self.simulation==0:
    self.threads.append(threading.Thread(target=self.udp_comm, args=()))
    
    self.dict_environment.update({'is_alive': True, 'ldc_signal':100.0})
    # run threads
    for t in self.threads:
      t.daemon = True
      t.start()

    while True:
      try:
        if self.endstamp==None:
          time.sleep(1)
        else:
          if self.dict_environment['unixtime'].mean() > self.endstamp:
            raise KeyboardInterrupt
      except KeyboardInterrupt:
        print('\nTerminating all processes..')
        for i in range(10):
          self.dict_environment['is_alive'] = False
    
        if self.case: time.sleep(5)  # delay to wait for other threads
        break

  def network(self):
    '''Model for electrical network'''
    if self.simulation:
      capacity = (self.dict_devices['house']['n_units'] * 5e3) * 1e-6
      self.dict_network = {self.dict_environment['unixtime'].mean():dict(zip(['capacity', 'target_mw',
        'p_mw', 'p_a_mw', 'p_b_mw', 'p_c_mw', 'ldc_signal'],
        [capacity, 0.8*capacity, 0, 0, 0, 0, 100.0]
        ))}
    

      factor = np.ones(self.dict_devices['house']['n_units'])

      while self.dict_environment['is_alive']:
        try:
          if self.dict_summary_demand:
            self.df_history = pd.DataFrame.from_dict(self.dict_summary_demand, orient='index').transpose().fillna(0)
            self.df_history['p_mw'] = self.df_history[self.dict_summary_demand.keys()].sum(axis=1) * 1e-6
            self.df_history['p_a_mw'] = np.multiply(self.df_history['p_mw'].values, (self.dict_house['phase']=='AN')*1)
            self.df_history['p_b_mw'] = np.multiply(self.df_history['p_mw'].values, (self.dict_house['phase']=='BN')*1)
            self.df_history['p_c_mw'] = np.multiply(self.df_history['p_mw'].values, (self.dict_house['phase']=='CN')*1)
            # self.df_history['unixtime'] = self.dict_environment['isotime'][0]
            # values = self.dict_summary_demand.values()
            # print(np.sum(np.array(values)))
            # print('-----------------------------------------------------------------------------------------')
            # for x,y in zip(self.df_history['p_mw'].values, np.sum(np.array(self.dict_summary_demand.values()), axis=1)):
            #   print(x,y)
            print(self.dict_environment['isotime'][0])
            self.dict_network.update({
              self.dict_environment['unixtime'].mean(): {
                'p_mw': self.df_history['p_mw'].sum(), 
                'p_a_mw': self.df_history['p_a_mw'].sum(), 
                'p_b_mw': self.df_history['p_b_mw'].sum(), 
                'p_c_mw': self.df_history['p_c_mw'].sum(), 
                'ldc_signal': self.dict_injector['ldc_signal'].mean(),
                'capacity': capacity,
                'target_mw':0.8*capacity
                }
              })

            # print(pd.DataFrame.from_dict(self.dict_network, orient='index'))
            # {**self.dict_network, **dict(zip(['p_mw', 
            #   'p_a_mw', 'p_b_mw', 'p_c_mw', 'ldc_signal', 'unixtime', 'group'],
            #   [np.array([self.df_history['p_mw'].sum()]),
            #     np.array([self.df_history['p_a_mw'].sum()]),
            #     np.array([self.df_history['p_b_mw'].sum()]),
            #     np.array([self.df_history['p_c_mw'].sum()]),
            #     self.dict_injector['ldc_signal'],
            #     self.dict_environment['unixtime'],
            #     np.array(['T001']),
            #   ]
            #   ))}
            
          time.sleep(self.pause)
        except Exception as e:
          print("Error AGGREGATOR.network:{}".format(e))
        except KeyboardInterrupt:
          break
    
      ### save data to disk
    if self.case!=None: 
      df = pd.DataFrame.from_dict(self.dict_network, orient='index')
      df.to_hdf('/home/pi/studies/results/house_vs_device_summer.h5', 
            key=self.case, mode='a', append=False, complib='blosc', format='table')


    ### feedback
    print(f'Common processes stopped...')
    return

  def environment(self):
    while self.dict_environment['is_alive']:
      try:
        new_time = clock(unixtime=self.dict_environment['unixtime'], realtime=self.realtime)
        ## update clock
        # for i in range(10):
        self.dict_environment = {**self.dict_environment, **dict(zip(['unixtime', 
          'step_size', 'year', 'month', 'day', 'yearweek', 'weekday', 'hour', 
          'minute', 'second', 'microsecond', 'isotime'], 
          [np.array([a]) for a in new_time]
          ))}
        ### update weather
        self.dict_environment = {**self.dict_environment, **dict(zip(['temp_out', 
          'humidity', 'windspeed'], 
          self.weather.get_weather(self.dict_environment['unixtime'])
          ))}

        while np.subtract(self.dict_environment['unixtime'].mean(), self.dict_heatpump['unixtime'].mean()) > 5:
          time.sleep(1e-6)
        # print(self.dict_environment['isotime'],
        #   "house:", self.dict_environment['unixtime'].mean()-self.dict_house['unixtime'].mean(),
        #   "heatpump:", self.dict_environment['unixtime'].mean()-self.dict_heatpump['unixtime'].mean(),
        #   "heater:", self.dict_environment['unixtime'].mean()-self.dict_heater['unixtime'].mean(),
        #   "waterheater:", self.dict_environment['unixtime'].mean()-self.dict_waterheater['unixtime'].mean(),
        #   "fridge:", self.dict_environment['unixtime'].mean()-self.dict_fridge['unixtime'].mean(),
        #   "freezer:", self.dict_environment['unixtime'].mean()-self.dict_freezer['unixtime'].mean(),
        #   "clotheswasher:", self.dict_environment['unixtime'].mean()-self.dict_clotheswasher['unixtime'].mean(),
        #   "clothesdryer:", self.dict_environment['unixtime'].mean()-self.dict_clothesdryer['unixtime'].mean(),
        #   "dishwasher:", self.dict_environment['unixtime'].mean()-self.dict_dishwasher['unixtime'].mean(),
        #   "ev:", self.dict_environment['unixtime'].mean()-self.dict_ev['unixtime'].mean(),
          # )
        time.sleep(0.01)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error AGGREGATOR.environment:{e}')
        
    ### feedback
    print(f'Environment processes stopped...')

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

    while self.dict_environment['is_alive']:
      try:
        self.dict_state = {**self.dict_state, **dict(zip(['unixtime'], 
          [np.multiply(factor, self.dict_environment["unixtime"])]
          ))}
        if self.dict_injector:
          self.dict_state = {**self.dict_state, **dict(zip(['ldc_signal'], 
            [np.multiply(np.random.normal(1,1e-3,self.factor), self.dict_injector['ldc_signal']).flatten()]
            ))}

        if self.dict_house:
          self.dict_state = {**self.dict_state, **dict(zip(['baseload_demand',
            'group'], 
            [self.dict_house["a_demand"],
            self.dict_house["name"],
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['baseload'], 
            [self.dict_house["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['baseload'], 
            [self.dict_house["a_status"]]
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
            self.dict_heatpump['a_status'], 
            self.dict_heatpump['a_demand'], 
            self.dict_heatpump['cooling_setpoint'], 
            self.dict_heatpump['heating_setpoint'],
            self.dict_heatpump['priority'],
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['heatpump'], 
            [self.dict_heatpump["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['heatpump'], 
            [self.dict_heatpump["a_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['heatpump'], 
            [self.dict_heatpump["mode"]]
            ))}
          if self.simulation==0:
            self.dict_state = {**self.dict_state, **dict(zip(['heatpump_a_mode', 
              'heatpump_target_temp'], 
              [self.dict_heatpump['heatpump_a_mode'], 
              self.dict_heatpump['heatpump_target_temp']]
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
            self.dict_heater['a_status'], 
            self.dict_heater['a_demand'], 
            self.dict_heater['cooling_setpoint'], 
            self.dict_heater['heating_setpoint'],
            self.dict_heater['priority'],
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['heater'], 
            [self.dict_heater["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['heater'], 
            [self.dict_heater["a_status"]]
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
            self.dict_waterheater['a_status'],
            self.dict_waterheater['a_demand'], 
            self.dict_waterheater['heating_setpoint'],
            self.dict_waterheater['priority']
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['waterheater'], 
              [self.dict_waterheater["a_demand"]]
              ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['waterheater'], 
              [self.dict_waterheater["a_status"]]
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
            self.dict_fridge['a_status'],
            self.dict_fridge['a_demand'], 
            self.dict_fridge['cooling_setpoint'], 
            self.dict_fridge['heating_setpoint'],
            self.dict_fridge['priority']
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['fridge'], 
            [self.dict_fridge["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['fridge'], 
            [self.dict_fridge["a_status"]]
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
            self.dict_freezer['a_status'],
            self.dict_freezer['a_demand'], 
            self.dict_freezer['cooling_setpoint'], 
            self.dict_freezer['heating_setpoint'],
            self.dict_freezer['priority']
            ]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['freezer'], 
            [self.dict_freezer["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['freezer'], 
            [self.dict_freezer["a_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['freezer'], 
            [self.dict_freezer["mode"]]
            ))}
          
          
        if self.dict_clotheswasher:
          self.dict_state = {**self.dict_state, **dict(zip(['clotheswasher_mode', 
            'clotheswasher_status', 'clotheswasher_demand', 
            'clotheswasher_progress', 'clotheswasher_priority'], 
            [self.dict_clotheswasher['mode'], 
            self.dict_clotheswasher['a_status'],
            self.dict_clotheswasher['a_demand'], 
            self.dict_clotheswasher['progress'],
            self.dict_clotheswasher['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['clotheswasher'], 
            [self.dict_clotheswasher["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['clotheswasher'], 
            [self.dict_clotheswasher["a_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['clotheswasher'], 
            [self.dict_clotheswasher["mode"]]
            ))}
          
          
        if self.dict_clothesdryer:
          self.dict_state = {**self.dict_state, **dict(zip(['clothesdryer_mode', 
            'clothesdryer_status', 'clothesdryer_demand', 
            'clothesdryer_progress', 'clothesdryer_priority'], 
            [self.dict_clothesdryer['mode'], 
            self.dict_clothesdryer['a_status'],
            self.dict_clothesdryer['a_demand'], 
            self.dict_clothesdryer['progress'],
            self.dict_clothesdryer['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['clothesdryer'], 
            [self.dict_clothesdryer["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['clothesdryer'], 
            [self.dict_clothesdryer["a_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['clothesdryer'], 
            [self.dict_clothesdryer["mode"]]
            ))}
          
          
        if self.dict_dishwasher:
          self.dict_state = {**self.dict_state, **dict(zip(['dishwasher_mode', 
            'dishwasher_status', 'dishwasher_demand', 
            'dishwasher_progress', 'dishwasher_priority'], 
            [self.dict_dishwasher['mode'], 
            self.dict_dishwasher['a_status'],
            self.dict_dishwasher['a_demand'], 
            self.dict_dishwasher['progress'],
            self.dict_dishwasher['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['dishwasher'], 
            [self.dict_dishwasher["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['dishwasher'], 
            [self.dict_dishwasher["a_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['dishwasher'], 
            [self.dict_dishwasher["mode"]]
            ))}
          
          
        if self.dict_ev:
          self.dict_state = {**self.dict_state, **dict(zip(['ev_mode', 
            'ev_status', 'ev_demand', 'ev_progress', 'ev_priority'], 
            [self.dict_ev['mode'], 
            self.dict_ev['a_status'],
            self.dict_ev['a_demand'], 
            self.dict_ev['progress'],
            self.dict_ev['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['ev'], 
            [self.dict_ev["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['ev'], 
            [self.dict_ev["a_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['ev'], 
            [self.dict_ev["mode"]]
            ))}
          
          
        if self.dict_storage:
          self.dict_state = {**self.dict_state, **dict(zip(['storage_mode', 
            'storage_status', 'storage_demand', 
            'storage_progress', 'priority'], 
            [self.dict_storage['mode'], 
            self.dict_storage['a_status'],
            self.dict_storage['a_demand'], 
            self.dict_storage['progress'],
            self.dict_storage['priority']]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['storage'], 
            [self.dict_storage["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['storage'], 
            [self.dict_storage["a_status"]]
            ))}
          self.dict_summary_mode = {**self.dict_summary_mode, **dict(zip(['storage'], 
            [self.dict_storage["mode"]]
            ))}
          
          
        if self.dict_solar:
          self.dict_state = {**self.dict_state, **dict(zip(['solar_demand', 'solar_status'], 
            [self.dict_solar["a_demand"], self.dict_solar["a_status"]]
            ))}
          self.dict_summary_demand = {**self.dict_summary_demand, **dict(zip(['solar'], 
            [self.dict_solar["a_demand"]]
            ))}
          self.dict_summary_status = {**self.dict_summary_status, **dict(zip(['solar'], 
            [self.dict_solar["a_status"]]
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

  def ldc_injector(self):
    ''' Model for LDC Injector'''
    print("Running ldc_injector...")
    if self.simulation:
      while self.dict_environment['is_alive']:
        try:
          if self.dict_network and self.dict_injector:
            ### update ldc_signal
            stamp, network_last_state = self.dict_network.popitem()
             
            self.dict_network.update({stamp:network_last_state}) # return item
            
            # print(ldc_injector(signal=self.dict_injector['ldc_signal'], 
            #           latest_power=np.array([network_last_state['p_mw']]), 
            #           target_power=np.array([network_last_state['target_mw']]), 
            #           step_size=self.dict_environment['step_size']))

            self.dict_injector = {**self.dict_injector, **dict(zip(['ldc_signal',
              'p_mw', 'target_mw', 'isotime'], 
              [ldc_injector(signal=self.dict_injector['ldc_signal'], 
                      latest_power=np.array([network_last_state['p_mw']]), 
                      target_power=np.array([network_last_state['target_mw']]), 
                      step_size=self.dict_environment['step_size']),
              np.array([network_last_state['p_mw']]),
              np.array([network_last_state['target_mw']]),
              self.dict_environment['isotime']
              ]
              ))}

            

        except Exception as e:
          print(f"Error AGGREGATOR.ldc_injector:{e}")
        except KeyboardInterrupt:
          break
        time.sleep(self.pause)
    else:
      try:
        ### for reading ldc signal
        import spidev
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # (bus, device)
        self.spi.bits_per_word = 8
        self.spi.max_speed_hz = 500000
        self.spi.mode = 3
        while self.dict_environment['is_alive']:
          try:
            # read ldc_signal from spi
            s = float(self.spi.readbytes(1)[0])
            if (s>0.0):
              self.dict_injector.update({
                'ldc_signal':np.array([s]),
                'ldc_signal_spi':np.array([s]),
                'unixtime':np.array([self.dict_environment["unixtime"]])
                })
            else:
              dict_s = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, 
                ip='224.0.2.0', port=17000, timeout=0.1, hops=1)
              if dict_s:
                s = dict_s["ldc_signal_spi"]
                self.dict_injector.update({
                  'ldc_signal':np.array([s]),
                  'unixtime':np.array([self.dict_environment["unixtime"]])
                  }) 

          except Exception as e:
            print("Error AGGREGATOR.ldc_injector:{}".format(e))
            dict_s = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, 
                ip='224.0.2.0', port=17000, timeout=0.1, hops=1)
            if dict_s:
              s = dict_s["ldc_signal_spi"]
              self.dict_injector.update({
                'ldc_signal':np.array([s]),
                'unixtime':np.array([self.dict_environment["unixtime"]])
                })
          except KeyboardInterrupt:
            break
          time.sleep(1)
      except Exception as e:
        print("Error AGGREGATOR.ldc_injector spidev setup:{}".format(e))
        while self.dict_environment['is_alive']:
          try:
            dict_s = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, 
                ip='224.0.2.0', port=17000, timeout=0.1, hops=1)
            s = dict_s["ldc_signal_spi"]
            self.dict_injector.update({
              'ldc_signal':np.array([s]),
              'unixtime':np.array([self.dict_environment["unixtime"]])
              })
          except Exception as e:
            print("Error AGGREGATOR.ldc_injector:{}".format(e))
          except KeyboardInterrupt:
            break
          time.sleep(1)
          
  # def ldc_dongle(self):
  #   # dongles are implemented at each device methodsz
  #   return

  def house(self):
    self.dict_interpolator_house = {}
    validity_start = 0
    validity_end = 0
    print('Running house baseloads...')
    self.dict_house['mode'] = np.zeros(self.dict_devices['house']['n_units'])

    while self.dict_environment['is_alive']:
      try:
        ### update data from dict_environment
        self.dict_house = {**self.dict_house, **dict(zip(['unixtime',
          'humidity','temp_out','windspeed', 'isotime'], 
          [self.dict_environment['unixtime'], self.dict_environment['humidity'], 
          self.dict_environment['temp_out'],self.dict_environment['windspeed'], 
          self.dict_environment['isotime']]
          ))}

        if (int(self.dict_house['unixtime'])>validity_end):
          ### get baseload for current time
          yearsecond = int(self.dict_house['unixtime'])%31536000
          n_seconds = 3600                   
          with pd.HDFStore('./profiles/baseload.h5', 'r') as store:
            df = store.select('records', where='index>={} and index<{}'.format(int(yearsecond), 
              int(yearsecond+(2*n_seconds))))
            df.reset_index(drop=True, inplace=True)
            df.index = np.add(df.index.values, int(self.dict_house['unixtime']))
          validity_start = df.index.values[0]
          validity_end = df.index.values[-int(n_seconds/2)]  # a buffer is added to catch up with the clock
          
        ### update baseload
        self.dict_house = {**self.dict_house, **dict(zip(['a_demand'], 
          [df.loc[self.dict_house['unixtime'], self.dict_house['profile']].values.flatten()]
          ))}

        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print("Error AGGREGATOR.house:", e)
        
    ### feedback
    print('Baseload simulation stopped...')
        

  def heatpump(self):
    print('Running heatpump...')
    self.dict_heatpump['unixstart'] = np.zeros(len(self.dict_heatpump['schedule']))
    self.dict_heatpump['unixend'] = np.zeros(len(self.dict_heatpump['schedule']))
    self.dict_heatpump['mass_flow'] = np.clip(np.random.normal(1.2754*1e-1, 0.01, 
      len(self.dict_heatpump['schedule'])), a_min=0.001, a_max=1.2754)

    ### make sure schedule is available
    while 'current_task' not in self.dict_schedule.keys():
      time.sleep(self.pause)

    if self.simulation:      
      while self.dict_environment['is_alive']:
        try:
          ### check if unixtime has been updated
          while self.dict_environment['unixtime'].mean()<=self.dict_heatpump['unixtime'].mean(): 
            time.sleep(self.pause)
          
          ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
          self.dict_heatpump['temp_out'] = (self.dict_heatpump['temp_out']**0) * self.dict_environment['temp_out']

          ### update unixstart and unixend
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['unixstart', 'unixend'], 
            make_schedule(unixtime=self.dict_environment['unixtime'],
              current_task=self.dict_schedule['current_task'],
              load_type_id=11, # 11 is the code for heatpumps
              unixstart=self.dict_heatpump['unixstart'],
              unixend=self.dict_heatpump['unixend']
              )
            ))}
          ## update if connected
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['connected'], 
            [is_connected(unixtime=self.dict_environment['unixtime'],
              unixstart=self.dict_heatpump['unixstart'],
              unixend=self.dict_heatpump['unixend'])]
            ))}
          
          ### update device proposed mode, status, priority, and demand
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['mode', 
            'p_status', 'p_demand', 'priority',
            'cooling_power_thermal', 'heating_power_thermal', 
            'a_demand'], 
            device_tcl(mode=self.dict_heatpump['mode'], 
              temp_in=self.dict_heatpump['temp_in'], 
              temp_min=self.dict_heatpump['temp_min'], 
              temp_max=self.dict_heatpump['temp_max'],
              priority=self.dict_heatpump['priority'], 
              temp_out=self.dict_heatpump['temp_out'], 
              a_status=self.dict_heatpump['a_status'],
              a_demand=self.dict_heatpump['a_demand'], 
              p_status=self.dict_heatpump['p_status'], 
              p_demand=self.dict_heatpump['p_demand'], 
              cooling_setpoint=self.dict_heatpump['cooling_setpoint'], 
              heating_setpoint=self.dict_heatpump['heating_setpoint'],
              tolerance=self.dict_heatpump['tolerance'], 
              cooling_power=self.dict_heatpump['cooling_power'], 
              heating_power=self.dict_heatpump['heating_power'],
              cop=self.dict_heatpump['cop'],
              standby_power=self.dict_heatpump['standby_power'],
              ventilation_power=self.dict_heatpump['ventilation_power'],
              cooling_power_thermal=self.dict_heatpump['cooling_power_thermal'],
              heating_power_thermal=self.dict_heatpump['heating_power_thermal'])
            ))}
          ### update ldc_dongle approval for the proposed status and demand
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['a_status'], 
            [ldc_dongle(priority=self.dict_heatpump['priority'], 
              signal=self.dict_injector['ldc_signal'], 
              p_status=self.dict_heatpump['p_status'],
              with_dr=self.dict_heatpump['with_dr'])
              ]
            ))}
          ### update device states, e.g., temp_in, temp_mat, through simulation
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['temp_in', 
            'temp_mat', 'temp_in_active', 'unixtime'], 
            enduse_tcl(heat_all=self.dict_heatpump['heating_power_thermal'],
              air_part=self.dict_heatpump['air_part'],
              temp_in=self.dict_heatpump['temp_in'],
              temp_mat=self.dict_heatpump['temp_mat'],
              temp_out=self.dict_heatpump['temp_out'],
              Um=self.dict_heatpump['Um'],
              Ua=self.dict_heatpump['Ua'],
              Cp=self.dict_heatpump['Cp'],
              Ca=self.dict_heatpump['Ca'],
              Cm=self.dict_heatpump['Cm'],
              mass_flow= self.dict_heatpump['mass_flow'],
              step_size=np.subtract(self.dict_environment['unixtime'], self.dict_heatpump['unixtime']),
              unixtime=self.dict_heatpump['unixtime'],
              connected=self.dict_heatpump['connected'])
            ))}
          ### temporary calculation for indoor humidity
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['humidity_in'], 
            [np.random.normal(1, 0.001, len(self.dict_heatpump['temp_in'])) * self.dict_environment['humidity'] * 100]
            ))}
          ### air density = 1.2754 kg/m^3
          if self.dict_window:
            self.dict_heatpump['mass_flow'] = np.clip(np.multiply(self.dict_window['window0_a_status'], 
              np.random.normal(1.2754*0.1, 0.1, len(self.dict_window['window0_a_status']))), 
              a_min=0.0017, a_max=1.2754)
          

          time.sleep(self.pause)  # to give way to other threads
        except KeyboardInterrupt:
          break

        except Exception as e:
          print(f'Error heatpump:{e}')
        
    elif self.device_ip==111:
      import SENSIBO
      dict_a_mode = {'cool':0, 'heat':1, 'fan':2, 'dry':3, 'auto':4}  # actual mode

      self.sensibo_api = SENSIBO.SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
      devices = self.sensibo_api.devices()
      self.uid = devices['ldc_heatpump_h{}'.format(int(self.house_num))]
      self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
      self.sensibo_history = self.sensibo_api.pod_history(self.uid)
      
      while self.dict_environment['is_alive']:
        try:
          ### check if unixtime has been updated
          while self.dict_environment['unixtime'].mean()<=self.dict_heatpump['unixtime'].mean(): 
            time.sleep(self.pause)

          ### get actual sensibo state every 30 seconds
          if self.dict_environment['second']%30==0:
            self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
            self.sensibo_history = self.sensibo_api.pod_history(self.uid)
          
          ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
          self.dict_heatpump['temp_out'] = (self.dict_heatpump['temp_out']**0) * self.dict_environment['temp_out']

          ### update unixstart and unixend
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['unixstart', 'unixend'], 
            make_schedule(unixtime=self.dict_environment['unixtime'],
              current_task=self.dict_schedule['current_task'],
              load_type_id=11, # 11 is the code for heatpumps
              unixstart=self.dict_heatpump['unixstart'],
              unixend=self.dict_heatpump['unixend']
              )
            ))}
          ## update if connected
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['connected'], 
            [np.array([1])
            # is_connected(unixtime=self.dict_environment['unixtime'],
            #   unixstart=self.dict_heatpump['unixstart'],
            #   unixend=self.dict_heatpump['unixend'])
            ]
            ))}
          
          ### update device proposed mode, status, priority, and demand (this is a simulation model)
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['mode', 
            'p_status', 'p_demand', 'priority',
            'cooling_power_thermal', 'heating_power_thermal', 'a_demand'], 
            device_tcl(mode=self.dict_heatpump['mode'], 
              temp_in=self.dict_heatpump['temp_in'], 
              temp_min=self.dict_heatpump['temp_min'], 
              temp_max=self.dict_heatpump['temp_max'],
              priority=self.dict_heatpump['priority'], 
              temp_out=self.dict_heatpump['temp_out'], 
              a_status=self.dict_heatpump['a_status'],
              a_demand=self.dict_heatpump['a_demand'], 
              p_status=self.dict_heatpump['p_status'], 
              p_demand=self.dict_heatpump['p_demand'], 
              cooling_setpoint=self.dict_heatpump['cooling_setpoint'], 
              heating_setpoint=self.dict_heatpump['heating_setpoint'],
              tolerance=self.dict_heatpump['tolerance'], 
              cooling_power=self.dict_heatpump['cooling_power'], 
              heating_power=self.dict_heatpump['heating_power'],
              cop=self.dict_heatpump['cop'],
              standby_power=self.dict_heatpump['standby_power'],
              ventilation_power=self.dict_heatpump['ventilation_power'],
              cooling_power_thermal=self.dict_heatpump['cooling_power_thermal'],
              heating_power_thermal=self.dict_heatpump['heating_power_thermal'])
            ))}
          
          ### update ldc_dongle approval for the proposed status and demand
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['a_status'], 
            [ldc_dongle(priority=self.dict_heatpump['priority'], 
              signal=self.dict_injector['ldc_signal'], 
              p_status=self.dict_heatpump['p_status'],
              with_dr=self.dict_heatpump['with_dr'])]
            ))}

          ### control
          ### change status
          # if self.dict_heatpump['a_status'][0]==1 and self.sensibo_state['on']==False:
          #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "on", True) 
          # elif self.dict_heatpump['a_status'][0]==0 and self.sensibo_state['on']==True:
          #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "on", False)
          # ### change mode if needed (disabled since this is automanaged by sensibo)
          # if self.dict_heatpump['mode'][0]==1 and self.sensibo_state['mode']=='cool':
          #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "mode", "heat")  # change to heating
          # elif self.dict_heatpump['mode'][0]==0 and self.sensibo_state['mode']=='heat':
          #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "mode", "cool")  # change to cooling
          
          ### change temperature setpoint
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['cooling_setpoint', 
            'heating_setpoint'], 
            [adjust_setpoint(a_status=self.dict_heatpump['a_status'], 
              mode=self.dict_heatpump['mode'], 
              old_setpoint=self.dict_heatpump['cooling_setpoint'], 
              upper_limit=self.dict_heatpump['temp_max'], 
              lower_limit=self.dict_heatpump['temp_min']),
            adjust_setpoint(a_status=self.dict_heatpump['a_status'], 
              mode=self.dict_heatpump['mode'], 
              old_setpoint=self.dict_heatpump['heating_setpoint'], 
              upper_limit=self.dict_heatpump['temp_max'], 
              lower_limit=self.dict_heatpump['temp_min'])
            ]
            ))}

          if ((self.sensibo_state['mode']=='cool') 
            and (self.sensibo_state['targetTemperature']!=int(self.dict_heatpump['cooling_setpoint'][0]))):
            self.sensibo_api.pod_change_ac_state(self.uid, 
              self.sensibo_state, "targetTemperature", 
              int(self.dict_heatpump['cooling_setpoint'][0]))
          elif ((self.sensibo_state['mode']=='heat') 
            and (self.sensibo_state['targetTemperature']!=int(self.dict_heatpump['heating_setpoint'][0]))):
            self.sensibo_api.pod_change_ac_state(self.uid, 
              self.sensibo_state, "targetTemperature", 
              int(self.dict_heatpump['heating_setpoint'][0]))

          ### update device states, e.g., temp_in, temp_mat, actual reading
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['temp_in', 
            'temp_mat','temp_in_active','unixtime'], 
            [np.array([self.sensibo_history['temperature'][-1]['value']]),
            np.array([self.sensibo_history['temperature'][-1]['value']]),
            np.array([self.sensibo_history['temperature'][-1]['value']]),
            np.array([self.dict_environment['unixtime']])]
            ))}
          ### indoor humidity (actual reading)
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['humidity_in'], 
            [np.array([self.sensibo_history['humidity'][-1]['value']])]
            ))}
          ### additional data
          self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['heatpump_a_mode', 
            'heatpump_target_temp'], 
            [np.array([dict_a_mode[self.sensibo_state['mode']]]), 
            np.array([self.sensibo_state['targetTemperature']])]
            ))}

          time.sleep(1)
        except Exception as e:
          print(f'Error heatpump actual device:{e}')

    ### feedback
    print('Heatpump simulation stopped...')
        

  def heater(self):
    print('Running electric heater...')
    ### initialize dynamic variables
    self.dict_heater['unixstart'] = np.zeros(len(self.dict_heater['schedule']))
    self.dict_heater['unixend'] = np.zeros(len(self.dict_heater['schedule']))
    self.dict_heater['mass_flow'] = np.clip(np.random.normal(1.2754*1e-1, 0.01, len(self.dict_heater['schedule'])), a_min=0.001, a_max=1.2754)
    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    while self.dict_environment['is_alive']:
      try:                
        while self.dict_environment['unixtime'].mean()<=self.dict_heater['unixtime'].mean(): 
          time.sleep(self.pause)  # wait for unixtime update
          
        self.dict_heater['temp_out'] = (self.dict_heater['temp_out']**0) * self.dict_environment['temp_out']

        ### update unixstart and unixend
        self.dict_heater = {**self.dict_heater, **dict(zip(['unixstart', 'unixend'], 
          make_schedule(unixtime=self.dict_environment['unixtime'],
            current_task=self.dict_schedule['current_task'],
            load_type_id=3, # code for heaters
            unixstart=self.dict_heater['unixstart'],
            unixend=self.dict_heater['unixend']
            )
          ))}

        ## update if connected
        self.dict_heater = {**self.dict_heater, **dict(zip(['connected'], 
          [is_connected(unixtime=self.dict_environment['unixtime'],
            unixstart=self.dict_heater['unixstart'],
            unixend=self.dict_heater['unixend'])]
          ))}

        
        ### update device proposed mode, status, priority, and demand
        self.dict_heater = {**self.dict_heater, **dict(zip(['p_status', 'p_demand', 'priority',
          'heating_power_thermal', 'a_demand'], 
          device_heating(mode=self.dict_heater['mode'],
            temp_in=self.dict_heater['temp_in'], 
            temp_min=self.dict_heater['temp_min'], 
            temp_max=self.dict_heater['temp_max'], 
            a_status=self.dict_heater['a_status'], 
            a_demand=self.dict_heater['a_demand'],
            heating_setpoint=self.dict_heater['heating_setpoint'], 
            tolerance=self.dict_heater['tolerance'], 
            heating_power=self.dict_heater['heating_power'],
            cop=self.dict_heater['cop'],
            standby_power=self.dict_heater['standby_power'],
            ventilation_power=self.dict_heater['ventilation_power'])
          ))}


        ### update ldc_dongle approval for the proposed status and demand
        self.dict_heater = {**self.dict_heater, **dict(zip(['a_status'], 
          [ldc_dongle(priority=self.dict_heater['priority'], 
            signal=self.dict_injector['ldc_signal'], 
            p_status=self.dict_heater['p_status'],
            with_dr=self.dict_heater['with_dr'])]
          ))}

        ### update device states, e.g., temp_in, temp_mat, through simulation
        self.dict_heater = {**self.dict_heater, **dict(zip(['temp_in', 'temp_mat', 'temp_in_active', 'unixtime'], 
          enduse_tcl(heat_all=self.dict_heater['heating_power_thermal'],
            air_part=self.dict_heater['air_part'],
            temp_in=self.dict_heater['temp_in'],
            temp_mat=self.dict_heater['temp_mat'],
            temp_out=self.dict_heater['temp_out'],
            Um=self.dict_heater['Um'],
            Ua=self.dict_heater['Ua'],
            Cp=self.dict_heater['Cp'],
            Ca=self.dict_heater['Ca'],
            Cm=self.dict_heater['Cm'],
            mass_flow=self.dict_heater['mass_flow'],
            step_size=np.subtract(self.dict_environment['unixtime'], self.dict_heater['unixtime']),
            unixtime=self.dict_heater['unixtime'],
            connected=self.dict_heater['connected'])
          ))}
              
        ### temporary calculation for indoor humidity
        self.dict_heater = {**self.dict_heater, **dict(zip(['humidity_in'], 
          [np.random.normal(1, 0.001, len(self.dict_heater['temp_in'])) * self.dict_environment['humidity'] * 100]
          ))}
        ### air density = 1.2754 kg/m^3
        if self.dict_window:
          self.dict_heater['mass_flow'] = np.clip(np.multiply(self.dict_window['window0_a_status'], 
            np.random.normal(1.2754*0.1, 0.1, len(self.dict_window['window0_a_status']))), 
            a_min=0.0017, a_max=1.2754)
        
        if self.dict_window:
          self.dict_heater['mass_flow'] = np.clip(np.multiply(self.dict_window['window0_a_status'], 
            np.random.normal(1.2754*0.1, 0.1, len(self.dict_window['window0_a_status']))), 
            a_min=0.0017, a_max=1.2754)

        time.sleep(self.pause)  # to give way to other threads
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error heater:{e}')
        
    ### feedback
    print('Electric heater simulation stopped...')

  def waterheater(self):
    print('Running waterheater...')

    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule.keys():
      time.sleep(self.pause)

    ### initialization
    self.dict_waterheater = {**self.dict_waterheater, **dict(zip(['mass_flow'], 
            [np.zeros(len(self.dict_waterheater['schedule']))]        
            ))}
    
    if True: #self.simulation:
      while self.dict_environment['is_alive']:
        try:
          while self.dict_environment['unixtime'].mean()<=self.dict_waterheater['unixtime'].mean(): 
            time.sleep(self.pause)

          self.dict_waterheater['temp_out'] = (self.dict_waterheater['temp_out']**0) * self.dict_environment['temp_out']
          ### update device proposed mode, status, priority, and demand
          self.dict_waterheater = {**self.dict_waterheater, **dict(zip(['p_status', 
            'p_demand', 'priority', 'heating_power_thermal', 'a_demand'], 
            device_heating(mode=self.dict_waterheater['mode'],
              temp_in=self.dict_waterheater['temp_in'], 
              temp_min=self.dict_waterheater['temp_min'], 
              temp_max=self.dict_waterheater['temp_max'], 
              a_status=self.dict_waterheater['a_status'], 
              a_demand=self.dict_waterheater['a_demand'],
              heating_setpoint=self.dict_waterheater['heating_setpoint'], 
              tolerance=self.dict_waterheater['tolerance'], 
              heating_power=self.dict_waterheater['heating_power'],
              cop=self.dict_waterheater['cop'],
              standby_power=self.dict_waterheater['standby_power'],
              ventilation_power=self.dict_waterheater['ventilation_power'])
            ))}

          ### update ldc_dongle approval for the proposed status and demand
          self.dict_waterheater = {**self.dict_waterheater, **dict(zip(['a_status'], 
            [ldc_dongle(priority=self.dict_waterheater['priority'], 
              signal=self.dict_injector['ldc_signal'], 
              p_status=self.dict_waterheater['p_status'],
              with_dr=self.dict_waterheater['with_dr'])]
            ))}

          ### update device states, e.g., temp_in, temp_mat, through simulation
          self.dict_waterheater = {**self.dict_waterheater, **dict(zip(['temp_in', 
            'temp_mat', 'temp_in_active', 'unixtime'], 
            enduse_tcl(heat_all=self.dict_waterheater['heating_power_thermal'],
              air_part=self.dict_waterheater['air_part'],
              temp_in=self.dict_waterheater['temp_in'],
              temp_mat=self.dict_waterheater['temp_mat'],
              temp_out=self.dict_waterheater['temp_out'],
              Um=self.dict_waterheater['Um'],
              Ua=self.dict_waterheater['Ua'],
              Cp=self.dict_waterheater['Cp'],
              Ca=self.dict_waterheater['Ca'],
              Cm=self.dict_waterheater['Cm'],
              mass_flow=self.dict_waterheater['mass_flow'],  # kg/s
              step_size=np.abs(np.subtract(self.dict_waterheater['unixtime'], self.dict_environment['unixtime'])),
              unixtime=self.dict_waterheater['unixtime'],
              connected=self.dict_waterheater['connected'])
            ))}

          # if self.dict_valve:
          #   self.dict_waterheater['mass_flow'] = np.clip(np.multiply(self.dict_valve['valve0_a_status'], 
          #     np.random.normal(0.1167, 0.1, len(self.dict_valve['valve0_a_status']))), 
          #     a_min=0.0, a_max=0.4167)

        # elif self.device_ip==112:
        #   ### read actual temperatures
        #   pass

          time.sleep(self.pause)  # to give way to other threads
        except KeyboardInterrupt:
          break
        except Exception as e:
          print(f'Error AGGREGATOR.waterheater:{e}')
        
    ### feedback
    print('Waterheater simulation stopped...')

  def fridge(self):
    print('Running fridge...')

    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    while self.dict_environment['is_alive']:
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_fridge['unixtime'].mean(): 
          time.sleep(self.pause)
        
        ### update device proposed mode, status, priority, and demand
        self.dict_fridge = {**self.dict_fridge, **dict(zip(['p_status', 'p_demand', 'priority', 
          'cooling_power_thermal', 'a_demand'], 
          device_cooling(mode=self.dict_fridge['mode'],
            temp_in=self.dict_fridge['temp_in'], 
            temp_min=self.dict_fridge['temp_min'], 
            temp_max=self.dict_fridge['temp_max'], 
            a_status=self.dict_fridge['a_status'], 
            a_demand=self.dict_fridge['a_demand'],
            cooling_setpoint=self.dict_fridge['cooling_setpoint'], 
            tolerance=self.dict_fridge['tolerance'], 
            cooling_power=self.dict_fridge['cooling_power'],
            cop=self.dict_fridge['cop'], 
            standby_power=self.dict_fridge['standby_power'],
            ventilation_power=self.dict_fridge['ventilation_power'])
          ))}

        ### update ldc_dongle approval for the proposed status and demand
        self.dict_fridge = {**self.dict_fridge, **dict(zip(['a_status'], 
          [ldc_dongle(priority=self.dict_fridge['priority'], 
            signal=self.dict_injector['ldc_signal'], 
            p_status=self.dict_fridge['p_status'],
            with_dr=self.dict_fridge['with_dr'])]
          ))}

        ### update device states, e.g., temp_in, temp_mat, through simulation
        self.dict_fridge = {**self.dict_fridge, **dict(zip(['temp_in', 'temp_mat', 'temp_in_active', 'unixtime'], 
          enduse_tcl(heat_all=self.dict_fridge['cooling_power_thermal'],
            air_part=self.dict_fridge['air_part'],
            temp_in=self.dict_fridge['temp_in'],
            temp_mat=self.dict_fridge['temp_mat'],
            temp_out=self.dict_fridge['temp_out'],
            Um=self.dict_fridge['Um'],
            Ua=self.dict_fridge['Ua'],
            Cp=self.dict_fridge['Cp'],
            Ca=self.dict_fridge['Ca'],
            Cm=self.dict_fridge['Cm'],
            mass_flow= 0.001, #self.dict_fridge['mass_flow'],
            step_size=np.subtract(self.dict_environment['unixtime'], self.dict_fridge['unixtime']),
            unixtime=self.dict_fridge['unixtime'],
            connected=self.dict_fridge['connected'])
          ))}
        
        time.sleep(self.pause)  # to give way to other threads
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error fridge:{e}')
    ### feedback
    print('Fridge simulation stopped...')
          

  def freezer(self):
    print('Running freezer...')

    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    while self.dict_environment['is_alive']:
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_freezer['unixtime'].mean(): 
          time.sleep(self.pause)
          
        ### update required parameters, e.g.mass flow, unixstart, connected, etc.
        # self.dict_freezer.update({'mass_flow': x[0]})

        
        ### update device proposed mode, status, priority, and demand
        self.dict_freezer = {**self.dict_freezer, **dict(zip(['p_status', 'p_demand', 'priority', 
          'cooling_power_thermal', 'a_demand'], 
          device_cooling(mode=self.dict_freezer['mode'],
            temp_in=self.dict_freezer['temp_in'], 
            temp_min=self.dict_freezer['temp_min'], 
            temp_max=self.dict_freezer['temp_max'], 
            a_status=self.dict_freezer['a_status'], 
            a_demand=self.dict_freezer['a_demand'],
            cooling_setpoint=self.dict_freezer['cooling_setpoint'], 
            tolerance=self.dict_freezer['tolerance'], 
            cooling_power=self.dict_freezer['cooling_power'],
            cop=self.dict_freezer['cop'],
            standby_power=self.dict_freezer['standby_power'],
            ventilation_power=self.dict_freezer['ventilation_power'])
          ))}

        ### update ldc_dongle approval for the proposed status and demand
        self.dict_freezer = {**self.dict_freezer, **dict(zip(['a_status'], 
          [ldc_dongle(priority=self.dict_freezer['priority'], 
            signal=self.dict_injector['ldc_signal'], 
            p_status=self.dict_freezer['p_status'],
            with_dr=self.dict_freezer['with_dr'])]
          ))}

        ### update device states, e.g., temp_in, temp_mat, through simulation
        self.dict_freezer = {**self.dict_freezer, **dict(zip(['temp_in', 'temp_mat', 'temp_in_active', 'unixtime'], 
          enduse_tcl(heat_all=self.dict_freezer['cooling_power_thermal'],
            air_part=self.dict_freezer['air_part'],
            temp_in=self.dict_freezer['temp_in'],
            temp_mat=self.dict_freezer['temp_mat'],
            temp_out=self.dict_freezer['temp_out'],
            Um=self.dict_freezer['Um'],
            Ua=self.dict_freezer['Ua'],
            Cp=self.dict_freezer['Cp'],
            Ca=self.dict_freezer['Ca'],
            Cm=self.dict_freezer['Cm'],
            mass_flow= 0.001, #self.dict_freezer['mass_flow'],
            step_size=np.subtract(self.dict_environment['unixtime'], self.dict_freezer['unixtime']),
            unixtime=self.dict_freezer['unixtime'],
            connected=self.dict_freezer['connected'])
          ))}
        
        time.sleep(self.pause)  # to give way to other threads
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error freezer:{e}')
        
    ### feedback
    print('Freezer simulation stopped...')

  def clotheswasher(self):
    print('Running clotheswasher...')
    ### initialize dynamic variables 
    self.dict_clotheswasher['unixstart'] = np.zeros(self.dict_devices['clotheswasher']['n_units'])
    self.dict_clotheswasher['unixend'] = np.zeros(self.dict_devices['clotheswasher']['n_units'])
    
    ### setup the profiles
    try:
      self.dict_interpolator_clotheswasher = {}
      with open('./profiles/nntcl.json') as f:
        nntcl = json.load(f)
      
      dict_data = nntcl['Clotheswasher']
      for k in dict_data.keys():
        self.dict_interpolator_clotheswasher[k] = interp1d(np.arange(len(dict_data[k])), dict_data[k])
      
      del nntcl  # free up the memory
      
    except Exception as e:
      print(f'Error clotheswasher setup:{e}')


    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    ### run profiles
    while self.dict_environment['is_alive']:
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_clotheswasher['unixtime'].mean(): 
          time.sleep(self.pause)
          
        ### update unixstart and unixend
        self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['unixstart', 'unixend'], 
          make_schedule(unixtime=self.dict_environment['unixtime'],
            current_task=self.dict_schedule['current_task'],
            load_type_id=6, # code for clotheswashers
            unixstart=self.dict_clotheswasher['unixstart'],
            unixend=self.dict_clotheswasher['unixend']
            )
          ))}

        ## update if connected
        self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['connected'], 
          [is_connected(unixtime=self.dict_environment['unixtime'],
            unixstart=self.dict_clotheswasher['unixstart'],
            unixend=self.dict_clotheswasher['unixend'])]
          ))}


        ### update device proposed mode, status, priority, and demand
        self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['p_status', 'flexibility', 
          'priority', 'p_demand', 'a_demand'], 
          device_ntcl(len_profile=self.dict_clotheswasher['len_profile'],
            unixtime=self.dict_clotheswasher['unixtime'], 
            unixstart=self.dict_clotheswasher['unixstart'],
            unixend=self.dict_clotheswasher['unixend'],
            connected=self.dict_clotheswasher['connected'],
            progress=self.dict_clotheswasher['progress'],
            a_status=self.dict_clotheswasher['a_status'],
            # p_demand=np.array([self.dict_interpolator_clotheswasher[k](np.clip(np.multiply(x, y), a_min=0, a_max=x-1)) for k, x, y in zip(self.dict_clotheswasher['profile'], self.dict_clotheswasher['len_profile'], self.dict_clotheswasher['progress'])]).flatten(),
            p_demand=np.array([ dict_data[k][int((x*y)%x)] for k, x, y in zip(self.dict_clotheswasher['profile'], self.dict_clotheswasher['len_profile'], self.dict_clotheswasher['progress'])]).flatten(),
            a_demand=self.dict_clotheswasher['p_demand'])
          ))}

        

        ### update ldc_dongle approval for the proposed status and demand
        self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['a_status'], 
          [(
            (ldc_dongle(priority=self.dict_clotheswasher['priority'], 
              signal=self.dict_injector['ldc_signal'], 
              p_status=self.dict_clotheswasher['p_status'],
              with_dr=self.dict_clotheswasher['with_dr'])==1) | 
            ((self.dict_clotheswasher['a_status']==1)&(self.dict_clotheswasher['progress']<=1))
            )*1
          ]

          ))}

        
        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['unfinished','finished','progress', 'unixtime'], 
          enduse_ntcl(len_profile=self.dict_clotheswasher['len_profile'],
            progress=self.dict_clotheswasher['progress'],
            step_size=np.subtract(self.dict_environment['unixtime'], self.dict_clotheswasher['unixtime']), 
            a_status=self.dict_clotheswasher['a_status'],
            unixtime=self.dict_clotheswasher['unixtime'],
            connected=self.dict_clotheswasher['connected']
            )
          
          ))}
        
        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error clotheswasher run:{e}')
        
    ### feedback
    print('Clotheswasher simulation stopped...')
        

  # def clothesdryer(self):
  #     print('Running clothesdryer...')    
  #     '''
  #     g = (25 + (19*v)) * A (x_s - x)/3600  # v = air velocity on water surface, 
  #     A = exposed water surface area, x_s = kg_h20/ kg_dryair of sturated air in same temp, x = kg_h20/kg_dry air for given air temp
  #     g =  evaporation rate [kg/s]
  #     '''


  def clothesdryer(self):
    print('Running clothesdryer...')
    ### initialize dynamic variables 
    self.dict_clothesdryer['unixstart'] = np.zeros(self.dict_devices['clothesdryer']['n_units'])
    self.dict_clothesdryer['unixend'] = np.zeros(self.dict_devices['clothesdryer']['n_units'])
    
    ### setup the profiles
    try:
      self.dict_interpolator_clothesdryer = {}
      with open('./profiles/nntcl.json') as f:
        nntcl = json.load(f)
        
      dict_data = nntcl['Clothesdryer']
      
      for k in dict_data.keys():
        self.dict_interpolator_clothesdryer[k] = interp1d(np.arange(len(dict_data[k])), dict_data[k])
      
      self.dict_clothesdryer['len_profile'] = np.array([len(dict_data[k]) for k in self.dict_clothesdryer['profile']])

      # print(self.dict_clothesdryer['len_profile'])
      del nntcl
      
    except Exception as e:
      print(f'Error clothesdryer setup:{e}')

    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    ### run the profiles
    while self.dict_environment['is_alive']:
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_clothesdryer['unixtime'].mean(): 
          time.sleep(self.pause)
          
        ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
        ### update unixstart and unixend
        self.dict_clothesdryer = {**self.dict_clothesdryer, **dict(zip(['unixstart', 'unixend'], 
          make_schedule(unixtime=self.dict_environment['unixtime'],
            current_task=self.dict_schedule['current_task'],
            load_type_id=4, # code for clothesdryer
            unixstart=self.dict_clothesdryer['unixstart'],
            unixend=self.dict_clothesdryer['unixend']
            )
          ))}

        ## update if connected
        self.dict_clothesdryer = {**self.dict_clothesdryer, **dict(zip(['connected'], 
          [is_connected(unixtime=self.dict_environment['unixtime'],
            unixstart=self.dict_clothesdryer['unixstart'],
            unixend=self.dict_clothesdryer['unixend'])]
          ))}


        # print(datetime.datetime.fromtimestamp(self.dict_clothesdryer['unixtime']), self.dict_clothesdryer['connected'], self.dict_clothesdryer['progress'], self.dict_clothesdryer['len_profile'])


        ### update device proposed mode, status, priority, and demand
        self.dict_clothesdryer = {**self.dict_clothesdryer, **dict(zip(['p_status', 
          'flexibility', 'priority', 'p_demand', 'a_demand'], 
          device_ntcl(len_profile=self.dict_clothesdryer['len_profile'],
            unixtime=self.dict_clothesdryer['unixtime'], 
            unixstart=self.dict_clothesdryer['unixstart'],
            unixend=self.dict_clothesdryer['unixend'],
            connected=self.dict_clothesdryer['connected'],
            progress=self.dict_clothesdryer['progress'],
            a_status=self.dict_clothesdryer['a_status'],
            # p_demand=np.array([self.dict_interpolator_clothesdryer[k](np.clip(np.multiply(x, y), a_min=0, a_max=x-1)) for k, x, y in zip(self.dict_clothesdryer['profile'], self.dict_clothesdryer['len_profile'], self.dict_clothesdryer['progress'])]).flatten(),
            p_demand=np.array([dict_data[k][int((x*y)%x)] for k, x, y in zip(self.dict_clothesdryer['profile'], self.dict_clothesdryer['len_profile'], self.dict_clothesdryer['progress'])]).flatten(),
            a_demand=self.dict_clothesdryer['p_demand'])
          ))}


        ### update ldc_dongle approval for the proposed status and demand
        self.dict_clothesdryer = {**self.dict_clothesdryer, **dict(zip(['a_status'], 
          [(
            (ldc_dongle(priority=self.dict_clothesdryer['priority'], 
              signal=self.dict_injector['ldc_signal'], 
              p_status=self.dict_clothesdryer['p_status'],
              with_dr=self.dict_clothesdryer['with_dr'])==1) | 
            ((self.dict_clothesdryer['a_status']==1)&(self.dict_clothesdryer['progress']<=1))
            )*1
          ]

          ))}

        
        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_clothesdryer = {**self.dict_clothesdryer, **dict(zip(['unfinished',
          'finished','progress', 'unixtime'], 
          enduse_ntcl(len_profile=self.dict_clothesdryer['len_profile'],
            progress=self.dict_clothesdryer['progress'],
            step_size=np.subtract(self.dict_environment['unixtime'], self.dict_clothesdryer['unixtime']), 
            a_status=self.dict_clothesdryer['a_status'],
            unixtime=self.dict_clothesdryer['unixtime'],
            connected=self.dict_clothesdryer['connected']
            )
          ))}

        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error clothesdryer run:{e}')
          
    ### feedback
    print('clothesdryer simulation stopped...')

  def dishwasher(self):
    print('Running dishwasher...')
    ### initialize dynamic variables 
    self.dict_dishwasher['unixstart'] = np.zeros(self.dict_devices['dishwasher']['n_units'])
    self.dict_dishwasher['unixend'] = np.zeros(self.dict_devices['dishwasher']['n_units'])

    ### setup the profiles
    try:
      self.dict_interpolator_dishwasher = {}
      with open('./profiles/nntcl.json') as f:
        nntcl = json.load(f)
      
      dict_data = nntcl['Dishwasher']
      for k in dict_data.keys():
        self.dict_interpolator_dishwasher[k] = interp1d(np.arange(len(dict_data[k])), dict_data[k])
      
      del nntcl
      
    except Exception as e:
      print(f'Error dishwasher setup:{e}')

    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    ### run the profiles
    while self.dict_environment['is_alive']:
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_dishwasher['unixtime'].mean(): 
          time.sleep(self.pause)
          
        ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
        ### update unixstart and unixend
        self.dict_dishwasher = {**self.dict_dishwasher, **dict(zip(['unixstart', 'unixend'], 
          make_schedule(unixtime=self.dict_environment['unixtime'],
            current_task=self.dict_schedule['current_task'],
            load_type_id=4, # code for dishwasher
            unixstart=self.dict_dishwasher['unixstart'],
            unixend=self.dict_dishwasher['unixend']
            )
          ))}

        ## update if connected
        self.dict_dishwasher = {**self.dict_dishwasher, **dict(zip(['connected'], 
          [is_connected(unixtime=self.dict_environment['unixtime'],
            unixstart=self.dict_dishwasher['unixstart'],
            unixend=self.dict_dishwasher['unixend'])]
          ))}

        ### update device proposed mode, status, priority, and demand
        self.dict_dishwasher = {**self.dict_dishwasher, **dict(zip(['p_status', 'flexibility', 'priority', 'p_demand', 'a_demand'], 
          device_ntcl(len_profile=self.dict_dishwasher['len_profile'],
            unixtime=self.dict_dishwasher['unixtime'], 
            unixstart=self.dict_dishwasher['unixstart'],
            unixend=self.dict_dishwasher['unixend'],
            connected=self.dict_dishwasher['connected'],
            progress=self.dict_dishwasher['progress'],
            a_status=self.dict_dishwasher['a_status'],
            # p_demand=np.array([self.dict_interpolator_dishwasher[k](np.clip(np.multiply(x, y), a_min=0, a_max=x-1)) for k, x, y in zip(self.dict_dishwasher['profile'], self.dict_dishwasher['len_profile'], self.dict_dishwasher['progress'])]).flatten(),
            p_demand=np.array([dict_data[k][int((x*y)%x)] for k, x, y in zip(self.dict_dishwasher['profile'], self.dict_dishwasher['len_profile'], self.dict_dishwasher['progress'])]).flatten(),
            a_demand=self.dict_dishwasher['p_demand'])  # previous p_demand
          ))}


        ### update ldc_dongle approval for the proposed status and demand
        self.dict_dishwasher = {**self.dict_dishwasher, **dict(zip(['a_status'], 
          [(
            (ldc_dongle(priority=self.dict_dishwasher['priority'], 
              signal=self.dict_injector['ldc_signal'], 
              p_status=self.dict_dishwasher['p_status'],
              with_dr=self.dict_dishwasher['with_dr'])==1) | 
            ((self.dict_dishwasher['a_status']==1)&(self.dict_dishwasher['progress']<=1))
            )*1
          ]

          ))}

        
        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_dishwasher = {**self.dict_dishwasher, **dict(zip(['unfinished',
          'finished','progress', 'unixtime'], 
          enduse_ntcl(len_profile=self.dict_dishwasher['len_profile'],
            progress=self.dict_dishwasher['progress'],
            step_size=np.subtract(self.dict_environment['unixtime'], self.dict_dishwasher['unixtime']), 
            a_status=self.dict_dishwasher['a_status'],
            unixtime=self.dict_dishwasher['unixtime'],
            connected=self.dict_dishwasher['connected']
            )
          
          ))}
        
        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error dishwasher run:{e}')
          
    ### feedback
    print('Dishwasher simulation stopped...')

  def ev(self):
    print('Running electric vehicle model...')
    ### initialize dynamic variables 
    self.dict_ev['unixstart'] = np.zeros(self.dict_devices['ev']['n_units'])
    self.dict_ev['unixend'] = np.zeros(self.dict_devices['ev']['n_units'])
    self.dict_ev['progress'] = np.divide(self.dict_ev['soc'], self.dict_ev['target_soc'])
    self.dict_ev['mode'] = np.zeros(self.dict_devices['ev']['n_units'])
    ### setup the profiles
    try:

      # self.dict_interpolator_ev = {}
      # with open('./profiles/battery.json') as f:
      #   dict_data = json.load(f)
        
      # for k in dict_data.keys():
      #   if k=='tesla_powerwall': 
      #     continue        
      #   self.dict_interpolator_ev[k] = interp1d(np.array(dict_data[k]['charge_ratio']), np.array(dict_data[k]['power_kw'])*1000)
      
      # # del dict_data  # free up the memory
      # # df = pd.DataFrame.to_dict(dict_data)
      
      # for k in dict_data.keys():
      #   print(len(dict_data[k]['charge_ratio']), len(dict_data[k]['power_kw']))

      with pd.HDFStore('/home/pi/ldc_project/ldc_simulator/profiles/ev_battery.h5', 'r') as store:
        df = store.select('records')
        print(df)
    


    except Exception as e:
      print(f'Error electric_vehicle setup:{e}')


    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    ### run profiles
    while self.dict_environment['is_alive']:
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_ev['unixtime'].mean(): 
          time.sleep(self.pause)
          
        ### update unixstart and unixend
        self.dict_ev = {**self.dict_ev, **dict(zip(['unixstart', 'unixend'], 
          make_schedule(unixtime=self.dict_environment['unixtime'],
            current_task=self.dict_schedule['current_task'],
            load_type_id=6, # code for clotheswashers
            unixstart=self.dict_ev['unixstart'],
            unixend=self.dict_ev['unixend']
            )
          ))}

        ## update if connected
        self.dict_ev = {**self.dict_ev, **dict(zip(['connected'], 
          [is_connected(unixtime=self.dict_environment['unixtime'],
            unixstart=self.dict_ev['unixstart'],
            unixend=self.dict_ev['unixend'])]
          ))}

        ### update device proposed mode, status, priority, and demand
        self.dict_ev = {**self.dict_ev, **dict(zip(['p_status', 'flexibility', 
          'priority', 'p_finish', 'p_demand', 'a_demand'], 
          device_battery(unixtime=self.dict_ev['unixtime'], 
            unixstart=self.dict_ev['unixstart'],
            unixend=self.dict_ev['unixend'],
            soc=self.dict_ev['soc'],
            charging_power=self.dict_ev['charging_power'],
            target_soc=self.dict_ev['target_soc'],
            capacity=self.dict_ev['capacity'],
            connected=self.dict_ev['connected'],
            progress=self.dict_ev['progress'],
            a_status=self.dict_ev['a_status'],
            a_demand=self.dict_ev['p_demand'])

          # device_charger_ev(unixtime=self.dict_ev['unixtime'], 
          #   unixstart=self.dict_ev['unixstart'],
          #   unixend=self.dict_ev['unixend'],
          #   soc=self.dict_ev['soc'],
          #   charging_power=self.dict_ev['charging_power'],
          #   target_soc=self.dict_ev['target_soc'],
          #   capacity=self.dict_ev['capacity'],
          #   connected=self.dict_ev['connected'],
          #   progress=self.dict_ev['progress'],
          #   a_status=self.dict_ev['a_status'],
          #   p_demand=np.diag(df.loc[self.dict_ev['soc'].round(3), self.dict_ev['profile']].interpolate()),
          #   # p_demand=np.array([dict_data[k] for k, x in zip(self.dict_ev['profile'], self.dict_ev['soc'])]).flatten(),
          #   a_demand=self.dict_ev['p_demand'])
          ))}
        




        ### update ldc_dongle approval for the proposed status and demand
        self.dict_ev = {**self.dict_ev, **dict(zip(['a_status'], 
          [(
            (ldc_dongle(priority=self.dict_ev['priority'], 
              signal=self.dict_injector['ldc_signal'], 
              p_status=self.dict_ev['p_status'],
              with_dr=self.dict_ev['with_dr'])==1) | 
            ((self.dict_ev['a_status']==1)&(self.dict_ev['progress']<=1))
            )*1
          ]
          ))}

        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_ev = {**self.dict_ev, **dict(zip(['unfinished',
          'finished','progress', 'soc', 'unixtime'], 
          enduse_ev(soc=self.dict_ev['soc'],
            target_soc=self.dict_ev['target_soc'],
            capacity=self.dict_ev['capacity'],
            a_demand=self.dict_ev['a_demand'],
            connected=self.dict_ev['connected'],
            unixtime=self.dict_ev['unixtime'],
            step_size=np.subtract(self.dict_environment['unixtime'], self.dict_ev['unixtime']), 
            )          
          ))}

        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error ev run:{e}')        
    ### feedback
    print('EV simulation stopped...')
         

  def storage(self):
    print('Running battery storage model...')
    ### initialize dynamic variables 
    self.dict_storage['unixstart'] = np.zeros(self.dict_devices['storage']['n_units'])
    self.dict_storage['unixend'] = np.zeros(self.dict_devices['storage']['n_units'])
    self.dict_storage['progress'] = np.random.rand(1, self.dict_devices['storage']['n_units'])

    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    while self.dict_environment['is_alive']:  
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_storage['unixtime'.mean()]:
          time.sleep(self.pause)

        ### update unixstart and unixend
        self.dict_storage = {**self.dict_storage, **dict(zip(['unixstart', 'unixend'], 
          make_schedule(unixtime=self.dict_environment['unixtime'],
            current_task=self.dict_schedule['current_task'],
            load_type_id=6, # code for clotheswashers
            unixstart=self.dict_storage['unixstart'],
            unixend=self.dict_storage['unixend']
            )
          ))}

        ## update if connected
        self.dict_storage = {**self.dict_storage, **dict(zip(['connected'], 
          [is_connected(unixtime=self.dict_environment['unixtime'],
            unixstart=self.dict_storage['unixstart'],
            unixend=self.dict_storage['unixend'])]
          ))}

        ### update device proposed mode, status, priority, and demand
        self.dict_storage = {**self.dict_storage, **dict(zip(['p_status', 'flexibility', 
          'priority', 'p_finish', 'p_demand', 'a_demand'], 
          device_charger_storage(unixtime=self.dict_storage['unixtime'], 
            unixstart=self.dict_storage['unixstart'],
            unixend=self.dict_storage['unixend'],
            soc=self.dict_storage['soc'],
            charging_power=self.dict_storage['charging_power'],
            target_soc=self.dict_storage['target_soc'],
            capacity=self.dict_storage['capacity'],
            connected=self.dict_storage['connected'],
            progress=self.dict_storage['progress'],
            a_status=self.dict_storage['a_status'],
            p_demand=self.dict_storage['charging_power'],
            a_demand=self.dict_storage['p_demand'])
          ))}

        ### update ldc_dongle approval for the proposed status and demand
        self.dict_storage = {**self.dict_storage, **dict(zip(['a_status'], 
          [(
            (ldc_dongle(priority=self.dict_storage['priority'], 
              signal=self.dict_injector['ldc_signal'], 
              p_status=self.dict_storage['p_status'],
              with_dr=self.dict_storage['with_dr'])==1) | 
            ((self.dict_storage['a_status']==1)&(self.dict_storage['progress']<=1))
            )*1
          ]

          ))}

        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        self.dict_storage = {**self.dict_storage, **dict(zip(['unfinished',
          'finished','progress', 'soc', 'unixtime'], 
          enduse_storage(soc=self.dict_storage['soc'],
            target_soc=self.dict_storage['target_soc'],
            capacity=self.dict_storage['capacity'],
            a_demand=self.dict_storage['a_demand'],
            connected=self.dict_storage['connected'],
            unixtime=self.dict_storage['unixtime'],
            step_size=np.subtract(self.dict_environment['unixtime'], self.dict_storage['unixtime']), 
            )          
          ))}        
      except Exception as e:
        print("Error AGGREGATOR.storage:{}".format(e))
      except KeyboardInterrupt:
        break 
    print("Storage simulation stopped...")

  def solar(self):
    print('Running solar panel model...')
    ### initialize dynamic variables 
    self.dict_solar['unixstart'] = np.zeros(self.dict_devices['solar']['n_units'])
    self.dict_solar['unixend'] = np.zeros(self.dict_devices['solar']['n_units'])
    self.dict_solar['mode'] = np.ones(self.dict_devices['solar']['n_units'])
    
    import solar
    
    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    while self.dict_environment['is_alive']:
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_solar['unixtime'].mean(): 
          time.sleep(self.pause)

        self.dict_solar['unixtime'] = self.dict_environment['unixtime']
        
        self.dict_solar = {**self.dict_solar, **dict(zip(['irradiance_roof', 
          'irradiance_wall1' , 'irradiance_wall2', 'irradiance_wall3', 
          'irradiance_wall4', 
          'a_demand'], 
          [solar.get_irradiance(
              unixtime=self.dict_solar['unixtime'],
              humidity=self.dict_environment['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=self.dict_solar['roof_tilt'],
              azimuth=self.dict_solar['azimuth'],
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_environment['isotime']),
          solar.get_irradiance(
              unixtime=self.dict_solar['unixtime'],
              humidity=self.dict_environment['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=np.ones(len(self.dict_solar['azimuth']))*90,
              azimuth=self.dict_solar['azimuth'],
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_environment['isotime']),
          solar.get_irradiance(
              unixtime=self.dict_solar['unixtime'],
              humidity=self.dict_environment['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=np.ones(len(self.dict_solar['azimuth']))*90,
              azimuth=self.dict_solar['azimuth']+90,
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_environment['isotime']),
          solar.get_irradiance(
              unixtime=self.dict_solar['unixtime'],
              humidity=self.dict_environment['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=np.ones(len(self.dict_solar['azimuth']))*90,
              azimuth=self.dict_solar['azimuth']-90,
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_environment['isotime']),
          solar.get_irradiance(
              unixtime=self.dict_solar['unixtime'],
              humidity=self.dict_environment['humidity'],
              latitude=self.dict_solar['latitude'],
              longitude=self.dict_solar['longitude'],
              elevation=self.dict_solar['elevation'],
              tilt=np.ones(len(self.dict_solar['azimuth']))*90,
              azimuth=self.dict_solar['azimuth']+180,
              albedo=self.dict_solar['albedo'],
              isotime=self.dict_environment['isotime']),
          np.multiply(np.multiply(self.dict_solar['capacity'], 
              self.dict_solar['irradiance_roof']*1e-3), 
              self.dict_solar['inverter_efficiency'])*-1
          ]
          ))}
        
        last_unixtime = self.dict_house['unixtime']
        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error solar:{e}')
        
    ### feedback 
    print('Solar simulation stopped...')
        

  def wind(self):
    print('Running wind turbine model...')
    ### initialize dynamic variables 
    self.dict_wind['unixstart'] = np.zeros(self.dict_devices['wind']['n_units'])
    self.dict_wind['unixend'] = np.zeros(self.dict_devices['wind']['n_units'])
    
    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)

    while self.dict_environment['is_alive']:
      try:
        while self.dict_environment['unixtime'].mean()<=self.dict_wind['unixtime'].mean():
          time.sleep(self.pause)
        self.dict_wind['unixtime'] = self.dict_environment['unixtime']
      except Exception as e:
        print("Error AGGREGATOR.wind:{}".format(e))
      except KeyboardInterrupt:
        break

  def schedules(self):
    print('Running schedules...')
    ### setup the profiles
    try:
      self.dict_interpolator_person = {}
      df_schedules = pd.read_csv('./specs/schedules.csv')
      
      for k in df_schedules.columns:
        self.dict_interpolator_person[k] = interp1d(df_schedules.index, df_schedules[k])
      
      del df_schedules

      if self.dict_devices:
        k = self.dict_devices.keys()[0]
        self.dict_schedule["schedule_profile"] =  eval(f'self.dict_{k}')["schedule"]  
        # only one type of appliance is needed since all appliances have the same profile for each house
        
      else:
        self.dict_schedule['schedule_profile'] = [f'P{(self.idx%5) + 1}']
        
    except Exception as e:
      print(f'Error schedules setup:{e}')


    while  self.dict_environment['is_alive']:
      try:
        ### update tasks
        weekminute = int((self.dict_environment['weekday'] * 24) + (self.dict_environment['hour'] * 60) + (self.dict_environment['minute']))
        self.dict_schedule = {**self.dict_schedule, **dict(zip(['current_task'], 
          [np.array([self.dict_interpolator_person[k](weekminute) for k in self.dict_schedule['schedule_profile']]).flatten()]
          ))}


        ### for testing ###
        # if self.dict_environment['minute']%5==0:
        #     self.dict_environment = {**self.dict_environment, **dict(zip(['current_task'], 
        #         [np.array([23 + (np.random.randint(60, 120) * 1e-5) ])]
        #         ))}

        '''NOTE: current_task values are floats wherein the integer part denotes the type of appliance, and the decimal part denotes the duration'''

        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error schedules run:{e}')

  def waterusage(self):
    # opening and closing of water valves
    print('Emulating water usage...')
    ### check if task schedules are loaded
    if self.dict_waterheater:
      for i in range(2):
        self.dict_valve = {**self.dict_valve, **dict(zip([f'valve{i}_unixstart', f'valve{i}_unixend', f'valve{i}_connected', f'valve{i}_a_status'], 
            [np.zeros(len(self.dict_waterheater['schedule'])), 
              np.zeros(len(self.dict_waterheater['schedule'])),
              np.zeros(len(self.dict_waterheater['schedule'])),
              np.zeros(len(self.dict_waterheater['schedule'])),
            ]        
            ))}
    else:
      for i in range(2):
        self.dict_valve = {**self.dict_valve, **dict(zip([f'valve{i}_unixstart', f'valve{i}_unixend', f'valve{i}_connected', f'valve{i}_a_status'], 
            [np.zeros(1), np.zeros(1), np.zeros(1), np.zeros(1)]        
            ))}

    while 'current_task' not in self.dict_schedule:
      time.sleep(self.pause)
    
    self.dict_valve['unixtime'] = self.dict_environment['unixtime']
    
    while self.dict_environment['is_alive']:
      try:
        ### check if unixtime has been updated
        while self.dict_valve['unixtime'] == self.dict_environment['unixtime']: 
          time.sleep(self.pause)
        
        ### update unixtime
        self.dict_valve['unixtime'] = self.dict_environment['unixtime']
        
        ### update unixstart and unixend
        for i in range(2):
          self.dict_valve = {**self.dict_valve, **dict(zip([f'valve{i}_unixstart', f'valve{i}_unixend'], 
            make_schedule(unixtime=self.dict_valve['unixtime'],
              current_task=self.dict_schedule['current_task'],  # float, code.duration
              load_type_id= 13+i, # 13 is the code for hot water valve, 14 is for the cold valve
              unixstart=self.dict_valve[f'valve{i}_unixstart'],
              unixend=self.dict_valve[f'valve{i}_unixend']
              )
            ))}

          ## update if connected
          self.dict_valve = {**self.dict_valve, **dict(zip([f'valve{i}_connected'], 
            [is_connected(unixtime=self.dict_valve['unixtime'],
              unixstart=self.dict_valve[f'valve{i}_unixstart'],
              unixend=self.dict_valve[f'valve{i}_unixend'])]
            ))}

          self.dict_valve = {**self.dict_valve, **dict(zip([f'valve{i}_a_status'], 
            [self.dict_valve[f'valve{i}_connected']]
            ))}

        time.sleep(self.pause)

      except Exception as e:
        print(f'Error waterusage loop:{e}')
      except KeyboardInterrupt:
        break        
    return   # mass_flow of water heater

  def window(self):
    ### this method affects the opening and closing of windows, impacts the air change per hour
    print('Emulating window opening / closing...')

    if self.dict_heatpump:
      for i in range(5):
        self.dict_window = {**self.dict_window, **dict(zip([f'window{i}_unixstart', f'window{i}_unixend', 
          f'window{i}_connected', f'window{i}_a_status'], 
            [np.zeros(len(self.dict_heatpump['schedule'])), 
            np.zeros(len(self.dict_heatpump['schedule'])),
            np.zeros(len(self.dict_heatpump['schedule'])),
            np.zeros(len(self.dict_heatpump['schedule'])),
            ]        
            ))}

    if self.dict_heater:
      for i in range(5):
        self.dict_window = {**self.dict_window, **dict(zip([f'window{i}_unixstart', f'window{i}_unixend', 
          f'window{i}_connected', f'window{i}_a_status'], 
            [np.zeros(len(self.dict_heater['schedule'])), 
            np.zeros(len(self.dict_heater['schedule'])),
            np.zeros(len(self.dict_heater['schedule'])),
            np.zeros(len(self.dict_heater['schedule'])),
            ]        
            ))}

    else:
      for i in range(5):
        self.dict_window = {**self.dict_window, **dict(zip([f'window{i}_unixstart', f'window{i}_unixend', 
          f'window{i}_connected', f'window{i}_a_status'], 
            [np.zeros(1), 
            np.zeros(1), 
            np.zeros(1), 
            np.zeros(1)
            ]
            ))}

    ### check if task schedules are loaded
    while 'current_task' not in self.dict_schedule:
      try:
        time.sleep(self.pause)
      except KeyboardInterrupt:
        break

    ### initialize the unixtime for windows
    self.dict_window['unixtime'] = self.dict_environment['unixtime']

    while self.dict_environment['is_alive']:
      try:
        ### check if unixtime has been updated
        while self.dict_environment['unixtime'].mean()<=self.dict_window['unixtime'].mean(): 
          time.sleep(self.pause)
          
        self.dict_window['unixtime'] = self.dict_environment['unixtime']
          
        ### update unixstart and unixend
        for i in range(5):
          self.dict_window = {**self.dict_window, **dict(zip([f'window{i}_unixstart', f'window{i}_unixend'], 
            make_schedule(unixtime=self.dict_window['unixtime'],
              current_task=self.dict_schedule['current_task'],  # float, code.duration
              load_type_id= 18+i, # codes for windows are 18..22
              unixstart=self.dict_window[f'window{i}_unixstart'],
              unixend=self.dict_window[f'window{i}_unixend']
              )
            ))}

          ## update if connected
          self.dict_window = {**self.dict_window, **dict(zip([f'window{i}_connected'], 
            [is_connected(unixtime=self.dict_window['unixtime'],
              unixstart=self.dict_window[f'window{i}_unixstart'],
              unixend=self.dict_window[f'window{i}_unixend'])]
            ))}

          self.dict_window = {**self.dict_window, **dict(zip([f'window{i}_a_status'], 
            [self.dict_window[f'window{i}_connected']]
            ))}

        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error window:{e}')
    
    ### feedback termination
    print(f'window simulation stopped...')
    

  def door(self):
    '''controls the opening and closing of doors, impacting airchange per hour'''
    if self.device_ip in [123, 124, 125]:
      print('Emulating door opening / closing ...')
      if self.dict_heatpump:
        print('test_heatpump')
        for i in range(3):
          self.dict_door = {**self.dict_door, **dict(zip([f'door{i}_unixstart', 
            f'door{i}_unixend', f'door{i}_connected', f'door{i}_a_status'], 
              [
                np.zeros(len(self.dict_heatpump['schedule'])), 
                np.zeros(len(self.dict_heatpump['schedule'])),
                np.zeros(len(self.dict_heatpump['schedule'])),
                np.zeros(len(self.dict_heatpump['schedule'])),
              ]        
              ))}
          
      elif self.dict_heater:
        print('test_heater')    
        for i in range(3):
          self.dict_door = {**self.dict_door, **dict(zip([f'door{i}_unixstart', 
            f'door{i}_unixend', f'door{i}_connected', f'door{i}_a_status'], 
              [
                np.zeros(len(self.dict_heater['schedule'])), 
                np.zeros(len(self.dict_heater['schedule'])),
                np.zeros(len(self.dict_heater['schedule'])),
                np.zeros(len(self.dict_heater['schedule'])),
              ]        
              ))}   
               
      else:
        print('test_else')
        for i in range(3):
          self.dict_door = {**self.dict_door, **dict(zip([f'door{i}_unixstart', 
            f'door{i}_unixend', f'door{i}_connected', f'door{i}_a_status'], 
              [
                np.zeros(1), np.zeros(1), np.zeros(1), np.zeros(1)
              ]
              ))}
          
      ### check if task schedules are loaded
      while 'current_task' not in self.dict_schedule:
        time.sleep(self.pause)
      
      self.dict_door['unixtime'] = self.dict_environment['unixtime']


      while self.dict_environment['is_alive']:
        try:
          ### check if unixtime has been updated
          if self.dict_environment['unixtime']<=self.dict_door['unixtime']: 
            time.sleep(self.pause)
            continue  # skip all processes if time was not updated yet
          else:
            self.dict_door['unixtime'] = self.dict_environment['unixtime']
            
          ### update unixstart and unixend
          for i in range(3):
            self.dict_door = {**self.dict_door, **dict(zip([f'door{i}_unixstart', f'door{i}_unixend'], 
              make_schedule(unixtime=self.dict_door['unixtime'],
                current_task=self.dict_schedule['current_task'],  # float, code.duration
                load_type_id= 23+i, # codes for doors are 23..24
                unixstart=self.dict_door[f'door{i}_unixstart'],
                unixend=self.dict_door[f'door{i}_unixend']
                )
              ))}

            ## update if connected
            self.dict_door = {**self.dict_door, **dict(zip([f'door{i}_connected'], 
              [is_connected(unixtime=self.dict_door['unixtime'],
                unixstart=self.dict_door[f'door{i}_unixstart'],
                unixend=self.dict_door[f'door{i}_unixend'])]
              ))}

            self.dict_door = {**self.dict_door, **dict(zip([f'door{i}_a_status'], 
              [self.dict_door[f'door{i}_connected']]
              ))}


          # if self.dict_environment['unixtime']%1 < 0.005:
          #     print(self.dict_environment['isotime'], self.dict_heater['mass_flow'], newstate)
          
          time.sleep(self.pause)
        except KeyboardInterrupt:
          break
        except Exception as e:
          print(f'Error door:{e}')
      
      ### feedback termination
      print(f'door simulation stopped...')
       

  def drive_chroma(self):
    # Send data to Chroma variable load simulator
    # through serial interface (rs232)
    import serial
      
    while self.dict_environment['is_alive']:
      try:
        rs232 = serial.Serial(
          port='/dev/ttyUSB0',
          baudrate = 57600,
          parity=serial.PARITY_NONE,
          stopbits=serial.STOPBITS_ONE,
          bytesize=serial.EIGHTBITS,
          timeout=1
          )

        if self.dict_emulation_value['chroma_load']<=0:
          rs232.write(b'LOAD OFF\r\n')
        else:    
          rs232.write(b'CURR:PEAK:MAX 28\r\n')
          rs232.write(b'MODE POW\r\n')
          cmd = 'POW '+ str(self.dict_emulation_value['chroma_load']) +'\r\n'
          rs232.write(cmd.encode())
          rs232.write(b'LOAD ON\r\n')
        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print("Error drive_chroma:", e)
        
    ### turn off chroma load
    print('Chroma stopped...')
    rs232.write(b'LOAD OFF\r\n')
        

  def drive_piface(self):
    # initialization to drive the pifacedigital
    try:
      import pifacedigitalio
      import RPi.GPIO as GPIO
      GPIO.setmode(GPIO.BOARD)
      GPIO.setwarnings(False)
      self.pins = [0,0,0,0,0,0,0,0]
      self.pf = pifacedigitalio.PiFaceDigital()
      
    
      self.df_relay, self.df_states = FUNCTIONS.create_states(report=False)  # create power levels based on resistor bank
      while self.dict_environment['is_alive']:
        try:
          ### add all demand
          total = 0.0
          for p in self.dict_summary_demand.keys():
            if p in ['heatpump', 'waterheater']: continue
            total = np.add(np.sum(self.dict_summary_demand[p]), total)

          total = min([total, 10e3])

          ### convert baseload value into 8-bit binary to drive 8 pinouts of piface
          newpins, grainy, chroma = FUNCTIONS.relay_pinouts(total, self.df_relay, self.df_states, report=False)
          # newpins, grainy, chroma = FUNCTIONS.pinouts(total, self.df_states, report=False)

          for i in range(len(self.pins)):
            if self.pins[i]==0 and newpins[i]==1:
              self.pf.output_pins[i].turn_on()
            elif self.pins[i]==1 and newpins[i]==0:
              self.pf.output_pins[i].turn_off()
            else:
              pass
          self.pins = newpins

          ### update grainy_load
          self.dict_emulation_value = {**self.dict_emulation_value, **dict(zip(['grainy_load'], 
              [grainy]
              ))}

          ### update chroma load
          self.dict_emulation_value = {**self.dict_emulation_value, **dict(zip(['chroma_load'], 
            [chroma]
            ))}

          time.sleep(self.pause)
        except KeyboardInterrupt:
          break
        except Exception as e:
          print("Error drive_piface:", e)

    except Exception as e:
      print("Error setting up piface:{}".format(e))
    
    ### reset IOs
    print('Grainy load stopped...')
    for i in range(len(self.pins)):
      self.pf.output_pins[i].turn_off()

  def drive_relay(self):
    try:
      import RPi.GPIO as GPIO
      GPIO.setmode(GPIO.BOARD)
      GPIO.setwarnings(False)
      
      unixtime = self.dict_environment['unixtime']
      # put in closed status initially
      setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
      GPIO.output([15, 32, 36, 38, 40], [0, 0, 0, 0, 0])
      
      while self.dict_environment['is_alive']:
        try:
          if unixtime >= self.dict_environment['unixtime']: 
            time.sleep(self.pause)
            continue
          else:
            unixtime = self.dict_environment['unixtime']

          if self.dict_heatpump and self.device_ip==111:
            new_status = int(self.dict_heatpump['a_status'][0])
          elif self.dict_waterheater and self.device_ip==112:
            new_status = int(self.dict_waterheater['a_status'][0])
          elif self.dict_heater and self.device_ip==103:
            new_status = int(self.dict_heater['a_status'][0])
          elif self.dict_fridge and self.device_ip==109:
            new_status = int(self.dict_fridge['a_status'][0])
          elif self.dict_freezer and self.device_ip==110:
            new_status = int(self.dict_freezer['a_status'][0])
          elif self.dict_clotheswasher and self.device_ip==106:
            new_status = int(self.dict_clotheswasher['a_status'][0])
          elif self.dict_clothesdryer and self.device_ip==105:
            new_status = int(self.dict_clothesdryer['a_status'][0])
          elif self.dict_dishwasher and self.device_ip==104:
            new_status = int(self.dict_dishwasher['a_status'][0])
          elif self.dict_ev and self.device_ip==108:
            new_status = int(self.dict_ev['a_status'][0])
          elif self.dict_storage and self.device_ip==107:
            new_status = int(self.dict_storage['a_status'][0])
          elif self.dict_valve and self.device_ip==113:  ### hot water valve
            new_status = int(self.dict_valve['valve0_a_status'][0])
          elif self.dict_valve and self.device_ip==114:  ### water dump for cold water is disabled
            new_status = 0 # int(self.dict_valve['valve1_a_status'][0])
          elif self.dict_window and self.device_ip in [118, 119, 120, 121, 122]: ### windows
            new_status = self.dict_window[f'window{self.device_ip-118}_a_status'][0]
          elif self.dict_door and self.device_ip in [123, 124, 125]: ### doors
            new_status = self.dict_door[f'door{self.device_ip-123}_a_status'][0]
          else:
            new_status = 0

          execute_state(int(new_status), device_id=self.device_ip, report=True)                    
          time.sleep(self.pause)
        except IOError:
          break
        except KeyboardInterrupt:
          break
        except Exception as e:
          print(f'Error drive_relay:{e}')
      ### feedback termination
      print('drive_relay stopped...')
      GPIO.cleanup()         # clean up the GPIO to reset mode
    
    except Exception as e:
      print("Error setting up GPIO:{}".format(e))

  def meter(self):
    from METER import EnergyMeter
    EM1 =  EnergyMeter(house=f'H{self.house_num}', IDs=[0])
    while self.dict_environment['is_alive']:
      try:
        EM1.get_meter_data(report=False)
        self.dict_meter = {**self.dict_meter, **dict(zip(['voltage_volt', 
          'current_amp', 'powerfactor', 'frequency_hz', 'power_kw', 
          'power_kvar', 'power_kva', 'energy_kwh', 'energy_kvarh' ], 
          [np.array([EM1.dict_data['voltage_0']]),
          np.array([EM1.dict_data['current_0']]),
          np.array([EM1.dict_data['powerfactor_0']]),
          np.array([EM1.dict_data['frequency_0']]),
          np.array([EM1.dict_data['power_active_0']]),
          np.array([EM1.dict_data['power_reactive_0']]),
          np.array([EM1.dict_data['power_apparent_0']]),
          np.array([EM1.dict_data['energy_active_0']]),
          np.array([EM1.dict_data['energy_reactive_0']])]
          ))}
        
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error meter:{e}')

    print("meter stopped...")
    del EM1

  def udp_comm(self):
    # Receive multicast message from the group
    while  self.dict_environment['is_alive']:
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
        break
      except Exception as e:
        print("Error in udp_comm binding socket:",e)
        print("Retrying...")
        time.sleep(10)
      except KeyboardInterrupt:
        break
    
    # Receive/respond loop
    while self.dict_environment['is_alive']:
      data, address = sock.recvfrom(1024)
      msg_in = data.decode("utf-8").replace("'", "\"")
      if msg_in:
        try:
          dict_msg = json.loads(msg_in)
          keys = dict_msg.keys()
          if 'states' in keys:
            dict_to_send = {}
            if dict_msg['states']=="all":
              for k in self.dict_state.keys():  
                dict_to_send.update({k:self.dict_state[k][0]}) # send only 1 item
            else:
              k = dict_msg['states']
              dict_to_send.update({k:self.dict_state[k][0]})
            ### send response 
            sock.sendto(str(dict_to_send).encode(), address)   
            
          if 'summary' in keys:
            dict_to_send = {}
            if dict_msg['summary']=="demand":
              for k in self.dict_summary_demand.keys():
                dict_to_send.update({k:self.dict_summary_demand[k][0]})
            elif dict_msg['summary']=="status":
              for k in self.dict_summary_status.keys():
                dict_to_send.update({k:self.dict_summary_status[k][0]})
            elif dict_msg['summary']=="mode":
              for k in self.dict_summary_mode.keys():
                dict_to_send.update({k:self.dict_summary_mode[k][0]})
            
            ### send response 
            sock.sendto(str(dict_to_send).encode(), address)   
            
          if 'ldc_signal' in keys: # update ldc_signal
            try:
              w = 0.99  # weight given to new value
              s = ((1-w)*self.dict_injector["ldc_signal"]) + (w*dict_msg["ldc_signal"])
            except:
              s = dict_msg['ldc_signal']
            self.dict_injector.update({"ldc_signal":np.array([s])})

          if 'injector' in keys:
            k = dict_msg['injector']
            if k in self.dict_injector.keys():
              sock.sendto(str({k:self.dict_injector[k][0]}).encode(), address)

              
        except Exception as e:
          print("Error in udp_comm respond loop:", e, msg_in, k)
          pass

        except KeyboardInterrupt:
          break

    ### inform main of stoppage
    print("multicast receiver stopped...")                      
    
  
  def history(self):
    time.sleep(5)
    while self.dict_environment['is_alive']:
      try:
        filename = '/home/pi/studies/results/{}_{}_{}.h5'.format(self.dict_environment['year'],
          self.dict_environment['month'], self.dict_environment['day'])
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
    print('Main terminated...')
    if self.simulation==0:
      try:
        print('Reseting IOs.')
        GPIO.cleanup()         # clean up the GPIO to reset mode
        if self.device_ip in list(range(100)):
          for i in range(len(self.pins)):
            self.pf.output_pins[i].turn_off()
      except Exception as e:
        print(f'Error reseting IOs:{e}')



