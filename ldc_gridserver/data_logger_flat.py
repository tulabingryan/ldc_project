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
        self.dict_agg = {"unixtime":int(time.time())}
        self.df_agg = pd.DataFrame([])
        
        self.log_data()



    def log_data(self):
        count = 0  # counter for feedback printing
        t_0 = int(time.time())
        while True:
            try:
                self.dict_agg.update(MULTICAST.send(dict_msg={"unixstart":0}, ip=self.mcast_ip, port=self.mcast_port, timeout=0.1))
                t_1 = self.dict_agg['unixtime']

                if t_0 != t_1 and len(self.df_agg.index) > 0:
                    #save to database
                    print(self.df_agg)
                    
                    self.write_db(df_data=self.df_agg, db_name='./ldc_agg_flat.db')
                    t_0 = t_1
                    self.df_agg = pd.DataFrame.from_dict(self.dict_agg, orient='index').T
                    self.df_agg = self.df_agg.groupby('unixtime', as_index=False).mean().tail(1)
                    self.df_agg['localtime'] = pd.to_datetime(self.df_agg['unixtime'], unit='s')
                    self.df_agg = self.df_agg.tail(1)
                    
                else:
                    self.df_agg = pd.concat([self.df_agg, pd.DataFrame.from_dict(self.dict_agg, orient='index').T]).reset_index(drop=True)
                    try:
                        self.df_agg = self.df_agg.groupby('unixtime', as_index=False).mean().tail(1)
                    except:
                        pass
                    self.df_agg['localtime'] = pd.to_datetime(self.df_agg['unixtime'], unit='s')
                    self.df_agg = self.df_agg.tail(1)


                    
                
                    
                
            except Exception as e:
                print("Error in log_data:", e)
                raise e
        
            except KeyboardInterrupt:
                break


    def write_db(self, df_data, db_name):
        # write a dataframe to the database
        try:
            db_writer = lite.connect(db_name, isolation_level=None)

            db_writer.execute('pragma journal_mode=wal;')
            df_data.to_sql('data', db_writer, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
            db_writer.execute('CREATE INDEX IF NOT EXISTS unixtime ON data (unixtime);')
            db_writer.commit()
            db.writer.close()
        except:
            pass
        

    def read_db(self, db_name='./ldc_all.db', start=None, end=None, duration=60):
        # read database
        try:
            db_reader = lite.connect(db_name, isolation_level=None)
            db_reader.execute('pragma journal_mode=wal;')
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

            db_reader.commit()
            db_reader.close()
                
            return df_data

        except Exception as e:
            print("Error in get_data:", e)
            return pd.DataFrame([])


        

if __name__=="__main__":
    while True:
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

        except KeyboardInterrupt:
            break

