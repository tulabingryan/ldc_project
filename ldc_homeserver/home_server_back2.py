##./home_server.py
# -*- coding: utf-8 -*-
import flask
import math
import dash
import dash_daq as daq
from dash.dependencies import Output, Input
import dash_core_components as dcc
import dash_html_components as html
import colorlover as cl
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

# multicasting packages
import socket
import struct
import sys
import time
import json
import ast

import socket

import MULTICAST

import plotly.express as px
# color_set = px.colors.qualitative.Set1
# color_set = px.colors.qualitative.Plotly
color_set = px.colors.qualitative.D3  # default for Dash
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
global device_names, df_data_cols, dict_cmd, cmd_algorithm, cmd_loading, ldc_signal, latest_demand
global local_ip, subnet, house_name, mcast_ip, mcast_port, df_data, dict_data, date_list

try:

  dict_data = {}

  date_list = []
  hist_files = glob.glob("history/*.feather")
  list_files = [x.split('/')[1] for x in hist_files]
  dates = [x.split('.')[0] for x in list_files]
  dates.sort()
  date_list.extend(dates)
  date_list.extend([
    'Last 2 Hours', 
    'Last 1 Hour', 
    'Last 30 Minutes',
    'Last 15 Minutes'])
  date_list.reverse()

  dict_cmd = read_json('/home/pi/ldc_project/ldc_simulator/dict_cmd.txt')
  print(dict_cmd)
  
  cmd_algorithm = dict_cmd['algorithm']
  ldc_signal = float(dict_cmd['frequency'])
  history_range = dict_cmd['history']
  gain = dict_cmd['gain']
except Exception as e:
  print("Error initial command:", e)


def read_csv(filename, failed=True):
  # Continually try reading csv until successful
  while True:
    try:
      df = pd.read_csv(filename)
      break
    except Exception as e:
      print("Error read_csv:", e)
  return df


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


list_colors = ["aliceblue", "antiquewhite", "aqua", "aquamarine", "azure",
    "beige", "bisque", "black", "blanchedalmond", "blue",
    "blueviolet", "brown", "burlywood", "cadetblue",
    "chartreuse", "chocolate", "coral", "cornflowerblue",
    "cornsilk", "crimson", "cyan", "darkblue", "darkcyan",
    "darkgoldenrod", "darkgray", "darkgrey", "darkgreen",
    "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange",
    "darkorchid", "darkred", "darksalmon", "darkseagreen",
    "darkslateblue", "darkslategray", "darkslategrey",
    "darkturquoise", "darkviolet", "deeppink", "deepskyblue",
    "dimgray", "dimgrey", "dodgerblue", "firebrick",
    "floralwhite", "forestgreen", "fuchsia", "gainsboro",
    "ghostwhite", "gold", "goldenrod", "gray", "grey", "green",
    "greenyellow", "honeydew", "hotpink", "indianred", "indigo",
    "ivory", "khaki", "lavender", "lavenderblush", "lawngreen",
    "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
    "lightgoldenrodyellow", "lightgray", "lightgrey",
    "lightgreen", "lightpink", "lightsalmon", "lightseagreen",
    "lightskyblue", "lightslategray", "lightslategrey",
    "lightsteelblue", "lightyellow", "lime", "limegreen",
    "linen", "magenta", "maroon", "mediumaquamarine",
    "mediumblue", "mediumorchid", "mediumpurple",
    "mediumseagreen", "mediumslateblue", "mediumspringgreen",
    "mediumturquoise", "mediumvioletred", "midnightblue",
    "mintcream", "mistyrose", "moccasin", "navajowhite", "navy",
    "oldlace", "olive", "olivedrab", "orange", "orangered",
    "orchid", "palegoldenrod", "palegreen", "paleturquoise",
    "palevioletred", "papayawhip", "peachpuff", "peru", "pink",
    "plum", "powderblue", "purple", "red", "rosybrown",
    "royalblue", "saddlebrown", "salmon", "sandybrown",
    "seagreen", "seashell", "sienna", "silver", "skyblue",
    "slateblue", "slategray", "slategrey", "snow", "springgreen",
    "steelblue", "tan", "teal", "thistle", "tomato", "turquoise",
    "violet", "wheat", "white", "whitesmoke", "yellow",
    "yellowgreen",
  ]

tabs_styles = {'height': '40px'}
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



### ancillary functions ###
def get_data(day, unixstart=None, unixend=None):
  """ Fetch data from the local database"""
  global subnet
  df_data = pd.DataFrame([])
  while len(df_data.index)<=0:
    try:
      df_data = pd.read_feather(f'/home/pi/studies/ardmore/homeserver/h{subnet}_{day}.feather')
    except Exception as e:
      # print(f"Error grid_server.get_data:{e}")
      pass
  if unixstart!=None:
    df_data = df_data[(df_data['unixtime']>=unixstart)&(df_data['unixtime']<=unixend)]
  float_cols = [x for x in df_data.columns if  not x.startswith('timezone')]
  df_data = df_data[float_cols].astype(float)
  return df_data





# def send_command(dict_cmd, ip='localhost', port=10000):
#     try:
#         # Create a TCP/IP socket
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#         # Connect the socket to the port where the server is listening
#         server_address = (ip, port)
#         sock.connect(server_address)
    
#         message_toSend = str(dict_cmd).encode()
#         # send message
#         sock.sendall(message_toSend)
    
#         # receive response
#         data = sock.recv(2**16)
#         received_msg = data.decode("utf-8")
#         dict_msg = ast.literal_eval(received_msg)
#         # print('received {!r}'.format(dict_msg))
        
#     except Exception as e:
#         dict_msg = {}

#     finally:
#         sock.close()

#     return dict_msg


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
      pass
  return local_ip


def create_shapePath(points):
    # declare path of the shape using the points
    path = 'M '
    for p in points:
      path = path+ '{} {} L '.format(str(p[0]), str(p[1]))
      
    path = path + ' Z' 
    return path

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



local_ip = get_local_ip()
subnet = int(local_ip.split('.')[2])
if subnet in [11,12,13,14,15]:
  pass
else:
  subnet = 12
# df_housespecs = read_csv('./houseSpecs.csv')
# house_name = df_housespecs.loc[subnet-1, 'name']
# mcast_ip = df_housespecs.loc[subnet-1, 'ip_local']
# mcast_port = df_housespecs.loc[subnet-1, 'port_local']



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






@app.callback(
  dash.dependencies.Output('dropdown-history', 'option'),
  [dash.dependencies.Input('periodic-target-update', 'n_intervals')],
  )
def update_history_option(n_intervals):
  # change the frequency signal 
  global date_list
  hist_files = glob.glob("history/*.feather")
  list_files = [x.split('/')[1] for x in hist_files]
  dates = [x.split('.')[0] for x in list_files]
  dates.sort()
  date_list = dates
  date_list.extend([
    # 'Last 2 Hours', 
    'Last 1 Hour', 
    # 'Last 30 Minutes',
    # 'Last 15 Minutes'
    ])
  date_list.reverse()
  return [{'label': x, 'value': x} for x in date_list]  

@app.callback(
  dash.dependencies.Output('data-update', 'interval'),
  [dash.dependencies.Input('dropdown-history', 'value')])
def update_refresh_rate(history_range):
  # set history to put to graph
  if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
    refresh_rate = 5*1000  #[ms]
  else:
    refresh_rate = 60*1000 
  print("Range: {}   Refresh: {}".format(history_range, refresh_rate))
  return refresh_rate



@app.callback(
  dash.dependencies.Output('hidden-data','children'),
  [dash.dependencies.Input('data-update','n_intervals'),
  dash.dependencies.Input('dropdown-history', 'value')],
  [dash.dependencies.State('hidden-data', 'children')],
  )
def update_data(n_intervals, history_range, json_data):
  # update the graph
  global cmd_algorithm, cmd_loading, ldc_signal, latest_demand
  if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
    day = datetime.datetime.now().strftime('%Y-%m-%d')
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


  if json_data:
    df_data = pd.read_json(json_data, orient='split').astype(float)
      ### get upperbound data
    if unixend > df_data['unixtime'].max():
      s = df_data['unixtime'].max()
      e = unixend # np.min([unixend, s+900])
      day = datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d')
      new_data = get_data(day=day, unixstart=unixstart, unixend=unixend)
      df_data = pd.concat([df_data, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)

    ### get lowerbound data
    if unixstart < df_data['unixtime'].min():
      e = df_data['unixtime'].min()
      s = unixstart # np.max([unixstart, e-900])
      day = datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d')
      new_data = get_data(day=day, unixstart=unixstart, unixend=unixend)
      df_data = pd.concat([new_data.reset_index(), df_data], axis=0, sort='unixtime').reset_index(drop=True)
    
  else:
    df_data = get_data(day=day, unixstart=unixstart, unixend=unixend).reset_index(drop=True)
  
    
  
  
  df_data = df_data.groupby('unixtime').mean().reset_index(drop=False)
  df_data.index = pd.to_datetime(df_data['unixtime'].values, unit='s')
  sample = '{}S'.format(max([1,int(n_points/3600)]))
  df_data = df_data.resample(sample).bfill().reset_index(drop=True)
  return  df_data.to_json(orient='split') # limit number of points to 1000 max




@app.callback(
  dash.dependencies.Output('graphs','children'),
  [dash.dependencies.Input('hidden-data', 'children')],
  )
def update_graph(json_data):  
  global device_names
  t = time.perf_counter()
  graphs = []
  traces_livability_temp = []
  traces_demand = []
  traces_status = []
  traces_temp_in = []
  traces_humidity = []

  
  if json_data:
    df_data = pd.read_json(json_data, orient='split')
    print(df_data[[x for x in df_data.columns if x.startswith('waterheater')]])
    # convert timezone from UTC to local timezone before graph
    df_data.index = pd.to_datetime(df_data['unixtime'].values, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland') #[pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').isoformat() for a in df_data['unixtime']]
    df_data.index = df_data.index.tz_localize(None)
    df_data['power_kw'] = df_data['power_active_0']
    # plot total house demand
    trace = go.Scattergl(
              x = df_data.index,
              y = df_data['power_kw'].values,
              name = 'power_kw',
              mode = 'lines',
              fill = "tozeroy",
              opacity=0.8,
              )
    trace_rolling_avg_60s = go.Scattergl(
                x = df_data.index, 
                y = df_data["power_kw"].rolling(60).mean(),
                name = 'rolling_avg_60s',
                line= {'color':'rgb(255,0,255)'},
                # opacity = 0.8,
                # fill = "tozeroy",
                )

    graphs.append(html.Div(dcc.Graph(
        id='total-house-demand',
        animate=False,
        figure={'data': [trace, trace_rolling_avg_60s],
                'layout' : go.Layout(xaxis= dict(autorange=True),
                            yaxis=dict(autorange=True, title='Power (kW)'),
                            margin={'l':50,'r':1,'t':45,'b':50},
                            title='Total House Demand',
                            showlegend=True,
                            autosize=True,
                            # height=400,
                            font=dict(color='#CCCCCC'),
                            titlefont=dict(color='#CCCCCC', size=14),
                            hovermode="closest",
                            plot_bgcolor="#020202", #"#191A1A",
                            paper_bgcolor="#18252E",
                            uirevision='same',
                            )}
        ), className='row'))

    list_priority = [a for a in df_data.columns if a.lower().endswith('priority')]
    list_priority.extend(['ldc_signal'])
    # print(df_data[list_priority])

    # plot individual device demand
    list_minus_wh = [a for a in df_data.columns if (a.lower().endswith('demand') and not (a.lower().startswith('waterheater')) and not (a.lower().startswith('heatpump')))] 
    # df_data['waterheater_actual_demand'] = np.roll(df_data['waterheater_actual_demand'].values, shift=0) * (((df_data['power_kw']>1.7)&(df_data[list_minus_wh].sum(axis=1)<1500))*1)
    list_params = [a for a in df_data.columns if a.lower().endswith('demand')]
    list_minus_hp = [a for a in df_data.columns if (a.lower().endswith('demand') and not (a.lower().startswith('heatpump')))]
    df_data['heatpump_actual_demand'] = np.clip(((df_data['power_kw'] * 1000) - np.roll(df_data[list_minus_hp].sum(axis=1), shift=0))-200, a_min=0, a_max=1000)
    
    
    # print(df_data[list_params].tail(1))

    for param in list_params:
      traces_demand.extend([
        go.Scattergl(
          x = df_data.index,
          y = df_data[param].values,
          name = param.split('_')[0],
          mode = 'lines',
          fill = "tozeroy",
          opacity=0.8,
          )
        ])
    graphs.append(html.Div(dcc.Graph(
        id='house-demand',
        animate=False,
        figure={'data': traces_demand,
                'layout' : go.Layout(xaxis= dict(autorange=True),
                            yaxis=dict(autorange=True, title='Power (W)'),
                            margin={'l':50,'r':1,'t':45,'b':50},
                            title='Devices Demand',
                            # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                            autosize=True,
                            # height=400,
                            font=dict(color='#CCCCCC'),
                            titlefont=dict(color='#CCCCCC', size=14),
                            hovermode="closest",
                            plot_bgcolor="#020202", #"#191A1A",
                            paper_bgcolor="#18252E",
                            uirevision='same',
                            )}
        ), className='row'))

    # plot temperatures
    list_params = [a for a in df_data.columns if a.lower().endswith('temperature')]
    if len(list_params):
      for param in list_params:
        traces_livability_temp.extend([
          go.Scattergl(
            x = df_data.index,
            y = df_data[param].values,
            name = param.split('_')[0],
            mode = 'lines',
            # fill = "tozeroy",
            # opacity=0.8,
            )
          ])
      graphs.append(html.Div(dcc.Graph(
          id='house-temperature',
          animate=False,
          figure={'data': traces_livability_temp,
                  'layout' : go.Layout(xaxis= dict(autorange=True),
                              yaxis=dict(autorange=True, title='Temperature (C)'),
                              margin={'l':50,'r':1,'t':45,'b':50},
                              title='Livability House Temperature',
                              # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                              autosize=True,
                              # height=400,
                              font=dict(color='#CCCCCC'),
                              titlefont=dict(color='#CCCCCC', size=14),
                              hovermode="closest",
                              plot_bgcolor="#020202", #"#191A1A",
                              paper_bgcolor="#18252E",
                              uirevision='same',
                              )}
          ), className='row'))

    # plot status
    list_params = [a for a in df_data.columns if ((a.lower().endswith('status')) and not (a.lower().startswith('window')) and not (a.lower().startswith('door')))]
    i = 0
    for param in list_params:
      traces_status.extend([
        go.Scattergl(
          x = df_data.index,
          y = df_data[param].values + i,
          name = param.split('_')[0],
          mode = 'lines',
          # fill = "tozeroy",
          opacity=1.0,
          )
        ])
      i = i + 2
    graphs.append(html.Div(dcc.Graph(
        id='device-status',
        animate=False,
        figure={'data': traces_status,
                'layout' : go.Layout(xaxis= dict(autorange=True),
                            yaxis=dict(autorange=True, title='Status (1=ON, 0=OFF)', 
                              tickvals=[x for x in range(20)], ticktext=['0' if x%2==0 else '1' for x in range(20)]),
                            margin={'l':50,'r':1,'t':45,'b':50},
                            title='Device Status',
                            # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                            autosize=True,
                            # height=400,
                            font=dict(color='#CCCCCC'),
                            titlefont=dict(color='#CCCCCC', size=14),
                            hovermode="closest",
                            plot_bgcolor="#020202", #"#191A1A",
                            paper_bgcolor="#18252E",
                            uirevision='same',
                            )}
        ), className='row'))

    # plot device temp_in
    list_params = [a for a in df_data.columns if a.lower().endswith('temp_in')]
    list_params.extend([a for a in df_data.columns if a.lower().endswith('target_temp')])
    
    if 'heatpump_temp_out' in df_data.columns: 
      list_params.extend(['heatpump_temp_out'])
    for param in list_params:
      traces_temp_in.extend([
        go.Scattergl(
          x = df_data.index,
          y = df_data[param].values,
          name = param.split('_')[0],
          mode = 'lines',
          # fill = "tozeroy",
          # opacity=0.8,
          )
        ])
    graphs.append(html.Div(dcc.Graph(
        id='device-temp',
        animate=False,
        figure={'data': traces_temp_in,
                'layout' : go.Layout(xaxis= dict(autorange=True),
                            yaxis=dict(autorange=True, title='Temperature (C)'),
                            margin={'l':50,'r':1,'t':45,'b':50},
                            title='Device Inside Temperature',
                            # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                            autosize=True,
                            # height=400,
                            font=dict(color='#CCCCCC'),
                            titlefont=dict(color='#CCCCCC', size=14),
                            hovermode="closest",
                            plot_bgcolor="#020202", #"#191A1A",
                            paper_bgcolor="#18252E",
                            uirevision='same',
                            )}
        ), className='row'))


    # plot device temp_target
    list_params = [a for a in df_data.columns if a.lower().endswith('temp_target')]
    # list_params.extend([a for a in df_data.columns if a.lower().endswith('target_temp')])
    traces_temp_target = []
    if 'heatpump_temp_out' in df_data.columns: 
      list_params.extend(['heatpump_temp_out'])
    for param in list_params:
      traces_temp_target.extend([
        go.Scattergl(
          x = df_data.index,
          y = df_data[param].values,
          name = param.split('_')[0],
          mode = 'lines',
          # fill = "tozeroy",
          # opacity=0.8,
          )
        ])
    graphs.append(html.Div(dcc.Graph(
        id='device-temp',
        animate=False,
        figure={'data': traces_temp_target,
                'layout' : go.Layout(xaxis= dict(autorange=True),
                            yaxis=dict(autorange=True, title='Temperature (C)'),
                            margin={'l':50,'r':1,'t':45,'b':50},
                            title='Device Target Temperature',
                            # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                            autosize=True,
                            # height=400,
                            font=dict(color='#CCCCCC'),
                            titlefont=dict(color='#CCCCCC', size=14),
                            hovermode="closest",
                            plot_bgcolor="#020202", #"#191A1A",
                            paper_bgcolor="#18252E",
                            uirevision='same',
                            )}
        ), className='row'))
  # print(f"update_graph dt:{time.perf_counter()-t}")
  return graphs





def serve_layout():
  return html.Div(
      [
        # header
        html.Div([
          dcc.Location(id='url', refresh=False),
          get_logo(),
          html.H2("Localized Demand Control", 
            style={'marginTop':'0', 'marginLeft':'20', 'display':'inline-block', 'text-align':'left','float':'center', 'color':'white', "backgroundColor": "#18252E"}),
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



def create_priorities_div(dict_items):
  list_div = []
  for k,v in dict_items.items():
    list_div.extend([
      html.Label(f'{v["name"]}:', 
        className='column', 
        style={'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
        ),
      dcc.Slider(
        id=f'priority-slider-{k}',
        min=0,
        max=100,
        step=1,
        value=v["priority"],
        className='column'
      )]
    )
  return list_div

@app.callback(
  dash.dependencies.Output('device-states','children'),
  [dash.dependencies.Input('hidden-data', 'children')],
  )
def create_states_div(json_data):
  if json_data:
    df_data = pd.read_json(json_data, orient='split')
  d=df_data.tail(1).round(3)
  
  dict_all_devices = {
    'baseload':{'name':'Baseload', 'priority':0},
    'waterheater':{'name':'Waterheater', 'priority':80}, 
    'heatpump':{'name':'Heat Pump', 'priority':60}, 
    'heater':{'name':'Space Heater', 'priority':70}, 
    'fridge':{'name':'Fridge', 'priority':50}, 
    'freezer':{'name':'Freezer', 'priority':40}, 
    'clotheswasher':{'name':'Washing Machine', 'priority':30}, 
    'clothesdryer':{'name': 'Dryer', 'priority':75}, 
    'dishwasher':{'name':'Dishwasher', 'priority':65},
    'valve0':{'name':'Hot Water Valve'},
    'signal':{'name':'LDC Signal'}}


  list_div = []
  list_div.extend([
        html.Label(f"Total Power: {np.round(d['power_active_0'].values[0], 3)} kW", 
          className='column', 
          style={'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
          ),
        html.Label(f"Power Factor: {np.round(d['powerfactor_0'].values[0], 3)} ", 
          className='column', 
          style={'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
          ),
        html.Label(f"Voltage: {np.round(d['voltage_0'].values[0], 2)} V", 
          className='column', 
          style={'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
          ),
        html.Div('  ',
          className='column',
          style={'color':'white', 'marginTop':10, 'display':'inline-block', "position": "relative"}
        ),
        ]
      )
  for k in dict_all_devices.keys():
    params = [x for x in d.columns if x.startswith(k)]
    if len(params)>0:
      list_div.extend([
        html.Label(f"{dict_all_devices[k]['name']}", 
          className='column', 
          style={'color':'white', 'text-align':'left', 'display':'inline-block', "position": "relative"}
          ),
        ]
      )
      for p in params:
        list_div.extend([
          html.Label(f"{' '.join([x.capitalize() for x in p.split('_')[1:]])}: {d[p].values[0]}", 
            className='column', 
            style={'color':'white', 'marginLeft':10, 'text-align':'left', 'display':'inline-block', "position": "relative"}
            ),
          ]
        )
    list_div.extend([
      html.Div('  ',
          className='column',
          style={'color':'white', 'marginTop':10, 'display':'inline-block', "position": "relative"}
        ),
      ])
  return list_div

def render_status():
  # render content for status tab
  global cmd_algorithm, cmd_loading, ldc_signal, date_list, dict_cmd
  date_list = []
  hist_files = glob.glob("history/*.feather")
  list_files = [x.split('/')[1] for x in hist_files]
  dates = [x.split('_')[-1].split('.')[0] for x in list_files]
  dates.sort()
  date_list.extend(dates)
  date_list.extend([
  #   'Last 2 Hours', 
    'Last 1 Hour', 
  #   'Last 30 Minutes',
    # 'Last 15 Minutes',
    ])
  date_list.reverse()
  dict_all_devices = {
    'waterheater':{'name':'Waterheater', 'priority':80}, 
    'heatpump':{'name':'Heat Pump', 'priority':60}, 
    'heater':{'name':'Space Heater', 'priority':70}, 
    'fridge':{'name':'Fridge', 'priority':50}, 
    'freezer':{'name':'Freezer', 'priority':40}, 
    'clotheswasher':{'name':'Washing Machine', 'priority':30}, 
    'clothesdryer':{'name': 'Dryer', 'priority':75}, 
    'dishwasher':{'name':'Dishwasher', 'priority':65}}

  while True:
    try:
      df_data = get_data(day=dates[-1])
      break
    except:
      pass
  list_devices = [x.split('_')[0] for x in df_data.columns]
  dict_items = {}
  for k in dict_all_devices.keys():
    if k in list_devices:
      dict_items.update({k:{'name':dict_all_devices[k]['name'], 'priority':100-float(df_data.tail(1)[f'{k}_priority'])}})
  priority_div = create_priorities_div(dict_items)

  return html.Div(children=[
        # html.Div([
        #   html.H1(" ", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
        #   ], className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E"}
        # ),

        html.Div([
          html.H1("Home Status", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
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
            html.Div('  ',
              className='column',
              style={'color':'white', 'marginTop':20, 'display':'inline-block', "position": "relative"}
            ),

            html.Div([
              html.Label('Set Priorities', 
                className='column', 
                style={'color':'white', 'font-size':'large', 'text-align':'center', 'display':'inline-block', "position": "relative"}
                ),

              html.Div(children=priority_div, 
                className='column'
                ),
              ]
            ),
            
            html.Div([
              html.Label('Device State', 
                className='column', 
                style={'color':'white', 'font-size':'large', 'text-align':'center', 'display':'inline-block', "position": "relative"}
                ),
              html.Div('  ',
                className='column',
                style={'color':'white', 'marginTop':10, 'display':'inline-block', "position": "relative"}
              ),
              html.Div(children=html.Div(id='device-states'), className='row',),
              ],
              className='column',
              style={'color':'white', 'marginTop':20, 'display':'inline-block', "position": "relative"}
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


        html.Div(
          html.Div(children=html.Div(id='graphs'), className='row',),
          className='col s12 m12 l7',
          style={'width':'80%', 'display':'inline-block', 'padding':'3px'},
        ),


        # hidden div: holder of data
        html.Div([
          html.Div(children=html.Div(id='hidden-data'), className='row', style={'opacity':'1.0', 'display':'none'}),
          dcc.Interval(id='data-update', interval=3*1000),
          ], className='row', style={'display':'none',},
        ),
        
        
      
      ],
      style={'display':'inline-block', "backgroundColor": "#18252E", "width":"100%"} 
      
    )


'''
NOTE: properties for dcc.Input
n_submit, The number of times enter was pressed when the component had focus.
n_submit_timestamp The last timestamp enter was pressed.
n_blur, The number of times the component lost focus.
n_blur_timestamp, The last time the component lost focus.
'''


def render_settings():
  # render content for settings tab
  return html.Div(children=[
        html.Div([
          html.H1("Settings", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
          ], 
          className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
        ),
        
        html.Div([
          
          ], 
          className='col s12 m2 l1',
          style={'display': 'inline-block', 'padding':'3', 'float':'left'}
        ),
        
        # hidden div: holder of data
        html.Div([
          
          ], 
          className='row', 
          style={'display':'none',},
        ),
        

        html.Div([
          ], 
          className='col s12 m12 l7',
          style={'width':'80%', 'display':'inline-block', 'padding':'3px'},
        ),
      
      ],

      style={'display':'inline-block', "backgroundColor": "#18252E", 'width':'100%'} 
      
    )


def render_history():
  # render content for history tab
  return html.Div(children=[
        html.Div([
          html.H1("History", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
          ], 
          className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
        ),
        
        html.Div([
          
          ], 
          className='col s12 m2 l1',
          style={'display': 'inline-block', 'padding':'3', 'float':'left'}
        ),
        
        # hidden div: holder of data
        html.Div([
          
          ], 
          className='row', 
          style={'display':'none',},
        ),
        

        html.Div([
          ], 
          className='col s12 m12 l7',
          style={'width':'80%', 'display':'inline-block', 'padding':'3px'},
        ),
      
      ],

      style={'display':'inline-block', "backgroundColor": "#18252E", 'width':'100%'} 
      
    )



app.layout = serve_layout()




@app.callback(Output("tab_content", "children"), [Input("tabs", "value")])
def render_content(tab):
  if tab == "status_tab":
    return render_status()
  elif tab == "settings_tab":
    return render_settings()
  elif tab == "history_tab":
    return render_history()
  else:
    return render_status()


# external_css = [
#     "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",
#     "https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css",
#     "https://cdn.rawgit.com/amadoukane96/d930d574267b409a1357ea7367ac1dfc/raw/1108ce95d725c636e8f75e1db6e61365c6e74c8a/web_trader.css",
#     "https://use.fontawesome.com/releases/v5.2.0/css/all.css"
# ]

# for css in external_css:
#     app.css.append_css({"external_url": css})

# if 'DYNO' in os.environ:
#     app.scripts.append_script({
#         'external_url': 'https://cdn.rawgit.com/chriddyp/ca0d8f02a1659981a0ea7f013a378bbd/raw/e79f3f789517deec58f41251f7dbb6bee72c44ab/plotly_ga.js'
#     })



if __name__ == "__main__":
  app.run_server(debug=True, host='0.0.0.0', port=21003)