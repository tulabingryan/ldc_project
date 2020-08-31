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


def send(dict_msg, ip='224.0.2.0', port=10000 ):
    # send multicast query to all devices in the network
    multicast_group=(ip, port)
    # Create the datagram socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Set a timeout so the socket does not block
    # indefinitely when trying to receive data.
    sock.settimeout(3)

    # Set the time-to-live for messages to 1 so they do not
    # go past the local network segment.
    ttl = struct.pack('b', 1)  # number of hops
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    dict_demand = {}
    
    try:
        # Send data to the multicast group 
        message = str(dict_msg).encode()
        counter = time.perf_counter()
        sent = sock.sendto(message, multicast_group)

        # Look for responses from all recipients
        while True:
            try:
                data, server = sock.recvfrom(2048*10)
                message = data.decode("utf-8")
                dict_msg = ast.literal_eval(message)
                dict_demand.update(dict_msg)
            except socket.timeout:
                # print("Socket timed out.", time.perf_counter()-x, count, dif)
                break
            else:
                pass

    except Exception as e:
        print("Error in send:", e)

    finally:
        sock.close()

    return dict_demand


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
        data = cur.fetchall()

def clean_database(db_name='./ldc.db'):
    ''' This function cleans up the database from duplicated data record'''
    n_duplicates = check_for_duplicates(db_name=db_name)
    while n_duplicates > 0 :
        delete_duplicates(db_name)
        n_duplicates = check_for_duplicates(db_name=db_name)


def query(state='proposed', report=False):    
    # localtime = datetime.datetime.now().isoformat()    
    # unixtime = time.time()
    df = pd.DataFrame([])
    
    counter = 0 # counts the number of trials done to fecth data
    while True and counter < 10:
        try:
            # get proposed load demands
            df_demand = pd.DataFrame.from_dict(send(dict({"all":state})),orient='index')
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
            print("Error update_ldc_db query:", e)

    try:
        df_b = df[df['parameter']=='total']
        df_c = df[df['parameter']=='limit']
        utime = np.mean([np.mean([b,c]) for b,c in zip(df_b['unixtime'], df_c['unixtime'])])
        b = np.sum(df_b['value'].values)
        c = np.sum(df_c['value'].values)
        
        if report: 
            print(utime, state, " demand:", b, "limit:", c)
        return b
    except Exception as e:
        print("Error in update_ldc_db query report:", e)
                



def command(cmd='A1', freq=810, report=False):
    df = pd.DataFrame([])

    counter = 0 # counts the number of trials done to fecth data
    while True and counter < 10:
        try:
            # get proposed load demands
            df_demand = pd.DataFrame.from_dict(send(dict_msg={str(cmd):str(freq)}),orient='index')
            unixtime = np.mean(df_demand['unixtime'].values.astype(float))
            localtime = datetime.datetime.fromtimestamp(unixtime).isoformat()
            # p = np.sum(df_demand['proposed'].values.astype(float))
            # a = np.sum(df_demand['actual'].values.astype(float))
            # l = np.sum(df_demand['limit'].values.astype(float))

            df_demand['id'] = df_demand.index
            df_demand['unixtime'] = unixtime
            df_demand['localtime'] = localtime


            df = pd.melt(df_demand, id_vars=["unixtime", "localtime", "house", "id", "type"], 
                      var_name="parameter", value_name="value")

            df = df.dropna()
            df['state'] = 'agg'  # aggregated
            df = df[df['type']=='meter']
            
            print(df)
            # save to database
            con = lite.connect('./ldc.db')
            df.to_sql('data', con, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
            break
        except Exception as e:
            counter += 1
            print("Error update_ldc_db query:", e)

    try:
        df_a = df[df['parameter']=='proposed']
        df_b = df[df['parameter']=='actual']
        df_c = df[df['parameter']=='limit']
        utime = np.mean([np.mean([b,c]) for b,c in zip(df_b['unixtime'], df_c['unixtime'])])
        a = np.sum(df_a['value'].values)
        b = np.sum(df_b['value'].values)
        c = np.sum(df_c['value'].values)
        
        if report: 
            print(utime, "proposed:", a, " actual:", b, "limit:", c)
        return df
    except Exception as e:
        print("Error in update_ldc_db query report:", e)
                
        
        



#--- Test Calls--------------------------
if __name__=="__main__":
    snapshot = 1  # [s] interval of recording to database
    while True:
        try:
            if (int(time.time()) % snapshot == 0):
                query(state='proposed', report=True)
                query(state='actual', report=True)
                #command(cmd='A1', freq=810, report=True)
                clean_database('./ldc.db')
                # time.sleep(snapshot-1)
        except Exception as e:
            print("Error in update_ldc_db: ", e)
