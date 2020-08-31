# -----------------------------------------------------------------
# update_ldc_db.py
# Real-time Market Price of Electricity in New Zealand
# Source: Electricity Market Information (EMI)
# WEB: emi.portal.azure-api.net
# This file is used to update the market.db, storing the electricity market transactions from EMI


import http.client, urllib.request, urllib.parse, urllib.error, base64
import json, datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sqlite3 as lite
import time
import os
from dateutil import tz

# multicasting packages
import socket
import struct
import sys
import time
import json
import ast
import pandas as pd


# set timezone 
tz = tz.gettz('Pacific/Auckland')
timezone = 'Pacific/Auckland'
os.environ['TZ'] = timezone
time.tzset()

global n_houses
n_houses = 1  # initial number of houses


def send(dict_msg, ip='224.0.2.0', port=10000, timeout=2, hops=64):
    # send multicast query to listening devices
    multicast_group=(ip, port)
    # Create the datagram socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Set a timeout so the socket does not block
    # indefinitely when trying to receive data.
    sock.settimeout(timeout)

    # Set the time-to-live for messages to 1 so they do not
    # go past the local network segment.
    ttl = struct.pack('b', hops)  # number of hops
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    dict_demand = {}
    x = time.perf_counter()

    try:
        # Send data to the multicast group 
        message = str(dict_msg).encode()
        counter = time.perf_counter()
        sent = sock.sendto(message, multicast_group)
        # Look for responses from all recipients
        while True:
            try:
                data, server = sock.recvfrom(int(2**16))
                message = data.decode("utf-8")
                dict_msg = ast.literal_eval(message)
                dict_demand.update(dict_msg)
            except socket.timeout:
                break
            else:
                pass
    except Exception as e:
        print("Error in MULTICAST send", e, dict_msg, ip, port, message)
        sock.close()
    finally:
        sock.close()

    return dict_demand

            # if self.timestamp >= int(self.df_weather['unixtime'].tail(1)):
                        #     self.df_weather = self.get_weatherHistory(unixtime=int(self.timestamp) + (60*60*2), report=False)
            

## test ###
# d = send(dict_msg={"all":"id"}, ip='224.0.2.0', port=10000, timeout=2, hops=64)
# print(d)
## end test ###



def check_for_duplicates(db_name='./ldc.db', report=False):
    ''' This function checks the records of an sql database for duplicates'''
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()        
        cur.execute('SELECT * FROM data GROUP BY unixtime, localtime, house, id, parameter, value, state, type HAVING COUNT(*)> 1')
        data = np.array(cur.fetchall())
    if report:
        print('Database record with duplicates:' + str(len(data)))
    
    return len(data)


def delete_duplicates(db_name='./ldc.db'):
    """ This function saves an array of data to an SQL database"""
    # print('Deleting duplicates...')
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()
        cur.execute('DELETE FROM data WHERE ROWID NOT IN (SELECT min(ROWID) FROM data GROUP BY unixtime, localtime, house, id, parameter, value, state, type)')
        #cur.execute('CREATE INDEX idx_unixtime ON  data (unixtime)')
        #cur.execute('CREATE INDEX idx_all ON  data (unixtime, house, parameter, value, state)')
        data = cur.fetchall()

def clean_database(db_name='./ldc.db'):
    ''' This function cleans up the database from duplicated data record'''
    n_duplicates = check_for_duplicates(db_name=db_name)
    while n_duplicates > 0 :
        delete_duplicates(db_name)
        n_duplicates = check_for_duplicates(db_name=db_name)


# def command(cmd='Q', freq=810, save=True, report=False):
#     global n_houses

#     if cmd!='Q':
#         send(dict_msg={str(cmd):str(freq)})
#         return
#     else:
#         df = pd.DataFrame([])
#         df_agg = pd.DataFrame([])

#         counter = 0 # counts the number of trials done to fecth data
#         while True and counter < 10:
#             try:
#                 # get proposed load demands
#                 df_query = pd.DataFrame.from_dict(send(dict_msg={str(cmd):str(freq)}),orient='index')
#                 print(df_query)

#                 if (n_houses < len(np.unique(df_query['house']))) and (counter < 8):
#                         raise Exception
#                 else:
#                     n_houses = len(np.unique(df_query['house']))


#                 unixtime = time.time()#np.mean(df_demand['unixtime'].values.astype(float))
#                 localtime = datetime.datetime.fromtimestamp(unixtime).isoformat()
                
#                 df_demand = df_query[['type', 'house', 'actual', 'proposed', 'flexibility', 'limit']]
#                 df_demand['id'] = df_query.index
#                 df_demand['unixtime'] = unixtime
#                 df_demand['localtime'] = localtime


#                 df = pd.melt(df_demand, id_vars=["unixtime", "localtime", "house", "id", "type"], 
#                           var_name="parameter", value_name="value")

#                 df = df.dropna()
#                 df['state'] = 'agg'  # aggregated
#                 df = df[df['type']=='meter']
    
#                 # save to database
#                 if save:
#                     con = lite.connect('./ldc.db')
#                     df.to_sql('data', con, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
#                 else:
#                     pass

#                 # calculate aggregated values
#                 df_a = df[df['parameter']=='proposed']
#                 df_b = df[df['parameter']=='actual']
#                 df_c = df[df['parameter']=='limit']
#                 df_d = df[df['parameter']=='flexibility']

#                 a = np.sum(df_a['value'].values)
#                 b = np.sum(df_b['value'].values)
#                 c = np.sum(df_c['value'].values)
#                 d = np.mean(df_d['value'].values)
                
#                 df_agg['unixtime'] = [unixtime]
#                 df_agg['localtime'] = [localtime]
#                 df_agg['n_houses'] = [n_houses]
#                 df_agg['agg_actual'] = [a]
#                 df_agg['agg_proposed'] = [b]
#                 df_agg['agg_limit'] = [c]
#                 df_agg['agg_flexibility'] = [d]

                
#                 try:
#                     con = lite.connect('./ldc.db')
#                     df_agg.to_sql('aggregated', con, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)

#                 except Exception as e:
#                     pass
                

#                 break
#             except Exception as e:
#                 counter += 1
#                 print("Error update_ldc_db command:", e)
        
    
#         try:
#             if report: 
#                 print(df_agg)
#             return df_agg[['agg_actual', 'agg_proposed', 'agg_limit', 'agg_flexibility']]
#         except Exception as e:
#             print("Error in update_ldc_db command report:", e)
                    
            
            


def query(state='proposed', report=False):
    """ Fetch data from the EMI website and return a pd dataframe"""
    global n_houses
    # localtime = datetime.datetime.now().isoformat()    
    # unixtime = time.time()
    df = pd.DataFrame([])
    
    counter = 0 # counts the number of trials done to fecth data
    while True and counter < 10:
        try:
            # get load demands
            df_demand = pd.DataFrame.from_dict(send(dict({"all":state})),orient='index')
                       
            if (n_houses != len(np.unique(df_demand['house'].values))) and (counter < 8) or (len(df_demand.index)<1):
                raise Exception
            else:
                n_houses = len(np.unique(df_demand['house'].values))

            unixtime = np.mean(df_demand['unixtime'].values.astype(float))
            localtime = datetime.datetime.fromtimestamp(unixtime).isoformat()
            df_demand['id'] = df_demand.index
            df_demand['unixtime'] = unixtime
            df_demand['localtime'] = localtime
            df = pd.melt(df_demand, id_vars=["unixtime", "localtime", "house", "id", "type"], 
                      var_name="parameter", value_name="value")
            df = df.dropna()
            df['state'] = state

            # save to database
            con = lite.connect('./ldc.db')
            df.to_sql('data', con, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
            break
        except Exception as e:
            counter += 1
            print("Error update_ldc_db query count:", counter, 'log:', e)

    if report: 
        df_proposed = df[(df['state']=='proposed') & (df['parameter']=='total')].drop(['unixtime', 'id'], axis=1)
        df_actual = df[(df['state']=='actual') & (df['parameter']=='total')].drop(['unixtime', 'id'], axis=1)

        print(state, df_proposed, df_actual)
    return df                






#--- Test Calls--------------------------
if __name__=="__main__":
    snapshot = 1  # [s] interval of recording to database
    while True:
        try:
            if (int(time.time()) % snapshot == 0):
                # query(state='proposed', report=True)
                query(state='actual', report=True)
                # command(cmd='Q', freq=810, report=True)
                clean_database('./ldc.db')
                # time.sleep(snapshot-1)
        except Exception as e:
            print("Error in update_ldc_db: ", e)



