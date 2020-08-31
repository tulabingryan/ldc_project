import socket
import sys
import time, datetime
import numpy as np
import pandas as pd
import ast
import sqlite3 as lite

class tcp_server():
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        sock = self.connect()
        self.receive_message(sock)
               

    def connect(self):
        while True:
            try:
                # Create a TCP/IP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # Bind the socket to the port
                server_address = (self.ip, self.port)
                print('starting up on {} port {}'.format(*server_address))
                sock.bind(server_address)

                # Listen for incoming connections
                sock.listen(500)
                break
            except:
                pass
            finally:
                break
       
        return sock


    def receive_message(self, sock):
        while True:
            # Wait for a connection
            print('waiting for a connection')
            connection, client_address = sock.accept()
            try:
                print('connection from', client_address)

                # Receive the data in small chunks and retransmit it
                while True:
                    data = connection.recv(2**16)
                    #print('received {!r}'.format(data))
                    if data:
                        connection.sendall(str({"A2":810}).encode())
                        message = data.decode("utf-8")
                        dict_msg = ast.literal_eval(message)

                        df_demand = pd.DataFrame.from_dict(dict_msg,orient='index')

                        df = pd.DataFrame([])
        
                        counter = 0 # counts the number of trials done to fecth data
                        while True and counter < 10:
                            try:
                                unixtime = df_demand['unixtime'].values.astype(int)
                                localtime = datetime.datetime.fromtimestamp(unixtime).isoformat()
                                df_demand['id'] = df_demand.index
                                df_demand['unixtime'] = unixtime
                                df_demand['localtime'] = localtime
                                df = pd.melt(df_demand, id_vars=["unixtime", "localtime", "house", "id", "type", "state",], 
                                          var_name="parameter", value_name="value")
                                df = df.dropna()
                                print(df)
                                
                                # save to database
                                con = lite.connect('./ldc.db')
                                df.to_sql('data', con, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
                                break
                            except Exception as e:
                                print("Error in tcp_server:", e)
                                counter += 1
                        

                    
                    else:
                        print('no data from', client_address)
                        break
            except Exception as e:
                print("Error in tcp_server receive_msg:", e)

            finally:
                # Clean up the connection
                connection.close()



if __name__=="__main__":
    while True:
        try:
            S = tcp_server('localhost', 10000)
        except:
            pass
        
