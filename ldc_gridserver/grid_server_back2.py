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


def get_data(db_name='./ldc.db', start=None, end=None, duration=60*60, report=False):
    """ Fetch data from the local database"""
    counter = 0
    data = []
    df_data = pd.DataFrame(data, columns=['unixtime', 'localtime', 'house', 'id', 'type', 'state', 'parameter', 'value'])
    while True and len(data) < 1:
        try:
            con = lite.connect(db_name)
            con.execute('pragma journal_mode=wal;')
            cur = con.cursor()
            if start==None or end==None:
                with con:
                    
                    # Get the last timestamp recorded
                    cur.execute('SELECT unixtime FROM data ORDER BY unixtime DESC LIMIT 1') 
                    end = np.array(cur.fetchall()).flatten()[0]
                    start = end - duration
                    
            else:
                pass
    
            # get the last set of records for a specified duration
            with con:
                sql_cmd = "SELECT unixtime, localtime, house, id, type, state, parameter, value FROM data WHERE unixtime BETWEEN " + str(start) + " AND " + str(end) + " ORDER BY unixtime ASC"
                cur.execute(sql_cmd) 
                data = np.array(cur.fetchall())
                df_data = pd.DataFrame(data, columns=['unixtime', 'localtime', 'house', 'id', 'type', 'state', 'parameter', 'value'])   

            break
        except Exception as e:
            print("Error in get_data:", e)
            print(data)
            counter += 1

    if report: 
        print(df_data['parameter'].tail(50))
        
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
        pass

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

def calc_ldc_frequency(cmd_algorithm, cmd_loading, latest_demand, capacity, ldc_signal):
    # calculate the ldc signal frequency to be sent
    ldc_upper = 860
    ldc_lower = 760
    ldc_center = 810 
    ldc_bw = ldc_upper - ldc_lower  # bandwidth
    w_past = 0.1  # weight given to the past signal, acting as a damper to change in ldc_signal
  
    percent_loading = cmd_loading / capacity  # [W/W]

    try:
        offset = np.nan_to_num(1 - (latest_demand / (cmd_loading)))

    except Exception as e:
        print("Error in getting offset value:",e)
        offset = 0
    
    try:
        if cmd_algorithm=='A0':
            ldc_signal=ldc_upper

        elif cmd_algorithm=='A1':
            ldc_signal = float(760 + (ldc_bw * percent_loading))
            ldc_signal = np.min([ldc_signal, 860])
            ldc_signal = np.max([ldc_signal, 760])
            
        elif cmd_algorithm=='A2':
            ldc_signal_new = float(ldc_center + (ldc_bw * offset))
            ldc_signal = (w_past * ldc_signal) + ((1-w_past) * ldc_signal_new)
            ldc_signal = np.min([ldc_signal, 860])
            ldc_signal = np.max([ldc_signal, 760])

        elif cmd_algorithm == 'A3':
            ldc_signal = float(760 + (ldc_bw * percent_loading))
            ldc_signal = np.min([ldc_signal, 860])
            ldc_signal = np.max([ldc_signal, 760])
            
        else: # default is 'A2'
            ldc_signal_new = float(ldc_center + ((ldc_bw) * offset))
            ldc_signal = (w_past * ldc_signal) + ((1-w_past) * ldc_signal_new)
            ldc_signal = np.min([ldc_signal, 860])
            ldc_signal = np.max([ldc_signal, 760])

        
        return ldc_signal

    except Exception as e:
        print("Error in get_cmd:", e)

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


### GLOBAL VARIABLES ###
local_ip = get_local_ip()
dict_data = send_command(dict_cmd={'A':'A0', 'L':10, 'F':810, 'T':1}, ip=local_ip, port=10000)
df_data = pd.DataFrame.from_dict(dict_data['houses'], orient='index')
cmd_algorithm = 'A0'
cmd_loading = 10000  # [W]
ldc_signal = 810
timescale = 1
latest_demand = dict_data['grid']  # [W]
capacity = 30000  # [W]
print(dict_data)
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


app.layout = html.Div(
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
    [dash.dependencies.Input('button', 'n_clicks')],
    [dash.dependencies.State('input-cmd-loading', 'value')])
def update_output(n_clicks, value):
    return value





@app.callback(
        dash.dependencies.Output('data','children'),
        [dash.dependencies.Input('cmd-algorithm','value'),
        dash.dependencies.Input('cmd-loading','children'),],
        events=[dash.dependencies.Event('data-update','interval')],
        )
def update_data(cmd_algorithm, cmd_loading):
    global latest_demand, capacity, ldc_signal, timescale, df_data, sum_actual, sum_proposed
    
    try:
        ldc_signal = calc_ldc_frequency(cmd_algorithm, cmd_loading*1000, latest_demand, capacity, ldc_signal)  # note: cmd_loading is converted to W 
        dict_newdata = send_command(dict_cmd={'A':cmd_algorithm, 'L':cmd_loading, 'F':ldc_signal, 'T':1}, ip=local_ip, port=10000)
        # df_data = pd.DataFrame.from_dict(dict_data['houses'], orient='index')
        # sum_actual = df_data['actual'].sum()  # [W]
        # sum_proposed = df_data['proposed'].sum() # [W]
        # latest_demand = sum_actual #dict_data['grid']  # [W]
        # df_data['actual'] = [latest_demand * (x/sum_actual) for x in df_data['actual']]

    except Exception as e:
        print("Error in dash_app update_data:", e)
        dict_newdata = {}
    return json.dumps(dict_newdata)









@app.callback(
    dash.dependencies.Output('graphs','children'),
    [dash.dependencies.Input('data', 'children')],)
    # [dash.dependencies.Input('cmd-algorithm','value'),
    # dash.dependencies.Input('cmd-loading','children'),],
    # events=[dash.dependencies.Event('graph-update','interval')],
    # )
def update_graph(json_data):
    global latest_demand, capacity, ldc_signal, timescale

    graphs = []
    

    # try:
    #     ldc_signal = calc_ldc_frequency(cmd_algorithm, cmd_loading*1000, latest_demand, capacity, ldc_signal)  # note: cmd_loading is converted to W 
    #     dict_data = send_command(dict_cmd={'A':cmd_algorithm, 'L':cmd_loading, 'F':ldc_signal, 'T':1}, ip=local_ip, port=10000)
    # except Exception as e:
    #     print("Error in dash_app update_data:", e)
    #     dict_data = {}

    # process data to be ploted
    try:
        dict_data = json.loads(json_data)
        print("update_graph:", dict_data)
        df_data = pd.DataFrame.from_dict(dict_data['houses'], orient='index')
        sum_actual = df_data['actual'].sum()  # [W]
        sum_proposed = df_data['proposed'].sum() # [W]
        latest_demand = sum_actual #dict_data['grid']  # [W]
        # df_data['actual'] = [latest_demand * (x/sum_actual) for x in df_data['actual']]

    except Exception as e:
        print(e)

    # graph for aggregation------------------------------
    meter_all_proposed = {
        "values": [np.round(x/1000,3) for x in df_data['proposed'].astype(float)],  # displayed as kW
        "labels": [x for x in df_data['house']],
        "position":"center",
        "domain": {"x": [0.1, 0.9], "y":[0.1, 0.9]},
        "name": "Gauge_all",
        "hole": .7,
        "type": "pie",
        "direction": "clockwise",
        "rotation": 90,
        "showlegend": False,
        "textinfo": "label+percent+value",
        "textposition": "outside",
        "hoverinfo": "none", #"label+percent+value",
    }


    layout_all_proposed = dict(
        autosize=True,
        height=700,
        font=dict(color='#CCCCCC'),
        titlefont=dict(color='#CCCCCC', size='14'),
        margin=dict(
            l=35,
            r=35,
            b=35,
            t=45
        ),
        hovermode="closest",
        plot_bgcolor="#191A1A",
        paper_bgcolor="#18252E",
        legend=dict(font=dict(size=10), orientation='h'),

        annotations = [
            {
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'text': "Proposed Demand",
                'font':{'color':"white", 'size':'18'},
                'textposition':'center',
                'showarrow': False,
            },

            {
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.45,
                'text': str(np.round(df_data['proposed'].sum()/1000, 3)) + ' kW',
                'font':{'color':"white", 'size':'22'},
                'showarrow': False
            }
        ],
    )

    fig_all_proposed = {"data": [meter_all_proposed], "layout": layout_all_proposed,}
    graphs.append(html.Div(dcc.Graph(id='fig-all_proposed', figure=fig_all_proposed,),
            className='col s12 m12 l12',
            style={"backgroundColor": "#18252E", 'display':'inline-block'},
        ))




    meter_all_actual = {
        "values": [np.round(x/1000,3) for x in df_data['actual'].astype(float)],
        "labels": [x for x in df_data['house']],
        "position":"center",
        "domain": {"x": [0.1, 0.9], "y":[0.1, 0.9]},
        "name": "Gauge_all",
        "hole": .7,
        "type": "pie",
        "direction": "clockwise",
        "rotation": 90,
        "showlegend": False,
        "textinfo": "label+percent+value",
        "textposition": "outside",
        "hoverinfo": "none", #"label+percent+value",
    }


    layout_all_actual = dict(
        autosize=True,
        height=700,
        font=dict(color='#CCCCCC'),
        titlefont=dict(color='#CCCCCC', size='14'),
        margin=dict(
            l=35,
            r=35,
            b=35,
            t=45
        ),
        hovermode="closest",
        plot_bgcolor="#191A1A",
        paper_bgcolor="#18252E",
        legend=dict(font=dict(size=10), orientation='h'),

        annotations = [
            {
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'text': "Approved Demand",
                'font':{'color':"white", 'size':'18'},
                'textposition':'center',
                'showarrow': False,
            },

            {
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.45,
                'text': str(np.round(df_data['actual'].sum()/1000, 3)) + ' kW',
                'font':{'color':"white", 'size':'22'},
                'showarrow': False
            },

        ],
    )

    fig_all_actual = {"data": [meter_all_actual], "layout": layout_all_actual,}



    graphs.append(html.Div(dcc.Graph(id='fig-all_actual', figure=fig_all_actual,),
            className='col s12 m12 l12',
            style={"backgroundColor": "#18252E", 'display':'inline-block'},
        ))








    # display guage for total house demand
    p_value = (ldc_signal - 760) * 100/((860-760)*2)
    p_filler = 50 - p_value

    # base chart parameters
    values=[40, 10, 10, 10, 10, 10, 10]
    labels=[" ", "760Hz", "780Hz", "800Hz", "820Hz", "840Hz", "860Hz"]
    colors=['#18252E', '#18252E', '#18252E', '#18252E', '#18252E', '#18252E', '#18252E']

    base_chart = create_baseChart(values, labels, colors)


    # points for pointer needle
    points_house = [[0.5, 0.7],
                    [0.43, 0.6],
                    [0.44, 0.6],
                    [0.44, 0.53],
                    [0.56, 0.53],
                    [0.56, 0.6],
                    [0.57, 0.6],
                    [0.5, 0.7]]


    path_house = create_shapePath(points_house)
    
    meter_chart = {
        "values": [50, p_value, p_filler],
        "labels": ["Power Demand", "Demand", " ",], #"Debug", "Info", "Warn", "Error", "Fatal"],
        "marker": {
            'colors': [
                # 'rgb(255, 255, 255)',
                '#18252E',
                'rgba(255,0,0, 1)',
                'rgba(0, 0, 0, 1)',
            ]
        },
        "domain": {"x": [0.1, 0.9]},
        "name": "Gauge",
        "hole": .9,
        "type": "pie",
        "direction": "clockwise",
        "rotation": 90,
        "showlegend": False,
        "textinfo": 'none', #"label",
        "textposition": "inside",
        "hoverinfo": "none", #"label+percent+name",
    }


    layout_house = dict(
        autosize=True,
        height=300,
        # width=500,
        font=dict(color='#CCCCCC'),
        titlefont=dict(color='#CCCCCC', size='14'),
        margin=dict(
            l=35,
            r=35,
            b=35,
            t=45
        ),
        hovermode="closest",
        plot_bgcolor="#191A1A",
        paper_bgcolor="#18252E",
        legend=dict(font=dict(size=10), orientation='h'),
        # title='Satellite Overview',
        shapes = [
            {
                'type': 'path',
                'path': path_house, #'M 0.235 0.5' + 'L 0.24 0.65 L 0.245 0.5 Z',
                'fillcolor': 'rgba(255, 0, 0, 0.9)',
                'line': {
                    'width': 0.0
                },
                'xref': 'paper',
                'yref': 'paper'
            }
        ],
        annotations = [
            {
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'text': "LDC Signal",
                'showarrow': False,
            },

            {
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.42,
                'text': str(int(np.round(ldc_signal, 0))) + ' Hz',
                'font':{'color':"white", 'size':'22'},
                'showarrow': False
            }
        ],

    )

    # we don't want the boundary now
    base_chart['marker']['line']['width'] = 0

    fig_house = {"data": [base_chart, meter_chart],
           "layout": layout_house,
           }



    graphs.append(html.Div([
        html.Div(dcc.Graph(id='total-actual', figure=fig_house,),
            className='col s12 m12 l12',
            style={"backgroundColor": "#18252E", 'display':'inline-block'},
           ),
        # html.Div(dcc.Graph(id='total-proposed', figure=fig_house,),
        #     className='col s12 m12 l12',
        #     style={"backgroundColor": "#18252E", 'display':'inline-block'},
        #     ),
        ],
        className='col s12 m12 l12',
        style={"backgroundColor": "#18252E", 'display':'inline-block', 'width':'50%'},
        ),)
    





    

    return graphs








appstatus_layout = [
        html.Div(children=[
                html.Div([
                    html.H1("Grid Status", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
                    ], 
                    className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
                ),
                
                html.Div([
                    html.Div([
                        
                        html.Label('Power limit:', 
                            className='row',
                            style={'color':'white', 'display':'inline-block', 'width':'100%', 'margin':'3'}),
                        html.Div(id='cmd-loading', children=np.round(30000/1000, 3), 
                            style={'font-size':'xx-large', 'color':'white', 'text-align':'right', 'display':'inline-block', 'width':'30%', 'padding':'9'}),
                        html.Div(id='cmd-loading-unit', children='kVA', 
                            style={'font-size':'xx-large', 'color':'white', 'text-align':'left', 'display':'inline-block', 'width':'30%', 'padding':'9'}),
                        ], 
                        className='row',
                    ),

                    html.Div([
                        html.Label('Set limit (kVA):', 
                            className='row',
                            style={'width':'100%', 'color':'white', 'display':'inline-block', 'margin':'3'}),
                        dcc.Input(id='input-cmd-loading', 
                            value= np.round(30000/1000, 3), # converted to kW
                            disabled=False, 
                            type='number', 
                            min=0, #max= np.round(capacity * 1.5 / 1000, 3), # converted to kW
                            step=1.0, 
                            inputmode='numeric',
                            className='row',
                            style={'width':'90%', 'text-align':'center', 'display':'inline-block', 'padding':'9'}),

                        html.Button('Submit', id='button', style={'width':'90%', 'text-align':'center', 'display':'inline-block', 'padding':'0'}),
                        ], 
                        className='row',
                    ),

                    html.Div([
                        html.Label('Algorithm:', 
                            className='row',
                            style={'color':'white', 'display':'inline-block'}),
                        dcc.RadioItems(
                            id='cmd-algorithm',
                            options=[
                                        {"label": "No LDC", "value": "A0"},
                                        {"label": "Basic LDC", "value": "A1"},
                                        {"label": "Integral", "value": "A2"},
                                        {"label": "Percentage", "value": "A3"},
                                    ],
                            value="A0",
                            className='row',
                            style={'color':'white', 'margin':'3'}
                        ),
                      
                        ], 
                        className='row',
                        style={'display':'inline-block'}
                    ),


                    ], 
                    className='col s12 m2 l1',
                    style={'display': 'inline-block', 'padding':'3', 'float':'left'}
                ),
                
                # hidden div: holder of data
                html.Div([
                    html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0', 'display':'none'}),
                    dcc.Interval(id='data-update', interval=1*1000),
                    ], 
                    className='row', 
                    style={'display':'none',},
                ),
                

                html.Div([
                    html.Div(children=html.Div(id='graphs'), className='row',),
                    # dcc.Interval(id='graph-update', interval=1.5*1000),
                    
                    # hidden update for sending ldc command signal
                    html.Div(children=html.Div(id='command'), style={'display': 'none'}),
                    # dcc.Interval(id='cmd-update', interval=10.1*1000),

                    ], 
                    className='col s12 m12 l7',
                    style={'width':'80%', 'display':'inline-block', 'padding':'3px'},
                ),
            
            ],

            style={'display':'inline-block', "backgroundColor": "#18252E", 'width':'100%'} 
            
        ),
    ]


# appsettings_layout = [
#     html.Div(children=[
#                 html.Div([
#                     html.H1("Settings", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
#                     ], 
#                     className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
#                 ),
                
#                 html.Div([
                    
#                     ], 
#                     className='col s12 m2 l1',
#                     style={'display': 'inline-block', 'padding':'3', 'float':'left'}
#                 ),
                
#                 # hidden div: holder of data
#                 html.Div([
                    
#                     ], 
#                     className='row', 
#                     style={'display':'none',},
#                 ),
                

#                 html.Div([
#                     ], 
#                     className='col s12 m12 l7',
#                     style={'width':'80%', 'display':'inline-block', 'padding':'3px'},
#                 ),
            
#             ],

#             style={'display':'inline-block', "backgroundColor": "#18252E", 'width':'100%'} 
            
#         ),
    
#     ]

array_dates = pd.date_range(start='2018-11-13T00:00', end=datetime.datetime.now(), freq='S', tz='Pacific/Auckland')

apphistory_layout = [

    html.Div([
        html.H2("History", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
        # Settings
        html.Div([
            html.Label('From:', style={'color':'white', 'display':'inline-block', 'text-align':'center'}),
            dcc.Dropdown(id='date1', 
                multi=False,
                clearable=False,
                options={'labels':array_dates, 'values':array_dates},
                value=array_dates[0],
            ),
            
            ], className='row', style={'width':'20%', 'display':'inline-block', 'margin':'2'}
        ),

        html.Div([
            html.Label('To:', style={'color':'white', 'display':'inline-block', 'text-align':'center'}),
            dcc.Dropdown(id='date2', 
                multi=False,
                clearable=False,
                options={'labels':array_dates, 'values':array_dates},
                value=array_dates[-1],
            ),
            
            ], className='row', style={'width':'20%', 'display':'inline-block', 'margin':'2'}
        ),

        ], 
        className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
    ),
        
    ]



@app.callback(Output("tab_content", "children"), [Input("tabs", "value")])
def render_content(tab):
    if tab == "status_tab":
        # array_dates = get_dates()
        return appstatus_layout[0]
    elif tab == "settings_tab":
        return appsettings_layout[0]
    elif tab == "history_tab":
        return apphistory_layout[0]
    else:
        return appstatus_layout[0]


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


if __name__ == '__main__':
    app.run_server(debug=True, host=local_ip, port=15000)
    


















# @app.callback(
#     dash.dependencies.Output('graphs','children'),
#     [dash.dependencies.Input('data', 'children')],)
# def update_graph(json_data):
#     graphs = []
#     try:
#         dict_data = json.loads(json_data)
        
#         total_proposed = pd.read_json(dict_data['total_proposed'], orient='split')
#         total_actual = pd.read_json(dict_data['total_actual'], orient='split')
#         total_limit = pd.read_json(dict_data['total_limit'], orient='split')
#         flex_avg = pd.read_json(dict_data['flex_avg'], orient='split')
#         flex_min = pd.read_json(dict_data['flex_min'], orient='split')
#         flex_max = pd.read_json(dict_data['flex_max'], orient='split')

#         # house_demand = pd.read_json(dict_data['house_demand'], orient='split')
#         latest_demand = float(dict_data['latest_demand'])
#         n_houses = int(dict_data['n_houses'])
        
        
#     except Exception as e:
#         print(e)
#         df_data = df_data_init
#         total_proposed = df_data[(df_data['state']=='agg') & (df_data['parameter']=='proposed')].drop(['unixtime','id','state','parameter','house','type'], axis=1)
#         total_proposed['value'] = total_proposed['value'].astype(float)
#         total_proposed = total_proposed.groupby(['localtime']).sum(axis=1).reset_index()
        
#         total_actual = df_data[(df_data['state']=='agg') & (df_data['parameter']=='agg_demand')].drop(['unixtime','id','state','parameter','house','type'], axis=1)
#         total_actual['value'] = total_actual['value'].astype(float)
#         total_actual = total_actual.groupby(['localtime']).sum(axis=1).reset_index()
        
#         total_limit = df_data[(df_data['state']=='agg') & (df_data['parameter']=='limit')].drop(['unixtime','id','state','parameter','house','type'], axis=1)
#         total_limit['value'] = total_limit['value'].astype(float)
#         total_limit = total_limit.groupby(['localtime']).sum(axis=1).reset_index()

#         flex_avg = df_data[(df_data['state']=='agg') & (df_data['parameter']=='flexibility')].drop(['unixtime','id','state','parameter','house','type'], axis=1)
#         flex_avg['value'] = flex_avg['value'].astype(float)
#         flex_avg = flex_avg.groupby(['localtime']).mean().reset_index()
        
#         flex_min = df_data[(df_data['state']=='agg') & (df_data['parameter']=='flexibility')].drop(['unixtime','id','state','parameter','house','type'], axis=1)
#         flex_min['value'] = flex_min['value'].astype(float)
#         flex_min = flex_min.groupby(['localtime']).min().reset_index()
        
#         flex_max = df_data[(df_data['state']=='agg') & (df_data['parameter']=='flexibility')].drop(['unixtime','id','state','parameter','house','type'], axis=1)
#         flex_max['value'] = flex_max['value'].astype(float)
#         flex_max = flex_max.groupby(['localtime']).max().reset_index()
        
#         # house_demand = df_data[['localtime','id','parameter','value']]
#         latest_demand = total_actual['value'].tail(1).values.astype(float)[0]
#         n_houses = len(np.unique(df_data['house']))
        

#     # graph for aggregation------------------------------
#     # actual demand

#     trace_actual = go.Scatter(
#         x = total_actual['localtime'],
#         y = total_actual['value'],
#         name = 'Actual',
#         fill = "tozeroy",
#         )

#     # proposed demand
#     trace_proposed = go.Scatter(
#         x = total_proposed['localtime'],
#         y = total_proposed['value'],
#         name = 'Proposed',
#         fill = "tozeroy", # "tonexty"
#         )

#     # power limit
#     trace_limit = go.Scatter(
#         x = total_limit['localtime'],
#         y = total_limit['value'],
#         name = 'Limit',
#         )

#     # combining plots
#     trace_agg = [trace_proposed, trace_actual, trace_limit]

#     graphs.append(html.Div(dcc.Graph(
#                 id='aggregation',
#                 animate=False,
#                 figure={'data': trace_agg,
#                         'layout' : go.Layout( height=450,
#                                 xaxis= dict(autorange=True, showgrid=True),
#                                 yaxis=dict(autorange=True, showgrid=True, title='Power (VA)'),
#                                 margin={'l':50,'r':50,'t':45,'b':50},
#                                 title= 'Power Demand of '+ str(n_houses) + ' Houses',
#                                 )
#                         }
#                 ), 
#                 className='col s12 m12 l12',
#                 # style = {
#                 #     "position": "relative",
#                 #     "float": "left",
#                 #     "border": "1px solid",
#                 #     "borderColor": "rgba(68,149,209,.9)",
#                 #     "overflow": "hidden",
#                 #     "marginBottom": "2px",
#                 # },
#                 ),
#     )

#     # add space after one graph layout
#     graphs.append(html.H2('', className='row',),)


#     # # plot demands of individual houses
#     # house_names = np.unique(house_demand['id'])
#     # trace_houses = []
#     # for name in house_names:
#     #     df = house_demand[(house_demand['id']==name)]
#     #     trace = go.Scatter(
#     #         x = df['localtime'],
#     #         y = df['value'],
#     #         name = name, #get_type(name),
#     #         # fill = "tozeroy",
#     #         )

#     #     trace_houses.append(trace)
        
#     # graphs.append(html.Div(dcc.Graph(
#     #             id='house-demands',
#     #             animate=False,
#     #             figure={'data': trace_houses,
#     #                     'layout' : go.Layout(xaxis= dict(autorange=True),# tickformat= '%y-%-m-%d %H:%M:%S'),
#     #                                         yaxis=dict(autorange=True, title='Power (VA)'),
#     #                                         margin={'l':50,'r':1,'t':45,'b':50},
#     #                                         title='Power Demands')}
#     #             ), className='col s12 m6 l6'))

    

#     # graph for flexibility
#     trace_avgflex = go.Scatter(
#         x = flex_avg['localtime'],
#         y = flex_avg['value'],
#         name = 'Average',
#         )

#     trace_minflex = go.Scatter(
#         x = flex_min['localtime'],
#         y = flex_min['value'],
#         name = 'Minimum',
#         )

#     trace_maxflex = go.Scatter(
#             x = flex_max['localtime'],
#             y = flex_max['value'],
#             name = 'Maximum',
#             )


#     # combining plots
#     trace_flexibility = [trace_avgflex, trace_minflex, trace_maxflex]
    
#     graphs.append(html.Div(dcc.Graph(
#                 id='flexibility',
#                 animate=False,
#                 figure={'data': trace_flexibility,
#                         'layout' : go.Layout(xaxis= dict(autorange=True),
#                                             yaxis=dict(autorange=True, title='Flexibility'),
#                                             margin={'l':50,'r':1,'t':45,'b':50},
#                                             title= 'Flexibility of '+ str(n_houses) + ' Houses',
#                                             )
#                         }
#                 ), className='col s12 m12 l12'))


#     return graphs

