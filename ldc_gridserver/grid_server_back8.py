##./grid_server.py
# -*- coding: utf-8 -*-
import flask
# import plotly.plotly as py
import math
import dash
from dash.dependencies import Output, Input
import dash_core_components as dcc
import dash_html_components as html

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
global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit
global ldc_signal, latest_demand, emergency, start_date, n_submit_input_cmd_loading



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



# def get_data(dict_msg={"algorithm":"basic_ldc", "target_watt":10, "frequency":810, 
#   "timescale":1, "duration":60*15, "unixstart":0, "unixend":0},
#   db_name='/home/pi/ldc_project/ldc_gridserver/ldc_agg_melted.db', 
#   duration=60*60*24, mcast_ip="224.0.2.3", mcast_port=16003, report=False,
#   params=["power_kw", "power_kw_1", "power_kw_2", "power_kw_3", 
#   "voltage_1", "voltage_2", "voltage_3", "frequency_1", "target_watt", "signal"]):
#   """ Fetch data from the local database"""
#   global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm
#   global cmd_loading, previous_limit, ldc_signal, latest_demand

#   start = int(dict_msg['unixstart'])
#   end = int(dict_msg['unixend'])
#   if start==0 and end==0:
#     end = time.time()
#     start = end - duration
#   else:
#     pass

#   con = lite.connect(db_name)
#   con.execute('pragma journal_mode=wal;')
#   cur = con.cursor()
#   while True:
#     try:
#       end = end + 1
#       start = start -1    
#       with con:
#         sql_cmd = "SELECT * FROM data WHERE unixtime BETWEEN {} AND {} ORDER BY unixtime ASC".format(start, end)
#         cur.execute(sql_cmd) 
#         data = np.array(cur.fetchall())
#         df_data = pd.DataFrame(data, columns=['unixtime', 'parameter','value'])

#       if len(df_data.index):
#         df_data = df_data[df_data['parameter'].isin(params)]
#         df_data['value'] = df_data['value'].values.astype(float)
#         df_data['unixtime'] = df_data['unixtime'].values.astype(float)
#         df_data = pd.pivot_table(data=df_data, values='value', index='unixtime', columns='parameter')
#         df_data.rename(columns={'target_watt':'target_kw'}, inplace=True)
#         print(df_data.columns)
#         return df_data
#       else:
#         print("Error in get_data: No data.")
#         raise Exception 
#     except Exception as e:
#       start = start - 5
#       end = end + 10
#       time.sleep(1e-6)
#       print("Error grid_server.get_data:{}".format(e))
#     except KeyboardInterrupt:
#       break


def get_data(dict_msg={"algorithm":"basic_ldc", "target_watt":10, "frequency":810, 
  "timescale":1, "duration":60*15, "unixstart":0, "unixend":0},
  db_name='/home/pi/ldc_project/ldc_gridserver/ldc_agg_melted.db', 
  duration=60*60*24, mcast_ip="224.0.2.3", mcast_port=16003, report=False,
  params=["power_kw", "power_kw_1", "power_kw_2", "power_kw_3", 
  "voltage_1", "voltage_2", "voltage_3", "frequency_1", "target_watt", "signal"]):
  """ Fetch data from the local database"""
  global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm
  global cmd_loading, previous_limit, ldc_signal, latest_demand


  try:
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    df_data = pd.read_feather(f'history/{today}.feather')
    df_data['target_kw'] = df_data['target_watt'] * 1e3
    return df_data
  except Exception as e:
    print(f"Error grid_server.get_data:{e}")
  else:
    pass

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




def send_command(dict_cmd, ip='localhost', port=10000):
  try:
    response = MULTICAST.send(dict_cmd, ip="224.0.2.3", port=16003, timeout=0.1)
    print('sent:', dict_cmd)
    print('confirmation:',response)
    return response
  except Exception as e:
    print("Error send_command:{}".format(e))
    return
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
n_submit_input_cmd_loading = 0
display_limit =True
emergency = False
dict_agg = {}
sd = datetime.datetime.fromtimestamp(get_start_date())
start_date = datetime.datetime(sd.year, sd.month, sd.day)

# date_list = list(pd.date_range(start=start_date, end=datetime.datetime.now(), normalize=True))
date_list = []
date_list.extend([
  'Last 2 Hours', 
  'Last 1 Hour', 
  'Last 30 Minutes',
  'Last 15 Minutes'])
# date_list.extend(['Last 15 Minutes'])
date_list.reverse()

refresh_rate = 3 * 1000  # [ms]

local_ip = get_local_ip()
tcp_ip = '192.168.1.3'
tcp_port = 10000
capacity = 30000  # [W]
dict_cmd = {}

try:
  dict_cmd = read_json('dict_cmd.txt')
  cmd_loading = float(dict_cmd['target_watt'])
  cmd_algorithm = dict_cmd['algorithm']
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
df_data = get_data(dict_msg={"algorithm":cmd_algorithm, "target_watt":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":0, "unixend":0})


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
  dash.dependencies.Output('input-cmd-target_watt', 'value'),
  [dash.dependencies.Input('btn_cmd_drop', 'n_clicks_timestamp')]
  )
def drop_load(n_clicks_timestamp):
  global cmd_loading
  try:
    cmd_loading = 1
    return 0.001
  except Exception as e:
    print(f"Error grid_server.drop_load:{e}")

@app.callback(
  dash.dependencies.Output('cmd-target_watt', 'children'),
  [
  dash.dependencies.Input('periodic-target-update', 'n_intervals'),
  dash.dependencies.Input('input-cmd-target_watt', 'n_submit'),
  # dash.dependencies.Input('input-cmd-target_watt', 'n_blur'),
  dash.dependencies.Input('cmd-algorithm','value'),
  dash.dependencies.Input('cmd-set-target','value'),
  dash.dependencies.Input('btn_cmd_drop', 'n_clicks_timestamp')
  ],
  [
  dash.dependencies.State('input-cmd-target_watt', 'value')
  ])
def update_loading(n_intervals, n_submit, algorithm, set_target, n_clicks_timestamp, target_watt):
  global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand, emergency, n_submit_input_cmd_loading
  try:
    cmd_algorithm = algorithm
    
    if (cmd_algorithm=='no_ldc') and (cmd_loading!=30000):
      cmd_loading = 30000
      msg = "s {}".format(cmd_loading)
      send_command(dict_cmd={"cmd":msg, "target_watt":cmd_loading, "set_target":set_target}, ip=tcp_ip, port=tcp_port)
      msg = "k {}".format(10000)
      send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
    
    elif (n_clicks_timestamp!=None) and ((time.time()-(n_clicks_timestamp*1e-3)) < 0.01) and (cmd_algorithm=='basic_ldc'): ## emergency drop
      # print(time.time()-n_clicks_timestamp, time.time(), n_clicks_timestamp*1e-3)
      frequency = 750
      ldc_signal = frequency
      emergency = True
      display_limit = True
      cmd_loading = 1
      msg = "s {}".format(cmd_loading)
      send_command(dict_cmd={"cmd":msg, "algorithm":cmd_algorithm, "set_target":set_target}, ip=tcp_ip, port=tcp_port)
      previous_limit = cmd_loading        
      msg = "k {}".format(10000)
      send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)

    elif (cmd_algorithm=='basic_ldc'):
      if n_submit==n_submit_input_cmd_loading:
        pass
      else:
        n_submit_input_cmd_loading = n_submit
        cmd_loading = target_watt * 1000
        msg = "s {}".format(cmd_loading)
        send_command(dict_cmd={"cmd":msg, "algorithm":cmd_algorithm, "set_target":set_target}, ip=tcp_ip, port=tcp_port)
        previous_limit = cmd_loading        
        msg = "k {}".format(gain)
        send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)

      display_limit = True
    elif (cmd_algorithm=='advanced_ldc'):
      response = send_command(dict_cmd={"algorithm":cmd_algorithm, "set_target":set_target}, ip=tcp_ip, port=tcp_port)
      cmd_loading = response["target_watt"]
      # msg = "s {}".format(cmd_loading)
      # send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
      # previous_limit = cmd_loading        
      # msg = "k {}".format(gain)
      # send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
    else:
      pass

    dict_cmd.update({"target_watt":str(cmd_loading), "set_target":set_target, "frequency":str(ldc_signal), "algorithm":str(cmd_algorithm)})
    save_json(dict_cmd, 'dict_cmd.txt')

    return np.round(float(cmd_loading)/1000, 3)

  except Exception as e:
    print("Error grid_server.update_loading:{}".format(e))


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
      cmd_loading = float(dict_cmd['target_watt'])
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
      dict_cmd.update({"gain":str(gain)})
      save_json(dict_cmd, 'dict_cmd.txt')
    return gain
  except Exception as e:
    print("Error grid_server.update_gain:",e)

  
  


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
    return frequency
  except Exception as e:
    print("Error grid_server.update_frequency:",e)
  
  



@app.callback(
  dash.dependencies.Output('cmd-signal', 'children'),
  [dash.dependencies.Input('input-cmd-target_watt', 'n_submit'),
  dash.dependencies.Input('input-cmd-target_watt', 'n_blur'),
  dash.dependencies.Input('data', 'children')
  ],
  [dash.dependencies.State('input-cmd-target_watt', 'value')],
  )
def update_signal(n_submit, n_blur, json_data, value):
  # change the frequency signal 
  global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
  df_data = pd.read_json(json_data, orient='split') 
  print(df_data)
  ldc_signal = df_data['signal'].values[-1]

  return np.round(ldc_signal, 2)

  

# @app.callback(
#         dash.dependencies.Output('command','children'),
#         [dash.dependencies.Input('cmd-algorithm','value')])
# def update_algorithm(value):
#     # change the command algorithm
#     global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
#     cmd_algorithm = value

#     if cmd_algorithm==0:
#         frequency = 850
#         ldc_signal = frequency
#         cmd_loading = 30000
#         display_limit = True
#         msg = "s {}".format(cmd_loading)
#         send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
#         msg = "k {}".format(10000)  # accelerate gain
#         send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
    
#     else:
#         dict_cmd = read_json('dict_cmd.txt')
#         cmd_loading = float(dict_cmd['target_watt'])
#         ### change target power setpoint at ldc injector
#         # print("Setpoint changed to ", str(cmd_loading), " kVA")
#         msg = "s {}".format(cmd_loading)
#         send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
#         msg = "k {}".format(gain)  # restor gain
#         send_command(dict_cmd={"cmd":msg}, ip=tcp_ip, port=tcp_port)
    
#         previous_limit = cmd_loading    

#     dict_cmd.update({"target_watt":str(cmd_loading), "algorithm":str(cmd_algorithm)})
#     save_json(dict_cmd, 'dict_cmd.txt')
  
  
#     display_limit = True
#     return cmd_algorithm


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


# @app.callback(
#     dash.dependencies.Output('data-update', 'n_intervals'),
#     [dash.dependencies.Input('dcc-holder', 'children')]
#     )
# def reset_dcc_data_update(dcc1):
#     return dcc1


# @app.callback(
#     dash.dependencies.Output('dcc-holder', 'children'),
#     [dash.dependencies.Input('data-update', 'n_intervals'),
#     dash.dependencies.Input('periodic-target-update', 'n_intervals')]
#     )
# def reset_dcc_target_update(dcc_data, dcc_target):
#     return 0


@app.callback(
  dash.dependencies.Output('data-update', 'interval'),
  [dash.dependencies.Input('dropdown-history', 'value')])
def update_history_range(value):
  # set history to put to graph
  global date_list, refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand, df_data
  history_range = value

  # update date_list
  # date_list = list(pd.date_range(start=start_date, end=datetime.datetime.now(), normalize=True))
  date_list = []
  date_list.extend([
    'Last 2 Hours', 
    'Last 1 Hour', 
    'Last 30 Minutes',
    'Last 15 Minutes'])
  # date_list.extend(['Last 15 Minutes'])
  date_list.reverse()

  if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
    refresh_rate = 3*1000  #[ms]
  else:
    refresh_rate = 60*1000 

  print("Range: {}   Refresh: {}".format(history_range, refresh_rate))
  
  
  dict_cmd.update({"history":history_range})
  save_json(dict_cmd, 'dict_cmd.txt')


  return refresh_rate




@app.callback(
  dash.dependencies.Output('data','children'),
  [
  # dash.dependencies.Input('cmd-algorithm','value'),
  # dash.dependencies.Input('cmd-target_watt','children'),
  dash.dependencies.Input('data-update','n_intervals'),
  dash.dependencies.Input('dropdown-history','value')
  ],
  [dash.dependencies.State('data', 'children'), 
  dash.dependencies.State('graphs','children')],)
def update_data(n_intervals, history_range, json_data, past_graph):
  global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
  try:
    # t = time.perf_counter()
    # if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
    #   if history_range.split()[2]=='Minutes':
    #     n_points = int(history_range.split()[1]) * 60 # number of seconds
    #   else:
    #     n_points = int(history_range.split()[1]) * 60 * 60 # number of seconds
    #   unixend = int(time.time())
    #   unixstart =  int(unixend - n_points)
    #   sample = '1S' #'{}S'.format(max([1,int(n_points/10000)]))
    # else:
    #   n_points = 60 * 60 * 24  # number of seconds
    #   dt_start = pd.to_datetime(history_range).tz_localize('Pacific/Auckland')
    #   dt_end = dt_start + datetime.timedelta(days=1)
    #   unixstart =  dt_start.timestamp()
    #   unixend = dt_end.timestamp()
    #   sample = '1S' # '{}S'.format(max([1,int(n_points/10000)]))

    # if json_data:
    #   df_data = pd.read_json(json_data, orient='split').astype(float)
    # else:
    #   df_data = get_data(dict_msg={"algorithm":cmd_algorithm, "target_watt":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":unixstart, "unixend":unixend}).reset_index()

    # ### get upperbound data
    # if unixend > df_data['unixtime'].max():
    #   s = df_data['unixtime'].max()
    #   e = unixend # np.min([unixend, s+900])
    #   new_data = get_data(dict_msg={"algorithm":cmd_algorithm, "target_watt":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":s, "unixend":e})
    #   df_data = pd.concat([df_data, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)
    
    # ### get lowerbound data
    # if unixstart < df_data['unixtime'].min():
    #   e = df_data['unixtime'].min()
    #   s = unixstart # np.max([unixstart, e-900])
    #   new_data = get_data(dict_msg={"algorithm":cmd_algorithm, "target_watt":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":s, "unixend":e})
    #   df_data = pd.concat([new_data.reset_index(), df_data], axis=0, sort='unixtime').reset_index(drop=True)
      
    # if len(df_data.index):
    #   df_data = df_data[((df_data['unixtime']>=unixstart)&(df_data['unixtime']<=unixend))]
    #   df_data = df_data.groupby('unixtime', as_index=True).mean().reset_index(drop=False)
    #   df_data.index = pd.to_datetime(df_data['unixtime'], unit='s')
    #   df_data = df_data.resample(sample).pad().reset_index(drop=True)
    #   ldc_signal = float(df_data.tail(1)['signal'])
      # print('update_data dt:', time.perf_counter()-t)
    #   return df_data.to_json(orient='split')
    # else:
    #   print("failed data fetch.")
    df_data = get_data()
    df_data.to_json(orient='split')
  except Exception as e:
    print(f'Error update_data: {e}')




@app.callback(
  dash.dependencies.Output('graphs','children'),
  [
  # dash.dependencies.Input('data-update','n_intervals'),
  dash.dependencies.Input('dropdown-history', 'value'),
  dash.dependencies.Input('data', 'children'),
  ],
  # [
  # dash.dependencies.State('data', 'children'),
  # dash.dependencies.State('graphs','children'),
  # ]
  )
def update_graph(history_range, json_data): 
  t = time.perf_counter() 
  global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand
  graphs = []
  try:
    t = time.perf_counter()
    if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
      if history_range.split()[2]=='Minutes':
        n_points = int(history_range.split()[1]) * 60 # number of seconds
      else:
        n_points = int(history_range.split()[1]) * 60 * 60 # number of seconds
      unixend = int(time.time())
      unixstart =  int(unixend - n_points)
      sample = '1S' #'{}S'.format(max([1,int(n_points/10000)]))
    else:
      n_points = 60 * 60 * 24  # number of seconds
      dt_start = pd.to_datetime(history_range).tz_localize('Pacific/Auckland')
      dt_end = dt_start + datetime.timedelta(days=1)
      unixstart =  dt_start.timestamp()
      unixend = dt_end.timestamp()
      sample = '1S' # '{}S'.format(max([1,int(n_points/10000)]))

    # try:
    #     dict_data = {}
    #     for k in past_graph:
    #         for d in k['props']['children']['props']['figure']['data']:
    #             dict_data.update({d['name']:d['y']})

    #     df_data = pd.DataFrame(data=dict_data)
    #     df_data['unixtime'] = pd.to_datetime(d['x']).astype(int) * 1e-9
      
    #     ### get upperbound data
    #     s = int(df_data.tail(1)['unixtime'])
    #     e = unixend
    #     new_data = get_data(dict_msg={"algorithm":cmd_algorithm, "target_watt":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":s, "unixend":e})
    #     df_data = pd.concat([df_data, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)
    #     t2 = len(new_data.index)
      
    #     # ### get lowerbound data
    #     if unixstart < int(df_data['unixtime'].values[0]):
    #         s = unixstart
    #         e = int(df_data['unixtime'].values[0])
    #         new_data = get_data(dict_msg={"algorithm":cmd_algorithm, "target_watt":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":unixstart, "unixend":unixend})
    #         df_data = pd.concat([new_data.reset_index(), df_data], axis=0, sort='unixtime').reset_index(drop=True)
    #         t1 = len(new_data.index)
    # except Exception as e:
    #     print("error past_graph:{}".format(e))

    if json_data:
      df_data = pd.read_json(json_data, orient='split')  
    else:
      df_data = get_data().reset_index()
      
    df_data = df_data[(df_data['unixtime'] >= unixstart) & (df_data['unixtime']<=unixend)]
    df_data.index = [pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').isoformat() for a in df_data['unixtime']]

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
          y = df_data["target_kw"].values * 0.001,
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


    trace_signal = go.Scattergl(
          x = df_data.index, 
          y = df_data["signal"].values, 
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


    ### PHASE POWER ###
    list_phase_power = [a for a in df_data.columns if a.lower().startswith('power_kw_')]
    traces_phase_power = []
    i = 0
    for p in list_phase_power:
      traces_phase_power.append(go.Scattergl(
          x = df_data.index,
          y = df_data[p],
          name = p,
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
                        yaxis=dict(autorange=True, title='Power (kW)'),
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
          name = p,
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
    # print("update_graph dt:", time.perf_counter() - t)
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
          html.H2("Localized Demand Control", 
            style={'marginTop':'5', 'marginLeft':'7', 'display':'inline-block', 'text-align':'center','float':'center', 'color':'white', "backgroundColor": "#18252E"}),
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
  global date_list, refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand

  

  return html.Div(children=[
        html.Div([
          html.H1("Microgrid Status", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
          ], className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
        ),

        html.Div([
            html.Div([
              html.Label('Plot Range:', 
                className='column', 
                style={'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
                ),
              dcc.Dropdown(
                id='dropdown-history',
                options=[{'label': x, 'value': x} for x in date_list],
                value=date_list[0],
                ),
              ],className='row', 
            ),
            html.Div([
              html.Label('Target:', 
                className='column', 
                style={'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
                ),
              html.Div(id='cmd-target_watt', 
                children=f'{np.round(float(cmd_loading)*1e-3, 3)} kW', 
                className='column', 
                style={'font-size':'xx-large', 'color':'white', 'text-align':'left', 'display':'inline-block',  "position": "relative"}
                ),
              dcc.Interval(id='periodic-target-update', interval=10*1000, n_intervals=0),
              ], className='row', 
            ),
            html.Div([
              html.Label('Signal:', 
                className='column',
                style={'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
                ),
              html.Div(id='cmd-signal', 
                children=f'{np.round(ldc_signal, 1)} Hz', 
                className='column',
                style={'font-size':'x-large', 'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
                ),
              ], className='row',
            ),
            html.Div('  ',
              className='column',
              style={'color':'white', 'marginTop':20, 'display':'inline-block', "position": "relative"}
            ),
            html.Div([
              html.Label('Algorithm:', 
                className='column',
                style={'color':'white', 'display':'inline-block', "position": "relative"}
                ),
              dcc.RadioItems(
                id='cmd-algorithm',
                options=[
                  {"label": "No LDC", "value": 'no_ldc'},
                  {"label": "Basic LDC", "value": 'basic_ldc'},
                  {"label": "Advanced LDC", "value": 'advanced_ldc'},
                  # {"label": "Smart LDC", "value": 'smart_ldc'},
                  {"label": "Ripple Control", "value": 'ripple_control'},
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
              html.Label('Set Target:', 
                className='column',
                style={'color':'white', 'display':'inline-block', "position": "relative"}
                ),
              dcc.RadioItems(
                id='cmd-set-target',
                options=[
                      {"label": "Auto", "value": 'auto'},
                      {"label": "Manual", "value": 'manual'},
                    ],
                value=dict_cmd["set_target"],
                className='column',
                style={'color':'white', 'margin':'3', "position": "relative",}
              ),
              dcc.Input(id='input-cmd-target_watt', 
                    value= np.round(float(cmd_loading)/1000, 3), # converted to kW
                    disabled=False, 
                    type='number', 
                    min=0, 
                    max= 30, # converted to kW
                    step=0.10, 
                    className='row',
                    style={'font-size':'large', 'text-align':'right', 'display':'inline-block', 'width':'100px', 'padding':'0', "position": "relative"}
              ),

              ], 
              className='row',
              style={'display':'inline-block', "position": "relative",}
            ),
            html.Div([
              html.Label('Set gain:', 
                className='column',
                style={'text-align':'left', 'color':'white', 'display':'inline-block', 'margin':'0', "float": "left"}
                ),
              dcc.Input(id='input-cmd-gain', 
                # value=gain,
                disabled=False, 
                type='number', 
                min=0, 
                max= 5000, 
                step=1, 
                className='row',
                style={'font-size':'large', 'text-align':'center', 'display':'inline-block', 'width':'100px', 'padding':'0', "position": "relative"}
                ),
              ], 
              className='column', 
              style={'text-align':'left', 'display':'inline-block', 'padding':'0', "float": "left"},
            ),

            html.Div([
              html.Label('Set signal:', 
                className='column',
                style={'text-align':'left', 'color':'white', 'display':'inline-block', 'margin':'0', "float": "left"}
                ),
              dcc.Input(id='input-cmd-freq', 
                # value=ldc_signal,
                disabled=False, 
                type='number', 
                min=0, 
                max= 5000, 
                step=1, 
                className='row',
                style={'font-size':'large', 'text-align':'center', 'display':'inline-block', 'width':'100px', 'padding':'0', "position": "relative"}
                ),
              ], 
              className='column', 
              style={'text-align':'left', 'display':'inline-block', 'padding':'0', "float": "left"},
            ),
            html.Div([
              html.Label('Emergency load shedding:', 
                className='column',
                style={'text-align':'left', 'color':'white', 'display':'inline-block', 'margin':'0', "float": "left"}
                ),
              html.Button('Shed!', 
                id='btn_cmd_drop', 
                n_clicks_timestamp=0, 
                className='row', 
                style={'text-align':'center', 'font-size':'large', 'border-radius':'30px', 'hover':{'background-color':'rgb(255,255,255)', 'color': 'rgb(255,0,0)'}}),
              ],
              className='column', 
            ),


          ], 
          # className='row', 
          # style={'color':'white', 'display':'inline-block', 'margin':'3', 'width':'150px'},
          className='row s12 m2 l2',
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
        dcc.Interval(id='data-update', interval=refresh_rate, n_intervals=1),
        html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0'}),
        html.Div(children=html.Div(id='output-gain'), style={'display': 'none'}),
        html.Div(children=html.Div(id='output-freq'), style={'display': 'none'}),
        html.Div(children=html.Div(id='output-freq2'), style={'display': 'none'}),
        # html.Div(children=html.Div(id='dcc-holder'), style={'display': 'none'}),
        ], 
        style={'display':'none'},
      ),


      ### actual graph
      html.Div([
        html.Div(children=html.Div(id='graphs'), className='row'),
        ], className='col s12 m12 l7',
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
  global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm, cmd_loading, previous_limit, ldc_signal, latest_demand, start_date
  date_list = pd.date_range(start=start_date, end=datetime.datetime.now(), normalize=True)
  date_list = [a.strftime('%Y-%m-%d') for a in date_list]
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

                html.Div([
           html.Div([
            html.Label('Power Target:', className='column',
              style={'color':'white', 'display':'inline-block', 'margin':'3'}),
            
            html.Div([
                html.Div(id='cmd-target_watt', children=np.round(float(cmd_loading)/1000, 3), className='row', 
                  style={'font-size':'xx-large', 'color':'white', 'text-align':'right', 'display':'inline-block', 'padding':'9', "position": "relative",}),
                html.Div(id='cmd-target_watt-unit', children='kW', className='row',
                  style={'font-size':'xx-large', 'color':'white', 'text-align':'left', 'display':'inline-block', 'padding':'9',"position": "relative",}),
              ], className='column', style={'display':'inline-block'}
            ),
            dcc.Interval(id='periodic-target-update', interval=30*1000),
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
                  dcc.Input(id='input-cmd-target_watt', 
                    value= np.round(float(cmd_loading)/1000, 3), # converted to kW
                    disabled=False, 
                    type='number', 
                    min=0, 
                    max= 30, # converted to kW
                    step=0.10, 
                    className='row',
                    style={'font-size':'large', 'text-align':'center', 'display':'inline-block', 'width':'100px', 'padding':'0', "position": "relative",}),

                  html.Div(id='cmd-target_watt-unit', children='kW', className='row',
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
                    {"label": "Auto Target", "value": 2},
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
        style = {"display":"none"},
        ),

        ### hidden divs
        html.Div([
          dcc.Interval(id='data-update', interval=refresh_rate),
          html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0'}),
          # html.Div(children=html.Div(id='command'), style={'display': 'none'}),
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
