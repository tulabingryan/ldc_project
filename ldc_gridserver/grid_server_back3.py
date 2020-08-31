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
# app.scripts.config.serve_locally = True
# app.css.config.serve_locally = True






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




### ancillary functions ###
def get_dates(db_name='./ldc.db', report=False):
    """ Fetch data from the local database"""
    counter = 0
    data = []
    while True and counter < 10:
        try:
            con = lite.connect(db_name, isolation_level=None)
            con.execute('pragma journal_mode=wal;')
            cur = con.cursor()
       
            # get the last set of records for a specified duration
            with con:
                sql_cmd = "SELECT DISTINCT localtime FROM data ORDER BY unixtime ASC"
                cur.execute(sql_cmd) 
                data = np.array(cur.fetchall())
            
            break
        except Exception as e:
            print("Error in get_dates:", e)
            counter += 1

    if report: 
        print(data)
        
    return data


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


def get_data(dict_msg={"algorithm":"A0", "loading":10, "frequency":810, "timescale":1, "unixstart":0, "unixend":0}, 
    db_name='./ldc_all.db', mcast_ip="224.0.2.3", mcast_port=16003, report=False):
    # define timeout
    if dict_msg["unixstart"]==0:
        tm = 0.1
    else:
        tm = 10
    # get data from database
    dict_data = MULTICAST.send(dict_msg, ip=mcast_ip, port=mcast_port, timeout=tm)
    df_data = pd.DataFrame.from_dict(dict_data, orient='index')
    for i in range(len(df_data.index)):
        try:
            df_data.loc[i,'value'] = float(df_data.loc[i, 'value'])
        except:
            pass

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


### GLOBAL VARIABLES ###
global dict_cmd, cmd_algorithm, cmd_loading, ldc_signal, latest_demand

local_ip = get_local_ip()
df_data = get_data(dict_msg={"timescale":1, "unixstart":0, "unixend":0}) #send_command(dict_cmd={'algorithm':'A0', 'loading':10, 'frequency':810, 'timescale':1}, ip=local_ip, port=10000)
capacity = 30000  # [W]

try:
    dict_cmd = read_json('target_loading.txt')
    target_loading = float(dict_cmd['agg_limit'])
    cmd_algorithm = dict_cmd['algorithm']
except Exception as e:
    print("Error initial command:", e)
    cmd_algorithm = "A0"
    try:
        target_loading = df_data[df_data['parameter']=='agg_limit'].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).tail(1)['value']
        
    except:
        target_loading = 0
try:        
    agg_demand = df_data[df_data['parameter']=='agg_demand'].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).tail(1)['value']
    ldc_signal = df_data[df_data['parameter']=='frequency'].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).tail(1)['value']
except:
    agg_demand = 0
    ldc_signal = 810

latest_demand = agg_demand
cmd_loading = target_loading  # [W]    
timescale = 1
sum_actual = 0
sum_proposed = 0



# array_dates = get_dates()
# print(array_dates)
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
                            # dcc.Tab(
                            #     label="Settings", 
                            #     value="settings_tab", 
                            #     style=tab_style,
                            #     selected_style=tab_selected_style,
                            #     className='custom-tab',
                            #     ),
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
                html.Div(id="tab_content", className="row", style={"margin": "2%"}),
           ],
            className="row",
            style={"margin": "0%", "backgroundColor": "#18252E"},
        )



@app.callback(
    dash.dependencies.Output('cmd-loading', 'children'),
    [dash.dependencies.Input('input-cmd-loading', 'n_submit'),
    dash.dependencies.Input('cmd-algorithm','value'),],
    [dash.dependencies.State('input-cmd-loading', 'value')])
def update_output(n_submit, algorithm, loading):
    global cmd_loading, cmd_algorithm, dict_cmd
    cmd_algorithm = algorithm
    if cmd_algorithm=='A0':
        cmd_loading = 30000
    else:
        cmd_loading = loading * 1000
        
    dict_cmd.update({"agg_limit":cmd_loading, "algorithm":cmd_algorithm})
    save_json(dict_cmd, 'target_loading.txt')
    
    return cmd_loading / 1000


@app.callback(
    dash.dependencies.Output('cmd-signal', 'children'),
    [dash.dependencies.Input('input-cmd-loading', 'n_submit')],
    [dash.dependencies.State('input-cmd-loading', 'value')],
    events=[dash.dependencies.Event('data-update','interval')])
def update_signal(n_submit, value):
    global cmd_algorithm, cmd_loading, ldc_signal
    ldc_signal = get_frequency(cmd_algorithm, cmd_loading)
    return int(ldc_signal)

    

@app.callback(
        dash.dependencies.Output('command','children'),
        [dash.dependencies.Input('cmd-algorithm','value'),
        dash.dependencies.Input('cmd-loading','children'),])
def update_command(algorithm, loading):
    global cmd_loading, cmd_algorithm, dict_cmd
    cmd_algorithm = algorithm
    
    if cmd_algorithm=='A0':
        cmd_loading = 30000
    else:
        cmd_loading = loading * 1000
    
    dict_cmd.update({"agg_limit":loading * 1000, "algorithm":cmd_algorithm})
    save_json(dict_cmd, 'target_loading.txt')

    return


def get_frequency(cmd_algorithm, cmd_loading):
    global capacity, ldc_signal, latest_demand

    target_loading = float(cmd_loading)
    percent_loading = float(target_loading) / capacity

    
    ldc_upper = 860
    ldc_lower = 760
    ldc_center = 810 
    ldc_bw = ldc_upper - ldc_lower  # bandwidth
    w_past = 0.1  # weight given to the past signal, acting as a damper to change in ldc_signal

    try:
        if cmd_algorithm=='A0':
            ldc_signal=ldc_upper

        # elif cmd_algorithm in ['A1', 'A2']:
        else:
            offset = ((target_loading - latest_demand)/latest_demand) * ((860-760))
            ldc_signal += offset
            ldc_signal = np.min([ldc_signal, 860])
            ldc_signal = np.max([ldc_signal, 760]) 

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
    
    try:
        try:
            dict_data = json.loads(json_data)
            # agg_proposed_old = pd.read_json(dict_data['agg_proposed'], orient='split')
            # agg_approved_old = pd.read_json(dict_data['agg_approved'], orient='split')
            agg_demand_old = pd.read_json(dict_data['agg_demand'], orient='split')
            agg_limit_old = pd.read_json(dict_data['agg_limit'], orient='split')
        except Exception as e:
            print("Error update_data old data:", e)
            agg_proposed_old = pd.DataFrame([], columns=['value'])
            agg_approved_old = pd.DataFrame([], columns=['value'])
            agg_demand_old = pd.DataFrame([], columns=['value'])
            agg_limit_old = pd.DataFrame([], columns=['value'])
                     
        
        try:
            
            df_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":0, "unixend":0})
            
            # agg_proposed_new = df_data[(df_data['parameter']=='agg_proposed')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).sum()
            # agg_approved_new = df_data[(df_data['parameter']=='agg_approved')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).sum()
            agg_limit_new = df_data[(df_data['parameter']=='agg_limit')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).mean()
            agg_demand_new = df_data[df_data['parameter']=='agg_demand'].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).mean()
            
            # agg_proposed_new = pd.read_json(agg_proposed_new.to_json(orient='split'), orient='split')
            # agg_approved_new = pd.read_json(agg_approved_new.to_json(orient='split'), orient='split')
            agg_limit_new = pd.read_json(agg_limit_new.to_json(orient='split'), orient='split')
            agg_demand_new = pd.read_json(agg_demand_new.to_json(orient='split'), orient='split')
            
            latest_demand = float(agg_demand_new.tail(1)['value'].values[0])
            # latest_demand = float(agg_approved_new['value'].tail(1).values[0])


        except Exception as e:
            print("Error update_data new data:", e)
            # agg_proposed_new = pd.DataFrame([], columns=['value'])
            # agg_approved_new = pd.DataFrame([], columns=['value'])
            agg_demand_new = pd.DataFrame([], columns=['value'])
            agg_limit_new = pd.DataFrame([], columns=['value'])
            

        # agg_proposed = pd.concat([agg_proposed_old,agg_proposed_new]).tail(60*5)
        # agg_approved = pd.concat([agg_approved_old, agg_approved_new]).tail(60*5)
        agg_limit = pd.concat([agg_limit_old, agg_limit_new]).tail(60*5)
        agg_demand = pd.concat([agg_demand_old, agg_demand_new]).tail(60*5)


        
    except Exception as e:
        print("Error update_data:", e)
        try:
            df_data = get_data(dict_msg={"algorithm":cmd_algorithm, "loading":cmd_loading, "frequency":ldc_signal, "timescale":1, "unixstart":0, "unixend":0})
           
            # df_data['localtime'] = [datetime.datetime.fromtimestamp(x).strftime('%y-%m-%d %H:%M:%S.%f') for x in df_data['unixtime']]
            # agg_proposed = df_data[(df_data['parameter']=='agg_proposed')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).sum()
            # agg_approved = df_data[(df_data['parameter']=='agg_approved')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).sum()
            agg_limit = df_data[(df_data['parameter']=='agg_limit')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).mean()
            agg_demand = df_data[(df_data['parameter']=='agg_demand')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).mean()
            
            latest_demand = float(agg_demand.tail(1)['value'].values[0])
            # latest_demand = float(agg_approved['value'].tail(1).values[0])


        except Exception as e:
            print("Error update_data exception:", e)
            # agg_proposed = pd.DataFrame([], columns=['value'])
            # agg_approved = pd.DataFrame([], columns=['value'])
            agg_limit = pd.DataFrame([], columns=['value'])
            agg_demand = pd.DataFrame([], columns=['value'])

    
    dict_newdata = {
        # "agg_proposed" : agg_proposed.to_json(orient='split'),
        # "agg_approved" : agg_approved.to_json(orient='split'),
        "agg_limit" : agg_limit.to_json(orient='split'),
        "agg_demand" : agg_demand.to_json(orient='split'),
    }

    
    return json.dumps(dict_newdata) #df_data.to_json(orient='split')







@app.callback(
    dash.dependencies.Output('graphs','children'),
    [dash.dependencies.Input('data', 'children')],
    )
def update_graph(json_data):  
    global df_data, cmd_algorithm
    graphs = []
    
    try:
        dict_data = json.loads(json_data)
        agg_proposed = pd.read_json(dict_data['agg_proposed'], orient='split')
        agg_approved = pd.read_json(dict_data['agg_approved'], orient='split')
        agg_limit = pd.read_json(dict_data['agg_limit'], orient='split')
        agg_demand = pd.read_json(dict_data['agg_demand'], orient='split')

        

        
    except Exception as e:
        try:
            agg_proposed = df_data[(df_data['parameter']=='agg_proposed')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).sum()
            agg_approved = df_data[(df_data['parameter']=='agg_approved')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).sum()
            agg_limit = df_data[(df_data['parameter']=='agg_limit')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).mean()
            agg_demand = df_data[(df_data['parameter']=='agg_demand')].drop(['parameter'], axis=1).astype(float).groupby(['unixtime']).mean()

            
        except:
            agg_proposed = pd.DataFrame([], columns=['value'])
            agg_approved = pd.DataFrame([], columns=['value'])
            agg_demand = pd.DataFrame([], columns=['value'])
            agg_limit = pd.DataFrame([], columns=['value'])
    

    # convert timezone from UTC to local timezone before graph
    agg_proposed.index = [a.tz_localize('UTC').tz_convert(timezone) for a in agg_proposed.index]
    agg_approved.index = [a.tz_localize('UTC').tz_convert(timezone) for a in agg_approved.index]
    agg_demand.index = [a.tz_localize('UTC').tz_convert(timezone) for a in agg_demand.index]
    agg_limit.index = [a.tz_localize('UTC').tz_convert(timezone) for a in agg_limit.index]
    
               
    # plot total demand
    trace_proposed = go.Scattergl(
                x = [a.isoformat() for a in agg_proposed.index],
                y = agg_proposed['value'],
                name = 'Proposed',
                # opacity = 0.8,
                # fill = "tozeroy",
                )

    trace_approved = go.Scattergl(
                x = [a.isoformat() for a in agg_approved.index],
                y = agg_approved['value'],
                name = 'Approved',
                # opacity = 0.8,
                # fill = "tozeroy",
                )

    

    trace_actual = go.Scattergl(
                x = [a.isoformat() for a in agg_demand.index],
                y = agg_demand['value'],
                name = 'Actual',
                line= {'color':'rgb(0,255,0)'},
                # opacity = 0.8,
                fill = "tozeroy",
                )

    trace_limit = go.Scattergl(
                x = [a.isoformat() for a in agg_limit.index], # [a.tz_localize('UTC').tz_convert(timezone) for a in agg_limit.index],
                y = agg_limit['value'],
                name = 'Limit',
                line= {'color':'rgb(255,0,0)'},
                # opacity = 0.8,
                # fill = "tozeroy",
                )

    # if cmd_algorithm=='A0':
    trace_agg = [trace_actual]
    # else:
    #     trace_agg = [trace_actual, trace_limit]

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


    # trace_agg2 = [trace_proposed, trace_approved]
    # graphs.append(html.Div(dcc.Graph(
    #             id='total-demand_houses',
    #             animate=False,
    #             figure={'data': trace_agg2,
    #                     'layout' : go.Layout(xaxis= dict(autorange=True),
    #                                         yaxis=dict(autorange=True, title='Power (VA)'),
    #                                         margin={'l':50,'r':1,'t':45,'b':50},
    #                                         title='Power Demand',
    #                                         legend=dict(font=dict(size=10), orientation='v'),
    #                                         autosize=True,
    #                                         height=500,
    #                                         font=dict(color='#CCCCCC'),
    #                                         titlefont=dict(color='#CCCCCC', size=14),
    #                                         hovermode="closest",
    #                                         plot_bgcolor="#020202", #"#191A1A",
    #                                         paper_bgcolor="#18252E",
                                            
    #                                         )}
    #             ), className='row'))
    
    # # add space after one graph layout
    # graphs.append(html.H2('', className='row',),)


    # # plot demands of individual devices
    # device_names = np.unique(device_demand['id'])
    # trace_devices = []
    # for name in device_names:
    #     df = device_demand[(device_demand['id']==name)]
    #     trace = go.Scatter(
    #         x = df['localtime'],
    #         y = df['value'],
    #         name = name, #get_type(name),
    #         # fill = "tozeroy",
    #         )

    #     trace_devices.append(trace)
        
    # graphs.append(html.Div(dcc.Graph(
    #             id='device-demands',
    #             animate=False,
    #             figure={'data': trace_devices,
    #                     'layout' : go.Layout(xaxis= dict(autorange=True),# tickformat= '%y-%-m-%d %H:%M:%S'),
    #                                         yaxis=dict(autorange=True, title='Power (VA)'),
    #                                         # margin={'l':50,'r':1,'t':45,'b':50},
    #                                         title='Power Demands',
    #                                         autosize=True,
    #                                         height=500,
    #                                         font=dict(color='#CCCCCC'),
    #                                         titlefont=dict(color='#CCCCCC', size=14),
    #                                         margin=dict(
    #                                             l=35,
    #                                             r=35,
    #                                             b=35,
    #                                             t=45
    #                                         ),
    #                                         hovermode="closest",
    #                                         plot_bgcolor="#020202", #"#191A1A",
    #                                         paper_bgcolor="#18252E",
    #                                         # legend=dict(font=dict(size=10), orientation='h'),
    #                                         )}
    #             ), className='col s12 m6 l6'))

    return graphs



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
                        html.Div(id='cmd-loading', children=np.round(float(cmd_loading)/1000, 3), className='row', 
                            style={'font-size':'xx-large', 'color':'white', 'text-align':'right', 'display':'inline-block', 'padding':'9', "position": "relative",}),
                        html.Div(id='cmd-loading-unit', children='kVA', className='row',
                            style={'font-size':'xx-large', 'color':'white', 'text-align':'left', 'display':'inline-block', 'padding':'9',"position": "relative",}),
                        ], 
                        className='column',
                    ),

                    
                        

                    html.Div([
                        html.Label('Set limit (kVA):', className='column',
                            style={'color':'white', 'display':'inline-block', 'margin':'3', "position": "relative",}),
                        
                        dcc.Input(id='input-cmd-loading', className='row',
                            value= np.round(float(cmd_loading)/1000, 3), # converted to kW
                            disabled=False, 
                            type='number', 
                            min=0, 
                            max= 30, # converted to kW
                            step=0.10, 
                            inputmode='numeric',
                            style={'text-align':'center', 'display':'inline-block', 'padding':'9', "position": "relative",}),
                        
                        ], 
                        className='column',
                    ),


                    html.Div([
                        html.Label('LDC Signal:', className='column',
                            style={'color':'white', 'display':'inline-block', 'margin':'3'}),
                        html.Div(id='cmd-signal', children=ldc_signal, className='row',
                            style={'font-size':'xx-large', 'color':'white', 'text-align':'right', 'display':'inline-block', 'padding':'9', "position": "relative",}),
                        html.Div(id='cmd-signal-unit', children='Hz', className='row',
                            style={'font-size':'xx-large', 'color':'white', 'text-align':'left', 'display':'inline-block', 'padding':'9', "position": "relative",}),
                        ], 
                        className='row',
                    ),



                    html.Div([
                        html.Label('Algorithm:', className='column',
                            style={'color':'white', 'display':'inline-block', "position": "relative",}),
                        dcc.RadioItems(
                            id='cmd-algorithm',
                            options=[
                                        {"label": "No LDC", "value": "A0"},
                                        {"label": "Basic LDC", "value": "A1"},
                                        {"label": "Advance LDC", "value": "A2"},
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
