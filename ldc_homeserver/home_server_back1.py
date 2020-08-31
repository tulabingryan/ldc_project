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
import os
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




### GLOBAL VARIABLES ###
global device_names, df_data_cols, dict_cmd, cmd_algorithm, cmd_loading, ldc_signal, latest_demand
global local_ip, subnet, house_name, mcast_ip, mcast_port, df_data, dict_data

dict_data = {}


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



# def get_data(dict_msg={"algorithm":1, "loading":10, "frequency":810, 
#     "timescale":1, "duration":60*15, "unixstart":0, "unixend":0},
#     db_name='/home/pi/ldc_project/ldc_homeserver/homedata.db', 
#     duration=60*60*24, mcast_ip="224.0.2.3", mcast_port=17000, report=False,
#     params=["power_kw_0", "voltage_0", "frequency_0", "loading", "signal"]):
#     """ Fetch data from the local database"""
#     global refresh_rate, gain, dict_cmd, dict_agg, cmd_algorithm
#     global cmd_loading, previous_limit, ldc_signal, latest_demand

#     start = int(dict_msg['unixstart'])
#     end = int(dict_msg['unixend'])
#     if start==0 and end==0:
#         end = time.time()
#         start = end - duration
#     con = lite.connect(db_name)
#     con.execute('pragma journal_mode=wal;')
#     cur = con.cursor()          
#     while True:
#         try:
#           t = time.perf_counter()
#           end = end + 1
          
#           with con:
#               cur.execute("SELECT * FROM data WHERE unixtime BETWEEN {} AND {} ORDER BY unixtime ASC".format(start, end)) 
#               data = np.array(cur.fetchall())
#               print(time.perf_counter() - t)
#               df_data = pd.DataFrame(data, columns=['unixtime','group','parameter','value'])
              
#           if len(df_data.index):
#               # return only data specified by params
#               # df_data = df_data[df_data['parameter'].isin(params)]
#               df_data['value'] = df_data['value'].values.astype(float)
#               df_data['unixtime'] = df_data['unixtime'].values.astype(float)
#               df_data = pd.pivot_table(data=df_data, values='value', index='unixtime', columns='parameter')
#               df_data.reset_index(drop=False, inplace=True)
#               df_data = df_data.ffill()
#               df_data = df_data.bfill()
#               return df_data

#           else:
#               print("Error in get_data: No data.")
#               raise Exception            
          
#         except KeyboardInterrupt:
#             break
            
#         except Exception as e:
#             ### adjust date bounderies to fetch
#             start = start - 5
#             end = end + 10
#             time.sleep(1e-6)
#             print("Error grid_server.get_data:{}".format(e))
            

def get_data(day, unixstart=None, unixend=None):
  """ Fetch data from the local database"""
  global subnet
  df_data = pd.DataFrame([])
  while len(df_data.index)<=0:
    try:
      df_data = pd.read_feather(f'history/h{subnet}_{day}.feather')
    except Exception as e:
      # print(f"Error grid_server.get_data:{e}")
      pass
  if unixstart!=None:
    df_data = df_data[(df_data['unixtime']>=unixstart)&(df_data['unixtime']<=unixend)]
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



local_ip = get_local_ip()
subnet = int(local_ip.split('.')[2])
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









# @app.callback(
#   dash.dependencies.Output('hiddend-counter', 'chil')
#   )

@app.callback(
  dash.dependencies.Output('hidden-data','children'),
  [dash.dependencies.Input('data-update','n_intervals')],
  [dash.dependencies.State('hidden-data', 'children')],
  )
def update_data(n_intervals, json_data):
  # update the graph
  global cmd_algorithm, cmd_loading, ldc_signal, latest_demand
  print("update_data", n_intervals)
  n_points = 3600*3
  unixend = int(time.time())
  unixstart =  int(unixend - n_points)
  if json_data:
    df_data = pd.read_json(json_data, orient='split').astype(float)
    ### get upperbound data
    s = int(df_data.tail(1)['unixtime'])
    e = unixend
    new_data = get_data(dict_msg={"unixstart":s, "unixend":e, "duration":n_points})
    df_data = pd.concat([df_data, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)
    # ### get lowerbound data
    if unixstart < min(df_data['unixtime'].values):
        e = int(df_data['unixtime'].values[0])
        s = max([unixstart, e-1000])
        new_data = get_data(dict_msg={"unixstart":s, "unixend":e, "duration":n_points})
        df_data = pd.concat([new_data.reset_index(), df_data], axis=0, sort='unixtime').reset_index(drop=True)
  else:
    # get new data 
    df_data = get_data(dict_msg={"duration":n_points, "unixstart":unixstart, "unixend":unixend})
 
  df_data = df_data.groupby('unixtime', as_index=True).mean().reset_index(drop=False)
  df_data = df_data.ffill()
  df_data = df_data.bfill()
  return  df_data.tail(n_points).to_json(orient='split') # limit number of points to 1000 max




@app.callback(
  dash.dependencies.Output('graphs','children'),
  [dash.dependencies.Input('hidden-data', 'children')],
  )
def update_graph(json_data):  
  global device_names
  graphs = []
  traces_livability_temp = []
  traces_demand = []
  traces_status = []
  traces_temp_in = []
  traces_humidity = []

  print("update_graph")
  if json_data:
    df_data = pd.read_json(json_data, orient='split')

    # convert timezone from UTC to local timezone before graph
    df_data.index = pd.to_datetime(df_data['unixtime'], unit='s')
    df_data.index = df_data.index.tz_localize('UTC').tz_convert('Pacific/Auckland')
    # df_data = df_data.resample('1S').pad()
    df_data.index = [a.isoformat() for a in df_data.index]
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
    df_data['waterheater_actual_demand'] = np.roll(df_data['waterheater_actual_demand'].values, shift=3) * (((df_data['power_kw']>1.7)&(df_data[list_minus_wh].sum(axis=1)<1500))*1)
    list_params = [a for a in df_data.columns if a.lower().endswith('demand')]
    list_minus_hp = [a for a in df_data.columns if (a.lower().endswith('demand') and not (a.lower().startswith('heatpump')))]
    df_data['heatpump_actual_demand'] = np.clip(((df_data['power_kw'] * 1000) - np.roll(df_data[list_minus_hp].sum(axis=1), shift=0)), a_min=0, a_max=999999)
    
    
    print(df_data[list_params])

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
                            yaxis=dict(autorange=True, title='Status (1=ON, 0=OFF)'),
                            margin={'l':50,'r':1,'t':45,'b':50},
                            title='Device Status',
                            # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                            autosize=True,
                            # height=300,
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
          name = param,
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
                            # height=300,
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
          name = param,
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
                            title='Device Inside Temperature',
                            # legend=dict(font=dict(size=10), orientation='h', x=0.85, y=1.15),
                            autosize=True,
                            # height=300,
                            font=dict(color='#CCCCCC'),
                            titlefont=dict(color='#CCCCCC', size=14),
                            hovermode="closest",
                            plot_bgcolor="#020202", #"#191A1A",
                            paper_bgcolor="#18252E",
                            uirevision='same',
                            )}
        ), className='row'))

    
    
  #   # add space after one graph layout
  #   # graphs.append(html.H2('', className='row', style={'display':'inline-block', 'position':'relative', "border": "1px solid", "borderColor": "rgba(68,149,209,.9)"}))


  #   # plot demands of individual devices
  #   device_names = np.unique(df_data['id'])
  #   trace_devices = []
  #   today = datetime.datetime.today()
  #   tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)
  #   dict_status = {1:'ON', 0:'OFF'}
  #   count = 0
  #   for name in device_names:
  #     count += 1
  #     df = df_data[(df_data['id']==name)].reset_index(drop=True)
  #     idx = len(df.index) - 1
  #     d_type = df.loc[idx,'type']
  #     d_status = int(df.loc[idx,'a_status'])
  #     d_limit = float(df.loc[idx, 'limit'])
      
  #     d_signal = np.round(float(df.loc[idx,'signal']), 2)
  #     d_priority = int(np.round(float(df.loc[idx,'priority']),0))
  #     d_flexibility = np.round(float(df.loc[idx,'flexibility']), 2)
  #     d_soc = np.round(float(df.loc[idx,'soc']), 2)

  #     if d_type in ['dishwasher', 'clothesdryer', 'clotheswasher', 'ev']:
  #       display_sched = 'inline-block'
  #       start_sched = df.loc[idx, 'start']
  #       end_sched = df.loc[idx, 'end']
  #     else:
  #       display_sched = 'none'
  #       start_sched = 'none'
  #       end_sched = 'none'

  #     if d_type in ['hvac', 'waterheater', 'fridge', 'freezer']:
  #       d_temp_in = np.round(float(df.loc[idx, 'temp_in']), 2)
  #       d_temp_out = np.round(float(df.loc[idx, 'temp_out']), 2)
  #       d_heating_sp = np.round(float(df.loc[idx, 'heating_sp']), 2)
  #       d_cooling_sp = np.round(float(df.loc[idx, 'cooling_sp']), 2)
  #       d_tolerance = np.round(float(df.loc[idx, 'tolerance']), 2)
  #       d_temp_min = np.round(float(df.loc[idx, 'temp_min']), 2)
  #       d_temp_max = np.round(float(df.loc[idx, 'temp_max']), 2)

  #     else:
  #       d_temp_in = 'none'
  #       d_temp_out = 'none'
  #       d_heating_sp = 'none'
  #       d_cooling_sp = 'none'
  #       d_tolerance = 'none'
  #       d_temp_min = 'none'
  #       d_temp_max = 'none'
        
      
  #     if d_type in ['hvac']:    
  #       display_heating = 'inline-block'
  #       display_cooling = 'inline-block'
  #       display_tolerance = 'inline-block'
  #       display_temp = 'inline-block'
        
  #     elif d_type in ['waterheater']:
  #       display_heating = 'inline-block'
  #       display_cooling = 'none'
  #       display_tolerance = 'inline-block'
  #       display_temp = 'inline-block'
  #     elif d_type in ['fridge' , 'freezer']:
  #       display_heating = 'none'
  #       display_cooling = 'inline-block'
  #       display_tolerance = 'inline-block'
  #       display_temp = 'inline-block'
        
  #     else:
  #       display_heating = 'none'
  #       display_cooling = 'none'
  #       display_tolerance = 'none'
  #       display_temp = 'none'
        

  #     if d_type in ['baseload']:
  #       display_status = 'none'
  #     else:
  #       display_status = 'inline-block'




  #     trace1 = go.Scattergl(
  #       x = df['localtime'].values,
  #       y = df['a_demand'].values,
  #       name = 'demand',#name+'_'+d_type,
  #       mode = 'lines',
  #       fill = "tozeroy",
  #       line= {'color':'rgb(0,255,0)'},
  #       )

  #     trace2 = go.Scattergl(
  #       x = df['localtime'].values,
  #       y = df['temp_in'].values,
  #       name = 'temperature',
  #       mode = 'lines',
  #       yaxis= 'y2',
  #       line= {'color':'rgb(255,0,0)'},
  #       )

  #     if display_temp=='inline-block':
  #       traces = [trace1, trace2]
  #     else:
  #       traces = [trace1]

  #     graphs.append(
  #       html.Div([
  #         html.Div([
  #           html.Div([
  #             html.Div(id='label-status-'+name, children='State:', 
  #               className='column', style={'font-size':'large', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
              
  #             html.Div(id='device-type-'+name, children='Type : ' + dict_devices[d_type], 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':'inline-block', 'padding':'3', "position": "relative"}),
  #             html.Div(id='device-id-'+name, children='ID : ' + name, 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':'inline-block', 'padding':'3', "position": "relative"}),
              
  #             # status and priority
  #             html.Div(id='device-status-'+name, children='Status: ' + dict_status[d_status], 
  #                 className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
  #             html.Div(id='device-priority-'+name, children='Priority:  ' + str(d_priority), 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
  #             html.Div(id='device-flexibility-'+name, children='Flexibility:  ' + str(d_flexibility), 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
  #             html.Div(id='device-soc-'+name, children='SOC:  ' + str(d_soc), 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
  #             html.Div(id='device-limit-'+name, children='limit:  ' + str(d_limit), 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':'inline-block', 'padding':'3', "position": "relative"}),
              
  #             # temperatures
  #             html.Div(id='temp-in-'+name, children='Temp In: ' + str(d_temp_in) + ' °C', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_temp, 'padding':'3', "position": "relative"}),
  #             html.Div(id='temp-out-'+name, children='Temp Out: ' + str(d_temp_out) + ' °C', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_temp, 'padding':'3', "position": "relative"}),
  #             html.Div(id='sp-heating-'+name, children='Heating SP: ' + str(d_heating_sp) + ' °C', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_heating, 'padding':'3', "position": "relative"}),
  #             html.Div(id='sp-cooling-'+name, children='Cooling SP: ' + str(d_cooling_sp) + ' °C', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_cooling, 'padding':'3', "position": "relative"}),
  #             html.Div(id='sp-tolerance-'+name, children='Tolerance: ' + str(d_tolerance) + ' °C', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_tolerance, 'padding':'3', "position": "relative"}),
  #             html.Div(id='temp-min-'+name, children='Temp Min: ' + str(d_temp_min) + ' °C', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_tolerance, 'padding':'3', "position": "relative"}),
  #             html.Div(id='temp-max-'+name, children='Temp Max: ' + str(d_temp_max) + ' °C', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_tolerance, 'padding':'3', "position": "relative"}),
              
  #             # # schedules
  #             # html.Div(id='device-start-'+name, children='Start:  ' + start_sched, 
  #             #     className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_sched, 'padding':'3', "position": "relative"}),
  #             # html.Div(id='device-end-'+name, children='End:  '+end_sched, 
  #             #     className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_sched, 'padding':'3', "position": "relative"}),
              
  #             # # ldc signal
  #             # html.Div(id='device-signal-'+name, children='LDC Signal : ' + str(d_signal), 
  #             #     className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
              


  #             ], 
  #             className='column', style={'display':'inline-block', 'padding':'5', "position": "relative"},
  #           ),

  #           html.Div([
              
  #             ], className='column', style={'display':'inline-block', 'padding':'5', "position": "relative"},
  #           ),
  #           ],className='column', style={'display':'inline-block', 'width':'15%', 'position':'relative', "border": "none", "borderColor": "rgba(68,149,209,.9)"},  # 
  #         ),

  #         html.Div([
  #           dcc.Graph(
  #               id='device-graph-' + name,
  #               animate=False,
  #               figure={'data': traces,
  #                   'layout' : go.Layout(xaxis= dict(autorange=True,),
  #                             yaxis=dict(range=dict_power_range[d_type], 
  #                               title='Power (W)',
  #                               titlefont=dict(color='#CCCCCC', size=14),
  #                               tickfont=dict(color='#CCCCCC', size=14),
  #                               # hoverformat='closest',
  #                             ),
  #                             yaxis2=dict(range=dict_temp_range[d_type], 
  #                               title='Temperature (C)', 
  #                               side='right', 
  #                               titlefont=dict(color='rgb(255,0,0)'),
  #                               tickfont=dict(color='rgb(255,0,0)'),
  #                               # hoverformat='closest',
  #                               # anchor='free',
  #                               # overlaying='y',
  #                               # position=1,
  #                             ),
  #                             margin={'l':50,'r':50,'t':50,'b':100},
  #                             title='Power Demand: '+dict_devices[d_type]+' '+name,
  #                             autosize=True,
  #                             font=dict(color='#CCCCCC'),
  #                             titlefont=dict(color='#CCCCCC', size=14),
  #                             # height=500,
  #                             # hovermode="closest",
  #                             plot_bgcolor="#020202", #"#191A1A",
  #                             paper_bgcolor="#18252E",
  #                             legend=dict(font=dict(size=10), orientation='h', x=0.0, y=1.1),
  #                             )}
  #               ),
              
  #           ],
  #           className='column',
  #           style={'display':'inline-block', 'width':'70%', 'padding':'10', 'position':'relative'}  # , "border": "1px solid", "borderColor": "rgba(68,149,209,.9)"
  #         ),

  #         html.Div([
  #             html.Div(id='label-settings-'+name, children='\n', 
  #               className='column', style={'font-size':'large', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'10', "position": "relative"}),
  #             # status
  #             # html.Div(id='device-status-settings'+name, children='Status: ', 
  #             #         className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
  #             html.Div([
                  

  #                 daq.ToggleSwitch(
  #                   id='daq-light-dark-theme',
  #                   label=['OFF', 'ON'],
  #                   style={'width': '150px', 'margin': 'auto', 'color':'white'}, 
  #                   value=d_status,
  #                   labelPosition='top',
  #                   theme='dark',
  #                   color='orange',
  #                 ),

                  
  #                 # dcc.RadioItems(
  #                 #     options=[
  #                 #         {'label': 'ON', 'value': 1},
  #                 #         {'label': 'OFF', 'value': 0},
  #                 #     ],
  #                 #     value=d_status,
  #                 #     labelStyle={'color':'white'},
  #                 # ),
  #                 # dcc.Slider(min=0, max=1, step=1, 
  #                 #     marks={0: 'OFF', 1: 'ON'}, 
  #                 #     value= d_status, 
  #                 #     vertical=False, 
  #                 #     updatemode='drag',
  #                 # ),
  #               ], className='column', style={'display':display_status, 'padding':'10', 'width':'100', 'padding':'10','float':'center', 'font-color':'white'},  # "border": "1px solid", "borderColor": "rgba(68,149,209,.9)"
  #             ),

  #             # priority
  #             # html.Div(id='device-priority-settings-'+name, children='Priority: ', 
  #             #     className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
  #             # html.Div([
  #             #         dcc.Dropdown(id='dropdown-priority',
  #             #             options=[{'label':str(x), 'value':x} for x in range(0,11)],
  #             #             value=d_priority,                                    
  #             #         ),
  #             #     ], className='column', style={'width':'100%', 'padding':'3', 'display':display_status},
  #             # ),

              
                
  #             # schedules
  #             html.Div(id='device-start-settings-'+name, children='Start:  ', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_sched, 'padding':'3', "position": "relative"}),
  #             html.Div([
  #                 # dcc.DatePickerSingle(
  #                 #     id='my-date-picker-start-' + name,
  #                 #     min_date_allowed=datetime.datetime.now(),
  #                 #     max_date_allowed=datetime.datetime.now() + datetime.timedelta(days=360),
  #                 #     initial_visible_month=datetime.datetime.now(),
  #                 #     # date=datetime.datetime.now()
  #                 # ),
  #                 dcc.Dropdown(id='dropdown-start',
  #                   options=[{'label':datetime.datetime.strftime(x,'%Y-%m-%d %H:%M'), 'value':datetime.datetime.strftime(x,'%Y-%m-%d %H:%M')} for x in pd.date_range(start=today, end=tomorrow, freq='30min')],
                                      
  #                 ),
  #               ], className='column', style={'width':'100%', 'padding':'3', 'display':display_sched},
  #             ),
              

  #             html.Div(id='device-end-'+name, children='End:  ', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_sched, 'padding':'3', "position": "relative"}),
  #             html.Div([
  #                 # dcc.DatePickerSingle(
  #                 #     id='my-date-picker-end-' + name,
  #                 #     min_date_allowed=datetime.datetime.now(),
  #                 #     max_date_allowed=datetime.datetime.now() + datetime.timedelta(days=360),
  #                 #     initial_visible_month=datetime.datetime.now(),
  #                 #     # date=datetime.datetime.now() + datetime.timedelta(days=1),
  #                 # ),
  #                 dcc.Dropdown(id='dropdown-start',
  #                   options=[{'label':datetime.datetime.strftime(x,'%Y-%m-%d %H:%M'), 'value':datetime.datetime.strftime(x,'%Y-%m-%d %H:%M')} for x in pd.date_range(start=today, end=tomorrow, freq='30min')],
                                      
  #                 ),
  #               ], className='column', style={'width':'100%', 'padding':'3', 'display':display_sched},
  #             ),

  #             html.Div(id='device-mode-settings-'+name, children='\n\n ', 
  #               className='column', style={'font-size':'small', 'color':'white', 'text-align':'left', 'display':display_status, 'padding':'3', "position": "relative"}),
  #             html.Div([
  #               daq.PowerButton(
  #                   id='my-daq-powerbutton',
  #                   on=True,
  #                   color='red',
  #                   label='Auto',
  #                   labelPosition='bottom',
  #                   style={'color':'white','margin': 'auto'},
  #                   theme='dark',
  #                 ) ,

                  
  #               ], className='column', style={'width':'100%', 'padding':'10', 'display':display_status},
  #             ),



                    
  #           ], className='column', style={'display':'inline-block', 'width':'10%', "position": "relative", "border": "none", "borderColor": "rgba(68,149,209,.9)"},
  #         ),
          
  #         ],
  #         className='eleven columns',
  #         style={'display':'inline-block', 'position':'relative', "border": "1px solid", "borderColor": "rgba(68,149,209,.9)"}  #  
  #       )
  #     )
    
  #     # add space after one graph layout
  #     # graphs.append(html.Div('', className='row',style={'display':'inline-block', 'position':'relative', "border": "1px solid", "borderColor": "rgba(68,149,209,.9)"}))



  return graphs



# def render_controller():
#     global df_data
#     user_commands = []


#     device_names = np.unique(df_data['id'])
#     for name in device_names:
#         df = df_data[(df_data['id']==name)].reset_index(drop=True)
#         d_type = df.loc[0,'type']
#         user_commands.append(
#             html.Div(
#                 html.Label(name+'_'+d_type, className='column', style={'color':'white', 'display':'inline-block', 'margin':'3'}),
#                 html.Div(
#                     dcc.RadioItems(
#                         id='status'+name,
#                         options=[
#                             {'label':'ON', 'value':'ON'},
#                             {'label':'OFF', 'value':'OFF'},
#                             ],
#                         value='ON',
#                     ), 
#                     className='column',
#                     style={'color':'white', 'margin':'3', "position": "relative", "border": "1px solid", "borderColor": "rgba(68,149,209,.9)",},
#                 ),
#                 html.Div(dcc.Input(
#                     id='schedule'+name,
#                     placeholder='HH:MM',
#                     type='text',
#                     value='HH:MM',
#                     ), 
#                     className='column',
#                     style={'color':'white', 'margin':'3', "position": "relative", "border": "1px solid", "borderColor": "rgba(68,149,209,.9)",},
#                 ),    
#             )

#         )


#     return html.Div(user_commands)


def serve_layout():
  return html.Div(
      [
        # header
        html.Div([
          dcc.Location(id='url', refresh=False),
          get_logo(),
          html.H2("Home Status", style={'marginTop':'5', 'marginLeft':'7', 'display':'block', 'text-align':'center','float':'center', 'color':'white', "backgroundColor": "#18252E"}),
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
              # dcc.Tab(
              #     label="Settings", 
              #     value="settings_tab", 
              #     style=tab_style,
              #     selected_style=tab_selected_style,
              #     className='custom-tab',
              #     ),
              # dcc.Tab(
              #   label="History", 
              #   value="history_tab",
              #   style=tab_style,
              #   selected_style=tab_selected_style,
              #   className='custom-tab',
              #   ),
            ],value="status_tab", className="col s12 m3 l2", style=tabs_styles,
          )
              
          ], className='col s12 m3 l2', style={'display': 'inline-block', 'padding':'5', 'float':'left'}
        ),
            
     

        # # Tab content
        html.Div(id="tab_content", className="row", style={"margin": "2%"}),
        # dcc.Location(id='url', refresh=False),
        # html.Div(id="page-content", children='Start'),
       ],
      className="row",
      style={"margin": "0%", "backgroundColor": "#18252E"},
    )


def render_status():
  # render content for status tab
  global cmd_algorithm, cmd_loading, ldc_signal
  return html.Div(children=[
        html.Div([
          html.H1(" ", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
          ], className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E"}
        ),


        html.Div(
          html.Div(children=html.Div(id='graphs'), className='row',),
          className='12 columns',
          style = {
             "position": "relative",
            "float": "left",
            # "border": "1px solid",
            # "borderColor": "rgba(68,149,209,.9)",
            "overflow": "hidden",
            "marginBottom": "2px",
          },
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