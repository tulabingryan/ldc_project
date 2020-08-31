"""
Python script that fetches site elevation, timezone, and weather data
Created on Thu Apr 23 16:32:46 2015
@author: Ryan Tulabing
"""

import pytz
import json
import csv
import numpy as np
import pandas as pd
import os
import sqlite3 as lite
import datetime, time
import threading, queue
import numpy as np
# import multiprocessing
import time, datetime

# for multicast
import socket
import struct
import sys
import json
import ast


from dateutil.parser import parse
import urllib.request
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

from scipy.interpolate import CubicSpline


#---import local packages---
import MULTICAST
import CLOCK
import FUNCTIONS

class Weather():
    """docstring for Weather"""
    n = 0
    def __init__(self, latitude, longitude, timestamp, realtime=False, mcast_ip='238.173.254.147', mcast_port=12604):  
        self.name = 'Weather_{}'.format(self.n+1)
        self.type = 'weather'
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = 5.0
        self.timezone = 'Pacific/Auckland'  # default timezone is in New Zealand
        self.realtime = realtime
        if self.realtime:
            self.timestamp = time.time()
        else:  # simulation
            self.timestamp = timestamp
            
        # initialize run of essential functions
        # self.get_elevation(report=False)
        # self.get_timezone(report=False)
        

        # multicasting parameters
        self.mcast_ip = mcast_ip
        self.mcast_port = mcast_port
        
        # print("Running...", self.name, "local mcast:", self.mcast_ip, ":", self.mcast_port)
        self.df_weather = pd.DataFrame([])

        try:
            self.df_weather = pd.read_csv('./profiles/latest_weather.csv')
            # check if current saved file is the needed weather data
            list_unix = self.df_weather['unixtime'].values.astype(int)
            if (self.timestamp < np.min(list_unix)) | (self.timestamp > np.max(list_unix)):
                print("Obsolete weather data...")
                self.df_weather = self.get_weatherHistory(unixtime=int(self.timestamp), report=False)
            else:
                pass
            

        except Exception as e:
            print("Error in Weather init:", e)
            self.df_weather = self.get_weatherHistory(unixtime=int(self.timestamp), report=False)

        
        self.df_weather = self.df_weather[["unixtime",  "temperature", "humidity", "windspeed"]]
        self.df_weather = self.df_weather.rolling(1).mean()
        self.df_weather = self.df_weather.dropna()
        self.df_weather['unixtime'] = self.df_weather['unixtime'].astype(int)
        self.dict_interpolator = {}
        for k in self.df_weather:
            self.dict_interpolator[k] = CubicSpline(self.df_weather['unixtime'].values, self.df_weather[k].values)
        
    def get_coordinateSet(self, from_sensor=False, report=False):
        """" Determine the latitude and longitude coordinates 
        based on address inputed in the googlemap api """
        return FUNCTIONS.get_coordinates()

    def get_elevation(self, report=False):
        ''' This function determines the elevation of the location specified by latitude and longitude
        '''
        try:
            raise Exception
            # api_str = 'https://maps.googleapis.com/maps/api/elevation/json?locations=' + str(self.latitude) + ',' + str(self.longitude) + '&key=' + 'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'
            # req = urllib.request.Request(api_str)
            # f = urllib.request.urlopen(req)
            # json_string = f.read()
            # parsed_json = json.loads(json_string.decode('utf-8'))

            # elevation = parsed_json["results"][0]['elevation']  # get the elevation
            # if report:
            #     print('Elevation: ',elevation)
            #     print('Location: ',parsed_json["results"][0]['location'])
            # else:
            #     pass


            # # save the whole json file
            # json_out = open('elevation.json', 'w')
            # json.dump(json_string, json_out, indent = None )
            # json_out.close()
            
            f.close()
        except Exception as e:
            print("Error WEATHER get_elevation:",e)
            # print("Assuming 5m elevation.")
            elevation = 5.0

        return elevation


    def get_timezone(self, report=False):
        '''
        This function determines the timezone in the location specified by the latitude and longitude
        '''
        try:
            raise Exception
            # api_str = 'https://maps.googleapis.com/maps/api/timezone/json?location=' + str(self.latitude) + ',' + str(self.longitude) + '&timestamp=' + str(self.timestamp) + '&key=AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'
            # req = urllib.request.Request(api_str)
            # f = urllib.request.urlopen(req)
            # json_string = f.read()
            # parsed_json = json.loads(json_string.decode('utf-8'))

            # self.timezone = parsed_json['timeZoneId']
            
            # # # save the whole json file
            # # json_out = open('timezone.json', 'w')
            # # json.dump(json_string, json_out, indent = None )
            # # json_out.close()
            
            f.close()

        except Exception as e:
            print("Error WEATHER get_timezone: ", e)
            self.timezone = 'Pacific/Auckland'
        
        if report: print(self.timezone)

        return self.timezone




    def get_weatherHistory(self, unixtime, report=False):
        """
        Get weather conditions from the darkskyio database
        at the specified time span startTime and endTime
        """
        # k = '9677bc93058aec560eb917d33842870e'  # yahoomail
        # k = '564ebd21967d3ef7ec6c5d15f588bd26'  # gmail
        unixtime = int(unixtime)
        
        # print ('Fetching weather data for ', datetime.datetime.fromtimestamp(unixtime).date())
        # Collect past weather condition using Dark Sky Forecast API 
        # for specified location and timestamp
        # in SI units, using specified API key

        try:
            if self.realtime: 
                for i in range(5):
                    try:
                        url = f'https://api.darksky.net/forecast/9677bc93058aec560eb917d33842870e/{self.latitude},{self.longitude},{int(unixtime)}?units=si'
                        req = Request(url)
                        date = datetime.datetime.fromtimestamp(unixtime)
                        date = date.strftime('%Y-%m-%d %H:%M:%S')
                        response = urlopen(req)
                        respData = response.read()
                        response.close()
                        respData = respData.decode("utf-8")
                        data = json.loads(respData)
                        # timezone = data['timezone']  # to get the timezone
                        hourly_ob = data['hourly']  # to get the hourly conditions
                        # daily_ob = data['daily']  # to get the daily condition
                        df_weather = pd.DataFrame(hourly_ob['data'])
                        print('Weather data from online...')
                        break
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        print("Error in ", self.name, " get_weatherHistory:", e)
                        time.sleep(1)
                ### the following lines will raise an Exception if no data collected from online
                df_weather = df_weather.rename(columns={'time':'unixtime'})
                df_weather = df_weather[['unixtime', 'humidity', 'temperature', 'windSpeed', 'pressure']]
                df_weather.columns=['unixtime', 'humidity', 'temperature', 'windspeed', 'pressure']
            else:
                raise Exception

        except Exception as e:
            print("Offline: resorting to equivalent past weather data...", e)
            dt_range = pd.date_range(start=pd.to_datetime(unixtime, unit='s'), freq='H', periods=24, tz='UTC')
            dt_range = dt_range.tz_convert('Pacific/Auckland')

            yearhour = (7*24*(dt_range.week-1)) + (24*dt_range.weekday) + dt_range.hour

            start = yearhour[0]
            end = yearhour[-1]

            try:
                con = lite.connect('./profiles/weather.db', isolation_level=None)
                con.execute('pragma journal_mode=wal;')
                with con:
                    cur = con.cursor()
                    cur.execute("SELECT humidity, temperature, windspeed, pressure FROM data WHERE yearhour BETWEEN {} AND {} ORDER BY yearhour ASC".format(start, end))
                    data = np.array(cur.fetchall())
                    df_weather = pd.DataFrame(data, columns=['humidity', 'temperature', 'windspeed', 'pressure'])
                    df_weather['unixtime'] = dt_range.astype(int) * 1e-9
                    
                # Save (commit) the changes
                con.commit()
                con.close()
            except Exception as e:
                print("Error connecting to ./profiles/weather.db:", e)


        # ensure that the weather values are floats
        # df_weather[['humidity', 'temperature', 'windspeed']] = df_weather[['humidity', 'temperature', 'windspeed']].astype(float) 
        # df_weather = df_weather.reset_index(drop=True)
        self.df_weather = df_weather.astype(float).reset_index(drop=True)
        del df_weather
        
        # save to hard drive
        self.df_weather.to_csv('./profiles/latest_weather.csv', index=False)


        if report: print(self.df_weather)


        return self.df_weather


    def weather_now(self, timestamp):
        try:
            if float(timestamp) >= float(self.df_weather['unixtime'].tail(1).values):
                self.df_weather = self.get_weatherHistory(unixtime=float(timestamp + 3600), report=False)
                self.df_weather = self.df_weather[["unixtime",  "temperature", "humidity", "windspeed"]]
                self.df_weather = self.df_weather.rolling(1).mean()
                self.df_weather = self.df_weather.dropna()
                self.df_weather['unixtime'] = self.df_weather['unixtime'].astype(int)
                self.dict_interpolator = {}
                for k in self.df_weather:
                    self.dict_interpolator[k] = CubicSpline(self.df_weather['unixtime'].values, self.df_weather[k].values)
                
        except Exception as e:
            print("Error in fetch new weather data:", e)

        # get weather conditions for current timestamp
        try:
            # self.To = np.interp([float(timestamp)], self.df_weather['unixtime'].astype('float64'), self.df_weather['temperature'].astype('float64'))[0]
            self.To = self.dict_interpolator['temperature'](float(timestamp))
            self.To = np.round(self.To, 3)
            # if type(self.To) != float: raise Exception
        except Exception as e:
            print("Error in ", self.name, " To:", e)
            self.To = 20.0

        try:
            # self.humidity = np.interp([timestamp],self.df_weather['unixtime'].astype('float64'),self.df_weather['humidity'].astype('float64'))[0]
            self.humidity = self.dict_interpolator['humidity'](float(timestamp))
            self.humidity = np.round(self.humidity, 3)
            # if type(self.humidity) != float: raise Exception
        except Exception as e:
            print("Error in ", self.name, " humidity:", e)
            self.humidity = 0.75
            
        try:
            # self.windspeed = np.interp([timestamp],self.df_weather['unixtime'].astype('float64'),self.df_weather['windspeed'].astype('float64'))[0]
            self.windspeed = self.dict_interpolator['windspeed'](float(timestamp))
            self.windspeed = np.round(self.windspeed, 3)
            # if type(self.windspeed) != float: raise Exception
        except Exception as e:
            print("Error in ", self.name, " windspeed:", e)
            self.windspeed = 0
        

        dict_weather ={str(self.type):
            {"type": self.type,
            "unixtime": timestamp,
            "temp_out": self.To,
            "humidity": self.humidity,
            "windspeed": self.windspeed,
            }}
        return dict_weather


    def get_weather(self, timestamp):
    
        if float(timestamp) >= float(self.df_weather['unixtime'].values[-1]):
            self.df_weather = self.get_weatherHistory(unixtime=float(timestamp + 3600), report=False)
            self.df_weather = self.df_weather[["unixtime",  "temperature", "humidity", "windspeed"]]
            self.df_weather = self.df_weather.rolling(1).mean()
            self.df_weather = self.df_weather.dropna()
            self.df_weather['unixtime'] = self.df_weather['unixtime'].astype(int)


            self.dict_interpolator = {}
            for k in self.df_weather:
                self.dict_interpolator[k] = CubicSpline(self.df_weather['unixtime'].values, self.df_weather[k].values)
            
    
        self.To = np.round(self.dict_interpolator['temperature'](float(timestamp)), 3)
        self.humidity = np.round(self.dict_interpolator['humidity'](float(timestamp)), 3)
        self.windspeed = np.round(self.dict_interpolator['windspeed'](float(timestamp)), 3)
        
        return {'temp_out':self.To, 
            'humidity':self.humidity, 
            'windspeed':self.windspeed
            }





    #--- BACKGROUND THREADS ---
    def receive_mcast(self):
        # Receive multicast message from the group
        # ip and port should be local in actual implementation
        # however, for testing, global ip and port are used
        # since queries for weather data are limited to 1000 per day
        multicast_ip = self.mcast_ip
        port = self.mcast_port        
        multicast_group = (multicast_ip, port)  # (ip_address, port)
        # Create the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind to the server address
        sock.bind(multicast_group)
        # Tell the operating system to add the socket to
        # the multicast group on all interfaces.
        group = socket.inet_aton(multicast_ip)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            mreq)
        
        # Receive/respond loop
        while True:
            # receive and decode message
            data, address = sock.recvfrom(1024)
            received_msg = data.decode("utf-8")
            try:
                dict_msg = ast.literal_eval(received_msg)
            except Exception as e:
                print("Error in WEATHER.py receive_mcast ast.literal_eval:", e)

            # prepare data to send, fetch latest data from the queue
            try:
                # Note: house name is used as the key, 'all' is a query from the aggregator  
                for key in dict_msg:
                    if key in ["W"]:
                        self.timestamp = dict_msg[key]
                        # fetch new weather data if current buffer is used up
                        dict_weather = self.weather_now(self.timestamp)
                        message_toSend = str(dict_weather).encode()
                        # send message
                        sock.sendto(message_toSend, address)
                    
                    else:
                        pass

            except Exception as e:
                print("Error in ", self.name, " receive_mcast:", e)
                pass                      
        return



  



###################### Tests #################################################################################################################

if __name__ == '__main__':
    latitude = '-37.0321'
    longitude = '174.9794'

    mcast_ip = '238.173.254.147'
    mcast_port = 12604
    a = datetime.datetime.now().timestamp()
    b = a + (3600*24)
    W = Weather(latitude=latitude, longitude=longitude, timestamp=a)

    W.get_weatherHistory(unixtime=time.time()-(3600*24), report=True)
    W.get_weatherHistory(unixtime=time.time(), report=True)

    # 'https://api.forecast.io/forecast/9677bc93058aec560eb917d33842870e/-36.866590076725494,174.77534779638677,1588308038.888062?units=si'
    # 'https://api.darksky.net/forecast/9677bc93058aec560eb917d33842870e/-36.866590076725494,174.77534779638677,1588308038?units=si'

    for i in range(3600*24*5):
        print(W.weather_now(timestamp=a+i))
        time.sleep(0.5)

    del W
################################################################################################################################################
