##./grid_server.py
# -*- coding: utf-8 -*-
import flask
# import plotly.plotly as py
import math
import dash
from dash.dependencies import Output, Input, State
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

import plotly.express as px
# from flask_caching import Cache
# from pandas_datareader.data import DataReader
from collections import deque
import plotly.graph_objs as go
# import dash_auth
import base64

import random
import time, datetime
import pandas as pd
import numpy as np
import sqlite3 as lite
import os, glob
import uuid
import re
# import serial

# multicasting packages
import socket
import struct
import sys
import time
import json
import ast
import socket

import MULTICAST

color_set = px.colors.qualitative.Set1
# color_set = px.colors.qualitative.Plotly
# color_set = px.colors.qualitative.D3  # default for Dash
# color_set = px.colors.qualitative.G10
# color_set = px.colors.qualitative.T10
# color_set = px.colors.qualitative.Alphabet

### other color sets
# Dark24, Light24, Pastel1, Dark2, Set2, Pastel2, Set3,
# Antique, Bold, Pastel, Prism, Safe, Vivid

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
global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt
global ldc_signal, latest_demand, emergency, start_date



# def get_timezone(latitude,longitude,timestamp,report=False):
#     """ Determines the timezone based on 
#     location specified by the latitude and longitude """
#     global timezone

#     url = 'https://maps.googleapis.com/maps/api/timezone/json?location='\
#         + str(latitude) + ',' + str(longitude) + '&timestamp='\
#         + str(timestamp) + '&key=' + 'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'
#     req = Request(url)

#     success = False
#     attempts = 0
#     while not(success) and (attempts<=10):
#         try:
#             response = urlopen(req)
#             respData = response.read()
#             response.close()

#             respData = respData.decode("utf-8")
#             data = json.loads(respData)

#             if data['timeZoneId']:
#                 timezone = data['timeZoneId']  # get timezone
        
#                 if report:
#                     print("latitude: "+ latitude)
#                     print("longitude: "+ longitude)
#                     print ("timezone: "+ timezone)

#                 # adjust timezone setting used for runtime
#                 os.environ['TZ'] = timezone
#                 time.tzset()
#                 success = True
#                 return timezone
#             else:
#                 print("No results... retrying...")
#                 return None
      
#         except HTTPError as e:
#             print('The server couldn\'t fulfill the request.')
#             print('Error code: ', e.code)
#         except URLError as e:
#             print('We failed to reach a server.')
#             print('Reason: ', e.reason)
#         else:
#             print("Unknown Error")  # everything is fine




# # adjust timezone setting used for runtime
# global timezone
# try:
#     timezone = get_timezone(latitude, longitude, timestamp=time.time())
# except:
#     timezone = 'Pacific/Auckland'
# try:
#     os.environ['TZ'] = timezone
#     time.tzset()
#     print("Timezone:", timezone)
# except Exception as e:
#     print("Error setting timezone:", e)




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
                timeout=1)

        ser.flushInput()
        ser.flushOutput()
        s_msg = list(msg)
        for s in s_msg:
            ser.write(s.encode('ascii'))
            time.sleep(0.001)
        ser.write(b'\r')
        time.sleep(0.5)

    except Exception as e:
        print("Error writing to serial:", e)



def get_start_date(db_name='/home/pi/ldc_project/ldc_gridserver/ldc_agg_melted.db'):
    # read database
    db_reader = lite.connect(db_name, isolation_level=None)
    # enable non-blocking for simultaneous reading
    db_reader.execute('pragma journal_mode=wal;')  

    try:
        cur = db_reader.cursor()
        with db_reader:
            # Get the last timestamp recorded
            cur.execute('SELECT min(unixtime) FROM data') 
            start = np.array(cur.fetchall()).flatten()[0]
        return float(start)

    except Exception as e:
        print("Error in get_start_date:", e)
        return time.time()




# def get_data(day, unixstart=None, unixend=None):
#     """ Fetch data from the local database"""
#     df_data = pd.DataFrame([])
#     while len(df_data.index)<=0:
#         try:
#             df_data = pd.read_pickle(f'/home/pi/studies/ardmore/data/T1_{day}.pkl.xz')
#         except Exception as e:
#             # print("Error grid_server.get_data: no saved data.")
#             time.sleep(1)

#     df_data['target_kw'] = df_data['target_watt'] * 1e-3
#     if unixstart!=None:
#         df_data = df_data[(df_data['unixtime']>=unixstart)&(df_data['unixtime']<=unixend)]
#     return df_data


def get_data(day=None, unixstart=None, unixend=None, diagnostics=False):
    """ Fetch data from the local database"""
    while True:
        try:
            if day:
                df_data = pd.read_pickle(f'/home/pi/studies/ardmore/data/T1_{day}.pkl.xz', compression='infer')    
            else:
                if unixstart: 
                    daystart = pd.to_datetime(unixstart, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%Y_%m_%d')
                    date_list = [daystart]
                if unixend:
                    dayend = pd.to_datetime(unixstart, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%Y_%m_%d')
                    if daystart!=dayend:
                        date_list = pd.date_range(start='2020-11-24', end='2020-11-30').astype(str)
                    
                df_data = pd.concat([pd.read_pickle(f'/home/pi/studies/ardmore/data/T1_{d}.pkl.xz', compression='infer') for d in date_list], axis=0)
            
            break
        
        except Exception as e:
            if diagnostics: 
                print(f"Error get_data:{e}")
            pass
        except KeyboardInterrupt:
            break
                
    # float_cols = [x for x in df_data.columns if  not x.startswith('timezone')]
    # df_data.index = pd.to_datetime(df_data['unixtime'].values, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
    # df_data = df_data.resample(f'1S').mean() 
    # df_data = df_data[(df_data['unixtime']>=unixstart)&(df_data['unixtime']<=unixend)]
    # print(df_data.tail(10))
    return df_data
    
        
        
    
    
def contact_server_udp(dict_msg, ip, port, timeout=1, hops=1):
    # send multicast query to listening devices
    multicast_group=(ip, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout)  # duration of blocking the socket
    ttl = struct.pack('b', hops)  # number of routers to reach
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    try:
        dict_demand = {}
        message = str(dict_msg).replace("'", "\"").encode()
        sent = sock.sendto(message, multicast_group)
        # get responses
        while True:
            try:
                data, server = sock.recvfrom(int(2**16))
                received_msg = data.decode("utf-8")
                dict_msg = ast.literal_eval(received_msg)
                dict_demand.update(dict_msg)
            except Exception as e:
                # print("Error inner:", e)
                break
    except Exception as e:
        print("Error in MULTICAST send:", e)
    finally:
        sock.close()
    return dict_demand




def send_command(dict_cmd, ip='192.168.1.3', port=10000, report=True, timeout=0.1):
    try:
        # ip="224.0.2.3"
        response = MULTICAST.send(dict_cmd, ip=ip, port=port, timeout=timeout)
        
        for k, v in response.items():
            if report:
                print('sent:', dict_cmd)
                print('confirmation:', response)
            return v
    except Exception as e:
        print("Error send_command:{}".format(e))
        return {}

    # try:
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a TCP/IP socket
    #     sock.connect((ip, port))  # Connect the socket to the port where the server is listening
    #     sock.sendall(str(dict_cmd).encode())  # send message
    #     # receive response
    #     data = sock.recv(4096)
    #     response = data.decode("utf-8")
    #     if report:
    #         print(f"sent: {dict_cmd}")
    #         print(f"confirmation: {response}")
    # except Exception as e:
    #     response = {}
    # finally:
    #     sock.close()

    # return response


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
dict_agg = {}
start_date = datetime.datetime.now()

# date_list = list(pd.date_range(start=start_date, end=datetime.datetime.now(), normalize=True))
date_list = [
    # 'Last 2 Hours', 
    # 'Last 1 Hour', 
    # 'Last 30 Minutes',
    # 'Last 15 Minutes'
    ]
date_list.reverse()

refresh_rate = 3 * 1000  # [ms]

local_ip = get_local_ip()
tcp_ip = '192.168.1.3'
tcp_port = 10000
capacity = 30000  # [W]
dict_cmd = {}
today = datetime.datetime.now().day

while len(dict_cmd.keys())<=0:
    try:
        dict_cmd = read_json('dict_cmd.txt')
    except Exception as e:
        dict_cmd = {
            "target_watt":30, 
            "set_target":30, 
            "frequency":30, 
            "algorithm":1,
            "history": 'Last 15 Minutes',
            "gain": 32
            }
    
    
cmd_target_watt = float(dict_cmd['target_watt'])
cmd_algorithm = dict_cmd['algorithm']
ldc_signal = float(dict_cmd['frequency'])
history_range = dict_cmd['history']
gain = float(dict_cmd['gain'])

send_command(dict_cmd={"cmd": f"s {cmd_target_watt}"}, ip=tcp_ip, port=tcp_port, timeout=0.1)
send_command(dict_cmd={"cmd": f"k {gain}"}, ip=tcp_ip, port=tcp_port, timeout=0.1)
send_command(dict_cmd={"cmd": f"0 {ldc_signal}"}, ip=tcp_ip, port=tcp_port, timeout=0.1)

df_data = get_data(day=datetime.datetime.now().strftime('%Y_%m_%d'))#.reset_index(drop=True)

algo_labels = {
        'no_ldc': 'Normal', 
        'basic_ldc': 'Basic',
        'advanced_ldc': 'Advanced',
        'ripple_control': 'Ripple'
        }

# returns logo div
def get_logo():
    image = "./UOA.png"
    encoded_image = base64.b64encode(open(image, "rb").read())
    logo = html.Div(
                html.Img(src="data:image/png;base64,{}".format(encoded_image.decode()), height="57"),
                        style={"marginTop": "0", "float":"left", "backgroundColor": "#18252E"},
                className="row",
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


@app.callback(
    Output(component_id='hidden-target', component_property='value'),
    [Input(component_id='btn_cmd_drop', component_property='n_clicks_timestamp')],
    [])
def drop_load(n_clicks_timestamp):
    global cmd_target_watt, cmd_algorithm, ldc_signal
    try:
        # if cmd_algorithm=='basic_ldc': ## emergency drop
        if n_clicks_timestamp>(time.time()*1e3)-10:
            ldc_signal = 750
            cmd_target_watt = 1
            send_command(dict_cmd={"cmd":"s {}".format(cmd_target_watt)}, ip=tcp_ip, port=tcp_port, timeout=0.1)
            send_command(dict_cmd={"cmd":"k {}".format(10000)}, ip=tcp_ip, port=tcp_port, timeout=0.1)
            send_command(dict_cmd={"cmd":"0 {}".format(ldc_signal)}, ip=tcp_ip, port=tcp_port, timeout=0.1)
            return 0.001
        else:
            return cmd_target_watt
    except Exception as e:
        print(f"Error grid_server.drop_load:{e}")




@app.callback(
    Output(component_id='settings', component_property='children'),
    [Input(component_id='input-target-kw', component_property='n_submit'),
    Input(component_id='cmd-algorithm', component_property='value'),
    Input(component_id='cmd-set-target', component_property='value'),
    # Input(component_id='btn_cmd_drop', component_property='n_clicks_timestamp'),
    Input(component_id='input-target-kw', component_property='value'),
    Input(component_id='periodic-target-update', component_property='n_intervals')],
    [])
def update_settings(n_submit, algorithm, set_target, target_watt, n_intervals):
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal #latest_demand
    try:
        cmd_algorithm = algorithm
        send_command(dict_cmd={"algorithm":cmd_algorithm}, ip=tcp_ip, port=tcp_port)

        if cmd_algorithm=='no_ldc':
            ldc_signal = 850
            send_command(dict_cmd={"cmd":f"o {ldc_signal}"}, ip=tcp_ip, port=tcp_port)
            send_command(dict_cmd={"cmd":f"s {30000}", "set_target":30000}, ip=tcp_ip, port=tcp_port)

        elif cmd_algorithm=='ripple_control':
            now = datetime.datetime.now()
            hour = now.hour
            minute = now.minute
            if hour>=21:
                minute_block = ((hour-21)*60) + minute
                signal = 20 + (int(minute_block/10)*5)
            elif (hour>=4):
                minute_block = ((hour-4)*60) + minute
                signal = 100 - (int(minute_block/10)*5)
            elif (hour<4):
                signal = 100
            else:
                signal = 0.0
            
            ldc_signal = signal + 750
            send_command(dict_cmd={"cmd":f"o {ldc_signal}"}, ip=tcp_ip, port=tcp_port)

        elif cmd_algorithm in ['basic_ldc', 'advanced_ldc']:
            print(n_submit, algorithm, set_target, target_watt)
            if n_submit==None or target_watt==None:
                pass
            else:
                cmd_target_watt = target_watt * 1000
                send_command(dict_cmd={"cmd":f"s {cmd_target_watt}", "set_target":set_target}, ip=tcp_ip, port=tcp_port)
                send_command(dict_cmd={"cmd":f"k {gain}"}, ip=tcp_ip, port=tcp_port)

        dict_cmd.update({"target_watt":str(cmd_target_watt), "set_target":set_target, "frequency":str(ldc_signal), "algorithm":cmd_algorithm})
        save_json(dict_cmd, 'dict_cmd.txt')

        return str(dict_cmd)

    except Exception as e:
        print("Error grid_server.update_settings:{}".format(e))




@app.callback(
    Output(component_id='input-target-kw', component_property='style'),
    [Input(component_id='cmd-set-target', component_property='value')],
    [])
def disable_input_target_kw(set_target):
    try:
        if set_target=='auto':
            return {'display':'none'}
        else:
            return {'display': 'block', 'width':'90%'}
    except Exception as e:
        print("Error grid_server.disable_input_target_kw:{}".format(e))




@app.callback(
    Output(component_id='hidden-gain', component_property='children'),
    [Input(component_id='input-cmd-gain', component_property='n_submit')],
    [State(component_id='input-cmd-gain', component_property='value')])
def update_gain(n_submit, new_gain):
    ### change target power setpoint at ldc injector
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand, emergency
    try:
        if n_submit==None or new_gain==None:
            pass
        else:
            gain = int(new_gain)
            print("Gain changed to ", str(gain))
            dict_cmd.update({"gain":str(gain)})
            save_json(dict_cmd, 'dict_cmd.txt')
            msg = "k {}".format(gain)
            send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
            return gain
    except Exception as e:
        print("Error grid_server.update_gain:",e)

  
  


@app.callback(
    Output(component_id='hidden-freq', component_property='children'),
    [Input(component_id='input-cmd-freq', component_property='n_submit'),
    Input(component_id='input-cmd-freq', component_property='value')],
    [])
def update_signal(n_submit, frequency):
    ### change target power setpoint at ldc injector
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand
    try:
        if n_submit==None or frequency==None:
            pass
        else:
            frequency = float(frequency)
            msg = "o {}".format(frequency)
            send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
            print("Frequency changed to ", str(frequency))
            dict_cmd.update({"frequency":str(ldc_signal)})
            save_json(dict_cmd, 'dict_cmd.txt')
            return frequency
    except Exception as e:
        print("Error grid_server.update_frequency:",e)
  
  



@app.callback(
    Output(component_id='display-target-kw', component_property='children'),
    [Input(component_id='periodic-target-update', component_property='n_intervals')],
    [])
def update_display_target(n_intervals):
    # change the frequency signal 
    global date_list, refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand
    d = send_command(dict_cmd={'states':'target_watt'}, report=True)
    if d:
        cmd_target_watt = d["target_watt"]
    return f' {np.round(cmd_target_watt*1e-3, 2)} kW'


@app.callback(
    Output(component_id='display-signal-hz', component_property='children'),
    [Input(component_id='periodic-target-update', component_property='n_intervals')],
    [])
def update_display_signal(n_intervals):
    # change the frequency signal 
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand
    
    d = send_command(dict_cmd={'states':'signal'}, report=True)
    
    if d:
        ldc_signal = d['signal']
    
    return f' {np.round(ldc_signal, 2)} Hz'


@app.callback(
    Output(component_id='display-gain', component_property='children'),
    [Input(component_id='periodic-target-update', component_property='n_intervals')],
    [])
def update_display_gain(n_intervals):
    # change the frequency signal 
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand
    d = send_command(dict_cmd={'states':'gain'}, report=True)
    if d: 
        return f" {d['gain']}"
    return f' {np.round(gain, 2)}'


@app.callback(
    Output(component_id='display-algo', component_property='children'),
    [Input(component_id='periodic-target-update', component_property='n_intervals')],
    [])
def update_display_algo(n_intervals):
    # change the frequency signal 
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand
    d = send_command(dict_cmd={'states':'algorithm'}, report=True)
    if d: 
        return f" {algo_labels[d['algorithm']]}"
    return f' {cmd_algorithm}'

@app.callback(
    Output(component_id='dropdown-history', component_property='option'),
    [Input(component_id='periodic-target-update', component_property='n_intervals')],
    [])
def update_history_option(n_intervals):
    # change the frequency signal 
    global date_list
    hist_files = glob.glob("/home/pi/studies/ardmore/data/T1_*.pkl.xz")
    list_files = [x.split('/')[-1] for x in hist_files]
    dates = ['-'.join(x.split('.')[0].split('_')[1:]) for x in list_files]
    dates.sort()
    date_list = dates
    date_list.extend([
        # 'Last 2 Hours', 
        # 'Last 1 Hour', 
        # 'Last 30 Minutes',
        # 'Last 15 Minutes',
        ])
    date_list.reverse()
    return [{'label': x, 'value': x} for x in date_list]  
  




@app.callback(
    Output(component_id='data-update', component_property='interval'),
    [Input(component_id='dropdown-history', component_property='value')],
    [])
def update_history_range(value):
    # set history to put to graph
    t = time.perf_counter()
    global date_list, refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand, df_data
    history_range = value


    if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours']:
        refresh_rate = 3*1000  #[ms]
    else:
        refresh_rate = 60*1000 

    print("Range: {}   Refresh: {}".format(history_range, refresh_rate))
  
  
    dict_cmd.update({"history":history_range})
    save_json(dict_cmd, 'dict_cmd.txt')

    print("update_history_range dt:", time.perf_counter()-t)
    return refresh_rate




@app.callback(
    Output(component_id='data', component_property='children'),
    [Input(component_id='data-update', component_property='n_intervals'),
    Input(component_id='dropdown-history', component_property='value')],
    [State(component_id='data', component_property='children'), 
    State(component_id='graphs', component_property='children')],
    )
def update_data(n_intervals, history_range, json_data, graph_data):
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand
    try:
        t = time.perf_counter()
        
        if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
            day = datetime.datetime.now().strftime('%Y_%m_%d')
            
            if history_range.split()[2]=='Minutes':
                n_points = int(history_range.split()[1]) * 60 # number of seconds
            else:
                n_points = int(history_range.split()[1]) * 60 * 60 # number of seconds
            
            unixend = int(time.time())
            unixstart =  int(unixend - n_points)
            
            # if json_data:
            #     df_data = pd.read_json(json_data, orient='split').astype(float)
            #     print(df_data)
        else:
            day = history_range
            n_points = 60 * 60 * 24  # number of seconds
            dt_start = pd.to_datetime(history_range).tz_localize('Pacific/Auckland')
            dt_end = dt_start + datetime.timedelta(days=1)
            unixstart =  dt_start.timestamp()
            unixend = dt_end.timestamp()


        
        df_data = get_data(unixstart=unixstart, unixend=unixend)
        
        # if new_data.size:
        #     df_data = pd.concat([df_data, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)
        
        # ### get upperbound data
        # if unixend > df_data['unixtime'].max():
        #     s = df_data['unixtime'].max()
        #     e = unixend # np.min([unixend, s+900])
        #     day = datetime.datetime.fromtimestamp(s).strftime('%Y_%m_%d')
        #     new_data = get_data(unixstart=unixstart, unixend=unixend)
        #     df_data = pd.concat([df_data, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)

        # ### get lowerbound data
        # if unixstart < df_data['unixtime'].min():
        #     e = df_data['unixtime'].min()
        #     s = unixstart # np.max([unixstart, e-900])
        #     day = datetime.datetime.fromtimestamp(s).strftime('%Y_%m_%d')
        #     new_data = get_data(unixstart=unixstart, unixend=unixend)
        #     df_data = pd.concat([new_data.reset_index(), df_data], axis=0, sort='unixtime').reset_index(drop=True)
        
        # df_data = get_data(day=day)

        ### resample to reduce number of points to plot
        df_data.index = pd.to_datetime(df_data['unixtime'].values, unit='s')
        sample = '{}S'.format(max([1,int(n_points/3600)]))
        df_data = df_data.resample(sample).mean().interpolate().reset_index(drop=True)
        if 'target_watt' in df_data.columns: 
            df_data['target_kw'] = df_data['target_watt'] * 1e-3
        if 'power_kw' in df_data.columns:
            pass
        else:
            df_data['power_kw'] = df_data[[x for x in df_data.columns if x.startswith('power_active_')]].sum(axis=1)

        # print("update_data dt:", time.perf_counter() - t)
        return df_data.to_json(orient='split')
    except Exception as e:
        print(f'Error update_data: {e}')




@app.callback(
    Output(component_id='graphs', component_property='children'),
    [
    #Input(component_id='data-update', component_property='n_intervals'),
    Input(component_id='dropdown-history', component_property='value'),
    Input(component_id='data', component_property='children'),
    ],
    # [
    # State(component_id='data', component_property='children'),
    # State(component_id='graphs', component_property='children'),
    # ]
    )
def update_graph(history_range, json_data): 
    t = time.perf_counter() 
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand
    graphs = []
    try:
        t = time.perf_counter()
        if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
            day = datetime.datetime.now().strftime('%Y_%m_%d')
            if history_range.split()[2]=='Minutes':
                n_points = int(history_range.split()[1]) * 60 # number of seconds
            else:
                n_points = int(history_range.split()[1]) * 60 * 60 # number of seconds
            unixend = int(time.time())
            unixstart =  int(unixend - n_points)
        else:
            day = history_range
            n_points = 60 * 60 * 24  # number of seconds
            dt_start = pd.to_datetime(history_range).tz_localize('Pacific/Auckland')
            dt_end = dt_start + datetime.timedelta(days=1)
            unixstart =  dt_start.timestamp()
            unixend = dt_end.timestamp()
            
        # print("before json:",time.perf_counter()-t)
        t = time.perf_counter()
        if json_data:
            df_data = pd.read_json(json_data, orient='split') 
            
            t = time.perf_counter()

            df_data = df_data[(df_data['unixtime']>=unixstart)&(df_data['unixtime']<=unixend)] 
            df_data.index = pd.to_datetime(df_data['unixtime'].values, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland') #[pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').isoformat() for a in df_data['unixtime']]
            df_data.index = df_data.index.tz_localize(None)
            # print("data pruning and changing index:", time.perf_counter()-t)
            t = time.perf_counter()

            

            ### TOTAL POWER ### 
            trace_actual = go.Scattergl(
                x = df_data.index, 
                y = df_data["power_kw"].values,  
                name = 'power_kw',
                line= {'color':color_set[1]},
                # opacity = 0.8,
                fill = "tozeroy",
                # mode = 'markers+lines'
                )

            trace_limit = go.Scattergl(
                x = df_data.index, 
                y = df_data["target_kw"].values,
                name = 'target_kw',
                line= {'color':'orange'},
                # opacity = 0.8,
                # fill = "tozeroy",
                )

            trace_avg_60s = go.Scattergl(
                x = df_data.index, 
                y = df_data["power_kw"].rolling(60).mean(),
                name = 'avg_60s',
                line= {'color':'rgb(255,0,255)'},
                # opacity = 0.8,
                # fill = "tozeroy",
                )


            trace_agg = [trace_actual, trace_limit, trace_avg_60s]

            # trace_agg = [
            #     go.Scattergl(
            #         x = df_data.index, 
            #         y = df_data[x].values,  
            #         name = x,
            #         # line= {'color':color_set[1]},
            #         # opacity = 0.8,
            #         fill = "tozeroy", # if x.startswith('power_kw') else "toself",
            #         # mode = 'markers+lines'
            #         ) for x in ['target_kw', 'power_kw'] if x in df_data.columns
            # ]

            graphs.append(html.Div(dcc.Graph(
                id='total-demand',
                animate=False,
                figure={'data': trace_agg,
                    'layout' : go.Layout(xaxis= dict(autorange=True),
                              yaxis=dict(autorange=True, title='Power (kW)'),
                              margin={'l':50,'r':50,'t':50,'b':50},
                              title='Three Phase Power Demand',
                              # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                              autosize=True,
                              height=300,
                              font=dict(color='#CCCCCC'),
                              titlefont=dict(color='#CCCCCC', size=14),
                              hovermode="closest",
                              plot_bgcolor="#020202", #"#191A1A",
                              paper_bgcolor="#18252E",
                              uirevision='same',
                              )}
                ), className='row'))


            

            ### PHASE POWER ###
            list_phase_power = [a for a in df_data.columns if (a.lower().startswith('power_active_') or a.lower().startswith('power_kw_'))]
            traces_phase_power = []
            i = 0
            for p in list_phase_power:
                traces_phase_power.append(go.Scattergl(
                    x = df_data.index,
                    y = df_data[p],
                    name = f'phase_{p.split("_")[-1]}',
                    line= {'color':color_set[i]},
                    # mode = 'markers+lines'
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )
                  )
                i += 1

            graphs.append(html.Div(dcc.Graph(
                id='demand-per-phase',
                animate=False,
                figure={'data': traces_phase_power,
                    'layout' : go.Layout(xaxis= dict(autorange=True),
                              yaxis=dict(autorange=True, title='Power (W)'),
                              margin={'l':50,'r':50,'t':50,'b':50},
                              title='Power Demand Per Phase',
                              # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                              autosize=True,
                              height=300,
                              font=dict(color='#CCCCCC'),
                              titlefont=dict(color='#CCCCCC', size=14),
                              hovermode="closest",
                              plot_bgcolor="#020202", #"#191A1A",
                              paper_bgcolor="#18252E",
                              uirevision='same',
                              )}
                ), className='row'))

            ### VOLTAGES ###
            list_phase_voltage = [a for a in df_data.columns if a.lower().startswith('voltage_')]
            traces_phase_voltage = []
            i = 0
            for p in list_phase_voltage:
                traces_phase_voltage.append(go.Scattergl(
                        x = df_data.index,
                        y = df_data[p],
                        name = f'phase_{p.split("_")[-1]}',
                        line= {'color':color_set[i]},
                        # mode = 'markers+lines'
                        # opacity = 0.8,
                        # fill = "tozeroy",
                        )
                    )
                i += 1 

            graphs.append(html.Div(dcc.Graph(
                id='voltage-per-phase',
                animate=False,
                figure={'data': traces_phase_voltage,
                    'layout' : go.Layout(xaxis= dict(autorange=True),
                                    yaxis=dict(autorange=True, title='Voltage (V)'),
                                    margin={'l':50,'r':50,'t':50,'b':50},
                                    title='Voltage Per Phase',
                                    # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                                    autosize=True,
                                    height=300,
                                    font=dict(color='#CCCCCC'),
                                    titlefont=dict(color='#CCCCCC', size=14),
                                    hovermode="closest",
                                    plot_bgcolor="#020202", #"#191A1A",
                                    paper_bgcolor="#18252E",
                                    uirevision='same',
                                    )}
                ), className='row'))
            
            trace_signal = go.Scattergl(
                x = df_data.index, 
                y = df_data["signal"].values, 
                name = 'signal',
                line= {'color':'rgb(0,255,255)'},
                opacity = 0.8,
                fill = "tozeroy",
                )

            graphs.append(html.Div(dcc.Graph(
                id='graph-signal',
                animate=False,
                figure={'data': [trace_signal],
                    'layout' : go.Layout(xaxis= dict(autorange=True),
                              yaxis=dict(range=[750, 900], title='Frequency(Hz)'),
                              margin={'l':50,'r':50,'t':50,'b':50},
                              title='LDC Signal',
                              # legend=dict(font=dict(size=10), orientation='v', x=0.85, y=1.15),
                              showlegend=True,
                              autosize=True,
                              height=300,
                              font=dict(color='#CCCCCC'),
                              titlefont=dict(color='#CCCCCC', size=14),
                              hovermode="closest",
                              plot_bgcolor="#020202", #"#191A1A",
                              paper_bgcolor="#18252E",
                              uirevision='same',
                              )}
                ), className='row'))

            
            # print("update_graph dt:", time.perf_counter() - t)

            return graphs

    except Exception as e:
        print(f"Error graph_update: {e}")




@app.callback(
    Output("modal", "is_open"),
    [Input("open", "n_clicks"), Input("close", "n_clicks")],
    [State("modal", "is_open")],
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


def serve_layout():
    return html.Div([
        # header
        html.Div([
            dcc.Location(id='url', refresh=False),
            get_logo(),
            html.H2("Localized Demand Control", 
                style={
                    'marginTop':'5', 
                    'marginLeft':'7', 
                    'display':'inline-block', 
                    'text-align':'center',
                    'float':'center', 
                    'color':'white', 
                    "backgroundColor": "#18252E"}),
            ],
        ),
        
        # tabs
        html.Div([
            dcc.Tabs( id="tabs", children=[
                dcc.Tab(
                    label="Realtime", 
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




def render_status(history=True):
    # render content for status tab
    global date_list, refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_target_watt, ldc_signal, latest_demand

    date_list = []
    if history:
        hist_files = glob.glob("/home/pi/studies/ardmore/data/T1_*.pkl.xz")
        list_files = [x.split('/')[-1] for x in hist_files]
        dates = ['-'.join(x.split('.')[0].split('_')[1:]) for x in list_files]
        dates.sort()
        date_list.extend(dates)
        
    else:
        date_list.extend([
            'Last 2 Hours', 
            'Last 1 Hour', 
            'Last 30 Minutes',
            'Last 15 Minutes',
            ])
        
    date_list.reverse()

    empty = html.Div('  ',
                className='column',
                style={
                    'color':'white', 
                    'marginTop':20, 
                    'display':'inline-block', 
                    "position": "relative"
                    }
            )

    banner = html.Div([
                html.H1("Microgrid Status", 
                    style={
                        'marginTop':'5', 
                        'text-align':'center',
                        'float':'center', 
                        'color':'white'
                        }
                    ),
                ], 
                className='banner', 
                style={
                    'width':'100%', 
                    'display':'inline-block',
                    "backgroundColor": "#18252E",
                    }
            )

    plot_range_block = html.Div([
                            html.Label('Plot Range:', 
                                className='column', 
                                style={
                                    'color':'white', 
                                    'text-align':'left', 
                                    'display':'inline-block', 
                                    "position": "relative"
                                    }
                                ),
                            dcc.Dropdown(
                                id='dropdown-history',
                                options=[{'label': x, 'value': x} for x in date_list],
                                value=date_list[0],
                                ),
                            ],className='column', 
                        )

    show_target_block = html.Div([
                        html.Label('Target:', 
                            className='column', 
                            style={
                                'color':'white', 
                                'text-align':'left', 
                                'display':'inline-block', 
                                'position': 'relative'
                                }
                            ),
                        html.Div(id='display-target-kw', 
                            children=f'{np.round(float(cmd_target_watt)*1e-3, 3)} kW', 
                            className='column', 
                            style={
                                'font-size':'x-large', 
                                'color':'white', 
                                'text-align':'left', 
                                'display':'inline-block', 
                                'position': 'relative'
                                }
                            ),
                        dcc.Interval(id='periodic-target-update', 
                                interval=10*1000, 
                                n_intervals=0
                            ),
                        ], className='column', 
                    )
    
    show_signal_block = html.Div([
                        html.Label('Signal:', 
                            className='column',
                            style={
                                'color':'white', 
                                'text-align':'left', 
                                'display':'inline-block', 
                                'position': 'relative'
                                }
                            ),
                        html.Div(id='display-signal-hz', 
                            children=f'{np.round(ldc_signal, 1)} Hz', 
                            className='column',
                            style={
                                'font-size':'x-large', 
                                'color':'white', 
                                'text-align':'left', 
                                'display':'inline-block', 
                                'position': 'relative'
                                }
                            ),
                        ], className='column',
                    )
                    
    show_gain_block = html.Div([
                    html.Label('Gain:', 
                        className='column',
                        style={
                            'color':'white', 
                            'text-align':'left', 
                            'display':'inline-block', 
                            "position": "relative"
                            }
                        ),
                    html.Div(id='display-gain', 
                        children=f'{np.round(gain, 1)}', 
                        className='column',
                        style={
                            'font-size':'x-large', 
                            'color':'white', 
                            'text-align':'left', 
                            'display':'inline-block', 
                            "position": "relative"
                            }
                        ),
                    ], className='column',
                )
    
    show_algorithm_block = html.Div([
                    html.Label('Algorithm:', 
                        className='column',
                        style={
                            'color':'white', 
                            'text-align':'left', 
                            'display':'inline-block', 
                            "position": "relative"
                            }
                        ),
                    html.Div(id='display-algo', 
                        children=f'{algo_labels[cmd_algorithm]}', 
                        className='column',
                        style={
                            'font-size':'x-large', 
                            'color':'white', 
                            'text-align':'left', 
                            'display':'inline-block', 
                            "position": "relative"
                            }
                        ),
                    ], className='column',
                )
    
    ##################################################
    set_algorithm_block = html.Div([
                        html.Label('Algorithm:', 
                            className='column',
                            style={
                                'color':'white', 
                                'display':'inline-block', 
                                "position": "relative"
                                }
                            ),
                        dcc.RadioItems(
                            id='cmd-algorithm',
                            options=[
                                {"label": "No LDC", "value": 'no_ldc'},
                                {"label": "Basic", "value": 'basic_ldc'},
                                {"label": "Advanced", "value": 'advanced_ldc'},
                                # {"label": "Smart", "value": 'smart_ldc'},
                                {"label": "Ripple Control", "value": 'ripple_control'},
                            ],
                            value=cmd_algorithm,
                            className='column',
                            style={
                                'color':'white', 
                                # 'margin': '3', 
                                "position": "relative", 
                                'display': 'inline-block'}
                            ),  
                        ], 
                        className='column',
                        style={
                            'display':'inline-block', 
                            "position": "relative",
                            }
                    )

    set_target_block = html.Div([
                            html.Label('Set Target:', 
                                className='column',
                                style={
                                    'color':'white', 
                                    'display':'inline-block', 
                                    "position": "relative"
                                    }
                                ),
                            dcc.RadioItems(
                                id='cmd-set-target',
                                options=[
                                    {"label": "Auto", "value": 'auto'},
                                    {"label": "Manual (kW)", "value": 'manual'},
                                ],
                                value=dict_cmd["set_target"],
                                className='column',
                                style={
                                    'color':'white', 
                                    'margin': '3', 
                                    "position": "relative",
                                    }
                            ),
                            dcc.Input(id='input-target-kw', 
                                # value= np.round(float(cmd_target_watt)/1000, 3), # converted to kW
                                disabled=False, 
                                type='number', 
                                min=0, 
                                # max= 30, # converted to kW
                                step=0.10, 
                                debounce=True,
                                className='column',
                                style={
                                    'font-size': 'large', 
                                    'text-align': 'center', 
                                    'display':'inline-block', 
                                    'width':'120', 
                                    # 'padding':'3', 
                                    "position": "relative"
                                    }
                                ),
                            ], 
                            className='column',
                            style={'display':'inline-block', "position": "relative",}
                        )
    
    set_signal_block = html.Div([
                            html.Label('Set signal (Hz):', 
                                className='column',
                                style={
                                    'text-align':'left', 
                                    'color':'white', 
                                    'display':'inline-block', 
                                    'margin':'0', 
                                    "float": "left"
                                    }
                                ),
                            dcc.Input(id='input-cmd-freq', 
                                # value=ldc_signal,
                                disabled=False, 
                                type='number', 
                                min=0, 
                                max= 5000, 
                                step=1, 
                                debounce=True,
                                className='column',
                                style={
                                    'font-size':'large', 
                                    'text-align':'center', 
                                    'display':'inline-block', 
                                    'width':'120', 
                                    'padding':'0', 
                                    "position": "relative"
                                    }
                                ),
                            ], 
                            className='column', 
                            style={
                                'text-align': 'left', 
                                'display': 'inline-block', 
                                'padding': '0', 
                                "float": "left"
                                },
                        )

    set_gain_block = html.Div([
                        html.Label('Set gain:', 
                            className='column',
                            style={
                                'text-align': 'left', 
                                'color': 'white', 
                                'display': 'inline-block', 
                                'margin': '0', 
                                "float": "left"
                                }
                            ),
                        dcc.Input(id='input-cmd-gain', 
                            # value=gain,
                            disabled=False, 
                            type='number', 
                            min=0, 
                            max= 5000, 
                            step=1, 
                            debounce=True,
                            className='column',
                            style={
                                # 'font-size':'large', 
                                'text-align':'center', 
                                'display':'inline-block', 
                                'width':'120', 
                                'padding':'0', 
                                "position": "relative"
                                }
                            ),
                        ], 
                        className='column', 
                        style={
                            'text-align':'left', 
                            'display':'inline-block', 
                            'padding':'0', 
                            "float": "left"
                            },
                    )

    set_emergency_block = html.Div([
                                html.Label('Emergency load shedding:', 
                                    className='column',
                                    style={
                                        'text-align':'left', 
                                        'color':'white', 
                                        'display':'inline-block', 
                                        'margin':'0', 
                                        "float": "left"
                                        }
                                    ),
                                html.Button('Drop!', 
                                    id='btn_cmd_drop', 
                                    n_clicks_timestamp=0, 
                                    className='column', 
                                    style={
                                        'text-align':'center', 
                                        'font-size':'large', 
                                        'width': '60',
                                        'border-radius':'10px', 
                                        'hover':{
                                            'background-color':'rgb(255,255,255)', 
                                            'color': 'rgb(255,0,0)'
                                            }
                                        }
                                    ),
                                ],
                                className='column', 
                            )

    settings = html.Div(
                [
                    dbc.Button("Change Settings", id="open"),
                    dbc.Modal(
                        [
                            dbc.ModalHeader("Settings"),
                            dbc.ModalBody(
                                children=[
                                    set_algorithm_block,
                                    set_target_block,
                                    set_signal_block,
                                    set_gain_block,
                                    set_emergency_block,
                                ]
                            ),
                            empty,
                            dbc.ModalFooter(
                                dbc.Button("Close", id="close", className="ml-auto")
                            ),
                        ],
                        id="modal",
                        size='sm',
                        
                    ),
                ]
            )

    if history:
        sidebar = html.Div([
            plot_range_block,
            ],
            className='column s12 m2 l2',
            style = {
                "position": "relative",
                "float": "left",
                # "border": "1px solid",
                # "borderColor": "rgba(68,149,209,.9)",
                "overflow": "hidden",
                "marginBottom": "2px",
                "width":"15%"
            },
        )
    else:
        sidebar = html.Div([
            plot_range_block,
            empty,
            show_target_block,
            show_signal_block,
            show_gain_block,
            show_algorithm_block,
            empty,
            settings,
            ], 
            # className='row', 
            # style={'color':'white', 'display':'inline-block', 'margin':'3', 'width':'150px'},
            className='column s12 m2 l2',
            style = {
                "position": "relative",
                "float": "left",
                # "border": "1px solid",
                # "borderColor": "rgba(68,149,209,.9)",
                "overflow": "hidden",
                "marginBottom": "2px",
                "width":"15%"
            },
        )

    hidden_data_block = html.Div([
                            dcc.Interval(id='data-update', interval=refresh_rate, n_intervals=1),
                            html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0'}),
                            html.Div(children=html.Div(id='settings'), className='row', style={'display':'none'}),
                            html.Div(children=html.Div(id='hidden-target'), style={'display': 'none'}),
                            html.Div(children=html.Div(id='hidden-gain'), style={'display': 'none'}),
                            html.Div(children=html.Div(id='hidden-freq'), style={'display': 'none'}),
                            html.Div(children=html.Div(id='hidden-freq2'), style={'display': 'none'}),
                            # html.Div(children=html.Div(id='dcc-holder'), style={'display': 'none'}),
                            ], 
                            style={'display':'none'},
                        )

    graphs_block = html.Div([
            html.Div(id='graphs')], 
            className='col s12 m12 l7',
            style={'width':'80%', 'display':'inline-block', 'padding':'3px'}
        )

    return html.Div(children=[
                banner,
                ### setttings
                sidebar,
                ### hidden divs
                hidden_data_block,
                ### actual graph
                graphs_block,
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





app.layout = serve_layout()

@app.callback(
    Output(component_id="tab_content", component_property="children"), 
    [Input(component_id="tabs", component_property="value")])
def render_content(tab):
    if tab == "status_tab":
        return render_status(history=False)
    elif tab == "history_tab":
        return render_status(history=True)
    else:
        return render_status(history=False)



css_directory = os.getcwd()


if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0', port=15003)


# to run in gunicorn:
# gunicorn grid_server:server -b :15003
