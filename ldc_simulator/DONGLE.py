#############################################################
# Codes for the main file to simulate Aggregation of Flexible Loads
# by: Ryan Tulabing
# University of Auckland, 2017
#############################################################

import sys, os
import time, datetime
import csv, json
import numpy as np
import sqlite3 as lite
import pandas as pd

from scipy import stats
from multiprocessing import Process, Manager, Pool
import threading, queue

import pytz  # timezone

# for the grainy load controller, raspi3
try:
    import pifacedigitalio
    pf = pifacedigitalio.PiFaceDigital()
    # for driving chroma through rs232
    import serial
except:
    pass

# for dongles, raspi0
try:
    # for interacting with raspi
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)     # set up BOARD GPIO numbering 
    # for reading spi
    import spidev
except Exception as e:
    print("Error importing GPIO, spidev",e)



# for internet query
from dateutil.parser import parse
import urllib.request
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

# for multicast
import socket
import struct
import sys
import json
import ast

# import created classes and functions
from LOAD import *
import MULTICAST
import FUNCTIONS
import SENSIBO


class Dongle(multiprocessing.Process):
    """docstring for Dongle"""
    def __init__(self, dict_devices, idx):
        super(Dongle, self).__init__()
        
        multiprocessing.Process.__init__(self)
        self.daemon = True


        # initialization to drive output pin for onboard relay
        self.relay_status = 0
        self.relay_pin = 15
        try:
            GPIO.setup(self.relay_pin, GPIO.OUT)
        except:
            pass

        try:
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)  # (bus, device)
            self.spi.bits_per_word = 8
            self.spi.max_speed_hz = 500000
            self.spi.mode = 3
        except Exception as e:
            print("Error initializing spi:",e)
            pass
            
        # initialization to drive the pifacedigital
        self.pins = [0,0,0,0,0,0,0,0]
        try:
            self.pf = pifacedigitalio.PiFaceDigital()
        except:
            pass

        
        self.q_states_self = queue.Queue(maxsize=10)  # queue for data of the device
        self.q_states_all = queue.Queue(maxsize=10)  # queue for data of peers
        self.q_user_cmd = queue.Queue(maxsize=10)  # queue for holding the user-command on the state of the date (overiding the auto mode)
        self.q_grid_cmd = queue.Queue(maxsize=10)
        self.q_house_agg = queue.Queue(maxsize=10)  # queue to respond to EMULATOR, i.e., grainy load

        
        self.dict_states_self = {}
        self.dict_states_all = {}
        self.dict_user_cmd = {}
        self.dict_grid_cmd = {}
        self.dict_house_agg = {}

        self.q_states_self.put(self.dict_states_self)
        self.q_states_all.put(self.dict_states_all)
        self.q_user_cmd.put(self.dict_user_cmd)
        self.q_grid_cmd.put(self.dict_grid_cmd)
        self.q_house_agg.put(self.dict_house_agg)

        # create network of houses, main() is a function from LOAD 
        self.appliance = make_devices(dict_devices=dict_devices, idx=idx, capacity=30, loading=0.5,
                                start=int(time.time()), step_size=1, realtime = True,
                                timescale=1, three_phase=True, simulate=0, renew=0,
                                latitude=-36.866590076725494, longitude=174.77534779638677,
                                mcast_ip_local='238.173.254.147', mcast_port_local = 12604,
                            )

        self.name = self.appliance.App.name[0]
        self.house = self.appliance.App.house[0]
        self.load_type = self.appliance.App.load_type[0]
        self.house_num = int(''.join(list(self.house)[3:]))

        # if self.load_type=='hvac' and self.house_num in [2, 3, 4, 5]:
        #     self.sensibo_api = SENSIBO.SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
        #     devices = self.sensibo_api.devices()
        #     self.uid = devices['ldc_heatpump_h{}'.format(int(self.house_num))]

        #     self.appliance.App.__dict__['temp_in'][0] = self.sensibo_api.pod_history(self.uid)['temperature'][-1]['value']
        #     self.appliance.App.__dict__['temp_mat'][0] = self.appliance.App.__dict__['temp_in'][0]

        #     self.drive_sensibo()

        # else:
        #     pass

        print("Running {}...".format(self.name))
        # # run separate threads
        # thread_1 = threading.Thread(target=self.mcast_listener, args=())
        # thread_1.daemon = True                         # Daemonize thread
        # thread_1.start() 

        # # run separate threads
        # thread_2 = threading.Thread(target=self.step, args=())
        # thread_2.daemon = True                         # Daemonize thread
        # thread_2.start() 
        
        self.step()

    def step(self):
        ### main thread running the model
        while True:
            try:
                # get ldc signal
                self.ldc_signal = self.read_signal(report=True)
                t = time.perf_counter()
                # run simulation
                self.appliance.step(ldc_signal=self.ldc_signal)
                print(time.perf_counter()- t)
                
                # turn ON/OFF relay
                self.drive_relay(int(self.appliance.App.a_status[0]))

                # # for hvac, change temp_in based on actual reading
                # if self.load_type=='hvac' and self.house_num in [2,3,4,5,]: 
                #     self.drive_sensibo()
                # else:
                #     pass

                # # for water heater, change temp_in based on actual reading
                # if self.load_type=='waterheater' and self.house_num in [2,3,4,5]: 
                #     self.query_waterheater()
                # else:
                #     pass

                # # update data to be sent to grainy load
                # # prohibit water heater and hvac to send power emulation to grainy load
                # factor = (self.load_type not in ['hvac', 'waterheater'])*1
            
                # self.dict_house_agg.update({self.appliance.App.name[0]:
                #         {
                #             'unixtime': np.mean(self.appliance.App.unixtime),
                #             'house': self.appliance.App.house[0],
                #             'p_mw': self.appliance.df_agg.sum_a_mw.values[0] * factor,
                #             'q_mvar': self.appliance.df_agg.sum_a_mvar.values[0] * factor,
                #         }
                #     }
                # )                
                # # update queue for multicast response
                # if self.q_house_agg.full():
                #     self.q_house_agg.get(block=False)  # remove one item
                #     self.q_house_agg.task_done()  # release blocking
                #     self.q_house_agg.put(self.dict_house_agg)  # put one item on queue
                # else:
                #     self.q_house_agg.put(self.dict_house_agg)  # put one item on queue
                
                # # update queue to be sent to data logger for home_server
                # self.dict_states_self.update({self.appliance.App.name[0]:
                #     {   
                #         "load_type": self.appliance.App.__dict__['load_type'][0],
                #         "load_class": self.appliance.App.__dict__['load_class'][0],
                #         "name": self.appliance.App.__dict__['name'][0],
                #         "unixtime": self.appliance.App.__dict__['unixtime'], 
                #         "house": self.appliance.App.__dict__['house'][0],
                #         "flexibility": self.appliance.App.__dict__['flexibility'][0],
                #         "soc": self.appliance.App.__dict__['soc'][0],
                #         "priority": self.appliance.App.__dict__['priority'][0],
                #         "a_demand": self.appliance.App.__dict__['a_demand'][0],
                #         "a_status": self.appliance.App.__dict__['a_status'][0],
                #         "temp_in": self.appliance.App.__dict__['temp_in'][0],
                #         "humidity": self.appliance.App.__dict__['humidity'][0],
                #         "windspeed": self.appliance.App.__dict__['windspeed'][0],
                #         "temp_out": self.appliance.App.__dict__['temp_out'][0],
                #         "ldc_signal": self.appliance.App.__dict__['ldc_signal'][0],
                #         # "hour_start": self.appliance.App.__dict__['hour_start'][0],
                #         # "hour_end": self.appliance.App.__dict__['hour_end'][0],
                #         # "unix_start": self.appliance.App.__dict__['unix_start'][0],
                #         # "unix_end": self.appliance.App.__dict__['unix_end'][0],
                #         # "n_usage": self.appliance.App.__dict__['n_usage'][0],
                #         # "connected": self.appliance.App.__dict__['connected'][0],
                #         # "mode": self.appliance.App.__dict__['mode'][0],
                #         # "p_demand": self.appliance.App.__dict__['p_demand'][0],
                #         # "limit": self.appliance.App.__dict__['limit'][0],
                #         # "p_status": self.appliance.App.__dict__['p_status'][0],
                #         # "can_ramp": self.appliance.App.__dict__['can_ramp'][0],
                #         # "can_shed": self.appliance.App.__dict__['can_shed'][0],
                #         # "ramp_power": self.appliance.App.__dict__['ramp_power'][0],
                #         # "shed_power": self.appliance.App.__dict__['shed_power'][0],
                #         # "temp_in_active": self.appliance.App.__dict__['temp_in_active'][0],
                #         # "cooling_setpoint": self.appliance.App.__dict__['cooling_setpoint'][0],
                #         # "heating_setpoint": self.appliance.App.__dict__['heating_setpoint'][0],
                #         # "tolerance": self.appliance.App.__dict__['tolerance'][0],
                #         # "temp_min": self.appliance.App.__dict__['temp_min'][0],
                #         # "temp_max": self.appliance.App.__dict__['temp_max'][0],
                #         # "irradiance": self.appliance.App.__dict__['irradiance'][0],
                #         # "irradiance_roof": self.appliance.App.__dict__['irradiance_roof'][0],
                #         # "irradiance_wall1": self.appliance.App.__dict__['irradiance_wall1'][0],
                #         # "irradiance_wall2": self.appliance.App.__dict__['irradiance_wall2'][0],
                #         # "irradiance_wall3": self.appliance.App.__dict__['irradiance_wall3'][0],
                #         # "irradiance_wall4": self.appliance.App.__dict__['irradiance_wall4'][0],
                #         # "solar_capacity": self.appliance.App.__dict__['solar_capacity'][0],
                #         # "solar_efficiency": self.appliance.App.__dict__['solar_efficiency'[0]]
                #     }
                # })

                # if self.q_states_self.full():
                #     self.q_states_self.get(block=False)  # remove one item on queue
                #     self.q_states_self.task_done()  # release blocking
                #     self.q_states_self.put(self.dict_states_self)  # put one item on queue
                # else:
                #     self.q_states_self.put(self.dict_states_self)  # put one item on queue

                # # print('q_house_agg:', self.q_house_agg.qsize())    
                # # print('q_states_self:', self.q_states_self.qsize())

            except Exception as e:
                print("Error DONGLE step:", e)
            except KeyboardInterrupt:
                break

    def drive_sensibo(self):        
        # get actual temp readings
        self.appliance.App.__dict__['temp_in'][0] = self.sensibo_api.pod_history(self.uid)['temperature'][-1]['value']
        
        # get actual state of heat pump
        self.ac_state = self.sensibo_api.pod_ac_state(self.uid)
        
        # change status
        if self.appliance.App.__dict__['a_status'][0]==1 and self.ac_state['on']==False:
            self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "on", True) 
        elif self.appliance.App.__dict__['a_status'][0]==0 and self.ac_state['on']==True:
            self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "on", False)
        else:
            pass

        # change mode if needed
        if self.appliance.App.__dict__['mode'][0]==1 and self.ac_state['mode']=='cool':
            self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "mode", 'heat')
            self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "targetTemperature", self.appliance.App.__dict__['heating_setpoint'][0])
        elif self.appliance.App.__dict__['mode'][0]==0 and self.ac_state['mode']=='heat':
            self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "mode", 'cool')
            self.sensibo_api.pod_change_ac_state(self.uid, self.ac_state, "targetTemperature", self.appliance.App.__dict__['cooling_setpoint'][0])
        else:
            pass

    
    def query_waterheater(self):

        pass
        

    

    def read_signal(self, report=False):
        # Receive ldc signal
        try:
            s = self.read_spi()  # read signal detector
            if s > 0:
                self.ldc_signal = s 
            else:
                self.ldc_signal = 100  # no signal, hence, loads can consume as they need

            if report: print('ldc_signal:', self.ldc_signal)
        except Exception as e:
            self.ldc_signal = 100
            
        return self.ldc_signal


    def read_spi(self):
        '''Read data via spi, currently used for ldc_signal'''
        try:
            r = self.spi.readbytes(1)
            return float(r[0])
        except Exception as e:
            return 0


    def drive_relay(self, status):
        # turn on / off the relay
        try:
            if self.relay_status!=status:
                GPIO.output(self.relay_pin, status)
                self.relay_status = status
            else:
                pass
        except Exception as e:
            # print(self.relay_status, self.a_status)
            print("Error drive_relay:", e)
            pass



    
    def __del__(self):
        try:
            # GPIO.cleanup()         # clean up the GPIO to reset mode
            print("deleted:", self.name)    
        except Exception as e:
            print("Error in ", self.load_type, " __del__:", e)
            pass


    # def get_user_cmd(self):
    #     while True:
    #         try:
    #             # Create a TCP/IP socket
    #             sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #             # Connect the socket to the port where the server is listening
    #             try:
    #                 s_ip = self.local_ip.split('.')
    #                 home_server_ip = str(s_ip[0]) + '.' + str(s_ip[1]) + '.' + str(s_ip[2]) + '.3' 
    #                 server_address = (home_server_ip, 30000)
    #                 sock.connect(server_address)

    #             except Exception as e:
    #                 server_address = (self.local_ip, 30000)
    #                 sock.connect(server_address)
                    
    #             # send message
    #             sock.sendall(str(self.dict_states_self).encode("utf-8"))
                
    #             # receive response
    #             data = sock.recv(2**16)
    #             message = data.decode("utf-8").replace("'", "\"")
    #             dict_msg = json.loads(message)
    #             # update user command
    #             while self.q_user_cmd.empty() is False:
    #                 self.dict_user_cmd = self.q_user_cmd.get()
    #                 self.q_user_cmd.task_done()

    #             self.dict_user_cmd.update(dict_msg)
    #             self.q_user_cmd.put(self.dict_user_cmd)

    #             # time.sleep(1/self.timescale)

    #             return self.dict_user_cmd

    #         except Exception as e:
    #             return {'status':1, 'priority':0, 'schedule':{}}

    #         finally:
    #             # print('closing socket')
    #             sock.close()

    # def query(self):
    #     # Ask peers about their demand and flexibility
    #     try:
    #         dict_msg = {self.house:'p'}
    #         dict_states_all_new = MULTICAST.send(dict_msg, ip=self.mcast_ip_local, port=self.mcast_port_local)
    #         print(dict_states_all_new)
    #         self.dict_states_all.update(dict_states_all_new)
    #         self.dict_states_all.update(self.dict_states_self)
    #         self.dict_states_all = self.delete_past(self.dict_states_all, latest=10)
    #         while self.q_states_all.empty() is False:
    #             self.q_states_all.get()
    #             self.q_states_all.task_done()
    #         self.q_states_all.put(self.dict_states_all)

    #         df_demand = pd.DataFrame.from_dict(self.dict_states_all, orient='index')
    #         df_demand = df_demand.loc[(df_demand['house']==self.house)]
    #         df_demand[['p_demand', 'a_demand', 'flexibility','priority']] = df_demand[['p_demand', 'a_demand', 'flexibility','priority']].astype(float)
    #         # print(df_demand[['type', 'p_demand','a_demand','p_status','a_status','flexibility']])

    #         try:  # get command details 
    #             self.dict_grid_cmd.update({
    #                 'algorithm':df_demand[df_demand['type']=='baseload']['algorithm'].values[0], 
    #                 'frequency':df_demand[df_demand['type']=='baseload']['signal'].values[0], 
    #                 'loading':df_demand[df_demand['type']=='baseload']['limit'].values[0], 
    #                 'timescale':df_demand[df_demand['type']=='baseload']['timescale'].values[0]
    #                 })
    #             while self.q_grid_cmd.empty() is False:
    #                 self.q_grid_cmd.get()
    #                 self.q_grid_cmd.task_done()
    #             self.q_grid_cmd.put(self.dict_grid_cmd)
                
    #         except Exception as e:
    #             # print("Error in ", self.name, " query ldc_signal:", e)
    #             pass

    #         try: # get weather details, for a TCL (except heatpump, temp_out is the inside temperature of the house 
    #             if (self.load_type=='hvac') or (self.load_type=='waterheater' and self.location=='outside'):
    #                 self.temp_out = df_demand[df_demand['type']=='baseload']['temp_out'].values[0]
    #             else:
    #                 self.temp_out = df_demand[df_demand['type']=='hvac']['temp_in'].values[0]

    #         except Exception as e:
    #             # print("Error in ", self.name, " query To:", e)
    #             self.temp_out = 20.0
    #             pass

    #         return df_demand
    #     except Exception as e:
    #         print("Error in ", self.name, " query:", e)
    #         return pd.DataFrame(columns=['id','p_demand','a_demand','flexibility','priority'])







    #--- BACKGROUND THREADS ---
    def mcast_listener(self):
        # Receive multicast message from the group
        counter = 0
        while  True:
            try:
                multicast_ip = '238.173.254.147'
                port=12604
                multicast_group = (multicast_ip, port)  # (ip_address, port)
                # Create the socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Bind to the server address
                sock.bind(multicast_group)

                # Tell the operating system to add the socket to
                # the multicast group on all interfaces.
                group = socket.inet_aton(multicast_ip)
                mreq = struct.pack('4sL', group, socket.INADDR_ANY)
                sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    mreq)
                break
            except Exception as e:
                print("Error in ", self.name, " mcast_listener binding socket:",e)
        
        dict_toSend_self = {}
        dict_toSend_all = {}
        dict_toSend_house = {}
        # Receive/respond loop
        while True:
            # receive and decode message
            data, address = sock.recvfrom(1024)
            received_msg = data.decode("utf-8")
            dict_msg = ast.literal_eval(received_msg)
            
            # prepare data to send, fetch latest data from the queue
            try:
                # Note: house name is used as the key, 'all' is a query from the aggregator  
                key = list(dict_msg)[0]
                
                
                if key in [self.house, "all"]:          
                    if dict_msg[key] in ["h"]:  # response to home_server
                        if self.q_states_self.empty():
                            # print('q_states_self is empty ')
                            time.sleep(0.1)
                        else:
                            dict_onQueue = self.q_states_self.get(block=False)  # remove one item on queue
                            self.q_states_self.task_done()  # release block
                            dict_toSend_self.update(dict_onQueue)
                            message_toSend_self = str(dict_toSend_self).encode()
                            sock.sendto(message_toSend_self, address)
                            # print("Responded to home_server at:", address)
                        
                    if dict_msg[key] in ["a"]: # response to RESISTORBANK
                        if self.q_house_agg.empty():
                            # print('q_house_agg is empty')
                            time.sleep(0.1)
                        else:
                            dict_onQueue_house = self.q_house_agg.get(block=False)
                            self.q_house_agg.task_done()
                            dict_toSend_house.update(dict_onQueue_house)
                            message_toSend_house = str(dict_toSend_house).encode()
                            sock.sendto(message_toSend_house, address)
                            # print("Responded to RESISTORBANK at:", address)

                    else:
                        pass

                # elif key==self.App.name[0]:
                #     while  self.q_states_all.empty() is False:
                #         dict_onQueue = self.q_states_all.get(block=False)
                #         self.q_states_all.task_done()
                #     self.q_states_all.put(dict_onQueue)
                #     dict_toSend_all.update(dict_onQueue)
                #     message_toSend = str(dict_toSend_all).encode()
                #     sock.sendto(message_toSend, address)

                #     # update user command
                #     while self.q_user_cmd.empty() is False:
                #         self.dict_user_cmd = self.q_user_cmd.get()
                #         self.q_user_cmd.task_done()
                #     self.dict_user_cmd.update(dict_msg[self.name])
                #     self.q_user_cmd.put(self.dict_user_cmd)
                else:
                    pass

                    
            except Exception as e:
                print("Error in DONGLE mcast_listener:", e)
                pass                      
        return


    # def mcast_for_homeserver(self):
    #     # Receive multicast message from the group
    #     while  True:
    #         try:
    #             multicast_ip = '224.0.2.3'
    #             port = 16003
                
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
    #             print("Error in ", self.name, " mcast_for_homeserver binding socket:",e)
        
    #     dict_toSend_self = {}
    #     dict_toSend_all = {}
    #     dict_toSend_house = {}
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
                
    #             if key in [self.house, "all"]:          
    #                 if dict_msg[key] in ["h"]:  # response to home_server
    #                     if self.q_states_self.empty():
    #                         pass
    #                     else:
    #                         dict_onQueue = self.q_states_self.get()  # remove one item on queue
    #                         self.q_states_self.task_done()  # release block
    #                         dict_toSend_self.update(dict_onQueue)
    #                         message_toSend_self = str(dict_toSend_self).encode()
    #                         sock.sendto(message_toSend_self, address)
    #                         print("Responded to home_server at:", address)
                        
    #                 # elif dict_msg[key] in ["a"]: # response to RESISTORBANK
    #                 #     if self.q_house_agg.empty():
    #                 #         pass
    #                 #     else:
    #                 #         dict_onQueue_house = self.q_house_agg.get(block=False)
    #                 #         self.q_house_agg.task_done()
    #                 #         dict_toSend_house.update(dict_onQueue_house)
    #                 #         message_toSend_house = str(dict_toSend_house).encode()
    #                 #         sock.sendto(message_toSend_house, address)
    #                 #         # print("Responded to RESISTORBANK at:", address)

    #                 else:
    #                     pass

    #             # elif key==self.App.name[0]:
    #             #     while  self.q_states_all.empty() is False:
    #             #         dict_onQueue = self.q_states_all.get(block=False)
    #             #         self.q_states_all.task_done()
    #             #     self.q_states_all.put(dict_onQueue)
    #             #     dict_toSend_all.update(dict_onQueue)
    #             #     message_toSend = str(dict_toSend_all).encode()
    #             #     sock.sendto(message_toSend, address)

    #             #     # update user command
    #             #     while self.q_user_cmd.empty() is False:
    #             #         self.dict_user_cmd = self.q_user_cmd.get()
    #             #         self.q_user_cmd.task_done()
    #             #     self.dict_user_cmd.update(dict_msg[self.name])
    #             #     self.q_user_cmd.put(self.dict_user_cmd)
    #             else:
    #                 pass
                    
    #         except Exception as e:
    #             print("Error in DONGLE mcast_for_homeserver:", e)
    #             pass                      
    #     return





    # def detect_signal(self):
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
    

    

def main():
    # function to be called for testing
    local_ip = FUNCTIONS.get_local_ip(report=True)
    idx = int(local_ip.split('.')[2])-1
    while True:
        try:
            # sample run is house baseload
            n = 1  # number of units
            ldc_adoption = 1.0
            dict_devices = {
                'House':{'n':int(n*0), 'ldc':ldc_adoption},
                'Hvac':{'n':int(n*0), 'ldc':ldc_adoption},
                'Heater':{'n':int(n*0), 'ldc':ldc_adoption},
                'Fridge':{'n':int(n*0), 'ldc':ldc_adoption},
                'Freezer':{'n':int(n*0), 'ldc':ldc_adoption},
                'Waterheater':{'n':int(n*1), 'ldc':ldc_adoption},
                'Clotheswasher':{'n':int(n*0), 'ldc':ldc_adoption},
                'Clothesdryer':{'n':int(n*0), 'ldc':ldc_adoption},
                'Dishwasher':{'n':int(n*0), 'ldc':ldc_adoption},
                'Ev':{'n':int(n*0), 'ldc':ldc_adoption, 'v2g':int(n*0.0)},
                'Storage':{'n':int(n*0), 'ldc':ldc_adoption},
                'Solar':{'n':int(n*0), 'ldc':ldc_adoption},
                'Wind':{'n':int(n*0), 'ldc':ldc_adoption},    
                }

            d = Dongle(dict_devices, idx=idx)
        except Exception as e:
            print("Error DONGLE main:", e)
            del d
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    main()