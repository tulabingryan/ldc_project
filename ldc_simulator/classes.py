'''
./classes.py 
Author: Ryan Tulabing
Project: Local Demand Control
Institution: University of Auckland
Year: 2017 - 2021
Project: Localized Demand Control for Local Grids with Limited Resources
'''

from models import *



class Base():
    '''
    Base class for all devices.
    '''
    def __init__(self):
        self.dict_constant_states = {}
        self.dict_variable_states = {}
        self.dict_global_states = {}
        self.load_class = 'generic'
        self.load_type = 'generic'
        self.dict_house = {}
        self.idx = 0
        

        self.list_variable_states = [
            'proposed_status', 'actual_status',
            'proposed_demand', 'actual_demand',
            'mode', 'flexibility', 'progress',
            'connected', 'priority', 'ldc_signal',
            'temp_in', 'temp_out', 'humidity_in',
            'humidity_out'
        ]

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


    def add_device(self, dict_devices, idx, distribution, dict_global_states):
        self.n_house = dict_devices['house']['n_units']
        self.n_units = dict_devices[self.load_type]['n_units']
        self.n_ldc = dict_devices[self.load_type]['n_ldc']
        # n_b2g = dict_devices[self.load_type]['n_b2g']
        self.dict_global_states = dict_global_states

        print(f'Creating {self.load_type} {self.n_units} units...')
        k = 'house' if self.load_type=='baseload' else self.load_type
        
        with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
            df = store.select(k, where='index>={} and index<{}'.format(idx, idx+self.n_units))
            if 'with_dr' in df.columns:
                idxs = df.index
                if distribution=='per_device':
                    df['with_dr'] = 0
                    selection = np.random.choice(idxs, self.n_ldc, replace=False)
                    df.loc[selection, 'with_dr'] = 1
                else:
                    df.loc[idxs[0:n_ldc], 'with_dr'] = 1
                    df.loc[idxs[n_ldc:], 'with_dr'] = 0
            
            
            
        #     ### assign b2g
        #     df['b2g'] = 0
        #     idxs = df.index
        #     if distribution=='per_device':
        #         df['b2g'] = 0
        #         selection = np.random.choice(idxs, n_b2g, replace=False)
        #         df.loc[selection, 'b2g'] = 1
        #     else:
        #         df.loc[idxs[0:n_b2g], 'b2g'] = 1
        #         df.loc[idxs[n_b2g:], 'b2g'] = 0

        self.dict_constant_states = df.to_dict(orient='list')
        


        # for k, v in dict_out.items():
        #     dict_out[k] = np.array(v)
        
        # dict_out['unixstart'] = np.random.normal(common['unixtime'] - (common['hour']*3600), 0.1, n_units)
        # dict_out['unixend'] = np.random.normal(common['unixtime'] - (common['hour']*3600) + (3600*24), 0.1, n_units)
        # dict_out['alpha'] = np.exp(np.ones(n_units)/60)
        # dict_out['actual_demand'] = np.zeros(n_units)
        

    def step(self):
        pass

    def autorun(self):
        pass

    def __del__(self):
        pass





class ThermostatControlledLoad(Base):
    '''
    Generic class for all thermostat-controlled loads.
    '''
    def __init__(self):
        super(ThermostatControlledLoad, self).__init__()
        Base.__init__(self)
        self.device_class = 'tcl'
        self.dict_entry = {}

    def step(self):
        try:
            # self.dict_global_states.update(self.pipe_agg_waterheater1.recv())
            # if self.dict_global_states['is_alive']==False: 
            #     raise KeyboardInterrupt
            
            # ### update common variables
            # update_from_common(self.dict_variable_states, self.dict_global_states)
            
            ### update weather
            self.dict_variable_states['temp_out'] = np.add(np.random.normal(0,0.01, self.n_units), self.dict_global_states['temp_out'])
            
            # ### update status of zone entrance/exit
            # self.dict_entry.update(update_device(n_device=1, 
            #     device_type='valve', 
            #     dict_startcode=self.dict_startcode, 
            #     dict_self=self.dict_entry, 
            #     dict_parent=self.dict_variable_states, 
            #     dict_common=self.dict_global_states))

            
            ### update device proposed mode, status, priority, and demand
            device_tcl(self.dict_variable_states, self.dict_global_states, inverter=False)

            ### update ldc_dongle approval for the proposed status and demand
            ldc_dongle(self.dict_variable_states, self.dict_global_states)

            # ### send data to main
            # self.pipe_agg_waterheater1.send(self.dict_variable_states)
            
            ### update mass_flow, water density = 999.1 kg/m^3 (or 0.999 kg/liter) at 15 degC 101.325kPa (sea level)
            # self.dict_variable_states['mass_flow'] = np.multiply(self.dict_entry['valve0']['actual_status'], np.clip(np.random.normal(999.1*0.001*0.1, 0.01, self.n_units), a_min=0.01, a_max=0.25))  # assumed 0.1 L/s
            self.dict_variable_states['mass_flow'] = np.add(self.dict_variable_states['mass_flow'], np.random.choice([0, 0.01], n_units, p=[0.9, 0.1]))
            
            ### update device states, e.g., temp_in, temp_mat, through simulation
            enduse_tcl(self.dict_variable_states)
                


            # ### get actual readings
            # if self.simulation==0:
            #     response = MULTICAST.send(dict_msg={"pcsensor":"temp_in"}, ip=ip, port=port, timeout=timeout, hops=1)
            #     if response:
            #         self.dict_variable_states['temp_in'] = response[ip]                                            
            #     ### execute status
            #     execute_state(int(self.dict_variable_states['actual_status']), device_id=self.device_ip, report=True)
            #     time.sleep(1)

            
                                    
            # ### save data
            # if self.simulation and self.save_history:
            #     ### for waterheaters, both summary and individual states are recorded to check the legal compliance
            #     if self.summary:
            #         dict_save.update(prepare_summary(states=self.dict_variable_states, common=self.dict_global_states))
            #     else:
            #         dict_save.update(prepare_data(states=self.dict_variable_states, common=self.dict_global_states))

            #     if (self.dict_global_states['unixtime']-self.start_unixtime)>=self.save_interval and (self.case!=None):
            #         dict_save = save_data(dict_save, case=self.case,  folder=self.casefolder, filename='waterheater.h5', summary=self.summary)
            #         self.start_unixtime = self.dict_global_states['unixtime']

            time.sleep(self.pause) # to give way to other threads
        except Exception as e:
            print(f'Error AGGREGATOR.waterheater:{e}')
        except KeyboardInterrupt:
            # if self.simulation==1 and self.save_history: 
            #     save_data(dict_save, case=self.case,  folder=self.casefolder, filename='waterheater.h5', summary=self.summary)

            # print('Terminating waterheater...')
            # self.pipe_agg_waterheater1.close()
            # break
            pass

        


class NonThermostatControlledLoad(Base):
    '''
    Generic class for all non-thermostat-controlled loads.
    '''
    def __init__(self):
        super(NonThermostatControlledLoad, self).__init__()
        Base.__init__(self)
        self.device_class = 'ntcl'




class BatteryBasedLoad(Base):
    '''
    Generic class for all battery-based loads.
    '''
    def __init__(self):
        super(BatteryBasedLoad, self).__init__()
        Base.__init__(self)
        self.device_class = 'bbl'


class StaticGenerator(Base):
    '''
    Generic class for all local generators.
    '''
    def __init__(self):
        super(StaticGenerator, self).__init__()
        Base.__init__(self)
        self.device_class = 'sgen'


class Solar(StaticGenerator):
    '''
    Generic class for all solar PV.
    '''
    def __init__(self):
        super(Solar, self).__init__()
        StaticGenerator.__init__(self)
        self.load_type = 'solar'


class Wind(StaticGenerator):
    '''
    Generic class for all wind turbines.
    '''
    def __init__(self):
        super(Wind, self).__init__()
        StaticGenerator.__init__(self)
        self.load_type = 'wind'


class Ev(BatteryBasedLoad):
    '''
    Generic class for all electric vehicles.
    '''
    def __init__(self):
        super(Ev, self).__init__()
        BatteryBasedLoad.__init__(self)
        self.load_type = 'ev'


class Storage(BatteryBasedLoad):
    '''
    Generic class for all energy storage.
    '''
    def __init__(self):
        super(Storage, self).__init__()
        BatteryBasedLoad.__init__(self)
        self.load_type = 'storage'





class House(NonThermostatControlledLoad):
    '''
    Generic class for all houses.
    '''
    def __init__(self):
        super(House, self).__init__()
        NonThermostatControlledLoad.__init__(self)
        self.device_class = 'ntcl'
        self.load_type = 'house'

        


class Baseload(NonThermostatControlledLoad):
    '''
    Generic class for all baseloads.
    '''
    def __init__(self):
        super(Baseload, self).__init__()
        NonThermostatControlledLoad.__init__(self)
        self.device_class = 'ntcl'
        self.load_type = 'baseload'



class Clotheswasher(NonThermostatControlledLoad):
    '''
    Generic class for all clotheswashers.
    '''
    def __init__(self):
        super(Clotheswasher, self).__init__()
        NonThermostatControlledLoad.__init__(self)
        self.device_class = 'ntcl'
        self.load_type = 'clotheswasher'
        


class Clothesdryer(NonThermostatControlledLoad):
    '''
    Generic class for all clothesdryers.
    '''
    def __init__(self):
        super(Clothesdryer, self).__init__()
        NonThermostatControlledLoad.__init__(self)
        self.device_class = 'ntcl'
        self.load_type = 'clothesdryer'



class Dishwasher(NonThermostatControlledLoad):
    '''
    Generic class for all dishwashers.
    '''
    def __init__(self):
        super(Dishwasher, self).__init__()
        NonThermostatControlledLoad.__init__(self)
        self.device_class = 'ntcl'
        self.load_type = 'dishwasher'



class Heatpump(ThermostatControlledLoad):
    '''
    Generic class for all heat pumps
    '''
    def __init__(self):
        super(Heatpump, self).__init__()
        ThermostatControlledLoad.__init__(self)
        self.load_type = 'heatpump'



class Fridge(ThermostatControlledLoad):
    '''
    Generic class for all fridges
    '''
    def __init__(self):
        super(Fridge, self).__init__()
        ThermostatControlledLoad.__init__(self)
        self.load_type = 'fridge'


class Freezer(ThermostatControlledLoad):
    '''
    Generic class for all freezers.
    '''
    def __init__(self):
        super(Freezer, self).__init__()
        ThermostatControlledLoad.__init__(self)
        self.load_type = 'freezer'




class Heater(ThermostatControlledLoad):
    '''
    Generic class for all electric heaters.
    '''
    def __init__(self):
        super(Heater, self).__init__()
        ThermostatControlledLoad.__init__(self)
        self.load_type = 'heater'
        


class Relay(Base):
    '''
    Generic class for all relay-based equipments, e.g., door, window, valve
    '''
    def __init__(self):
        super(Relay, self).__init__()
        Base.__init__(self)
        self.load_type = 'relay'


class Waterheater(ThermostatControlledLoad):
    '''
    Generic class for all water heaters.
    '''
    def __init__(self):
        super(Waterheater, self).__init__()
        ThermostatControlledLoad.__init__(self)
        self.load_type = 'waterheater'
        self.dict_valve = {}
        
        print('Running waterheater...')

    #     self.dict_waterheater.update(
    #         initialize_load(
    #             load_type='waterheater', 
    #             dict_devices=self.dict_devices,
    #             dict_house=self.dict_house, 
    #             idx=self.idx, 
    #             distribution=self.distribution,
    #             common=self.dict_global_states,
    #             )
    #         )
        
    #     self.save_interval += np.random.randint(0,60)

    #     ip = f"{'.'.join(self.local_ip.split('.')[:-1])}.113"
    #     port = 17001
    #     timeout = 0.2
    #     ### initialize water valves    
        # n_units = self.dict_devices['waterheater']['n_units']
        # self.dict_valve.update(initialize_device(n_parent=n_units, n_device=1, device_type='valve', schedule=self.dict_waterheater['schedule']))
            
        # dict_save = {}

    



class Aggregator(Base):
    '''
    Generic class for all aggregators.
    '''
    def __init__(self):
        super(Aggregator, self).__init__()
        Base.__init__(self)
        ### run common threads
        self.list_processes = [] 
        self.list_load_instances = []
        self.common_observer = []
        self.agg_observer = []
        self.load_pipes = []
        self.df_schedules = pd.read_csv('./specs/schedules.csv')     
        
        latitude = '-36.866590076725494'
        longitude = '174.77534779638677' 
        self.timestamp = time.time()
        self.realtime = False
        self.timestep = 1.0

        self.weather = Weather(latitude=latitude, 
            longitude=longitude, 
            timestamp=self.timestamp, 
            realtime=self.realtime)

        self.dict_global_states.update({
            # 'local_ip':local_ip, 
            'unixtime': self.timestamp, 
            'step_size': self.timestep,
            'realtime': self.realtime,
            'previous_error':0, 
            'previous_i_term':0, 
            'derivative': 0.0, 
            'max_d': 0.0,
            'min_d': 0.0,
            'tcl_control': 'direct', #tcl_control,
            'case': '', #self.case, 
            'algorithm': 'advanced_ldc' ,#self.algorithm, 
            'ranking': 'dynamic', #self.ranking, 
            'distribution': 'per_device',  #self.distribution, 
            'delay': 1.0, #delay,
            'resolution': 1.0,  #self.resolution, 
            'target': 0.3, #target, 
            'target_percent': 0.3, #self.target_loading, 
            'simulation': 1.0, #simulation, 
            'ldc_signal': 30.0, 
            'flex': 1.0, 
            'loading_percent':0.0, 
            'injector_gain': 0.8, #self.injector_gain,
            })    
    

    def create_network(self):
        pass

    def add_device(self, dict_devices, idx, distribution):
        # self.list_load_instances.append(eval('Waterheater()'))
        for k in dict_devices.keys():
            self.list_load_instances.append(eval(f'{k}()'.capitalize()))
        
        for k in self.list_load_instances:
            k.add_device(dict_devices, idx, distribution, self.dict_global_states)

    def step(self):
        ### update clock
        t = time.perf_counter()
        self.dict_global_states.update(clock(unixtime=self.dict_global_states['unixtime'], 
                step_size=self.dict_global_states['step_size'], 
                realtime=self.dict_global_states['realtime']))
        ### update weather
        self.dict_global_states.update(self.weather.get_weather(self.dict_global_states['unixtime']))

        ### update tasks
        for k in self.list_load_instances:
            k.step()
            # print(self.dict_global_states['unixtime'])
        
        print(time.perf_counter()- t)
        


n_houses = 60
n_ldc = 1.0
n_b2g = 1.0
idx = 10
distribution = 'per_device'
app_per_house = dict(house=1, baseload=1, heatpump=0.61, heater=1.31, waterheater=0.8,
                fridge=1.31, freezer=0.5, clotheswasher=1.08, clothesdryer=0.7816,
                dishwasher=0.6931, ev=0.3, storage=0.3, solar=0.3, wind=0.3)

devices_to_simulate = [x for x in app_per_house.keys() if app_per_house[x]>0]
ldc_devices = [x for x in devices_to_simulate if x not in ['house', 'baseload', 'solar', 'wind', 'fridge', 'freezer', 'dishwasher', 'clotheswasher']]
b2g_devices = ['ev', 'storage']

dict_devices = {k:{
    'n_units':int(n_houses*app_per_house[k]), 
    'n_ldc': (k in ldc_devices)*int(n_houses*n_ldc*app_per_house[k]),
    'n_b2g': (k in b2g_devices)*int(n_houses*n_b2g*app_per_house[k]),
    } for k in devices_to_simulate}
            
if 'storage' in devices_to_simulate:
    dict_devices['storage']['n_b2g'] = int(n_houses*app_per_house['storage']) # set all batteries as b2g capable


















if __name__ == "__main__":
    b = Aggregator()
    b.add_device(dict_devices, idx, distribution)
    for i in range(3):
        b.step()

