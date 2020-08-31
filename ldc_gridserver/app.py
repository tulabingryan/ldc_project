# from .server import app
# from . import router

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

# multicasting packages
import socket
import struct
import sys
import time
import json
import ast

# local package
import update_ldc_db


app = dash.Dash('streaming-wind-app')
server = app.server



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



# returns logo div
def get_logo():
    image = "images/UOA.png"
    encoded_image = base64.b64encode(open(image, "rb").read())
    logo = html.Div(
        html.Img(
            src="data:image/png;base64,{}".format(encoded_image.decode()), height="57"
        ),
        style={"marginTop": "0", "float":"left"},
        # className="sept columns",
    )
    return logo


def send(dict_msg, ip='224.0.2.0', port=10000 ):
    # send multicast query to all devices in the network
    multicast_group=(ip, port)
    # Create the datagram socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Set a timeout so the socket does not block
    # indefinitely when trying to receive data.
    sock.settimeout(0.00001)

    # Set the time-to-live for messages to 1 so they do not
    # go past the local network segment.
    ttl = struct.pack('b', 1)  # number of hops
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    dict_demand = {}
    x = time.perf_counter()
    dif = 0
    try:
        # Send data to the multicast group 
        message = str(dict_msg).encode()
        counter = time.perf_counter()
        sent = sock.sendto(message, multicast_group)

        count = 0
        # Look for responses from all recipients
        while True:
            try:
                
                count += 1
                data, server = sock.recvfrom(10)

            except socket.timeout:
                
                break
            
            else:
                pass
        
    except Exception as e:
        print("Error in send:", e)

    finally:
        sock.close()

    return







def get_data(db_name='ldc.db', query='aggregated', duration=60*60, report=False):
    """ Fetch data from the local database"""
    counter = 0
    data = []
    while True and counter < 10 and len(data) < 1:
        try:
            con = lite.connect(db_name)
            with con:
                cur = con.cursor()
                # Get the last timestamp recorded
                cur.execute('SELECT unixtime FROM data ORDER BY unixtime DESC LIMIT 1') 
                end = np.array(cur.fetchall()).flatten()[0]
                start = end - duration
                # get the last set of records for a specified duration
                cur.execute('SELECT unixtime, house, parameter, value, state FROM data WHERE unixtime > ? ORDER BY unixtime ASC', (start,)) 
                data = np.array(cur.fetchall())
                df_data = pd.DataFrame(data, columns=['unixtime', 'house', 'parameter', 'value', 'state'])
                    

            break
        except Exception as e:
            print("Error in get_data:", e)
            counter += 1

    if report: 
        print(df_data['parameter'].tail(50))
        
    return df_data



### GLOBAL VARIABLES ----------------------------------
global ldc_signal, percent_loading, n_houses, capacity, target_loading
df_data_init = get_data(db_name='ldc.db', query='aggregated', duration=1)
# print(df_data_init)
ldc_signal = 860.0
percent_loading = 1.0
# n_houses = float(df_data_init['n_houses'].values) #len(np.unique(df_data_init['house']))
n_houses = 1
gridUtilizationFactor =  1 #0.8**(0.9 * np.log(n_houses))
capacity = n_houses * 5000 * gridUtilizationFactor    
target_loading = percent_loading * capacity

### -------------------------------------------------------

app.layout = html.Div(children=[
    dcc.Location(id='url', refresh=False),
    get_logo(),
    html.Div([
        html.H2("LDC Microgrid Status", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
        ], 
        className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
    ),
    
    # # tabs
    # html.Div([

    #     dcc.Tabs(
    #         id="tabs",
    #         style={"height":"20","verticalAlign":"middle"},
    #         children=[
    #             dcc.Tab(label="Opportunities", value="opportunities_tab"),
    #             dcc.Tab(label="Leads", value="leads_tab"),
    #             dcc.Tab(id="cases_tab",label="Cases", value="cases_tab"),
    #         ],
    #         value="leads_tab",
    #     )

    #     ],
    #     className="row tabs_div"
    #     ),
   

    html.Div([
        html.Div([
            html.Label('Target loading:', 
                className='row',
                style={'color':'white', 'display':'inline-block', 'width':'100%', 'margin':'3'}),
            html.Div(id='cmd-loading', children=str(np.round(target_loading/1000, 2)), 
                style={'font-size':'xx-large', 'color':'white', 'text-align':'right', 'display':'inline-block', 'width':'30%', 'padding':'9'}),
            html.Div(id='cmd-loading-unit', children='kVA', 
                style={'font-size':'xx-large', 'color':'white', 'text-align':'left', 'display':'inline-block', 'width':'30%', 'padding':'9'}),
            ], 
            className='row',
        ),


        # html.H2('',
        #     className='row',
        #     ),

        html.Div([
            html.Label('Change loading (kVA):', 
                className='row',
                style={'width':'100%', 'color':'white', 'display':'inline-block', 'margin':'3'}),
            dcc.Input(id='input-cmd-loading', 
                value=np.round(target_loading/1000, 2), # converted to kW
                disabled=False, 
                type='number', 
                min=0, max= np.round(capacity * 1.5 / 1000, 2), # converted to kW
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
                            {"label": "Integral Loop", "value": "A2"},
                            {"label": "Decentralized", "value": "A3"},
                        ],
                value="A2",
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
    

    html.Div([
        html.Div(children=html.Div(id='graphs'), className='row',),
        # dcc.Interval(id='graph-update', interval=3*1000),
        
        # hidden update for sending ldc command signal
        html.Div(children=html.Div(id='command'), style={'display': 'none'}),
        dcc.Interval(id='cmd-update', interval=1*1000),

        ], 
        className='col s12 m12 l7',
        style={'width':'80%', 'display':'inline-block', 'padding':'3px'},
    ),
    
    # hidden div: holder of data
    html.Div([
        html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0', 'display':'none'}),
        dcc.Interval(id='data-update', interval=2.1*1000),
        ], 
        className='row', 
        style={'display':'none',},
    ),
        
    
    
    
    ],

    style={'display':'inline-block', "backgroundColor": "#18252E", 'width':'100%'} 
    # style={'padding': '0px 10px 15px 10px',
    #       'marginLeft': 'auto', 'marginRight': 'auto', "width": "900px",
    #       'boxShadow': '0px 0px 5px 5px rgba(204,204,204,0.4)'}
)



@app.callback(
    dash.dependencies.Output('data','children'),
    # [],[dash.dependencies.State('graphs', 'children')],
    events=[dash.dependencies.Event('data-update','interval')])
def update_data():
    # print(graph_figures)
    df_data = get_data(duration=60*60*8)
        
    return df_data.to_json(orient='split')



@app.callback(
    dash.dependencies.Output('cmd-loading', 'children'),
    [dash.dependencies.Input('button', 'n_clicks')],
    [dash.dependencies.State('input-cmd-loading', 'value')])
def update_output(n_clicks, value):
    return value




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






@app.callback(
        dash.dependencies.Output('command','children'),
        [dash.dependencies.Input('cmd-algorithm','value'),
        dash.dependencies.Input('cmd-loading','children'),
        dash.dependencies.Input('data','children'),])
def update_command(cmd_algorithm, cmd_loading, json_data):
    try:
        dict_newdata = send_command(dict_cmd={cmd_algorithm:ldc_signal}, ip='localhost', port=10000)

        # print(cmd_algorithm, percent_loading, ldc_signal, latest_demand, target_loading, offset)        
    except Exception as e:
        print("Error in dash_app update_command:", e)
        dict_newdata = {}

    return json.dumps(dict_newdata)





@app.callback(
    dash.dependencies.Output('graphs','children'),
    [dash.dependencies.Input('data', 'children')],)
def update_graph(json_data):
    df_data = pd.read_json(json_data, orient='split')
    n_houses = int(df_data['n_houses'].tail(1).values)

    graphs = []
    
    # graph for aggregation------------------------------
    # actual demand
    trace_actual = go.Scatter(
        x = df_data['localtime'],
        y = df_data['actual'],
        name = 'With LDC',
        fill = "tozeroy",
        )

    # proposed demand
    trace_proposed = go.Scatter(
        x = df_data['localtime'],
        y = df_data['proposed'],
        name = 'No LDC',
        fill = "tozeroy", # "tonexty"
        )

    # power limit
    trace_limit = go.Scatter(
        x = df_data['localtime'],
        y = df_data['limit'],
        name = 'Limit',
        )

    # combining plots
    trace_agg = [trace_proposed, trace_actual, trace_limit]

    graphs.append(html.Div(dcc.Graph(
                id='aggregation',
                animate=False,
                figure={'data': trace_agg,
                        'layout' : go.Layout( height=450,
                                xaxis= dict(autorange=True, showgrid=False),
                                yaxis=dict(autorange=True, showgrid=True, title='Power (VA)'),
                                margin={'l':50,'r':50,'t':45,'b':50},
                                title= 'Total Demand:'+str(n_houses) + ' Houses',
                                )
                        }
                ), 
                className='col s12 m12 l12',
                # style = {
                #     "position": "relative",
                #     "float": "left",
                #     "border": "1px solid",
                #     "borderColor": "rgba(68,149,209,.9)",
                #     "overflow": "hidden",
                #     "marginBottom": "2px",
                # },
                ),
    )

    # plot demands of individual devices
    device_names = np.unique(device_demand['id'])
    trace_devices = []
    for name in device_names:
        df = device_demand[(device_demand['id']==name)]
        trace = go.Scatter(
            x = df['localtime'],
            y = df['value'],
            name = name, #get_type(name),
            # fill = "tozeroy",
            )

        trace_devices.append(trace)
        
    graphs.append(html.Div(dcc.Graph(
                id='device-demands',
                animate=False,
                figure={'data': trace_devices,
                        'layout' : go.Layout(xaxis= dict(autorange=True),# tickformat= '%y-%-m-%d %H:%M:%S'),
                                            yaxis=dict(autorange=True, title='Power (VA)'),
                                            margin={'l':50,'r':1,'t':45,'b':50},
                                            title='Power Demands')}
                ), className='col s12 m6 l6'))

    


    # add space after one graph layout
    graphs.append(html.H2('', className='row',),)



    # graph for flexibility
    trace_flex = go.Scatter(
        x = df_data['localtime'],
        y = df_data['flexibility'],
        name = 'Average flexibility',
        fill = 'tozeroy'
        )


    # combining plots
    trace_flexibility = [trace_flex]
    
    graphs.append(html.Div(dcc.Graph(
                id='flexibility',
                animate=False,
                figure={'data': trace_flexibility,
                        'layout' : go.Layout(xaxis= dict(autorange=True),
                                            yaxis=dict(autorange=True, title='Flexibility'),
                                            margin={'l':50,'r':1,'t':45,'b':50},
                                            title= 'Average Flexibility of '+str(n_houses) + ' Houses',
                                            )
                        }
                ), className='col s12 m12 l12'))



    
    # for name in device_names:
    #     df = df_device[(df_device['id']==name)]
    #     trace = go.Scatter(
    #         x = times,
    #         y = df['value'],
    #         name = name,
    #         line = dict(color = colors[i][i]), # colors are predefined as global
    #         # opacity = 0.8,

    #         # fill = "tozeroy",
    #         # fillcolor = colors[i]#"#6897bb"
    #         )

    #     i += 1
    #     data_device.append(trace)
        
    #     current_max = np.max(df['value'])
    #     current_min = np.min(df['value'])
    #     max_y = np.max([float(current_max), max_y]) * 1.03
    #     min_y = np.min([float(current_min), min_y])
        
    
    
    # graphs.append(html.Div(dcc.Graph(
    #             id='device-demands',
    #             animate=False,
    #             figure={'data': data_device,
    #                     'layout' : go.Layout(xaxis= dict(range=[times[0], times[-1]]),# tickformat= '%y-%-m-%d %H:%M:%S'),
    #                                                         yaxis=dict(autorange=True, title='Power (VA)'),
    #                                                         margin={'l':50,'r':1,'t':45,'b':50},
    #                                                         title= 'Demands: '+ str(device_type))}
    #             ), className='col s12 m6 l6'))






    # # graph for device demands
    # i = 0
    # max_y = 0
    # min_y = 0
    # df_device = df_data[df_data['type']==device_type]
    # df_device = df_device[df_device['house'].isin(list(house_names))]
    # df_device = df_device[(df_device['parameter']=='demand')]
    # device_names = np.unique(df_device['id'])

    # # print(device_names)
    # for name in device_names:
    #     df = df_device[(df_device['id']==name)]
    #     trace = go.Scatter(
    #         x = times,
    #         y = df['value'],
    #         name = name,
    #         line = dict(color = colors[i][i]), # colors are predefined as global
    #         # opacity = 0.8,

    #         # fill = "tozeroy",
    #         # fillcolor = colors[i]#"#6897bb"
    #         )

    #     i += 1
    #     data_device.append(trace)
        
    #     current_max = np.max(df['value'])
    #     current_min = np.min(df['value'])
    #     max_y = np.max([float(current_max), max_y]) * 1.03
    #     min_y = np.min([float(current_min), min_y])
        
    
    
    # graphs.append(html.Div(dcc.Graph(
    #             id='device-demands',
    #             animate=False,
    #             figure={'data': data_device,
    #                     'layout' : go.Layout(xaxis= dict(range=[times[0], times[-1]]),# tickformat= '%y-%-m-%d %H:%M:%S'),
    #                                                         yaxis=dict(autorange=True, title='Power (VA)'),
    #                                                         margin={'l':50,'r':1,'t':45,'b':50},
    #                                                         title= 'Demands: '+ str(device_type))}
    #             ), className='col s12 m6 l6'))




    # # graph for device soc
    # i = 0
    # max_y = 0
    # min_y = 0
    # df_device = df_data[df_data['type']==device_type]
    # df_device = df_device[df_device['house'].isin(list(house_names))]
    # df_device = df_device[df_device['parameter']=='soc']
    # device_names = np.unique(df_device['id'])
    # df_device['value'] = [float(a)*100 for a in df_device['value']] 
    # for name in device_names:
    #     df = df_device[(df_device['id']==name)]
    #     trace = go.Scatter(
    #         x = times,
    #         y = df['value'],
    #         name = name,
    #         line = dict(color = colors[i][i]), # colors are predefined as global
    #         # opacity = 0.8,

    #         # fill = "tozeroy",
    #         # fillcolor = colors[i]#"#6897bb"
    #         )

    #     i += 1
    #     data_soc.append(trace)
        
    #     current_max = np.max(df['value'])
    #     current_min = np.min(df['value'])
    #     max_y = np.max([float(current_max), max_y]) * 1.03
    #     min_y = np.min([float(current_min), min_y])
        
    
    
    # graphs.append(html.Div(dcc.Graph(
    #             id='device-soc',
    #             animate=False,
    #             figure={'data': data_soc,
    #                     'layout' : go.Layout(xaxis= dict(range=[times[0], times[-1]]),# tickformat= '%y-%-m-%d %H:%M:%S'),
    #                                                         yaxis=dict(autorange=True, title='State of Charge (%)'),
    #                                                         margin={'l':50,'r':1,'t':45,'b':50},
    #                                                         title= 'State Of Charge: '+ str(device_type))}
    #             ), className='col s12 m6 l6'))




    return graphs








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
    app.run_server(debug=True, host='0.0.0.0', port=15003)