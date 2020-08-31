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
global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit
global ldc_signal, latest_demand, emergency



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
        print("Error writing to serial:", e)



def get_start_date(db_name='./ldc_agg_flat.db', table='data'):
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
            
        return int(start)

    except Exception as e:
        print("Error in get_start_date:", e)
        return time.time()



def get_data(dict_msg={"algorithm":1, "loading":10, "frequency":810, "timescale":1, "duration":60*15, "unixstart":0, "unixend":0},
    db_name='./ldc_agg_melted.db', duration=60*60*24, mcast_ip="224.0.2.3", mcast_port=16003, report=False,
    params='("power_kw", "power_kw_1", "power_kw_2", "power_kw_3", "voltage_1", "voltage_2", "voltage_3", "frequency_1", "loading", "signal")'):
    """ Fetch data from the local database"""
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand

    start = int(dict_msg['unixstart'])
    end = int(dict_msg['unixend'])
    if start==0 and end==0:
        end = time.time()
        start = end - duration
    else:
        pass

    while True:
        try:
            con = lite.connect(db_name)
            con.execute('pragma journal_mode=wal;')
            # row = con.execute('PRAGMA table_info(data);')
            # col_labels = [desc[1] for desc in row.fetchall()]
            
            cur = con.cursor()
            with con:
                sql_cmd = "SELECT * FROM data WHERE parameter IN {} AND unixtime BETWEEN {} AND {} ORDER BY unixtime ASC".format(params, start, end)
                cur.execute(sql_cmd) 
                data = np.array(cur.fetchall())
                df_data = pd.DataFrame(data, columns=['unixtime', 'parameter','value'])

            if len(df_data.index):
                df_data['value'] = df_data['value'].values.astype(float)
                df_data['unixtime'] = df_data['unixtime'].values.astype(float)
                df_data = pd.pivot_table(data=df_data, values='value', index='unixtime', columns='parameter')
                df_data.rename(columns={'loading':'target_kw'}, inplace=True)
                # df_data['agg_demand'] = df_data[['power_kw_1', 'power_kw_2', 'power_kw_3']].sum(axis=1)
                
                return df_data

            else:
                print("Error in get_data: No data.")
                raise Exception            
            
        except KeyboardInterrupt:
            break
            
        except Exception as e:
            ### adjust date bounderies to fetch
            start = start - 5
            end = end - 1
            time.sleep(1e-6)
            pass






def send_command(dict_cmd, ip='localhost', port=10000):
    try:
        response = MULTICAST.send(dict_cmd, ip="224.0.2.3", port=16003, timeout=1)
        print(response)
    except Exception as e:
        print("Error send_command:{}".format(e))

    # try:
    #     # Create a TCP/IP socket
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #     # Connect the socket to the port where the server is listening
    #     server_address = (ip, port)
    #     sock.connect(server_address)
        
    #     message_toSend = str(dict_cmd).encode()
    #     # send message
    #     sock.sendall(message_toSend)
        
    #     # receive response
    #     data = sock.recv(2**16)
    #     received_msg = data.decode("utf-8")
    #     print("Injector response:", received_msg)
    #     dict_msg = ast.literal_eval(received_msg)
    #     # print('received {!r}'.format(dict_msg))
              
    # except Exception as e:
    #     dict_msg = {}

    # finally:
    #     sock.close()

    # return dict_msg


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
display_limit =True
emergency = False
dict_agg = {}
sd = datetime.datetime.fromtimestamp(get_start_date())
start_date = datetime.datetime(sd.year, sd.month, sd.day)
refresh_rate = 10 * 1000  # [ms]

local_ip = get_local_ip()
tcp_ip = '192.168.1.3'
tcp_port = 10000
capacity = 30000  # [W]
dict_cmd = {}

try:
    dict_cmd = read_json('dict_cmd.txt')
    cmd_loading = float(dict_cmd['agg_limit'])
    cmd_algorithm = int(dict_cmd['algorithm'])
    ldc_signal = float(dict_cmd['frequency'])
    history_range = dict_cmd['history']
    gain = dict_cmd['gain']
except Exception as e:
    print("Error initial command:", e)
    cmd_loading = 30000
    cmd_algorithm = 0
    ldc_signal = 850
    latest_demand = 0
    history_range = 'Last 30 Minutes'
    gain = 100

previous_limit = cmd_loading  
timescale = 1
sum_actual = 0
sum_proposed = 0
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




@app.callback(
    dash.dependencies.Output('cmd-loading', 'children'),
    [dash.dependencies.Input('input-cmd-loading', 'n_submit'),
    dash.dependencies.Input('input-cmd-loading', 'n_blur'),
    dash.dependencies.Input('cmd-algorithm','value'),
    dash.dependencies.Input('btn_cmd_drop', 'n_clicks')],
    [dash.dependencies.State('input-cmd-loading', 'value')])
def update_loading(n_submit, n_blur, algorithm, n_clicks_timestamp, loading):
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand, emergency
    cmd_algorithm = algorithm
    emergency = False
    if n_clicks_timestamp==None: 
        n_clicks_timestamp=0
        dict_cmd = read_json('dict_cmd.txt')
        cmd_loading = float(dict_cmd['agg_limit'])
        cmd_algorithm = int(dict_cmd['algorithm'])
        ldc_signal = float(dict_cmd['frequency'])
        history_range = dict_cmd['history']
        gain = dict_cmd['gain']

    elif ((time.time()-n_clicks_timestamp) < 0.1):
        dict_cmd = read_json('dict_cmd.txt')
        cmd_loading = float(dict_cmd['agg_limit'])
        cmd_algorithm = int(dict_cmd['algorithm'])
        ldc_signal = float(dict_cmd['frequency'])
        history_range = dict_cmd['history']
        gain = dict_cmd['gain']
        
    elif cmd_algorithm==0:
        cmd_loading = 30000
        # print("Setpoint changed to ", str(cmd_loading), " kVA")
        msg = "s {}".format(cmd_loading)
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)

        msg = "k {}".format(10000)
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
        

    else:
        cmd_loading = loading * 1000
        ### change target power setpoint at ldc injector
        # if n_submit>0: #(cmd_loading!=previous_limit):
        # print("Setpoint changed to ", str(cmd_loading), " kVA")
        msg = "s {}".format(cmd_loading)
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
        previous_limit = cmd_loading        
        
        msg = "k {}".format(gain)
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)


    dict_cmd.update({"agg_limit":str(cmd_loading), "frequency":str(ldc_signal), "gain":gain})
    save_json(dict_cmd, 'dict_cmd.txt')

    display_limit = True

    return np.round(float(cmd_loading)/1000, 3)


@app.callback(
    dash.dependencies.Output('output-gain', 'children'),
    [dash.dependencies.Input('input-cmd-gain', 'n_submit'),
    dash.dependencies.Input('input-cmd-gain', 'n_blur'),],
    [dash.dependencies.State('input-cmd-gain', 'value')])
def update_gain(n_submit, n_blur, new_gain):
    ### change target power setpoint at ldc injector
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand, emergency
    try:
        if new_gain==None:
            dict_cmd = read_json('dict_cmd.txt')
            cmd_loading = float(dict_cmd['agg_limit'])
            cmd_algorithm = int(dict_cmd['algorithm'])
            ldc_signal = float(dict_cmd['frequency'])
            history_range = dict_cmd['history']
            gain = dict_cmd['gain']
            print("update_gain initial")
        else:
            gain = int(new_gain)
            msg = "k {}".format(gain)
            send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
            # print("Gain changed to ", str(gain))
            dict_cmd.update({"gain":gain})
            save_json(dict_cmd, 'dict_cmd.txt')

    except Exception as e:
        print("Error changing gain:",e)

    
    return gain


@app.callback(
    dash.dependencies.Output('output-freq', 'children'),
    [dash.dependencies.Input('input-cmd-freq', 'n_submit'),
    dash.dependencies.Input('input-cmd-freq', 'n_blur'),],
    [dash.dependencies.State('input-cmd-freq', 'value')])
def update_frequency(n_submit, n_blur, frequency):
    ### change target power setpoint at ldc injector
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
    try:
        # if n_submit==None:
        #     pass
        # elif n_submit > 0:
        try:
            frequency = float(frequency)
            print("update_frequency if0")
        except:
            dict_cmd = read_json('dict_cmd.txt')
            frequency = float(dict_cmd['frequency'])
            
        ldc_signal = frequency
        msg = "o {}".format(frequency)
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
        # print("Frequency changed to ", str(frequency))
        display_limit = True
        dict_cmd.update({"frequency":str(ldc_signal)})
        save_json(dict_cmd, 'dict_cmd.txt')

    except Exception as e:
        print("Error changing frequency:",e)
    
    return frequency


@app.callback(
    dash.dependencies.Output('input-cmd-loading', 'value'),
    [dash.dependencies.Input('btn_cmd_drop', 'n_clicks'),],
    )
def emergency(b1_nclick):
    ### change target power setpoint at ldc injector
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand, emergency
    
    if cmd_algorithm==0 or b1_nclick==None:
        b1_nclick = 0
    else:
        try:
            if (b1_nclick > 0):
                frequency = 750
                ldc_signal = frequency
                emergency = True
                display_limit = True
                cmd_loading = 1
                msg = "s {}".format(cmd_loading)
                send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)

                msg = "k {}".format(10000)  # accelerate gain
                send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)

                dict_cmd.update({"agg_limit":str(cmd_loading), "frequency":str(ldc_signal)})
                save_json(dict_cmd, 'dict_cmd.txt')

            else:
                pass
        except Exception as e:
            print("Error changing frequency:",e)

    
    return cmd_loading/1000



@app.callback(
    dash.dependencies.Output('cmd-signal', 'children'),
    [dash.dependencies.Input('input-cmd-loading', 'n_submit'),
    dash.dependencies.Input('input-cmd-loading', 'n_blur'),
    dash.dependencies.Input('data', 'children')
    ],
    [dash.dependencies.State('input-cmd-loading', 'value')],
    )
def update_signal(n_submit, n_blur, json_data, value):
    # change the frequency signal 
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
    df_data = pd.read_json(json_data, orient='split') 
    ldc_signal = df_data['signal'].values[-1]

    return np.round(ldc_signal, 2)

    

@app.callback(
        dash.dependencies.Output('command','children'),
        [dash.dependencies.Input('cmd-algorithm','value')])
def update_command(algorithm):
    # change the command algorithm
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
    cmd_algorithm = algorithm

    if cmd_algorithm==0:
        frequency = 850
        ldc_signal = frequency
        cmd_loading = 30000
        display_limit = True
        msg = "s {}".format(cmd_loading)
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
        msg = "k {}".format(10000)  # accelerate gain
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
        
    else:
        dict_cmd = read_json('dict_cmd.txt')
        cmd_loading = float(dict_cmd['agg_limit'])
        ### change target power setpoint at ldc injector
        # print("Setpoint changed to ", str(cmd_loading), " kVA")
        msg = "s {}".format(cmd_loading)
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
        msg = "k {}".format(gain)  # restor gain
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
        
        previous_limit = cmd_loading    

    dict_cmd.update({"agg_limit":str(cmd_loading), "frequency":str(ldc_signal)})
    save_json(dict_cmd, 'dict_cmd.txt')
    
    
    display_limit = True
    return algorithm


# def get_frequency(cmd_algorithm, cmd_loading):
#     global capacity, ldc_signal, latest_demand

#     target_loading = float(cmd_loading)
#     percent_loading = float(target_loading) / capacity

    
#     ldc_upper = 850
#     ldc_lower = 750
#     ldc_center = 810 
#     ldc_bw = ldc_upper - ldc_lower  # bandwidth
#     w_past = 0.1  # weight given to the past signal, acting as a damper to change in ldc_signal

#     try:
#         if cmd_algorithm==0:
#             ldc_signal=ldc_upper

#         else:
#             offset = ((target_loading - latest_demand)/latest_demand) * ((850-750))
#             ldc_signal += offset
#             ldc_signal = np.min([ldc_signal, 850])
#             ldc_signal = np.max([ldc_signal, 750]) 

#         return np.round(ldc_signal, 2)
#     except Exception as e:
#         print("Error in get_frequency:", e, cmd_algorithm, cmd_loading, ldc_signal)
#         return 810



@app.callback(
    dash.dependencies.Output('data-update', 'interval'),
    [dash.dependencies.Input('dropdown-history', 'value')])
def update_history_range(value):
    # set history to put to graph
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand, df_data
    history_range = value

    if history_range in ['Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
        refresh_rate = 10*1000  #[ms]
    else:
        refresh_rate = 10*1000 * 60 * 60

    print("Range: {}   Refresh: {}".format(history_range, refresh_rate))
    
    
    dict_cmd.update({"history":history_range})
    save_json(dict_cmd, 'dict_cmd.txt')


    return refresh_rate




@app.callback(
    dash.dependencies.Output('data','children'),
    [
    # dash.dependencies.Input('cmd-algorithm','value'),
    # dash.dependencies.Input('cmd-loading','children'),
    # dash.dependencies.Input('data-update','n_intervals'),
    dash.dependencies.Input('dropdown-history','value')
    ],
    [dash.dependencies.State('data', 'children')],)
def update_data(new_range,json_data):
# def update_data(algorithm, loading, n_intervals, new_range, json_data):
    # update the graph
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
    
    # print("update_data:", n_intervals)
    try:
        history_range = new_range
        dict_cmd.update({"agg_limit":str(cmd_loading), "algorithm":str(cmd_algorithm), "frequency":str(ldc_signal), "gain":gain, "history":history_range})
        save_json(dict_cmd, 'dict_cmd.txt')
        
        if history_range in ['Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
            if history_range.split()[2]=='Minutes':
                n_points = int(history_range.split()[1]) * 60 # number of seconds
            else:
                n_points = int(history_range.split()[1]) * 60 * 60 # number of seconds

            unixend = int(time.time())
            unixstart =  int(unixend - n_points)
            sample = '{}S'.format(max([1,int(n_points/2000)]))
            
        else:
            n_points = 60 * 60 * 24  # number of seconds
            dt_start = datetime.datetime.strptime(history_range, '%Y-%m-%d')
            dt_end = dt_start + datetime.timedelta(days=1)
            unixstart =  int(time.mktime(dt_start.timetuple()))
            unixend = int(time.mktime(dt_end.timetuple()))
            sample = '60S'

        t1 = 0
        t2 = 0
        
        if json_data:
            df_data = pd.read_json(json_data, orient='split').astype(float)

            ### get upperbound data
            s = int(df_data.tail(1)['unixtime'])
            e = unixend
            new_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":s, "unixend":e})
            df_data = pd.concat([df_data, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)
            t2 = len(new_data.index)
        
            # ### get lowerbound data
            if unixstart < int(df_data['unixtime'].values[0]):
                s = unixstart
                e = int(df_data['unixtime'].values[0])
                new_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":unixstart, "unixend":unixend})
                df_data = pd.concat([new_data.reset_index(), df_data], axis=0, sort='unixtime').reset_index(drop=True)
                t1 = len(new_data.index)
            
        else:
            df_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":unixstart, "unixend":unixend})
            ### params='("power_kw", "power_kw_1", "power_kw_2", "power_kw_3", "voltage_1", "voltage_2", "voltage_3", "frequency_1", "loading", "signal")')       
        if len(df_data.index):
            df_data = df_data.groupby('unixtime', as_index=True).mean().reset_index(drop=False)
            df_data.index = pd.to_datetime(df_data['unixtime'], unit='s')
            df_data = df_data.resample('1S').pad().reset_index(drop=True)
            
            ### update target
            cmd_loading =  (np.mean(df_data.tail(3600)['power_kw'].values) * 1000)
            if cmd_loading:
                msg = "s {}".format(cmd_loading)
                send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
        
            # df_data = df_data[(df_data['unixtime']>=unixstart) & (df_data['unixtime']<=unixend)]
            ldc_signal = float(df_data.tail(1)['signal'])
            print("lowerbound:{}    upperbound:{}    all:{}    {}    {}".format(t1, t2, len(df_data.index), unixstart, unixend))
            return df_data.to_json(orient='split')
        else:
            print("failed data fetch.")

    except Exception as e:
        print(f'Error update_data: {e}')




@app.callback(
    dash.dependencies.Output('graphs','children'),
    [
    # dash.dependencies.Input('data', 'children'),
    dash.dependencies.Input('data-update','n_intervals'),
    dash.dependencies.Input('dropdown-history', 'value')
    ],
    [dash.dependencies.State('graphs','children'),
    ]
    )
def update_graph(n_intervals, history_range, past_graph):  
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
    graphs = []
    # print("update_graph")
    try:
        dict_cmd.update({"agg_limit":str(cmd_loading), "algorithm":str(cmd_algorithm), "frequency":str(ldc_signal), "gain":gain, "history":history_range})
        save_json(dict_cmd, 'dict_cmd.txt')
        
        if history_range in ['Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
            if history_range.split()[2]=='Minutes':
                n_points = int(history_range.split()[1]) * 60 # number of seconds
            else:
                n_points = int(history_range.split()[1]) * 60 * 60 # number of seconds

            unixend = int(time.time())
            unixstart =  int(unixend - n_points)
            sample = '{}S'.format(max([1,int(n_points/2000)]))

        else:
            n_points = 60 * 60 * 24  # number of seconds
            dt_start = datetime.datetime.strptime(history_range, '%Y-%m-%d')
            dt_end = dt_start + datetime.timedelta(days=1)
            unixstart =  int(time.mktime(dt_start.timetuple()))
            unixend = int(time.mktime(dt_end.timetuple()))
            sample = '60S'

        t1 = 0
        t2 = 0
        try:
            dict_data = {}
            for k in past_graph:
                for d in k['props']['children']['props']['figure']['data']:
                    dict_data.update({d['name']:d['y']})

            df_data_graph = pd.DataFrame(data=dict_data)
            df_data_graph['unixtime'] = pd.to_datetime(d['x']).astype(int) * 1e-9
            
            ### get upperbound data
            s = int(df_data_graph.tail(1)['unixtime'])
            e = unixend
            new_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":s, "unixend":e})
            df_data_graph = pd.concat([df_data_graph, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)
            t2 = len(new_data.index)
            
            # ### get lowerbound data
            if unixstart < int(df_data_graph['unixtime'].values[0]):
                s = unixstart
                e = int(df_data_graph['unixtime'].values[0])
                new_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":unixstart, "unixend":unixend})
                df_data_graph = pd.concat([new_data.reset_index(), df_data_graph], axis=0, sort='unixtime').reset_index(drop=True)
                t1 = len(new_data.index)
                
        except Exception as e:
            print("error past_graph:{}".format(e))
            # df_data_graph = pd.read_json(json_data, orient='split')  
            df_data_graph = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":unixstart, "unixend":unixend})
            
        # if len(df_data.index):
        df_data_graph = df_data_graph.groupby('unixtime', as_index=True).mean().reset_index(drop=False)
        df_data_graph.index = pd.to_datetime(df_data_graph['unixtime'], unit='s')
        df_data_graph = df_data_graph.resample('1S').pad().reset_index(drop=True)
        
        ### update target
        cmd_loading =  (np.mean(df_data_graph.tail(3600)['power_kw'].values) * 1000)
        if cmd_loading:
            msg = "s {}".format(cmd_loading)
            send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
    
        # df_data = df_data[(df_data['unixtime']>=unixstart) & (df_data['unixtime']<=unixend)]
        ldc_signal = float(df_data_graph.tail(1)['signal'])
        print("lowerbound:{}    upperbound:{}    all:{}    {}    {}".format(t1, t2, len(df_data_graph.index), unixstart, unixend))
    

        df_data_graph = df_data_graph[(df_data_graph['unixtime'] >= unixstart) & (df_data_graph['unixtime']<=unixend)]
        df_data_graph.index = [pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').isoformat() for a in df_data_graph['unixtime']]

        ### TOTAL POWER ### 
        trace_actual = go.Scattergl(
                    x = df_data_graph.index, 
                    y = df_data_graph["power_kw"].values,  
                    name = 'power_kw',
                    line= {'color':'rgb(0,255,0)'},
                    # opacity = 0.8,
                    fill = "tozeroy",
                    # mode = 'markers+lines'
                    )

        trace_limit = go.Scattergl(
                    x = df_data_graph.index, 
                    y = df_data_graph["target_kw"].values * 0.001,
                    name = 'target_kw',
                    line= {'color':'rgb(255,0,0)'},
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )



        trace_agg = [trace_actual, trace_limit]

        graphs.append(html.Div(dcc.Graph(
                    id='total-demand',
                    animate=False,
                    figure={'data': trace_agg,
                            'layout' : go.Layout(xaxis= dict(autorange=True),
                                                yaxis=dict(autorange=True, title='Power (kW)'),
                                                margin={'l':50,'r':1,'t':45,'b':50},
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


        trace_signal = go.Scattergl(
                    x = df_data_graph.index, 
                    y = df_data_graph["signal"].values, 
                    name = 'signal',
                    line= {'color':'rgb(0,255,255)'},
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )



        graphs.append(html.Div(dcc.Graph(
                    id='graph-signal',
                    animate=False,
                    figure={'data': [trace_signal],
                            'layout' : go.Layout(xaxis= dict(autorange=True),
                                                yaxis=dict(autorange=True, title='Frequency(Hz)'),
                                                margin={'l':50,'r':1,'t':45,'b':50},
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


        ### PHASE POWER ###
        trace_power1 = go.Scattergl(
                    x = df_data_graph.index,
                    y = df_data_graph['power_kw_1'],
                    name = 'power_kw_1',
                    line= {'color':'rgb(255,0,0)'},
                    # mode = 'markers+lines'
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )

        trace_power2 = go.Scattergl(
                    x = df_data_graph.index,
                    y = df_data_graph['power_kw_2'],
                    name = 'power_kw_2',
                    line= {'color':'rgb(0,255,0)'},
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )

        trace_power3 = go.Scattergl(
                    x = df_data_graph.index,
                    y = df_data_graph['power_kw_3'],
                    name = 'power_kw_3',
                    line= {'color':'rgb(0,0,255)'},
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )

        graphs.append(html.Div(dcc.Graph(
                    id='demand-per-phase',
                    animate=False,
                    figure={'data': [trace_power1, trace_power2, trace_power3], 
                            'layout' : go.Layout(xaxis= dict(autorange=True),
                                                yaxis=dict(autorange=True, title='Power (kW)'),
                                                margin={'l':50,'r':1,'t':45,'b':50},
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
        trace_voltage1 = go.Scattergl(
                    x = df_data_graph.index,
                    y = df_data_graph['voltage_1'],
                    name = 'voltage_1',
                    line= {'color':'rgb(255,30,0)'},
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )

        trace_voltage2 = go.Scattergl(
                    x = df_data_graph.index,
                    y = df_data_graph['voltage_2'],
                    name = 'voltage_2',
                    line= {'color':'rgb(0,255,0)'},
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )

        trace_voltage3 = go.Scattergl(
                    x = df_data_graph.index,
                    y = df_data_graph['voltage_3'],
                    name = 'voltage_3',
                    line= {'color':'rgb(0,0,255)'},
                    # opacity = 0.8,
                    # fill = "tozeroy",
                    )

        trace_phase_voltage = [trace_voltage1, trace_voltage2, trace_voltage3]

        graphs.append(html.Div(dcc.Graph(
                    id='voltage-per-phase',
                    animate=False,
                    figure={'data': trace_phase_voltage,
                            'layout' : go.Layout(xaxis= dict(autorange=True),
                                                yaxis=dict(autorange=True, title='Voltage (V)'),
                                                margin={'l':50,'r':1,'t':45,'b':50},
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

        return graphs

    except Exception as e:
        print(f"Error graph_update: {e}")





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
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand

    date_list = list(pd.date_range(start=start_date, end=datetime.datetime.now(), normalize=True))
    date_list.extend(['Last 24 Hour', 
        'Last 12 Hours', 
        'Last 6 Hours', 
        'Last 2 Hours', 
        'Last 1 Hour', 
        'Last 30 Minutes'])
    date_list.reverse()

    return html.Div(children=[
                html.Div([
                    html.Div([
                        html.Label('Plot Range:', className='column',
                            style={'color':'white', 'display':'inline-block', 'margin':'3', 'width':'150px'}),
                        dcc.Dropdown(
                            id='dropdown-history',
                            options=[{'label': x, 'value': x} for x in date_list],
                            value=date_list[0]
                        ),

                        html.Div(id='output-history', style={'color':'white', 'display':'none', 'margin':'3', 'width':'150px'}),
                        
                        ],className='row', style={'color':'white', 'display':'inline-block', 'margin':'3', 'width':'150px'}, 
                    ),
                    html.H1("Microgrid Status", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
                ], className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
                ),


                html.Div([
                     html.Div([
                        html.Label('Power Target:', className='column',
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
                            html.Label('Set Target:', className='column',
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
                        html.Label('Signal:', className='column',
                            style={'color':'white', 'display':'inline-block', 'margin':'3'}),
                        html.Div(id='cmd-signal', children=str(ldc_signal), className='row',
                            style={'font-size':'large', 'color':'white', 'text-align':'right', 'display':'inline-block', 'padding':'9', "position": "relative",}),
                        
                        ], 
                        className='column', style={'display':'inline-block'},
                    ),



                    html.Div([
                        html.Label('Algorithm:', className='column',
                            style={'color':'white', 'display':'inline-block', "position": "relative",}),
                        dcc.RadioItems(
                            id='cmd-algorithm',
                            options=[
                                        {"label": "No LDC", "value": 0},
                                        {"label": "With LDC", "value": 1},
                                        # {"label": "Advance LDC", "value": 2},
                                        # {"label": "Smart LDC", "value": 3},
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
                                        # value=gain,
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
                        # html.Label('Emergency load shedding:', className='column',
                        #         style={'text-align':'left', 'color':'white', 'display':'inline-block', 'margin':'0', "float": "left",}),
                            
                        html.Div([
                            html.Button('Drop!', id='btn_cmd_drop', n_clicks_timestamp=0, className='row', style={'text-align':'center', 'font-size':'large', 'border-radius':'30px'}), #, 'hover':{'background-color':'rgb(255,255,255)', 'color': 'rgb(255,0,0)'}}),
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

                ### hidden divs
                html.Div([
                    dcc.Interval(id='data-update', interval=refresh_rate),
                    html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0'}),
                    html.Div(children=html.Div(id='command'), style={'display': 'none'}),
                    html.Div(children=html.Div(id='output-gain'), style={'display': 'none'}),
                    html.Div(children=html.Div(id='output-freq'), style={'display': 'none'}),
                    html.Div(children=html.Div(id='output-freq2'), style={'display': 'none'}),

                    ], 
                    style={'display':'none'},
                ),
                ### actual graph
                html.Div([
                    html.Div(children=html.Div(id='graphs'), className='row'),
                ],
                className='col s12 m12 l7',
                style={'width':'80%', 'display':'inline-block', 'padding':'3px'},
                ),

            
                
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





def render_history():
    # render content for status tab
    global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
    date_list = list(pd.date_range(start=start_date, end=datetime.datetime.now(), normalize=True))
    date_list.reverse()    
    return html.Div(children=[
                html.Div([
                    html.Div([
                        html.Label('Plot Range:', className='column',
                            style={'color':'white', 'display':'inline-block', 'margin':'3', 'width':'150px'}),
                        dcc.Dropdown(
                            id='dropdown-history',
                            options=[{'label': x, 'value': x} for x in date_list],
                            value=date_list[0]
                        ),

                        html.Div(id='output-history', style={'color':'white', 'display':'none', 'margin':'3', 'width':'150px'}),
                        
                        ],className='row', style={'color':'white', 'display':'inline-block', 'margin':'3', 'width':'150px'}, 
                    ),
                    html.H1("Microgrid History", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
                ], className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
                ),


                ### hidden divs
                html.Div([
                    dcc.Interval(id='data-update', interval=refresh_rate),
                    html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0'}),
                    html.Div(children=html.Div(id='command'), style={'display': 'none'}),
                    html.Div(children=html.Div(id='output-gain'), style={'display': 'none'}),
                    html.Div(children=html.Div(id='output-freq'), style={'display': 'none'}),
                    html.Div(children=html.Div(id='output-freq2'), style={'display': 'none'}),

                    ], 
                    className='col s12 m12 l7',
                    style={'width':'80%', 'display':'inline-block', 'padding':'3px', 'display':'none'},
                ),
                ### actual graph
                html.Div([
                    html.Div(children=html.Div(id='graphs'), className='row'),
                ],
                className='col s12 m12 l7',
                style={'width':'100%', 'display':'inline-block', 'padding':'3px'},
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


if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0', port=15003)


# to run in gunicorn:
# gunicorn grid_server:server -b :15003
