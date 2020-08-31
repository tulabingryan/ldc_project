#############################################################
# Auxiliary Codes for different functions used in Aggretion of Flexible Loads
# by: Ryan Tulabing
# LBNL 2015
#############################################################



import sys
import os
import time
import datetime
import csv
import numpy as np
import pandas as pd
from scipy import stats
import glob
import solar
from dateutil.parser import parse
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError
import json
import requests
import socket



def populate(quantity, lowerlimit, upperlimit, average):
    # This function creates a set of numbers in gaussian distribution
    # Parameters:
    #   quantity = number of samples
    #   lowerlimit = lowest possible value
    #   upperlimit = highest possible value
    #   average = average value of the whole set 
    lower = lowerlimit
    upper = upperlimit
    mu = average
    N = quantity
    sigma = (((upper-mu)**2.) + ((lower-mu)**2.) )/2.
    value = stats.truncnorm.rvs((lower - mu)/sigma, (upper-mu)/sigma, loc=mu, scale=sigma, size = N)
    return value

def updateCSV(dataToWrite,csvFilename,header):
    # This function writes the updates the data in a csv file
    # Parameters:
    #   dataToWrite = array containing the data to be written
    #   csvFilename = the filename of the csv file where the data should be written
    #   header = an tuple of words representing the headers for the csv file

    fileToWrite = open(csvFilename, 'wt')
    writer = csv.writer(fileToWrite)
    writer.writerow(header)
    for i in range(0,len(dataToWrite)):
        newList = dataToWrite[i]
        writer.writerow(newList)
    fileToWrite.close()
    return

def to_csv(self, data, dist, headers):
    # This function writes the data into a csv file
    # if file does not exist write header 
    df = pd.DataFrame(data, index=self.timeHistory, columns=headers)
    if not os.path.isfile(dist):
       df.to_csv(dist, index=True, index_label='timestamp', header=headers)
    else: # else it exists so append without writing the header
        df.to_csv(dist, mode='a', header=False)
    return

def save_toDatabase(arrayToSave, databaseName, headers):
    """ This function saves an array of data to an SQL database"""
    con = lite.connect(databaseName)
    with con:
        cur = con.cursor()
        #cur.execute('DROP TABLE IF EXISTS tableName')  # deletes tableName in the database
        cur.execute('CREATE TABLE IF NOT EXISTS STOCKTABLE('+ str(headers) + ')')
        cur.executemany('INSERT INTO STOCKTABLE VALUES(?,?,?,?,?,?,?,?)',arrayToSave)
    return


def process_PV(PV):
    PV.get_solarPower()
    PV.record_History()
    return

def process_hvacBase(hvac):
    hvac.update_data()
    return

def update_data(aggregators, aggregators_A, aggregators_B, aggregators_C, DREvents):
    # get influencial factors: time, weather, market price powerlimit
    # DR case
    

    for i in range(0,len(aggregators)):
        # update houses
        [house.update_data() for house in aggregators[i].houses]
        # update power sources for DR case
        [source.get_powerOutput() for source in aggregators[i].supplyUnits]
        [source.record_History() for source in aggregators[i].supplyUnits]
        # aggregate available supply
        aggregators[i].sum_supply()
        # get demands
        aggregators[i].get_demands()
        # aggregate total demand
        aggregators[i].sum_demand()
        # get flexibilities
        aggregators[i].get_flexibility()
        # prioritize loads
        aggregators[i].prioritize_loads()
        if i==0: 
            aggregators[i].allocate_power([],'commands_base.csv')
        else:
            aggregators[i].allocate_power(DREvents,'commands_DR.csv')

        # simulate behaviour
        aggregators[i].simulate_models()

        # aggregation steps
        # update sum of demand
        aggregators[i].sum_demand()
        # sum actual demand per phase
        aggregators_A[i].sum_demand()
        aggregators_B[i].sum_demand()
        aggregators_C[i].sum_demand()
        # take average status of all loads
        aggregators[i].take_average()
        aggregators_A[i].take_average()
        aggregators_B[i].take_average()
        aggregators_C[i].take_average()


        # record status to history
        aggregators[i].record_history()
        aggregators_A[i].record_history()
        aggregators_B[i].record_history()
        aggregators_C[i].record_history()
        
    return 




def get_coordinates(query='79 Mullins Road, Ardmore, Papakura, New Zealand', from_sensor=False, report=False):
    """" Determine the latitude and longitude coordinates 
    based on address inputed in the googlemap api """

    query = query.encode('utf-8')
    params = {
        'address': query,
        'sensor': 'false',
        'key':'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k',
    }

    # Get site location coordinates: latitude and longitude
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    # req = url + urlencode(params)
    try:
        # response = urlopen(req)
        # respData = response.read()
        # response.close()

        # respData = respData.decode("utf-8")
        # data = json.loads(respData)
        r = requests.get(url, params=params)
        data = r.json()

        if data['results']:
            location = data['results'][0]['geometry']['location']
            latitude, longitude = location['lat'], location['lng']
            
            if report: 
                print(query, latitude, longitude)    
            
        else:
            latitude = -36.86667 
            longitude = 174.76667
            print(query, "No results... retrying...")
            
    except HTTPError as e:
        print('The server couldn\'t fulfill the request.')
        print('Error code: ', e.code)
        latitude = -36.86667 
        longitude = 174.76667
            
        
    except URLError as e:
        print('We failed to reach a server.')
        print('Reason: ', e.reason)
        latitude = -36.86667 
        longitude = 174.76667
        
    else:
        print("Unknown error. Assuming -36.86667, 174.76667")  
        latitude = -36.86667 
        longitude = 174.76667
            
    return latitude, longitude

### test ###
# get_coordinates(query='79 Mullins Road, Ardmore, Papakura, New Zealand', report=True)        

### end test ### 


def get_elevation(latitude, longitude, report=False):
    """ Determine the elevation of the location 
    specified by latitude and longitude
    """
    url = 'https://maps.googleapis.com/maps/api/elevation/json?locations='\
        + str(latitude) + ',' + str(longitude) + '&key=' + 'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'
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
                return 5.0
            
        except HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
            return 5.0
        except URLError as e:
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
            return 5.0
        else:
            print("Unknown error. Assuming 5m")  
            return 5.0


def get_timezone(latitude,longitude,timestamp,report=False):
    """ Determines the timezone based on 
    location specified by the latitude and longitude """
    global timezone

    url = 'https://maps.googleapis.com/maps/api/timezone/json?location='\
        + str(latitude) + ',' + str(longitude) + '&timestamp='\
        + str(timestamp) + '&key=' + 'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'
    req = Request(url)

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
            return 'Pacific/Auckland'
        
    except HTTPError as e:
        print('The server couldn\'t fulfill the request.')
        print('Error code: ', e.code)
        return 'Pacific/Auckland'
    except URLError as e:
        print('We failed to reach a server.')
        print('Reason: ', e.reason)
        return 'Pacific/Auckland'
    else:
        print("Unknown Error. Assuming Pacific/Auckland")  # everything is fine
        return 'Pacific/Auckland'


        
def get_weatherHistory(latitude, longitude, unixtime, report=False):
    """
    Get weather conditions from the darkskyio database
    at the specified time span startTime and endTime
    """
    global timezone

    
    # print ('Fetching weather data . . .')
    
    # Collect past weather condition using Dark Sky Forecast API 
    # for specified location and timestamp
    # in SI units, using specified API key

    url = 'https://api.forecast.io/forecast/' + '564ebd21967d3ef7ec6c5d15f588bd26' + '/' + str(latitude) \
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
            print("Error FUNCTIONS get_weatherHistory access web:", e)
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
            df_weather.to_sql('data', con, flavor=None, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)

    except Exception as e:
        print("Error FUNCTIONS get_weatherHistory process data:", e)

    return df_weather

  


def get_weatherNow(latitude, longitude, report=False):
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
    url = 'https://api.forecast.io/forecast/' + '564ebd21967d3ef7ec6c5d15f588bd26' + '/' \
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
        print("Error FUNCTIONS get_weatherNow:", e)
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



def get_pastWeather(n_days, latitude=-37.0321395, longitude=174.9793777, report=False):
    """ Get past prices in n_days"""
    t_delta = datetime.timedelta(days=n_days)
    end = datetime.datetime.now()
    start = end - t_delta
    
    dateSeries = pd.date_range(start=start, end=end, freq='D', normalize=False) 
    for date in dateSeries:
        unixtime = int(time.mktime(date.timetuple()))
        get_weatherHistory(latitude, longitude, unixtime=unixtime, report=report)
        clean_database('./weather.db')


def check_last(db_name='./weather.db'):
    try:
        con = lite.connect(db_name)
        with con:
            # get last record timestamp
            c = con.cursor()
            c.execute('SELECT unixtime FROM data ORDER BY unixtime DESC LIMIT 1')             
            latest_timestamp = np.array(c.fetchall()).flatten()[0]
        
        return latest_timestamp

    except Exception as e:
        print("Error FUNCTIONS check_last", e)
        



def update_database(db_name='./weather.db', latitude=-37.0321395, longitude=174.9793777):
    ''' Update weather database'''
    con = lite.connect(db_name)
    with con:
        cur = con.cursor()
        cur.execute('SELECT DISTINCT interval FROM data ORDER BY interval DESC LIMIT 10')
        dates = np.array(cur.fetchall())

    start = dates[0][0]
    start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    end = datetime.datetime.now()

    n_days_passed = int((end-start).total_seconds() / (60*60*24))  # convert seconds to days

    n_days = int(np.max([n_days_passed, 3]))
    get_pastWeather(n_days, latitude, longitude, report=False)




def get_public_ip(report=False):
    ''' Get public IP adress of the router'''
    req = 'http://ip-api.com/json'
    count = 0
    public_ip = '127.0.0.1'
    while True and count < 5:
        try:
            response = urlopen(req)
            respData = response.read()
            respData = respData.decode("utf-8")
            response = json.loads(respData)
            public_ip = response['query']
            break
        except Exception as e:
            print("Error FUNCTIONS get_public_ip:", e)
            count += 1

    if report: print('external ip address: {}'.format(public_ip))

    return public_ip

##---test get_public_ip---
# ip = get_public_ip()
# print(ip)
##------------------


def get_local_ip():
  # get local ip address
  while True:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.connect(("8.8.8.8", 80))
      local_ip = s.getsockname()[0]
      s.close()
      break
    except Exception as e:
      time.sleep(3)
      pass
    except KeyboardInterrupt:
      break
  return local_ip

##---test get_public_ip---
# ip = get_local_ip()
# print(ip)
##------------------


def create_states(power_list=[75,150,300,600,1200,2400,4800,4800], report=False):
    # create a 256 combination of power levels in the power_list

    try:
        ### read csv
        df_relay = pd.read_csv('./relay_states.csv')
        df_states = pd.read_csv('./power_states.csv')
        
    except Exception as e:    
        state_list = [np.array(list('{0:08b}'.format(x))).astype(int) for x in np.arange(256)]
        df_relay = pd.DataFrame(state_list)
        array_states = np.array(state_list) * np.array(power_list).T
        df_states = pd.DataFrame(array_states)
        df_states['value'] = df_states.sum(axis=1)
        ### save to csv 
        # df_states['orig_idx'] = df_states.index
        # df_states = df_states.sort_values('value').reset_index(drop=True)
        # df_relay.to_csv('./relay_states.csv', index=False)
        # df_states.to_csv('./power_states.csv', index=False)

    if report:
        print(df_relay)
        print(df_states)
        print(sorted(df_states['value']))
    return df_relay, df_states
# test #
# create_states(report=True)
# end test


def calc_distance(a, b):
    return np.linalg.norm(a-b)

# test
# d = calc_distance(43, 24)
# print(d)
# end test


def find_nearest(value, value_list, report=False, border='lower'):
    # map value to the nearest value in the value_list
    try:
        ds = [calc_distance(value, x) for x in value_list]
        idx = np.argsort(ds)
        closest_value = value_list[idx[0]]
        

        if value_list[idx[0]] <  value_list[idx[1]]:
            lower_idx = idx[0]
            lower_value = value_list[idx[0]]
            upper_idx = idx[1]
            upper_value = value_list[idx[1]]
        else:
            lower_idx = idx[1]
            lower_value = value_list[idx[1]]
            upper_idx = idx[0]
            upper_value = value_list[idx[0]]
        
        

        if report: 
            print("Value:{}  closest:{}  lower:{}  upper:{}  ".format(value, closest_value, lower_value, upper_value))

        if border=='lower':
            return lower_idx, lower_value
        elif border=='upper':
            return upper_idx, upper_value
        elif border=='closest':
            return idx[0], closest_value

        
    except Exception as e:
        print("Error find_nearest:", e)
        df_relay, df_states = create_states()
        value_list = df_states['value']
        ds = [calc_distance(value, x) for x in value_list]
        idx = np.argmin(ds)
        if report: print(idx)
        return idx, value_list[idx]



def relay_pinouts(value, df_relay, df_states, report=False):
    # drive the raspi pinouts
    try:
        idx, nearest_power = find_nearest(value, df_states['value'], border='lower', report=False)
        residual = value - nearest_power
        if report: print('Nearest:{}, Residual:{}, Pins:{}'.format(nearest_power, residual, df_relay.loc[idx].values))
        return df_relay.loc[idx].values, nearest_power, residual 
    except Exception as e:
        #print("Error relay_pinouts:",e)
        df_relay, df_states = create_states()
        idx, nearest_power = find_nearest(value, df_states['value'], border='lower')
        residual = value - nearest_power
        if report: print('Nearest:{}, Residual:{}, Pins:{}'.format(nearest_power, residual, df_relay.loc[idx].values))
        return df_relay.loc[idx].values, nearest_power, residual


def pinouts(value, df_states, report=False):
    df_states['idx'] = df_states.index
    # df_states = df_states.sort_values(['value'])
    # df_states = df_states[df_states['value']<=value]
    residual = value % 75
    nearest_power = value - residual
    new_pins = df_states[[0,1,2,3,4,5,6,7]][df_states['value']==nearest_power].values[0].flatten()
    new_pins = (new_pins>0)*1
    if report: print('Nearest:{}  Residual:{}  Pins:{}'.format(nearest_power, residual, new_pins))

    return new_pins, nearest_power, residual



# ### test
# df_relay, df_states = create_states(report=False)

# for i in range(10):
#     value = np.random.normal(5000, 1000)

#     print(f'value:{value}')
#     pins, nearest_power, residual = relay_pinouts(value, df_relay, df_states, report=True)
    
#     pinouts(value, df_states, report=True)
## end test

