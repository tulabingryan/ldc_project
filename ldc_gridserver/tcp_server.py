

import socket
import struct
import sys, os
import time, datetime
import numpy as np
import pandas as pd
import csv
import glob
from optparse import OptionParser
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
import serial.tools.list_ports
import METER
import INJECTOR
import SERVER


class TcpServer(multiprocessing.Process):
    def __init__(self, ip, port, report=0):
        multiprocessing.Process.__init__(self)
        self.daemon = True

        self.name = "xmer_monitor"
        self.report = report
        self.tcp_ip = ip
        self.tcp_port = port
        self.mcast_ip = '224.0.2.3'
        self.mcast_port = 17001
        self.multicast = False
        self.dict_serialports = self.get_ports()
        self.port_meters = self.dict_serialports['PID=0403']
        self.port_injector = self.dict_serialports['PID=067B']

        self.manager = multiprocessing.Manager()
        self.dict_all = self.manager.dict()
        self.dict_all.update({'algorithm':'basic_ldc', 'set_target':'auto'})
        self.dict_common = self.manager.dict()
        self.dict_common.update({"is_alive":True})
        self.dict_meter = self.manager.dict()
        self.dict_injector = self.manager.dict()
        
        self.df_all = pd.DataFrame([])
        self.df_agg = pd.DataFrame([])
        self.agg_demand = 0
        self.agg_loading = 0
        self.agg_frequency = 860
        self.inactive_nodes = []
        self.pause = 1e-16

        # SERVER.ThreadedServer.__init__(self, self.tcp_ip, self.tcp_port)
        self.meter = METER.EnergyMeter(house=1001, IDs=[1,2,3], autorun=False)
        self.injector = INJECTOR.LdcInjector()

        # initialize communication to serial port and spi
        try:
          self.spi = spidev.SpiDev()
          self.spi.open(0, 0)  #(bus, device)
          self.spi.bits_per_word = 8
          self.spi.max_speed_hz = 500000
          self.spi.mode = 3
        except:
          pass

        self.autorun()


    @staticmethod
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

    

    def collect_data_meter(self):
        print("Collecting microgrid data_meter...")
        while self.dict_common['is_alive']:
            try:
                self.dict_meter.update(self.meter.get_meter_data(params=['power_active','powerfactor', 'voltage', 'frequency']))
                time.sleep(self.pause)
            except Exception as e:
                print("Error in tcp_server.collect_data_meter:", e)
                raise e
            except BrokenPipeError:
                break
            except KeyboardInterrupt:
                break
        print("Stopped collect_data_meter...")


    def collect_data_injector(self):
        print("Collecting microgrid data_injector...")
        d = {}
        while self.dict_common['is_alive']:
            try:
                new_data = self.injector.read_ldc_injector()
                if new_data:
                    self.dict_injector.update(new_data)
                    d.update({datetime.datetime.now():new_data})
                    
                time.sleep(self.pause)
            except Exception as e:
                print("Error tcp_server.collect_data_injector:", e)
                raise e
            except BrokenPipeError:
                break
            except KeyboardInterrupt:
                break
        print("Stopped collect_data_injector...")


    def collect_data_all(self):
        print("Aggregate data from meter and injector...")
        # list_p_kw = []
        avg_w = None
        a = 1/3600

        while self.dict_common['is_alive']:
            try:
                if self.dict_meter:
                    self.dict_all.update(self.dict_meter)
                    # update running avg
                    # list_p_kw.append(self.dict_all['power_kw'])
                    # list_p_kw = list_p_kw[-3600:]  # maintain 3600 records
                    # avg = np.mean(list_p_kw) * 1000  # [watts]
                    
                    if avg_w==None:
                        avg_w = self.dict_all['power_kw'] * 1000
                    else:
                        avg_w = (avg_w*(1-a)) + (a*self.dict_all['power_kw']*1000)

                    if ((self.dict_all['set_target']=='auto')): # and (int(time.time())%300==0)):
                        self.injector.write_ldc_injector('s {}'.format(avg_w))
                        self.dict_all.update({"target_watt": avg_w})
                  
                if self.dict_injector:
                    self.dict_all.update(self.dict_injector)

                if self.report: 
                    print(self.dict_all)

                time.sleep(self.pause)
            except Exception as e:
                print("Error tcp_server.collect_data_all:", e)
                time.sleep(1)
            except BrokenPipeError:
                break
            except KeyboardInterrupt:
                break
        print("Stopped collect_data_all...")

    def save_data(self):
        print("Saving data...")
        dict_save = {}
        while self.dict_common['is_alive']:
            try:
                now = datetime.datetime.now()
                unixtime = now.timestamp()
                today = now.strftime("%Y_%m_%d")
                dict_save.update({unixtime:self.dict_all.copy()})
                
                if len(dict_save.keys())>10:
                    dict_save = self.save_pickle(dict_data=dict_save, path=f'/home/pi/ldc_project/history/T1_{int(time.time()*1000)}.pkl.xz')
                # self.df_all = pd.DataFrame.from_dict(self.dict_all, orient='index').T
                # if len(self.df_all.index):
                #   ### save csv melted format
                #   df_agg = pd.melt(self.df_all.astype(str), id_vars=["unixtime"], var_name="parameter", value_name="value")
                #   dt = datetime.datetime.fromtimestamp(float(self.dict_all['unixtime']))
                  
                #   filename = dt.strftime(f'/home/pi/ldc_project/history/T1_%Y_%m_%d.csv')
                #   with open(filename, 'a') as f:
                #     df_agg.to_csv(f, mode='a', header=f.tell()==0, index=False)
                #     time.sleep(1)
                time.sleep(0.5)
            except Exception as e:
                print("Error tcp_server.save_data:", e)
                pass
            except BrokenPipeError:
                break
            except KeyboardInterrupt:
                break
        print("Stopped save_data...")


    def save_feather(self, dict_data):
        try:
            df_all = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            try:
                on_disk = pd.read_feather(f'/home/pi/ldc_project/history/injector_{today}.feather').reset_index(drop=True)
                df_all = pd.concat([on_disk, df_all], axis=0).reset_index(drop=True)
            except Exception as e:
                # print(e)
                pass
            df_all.to_feather(f'/home/pi/ldc_project/history/injector_{today}.feather')
            
            return {}
        except Exception as e:
            print("Error data_logger.save_feather:", e)
            return dict_data


    def save_pickle(self, dict_data, path='history/data.pkl'):
        'Save data as pickle file.'
        try:
            df_all = pd.DataFrame.from_dict(dict_data, orient='index')#.reset_index(drop=True)
            df_all.to_pickle(path, compression='infer')
            # try:
            #     on_disk = pd.read_pickle(path, compression='infer').reset_index(drop=True)
            #     df_all = pd.concat([on_disk, df_all], axis=0, sort=False).reset_index(drop=True)
            #     df_all = df_all.groupby('unixtime').mean().reset_index(drop=False)
            #     # df_all['unixtime'] = df_all['unixtime'].astype(int)
            #     df_all.to_pickle(path, compression='infer')
            # except Exception as e:
            #     df_all.to_pickle(path, compression='infer')
        
            return {}
        except Exception as e:
            print("Error tcp_server.save_pickle:", e)
            return {} # dict_data 



    def save_hdf(self, dict_data):
        try:
            df = pd.DataFrame.from_dict(dict_data, orient='index')
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            df.to_hdf(f'/home/pi/ldc_project/history/injector_{today}.h5', 
                    key=f'injector', 
                    mode='a', 
                    append=True, 
                    complib='blosc', 
                    complevel=9, 
                    format='table')
            return {}
        except Exception as e:
            print("Error tcp_server.save_hdf:", e)
            return dict_data

    def read_spi(self):
        try:
            # read spi
            r = self.spi.readbytes(1)
            return r[0]
        except Exception as e:
            print("Error:", e)
            return 

    def connect_udp_socket(self, ip, port, multicast=True):
        'Setup socket connection'
        while True:
            try:
                if multicast: ip=self.mcast_ip
                udp_address_port = (ip, port)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # sock.settimeout(60)  
                sock.bind(udp_address_port)
                if multicast:
                    group = socket.inet_aton(ip)
                    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,mreq)
                print(f'socket created: {udp_address_port}')
                return sock
            except Exception as e:
                print("Error in AGGREGATOR.connect_udp_socket:",e)
                print("Retrying...")
                time.sleep(3)


    def udp_com(self):
        udp_sock = self.connect_udp_socket(ip=self.tcp_ip, port=self.tcp_port, multicast=False)
        
        translate_cmd = {"s":"target_watt", "o":"signal", "k":"gain"}

        # Receive/respond loop
        while self.dict_common['is_alive']:
            dict_response= {}
            # receive and decode message
            data, address = udp_sock.recvfrom(1024)
            received_msg = data.decode("utf-8").replace("'", "\"")
            dict_msg = json.loads(received_msg)
            
            try:
                keys = dict_msg.keys()
        
                if 'states' in keys:
                    k = dict_msg['states']
                    if k=='all':
                        message_toSend = str(self.dict_all).replace("'", "\"").encode()
                        udp_sock.sendto(message_toSend, address)
                    elif k in self.dict_all.keys():
                        message_toSend = str({k:self.dict_all[k]}).encode()
                        udp_sock.sendto(message_toSend, address)
          
                if 'cmd' in keys:
                    k, value = dict_msg['cmd'].split()
                    self.dict_all.update({translate_cmd[k]:float(value), 'unixtime':time.time()})
                    ### write command to ldc injector serial port
                    self.injector.write_ldc_injector(dict_msg['cmd'])
                    ### send confirmation
                    message_toSend = str({'cmd':dict_msg['cmd']}).encode()
                    udp_sock.sendto(message_toSend, address)
          
                if 'algorithm' in keys:
                    self.dict_all.update({"algorithm":dict_msg["algorithm"]})
                    message_toSend = str({"target_watt":self.dict_all["target_watt"]}).encode()
                    udp_sock.sendto(message_toSend, address)

                if 'set_target' in keys:
                    self.dict_all.update({"set_target":dict_msg["set_target"]})
                    message_toSend = str({"set_target":self.dict_all["set_target"]}).encode()
                    udp_sock.sendto(message_toSend, address)

            except BrokenPipeError:
                break
            except Exception as e:
                print("Error in tcp_server.udp_com: ", e)
    

    def tcp_comm(self):
        try:
            # Create a TCP/IP socket
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Bind the socket to the port
            server_address = (self.tcp_ip, self.tcp_port)
            print('starting tcp_comm on {} port {}'.format(*server_address))
            tcp_sock.bind(server_address)
            # Listen for incoming connections
            tcp_sock.listen(50)

            translate_cmd = {"s":"target_watt", "o":"signal", "k":"gain"}

            while self.dict_common['is_alive']:
                connection, client_address = tcp_sock.accept()  # wait for connection
                try:
                    while self.dict_common['is_alive']:
                        data = connection.recv(int(2**12))  # wait for data
                        
                        if data:
                            message = data.decode("utf-8").replace("'", "\"")
                            dict_msg = json.loads(message)
                            try:
                                keys = dict_msg.keys()
                                
                                if 'states' in keys:
                                    k = dict_msg['states']
                                    if k=='all':
                                        message_toSend = str(self.dict_all).replace("'", "\"").encode()
                                        
                                    elif k in self.dict_all.keys():
                                        message_toSend = str({k:self.dict_all[k]}).encode()              
                                    ### send data
                                    connection.sendall(message_toSend)
                          
                                if 'cmd' in keys:
                                    k, value = dict_msg['cmd'].split()
                                    self.dict_all.update({translate_cmd[k]:float(value), 'unixtime':time.time()})
                                    ### write command to ldc injector serial port
                                    self.injector.write_ldc_injector(dict_msg['cmd'])
                                    ### send confirmation
                                    message_toSend = str({'cmd':dict_msg['cmd']}).encode()
                                    ### send data
                                    connection.sendall(message_toSend)
                          
                                if 'algorithm' in keys:
                                    self.dict_all.update({"algorithm":dict_msg["algorithm"]})
                                    message_toSend = str({"target_watt":self.dict_all["target_watt"]}).encode()
                                    ### send data
                                    connection.sendall(message_toSend)
                          
                                if 'set_target' in keys:
                                    self.dict_all.update({"set_target":dict_msg["set_target"]})
                                    message_toSend = str({"set_target":self.dict_all["set_target"]}).encode()
                                    ### send data
                                    connection.sendall(message_toSend)
                          

                            except BrokenPipeError:
                                break
                            except Exception as e:
                                print("Error tcp_server.tcp_comm:", e)
                          
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




    def autorun(self):
        self.threads = [threading.Thread(target=self.collect_data_meter, args=())]
        self.threads.append(threading.Thread(target=self.collect_data_injector, args=()))
        self.threads.append(threading.Thread(target=self.collect_data_all, args=()))
        self.threads.append(threading.Thread(target=self.save_data, args=()))
        self.threads.append(threading.Thread(target=self.udp_com, args=()))
        # self.threads.append(threading.Thread(target=self.tcp_comm, args=()))

        # run threads
        for t in self.threads:
            t.daemon = True
            t.start()

        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print('\nTerminating all processes..')
                for i in range(10):
                    self.dict_common['is_alive'] = False
                time.sleep(1)  # delay to wait for other threads
                break

  

    def __del__(self):
        self.dict_common.update({"is_alive":False})
        print("Deleted:", self.name)
        for t in self.list_processes:
            if t.is_alive():
                t.terminate()
        





if __name__=="__main__":
    parser = OptionParser(version=' ')
    parser.add_option('--report', dest='report', default=0, help='show data during tests and troubleshooting')
    options, args = parser.parse_args(sys.argv[1:])
    report = int(options.report)
  
    while  True:
        try:
            local_ip = IP.get_local_ip()
            if local_ip:
                S = TcpServer(local_ip, 10000, report=report)
            else:
                local_ip = "192.168.1.3"
                S = TcpServer(local_ip, 10000, report=report)
        except Exception as e:
            print("Error main:", e)
        except KeyboardInterrupt:
            S.dict_common.update({"is_alive":False})
            break
        finally:
            try:
                del S
            except:
                pass
            time.sleep(5)





  # def get_cmd(self):
  #   target_loading = float(self.cmd_loading) * 1000 # converted to Watts
  #   # try:
  #   #     if latest_demand == None: raise Exception
  #   # except Exception as e:
  #   #     if len(self.df_agg.index) > 0:
  #   #         n_houses = len(self.df_agg.index)
  #   #         latest_demand = self.df_agg['actual'].sum()
  #   #     else:
  #   #         n_houses = 1
  #   #         latest_demand = 10000

  #   #     gridUtilizationFactor =  1 #0.8**(0.9 * np.log(n_houses))
  #   #     capacity = n_houses * 10000 * gridUtilizationFactor #[kW]

  #   latest_demand = self.agg_demand
  #   capacity = 30000
    
  #   percent_loading = target_loading / capacity
    
  #   try:
  #     offset = np.nan_to_num(1 - (latest_demand / (target_loading)))

  #   except Exception as e:
  #     print("Error in getting offset value:",e)
  #     offset = 0

  #   ldc_upper = 860
  #   ldc_lower = 760
  #   ldc_center = 810 
  #   ldc_bw = ldc_upper - ldc_lower  # bandwidth
  #   w_past = 0.1  # weight given to the past signal, acting as a damper to change in ldc_signal

  #   try:
  #     if self.cmd_algorithm==0:
  #       self.ldc_signal=ldc_upper

  #     elif self.cmd_algorithm==1:
  #       self.ldc_signal = float(760 + (ldc_bw * percent_loading))
  #       self.ldc_signal = np.min([self.ldc_signal, 860])
  #       self.ldc_signal = np.max([self.ldc_signal, 760])
    
  #     elif self.cmd_algorithm==2:
  #       self.ldc_signal_new = float(ldc_center + ((ldc_bw) * offset * 0.1))
  #       self.ldc_signal = (w_past * self.ldc_signal) + ((1-w_past) * self.ldc_signal_new)
  #       self.ldc_signal = np.min([self.ldc_signal, 860])
  #       self.ldc_signal = np.max([self.ldc_signal, 760])

  #     elif self.cmd_algorithm == 3:
  #       self.ldc_signal = float(760 + (ldc_bw * percent_loading))
  #       self.ldc_signal = np.min([self.ldc_signal, 860])
  #       self.ldc_signal = np.max([self.ldc_signal, 760])
    
  #     else: # default is 2
  #       self.ldc_signal_new = float(ldc_center + ((ldc_bw) * offset))
  #       self.ldc_signal = (w_past * self.ldc_signal) + ((1-w_past) * self.ldc_signal_new)
  #       self.ldc_signal = np.min([self.ldc_signal, 860])
  #       self.ldc_signal = np.max([self.ldc_signal, 760])

  #     self.dict_cmd = {self.cmd_algorithm:self.ldc_signal}
  #     # print(self.dict_cmd, latest_demand, target_loading, offset)
  #     return self.dict_cmd

  #   except Exception as e:
  #     print("Error in get_cmd:", e)

















  # def tcp_comm(self):
  #   try:
  #     # Create a TCP/IP socket
  #     tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
  #     # Bind the socket to the port
  #     server_address = (self.tcp_ip, self.tcp_port)
  #     print('starting up on {} port {}'.format(*server_address))
  #     tcp_sock.bind(server_address)
    
  #     # Listen for incoming connections
  #     tcp_sock.listen(500)

  #     count = 0  # counter for feedback printing
  
  
  #     while True:
  #       # Wait for a connection
  #       # print('waiting for a connection')

  #       connection, client_address = tcp_sock.accept()
  #       try:
  #         # Receive the data in small chunks and retransmit it
  #         while True:
  #           # fetch dict_cmd to queue
  #           while self.q_cmd.empty() is False:
  #             self.dict_cmd = self.q_cmd.get()
  #             self.q_cmd.task_done()
  #           self.q_cmd.put(self.dict_cmd)  # return the latest data to queue


  #           data = connection.recv(int(2**12))
  #           if data:
  #             message = data.decode("utf-8").replace("'", "\"")
  #             dict_msg = json.loads(message)
        
        
  #             if list(dict_msg)[0] in ['algorithm', 'loading', 'frequency', 'timescale', 'unixstart', 'unixend']:
  #               # # reply: latest aggregated data
  #               # connection.sendall(str(self.dict_all).encode())
  #               # # update command settings
  #               # self.dict_cmd.update(dict_msg)
  #               # print(self.dict_cmd)    
  #               pass
  #             # elif list(dict_msg)[0] in ['cmd']:
  #             #     key = list(dict_msg)[0]
  #             #     self.injector.write_ldc_injector(dict_msg[key])
  #             #     message_toSend = str('Command confirmed: ' + dict_msg[key]).encode()
  #             #     connection.sendall(message_toSend)
  #             #     print(message_toSend)
  #             else:
  #               # reply: ldc command settings
  #               connection.sendall(str(self.dict_cmd).encode())
  #               self.dict_all.update(dict_msg)
  #               # if count >= 100:
  #               #     count = 0
  #               #     print(self.dict_cmd)
  #               # else:
  #               #     count += 1   
        
  #           else:
  #             connection.close()
  #             break




  #         # delete obsolete data in the dictionary
  #         # dict_local = {}
  #         # for key in list(self.dict_all):
  #         #     if self.dict_all[key]['unixtime'] > (time.time() - 60):
  #         #         dict_local.update({key:self.dict_all[key]})
  #         #     else:
  #         #         pass
  #         # self.dict_all = dict_local

  #         # print(self.dict_all)
  #         # save dict_agg to queue
  #         while self.q_all.empty() is False:
  #           self.q_all.get()
  #           self.q_all.task_done()
  #         self.q_all.put(self.dict_all)

       
      

  #       except Exception as e:
  #         print("Error in tcp_server receive_msg:", e)
  #         print(dict_msg)
  #         connection.close()
      
      
  #       finally:
  #         # Clean up the connection
  #         connection.close()

  #   except Exception as e:
  #     print(time.time(), "Error in tcp_server connect:",e)
  #     tcp_sock.shutdown(socket.SHUT_RDWR)
  #     tcp_sock.close()
  #     self.__del__()
    

  #   finally:
  #     tcp_sock.shutdown(socket.SHUT_RDWR)
  #     tcp_sock.close()




  # def gui_responder(self):
  #   try:
  #     # Create a TCP/IP socket
  #     tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
  #     # Bind the socket to the port
  #     server_address = (self.tcp_ip, 10000)
  #     print('starting up on {} port {}'.format(*server_address))
  #     tcp_sock.bind(server_address)
    
  #     # Listen for incoming connections
  #     tcp_sock.listen(10)
  
  
  #     while True:
  #       # Wait for a connection
  #       # print('waiting for a connection')
  #       connection, client_address = tcp_sock.accept()
  #       try:
  #         # Receive the data in small chunks and retransmit it
  #         while True:
  #           self.read_ldc_injector()

  #           # fetch dict_cmd to queue
  #           while self.q_cmd.empty() is False:
  #             self.dict_cmd = self.q_cmd.get()
  #             self.q_cmd.task_done()
  #           self.q_cmd.put(self.dict_cmd)  # return the latest data to queue


  #           data = connection.recv(int(2**12))
  #           if data:
  #             message = data.decode("utf-8").replace("'", "\"")
  #             dict_msg = json.loads(message)
        
  #             if list(dict_msg)[0] in ['algorithm', 'loading', 'frequency', 'timescale', 'unixstart', 'unixend']:
  #               # reply: latest aggregated data
  #               if dict_msg['unixstart']==0:
  #                 while self.q_agg.empty() is False:
  #                   dict_response = self.q_agg.get()
  #                   self.q_agg.task_done()
  #                 self.q_agg.put(dict_response)  # return data to queue
  #                 message_toSend = str(dict_response).replace("'", "\"").encode()
  #               else:
  #                 df_data = self.read_db(start=dict_msg['unixstart'], end=dict_msg['unixend'])
  #                 dict_response = df_data.to_dict(orient='index')
  #                 message_toSend = str(dict_response).replace("'", "\"").encode()

  #               connection.sendall(message_toSend)
  #               print(message_toSend)
        
  #             elif list(dict_msg)[0] in ['cmd']:
  #               key = list(dict_msg)[0]
  #               self.injector.write_ldc_injector(dict_msg[key])
  #               message_toSend = str('Command confirmed: ' + dict_msg[key]).encode()
  #               connection.sendall(message_toSend)
  #               print(message_toSend)
  #             else:
  #               pass   
        
  #           else:
  #             connection.close()
  #             break




  #           # # delete obsolete data in the dictionary
  #           # self.df_agg = pd.DataFrame.from_dict(self.dict_all['houses'], orient='index')
  #           # self.df_agg = self.df_agg[self.df_agg['unixtime'] > (time.time() - 60)]
  #           # self.dict_all['houses'] = self.df_agg.to_dict(orient='index')


  #           # save dict_agg to queue
  #           while self.q_all.empty() is False:
  #             self.q_all.get()
  #             self.q_all.task_done()
  #           self.q_all.put(self.dict_all)

      

  #       except Exception as e:
  #         print("Error in tcp_server receive_msg:", e)
  #         print(dict_msg)
  #         connection.close()
      
      
  #       finally:
  #         # Clean up the connection
  #         connection.close()

  #   except Exception as e:
  #     print(time.time(), "Error in tcp_server connect:",e)
  #     tcp_sock.shutdown(socket.SHUT_RDWR)
  #     tcp_sock.close()
  #     raise Exception

