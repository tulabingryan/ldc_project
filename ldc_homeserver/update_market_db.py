# -----------------------------------------------------------------
# update_market_db.py
# Real-time Market Price of Electricity in New Zealand
# Source: Electricity Market Information (EMI)
# WEB: emi.portal.azure-api.net
# This file is used to update the ./market.db, storing the electricity market transactions from EMI


import http.client, urllib.request, urllib.parse, urllib.error, base64
import json, datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sqlite3 as lite
import time
import os
from dateutil import tz

# set timezone 
tz = tz.gettz('Pacific/Auckland')
timezone = 'Pacific/Auckland'
os.environ['TZ'] = timezone
time.tzset()



def contact_EMI(startTime=None, endTime=None, report=False):
    """ Fetch data from the EMI website and return a pd dataframe"""
    # startTime and endTime are in datetime.isoformat()
    headers = {
        # Request headers
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': 'a477e8bfd457450493877e188fb2cf09',
    }

    if startTime==None or endTime==None:
        params = urllib.parse.urlencode({})
    else:
        params = urllib.parse.urlencode({
            # Request parameters for specific date and time
            '$filter': "interval_datetime gt datetime'" + startTime + "' and interval_datetime lt datetime'" + endTime + "'",
        })
    
        
    success = False
    counter = 0
    while not(success):
        try:
            counter += 1
            # print('Fetching market data from the internet...')
            conn = http.client.HTTPSConnection('emi.azure-api.net')
            conn.request("GET", "/rtp/?%s" % params, "{body}", headers)
            response = conn.getresponse()
            data = response.read()
            # print(data)
            # close connection
            conn.close()

            # decode data
            parsed = json.loads(data.decode('utf-8'))
            df_all = pd.DataFrame.from_dict(parsed, orient='columns')
            success = True
        except Exception as e:
            if counter <= 10: 
                success = False
            else:
                success = True


    try:
        # save to database
        con = lite.connect('./market.db')
        with con:
            cur = con.cursor()
            cur.execute('SELECT DISTINCT interval_datetime FROM data ORDER BY interval_datetime DESC LIMIT 1000')
            dates = np.array(cur.fetchall())
        
        if df_all['interval_datetime'].tail(1).values in dates:  # check if the new data is already in the database 
            # print("New data already exist in the local database.")
            # print("Latest record: ", dates[0])
            report = False
        else:
            # save the new data to the database
            df_all.to_sql('data', con, flavor=None, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
        
    except Exception as e:
        print(e)
        df_all.to_sql('data', con, flavor=None, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)

    if report:
        print(df_all.head(1))
    return list(df_all)
        



def check_for_duplicates(db_name='./market.db', report=False):
    ''' This function checks the records of an sql database for duplicates'''
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()        
        cur.execute('SELECT * FROM data GROUP BY pnode, interval HAVING COUNT(*)> 1')
        data = np.array(cur.fetchall())
    if report:
        print('Database record with duplicates:' + str(len(data)))
    
    return len(data)


def delete_duplicates(db_name='./market.db'):
    """ This function saves an array of data to an SQL database"""
    print('Deleting duplicates...')
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()
        cur.execute('DELETE FROM data WHERE ROWID NOT IN (SELECT max(ROWID) FROM data GROUP BY interval, pnode, price, generation, load, interval_datetime, five_min_period, isDayLightSavingHR)')

'''
def delete_duplicates(db_name='./market.db'):
    """ This function saves an array of data to an SQL database"""
    print('Deleting duplicates...')
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()
        cur.execute('SELECT DISTINCT interval, pnode, price, generation, load, interval_datetime, five_min_period, isDayLightSavingHR FROM data ORDER BY interval_datetime ASC')
        #cur.execute('SELECT DISTINCT * FROM data ORDER BY interval_datetime ASC')
        data = np.array(cur.fetchall())
        # print(data.T[0:5].T)
        # delete the table
        cur.execute('DROP TABLE IF EXISTS data')
        # recreate the table and save the unique data records
        cur.execute('CREATE TABLE IF NOT EXISTS data(interval, pnode, price, generation, load, interval_datetime, five_min_period, isDayLightSavingHR)')
        cur.executemany('INSERT INTO data VALUES(?, ?, ?, ?, ?, ?, ?, ?)',data)
    return
'''

def clean_database(db_name='./market.db'):
    ''' This function cleans up the database from duplicated data record'''
    n_duplicates = check_for_duplicates(db_name=db_name, report=True)
    while n_duplicates > 0 :
        delete_duplicates(db_name)
        n_duplicates = check_for_duplicates(db_name=db_name, report=True)



def get_pastPrices(n_days):
    """ Get past prices in n_days"""
    t_delta = datetime.timedelta(days=1)
    end = datetime.datetime.now()
    for i in range(n_days):
        start = end - t_delta
        startTime = start.isoformat()
        endTime = end.isoformat()
        end = start
        contact_EMI(startTime, endTime, report=False)
    clean_database('./market.db')



def update_database(db_name='./market.db'):
    counter = 0
    con = lite.connect(db_name)
    try:
        with con:
            cur = con.cursor()
            cur.execute('SELECT DISTINCT interval_datetime FROM data ORDER BY interval_datetime DESC')
            dates = np.array(cur.fetchall())


        print("Latest date on record: ", dates[0:1])
        start = dates[0][0]
        start = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        end = datetime.datetime.now()
        if True:
        # if (end-start).total_seconds() > 60*0 : 
            startTime = start.isoformat()
            endTime = end.isoformat()
            contact_EMI(startTime, endTime, report=False)    
        else:
            contact_EMI(report=False)
        # clean up the database
        clean_database('./market.db')
    except Exception as e:
        contact_EMI(report=False)

def clean_nodeID(nodeID):
    node_split = nodeID.split()
    key = node_split[0]
    return key



#--- Test Calls--------------------------

while True:
    try:
        print("Updating market database on the background...")
        update_database(db_name='./market.db')
        print("Done. Sleeping for 5 minutes...")
        time.sleep(60*5)
    except Exception as e:
        print(e)
        print("No internet connection.")






########### Getting data on  Installation Control Points (ICP) #############
# The following functions are not used for the current stage of development

def get_ICPData(report=False):
    """ Fetch ICP data from the EMI website"""
    headers = {
        # Request headers
        'Ocp-Apim-Subscription-Key': 'd349fa755cdf44de9a6ede5ef2d10013',
    }

    params = urllib.parse.urlencode({})

    try:
        conn = http.client.HTTPSConnection('emi.azure-api.net')
        conn.request("GET", "/ICPConnectionData/list/?ids={list_of_ICPs}&%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read()
        # print(data)
        df = pd.read_json(path_or_buf=data, orient='values', typ='frame', dtype=True,
            convert_axes=True, convert_dates=True, keep_default_dates=True,numpy=False)
        conn.close()
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))

    # f, (ax04) = plt.subplots(1, 1, figsize=(10,4))
    # HVAC2_Temp.plot(ax=ax04, legend=True, title='MarketPrice',color='r')
    if report:
        print(df)
        # parsed = json.loads(data.decode('utf-8'))
        # print(parsed)
    return df


def search_ICPData(unit='145', street='Basset Road',
    suburb='Remuera',region='Auckland',report=False):
    """ Get the ICP data based on a given address """
    headers = {
        # Request headers
        'Ocp-Apim-Subscription-Key': 'd349fa755cdf44de9a6ede5ef2d10013',
    }

    params = urllib.parse.urlencode({
        # Request parameters
        'unitOrNumber': '145', #'{string}',
        'streetOrPropertyName': 'Basset Road', #'{string}',
        'suburbOrTown': 'Remuera', #'{string}',
        'region': 'Auckland', #'{string}',
    })

    try:
        conn = http.client.HTTPSConnection('emi.azure-api.net')
        conn.request("GET", "/ICPConnectionData/search/?%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        df = pd.read_json(path_or_buf=data, orient='values', typ='frame', dtype=True,
            convert_axes=True, convert_dates=True, keep_default_dates=True,numpy=False)
    
        if report: print(df)
    
        conn.close()
    except Exception as e:
        print(e)
        # print("[Errno {0}] {1}".format(e.errno, e.strerror))

    

