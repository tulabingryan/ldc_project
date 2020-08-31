import serial
import serial.tools.list_ports
import time, datetime
import pandas as pd
import numpy as np
import sqlite3 as lite

import socket
import struct
import sys
import json
import ast
import multiprocessing
import threading





class DataLogger(multiprocessing.Process):
  def __init__(self, local_ip, local_port):
    multiprocessing.Process.__init__(self)
    self.daemon = True
    self.name = "data_logger"
    self.local_ip = local_ip
    self.local_port = local_port
    self.mcast_ip = '224.0.2.3'
    self.mcast_port = 16003
    self.manager = multiprocessing.Manager()
    self.dict_all = self.manager.dict()
    self.dict_sensors = self.manager.dict()
    self.dict_dongles = self.manager.dict()
    self.dict_common = self.manager.dict()
    self.pause = 1e-1
    self.autorun()


  def autorun(self):
    self.threads = [threading.Thread(target=self.collect_data_dongles, args=())]
    self.threads.append(threading.Thread(target=self.collect_data_sensors, args=()))
    self.threads.append(threading.Thread(target=self.collect_data_all, args=()))
    # run threads
    self.dict_common.update({'is_alive':True})  # signals other threads
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
    dict_data = {} # holder of the output
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (ip, port)
    try:
      sock.connect(server_address)  # connect to server
      msg_out = str(dict_msg).encode()
      sock.sendall(msg_out)  # send message
      data = sock.recv(2**16) # receive response
      msg_in = data.decode("utf-8").replace("'", "\"")
      dict_data.update(json.loads(msg_in))
    except Exception as e:
      print(f"Error data_logger.contact_server_tcp:{e}")
    finally:
      sock.close()
    return dict_data


  def contact_server_udp(self, dict_msg, ip, port, timeout=1, hops=1):
    # send multicast query to listening devices
    dict_data = {}  # holder of output
    multicast_group=(ip, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
      sock.settimeout(timeout)  # duration of blocking the socket
      ttl = struct.pack('b', hops)  # number of routers to reach
      sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
      msg_out = str(dict_msg).replace("'", "\"").encode('utf-8')
      sent = sock.sendto(msg_out, multicast_group)  # send message
      # get responses
      while True:
        try:
          data, server = sock.recvfrom(int(2**16))
          if data:
            msg_in = data.decode("utf-8").replace("'", "\"")
            dict_data.update(json.loads(msg_in))
        except Exception as e:
          # print("Error inner:", e)
          break
    except Exception as e:
      print(f"Error data_logger.contact_server_udp:{e}")
    finally:
      sock.close()
    return dict_data


  def get_ports(self, report=False):
    try:
      ports = serial.tools.list_ports.comports()
      dict_ports = {}
      for port, desc, hwid in sorted(ports):
        try:
          hardware_id = hwid.split(':')[1]
          dict_ports[hardware_id] = port
        except:
          pass
      if report:
        print(dict_ports)
      return dict_ports
    except Exception as e:
      print(f"Error data_logger.get_ports:{e}")
      return


  def connect_serial(self, port, baudrate=115200, report=False):
    try:
      ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.5
      )
      if ser.isOpen() and report:
        print("Port {} is open.".format(port))
      return ser
    except Exception as e:
      print(f"Error data_logger.connect_serial:{e}")
      return


  def collect_data_sensors(self, report=False):
    print("Collecting data from sensors...")
    df_location = pd.read_csv('sensors_location.csv').set_index('node_id')
    dict_hist = {}  # temporary holder
    while self.dict_common['is_alive']:
      try:
        ### query env_sensors
        dict_ports = self.get_ports(report=False)
        ser = self.connect_serial(port=dict_ports['PID=0483'])
        now = datetime.datetime.now()
        dt = now.strftime('%Y-%m-%d %H:%M')
        b = ser.read(18)
        if b:
          if((b[0] & 0xFF) == 0xAA):
            dict_data = dict(
              date_time=dt,
              dest_group_id = b[7] & 0xFF,
              dest_node_id = b[8] & 0xFF,
              source_group_id = b[9] & 0xFF,
              source_node_id = b[10] & 0xFF,
              temperature = (b[12] & 0xFF) + (b[13] & 0xFF) / 100,
              humidity = (b[14] & 0xFF) + (b[15] & 0xFF) / 100,
              light = (((b[16] & 0xFF) << 8) + (b[17] & 0xFF)) * 16
              )

            location = df_location.loc[dict_data['source_node_id'],'location']
            group = df_location.loc[dict_data['source_node_id'],'group']
            if group!='xxxx':
              self.dict_sensors.update({str(dict_data['source_node_id']):{
                'group': group,
                'location': location,
                'temperature':dict_data['temperature'],
                'humidity':dict_data['humidity'],
                'light':dict_data['light'],
                }})
            
        time.sleep(1)
      except Exception as e:
        if report: print(f"Error data_logger.query_sensors:{e}")
      except BrokenPipeError:
        break 
      except KeyboardInterrupt:
        break


  def collect_data_dongles(self, report=False):
    print("Collecting data from dongles...")
    dict_data = {}
    dict_dongles = {}
    subnet = self.local_ip.split(".")[2]
    while self.dict_common['is_alive']:
      try:
        self.dict_dongles = self.contact_server_udp(dict_msg={"states":"all"}, ip=f'192.168.{subnet}.101', port=17001, timeout=0.3, hops=1)
        ### save as feather file
        if self.dict_dongles:
          now = datetime.datetime.now()
          today = now.strftime('%Y-%m-%d')
          unixtime = now.timestamp()
          self.dict_dongles.update({'unixtime':unixtime})
          
          dict_dongles.update(self.dict_dongles)
          dict_data.update({int(unixtime):dict_dongles})
          if len(dict_data.keys())>10:
            # dict_data = self.save_data(dict_data=dict_data, path=f'history/h{self.local_ip.split(".")[2]}_{today}.feather')
            dict_data = self.pickle_data(dict_data=dict_data, path=f'history/h{self.local_ip.split(".")[2]}_{today}.pkl')
          time.sleep(0.7)
      except Exception as e:
        print(f"Error data_logger.query_dongles:{e}")
      except KeyboardInterrupt:
        break
      except BrokenPipeError:
        break 

  def save_data(self, dict_data, path='history/sample.feather'):
    try:
      df_all = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True).astype(float)
      try:
        on_disk = pd.read_feather(path).reset_index(drop=True)
        df_all = pd.concat([on_disk, df_all], axis=0).groupby('unixtime').mean().reset_index(drop=False)
      except Exception as e:
        # print(e)
        pass
      df_all.to_feather(path)
      print(df_all.tail(3))
      return {}
    except Exception as e:
      print("Error data_logger.save_data:", e)
      return dict_data  

  def pickle_data(self, dict_data, path='history/sample.pkl'):
    try:
      df_all = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True).astype(float)
      try:
        on_disk = pd.read_pickle(path).reset_index(drop=True)
        df_all = pd.concat([on_disk, df_all], axis=0).groupby('unixtime').mean().reset_index(drop=False)
      except Exception as e:
        # print(e)
        pass
      df_all.to_pickle(path)
      df_all.to_pickle(f"/home/pi/studies/ardmore/homeserver/{path.split('/')[-1]}")
      print(df_all.tail(3))
      return {}
    except Exception as e:
      print("Error data_logger.save_data:", e)
      return dict_data 

  def collect_data_all(self, report=True, save=True):
    print("\nGathering data...")
    db_writer = lite.connect('/home/pi/ldc_project/ldc_homeserver/homedata.db', isolation_level=None)
    db_writer.execute('pragma journal_mode=wal;')
    while self.dict_common['is_alive']:
      try:
        time.sleep(1)
        unixtime = int(time.time())
        now = datetime.datetime.now()
        if False: #self.dict_sensors:
          ### process data
          df_hist = pd.DataFrame.from_dict(self.dict_sensors, orient='index')
          df_hist = df_hist.groupby(['location', 'group']).mean()
          df_hist['unixtime'] = unixtime
          df_hist = df_hist.reset_index(drop=False)
          df_hist = pd.melt(df_hist.astype(str), id_vars=["unixtime", "group", "location"], 
                      var_name="parameter", value_name="value")
          df_hist['parameter'] = ['_'.join(i) for i in zip(df_hist['location'], df_hist['parameter'])]
          df_hist.drop(labels=['location'], inplace=True, axis=1)
        
          if report: print(df_hist)
          if save:
            ### save in database
            df_hist.to_sql('data', db_writer, schema=None, if_exists='append', index=False, 
              chunksize=None, dtype=None)
            db_writer.execute('CREATE INDEX IF NOT EXISTS unixtime ON data (unixtime);')
            db_writer.commit()
            ### save as csv
            filename = '/home/pi/ldc_project/history/H1_{}_ALL.csv'.format(now.strftime('%Y_%m_%d'))
            with open(filename, 'a') as f:
              df_hist.to_csv(f, mode='a', header=f.tell()==0, index=False)

        if False: #self.dict_dongles:
          df_ldc = pd.DataFrame.from_dict(self.dict_dongles, orient='index').T.round(7)
          df_ldc = pd.melt(df_ldc.astype(str), id_vars=["unixtime"], 
                      var_name="parameter", value_name="value")
          df_ldc['unixtime'] = [unixtime for a in df_ldc.index]
          
          if save:
            ### save in database
            df_ldc.to_sql('data', db_writer, schema=None, if_exists='append', index=False, 
              chunksize=None, dtype=None)
            db_writer.execute('CREATE INDEX IF NOT EXISTS unixtime ON data (unixtime);')
            db_writer.commit()
            ### save as csv
            now = datetime.datetime.now()
            filename = '/home/pi/ldc_project/history/H1_{}_ALL.csv'.format(now.strftime('%Y_%m_%d'))
            with open(filename, 'a') as f:
              df_ldc.to_csv(f, mode='a', header=f.tell()==0, index=False)
            # if report: print(df_ldc)
            
      except Exception as e:
        print("Error data_logger.collect_data:", e)
      except KeyboardInterrupt:
        break
      except BrokenPipeError:
        break
    db_writer.close()



  


def get_local_ip():
  # get local ip address
  local_ip = '192.168.1.81'  # default
  while True:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.connect(("8.8.8.8", 80))
      local_ip = s.getsockname()[0]
      s.close()
      break
    except Exception as e:
      print("Error in get_local_ip: ", e)
      pass
  return local_ip


    

if __name__=="__main__":
  try:
    local_ip = get_local_ip()
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






# def write_db(df_data, db_name):
#   try:
#     db_writer = lite.connect(db_name, isolation_level=None)
#     db_writer.execute('pragma journal_mode=wal;')
#     df_data.to_sql('data', db_writer, schema=None, if_exists='append', 
#       index=False, chunksize=None, dtype=None)
#     db_writer.execute('CREATE INDEX IF NOT EXISTS unixtime ON data (unixtime);')
#     db_writer.commit()
#     db_writer.close()
#   except Exception as e:
#       print("Error data_logger.write_db:{}".format(e), "db_name:{}".format(db_name))

# def check_for_duplicates(db_name, report=False):
#   ''' This function checks the records of an sql database for duplicates'''
#   try:
#     con = lite.connect(db_name)
#     with con:
#       cur = con.cursor()        
#       cur.execute('SELECT * FROM data GROUP BY * HAVING COUNT(*)> 1')
#       data = np.array(cur.fetchall())
#     if report:
#       print('Database record with duplicates:' + str(len(data)))
#     return len(data)
#   except Exception as e:
#     print("Error check_for_duplicates:{}".format(e))

# def delete_duplicates(db_name):
#   """ This function saves an array of data to an SQL database"""
#   # print('Deleting duplicates...')
#   try:        
#     con = lite.connect(db_name)
#     with con:
#       cur = con.cursor()
#       cur.execute('DELETE FROM data WHERE ROWID NOT IN (SELECT min(ROWID) FROM data GROUP BY *)')
#       data = cur.fetchall()
#   except Exception as e:
#     print("Error delete_duplicates:{}".format(e))


# def clean_database(db_name):
#   ''' This function cleans up the database from duplicated data record'''
#   try:
#     n_duplicates = check_for_duplicates(db_name=db_name)
#     while n_duplicates > 0 :
#       delete_duplicates(db_name)
#       n_duplicates = check_for_duplicates(db_name=db_name)
#   except Exception as e:
#     print("Error clean_database:{}".format(e))



   


# def autorun(report=False, save=False, error_feedback=False):
#   threads = []
#   try: 
#     threads.append(threading.Thread(target=query_sensors, args=()))
#     threads.append(threading.Thread(target=query_dongles, args=()))
#     for t in threads:
#       t.daemon = True
#       t.start()
#     ### keep main function alive
#     while True:
#       try:
#         time.sleep(1)
#       except Exception as e:
#         print(e)
#       except KeyboardInterrupt:
#         break
#   except Exception as e:
#     if error_feedback: print("Error data_logger.autorun", e)
#     time.sleep(1)




# def main():
#   autorun(report=True, save=True, error_feedback=True)

# if __name__ == '__main__':
#   main()
