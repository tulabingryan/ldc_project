"""
./LOAD.py 
Module for Load model
Author: Ryan Tulabing
Project: Local Demand Control
Institution: University of Auckland
Year: 2017 - 2020
"""

#---import python packages---
from optparse import OptionParser
# from cvxopt.base import matrix, mul, sin, cos
from numpy import linspace
import sys


import numpy as np
import pandas as pd
import datetime, time
import threading, queue
import multiprocessing

# from optparse import OptionParser
# from cvxopt.base import matrix, mul, sin, cos
# from numpy import linspace
# import sys
# import matplotlib.pyplot as pyplot

# try:
#     # for interacting with raspi
#     import RPi.GPIO as GPIO
#     GPIO.setmode(GPIO.BOARD)     # set up BOARD GPIO numbering 
#     # for driving chroma through rs232
#     import serial
#     # for reading spi
#     import spidev
# except:
#     pass

# try:
#     # for controlling pifacedigital
#     import pifacedigitalio
# except:
#     pass

# for multicast
import socket
import struct
import sys
import json
import ast


#---import local modules---
import FUNCTIONS
import CLOCK
import WEATHER
import solar
import CREATOR
import COMMON

from CREATOR import df_houseSpecs, df_heatpumpSpecs, df_heaterSpecs, df_fridgeSpecs, df_freezerSpecs 
from CREATOR import df_waterheaterSpecs, df_clotheswasherSpecs, df_clothesdryerSpecs
from CREATOR import df_dishwasherSpecs, df_evSpecs, df_storageSpecs
from CREATOR import df_clotheswasher, df_clothesdryer, df_dishwasher
from CREATOR import df_solarSpecs, df_windSpecs


global history, df_history, df_demand, df_demand_copy, cols, target_loading, grid_capacity, aggregation
global mean_latitude, mean_longitude, start_time, time_step, df_baseload

from numpy import nanmean, nanmin, nanmax
history = {}
cols = ['name', 'house', 'load_type', 'load_class', 'unixtime', 'hour_start', 'hour_end', 'temp_in', 'temp_out', 'connected', 'mode', 'p_status', 'a_status', 'p_demand', 'a_demand', 'soc','flexibility', 'priority', 'limit', 'ldc_signal']
df_demand = pd.DataFrame([], columns=cols)
df_demand_copy = df_demand.copy()
df_history = pd.DataFrame([])


aggregation = {
    'temp_in': ['mean', 'min', 'max'],
    'temp_in_active': [nanmean, nanmin, nanmax],
    'temp_out': ['mean', 'min', 'max'],
    'soc': ['mean', 'min', 'max'],
    'flexibility': ['mean', 'min', 'max'],
    'priority':['mean', 'min', 'max'],
    'a_demand': ['sum'],
    'p_demand': ['sum']
}



class base():
    """Common base class for all devices"""
    def __init__(self):
        # multiprocessing.Process.__init__(self)
        # self.daemon = True

        self.params = {}
        # self.q_states_self = queue.Queue(maxsize=3)  # queue for data of the device
        # self.q_states_all = queue.Queue(maxsize=3)  # queue for data of peers
        # self.q_user_cmd = queue.Queue(maxsize=3)  # queue for holding the user-command on the state of the date (overiding the auto mode)
        # self.q_grid_cmd = queue.Queue(maxsize=3)
        
        self.dict_states_self = {}
        self.dict_states_all = {}
        self.dict_user_cmd = {}
        self.dict_grid_cmd = {}

        # self.q_states_self.put(self.dict_states_self)
        # self.q_states_all.put(self.dict_states_all)
        # self.q_user_cmd.put(self.dict_user_cmd)
        # self.q_grid_cmd.put(self.dict_grid_cmd)

        self.unixtime = 0
        self.isotime = ''
        
        self.n = 0

    def setup(self):
        for key in self.params.keys():
            self.__dict__[key] = np.array([]) #self.params[key]

        # self.dict_user_cmd.update({'status':1, 'priority':0, 'schedule':{}, 'can_shed':0, 'can_ramp':0, 'hour_start':0, 'hour_end':0})
        # # self.q_user_cmd.put(self.dict_user_cmd)
        
        # self.dict_grid_cmd.update({'algorithm':self.algorithm, 'frequency':self.ldc_signal, 'loading':self.limit, 'timescale':self.timescale})
        # self.q_grid_cmd.put(self.dict_grid_cmd)
        

    def list2matrix(self):
        for key in self.params.keys():
            self.__dict__[key] = matrix(self.__dict__[key], (self.n, 1), 'd')

    def add(self, **kwargs):
        self.n += 1
        keys = self.params.keys()

        # create additional slot in the numpy array
        for key in keys:
            try:
                self.__dict__[key] = np.append(self.__dict__[key], np.array([self.params[key]]))

            except Exception as e:
                print("Error:", key, e)

        # add value to the last slot in the numpy array, except for list_starts, list_ends, and q_user_cmd
        for key, val in kwargs.items():
            if not key in keys: continue

            try:
                if key in ['list_starts', 'list_ends', 'q_user_cmd']:
                    self.params[key].append(val)
                else:
                    self.__dict__[key][-1] = val

            except Exception as e:
                print(e, self.__dict__[key], key, val)


    def prerun(self):
        self.n_usage = self.n_usage.astype(int)
        self.counter = self.counter.astype(int)
        self.old_status = self.a_status
        self.params['list_starts'] = np.array(self.params['list_starts'])
        self.params['list_ends'] = np.array(self.params['list_ends'])
        # padd arrays
        # if 'baseload' in self.params['load_type']:
        # self.__dict__['profile'] = np.array(self.params['profile'])
        # else:
        #     for i in range(len(self.params['profile'])):
        #         p = int(np.max(self.len_profile)-self.len_profile[i])
        #         self.params['profile'][i] = np.pad(self.params['profile'][i], (0, p), mode='constant')
            
        #     self.params['profile'] = np.array(self.params['profile']).reshape(len(self.params['profile']), int(np.max(self.len_profile)))
        

    




    def run_device(self):
        # self.drive_chroma()
        # self.drive_piface()
        # self.drive_relay()
        self.simulate_model()
        # do other stuff
        return 0


    def step(self):
        # simulation step for the house and all loads therein
        try:
            self.propose_demand()
            self.decide()
            self.update_demand()
            self.run_device()
            return self.dict_states_self  # dict_states_self is updated at COMMON.py
        except Exception as e:
            print("Error in ", self.name, " step:", e)















class Load(base):
    def __init__(self):
        base.__init__(self)
        self.params = {}
        
        self.params.update({
            'unixtime':time.time(), 
            'isotime':datetime.datetime.now().isoformat(),
            'timescale':1, 
            'timestep':1,
            'schedule_skew':0,
            'skew':0,
            'ldc':0,
            'baseload':0,
            'humidity':0,
            'windspeed':0,
            'irradiance': 0,
            'irradiance_roof': 0,
            'irradiance_wall1': 0,
            'irradiance_wall2': 0,
            'irradiance_wall3': 0,
            'irradiance_wall4': 0,
            'solar_capacity': 0,
            'solar_efficiency': 0,

            'heat_in':0.0, 
            'heat_ex':0.0, 
            'heat_device':0.0, 
            'heat_all':0.0,
            'demand_heating':0.0, 
            'demand_cooling':0.0,
            'Cp': 1006.0,
            'Ca': 1006.0,
            'Cm': 1006.0, 
            'Um': 0,
            'Ua': 0,
            'water_density':1000.0, 
            'mass_flow':0.0,
            'cop': 3.5, 
            'temp_in': 0,
            'temp_mat': 0,
            'temp_out': 0,
            'cooling_setpoint': 0,
            'heating_setpoint': 0,
            'tolerance': 0,
            'temp_min': 0,
            'temp_max': 0,
            'heat_in':0.0, 
            'heat_ex':0.0, 
            'heat_device':0.0, 
            'heat_all':0.0,
            'cooling_counter': 0,
            'heating_counter': 0,
            'min_coolingtime': 0,
            'min_heatingtime': 0,

            'charging_counter':0,
            'discharging_counter': 0,
            'charging_counter':0,
            'discharging_counter': 0,
            'min_chargingtime': 5,
            'min_dischargingtime': 5,
            'counter':0,
            'power_battery':0, 
            'trip_time':0,  
            
            'priority':0.0, 
            'd_priority':0.0, 
            'job_status':0,
            'flexibility':0.0, 
            'soc':0.0,
            'mode':0,
            'ramp_power':0.0, 
            'shed_power':0.0,
            'can_shed':0,
            'can_ramp':0,
            'p_status':0,
            'a_status':0,
            'p_demand':0.0,
            'a_demand':0.0,

            'house_capacity':10000.0, 
            'house_limit':10000.0,
            'ldc_signal':100, 
            'delta_signal':0, 
            'ldc_command':1.0, 
            'algorithm':0, 
            'limit':10000.0,
            'load_class':'ntcl',
            'load_type':'ntcl',
            'hour_start':0,
            'hour_end':24,
            'unix_start':0,
            'unix_end':0,
            'connected':0,
            'finish':0,
            'n_usage':0,
            'list_starts':[],
            'list_ends':[],
            'profile':[],
            'len_profile':0,
            'q_user_cmd':[],
            })
        self.setup()
        





    def propose_demand(self):
        # This function proposes the demand and status of the device for the next time step
        try:
            # determine if the device is connected
            #   update n_usage... used as index for list_starts, and list_ends (the schedule)
            self.__dict__.update(COMMON.get_n_usage(**self.__dict__))
            #   get the data about when the device should start and end
            self.__dict__.update(COMMON.get_hour(**self.__dict__))
            #   convert schedules from hours of the day to unix
            self.__dict__.update(COMMON.get_unix(**self.__dict__))
            #   based on unix_start and unix_end determine if the device is connected at current unixtime
            self.__dict__.update(COMMON.is_connected(**self.__dict__))

            # determine device status
            #   get flexibility
            self.__dict__.update(COMMON.get_flexibility(**self.__dict__))
            #   get state of charge
            self.__dict__.update(COMMON.get_soc(**self.__dict__))
            #   get job status
            self.__dict__.update(COMMON.get_job_status(**self.__dict__))
            #   determine mode of the device
            self.__dict__.update(COMMON.get_mode(**self.__dict__))
            #   propose a status for the device (i.e., on or off)
            self.__dict__.update(COMMON.get_p_status(**self.__dict__))

            # determine device demand for this timestep
            #   propose a power demand of the device
            self.__dict__.update(COMMON.get_p_demand(**self.__dict__))

            # determine ramping and shedding potential
            #   determine if can ramp or can shed
            self.__dict__.update(COMMON.check_ramp_shed(**self.__dict__))
            #   calculate ramping power
            self.__dict__.update(COMMON.get_ramp_power(**self.__dict__))
            #   calculate shedding power
            self.__dict__.update(COMMON.get_shed_power(**self.__dict__))

        except Exception as e:
            print("Error propose_demand:", e)

        return 0


    def decide(self):
        # decide to approve or deny the proposed status
        #   get device priority
        self.__dict__.update(COMMON.adjust_priority(**self.__dict__))
        #   interpret ldc_signal
        self.__dict__.update(COMMON.interpret_signal(**self.__dict__))
        #   adjust local limit
        self.__dict__.update(COMMON.adjust_limit(**self.__dict__))
        #   save old status
        self.old_status = self.a_status # save old status
        #   decide on the next status
        self.__dict__.update(COMMON.get_a_status(**self.__dict__))
        
        return self.a_status

    def update_demand(self):
        # Update the heat contribution of the TCL considering the aggregators command
        #   recalculate demand for next timestep
        self.__dict__.update(COMMON.get_a_demand(**self.__dict__))

        return self.a_demand


    def simulate_model(self):
        # simulate the model
        #   run simulation and determine the temp_in and temp_mat 
        self.__dict__.update(COMMON.simulate_model(**self.__dict__))

        # update data for peers and history records
        self.__dict__.update(COMMON.broadcast(**self.__dict__))

        # update counter, which counts how long the device is at a certain status
        self.__dict__.update(COMMON.adjust_counter(**self.__dict__))

        return self.temp_in, self.temp_mat




class App(Load):
    def __init__(self):
        Load.__init__(self)

        for key in list(df_houseSpecs):
            self.params[key] = df_houseSpecs.loc[self.n, key] 

        for key in list(df_heatpumpSpecs):
            self.params[key] = df_heatpumpSpecs.loc[self.n, key] 

        for key in list(df_waterheaterSpecs):
            self.params[key] = df_waterheaterSpecs.loc[self.n, key] 

        for key in list(df_freezerSpecs):
            self.params[key] = df_freezerSpecs.loc[self.n, key] 

        for key in list(df_fridgeSpecs):
            self.params[key] = df_fridgeSpecs.loc[self.n, key] 

        for key in list(df_clotheswasherSpecs):
            self.params[key] = df_clotheswasherSpecs.loc[self.n, key] 

        for key in list(df_clothesdryerSpecs):
            self.params[key] = df_clothesdryerSpecs.loc[self.n, key] 

        for key in list(df_dishwasherSpecs):
            self.params[key] = df_dishwasherSpecs.loc[self.n, key] 

        for key in list(df_evSpecs):
            self.params[key] = df_evSpecs.loc[self.n, key] 

        for key in list(df_solarSpecs):
            self.params[key] = df_solarSpecs.loc[self.n, key]


        self.setup()







class Device():
    """interface for all specific device classes"""

    def __init__(self, flist, realtime=False, timescale=1):
        
        global history, df_history, df_demand, df_demand_copy, cols, target_loading, grid_capacity, aggregation
        global mean_latitude, mean_longitude, start_time, time_step, df_baseload

        self.flist = flist
        self.ldc_signal = 100
        self.limit = grid_capacity
        self.loading = target_loading
        self.target = self.loading * self.limit
        self.dict_agg = {}
        self.df_agg = pd.DataFrame([])

        # run global clock
        self.clock = CLOCK.Clock(name='clock', start=start_time, end=None, step_size=time_step, realtime=realtime, timescale=timescale) 
        # run weather sensor object
        self.weather = WEATHER.Weather(name='weather', latitude=mean_latitude, longitude=mean_longitude, timestamp=start_time, mcast_ip='238.173.254.147', mcast_port=12604)
        # save df_baseloads
        
        # elapsed time counter
        self.c = time.perf_counter()
        # checkpoint to display simulation status
        self.checkpoint = 60 # [s] display every 60 seconds

        for item in self.flist:
            try:
                self.__dict__[item] = eval(item + '()')
                history[item] = []
            except Exception as e:
                print("Error Device init:", e)

    def setup(self):
        for item in self.flist:
            if self.__dict__[item].n:
                self.__dict__[item].list2matrix()

    def fcall(self, x):
        f = 0
        for item in self.flist:
            if self.__dict__[item].n:
                f += self.__dict__[item].fcall(x)

        return f

    def dfcall(self, x):
        df = 0
        for item in self.flist:
            if self.__dict__[item].n:
                df += self.__dict__[item].dfcall(x)

        return df

    def step(self, ldc_signal=None, loading=None, report=False, save=False):
        global history, df_demand, cols, df_history, aggregation

        # update ldc_signal
        if ldc_signal: self.ldc_signal = ldc_signal
        if loading: 
            self.loading = loading
            self.target = self.limit * self.loading
        # advance clock
        self.clock.step()
        self.__dict__['App'].unixtime = self.clock.timestamp
        self.__dict__['App'].isotime = self.clock.isotime
        self.__dict__['App'].dayhour = self.clock.dayhour
        self.__dict__['App'].daysecond = self.clock.daysecond
        self.__dict__['App'].tm_min = self.clock.tm_min
        self.__dict__['App'].step_size = self.clock.step_size
        self.__dict__['App'].m = 1

        # get weather data
        dict_weather = self.weather.weather_now(self.clock.timestamp)['weather']

        # get indices for each type of device
        idx_house = np.flatnonzero(self.__dict__['App'].load_type=='baseload')
        idx_hvac = np.flatnonzero((self.__dict__['App'].load_type=='hvac') | (self.__dict__['App'].load_type=='heater'))
        idx_tcl = np.flatnonzero(self.__dict__['App'].load_class=='tcl')
        idx_der = np.flatnonzero(self.__dict__['App'].load_class=='der')
        
        if np.size(idx_house): 
            self.__dict__['App'].humidity[idx_house] = np.add(np.random.normal(0, 0.001, np.size(idx_house)), dict_weather['humidity'])
            self.__dict__['App'].windspeed[idx_house] = np.add(np.random.normal(0, 0.1, np.size(idx_house)), dict_weather['windspeed'])
            self.__dict__['App'].temp_out[idx_house] = np.add(np.random.normal(0, 0.01, np.size(idx_house)), dict_weather['temp_out'])

        for item in self.flist:
            try:
                if self.__dict__[item].n:
                    # signal is added with randomness to account for variations in the accuracy of the sensors
                    self.__dict__[item].ldc_signal = np.clip(np.add(np.random.normal(0, 3, self.__dict__[item].n), self.ldc_signal), a_min=0.1, a_max=100)
                    df_data = pd.DataFrame.from_dict(self.__dict__[item].step(), orient='columns')
                    df_data.index = df_data['name'].values
                    df_data[['unixtime', 'unix_start', 'unix_end']] = df_data[['unixtime', 'unix_start', 'unix_end']].astype(int)
                    # print(df_data[['isotime','unixtime', 'unix_start', 'unix_end', 'connected', 'soc', 'mode','p_status', 'a_status','a_demand', 'temp_out','temp_in', 'temp_max', 'temp_min', 'can_ramp', 'can_shed']])
                    if df_data.index[0] in df_demand.index:
                        df_demand.update(df_data)
                    else:
                        df_demand = pd.concat([df_demand, df_data], sort=False)

                df_demand_copy = df_demand.set_index('house', inplace=False)
                # print(df_demand_copy[['hour_start', 'hour_end', 'unixtime', 'unix_start', 'unix_end', 'connected', 'soc', 'mode','p_status', 'a_status','a_demand', 'n_usage', 'irradiance']])
            except Exception as e:
                print("Error Device step:", e, item)
                
        # extend baseload data to all devices in each house
        try:
            self.__dict__['App'].baseload = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand['house'].values, 'a_demand'].values
        except:
            pass

        # update irradiance for all houses
        if np.size(idx_der):
            self.__dict__['App'].irradiance[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'irradiance'].values
            self.__dict__['App'].irradiance_roof[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'irradiance_roof'].values
            self.__dict__['App'].irradiance_wall1[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'irradiance_wall1'].values
            self.__dict__['App'].irradiance_wall2[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'irradiance_wall2'].values
            self.__dict__['App'].irradiance_wall3[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'irradiance_wall3'].values
            self.__dict__['App'].irradiance_wall4[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'irradiance_wall4'].values
            self.__dict__['App'].humidity[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'humidity'].values
            self.__dict__['App'].windspeed[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'windspeed'].values
            self.__dict__['App'].temp_out[idx_der] = df_demand_copy[df_demand_copy['load_type']=='baseload'].loc[df_demand[df_demand['load_class']=='der']['house'].values, 'temp_out'].values


        # The following lines are valid since, the ratio of hvac to house is 1:1
        if np.size(idx_hvac): 
            # self.__dict__['App'].temp_in[idx_house] = df_demand_copy[df_demand_copy['load_type']=='hvac'].loc[df_demand[df_demand['load_class']=='tcl']['house'].values,'temp_in'].values
            # update temp_out of all tcl devices, note: hvac temp_out will be update below
            # self.__dict__['App'].temp_out[idx_tcl] = df_demand_copy[df_demand_copy['load_type']=='hvac'].loc[df_demand[df_demand['load_class']=='tcl']['house'].values,'temp_in'].values
            # update temp out of hvacs
            self.__dict__['App'].temp_out[idx_hvac] = np.add(np.random.normal(0, 0.01, np.size(idx_hvac)), dict_weather['temp_out'])
            self.__dict__['App'].humidity[idx_hvac] = np.add(np.random.normal(0, 0.001, np.size(idx_hvac)), dict_weather['humidity'])
            self.__dict__['App'].windspeed[idx_hvac] = np.add(np.random.normal(0, 0.1, np.size(idx_hvac)), dict_weather['windspeed'])
        
  
        
        # adjust ldc_signal
        if ldc_signal==None:
            offset = (((self.target) - df_demand['a_demand'].sum()) / self.limit)
            self.ldc_signal += offset * (self.clock.step_size * 1e-1)
            self.ldc_signal = np.clip(self.ldc_signal, a_min=0.01, a_max=100.0)

        # prepare data to return
        df_data = df_demand[['house','a_demand']].groupby('house', sort=True).sum().reset_index(drop=True)
        df_data['p_mw'] = df_data['a_demand'] * 1e-6
        df_data['pf'] = np.random.normal(0.94, 0.01, len(df_data.index))  # assumed average power factor is 0.94
        df_data['q_mvar'] = (df_data['p_mw'] / df_data['pf']) * np.sin(np.arccos(df_data['pf']))
        
        idx_a = np.flatnonzero(self.__dict__['App'].phase=='AN')
        idx_b = np.flatnonzero(self.__dict__['App'].phase=='BN')
        idx_c = np.flatnonzero(self.__dict__['App'].phase=='CN')

        dict_phases = {'AN':idx_a, 'BN':idx_b, 'CN':idx_c}

        for i in ['A', 'B', 'C']:
            df_data['p_{}_mw'.format(i)] = 0
            df_data['p_{}_mw'.format(i)][dict_phases['{}N'.format(i)]] = df_data['p_mw'][dict_phases['{}N'.format(i)]]
            df_data['q_{}_mvar'.format(i)] = 0
            df_data['q_{}_mvar'.format(i)][dict_phases['{}N'.format(i)]] = df_data['q_mvar'][dict_phases['{}N'.format(i)]]

        
        # prepare aggregated data of all devices
        summary = df_demand.groupby('load_type').agg(aggregation)
        summary.columns = ["_".join(x) for x in summary.columns.ravel()]
        self.df_agg = summary.T.unstack().to_frame().sort_index(level=1).T
        self.df_agg.columns = self.df_agg.columns.map('_'.join)        
        self.df_agg['limit'] = self.limit
        self.df_agg['unixtime'] = df_demand['unixtime'].mean()
        self.df_agg['ldc_signal'] = df_demand['ldc_signal'].mean()
        self.df_agg['loading'] = self.loading 
        self.df_agg['sum_a_mw'] = df_data['p_mw'].sum()  # from df_data
        self.df_agg['sum_a_mvar'] = df_data['q_mvar'].sum() # from df_data
        self.df_agg['sum_p_mw'] = df_demand['p_demand'].sum() * 1e-6  
        self.df_agg['sum_p_mvar'] = (self.df_agg['sum_p_mw'] / 0.94) * np.sin(np.arccos(0.94)) 
        self.df_agg['sum_solar_mw'] = df_demand['solar_capacity'].sum() * 1e-6
        self.df_agg['mean_flexibility'] = df_demand['flexibility'].mean()

        # append to history    
        if save:
            df_history = pd.concat([df_history, self.df_agg], sort=False).reset_index(drop=True)
            
            # save history to csv file
            if int(self.clock.timestamp)<=start_time+1:
                df_history.to_csv('./results/history_basic_ldc.csv', index=False, header=True)  # write first row of data with headers
                df_history = df_history.tail(0)  # empty the data frame
            elif int(self.clock.timestamp)%self.checkpoint==0: 
                if report:
                    t = time.perf_counter()
                    print(self.clock.isotime, np.round((t - self.c)/self.checkpoint, 3), 's/step', 
                        'demand:', np.round(df_demand['a_demand'].sum(),3), 'signal:', np.round(df_demand['ldc_signal'].mean(), 3), 
                        'limit:', np.round(df_demand['limit'].mean(), 3), 'flex:', np.round(df_demand['flexibility'].mean(), 3), 
                        'priority:', np.round(df_demand['priority'].mean(), 3))

                    self.c = t

                with open('./results/history_basic_ldc.csv', 'a') as f:
                    df_history.to_csv(f, index=False, header=False)  # do not write the header
                df_history = df_history.tail(0)  # empty the data frame (to reduce memory load) since data has already been written to csv file.
            

        # df_data['unixtime'] = np.mean(df_demand['unixtime'])
        # df_demand['localtime'] = [pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').isoformat() for a in df_demand['unixtime']]

        # df=df.groupby('Name').agg({'Missed':'sum', 'Credit':'sum','Grade':'mean'}).rename(columns=d), 
        # df_demand['iso_end'] = [pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').isoformat() for a in df_demand['unix_end']]

        return df_data[['p_mw', 'q_mvar', 'p_A_mw', 'p_B_mw', 'p_C_mw', 'q_A_mvar', 'q_B_mvar', 'q_C_mvar']]

    def save(self):
        for item in self.flist:
            if self.__dict__[item].n:
                self.__dict__[item].save()        
        return 0



def read():
    """parse input data in lain text format"""
    # fid = open(datafile, 'rt')

    for line in fid:
        data = line.split()
        if not len(data): continue
        if data[0] == 'fridge':
            Function.poly.add(  a = float(data[1]),
                                b = float(data[2]),
                                c = float(data[3]))
        elif data[0] == 'freezer':
            Function.sine.add(  A = float(data[1]),
                                omega = float(data[2]),
                                phi = float(data[3]))

    fid.close()



def change_ldc(device, load_type, n_ldc, report=False):
    idx = np.flatnonzero(device.App.__dict__['load_type']==load_type)
    device.App.__dict__['ldc'][idx] = 0
    s = idx[:int(n_ldc)]

    if np.size(s): device.App.__dict__['ldc'][s] = 1
    if report: print('{} units of {} are capable, out of {}'.format(np.size(s), load_type, np.size(idx)))
    return device



def add_unit(device, load_type, n_unit=0, n_ldc=0, idx=10, report=False):
    # solar PV
    dict_load_specs = {
        'baseload': [df_houseSpecs, device.App.__dict__['df_baseload']],
        'hvac': [df_heatpumpSpecs, device.App.__dict__['df_baseload']],
        'heater': [df_heaterSpecs, device.App.__dict__['df_baseload']],
        'waterheater': [df_waterheaterSpecs, device.App.__dict__['df_baseload']],
        'fridge': [df_fridgeSpecs, device.App.__dict__['df_baseload']],
        'freezer': [df_freezerSpecs, device.App.__dict__['df_baseload']],
        'clotheswasher': [df_clotheswasherSpecs, df_clotheswasher],
        'clothesdryer': [df_clothesdryerSpecs, df_clothesdryer],
        'dishwasher': [df_dishwasherSpecs, df_dishwasher],
        'ev': [df_evSpecs, 0],
        'storage': [df_storageSpecs, 0],
        'solar': [df_solarSpecs, 0],
        'wind': [df_windSpecs, 0]
    }

    try:
        device.App.params['list_starts'] = list(device.App.params['list_starts'])
        device.App.params['list_ends'] = list(device.App.params['list_ends'])
        
        if n_unit:
            for i in range(idx, idx + n_unit):
                dict_params = {}
                for key in list(dict_load_specs[load_type][0]):
                    dict_params[key] = dict_load_specs[load_type][0].loc[i, key]    
                dict_params['list_starts'] = np.array([dict_params['s{}'.format(i)] for i in range(10)])
                dict_params['list_ends'] = np.array([dict_params['e{}'.format(i)] for i in range(10)])

                if load_type in ['ev', 'storage', 'solar', 'wind']:
                    dict_params['len_profile'] = 0 
                else:
                    dict_params['len_profile'] = len(dict_load_specs[load_type][1][dict_params['profile']].values)
                device.App.add(**dict_params)

        device.App.prerun()

        if report: print('System has {} units of {}'.format(n_unit, load_type))

    except Exception as e:
        print("Error LOAD.py add_unit:", e, load_type)
    return device

def add_device(device, dict_devices, idx=10):
    '''
    Add units of devices based on dict_devices
    '''
    dict_load_type = {
        'House': 'baseload',
        'Hvac': 'hvac',
        'Heater': 'heater',
        'Waterheater': 'waterheater',
        'Fridge': 'fridge',
        'Freezer': 'freezer',
        'Clotheswasher': 'clotheswasher',
        'Clothesdryer': 'clothesdryer',
        'Dishwasher': 'dishwasher',
        'Ev': 'ev',
        'Storage': 'storage',
        'Solar': 'solar',
        'Wind': 'wind'
    }

    for k in dict_load_type.keys():
        if dict_devices[k]['n']:
            if len(device.App.__dict__['load_type']):
                x_unit = len(np.flatnonzero(device.App.__dict__['load_type']==dict_load_type[k]))  # existing number of units
                x_ldc = len(np.flatnonzero((device.App.__dict__['load_type']==dict_load_type[k])&(device.App.__dict__['ldc']==1)))  # existing number of units with ldc
                
            else:
                x_unit = 0
                x_ldc = 0

            n_idx = idx + x_unit  # offset starting index for profile selection in df_houseSPecs, etc..
            n_unit = dict_devices[k]['n'] - x_unit

            if n_unit:
                n_ldc = int(dict_devices[k]['n'] * dict_devices[k]['ldc']) - x_ldc
                device = add_unit(device=device, load_type=dict_load_type[k], n_unit=n_unit, n_ldc=n_ldc, idx=n_idx)
                device = change_ldc(device=device, load_type=dict_load_type[k], n_ldc=int(dict_devices[k]['n'] * dict_devices[k]['ldc']))

    return device





def to_yearsecond(start, duration):
    dt_range = pd.date_range(start=pd.to_datetime(start, unit='s'),
                            freq='S', periods=duration, tz='UTC')
    
    dt_range = dt_range.tz_convert('Pacific/Auckland')
    df_datetime = pd.DataFrame(dt_range, columns=['date_time'])
    df_datetime.index = pd.DatetimeIndex(df_datetime['date_time'])
    df_datetime['yearsecond'] = ((df_datetime.index.week - 1) * (3600*24*7)) \
                        + (df_datetime.index.dayofweek * (3600*24)) \
                        + (df_datetime.index.hour * 3600) \
                        + (df_datetime.index.minute * 60) \
                        + (df_datetime.index.second)

    # print(dt_range)
    
    return df_datetime['yearsecond'].values[0], df_datetime['yearsecond'].values[-1]

def get_baseloads(start, duration, padding=1800):
    '''
    Get the baseloads from './profiles/baseload.h5' and return a dataframe
    '''
    x, y = to_yearsecond(start, duration)
    with pd.HDFStore('./profiles/baseload.h5', 'r') as store:
        df = store.select('records', where='index>={} and index<={}'.format(x - padding, y + padding))
    return df
    

####---------------------------------------------------------------------------------

def make_devices(dict_devices, 
    idx=11,
    capacity = 300e3,
    loading = 0.5,
    start = time.time(),
    duration = 3600, #[s]72 hours
    step_size = 1,
    realtime = True,
    timescale = 1,
    three_phase = True,
    simulate=1,
    renew=1,
    latitude = -36.866590076725494,
    longitude = 174.77534779638677,
    mcast_ip_local = '238.173.254.147',
    mcast_port_local = 12604,
    ):
    
    global history, df_history, df_demand, df_demand_copy, cols, target_loading, grid_capacity
    global mean_latitude, mean_longitude, start_time, time_step, df_baseload
    grid_capacity = capacity
    target_loading = loading
    mean_latitude = latitude
    mean_longitude = longitude
    start_time = start
    time_step = step_size


    # CREATOR.create_specs(
    #     n_houses = dict_devices['House']['n'] + idx, 
    #     n_hvacs = dict_devices['Hvac']['n'] + idx, 
    #     n_heaters = dict_devices['Heater']['n'] + idx, 
    #     n_waterheaters = dict_devices['Waterheater']['n'] + idx, 
    #     n_fridges = dict_devices['Fridge']['n'] + idx, 
    #     n_freezers = dict_devices['Freezer']['n'] + idx,
    #     n_evs = dict_devices['Ev']['n'] + idx, 
    #     n_storages = dict_devices['Storage']['n'] + idx, 
    #     n_clotheswashers = dict_devices['Clotheswasher']['n'] + idx, 
    #     n_clothesdryers = dict_devices['Clothesdryer']['n'] + idx, 
    #     n_dishwashers = dict_devices['Dishwasher']['n'] + idx,
    #     n_pvs = dict_devices['Solar']['n'] + idx, 
    #     n_winds = dict_devices['Wind']['n'] + idx, 
    #     ldc_adoption = dict_devices['House']['ldc'], 
    #     v2g_adoption = dict_devices['Ev']['v2g'], 
    #     latitude = latitude,
    #     longitude = longitude, 
    #     renew=renew
    #     )

    df_houseSpecs = pd.read_csv('./specs/houseSpecs.csv')
    df_heatpumpSpecs = pd.read_csv('./specs/hvacSpecs.csv')
    df_heaterSpecs = pd.read_csv('./specs/heaterSpecs.csv')
    df_fridgeSpecs = pd.read_csv('./specs/fridgeSpecs.csv')
    df_freezerSpecs = pd.read_csv('./specs/freezerSpecs.csv')
    df_waterheaterSpecs = pd.read_csv('./specs/waterheaterSpecs.csv')
    df_clotheswasherSpecs = pd.read_csv('./specs/clotheswasherSpecs.csv')
    df_clothesdryerSpecs = pd.read_csv('./specs/clothesdryerSpecs.csv')
    df_dishwasherSpecs = pd.read_csv('./specs/dishwasherSpecs.csv')
    df_evSpecs =  pd.read_csv('./specs/evSpecs.csv')
    df_storageSpecs =  pd.read_csv('./specs/storageSpecs.csv')
    

    df_baseload = get_baseloads(start, duration)


    device = Device(['App'], realtime=realtime, timescale=timescale) #list(dict_devices))
    # fetch baseload profiles
    device.App.__dict__['df_baseload'] = df_baseload

    device = add_device(device, dict_devices, idx=idx)

    return device


        
if __name__ == '__main__':

    parser = OptionParser(version=' ')
    parser.add_option('-i', '--i', dest='idx',
                    default=11, help='starting index')
    parser.add_option('-n', '--n', dest='n',
                    default=70, help='number of units')
    
    options, args = parser.parse_args(sys.argv[1:])

    start_idx = 0
    ldc_adoption = 0.0
    n = int(options.n)
    grid_capacity = n * 5000
    target_loading = 0.5

    dt_start = datetime.datetime(2018, 7, 15, 17, 0, 0)
    start = time.mktime(dt_start.timetuple())

    
    
    # define the number of devices to run
    dict_devices = {
        'House':{'n':int(n*0), 'ldc':ldc_adoption},
        'Hvac':{'n':int(n*0), 'ldc':ldc_adoption},
        'Heater':{'n':int(n*0), 'ldc':ldc_adoption},
        'Fridge':{'n':int(n*0), 'ldc':ldc_adoption},
        'Freezer':{'n':int(n*0), 'ldc':ldc_adoption},
        'Waterheater':{'n':int(n*0), 'ldc':ldc_adoption},
        'Clotheswasher':{'n':int(n*1), 'ldc':ldc_adoption},
        'Clothesdryer':{'n':int(n*0), 'ldc':ldc_adoption},
        'Dishwasher':{'n':int(n*0), 'ldc':ldc_adoption},
        'Ev':{'n':int(n*0), 'ldc':ldc_adoption, 'v2g':int(n*0.0)},
        'Storage':{'n':int(n*0), 'ldc':ldc_adoption},
        'Solar':{'n':int(n*0), 'ldc':ldc_adoption},
        'Wind':{'n':int(n*0), 'ldc':ldc_adoption},    
        }

    device = make_devices(dict_devices=dict_devices,
                    idx=start_idx,
                    capacity = grid_capacity,
                    loading = target_loading,
                    start = start,
                    duration = 1800,
                    step_size = 1,
                    realtime = False,
                    timescale = 1,
                    three_phase = True,
                    simulate=1,
                    renew=0,
                    latitude = -36.866590076725494,
                    longitude = 174.77534779638677,
                    mcast_ip_local = '238.173.254.147',
                    mcast_port_local = 12604,
                )

    checkpoint = 60 # [s]  # to display simulation status and write accumulated data to the disk
    print(dict_devices)
    for i in range(60*60*36):
        # simulate devices through time
        t0 = time.perf_counter()
        x = device.step()
        print(device.App.isotime, time.perf_counter()-t0) #, device.App.a_status)
        # print(x)
        # print(device.df_agg[['waterheater_temp_in_mean', 'waterheater_temp_out_mean', 'waterheater_a_demand_sum', 'waterheater_flexibility_mean']])
        # print(x.sum(axis=0))
        
            