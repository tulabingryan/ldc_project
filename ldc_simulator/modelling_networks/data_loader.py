"""
data_loader.py
Prepare data for machine learning
Author: Ryan Tulabing, University of Auckland, New Zealand, 2017
"""
import numpy as np
import pandas as pd
from time import (process_time,perf_counter,sleep,)
import matplotlib.pyplot as plt
import subprocess



def cmd(command='ls',args='.'):
    process = subprocess.Popen([command,args])
    (output, err) = process.communicate()
    print(output,err)

def normalize(x,min_input=None,max_input=None,method='minmax',index=''):
    """ Normalize the data to range from 0 to 1. """
    df = pd.DataFrame(x)
    if index=='Date':    
        dates = df.pop('Date')
        df.index = dates

    if min_input==None: min_input = df.min()
    if max_input==None: max_input = df.max()
    

    if method=='minmax':
        return (df-min_input)/(max_input-min_input) 
    else:  # minmax
        return (df - df.mean())/df.std()


def one_hot(x, n_classes=10):
    """
    One hot encode a list of sample labels. Return a one-hot encoded vector for each label.
    : x: List of sample Labels
    : return: Numpy array of one-hot encoded labels
     """
    x = pd.DataFrame(x)
    x = normalize(x,method='minmax') * (n_classes-1)
    x = x.round(0).astype(int)
    return np.eye(n_classes)[x]

def get_colnames(filename, header=0, report=False):
    """ Get the names of the columns in the input file"""
    for chunk in pd.read_csv(filename, chunksize=2, header=header, parse_dates=True, infer_datetime_format=True):
        # chunk = chunk.dropna(axis=1, how='any')  # exclude columns with na values
        colnames = list(chunk)
        if report: print(colnames)
        return colnames

def get_minmax(filename, col, header=0, report=False):
    """ Get the minimum and maximum value of a data"""

    min_value = 999999
    max_value = -999999

    for chunk in pd.read_csv(filename, chunksize=10000, header=header):
        chunk_min = chunk[col].min()
        chunk_max = chunk[col].max()
        if chunk_min < min_value: min_value = chunk_min
        if chunk_max > max_value: max_value = chunk_max    

    if report: print("min: ", min_value, "max: ",max_value)
    return min_value, max_value

def time_counter(report=False):
    """ Count the elapsed time of a process"""

    previous_time = perf_counter()
    current_time = perf_counter()
    frequency = 0
    sleep_time = 1/800
    try:  
        while True:
            sleep(sleep_time*0.9)
            current_time = perf_counter()
            frequency = 1 /(current_time-previous_time)
            previous_time = current_time
            print(frequency)

    finally:                   
        print("Finished.")



def data_generator(filename,x_col=None,y_col=None,drop_col=['dataid','use'],header=0,batch_size=100,index_format='datetime',report=False):
    """ Fetch data from a file and preprocess it for machine learning"""
    for chunk in pd.read_csv(filename, chunksize=batch_size, index_col=x_col,header=header, parse_dates=True, infer_datetime_format=True):
        # chunk = chunk.dropna(axis=1, how='any')  # exclude columns with na values
        # print(x_col)
        print(list(chunk))
        for col in drop_col:
            try:
                chunk = chunk.drop(col, axis=1)  # remove the unwanted columns
            except Exception as e:
                print(e)

        if y_col==None: 
            y_col = list(chunk)

        if index_format=='datetime':
            chunk.index = pd.to_datetime(chunk.index,infer_datetime_format=True,unit='s')
            chunk.index = chunk.index.round('min')
            chunk.index = chunk.index.to_pydatetime()
        
        else:
            pass
        
        # chunk = process_dates(chunk)
        x = chunk.index
        y = chunk[y_col]

        if report:
            print(list(chunk))
            print(x)
            print(y)
        yield x,y

def clean_date(filename,report=False):
    for chunk in pd.read_csv(filename, chunksize=10, header=0, parse_dates=True, infer_datetime_format=True):
        if report: print(chunk)
        return chunk['localminute']



def clean_data(data,report=False):
    """Remove outliers from the dataset"""
    df_data = pd.DataFrame(data)
    avg = df_data.mean()
    std = df_data.std()
    if report: 
        print("avg: ", avg)
        print("std: ", std)
    return df_data


def convert_F2C(F):
    """ Convert degF to degC"""
    C = (F - 32) * 5.0 / 9.0
    return C 


def process_dates(df,report=False):
    """ Translate dates in the index of df into day of week, day of year, holidays, etc..."""
    df['day_of_week'] = df.index.dayofweek
    df['day_of_year'] = df.index.dayofyear
    if report:
        print(df.tail(20))
    return df



def prepare_data(x,y,report=False):
    """ Process input features and labels"""




# test -----------------------------------------------------------------
def test_datagenerator(x_col=None,y_col=None):
    xy_data = data_generator(filename,x_col=x_col, y_col=y_col, drop_col=['dataid'], header=header, batch_size=24*60, report=False)
    query = pd.Period('2015')
    print(query.start_time, query.end_time)
    # try:
    for i in range(365*10):
        x,y = next(xy_data)
        # print(x[0])
        # print(list(y))
        # print(x)
        print(y.tail)
        # print(normalize(y,min_input=0.0,max_input=20.0))
        # print(one_hot(y,n_classes=10))

        # y['total'] = y[[ 'kitchen1','kitchenapp1','livingroom1','livingroom2','bathroom1','bathroom2','bedroom1','bedroom2','office1','air1','airwindowunit1','car1','clotheswasher1','dishwasher1','disposal1','drye1','furnace1','lights_plugs1','lights_plugs2','outsidelights_plugs1','outsidelights_plugs2','microwave1','oven1','refrigerator1','refrigerator2']].sum(axis=1)
        # y['hvac'] = y[['air1','airwindowunit1']].sum(axis=1)
        # y['ev'] = y['car1']
        # y['lights'] = y[['lights_plugs1','lights_plugs2','outsidelights_plugs1','outsidelights_plugs2']].sum(axis=1)
        # y['fridges'] = y[['refrigerator1','refrigerator2']].sum(axis=1)
        # y['freezers'] = y[['freezer1']].sum(axis=1)
        # y['total2'] = y[['hvac','ev','lights','fridges','nntcl','other_baseload']].sum(axis=1)

        #---classified loads---
        # y['tcl'] = y[['hvac','heater1','fridges','freezers','waterheater1','waterheater2','winecooler1']].sum(axis=1)
        # y['nntcl'] = y[['clotheswasher1','c2o','dishwasher1','disposal1','drye1','dryg1','sprinkler1','pool1','pool2','poolpump1','pump1','aquarium1']].sum(axis=1)
        # y['battery'] = y[['car1']].sum(axis=1)
        # y['baseload'] = y[['microwave1','oven1','furnace1','kitchen1','kitchenapp1','livingroom1','livingroom2','bathroom1','bathroom2','bedroom1','bedroom2','office1',]].sum(axis=1)
        # y['total'] = y[['tcl','nntcl','battery','baseload']].sum(axis=1)
        # y_col2= ['total','tcl','nntcl','battery','baseload']
        
        #---sample
        # y_col2 = ['airwindowunit1']#,'oven1','range1','venthood1']
        # y_col2 = list(y)
        #---plot data---
        if True: #((x[0] >= query.start_time) and (x[0] <= query.end_time)):
            # for d in list(y[['air_temperature','outdoor_temperature']]): y[d] = convert_F2C(y[d]) # convert temperature data to degC
            f, (ax00) = plt.subplots(1, 1, figsize=(10,4))
            y[['electric heating element','fan']].plot(kind='line',ax=ax00, stacked=False, legend=True, label=True, x_compat=False,) # secondary_y=['air_temperature','outdoor_temperature'])
            
            ax00.get_yaxis().get_major_formatter().set_useOffset(False)  # do not use scientific notation
            ax00.set_ylabel('Power(kW)')
            ax00.set_xlabel('Datetime')
            ax00.yaxis.grid(True, which="major")
            ax00.xaxis.grid(True, which="minor")
            
            plt.title('Demand')
            plt.show()

            #---test date processing---
            # y = process_dates(y,report=True)
                

    # except Exception as e:
    #     print("Stopped at iteration ", i, " Error: ",e)

def join_data(filename0, filename1, filename2, save_filename):
    xy_data_temp = data_generator(filename0,x_col=x_col, y_col=['temp_c'], drop_col=['dataid'], header=header, batch_size=400*24*60, index_format='datetime',report=False)
    xy_data_power = data_generator(filename1,x_col=x_col, y_col=['air1','lights_plugs1'], drop_col=['dataid'], header=header, batch_size=400*24*60, index_format='datetime',report=False)  # ,'livingroom1','livingroom2','outsidelights_plugs1
    xy_data_weather = data_generator(filename2,x_col=['time'], y_col=['temperature','timestamp'], drop_col=[], header=header, batch_size=400*24*60, index_format='datetime', report=False)
    df_combined = pd.DataFrame()
    query = pd.Period('2015')
    print(query.start_time, query.end_time)
    for i in range(365*10):
        x0,y0 = next(xy_data_temp)
        x1,y1 = next(xy_data_power)
        x2,y2 = next(xy_data_weather)
        
        #-- delete duplicates
        y0 = y0[~y0.index.duplicated(keep='first')]
        y1 = y1[~y1.index.duplicated(keep='first')]
        y2 = y2[~y2.index.duplicated(keep='first')]

        y0.index = y0.index.astype(np.int64) // 10**9
        # y1.index = y1.index.astype(np.int64) // 10**9
        y2_idx = y2.index # save index of y2
        y2.index = y2.index.astype(np.int64) // 10**9  # convert index of y2 to unix
        
        y2['temp_c'] = np.interp(y2.index,y0.index,y0['temp_c'])
        
        y2.index = y2_idx  # convert back to datetime format the index of y2
        
        

        df_combined = pd.concat([y1,y2],axis=1, join='outer')
        # print(df_combined.head())
        df_combined.index.name = 'localtime'
        if len(df_combined) < 1:
            print(y0,y1)
        else:
            print(df_combined.tail)

        df_combined.to_csv(save_filename, index=True, mode='w')

        f, (ax00) = plt.subplots(1, 1, figsize=(10,4))
        df_combined[['temp_c','temperature']].plot(kind='line',ax=ax00, stacked=False, legend=True, label=True, x_compat=False,) # secondary_y=['air_temperature','outdoor_temperature'])
        ax00.get_yaxis().get_major_formatter().set_useOffset(False)  # do not use scientific notation
        ax00.set_ylabel('Temperature(degC)')
        ax00.set_xlabel('Datetime')
        ax00.yaxis.grid(True, which="major")
        ax00.xaxis.grid(True, which="minor")
        ax01 = ax00.twinx()
        ax01.set_ylabel('Power (kW)')
        df_combined[['air1','lights_plugs1']].plot(kind='line',ax=ax01, stacked=False, legend=True, label=True, x_compat=False, color=['red','cyan'])
        
        plt.xticks(rotation='vertical')
        plt.title('Demand')
        plt.show()
        
        
        
        # if ((x0[0] >= query.start_time) and (x0[0] <= query.end_time)):
            





# filename = 'E_ID1714_SingleFamily_Austin1950_A1934_20120901_20170930.csv' 
# filename = 'E_ID_SingleFamily_Austin2014_A6408_20160101_20161231.csv'



# y_col = ['use','kitchen1','kitchenapp1','livingroom1','livingroom2','bathroom1','bathroom2','bedroom1','bedroom2','office1','air1','airwindowunit1','car1','clotheswasher1','dishwasher1','disposal1','drye1','furnace1','lights_plugs1','lights_plugs2','outsidelights_plugs1','outsidelights_plugs2','microwave1','oven1','refrigerator1','refrigerator2']

#---test onehot---
# print(one_hot([0,4,5,6],n_classes=10))

#---test cmd---
# cmd()

#---test clean_date---
# clean_date(filename)

#--get the column names---
# x_col = ['']
# y_col = get_colnames(filename,header=header,report=True) 
# x_col = ['localminute']
# y_col = ['refrigerator1']


#---minmax test---
# min_value, max_value = get_minmax(filename, col='air1', report=True)


#--data generator test---
# test_datagenerator(x_col=x_col,y_col=y_col)


#---join data test

# FOR 2015
# filename0 = 'training_data/indoor_temp_1714_2015.csv'
# filename1 = 'training_data/E_ID1714_2015.csv'
# filename2 = 'training_data/darksky_2015.csv'
# header = 0
# x_col = ['localminute']
# join_data(filename0, filename1, filename2, save_filename='hvac1714_2015.csv')

# FOR 2016
filename0 = 'training_data/indoor_temp_1714_2016.csv'
filename1 = 'training_data/E_ID1714_2016.csv'
filename2 = 'training_data/darksky_2016.csv'
header = 0
x_col = ['localminute']
join_data(filename0, filename1, filename2, save_filename='hvac1714_2016.csv')

#---time counter test---
# time_counter(report=True)


