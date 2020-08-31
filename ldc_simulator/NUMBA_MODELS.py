"""
./MODELS.py 
Module for LDC System Models
Author: Ryan Tulabing
Project: Local Demand Control
Institution: University of Auckland
Year: 2017 - 2020

Generic model:

                           _________________Se_________________ 
                          |                                    |
     __________   A1   ___|/____   A2   __________        _____|_________
    |  Dongle  |----->| Device |----->|  End-use |  Se  |  Environment |
    |__________|<-----|________|<-----|__________|<-----|______________|
       /|        S1     |  /|      S2    |    /|                |
        |A0           S4|   |A4        S3|/____|A3              |
     ___|_______       _|/__|____      | Person |               |
    |  LDC     |  S5  |  Local  |      |________|               |
    | Injector |<-----|  Grid   |<------------------------------|
     ----------        ---------     Se

Definitions:
LDC Injector = LDC signal injector
    A0 = LDC signal (750-850Hz)
Dongle = LDC dongles to control the loads
    A1 = Action, approval of proposed demand
    S1 = State of the device, e.g., priority, mode, etc.
Device = Load appliance, e.g., heatpump, waterheater, etc.
    A2 = Action of the device, e.g., provide heat, cool freezer, etc.
    S2 = State of the end-use, e.g., room temp, freezer temp, job status, soc, etc.
End-use = End-usage application, room to heat, dishes to wash, laundry to dry
    A3 = Action of users, e.g., schedules, water usage, other settings, etc.
    S3 = State of the end-usage, e.g., temperature, soc, 
Person = person that creates schedules and settings for end-uses
Local Grid = local power grid
    A4 = Action of the grid, e.g., voltage, frequency
    S4 = State of the device, e.g., power demand, 
    S5 = state of the grid, e.g., aggregated demand, voltage, frequency, 
Environment = Weather environment, e.g, outside temperature, humidity, solar, wind
    Se = state of the environment, e.g., outside temp, solar, windspeed, humidity



"""

#---import python packages---
from optparse import OptionParser
import sys, os


import numpy as np
import pandas as pd
import datetime, time
import threading, queue, multiprocessing

# # for multicast
# import socket, struct, sys, json, ast


# #---import local modules---
import FUNCTIONS
# import CLOCK
from WEATHER import Weather
# import solar
# import CREATOR
# import COMMON


from numba import jit

stamp_now = time.time()

# for k in state:
#     print(k, state[k])


def clock(unixtime, real_time=True, step_size=1):
    # return next timestamp and stepsize
    if real_time:
        timestamp = time.time()
        step_size = np.subtract(timestamp, unixtime)
    else:
        timestamp = np.add(unixtime, step_size)

    dt = pd.to_datetime(timestamp, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
    return timestamp, step_size, dt.week, dt.dayofweek, dt.hour, dt.minute, dt.second, dt.microsecond, dt.isoformat()



################ models for end-uses ###################################################
@jit(nopython=True)
def enduse_tcl(heat_all, air_part, temp_in, temp_mat, temp_out, Um, Ua, Cp, Ca, Cm, mass_flow, step_size, unixtime, connected):
    # update temp_in and temp_mat, and temp_in_active, i.e., for connected tcls

    count = 0
    if step_size > 0:
        increment = np.min(np.array([0.5, step_size]))
        while count < step_size:
            # for air temp
            conv_heat = np.multiply(heat_all, air_part)
            conv_in_mat = np.multiply(np.subtract(temp_in, temp_mat), Um)
            conv_in_out = np.multiply(np.subtract(temp_in, temp_out), Ua)
            mcpdt = np.multiply(np.subtract(temp_in, temp_out), np.multiply(mass_flow, Cp))

            partial = conv_heat
            partial = np.subtract(partial, conv_in_mat)
            partial = np.subtract(partial, conv_in_out)
            partial = np.subtract(partial, mcpdt)

            dtemp_in_dt = np.divide(partial, Ca)
            dtemp_in = np.multiply(dtemp_in_dt, increment )
            temp_in = np.add(temp_in, dtemp_in)

            # for material temp
            direct_heat = np.multiply(heat_all, (1 - air_part))
            conv_mat_in = np.multiply(np.subtract(temp_mat, temp_in), Um)
            partial_m = np.subtract(direct_heat, conv_mat_in)

            dtemp_mat_dt = np.divide(partial_m, Cm)
            dtemp_mat = np.multiply(dtemp_mat_dt, increment)
            temp_mat = np.add(temp_mat, dtemp_mat)

            count = count + increment
    
    temp_in_active = np.divide(temp_in, connected)
    
    return temp_in, temp_mat, temp_in_active, unixtime + count


@jit(nopython=True)
def enduse_storage(soc, power, capacity, step_size):
    # update soc
    return np.divide(np.add(np.multiply(power, step_size), np.multiply(soc, capacity)), capacity)  # soc


@jit(nopython=True)
def enduse_ev(soc, power, capacity, step_size):
    # update soc
    return np.divide(np.add(np.multiply(power, step_size), np.multiply(soc, capacity)), capacity)  # soc


@jit(nopython=True)
def enduse_ntcl(len_profile, counter, step_size):
    # update job status
    return np.divide(np.add(counter, step_size), len_profile)  # job_status


############# models for devices #######################################################
@jit(nopython=True)
def device_cooling(mode, temp_in, temp_min, temp_max, a_status, a_demand, cooling_setpoint, tolerance, cooling_power, cop, standby_power, ventilation_power):
    # device model for freezer, fridge, air condition
    p_status = ((((temp_in>=np.subtract(cooling_setpoint, tolerance)) & (a_status==1)) | ((temp_in>=np.add(cooling_setpoint, tolerance))&(a_status==0)))&(mode==0)) * 1
    return p_status, np.multiply(p_status, cooling_power), (((temp_max - temp_in) / (temp_max - temp_min)) * 100), np.multiply(np.multiply(cop, cooling_power), a_status)*((mode==0)*-1), np.add(np.add(np.multiply(a_status, cooling_power), standby_power), ventilation_power)*((mode==0)*1)
            # p_status, p_demand, priority, cooling_power_thermal, a_demand
        


@jit(nopython=True)
def device_heating(mode, temp_in, temp_min, temp_max, a_status, a_demand, heating_setpoint, tolerance, heating_power, cop, standby_power, ventilation_power):
    # device model for water heaters, electric heaters, etc.
    p_status = ((((temp_in<=np.add(heating_setpoint, tolerance))&(a_status==1)) |  ((temp_in<=np.subtract(heating_setpoint, tolerance))&(a_status==0)))&(mode==1)) * 1
    return p_status, np.multiply(p_status, heating_power), (((temp_in - temp_min) / (temp_max - temp_min)) * 100), np.multiply(np.multiply(cop, heating_power), a_status)*((mode==1)*1), np.add(np.add(np.multiply(a_status, heating_power), standby_power), ventilation_power)*((mode==1)*1)
        # p_status, p_demand, priority, heating_power_thermal, a_demand


@jit(nopython=True)
def device_tcl(mode, temp_in, temp_out, temp_min, temp_max, priority, a_status, a_demand, p_status, p_demand, 
    cooling_setpoint, heating_setpoint, tolerance, cooling_power, heating_power, cop, standby_power, ventilation_power,
    cooling_power_thermal, heating_power_thermal):
    # determine mode
    mode = (heating_setpoint > temp_out) * 1
    
    # set proposed demand
    c = device_cooling(mode=mode, temp_in=temp_in, temp_min=temp_min, temp_max=temp_max, 
        a_status=a_status, a_demand=a_demand, cooling_setpoint=cooling_setpoint, 
        tolerance=tolerance, cooling_power=cooling_power, cop=cop,
        standby_power=standby_power, ventilation_power=ventilation_power)


    h = device_heating(mode=mode, temp_in=temp_in, temp_min=temp_min, temp_max=temp_max, 
        a_status=a_status, a_demand=a_demand, heating_setpoint=heating_setpoint, 
        tolerance=tolerance, heating_power=heating_power, cop=cop, 
        standby_power=standby_power, ventilation_power=ventilation_power)

    p_status = np.add(c[0], h[0]) 
    p_demand = np.add(c[1], h[1]) 
    priority = np.add(c[2], h[2]) 
    heating_power_thermal = h[3]
    cooling_power_thermal = c[3]
    a_demand = np.add(c[4], h[4])

    return mode, p_status, p_demand, priority, cooling_power_thermal, heating_power_thermal, a_demand

@jit(nopython=True)
def device_ev(unixtime, unix_start, unix_end, soc_ev, charging_power, target_soc, capacity):
    '''
    Charging time for 100 km of BEV range   Power supply    power   Voltage     Max. current
    6–8 hours                               Single phase    3.3 kW  230 V AC        16 A
    3–4 hours                               Single phase    7.4 kW  230 V AC        32 A
    2–3 hours                               Three phase     11 kW   400 V AC        16 A
    1–2 hours                               Three phase     22 kW   400 V AC        32 A
    20–30 minutes                           Three phase     43 kW   400 V AC        63 A
    20–30 minutes                           Direct current  50 kW   400–500 V DC    100–125 A
    10 minutes                              Direct current  120 kW  300–500 V DC    300–350 A
    '''
    # get p_status
    p_status = ((unix_start<=unixtime) & (unix_end>=unixtime)) * 1
    # get p_demand
    p_demand = np.divide(charging_power, np.e**(np.multiply((soc_ev>=0.9)*1, np.subtract(np.multiply(soc_ev, 100), 90))))
    # predict finish
    p_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, soc_ev), capacity), charging_power))
    # # get priority
    priority = (np.divide(np.subtract(unix_end, p_finish), np.subtract(unix_end, unix_start))-0.1) * 100  # priority is lowered by 0.1 to charge EVs earlier
    
    return p_status, p_demand, p_finish, priority

@jit(nopython=True)
def device_storage(unixtime, unix_start, unix_end, soc_storage, charging_power, target_soc, capacity):
    # get p_status
    p_status = ((unix_start<=unixtime) & (unix_end>=unixtime)) * 1
    # get p_demand
    p_demand = np.divide(charging_power, np.e**(np.multiply((soc_ev>=0.9)*1, np.subtract(np.multiply(soc_ev, 100), 90))))
    # predict finish
    p_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, soc_ev), capacity), charging_power))
    # # get priority
    priority = (np.divide(np.subtract(unix_end, p_finish), np.subtract(unix_end, unix_start))-0.1) * 100  # priority is lowered by 0.1 to charge EVs earlier
    
    return p_status, p_demand, p_finish, priority







######## model for ldc #################
@jit(nopython=True)
def get_ldc_signal():
    return np.random.randint(0,100)

@jit(nopython=True)
def dongle(priority, signal, p_status):
    return np.multiply(p_status, (priority<=signal)*1)  # a_status

@jit(nopython=True)
def person(unixtime, load_type):
    unix_start = load_type * unixtime
    unix_end = np.add(unix_start, (24*3600))
    return unix_start, unix_end

@jit(nopython=True)
def is_connected(unixtime, unix_start, unix_end):
    return ((unix_start>=unixtime)&(unix_end>unixtime)) * 1

@jit(nopython=True)
def add_demands(baseload=0, heatpump=0, heater=0, waterheater=0, fridge=0, freezer=0, clotheswasher=0,
    clothesdryer=0, dishwasher=0, solar=0, wind=0):
    return np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(baseload, heatpump), heater), waterheater),
        fridge), freezer), clotheswasher), clothesdryer), dishwasher), solar), wind)


'''
@jit(nopython=True)
# def dongle_tcl(mode, temp_in, temp_min, temp_max, signal):
#     priority = mode
#     idx_0 = np.nonzero(mode==1)
#     idx_1 = np.nonzero(mode==0)

#     if len(idx_0): priority[idx_0] = (((temp_max[idx_0] - temp_in[idx_0]) / (temp_max[idx_0] - temp_min[idx_0])) * 100)

#     if len(idx_1): priority[idx_1] = (((temp_in[idx_1] - temp_min[idx_1]) / (temp_max[idx_1] - temp_min[idx_1])) * 100)

#     a_status = (priority <= signal) * 1

#     return priority, a_status  
''' 




# dt = 0
# for i in range(100000):
#     ### test
#     t = time.perf_counter()
    
#     for load_type in ['baseload', 'water_heater', 'electric_heater', 'water_heater', 'freezer', 'fridge', 'clothes_washer', 'clothes_dryer', 'dish_washer']:

#         x = clock(unixtime=state['unixtime'], timestamp=time.time(), real_time=True)
#         state.update({'unixtime':x[0], 'step_size':x[1]})

        
#         x = device_cooling(temp_in=state[load_type]['temp_in'], temp_min=state[load_type]['temp_min'], temp_max=state[load_type]['temp_max'], 
#             a_status=state[load_type]['a_status'], setpoint=state[load_type]['cooling_setpoint'], 
#             tolerance=state[load_type]['tolerance'], cooling_power=state[load_type]['cooling_power'])

#         state[load_type].update({'p_status': x[0], 'p_demand': x[1]})
        
#         x = device_heating(temp_in=state[load_type]['temp_in'], temp_min=state[load_type]['temp_min'], temp_max=state[load_type]['temp_max'], 
#             a_status=state[load_type]['a_status'], setpoint=state[load_type]['heating_setpoint'], 
#             tolerance=state[load_type]['tolerance'], heating_power=state[load_type]['heating_power'])

#         state[load_type].update({'p_status': x[0], 'p_demand': x[1]})

#         x = device_tcl(mode=state[load_type]['mode'], temp_in=state[load_type]['temp_in'], temp_min=state[load_type]['temp_min'], temp_max=state[load_type]['temp_max'],
#             priority=state[load_type]['priority'], temp_out=state[load_type]['temp_out'], a_status=state[load_type]['a_status'], p_status=state[load_type]['p_status'], 
#             p_demand=state[load_type]['p_demand'], cooling_setpoint=state[load_type]['cooling_setpoint'], heating_setpoint=state[load_type]['heating_setpoint'],
#             tolerance=state[load_type]['tolerance'], cooling_power=state[load_type]['cooling_power'], heating_power=state[load_type]['heating_power'])

#         state[load_type].update({'mode':x[0], 'p_status':x[1], 'p_demand':x[2], 'priority':x[3]})

#         x = device_ev(unixtime=state['unixtime'], unix_start=state[load_type]['unix_start'], 
#                 unix_end=state[load_type]['unix_end'], soc_ev=state[load_type]['soc_ev'], charging_power=state[load_type]['charging_power'],
#                 target_soc=state[load_type]['target_soc'], capacity=state[load_type]['capacity'])
        
#         state[load_type].update({'p_status':x[0], 'p_demand':x[1], 'p_finish':x[2], 'priority':x[3]})


#         x = dongle(priority=state[load_type]['priority'], signal=state[load_type]['ldc_signal'], p_demand=state[load_type]['p_demand'])

#         state[load_type].update({'a_status':x[0], 'a_demand':x[1]})

#         x = enduse_tcl(heat_all=state[load_type]['heat_all'],
#                 air_part=state[load_type]['air_part'],
#                 temp_in=state[load_type]['temp_in'],
#                 temp_mat=state[load_type]['temp_mat'],
#                 temp_out=state[load_type]['temp_out'],
#                 Um=state[load_type]['Um'],
#                 Ua=state[load_type]['Ua'],
#                 Cp=state[load_type]['Cp'],
#                 Ca=state[load_type]['Ca'],
#                 Cm=state[load_type]['Cm'],
#                 mass_flow=state[load_type]['mass_flow'],
#                 step_size=state['step_size'],
#                 connected=state[load_type]['connected'],
#                 temp_in_active=state[load_type]['temp_in_active'])
        
#         state[load_type].update({'temp_in': x[0], 'temp_mat': x[1], 'temp_in_active': x[2]})


#         x = enduse_storage(soc=state[load_type]['soc_storage'], power=state[load_type]['a_demand'], capacity=state[load_type]['capacity'], step_size=state['step_size']) 
#         state[load_type].update({'soc_storage': x})

#         x = enduse_ev(soc=state[load_type]['soc_ev'], power=state[load_type]['a_demand'], capacity=state[load_type]['capacity'], step_size=state['step_size']) 
#         state[load_type].update({'soc_ev': x})

#         x = enduse_ntcl(len_profile=state[load_type]['len_profile'], counter=state[load_type]['counter'], step_size=state['step_size']) 
#         state[load_type].update({'job_status': x})


#     dt = ((time.perf_counter()-t)*0.1) + (0.9*dt)
        
#     print(dt, state['unixtime'], state['step_size'], state[load_type]['temp_in'][0], state[load_type]['soc_ev'][0], state[load_type]['priority'][0], state[load_type]['a_status'][0])


























def simulate_model(**kwargs):
    ''' This is the model of the TCL system.
    This function solves the system dy/dt = f(y, t)
    the output is the updated value for Ta and Tm
    (see Munz et al. 2009)
    Input:
        temp_out = outside temperature
        temp_in = inside temperature of medium (e.g., air)
        temp_mat = inside temperature of materials
        Ua = coefficient of conduction between inside and outside
        Um = coefficient of conduction between inside air and material
        Ca = heat capacity of air
        Cm = heat capacity of materials
        heat = total heat injected in the air (Qex+Qin+heat_device)  [W or J/s]
        mass_flow = mass exchange between inner and outer environment [kg/s]
        step_size = time delta [s]
        Cp = heat capacity of mass flowing in and out of thermal zone [J/kgK]
        m = fraction of total heat (Qin, Qex, heat_device) that gets to the medium
    Output:
        temp_in = updated temperature of inside air
        temp_out = updated temperature of inside materials

    # dtemp_in_dt = ((m*heat_all)/Ca) + ((temp_mat-temp_in)*Um/Ca) + ((kwargs['temp_out']-temp_in)*Ua/Ca) - ((temp_in-kwargs['temp_out'])*mass_flow*Cp/Ca)
        
    '''
    
    
    try:
        # for TCLs
        kwargs.update(get_massflow(**kwargs))
        kwargs.update(get_irradiance(**kwargs))
        kwargs.update(heat_from_inside(**kwargs))
        kwargs.update(heat_from_outside(**kwargs))
        kwargs.update(heat_from_all(**kwargs))

        idx1 = np.flatnonzero((kwargs['load_class']=='tcl'))
        
        counter = 0
        inc = 1e-2
        

        # for battery
        work_start = np.add(kwargs['unix_end'], np.multiply(kwargs['trip_time'], 3600)).astype(int)
        work_end = np.subtract(kwargs['unix_start'], np.multiply(kwargs['trip_time'], 3600)).astype(int)

        idx_trip = np.flatnonzero(((kwargs['load_type']=='ev') & (kwargs['mode']==1) & (work_start>kwargs['unixtime']) & (kwargs['unix_end']<kwargs['unixtime'])) |  # traveling to work
                            ((kwargs['load_type']=='ev') & (kwargs['mode']==1) & (work_end<kwargs['unixtime']) & (kwargs['unix_start']>kwargs['unixtime']))  # traveling to home
                        )
        idx_work = np.flatnonzero((kwargs['load_type']=='ev') & (kwargs['mode']==1) & (work_start<=kwargs['unixtime']) & (work_end>=kwargs['unixtime']))
        
        # iii = np.flatnonzero(kwargs['load_type']=='ev')
        # print(pd.to_datetime(kwargs['unixtime'], unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%d %H:%M'), 
        #     "  power:", int(kwargs['power_battery'][iii][0]),
        #     "  n_usage", kwargs['n_usage'][iii][0],
        #     "  unix_end", pd.to_datetime(kwargs['unix_end'][iii][0], unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%d %H:%M'), 
        #     "  work_start", pd.to_datetime(work_start[iii][0], unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%d %H:%M'), 
        #     "  work_end", pd.to_datetime(work_end[iii][0], unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%d %H:%M'), 
        #     "  unix_start", pd.to_datetime(kwargs['unix_start'][iii][0], unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%d %H:%M') )

        idx2 = np.flatnonzero((kwargs['load_type']=='storage')&(kwargs['mode']==1))  # for storage discharging
        idx3 = np.flatnonzero((kwargs['load_class']=='battery')&(kwargs['mode']==0))  # for all batteries acting as a load
        
        # get power_battery for ev on travel
        if np.size(idx_trip):
            speed = np.random.normal(75, 5, np.size(idx_trip))/3600  #[km/s]
            distance = np.multiply(speed, kwargs['step_size'])  #[km]
            energy = np.divide(distance, kwargs['km_per_kwh'][idx_trip]) #[kwh]
            kwargs['power_battery'][idx_trip] = np.divide(np.multiply(energy,(1000*3600)), kwargs['step_size']) * np.random.choice(np.arange(-1.0, 0.1, 0.01))  # [w]
            # print('TRIP:')

        # get power_battery for ev at work
        if np.size(idx_work): 
            kwargs['power_battery'][idx_work] = kwargs['leakage'][idx_work] * -1 # EV standby, not connected
            # print('WORK:')

        # for storage discharging to the grid
        if np.size(idx2): kwargs['power_battery'][idx2] = np.multiply(kwargs['charging_efficiency'][idx2], kwargs['a_demand'][idx2]) * -1  # Storage discharging
        # for all batteries as a load
        if np.size(idx3): kwargs['power_battery'][idx3] = np.multiply(kwargs['charging_efficiency'][idx3], kwargs['a_demand'][idx3])  # all batteries acting as a load

        # adjust SOC for all batteries based on power_battery
        idx = np.flatnonzero((kwargs['load_class']=='battery'))
        if np.size(idx): 
            kwargs['soc'][idx] = np.clip(np.add(kwargs['soc'][idx], np.divide(np.multiply(kwargs['power_battery'][idx], kwargs['step_size']), kwargs['capacity'][idx])), a_min=0, a_max=1.0)
            
        
    except Exception as e:
        print("Error in COMMON simulate_model:", e)

    # # smooth the temperature update
    # w = 0.9 #np.random.choice(np.arange(0.1, 0.9, 0.01))  
    # temp_in = np.add(np.multiply(new_temp_in, w), np.multiply(temp_in, (1-w)))
    # temp_mat = np.add(np.multiply(new_temp_mat, w), np.multiply(temp_mat, (1-w)))
    
    return kwargs









# D = Dongle()

# x = 0
# y = 0

# for i in range(100000):
#     t = time.perf_counter()
#     signal = get_ldc_signal()
#     z = dongle(priority=state['priority'], signal=signal)
#     x = (x + time.perf_counter()-t) * 0.5

#     t= time.perf_counter()
#     # D.dongle()
#     z2 = dongle2(priority=state['priority'], signal=signal)
    
#     y = (y + time.perf_counter()-t) * 0.5

#     print(x, y)

#     print(z)
#     print(z2)






class Aggregator(object):
    """docstring for Aggregator"""
    def __init__(self, dict_devices, timestamp, latitude, longitude, idx, device_ip):
        super(Aggregator, self).__init__()
        
        self.dict_devices = dict_devices
        self.idx = idx
        self.house_num = idx + 1
        self.device_ip = device_ip

        if timestamp=='real_time':
            self.real_time = True
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
            self.real_time = False

        self.pause = 1e-6  # pause time used in thread interrupts

        ### common dictionary available in all threads
        manager = multiprocessing.Manager()
        self.dict_common = manager.dict()
        self.dict_house = manager.dict()
        self.dict_baseload = self.dict_house  # set another name for dict_house, refering to the same object
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
        self.dict_summary = manager.dict()
        self.dict_emulation_values = manager.dict()

        ### weather provider object
        self.weather = Weather(name='weather', latitude=latitude, longitude=longitude, timestamp=timestamp)
        self.df_history = pd.DataFrame([], columns=self.dict_devices.keys())

        ### for relay
        if self.device_ip in list(range(100, 150, 1)):
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BOARD)
            self.relay_status = 0
            self.relay_pin = 15
            GPIO.setup(self.relay_pin, GPIO.OUT)
            
            ### for reading ldc signal
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)  # (bus, device)
            self.spi.bits_per_word = 8
            self.spi.max_speed_hz = 500000
            self.spi.mode = 3
        
        ### for piface driver, in grainy load raspi3
        if self.device_ip==100:
            import pifacedigitalio
            self.pins = [0,0,0,0,0,0,0,0]
            self.pf = pifacedigitalio.PiFaceDigital()
        

        self.setup()
        # self.prerun()
        self.autorun()

        


    def setup(self):
        timestamp = self.timestamp
        dt = pd.to_datetime(timestamp, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
        self.dict_common.update({
            'unixtime':timestamp, 
            'step_size':1, 
            'yearweek': dt.week, 
            'weekday': dt.dayofweek, 
            'hour': dt.hour, 
            'minute': dt.minute, 
            'second':dt.second, 
            'microsecond': dt.microsecond, 
            'isotime': dt.isoformat(),
            'ldc_signal':100,
            'temp_out': 15,
            'humidity': 0.8,
            'windspeed': 3.0,
            })

        self.dict_emulation_values.update({'grainy_load':0, 'chroma_load':0})

        for load_type in self.dict_devices:
            n_devices = self.dict_devices[load_type]['n']
            if n_devices:   
                with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
                    df = store.select(load_type, where='index>={} and index<{}'.format(self.idx, self.idx+n_devices))
                    # df.index = df.name.values
                    
                if load_type=='heatpump':
                    for p in df.columns:
                        self.dict_heatpump.update({p:df[p].values})
                    self.dict_heatpump.update({'unixtime':timestamp})
                elif load_type=='heater':
                    for p in df.columns:
                        self.dict_heater.update({p:df[p].values})
                    self.dict_heater.update({'unixtime':timestamp})
                elif load_type=='waterheater':
                    for p in df.columns:
                        self.dict_waterheater.update({p:df[p].values})
                    self.dict_waterheater.update({'unixtime':timestamp})
                elif load_type=='freezer':
                    for p in df.columns:
                        self.dict_freezer.update({p:df[p].values})
                    self.dict_freezer.update({'unixtime':timestamp})
                elif load_type=='fridge':
                    for p in df.columns:
                        self.dict_fridge.update({p:df[p].values})
                    self.dict_fridge.update({'unixtime':timestamp})
                elif load_type=='clothesdryer':
                    for p in df.columns:
                        self.dict_clothesdryer.update({p:df[p].values})
                    self.dict_clothesdryer.update({'unixtime':timestamp})
                elif load_type=='clotheswasher':
                    for p in df.columns:
                        self.dict_clotheswasher.update({p:df[p].values})
                    self.dict_clotheswasher.update({'unixtime':timestamp})
                elif load_type=='dishwasher':
                    for p in df.columns:
                        self.dict_dishwasher.update({p:df[p].values})
                    self.dict_dishwasher.update({'unixtime':timestamp})
                elif load_type=='house':
                    for p in df.columns:
                        self.dict_house.update({p:df[p].values})
                    self.dict_house.update({'unixtime':timestamp})

                del df

                
                
    # def prerun(self):
    #     for load_type in self.dict_common.keys():
    #         if load_type in ['unixtime', 'step_size']: continue

    #         for p in self.dict_common[load_type].keys():
    #             self.dict_common[load_type][p] = np.array(self.dict_common[load_type][p])
    #             print(type(self.dict_common[load_type][p]))
            


    def autorun(self):
        # threads = [threading.Thread(target=self.mcast_listener, args=())]

        self.threads = [threading.Thread(target=self.common, args=())]
        # create separate threads for each type of appliance
        for k in self.dict_devices:
            if self.dict_devices[k]['n']:
                eval('self.threads.append(threading.Thread(target=self.{}, args=()))'.format(k))

        self.threads.append(threading.Thread(target=self.drive_piface, args=()))
        self.threads.append(threading.Thread(target=self.drive_chroma, args=()))
        self.threads.append(threading.Thread(target=self.history, args=()))
        # run threads
        for t in self.threads:
            t.daemon = True
            t.start()
            

    def history(self):
        while True:
            try:
                if self.dict_summary:
                    self.df_history = pd.DataFrame.from_dict(self.dict_summary, orient='index').transpose().fillna(0)
                    self.df_history['isotime'] = self.dict_common['isotime']
                    
                    if self.device_ip==100: 
                        print(self.dict_emulation_values)
                    else:
                        print(self.df_history)    
                        # print(self.dict_summary)

                    h = {'iso':self.dict_common['isotime'], 'common':self.dict_common['unixtime']}
                    for p in self.dict_summary.keys():
                        h.update({p:eval('self.dict_{}["unixtime"]'.format(p))})
                    # print(h)

                time.sleep(self.pause)
            except Exception as e:
                print(f'Error history:{e}')

    def common(self):
        while True:
            try:
                
                ### update clock
                self.dict_common = {**self.dict_common, **dict(zip(['unixtime', 'step_size', 'yearweek', 'weekday', 'hour', 'minute', 'second', 'microsecond', 'isotime'], 
                    clock(unixtime=self.dict_common['unixtime'], real_time=self.real_time, step_size=1)
                    ))}
                
                ### update weather
                self.dict_common = {**self.dict_common, **dict(zip(['temp_out', 'humidity', 'windspeed'], 
                    self.weather.get_weather(self.dict_common['unixtime'])
                    ))}
                
  
                time.sleep(self.pause)  # to give way to other threads
            except KeyboardInterrupt:
                break

            
        

    def mcast(self):
        pass

    def window(self):
        # opening and closing of windows
        return  # mass flow of air in the house

    def waterusage(self):
        # opening and closing of water valves
        return   # mass_flow of water heater

    def person(self):
        # presence of people
        return  # thermal heat and humidity 


    def house(self):
        from scipy.interpolate import interp1d
        self.dict_interpolator_house = {}
        validity_start = 0
        validity_end = 0

        while True:
            try:
                # t0 = time.perf_counter()
                ### convert unixtime to yearsecond
                
                self.dict_house = {**self.dict_house, **dict(zip(['unixtime','humidity','temp_out','windspeed', 'isotime'], 
                    [self.dict_common['unixtime'], self.dict_common['humidity'], 
                    self.dict_common['temp_out'],self.dict_common['windspeed'], self.dict_common['isotime']]
                    ))}

                 
                
                if (int(self.dict_house['unixtime'])>validity_end):
                    ### get baseload for current time
                    yearsecond = int(self.dict_house['unixtime'])%31536000
                    n_seconds = 3600                   
                    with pd.HDFStore('./profiles/baseload.h5', 'r') as store:
                        df = store.select('records', where='index>={} and index<{}'.format(int(yearsecond), int(yearsecond+(2*n_seconds))))
                        df.reset_index(drop=True, inplace=True)
                        df.index = np.add(df.index.values, int(self.dict_house['unixtime']))
                    validity_start = df.index.values[0]
                    validity_end = df.index.values[-int(n_seconds/2)]  # a buffer is added to catch up with the clock
                    
                    ### create an interpolator for each house baseload profile
                    for k in df.keys():
                        self.dict_interpolator_house[k] = interp1d(df.index.values, df[k].values)
                    del df  # release memory held by df
                
                ### update baseload
                self.dict_house = {**self.dict_house, **dict(zip(['a_demand'], 
                    [np.array([self.dict_interpolator_house[k](np.add(t, self.dict_house['unixtime'])) for k, t in zip(self.dict_house['profile'], self.dict_house['skew'])]).flatten()]
                    ))}

                ### update summary
                self.dict_summary = {**self.dict_summary, **dict(zip(['baseload'], 
                    [self.dict_house["a_demand"]]
                    ))}
        
                if (np.min(self.dict_house['a_demand']) < 0) or (np.max(self.dict_house['a_demand'])>15e3): raise Exception

                # print(time.perf_counter()-t0)
                time.sleep(self.pause)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print("Error house:", e)
                print(self.dict_house['a_demand'], validity_start, validity_end, self.dict_common['unixtime'])
                

    def heatpump(self):
        if self.device_ip==112:
            import SENSIBO
            self.sensibo_api = SENSIBO.SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
            devices = self.sensibo_api.devices()
            self.uid = devices['ldc_heatpump_h{}'.format(int(self.house_num))]
            
            self.dict_heatpump['temp_in'][0] = self.sensibo_api.pod_history(self.uid)['temperature'][-1]['value']
            self.dict_heatpump['temp_mat'][0] = self.dict_heatpump['temp_in'][0]

        while True:
            try:
                # t0 = time.perf_counter()

                if self.dict_common['unixtime']==self.dict_heatpump['unixtime']: 
                    time.sleep(self.pause)
                    continue  # skip all processes if time was not updated yet

                ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
                self.dict_heatpump['temp_out'] = (self.dict_heatpump['temp_out']**0) * self.dict_common['temp_out']

                # x = 
                # self.dict_heatpump.update({'mass_flow': x[0]})
                
                self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['unix_start', 'unix_end'], 
                    person(unixtime=self.dict_common['unixtime'],
                        load_type=(self.dict_heatpump['load_type']=='heatpump')*1)
                    ))}

                
                self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['connected'], 
                    [is_connected(unixtime=self.dict_common['unixtime'],
                        unix_start=self.dict_heatpump['unix_start'],
                        unix_end=self.dict_heatpump['unix_end'])]
                    ))}

                
                ### update device proposed mode, status, priority, and demand
                self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['mode', 'p_status', 'p_demand', 'priority',
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


                ### update dongle approval for the proposed status and demand
                self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['a_status'], 
                    [dongle(priority=self.dict_heatpump['priority'], 
                        signal=self.dict_common['ldc_signal'], 
                        p_status=self.dict_heatpump['p_status'])]
                    ))}

                ### update device states, e.g., temp_in, temp_mat, through simulation
                self.dict_heatpump = {**self.dict_heatpump, **dict(zip(['temp_in', 'temp_mat', 'temp_in_active', 'unixtime'], 
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
                        mass_flow= 1, #self.dict_heatpump['mass_flow'],
                        step_size=np.subtract(self.dict_common['unixtime'], self.dict_heatpump['unixtime']),
                        unixtime=self.dict_heatpump['unixtime'],
                        connected=self.dict_heatpump['connected'])
                    ))}
                
                ### update summary
                self.dict_summary = {**self.dict_summary, **dict(zip(['heatpump'], 
                        [self.dict_heatpump["a_demand"]]
                        ))}

                ### actual device
                if self.device_ip==112:
                    ### override simulated values with actual values 
                    self.dict_heatpump['temp_in'][0] = self.sensibo_api.pod_history(self.uid)['temperature'][-1]['value']
                    
                    ### get actual state of heat pump
                    self.ac_state = self.sensibo_api.pod_ac_state(self.uid)
                    
                    ### change status
                    if self.dict_heatpump['a_status'][0]==1 and self.ac_state['on']==False:
                        self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "on", True) 
                    elif self.dict_heatpump['a_status'][0]==0 and self.ac_state['on']==True:
                        self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "on", False)

                    ### change mode if needed
                    if self.dict_heatpump['mode'][0]==1 and self.ac_state['mode']=='cool':
                        self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "mode", 'heat')  # change to heating
                        self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "targetTemperature", self.dict_heatpump['heating_setpoint'][0])
                    elif self.dict_heatpump['mode'][0]==0 and self.ac_state['mode']=='heat':
                        self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "mode", 'cool')  # change to cooling
                        self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "targetTemperature", self.dict_heatpump['cooling_setpoint'][0])

                    ### drive on-board relay
                    if self.relay_status!=self.dict_heatpump['a_status'][0]:
                        GPIO.output(self.relay_pin, self.dict_heatpump['a_status'][0])
                        self.relay_status = self.dict_heatpump['a_status'][0]
                    

                # print(self.dict_common['isotime'], self.dict_heatpump['load_type'][-1], self.dict_heatpump['temp_in'][-1])
                # print(time.perf_counter()-t0)
                time.sleep(self.pause)  # to give way to other threads

            except KeyboardInterrupt:
                break

            except Exception as e:
                print(f'Error heatpump:{e}')


    def heater(self):
        while True:
            try:
                # t0 = time.perf_counter()

                if self.dict_common['unixtime']==self.dict_heater['unixtime']: 
                    time.sleep(self.pause)
                    continue  # skip all processes if time was not updated yet

                ### update required parameters, e.g.mass flow, unix_start, connected, etc.
                # self.dict_heater.update({'mass_flow': x[0]})

                self.dict_heater['temp_out'] = (self.dict_heater['temp_out']**0) * self.dict_common['temp_out']

                
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


                ### update dongle approval for the proposed status and demand
                self.dict_heater = {**self.dict_heater, **dict(zip(['a_status'], 
                    [dongle(priority=self.dict_heater['priority'], 
                        signal=self.dict_common['ldc_signal'], 
                        p_status=self.dict_heater['p_status'])]
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
                        mass_flow= 0.1, #self.dict_heater['mass_flow'],
                        step_size=np.subtract(self.dict_common['unixtime'], self.dict_heater['unixtime']),
                        unixtime=self.dict_heater['unixtime'],
                        connected=self.dict_heater['connected'])
                    ))}
                
                ### update summary
                self.dict_summary = {**self.dict_summary, **dict(zip(['heater'], 
                        [self.dict_heater["a_demand"]]
                        ))}
                


                ### override simulated values with actual values, i.e., for real loads such as heatpumps and water heaters

                # print(self.dict_common['isotime'], self.dict_heater['load_type'][-1], self.dict_heater['temp_in'][-1])
                # print(time.perf_counter()-t0)
                time.sleep(self.pause)  # to give way to other threads

            except KeyboardInterrupt:
                break

    def waterheater(self):
        while True:
            try:
                # t0 = time.perf_counter()

                if self.dict_common['unixtime']==self.dict_waterheater['unixtime']: 
                    time.sleep(self.pause)
                    continue  # skip all processes if time was not updated yet

                ### update required parameters, e.g.mass flow, unix_start, connected, etc.
                # self.dict_waterheater.update({'mass_flow': x[0]})

                self.dict_waterheater['temp_out'] = (self.dict_waterheater['temp_out']**0) * self.dict_common['temp_out']
                
                ### update device proposed mode, status, priority, and demand
                self.dict_waterheater = {**self.dict_waterheater, **dict(zip(['p_status', 'p_demand', 'priority',
                    'heating_power_thermal', 'a_demand'], 
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


                ### update dongle approval for the proposed status and demand
                self.dict_waterheater = {**self.dict_waterheater, **dict(zip(['a_status'], 
                    [dongle(priority=self.dict_waterheater['priority'], 
                        signal=self.dict_common['ldc_signal'], 
                        p_status=self.dict_waterheater['p_status'])]
                    ))}

                ### update device states, e.g., temp_in, temp_mat, through simulation
                self.dict_waterheater = {**self.dict_waterheater, **dict(zip(['temp_in', 'temp_mat', 'temp_in_active', 'unixtime'], 
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
                        mass_flow= 0.01, #self.dict_waterheater['mass_flow'],
                        step_size=np.subtract(self.dict_common['unixtime'], self.dict_waterheater['unixtime']),
                        unixtime=self.dict_waterheater['unixtime'],
                        connected=self.dict_waterheater['connected'])
                    ))}

                ### update summary
                self.dict_summary = {**self.dict_summary, **dict(zip(['waterheater'], 
                        [self.dict_waterheater["a_demand"]]
                        ))}
                
                ### override simulated values with actual values, i.e., for real loads such as heatpumps and water heaters
                ### drive on-board relay
                if self.device_ip==112:
                    if self.relay_status!=self.dict_heatpump['a_status'][0]:
                        GPIO.output(self.relay_pin, self.dict_heatpump['a_status'][0])
                        self.relay_status = self.dict_heatpump['a_status'][0]
                    

                # print(self.dict_common['isotime'],  self.dict_waterheater['load_type'][-1], self.dict_waterheater['temp_in'][-1])
                # print(time.perf_counter()-t0)
                time.sleep(self.pause)  # to give way to other threads

            except KeyboardInterrupt:
                break
        

    def fridge(self):
        while True:
            try:
                # t0 = time.perf_counter()

                if self.dict_common['unixtime']==self.dict_fridge['unixtime']: 
                    time.sleep(self.pause)
                    continue  # skip all processes if time was not updated yet

                ### update required parameters, e.g.mass flow, unix_start, connected, etc.
                # self.dict_fridge.update({'mass_flow': x[0]})

                
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

                ### update dongle approval for the proposed status and demand
                self.dict_fridge = {**self.dict_fridge, **dict(zip(['a_status'], 
                    [dongle(priority=self.dict_fridge['priority'], 
                        signal=self.dict_common['ldc_signal'], 
                        p_status=self.dict_fridge['p_status'])]
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
                        step_size=np.subtract(self.dict_common['unixtime'], self.dict_fridge['unixtime']),
                        unixtime=self.dict_fridge['unixtime'],
                        connected=self.dict_fridge['connected'])
                    ))}
                

                ### update summary
                self.dict_summary = {**self.dict_summary, **dict(zip(['fridge'], 
                        [self.dict_fridge["a_demand"]]
                        ))}

                ### override simulated values with actual values (if applicable), i.e., for real loads such as heatpumps and water heaters at Ardmore
                # print(self.dict_common['isotime'],  self.dict_fridge['load_type'][-1], self.dict_fridge['temp_in'][-1])
                # print(time.perf_counter()-t0)
                time.sleep(self.pause)  # to give way to other threads

            except KeyboardInterrupt:
                break
        

    def freezer(self):
        while True:
            try:
                # t0 = time.perf_counter()

                if self.dict_common['unixtime']==self.dict_freezer['unixtime']: 
                    time.sleep(self.pause)
                    continue  # skip all processes if time was not updated yet

                ### update required parameters, e.g.mass flow, unix_start, connected, etc.
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

                ### update dongle approval for the proposed status and demand
                self.dict_freezer = {**self.dict_freezer, **dict(zip(['a_status'], 
                    [dongle(priority=self.dict_freezer['priority'], 
                        signal=self.dict_common['ldc_signal'], 
                        p_status=self.dict_freezer['p_status'])]
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
                        step_size=np.subtract(self.dict_common['unixtime'], self.dict_freezer['unixtime']),
                        unixtime=self.dict_freezer['unixtime'],
                        connected=self.dict_freezer['connected'])
                    ))}
                

                ### update summary
                self.dict_summary = {**self.dict_summary, **dict(zip(['freezer'], 
                        [self.dict_freezer["a_demand"]]
                        ))}

                ### override simulated values with actual values (if applicable), i.e., for real loads such as heatpumps and water heaters at Ardmore

                # print(self.dict_common['isotime'],  self.dict_freezer['load_type'][-1], self.dict_freezer['temp_in'][-1])
                # print(time.perf_counter()-t0)

                time.sleep(self.pause)  # to give way to other threads
            except KeyboardInterrupt:
                break

    def clotheswasher(self):
        from scipy.interpolate import interp1d
        import json
        ### setup the profiles
        try:
            self.dict_interpolator_clotheswasher = {}
            with open('./profiles/nntcl.json') as f:
                nntcl = json.load(f)
            
            dict_data = nntcl['Clotheswasher']
            for k in dict_data.keys():
                self.dict_interpolator_clotheswasher[k] = interp1d(np.arange(len(dict_data[k])), dict_data[k])
            
            del nntcl, dict_data  # free up the memory
        
        except Exception as e:
            print(f'Error clotheswasher setup:{e}')

        ### run profiles
        while True:
            try:
                # if self.dict_common['unixtime']==self.dict_clotheswasher['unixtime']: 
                #     time.sleep(self.pause)
                #     continue  # skip all processes if time was not updated yet

                # ### update environment models, e.g., air change, water usage, mass_flow, connected, etc.
                # self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['unix_start', 'unix_end'], 
                #     person(unixtime=self.dict_common['unixtime'],
                #         load_type=(self.dict_clotheswasher['load_type']=='clotheswasher')*1)
                #     ))}

                # self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['connected'], 
                #     is_connected(unixtime=self.dict_common['unixtime'],
                #         unix_start=self.dict_clotheswasher['unix_start'],
                #         unix_end=self.dict_clotheswasher['unix_end'])
                #     ))}

                # ### update device proposed mode, status, priority, and demand
                # self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['p_status', 'p_demand', 'priority', 
                #     'cooling_power_thermal'], 
                    

                #     ))}

                # ### update dongle approval for the proposed status and demand
                # self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['a_status', 'a_demand'], 
                #     dongle(priority=self.dict_clotheswasher['priority'], 
                #         signal=self.dict_common['ldc_signal'], 
                #         p_status=self.dict_clotheswasher['p_status'],
                #         p_demand=self.dict_clotheswasher['p_demand'],
                #         standby_power=self.dict_clotheswasher['standby_power'],
                #         ventilation_power=self.dict_clotheswasher['ventilation_power'])
                #     ))}

                # ### update device states, e.g., temp_in, temp_mat, through simulation
                # self.dict_clotheswasher = {**self.dict_clotheswasher, **dict(zip(['temp_in', 'temp_mat', 'temp_in_active', 'unixtime'], 
                #     enduse_tcl(heat_all=self.dict_clotheswasher['cooling_power_thermal'],
                #         air_part=self.dict_clotheswasher['air_part'],
                #         temp_in=self.dict_clotheswasher['temp_in'],
                #         temp_mat=self.dict_clotheswasher['temp_mat'],
                #         temp_out=self.dict_clotheswasher['temp_out'],
                #         Um=self.dict_clotheswasher['Um'],
                #         Ua=self.dict_clotheswasher['Ua'],
                #         Cp=self.dict_clotheswasher['Cp'],
                #         Ca=self.dict_clotheswasher['Ca'],
                #         Cm=self.dict_clotheswasher['Cm'],
                #         mass_flow= 0.001, #self.dict_clotheswasher['mass_flow'],
                #         step_size=np.subtract(self.dict_common['unixtime'], self.dict_clotheswasher['unixtime']),
                #         unixtime=self.dict_clotheswasher['unixtime'],
                #         connected=self.dict_clotheswasher['connected'])
                #     ))}
                

                # ### update summary
                # self.dict_summary = {**self.dict_summary, **dict(zip(['freezer'], 
                #         [self.dict_clotheswasher["a_demand"]]
                #         ))}



                time.sleep(self.pause)
            except Exception as e:
                print(f'Error clotheswasher run:{e}')


    def clothesdryer(self):

        pass
        # with open('./profiles/nntcl.json') as f:
        #     nntcl = json.load(f)
        #     list_clothesdryer = list(nntcl['Clothesdryer'])
        #     list_clotheswasher = list(nntcl['Clotheswasher'])
        #     list_dishwasher = list(nntcl['Dishwasher'])
        
        # dict_clotheswasher = nntcl['Clotheswasher']
        # dict_clothesdryer = nntcl['Clothesdryer']
        # dict_dishwasher = nntcl['Dishwasher']

        # df_clotheswasher = pd.DataFrame.from_dict(dict_clotheswasher, orient='index').transpose().fillna(0)
        # df_clothesdryer = pd.DataFrame.from_dict(dict_clothesdryer, orient='index').transpose().fillna(0)
        # df_dishwasher = pd.DataFrame.from_dict(dict_dishwasher, orient='index').transpose().fillna(0)


    def dishwasher(self):
        from scipy.interpolate import interp1d
        import json
        ### setup the profiles
        try:
            self.dict_interpolator_dishwasher = {}
            with open('./profiles/nntcl.json') as f:
                nntcl = json.load(f)
            
            dict_data = nntcl['Dishwasher']
            for k in dict_data.keys():
                self.dict_interpolator_dishwasher[k] = interp1d(np.arange(len(dict_data[k])), dict_data[k])
            
            del nntcl, dict_data
            
        except Exception as e:
            print(f'Error dishwasher setup:{e}')

        ### run the profiles
        while True:
            try:
                time.sleep(self.pause)
            except Exception as e:
                print(f'Error dishwasher run')


    def ev(self):
        pass

    def storage(self):
        pass

    def solar(self):
        import solar
        last_unixtime = self.dict_common['unixtime']
        while True:
            try:
                if last_unixtime==self.dict_house['unixtime']: 
                    time.sleep(self.pause)
                    continue

                self.dict_house['irradiance_roof'] = solar.get_irradiance(
                                                unixtime=self.dict_house['unixtime'],
                                                humidity=self.dict_house['humidity'],
                                                latitude=self.dict_house['latitude'],
                                                longitude=self.dict_house['longitude'],
                                                elevation=self.dict_house['elevation'],
                                                tilt=self.dict_house['roof_tilt'],
                                                azimuth=self.dict_house['azimuth'],
                                                albedo=self.dict_house['albedo'],
                                                isotime=self.dict_house['isotime']
                                            )
                self.dict_house['irradiance_wall1'] = solar.get_irradiance(
                                                unixtime=self.dict_house['unixtime'],
                                                humidity=self.dict_house['humidity'],
                                                latitude=self.dict_house['latitude'],
                                                longitude=self.dict_house['longitude'],
                                                elevation=self.dict_house['elevation'],
                                                tilt=np.ones(len(self.dict_house['azimuth']))*90,
                                                azimuth=self.dict_house['azimuth'],
                                                albedo=self.dict_house['albedo'],
                                                isotime=self.dict_house['isotime']
                                            )
                self.dict_house['irradiance_wall2'] = solar.get_irradiance(
                                                unixtime=self.dict_house['unixtime'],
                                                humidity=self.dict_house['humidity'],
                                                latitude=self.dict_house['latitude'],
                                                longitude=self.dict_house['longitude'],
                                                elevation=self.dict_house['elevation'],
                                                tilt=np.ones(len(self.dict_house['azimuth']))*90,
                                                azimuth=self.dict_house['azimuth']+90,
                                                albedo=self.dict_house['albedo'],
                                                isotime=self.dict_house['isotime']
                                            )
                self.dict_house['irradiance_wall3'] = solar.get_irradiance(
                                                unixtime=self.dict_house['unixtime'],
                                                humidity=self.dict_house['humidity'],
                                                latitude=self.dict_house['latitude'],
                                                longitude=self.dict_house['longitude'],
                                                elevation=self.dict_house['elevation'],
                                                tilt=np.ones(len(self.dict_house['azimuth']))*90,
                                                azimuth=self.dict_house['azimuth']-90,
                                                albedo=self.dict_house['albedo'],
                                                isotime=self.dict_house['isotime']
                                            )
                self.dict_house['irradiance_wall4'] = solar.get_irradiance(
                                                unixtime=self.dict_house['unixtime'],
                                                humidity=self.dict_house['humidity'],
                                                latitude=self.dict_house['latitude'],
                                                longitude=self.dict_house['longitude'],
                                                elevation=self.dict_house['elevation'],
                                                tilt=np.ones(len(self.dict_house['azimuth']))*90,
                                                azimuth=self.dict_house['azimuth']+180,
                                                albedo=self.dict_house['albedo'],
                                                isotime=self.dict_house['isotime']
                                            )
                # print(self.dict_house['isotime'], self.dict_house['irradiance_roof'], self.dict_house['humidity'])
                last_unixtime = self.dict_house['unixtime']
                time.sleep(self.pause)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f'Error solar:{e}')

    def wind(self):
        pass


    def drive_chroma(self):
        # Send data to Chroma variable load simulator
        # through serial interface (rs232)
        try:
            rs232 = None

            try:
                import serial

                rs232 = serial.Serial(
                            port='/dev/ttyUSB0',
                            baudrate = 57600,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            bytesize=serial.EIGHTBITS,
                            timeout=1
                            )
            except Exception as e:
                print("Error drive_chroma setup:", e)

            while True:
                try:
                    if rs232 != None:
                        if self.dict_emulation_values['chroma_load']<=0:
                            rs232.write(b'LOAD OFF\r\n')
                        else:    
                            rs232.write(b'CURR:PEAK:MAX 28\r\n')
                            rs232.write(b'MODE POW\r\n')
                            cmd = 'POW '+ str(self.dict_emulation_values['chroma_load']) +'\r\n'
                            rs232.write(cmd.encode())
                            rs232.write(b'LOAD ON\r\n')

                    time.sleep(self.pause)
                except KeyboardInterrupt:
                    break

                except Exception as e:
                    print("Error drive_chroma:", e)
        finally:
            print("serial aborted...")
            # rs232.write(b'LOAD OFF\r\n')
        

    def drive_piface(self):
        # initialization to drive the pifacedigital
        try:
            self.df_relay, self.df_states = FUNCTIONS.create_states(report=False)  # create power levels based on resistor bank

            if self.device_ip==100:
                while True:
                    try:
                        ### add all demand
                        total = 0.0
                        for p in self.dict_summary.keys():
                            total = np.add(np.sum(self.dict_summary[p]), total)

                        total = min([total, 14e3])

                        # print(self.dict_common['isotime'], self.dict_summary)  

                        # if self.dict_heatpump: print(self.dict_common['unixtime'], self.dict_heatpump['unixtime'], self.dict_heatpump['heating_power'], 
                        #     self.dict_heatpump['p_status'],self.dict_heatpump['a_status'], self.dict_heatpump['priority'], self.dict_heatpump['heating_power_thermal'],
                        #     self.dict_heatpump['temp_in'],self.dict_heatpump['a_demand'])                  
                        
                        ### convert baseload value into 8-bit binary to drive 8 pinouts of piface
                        # newpins, grainy, chroma = FUNCTIONS.relay_pinouts(total, self.df_relay, self.df_states, report=False)
                        newpins, grainy, chroma = FUNCTIONS.pinouts(total, self.df_states, report=False)
                        
                        
                        for i in range(len(self.pins)):
                            if self.pins[i]==0 and newpins[i]==1:
                                self.pf.output_pins[i].turn_on()
                            elif self.pins[i]==1 and newpins[i]==0:
                                self.pf.output_pins[i].turn_off()
                            else:
                                pass
                        self.pins = newpins
                    

                        ### update grainy_load
                        self.dict_emulation_values = {**self.dict_emulation_values, **dict(zip(['grainy_load'], 
                                [grainy]
                                ))}
                        ### update chroma load
                        self.dict_emulation_values = {**self.dict_emulation_values, **dict(zip(['chroma_load'], 
                            [chroma]
                            ))}

                        # print(total, self.dict_common['isotime'], self.dict_emulation_values)
                        time.sleep(self.pause)
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        print("Error drive_piface:", e)
        finally:
            print("piface aborted...")
            
    def __del__(self):
        if self.device_ip in list(range(100, 150)):
            GPIO.cleanup()         # clean up the GPIO to reset mode
            for i in range(len(self.pins)):
                self.pf.output_pins[i].turn_off()


if __name__ == '__main__':
    
    local_ip = FUNCTIONS.get_local_ip(report=True)
    start_idx = int(local_ip.split('.')[2]) - 1
    device_ip = int(local_ip.split('.')[3])
    ldc_adoption = 0.0
    n = 1
    grid_capacity = n * 5000
    target_loading = 0.5

    
    
    latitude = '-36.866590076725494'
    longitude = '174.77534779638677'
    start = 'real_time'
    
    # define the number of devices to run
    if device_ip=='100':
        dict_devices = {
            'house':{'n':int(n*1), 'ldc':ldc_adoption},
            'heatpump':{'n':int(n*1), 'ldc':ldc_adoption},
            'heater':{'n':int(n*1), 'ldc':ldc_adoption},
            'fridge':{'n':int(n*1.5), 'ldc':ldc_adoption},
            'freezer':{'n':int(n*1), 'ldc':ldc_adoption},
            'waterheater':{'n':int(n*1), 'ldc':ldc_adoption},
            'clotheswasher':{'n':int(n*1), 'ldc':ldc_adoption},
            'clothesdryer':{'n':int(n*1), 'ldc':ldc_adoption},
            'dishwasher':{'n':int(n*1), 'ldc':ldc_adoption},
            'ev':{'n':int(n*1), 'ldc':ldc_adoption, 'v2g':int(n*0.0)},
            'storage':{'n':int(n*1), 'ldc':ldc_adoption},
            'solar':{'n':int(n*1), 'ldc':ldc_adoption},
            'wind':{'n':int(n*1), 'ldc':ldc_adoption},    
            }
    if device_ip==101:
        dict_devices = {
            }
    elif device_ip==102:
        dict_devices = {
            'house':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    elif device_ip==103:
        dict_devices = {
            'heater':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    elif device_ip==104:
        dict_devices = {
            'dishwasher':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    elif device_ip==105:
        dict_devices = {
            'clothesdryer':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    elif device_ip==106:
        dict_devices = {
            'clotheswasher':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    elif device_ip==107:
        dict_devices = {
            'storage':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    elif device_ip==108:
        dict_devices = {
            'ev':{'n':int(n*1), 'ldc':ldc_adoption, 'v2g':int(n*0.0)},
            }
    elif device_ip==109:
        dict_devices = {
            'fridge':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    elif device_ip==110:
        dict_devices = {
            'freezer':{'n':int(n*1), 'ldc':ldc_adoption},
            }
            
    elif device_ip==111:
        dict_devices = {
            'heatpump':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    elif device_ip==112:
        dict_devices = {
            'waterheater':{'n':int(n*1), 'ldc':ldc_adoption},
            }
    else:
        n = 5
        dict_devices = {
            'house':{'n':int(n*1), 'ldc':ldc_adoption},
            'heatpump':{'n':int(n*1), 'ldc':ldc_adoption},
            'heater':{'n':int(n*1), 'ldc':ldc_adoption},
            'fridge':{'n':int(n*1.5), 'ldc':ldc_adoption},
            'freezer':{'n':int(n*1), 'ldc':ldc_adoption},
            'waterheater':{'n':int(n*1), 'ldc':ldc_adoption},
            'clotheswasher':{'n':int(n*1), 'ldc':ldc_adoption},
            'clothesdryer':{'n':int(n*1), 'ldc':ldc_adoption},
            'dishwasher':{'n':int(n*1), 'ldc':ldc_adoption},
            'ev':{'n':int(n*1), 'ldc':ldc_adoption, 'v2g':int(n*0.0)},
            'storage':{'n':int(n*1), 'ldc':ldc_adoption},
            'solar':{'n':int(n*1), 'ldc':ldc_adoption},
            'wind':{'n':int(n*1), 'ldc':ldc_adoption},    
            }

        dt_start = datetime.datetime(2018, 1, 1, 6, 0, 0)
        start = time.mktime(dt_start.timetuple())
    
    
    
    
    
    
    
    
    
    

    A = Aggregator(dict_devices, timestamp=start, latitude=latitude, longitude=longitude, idx=start_idx, device_ip=device_ip)

    while True:
        try:
            # print(A.dict_summary)
            time.sleep(1)
        except KeyboardInterrupt:
            break


