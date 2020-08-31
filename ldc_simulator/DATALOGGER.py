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
import threading, queue
import multiprocessing
import json, ast
import MULTICAST
import FUNCTIONS



class DataLogger(multiprocessing.Process):
    def __init__(self, house):
        multiprocessing.Process.__init__(self)
        self.daemon = True

        self.house = house
        self.dict_agg = {}
        self.df_agg = pd.DataFrame([])
        
        self.log_data()



    def log_data(self):
        while True:
            try:
                self.dict_agg.update(MULTICAST.send(dict_msg={self.house:"h"}, ip='238.173.254.147', port=12604, timeout=0.1))  # update data
                self.df_agg = pd.DataFrame.from_dict(self.dict_agg, orient='index')
                print(self.df_agg)
                # t_1 = self.dict_agg['unixtime']

                # if t_0 != t_1 and len(self.df_agg.index) > 0:
                #     #save to database
                #     print(self.df_agg)
                    
                #     self.write_db(df_data=self.df_agg, db_name='./ldc_home_flat.db')
                #     t_0 = t_1
                #     self.df_agg = pd.DataFrame.from_dict(self.dict_agg, orient='index').T
                #     self.df_agg = self.df_agg.groupby('unixtime', as_index=False).mean().tail(1)
                #     self.df_agg = self.df_agg.tail(1)
                    
                # else:
                #     self.df_agg = pd.concat([self.df_agg, pd.DataFrame.from_dict(self.dict_agg, orient='index').T]).reset_index(drop=True)
                #     try:
                #         self.df_agg = self.df_agg.groupby('unixtime', as_index=False).mean().tail(1)
                #     except:
                #         pass
                #     # self.df_agg['localtime'] = pd.to_datetime(self.df_agg['unixtime'], unit='s')
                #     self.df_agg = self.df_agg.tail(1)

                # print(self.df_agg)
                # time.sleep(0.1)
            except Exception as e:
                print("Error in save_data:", e)
                
            except KeyboardInterrupt:
                break


    def write_db(self, df_data, db_name):
        # write a dataframe to the database
        db_writer = lite.connect(db_name, isolation_level=None)

        db_writer.execute('pragma journal_mode=wal;')
        df_data.to_sql('data', db_writer, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
        db_writer.execute('CREATE INDEX IF NOT EXISTS unixtime ON data (unixtime);')
        return

    # def read_db(self, db_name='./ldc_all.db', start=None, end=None, duration=60):
    #     # read database
    #     db_reader = lite.connect(db_name, isolation_level=None)
    #     db_reader.execute('pragma journal_mode=wal;')

    #     try:
    #         cur = db_reader.cursor()
    #         if start==None or end==None:
    #             with db_reader:
    #                 # Get the last timestamp recorded
    #                 cur.execute('SELECT unixtime FROM data ORDER BY unixtime DESC LIMIT 1') 
    #                 end = np.array(cur.fetchall()).flatten()[0]
    #                 start = end - duration
                    
    #         else:
    #             pass
    
    #         # get the last set of records for a specified duration
    #         with db_reader:
    #             sql_cmd = "SELECT unixtime, parameter, value FROM data WHERE unixtime BETWEEN " + str(start) + " AND " + str(end) + " ORDER BY unixtime ASC"
    #             cur.execute(sql_cmd) 
    #             data = np.array(cur.fetchall())
    #             df_data = pd.DataFrame(data, columns=['unixtime', 'parameter', 'value'])
                
    #         return df_data

    #     except Exception as e:
    #         print("Error in get_data:", e)
    #         return pd.DataFrame([])


        

if __name__=="__main__":
    df_houseSpecs = pd.read_csv('./specs/houseSpecs.csv')
    local_ip = FUNCTIONS.get_local_ip(report=True)
    # while True:
    try:
        idx = int(local_ip.split('.')[2])-1
        D = DataLogger(house=df_houseSpecs.loc[idx, 'name'])
        
    except Exception as e:
        print("Error:", e)
        del D
        time.sleep(5)

        # except KeyboardInterrupt:
        #     break

