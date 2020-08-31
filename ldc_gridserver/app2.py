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
VALID_USERNAME_PASSWORD_PAIRS = [
    ['user', 'pass'],
    ['superuser', 'superpass']
]

app = dash.Dash('auth')
auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)



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







def get_data(db_name='ldc.db', duration=60*60, report=False):
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
# define all colors
colors = []
for a in cl.scales:
    for b in cl.scales[a]:
        for c in cl.scales[a][b]:
            colors.append(cl.scales[a][b][c])



global capacity, latest_demand, ldc_signal, house_names, percent_loading
global n_houses, house_names, parameter_names, target_loading

df_data_init = get_data(db_name='ldc.db', duration=60)
df_actual = df_data_init[df_data_init['state']=='actual']
df_actual = df_actual[df_actual['parameter']=='total']  
df_actual_sum = df_actual[['unixtime','value']].astype(float).groupby(['unixtime']).sum()
latest_demand = df_actual_sum['value'].tail(1).values
ldc_signal = 860.0
percent_loading = 1.0
n_houses = len(np.unique(df_data_init['house']))
gridUtilizationFactor =  1 #0.8**(0.9 * np.log(n_houses))
capacity = n_houses * 10000 * gridUtilizationFactor    
target_loading = percent_loading * capacity
house_names = np.unique(df_data_init['house'])
# device_names = np.unique(df_data_init['type'])
parameter_names = np.unique(df_data_init['parameter'])

dict_names = {
    "house_names": house_names,
    # "device_names": device_names,
    "parameter_names": parameter_names,
}

### -------------------------------------------------------

app.layout = html.Div(children=[
    dcc.Location(id='url', refresh=False),
    get_logo(),
    html.Div([
        html.H2("LDC Microgrid Status", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
        ], 
        className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
    ),
    
    html.Div([
        html.Div([
            html.Label('Target loading (kVA):', 
                className='row',
                style={'color':'white', 'display':'inline-block', 'width':'100%', 'margin':'3'}),
            html.Div(id='cmd-loading', children=str(np.round(target_loading/1000, 2)), 
                style={'font-size':'xx-large', 'color':'white', 'text-align':'center', 'display':'inline-block', 'width':'100px', 'margin':'3'}),
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
                style={'width':'100%', 'display':'inline-block', 'margin':'3'}),
            html.Button('Submit', id='button', style={'width':'100px', 'display':'inline-block', 'margin':'3'}),
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
                            {"label": "Constant", "value": "A0"},
                            {"label": "Offset", "value": "A1"},
                            {"label": "Percentage", "value": "A2"},
                        ],
                value="A2",
                className='row',
                style={'color':'white', 'margin':'3'}
            ),
          
            ], 
            className='row',
            # style={'display':'inline-block'}
        ),

        ], 
        className='col s12 m12 l2',
        style={'display': 'inline-block', 'margin':'3', 'float':'left'}
    ),
    



    html.Div([
        html.Div(children=html.Div(id='graphs'), className='row',),
        # dcc.Interval(id='graph-update', interval=3*1000),
        
        # hidden update for sending ldc command signal
        html.Div(children=html.Div(id='command'), style={'display': 'none'}),
        # dcc.Interval(id='cmd-update', interval=3*1000),

        ], 
        className='col s12 m12 l7',
        style={'width':'80%', 'display':'inline-block', 'padding':'3px'},
    ),
    
    # hidden div: holder of data
    html.Div([
        html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0'}),
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
    dash.dependencies.Output('cmd-loading', 'children'),
    [dash.dependencies.Input('button', 'n_clicks')],
    [dash.dependencies.State('input-cmd-loading', 'value')])
def update_output(n_clicks, value):
    return value



@app.callback(
    dash.dependencies.Output('data','children'),
    events=[dash.dependencies.Event('data-update','interval')]
    )
def update_data():
    # global df_data #, latest_demand, capacity
    
    df_data = get_data(duration=60*60*8)
    
    return df_data.to_json(orient='split')





@app.callback(
        dash.dependencies.Output('command','children'),
        [dash.dependencies.Input('cmd-algorithm','value'),
        dash.dependencies.Input('cmd-loading','children'),
        dash.dependencies.Input('data','children'),],
        # events=[dash.dependencies.Event('cmd-update','interval')],
        )
def update_command(cmd_algorithm, cmd_loading, json_data):
    global latest_demand, capacity, ldc_signal, percent_loading, target_loading
    
    df_data = pd.read_json(json_data, orient='split')
    target_loading = float(cmd_loading) * 1000 # converted to Watts
    percent_loading = target_loading / capacity
    # print(percent_loading, target_loading, capacity)
      
    try:
        df_data = df_data[df_data['parameter']=='actual']
        df_data_sum = df_data[['unixtime','value']].astype(float).groupby(['unixtime']).sum()
        latest_demand = df_data_sum['value'].tail(1).values

        n_houses = len(np.unique(df_data['house']))
        gridUtilizationFactor =  1#0.8**(0.9 * np.log(n_houses))
        capacity = n_houses * 10000 * gridUtilizationFactor #[kW]  
        
        
        offset = np.nan_to_num(1 - (latest_demand / (target_loading)))[0]

    except:
        offset = 0

    ldc_upper = 860
    ldc_lower = 760
    ldc_center = 810 
    ldc_bw = ldc_upper - ldc_lower  # bandwidth
    w_past = 0.1  # weight given to the past signal, acting as a damper to change in ldc_signal

    try:
        if cmd_algorithm=='A0':
            ldc_signal=ldc_upper
            # update_ldc_db.command(cmd=cmd_algorithm, freq=ldc_signal, report=False)

            
        elif cmd_algorithm=='A1':
            ldc_signal_new = float(ldc_center + ((ldc_bw) * offset * 0.1))
            ldc_signal = (w_past * ldc_signal) + ((1-w_past) * ldc_signal_new)
            ldc_signal = np.min([ldc_signal, 860])
            ldc_signal = np.max([ldc_signal, 760])
            # update_ldc_db.command(cmd=cmd_algorithm, freq=ldc_signal, report=False)
            
        elif cmd_algorithm=='A2':
            ldc_signal = float(760 + (ldc_bw * percent_loading))
            ldc_signal = np.min([ldc_signal, 860])
            ldc_signal = np.max([ldc_signal, 760])
            # update_ldc_db.command(cmd=cmd_algorithm, freq=ldc_signal, report=False)
            
        else: # default is 'A1'
            ldc_signal_new = float(ldc_center + ((ldc_bw) * offset))
            ldc_signal = (w_past * ldc_signal) + ((1-w_past) * ldc_signal_new)
            ldc_signal = np.min([ldc_signal, 860])
            ldc_signal = np.max([ldc_signal, 760])
        
        n_rows = len(df_data.index)    
        # df_data = df_data.append(update_ldc_db.command(cmd='Q', freq=ldc_signal, save=False, report=False))

        send(dict_msg={cmd_algorithm:ldc_signal}, ip='224.0.2.0', port=10000 )

        # print(cmd_algorithm, cmd_loading, ldc_signal, latest_demand, target_loading, offset)        
    except Exception as e:
        print("Error in dash_app update_command:", e)

    return





@app.callback(
    dash.dependencies.Output('graphs','children'),
    [dash.dependencies.Input('data', 'children'),
    ],
    # events=[dash.dependencies.Event('graph-update', 'interval')]
    )
def update_graph(json_data):
    global latest_demand, capacity, house_names, target_loading

    df_data = pd.read_json(json_data, orient='split')

    graphs = []
    data_agg = []
    data_house = []
    data_device = []
    data_soc = []

    # df_data = pd.read_json(json_data)
    house_list = np.unique(df_data['house'])
    times_sorted = df_data[['unixtime', 'value']].groupby(['unixtime']).sum() 
    times = [datetime.datetime.fromtimestamp(float(t)) for t in times_sorted.index]

    # graph for aggregation------------------------------
    # actual demand
    df_actual = df_data[df_data['state']=='agg']
    df_actual = df_actual[df_actual['parameter']=='actual']  
    # print(df_actual)
    df_actual_sum = df_actual[['unixtime','value']].astype(float).groupby(['unixtime']).sum()
    # print(df_actual_sum)
    data_actual = go.Scatter(
        x = times,
        y = df_actual_sum['value'],
        name = 'With LDC',
        fill = "tozeroy",
        )

    # proposed demand
    df_proposed = df_data[df_data['state']=='agg']
    df_proposed = df_proposed[df_proposed['parameter']=='proposed']  
    df_proposed_sum = df_proposed[['unixtime','value']].astype(float).groupby(['unixtime']).sum()
    data_proposed = go.Scatter(
        x = times,
        y = df_proposed_sum['value'],
        name = 'No LDC',
        fill = "tozeroy", # "tonexty"
        )

    # power limit
    df_limit = df_data[df_data['state']=='agg']
    df_limit = df_limit[df_limit['parameter']=='limit']  
    df_limit_sum = df_limit[['unixtime','value']].astype(float).groupby(['unixtime']).sum()
    data_limit = go.Scatter(
        x = times,
        y = df_limit_sum['value'],
        name = 'Limit',
        )

    # print(len(df_actual_sum.index), len(df_proposed_sum.index), len(df_limit_sum.index))
    # combining plots
    data_agg = [data_proposed, data_actual, data_limit]

    graphs.append(html.Div(dcc.Graph(
                id='aggregation',
                animate=False,
                figure={'data': data_agg,
                        'layout' : go.Layout( height=450,
                                xaxis= dict(autorange=True, showgrid=False), #range=[times[0], times[-1]]),# tickformat= '%y-%-m-%d %H:%M:%S'),
                                yaxis=dict(autorange=True, showgrid=True, title='Power (VA)'),
                                margin={'l':50,'r':50,'t':45,'b':50},
                                title= 'Total Demand:'+str(len(house_list)) + ' Houses',
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





    # graph for house demands ------------------------------------------------------
    max_y = 7000
    min_y = 0
    df_total = df_data[df_data['state']=='agg']
    df_total = df_total[df_total['house'].isin(list(house_names))]
    df_total = df_total[df_total['parameter']=='actual']


    # for name in house_names:
    for i in range(len(house_names)):
        df = df_total[df_total['house'].isin(house_names[i:i+1])]
        # df = df_total[df_total['house'].isin(house_names[:i])]
        # df = df[['unixtime','value']].astype(float).groupby(['unixtime']).sum()
        
        trace = go.Scatter(
            x = times,
            y = df['value'],
            name = house_names[i],
            mode = 'lines',
            # fill = 'tonexty',
            )

        data_house.append(trace)
        
        current_max = float(np.max(df['value'].values.astype(float))) * 1.03
        current_min = float(np.min(df['value'].values.astype(float)))
        max_y = np.max([current_max, max_y]) 
        min_y = np.min([current_min, min_y])
        

    graphs.append(html.Div(dcc.Graph(
                id='house-demands',
                animate=False,
                figure={'data': data_house,
                        'layout' : go.Layout(xaxis= dict(autorange=True),# tickformat= '%y-%-m-%d %H:%M:%S'),
                                            yaxis=dict(autorange=True, title='Power (VA)'),
                                            margin={'l':50,'r':1,'t':45,'b':50},
                                            title= 'House Demands')}
                ), className='col s12 m12 l12'))



    # graph for flexibility
    i = 0
    max_y = 1.03
    min_y = 0
    df_flexibility = df_data[df_data['house'].isin(list(house_names))]
    df_flexibility = df_flexibility[(df_flexibility['parameter']=='flexibility')]
    df_flexibility_mean = df_flexibility[['unixtime','value']].astype(float).groupby(['unixtime']).mean()

    data_flex = go.Scatter(
        x = df_flexibility_mean.index,
        y = df_flexibility_mean['value'],
        name = 'Average flexibility',
        fill = 'tozeroy'
        )


    # combining plots
    data_flexibility = [data_flex]
    # max_agg = 1.03

    graphs.append(html.Div(dcc.Graph(
                id='flexibility',
                animate=False,
                figure={'data': data_flexibility,
                        'layout' : go.Layout(xaxis= dict(autorange=True), #range=[times[0], times[-1]]),# tickformat= '%y-%-m-%d %H:%M:%S'),
                                            yaxis=dict(range=[0,1.1], title='Flexibility'),
                                            margin={'l':50,'r':1,'t':45,'b':50},
                                            title= 'Average Flexibility of '+str(len(house_list)) + ' Houses',
                                            )
                        }
                ), className='col s12 m12 l12'))


#----------------------------------------------------------------------------
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






# app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})

# external_css = ["https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/css/materialize.min.css"]
# for css in external_css:
#     app.css.append_css({"external_url": css})

# external_js = ['https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/js/materialize.min.js']
# for js in external_css:
#     app.scripts.append_script({'external_url': js})



# external_css = ["https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
#                 "https://cdn.rawgit.com/plotly/dash-app-stylesheets/737dc4ab11f7a1a8d6b5645d26f69133d97062ae/dash-wind-streaming.css",
#                 "https://fonts.googleapis.com/css?family=Raleway:400,400i,700,700i",
#                 "https://fonts.googleapis.com/css?family=Product+Sans:400,400i,700,700i"]

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
    app.run_server(debug=True, host='0.0.0.0', port=15000)