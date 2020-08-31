import socket
import struct
import sys, os
import time, datetime
import numpy as np
import pandas as pd
import csv
import glob
from dateutil.parser import parse
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError
import requests
import sqlite3 as lite
import IP
import threading, queue
import multiprocessing
import json, ast
import serial
import serial.tools.list_ports



def get_ports(report=False):
    # get list of serial ports and the id of the connected device
    ports = serial.tools.list_ports.comports()
    dict_ports = {}
    for port, desc, hwid in sorted(ports):
            try:
                hardware_id = hwid.split(':')[1]
                dict_ports[hardware_id] = port
            except:
                pass
    if report: print(dict_ports)

    return dict_ports






class LdcInjector(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.daemon = True

        self.name = "ldc_injector"

        self.mcast_ip = '224.0.2.3'
        self.mcast_port = 16003
        self.dict_serialports = get_ports()
        self.port_meters = self.dict_serialports['PID=0403']
        self.port_injector = self.dict_serialports['PID=067B']
        self.ser = ser = serial.Serial(
                port=self.port_injector,
                baudrate = 38400,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.5
                )


        self.dict_data = {}
        # self.q_data = queue.Queue(maxsize=10)
        # self.q_data.put(self.dict_data)
        
        self.df_data = pd.DataFrame([])
        self.power_kw = 0
        self.agg_loading = 0
        self.agg_frequency = 860
        
  


    def get_ldc_data(self, report=False):
        self.dict_data.update(self.read_ldc_injector())
        self.df_data = pd.concat([self.df_data, pd.DataFrame.from_dict(self.dict_data, orient='index').T]).reset_index(drop=True)
        self.df_data = self.df_data.groupby('unixtime', as_index=False).mean().tail(50)
        self.df_data['localtime'] = pd.to_datetime(self.df_data['unixtime'], unit='s')
        self.df_data = self.df_data.tail(3600*24)
        
        if report: print(self.df_data)

        return self.dict_data


    
    
    def read_ldc_injector(self, report=False):
        # read data from rs232
        dict_data = {}
        
        try:
            while True:
                try:
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
             
                    response = self.ser.readline().decode('utf-8')
                    p, power, csum, k, x = response.split()
                    # print(p, power, csum, k, x)

                    dict_data.update({
                        "unixtime": time.time(),
                        "power_kw": float(power) * 1e-3,
                        "csum": float(csum),
                        "signal": min([float(x)*(-0.199733273641597) + 1798.24514853189, 850.0]), 
                        "k": float(k),
                        })
                    
                    if report:print(dict_data)

                    self.power_kw = dict_data['power_kw']
                    break

                except KeyboardInterrupt:
                    break
                except BrokenPipeError:
                    break
                except Exception as e:
                    #print("Error read_ldc_injector loop:", e)
                    dict_data = {}

            return dict_data

        except Exception as e:
            print("Error read_ldc_injector:", e)
            return None
            
    def save_feather(self, dict_data):
        try:
          df_all = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True)
          today = datetime.datetime.now().strftime("%Y-%m-%d")
          try:
            on_disk = pd.read_feather(f'/home/pi/ldc_project/history/t1_{today}.feather').reset_index(drop=True)
            df_all = pd.concat([on_disk, df_all], axis=0).reset_index(drop=True)
          except Exception as e:
            # print(e)
            pass
          df_all.to_feather(f'history/{today}.feather')
          return {}
        except Exception as e:
          print("Error data_logger.save_feather:", e)
          return dict_data

    def write_ldc_injector(self, msg, port='/dev/ttyUSB0'):
        # send data to serial port
        try:
            # ser = serial.Serial(
            #     port=self.port_injector,
            #     baudrate = 38400,
            #     parity=serial.PARITY_NONE,
            #     stopbits=serial.STOPBITS_ONE,
            #     bytesize=serial.EIGHTBITS,
            #     timeout=0.1
            #     )

            self.ser.flushInput()
            self.ser.flushOutput()
            s_msg = list(msg)
            for s in s_msg:
                self.ser.write(s.encode('ascii'))
                time.sleep(0.01)
            self.ser.write(b'\r')
            time.sleep(0.5)

        except Exception as e:
            print("Error write_ldc_injector:", e)
            pass


    # def respond_to_query(self):
    #     # Receive query and send dict_data as a response (running as a separate thread)
    #     multicast_ip = self.mcast_ip
    #     port = self.mcast_port

    #     multicast_group = (multicast_ip, port)  # (ip_address, port)

    #     # Create the socket
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    #     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #     # Bind to the server address
    #     sock.bind(multicast_group)

    #     # Tell the operating system to add the socket to
    #     # the multicast group on all interfaces.
    #     group = socket.inet_aton(multicast_ip)
    #     mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    #     sock.setsockopt(
    #         socket.IPPROTO_IP,
    #         socket.IP_ADD_MEMBERSHIP,
    #         mreq)
        
    #     dict_toSend = {}
        
    #     # Receive/respond loop
    #     while True:
    #         # receive and decode message
    #         data, address = sock.recvfrom(1024)
    #         received_msg = data.decode("utf-8")
    #         dict_msg = ast.literal_eval(received_msg)
    #         # prepare data to send, fetch latest data from the queue
    #         try:
    #             if list(dict_msg)[0] in ['power']:
    #                 # fetch latest data on queue        
    #                 while self.q_data.empty() is False:
    #                     dict_onQueue = self.q_data.get()
    #                     self.q_data.task_done()
    #                 # self.q_data.put(dict_onQueue)  # return latest data on queue to avoid empty queue
                    
    #                     dict_toSend.update(dict_onQueue)
    #                     message_toSend = str(dict_toSend).encode('utf-8')
    #                     # send message
    #                     sock.sendto(message_toSend, address)

    #             else:
    #                 pass
                
    #         except Exception as e:
    #             print("Error respond_to_query:", e)
                
    #     return



        

if __name__=="__main__":
    LDC = LdcInjector()
    while True:
        try:
            LDC.get_ldc_data(report=True)
        except Exception as e:
            print("Error:", e)
            
            time.sleep(1)
        except BrokenPipeError:
            break
        except KeyboardInterrupt:
            break



