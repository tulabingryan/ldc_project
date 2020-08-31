"""
Python script that fetches site elevation, timezone, and weather data
Created on Thu Apr 23 16:32:46 2015
@author: Ryan Tulabing
"""
import datetime
import time
import urllib.request
import json
import csv
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt

def get_elevation(mapAPIkey, latitude, longitude, printout=False):
    ''' This function determines the elevation of the location specified by latitude and longitude
    '''
    api_str = 'https://maps.googleapis.com/maps/api/elevation/json?locations=' + str(latitude) + ',' + str(longitude) + '&key=' + mapAPIkey
    req = urllib.request.Request(api_str)
    f = urllib.request.urlopen(req)
    json_string = f.read()
    parsed_json = json.loads(json_string.decode('utf-8'))

    elevation = parsed_json["results"][0]['elevation']  # get the elevation
    if printout:
        print('Elevation: ',elevation)
        print('Location: ',parsed_json["results"][0]['location'])
    else:
        pass
    # # save the whole json file
    # json_out = open('elevation.json', 'w')
    # json.dump(json_string, json_out, indent = None )
    # json_out.close()
    
    f.close()

    print ('Searching elevation . . . finished')

    return elevation

def get_timezone(mapAPIkey,latitude,longitude,timestamp):
    '''
    This function determines the timezone in the location specified by the latitude and longitude
    '''
    api_str = 'https://maps.googleapis.com/maps/api/timezone/json?location=' + str(latitude) + ',' + str(longitude) + '&timestamp=' + str(timestamp) + '&key=' + str(mapAPIkey)
    req = urllib.request.Request(api_str)
    f = urllib.request.urlopen(req)
    json_string = f.read()
    parsed_json = json.loads(json_string.decode('utf-8'))

    timezone = parsed_json['timeZoneId']

    # # save the whole json file
    # json_out = open('timezone.json', 'w')
    # json.dump(json_string, json_out, indent = None )
    # json_out.close()
    
    f.close()

    print ('Adjusting timezone . . . finished')

    return timezone


def get_weatherHistory(api_key, latitude, longitude, startTime, endTime, report=False):
    '''this function returns a csv file with weather conditions within the specified startTime and endTime times
    '''
    print ('Fetching weather data . . .')
    timeInc = datetime.timedelta(days = 1)
    currentStamp = int(startTime)
    endTimeStamp = int(endTime)
    currentDate = datetime.datetime.fromtimestamp(currentStamp)
    df_hourlyWeather = pd.DataFrame()
    trial = 0
    try:
        while currentStamp <= endTimeStamp:
            timestamp = str(currentStamp)
            # Collect past weather condition using Dark Sky Forecast API for specified location and timestamp
            # in SI units, using specified API key

            api_str = 'https://api.darksky.net/forecast/' + str(api_key) + '/' + str(latitude) + ',' + str(longitude) + ','+ str(timestamp)+'?units=si'\
                        #+'?exclude=currently,minutely,daily,alerts,flags'
            
            req = urllib.request.Request(api_str)
            f = urllib.request.urlopen(req)
            json_string = f.read()
            f.close()  # close the connection
            parsed_json = json.loads(json_string.decode('utf-8'))
            hourly_ob = parsed_json['hourly']  # to get the hourly conditions
            localTime = float(timestamp)
            localTime = time.localtime(localTime)

            df_now = pd.DataFrame.from_dict(hourly_ob['data'],orient='columns')
            df_hourlyWeather = pd.concat([df_hourlyWeather,df_now], ignore_index=True)

            #--Iterate for next request using the next day timestamp
            if len(df_now) > 0:
                print(currentDate)
                currentDate = currentDate + timeInc
                currentStamp = int(time.mktime(currentDate.timetuple()))
                currentDate = datetime.datetime.fromtimestamp(currentStamp)
                trial = 0

            else:
                trial += 1
                if trial > 10: raise Exception   
        else:
            print ('Finished saving weather history.')
            df_hourlyWeather = df_hourlyWeather.dropna(axis=1, how='any')
            df_hourlyWeather.to_csv('hourly_'+str(int(startTime))+'_'+str(int(endTime))+'.csv', index=False)
            if report: print(df_hourlyWeather)
            return df_hourlyWeather
    except Exception as e:
        print('Connection error: ',e)
    

def get_outsideConditions(darkskyKey, latitude, longitude, startTime, endTime, online=True, stepSize=60, save=True, report=False, plot=False):
    # This function fetches the outside temperature and relative humidity from the tmy3 database
    # Create data of outside conditions by Resolution using interpolation
    # resolution is determined by stepsize
    try:
        if online == True:
            # get new data from online database
            df_hourlyWeather = get_weatherHistory(darkskyKey, latitude, longitude, startTime, endTime)
        else:
            raise Exception
    except Exception as e:
        print("Offline: resorting to previously saved file.")
        filename = 'hourly_'+str(int(startTime))+'_'+str(int(endTime))+'.csv'
        df_hourlyWeather = pd.read_csv(filename, header=0, index_col='datetime', parse_dates=True, infer_datetime_format=True)

    #---drop columns with text values
    df_hourlyWeather = df_hourlyWeather.drop(['summary','icon'], axis=1).astype(float)
    #---make timestamps as index
    df_hourlyWeather.index = df_hourlyWeather['time']
    #--- Minutely weather data
    df_minutelyWeather = pd.DataFrame()
    df_minutelyWeather['time'] = np.arange(df_hourlyWeather.index[0], (df_hourlyWeather.index[-1]), stepSize)  # by Resolution (minutely) timestamps
    df_minutelyWeather.index = df_minutelyWeather['time']
    
    for col in list(df_hourlyWeather):
        df_minutelyWeather[col] = np.interp(df_minutelyWeather['time'],df_hourlyWeather['time'],df_hourlyWeather[col]) # by Resolution (minutely)
    
    # df_minutelyWeather.index = pd.to_datetime(df_minutelyWeather['time'],infer_datetime_format=True,unit='s')
    # df_minutelyWeather.index.name = 'datetime'
    df_minutelyWeather = df_minutelyWeather.rename(columns={'time':'timestamp'})
    
    #---Outputs---
    if save: df_minutelyWeather.to_csv('minutely_'+str(int(startTime))+'_'+str(int(endTime))+'.csv', index=True)
    if report: print(df_minutelyWeather)
    if plot:
        df_minutelyWeather.index = pd.to_datetime(df_minutelyWeather['timestamp'],infer_datetime_format=True,unit='s')
        df_minutelyWeather.index.name = 'datetime'
        df_minutelyWeather[['temperature']].plot()
        # df_minutelyWeather.plot(kind='area',ax=ax00, stacked=False, legend=True, label=True, x_compat=False, secondary_y=['air_temperature','outdoor_temperature'])
        plt.show()

    return df_minutelyWeather


def plot_df(filename):
    df_minutelyWeather = pd.read_csv(filename, header=0, index_col='time', parse_dates=True, infer_datetime_format=True)
    df_minutelyWeather.index = pd.to_datetime(df_minutelyWeather.index,infer_datetime_format=True,unit='s')
    df_minutelyWeather.index.name = 'datetime'
    df_minutelyWeather[['temperature']].plot()
    plt.show()




###################### Tests #################################################################################################################
#---Uncomment the following line to download historical weather data from the web
# darkskyKey_yahoo = '9677bc93058aec560eb917d33842870e'
darkskyKey_gmail = '564ebd21967d3ef7ec6c5d15f588bd26'
mapAPIkey = 'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'
# Austin Texas
latitude, longitude = '30.292432', '-97.699662'  # from Pecan Street Database
elevation = get_elevation(mapAPIkey, latitude, longitude, printout=True)
startTime_tuple = datetime.datetime(2016,1,1,0,0,0).timetuple()
endTime_tuple = datetime.datetime(2016,12,31,23,59,0).timetuple()
startTime = time.mktime(startTime_tuple)
endTime = time.mktime(endTime_tuple)
# timeLen = datetime.timedelta(days=1)
# currentDate = datetime.datetime.fromtimestamp(int(startTime))
# endTime = str(int(time.mktime(datetime.datetime.timetuple(currentDate + timeLen))))
timezone = get_timezone(mapAPIkey,latitude,longitude,startTime)

data = get_outsideConditions(darkskyKey_gmail, latitude, longitude, startTime, endTime, online=True, save=True, plot=True, report=True)


################################################################################################################################################

#---test plot_df---
# plot_df('minutely_1346414400.0_1377950399.0.csv')
# plot_df('minutely_1377950400.0_1409486399.0.csv')

# 30.2672° N, 97.7431° W  # general