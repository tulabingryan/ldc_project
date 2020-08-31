##./grid_server.py
# -*- coding: utf-8 -*-
import flask
import plotly.plotly as py
import math
import dash
from dash.dependencies import Output, Input
import dash_core_components as dcc
import dash_html_components as html
import colorlover as cl
from flask_caching import Cache
# from pandas_datareader.data import DataReader
from collections import deque
import plotly.graph_objs as go
import dash_auth
import base64

import random
import time, datetime
import pandas as pd
import numpy as np
import sqlite3 as lite
import os
import uuid
import re

try:
    import serial
except Exception as e:
    print("Error importing serial module:", e)

try:
    # for interacting with raspi
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)     # set up BOARD GPIO numbering 
except Exception as e:
    print("Error importing RPi GPIO:", e)

try:
    import spidev
except:
    pass


# multicasting packages
import socket
import struct
import sys
import time
import json
import ast

import socket

import MULTICAST



# app = dash.Dash('grid-server')
# server = app.server

# Keep this out of source code repository - save in a file or a database
# VALID_USERNAME_PASSWORD_PAIRS = [
#     ['user', 'pass'],
#     ['superuser', 'superpass']
# ]

# app = dash.Dash('auth')
# auth = dash_auth.BasicAuth(
#     app,
#     VALID_USERNAME_PASSWORD_PAIRS
# )


server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server)
app.config.suppress_callback_exceptions = True
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True



# Declare global variables
global dict_cmd, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand, df_data, df_data_cols, display_limit
display_limit =True


def get_timezone(latitude,longitude,timestamp,report=False):
    """ Determines the timezone based on 
    location specified by the latitude and longitude """
    global timezone

    url = 'https://maps.googleapis.com/maps/api/timezone/json?location='\
        + str(latitude) + ',' + str(longitude) + '&timestamp='\
        + str(timestamp) + '&key=' + 'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'
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




# adjust timezone setting used for runtime
global timezone
try:
    timezone = get_timezone(latitude, longitude, timestamp=time.time())
except:
    timezone = 'Pacific/Auckland'
try:
    os.environ['TZ'] = timezone
    time.tzset()
    print("Timezone:", timezone)
except Exception as e:
    print("Error setting timezone:", e)




def read_rs232():
    # read data from rs232
    try:
        ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate = 38400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
            )

        ser.flushInput()
        ser.flushOutput()
        time.sleep(0.1)
        while True:
            response = ser.read(1).decode()
            
            if response[0] == 'p':
                response = ser.read(16).decode().split()
                power, csum, k = response
                # print("power:", power, " csum:", csum, " k:", k)
                agg_demand = float(power)
                break
            else:
                pass
        if agg_demand < 100000 and agg_demand >= 0:
            return agg_demand
        else:
            return None
    except Exception as e:
        # print("Error in read_rs232.", e)
        return None

def write_rs232(msg):
    # send data to serial port
    try:
        ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate = 38400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
            )

        ser.flushInput()
        ser.flushOutput()
        s_msg = list(msg)
        for s in s_msg:
            ser.write(s.encode('ascii'))
            time.sleep(0.001)
        ser.write(b'\r')
        time.sleep(0.5)

    except Exception as e:
        raise e

def write_db(df_data, db_name='./ldc_all.db', table='data'):
        # write a dataframe to the database
        db_writer = lite.connect(db_name, isolation_level=None)    
        db_writer.execute('pragma journal_mode=wal;')  # set for non-blocking to enable simultaneous reading
        df_data.to_sql(table, db_writer, schema=None, if_exists='append', index=False, chunksize=None, dtype=None)
        return

def read_db(db_name='./ldc_all.db', table='data', start=None, end=None, duration=60):
    # read database
    db_reader = lite.connect('./ldc_all.db', isolation_level=None)
    db_reader.execute('pragma journal_mode=wal;')  # enable non-blocking for simultaneous reading

    try:
        cur = db_reader.cursor()
        if start==None or end==None:
            with db_reader:
                # Get the last timestamp recorded
                sql_q = 'SELECT unixtime FROM ' + str(table) + ' ORDER BY unixtime DESC LIMIT 1'
                cur.execute(sql_q) 
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
            
        return df_data

    except Exception as e:
        print("Error in get_data:", e)
        return pd.DataFrame([])


def get_start_date(db_name='./ldc_all.db', table='data'):
    # read database
    db_reader = lite.connect(db_name, isolation_level=None)
    db_reader.execute('pragma journal_mode=wal;')  # enable non-blocking for simultaneous reading

    try:
        cur = db_reader.cursor()
        with db_reader:
            # Get the last timestamp recorded
            sql_q = 'SELECT unixtime FROM ' + str(table) + ' ORDER BY unixtime ASC LIMIT 1'
            cur.execute(sql_q) 
            start = np.array(cur.fetchall()).flatten()[0]
            
        return float(start)

    except Exception as e:
        print("Error in get_start_date:", e)
        return time.time()

start_date_db = get_start_date(db_name='./ldc_all.db', table='data')



### ancillary functions ###
# def get_dates(db_name='./ldc.db', report=False):
#     """ Fetch data from the local database"""
#     counter = 0
#     data = []
#     while True and counter < 10:
#         try:
#             con = lite.connect(db_name, isolation_level=None)
#             con.execute('pragma journal_mode=wal;')
#             cur = con.cursor()
       
#             # get the last set of records for a specified duration
#             with con:
#                 sql_cmd = "SELECT DISTINCT localtime FROM data ORDER BY unixtime ASC"
#                 cur.execute(sql_cmd) 
#                 data = np.array(cur.fetchall())
            
#             break
#         except Exception as e:
#             print("Error in get_dates:", e)
#             counter += 1

#     if report: 
#         print(data)
        
#     return data


# def get_data(db_name='./ldc.db', start=None, end=None, duration=60*60, report=False):
#     """ Fetch data from the local database"""
#     counter = 0
#     data = []
#     df_data = pd.DataFrame(data, columns=['unixtime', 'localtime', 'house', 'id', 'type', 'state', 'parameter', 'value'])
#     while True and len(data) < 1:
#         try:
#             con = lite.connect(db_name)
#             con.execute('pragma journal_mode=wal;')
#             cur = con.cursor()
#             if start==None or end==None:
#                 with con:
                    
#                     # Get the last timestamp recorded
#                     cur.execute('SELECT unixtime FROM data ORDER BY unixtime DESC LIMIT 1') 
#                     end = np.array(cur.fetchall()).flatten()[0]
#                     start = end - duration
                    
#             else:
#                 pass
    
#             # get the last set of records for a specified duration
#             with con:
#                 sql_cmd = "SELECT unixtime, localtime, house, id, type, state, parameter, value FROM data WHERE unixtime BETWEEN " + str(start) + " AND " + str(end) + " ORDER BY unixtime ASC"
#                 cur.execute(sql_cmd) 
#                 data = np.array(cur.fetchall())
#                 df_data = pd.DataFrame(data, columns=['unixtime', 'localtime', 'house', 'id', 'type', 'state', 'parameter', 'value'])   

#             break
#         except Exception as e:
#             print("Error in get_data:", e)
#             print(data)
#             counter += 1

#     if report: 
#         print(df_data['parameter'].tail(50))
        
#     return df_data


def get_data(dict_msg={"algorithm":"A1", "loading":10, "frequency":810, "timescale":1, "unixstart":0, "unixend":0}, 
    db_name='./ldc_all.db', mcast_ip="224.0.2.3", mcast_port=16003, report=False):
    global ser, latest_demand, cmd_loading, cmd_algorithm, ldc_signal, previous_limit
    # define timeout
    if dict_msg["unixstart"]==0:
        tm = 0.1
    else:
        tm = 10
    # get data from database
    try:
        dict_agg = MULTICAST.send(dict_msg, ip=mcast_ip, port=mcast_port, timeout=tm)
        latest_demand = float(dict_agg[0]['agg_demand'])
        df_data = pd.DataFrame.from_dict(dict_agg, orient='index')
        df_data['frequency'] = [ldc_signal]
    except Exception as e:
        print("Error get_data, dict_agg is empty:", e)
        # read from power meter
        try:
            latest_reading = None
            while latest_reading==None:
                latest_reading = read_rs232()
            latest_demand = latest_reading
            
        except Exception as e:
            print("Error reading power meter:", e)

        

        ### aggregation parameters
        unixtime = time.time()
        df_data = pd.DataFrame([], columns=['unixtime', 'agg_demand', 'agg_limit', 'algorithm', 'frequency'])
        df_data['unixtime'] = [unixtime]
        df_data['agg_demand'] = [latest_demand]
        df_data['agg_limit'] = [cmd_loading]
        df_data['algorithm'] = [cmd_algorithm]
        df_data['frequency'] = [ldc_signal]


    if report: print(df_data)
    return df_data


def send_command(dict_cmd, ip='localhost', port=10000):
    try:
        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        server_address = (ip, port)
        sock.connect(server_address)
        
        message_toSend = str(dict_cmd).encode()
        # send message
        sock.sendall(message_toSend)
        
        # receive response
        data = sock.recv(2**16)
        received_msg = data.decode("utf-8")
        dict_msg = ast.literal_eval(received_msg)
        # print('received {!r}'.format(dict_msg))
              
    except Exception as e:
        dict_msg = {}

    finally:
        sock.close()

    return dict_msg


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
            print("Error in get_local_ip: ", e)
            local_ip = '0.0.0.0'
            break
    return local_ip





def create_shapePath(points):
        # declare path of the shape using the points
        path = 'M '
        for p in points:
            path = path+ '{} {} L '.format(str(p[0]), str(p[1]))
            
        path = path + ' Z' 
        return path

def create_baseChart(values=[40, 10, 10, 10, 10, 10, 10], 
    labels=[" ", "0", "2kW", "4kW", "6kW", "8kW", "10kW"],
    colors=['#18252E', '#18252E', '#18252E', '#18252E', '#18252E', '#18252E', '#18252E'],):
    # create base chart to display guage tick lables
    base_chart = {
        "values": values,
        "labels": labels,
        "domain": {"x": [0.1, .9]},
        "marker": {
            "colors": colors,
            "line": {"width": 1}
        },
        "name": "Gauge",
        "hole": .4,
        "type": "pie",
        "direction": "clockwise",
        "rotation": 108,
        "showlegend": False,
        "hoverinfo": "none",
        "textinfo": "label",
        "textposition": "outside"
    }
    return base_chart


def save_json(json_data, filename):
    # save json_data in filename
    with open(filename, 'w') as outfile:  
        json.dump(json_data, outfile)

    return filename

def read_json(filename):
    # read file as json
    with open(filename) as json_file:  
        data = json.load(json_file)
    
    return data


### GLOBAL VARIABLES ###
local_ip = get_local_ip()
capacity = 30000  # [W]
dict_cmd = {}

try:
    dict_cmd = read_json('dict_cmd.txt')
    cmd_loading = float(dict_cmd['agg_limit'])
    cmd_algorithm = dict_cmd['algorithm']
    ldc_signal = float(dict_cmd['frequency'])
except Exception as e:
    print("Error initial command:", e)
    cmd_loading = 30000
    cmd_algorithm = "A0"
    ldc_signal = 860
    latest_demand = 0

previous_limit = cmd_loading  
timescale = 1
sum_actual = 0
sum_proposed = 0
df_data_cols = ['unixtime', 'agg_demand', 'agg_limit', 'algorithm', 'frequency']
df_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":0, "unixend":0})


# returns logo div
def get_logo():
    image = "./UOA.png"
    encoded_image = base64.b64encode(open(image, "rb").read())
    logo = html.Div(
        html.Img(
            src="data:image/png;base64,{}".format(encoded_image.decode()), height="57"
        ),
        style={"marginTop": "0", "float":"left", "backgroundColor": "#18252E"},
        # className="sept columns",
    )
    return logo



tabs_styles = {
    'height': '40px'
}
tab_style = {
    'borderTop': '1px solid #18252E',
    'borderBottom': '1px solid #18252E',
    'backgroundColor': '#18252E',
    'color':'white',
    'padding': '10px',
    'fontWeight': 'bold',
    'text-align':'center',
    'float':'center',
}

tab_selected_style = {
    'borderTop': '1px solid #18252E',
    'borderBottom': '1px solid #18252E',
    'backgroundColor': '#d6d6d6',
    'color': 'black',
    'padding': '10px',
    'text-align':'center',
    'float':'center',
}




# @app.callback(
#     dash.dependencies.Output('input-cmd-loading', 'value'),
#     [dash.dependencies.Input('button-power-up', 'n_clicks_timestamp'),
#     dash.dependencies.Input('button-power-down', 'n_clicks_timestamp'),
#     # dash.dependencies.Input('input-cmd-loading', 'n_submit'),
#     dash.dependencies.Input('cmd-algorithm','value')],
#     [], events=[],
#     )
# def update_output(b1_click, b2_click, algorithm):
#     # increase power limit
#     global dict_cmd, cmd_loading, cmd_algorithm, dict_cmd, ldc_signal, previous_limit
#     cmd_algorithm = algorithm
#     now = time.time() * 1000
#     if cmd_algorithm=='A0':
#         cmd_loading = 30000
#     elif b1_click > b2_click:
#         cmd_loading = cmd_loading + 100
#     elif b1_click < b2_click:
#         cmd_loading = cmd_loading - 100
#     else:
#         cmd_loading = previous_limit

#     ### change target power setpoint at ldc injector
#     if (cmd_loading!=previous_limit) and (((now - b1_click) > 0.5) or ((now - b2_click) > 0.5)):
#         print("Setpoint changed to ", str(cmd_loading), " kVA")
#         msg = 's' + str(cmd_loading)
#         write_rs232(msg)
#         previous_limit = cmd_loading
    
#         dict_cmd.update({"agg_limit":str(cmd_loading), "algorithm":str(cmd_algorithm), "frequency":str(ldc_signal)})
#         save_json(dict_cmd, 'dict_cmd.txt')
    
#     else:
#         pass

#     return np.round(float(cmd_loading)/1000, 3)




@app.callback(
    dash.dependencies.Output('cmd-loading', 'children'),
    [dash.dependencies.Input('input-cmd-loading', 'n_submit'),
    dash.dependencies.Input('cmd-algorithm','value'),],
    [dash.dependencies.State('input-cmd-loading', 'value')])
def update_loading(n_submit, algorithm, loading):
    global dict_cmd, cmd_loading, cmd_algorithm, dict_cmd, ldc_signal, display_limit
    cmd_algorithm = algorithm
    if cmd_algorithm=='A0':
        cmd_loading = 30000
        print("Setpoint changed to ", str(cmd_loading), " kVA")
        ldc_signal = 850
        msg = 'o ' + str(ldc_signal)
        write_rs232(msg)
    else:
        cmd_loading = loading * 1000
        ### change target power setpoint at ldc injector
        if n_submit>0: #(cmd_loading!=previous_limit):
            print("Setpoint changed to ", str(cmd_loading), " kVA")
            msg = 's' + str(cmd_loading)
            write_rs232(msg)
            previous_limit = cmd_loading        
        else:
            pass

    dict_cmd.update({"agg_limit":str(cmd_loading), "algorithm":str(cmd_algorithm), "frequency":str(ldc_signal)})
    save_json(dict_cmd, 'dict_cmd.txt')

    display_limit = True

    return np.round(float(cmd_loading)/1000, 3)


@app.callback(
    dash.dependencies.Output('output-gain', 'children'),
    [dash.dependencies.Input('input-cmd-gain', 'n_submit'),],
    [dash.dependencies.State('input-cmd-gain', 'value')])
def update_gain(n_submit, gain):
    ### change target power setpoint at ldc injector
    try:
        gain = int(gain)
        msg = 'k ' + str(gain)
        write_rs232(msg)
        print("Gain changed to ", str(gain))
    except Exception as e:
        print("Error changing gain:",e)

    display_limit = True
    
    return gain


@app.callback(
    dash.dependencies.Output('output-freq', 'children'),
    [dash.dependencies.Input('input-cmd-freq', 'n_submit'),],
    [dash.dependencies.State('input-cmd-freq', 'value')])
def update_frequency(n_submit, frequency):
    ### change target power setpoint at ldc injector
    global ldc_signal, display_limit
    try:
        if n_submit==None:
            pass
        elif n_submit > 0:
            frequency = float(frequency)
            ldc_signal = frequency
            msg = 'o ' + str(frequency)
            write_rs232(msg)
            print("Frequency changed to ", str(frequency))
            display_limit = False
        else:
            pass
    except Exception as e:
        print("Error changing frequency:",e)
    
    return frequency


@app.callback(
    dash.dependencies.Output('input-cmd-loading', 'value'),
    [dash.dependencies.Input('btn-cmd-freq', 'n_clicks'),],
    )
def emergency(b1_nclick):
    ### change target power setpoint at ldc injector
    global ldc_signal, display_limit, cmd_loading, cmd_algorithm
    
    if cmd_algorithm=='A0':
        pass
    else:
        try:
            if b1_nclick > 0:
                frequency = 750
                ldc_signal = frequency
                msg = 'o ' + str(frequency)
                write_rs232(msg)
                print("Load shed: frequency forced to ", str(frequency))
                display_limit = True
                cmd_loading = 1
            else:
                pass
        except Exception as e:
            print("Error changing frequency:",e)

    # ### change target power setpoint at ldc injector
    # try:
    #     cmd_loading = 1000
    #     print("Setpoint changed to ", str(cmd_loading), " kVA")
    #     ldc_signal = get_frequency(cmd_algorithm, cmd_loading)
    #     msg = 's' + str(cmd_loading)
    #     # msg = 'o ' + str(ldc_signal)
    #     write_rs232(msg)
    #     previous_limit = cmd_loading        
    # except Exception as e:
    #     print("Error changing setpoint.", e)

    # dict_cmd.update({"agg_limit":str(cmd_loading), "algorithm":str(cmd_algorithm), "frequency":str(ldc_signal)})
    # save_json(dict_cmd, 'dict_cmd.txt')

    return cmd_loading/1000

# @app.callback(
#     dash.dependencies.Output('output-freq2', 'children'),
#     [dash.dependencies.Input('btn-cmd-freq', 'n_clicks'),],
#     )
# def emergency2(b1_nclick):
#     ### change target power setpoint at ldc injector
#     global ldc_signal, cmd_loading, display_limit
#     frequency = 750
#     ldc_signal = frequency
#     try:
#         msg = 'o ' + str(frequency)
#         write_rs232(msg)
#         print("Load shed: frequency forced to ", str(frequency))
#     except Exception as e:
#         print("Error changing frequency:",e)

    # ### change target power setpoint at ldc injector
    # try:
    #     cmd_loading = 1
    #     print("Setpoint changed to ", str(cmd_loading), " kVA")
    #     ldc_signal = get_frequency(cmd_algorithm, cmd_loading)
    #     msg = 's' + str(cmd_loading)
    #     # msg = 'o ' + str(ldc_signal)
    #     write_rs232(msg)
    #     previous_limit = cmd_loading        
    # except Exception as e:
    #     print("Error changing setpoint.", e)

    # dict_cmd.update({"agg_limit":str(cmd_loading), "algorithm":str(cmd_algorithm), "frequency":str(ldc_signal)})
    # save_json(dict_cmd, 'dict_cmd.txt')

    
    # return 1



@app.callback(
    dash.dependencies.Output('cmd-signal', 'children'),
    [dash.dependencies.Input('input-cmd-loading', 'n_submit')],
    [dash.dependencies.State('input-cmd-loading', 'value')],
    events=[dash.dependencies.Event('data-update','interval')])
def update_signal(n_submit, value):
    # change the frequency signal 
    global cmd_algorithm, cmd_loading, ldc_signal
    ldc_signal = get_frequency(cmd_algorithm, cmd_loading)
    return np.round(ldc_signal, 2)

    

@app.callback(
        dash.dependencies.Output('command','children'),
        [dash.dependencies.Input('cmd-algorithm','value'),
        dash.dependencies.Input('cmd-loading','children'),])
def update_command(algorithm, loading):
    # change the command algorithm
    global cmd_loading, cmd_algorithm, dict_cmd, ldc_signal, previous_limit
    cmd_algorithm = algorithm

    if cmd_algorithm=='A0':
        frequency = 850
        ldc_signal = frequency
        msg = 'o ' + str(frequency)
        write_rs232(msg)
        print("No LDC: frequency forced to ", str(frequency))
        display_limit = True
    else:
        cmd_loading = float(loading) * 1000
        ### change target power setpoint at ldc injector
        print("Setpoint changed to ", str(cmd_loading), " kVA")
        msg = 's' + str(cmd_loading)
        write_rs232(msg)
        previous_limit = cmd_loading        
    
    display_limit = True
    return algorithm


def get_frequency(cmd_algorithm, cmd_loading):
    global capacity, ldc_signal, latest_demand

    target_loading = float(cmd_loading)
    percent_loading = float(target_loading) / capacity

    
    ldc_upper = 850
    ldc_lower = 750
    ldc_center = 810 
    ldc_bw = ldc_upper - ldc_lower  # bandwidth
    w_past = 0.1  # weight given to the past signal, acting as a damper to change in ldc_signal

    try:
        if cmd_algorithm=='A0':
            ldc_signal=ldc_upper

        # elif cmd_algorithm in ['A1', 'A2']:
        else:
            offset = ((target_loading - latest_demand)/latest_demand) * ((850-750))
            ldc_signal += offset
            ldc_signal = np.min([ldc_signal, 850])
            ldc_signal = np.max([ldc_signal, 750]) 

        # elif cmd_algorithm=='A2':
            # offset = np.nan_to_num(1 - (latest_demand / target_loading))
            # ldc_signal_new = float(ldc_center + ((ldc_bw) * offset))
            # ldc_signal = (w_past * ldc_signal) + ((1-w_past) * ldc_signal_new)
            # ldc_signal = np.min([ldc_signal, 860])
            # ldc_signal = np.max([ldc_signal, 760])

        # elif cmd_algorithm=='A3':
        #     # ldc_signal = float(760 + (ldc_bw * percent_loading))
        #     # ldc_signal = np.min([ldc_signal, 860])
        #     # ldc_signal = np.max([ldc_signal, 760])
            
        # else: # default is 'A1'
        #     offset = ((target_loading - latest_demand)/capacity) * ((860-760))
        #     ldc_signal += offset
        #     ldc_signal = np.min([ldc_signal, 860])
        #     ldc_signal = np.max([ldc_signal, 760]) 

        

        return np.round(ldc_signal, 2)
    except Exception as e:
        print("Error in get_frequency:", e, cmd_algorithm, cmd_loading, ldc_signal)
        return 810




@app.callback(
    dash.dependencies.Output('data','children'),
    [dash.dependencies.Input('cmd-algorithm','value'),
    dash.dependencies.Input('cmd-loading','children'),],
    [dash.dependencies.State('data', 'children')],
    events=[dash.dependencies.Event('data-update','interval')])
def update_data(algorithm, loading, json_data):
    # update the graph
    global cmd_algorithm, cmd_loading, ldc_signal, latest_demand
    ldc_signal = get_frequency(cmd_algorithm, cmd_loading)

    df_data = pd.DataFrame([], columns=df_data_cols)
    df_data_old = pd.DataFrame([], columns=df_data_cols)
    df_data_new = pd.DataFrame([], columns=df_data_cols)
    
    try:  # get old data and append new data
        try:
            df_data_old = pd.read_json(json_data, orient='split')
        except Exception as e:
            print("Error update_data old data:", e)
            df_data_old = pd.DataFrame([], columns=df_data_cols)         
        
        try:
            while len(df_data_new.index) <= 0:
                df_data_new = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":0, "unixend":0})
        except Exception as e:
            print("Error update_data new data:", e)
            df_data_new = pd.DataFrame([], columns=df_data_cols)             

        print("new:",df_data_new)

        try:
            df_data = pd.concat([df_data_old,df_data_new], sort=False).reset_index(drop=True)
            df_data = df_data[df_data['unixtime'] >= time.time()-(60*10)]
        except Exception as e:
            print("Error concat:", e)

        

    except Exception as e:
        print("Error update_data:", e)
        try:
            while len(df_data.index)<=0:
                df_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":0, "unixend":0})
        except Exception as e:
            print("Error update_data exception:", e)
            df_data = pd.DataFrame([], columns=df_data_cols)
    
    
    return df_data.to_json(orient='split')







@app.callback(
    dash.dependencies.Output('graphs','children'),
    [dash.dependencies.Input('data', 'children')],
    )
def update_graph(json_data):  
    global df_data, cmd_algorithm, display_limit
    graphs = []
    
    try:
        df_data_graph = pd.read_json(json_data, orient='split')        
    except Exception as e:
        try:
            df_data_graph = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":0, "unixend":0})
           
        except Exception as e:
            print("Error update_data exception:", e)
            df_data_graph = pd.DataFrame([], columns=df_data_cols)
    

    # convert timezone from UTC to local timezone before graph
    df_data_graph.index = [pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert(timezone).isoformat() for a in df_data_graph['unixtime']]
               
    # plot total demand
    
    trace_actual = go.Scattergl(
                x = df_data_graph.index,
                y = df_data_graph['agg_demand'],
                name = 'Demand',
                line= {'color':'rgb(0,255,0)'},
                # opacity = 0.8,
                fill = "tozeroy",
                )

    trace_limit = go.Scattergl(
                x = df_data_graph.index, 
                y = df_data_graph['agg_limit'],
                name = 'Limit',
                line= {'color':'rgb(255,0,0)'},
                # opacity = 0.8,
                # fill = "tozeroy",
                )

    if display_limit:
        trace_agg = [trace_actual, trace_limit]
    else:
        trace_agg = [trace_actual]

    graphs.append(html.Div(dcc.Graph(
                id='total-demand',
                animate=False,
                figure={'data': trace_agg,
                        'layout' : go.Layout(xaxis= dict(autorange=True),
                                            yaxis=dict(autorange=True, title='Power (W)'),
                                            margin={'l':50,'r':1,'t':45,'b':50},
                                            title='Power Reading at Transformer',
                                            legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.1),
                                            autosize=True,
                                            height=700,
                                            font=dict(color='#CCCCCC'),
                                            titlefont=dict(color='#CCCCCC', size=14),
                                            hovermode="closest",
                                            plot_bgcolor="#020202", #"#191A1A",
                                            paper_bgcolor="#18252E",
                                            )}
                ), className='row'))


    
    return graphs






def serve_layout():
    return html.Div(
            [
                # header
                html.Div([
                    dcc.Location(id='url', refresh=False),
                    get_logo(),
                    html.H2("Localized Demand Control", style={'marginTop':'5', 'marginLeft':'7', 'display':'inline-block', 'text-align':'center','float':'center', 'color':'white', "backgroundColor": "#18252E"}),
                    ],
                ),
                
                # tabs
                html.Div([
                    dcc.Tabs( id="tabs", children=[
                            dcc.Tab(
                                label="Status", 
                                value="status_tab", 
                                style=tab_style,
                                selected_style=tab_selected_style,
                                className='custom-tab',
                                ),
                           dcc.Tab(
                                label="History", 
                                value="history_tab",
                                style=tab_style,
                                selected_style=tab_selected_style,
                                className='custom-tab',
                                ),
                            
                        ],
                        value="status_tab",
                        className="col s12 m3 l2",
                        style=tabs_styles,
                        
                    )
                            
                    ], 
                    className='col s12 m3 l2',
                    style={'display': 'inline-block', 'padding':'5', 'float':'left'}
                ),
                        
         

                # # Tab content
                html.Div(id="tab_content", className="row", style={"margin": "1%"}),
           ],
            className="row",
            style={"margin": "0%", "backgroundColor": "#18252E"},
        )




def render_status():
    # render content for status tab
    global cmd_algorithm, cmd_loading, ldc_signal
    return html.Div(children=[
                html.Div([
                    html.H1("Microgrid Status", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
                    ], 
                    className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
                ),
                
                html.Div([
                    
                     html.Div([
                        html.Label('Power limit:', className='column',
                            style={'color':'white', 'display':'inline-block', 'margin':'3'}),
                        
                        html.Div([
                                html.Div(id='cmd-loading', children=np.round(float(cmd_loading)/1000, 3), className='row', 
                                    style={'font-size':'xx-large', 'color':'white', 'text-align':'right', 'display':'inline-block', 'padding':'9', "position": "relative",}),
                                html.Div(id='cmd-loading-unit', children='kW', className='row',
                                    style={'font-size':'xx-large', 'color':'white', 'text-align':'left', 'display':'inline-block', 'padding':'9',"position": "relative",}),
                            ], className='column', style={'display':'inline-block'}
                        ),
                        
                        # html.Div([
                        #     html.Button('+100W', id='button-power-up', n_clicks_timestamp=0, className='row', style={'padding':'3px 3px', 'font-size':'small', 'width':'60px', 'hover':{'background-color':'#4CAF50', 'color': 'white'}}),
                        #     html.Button('-100W', id='button-power-down', n_clicks_timestamp=0, className='row', style={'padding':'3px 3px', 'font-size':'small', 'width':'60px', 'hover':{'background-color':'#4CAF50', 'color': 'white'}}),
                        #     ], className='column'),

                        ], className='column', 
                    ),


                    html.Div([
                            html.Label('Set limit:', className='column',
                                style={'text-align':'left', 'color':'white', 'display':'inline-block', 'margin':'0', "float": "left",}),
                            html.Div([
                                    dcc.Input(id='input-cmd-loading', 
                                        value= np.round(float(cmd_loading)/1000, 3), # converted to kW
                                        disabled=False, 
                                        type='number', 
                                        min=0, 
                                        max= 30, # converted to kW
                                        step=0.10, 
                                        inputmode='numeric',
                                        className='row',
                                        style={'font-size':'large', 'text-align':'center', 'display':'inline-block', 'width':'100px', 'padding':'0', "position": "relative",}),

                                    html.Div(id='cmd-loading-unit', children='kW', className='row',
                                            style={'font-size':'large', 'color':'white', 'text-align':'left', 'display':'inline-block', 'padding':'3',"position": "relative",}),
                                ], className='column'
                            ),
                            
                        ], 
                        className='column', style={'text-align':'left', 'display':'inline-block', 'padding':'0', "float": "left",},
                    ),

                    html.Div([
                        html.Label(' ', className='column',
                            style={'color':'white', 'display':'inline-block', 'padding':'10'}),
                        ], 
                        className='column',
                    ),

                    html.Div([
                        html.Label('LDC Signal:', className='column',
                            style={'color':'white', 'display':'inline-block', 'margin':'3'}),
                        html.Div(id='cmd-signal', children=str(ldc_signal-760), className='row',
                            style={'font-size':'large', 'color':'white', 'text-align':'right', 'display':'inline-block', 'padding':'9', "position": "relative",}),
                        
                        ], 
                        className='column', style={'display':'none'},
                    ),



                    html.Div([
                        html.Label('Algorithm:', className='column',
                            style={'color':'white', 'display':'inline-block', "position": "relative",}),
                        dcc.RadioItems(
                            id='cmd-algorithm',
                            options=[
                                        {"label": "No LDC", "value": "A0"},
                                        {"label": "With LDC", "value": "A1"},
                                        # {"label": "Advance LDC", "value": "A2"},
                                        # {"label": "Smart LDC", "value": "A3"},
                                    ],
                            value=cmd_algorithm,
                            className='column',
                            style={'color':'white', 'margin':'3', "position": "relative",}
                        ),
                      
                        ], 
                        className='row',
                        style={'display':'inline-block', "position": "relative",}
                    ),

                    html.Div([
                            html.Label('Set gain:', className='column',
                                style={'text-align':'left', 'color':'white', 'display':'inline-block', 'margin':'0', "float": "left",}),
                            html.Div([
                                    dcc.Input(id='input-cmd-gain', 
                                        value=30,
                                        disabled=False, 
                                        type='number', 
                                        min=0, 
                                        max= 5000, 
                                        step=1, 
                                        inputmode='numeric',
                                        className='row',
                                        style={'font-size':'large', 'text-align':'center', 'display':'inline-block', 'width':'100px', 'padding':'0', "position": "relative",}),

                                    
                                ], className='column'
                            ),
                            
                        ], 
                        className='column', style={'text-align':'left', 'display':'inline-block', 'padding':'0', "float": "left",},
                    ),

                    html.Div([
                            html.Label('Set signal:', className='column',
                                style={'text-align':'left', 'color':'white', 'display':'inline-block', 'margin':'0', "float": "left",}),
                            html.Div([
                                    dcc.Input(id='input-cmd-freq', 
                                        # value=ldc_signal,
                                        disabled=False, 
                                        type='number', 
                                        min=0, 
                                        max= 5000, 
                                        step=1, 
                                        inputmode='numeric',
                                        className='row',
                                        style={'font-size':'large', 'text-align':'center', 'display':'inline-block', 'width':'100px', 'padding':'0', "position": "relative",}),

                                    
                                ], className='column'
                            ),
                            
                        ], 
                        className='column', style={'text-align':'left', 'display':'inline-block', 'padding':'0', "float": "left",},
                    ),

                    html.Div([
                        html.Label('Emergency load shedding:', className='column',
                                style={'text-align':'left', 'color':'white', 'display':'inline-block', 'margin':'0', "float": "left",}),
                            
                        html.Div([
                            html.Button('Shed!', id='btn-cmd-freq', n_clicks_timestamp=0, className='row', style={'text-align':'center', 'font-size':'large', 'border-radius':'30px'}), #, 'hover':{'background-color':'rgb(255,255,255)', 'color': 'rgb(255,0,0)'}}),
                        #     html.Button('-100W', id='button-power-down', n_clicks_timestamp=0, className='row', style={'padding':'3px 3px', 'font-size':'small', 'width':'60px', 'hover':{'background-color':'#4CAF50', 'color': 'white'}}),
                            ], className='column'),

                        ], className='column', 
                    ),



                ], 
                className='row s12 m2 l2',
                # style={'padding':'3', 'float':'left'}
                style = {
                       "position": "relative",
                        "float": "left",
                        # "border": "1px solid",
                        # "borderColor": "rgba(68,149,209,.9)",
                        "overflow": "hidden",
                        "marginBottom": "2px",
                        "width":"15%"
                    },
                ),
                

                html.Div([
                    html.Div(children=html.Div(id='graphs'), className='row',),
                    # dcc.Interval(id='graph-update', interval=1.5*1000),
                    ], 
                    className='row s12 m8 l8',
                    # style={'padding':'3', 'float':'left'},
                    style = {
                       "position": "relative",
                        "float": "left",
                        # "border": "1px solid",
                        # "borderColor": "rgba(68,149,209,.9)",
                        # "overflow": "hidden",
                        "marginBottom": "2px",
                        "width": "80%",
                    },
                ),


                # hidden div: holder of data
                html.Div([
                    html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0', 'display':'none'}),
                    dcc.Interval(id='data-update', interval=1*1000),
                    ], 
                    className='row', style={'display':'none',},
                ),

                # hidden update for sending ldc command signal
                html.Div(children=html.Div(id='command'), style={'display': 'none'}),
                html.Div(children=html.Div(id='output-gain'), style={'display': 'none'}),
                html.Div(children=html.Div(id='output-freq'), style={'display': 'none'}),
                html.Div(children=html.Div(id='output-freq2'), style={'display': 'none'}),

            
            ],
            className='row',
            style={'display':'inline-block', "backgroundColor": "#18252E", "width":"100%"} 
            
        )


'''
NOTE: properties for dcc.Input
n_submit, The number of times enter was pressed when the component had focus.
n_submit_timestamp The last timestamp enter was pressed.
n_blur, The number of times the component lost focus.
n_blur_timestamp, The last time the component lost focus.
'''




# # automatically change dropdown options for device_id based on selected device_type
# @app.callback(
#     dash.dependencies.Output('device-id', 'options'),
#     [dash.dependencies.Input('device-type', 'value')])
# def set_device_options(selected_device_type):
#     return [{'label': i, 'value': i} for i in np.unique(df_dev_class[df_dev_class['device_type']==selected_device_type]['device_id'])]

# @app.callback(
#     dash.dependencies.Output('device-id', 'value'),
#     [dash.dependencies.Input('device-id', 'options')])
# def set_device_value(available_options):
#     return available_options[0]['value']



def recall_data(start, end, report=False):
    """ Fetch data from the local database"""
    counter = 0
    data = []
    df_data = pd.DataFrame(data, columns=['unixtime', 'id', 'parameter', 'value'])
    while len(data) < 1:
        try:
            con = lite.connect('./ldc_all.db')
            con.execute('pragma journal_mode=wal;')
            cur = con.cursor()
            
            # get the last set of records for a specified duration
            with con:
                sql_cmd = "SELECT unixtime, id, parameter, value FROM data WHERE unixtime BETWEEN " + str(start) + " AND " + str(end) + " ORDER BY unixtime ASC"
                cur.execute(sql_cmd) 
                data = np.array(cur.fetchall())
                df_data = pd.DataFrame(data, columns=['unixtime', 'id', 'parameter', 'value'])   

            break
        except Exception as e:
            print("Error in recall_data:", e)
            
    if report: print(df_data['parameter'].tail(50))
        
    return df_data


@app.callback(
    dash.dependencies.Output('history-graphs','children'),
    [dash.dependencies.Input('date-picker-range', 'start_date'),
    dash.dependencies.Input('date-picker-range', 'end_date')],
    )
def history_graph(start_date, end_date):  
    global df_data, cmd_algorithm
    ts_date1 = datetime.datetime.strptime(start_date, '%Y-%m-%d').timestamp()
    today = datetime.datetime.now()
    if float(today.day) == float(end_date.split('-')[2]):
        ts_date2 = today.timestamp()
    else:
        ts_date2 = datetime.datetime.strptime(end_date, '%Y-%m-%d').timestamp()
    
    graphs = []
    
    try:
        df_history = recall_data(ts_date1, ts_date2)
       
    except Exception as e:
        print("Error update_data exception:", e)
        df_history = pd.DataFrame([], columns=['unixtime', 'id', 'parameter', 'value'])


    # convert timezone from UTC to local timezone before graph
    df_data_graph = pd.DataFrame([], columns=['agg_demand', 'agg_limit'])
    df_data_graph['agg_demand'] = df_history[df_history['parameter']=='agg_demand']['value'].values
    df_data_graph['agg_limit'] = df_history[df_history['parameter']=='agg_limit']['value'].values
    df_data_graph.index = df_history[df_history['parameter']=='agg_demand']['unixtime'].values
    # df_data_graph.index = [pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert(timezone).isoformat() for a in df_data_graph.index]

    # plot total demand
    
    # trace_actual = go.Scattergl(
    #             x = df_data_graph.index,
    #             y = df_data_graph['agg_demand'],
    #             name = 'Demand',
    #             line= {'color':'rgb(0,255,0)'},
    #             # opacity = 0.8,
    #             fill = "tozeroy",
    #             )

    # trace_limit = go.Scattergl(
    #             x = df_data_graph.index, 
    #             y = df_data_graph['agg_limit'],
    #             name = 'Limit',
    #             line= {'color':'rgb(255,0,0)'},
    #             # opacity = 0.8,
    #             # fill = "tozeroy",
    #             )

    # # if cmd_algorithm=='A0':
    # #     trace_agg = [trace_actual]
    # # else:
    # trace_agg = [trace_actual, trace_limit]

    # graphs.append(html.Div(dcc.Graph(
    #             id='total-demand',
    #             animate=False,
    #             figure={'data': trace_agg,
    #                     'layout' : go.Layout(xaxis= dict(autorange=True),
    #                                         yaxis=dict(autorange=True, title='Power (W)'),
    #                                         margin={'l':50,'r':1,'t':45,'b':50},
    #                                         title='Power Reading at Transformer',
    #                                         legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.1),
    #                                         autosize=True,
    #                                         height=700,
    #                                         font=dict(color='#CCCCCC'),
    #                                         titlefont=dict(color='#CCCCCC', size=14),
    #                                         hovermode="closest",
    #                                         plot_bgcolor="#020202", #"#191A1A",
    #                                         paper_bgcolor="#18252E",
    #                                         )}
    #             ), className='row'))


    
    return graphs



today = datetime.datetime.now()
yesterday = datetime.datetime.now() - datetime.timedelta(seconds=3600*24)
def render_history():
    # render the contents for history tab
    return html.Div(children=[
                html.Div([
                    html.H1("Microgrid History", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
                    ], 
                    className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
                ),
                
                html.Div([
                    html.Div([
                            html.Label('Data Range:', style={'color':'white', 'display':'inline-block', 'text-align':'center'}),
                            dcc.DatePickerRange(
                                id='date-picker-range',
                                display_format='YYYY-MM-DD',
                                min_date_allowed=start_date_db,
                                max_date_allowed=datetime.datetime.now(),
                                initial_visible_month=datetime.datetime.now(),
                                start_date=datetime.datetime(yesterday.year, yesterday.month, yesterday.day),
                                end_date=datetime.datetime(today.year, today.month, today.day),
                            ),
                        ], className='row', style={'color':'white', 'padding':'3', 'display':'inline-block'},
                    ),

                    
                    ],
                    className='row s12 m8 l8',
                    # style={'padding':'3', 'float':'left'},
                    style = {
                       "position": "relative",
                        "float": "left",
                        # "border": "1px solid",
                        # "borderColor": "rgba(68,149,209,.9)",
                        # "overflow": "hidden",
                        "marginBottom": "2px",
                        "width": "100%",
                    },
                ),
                

                html.Div([
                    html.Div(children=html.Div(id='history-graphs'), className='row',),
                    # dcc.Interval(id='graph-update', interval=1.5*1000),
                    ], 
                    className='row s12 m8 l8',
                    # style={'padding':'3', 'float':'left'},
                    style = {
                       "position": "relative",
                        "float": "left",
                        # "border": "1px solid",
                        # "borderColor": "rgba(68,149,209,.9)",
                        # "overflow": "hidden",
                        "marginBottom": "2px",
                        "width": "80%",
                    },
                ),


                
            
            ],
            className='row',
            style={'display':'inline-block', "backgroundColor": "#18252E", "width":"100%"} 
            
        )



app.layout = serve_layout()




@app.callback(Output("tab_content", "children"), [Input("tabs", "value")])
def render_content(tab):
    if tab == "status_tab":
        return render_status()
    elif tab == "history_tab":
        return render_history()
    else:
        return render_status()



css_directory = os.getcwd()


external_css = [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",
    "https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css",
    "https://cdn.rawgit.com/amadoukane96/d930d574267b409a1357ea7367ac1dfc/raw/1108ce95d725c636e8f75e1db6e61365c6e74c8a/web_trader.css",
    "https://use.fontawesome.com/releases/v5.2.0/css/all.css"
]

for css in external_css:
    app.css.append_css({"external_url": css})

if 'DYNO' in os.environ:
    app.scripts.append_script({
        'external_url': 'https://cdn.rawgit.com/chriddyp/ca0d8f02a1659981a0ea7f013a378bbd/raw/e79f3f789517deec58f41251f7dbb6bee72c44ab/plotly_ga.js'
    })



if __name__ == "__main__":
    app.run_server(debug=True, host=local_ip, port=15003)


# to run in gunicorn:
# gunicorn grid_server:server -b :15003
