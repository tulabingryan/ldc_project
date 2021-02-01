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
        self.pause = 1e-6

        self.n_house = 0
        self.n_units = 0
        self.n_ldc = 0
        self.n_b2g = 0
        

        self.list_variable_states = [
            'proposed_status', 'actual_status',
            'proposed_demand', 'actual_demand',
            'mode', 'flexibility', 'progress',
            'connected', 'priority', 'ldc_signal',
            'temp_in', 'temp_out', 'humidity_in',
            'humidity_out'
        ]

        self.dict_startcode = {
            'baseload': 0,
            'house': 0,
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
            'wind': 29,
        }

    
    def add_device(self, dict_devices, idx, distribution, dict_global_states):
        self.n_house += int(dict_devices['house']['n_units'])
        self.n_units += int(dict_devices[self.load_type]['n_units'])
        self.n_ldc += int(dict_devices[self.load_type]['n_ldc'])
        self.n_b2g += int(dict_devices[self.load_type]['n_b2g'])
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
            
            ### assign b2g
            df['b2g'] = 0
            idxs = df.index
            if distribution=='per_device':
                df['b2g'] = 0
                selection = np.random.choice(idxs, self.n_b2g, replace=False)
                df.loc[selection, 'b2g'] = 1
            else:
                df.loc[idxs[0:self.n_b2g], 'b2g'] = 1
                df.loc[idxs[self.n_b2g:], 'b2g'] = 0

        # self.dict_constant_states = df.to_dict(orient='list')
        self.dict_variable_states = df.to_dict(orient='list')

        for k, v in self.dict_variable_states.items():
            # self.dict_constant_states[k] = np.asarray(v).reshape(-1)
            self.dict_variable_states[k] = np.asarray(v).reshape(-1)


    def initialize_states(self, house_instance):
        '''
        Initialize time-invariant states
        '''
        self.dict_variable_states['unixstart'] = np.random.normal(self.dict_global_states['unixtime'] - (self.dict_global_states['hour']*3600), 0.1, self.n_units)
        self.dict_variable_states['unixend'] = np.random.normal(self.dict_global_states['unixtime'] - (self.dict_global_states['hour']*3600) + (3600*24), 0.1, self.n_units)
        self.dict_variable_states['alpha'] = np.exp(np.ones(self.n_units)/60)
        self.dict_variable_states['actual_demand'] = np.zeros(self.n_units)
        self.dict_variable_states['house'] = house_instance.dict_variable_states['name'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
        self.dict_variable_states['schedule'] = house_instance.dict_variable_states['schedule'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
        self.dict_variable_states['load_type_id'] = np.ones(self.n_units) * self.dict_startcode[self.load_type]
        self.dict_variable_states['old_signal'] = np.zeros(self.n_units)
        self.dict_variable_states['ldc_signal'] = np.zeros(self.n_units)
        if 'priority' not in self.dict_variable_states.keys(): 
            self.dict_variable_states['priority'] = np.random.uniform(20, 80, self.n_units)
        self.dict_variable_states['priority_offset'] = np.subtract(self.dict_variable_states['ldc_signal'], self.dict_variable_states['priority'])

        if self.load_type in ['house', 'baseload']:
            self.dict_variable_states['connected'] = np.ones(house_instance.n_units)

        if self.load_type in ['heatpump', 'heater']:
            self.dict_variable_states['latitude'] = house_instance.dict_variable_states['latitude'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['longitude'] = house_instance.dict_variable_states['longitude'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['elevation'] = house_instance.dict_variable_states['elevation'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['roof_tilt'] = house_instance.dict_variable_states['roof_tilt'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['azimuth'] = house_instance.dict_variable_states['azimuth'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['albedo'] = house_instance.dict_variable_states['albedo'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['roof_area'] = house_instance.dict_variable_states['roof_area'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['wall_area'] = house_instance.dict_variable_states['wall_area'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['window_area'] = house_instance.dict_variable_states['window_area'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['skylight_area'] = house_instance.dict_variable_states['skylight_area'][np.asarray(np.arange(self.n_units)%house_instance.n_units, dtype=int).reshape(-1)]
            self.dict_variable_states['mass_flow'] = np.zeros(self.n_units)   
            self.dict_variable_states['temp_target'] = self.dict_variable_states['heating_setpoint']
            # self.dict_variable_states['temp_in'] = self.dict_variable_states['temp_target'] - np.abs((np.random.normal(0.0,0.1,self.n_units)*self.dict_variable_states['tolerance']))
            self.dict_variable_states['solar_heat'] = np.zeros(self.n_units)
            self.dict_variable_states['power_thermal'] = np.zeros(self.n_units)
            self.dict_variable_states['heat_all'] = np.zeros(self.n_units)
            self.dict_variable_states['temp_out'] = np.random.normal(self.dict_global_states['temp_out'], 0.01, self.n_units)
            self.dict_variable_states['humidity'] = np.random.normal(self.dict_global_states['humidity'], 0.01, self.n_units)
            self.dict_variable_states['humidity_in'] = self.dict_variable_states['humidity'] - np.random.normal(0.1, 0.001, self.n_units)
            self.dict_variable_states['windspeed'] = np.random.normal(self.dict_global_states['windspeed'], 0.01, self.n_units)
            

        if self.load_type in ['fridge', 'freezer']:
            self.dict_variable_states['mass_flow'] = np.zeros(self.n_units)
            self.dict_variable_states['mode'] = np.zeros(self.n_units).astype(int)
            self.dict_variable_states['temp_target'] = self.dict_variable_states['cooling_setpoint']
            self.dict_variable_states['solar_heat'] = np.zeros(self.n_units)
            self.dict_variable_states['power_thermal'] = np.zeros(self.n_units)
            self.dict_variable_states['heat_all'] = np.zeros(self.n_units)
            # air density is 1.225kg/m^3 at 15degC sea level
            # air density is 1.2041 kg/m^3 at 20 degC sea level
            # water density is 999.1 kg/m^3 at 15degC sea level
        if self.load_type in ['heater', 'waterheater']:
            self.dict_variable_states['mass_flow'] = np.zeros(self.n_units)
            self.dict_variable_states['mode'] = np.ones(self.n_units)
            self.dict_variable_states['temp_target'] = self.dict_variable_states['heating_setpoint']
            self.dict_variable_states['temp_max'] = self.dict_variable_states['temp_target'] + (self.dict_variable_states['tolerance']*0.9)
            # self.dict_variable_states['temp_in'] = self.dict_variable_states['temp_target'] - np.abs((np.random.normal(0.0,0.3,self.n_units)*self.dict_variable_states['tolerance']))
            self.dict_variable_states['min_cycletime'] = np.random.uniform(1, 1.1, self.n_units)
            self.dict_variable_states['solar_heat'] = np.zeros(self.n_units)
            self.dict_variable_states['power_thermal'] = np.zeros(self.n_units)
            self.dict_variable_states['heat_all'] = np.zeros(self.n_units)
            # self.dict_variable_states['counter'] = np.random.uniform(2, 3, self.n_units)
            # self.dict_variable_states['temp_in'] = np.random.normal(np.mean(self.dict_variable_states['temp_in']), np.std(self.dict_variable_states['temp_in']), self.n_units)

        if self.load_type in ['storage']:
            self.dict_variable_states['soc'] = np.clip(np.random.normal(0.5, 0.3, self.n_units), a_min=0.2, a_max=0.8)
            self.dict_variable_states['progress'] = np.divide(self.dict_variable_states['soc'], self.dict_variable_states['target_soc'])
            self.dict_variable_states['mode'] = np.zeros(self.n_units)
            self.dict_variable_states['min_soc'] = np.random.uniform(0.2, 0.3, self.n_units)
            self.dict_variable_states['target_soc'] = np.random.uniform(0.9, 0.95, self.n_units)
            self.dict_variable_states['connected'] = np.ones(self.n_units)
            self.dict_variable_states['charging_power'] = np.ones(self.n_units) * 7400
            self.dict_variable_states['capacity'] = np.ones(self.n_units) * 13.0 * 1000 * 3600
            self.dict_variable_states['b2g'] = np.ones(self.n_units)
            
        if self.load_type in ['ev', 'evehicle']:
            self.dict_variable_states['soc'] = np.random.uniform(0.7, 0.8, self.n_units)
            self.dict_variable_states['progress'] = np.divide(self.dict_variable_states['soc'], self.dict_variable_states['target_soc'])
            self.dict_variable_states['min_soc'] = np.random.uniform(0.3, 0.4, self.n_units)
            self.dict_variable_states['target_soc'] = np.random.uniform(0.9, 0.95, self.n_units)
            self.dict_variable_states['connected'] = np.ones(self.n_units)
            self.dict_variable_states['capacity'] = np.array([dict_ev[x]['capacity'] for x in self.dict_variable_states['profile']]) * 1000 * 3600
            self.dict_variable_states['charging_power'] = np.array([dict_ev[x]['charging_power'] for x in self.dict_variable_states['profile']]) * 1000 
            
            self.dict_variable_states['daily_energy'] = np.multiply(np.clip(np.random.normal(0.6, 0.05, self.n_units), a_min=0.55, a_max=0.65), self.dict_variable_states['capacity']) #[Ws]
            self.dict_variable_states['km_per_kwh'] = np.clip(np.random.normal(6.0, 0.1, self.n_units), a_min=4.225, a_max=6.76) #[km/kWh] 1kWh per 6.5 km avg 
            self.dict_variable_states['trip_distance'] = np.multiply(self.dict_variable_states['km_per_kwh'], self.dict_variable_states['daily_energy']/1e3/3.6e3) # [km] avg daily trip
            self.dict_variable_states['avg_speed'] = np.clip(np.random.normal(85, 10, self.n_units), a_min=50, a_max=100)  # [km/h]
            self.dict_variable_states['trip_time'] = np.divide(self.dict_variable_states['trip_distance']*0.5, self.dict_variable_states['avg_speed']) #[hours] avg daily trip
            self.dict_variable_states['driving_power'] = ((self.dict_variable_states['trip_distance']*0.5/self.dict_variable_states['trip_time']) / self.dict_variable_states['km_per_kwh']) * 1000 * -1 #[W]
            self.dict_variable_states['unixstart'] = np.random.normal(self.dict_global_states['unixtime'] - (self.dict_global_states['hour']*3600) - (6*3600), 1800, self.n_units)
            self.dict_variable_states['unixend'] = np.random.normal(self.dict_global_states['unixtime'] - (self.dict_global_states['hour']*3600) + (6*3600), 1800, self.n_units)
            
        if self.load_type in ['dishwasher', 'clothesdryer', 'clotheswasher']:
            self.dict_variable_states['finished'] = np.ones(self.n_units)
            self.dict_variable_states['unfinished'] = np.zeros(self.n_units) 
            self.dict_variable_states['unixstart'] = np.random.normal(self.dict_global_states['unixtime'] - (self.dict_global_states['hour']*3600)- (3600*24) + (3600*18), 900, self.n_units)
            self.dict_variable_states['unixend'] = np.random.normal(self.dict_global_states['unixtime'] - (self.dict_global_states['hour']*3600) - (3600*24) + (3600*21) , 900, self.n_units)
        
        if self.load_type in ['solar', 'wind']:
            self.dict_variable_states['mode'] = np.ones(self.n_units)  # generation modes are 1
            self.dict_variable_states['priority'] = np.ones(self.n_units) * 90.0
            self.dict_variable_states['connected'] = np.ones(self.n_units)
            self.dict_variable_states['flexibility'] = np.ones(self.n_units) * 0.9
            self.dict_variable_states['capacity'] = np.clip(np.round(np.random.normal(270*18, 270, self.n_units), -1), a_min=270*10, a_max=270*56)


        if self.load_type in ['dishwasher', 'clotheswasher', 'clothesdryer']:
            ### setup the profiles
            try:
                with open('./profiles/nntcl.json') as f:
                    nntcl = json.load(f)
                    self.dict_data = nntcl[self.load_type.capitalize()]
                    self.dict_variable_states['len_profile'] = np.array([len(self.dict_data[k]) for k in self.dict_variable_states['profile']])
                del nntcl  # free up the memory
            except Exception as e:
                print(f'Error clotheswasher setup:{e}')
        
        if self.load_type in ['baseload', 'house']:
            self.df, self.validity = fetch_baseload(self.dict_global_states['season'])
            
        
        

    def step(self):
        pass

    def autorun(self):
        pass

    def __del__(self):
        print(f'Terminating {self.load_type}...')





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
            ### update weather
            self.dict_variable_states['temp_out'] = np.add(np.random.normal(0,0.01, self.n_units), self.dict_global_states['temp_out'])
            self.dict_variable_states['unixtime'] = np.ones(self.n_units)*self.dict_global_states['unixtime']
            ### update schedules
            update_schedules(self.dict_variable_states, self.dict_global_states)

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
            self.dict_variable_states['mass_flow'] = np.add(self.dict_variable_states['mass_flow'], np.random.choice([0, 0.01], self.n_units, p=[0.9, 0.1]))
            
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



    def step(self):
        try:
            ### update common variables
            update_from_common(self.dict_variable_states, self.dict_global_states)
            
            ### update schedules
            update_schedules(self.dict_variable_states, self.dict_global_states)

            ### update device proposed mode, status, priority, and demand
            device_ntcl(self.dict_variable_states, self.dict_data)

            ### update ldc_dongle approval for the proposed status and demand
            ldc_dongle(self.dict_variable_states, self.dict_global_states)
            
            # ### send data to main
            # self.pipe_agg_clotheswasher1.send(self.dict_variable_states)
            
            ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
            enduse_ntcl(self.dict_variable_states)

        except Exception as e:
            print(f"Error {self.load_type}: {e}")
        




class BatteryBasedLoad(Base):
    '''
    Generic class for all battery-based loads.
    '''
    def __init__(self):
        super(BatteryBasedLoad, self).__init__()
        Base.__init__(self)
        self.device_class = 'bbl'
    
    def step(self):
        ### update common variables
        update_from_common(self.dict_variable_states, self.dict_global_states)
        
        ### update device proposed mode, status, priority, and demand
        device_battery(self.dict_variable_states)

        ### update ldc_dongle approval for the proposed status and demand
        ldc_dongle(self.dict_variable_states, self.dict_global_states)
        
        # ### send data to main
        # self.pipe_agg_storage1.send(self.dict_variable_states)

        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        enduse_battery(self.dict_variable_states)



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

    def step(self):
        ### update common variables
        update_from_common(self.dict_variable_states, self.dict_global_states)
        
        ### update schedules
        update_schedules(self.dict_variable_states, self.dict_global_states)

        ### update device proposed mode, status, priority, and demand
        device_battery(self.dict_variable_states)

        ### update ldc_dongle approval for the proposed status and demand
        ldc_dongle(self.dict_variable_states, self.dict_global_states)
        
        # ### send data to main
        # self.pipe_agg_ev1.send(self.dict_variable_states)

        ### update device states, e.g., temp_in, temp_mat, progress, soc, through simulation
        enduse_battery(self.dict_variable_states)



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
        
    def step(self):
        # ### update common variables
        # update_from_common(self.dict_variable_states, self.dict_global_states)

        # ### update baseload
        # sk = np.mod(np.add(np.divide(self.dict_variable_states['schedule_skew'], 60), self.dict_global_states['weekminute']), 10080)  # 10080 minutes in a week
        # self.dict_variable_states['actual_demand'] = np.array([self.df.loc[x, y] for x, y in zip(sk.astype(int), self.dict_variable_states['schedule'])]) + np.abs(np.random.normal(0,10, self.n_units))
    
        # # ### send update to main
        # # self.pipe_agg_baseload1.send(self.dict_variable_states)
        
        # ### fetch next batch of data
        # if (self.dict_global_states['season']!=self.validity['season']):
        #     self.df, self.validity = fetch_baseload(self.dict_global_states['season'])
        pass


class Baseload(NonThermostatControlledLoad):
    '''
    Generic class for all baseloads.
    '''
    def __init__(self):
        super(Baseload, self).__init__()
        NonThermostatControlledLoad.__init__(self)
        self.device_class = 'ntcl'
        self.load_type = 'baseload'

    def step(self):
        ### update common variables
        update_from_common(self.dict_variable_states, self.dict_global_states)

        ### update baseload
        sk = np.mod(np.add(np.divide(self.dict_variable_states['schedule_skew'], 60), self.dict_global_states['weekminute']), 10080)  # 10080 minutes in a week
        self.dict_variable_states['actual_demand'] = np.array([self.df.loc[x, y] for x, y in zip(sk.astype(int), self.dict_variable_states['schedule'])]) + np.abs(np.random.normal(0,10, self.n_units))
    
        # ### send update to main
        # self.pipe_agg_baseload1.send(self.dict_variable_states)
        
        ### fetch next batch of data
        if (self.dict_global_states['season']!=self.validity['season']):
            self.df, self.validity = fetch_baseload(self.dict_global_states['season'])
        
        

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


class Network(Base):
    '''
    Generic class for electrical network.
    '''
    def __init__(self):
        super(Network, self).__init__()
        Base.__init__(self)
        
    



class Aggregator(Base):
    '''
    Generic class for all aggregators.
    '''
    def __init__(self):
        super(Aggregator, self).__init__()
        Base.__init__(self)
        self.load_type = 'aggregator'
        ### run common threads
        self.list_processes = [] 
        self.load_instances = {}
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
            if k=='house':
                self.house = House()
                self.house.add_device(dict_devices, idx, distribution, self.dict_global_states)
            else:
                self.load_instances.update({k: eval(f'{k}()'.capitalize())})
        
        for k, v in self.load_instances.items():
            v.add_device(dict_devices, idx, distribution, self.dict_global_states)

        self.house.loads = self.load_instances

    def initialize_states(self):
        self.dict_global_states.update(clock(unixtime=self.dict_global_states['unixtime'], 
                step_size=self.dict_global_states['step_size'], 
                realtime=self.dict_global_states['realtime']))
        ### update weather
        self.dict_global_states.update(self.weather.get_weather(self.dict_global_states['unixtime']))

        self.house_indices = {}

        for k, v in self.load_instances.items():
            v.initialize_states(house_instance=self.house)
            self.house_indices.update({k:{h:np.flatnonzero(v.dict_variable_states['house']==h) for h in self.house.dict_variable_states['name']}})

        self.tt = 0

    def step(self):
        ### update clock
        t = time.perf_counter()
        self.dict_global_states.update(clock(unixtime=self.dict_global_states['unixtime'], step_size=self.dict_global_states['step_size'], realtime=self.dict_global_states['realtime']))
        ### update weather
        self.dict_global_states.update(self.weather.get_weather(self.dict_global_states['unixtime']))
        ### update tasks
        self.dict_global_states['current_task'] = self.df_schedules.iloc[self.dict_global_states['weekminute']]

        ### update tasks
        [v.step() for k, v in self.load_instances.items()]
            
        ### sum up powers
        self.house.demand = [np.sum([d.dict_variable_states['actual_demand'][self.house_indices[k][h]].sum() for k, d in self.load_instances.items()]) for h in self.house.dict_variable_states['name']]
        ### 

        print(time.perf_counter()- t, self.dict_global_states['isotime'], self.house.loads['heatpump'].dict_variable_states['temp_in'][0])
    
    def autorun(self):
        while True:
            try:
                self.step()
            except Exception as e:
                print(f"Error autorun:{e}")
            except KeyboardInterrupt:
                break
        












if __name__ == "__main__":
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








    b = Aggregator()
    b.add_device(dict_devices, idx, distribution)
    b.initialize_states()
    b.autorun()

