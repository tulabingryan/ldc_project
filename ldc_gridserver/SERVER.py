import socket
import struct
import threading,queue
import numpy as np
import pandas as pd
import ast
import time, datetime
import sqlite3 as lite
import json

class ThreadedServer(object):
    # Class for threaded tp server
    def __init__(self, host, port):
        self.name = 'data_server'
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

        self.mcast_ip = '224.0.2.3'
        self.mcast_port = 16003
        


        self.dict_agg = {}
        self.df_agg = pd.DataFrame([])
        self.q_agg = queue.Queue()
        self.q_agg.put(self.dict_agg)

        self.cmd_algorithm = "A2"
        self.cmd_loading = 6  # kW
        self.ldc_signal = 810

        self.dict_cmd = self.read_json('dict_cmd.txt') #{'algorithm':0, 'loading':30, 'frequency':810, 'timescale':1, 'unixstart':0, 'unixend':0}
        self.q_cmd = queue.Queue()
        self.q_cmd.put(self.dict_cmd)

        self.dict_command = {self.cmd_algorithm:self.cmd_loading}
        self.q_command = queue.Queue()
        self.q_command.put(self.dict_command)

        # thread2 = threading.Thread(target=self.receive_mcast, args=())
        # thread2.daemon = True
        # thread2.start()

        self.listen()


    def read_json(self, filename):
        # read file as json
        with open(filename) as json_file:  
            data = json.load(json_file)
        
        return data


    def listen(self, sec=5):
        self.sock.listen(5)
        while  True:
            print("waiting for clients...")
            client, address = self.sock.accept()
            client.settimeout(sec)  # close client if inactive for 60 seconds
            threading.Thread(target=self.listenToClient, args=(client, address)).start()

    def listenToClient(self, client, address):
        size = 2**16
        while True:
            try:
                data = client.recv(size)
                
                if data:
                    # decode received data
                    received_msg = data.decode("utf-8").replace("'", "\"")
                    dict_msg = json.loads(received_msg)
                    
                    if 'cmd' in list(dict_msg):
                        # update command from gui
                        print('CMD:', dict_msg['cmd'])
                        self.dict_cmd.update(dict_msg)
                        while self.q_cmd.empty() is False:
                            self.q_cmd.get()
                            self.q_cmd.task_done()
                        self.q_cmd.put(self.dict_cmd)
                    else:        
                        # respond to client/ ldc injector
                        while self.q_cmd.empty() is False:
                            self.dict_cmd = self.q_cmd.get()
                            self.q_cmd.task_done()
                        self.q_cmd.put(self.dict_cmd)
                        message_toSend = str(self.dict_cmd).replace("'", "\"").encode()
                        client.sendall(message_toSend)
                        print("INSIDE:", message_toSend)
                    
                else:
                    print("No data")
                    raise Exception('Client disconnected')

            except Exception as e:
                print("Error:", e)
                client.close()
                return False
            
    # def receive_mcast(self):
    #     # Receive and respond to query from the group
    #     multicast_ip = self.mcast_ip
    #     port = self.mcast_port

    #     multicast_group = (multicast_ip, port)  # (ip_address, port)

    #     # Create the socket
    #     udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    #     udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #     # Bind to the server address
    #     udp_sock.bind(multicast_group)

    #     # Tell the operating system to add the socket to
    #     # the multicast group on all interfaces.
    #     group = socket.inet_aton(multicast_ip)
    #     mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    #     udp_sock.setsockopt(
    #         socket.IPPROTO_IP,
    #         socket.IP_ADD_MEMBERSHIP,
    #         mreq)
        
    #     dict_toSend= {}
    #     # Receive/respond loop
    #     while True:
    #         # receive and decode message
    #         data, address = udp_sock.recvfrom(1024)
    #         received_msg = data.decode("utf-8").replace("'", "\"")
    #         dict_msg = json.loads(received_msg)

    #         print(dict_msg)
            
    #         try:
    #             # Note: house name is used as the key, 'all' is a query from the aggregator  
    #             if list(dict_msg)[0] in ['cmd']:
    #                 # update dict_cmd and put in q_cmd
    #                 self.dict_cmd.update(dict_msg)
    #                 while self.q_cmd.empty() is False:
    #                     self.q_cmd.get()
    #                     self.q_cmd.task_done()
    #                 self.q_cmd.put(self.dict_cmd)

                        
    #             #     if dict_msg['unixstart']==0:
    #             #         while self.q_agg.empty() is False:
    #             #             dict_toSend = self.q_agg.get()
    #             #             self.q_agg.task_done()
    #             #         self.q_agg.put(dict_toSend)
    #             #         message_toSend = str(dict_toSend).replace("'", "\"").encode()
    #             #         udp_sock.sendto(message_toSend, address)
                        
                            
    #             #     else:
    #             #         pass

    #             # elif list(dict_msg)[0] in ['cmd']:
    #             #     key = list(dict_msg)[0]
    #             #     message_toSend = str('Command confirmed: ' + dict_msg[key]).encode()
    #             #     udp_sock.sendto(message_toSend, address)
    #             #     print(message_toSend)
    #             #     dict_msg = {}

    #             # elif list(dict_msg)[0] in ['all']:
    #             #     pass
    #             # else:
    #             #     pass

    #         except Exception as e:
    #             print("Error in ", self.name, " receive_mcast: ", e)
    #             pass                      
    #     return



    # def get_cmd(self):
    #     while self.q_agg.empty(): pass
    #     self.dict_agg = self.q_agg.get()
    #     self.q_agg.put(self.dict_agg)
    #     self.q_agg.task_done()
    #     self.df_agg = pd.DataFrame.from_dict(self.dict_agg, orient='index')

    #     while self.q_cmd.empty(): pass
    #     self.dict_cmd = self.q_cmd.get()
    #     self.q_cmd.put(self.dict_cmd)
    #     self.q_cmd.task_done()

    #     while self.q_command.empty(): pass
    #     self.dict_command = self.q_command.get()
    #     self.q_command.put(self.dict_command)
    #     self.q_command.task_done()
        
    #     self.cmd_algorithm = list(self.dict_command)[0]
    #     self.cmd_loading = self.dict_command[self.cmd_algorithm]
    #     self.ldc_signal = self.dict_cmd[self.cmd_algorithm]

    #     target_loading = float(self.cmd_loading) * 1000 # converted to Watts
    #     if len(self.df_agg.index) > 0:
    #         n_houses = len(self.df_agg.index)
    #         latest_demand = self.df_agg['actual'].sum()
    #     else:
    #         n_houses = 1
    #         latest_demand = 10000

    #     gridUtilizationFactor =  1 #0.8**(0.9 * np.log(n_houses))
    #     capacity = n_houses * 10000 * gridUtilizationFactor #[kW]  
        
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
    #         if self.cmd_algorithm=='A0':
    #             self.ldc_signal=ldc_upper

    #         elif self.cmd_algorithm=='A1':
    #             self.ldc_signal = float(760 + (ldc_bw * percent_loading))
    #             self.ldc_signal = np.min([self.ldc_signal, 860])
    #             self.ldc_signal = np.max([self.ldc_signal, 760])
                
    #         elif self.cmd_algorithm=='A2':
    #             self.ldc_signal_new = float(ldc_center + ((ldc_bw) * offset * 0.1))
    #             self.ldc_signal = (w_past * self.ldc_signal) + ((1-w_past) * self.ldc_signal_new)
    #             self.ldc_signal = np.min([self.ldc_signal, 860])
    #             self.ldc_signal = np.max([self.ldc_signal, 760])

    #         elif self.cmd_algorithm == 'A3':
    #             self.ldc_signal = float(760 + (ldc_bw * percent_loading))
    #             self.ldc_signal = np.min([self.ldc_signal, 860])
    #             self.ldc_signal = np.max([self.ldc_signal, 760])
                
    #         else: # default is 'A2'
    #             self.ldc_signal_new = float(ldc_center + ((ldc_bw) * offset))
    #             self.ldc_signal = (w_past * self.ldc_signal) + ((1-w_past) * self.ldc_signal_new)
    #             self.ldc_signal = np.min([self.ldc_signal, 860])
    #             self.ldc_signal = np.max([self.ldc_signal, 760])

    #         self.dict_cmd = {self.cmd_algorithm:self.ldc_signal}
    #         print(self.dict_cmd, latest_demand, target_loading, offset)
    #         return self.dict_cmd

    #     except Exception as e:
    #         print("Error in get_cmd:", e)

            

import IP

if __name__=="__main__":
    local_ip = IP.get_local_ip()
    while True:
        ThreadedServer(local_ip, 10000)