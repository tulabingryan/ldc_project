"""
./TCL.py 
Module for Thermostaticaly Controlled Load model
Author: Ryan Tulabing
Project: Local Demand Control
Institution: University of Auckland
Year: 2017 - 2020
"""

#---import python packages---
import numpy as np
# from numba import vectorize, jit
import solar
import pandas as pd
import datetime, time
# import threading, queue
# import multiprocessing


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

# # for multicast
# import socket
# import struct
# import sys
# import json
# import ast


# #---import local modules---
# import HOUSE
# import MULTICAST
# import TCL
# import CLOCK
# import FUNCTIONS

from CREATOR import df_clotheswasher, df_clothesdryer, df_dishwasher


def read_csv(filename):
    # Continually try reading csv until successful
    try:
        df = pd.read_csv(filename, index_col='id')
        failed = False
    except Exception as e:
        print("Error TCL read_csv:",e)
    return df


def delete_past(dict_holder, latest=60):
    # delete the data older than latest seconds
    dict_local = {}
    for key in list(dict_holder):
        if dict_holder[key]['unixtime'] > (time.time() - latest):
            dict_local.update({key:dict_holder[key]})
        else:
            pass
    return dict_local


# def get_queue(q):
#     data = q.get()
#     q.task_done()
#     if q.empty(): q.put(data)
#     return data

# def put_queue(q, name, dict_data):
#     if dict_data['name']==_id:
#         q.put(dict_data)
#     return q



def to_yearsecond(start, duration=1):
    '''
    Convert timestamp to yearsecond
    '''
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

    if duration==1:
        return df_datetime['yearsecond'].values[0]
    else:    
        return df_datetime['yearsecond'].values[0], df_datetime['yearsecond'].values[-1]

def get_baseloads(start, duration=3600, padding=1800):
    '''
    Get the baseloads from './profiles/baseload.h5' and return a dataframe
    '''
    x, y = to_yearsecond(start, duration)
    with pd.HDFStore('./profiles/baseload.h5', 'r') as store:
        df = store.select('records', where='index>={} and index<={}'.format(x - padding, y + padding))
    return df
    


###########################################
def get_n_usage(**kwargs):
    # adjust number of usage based on job_status
    try:
        idx = np.flatnonzero(((kwargs['load_type']!='ev')&(kwargs['unix_end']<=kwargs['unixtime'])) |
            ((kwargs['load_type']=='ev')&(np.add(kwargs['unix_end'], kwargs['trip_time']*3600)<=kwargs['unixtime'])&(kwargs['unix_start']<=kwargs['unix_end']))
            )
        
        if np.size(idx): 
            kwargs['n_usage'][idx] = np.add(kwargs['n_usage'][idx], 1)
            kwargs['counter'][idx] = 0
              
    except Exception as e:
        print("Error get_n_usage:", e)

    return kwargs




def get_hour(**kwargs):
    # get hour_start and hour_end based on the schedule lists
    try:
        if kwargs['unix_start'][0]==0:
            idx = np.flatnonzero(((np.isin(kwargs['load_class'], ['tcl', 'ntcl', 'battery', 'der']))))  
            if np.size(idx):
                kwargs['hour_start'][idx] = kwargs['params']['list_starts'][idx, np.remainder(kwargs['n_usage'][idx], 10)] 
                kwargs['hour_end'][idx] = kwargs['params']['list_ends'][idx, np.remainder(kwargs['n_usage'][idx], 10)]
        else:
            idx1 = np.flatnonzero(kwargs['unixtime'] > kwargs['unix_start'])
            idx2 = np.flatnonzero(kwargs['unixtime'] > kwargs['unix_end'])

            if np.size(idx1):
                # change hour_end
                kwargs['hour_end'][idx1] = kwargs['params']['list_ends'][idx1, np.remainder(kwargs['n_usage'][idx1], 10)]   
            if np.size(idx2):
                # change hour_start
                kwargs['hour_start'][idx2] = kwargs['params']['list_starts'][idx2, np.remainder(kwargs['n_usage'][idx2], 10)] 

    except Exception as e:
        print("Error TCL get_hour:", e)
        
    return kwargs




def get_unix(**kwargs):
    # convert hour to unix
    try:
        # normal: hour_end > hour_start
        if kwargs['unix_start'][0]==0:
            idx01 = np.flatnonzero(((kwargs['load_type']!='ev')&(kwargs['hour_end']>kwargs['hour_start'])&(kwargs['unix_end']<=kwargs['unixtime'])) |
                ((kwargs['load_type']=='ev')&(kwargs['hour_end']>kwargs['hour_start'])&(np.add(kwargs['unix_end'], kwargs['trip_time']*3600) < kwargs['unixtime']))
                )
            # not normal: hour_end < hour_start, and current dayhour > hour_end
            idx02 = np.flatnonzero(((kwargs['load_type']!='ev')&(kwargs['hour_end']<=kwargs['hour_start'])&(kwargs['unix_end']<=kwargs['unixtime'])) |
                ((kwargs['load_type']=='ev')&(kwargs['hour_end']<=kwargs['hour_start'])&((kwargs['unix_start']==0)|(kwargs['hour_end']<=kwargs['dayhour']))&(np.add(kwargs['unix_end'], kwargs['trip_time']*3600) < kwargs['unixtime']))
                )
            # # not normal: hour_end < hour_start, and current dayhour < hour_end
            # idx03 = np.flatnonzero(((kwargs['load_class']!='ntcl')&(kwargs['load_type']!='ev')&(kwargs['hour_end']<=kwargs['hour_start'])&(kwargs['unix_end']>kwargs['unixtime'])) |
            #     ((kwargs['load_type']=='ev')&(kwargs['hour_end']<=kwargs['hour_start'])&(kwargs['hour_end']>kwargs['dayhour'])&(np.add(kwargs['unix_end'], kwargs['trip_time']*3600) < kwargs['unixtime']))
            #     )
            

            if np.size(idx01): 
                kwargs['unix_start'][idx01] = np.add(np.dot(kwargs['hour_start'][idx01], 3600), (kwargs['unixtime'] - kwargs['daysecond']))
                kwargs['unix_end'][idx01] = np.add(np.dot(kwargs['hour_end'][idx01], 3600), (kwargs['unixtime'] - kwargs['daysecond']))

            if np.size(idx02): 
                kwargs['unix_start'][idx02] = np.add(np.dot(kwargs['hour_start'][idx02], 3600), (kwargs['unixtime'] - kwargs['daysecond']))
                kwargs['unix_end'][idx02] = np.add(np.add(np.dot(kwargs['hour_end'][idx02], 3600), (3600 * 24 * 0)), (kwargs['unixtime'] - kwargs['daysecond']))
            
            # if np.size(idx03): 
            #     kwargs['unix_start'][idx03] = np.add(np.dot(kwargs['hour_start'][idx03], 3600), (kwargs['unixtime'] - kwargs['daysecond']) - (3600*24))
            #     kwargs['unix_end'][idx03] = np.add(np.dot(kwargs['hour_end'][idx03], 3600), (kwargs['unixtime'] - kwargs['daysecond']))

            # idx = np.flatnonzero((kwargs['unix_end']<kwargs['unixtime']))
            # if np.size(idx): 
            #     kwargs['unix_start'][idx] = kwargs['unix_start'][idx] + (3600*24)
            #     kwargs['unix_end'][idx] = kwargs['unix_end'][idx] + (3600*24) 

        else:
            ### normal: hour_end > hour_start 
            idx11 = np.flatnonzero(((kwargs['load_type']!='ev')&(kwargs['unixtime'] >= kwargs['unix_start'])))
            if np.size(idx11): 
                kwargs['unix_end'][idx11] = np.add(np.dot(kwargs['hour_end'][idx11], 3600), (kwargs['unixtime'] - kwargs['daysecond']))

            ### not normal: hour_end < hour_start
            idx12 = np.flatnonzero(((kwargs['unixtime'] >= kwargs['unix_start'])&(kwargs['unix_end']<=kwargs['unix_start']))
                )
            if np.size(idx12): 
                kwargs['unix_end'][idx12] = np.add(np.add(np.dot(kwargs['hour_end'][idx12], 3600), (3600 * 24)), (kwargs['unixtime'] - kwargs['daysecond']))

            idx21 = np.flatnonzero(((kwargs['load_type']!='ev')&(kwargs['unixtime'] >= kwargs['unix_end'])) 
                # ((kwargs['unixtime'] > kwargs['unix_end'])&(kwargs['load_type']=='ev')&(kwargs['hour_end']>kwargs['hour_start'])&(np.add(kwargs['unix_end'], kwargs['trip_time']*3600) < kwargs['unixtime']))
                )
            if np.size(idx21): 
                kwargs['unix_start'][idx21] = np.add(np.dot(kwargs['hour_start'][idx21], 3600), (kwargs['unixtime'] - kwargs['daysecond']))

            ### not normal: hour_end < hour_start, and current dayhour > hour_end
            idx22 = np.flatnonzero(((kwargs['load_type']!='ev')&(kwargs['unixtime'] >= kwargs['unix_end'])&(kwargs['unix_start']<=kwargs['unix_end'])) |
                ((kwargs['load_type']=='ev')&(kwargs['unixtime'] >= np.add(kwargs['unix_end'], kwargs['trip_time']*3600)))
                )
            if np.size(idx22): 
                kwargs['unix_start'][idx22] = np.add(np.dot(kwargs['hour_start'][idx22], 3600), (kwargs['unixtime'] - kwargs['daysecond']))
            # # not normal: hour_end < hour_start, and current dayhour < hour_end
            # idx03 = np.flatnonzero(((kwargs['load_class']!='ntcl')&(kwargs['load_type']!='ev')&(kwargs['hour_end']<=kwargs['hour_start'])&(kwargs['unix_end']>kwargs['unixtime'])) |
            #     ((kwargs['load_type']=='ev')&(kwargs['hour_end']<=kwargs['hour_start'])&(kwargs['hour_end']>kwargs['dayhour'])&(np.add(kwargs['unix_end'], kwargs['trip_time']*3600) < kwargs['unixtime']))
            #     )

            

            
        
            
                
            
                
    except Exception as e:
        print("Error get_unix:", e)

        

    return kwargs






def is_connected(**kwargs):
    # determin if a load is connected based on users schedule
    try:
        idx = np.flatnonzero((kwargs['unix_start']<=kwargs['unixtime']) & (kwargs['unixtime']<=kwargs['unix_end']))
        idx_der = np.flatnonzero(kwargs['load_class']=='der')
        n_idx = np.flatnonzero((kwargs['unix_start']>kwargs['unixtime']) | (kwargs['unixtime'] > kwargs['unix_end']))

        if np.size(idx): kwargs['connected'][idx] = 1
        if np.size(n_idx): kwargs['connected'][n_idx] = 0
        # if np.size(idx_der): kwargs['connected'][idx_der] = 1

    except Exception as e:
        print("Error is_connected:", e)
    return kwargs



def predict_finish(**kwargs):
    try:
        idx1 = np.flatnonzero((kwargs['load_class']=='ntcl'))
        idx2 = np.flatnonzero((kwargs['load_class']=='battery'))

        if np.size(idx1): kwargs['finish'][idx1] = np.add(np.subtract(kwargs['len_profile'][idx1], kwargs['counter'][idx1]), kwargs['unixtime'])
        if np.size(idx2): kwargs['finish'][idx2] = np.add(kwargs['unixtime'], np.divide(np.multiply(np.subtract(kwargs['target_soc'][idx2], kwargs['soc'][idx2]), kwargs['capacity'][idx2]), (kwargs['charging_power'][idx2])))

    except Exception as e:
        print("Error predict_finish:", e)
    return kwargs




def get_flexibility(**kwargs):
    # This function calculates the flexibility of TCL
    try:
        kwargs.update(predict_finish(**kwargs))  # predict finish for NTCL and EVs

        idx1 = np.flatnonzero(((kwargs['cooling_counter']<=kwargs['min_coolingtime'])) |  # TCL, still uninterruptible
                        ((kwargs['can_shed']==0)&(kwargs['can_ramp']==0)) |  # TCL can't shed, cant'ramp
                        ((kwargs['load_class']=='ntcl')&((kwargs['connected']==0) | (kwargs['a_status']==1))) |  # NTCL not connected or already running
                        (kwargs['ldc']==0)
            )

        idx2 = np.flatnonzero(((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['can_shed']==1)&(kwargs['mode']==0)&(kwargs['cooling_counter']>kwargs['min_coolingtime'])) |  # TCL can shed cooling
                            ((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['can_ramp']==1)&(kwargs['mode']==0)&(kwargs['cooling_counter']>kwargs['min_coolingtime']))  # TCL can ramp cooling
            )

        idx3 = np.flatnonzero(((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['can_shed']==1)&(kwargs['mode']==1)&(kwargs['heating_counter']>kwargs['min_heatingtime'])) |  # TCL can shed heating
                            ((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['can_ramp']==1)&(kwargs['mode']==1)&(kwargs['heating_counter']>kwargs['min_heatingtime']))  # TCL can ramp heating
            )
        idx4 = np.flatnonzero((kwargs['ldc']==1)&(kwargs['load_class']=='ntcl')&(kwargs['connected']==1) & (kwargs['a_status']==0))  # NTCL still not running
        idx5 = np.flatnonzero((kwargs['ldc']==1)&(kwargs['load_class']=='battery'))  # Battery

        # Common
        if np.size(idx1): kwargs['flexibility'][idx1] = 0
        # TCL
        cooling_lowlimit = np.subtract(kwargs['cooling_setpoint'], kwargs['tolerance'])
        cooling_highlimit = np.add(kwargs['cooling_setpoint'], kwargs['tolerance'])
        heating_lowlimit = np.subtract(kwargs['heating_setpoint'], kwargs['tolerance'])
        heating_highlimit = np.add(kwargs['heating_setpoint'], kwargs['tolerance'])
        cooling_horizon = np.subtract(kwargs['temp_max'], cooling_lowlimit)
        heating_horizon = np.subtract(heating_highlimit, kwargs['temp_min'])
        operation_horizon = np.subtract(kwargs['unix_end'], kwargs['unix_start'])


        if np.size(idx2): kwargs['flexibility'][idx2] = np.divide(np.subtract(kwargs['temp_max'][idx2], kwargs['temp_in'][idx2]), cooling_horizon[idx2])
        if np.size(idx3): kwargs['flexibility'][idx3] = np.divide(np.subtract(kwargs['temp_in'][idx3], kwargs['temp_min'][idx3]), heating_horizon[idx3])
        # ntcl
        if np.size(idx4): kwargs['flexibility'][idx4] = np.divide(np.subtract(kwargs['unix_end'][idx4], kwargs['finish'][idx4]), operation_horizon[idx4])
        # batt
        if np.size(idx5): kwargs['flexibility'][idx5] = np.divide(np.subtract(kwargs['unix_end'][idx5], kwargs['finish'][idx5]), operation_horizon[idx5]) - 0.1


    except Exception as e:
        print("Error in COMMON  get_flexibility:", e)

    return kwargs



def get_soc(**kwargs):
    # This function calculates the flexibility of TCL
    try:
        idx1 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['mode']==0))  # TCL cooling
        idx2 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['mode']==1))  # TCL heating
        idx3 = np.flatnonzero((kwargs['load_class']=='ntcl')&(kwargs['connected']==1))  # NTCL connected
        idx4 = np.flatnonzero((kwargs['load_class']=='ntcl')&(kwargs['connected']==0))  # NTCL disconnected

        if np.size(idx1): kwargs['soc'][idx1] = np.divide(np.subtract(kwargs['temp_max'][idx1], kwargs['temp_in'][idx1]), np.subtract(kwargs['temp_max'][idx1], np.subtract(kwargs['cooling_setpoint'][idx1], kwargs['tolerance'][idx1])))
        if np.size(idx2): kwargs['soc'][idx2] = np.divide(np.subtract(kwargs['temp_in'][idx2], kwargs['temp_min'][idx2]), np.subtract(np.add(kwargs['heating_setpoint'][idx2], kwargs['tolerance'][idx2]), kwargs['temp_min'][idx2]))
        if np.size(idx3): kwargs['soc'][idx3] = np.divide(kwargs['counter'][idx3], kwargs['len_profile'][idx3])
        if np.size(idx4): kwargs['soc'][idx4] = 0
        # Note battery soc is calculated at simulate_model

    except Exception as e:
        print("Error in COMMON  get_soc:", e)

    return kwargs


def get_job_status(**kwargs):
    try:
        idx0 = np.flatnonzero(((kwargs['load_type']=='hvac')&((kwargs['unixtime']<kwargs['unix_start'])|(kwargs['unixtime']>=kwargs['unix_end'])))|
                            ((kwargs['load_class']=='ntcl')&(kwargs['connected']==0)) |
                            ((kwargs['load_type']=='baseload')|(kwargs['load_type']=='freezer')|(kwargs['load_type']=='fridge')) |
                            (kwargs['job_status']>1.0)
            )

        idx1 = np.flatnonzero((kwargs['load_type']=='hvac')&(kwargs['unixtime']>=kwargs['unix_start'])&(kwargs['unixtime']<kwargs['unix_end']))
        idx2 = np.flatnonzero((kwargs['load_class']=='ntcl')&(kwargs['connected']==1))
        idx3 = np.flatnonzero((kwargs['load_class']=='battery'))

        # Common
        if np.size(idx0): kwargs['job_status'][idx0] = 0
        # hvac
        if np.size(idx1): kwargs['job_status'][idx1] = np.divide(np.subtract(kwargs['unixtime'], kwargs['unix_start'][idx1]), np.subtract(kwargs['unix_end'][idx1], kwargs['unix_start'][idx1]))
        # NTCL
        if np.size(idx2): kwargs['job_status'][idx2] = np.divide(kwargs['counter'][idx2], kwargs['len_profile'][idx2])
        # Battery
        if np.size(idx3): kwargs['job_status'][idx3] = np.clip(np.divide(kwargs['soc'][idx3], kwargs['target_soc'][idx3]), a_min=0, a_max=1.0)

    except Exception as e:
        print("Error COMMON get_job_status:", e)
    return kwargs




def get_mode(**kwargs):
    # This function determines the mode of operation of a TCL unit
    try:
        # for TCLs
        idx1 = np.flatnonzero(((kwargs['load_class']=='tcl')&(((kwargs['temp_out'] <= kwargs['heating_setpoint'])&(kwargs['temp_in']<=kwargs['temp_max'])))) | # TCL heating mode  |(kwargs['temp_in']<kwargs['temp_min'])
                            ((kwargs['load_class']=='battery')&(kwargs['load_type']=='ev')&(kwargs['connected']==0)) | # ev discharging, travelling
                            ((kwargs['load_class']=='battery')&(kwargs['load_type']=='storage')&(kwargs['connected']==0))  # storage discharging, supplying power 
                            )

        idx2 = np.flatnonzero(((kwargs['load_class']=='tcl')&(((kwargs['temp_out'] > kwargs['heating_setpoint'])&(kwargs['temp_in']>=kwargs['temp_min'])))) |  # TCL cooling mode  |(kwargs['temp_in']>kwargs['temp_max'])
                            (kwargs['load_class']=='ntcl') |  #  NTCL 
                            ((kwargs['load_class']=='battery')&(kwargs['load_type']=='ev')&(kwargs['connected']==1)) |  # ev is charging
                            ((kwargs['load_class']=='battery')&(kwargs['load_type']=='storage')&(kwargs['connected']==1))  # storage is charging
                            )

        # controller decision: heating, cooling
        if np.size(idx1): kwargs['mode'][idx1] = 1  # TCL heating, battery discharging
        if np.size(idx2): kwargs['mode'][idx2] = 0  # TCL cooling, battery charging, NTCL
        
    except Exception as e:
        # print(temp_out, temp_in, cooling_setpoint, heating_setpoint)
        print("Error in COMMON get_mode:", e)

    return kwargs



def get_p_status(**kwargs):
    # This function determines the statjs of operation of an HVAC unit
    # controller decision: ON or OFF
    try:

        idx1 = np.flatnonzero(((kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['mode']==0)&(kwargs['a_status']==1)&(kwargs['temp_in']>np.subtract(kwargs['cooling_setpoint'], kwargs['tolerance']))) | # TCL
                            ((kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['mode']==0)&(kwargs['a_status']==0)&(kwargs['temp_in']>=np.add(kwargs['cooling_setpoint'], kwargs['tolerance']))) | # TCL
                            ((kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['mode']==1)&(kwargs['a_status']==1)&(kwargs['temp_in']<np.add(kwargs['heating_setpoint'], kwargs['tolerance']))) | # TCL
                            ((kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['mode']==1)&(kwargs['a_status']==0)&(kwargs['temp_in']<=np.subtract(kwargs['heating_setpoint'], kwargs['tolerance']))) | # TCL
                            ((kwargs['load_class']=='ntcl')&(kwargs['unix_start']<=kwargs['unixtime'])&(kwargs['job_status']<1)) | # NTCL  
                            ((kwargs['load_class']=='battery')&(kwargs['mode']==0)&(kwargs['soc']<1.0)) | # Battery
                            ((kwargs['load_class']=='battery')&(kwargs['mode']==1)&(kwargs['soc']>0.2))  # Battery               
                        )

        idx2 = np.flatnonzero(((kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['mode']==0)&(kwargs['a_status']==1)&(kwargs['temp_in']<=np.subtract(kwargs['cooling_setpoint'], kwargs['tolerance']))) | # TCL
                            ((kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['mode']==0)&(kwargs['a_status']==0)&(kwargs['temp_in']<np.add(kwargs['cooling_setpoint'], kwargs['tolerance']))) |  # TCL
                            ((kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['mode']==1)&(kwargs['a_status']==1)&(kwargs['temp_in']>=np.add(kwargs['heating_setpoint'], kwargs['tolerance']))) |  # TCL
                            ((kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['mode']==1)&(kwargs['a_status']==0)&(kwargs['temp_in']>np.subtract(kwargs['heating_setpoint'], kwargs['tolerance']))) |  # TCL
                            ((kwargs['load_class']=='tcl')&(kwargs['connected']==0))|  # TCL
                            ((kwargs['load_class']=='ntcl')&(kwargs['connected']==0)|(kwargs['job_status']>=1)) | # NTCL
                            ((kwargs['load_class']=='battery')&(kwargs['mode']==0)&(kwargs['soc']>=1.0)) |  # Battery 
                            ((kwargs['load_class']=='battery')&(kwargs['mode']==1)&(kwargs['soc']<=0.2))   # Battery
                        )

        if np.size(idx1): kwargs['p_status'][idx1] = 1
        if np.size(idx2): kwargs['p_status'][idx2] = 0


    except Exception as e:
        print("Error in COMMON  determine_status:", e)

    return kwargs


def adjust_cop(**kwargs):
    # calculate coefficient of performance
    try:
        # idx0 = np.flatnonzero((kwargs['load_class']=='tcl') & (kwargs['mode']==0))  # cooling mode
        # idx1 = np.flatnonzero((kwargs['load_class']=='tcl') & (kwargs['mode']==1))  # heating mode

        # ### cooling
        # if np.size(idx0): kwargs['cop'][idx0] = np.divide(cop, np.power(np.e, ((1e-2)*np.subtract(temp_in+273, temp_out+273+i))))
        # ### heating
        # if np.size(idx1): kwargs['cop'][idx1] = np.clip((np.divide(kwargs['temp_in'][idx1], (np.subtract(kwargs['temp_in'][idx1], kwargs['temp_out'][idx1])))), a_min=1, a_max=5)

        pass
        
    except Exception as e:
        print("Error in COMMON  adjust_cop:", e)
    return kwargs



def heat_from_p_self(**kwargs):
    # determine the electrical demand and thermal heat
    try:
        kwargs.update(adjust_cop(**kwargs))
        # idx11 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['load_type']=='hvac')&((kwargs['p_status']==1)&(kwargs['mode']==1)))
        # idx12 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['load_type']=='hvac')&((kwargs['p_status']==1)&(kwargs['mode']==0)))

        idx21 = np.flatnonzero((kwargs['load_class']=='tcl')&((kwargs['p_status']==1)&(kwargs['mode']==1)))
        idx22 = np.flatnonzero((kwargs['load_class']=='tcl')&((kwargs['p_status']==1)&(kwargs['mode']==0)))
        
        idx3 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['p_status']==0))

        # if np.size(idx11): 
        #     kwargs['heat_device'][idx11] = kwargs['heating_power'][idx11] 
        #     kwargs['demand_heating'][idx11] = np.nan_to_num(np.divide(kwargs['heating_power'][idx11], kwargs['cop'][idx11]))
        #     kwargs['demand_cooling'][idx11] = 0
        
        # if np.size(idx12): 
        #     kwargs['heat_device'][idx12] = kwargs['cooling_power'][idx12] * -1
        #     kwargs['demand_heating'][idx12] = 0
        #     kwargs['demand_cooling'][idx12] = np.nan_to_num(np.divide(kwargs['cooling_power'][idx12], kwargs['cop'][idx12]))
        
        if np.size(idx21): 
            kwargs['heat_device'][idx21] = np.nan_to_num(np.multiply(kwargs['heating_power'][idx21], kwargs['cop'][idx21]))
            kwargs['demand_heating'][idx21] = kwargs['heating_power'][idx21]
            kwargs['demand_cooling'][idx21] = 0
        

        if np.size(idx22): 
            kwargs['heat_device'][idx22] = np.nan_to_num(np.multiply(kwargs['cooling_power'][idx22], kwargs['cop'][idx22])) * -1
            kwargs['demand_heating'][idx22] = 0
            kwargs['demand_cooling'][idx22] = kwargs['cooling_power'][idx22] 
        
        if np.size(idx3): 
            kwargs['heat_device'][idx3] = 0
            kwargs['demand_heating'][idx3] = 0
            kwargs['demand_cooling'][idx3] = 0
                

    except Exception as e:
        print("Error in COMMON  heat_from_self:", e)

    return kwargs


def heat_from_a_self(**kwargs):
    # determine the electrical demand and thermal heat
    try:
        kwargs.update(adjust_cop(**kwargs))
        # idx11 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['load_type']=='hvac')&((kwargs['a_status']==1)&(kwargs['mode']==1)))
        # idx12 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['load_type']=='hvac')&((kwargs['a_status']==1)&(kwargs['mode']==0)))

        idx21 = np.flatnonzero((kwargs['load_class']=='tcl')&((kwargs['a_status']==1)&(kwargs['mode']==1)))
        idx22 = np.flatnonzero((kwargs['load_class']=='tcl')&((kwargs['a_status']==1)&(kwargs['mode']==0)))
        
        idx3 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['a_status']==0))

        # if np.size(idx11): 
        #     kwargs['heat_device'][idx11] = kwargs['heating_power'][idx11] 
        #     kwargs['demand_heating'][idx11] = np.nan_to_num(np.divide(kwargs['heating_power'][idx11], kwargs['cop'][idx11]))
        #     kwargs['demand_cooling'][idx11] = 0
        
        # if np.size(idx12): 
        #     kwargs['heat_device'][idx12] = kwargs['cooling_power'][idx12] * -1
        #     kwargs['demand_heating'][idx12] = 0
        #     kwargs['demand_cooling'][idx12] = np.nan_to_num(np.divide(kwargs['cooling_power'][idx12], kwargs['cop'][idx12]))
        
        if np.size(idx21): 
            kwargs['heat_device'][idx21] = np.nan_to_num(np.multiply(kwargs['heating_power'][idx21], kwargs['cop'][idx21]))
            kwargs['demand_heating'][idx21] = kwargs['heating_power'][idx21]
            kwargs['demand_cooling'][idx21] = 0
        

        if np.size(idx22): 
            kwargs['heat_device'][idx22] = np.nan_to_num(np.multiply(kwargs['cooling_power'][idx22], kwargs['cop'][idx22])) * -1
            kwargs['demand_heating'][idx22] = 0
            kwargs['demand_cooling'][idx22] = kwargs['cooling_power'][idx22] 
        
        if np.size(idx3): 
            kwargs['heat_device'][idx3] = 0
            kwargs['demand_heating'][idx3] = 0
            kwargs['demand_cooling'][idx3] = 0
        

    except Exception as e:
        print("Error in COMMON  heat_from_self:", e)

    return kwargs



# def batt_demand(**kwargs):
#     # calculate the demand at this time step
#     try:
#         idx1 = np.flatnonzero((kwargs['mode']==0)&(kwargs['p_status']==1)&(kwargs['soc']>0.9))
#         idx2 = np.flatnonzero((kwargs['mode']==0)&(kwargs['p_status']==1)&(kwargs['soc']<=0.9))
#         idx3 = np.flatnonzero((kwargs['mode']==0)&(kwargs['p_status']==0))
#         idx4 = np.flatnonzero((kwargs['mode']==1)&(kwargs['p_status']==1)&(kwargs['soc']<=0.2))
#         idx5 = np.flatnonzero((kwargs['mode']==1)&(kwargs['p_status']==1)&(kwargs['soc']>0.2)&(kwargs['load_type']=='storage'))
#         idx6 = np.flatnonzero((kwargs['mode']==1)&(kwargs['p_status']==0))
#         idx7 = np.flatnonzero((kwargs['mode']==1)&(kwargs['p_status']==1)&(kwargs['soc']>0.2)&(kwargs['load_type']=='ev'))

#         kwargs['p_demand'][idx1] = np.divide(kwargs['charging_power'][idx1], np.power(np.e, kwargs['soc'][idx1]*2) )
#         kwargs['p_demand'][idx2] = kwargs['charging_power'][idx2]
#         kwargs['p_demand'][idx3] = 0
#         kwargs['p_demand'][idx4] = 0
#         kwargs['p_demand'][idx5] = np.multiply(kwargs['charging_power'][idx5], -1)
#         kwargs['p_demand'][idx6] = 0
#         kwargs['p_demand'][idx7] = 0
        
#     except Exception as e:
#         print("Error Batter get_p_demand:", e)
    
#     return kwargs


def get_p_demand(**kwargs):
    # calculate the demand at this time step
    try:
        kwargs.update(heat_from_p_self(**kwargs))

        idx1 = np.flatnonzero((kwargs['p_status']==1)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1))  # TCL
        idx2 = np.flatnonzero((kwargs['p_status']==1)&(kwargs['connected']==1)&(kwargs['load_type']=='baseload'))  # houses
        idx3 = np.flatnonzero((kwargs['p_status']==1)&(kwargs['connected']==1)&(kwargs['load_type']=='clotheswasher'))  # clotheswasher
        idx4 = np.flatnonzero((kwargs['p_status']==1)&(kwargs['connected']==1)&(kwargs['load_type']=='clothesdryer'))  # clothesdryer
        idx5 = np.flatnonzero((kwargs['p_status']==1)&(kwargs['connected']==1)&(kwargs['load_type']=='dishwasher'))  # dishwasher
        # for battery
        b_idx1 = np.flatnonzero((kwargs['mode']==0)&(kwargs['p_status']==1)&(kwargs['soc']>0.9)&(kwargs['load_class']=='battery'))
        b_idx2 = np.flatnonzero((kwargs['mode']==0)&(kwargs['p_status']==1)&(kwargs['soc']<=0.9)&(kwargs['load_class']=='battery'))
        b_idx3 = np.flatnonzero((kwargs['mode']==0)&(kwargs['p_status']==0)&(kwargs['load_class']=='battery'))
        b_idx4 = np.flatnonzero((kwargs['mode']==1)&(kwargs['p_status']==1)&(kwargs['soc']<=0.2)&(kwargs['load_class']=='battery'))
        b_idx5 = np.flatnonzero((kwargs['mode']==1)&(kwargs['p_status']==1)&(kwargs['soc']>0.2)&(kwargs['load_class']=='battery')&(kwargs['load_type']=='storage'))
        b_idx6 = np.flatnonzero((kwargs['mode']==1)&(kwargs['p_status']==0)&(kwargs['load_class']=='battery'))
        b_idx7 = np.flatnonzero((kwargs['mode']==1)&(kwargs['p_status']==1)&(kwargs['soc']>0.2)&(kwargs['load_class']=='battery')&(kwargs['load_type']=='ev'))
        # for solar
        s_idx1 = np.flatnonzero((kwargs['load_type']=='solar'))
        # for wind
        w_idx1 = np.flatnonzero((kwargs['load_type']=='wind'))

        n_idx = np.flatnonzero((
            (kwargs['p_status']==0)&(kwargs['load_class']=='tcl')&(kwargs['connected']==0)) |  # TCLs
            ((kwargs['p_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='baseload')) |  # houses
            ((kwargs['p_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='clotheswasher')) |  # clotheswasher  
            ((kwargs['p_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='clothesdryer')) |  # clothesdryer
            ((kwargs['p_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='dishwasher'))  # dishwasher
            )
        # for all, OFF status
        if np.size(n_idx): kwargs['p_demand'][n_idx] = 0

        # TCL
        if np.size(idx1): kwargs['p_demand'][idx1] = np.nan_to_num(np.add(kwargs['demand_cooling'][idx1], np.add(kwargs['demand_heating'][idx1], np.add(kwargs['ventilation_power'][idx1], kwargs['standby_power'][idx1]))))
        # for houses
        try:
            if np.size(idx2): kwargs['p_demand'][idx2] =  np.diag(kwargs['df_baseload'].loc[np.add(kwargs['skew'][idx2], to_yearsecond(kwargs['unixtime'])).astype(int), kwargs['profile'][idx2]].values)
        except Exception as e:
            print("Error reading df_baseload:", e)
            kwargs['df_baseload'] = get_baseloads(kwargs['unixtime'])
            
            
        # for clotheswasher
        if np.size(idx3): kwargs['p_demand'][idx3] =  np.diag(df_clotheswasher.loc[kwargs['counter'][idx3], kwargs['profile'][idx3]].values)
        # for clothesdryer
        if np.size(idx4): kwargs['p_demand'][idx4] =  np.diag(df_clothesdryer.loc[kwargs['counter'][idx4], kwargs['profile'][idx4]].values)
        # dishwasher
        if np.size(idx5): kwargs['p_demand'][idx5] =  np.diag(df_dishwasher.loc[kwargs['counter'][idx5], kwargs['profile'][idx5]].values)
        # for battery
        if np.size(b_idx1): kwargs['p_demand'][b_idx1] = np.divide(kwargs['charging_power'][b_idx1], np.power(np.e, kwargs['soc'][b_idx1]*2) )
        if np.size(b_idx2): kwargs['p_demand'][b_idx2] = kwargs['charging_power'][b_idx2]
        if np.size(b_idx3): kwargs['p_demand'][b_idx3] = 0
        if np.size(b_idx4): kwargs['p_demand'][b_idx4] = 0
        if np.size(b_idx5): kwargs['p_demand'][b_idx5] = np.multiply(kwargs['charging_power'][b_idx5], -1)
        if np.size(b_idx6): kwargs['p_demand'][b_idx6] = 0
        if np.size(b_idx7): kwargs['p_demand'][b_idx7] = 0

        
        
        # for solar
        if np.size(s_idx1):
            area = np.multiply(kwargs['floor_area'][s_idx1], kwargs['pv_roof_area'][s_idx1])  # [m^2]
            kwargs['solar_capacity'][s_idx1] = np.round(np.clip(np.multiply(area, kwargs['power_per_area'][s_idx1]), a_min=2e3, a_max=20e3), -2)  # [W], based on standard irradiance of 1000W/m^2
            kwargs['solar_efficiency'][s_idx1] = np.multiply(kwargs['pv_efficiency'][s_idx1], kwargs['inverter_efficiency'][s_idx1])  #[%]
            std_irradiance = np.divide(kwargs['irradiance_roof'][s_idx1], 1000)  # actual irradiance / standard
            kwargs['p_demand'][s_idx1] = np.multiply(std_irradiance, np.multiply(kwargs['solar_capacity'][s_idx1], kwargs['solar_efficiency'][s_idx1])) * -1  #[W]


        # for wind
        if np.size(w_idx1):
            rho = np.add((np.power(kwargs['temp_out'][w_idx1], 2)*0.000001721), np.add(np.multiply(kwargs['temp_out'][w_idx1], -0.0026739231), 1.2612024555)) # air density, regression equation with R^2 value of 0.9692103547; data taken from www.EngineeringToolBox.com
            rho_o = np.ones(np.size(w_idx1)) * 1.225 # kg/m^3, air density at standard atmosphere sea level
            v_ave = kwargs['windspeed'][w_idx1]
            
            v_i = np.clip(np.random.normal(3.0, 0.01, np.size(w_idx1)), a_min=2.9, a_max=3.3) # m/s, cut-in speed
            v_o = np.clip(np.random.normal(18.0, 0.01, np.size(w_idx1)), a_min=17.5, a_max=18.5) # m/s, cut-out speed
            v_r = np.clip(np.random.normal(13.0, 0.01, np.size(w_idx1)), a_min=12.5, a_max=13.5) # m/s, rated speed
            v = np.multiply(v_ave, np.power(np.divide(rho, rho_o), (1/3)))

            a = v_i**3 / ((v_i**3)-(v_r**3))  # coefficients
            b = 1.0/((v_r**3)-(v_i**3))  # coefficients

            
            # if v_i <= v <= v_r:
            #     windPower = installedWind * (a + (b*(v**3)))
            # elif v_r <= v <= v_o:
            #     windPower = installedWind
            # else:
            #     windPower = 0.0

        idx0 = np.flatnonzero(np.isin(kwargs['load_class'], ['tcl', 'ntcl']))
        kwargs['p_demand'][idx0] = np.clip(np.add(kwargs['p_demand'][idx0], np.random.normal(0, 0.1)), a_min=0, a_max=9e6)

        

    except Exception as e:
        print("Error in COMMON get_p_demand:", e)
    
    return kwargs



def get_a_demand(**kwargs):
    # calculate the demand at this time step
    try:
        kwargs.update(heat_from_a_self(**kwargs))
        
        idx1 = np.flatnonzero((kwargs['a_status']==1)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1))  # TCL
        idx2 = np.flatnonzero((kwargs['a_status']==1)&(kwargs['connected']==1)&(kwargs['load_type']=='baseload'))  # houses
        idx3 = np.flatnonzero((kwargs['a_status']==1)&(kwargs['connected']==1)&(kwargs['load_type']=='clotheswasher'))  # clotheswasher
        idx4 = np.flatnonzero((kwargs['a_status']==1)&(kwargs['connected']==1)&(kwargs['load_type']=='clothesdryer'))  # clothesdryer
        idx5 = np.flatnonzero((kwargs['a_status']==1)&(kwargs['connected']==1)&(kwargs['load_type']=='dishwasher'))  # dishwasher
        # for battery
        b_idx1 = np.flatnonzero((kwargs['mode']==0)&(kwargs['a_status']==1)&(kwargs['soc']>0.9)&(kwargs['load_class']=='battery'))
        b_idx2 = np.flatnonzero((kwargs['mode']==0)&(kwargs['a_status']==1)&(kwargs['soc']<=0.9)&(kwargs['load_class']=='battery'))
        b_idx3 = np.flatnonzero((kwargs['mode']==0)&(kwargs['a_status']==0)&(kwargs['load_class']=='battery'))
        b_idx4 = np.flatnonzero((kwargs['mode']==1)&(kwargs['a_status']==1)&(kwargs['soc']<=0.2)&(kwargs['load_class']=='battery'))
        b_idx5 = np.flatnonzero((kwargs['mode']==1)&(kwargs['a_status']==1)&(kwargs['soc']>0.2)&(kwargs['load_class']=='battery')&(kwargs['load_type']=='storage'))
        b_idx6 = np.flatnonzero((kwargs['mode']==1)&(kwargs['a_status']==0)&(kwargs['load_class']=='battery'))
        b_idx7 = np.flatnonzero((kwargs['mode']==1)&(kwargs['a_status']==1)&(kwargs['soc']>0.2)&(kwargs['load_class']=='battery')&(kwargs['load_type']=='ev'))
        # for solar
        s_idx1 = np.flatnonzero((kwargs['load_type']=='solar'))
        # for wind
        w_idx1 = np.flatnonzero((kwargs['load_type']=='wind'))

        n_idx = np.flatnonzero(((kwargs['a_status']==0)&(kwargs['load_class']=='tcl')&(kwargs['connected']==0)) |  # TCLs
            ((kwargs['a_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='baseload')) |  # houses
            ((kwargs['a_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='clotheswasher')) |  # clotheswasher  
            ((kwargs['a_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='clothesdryer')) |  # clothesdryer
            ((kwargs['a_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='dishwasher')) |  # dishwasher
            ((kwargs['a_status']==0)|(kwargs['connected']==0)&(kwargs['load_type']=='ev'))  # ev
            )

        # for all, OFF status
        if np.size(n_idx): kwargs['a_demand'][n_idx] = 0

        # TCL
        if np.size(idx1): kwargs['a_demand'][idx1] = np.nan_to_num(np.add(kwargs['demand_cooling'][idx1], np.add(kwargs['demand_heating'][idx1], np.add(kwargs['ventilation_power'][idx1], kwargs['standby_power'][idx1]))))
        # for houses
        try:
            if np.size(idx2): kwargs['a_demand'][idx2] =  np.diag(kwargs['df_baseload'].loc[np.add(kwargs['skew'][idx2], to_yearsecond(kwargs['unixtime'])).astype(int), kwargs['profile'][idx2]].values)
        except:
            kwargs['df_baseload'] = get_baseloads(kwargs['unixtime'])

        # for clotheswasher
        if np.size(idx3): kwargs['a_demand'][idx3] =  np.diag(df_clotheswasher.loc[kwargs['counter'][idx3], kwargs['profile'][idx3]].values)
        # for clothesdryer
        if np.size(idx4): kwargs['a_demand'][idx4] =  np.diag(df_clothesdryer.loc[kwargs['counter'][idx4], kwargs['profile'][idx4]].values)
        # dishwasher
        if np.size(idx5): kwargs['a_demand'][idx5] =  np.diag(df_dishwasher.loc[kwargs['counter'][idx5], kwargs['profile'][idx5]].values)
        # for battery
        if np.size(b_idx1): kwargs['a_demand'][b_idx1] = np.divide(kwargs['charging_power'][b_idx1], np.power(np.e, kwargs['soc'][b_idx1]*2) )
        if np.size(b_idx2): kwargs['a_demand'][b_idx2] = kwargs['charging_power'][b_idx2]
        if np.size(b_idx3): kwargs['a_demand'][b_idx3] = 0
        if np.size(b_idx4): kwargs['a_demand'][b_idx4] = 0
        if np.size(b_idx5): kwargs['a_demand'][b_idx5] = np.multiply(kwargs['charging_power'][b_idx5], -1)
        if np.size(b_idx6): kwargs['a_demand'][b_idx6] = 0
        if np.size(b_idx7): kwargs['a_demand'][b_idx7] = 0

        
        
        # for solar
        if np.size(s_idx1):
            kwargs['a_demand'][s_idx1] = kwargs['p_demand'][s_idx1]

        if np.size(w_idx1):
            kwargs['a_demand'][w_idx1] = kwargs['p_demand'][w_idx1]

        # idx0 = np.flatnonzero(np.isin(kwargs['load_class'], ['tcl', 'ntcl']))
        # if np.size(idx0):
        #     kwargs['a_demand'][idx0] = np.clip(np.add(kwargs['a_demand'][idx0], np.random.normal(0, 0.1, np.size(idx0))), a_min=0, a_max=9e6)

        

    except Exception as e:
        print("Error in COMMON get_a_demand:", e)
    
    return kwargs



def check_ramp_shed(**kwargs):
    try:
        idx1 = np.flatnonzero(((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['a_status']==0)&(kwargs['mode']==0)&(kwargs['cooling_counter']>=kwargs['min_coolingtime'])&(kwargs['temp_in']>kwargs['temp_min'])) |
                            ((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['a_status']==0)&(kwargs['mode']==1)&(kwargs['heating_counter']>=kwargs['min_heatingtime'])&(kwargs['temp_in']<kwargs['temp_max'])) |
                            ((kwargs['ldc']==1)&(kwargs['load_class']=='battery')&(kwargs['mode']==0)&(kwargs['a_status']==0))
                            # ((kwargs['ldc']==1)&(kwargs['load_class']=='battery')&(kwargs['mode']==1)&(kwargs['a_status']==0))
                        )
    
        idx2 = np.flatnonzero(((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['a_status']==1)&(kwargs['mode']==0)&(kwargs['cooling_counter']>=kwargs['min_coolingtime'])&(kwargs['temp_in']<kwargs['temp_max'])) |
                            ((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['a_status']==1)&(kwargs['mode']==1)&(kwargs['heating_counter']>=kwargs['min_heatingtime'])&(kwargs['temp_in']>kwargs['temp_min'])) |
                            ((kwargs['ldc']==1)&(kwargs['load_class']=='battery')&(kwargs['flexibility']>0.1)&(kwargs['mode']==0)&(kwargs['a_status']==1))
                            # ((kwargs['ldc']==1)&(kwargs['load_class']=='battery')&(kwargs['mode']==1)&(kwargs['a_status']==1))
                        )

        idx3 = np.flatnonzero(((kwargs['load_class']=='battery')&(kwargs['flexibility']<=0.1)))

        n_idx = np.flatnonzero(((kwargs['ldc']==0)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['a_status']==0)&((kwargs['mode']==0)&((kwargs['cooling_counter']<kwargs['min_coolingtime'])|(kwargs['temp_in']<=kwargs['temp_min'])))) |
                            ((kwargs['ldc']==0)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['a_status']==0)&((kwargs['mode']==1)&((kwargs['heating_counter']<kwargs['min_heatingtime'])|(kwargs['temp_in']>=kwargs['temp_max'])))) |
                            ((kwargs['ldc']==0)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['a_status']==1)&((kwargs['mode']==0)&((kwargs['cooling_counter']<kwargs['min_coolingtime'])|(kwargs['temp_in']>=kwargs['temp_max']))))|
                            ((kwargs['ldc']==0)&(kwargs['load_class']=='tcl')&(kwargs['connected']==1)&(kwargs['a_status']==1)&((kwargs['mode']==1)&((kwargs['heating_counter']<kwargs['min_heatingtime'])|(kwargs['temp_in']<=kwargs['temp_min'])))) |
                            ((kwargs['ldc']==0)&(kwargs['load_class']=='tcl')&(kwargs['connected']==0)) |
                            ((kwargs['load_class']=='ntcl'))
                        )
        
        if np.size(idx1): kwargs['can_ramp'][idx1] = 1
        if np.size(idx2): kwargs['can_shed'][idx2] = 1
        if np.size(idx3): 
            kwargs['can_shed'][idx3] = 0
            kwargs['can_ramp'][idx3] = 1

        if np.size(n_idx):
            kwargs['can_ramp'][n_idx] = 0
            kwargs['can_shed'][n_idx] = 0

        
    except Exception as e:
        print("Error in COMMON check_ramp_shed:",e)

    return kwargs


def get_ramp_power(**kwargs):
    # get ramping capacity
    try:
        idx0 = np.flatnonzero((kwargs['can_ramp']==0))
        idx1 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['can_ramp']==1)&(kwargs['mode']==0))
        idx2 = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['can_ramp']==1)&(kwargs['mode']==1))
        idx3 = np.flatnonzero((kwargs['load_class']=='battery')&(kwargs['can_ramp']==1)&(kwargs['mode']==0))
        
        if np.size(idx0): kwargs['ramp_power'][idx0] = 0
        if np.size(idx1): kwargs['ramp_power'][idx1] = kwargs['cooling_power'][idx1]
        if np.size(idx2): kwargs['ramp_power'][idx2] = kwargs['heating_power'][idx2]
        if np.size(idx3): kwargs['ramp_power'][idx3] = kwargs['charging_power'][idx3]
        

    except Exception as e:
        print("Error in COMMON  get_ramp_power:", e)
    return kwargs


def get_shed_power(**kwargs):
    # get shedding capacity
    try:
        idx1 = np.flatnonzero((kwargs['can_shed']==1))
        idx2 = np.flatnonzero((kwargs['can_shed']==0))

        if np.size(idx1): kwargs['shed_power'][idx1] = kwargs['a_demand'][idx1]
        if np.size(idx2): kwargs['shed_power'][idx2] = 0

    except Exception as e:
        print("Error in COMMON  get_shed_power:", e)
    return kwargs


# def get_ramp_power(a_status, mode, flexibility, cooling_counter, heating_counter,
#     min_coolingtime, min_heatingtime, ramp_power, cooling_power, heating_power, connected):
#     # get ramping capacity
#     try:
#         idx1 = np.flatnonzero(((a_status==0)&(flexibility>0)&(connected==1)&(mode==0)&(cooling_counter<min_coolingtime)) |
#                             ((a_status==0)&(flexibility>0)&(connected==1)&(mode==1)&(heating_counter<min_heatingtime)) |
#                             ((a_status==1)|(flexibility<=0)|(connected==0))
#                         )

#         idx2 = np.flatnonzero(((a_status==0)&(flexibility>0)&(connected==1)&(mode==0)&(cooling_counter>=min_coolingtime)))
#         idx3 = np.flatnonzero(((a_status==0)&(flexibility>0)&(connected==1)&(mode==1)&(heating_counter>=min_heatingtime)))

#         if np.size(idx1): ramp_power[idx1] = 0
#         if np.size(idx2): ramp_power[idx2] = cooling_power[idx2]
#         if np.size(idx3): ramp_power[idx3] = heating_power[idx3]

#     except Exception as e:
#         print("Error in COMMON  get_ramp_power:", e)
#     return ramp_power


# def get_shed_power(a_status, mode, flexibility, cooling_counter, heating_counter,
#     shed_power, cooling_power, heating_power, min_coolingtime, min_heatingtime, connected):
#     # get shedding capacity
#     try:
#         idx1 = np.flatnonzero(((a_status==1)&(flexibility>0)&(connected==1)&(mode==0)&(cooling_counter<min_coolingtime)) |
#                             ((a_status==1)&(flexibility>0)&(connected==1)&(mode==1)&(heating_counter<min_heatingtime)) |
#                             ((a_status==0)|(flexibility<=0)|(connected==0))
#                         )
#         idx2 = np.flatnonzero(((a_status==1)&(flexibility>0)&(connected==1)&(mode==0)&(cooling_counter>=min_coolingtime)))
#         idx3 = np.flatnonzero(((a_status==1)&(flexibility>0)&(connected==1)&(mode==1)&(heating_counter>=min_heatingtime)))

#         if np.size(idx1): shed_power[idx1] = 0
#         if np.size(idx2): shed_power[idx2] = cooling_power[idx2]
#         if np.size(idx3): shed_power[idx3] = heating_power[idx3]

#     except Exception as e:
#         print("Error in COMMON  get_shed_power:", e)
#     return shed_power



def ramp_demand():
    proposedMode = 1
    return proposedMode



def get_massflow(**kwargs):
    try:
        # t = np.add(np.divide(kwargs['schedule_skew'], 3600), kwargs['dayhour'])  # [hours]
        
        # idx1 = np.flatnonzero((kwargs['load_class']=='tcl')&(t<=4))
        # idx2 = np.flatnonzero((kwargs['load_class']=='tcl')&(t>4)&(t<=8))
        # idx3 = np.flatnonzero((kwargs['load_class']=='tcl')&(t>8)&(t<=12))
        # idx4 = np.flatnonzero((kwargs['load_class']=='tcl')&(t>12)&(t<=16))
        # idx5 = np.flatnonzero((kwargs['load_class']=='tcl')&(t>16)&(t<=20))
        # idx6 = np.flatnonzero((kwargs['load_class']=='tcl')&(t>20))

        # if np.size(idx1): kwargs['mass_flow'][idx1] = 0.0019
        # if np.size(idx2): kwargs['mass_flow'][idx2] = np.multiply(kwargs['mass_change'][idx2], np.multiply(np.add(np.multiply(0.6, np.subtract(t[idx2], 4)), 0.25), 1e-4))
        # if np.size(idx3): kwargs['mass_flow'][idx3] = np.multiply(kwargs['mass_change'][idx3], np.multiply(np.add(np.multiply(-0.1, np.subtract(t[idx3], 8)), 0.99), 1e-4))
        # if np.size(idx4): kwargs['mass_flow'][idx4] = np.multiply(kwargs['mass_change'][idx4], np.multiply(np.add(np.multiply(-0.01, np.subtract(t[idx4], 12)), 0.44), 1e-4))
        # if np.size(idx5): kwargs['mass_flow'][idx5] = np.multiply(kwargs['mass_change'][idx5], np.multiply(np.add(np.multiply(-0.06, np.subtract(t[idx5], 16)), 0.14), 1e-4))
        # if np.size(idx6): kwargs['mass_flow'][idx6] = np.multiply(kwargs['mass_change'][idx6], np.multiply(np.add(np.multiply(-0.14, np.subtract(t[idx6], 20)), 0.8), 1e-4))
        idx1 = np.flatnonzero(kwargs['load_type']=='waterheater')
        idx2 = np.flatnonzero(kwargs['load_type']=='freezer')
        idx3 = np.flatnonzero(kwargs['load_type']=='fridge')
        if np.size(idx1): kwargs['mass_flow'][idx1] = np.multiply(kwargs['mass_change'][idx1], np.multiply(kwargs['baseload'][idx1]>500, 1e3))
        if np.size(idx2): kwargs['mass_flow'][idx2] = np.multiply(kwargs['mass_change'][idx2], np.multiply(kwargs['baseload'][idx2], 1e-4))
        if np.size(idx3): kwargs['mass_flow'][idx3] = np.multiply(kwargs['mass_change'][idx3], np.multiply(kwargs['baseload'][idx3], 1e-4))
        # print(np.mean(kwargs['temp_in'][idx1]), np.mean(kwargs['temp_in'][idx2]), np.mean(kwargs['temp_in'][idx3]))
        
    except Exception as e:
        print("Error in COMMON get_massflow:", e)
    return kwargs
    

def get_irradiance(**kwargs):
    try:
        idx = np.flatnonzero(kwargs['load_type']=='baseload')  # all houses

        if np.size(idx):
            kwargs['irradiance_roof'][idx] = solar.get_irradiance(
                                            unixtime=kwargs['unixtime'],
                                            humidity=kwargs['humidity'][idx],
                                            latitude=kwargs['latitude'][idx],
                                            longitude=kwargs['longitude'][idx],
                                            elevation=kwargs['elevation'][idx],
                                            tilt=kwargs['roof_tilt'][idx],
                                            azimuth=kwargs['azimuth'][idx],
                                            albedo=kwargs['albedo'][idx],
                                            isotime=kwargs['isotime']
                                        )
            kwargs['irradiance_wall1'][idx] = solar.get_irradiance(
                                            unixtime=kwargs['unixtime'],
                                            humidity=kwargs['humidity'][idx],
                                            latitude=kwargs['latitude'][idx],
                                            longitude=kwargs['longitude'][idx],
                                            elevation=kwargs['elevation'][idx],
                                            tilt=np.ones(np.size(idx))*90,
                                            azimuth=kwargs['azimuth'][idx],
                                            albedo=kwargs['albedo'][idx],
                                            isotime=kwargs['isotime']
                                        )
            kwargs['irradiance_wall2'][idx] = solar.get_irradiance(
                                            unixtime=kwargs['unixtime'],
                                            humidity=kwargs['humidity'][idx],
                                            latitude=kwargs['latitude'][idx],
                                            longitude=kwargs['longitude'][idx],
                                            elevation=kwargs['elevation'][idx],
                                            tilt=np.ones(np.size(idx))*90,
                                            azimuth=kwargs['azimuth'][idx]+90,
                                            albedo=kwargs['albedo'][idx],
                                            isotime=kwargs['isotime']
                                        )
            kwargs['irradiance_wall3'][idx] = solar.get_irradiance(
                                            unixtime=kwargs['unixtime'],
                                            humidity=kwargs['humidity'][idx],
                                            latitude=kwargs['latitude'][idx],
                                            longitude=kwargs['longitude'][idx],
                                            elevation=kwargs['elevation'][idx],
                                            tilt=np.ones(np.size(idx))*90,
                                            azimuth=kwargs['azimuth'][idx]-90,
                                            albedo=kwargs['albedo'][idx],
                                            isotime=kwargs['isotime']
                                        )
            kwargs['irradiance_wall4'][idx] = solar.get_irradiance(
                                            unixtime=kwargs['unixtime'],
                                            humidity=kwargs['humidity'][idx],
                                            latitude=kwargs['latitude'][idx],
                                            longitude=kwargs['longitude'][idx],
                                            elevation=kwargs['elevation'][idx],
                                            tilt=np.ones(np.size(idx))*90,
                                            azimuth=kwargs['azimuth'][idx]+180,
                                            albedo=kwargs['albedo'][idx],
                                            isotime=kwargs['isotime']
                                        )

            # ### simulate cloud cover
            # idx1 = np.flatnonzero((kwargs['unix_start']<kwargs['unixtime'])&(kwargs['unix_end']>kwargs['unixtime'])&(kwargs['load_type']=='solar'))
            # idx_c = np.flatnonzero(np.isin(kwargs['name'], kwargs['house'][idx1]))
            # if np.size(idx_c):
            #     kwargs['irradiance_roof'][idx_c] = np.multiply(kwargs['irradiance_roof'][idx_c], np.clip(np.random.normal(0.08, 0.001, np.size(idx_c)), a_min=0.01, a_max=0.8))
            #     kwargs['irradiance_wall1'][idx_c] = np.multiply(kwargs['irradiance_wall1'][idx_c], np.clip(np.random.normal(0.08, 0.001, np.size(idx_c)), a_min=0.01, a_max=0.8))
            #     kwargs['irradiance_wall2'][idx_c] = np.multiply(kwargs['irradiance_wall2'][idx_c], np.clip(np.random.normal(0.08, 0.001, np.size(idx_c)), a_min=0.01, a_max=0.8))
            #     kwargs['irradiance_wall3'][idx_c] = np.multiply(kwargs['irradiance_wall3'][idx_c], np.clip(np.random.normal(0.08, 0.001, np.size(idx_c)), a_min=0.01, a_max=0.8))
            #     kwargs['irradiance_wall4'][idx_c] = np.multiply(kwargs['irradiance_wall4'][idx_c], np.clip(np.random.normal(0.08, 0.001, np.size(idx_c)), a_min=0.01, a_max=0.8))

            # sum irradiance from all sides of the house
            kwargs['irradiance'][idx] = np.sum([kwargs['irradiance_roof'][idx]*kwargs['skylight_area'][idx], kwargs['irradiance_wall1'][idx]*kwargs['wall_area'][idx]/4, 
                kwargs['irradiance_wall2'][idx]*kwargs['wall_area'][idx]/4, kwargs['irradiance_wall3'][idx]*kwargs['wall_area'][idx]/4, kwargs['irradiance_wall4'][idx]*kwargs['wall_area'][idx]/4], axis=0)


    except Exception as e:
        print("Error in COMMON.py get_irradiance:", e)

    return kwargs


def heat_from_inside(**kwargs):
    try:
        idx = np.flatnonzero(kwargs['load_type']=='hvac')
        n_idx = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['load_type']!='hvac'))
        
        if np.size(idx): kwargs['heat_in'][idx] = 0.1 * kwargs['baseload'][idx]
        if np.size(n_idx): kwargs['heat_in'][n_idx] = 0
    except Exception as e:
        print("Error TCL heat_from_inside:", e)

    return kwargs


def heat_from_outside(**kwargs):
    try:
        idx = np.flatnonzero(kwargs['load_type']=='hvac')
        n_idx = np.flatnonzero((kwargs['load_class']=='tcl')&(kwargs['load_type']!='hvac'))
        if np.size(idx): kwargs['heat_ex'][idx] = 0.1 * kwargs['irradiance'][idx]
        if np.size(n_idx): kwargs['heat_ex'][n_idx] = 0 
    except Exception as e:
        print("Error TCL heat_from_outside:", e)
    return kwargs


def heat_from_all(**kwargs):
    # This function calculates the total heat into the thermal zone
    try:
        idx1 = np.flatnonzero((kwargs['load_class']=='tcl'))
        if np.size(idx1): kwargs['heat_all'][idx1] = np.add(kwargs['heat_ex'][idx1], np.add(kwargs['heat_in'][idx1], kwargs['heat_device'][idx1]))  #watts
    except Exception as e:
        print("Error in COMMON heat_from_all:", e)

    return kwargs

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
        

        if np.size(idx1):
            while counter<kwargs['step_size']:
                # for air temp
                conv_heat = np.nan_to_num(np.multiply(kwargs['heat_all'][idx1], kwargs['m']))
                conv_in_mat = np.nan_to_num(np.multiply(np.subtract(kwargs['temp_in'][idx1], kwargs['temp_mat'][idx1]), kwargs['Um'][idx1]))
                conv_in_out = np.nan_to_num(np.multiply(np.subtract(kwargs['temp_in'][idx1], kwargs['temp_out'][idx1]), kwargs['Ua'][idx1]))
                mcpdt = np.nan_to_num(np.multiply(np.subtract(kwargs['temp_in'][idx1], kwargs['temp_out'][idx1]), np.multiply(kwargs['mass_flow'][idx1], kwargs['Cp'][idx1])))

                partial = conv_heat
                partial = np.nan_to_num(np.subtract(partial, conv_in_mat))
                partial = np.nan_to_num(np.subtract(partial, conv_in_out))
                partial = np.nan_to_num(np.subtract(partial, mcpdt))

                dtemp_in_dt = np.nan_to_num(np.divide(partial, kwargs['Ca'][idx1]))
                dtemp_in = np.nan_to_num(np.multiply(dtemp_in_dt, inc ))
                kwargs['temp_in'][idx1] = np.nan_to_num(np.add(kwargs['temp_in'][idx1], dtemp_in))

                # for material temp
                direct_heat = np.nan_to_num(np.multiply(kwargs['heat_all'][idx1], (1-kwargs['m'])))
                conv_mat_in = np.nan_to_num(np.multiply(np.subtract(kwargs['temp_mat'][idx1], kwargs['temp_in'][idx1]), kwargs['Um'][idx1]))
                partial_m = np.nan_to_num(np.subtract(direct_heat, conv_mat_in))

                dtemp_mat_dt = np.nan_to_num(np.divide(partial_m, kwargs['Cm'][idx1]))
                dtemp_mat = np.nan_to_num(np.multiply(dtemp_mat_dt, kwargs['step_size']))
                kwargs['temp_mat'][idx1] = np.nan_to_num(np.add(kwargs['temp_mat'][idx1], dtemp_mat))
                counter += inc

        n_active = np.flatnonzero(kwargs['connected']==0)
        kwargs['temp_in_active'] = np.multiply(kwargs['temp_in'], kwargs['connected'])
        kwargs['temp_in_active'][n_active] = np.multiply(kwargs['temp_in'][n_active], np.nan)

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



def broadcast(**kwargs):
    # Tell peers about my demand and flexibility
    try:
        # for t in np.unique(kwargs['load_type']):

        kwargs['dict_states_self'].update( 
            {   "load_type": kwargs['load_type'],
               "load_class": kwargs['load_class'],
                "name": kwargs['name'],
                "isotime": kwargs['isotime'],
                "unixtime": kwargs['unixtime'], 
                "hour_start": kwargs['hour_start'],
                "hour_end": kwargs['hour_end'],
                "unix_start": kwargs['unix_start'],
                "unix_end": kwargs['unix_end'],
                "n_usage": kwargs['n_usage'],
                "connected": kwargs['connected'],
                "house": kwargs['house'],
                "flexibility": kwargs['flexibility'],
                "soc": kwargs['soc'],
                "priority": kwargs['priority'],
                "mode": kwargs['mode'],
                "p_demand": kwargs['p_demand'],
                "a_demand": kwargs['a_demand'],
                "limit": kwargs['limit'],
                "p_status": kwargs['p_status'],
                "a_status": kwargs['a_status'],
                "can_ramp": kwargs['can_ramp'],
                "can_shed": kwargs['can_shed'],
                "ramp_power": kwargs['ramp_power'],
                "shed_power": kwargs['shed_power'],
                "ldc_signal": kwargs['ldc_signal'],
                "temp_in": kwargs['temp_in'],
                "temp_in_active": kwargs['temp_in_active'],
                "temp_out": kwargs['temp_out'],
                "cooling_setpoint": kwargs['cooling_setpoint'],
                "heating_setpoint": kwargs['heating_setpoint'],
                "tolerance": kwargs['tolerance'],
                "temp_min": kwargs['temp_min'],
                "temp_max": kwargs['temp_max'],
                "humidity": kwargs['humidity'],
                "windspeed": kwargs['windspeed'],
                "irradiance": kwargs['irradiance'],
                "irradiance_roof": kwargs['irradiance_roof'],
                "irradiance_wall1": kwargs['irradiance_wall1'],
                "irradiance_wall2": kwargs['irradiance_wall2'],
                "irradiance_wall3": kwargs['irradiance_wall3'],
                "irradiance_wall4": kwargs['irradiance_wall4'],
                "solar_capacity": kwargs['solar_capacity'],
                "solar_efficiency": kwargs['solar_efficiency']
            }
            
        )


    except Exception as e:
        print("Error COMMON broadcast:", e)
        
    # try:
    #     while kwargs['q_states_self'].empty() is False:
    #         kwargs['q_states_self'].get(block=False)
    #         kwargs['q_states_self'].task_done()
    #     kwargs['q_states_self'].put(kwargs['dict_states_self'], block=False)

    # except Exception as e:
    #     print("Error in COMMON  broadcast:", e)
    #     pass 

    return kwargs




def query(dict_states_all):
    # Ask peers about their demand and flexibility
    try:
        dict_msg = {house:'p'}
        dict_states_all_new = MULTICAST.send(dict_msg, ip='224.0.2.0', port=10000)
        dict_states_all.update(dict_states_all_new)
        dict_states_all.update(dict_states_self)
        # dict_states_all = delete_past(dict_states_all, latest=10)
        # while q_states_all.empty() is False:
        #     q_states_all.get()
        #     q_states_all.task_done()
        # q_states_all.put(dict_states_all)
        return dict_states_all

        # df_demand = pd.DataFrame.from_dict(dict_states_all, orient='index')
        # df_demand = df_demand.loc[(df_demand['house']==house)]
        # df_demand[['p_demand', 'a_demand', 'flexibility','priority']] = df_demand[['p_demand', 'a_demand', 'flexibility','priority']].astype(float)
        # # print(df_demand[['type', 'p_demand','a_demand','p_status','a_status','flexibility']])

        # try:  # get command details 
        #     dict_grid_cmd.update({
        #         'algorithm':df_demand[df_demand['type']=='baseload']['algorithm'].values[0], 
        #         'frequency':df_demand[df_demand['type']=='baseload']['signal'].values[0], 
        #         'loading':df_demand[df_demand['type']=='baseload']['limit'].values[0], 
        #         'timescale':df_demand[df_demand['type']=='baseload']['timescale'].values[0]
        #         })
        #     while q_grid_cmd.empty() is False:
        #         q_grid_cmd.get()
        #         q_grid_cmd.task_done()
        #     q_grid_cmd.put(dict_grid_cmd)
            
        # except Exception as e:
        #     # print("Error in COMMON  query ldc_signal:", e)
        #     pass

        # try: # get weather details, for a TCL (except heatpump, temp_out is the inside temperature of the house 
        #     if (load_type=='hvac') or (load_type=='waterheater' and location=='outside'):
        #         temp_out = df_demand[df_demand['type']=='baseload']['temp_out'].values[0]
        #     else:
        #         temp_out = df_demand[df_demand['type']=='hvac']['temp_in'].values[0]

        # except Exception as e:
            # print("Error in COMMON  query To:", e)
            # temp_out = 20.0
            # pass
            # return {}

    except Exception as e:
        print("Error in COMMON  query:", e)
        return {}
        # return pd.DataFrame(columns=['id','p_demand','a_demand','flexibility','priority'])


def adjust_counter(**kwargs):
    # adjust the counter for heating or cooling
    try:
        idx1 = np.flatnonzero((kwargs['a_status']!=kwargs['old_status']) | 
            ((kwargs['load_type']=='ntcl')&((kwargs['a_status']!=kwargs['old_status'])|(kwargs['counter']>=kwargs['len_profile'])))
            )
        idx2 = np.flatnonzero((kwargs['a_status']==kwargs['old_status'])&(kwargs['mode']==0) | 
            ((kwargs['load_type']=='ntcl')&(kwargs['a_status']==kwargs['old_status'])&(kwargs['counter']<np.subtract(kwargs['len_profile'], 1)))
            )
        idx3 = np.flatnonzero((kwargs['a_status']==kwargs['old_status'])&(kwargs['mode']==1))

        if np.size(idx1): 
            kwargs['cooling_counter'][idx1] = 0
            kwargs['heating_counter'][idx1] = 0
            kwargs['charging_counter'][idx1] = 0
            kwargs['discharging_counter'][idx1] = 0
            kwargs['counter'][idx1] = 0
        if np.size(idx2): 
            kwargs['cooling_counter'][idx2] += kwargs['step_size']
            kwargs['charging_counter'][idx2] += kwargs['step_size']
            kwargs['counter'][idx2] = np.clip(np.add(kwargs['counter'][idx2], kwargs['step_size']), a_min=0, a_max=np.subtract(kwargs['len_profile'][idx2], 1))
        if np.size(idx3): 
            kwargs['heating_counter'][idx3] += kwargs['step_size']
            kwargs['discharging_counter'][idx3] += kwargs['step_size']

        
    except Exception as e:
        print("Error in COMMON  adjust_counter:", e)

    return kwargs


def adjust_priority(**kwargs):
    try:
        ### random prioritization
        # if kwargs['unixtime']%60==0: kwargs['priority'] = np.random.choice(np.arange(0,100,0.1), size=len(kwargs['priority']))
        
        
        ### flexibility-based prioritization,
        kwargs['priority'] = np.clip(np.multiply(100, kwargs['flexibility']), a_min=0, a_max=100)
    
        ### hybrid: flexibility + random
        # kwargs['priority'] = np.clip(np.add(np.multiply(130, kwargs['flexibility']), np.random.normal(0, 3, len(kwargs['priority']))), a_min=0, a_max=1000)

    except Exception as e:
        print("Error adjust_priority:", e)

    return kwargs


def interpret_signal(**kwargs):
    try:
        kwargs['ldc_command'] = np.divide(np.subtract(kwargs['ldc_signal'], kwargs['limit']),100.0)
        
    except Exception as e:
        print("Error interpret_signal:", e)
    return kwargs


def adjust_limit(**kwargs):
    # adjust group's power limit using the ldc signal
    try:
        ### integral limit adjustment: this provides delay as the offset builds up
        # kwargs['limit'] += kwargs['ldc_command']
        # kwargs['limit'] = np.clip(kwargs['limit'], a_min=0, a_max=100)  # upper limit is 100 which is the maximum priority 
        
        # ### direct limit adjustment
        kwargs['limit'] = kwargs['ldc_signal']
        
    except Exception as e:
        print("Error in COMMON adjust_limit:", e)

    return kwargs


def get_a_status(**kwargs):
    try:
        idx1 = np.flatnonzero(((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['priority'] <= kwargs['limit'])&(kwargs['can_ramp']==1))) # TCL can_ramp
        
        idx2 = np.flatnonzero(((kwargs['load_class']=='tcl')&(kwargs['priority'] <= kwargs['limit'])&(kwargs['can_ramp']==0)) | # TCL can't ramp
                            ((kwargs['load_class']=='tcl')&(kwargs['priority'] > kwargs['limit'])&(kwargs['can_shed']==0)) | # TCL can't shed
                            ((kwargs['load_class']=='ntcl')&(kwargs['priority'] <= kwargs['limit'])&(kwargs['job_status']>0)) | # NTCL can't delay
                            ((kwargs['load_class']=='battery')&(kwargs['priority'] <= kwargs['limit'])) |  # Battery can't shed
                            (kwargs['ldc']==0)
            )

        idx3 = np.flatnonzero(((kwargs['ldc']==1)&(kwargs['load_class']=='tcl')&(kwargs['priority'] > kwargs['limit'])&(kwargs['can_shed']==1)) | # TCL can shed
                            ((kwargs['ldc']==1)&(kwargs['load_class']=='ntcl')&(kwargs['priority'] > kwargs['limit'])&(kwargs['job_status']<=0)) | # NTCL can delay
                            ((kwargs['ldc']==1)&(kwargs['load_class']=='battery')&(kwargs['priority'] > kwargs['limit']))  # Battery can shed
            )

        if np.size(idx1): kwargs['a_status'][idx1] = 1
        if np.size(idx2): kwargs['a_status'][idx2] = kwargs['p_status'][idx2]
        if np.size(idx3): kwargs['a_status'][idx3] = 0

    except Exception as e:
        print("Error in COMMON get_a_status:", e)

    return kwargs



# def receive_signal(ldc_signal, kwargs['algorithm']):
#     # Receive ldc signal
#     old_signal = ldc_signal

#     # get the latest ldc signal
#     try:
#         # ldc_signal = dict_grid_cmd['frequency']
#         ldc_signal = read_spi()
        
#     except Exception as e:
#         # print("Error in COMMON receive_signal:", e)
#         while q_grid_cmd.empty() is False:  # q_grid_cmd is only used in the house module
#             dict_grid_cmd = q_grid_cmd.get()
#             q_grid_cmd.task_done()
#         algorithm = dict_grid_cmd['algorithm']
#         ldc_signal = dict_grid_cmd['frequency']

#     w = 0.9 #np.random.choice(np.arange(0.3, 0.6, 0.01))
#     ldc_signal = (ldc_signal * w) + (old_signal * (1-w))
#     delta_signal = ldc_signal - old_signal

#     return algorithm, ldc_signal, delta_signal


# def detect_signal():
#     # detect the ldc signal using gpio
#     frequency = 0
#     current_time = time.perf_counter()
#     previous_time = time.perf_counter()
    
#     try:  
#         while True:
#             GPIO.wait_for_edge(21, GPIO.RISING)
#             current_time = time.perf_counter()
#             frequency = 1 / (current_time-previous_time)
#             previous_time = current_time
            
        
#     finally:                   
#         GPIO.cleanup()         # clean up the GPIO to reset mode


# @np.vectorize
# def interpret_signal(algorithm, ldc_signal, delta_signal, 
#     minval=0.0, maxval=1.0, ldc_upper=100, ldc_lower=0):
#     # convert ldc signal to a ldc command
#     # signal value ranges from 760 to 860 Hz 
#     try:
#         if algorithm==0: # no ldc
#             # houses and appliances operate normally
#             ldc_command = 1

#         elif algorithm==1:  # basic ldc
#             # ldc_signal is divided into 20 steps, i.e., step0: 760-764.99, step1: 765-769.99, ... step19: 855-859.99
#             # each step corresponds to load priority, i.e., 0...19
#             # when ldc_signal is 760-764.99 Hz, loads with priority 0 will turn ON, 
#             # as the ldc_signal ramps up to 860 Hz, loads with corresponding priority will turn ON as well.
#             ldc_command = (((ldc_signal - ldc_lower) / (ldc_upper-ldc_lower)) * (maxval-minval)) + minval  

#         # elif algorithm==2:
#         #     # Signal corresponds to the offset deviation from the target load demand
#         #     # when target is hit, the ldc injector sends mid frequency, ldc_command is zero, and limit is not adjusted
#         #     # when loading is below target, ldc sends frequency above mid_freq, ldc_command is positive, limit is increased
#         #     # when loading is above target, ldc sends frequency below mid_freq, ldc_command is negative, limit is decreased
#         #     mid_freq = np.mean([ldc_lower,ldc_upper])
#         #     ldc_command = (ldc_signal - mid_freq) / (ldc_upper-ldc_lower)

#         # elif algorithm==2:
#         #     # look at the change in ldc_signal which should correspond to change in limit
#         #     ldc_command = delta_signal / (ldc_upper - ldc_lower)

#         elif algorithm in [2, 3]:
#             # Signal means the target percent loading of the transformer
#             # limit is adjusted to the target percentage
#             ldc_command = (((ldc_signal - ldc_lower) / (ldc_upper-ldc_lower)) * (maxval-minval)) + minval

#         else:
#             ldc_command = 1
        
        
#     except Exception as e:
#         print("Error in COMMON interpret_signal:",e)

#     return ldc_command



# def adjust_limit(**kwargs):
#     # adjust group's power limit using the ldc signal
#     try:
#         idx1 = np.flatnonzero((kwargs['algorithm']==0))
#         idx2 = np.flatnonzero((kwargs['algorithm']==1))
#         idx3 = np.flatnonzero((kwargs['algorithm']==2) | (kwargs['algorithm']==3))

#         if np.size(idx1): kwargs['limit'][idx1] = kwargs['house_capacity'][idx1]
#         if np.size(idx2): kwargs['limit'][idx2] = np.multiply(kwargs['house_capacity'][idx2], kwargs['ldc_command'][idx2])
#         if np.size(idx3): kwargs['limit'][idx3] += np.multiply(kwargs['house_capacity'][idx3], kwargs['ldc_command'][idx3])
        
#     except Exception as e:
#         print("Error in COMMON adjust_limit:", e)

#     return kwargs





# def get_user_cmd():
#     while True:
#         try:
#             # Create a TCP/IP socket
#             sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#             # Connect the socket to the port where the server is listening
#             try:
#                 s_ip = local_ip.split('.')
#                 home_server_ip = str(s_ip[0]) + '.' + str(s_ip[1]) + '.' + str(s_ip[2]) + '.3' 
#                 server_address = (home_server_ip, 30000)
#                 sock.connect(server_address)

#             except Exception as e:
#                 server_address = (local_ip, 30000)
#                 sock.connect(server_address)
                
#             # send message
#             sock.sendall(str(dict_states_self).encode("utf-8"))
            
#             # receive response
#             data = sock.recv(2**16)
#             message = data.decode("utf-8").replace("'", "\"")
#             dict_msg = json.loads(message)
#             # update user command
#             while q_user_cmd.empty() is False:
#                 dict_user_cmd = q_user_cmd.get()
#                 q_user_cmd.task_done()

#             dict_user_cmd.update(dict_msg)
#             q_user_cmd.put(dict_user_cmd)

#             # time.sleep(1/timescale)

#             return dict_user_cmd

#         except Exception as e:
#             return {'status':1, 'priority':0, 'schedule':{}}

#         finally:
#             # print('closing socket')
#             sock.close()



# #--- BACKGROUND THREADS ---
# def receive_mcast():
#     # Receive multicast message from the group
#     while  True:
#         try:
#             multicast_ip = mcast_ip_local
#             port = mcast_port_local

#             multicast_group = (multicast_ip, port)  # (ip_address, port)

#             # Create the socket
#             sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
#             sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#             # Bind to the server address
#             sock.bind(multicast_group)

#             # Tell the operating system to add the socket to
#             # the multicast group on all interfaces.
#             group = socket.inet_aton(multicast_ip)
#             mreq = struct.pack('4sL', group, socket.INADDR_ANY)
#             sock.setsockopt(
#                 socket.IPPROTO_IP,
#                 socket.IP_ADD_MEMBERSHIP,
#                 mreq)
#             break
#         except Exception as e:
#             print("Error in COMMON  receive_mcast binding socket:",e)
    
#     dict_toSend_self = {}
#     dict_toSend_all = {}
#     # Receive/respond loop
#     while True:
#         # receive and decode message
#         data, address = sock.recvfrom(1024)
#         received_msg = data.decode("utf-8")
#         dict_msg = ast.literal_eval(received_msg)
        
#         # prepare data to send, fetch latest data from the queue
#         try:
#             # Note: house name is used as the key, 'all' is a query from the aggregator  
#             key = list(dict_msg)[0]
#             if key in [house, "all"]:          
#                 if dict_msg[key] in ["proposed", "p"]:
#                     while q_states_self.empty() is False:
#                         dict_onQueue = q_states_self.get(block=False)
#                         q_states_self.task_done()
#                     q_states_self.put(dict_onQueue)
#                     dict_toSend_self.update(dict_onQueue)
#                     message_toSend = str(dict_toSend_self).encode()
#                     sock.sendto(message_toSend, address)
#                 else:
#                     pass

#             elif key==name:
#                 while  q_states_all.empty() is False:
#                     dict_onQueue = q_states_all.get(block=False)
#                     q_states_all.task_done()
#                 q_states_all.put(dict_onQueue)
#                 dict_toSend_all.update(dict_onQueue)
#                 message_toSend = str(dict_toSend_all).encode()
#                 sock.sendto(message_toSend, address)

#                 # update user command
#                 while q_user_cmd.empty() is False:
#                     dict_user_cmd = q_user_cmd.get()
#                     q_user_cmd.task_done()
#                 dict_user_cmd.update(dict_msg[name])
#                 q_user_cmd.put(dict_user_cmd)
#             else:
#                 pass
                
#         except Exception as e:
#             print("Error in COMMON  receive_mcast:", e)
#             pass                      
#     return


# def receive_mcast_global():
#     # Receive multicast message from the group
#     while True:
#         try:
#             multicast_ip = mcast_ip_global
#             port = mcast_port_global

#             multicast_group = (multicast_ip, port)  # (ip_address, port)

#             # Create the socket
#             sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
#             sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#             # Bind to the server address
#             sock.bind(multicast_group)

#             # Tell the operating system to add the socket to
#             # the multicast group on all interfaces.
#             group = socket.inet_aton(multicast_ip)
#             mreq = struct.pack('4sL', group, socket.INADDR_ANY)
#             sock.setsockopt(
#                 socket.IPPROTO_IP,
#                 socket.IP_ADD_MEMBERSHIP,
#                 mreq)
#             break
#         except Exception as e:
#             print("Error in COMMON  receive_mcast_global:",e)

    
#     # Receive/respond loop
#     while True:
#         # receive and decode message
#         data, address = sock.recvfrom(1024)
#         received_msg = data.decode("utf-8")
#         dict_msg = ast.literal_eval(received_msg)
#         # prepare data to send, fetch latest data from the queue
#         try:
#             # Note: house name is used as the key, 'all' is a query from the aggregator  
#             for key in dict_msg:    
#                 if key in [house, "all"]:          
#                     if dict_msg[key]=="id":
#                         dict_toSend = {name: {
#                             'house':house,
#                             'name': name,
#                             'type': load_type,
#                             'local_ip': FUNCTIONS.get_local_ip(),
#                             'public_ip': FUNCTIONS.get_public_ip(),
#                             'mcast_port_global': mcast_port_global,
#                             'mcast_ip_global': mcast_ip_global,
#                             'mcast_port_local': mcast_port_local,
#                             'mcast_ip_local': mcast_ip_local, 
                    
#                             }
#                         }

#                         message_toSend = str(dict_toSend).encode()
#                         # send message
#                         sock.sendto(message_toSend, address)

#                     else:
#                         pass
#                 else:
#                     pass
#         except Exception as e:
#             print("Error in COMMON  receive_mcast:", e)
#             pass                      
#     return


# def detect_signal():
#     # detect the ldc signal using gpio
#     frequency = 0
#     current_time = time.perf_counter()
#     previous_time = time.perf_counter()
    
#     try:  
#         while True:
#             GPIO.wait_for_edge(21, GPIO.RISING)
#             current_time = time.perf_counter()
#             frequency = 1 / (current_time-previous_time)
#             previous_time = current_time
        
#     finally:                   
#         GPIO.cleanup()         # clean up the GPIO to reset mode


# def read_spi():
#     '''Read data via spi'''
#     try:
#         r = spi.readbytes(1)
#         return float(r[0])
#     except Exception as e:
#         return 0  # device is non-ldc capable


# def drive_relay():
#     # turn on / off the relay
#     try:
#         status = int(a_status)
#         if relay_status!=status:
#             GPIO.output(relay_pin, status)
#             relay_status = status
#         else:
#             pass
#     except Exception as e:
#         # print(relay_status, a_status)
#         # print("Error drive_relay:", e)
#         pass



# def drive_chroma():
#     # Send data to Chroma variable load simulator
#     # through serial interface (rs232)
#     try:
#         rs232 = serial.Serial(
#             port='/dev/ttyUSB0',
#             baudrate = 57600,
#             parity=serial.PARITY_NONE,
#             stopbits=serial.STOPBITS_ONE,
#             bytesize=serial.EIGHTBITS,
#             timeout=1
#             )
        
#         chroma_load = actual_power - baseload
#         # print("Chroma:", chroma_load)

#         rs232.write(b'CURR:PEAK:MAX 28\r\n')
#         rs232.write(b'MODE POW\r\n')
#         rs232.write(b'LOAD ON\r\n')
#         cmd = 'POW '+ str(chroma_load) +'\r\n'
#         rs232.write(cmd.encode())
#     except Exception as e:
#         pass
#     return 

# def drive_piface():
#     try:
#         # convert baseload value into 8-bit binary to drive 8 pinouts of piface
#         newpins = FUNCTIONS.relay_pinouts(grainy_load, df_relay, df_states, report=False)
#         # print("Grainy:")
#         for i in range(len(pins)):
#             if pins[i]==0 and newpins[i]==1:
#                 pf.output_pins[i].turn_on()
#             elif pins[i]==1 and newpins[i]==0:
#                 pf.output_pins[i].turn_off()
#             else:
#                 pass
#         pins = newpins
#     except:
#         pass
#     return

# def run_device():
#     drive_chroma()
#     drive_piface()
#     drive_relay()
#     simulate_model()
#     # do other stuff
#     return

# def step():
#     # simulation step for the house and all loads therein
#     while True:
#         try:
#             clock.step()
#             propose_demand()
#             decide()
#             update_demand()
#             run_device()
#             # time.sleep(1/timescale)
#         except Exception as e:
#             # print("Error in COMMON  step:", e)
#             pass
        
# def __del__():
#     try:
#         GPIO.cleanup()         # clean up the GPIO to reset mode
#     except Exception as e:
#         print("Error in COMMON __del__:", e)






# # funtions for heating / cooling calculations (rule of thumb)
# #@numba.jit(nopython=True, parallel=True, nogil=True)
# def get_heating_power(floor_area):
#     '''Calculate the heating rate as a function of the floor area using the "rule-of-thumb"
#     Rating is based on the study done by Energy Star: http://www.energystar.gov/index.cfm?c=roomac.pr_properly_sized
#     Input:
#         floor_area = the floor area of a the room [m^2]
#     Output:
#         heating_rate = typical heating rate of the given floor area [W]
    
#     # assumption:
#     # 15 BTU/h/ft^2, typical rating of HVAC heating at places of lower latitude, 
#     # colder places may have 50 to 60 BTU/h/ft^2
#     1/(3.28**2)  # conversion factor from square feet to square meter
#     1/3.412141633 # conversion factor from BTU/h to watts
#     '''
#     return float(floor_area) * (15 * (1/3.412141633))/(1/(3.28**2))  # in Watts

# #@numba.jit(nopython=True, parallel=True, nogil=True)
# def get_cooling_power(floor_area):
#     '''This function calculates the cooling rate based on a given area using the "rule-of-thumb"
#     Input:
#         floor_area = floor are of the room [m^2]
#     Output:
#         cooling = cooling power [W]

#     rating is based on the study done by Energy Star: 
#     http://www.energystar.gov/index.cfm?c=roomac.pr_properly_sized
#     '''
#     floor_area = float(floor_area)
#     cf1 = 1/(3.28**2)  # conversion factor from square feet to square meter
#     cf2 = 1/3.412141633 # conversion factor from BTU/h to watts
    
#     if  floor_area < (150*cf1):
#         return 5000*cf2
#     elif (150*cf1) <= floor_area < (250*cf1):
#         return 6000*cf2
#     elif (250*cf1) <= floor_area < (300*cf1):
#         return 7000*cf2
#     elif (300*cf1) <= floor_area < (350*cf1):
#         return 8000*cf2
#     elif (350*cf1) <= floor_area < (400*cf1):
#         return 9000*cf2
#     elif (400*cf1) <= floor_area < (450*cf1):
#         return 10000*cf2
#     elif (450*cf1) <= floor_area < (550*cf1):
#         return 12000*cf2
#     elif (550*cf1) <= floor_area < (700*cf1):
#         return 14000*cf2
#     elif (700*cf1) <= floor_area < (1000*cf1):
#         return 18000*cf2
#     elif (1000*cf1) <= floor_area < (1200*cf1):
#         return 21000*cf2
#     elif (1200*cf1) <= floor_area < (1400*cf1):
#         return 23000*cf2
#     elif (1400*cf1) <= floor_area < (1500*cf1):
#         return 24000*cf2
#     elif (1500*cf1) <= floor_area < (2000*cf1):
#         return 30000*cf2
#     elif (2000*cf1) <= floor_area < (2500*cf1):
#         return 34000*cf2
#     elif (2500*cf1) <= floor_area < (3000*cf1):
#         return 38000*cf2
#     elif (3000*cf1) <= floor_area < (3500*cf1):
#         return 42000*cf2
#     else:
#         return 50000*cf2

