# update_weather_db.py
# Author: Ryan Tulabing
# Date: 2017-09-20
# University of Auckland, New Zealand
# This module fetches weather data from the darkskyio database 
# and save it in the local database ./weather.db

import datetime
import csv
from dateutil.parser import parse
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError
import json
import pandas as pd
import numpy as np
import sqlite3 as lite
import time
import os
from dateutil import tz

# set timezone 
tz = tz.gettz('Pacific/Auckland')
timezone = 'Pacific/Auckland'
os.environ['TZ'] = timezone
time.tzset()


# API keys
# forecastKey = '564ebd21967d3ef7ec6c5d15f588bd26'  # for darkskyio weather api
mapAPIkey = 'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'  # for googlemap api
# mapAPIkey = 'AIzaSyC4qUfNhcRiaHdWQx7m7z8sH0EumEN469I '
darkskyKey_yahoo = '9677bc93058aec560eb917d33842870e' # for darkskyio weather api using yahoomail account
darkskyKey_gmail = '564ebd21967d3ef7ec6c5d15f588bd26' # for darkskyio weather api using gmail acount
'''
Note: Default site location is 1124 Harvard Ln, Ardmore, Papakura 2582, New Zealand
latitude=-37.0321395, longitude=174.9793777
'''

def get_coordinates(query, from_sensor=False, report=False):
    """" Determine the latitude and longitude coordinates 
    based on address inputed in the googlemap api """

    query = query.encode('utf-8')
    params = {
        'address': query,
        'sensor': "true" if from_sensor else "false"
    }

    # Get site location coordinates: latitude and longitude
    googleGeocodeUrl = 'http://maps.googleapis.com/maps/api/geocode/json?'
    req = googleGeocodeUrl + urlencode(params)
    success = False
    attempts = 0
    # try fetching data from the internet for 10 attempts 
    while not(success) and (attempts <= 10): 
        try:
            response = urlopen(req)
            respData = response.read()
            response.close()

            respData = respData.decode("utf-8")
            data = json.loads(respData)
            if data['results']:
                location = data['results'][0]['geometry']['location']
                latitude, longitude = location['lat'], location['lng']
                
                if report: 
                    print(query, latitude, longitude)    
                
                success = True
                return latitude, longitude

            else:
                print(query, "No results... retrying...")
                return None, None            

        except HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
            
        except URLError as e:
            print('We failed to reach a server.')
            print('Reason: ', e.reason)

        else:
            print("Unknown error.")  
            



def get_elevation(mapAPIkey, latitude, longitude, report=False):
    """ Determine the elevation of the location 
    specified by latitude and longitude
    """
    url = 'https://maps.googleapis.com/maps/api/elevation/json?locations='\
        + str(latitude) + ',' + str(longitude) + '&key=' + str(mapAPIkey)
    req = Request(url)
    success = False
    attempts = 0
    # try fetching data from the internet for 10 attempts 
    while not(success) and (attempts<=10):
        try:
            response = urlopen(req)
            respData = response.read()
            response.close()
            respData = respData.decode("utf-8")
            data = json.loads(respData)

            if data['results']:
                elevation = data["results"][0]["elevation"]  # get the elevation
            
                if report:
                    print ("Elevation: " + str(elevation))
                
                success = True
                return elevation
    
            else:
                print("No results... retrying...")
                return None
            
        except HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
        except URLError as e:
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        else:
            print("Unknown error.")  


def get_timezone(mapAPIkey,latitude,longitude,timestamp,report=False):
    """ Determines the timezone based on 
    location specified by the latitude and longitude """
    global timezone

    url = 'https://maps.googleapis.com/maps/api/timezone/json?location='\
        + str(latitude) + ',' + str(longitude) + '&timestamp='\
        + str(timestamp) + '&key=' + str(mapAPIkey)
    req = Request(url)

    success = False
    attempts = 0
    while not(success) and (attempts<=10):
        try:
            response = urlopen(req)
            respData = response.read()
            response.close()

            respData = respData.decode("utf-8")
            data = json.loads(respData)

            if data['timeZoneId']:
                timezone = data['timeZoneId']  # get timezone
                
                if report:
                    print("latitude: "+ latitude)
                    print("longitude: "+ longitude)
                    print ("timezone: "+ timezone)

                # adjust timezone setting used for runtime
                os.environ['TZ'] = timezone
                time.tzset()
                success = True
                return timezone
            else:
                print("No results... retrying...")
                return None
            
        except HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
        except URLError as e:
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        else:
            print("Unknown Error")  # everything is fine


        
def get_weatherHistory(api_key, latitude, longitude, unixtime, report=False):
    """
    Get weather conditions from the darkskyio database
    at the specified time span startTime and endTime
    """
    global timezone

    
    # print ('Fetching weather data . . .')
    
    # Collect past weather condition using Dark Sky Forecast API 
    # for specified location and timestamp
    # in SI units, using specified API key

    url = 'https://api.forecast.io/forecast/' + api_key + '/' + str(latitude) \
        + ',' + str(longitude) + ','+ str(unixtime) + '?units=si'
    req = Request(url)

    date = datetime.datetime.fromtimestamp(unixtime)
    date = date.strftime('%Y-%m-%d %H:%M:%S')
    success = False
    attempts = 0
    while not(success) and (attempts<=10):
        try:
            response = urlopen(req)
            respData = response.read()
            response.close()

            respData = respData.decode("utf-8")
            data = json.loads(respData)
            
            if data['hourly']:
                timezone = data['timezone']  # to get the timezone
                hourly_ob = data['hourly']  # to get the hourly conditions
                # daily_ob = data['daily']  # to get the daily condition
                # localTime = float(unixtime)
                # localTime = datetime.datetime.timetuple(currentDate) # time.localtime(localTime)

                df_weather = pd.DataFrame(hourly_ob['data'])
                success = True
            else:
                print("No results... retrying...")
                success = False
                attempts += 1
                return None
        
        except Exception as e:
            print(e)
            attempts += 1


    try:
        df_weather['timezone'] = timezone
        df_weather = df_weather.rename(columns={'time':'unixtime'})
        df_weather['interval'] = pd.to_datetime(df_weather['unixtime'],unit='s')
        df_weather['interval'] = [a.tz_localize('UTC').tz_convert(timezone) for a in df_weather['interval']]
        df_weather['interval_datetime'] = [a.isoformat() for a in df_weather['interval']]
        df_weather['interval'] = [a.strftime("%Y-%m-%d %H:%M:%S") for a in df_weather['interval']]
        df_weather['latitude'] = latitude
        df_weather['longitude'] = longitude

        df_weather = df_weather[['interval', 'interval_datetime', 'unixtime', 'apparentTemperature', 'humidity', 'pressure', 'temperature', 'windSpeed', 'timezone','latitude','longitude']]
        if report: print(df_weather[['interval','timezone','temperature']])

        # save to database
        con = lite.connect('./weather.db')
        with con:
            df_weather.to_sql('data', con, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)



    except Exception as e:
        print(e)

    

    return df_weather

  


def get_weatherNow(api_key, latitude, longitude, report=False):
    """ Get weather data from darkskyio 
            Current conditions
            Minute-by-minute forecasts out to 1 hour (where available)
            Hour-by-hour forecasts out to 48 hours
            Day-by-day forecasts out to 7 days
            in SI units, using specified API key
    """
    global timezone

    df_weather = pd.DataFrame()  # empty holder of weather data

    # print ('Fetching weather data . . .')

    # Collect realtime weather condition using Dark Sky Forecast API
    url = 'https://api.forecast.io/forecast/' + api_key + '/' \
        + str(latitude) + ',' + str(longitude) + '?units=si'
    req = Request(url)

    success = False
    attempts = 0
    while not(success) and (attempts<=10):
        try:
            response = urlopen(req)
            respData = response.read()
            response.close()

            respData = respData.decode("utf-8")
            data = json.loads(respData)

            timezone = data['timezone']  # gets the timezone
            hourly_ob = data['hourly']  # to get the hourly conditions
            # daily_ob = data['daily']  # to get the daily condition
            data = pd.DataFrame(hourly_ob['data'])
            df_weather = df_weather.append(data)
            success = True

        except HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
            attempts += 1
        except URLError as e:
            print('We failed to reach the server.')
            print('Reason: ', e.reason)
            attempts += 1
        else:
            print("Fetching data. . . " ) # everything is fine
            attempts += 1


    df_weather['timezone'] = timezone
    df_weather = df_weather.rename(columns={'time':'unixtime'})
    df_weather['interval'] = pd.to_datetime(df_weather['unixtime'],unit='s')
    df_weather['interval'] = df_weather['interval'].tz_localize('UTC').tz_convert(timezone)
    df_weather['interval_datetime'] = [a.isoformat() for a in df_weather['interval']]

    # set time column as index
    df_weather = df_weather.set_index(['interval'])
    
    # save to database
    try:
        con = lite.connect('./weather.db')
        with con:
            cur = con.cursor()
            cur.execute('SELECT DISTINCT interval_datetime FROM data ORDER BY interval_datetime DESC LIMIT 1000')
            dates = np.array(cur.fetchall())
        
        if df_weather['interval_datetime'].tail(1).values in dates:  # check if the new data is already in the database 
            # print("New data already exist in the local database.")
            # print("Latest record: ", dates[0])
            report = False
        else:
            # save the new data to the database
            df_weather.to_sql('data', con, flavor=None, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
        
    except Exception as e:
        print(e)
        df_weather.to_sql('data', con, flavor=None, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)

    if report:
        print(df_weather.head(1))

    return df_weather




def check_for_duplicates(db_name='./weather.db', report=False):
    ''' This function checks the records of an sql database for duplicates'''
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()        
        cur.execute('SELECT * FROM data GROUP BY interval, interval_datetime, unixtime, apparentTemperature, humidity, pressure, temperature, windSpeed, timezone, latitude, longitude HAVING COUNT(*)> 1')
        data = np.array(cur.fetchall())
    
    if report:
        print('Database record with duplicates:' + str(len(data)))
    # print(data.T[0:4].T)
    return len(data)

def delete_duplicates(db_name='./weather.db'):
    """ Delete duplicated record in database and keep the latest version"""
    print('Deleting duplicates...')
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()
        cur.execute('DELETE FROM data WHERE ROWID NOT IN (SELECT max(ROWID) FROM data GROUP BY interval, interval_datetime, unixtime, apparentTemperature, humidity, pressure, temperature, windSpeed, timezone,latitude, longitude)')
        

def clean_database(db_name='./weather.db'):
    ''' This function cleans up the database from duplicated data record'''
    n_duplicates = check_for_duplicates(db_name=db_name, report=True)
    while n_duplicates > 0 :
        delete_duplicates(db_name)
        n_duplicates = check_for_duplicates(db_name=db_name, report=True)



def get_pastWeather(n_days, report=False):
    """ Get past prices in n_days"""
    t_delta = datetime.timedelta(days=n_days)
    end = datetime.datetime.now()
    start = end - t_delta
    
    dateSeries = pd.date_range(start=start, end=end, freq='D', normalize=False) 
    for date in dateSeries:
        unixtime = int(time.mktime(date.timetuple()))
        get_weatherHistory(api_key=darkskyKey_gmail, latitude=-37.0321395, longitude=174.9793777, unixtime=unixtime, report=report)
        clean_database('./weather.db')


def update_database(db_name='./weather.db'):
    counter = 0
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()
        cur.execute('SELECT DISTINCT interval FROM data ORDER BY interval DESC LIMIT 10')
        dates = np.array(cur.fetchall())

    # print(dates)
    start = dates[0][0]
    start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    end = datetime.datetime.now()

    n_days_passed = int((end-start).total_seconds() / (60*60*24))  # convert seconds to days

    n_days = int(np.max([n_days_passed, 3]))
    get_pastWeather(n_days=n_days, report=False)




if __name__=='__main__':
    while True:
        print("Updating weather database on the background...")
        update_database(db_name='./weather.db')
        print("Sleeping for 24 hours...")
        time.sleep(60*60*24)













#-----------------------------------------------------------------------------------------------------
# def getDataFromCSV(csv_file):
#     data = pd.DataFrame.from_csv(csv_file, header=0, sep=',',
#         index_col=0, parse_dates=True, encoding='utf-8',
#         tupleize_cols=False, infer_datetime_format=True)
#     return data



# def processDataSolar(row):
#     # preconditioning of variables
#     timezone =  row['timezone']
#     os.environ['TZ'] = timezone
#     time.tzset()
#     timeIndex = row.name
#     timestamp = datetime.datetime.timetuple(timeIndex)
#     temperature = row['temperature']
#     humidity = row['humidity']
#     cloudCover = row['cloudCover']
#     windspeed = row['windSpeed']
#     latitude = row['latitude']
#     longitude = row['longitude']
#     installed_PV = row['installed_PV']
#     array_Efficiency = row['array_Efficiency']
#     inverter_Efficiency = row['inverter_Efficiency']
#     installed_Wind = row['installed_Wind']
#     tilt = row['tilt']
#     azimuth = row['azimuth']
#     albedo = row['albedo']
#     elevation = row['elevation']
#     solar = get_solarPower(timestamp, latitude, longitude, elevation, tilt,
#             azimuth, albedo, temperature, humidity, cloudCover,installed_PV,
#             array_Efficiency, inverter_Efficiency)
#     return solar

# def processDataWind(row):
#     # preconditioning of variables
#     timezone =  row['timezone']
#     os.environ['TZ'] = timezone
#     time.tzset()
#     timeIndex = row.name
#     timestamp = datetime.datetime.timetuple(timeIndex)
#     temperature = row['temperature']
#     humidity = row['humidity']
#     cloudCover = row['cloudCover']
#     windspeed = row['windSpeed']
#     latitude = row['latitude']
#     longitude = row['longitude']
#     installed_PV = row['installed_PV']
#     array_Efficiency = row['array_Efficiency']
#     inverter_Efficiency = row['inverter_Efficiency']
#     installed_Wind = row['installed_Wind']
#     tilt = row['tilt']
#     azimuth = row['azimuth']
#     albedo = row['albedo']
#     elevation = row['elevation']
#     wind = get_windPower(installed_Wind, windspeed, temperature)
#     return wind


# def get_forecast(data):
#     print("Processing data...")
#     data['solarForecast'] = data.apply(processDataSolar, axis='columns', raw=True)
#     data['windForecast'] = data.apply(processDataWind, axis='columns', raw=True)
#     return data


# #----------------------------------------------------------------------------------------------------------------------------------

  
