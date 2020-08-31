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
import MULTICAST



class DataLogger(multiprocessing.Process):
  def __init__(self, ip, port):
    multiprocessing.Process.__init__(self)
    self.daemon = True

    self.name = "data_logger"

    self.tcp_ip = ip
    self.tcp_port = port
    self.mcast_ip = '224.0.2.3'
    self.mcast_port = 16003
    self.manager = multiprocessing.Manager()
    self.dict_all = self.manager.dict()
    self.dict_common = self.manager.dict()
    self.df_agg = pd.DataFrame([])
    self.pause = 1e-16
    self.autorun()


  def autorun(self):
    self.threads = [threading.Thread(target=self.collect_data, args=())]
    # self.threads.append(threading.Thread(target=self.save_data, args=()))
    
    # run threads
    self.dict_common.update({'is_alive':True})
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

  def contact_server_tcp(self, dict_msg, ip, port):
    # Create a TCP/IP socket
    
    try:
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      # Connect the socket to the port where the server is listening
      server_address = (ip, port)
      sock.connect(server_address)
      # send message
      message = str(dict_msg).encode()
      sock.sendall(message)
      print("Sent:", message)
      # Look for the response
      data = sock.recv(2**16)
      message = data.decode("utf-8").replace("'", "\"")
      print("Received:", message)
      return json.loads(message)

    except Exception as e:
      print("Error data_logger.contact_server_tcp:{}".format(e))
      return {}
    finally:
      sock.close()


  def contact_server_udp(self, dict_msg, ip, port, timeout=1, hops=1):
    # send multicast query to listening devices
    multicast_group=(ip, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout)  # duration of blocking the socket
    ttl = struct.pack('b', hops)  # number of routers to reach
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    try:
      dict_demand = {}
      message = str(dict_msg).replace("'", "\"").encode()
      sent = sock.sendto(message, multicast_group)
      # get responses
      while True:
        try:
          data, server = sock.recvfrom(int(2**16))
          received_msg = data.decode("utf-8")
          dict_msg = ast.literal_eval(received_msg)
          dict_demand.update(dict_msg)
        except Exception as e:
          # print("Error inner:", e)
          break
    except Exception as e:
      print("Error in MULTICAST send:", e)
    finally:
      sock.close()
    return dict_demand

   

  def collect_data(self):
    print("\nGathering data...")
    while self.dict_common['is_alive']:
      try:
        # self.dict_all.update(MULTICAST.send(dict_msg={"states":"all"}, ip=self.mcast_ip, port=self.mcast_port, timeout=1))
        # self.dict_all.update(self.contact_server_tcp(dict_msg={"states":"all"}, ip='192.168.1.3', port=10000))
        dict_all = MULTICAST.send(dict_msg={"states":"all"}, ip=self.mcast_ip, port=self.mcast_port, timeout=0.5)
        if dict_all:
          unixtime = time.time()
          dict_all.update({'unixtime':unixtime, 'timezone':'Pacific/Auckland'})
          self.dict_all.update({unixtime:dict_all})
          self.dict_all = self.save_data(self.dict_all)
        time.sleep(0.5)
      except Exception as e:
        print("Error data_logger.collect_data:", e)
      except KeyboardInterrupt:
        break
  

  def save_data(self, dict_data):
    try:
      df_all = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True)
      today = datetime.datetime.now().strftime("%Y-%m-%d")
      try:
        on_disk = pd.read_feather(f'history/{today}.feather').reset_index(drop=True)
        df_all = pd.concat([on_disk, df_all], axis=0).reset_index(drop=True)
      except Exception as e:
        # print(e)
        pass
      df_all.to_feather(f'history/{today}.feather')
      return {}
    except Exception as e:
      print("Error data_logger.save_data:", e)
      return dict_data

  # def collect_data(self):
  #   print("\nGathering data...")
  #   db_writer = lite.connect('/home/pi/ldc_project/ldc_gridserver/ldc_agg_melted.db', isolation_level=None)
  #   db_writer.execute('pragma journal_mode=wal;')
      
  #   while self.dict_common['is_alive']:
  #     try:
  #       self.dict_all.update(MULTICAST.send(dict_msg={"states":"all"}, ip=self.mcast_ip, port=self.mcast_port, timeout=1))
  #       # self.dict_all.update(self.contact_server_tcp(dict_msg={"states":"all"}, ip='192.168.1.3', port=10000))
  #       '''Note: even if no data is retrieved, database is written with a unixtime to 
  #       make the timeline consistent.'''
  #       self.dict_all.update({'unixtime':time.time()})  
  #       self.df_all = pd.DataFrame.from_dict(self.dict_all, orient='index').T
  #       # self.df_all = self.df_all.groupby('unixtime', as_index=False).mean().tail(1)
          
  #       df_all = pd.melt(self.df_all.astype(str), id_vars=["unixtime"], 
  #         var_name="parameter", value_name="value")
  #       # self.write_db(df_data=df_all, db_name='/home/pi/ldc_project/ldc_gridserver/ldc_agg_melted.db')
  #       df_all.to_sql('data', db_writer, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
        
  #       db_writer.execute('CREATE INDEX IF NOT EXISTS unixtime ON data (unixtime);')
  #       db_writer.execute('CREATE INDEX IF NOT EXISTS parameter ON data (parameter);')
  #       db_writer.commit()
        
  #     except Exception as e:
  #       print("Error data_logger.collect_data:", e)
  #     except KeyboardInterrupt:
  #       break
  #   db_writer.close()

  # def save_data(self):
  #   print("\nStart saving data...")
  #   while self.dict_common['is_alive']:
  #     try:
  #       if self.dict_all:
  #         self.df_all = pd.DataFrame.from_dict(self.dict_all, orient='index').T
  #         self.df_all = self.df_all.groupby('unixtime', as_index=False).mean().tail(1)
            
  #         df_all = pd.melt(self.df_all.astype(str), id_vars=["unixtime"], 
  #           var_name="parameter", value_name="value")
  #         self.write_db(df_data=df_all, db_name='/home/pi/ldc_project/ldc_gridserver/ldc_agg_melted.db')
  #         print(self.dict_all)
  #       time.sleep(1)
  #     except KeyboardInterrupt:
  #       break
  #     except Exception as e:
  #       print(f"Error data_logger.save_data:{e}")
  #       time.sleep(3)

  # def write_db(self, df_data, db_name):
  #   # write a dataframe to the database
  #   try:
  #     db_writer = lite.connect(db_name, isolation_level=None)
  #     db_writer.execute('pragma journal_mode=wal;')
  #     df_data.to_sql('data', db_writer, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
  #     db_writer.execute('CREATE INDEX IF NOT EXISTS unixtime ON data (unixtime);')
  #     db_writer.execute('CREATE INDEX IF NOT EXISTS parameter ON data (parameter);')
  #     db_writer.commit()
  #     db_writer.close()
  #   except Exception as e:
  #     print("Error data_logger2.write_db:{}".format(e))
      
  def read_db(self, db_name='./ldc_all.db', start=None, end=None, duration=60):
    # read database
    db_reader = lite.connect(db_name, isolation_level=None)
    db_reader.execute('pragma journal_mode=wal;')
    try:
      cur = db_reader.cursor()
      if start==None or end==None:
        with db_reader:
          cur.execute('SELECT unixtime FROM data ORDER BY unixtime DESC LIMIT 1') 
          end = np.array(cur.fetchall()).flatten()[0]
          start = end - duration
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


    

if __name__=="__main__":
  try:
    local_ip = IP.get_local_ip()
    S = DataLogger(local_ip, 10000)
  except Exception as e:
    print("Error:", e)
    try:
      del S
    except:
      pass
    time.sleep(5)

  # except KeyboardInterrupt:
  #     break

