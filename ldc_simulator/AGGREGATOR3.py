
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
    simulation=0, endstamp=None, case=None, network=None, casefolder='assorted'):
    super(Aggregator, self).__init__()
    multiprocessing.Process.__init__(self)
    self.daemon = False

    self.name = 'Aggregator_{}'.format(self.n+1)

    ### common dictionary available in all threads
    manager = multiprocessing.Manager()
    self.dict_devices = manager.dict()
    self.dict_common = {} #manager.dict()
    self.dict_network = {} #manager.dict()
    self.dict_house = {} #manager.dict()
    self.dict_baseload = self.dict_house  # set another name for dict_house
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
    self.dict_injector = {} #manager.dict()
    self.dict_schedule = {} #manager.dict()
    self.dict_valve = {} #manager.dict()
    self.dict_window = {} #manager.dict()
    self.dict_door = {} #manager.dict()
    self.dict_blind = {} #manager.dict()
    self.dict_summary_demand = {} #manager.dict()
    self.dict_emulation_value = {} #manager.dict()
    self.dict_state = {} #manager.dict()
    self.dict_summary_mode = {} #manager.dict()
    self.dict_summary_status = {} #manager.dict()
    self.ac_state = {} #manager.dict()
    self.dict_meter = {} #manager.dict()
    

    self.pipe_agg_house0, self.pipe_agg_house1 = multiprocessing.Pipe()
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
    self.pipe_agg_injector0, self.pipe_agg_injector1 = multiprocessing.Pipe()
    self.pipe_agg_ouput0, self.pipe_agg_ouput1 = multiprocessing.Pipe()

    
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
      self.network_grid = network 
      self.casefolder = casefolder
      self.save_params = ['connected', 'temp_in', 'temp_out', 'priority', 'flexibility', 'soc', 
        'humidity_in', 'actual_demand', 'actual_status', 'mode']
    else:
      self.realtime = True
      self.timestamp = time.time()
      self.step_size = None
      self.endstamp = None
      self.case = None
      self.network_grid = None

    ### create globl objects
    self.weather = Weather(latitude=latitude, longitude=longitude, timestamp=self.timestamp)
    
    self.dict_common['unixtime'] = self.timestamp
    self.df_history = pd.DataFrame([], columns=self.dict_devices.keys())
    self.pause = 1e-64  # pause time used in thread interrupts
    self.save_interval = 1000

    self.setup()
    self.add_device(dict_new_devices=dict_devices)
    self.autorun()

  def setup(self):
    ### initialize dictionaries
    # emulation value
    self.dict_emulation_value.update({'grainy_load':0, 'chroma_load':0})

    

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

    ### house data is available
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

    # if 'waterheater' in self.dict_devices.keys():
    #   n_valve = self.dict_devices['waterheater']['n_units'] # based on n_waterheaters
    #   self.dict_valve['schedule'] = self.dict_house['schedule'][np.arange(n_valve)%n_house] 
    
    # list_n_window = []
    # if 'heatpump' in self.dict_devices.keys():
    #   list_n_window.append(self.dict_devices['heatpump']['n_units'])
    # if 'heater' in self.dict_devices.keys():
    #   list_n_window.append(self.dict_devices['heater']['n_units'])

    # if len(list_n_window):
    #   n_window = max(list_n_window) # based on max([n_heatpump, n_heaters])
    #   self.dict_window['schedule'] = self.dict_house['schedule'][np.arange(n_window)%n_house] 

    return


  def autorun(self):
    ### run common threads
    self.threads = [] 
    # create separate threads for each type of appliance
    for k in self.dict_devices.keys():
      if self.dict_devices[k]['n_units']:
        eval('self.threads.append(multiprocessing.Process(target=self.{}, args=()))'.format(k))
        
    if self.device_ip==100:
      self.threads.append(threading.Thread(target=self.drive_piface, args=()))
      self.threads.append(threading.Thread(target=self.drive_chroma, args=()))
    if self.device_ip==101:
      self.threads.append(threading.Thread(target=self.meter, args=()))
    if self.device_ip in list(range(103, 130)):
      self.threads.append(threading.Thread(target=self.drive_relay, args=()))
    if self.simulation==0:
      self.threads.append(threading.Thread(target=self.udp_comm, args=()))
      self.threads.append(multiprocessing.Process(target=self.ldc_injector, args=()))
    if self.simulation==1: # only run history for simulation not on raspi
      self.threads.append(multiprocessing.Process(target=self.network, args=()))
      self.threads.append(multiprocessing.Process(target=self.log_data, args=()))
   
    # self.threads.append(threading.Thread(target=self.valve, args=()))
    # self.threads.append(threading.Thread(target=self.window, args=()))
    # self.threads.append(threading.Thread(target=self.door, args=()))

    ### setup the profiles
    try:
      print('Running schedules...')
      df_schedules = pd.read_csv('./specs/schedules.csv')      
      k = self.dict_devices.keys()[0]
      self.dict_schedule["schedule_profile"] =  eval(f'self.dict_{k}')["schedule"]  

      '''All appliances have the same schedule_profile for each house.'''
    except Exception as e:
      print(f'Error schedules setup:{e}')
      self.dict_schedule['schedule_profile'] = [f'P{(self.idx%5) + 1}']

    # run threads
    self.dict_common.update({'is_alive': True, 'ldc_signal':10.0})
    for t in self.threads:
      t.daemon = True
      t.start()

    agg_data = {}
    timeit = []
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
        for k in self.dict_devices.keys():
          eval(f'self.pipe_agg_{k}0.send(self.dict_common)')
        ### gather data from the device simulators
        for k in self.dict_devices.keys():
          d = eval(f'self.pipe_agg_{k}0.recv()')
          self.dict_summary_demand[f'{k}_demand'] = [d['actual_demand'][d['house']==h].sum() for h in self.dict_house['name']]
          agg_data.update({k:d})
          
        if self.simulation==1:
          p_mw = np.sum(list(self.dict_summary_demand.values()), axis=0) * 1e-6
          loading_percent = np.sum(p_mw)*100/(0.4 * 0.9)
          loss_percent = loading_percent**2 * 0.013333  # factors are derived using regression as compared with pandapower simulation
          self.dict_common.update(ldc_injector(signal=self.dict_common['ldc_signal'], 
            latest_power= loading_percent + loss_percent, 
            target_power=75.0, 
            step_size=self.dict_common['step_size'],
            case=self.case,
            hour=self.dict_common['hour'],
            minute=self.dict_common['minute']))

          ### send data to network simulator
          self.pipe_agg_network0.send({'summary_demand':{'p_mw':p_mw}, 'common':self.dict_common})

          if self.pipe_agg_network0.poll():
            d = self.pipe_agg_network0.recv()
            agg_data.update({'network':d})

          ### send data to data_logger
          self.pipe_agg_ouput0.send(agg_data)
          
          # if self.dict_common['second']<1:
          print(self.dict_common['isotime'], 'ldc_signal:',self.dict_common['ldc_signal'], 'timeit:', time.perf_counter()-t1)
        

          if self.dict_common['unixtime'] >= self.endstamp: raise KeyboardInterrupt          
        else:
          ### send data to processes for emulations
          self.pipe_agg_injector0.send(self.dict_common)
          self.dict_common.update(self.pipe_agg_injector0.recv())

          # self.pipe_agg_udp0.send(self.dict_state)
          # self.dict_common.update(self.pipe_agg_injector0.recv())

          # self.threads.append(multiprocessing.Process(target=self.udp_comm, args=()))
          # self.threads.append(multiprocessing.Process(target=self.ldc_injector, args=()))
          # if self.device_ip==100:
          #   self.threads.append(multiprocessing.Process(target=self.drive_piface, args=()))
          #   self.threads.append(multiprocessing.Process(target=self.drive_chroma, args=()))
          # if self.device_ip==101:
          #   self.threads.append(multiprocessing.Process(target=self.meter, args=()))
          # if self.device_ip in list(range(103, 130)):
          #   self.threads.append(multiprocessing.Process(target=self.drive_relay, args=()))
          

        
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error AGGREGATOR.autorun:{e}')
      except KeyboardInterrupt:
        self.dict_common['is_alive'] = False
        ### send stop signal to device simulators
        for k in self.dict_devices.keys():
          eval(f'self.pipe_agg_{k}0.send(self.dict_common)')
        if self.simulation==1:
          self.pipe_agg_network0.send({'summary_demand':self.dict_summary_demand,'common':self.dict_common})
        else:
          pass
        
        for t in self.threads:
          t.join()

        ### close all pipes
        for k in self.dict_devices.keys():
          eval(f'self.pipe_agg_{k}0.close()')
        if self.simulation==1:
          self.pipe_agg_network0.close()
        else:
          pass
        
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
        
        pp.create_transformer(net, 0, 1, std_type="YNyn", parallel=1,tap_pos=0,
                                index=pp.get_free_id(net.trafo))
        net.trafo.reset_index()
        
        ### add zero sequence for lines
        net.line["r0_ohm_per_km"] = 0.0848
        net.line["x0_ohm_per_km"] = 0.4649556
        net.line["c0_nf_per_km"] = 230.6
        
        ### convert loads to asymmetric loads
        for i in net.load.index:
          row = net.load.loc[i]
          phases = [0,0,0]
          p = i % 3
          phases[p] = 1
          pp.create_asymmetric_load(net, row['bus'], 
            p_a_mw=0*phases[0], q_a_mvar=0*phases[0], 
            p_b_mw=0*phases[1], q_b_mvar=0*phases[1],
            p_c_mw=0*phases[2], q_c_mvar=0*phases[2], 
            # sn_mva=row['sn_mva']
            )
          
        net.load['p_mw'] = 0
        net.load['q_mvar'] = 0
        pp.add_zero_impedance_parameters(net)
        return net


      if self.network_grid=='dickert_lv_long':
        net = nw.create_dickert_lv_network(feeders_range='long', 
          linetype='C&OHL', customer='multiple', case='good', 
          trafo_type_name='0.4 MVA 20/0.4 kV', trafo_type_data=None)
        # adjust line lengths to create variations
        net.line.length_km = np.round(np.random.normal(0.040, 0.005, len(net.line.length_km)), 4)
        net = convert_to_3ph(net)
      elif self.network_grid=='ieee_european_lv':
        net = nw.ieee_european_lv_asymmetric("off_peak_1")
      elif self.network_grid=='ardmore':
        ### read saved network
        net = nw.create_dickert_lv_network(feeders_range='long', 
          linetype='C&OHL', customer='multiple', case='good', 
          trafo_type_name='0.4 MVA 20/0.4 kV', trafo_type_data=None)
        # adjust line lengths to create variations
        net = convert_to_3ph(net, sn_mva=0.03)
      elif self.network_grid==None:
        pass

      capacity = (self.dict_devices['house']['n_units'] * 5e3) * 1e-6
      self.dict_network = {'ldc_signal':100}
    

      factor = np.ones(self.dict_devices['house']['n_units'])
      pf = 0.9 # assumed powerfactor

      dict_save = {}
      dict_agg = {}
      while True:
        try:
          ### receive data from main routine
          while self.pipe_agg_network1.poll():
            dict_agg = self.pipe_agg_network1.recv()
          if len(dict_agg.keys())==0: continue
          self.dict_common.update(dict_agg['common'])
          if self.dict_common['is_alive']:
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
            ### update ldc_signal
            
            # net.res_trafo_3ph['ldc_signal'] = ldc_injector(signal=self.dict_common['ldc_signal'], 
            #       latest_power=net.res_trafo_3ph['loading_percent'].values,
            #       target_power=50.0, 
            #       step_size=self.dict_common['step_size'])['ldc_signal']

            ### send result to main routine
            recent_data = net.res_trafo_3ph.head(1).to_dict(orient='records')[0]
            recent_data['ldc_signal'] = self.dict_common['ldc_signal']
            loading_percent = np.sum(self.dict_summary_demand['p_mw'])*100/(pf*net.trafo.sn_mva.values[0])
            loss_percent = loading_percent**2 * 0.013333
            recent_data['loading_percent_nogrid'] = loading_percent + loss_percent
              
            # self.pipe_agg_network1.send(recent_data)
            # ### collect data for saving
            # dict_save.update({self.dict_common['unixtime']:recent_data})
            # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
            #   save_data(dict_save, case=self.case, folder=self.casefolder, 
            #     filename=f'{self.network_grid}.h5')
            #   dict_save = {}
          else:
            # save_data(dict_save, case=self.case, 
            #   folder=self.casefolder, filename=f'{self.network_grid}.h5')
            break
          time.sleep(self.pause)
        except Exception as e:
          print("Error AGGREGATOR.network:{}".format(e))
          self.pipe_agg_network1.send({})
        except KeyboardInterrupt:
          break
      print(f'Grid simulator stopped...')
      self.pipe_agg_network1.close()


  def log_data(self):
    ''' Log historical data'''  
    print('Starting data_logger...')
    dict_save = {}
    while True:
      try:
        if self.pipe_agg_ouput1.poll():
          agg_data = self.pipe_agg_ouput1.recv()

        # for k in agg_data.keys():
        #   dict_data.update({k:{agg_data[k]}})

        if len(dict_save.keys()) > self.save_interval:
          save_data(dict_save)

        time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.log_data:", e)


  def ldc_injector(self):
    ''' Model for LDC Injector'''
    print("Running ldc_injector...")
    # if self.simulation:
    #   while self.dict_common['is_alive']:
    #     try:
    #       if self.dict_network and self.dict_injector:
    #         ### update ldc_signal
    #         stamp, network_last_state = self.dict_network.popitem()
    #         self.dict_network.update({stamp:network_last_state}) # return item
    #         self.dict_injector.update(
    #           ldc_injector(signal=self.dict_injector['ldc_signal'], 
    #             latest_power=np.array([network_last_state['p_mw']]), 
    #             target_power=np.array([network_last_state['target_mw']]), 
    #             step_size=self.dict_common['step_size'])
    #           ) 
    #         self.dict_injector['p_mw'] = np.array([network_last_state['p_mw']])
    #         self.dict_injector['target_mw'] = np.array([network_last_state['target_mw']])
    #         self.dict_injector['isotime'] = self.dict_common['isotime']
    #     except Exception as e:
    #       print(f"Error AGGREGATOR.ldc_injector:{e}")
    #     except KeyboardInterrupt:
    #       break
    #     time.sleep(self.pause)
    # else:
    if self.simulation==0:
      try:
        ### for reading ldc signal
        import spidev
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # (bus, device)
        self.spi.bits_per_word = 8
        self.spi.max_speed_hz = 500000
        self.spi.mode = 3
        while self.dict_common['is_alive']:
          try:
            self.dict_common.update(self.pipe_agg_injector1.recv())
            # read ldc_signal from spi
            s = float(self.spi.readbytes(1)[0])
            if (s>0.0):
              self.dict_injector.update({
                'ldc_signal':s,
                'ldc_signal_spi':s,
                'unixtime':self.dict_common["unixtime"]
                })
            else:
              dict_s = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, 
                ip='224.0.2.0', port=17000, timeout=0.1, hops=1)
              if dict_s:
                s = dict_s["ldc_signal_spi"]
                self.dict_injector.update({
                  'ldc_signal':np.array([s]),
                  'unixtime':self.dict_common["unixtime"]
                  }) 
          except Exception as e:
            print("Error AGGREGATOR.ldc_injector:{}".format(e))
            dict_s = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, 
                ip='224.0.2.0', port=17000, timeout=0.1, hops=1)
            if dict_s:
              s = dict_s["ldc_signal_spi"]
              self.dict_injector.update({
                'ldc_signal':np.array([s]),
                'unixtime':self.dict_common["unixtime"]
                })
          except KeyboardInterrupt:
            break

          self.pipe_agg_injector1.send(self.dict_injector)
          time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.ldc_injector spidev setup:{}".format(e))
        while self.dict_common['is_alive']:
          try:
            self.dict_common.update(self.pipe_agg_injector1.recv())            
            dict_s = MULTICAST.send(dict_msg={"injector":"ldc_signal_spi"}, 
                ip='224.0.2.0', port=17000, timeout=0.1, hops=1)
            if dict_s:
              s = dict_s["ldc_signal_spi"]
              self.dict_injector.update({
                'ldc_signal':np.array([s]),
                'unixtime':self.dict_common["unixtime"]
                })
          except Exception as e:
            print("Error AGGREGATOR.ldc_injector:{}".format(e))
          except KeyboardInterrupt:
            break
          self.pipe_agg_injector1.send(self.dict_injector)
          time.sleep(self.pause)
          

  def house(self):
    print('Running house baseloads...')
    ### convert lists to np arrays
    for k, v in self.dict_house.items():
      self.dict_house[k] = np.array(v)

    df, validity = fetch_baseload(self.dict_common['unixtime'], n_seconds=3600)
    self.dict_house['mode'] = np.zeros(self.dict_devices['house']['n_units'])
    dict_save = {}
    
    while True:
      try:
        if self.pipe_agg_house1.poll():
          self.dict_common.update(self.pipe_agg_house1.recv())
        if self.dict_common['is_alive']:
          self.dict_house.update(self.dict_common)
          ### update baseload
          sk = np.add(self.dict_house['schedule_skew'], self.dict_common['unixtime'])
          self.dict_house['actual_demand'] = np.array([df.loc[x, y] for x, y in zip(sk, self.dict_house['profile'])])
          ### send update to main
          self.pipe_agg_house1.send(self.dict_house)
          ### fetch next batch of data
          if (self.dict_common['unixtime']>=validity['end']):
            df, validity = fetch_baseload(self.dict_common['unixtime'], n_seconds=3600)
          # ### save data
          # dict_save.update({self.dict_common['unixtime']:{'sum_actual_demand':np.sum(self.dict_house['actual_demand']),
          #   'avg_actual_demand': np.mean(self.dict_house['actual_demand']),
          #   'std_actual_demand': np.std(self.dict_house['actual_demand']),
          #   'max_actual_demand': np.max(self.dict_house['actual_demand']),
          #   'min_actual_demand': np.min(self.dict_house['actual_demand']),
          #   }})

          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, folder=self.casefolder, filename='house.h5')
          #   dict_save = {}
        else:
          # save_data(dict_save, case=self.case, folder=self.casefolder, filename='house.h5')
          break
        time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.house:", e)
      except KeyboardInterrupt:
        break
    print('Baseload simulation stopped...')
    self.pipe_agg_house1.close()


  def heatpump(self):
    print('Running heatpump...')
    load_type = 'heatpump'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
    if 'with_dr' in df.columns:
      if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
        df['with_dr'] = False
      else:
        idxs = np.arange(n_units)
        if self.case=='per_device': 
          np.random.shuffle(idxs)
        df.loc[idxs[0:n_ldc], 'with_dr'] = True
        df.loc[idxs[n_ldc:], 'with_dr'] = False
    eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
    del df

    for k, v in self.dict_heatpump.items():
      self.dict_heatpump[k] = np.array(v)
    
    self.dict_heatpump['unixstart'] = np.zeros(len(self.dict_heatpump['schedule']))
    self.dict_heatpump['unixend'] = np.ones(len(self.dict_heatpump['schedule']))
    self.dict_heatpump['ldc_signal'] = self.dict_heatpump['priority'] - 5
    
    # dict_save = {'connected':{}, 
    #   'temp_in':{}, 
    #   'temp_out':{},
    #   'humidity_in':{},
    #   'cooling_setpoint':{},
    #   'heating_setpoint':{},
    #   'flexibility':{}, 
    #   'priority':{},
    #   'actual_demand':{}
    # }
    
    dict_save = {}

    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_heatpump['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_heatpump['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]
      self.dict_heatpump['latitude'] = self.dict_house['latitude'][np.arange(n_units)%n_house]
      self.dict_heatpump['longitude'] = self.dict_house['longitude'][np.arange(n_units)%n_house]
      self.dict_heatpump['elevation'] = self.dict_house['elevation'][np.arange(n_units)%n_house]
      self.dict_heatpump['roof_tilt'] = self.dict_house['roof_tilt'][np.arange(n_units)%n_house]
      self.dict_heatpump['azimuth'] = self.dict_house['azimuth'][np.arange(n_units)%n_house]
      self.dict_heatpump['albedo'] = self.dict_house['albedo'][np.arange(n_units)%n_house]
      self.dict_heatpump['roof_area'] = self.dict_house['roof_area'][np.arange(n_units)%n_house]
      self.dict_heatpump['wall_area'] = self.dict_house['wall_area'][np.arange(n_units)%n_house]
      self.dict_heatpump['window_area'] = self.dict_house['window_area'][np.arange(n_units)%n_house]
      self.dict_heatpump['skylight_area'] = self.dict_house['skylight_area'][np.arange(n_units)%n_house]

      ### initialize windows    
      for i in range(1): # 5 windows
        self.dict_window[f'window{i}'] = {
          'unixstart': np.zeros(n_units),
          'unixend': np.ones(n_units),
          'connected': np.zeros(n_units),
          'actual_status': np.zeros(n_units)
        }  
      ### initialize mass_flow
      self.dict_heatpump['mass_flow'] = np.clip(np.random.normal(1.225*0.01, 0.001, n_units), 
        a_min=0.001, a_max=1.225)      
        # air density is 1.225kg/m^3 at 15degC sea level
        # air density is 1.2041 kg/m^3 at 20 degC sea level

      while True:
        try:
          ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
          if self.pipe_agg_heatpump1.poll(): 
            self.dict_common.update(self.pipe_agg_heatpump1.recv())
          if self.dict_common['is_alive']:
            ### update window status
            for i in range(1):  # mass_flow is only based on 1 window (for simplicity), instead of five
              self.dict_window[f'window{i}'].update(make_schedule(unixtime=self.dict_common['unixtime'],
                  current_task=self.dict_common['current_task'][self.dict_heatpump['schedule']].values,  # float, code.duration
                  load_type_id= 18+i, # 18 to 22 is the code for window
                  unixstart=self.dict_window[f'window{i}']['unixstart'],
                  unixend=self.dict_window[f'window{i}']['unixend'],
                  schedule_skew=self.dict_heatpump['schedule_skew']))
              self.dict_window[f'window{i}'].update(is_connected(unixtime=self.dict_common['unixtime'],
                  unixstart=self.dict_window[f'window{i}']['unixstart'],
                  unixend=self.dict_window[f'window{i}']['unixend']))
              self.dict_window[f'window{i}'].update({'actual_status':self.dict_window[f'window{i}']['connected']})
            ### update mass_flow, air density = 1.225 kg/m^3
            self.dict_heatpump['mass_flow'] = np.clip(np.multiply(self.dict_window['window0']['actual_status'], 
                np.random.normal(1.225*0.001, 1e-6, n_units)), a_min=1e-6, a_max=1.225)  # 1 liter/s

            # ### update unixstart and unixend
            self.dict_heatpump.update(
              make_schedule(unixtime=self.dict_common['unixtime'],
                current_task=self.dict_common['current_task'][self.dict_heatpump['schedule']].values,
                load_type_id=11, # 11 is the code for heatpumps
                unixstart=self.dict_heatpump['unixstart'],
                unixend=self.dict_heatpump['unixend'],
                schedule_skew=self.dict_heatpump['schedule_skew'])
              )
            ### update if connected
            self.dict_heatpump.update(
              is_connected(unixtime=self.dict_common['unixtime'],
                unixstart=self.dict_heatpump['unixstart'],
                unixend=self.dict_heatpump['unixend'])
              )         

            ### update device proposed mode, status, priority, and demand
            self.dict_heatpump.update(
              device_heatpump(mode=self.dict_heatpump['mode'], 
              temp_in=self.dict_heatpump['temp_in'], 
              temp_min=self.dict_heatpump['temp_min'], 
              temp_max=self.dict_heatpump['temp_max'],
              temp_out=self.dict_common['temp_out'], 
              cooling_setpoint=self.dict_heatpump['cooling_setpoint'], 
              heating_setpoint=self.dict_heatpump['heating_setpoint'],
              tolerance=self.dict_heatpump['tolerance'], 
              cooling_power=self.dict_heatpump['cooling_power'], 
              heating_power=self.dict_heatpump['heating_power'],
              cop=self.dict_heatpump['cop'],
              standby_power=self.dict_heatpump['standby_power'],
              ventilation_power=self.dict_heatpump['ventilation_power'],
              actual_status=self.dict_heatpump['actual_status'])
            )
            ### update ldc_signal
            self.dict_heatpump.update(read_signal(ldc_signal=self.dict_heatpump['ldc_signal'], 
              new_signal=self.dict_common['ldc_signal'], 
              n_units=n_units))
            ### update ldc_dongle approval for the proposed status and demand
            self.dict_heatpump.update(
              ldc_dongle(flexibility=self.dict_heatpump['flexibility'],
                priority=self.dict_heatpump['priority'], 
                ldc_case=self.case,
                signal=self.dict_heatpump['ldc_signal'], 
                proposed_status=self.dict_heatpump['proposed_status'],
                with_dr=self.dict_heatpump['with_dr'],
                unixtime=self.dict_common['unixtime'])
              )
            ### change temperature setpoint
            self.dict_heatpump.update(
              adjust_setpoint(actual_status=self.dict_heatpump['actual_status'], 
                mode=self.dict_heatpump['mode'], 
                cooling_setpoint=self.dict_heatpump['cooling_setpoint'], 
                heating_setpoint=self.dict_heatpump['heating_setpoint'], 
                upper_limit=self.dict_heatpump['temp_max'], 
                lower_limit=self.dict_heatpump['temp_min']),
              )
            ### update environment
            self.dict_heatpump['temp_out'] = np.add(np.random.normal(0, 0.1, n_units), self.dict_common['temp_out'])
            self.dict_heatpump['humidity'] = np.add(np.random.normal(0, 0.1, n_units), self.dict_common['humidity'])
            self.dict_heatpump['windspeed'] = np.add(np.random.normal(0, 0.1, n_units), self.dict_common['windspeed'])
            ### update solar heat
            self.dict_heatpump.update(solar_heat(unixtime=self.dict_common['unixtime'], 
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
              enduse_tcl(heat_all=self.dict_heatpump['heat_all'],
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
                step_size=self.dict_common['step_size'],
                unixtime=self.dict_common['unixtime'],
                connected=self.dict_heatpump['connected'])
              )
            ### temporary calculation for indoor humidity
            self.dict_heatpump['humidity_in'] = np.random.normal(1, 0.001, len(self.dict_heatpump['temp_in'])) * self.dict_common['humidity'] * 100
            ### send data to main
            self.pipe_agg_heatpump1.send(self.dict_heatpump)
            ### save data
            # for k in dict_save.keys():
            #   dict_save[k].update({int(self.dict_common['unixtime']):{1:k, 2:k}}) 
            #   print('Done', k)
            #   for x in dict_save.keys():
            #     print(f'*****************{x}*****************')
            #     print(pd.DataFrame.from_dict(dict_save[x], orient='index'))


            # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_heatpump['temp_in']),
            #   'min_temp_in': np.min(self.dict_heatpump['temp_in']),
            #   'avg_temp_in': np.mean(self.dict_heatpump['temp_in']),
            #   'std_temp_in': np.std(self.dict_heatpump['temp_in']),
            #   'avg_temp_out': np.mean(self.dict_common['temp_out']),
            #   'mode': ''.join(self.dict_heatpump['mode'].astype(str)),
            #   'actual_status': ''.join(self.dict_heatpump['actual_status'].astype(str)),
            #   'connected': ''.join(self.dict_heatpump['connected'].astype(str)),
            #   'max_temp_in_active': np.max(self.dict_heatpump['temp_in_active']) if self.dict_heatpump['temp_in_active'].shape[0]>0 else np.nan,
            #   'min_temp_in_active': np.min(self.dict_heatpump['temp_in_active']) if self.dict_heatpump['temp_in_active'].shape[0]>0 else np.nan,
            #   'avg_temp_in_active': np.mean(self.dict_heatpump['temp_in_active']) if self.dict_heatpump['temp_in_active'].shape[0]>0 else np.nan,
            #   'std_temp_in_active': np.std(self.dict_heatpump['temp_in_active']) if self.dict_heatpump['temp_in_active'].shape[0]>0 else np.nan,
            #   'max_cooling_setpoint': np.max(self.dict_heatpump['cooling_setpoint']),
            #   'min_cooling_setpoint': np.min(self.dict_heatpump['cooling_setpoint']),
            #   'avg_cooling_setpoint': np.mean(self.dict_heatpump['cooling_setpoint']),
            #   'std_cooling_setpoint': np.std(self.dict_heatpump['cooling_setpoint']),
            #   'max_heating_setpoint': np.max(self.dict_heatpump['heating_setpoint']),
            #   'min_heating_setpoint': np.min(self.dict_heatpump['heating_setpoint']),
            #   'avg_heating_setpoint': np.mean(self.dict_heatpump['heating_setpoint']),
            #   'std_heating_setpoint': np.std(self.dict_heatpump['heating_setpoint']),
            #   'max_flexibility': np.max(self.dict_heatpump['flexibility']),
            #   'min_flexibility': np.min(self.dict_heatpump['flexibility']),
            #   'avg_flexibility': np.mean(self.dict_heatpump['flexibility']),
            #   'std_flexibility': np.std(self.dict_heatpump['flexibility']),
            #   'max_priority': np.max(self.dict_heatpump['priority']),
            #   'min_priority': np.min(self.dict_heatpump['priority']),
            #   'avg_priority': np.mean(self.dict_heatpump['priority']),
            #   'std_priority': np.std(self.dict_heatpump['priority']),
            #   'max_humidity_in': np.max(self.dict_heatpump['humidity_in']),
            #   'min_humidity_in': np.min(self.dict_heatpump['humidity_in']),
            #   'avg_humidity_in': np.mean(self.dict_heatpump['humidity_in']),
            #   'std_humidity_in': np.std(self.dict_heatpump['humidity_in']),
            #   'sum_a_demand': np.sum(self.dict_heatpump['actual_demand'])}})
            
            # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
            #   save_data(dict_save, case=self.case, folder=self.casefolder, filename='heatpump.h5')
            #   dict_save = {}#dict_save.fromkeys(dict_save, {})
          else:
            # save_data(dict_save, case=self.case, folder=self.casefolder, filename='heatpump.h5')
            break
          time.sleep(self.pause)  # to give way to other threads
        except Exception as e:
          print(f'Error heatpump:{e}')
        except KeyboardInterrupt:
          break
    elif self.device_ip==111:
      import SENSIBO
      dict_a_mode = {'cool':0, 'heat':1, 'fan':2, 'dry':3, 'auto':4}  # actual mode
      self.sensibo_api = SENSIBO.SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
      devices = self.sensibo_api.devices()
      self.uid = devices['ldc_heatpump_h{}'.format(int(self.house_num))]
      self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
      self.sensibo_history = self.sensibo_api.pod_history(self.uid)
      
      while self.dict_common['is_alive']:
        try:
          ### get actual sensibo state every 30 seconds
          if self.dict_common['second']%30==0:
            self.sensibo_state = self.sensibo_api.pod_ac_state(self.uid)
            self.sensibo_history = self.sensibo_api.pod_history(self.uid)
          
          ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
          if self.pipe_agg_heatpump1.poll():
            self.dict_common.update(self.pipe_agg_heatpump1.recv())
          self.dict_heatpump.update(self.dict_common)
          
          ### update unixstart and unixend
          self.dict_heatpump.update(
            make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_heatpump['schedule']].values,
              load_type_id=11, # 11 is the code for heatpumps
              unixstart=self.dict_heatpump['unixstart'],
              unixend=self.dict_heatpump['unixend'],
              schedule_skew=self.dict_heatpump['schedule_skew'])
            )
          ## update if connected
          self.dict_heatpump.update(
            is_connected(unixtime=self.dict_common['unixtime'],
              unixstart=self.dict_heatpump['unixstart'],
              unixend=self.dict_heatpump['unixend'])
            )
          ### update device proposed mode, status, priority, and demand (this is a simulation model)
          self.dict_heatpump.update(
            device_heatpump(mode=self.dict_heatpump['mode'], 
              temp_in=self.dict_heatpump['temp_in'], 
              temp_min=self.dict_heatpump['temp_min'], 
              temp_max=self.dict_heatpump['temp_max'],
              temp_out=self.dict_common['temp_out'], 
              cooling_setpoint=self.dict_heatpump['cooling_setpoint'], 
              heating_setpoint=self.dict_heatpump['heating_setpoint'],
              tolerance=self.dict_heatpump['tolerance'], 
              cooling_power=self.dict_heatpump['cooling_power'], 
              heating_power=self.dict_heatpump['heating_power'],
              cop=self.dict_heatpump['cop'],
              standby_power=self.dict_heatpump['standby_power'],
              ventilation_power=self.dict_heatpump['ventilation_power'],
              actual_status=self.dict_heatpump['actual_status'])
            )
          ### update ldc_dongle approval for the proposed status and demand
          self.dict_heatpump.update(
            ldc_dongle(flexibility=self.dict_heatpump['flexibility'],
              priority=self.dict_heatpump['priority'], 
              ldc_case=self.case,
              signal=self.dict_heatpump['ldc_signal'], 
              proposed_status=self.dict_heatpump['proposed_status'],
              with_dr=self.dict_heatpump['with_dr'],
              unixtime=self.dict_common['unixtime'])
            )

          ### control
          ### change status
          # if self.dict_heatpump['actual_status'][0]==1 and self.sensibo_state['on']==False:
          #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "on", True) 
          # elif self.dict_heatpump['actual_status'][0]==0 and self.sensibo_state['on']==True:
          #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "on", False)
          # ### change mode if needed (disabled since this is automanaged by sensibo)
          # if self.dict_heatpump['mode'][0]==1 and self.sensibo_state['mode']=='cool':
          #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "mode", "heat")  # change to heating
          # elif self.dict_heatpump['mode'][0]==0 and self.sensibo_state['mode']=='heat':
          #     self.sensibo_api.pod_change_ac_state(self.uid, self.sensibo_state, "mode", "cool")  # change to cooling
          
          ### change temperature setpoint
          self.dict_heatpump.update(
            adjust_setpoint(actual_status=self.dict_heatpump['actual_status'], 
              mode=self.dict_heatpump['mode'], 
              cooling_setpoint=self.dict_heatpump['cooling_setpoint'], 
              heating_setpoint=self.dict_heatpump['heating_setpoint'], 
              upper_limit=self.dict_heatpump['temp_max'], 
              lower_limit=self.dict_heatpump['temp_min']),
            )
          ### implement targetTemperature adjustment
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
          self.dict_heatpump['temp_in'] = np.array([self.sensibo_history['temperature'][-1]['value']])
          self.dict_heatpump['temp_mat'] = np.array([self.sensibo_history['temperature'][-1]['value']])
          self.dict_heatpump['temp_in_active'] = np.array([self.sensibo_history['temperature'][-1]['value']])
            
          ### indoor humidity (actual reading)
          self.dict_heatpump['humidity_in'] = np.array([self.sensibo_history['humidity'][-1]['value']])

          ### additional data
          self.dict_heatpump['heatpump_a_mode'] = np.array([dict_a_mode[self.sensibo_state['mode']]])
          self.dict_heatpump['heatpump_target_temp'] = np.array([self.sensibo_state['targetTemperature']])
          

          self.pipe_agg_heatpump1.send(self.dict_heatpump)
          time.sleep(self.pause)
        except Exception as e:
          print(f'Error heatpump actual device:{e}')
        except KeyboardInterrupt:
          break
    ### feedback
    print('Heatpump simulation stopped...')
    self.pipe_agg_heatpump1.close()
        

  def heater(self):
    print('Running electric heater...')
    load_type = 'heater'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df
    for k, v in self.dict_heater.items():
      self.dict_heater[k] = np.array(v)
    
    ### initialize dynamic variables
    self.dict_heater['unixstart'] = np.zeros(n_units)
    self.dict_heater['unixend'] = np.ones(n_units)
    self.dict_heater['ldc_signal'] = self.dict_heater['priority'] - 5
    
    # dict_save = {'connected':{}, 
    #   'temp_in':{}, 
    #   'humidity_in':{},
    #   'heating_setpoint':{},
    #   'flexibility':{}, 
    #   'priority':{},
    #   'actual_demand':{}
    # }
    # params = list(dict_save.keys())
    dict_save = {}
    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_heater['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_heater['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house] 
      self.dict_heater['latitude'] = self.dict_house['latitude'][np.arange(n_units)%n_house]
      self.dict_heater['longitude'] = self.dict_house['longitude'][np.arange(n_units)%n_house]
      self.dict_heater['elevation'] = self.dict_house['elevation'][np.arange(n_units)%n_house]
      self.dict_heater['roof_tilt'] = self.dict_house['roof_tilt'][np.arange(n_units)%n_house]
      self.dict_heater['azimuth'] = self.dict_house['azimuth'][np.arange(n_units)%n_house]
      self.dict_heater['albedo'] = self.dict_house['albedo'][np.arange(n_units)%n_house]
      self.dict_heater['roof_area'] = self.dict_house['roof_area'][np.arange(n_units)%n_house]
      self.dict_heater['wall_area'] = self.dict_house['wall_area'][np.arange(n_units)%n_house]
      self.dict_heater['window_area'] = self.dict_house['window_area'][np.arange(n_units)%n_house]
      self.dict_heater['skylight_area'] = self.dict_house['skylight_area'][np.arange(n_units)%n_house]
   
      ### initialize windows    
      for i in range(1): # 5 windows: 0 for hot, 1 for cold
        self.dict_window[f'window{i}'] = {
          'unixstart': np.zeros(n_units),
          'unixend': np.ones(n_units),
          'connected': np.zeros(n_units),
          'actual_status': np.zeros(n_units)
        }
    
    ### initialize mass_flow
    self.dict_heater['mass_flow'] = np.clip(np.random.normal(1.225*0.001, 1e-6, n_units), 
      a_min=1e-6, a_max=1.225)      

    while True:
      try:
        if self.pipe_agg_heater1.poll():             
          self.dict_common.update(self.pipe_agg_heater1.recv())
        if self.dict_common['is_alive']:
          ### update window status
          for i in range(1):
            self.dict_window[f'window{i}'].update(make_schedule(unixtime=self.dict_common['unixtime'],
                current_task=self.dict_common['current_task'][self.dict_heater['schedule']].values,  # float, code.duration
                load_type_id= 18+i, # 18 to 22 is the code for window
                unixstart=self.dict_window[f'window{i}']['unixstart'],
                unixend=self.dict_window[f'window{i}']['unixend'],
                schedule_skew=self.dict_heater['schedule_skew']))
            self.dict_window[f'window{i}'].update(is_connected(unixtime=self.dict_common['unixtime'],
                unixstart=self.dict_window[f'window{i}']['unixstart'],
                unixend=self.dict_window[f'window{i}']['unixend']))
            self.dict_window[f'window{i}'].update({'actual_status':self.dict_window[f'window{i}']['connected']})
          ### update mass_flow, air density = 1.225 kg/m^3 at 15 degC 101.325kPa (sea level)
          self.dict_heater['mass_flow'] = np.clip(np.multiply(self.dict_window['window0']['actual_status'], 
              np.random.normal(1.225*0.001, 1e-6, n_units)), a_min=0.001, a_max=1.225) # 1L/s
              
          ### update unixstart and unixend
          self.dict_heater.update(
            make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_heater['schedule']].values,
              load_type_id=3, # code for heaters
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
              actual_status=self.dict_heater['actual_status'])
            )
          ### update ldc_signal
          self.dict_heater.update(read_signal(ldc_signal=self.dict_heater['ldc_signal'], 
            new_signal=self.dict_common['ldc_signal'], 
            n_units=n_units))
          ### update ldc_dongle approval for the proposed status and demand
          self.dict_heater.update(
            ldc_dongle(flexibility=self.dict_heater['flexibility'],
              priority=self.dict_heater['priority'], 
              ldc_case=self.case,
              signal=self.dict_heater['ldc_signal'], 
              proposed_status=self.dict_heater['proposed_status'],
              with_dr=self.dict_heater['with_dr'],
              unixtime=self.dict_common['unixtime'])
            )
          ### update solar heat
          self.dict_heater.update(solar_heat(unixtime=self.dict_common['unixtime'], 
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
            enduse_tcl(heat_all=self.dict_heater['heating_power_thermal'],
              air_part=self.dict_heater['air_part'],
              temp_in=self.dict_heater['temp_in'],
              temp_mat=self.dict_heater['temp_mat'],
              temp_out=self.dict_common['temp_out'],
              Um=self.dict_heater['Um'],
              Ua=self.dict_heater['Ua'],
              Cp=self.dict_heater['Cp'],
              Ca=self.dict_heater['Ca'],
              Cm=self.dict_heater['Cm'],
              mass_flow=self.dict_heater['mass_flow'],
              step_size=self.dict_common['step_size'],
              unixtime=self.dict_common['unixtime'],
              connected=self.dict_heater['connected'])
            )
          ### temporary calculation for indoor humidity
          self.dict_heater['humidity_in'] = np.random.normal(1, 0.001, len(self.dict_heater['temp_in'])) * self.dict_common['humidity'] * 100
          ### send data to main  
          self.pipe_agg_heater1.send(self.dict_heater)
          ### save data
          # for k in params:
          #   dict_save[k].update({self.dict_common['unixtime']:dict(zip(self.dict_heater['name'], 
          #     self.dict_heater[k]))})

          # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_heater['temp_in']),
          #   'min_temp_in': np.min(self.dict_heater['temp_in']),
          #   'avg_temp_in': np.mean(self.dict_heater['temp_in']),
          #   'std_temp_in': np.std(self.dict_heater['temp_in']),
          #   'avg_temp_out': np.mean(self.dict_common['temp_out']),
          #   'mode': ''.join(self.dict_heater['mode'].astype(str)),
          #   'actual_status': ''.join(self.dict_heater['actual_status'].astype(str)),
          #   'connected': ''.join(self.dict_heater['connected'].astype(str)),
          #   'max_temp_in_active': np.max(self.dict_heater['temp_in_active']) if self.dict_heater['temp_in_active'].shape[0]>0 else np.nan,
          #   'min_temp_in_active': np.min(self.dict_heater['temp_in_active']) if self.dict_heater['temp_in_active'].shape[0]>0 else np.nan,
          #   'avg_temp_in_active': np.mean(self.dict_heater['temp_in_active']) if self.dict_heater['temp_in_active'].shape[0]>0 else np.nan,
          #   'std_temp_in_active': np.std(self.dict_heater['temp_in_active']) if self.dict_heater['temp_in_active'].shape[0]>0 else np.nan,
          #   'max_heating_setpoint': np.max(self.dict_heater['heating_setpoint']),
          #   'min_heating_setpoint': np.min(self.dict_heater['heating_setpoint']),
          #   'avg_heating_setpoint': np.mean(self.dict_heater['heating_setpoint']),
          #   'std_heating_setpoint': np.std(self.dict_heater['heating_setpoint']),
          #   'max_flexibility': np.max(self.dict_heater['flexibility']),
          #   'min_flexibility': np.min(self.dict_heater['flexibility']),
          #   'avg_flexibility': np.mean(self.dict_heater['flexibility']),
          #   'std_flexibility': np.std(self.dict_heater['flexibility']),
          #   'max_priority': np.max(self.dict_heater['priority']),
          #   'min_priority': np.min(self.dict_heater['priority']),
          #   'avg_priority': np.mean(self.dict_heater['priority']),
          #   'std_priority': np.std(self.dict_heater['priority']),
          #   'max_humidity_in': np.max(self.dict_heater['humidity_in']),
          #   'min_humidity_in': np.min(self.dict_heater['humidity_in']),
          #   'avg_humidity_in': np.mean(self.dict_heater['humidity_in']),
          #   'std_humidity_in': np.std(self.dict_heater['humidity_in']),
          #   'sum_a_demand': np.sum(self.dict_heater['actual_demand'])}})
        
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, folder=self.casefolder, filename='heater.h5')
          #   dict_save = {} #dict_save.fromkeys(dict_save, {})
        else:
          # save_data(dict_save, case=self.case, folder=self.casefolder, filename='heater.h5')
          break
        time.sleep(self.pause)  # to give way to other threads
      except Exception as e:
        print(f'Error heater:{e}')
      except KeyboardInterrupt:
        break        
    ### feedback
    print('Electric heater simulation stopped...')
    self.pipe_agg_heater1.close()


  def waterheater(self):
    print('Running waterheater...')
    load_type = 'waterheater'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df

    for k, v in self.dict_waterheater.items():
      self.dict_waterheater[k] = np.array(v)
    
    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_waterheater['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_waterheater['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
      self.dict_valve['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
      ### initialize water valves    
      for i in range(2): # 2 valves: 0 for hot, 1 for cold
        self.dict_valve[f'valve{i}'] = {
          'unixstart': np.zeros(n_units),
          'unixend': np.ones(n_units),
          'connected': np.zeros(n_units),
          'actual_status': np.zeros(n_units)
        }
        
    ### initialization
    self.dict_waterheater['mass_flow'] = np.zeros(n_units)
    self.dict_waterheater['ldc_signal'] = self.dict_waterheater['priority'] - 5
    
    # dict_save = {'connected':{}, 
    #   'temp_in':{}, 
    #   'heating_setpoint':{},
    #   'flexibility':{}, 
    #   'priority':{},
    #   'actual_demand':{}
    # }
    # params = list(dict_save.keys())
    dict_save = {}
    dict_wh_temp = {}
    if True: #self.simulation:
      while True:
        try:
          if self.pipe_agg_waterheater1.poll():
            self.dict_common.update(self.pipe_agg_waterheater1.recv())
          if self.dict_common['is_alive']:
            ### update valve status
            for i in range(2):
              self.dict_valve[f'valve{i}'].update(make_schedule(unixtime=self.dict_common['unixtime'],
                  current_task=self.dict_common['current_task'][self.dict_waterheater['schedule']].values,  # float, code.duration
                  load_type_id= 13+i, # 13 is the code for hot water valve, 14 is for the cold valve
                  unixstart=self.dict_valve[f'valve{i}']['unixstart'],
                  unixend=self.dict_valve[f'valve{i}']['unixend'],
                  schedule_skew=self.dict_waterheater['schedule_skew']))
              self.dict_valve[f'valve{i}'].update(is_connected(unixtime=self.dict_common['unixtime'],
                  unixstart=self.dict_valve[f'valve{i}']['unixstart'],
                  unixend=self.dict_valve[f'valve{i}']['unixend']))
              self.dict_valve[f'valve{i}'].update({'actual_status':self.dict_valve[f'valve{i}']['connected']})
            ### update mass_flow
            ### update mass_flow, water density = 999.1 kg/m^3 (or 0.999 kg/liter) at 15 degC 101.325kPa (sea level)
            self.dict_waterheater['mass_flow'] = np.clip(np.multiply(self.dict_valve['valve0']['actual_status'], 
                np.random.normal(0.9991*0.005, 1e-6, n_units)), a_min=1e-6, a_max=0.9991*0.5)  # assumed 5 mL/s
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
                actual_status=self.dict_waterheater['actual_status'])
              )
            ### update ldc_signal
            self.dict_waterheater.update(read_signal(ldc_signal=self.dict_waterheater['ldc_signal'], 
              new_signal=self.dict_common['ldc_signal'], 
              n_units=n_units))
            ### update ldc_dongle approval for the proposed status and demand
            self.dict_waterheater.update(
              ldc_dongle(flexibility=self.dict_waterheater['flexibility'],
                priority=self.dict_waterheater['priority'], 
                ldc_case=self.case,
                signal=self.dict_waterheater['ldc_signal'], 
                proposed_status=self.dict_waterheater['proposed_status'],
                with_dr=self.dict_waterheater['with_dr'],
                unixtime=self.dict_common['unixtime'],
                hour=self.dict_common['hour'])
              )
            ### update device states, e.g., temp_in, temp_mat, through simulation
            self.dict_waterheater.update(
              enduse_tcl(heat_all=self.dict_waterheater['heating_power_thermal'],
                air_part=self.dict_waterheater['air_part'],
                temp_in=self.dict_waterheater['temp_in'],
                temp_mat=self.dict_waterheater['temp_mat'],
                temp_out=self.dict_common['temp_out'],
                Um=self.dict_waterheater['Um'],
                Ua=self.dict_waterheater['Ua'],
                Cp=self.dict_waterheater['Cp'],
                Ca=self.dict_waterheater['Ca'],
                Cm=self.dict_waterheater['Cm'],
                mass_flow=self.dict_waterheater['mass_flow'],  # kg/s
                step_size=self.dict_common['step_size'],
                unixtime=self.dict_common['unixtime'],
                connected=self.dict_waterheater['connected'])
              )
            ### send data to main
            self.pipe_agg_waterheater1.send(self.dict_waterheater)
            ### save data
            # [dict_save[k].update({self.dict_common['unixtime']:dict(zip(self.dict_waterheater['name'], 
            #   self.dict_waterheater[k]))}) for k in params]
            
            # dict_wh_temp.update({self.dict_common['unixtime']: dict(zip(self.dict_waterheater['name'], self.dict_waterheater['temp_in'].flatten()))})
            
            # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_waterheater['temp_in']),
            #   'min_temp_in': np.min(self.dict_waterheater['temp_in']),
            #   'avg_temp_in': np.mean(self.dict_waterheater['temp_in']),
            #   'std_temp_in': np.std(self.dict_waterheater['temp_in']),
            #   'avg_temp_out': np.mean(self.dict_common['temp_out']),
            #   'above_60': ''.join(((self.dict_waterheater['temp_in']>60)*1).astype(str)),
            #   'mode': ''.join(self.dict_waterheater['mode'].astype(str)),
            #   'actual_status': ''.join(self.dict_waterheater['actual_status'].astype(str)),
            #   'connected': ''.join(self.dict_waterheater['connected'].astype(str)),
            #   'max_temp_in_active': np.max(self.dict_waterheater['temp_in_active']) if self.dict_waterheater['temp_in_active'].shape[0]>0 else np.nan,
            #   'min_temp_in_active': np.min(self.dict_waterheater['temp_in_active']) if self.dict_waterheater['temp_in_active'].shape[0]>0 else np.nan,
            #   'avg_temp_in_active': np.mean(self.dict_waterheater['temp_in_active']) if self.dict_waterheater['temp_in_active'].shape[0]>0 else np.nan,
            #   'std_temp_in_active': np.std(self.dict_waterheater['temp_in_active']) if self.dict_waterheater['temp_in_active'].shape[0]>0 else np.nan,
            #   'max_heating_setpoint': np.max(self.dict_waterheater['heating_setpoint']),
            #   'min_heating_setpoint': np.min(self.dict_waterheater['heating_setpoint']),
            #   'avg_heating_setpoint': np.mean(self.dict_waterheater['heating_setpoint']),
            #   'std_heating_setpoint': np.std(self.dict_waterheater['heating_setpoint']),
            #   'max_flexibility': np.max(self.dict_waterheater['flexibility']),
            #   'min_flexibility': np.min(self.dict_waterheater['flexibility']),
            #   'avg_flexibility': np.mean(self.dict_waterheater['flexibility']),
            #   'std_flexibility': np.std(self.dict_waterheater['flexibility']),
            #   'max_priority': np.max(self.dict_waterheater['priority']),
            #   'min_priority': np.min(self.dict_waterheater['priority']),
            #   'avg_priority': np.mean(self.dict_waterheater['priority']),
            #   'std_priority': np.std(self.dict_waterheater['priority']),
            #   'sum_a_demand': np.sum(self.dict_waterheater['actual_demand'])}})

            # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
            #   save_data(dict_save, case=self.case, folder=self.casefolder, filename='waterheater.h5')
            #   save_data(dict_wh_temp, case=self.case, folder=self.casefolder, filename='wh_temp.h5')
            #   dict_save = {} # dict_save.fromkeys(dict_save, {})
            #   dict_wh_temp = {}
          else:
            # save_data(dict_save, case=self.case, folder=self.casefolder, filename='waterheater.h5')
            # save_data(dict_wh_temp, case=self.case, folder=self.casefolder, filename='wh_temp.h5')
            break
          time.sleep(self.pause) # to give way to other threads
        except Exception as e:
          print(f'Error AGGREGATOR.waterheater:{e}')
        except KeyboardInterrupt:
          break
    ### feedback
    print('Waterheater simulation stopped...')
    self.pipe_agg_waterheater1.close()


  def fridge(self):
    print('Running fridge...')
    load_type = 'fridge'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df

    for k, v in self.dict_fridge.items():
      self.dict_fridge[k] = np.array(v)

    self.dict_fridge['ldc_signal'] = self.dict_fridge['priority'] - 5

    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_fridge['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_fridge['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    dict_save = {}    
    # dict_save = {'connected':{}, 
    #   'temp_in':{}, 
    #   'cooling_setpoint':{},
    #   'flexibility':{}, 
    #   'priority':{},
    #   'actual_demand':{}
    # }
    # params = list(dict_save.keys())

    while True:
      try:
        if self.pipe_agg_fridge1.poll():
          self.dict_common.update(self.pipe_agg_fridge1.recv())
        if self.dict_common['is_alive']:
          ### update device proposed mode, status, priority, and demand
          self.dict_fridge.update(
            device_cooling_compression(mode=self.dict_fridge['mode'],
              temp_in=self.dict_fridge['temp_in'], 
              temp_min=self.dict_fridge['temp_min'], 
              temp_max=self.dict_fridge['temp_max'], 
              cooling_setpoint=self.dict_fridge['cooling_setpoint'], 
              tolerance=self.dict_fridge['tolerance'], 
              cooling_power=self.dict_fridge['cooling_power'],
              cop=self.dict_fridge['cop'], 
              standby_power=self.dict_fridge['standby_power'],
              ventilation_power=self.dict_fridge['ventilation_power'],
              actual_status=self.dict_fridge['actual_status'])
            )

          ### update ldc_signal
          self.dict_fridge.update(read_signal(ldc_signal=self.dict_fridge['ldc_signal'], 
            new_signal=self.dict_common['ldc_signal'], 
            n_units=n_units))
          ### update ldc_dongle approval for the proposed status and demand
          self.dict_fridge.update(
            ldc_dongle(flexibility=self.dict_fridge['flexibility'],
              priority=self.dict_fridge['priority'], 
              ldc_case=self.case,
              signal=self.dict_fridge['ldc_signal'], 
              proposed_status=self.dict_fridge['proposed_status'],
              with_dr=self.dict_fridge['with_dr'],
              unixtime=self.dict_common['unixtime'])
            )
          ### change temperature setpoint
          self.dict_fridge.update(
            adjust_setpoint(actual_status=self.dict_fridge['actual_status'], 
              mode=self.dict_fridge['mode'], 
              cooling_setpoint=self.dict_fridge['cooling_setpoint'], 
              heating_setpoint=self.dict_fridge['heating_setpoint'], 
              upper_limit=self.dict_fridge['temp_max'], 
              lower_limit=self.dict_fridge['temp_min']),
            )
          ### update device states, e.g., temp_in, temp_mat, through simulation
          self.dict_fridge.update(
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
              mass_flow= 1.2041*0.001*0.001, # 1 mL/s
              step_size=self.dict_common['step_size'],
              unixtime=self.dict_common['unixtime'],
              connected=self.dict_fridge['connected'])
            )
          ### send data to main
          self.pipe_agg_fridge1.send(self.dict_fridge)
          ### save data
          # [dict_save[k].update({self.dict_common['unixtime']:dict(zip(self.dict_fridge['name'],
          #               self.dict_fridge[k]))}) for k in params]

          # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_fridge['temp_in']),
          #   'min_temp_in': np.min(self.dict_fridge['temp_in']),
          #   'avg_temp_in': np.mean(self.dict_fridge['temp_in']),
          #   'std_temp_in': np.std(self.dict_fridge['temp_in']),
          #   'avg_temp_out': np.mean(self.dict_fridge['temp_out']),
          #   'max_temp_in_active': np.max(self.dict_fridge['temp_in_active']) if self.dict_fridge['temp_in_active'].shape[0]>0 else np.nan,
          #   'min_temp_in_active': np.min(self.dict_fridge['temp_in_active']) if self.dict_fridge['temp_in_active'].shape[0]>0 else np.nan,
          #   'avg_temp_in_active': np.mean(self.dict_fridge['temp_in_active']) if self.dict_fridge['temp_in_active'].shape[0]>0 else np.nan,
          #   'std_temp_in_active': np.std(self.dict_fridge['temp_in_active']) if self.dict_fridge['temp_in_active'].shape[0]>0 else np.nan,
          #   'max_cooling_setpoint': np.max(self.dict_fridge['cooling_setpoint']),
          #   'min_cooling_setpoint': np.min(self.dict_fridge['cooling_setpoint']),
          #   'avg_cooling_setpoint': np.mean(self.dict_fridge['cooling_setpoint']),
          #   'std_cooling_setpoint': np.std(self.dict_fridge['cooling_setpoint']),
          #   'max_flexibility': np.max(self.dict_fridge['flexibility']),
          #   'min_flexibility': np.min(self.dict_fridge['flexibility']),
          #   'avg_flexibility': np.mean(self.dict_fridge['flexibility']),
          #   'std_flexibility': np.std(self.dict_fridge['flexibility']),
          #   'max_priority': np.max(self.dict_fridge['priority']),
          #   'min_priority': np.min(self.dict_fridge['priority']),
          #   'avg_priority': np.mean(self.dict_fridge['priority']),
          #   'std_priority': np.std(self.dict_fridge['priority']),
          #   'sum_a_demand': np.sum(self.dict_fridge['actual_demand'])}})
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #     save_data(dict_save, case=self.case, folder=self.casefolder, filename='fridge.h5')
          #     dict_save = {} #dict_save.fromkeys(dict_save, {})
        else:
          # save_data(dict_save, case=self.case, folder=self.casefolder, filename='fridge.h5')
          break
        time.sleep(self.pause)  # to give way to other threads
      except Exception as e:
        print(f'Error fridge:{e}')
      except KeyboardInterrupt:
        break
    ### feedback
    print('Fridge simulation stopped...')
    self.pipe_agg_fridge1.close()


  def freezer(self):
    print('Running freezer...')
    load_type = 'freezer'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df

    for k, v in self.dict_freezer.items():
      self.dict_freezer[k] = np.array(v)

    self.dict_freezer['ldc_signal'] = self.dict_freezer['priority'] - 5

    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_freezer['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_freezer['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    dict_save = {}
    while True:
      try:
        if self.pipe_agg_freezer1.poll():
          self.dict_common.update(self.pipe_agg_freezer1.recv())
        if self.dict_common['is_alive']:
          ### update required parameters, e.g.mass flow, unixstart, connected, etc.
          # self.dict_freezer.update({'mass_flow': x[0]})
          ### update device proposed mode, status, priority, and demand
          self.dict_freezer.update(
            device_cooling_compression(mode=self.dict_freezer['mode'],
              temp_in=self.dict_freezer['temp_in'], 
              temp_min=self.dict_freezer['temp_min'], 
              temp_max=self.dict_freezer['temp_max'], 
              cooling_setpoint=self.dict_freezer['cooling_setpoint'], 
              tolerance=self.dict_freezer['tolerance'], 
              cooling_power=self.dict_freezer['cooling_power'],
              cop=self.dict_freezer['cop'],
              standby_power=self.dict_freezer['standby_power'],
              ventilation_power=self.dict_freezer['ventilation_power'],
              actual_status=self.dict_freezer['actual_status'])
            )
          ### update ldc_signal
          self.dict_freezer.update(read_signal(ldc_signal=self.dict_freezer['ldc_signal'], 
            new_signal=self.dict_common['ldc_signal'], 
            n_units=n_units))
          ### update ldc_dongle approval for the proposed status and demand
          self.dict_freezer.update(
            ldc_dongle(flexibility=self.dict_freezer['flexibility'],
              priority=self.dict_freezer['priority'], 
              ldc_case=self.case,
              signal=self.dict_freezer['ldc_signal'], 
              proposed_status=self.dict_freezer['proposed_status'],
              with_dr=self.dict_freezer['with_dr'],
              unixtime=self.dict_common['unixtime'])
            )
          ### change temperature setpoint
          self.dict_freezer.update(
            adjust_setpoint(actual_status=self.dict_freezer['actual_status'], 
              mode=self.dict_freezer['mode'], 
              cooling_setpoint=self.dict_freezer['cooling_setpoint'], 
              heating_setpoint=self.dict_freezer['heating_setpoint'], 
              upper_limit=self.dict_freezer['temp_max'], 
              lower_limit=self.dict_freezer['temp_min']),
            )
          ### update device states, e.g., temp_in, temp_mat, through simulation
          self.dict_freezer.update(
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
              mass_flow= 1.2041*0.001*0.001, # 1 mL/s
              step_size=self.dict_common['step_size'],
              unixtime=self.dict_common['unixtime'],
              connected=self.dict_freezer['connected'])
            )
          ### send data to main
          self.pipe_agg_freezer1.send(self.dict_freezer)
          ### save data
          # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_freezer['temp_in']),
          #     'min_temp_in': np.min(self.dict_freezer['temp_in']),
          #     'avg_temp_in': np.mean(self.dict_freezer['temp_in']),
          #     'std_temp_in': np.std(self.dict_freezer['temp_in']),
          #     'avg_temp_out': np.mean(self.dict_freezer['temp_out']),
          #     'max_temp_in_active': np.max(self.dict_freezer['temp_in_active']) if self.dict_freezer['temp_in_active'].shape[0]>0 else np.nan,
          #     'min_temp_in_active': np.min(self.dict_freezer['temp_in_active']) if self.dict_freezer['temp_in_active'].shape[0]>0 else np.nan,
          #     'avg_temp_in_active': np.mean(self.dict_freezer['temp_in_active']) if self.dict_freezer['temp_in_active'].shape[0]>0 else np.nan,
          #     'std_temp_in_active': np.std(self.dict_freezer['temp_in_active']) if self.dict_freezer['temp_in_active'].shape[0]>0 else np.nan,
          #     'max_cooling_setpoint': np.max(self.dict_freezer['cooling_setpoint']),
          #     'min_cooling_setpoint': np.min(self.dict_freezer['cooling_setpoint']),
          #     'avg_cooling_setpoint': np.mean(self.dict_freezer['cooling_setpoint']),
          #     'std_cooling_setpoint': np.std(self.dict_freezer['cooling_setpoint']),
          #     'max_flexibility': np.max(self.dict_freezer['flexibility']),
          #     'min_flexibility': np.min(self.dict_freezer['flexibility']),
          #     'avg_flexibility': np.mean(self.dict_freezer['flexibility']),
          #     'std_flexibility': np.std(self.dict_freezer['flexibility']),
          #     'max_priority': np.max(self.dict_freezer['priority']),
          #     'min_priority': np.min(self.dict_freezer['priority']),
          #     'avg_priority': np.mean(self.dict_freezer['priority']),
          #     'std_priority': np.std(self.dict_freezer['priority']),
          #     'sum_a_demand': np.sum(self.dict_freezer['actual_demand'])}})
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, 
          #     folder=self.casefolder, filename='freezer.h5')
            # dict_save = {}
        else:
          # save_data(dict_save, case=self.case, 
          #   folder=self.casefolder, filename='freezer.h5')
          break
        time.sleep(self.pause)  # to give way to other threads
      except Exception as e:
        print(f'Error freezer:{e}')
      except KeyboardInterrupt:
        break
    ### feedback
    print('Freezer simulation stopped...')
    self.pipe_agg_freezer1.close()
    

  def clotheswasher(self):
    print('Running clotheswasher...')
    load_type = 'clotheswasher'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df
    for k, v in self.dict_clotheswasher.items():
      self.dict_clotheswasher[k] = np.array(v)

    self.dict_clotheswasher['ldc_signal'] = self.dict_clotheswasher['priority'] - 5

    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_clotheswasher['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_clotheswasher['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    
    ### initialize dynamic variables 
    self.dict_clotheswasher['unixstart'] = np.zeros(self.dict_devices['clotheswasher']['n_units'])
    self.dict_clotheswasher['unixend'] = np.ones(self.dict_devices['clotheswasher']['n_units'])
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
        if self.pipe_agg_clotheswasher1.poll():
          self.dict_common.update(self.pipe_agg_clotheswasher1.recv())
        if self.dict_common['is_alive']:
          ### update unixstart and unixend
          self.dict_clotheswasher.update(
            make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_clotheswasher['schedule']].values,
              load_type_id=6, # code for clotheswashers
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
              proposed_demand=np.array([dict_data[k][int((x*y)%x)] for k, x, y in zip(self.dict_clotheswasher['profile'], self.dict_clotheswasher['len_profile'], self.dict_clotheswasher['progress'])]).flatten(),
              actual_demand=self.dict_clotheswasher['proposed_demand'])
            )
          ### update ldc_signal
          self.dict_clotheswasher.update(read_signal(ldc_signal=self.dict_clotheswasher['ldc_signal'], 
            new_signal=self.dict_common['ldc_signal'], 
            n_units=n_units))
          ### update ldc_dongle approval for the proposed status and demand
          d = ldc_dongle(flexibility=self.dict_clotheswasher['flexibility'],
                priority=self.dict_clotheswasher['priority'], 
                ldc_case=self.case,
                signal=self.dict_clotheswasher['ldc_signal'], 
                proposed_status=self.dict_clotheswasher['proposed_status'],
                with_dr=self.dict_clotheswasher['with_dr'],
                unixtime=self.dict_common['unixtime'])
          self.dict_clotheswasher['actual_status'] = ((d['actual_status']==1) | 
                ((self.dict_clotheswasher['actual_status']==1)&(self.dict_clotheswasher['progress']<=1)))*1
          self.dict_clotheswasher['priority'] = d['priority']
          ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
          self.dict_clotheswasher.update(
            enduse_ntcl(len_profile=self.dict_clotheswasher['len_profile'],
              progress=self.dict_clotheswasher['progress'],
              step_size=self.dict_common['step_size'],
              actual_status=self.dict_clotheswasher['actual_status'],
              unixtime=self.dict_common['unixtime'],
              connected=self.dict_clotheswasher['connected'])
            )
          ### send data to main
          self.pipe_agg_clotheswasher1.send(self.dict_clotheswasher)
          ### save data
          # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_clotheswasher['progress']),
          #   'min_progress': np.min(self.dict_clotheswasher['progress']),
          #   'avg_progress': np.mean(self.dict_clotheswasher['progress']),
          #   'std_progress': np.std(self.dict_clotheswasher['progress']),
          #   'max_flexibility': np.max(self.dict_clotheswasher['flexibility']),
          #   'min_flexibility': np.min(self.dict_clotheswasher['flexibility']),
          #   'avg_flexibility': np.mean(self.dict_clotheswasher['flexibility']),
          #   'std_flexibility': np.std(self.dict_clotheswasher['flexibility']),
          #   'max_priority': np.max(self.dict_clotheswasher['priority']),
          #   'min_priority': np.min(self.dict_clotheswasher['priority']),
          #   'avg_priority': np.mean(self.dict_clotheswasher['priority']),
          #   'std_priority': np.std(self.dict_clotheswasher['priority']),
          #   'sum_a_demand': np.sum(self.dict_clotheswasher['actual_demand'])}})
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, 
          #     folder=self.casefolder, filename='clotheswasher.h5')
          #   dict_save = {}
        else:
          # save_data(dict_save, case=self.case, 
          #   folder=self.casefolder, filename='clotheswasher.h5')
          break
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error clotheswasher run:{e}')
      except KeyboardInterrupt:
        break  
    ### feedback
    print('Clotheswasher simulation stopped...')
    self.pipe_agg_clotheswasher1.close()


  # def clothesdryer(self):
  #     print('Running clothesdryer...')    
  #     '''
  #     g = (25 + (19*v)) * A (x_s - x)/3600  # v = air velocity on water surface, 
  #     A = exposed water surface area, x_s = kg_h20/ kg_dryair of sturated air in same temp, x = kg_h20/kg_dry air for given air temp
  #     g =  evaporation rate [kg/s]
  #     '''


  def clothesdryer(self):
    print('Running clothesdryer...')
    load_type = 'clothesdryer'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df
    for k, v in self.dict_clothesdryer.items():
      self.dict_clothesdryer[k] = np.array(v)
    
    self.dict_clothesdryer['ldc_signal'] = self.dict_clothesdryer['priority'] - 5

    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_clothesdryer['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_clothesdryer['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    ### initialize dynamic variables 
    self.dict_clothesdryer['unixstart'] = np.zeros(self.dict_devices['clothesdryer']['n_units'])
    self.dict_clothesdryer['unixend'] = np.ones(self.dict_devices['clothesdryer']['n_units'])
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
        if self.pipe_agg_clothesdryer1.poll():
          self.dict_common.update(self.pipe_agg_clothesdryer1.recv())
        if self.dict_common['is_alive']:
          ### update unixstart and unixend
          self.dict_clothesdryer.update(
            make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_clothesdryer['schedule']].values,
              load_type_id=4, # code for clothesdryer
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
              proposed_demand=np.array([dict_data[k][int((x*y)%x)] for k, x, y in zip(self.dict_clothesdryer['profile'], self.dict_clothesdryer['len_profile'], self.dict_clothesdryer['progress'])]).flatten(),
              actual_demand=self.dict_clothesdryer['proposed_demand'])
            )
          ### update ldc_signal
          self.dict_clothesdryer.update(read_signal(ldc_signal=self.dict_clothesdryer['ldc_signal'], 
            new_signal=self.dict_common['ldc_signal'], 
            n_units=n_units))
          ### update ldc_dongle approval for the proposed status and demand
          d = ldc_dongle(flexibility=self.dict_clothesdryer['flexibility'],
              priority=self.dict_clothesdryer['priority'], 
              ldc_case=self.case,
              signal=self.dict_clothesdryer['ldc_signal'], 
              proposed_status=self.dict_clothesdryer['proposed_status'],
              with_dr=self.dict_clothesdryer['with_dr'],
              unixtime=self.dict_common['unixtime'])
          self.dict_clothesdryer['actual_status'] = ((d['actual_status']==1) | 
              ((self.dict_clothesdryer['actual_status']==1)&(self.dict_clothesdryer['progress']<=1)))*1
          self.dict_clothesdryer['priority'] = d['priority']
          ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
          self.dict_clothesdryer.update(
            enduse_ntcl(len_profile=self.dict_clothesdryer['len_profile'],
              progress=self.dict_clothesdryer['progress'],
              step_size=self.dict_common['step_size'],
              actual_status=self.dict_clothesdryer['actual_status'],
              unixtime=self.dict_common['unixtime'],
              connected=self.dict_clothesdryer['connected'])
            )
          ### send data to main
          self.pipe_agg_clothesdryer1.send(self.dict_clothesdryer)
          ### save data
          # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_clothesdryer['progress']),
          #   'min_progress': np.min(self.dict_clothesdryer['progress']),
          #   'avg_progress': np.mean(self.dict_clothesdryer['progress']),
          #   'std_progress': np.std(self.dict_clothesdryer['progress']),
          #   'max_flexibility': np.max(self.dict_clothesdryer['flexibility']),
          #   'min_flexibility': np.min(self.dict_clothesdryer['flexibility']),
          #   'avg_flexibility': np.mean(self.dict_clothesdryer['flexibility']),
          #   'std_flexibility': np.std(self.dict_clothesdryer['flexibility']),
          #   'max_priority': np.max(self.dict_clothesdryer['priority']),
          #   'min_priority': np.min(self.dict_clothesdryer['priority']),
          #   'avg_priority': np.mean(self.dict_clothesdryer['priority']),
          #   'std_priority': np.std(self.dict_clothesdryer['priority']),
          #   'sum_a_demand': np.sum(self.dict_clothesdryer['actual_demand'])}})
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, 
          #     folder=self.casefolder, filename='clothesdryer.h5')
          #   dict_save = {}
        else:
          # save_data(dict_save, case=self.case, 
          #   folder=self.casefolder, filename='clothesdryer.h5')
          break
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error clothesdryer run:{e}')
      except KeyboardInterrupt:
        break
    ### feedback
    print('clothesdryer simulation stopped...')
    self.pipe_agg_clothesdryer1.close()
    


  def dishwasher(self):
    print('Running dishwasher...')
    load_type = 'dishwasher'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df
    for k, v in self.dict_dishwasher.items():
      self.dict_dishwasher[k] = np.array(v)
    
    self.dict_dishwasher['ldc_signal'] = self.dict_dishwasher['priority']- 5

    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_dishwasher['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_dishwasher['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    ### initialize dynamic variables 
    self.dict_dishwasher['unixstart'] = np.zeros(self.dict_devices['dishwasher']['n_units'])
    self.dict_dishwasher['unixend'] = np.ones(self.dict_devices['dishwasher']['n_units'])
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
        if self.pipe_agg_dishwasher1.poll():
          self.dict_common.update(self.pipe_agg_dishwasher1.recv())
        if self.dict_common['is_alive']:
          self.dict_dishwasher.update(self.dict_common)
          ### update unixstart and unixend
          self.dict_dishwasher.update(
            make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_dishwasher['schedule']].values,
              load_type_id=4, # code for dishwasher
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
              actual_demand=self.dict_dishwasher['proposed_demand'])  # previous proposed_demand
            )
          ### update ldc_signal
          self.dict_dishwasher.update(read_signal(ldc_signal=self.dict_dishwasher['ldc_signal'], 
            new_signal=self.dict_common['ldc_signal'], 
            n_units=n_units))
          ### update ldc_dongle approval for the proposed status and demand
          d = ldc_dongle(flexibility=self.dict_dishwasher['flexibility'],
              priority=self.dict_dishwasher['priority'], 
              ldc_case=self.case,
              signal=self.dict_dishwasher['ldc_signal'], 
              proposed_status=self.dict_dishwasher['proposed_status'],
              with_dr=self.dict_dishwasher['with_dr'],
              unixtime=self.dict_common['unixtime'])
          self.dict_dishwasher['actual_status'] = ((d['actual_status']==1) | 
              ((self.dict_dishwasher['actual_status']==1)&(self.dict_dishwasher['progress']<=1)))*1
          self.dict_dishwasher['priority'] = d['priority']
          ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
          self.dict_dishwasher.update(
            enduse_ntcl(len_profile=self.dict_dishwasher['len_profile'],
              progress=self.dict_dishwasher['progress'],
              step_size=self.dict_common['step_size'],
              actual_status=self.dict_dishwasher['actual_status'],
              unixtime=self.dict_common['unixtime'],
              connected=self.dict_dishwasher['connected'])
            )
          ### send data to main
          self.pipe_agg_dishwasher1.send(self.dict_dishwasher)
          ### save data
          # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_dishwasher['progress']),
          #   'min_progress': np.min(self.dict_dishwasher['progress']),
          #   'avg_progress': np.mean(self.dict_dishwasher['progress']),
          #   'std_progress': np.std(self.dict_dishwasher['progress']),
          #   'max_flexibility': np.max(self.dict_dishwasher['flexibility']),
          #   'min_flexibility': np.min(self.dict_dishwasher['flexibility']),
          #   'avg_flexibility': np.mean(self.dict_dishwasher['flexibility']),
          #   'std_flexibility': np.std(self.dict_dishwasher['flexibility']),
          #   'max_priority': np.max(self.dict_dishwasher['priority']),
          #   'min_priority': np.min(self.dict_dishwasher['priority']),
          #   'avg_priority': np.mean(self.dict_dishwasher['priority']),
          #   'std_priority': np.std(self.dict_dishwasher['priority']),
          #   'sum_a_demand': np.sum(self.dict_dishwasher['actual_demand'])}})
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, 
          #     folder=self.casefolder, filename='dishwasher.h5')
          #   dict_save = {}
        else:
          # save_data(dict_save, case=self.case, 
          #   folder=self.casefolder, filename='dishwasher.h5')
          break
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error dishwasher run:{e}')
      except KeyboardInterrupt:
        break
    ### feedback
    print('Dishwasher simulation stopped...')
    self.pipe_agg_dishwasher1.close()
    


  def ev(self):
    print('Running electric vehicle model...')
    load_type = 'ev'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df
    for k, v in self.dict_ev.items():
      self.dict_ev[k] = np.array(v)
    self.dict_ev['ldc_signal'] = self.dict_ev['priority'] - 5
    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_ev['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_ev['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    ### initialize dynamic variables 
    self.dict_ev['unixstart'] = np.zeros(self.dict_devices['ev']['n_units'])
    self.dict_ev['unixend'] = np.ones(self.dict_devices['ev']['n_units'])
    self.dict_ev['progress'] = np.divide(self.dict_ev['soc'], self.dict_ev['target_soc'])
    self.dict_ev['mode'] = np.zeros(self.dict_devices['ev']['n_units'])
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
        if self.pipe_agg_ev1.poll():
          self.dict_common.update(self.pipe_agg_ev1.recv())
        if self.dict_common['is_alive']:
          ### update unixstart and unixend
          self.dict_ev.update(
            make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_ev['schedule']].values,
              load_type_id=6, # code for clotheswashers
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
              actual_demand=self.dict_ev['proposed_demand'])

            # device_charger_ev(unixtime=self.dict_ev['unixtime'], 
            #   unixstart=self.dict_ev['unixstart'],
            #   unixend=self.dict_ev['unixend'],
            #   soc=self.dict_ev['soc'],
            #   charging_power=self.dict_ev['charging_power'],
            #   target_soc=self.dict_ev['target_soc'],
            #   capacity=self.dict_ev['capacity'],
            #   connected=self.dict_ev['connected'],
            #   progress=self.dict_ev['progress'],
            #   actual_status=self.dict_ev['actual_status'],
            #   proposed_demand=np.diag(df.loc[self.dict_ev['soc'].round(3), self.dict_ev['profile']].interpolate()),
            #   actual_demand=self.dict_ev['proposed_demand'])
            )
          ### update ldc_signal
          self.dict_ev.update(read_signal(ldc_signal=self.dict_ev['ldc_signal'], 
            new_signal=self.dict_common['ldc_signal'], 
            n_units=n_units))
          ### update ldc_dongle approval for the proposed status and demand
          d = ldc_dongle(flexibility=self.dict_ev['flexibility'],
              priority=self.dict_ev['priority'], 
              ldc_case=self.case,
              signal=self.dict_ev['ldc_signal'], 
              proposed_status=self.dict_ev['proposed_status'],
              with_dr=self.dict_ev['with_dr'],
              unixtime=self.dict_common['unixtime'])
          self.dict_ev['actual_status'] = ((d['actual_status']==1) | 
              ((self.dict_ev['actual_status']==1)&(self.dict_ev['progress']<=1)))*1
          self.dict_ev['priority'] = d['priority']
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
          self.pipe_agg_ev1.send(self.dict_ev)

          # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_ev['soc']),
          #   'min_soc': np.min(self.dict_ev['soc']),
          #   'avg_soc': np.mean(self.dict_ev['soc']),
          #   'std_soc': np.std(self.dict_ev['soc']),
          #   'max_target_soc': np.max(self.dict_ev['target_soc']),
          #   'min_target_soc': np.min(self.dict_ev['target_soc']),
          #   'avg_target_soc': np.mean(self.dict_ev['target_soc']),
          #   'std_target_soc': np.std(self.dict_ev['target_soc']),
          #   'max_flexibility': np.max(self.dict_ev['flexibility']),
          #   'min_flexibility': np.min(self.dict_ev['flexibility']),
          #   'avg_flexibility': np.mean(self.dict_ev['flexibility']),
          #   'std_flexibility': np.std(self.dict_ev['flexibility']),
          #   'max_priority': np.max(self.dict_ev['priority']),
          #   'min_priority': np.min(self.dict_ev['priority']),
          #   'avg_priority': np.mean(self.dict_ev['priority']),
          #   'std_priority': np.std(self.dict_ev['priority']),
          #   'sum_a_demand': np.sum(self.dict_ev['actual_demand'])}})
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, 
          #     folder=self.casefolder, filename='ev.h5')
          #   dict_save = {}
        else:
          # save_data(dict_save, case=self.case, 
          #   folder=self.casefolder, filename='ev.h5')
          break
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error ev run:{e}')
      except KeyboardInterrupt:
        break
    ### feedback
    print('EV simulation stopped...')
    self.pipe_agg_ev1.close()
    


  def storage(self):
    print('Running battery storage model...')
    load_type = 'storage'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df
    for k, v in self.dict_storage.items():
      self.dict_storage[k] = np.array(v)
    self.dict_storage['ldc_signal'] = self.dict_storage['priority'] - 5
    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_storage['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_storage['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    ### initialize dynamic variables 
    self.dict_storage['unixstart'] = np.zeros(self.dict_devices['storage']['n_units'])
    self.dict_storage['unixend'] = np.ones(self.dict_devices['storage']['n_units'])
    self.dict_storage['progress'] = np.random.rand(1, self.dict_devices['storage']['n_units'])

    dict_save = {}
    while True:
      try:
        if self.pipe_agg_storage1.poll():
          self.dict_common.update(self.pipe_agg_storage1.recv())
        if self.dict_common['is_alive']:
          self.dict_storage.update(self.dict_common)
          ### update unixstart and unixend
          self.dict_storage.update(
            make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_storage['schedule']].values,
              load_type_id=6, # code for clotheswashers
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
              actual_demand=self.dict_storage['proposed_demand'])

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
            #   proposed_demand=self.dict_storage['charging_power'],
            #   actual_demand=self.dict_storage['proposed_demand'])
            )
          ### update ldc_signal
          self.dict_storage.update(read_signal(ldc_signal=self.dict_storage['ldc_signal'], 
            new_signal=self.dict_common['ldc_signal'], 
            n_units=n_units))
          ### update ldc_dongle approval for the proposed status and demand
          d = ldc_dongle(flexibility=self.dict_storage['flexibility'],
              priority=self.dict_storage['priority'], 
              ldc_case=self.case,
              signal=self.dict_storage['ldc_signal'], 
              proposed_status=self.dict_storage['proposed_status'],
              with_dr=self.dict_storage['with_dr'],
              unixtime=self.dict_common['unixtime'])
          self.dict_storage['actual_status'] = ((d['actual_status']==1) | 
              ((self.dict_storage['actual_status']==1)&(self.dict_storage['progress']<=1)))*1
          self.dict_storage['priority'] = d['priority']
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
          self.pipe_agg_storage1.send(self.dict_storage)

          # dict_save.update({self.dict_common['unixtime']:{'max_temp_in': np.max(self.dict_storage['soc']),
          #   'min_soc': np.min(self.dict_storage['soc']),
          #   'avg_soc': np.mean(self.dict_storage['soc']),
          #   'std_soc': np.std(self.dict_storage['soc']),
          #   'max_target_soc': np.max(self.dict_storage['target_soc']),
          #   'min_target_soc': np.min(self.dict_storage['target_soc']),
          #   'avg_target_soc': np.mean(self.dict_storage['target_soc']),
          #   'std_target_soc': np.std(self.dict_storage['target_soc']),
          #   'max_flexibility': np.max(self.dict_storage['flexibility']),
          #   'min_flexibility': np.min(self.dict_storage['flexibility']),
          #   'avg_flexibility': np.mean(self.dict_storage['flexibility']),
          #   'std_flexibility': np.std(self.dict_storage['flexibility']),
          #   'max_priority': np.max(self.dict_storage['priority']),
          #   'min_priority': np.min(self.dict_storage['priority']),
          #   'avg_priority': np.mean(self.dict_storage['priority']),
          #   'std_priority': np.std(self.dict_storage['priority']),
          #   'sum_a_demand': np.sum(self.dict_storage['actual_demand'])}})
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, 
          #     folder=self.casefolder, filename='storage.h5')
          #   dict_save = {}
        else:
          # save_data(dict_save, case=self.case, 
          #   folder=self.casefolder, filename='storage.h5')
          break
        time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.storage:{}".format(e))
      except KeyboardInterrupt:
        break 
    print("Storage simulation stopped...")
    self.pipe_agg_storage1.close()
    

  def solar(self):
    print('Running solar panel model...')
    load_type = 'solar'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df
    for k, v in self.dict_solar.items():
      self.dict_solar[k] = np.array(v)
    self.dict_solar['ldc_signal'] = self.dict_solar['priority'] - 5
    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_solar['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_solar['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    
    ### initialize dynamic variables 
    self.dict_solar['unixstart'] = np.zeros(self.dict_devices['solar']['n_units'])
    self.dict_solar['unixend'] = np.ones(self.dict_devices['solar']['n_units'])
    self.dict_solar['mode'] = np.ones(self.dict_devices['solar']['n_units'])

    dict_save = {}
    while True:
      try:
        if self.pipe_agg_solar1.poll():
          self.dict_common.update(self.pipe_agg_solar1.recv())
        if self.dict_common['is_alive']:
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
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, 
          #     folder=self.casefolder, filename='solar.h5')
          #   dict_save = {}
        else:
          # save_data(dict_save, case=self.case, 
          #   folder=self.casefolder, filename='solar.h5')
          break
        time.sleep(self.pause)
      except Exception as e:
        print(f'Error solar:{e}')
      except KeyboardInterrupt:
        break
    print('Solar simulation stopped...')
    self.pipe_agg_solar1.close()
    


  def wind(self):
    print('Running wind turbine model...')
    load_type = 'wind'
    n_units = self.dict_devices[load_type]['n_units']
    n_ldc = self.dict_devices[load_type]['n_ldc']
    idx = self.idx
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
      if 'with_dr' in df.columns:
        if self.case in ['no_ldc', 'ripple_fixed', 'ripple_peak']:
          df['with_dr'] = False
        else:
          idxs = np.arange(n_units)
          if self.case=='per_device': 
            np.random.shuffle(idxs)
          df.loc[idxs[0:n_ldc], 'with_dr'] = True
          df.loc[idxs[n_ldc:], 'with_dr'] = False
      eval(f'self.dict_{load_type}').update(df.to_dict(orient='list'))
      del df
    for k, v in self.dict_wind.items():
      self.dict_wind[k] = np.array(v)
    self.dict_wind['ldc_signal'] = self.dict_wind['priority'] - 5
    if self.simulation:
      n_house = self.dict_devices['house']['n_units']
      self.dict_wind['house'] = self.dict_house['name'][np.arange(n_units)%n_house]
      self.dict_wind['schedule'] = self.dict_house['schedule'][np.arange(n_units)%n_house]    
    
    ### initialize dynamic variables 
    self.dict_wind['unixstart'] = np.zeros(self.dict_devices['wind']['n_units'])
    self.dict_wind['unixend'] = np.ones(self.dict_devices['wind']['n_units'])
    
    while True:
      try:
        if self.pipe_agg_wind1.poll():
          self.dict_common.update(self.pipe_agg_wind1.recv())
        if self.dict_common['is_alive']:
          ### send data to main
          self.pipe_agg_wind1.send(self.dict_wind)
          ### save data
          # if (len(dict_save.keys())>=self.save_interval) and (self.case!=None):
          #   save_data(dict_save, case=self.case, 
          #     folder=self.casefolder, filename='wind.h5')
          #   dict_save = {}
        else:
          # save_data(dict_save, case=self.case, 
          #   folder=self.casefolder, filename='wind.h5')
          break
        time.sleep(self.pause)
      except Exception as e:
        print("Error AGGREGATOR.wind:{}".format(e))
      except KeyboardInterrupt:
        break
    print("Wind power simulation stopped...")
    self.pipe_agg_wind1.close()
    


  def valve(self):
    # opening and closing of water valves
    print('Emulating valves...')
    n_valve = 1
    for i in range(2): # 2 valves: 0 for hot, 1 fo cold
      self.dict_valve[f'valve{i}'] = {
        'unixstart': np.zeros(n_valve),
        'unixend': np.ones(n_valve),
        'connected': np.zeros(n_valve),
        'actual_status': np.zeros(n_valve)
      }

    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select('house', where='index>={} and index<{}'.format(self.idx, self.idx+n_valve))    
    self.dict_valve['schedule'] = df['schedule'].values
    del df
    
    while self.dict_common['is_alive']:
      try:
        self.dict_common.update(self.pipe_agg_valve1.recv())
        ### update unixstart and unixend
        for i in range(2):
          self.dict_valve[f'valve{i}'] = make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_valve['schedule']].values,  # float, code.duration
              load_type_id= 13+i, # 13 is the code for hot water valve, 14 is for the cold valve
              unixstart=self.dict_valve[f'valve{i}']['unixstart'],
              unixend=self.dict_valve[f'valve{i}']['unixend'],
              schedule_skew=np.random.randint(0,900,1)
              )

          ## update if connected
          self.dict_valve[f'valve{i}'] = is_connected(unixtime=self.dict_common['unixtime'],
              unixstart=self.dict_valve[f'valve{i}']['unixstart'],
              unixend=self.dict_valve[f'valve{i}']['unixend'])
            
          self.dict_valve[f'valve{i}'] = {
            'actual_status': self.dict_valve[f'valve{i}']['connected']
          }

        self.pipe_agg_valve1.send(self.dict_valve)

        time.sleep(self.pause)
      except Exception as e:
        print(f'Error valve loop:{e}')
      except KeyboardInterrupt:
        break        
    return   # mass_flow of water heater

  def window(self):
    ### this method affects the opening and closing of windows, impacts the air change per hour
    print('Emulating window opening / closing...')
    n_window = 1
    for i in range(5):
      self.dict_window[f'window{i}'] = {
        'unixstart': np.zeros(n_window),
        'unixend': np.ones(n_window),
        'connected': np.zeros(n_window),
        'actual_status': np.zeros(n_window)
      }

    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select('house', where='index>={} and index<{}'.format(self.idx, self.idx+n_window))    
    self.dict_window['schedule'] = df['schedule'].values
    del df
    

    while self.dict_common['is_alive']:
      try:
        self.dict_common.update(self.pipe_agg_valve1.recv())
        ### update unixstart and unixend
        for i in range(5):
          self.dict_window[f'window{i}'] = make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_window['schedule']].values,  # float, code.duration
              load_type_id= 18+i, # codes for windows are 18..22
              unixstart=self.dict_window[f'window{i}']['unixstart'],
              unixend=self.dict_window[f'window{i}']['unixend'],
              schedule_skew=np.random.randint(0,900,1)
              )

          ## update if connected
          self.dict_window[f'window{i}'] = is_connected(unixtime=self.dict_common['unixtime'],
              unixstart=self.dict_window[f'window{i}']['unixstart'],
              unixend=self.dict_window[f'window{i}']['unixend'])
            
          self.dict_window[f'window{i}'] = {
            'actual_status': self.dict_window[f'window{i}']['connected']
          }

        self.pipe_agg_window1.send(self.dict_window)
        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print(f'Error window:{e}')
    
    ### feedback termination
    print(f'window simulation stopped...')
    

  def door(self):
    ### this method affects the opening and closing of doors, impacts the air change per hour
    print('Emulating door opening / closing...')
    n_door = 1
    for i in range(5):
      self.dict_door[f'door{i}'] = {
        'unixstart': np.zeros(n_door),
        'unixend': np.ones(n_door),
        'connected': np.zeros(n_door),
        'actual_status': np.zeros(n_door)
      }

    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
      df = store.select('house', where='index>={} and index<{}'.format(self.idx, self.idx+n_door))    
    self.dict_door['schedule'] = df['schedule'].values
    del df
    

    while self.dict_common['is_alive']:
      try:
        self.dict_common.update(self.pipe_agg_valve1.recv())
        ### update unixstart and unixend
        for i in range(5):
          self.dict_door[f'door{i}'] = make_schedule(unixtime=self.dict_common['unixtime'],
              current_task=self.dict_common['current_task'][self.dict_door['schedule']].values,  # float, code.duration
              load_type_id= 18+i, # codes for doors are 18..22
              unixstart=self.dict_door[f'door{i}']['unixstart'],
              unixend=self.dict_door[f'door{i}']['unixend'],
              schedule_skew=np.random.randint(0,900,1)
              )

          ## update if connected
          self.dict_door[f'door{i}'] = is_connected(unixtime=self.dict_common['unixtime'],
              unixstart=self.dict_door[f'door{i}']['unixstart'],
              unixend=self.dict_door[f'door{i}']['unixend'])
            
          self.dict_door[f'door{i}'] = {
            'actual_status': self.dict_door[f'door{i}']['connected']
          }

        self.pipe_agg_door1.send(self.dict_door)
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
      
    while self.dict_common['is_alive']:
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
      while self.dict_common['is_alive']:
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
      
      unixtime = self.dict_common['unixtime']
      # put in closed status initially
      setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
      GPIO.output([15, 32, 36, 38, 40], [0, 0, 0, 0, 0])
      
      while self.dict_common['is_alive']:
        try:
          if self.dict_heatpump and self.device_ip==111:
            new_status = int(self.dict_heatpump['actual_status'][0])
          elif self.dict_waterheater and self.device_ip==112:
            new_status = int(self.dict_waterheater['actual_status'][0])
          elif self.dict_heater and self.device_ip==103:
            new_status = int(self.dict_heater['actual_status'][0])
          elif self.dict_fridge and self.device_ip==109:
            new_status = int(self.dict_fridge['actual_status'][0])
          elif self.dict_freezer and self.device_ip==110:
            new_status = int(self.dict_freezer['actual_status'][0])
          elif self.dict_clotheswasher and self.device_ip==106:
            new_status = int(self.dict_clotheswasher['actual_status'][0])
          elif self.dict_clothesdryer and self.device_ip==105:
            new_status = int(self.dict_clothesdryer['actual_status'][0])
          elif self.dict_dishwasher and self.device_ip==104:
            new_status = int(self.dict_dishwasher['actual_status'][0])
          elif self.dict_ev and self.device_ip==108:
            new_status = int(self.dict_ev['actual_status'][0])
          elif self.dict_storage and self.device_ip==107:
            new_status = int(self.dict_storage['actual_status'][0])
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
    while self.dict_common['is_alive']:
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
    while  self.dict_common['is_alive']:
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
    while self.dict_common['is_alive']:
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