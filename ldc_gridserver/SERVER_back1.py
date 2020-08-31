import socket
import threading,queue
import numpy as np
import pandas as pd
import ast
import time, datetime
import sqlite3 as lite

class ThreadedServer(object):
    # Class for threaded tp server
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))


        self.dict_agg = {}
        self.df_agg = pd.DataFrame([])
        self.q_agg = queue.Queue()
        self.q_agg.put(self.dict_agg)

        self.cmd_algorithm = "A2"
        self.cmd_loading = 6  # kW
        self.ldc_signal = 810
        
        self.dict_cmd = {self.cmd_algorithm : self.ldc_signal}
        self.q_cmd = queue.Queue()
        self.q_cmd.put(self.dict_cmd)

        self.dict_command = {self.cmd_algorithm:self.cmd_loading}
        self.q_command = queue.Queue()
        self.q_command.put(self.dict_command)
        


    def listen(self, sec=60):
        self.sock.listen(5)
        while  True:
            # print("waiting for clients...")
            client, address = self.sock.accept()
            client.settimeout(sec)  # close client if inactive for 60 seconds
            threading.Thread(target=self.listenToClient, args=(client, address)).start()

    def listenToClient(self, client, address):
        size = 2**16
        while True:
            try:
                data = client.recv(size)
                if data:
                    # If data is received
                    message = data.decode("utf-8")
                    dict_msg = ast.literal_eval(message)
                    if list(dict_msg)[0] in ['A0', 'A1', 'A2', 'A3', 'A4']:
                        key = list(dict_msg)[0]
                        self.cmd_algorithm = key
                        self.cmd_loading = dict_msg[key]

                        while self.q_command.empty() is False:
                            self.dict_command = self.q_command.get()
                            self.q_command.task_done()

                        self.dict_command.update(dict_msg)
                        self.q_command.put(self.dict_command)
                        

                        # send ldc command as response
                        while self.q_agg.empty(): pass
                        self.dict_agg = self.q_agg.get()
                        self.q_agg.put(self.dict_agg)
                        self.q_agg.task_done()

                        client.sendall(str(self.dict_agg).encode())
                    

                    else:
                        while self.q_all.empty() is False:
                            self.dict_all = self.q_all.get()
                            self.q_all.task_done()
                        
                        self.dict_all.update(dict_msg)
                        self.q_all.put(self.dict_all)
                        
                        self.df_agg = pd.DataFrame.from_dict(self.dict_all, orient='index')
                        # print(self.df_all)


                        df_demand = pd.DataFrame.from_dict(dict_msg,orient='index')

                        df = pd.DataFrame([])
        
                        counter = 0 # counts the number of trials done to fecth data
                        # while True and counter < 10:
                        try:
                            unixtime = df_demand['unixtime'].values.astype(int)
                            localtime = datetime.datetime.fromtimestamp(unixtime).isoformat()
                            df_demand['id'] = df_demand.index
                            df_demand['unixtime'] = unixtime
                            df_demand['localtime'] = localtime
                            

                            df = pd.melt(df_demand, id_vars=["unixtime", "localtime", "house", "id", "type"], 
                                      var_name="parameter", value_name="value")

                            df = df.dropna()
                            df['state'] = 'agg'  # aggregated
                            df = df[df['type']=='meter']
                
                            
                            # save to database
                            con = lite.connect('./ldc.db')
                            df.to_sql('data', con, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
                            # break
                        except Exception as e:
                            print("Error in tcp_server:", e)
                            counter += 1

                        # send ldc command as response
                        self.dict_cmd = self.get_cmd()
                        client.sendall(str(self.dict_cmd).encode())
                    



                else:
                    raise Exception('Client disconnected')
            except Exception as e:
                print("Error:", e)
                client.close()
                return False
            finally:
                client.close()


    def get_cmd(self):
        while self.q_agg.empty(): pass
        self.dict_agg = self.q_agg.get()
        self.q_agg.put(self.dict_agg)
        self.q_agg.task_done()
        self.df_agg = pd.DataFrame.from_dict(self.dict_agg, orient='index')

        while self.q_cmd.empty(): pass
        self.dict_cmd = self.q_cmd.get()
        self.q_cmd.put(self.dict_cmd)
        self.q_cmd.task_done()

        while self.q_command.empty(): pass
        self.dict_command = self.q_command.get()
        self.q_command.put(self.dict_command)
        self.q_command.task_done()
        
        self.cmd_algorithm = list(self.dict_command)[0]
        self.cmd_loading = self.dict_command[self.cmd_algorithm]
        self.ldc_signal = self.dict_cmd[self.cmd_algorithm]

        target_loading = float(self.cmd_loading) * 1000 # converted to Watts
        if len(self.df_agg.index) > 0:
            n_houses = len(self.df_agg.index)
            latest_demand = self.df_agg['actual'].sum()
        else:
            n_houses = 1
            latest_demand = 10000

        gridUtilizationFactor =  1 #0.8**(0.9 * np.log(n_houses))
        capacity = n_houses * 10000 * gridUtilizationFactor #[kW]  
        
        percent_loading = target_loading / capacity
          
        try:
            offset = np.nan_to_num(1 - (latest_demand / (target_loading)))

        except Exception as e:
            print("Error in getting offset value:",e)
            offset = 0

        ldc_upper = 860
        ldc_lower = 760
        ldc_center = 810 
        ldc_bw = ldc_upper - ldc_lower  # bandwidth
        w_past = 0.1  # weight given to the past signal, acting as a damper to change in ldc_signal

        try:
            if self.cmd_algorithm=='A0':
                self.ldc_signal=ldc_upper

            elif self.cmd_algorithm=='A1':
                self.ldc_signal = float(760 + (ldc_bw * percent_loading))
                self.ldc_signal = np.min([self.ldc_signal, 860])
                self.ldc_signal = np.max([self.ldc_signal, 760])
                
            elif self.cmd_algorithm=='A2':
                self.ldc_signal_new = float(ldc_center + ((ldc_bw) * offset * 0.1))
                self.ldc_signal = (w_past * self.ldc_signal) + ((1-w_past) * self.ldc_signal_new)
                self.ldc_signal = np.min([self.ldc_signal, 860])
                self.ldc_signal = np.max([self.ldc_signal, 760])

            elif self.cmd_algorithm == 'A3':
                self.ldc_signal = float(760 + (ldc_bw * percent_loading))
                self.ldc_signal = np.min([self.ldc_signal, 860])
                self.ldc_signal = np.max([self.ldc_signal, 760])
                
            else: # default is 'A2'
                self.ldc_signal_new = float(ldc_center + ((ldc_bw) * offset))
                self.ldc_signal = (w_past * self.ldc_signal) + ((1-w_past) * self.ldc_signal_new)
                self.ldc_signal = np.min([self.ldc_signal, 860])
                self.ldc_signal = np.max([self.ldc_signal, 760])

            self.dict_cmd = {self.cmd_algorithm:self.ldc_signal}
            print(self.dict_cmd, latest_demand, target_loading, offset)
            return self.dict_cmd

        except Exception as e:
            print("Error in get_cmd:", e)

            

import IP

if __name__=="__main__":
    local_ip = IP.get_local_ip()
    while True:
        ThreadedServer(local_ip, 10000).listen(60)