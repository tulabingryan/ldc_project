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
import serial.tools.list_ports
import METER
import INJECTOR
import SERVER


class TcpServer(multiprocessing.Process):
    def __init__(self, ip='192.168.1.76', port=10000):
        multiprocessing.Process.__init__(self)
        self.daemon = True

        self.name = "data_logger"
        self.local_ip = IP.get_local_ip()
        self.tcp_ip = ip
        self.tcp_port = port
        self.mcast_ip = '224.0.2.3'
        self.mcast_port = 16003
        self.dict_serialports = self.get_ports()
        self.port_meters = self.dict_serialports['PID=0403']
        self.port_injector = self.dict_serialports['PID=067B']

        # SERVER.ThreadedServer.__init__(self, self.tcp_ip, self.tcp_port)
        self.meter = METER.EnergyMeter(house='XMER1', IDs=[1,2,3], autorun=False)
        self.injector = INJECTOR.LdcInjector()

        self.dict_all = {}
        self.dict_agg = {}
        self.dict_cmd = {'algorithm':0, 'loading':30, 'frequency':810, 'timescale':1, 'unixstart':0, 'unixend':0}
        self.q_all = queue.Queue(maxsize=10)
        self.q_agg = queue.Queue(maxsize=120)
        self.q_cmd = queue.Queue(maxsize=3)
        self.q_all.put(self.dict_all)
        self.q_agg.put(self.dict_agg)
        self.q_cmd.put(self.dict_cmd)

        self.df_all = pd.DataFrame([])
        self.df_agg = pd.DataFrame([])
        self.agg_demand = 0
        self.agg_loading = 0
        self.agg_frequency = 860
        self.inactive_nodes = []

        # # initialize communication to serial port and spi
        # try:
        #     self.spi = spidev.SpiDev()
        #     self.spi.open(0, 0)  #(bus, device)
        #     self.spi.bits_per_word = 8
        #     self.spi.max_speed_hz = 500000
        #     self.spi.mode = 3
        # except:
        #     pass



        thread = threading.Thread(target=self.send_data, args=())
        thread.daemon = True
        thread.start()

        # thread1 = threading.Thread(target=self.collect_data, args=())
        # thread1.daemon = True
        # thread1.start()

        thread2 = threading.Thread(target=self.receive_mcast, args=())
        thread2.daemon = True
        thread2.start()

        # thread3 = threading.Thread(target=self.gui_responder, args=())
        # thread3.daemon = True
        # thread3.start()

        # self.tcp_comm()
                
        # self.listen(60)
        self.collect_data()


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



    # def tcp_comm(self):
    #     try:
    #         # Create a TCP/IP socket
    #         tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
    #         # Bind the socket to the port
    #         server_address = (self.tcp_ip, self.tcp_port)
    #         print('starting up on {} port {}'.format(*server_address))
    #         tcp_sock.bind(server_address)
            
    #         # Listen for incoming connections
    #         tcp_sock.listen(500)

    #         count = 0  # counter for feedback printing
        
        
    #         while True:
    #             # Wait for a connection
    #             # print('waiting for a connection')

    #             connection, client_address = tcp_sock.accept()
    #             try:
    #                 # Receive the data in small chunks and retransmit it
    #                 while True:
    #                     # fetch dict_cmd to queue
    #                     while self.q_cmd.empty() is False:
    #                         self.dict_cmd = self.q_cmd.get()
    #                         self.q_cmd.task_done()
    #                     self.q_cmd.put(self.dict_cmd)  # return the latest data to queue


    #                     data = connection.recv(int(2**12))
    #                     if data:
    #                         message = data.decode("utf-8").replace("'", "\"")
    #                         dict_msg = json.loads(message)
                            
                            
    #                         if list(dict_msg)[0] in ['algorithm', 'loading', 'frequency', 'timescale', 'unixstart', 'unixend']:
    #                             # # reply: latest aggregated data
    #                             # connection.sendall(str(self.dict_all).encode())
    #                             # # update command settings
    #                             # self.dict_cmd.update(dict_msg)
    #                             # print(self.dict_cmd)    
    #                             pass
    #                         # elif list(dict_msg)[0] in ['cmd']:
    #                         #     key = list(dict_msg)[0]
    #                         #     self.injector.write_ldc_injector(dict_msg[key])
    #                         #     message_toSend = str('Command confirmed: ' + dict_msg[key]).encode()
    #                         #     connection.sendall(message_toSend)
    #                         #     print(message_toSend)
    #                         else:
    #                             # reply: ldc command settings
    #                             connection.sendall(str(self.dict_cmd).encode())
    #                             self.dict_all.update(dict_msg)
    #                             # if count >= 100:
    #                             #     count = 0
    #                             #     print(self.dict_cmd)
    #                             # else:
    #                             #     count += 1   
                                
    #                     else:
    #                         connection.close()
    #                         break




    #                 # delete obsolete data in the dictionary
    #                 # dict_local = {}
    #                 # for key in list(self.dict_all):
    #                 #     if self.dict_all[key]['unixtime'] > (time.time() - 60):
    #                 #         dict_local.update({key:self.dict_all[key]})
    #                 #     else:
    #                 #         pass
    #                 # self.dict_all = dict_local

    #                 # print(self.dict_all)
    #                 # save dict_agg to queue
    #                 while self.q_all.empty() is False:
    #                     self.q_all.get()
    #                     self.q_all.task_done()
    #                 self.q_all.put(self.dict_all)

                       
                        

    #             except Exception as e:
    #                 print("Error in tcp_server receive_msg:", e)
    #                 print(dict_msg)
    #                 connection.close()
                    
                    
    #             finally:
    #                 # Clean up the connection
    #                 connection.close()

    #     except Exception as e:
    #         print(time.time(), "Error in tcp_server connect:",e)
    #         tcp_sock.shutdown(socket.SHUT_RDWR)
    #         tcp_sock.close()
    #         self.__del__()
            

        # finally:
        #     tcp_sock.shutdown(socket.SHUT_RDWR)
        #     tcp_sock.close()


    def collect_data(self):
        count = 0  # counter for feedback printing
        while True:
            try:
                # Get dict_agg from queue
                while self.q_all.empty() is False:
                    self.dict_all = self.q_all.get()
                    self.q_all.task_done()
                self.q_all.put(self.dict_all)  # return latest data to queue

                # get dict_cmd from queue
                while self.q_cmd.empty() is False:
                    self.dict_cmd = self.q_cmd.get()
                    self.q_cmd.task_done()
                self.q_cmd.put(self.dict_cmd)  # return latest data to queue
                self.dict_agg.update(self.dict_cmd)

                # collect data from ldc injector
                try:
                    self.dict_agg.update(self.injector.read_ldc_injector())
                except:
                    print("Error INJECTOR.read_ldc_injector:", e)
                    pass

                # collect data from power meters
                try:
                    self.dict_agg.update(self.meter.get_meter_data(params=['power_active']))
                    self.dict_agg.update(self.meter.get_meter_data(params=['voltage']))
                    # print(self.dict_agg)
                except Exception as e:
                    print("Error METER.read_ldc_injector:", e)
                    pass

                ## put on queue
                while self.q_agg.empty() is False:
                    self.q_agg.get()
                    self.q_agg.task_done()
                self.q_agg.put(self.dict_agg)
                
                for label in list(self.dict_agg):
                    self.df_agg[label] = [self.dict_agg[label]]  

                self.df_agg['id'] = ['XMER1']
                df_agg = pd.melt(self.df_agg, id_vars=["unixtime", "id"], 
                          var_name="parameter", value_name="value")
                df_agg = df_agg.dropna()

                #save to database
                # self.write_db(df_data=df_agg, db_name='./ldc_all.db')



                # # # put on queue
                # if self.q_agg.full():
                #     self.q_agg.get()
                #     self.q_agg.put(self.df_agg.to_dict(orient='index'))  # return latest data to queue
                # else:
                #     self.q_agg.put(self.df_agg.to_dict(orient='index'))

        
            except Exception as e:
                print("Error in collect_data:", e)
                raise e
        
            except KeyboardInterrupt:
                break

    def send_data(self):
        # send collected date via tcp
        last_cmd = ' '
        while  True:
            try:
                # Create a TCP/IP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # try:
                # Connect the socket to the port where the server is listening
                server_address = (self.tcp_ip, 10000)
                sock.connect(server_address)
                # except:
                #     server_address = (self.local_ip, 10000)
                #     sock.connect(server_address)

                # while True:
                # try:
                while self.q_agg.empty() is False:
                    dict_msg = self.q_agg.get()
                    self.q_agg.task_done()
                self.q_agg.put(dict_msg)

                message_toSend = str(dict_msg).replace("'", "\"").encode()
                # send message
                sock.sendall(message_toSend)
                print("SENT:", message_toSend)
                
                # receive response
                data = sock.recv(2**16)
                if data:
                    # received_msg = data.decode("utf-8")
                    received_msg = data.decode("utf-8").replace("'", "\"")
                    dict_cmd = json.loads(received_msg)
                    print('RECEIVED:',dict_cmd)
                    if 'cmd' in list(dict_cmd):
                        # update dict_cmd and put in q_cmd
                        self.dict_cmd.update(dict_cmd)
                        if self.dict_cmd['cmd'] != last_cmd:
                            last_cmd = self.dict_cmd['cmd']
                            self.injector.write_ldc_injector(last_cmd)
                            cmd_loading = float(last_cmd.split()[1])
                            self.dict_cmd.update({'loading': cmd_loading})
                            print(self.dict_cmd)
                            
                        else:
                            pass

                        while self.q_cmd.empty() is False:
                            self.q_cmd.get()
                            self.q_cmd.task_done()
                        self.q_cmd.put(self.dict_cmd)
                        
                    else:
                        pass

                    
                    

                    while self.q_cmd.empty() is False:
                        self.q_cmd.get()
                        self.q_cmd.task_done()
                    self.q_cmd.put(self.dict_cmd)
                else:
                    raise Exception               
                # except Exception as e:
                #     print("finally closing socket:", e)
                      
            except Exception as e:
                print("Error in send_data:", e)
                sock.close()

            finally:
                sock.close()



    def read_spi(self):
        try:
            # read spi
            r = self.spi.readbytes(1)
            return r[0]
        
        except Exception as e:
            print("Error:", e)
            return None


    def write_db(self, df_data, db_name):
        # write a dataframe to the database
        if db_name=='./ldc_agg.db':
            db_writer = lite.connect('./ldc_agg.db', isolation_level=None)    
        else:
            db_writer = lite.connect('./ldc_all.db', isolation_level=None)

        db_writer.execute('pragma journal_mode=wal;')
        df_data.to_sql('data', db_writer, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
        return

    def read_db(self, db_name='./ldc_all.db', start=None, end=None, duration=60):
        # read database
        if db_name=='./ldc_agg.db':
            db_reader = lite.connect('./ldc_agg.db', isolation_level=None)
        else:
            db_reader = lite.connect('./ldc_all.db', isolation_level=None)

        db_reader.execute('pragma journal_mode=wal;')


        try:
            cur = db_reader.cursor()
            if start==None or end==None:
                with db_reader:
                    # Get the last timestamp recorded
                    cur.execute('SELECT unixtime FROM data ORDER BY unixtime DESC LIMIT 1') 
                    end = np.array(cur.fetchall()).flatten()[0]
                    start = end - duration
                    
            else:
                pass
    
            # get the last set of records for a specified duration
            with db_reader:
                sql_cmd = "SELECT unixtime, parameter, value FROM data WHERE unixtime BETWEEN " + str(start) + " AND " + str(end) + " ORDER BY unixtime ASC"
                cur.execute(sql_cmd) 
                data = np.array(cur.fetchall())
                df_data = pd.DataFrame(data, columns=['unixtime', 'parameter', 'value'])
                
            return df_data

        except Exception as e:
            print("Error in get_data:", e)
            return pd.DataFrame([])


    def receive_mcast(self):
        # Receive and respond to query from the group
        multicast_ip = self.mcast_ip
        port = self.mcast_port

        multicast_group = (multicast_ip, port)  # (ip_address, port)

        # Create the socket
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind to the server address
        udp_sock.bind(multicast_group)

        # Tell the operating system to add the socket to
        # the multicast group on all interfaces.
        group = socket.inet_aton(multicast_ip)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        udp_sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            mreq)
        
        dict_toSend= {}
        # Receive/respond loop
        while True:
            # receive and decode message
            data, address = udp_sock.recvfrom(1024)
            received_msg = data.decode("utf-8").replace("'", "\"")
            dict_msg = json.loads(received_msg)

            # print(dict_msg)
            
            try:
                pass
                # Note: house name is used as the key, 'all' is a query from the aggregator  
                # if list(dict_msg)[0] in ['algorithm', 'loading', 'frequency', 'timescale', 'unixstart', 'unixend']:
                #     # update dict_cmd and put in q_cmd
                #     self.dict_cmd.update(dict_msg)
                #     while self.q_cmd.empty() is False:
                #         self.q_cmd.get()
                #         self.q_cmd.task_done()
                #     self.q_cmd.put(self.dict_cmd)
                        
                #     if dict_msg['unixstart']==0:
                #         while self.q_agg.empty() is False:
                #             dict_toSend = self.q_agg.get()
                #             self.q_agg.task_done()
                #         self.q_agg.put(dict_toSend)
                #         message_toSend = str(dict_toSend).replace("'", "\"").encode()
                #         udp_sock.sendto(message_toSend, address)
                        

                #         # print(message_toSend)
                            
                        
                #         # while self.q_agg.empty() is False:
                #         #     dict_toSend = self.q_agg.get()
                #         #     self.q_agg.task_done()
                #         # self.q_agg.put(dict_toSend)
                #         # message_toSend = str(dict_toSend).replace("'", "\"").encode()
                #         # udp_sock.sendto(message_toSend, address)
                            
                            
                #     else:
                #         # df_data = pd.DataFrame([])
                #         # while len(df_data.index) <= 0:
                #         #     df_data = self.read_db(start=dict_msg['unixstart'], end=dict_msg['unixend'])

                    
                #         # # send udp packets per row
                #         # i = 0
                #         # size = 30
                #         # while i<= len(df_data.index):
                #         #     try:
                #         #         dict_toSend = df_data.loc[i:i+size,:].to_dict(orient='index')
                #         #         message_toSend = str(dict_toSend).replace("'", "\"").encode()
                #         #         udp_sock.sendto(message_toSend, address)
                #         #     except:
                #         #         dict_toSend = df_data.loc[i:,:].to_dict(orient='index')
                #         #         message_toSend = str(dict_toSend).replace("'", "\"").encode()
                #         #         udp_sock.sendto(message_toSend, address)
                #         #     i += size
                #         pass
                #     # print(message_toSend)

                # elif list(dict_msg)[0] in ['cmd']:
                #     key = list(dict_msg)[0]
                #     self.injector.write_ldc_injector(dict_msg[key])
                #     message_toSend = str('Command confirmed: ' + dict_msg[key]).encode()
                #     udp_sock.sendto(message_toSend, address)
                #     print(message_toSend)
                #     dict_msg = {}

                # elif list(dict_msg)[0] in ['all']:
                #     pass
                # else:
                #     pass

            except Exception as e:
                print("Error in ", self.name, " receive_mcast: ", e)
                pass                      
        return



    # def gui_responder(self):
    #     try:
    #         # Create a TCP/IP socket
    #         tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
    #         # Bind the socket to the port
    #         server_address = (self.tcp_ip, 10000)
    #         print('starting up on {} port {}'.format(*server_address))
    #         tcp_sock.bind(server_address)
            
    #         # Listen for incoming connections
    #         tcp_sock.listen(10)
        
        
    #         while True:
    #             # Wait for a connection
    #             # print('waiting for a connection')
    #             connection, client_address = tcp_sock.accept()
    #             try:
    #                 # Receive the data in small chunks and retransmit it
    #                 while True:
    #                     self.read_ldc_injector()

    #                     # fetch dict_cmd to queue
    #                     while self.q_cmd.empty() is False:
    #                         self.dict_cmd = self.q_cmd.get()
    #                         self.q_cmd.task_done()
    #                     self.q_cmd.put(self.dict_cmd)  # return the latest data to queue


    #                     data = connection.recv(int(2**12))
    #                     if data:
    #                         message = data.decode("utf-8").replace("'", "\"")
    #                         dict_msg = json.loads(message)
                            
    #                         if list(dict_msg)[0] in ['algorithm', 'loading', 'frequency', 'timescale', 'unixstart', 'unixend']:
    #                             # reply: latest aggregated data
    #                             if dict_msg['unixstart']==0:
    #                                 while self.q_agg.empty() is False:
    #                                     dict_toSend = self.q_agg.get()
    #                                     self.q_agg.task_done()
    #                                 self.q_agg.put(dict_toSend)  # return data to queue
    #                                 message_toSend = str(dict_toSend).replace("'", "\"").encode()
    #                             else:
    #                                 df_data = self.read_db(start=dict_msg['unixstart'], end=dict_msg['unixend'])
    #                                 dict_toSend = df_data.to_dict(orient='index')
    #                                 message_toSend = str(dict_toSend).replace("'", "\"").encode()

    #                             connection.sendall(message_toSend)
    #                             print(message_toSend)
                            
    #                         elif list(dict_msg)[0] in ['cmd']:
    #                             key = list(dict_msg)[0]
    #                             self.injector.write_ldc_injector(dict_msg[key])
    #                             message_toSend = str('Command confirmed: ' + dict_msg[key]).encode()
    #                             connection.sendall(message_toSend)
    #                             print(message_toSend)
    #                         else:
    #                             pass   
                                
    #                     else:
    #                         connection.close()
    #                         break




        #                 # # delete obsolete data in the dictionary
        #                 # self.df_agg = pd.DataFrame.from_dict(self.dict_all['houses'], orient='index')
        #                 # self.df_agg = self.df_agg[self.df_agg['unixtime'] > (time.time() - 60)]
        #                 # self.dict_all['houses'] = self.df_agg.to_dict(orient='index')


        #                 # save dict_agg to queue
        #                 while self.q_all.empty() is False:
        #                     self.q_all.get()
        #                     self.q_all.task_done()
        #                 self.q_all.put(self.dict_all)

                        

        #         except Exception as e:
        #             print("Error in tcp_server receive_msg:", e)
        #             print(dict_msg)
        #             connection.close()
                    
                    
        #         finally:
        #             # Clean up the connection
        #             connection.close()

        # except Exception as e:
        #     print(time.time(), "Error in tcp_server connect:",e)
        #     tcp_sock.shutdown(socket.SHUT_RDWR)
        #     tcp_sock.close()
        #     raise Exception



    

    # def __del__(self):
    #     self.spi.close()
    #     GPIO.cleanup()
    #     print("Deleted:", self.name)













        

if __name__=="__main__":
    while True:
        try:
            S = TcpServer()
        except Exception as e:
            print("Error main:", e)
            try:
                del S
            except:
                pass
            time.sleep(5)

        except KeyboardInterrupt:
            break




    # def get_cmd(self):
    #     target_loading = float(self.cmd_loading) * 1000 # converted to Watts
    #     # try:
    #     #     if latest_demand == None: raise Exception
    #     # except Exception as e:
    #     #     if len(self.df_agg.index) > 0:
    #     #         n_houses = len(self.df_agg.index)
    #     #         latest_demand = self.df_agg['actual'].sum()
    #     #     else:
    #     #         n_houses = 1
    #     #         latest_demand = 10000

    #     #     gridUtilizationFactor =  1 #0.8**(0.9 * np.log(n_houses))
    #     #     capacity = n_houses * 10000 * gridUtilizationFactor #[kW]

    #     latest_demand = self.agg_demand
    #     capacity = 30000
            
    #     percent_loading = target_loading / capacity
          
    #     try:
    #         offset = np.nan_to_num(1 - (latest_demand / (target_loading)))

    #     except Exception as e:
    #         print("Error in getting offset value:",e)
    #         offset = 0

    #     ldc_upper = 860
    #     ldc_lower = 760
    #     ldc_center = 810 
    #     ldc_bw = ldc_upper - ldc_lower  # bandwidth
    #     w_past = 0.1  # weight given to the past signal, acting as a damper to change in ldc_signal

    #     try:
    #         if self.cmd_algorithm==0:
    #             self.ldc_signal=ldc_upper

    #         elif self.cmd_algorithm==1:
    #             self.ldc_signal = float(760 + (ldc_bw * percent_loading))
    #             self.ldc_signal = np.min([self.ldc_signal, 860])
    #             self.ldc_signal = np.max([self.ldc_signal, 760])
                
    #         elif self.cmd_algorithm==2:
    #             self.ldc_signal_new = float(ldc_center + ((ldc_bw) * offset * 0.1))
    #             self.ldc_signal = (w_past * self.ldc_signal) + ((1-w_past) * self.ldc_signal_new)
    #             self.ldc_signal = np.min([self.ldc_signal, 860])
    #             self.ldc_signal = np.max([self.ldc_signal, 760])

    #         elif self.cmd_algorithm == 3:
    #             self.ldc_signal = float(760 + (ldc_bw * percent_loading))
    #             self.ldc_signal = np.min([self.ldc_signal, 860])
    #             self.ldc_signal = np.max([self.ldc_signal, 760])
                
    #         else: # default is 2
    #             self.ldc_signal_new = float(ldc_center + ((ldc_bw) * offset))
    #             self.ldc_signal = (w_past * self.ldc_signal) + ((1-w_past) * self.ldc_signal_new)
    #             self.ldc_signal = np.min([self.ldc_signal, 860])
    #             self.ldc_signal = np.max([self.ldc_signal, 760])

    #         self.dict_cmd = {self.cmd_algorithm:self.ldc_signal}
    #         # print(self.dict_cmd, latest_demand, target_loading, offset)
    #         return self.dict_cmd

    #     except Exception as e:
    #         print("Error in get_cmd:", e)
















