import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, Event
import plotly.plotly as py
from plotly.graph_objs import *
from scipy.stats import rayleigh
from flask import Flask
import numpy as np
import pandas as pd
import os
import sqlite3 as lite
import datetime
import time
import base64

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


# import update_ldc_db

import base64



app = dash.Dash('streaming-wind-app')
server = app.server


def my_round(x, prec=5, base=5): 
    prec = int(prec)
    base = float(base)
    return (base * (np.array(x).astype(float) / base).round()).round(prec)

def get_season(date_time, db_source='trace'):
    # determine the season based on the date
    # df_source = the location of the source of the load profile
    # 'refit' = from UK
    # 'dred' = from Netherlands
    # 'trace' = from Germany
    month = date_time.month 
    if db_source in ['trace', 'refit', 'dred']:
        seasons = {3:'spring', 4:'spring', 5:'spring',
                6:'summer', 7:'summer', 8:'summer',
                9:'autumn', 10:'autumn', 11:'autumn',
                12:'winter', 1:'winter', 2:'winter'}
        

    elif db_source in ['nz']:
        seasons = {9:'spring', 10:'spring', 11:'spring',
                12:'summer', 1:'summer', 2:'summer',
                3:'autumn', 4:'autumn', 5:'autumn',
                6:'winter', 7:'winter', 8:'winter'}

    season_code = {'spring':0, 'summer':1, 'autumn':2, 'winter':3}

    return season_code[seasons[month]]




def get_logo():
    image = "UOA.png"
    encoded_image = base64.b64encode(open(image, "rb").read())
    logo = html.Div(
        html.Img(
            src="data:image/png;base64,{}".format(encoded_image.decode()), height="57"
        ),
        style={"marginTop": "0", "float":"left"},
        # className="sept columns",
    )
    return logo




def classify_device(db_name='load_profiles.db', report=False):
    """ Define different states for all devices in tha database""" 
    try:
        df_dev_class = pd.read_csv('./dev_class.csv')

    except Exception as e:
        con = lite.connect(db_name)
        with con:
            cur = con.cursor()
            cur.execute('SELECT DISTINCT device_type, device_id, date_only FROM load_profiles LIMIT 100000')
            dev_class = np.array(cur.fetchall())
        
        df_dev_class = pd.DataFrame(dev_class, columns=['device_type', 'device_id', 'date_only'])
        df_dev_class.to_csv('./dev_class.csv')
    if report: print(df_dev_class)
    return df_dev_class


df_dev_class = classify_device(report=False)




app.layout = html.Div(children=[
    # dcc.Location(id='url', refresh=False),

    # Banner
    get_logo(),
    html.Div([
        html.H2("Load Demand Profile", style={'marginTop':'5', 'text-align':'center','float':'center', 'color':'white'}),
        # Settings
        html.Div([
            html.Label('Device type:', style={'color':'white', 'display':'inline-block', 'text-align':'center'}),
            dcc.Dropdown(id='device-type', 
                options=[{'label': x, 'value': x} for x in np.unique(df_dev_class['device_type'].values)],
                value=df_dev_class.loc[0, 'device_type'],
                multi=False,
                clearable=False,
            ),
            
            ], className='row', style={'width':'20%', 'display':'inline-block', 'margin':'2'}
        ),


        html.Div([
            html.Label('Device id:', style={'color':'white', 'display':'inline-block', 'text-align':'center'}),
            dcc.Dropdown(id='device-id', 
                multi=False,
                clearable=False,
            ),
            
            ], className='row', style={'width':'20%', 'display':'inline-block', 'margin':'2'}
        ),

        html.Div([
            html.Label('Date:', style={'color':'white', 'display':'inline-block', 'text-align':'center'}),
            dcc.Dropdown(id='date', 
                multi=False,
                clearable=False,
            ),
            
            ], className='row', style={'width':'20%', 'display':'inline-block', 'margin':'2'}
        ),

        html.Div([
            html.Label('Resolution:', style={'color':'white', 'display':'inline-block', 'text-align':'center'}),
            dcc.Dropdown(id='resolution', 
                multi=False,
                clearable=False,
                options=[{'label':x, 'value':x} for x in ['1', '2', '3', '4', '5', '10', '15', '20', '25', '30', '40', '50', '100', '1000']],
                value='1',
                
            ),
            
            ], className='row', style={'width':'20%', 'display':'inline-block', 'margin':'2'}
        ),


        ], 
        className='banner', style={'width':'100%', 'display':'inline-block',"backgroundColor": "#18252E",}
    ),
    

    # hidden div: holder of data
    html.Div([
        html.Div(children=html.Div(id='data'), className='row', style={'opacity':'1.0'}),
        ], 
        className='row', style={'width':'100%', 'display':'none', 'float':'left', 'marginTop':'2%', 'marginBottom':'2%', 'marginLeft':'2%', 'marginRight':'2%'}
    ),
      


    html.Div([
        html.Div([
                html.H3("POWER DEMAND")
            ], className='Title', style={'color':'white'}),

        html.Div(children=html.Div(id='graphs'), className='row', style={'opacity':'1.0'}),
        # dcc.Interval(id='graph-update', interval=30*1000),
        
        ], 
        className='col s12 m10 l10',
        style={'display':'inline-block', 'position':'relative', 'width':'90%', 'float':'center', 'padding':'3%'},
    ),
    

    html.Div([
            html.Div([
                html.H3("HISTOGRAM")
            ], className='Title', style={'color':'white'}),
            html.Div([
                dcc.Slider(
                    id='bin-slider',
                    min=1,
                    max=60,
                    step=1,
                    value=16,
                    updatemode='drag'
                ),
            ], className='histogram-slider', style={'color':'white'}),
            html.P('# of Bins: Auto', id='bin-size', className='bin-size', style={'color':'white'}),
            html.Div([
                dcc.Checklist(
                    id='bin-auto',
                    options=[
                        {'label': 'Auto', 'value': 'Auto'}
                    ],
                    values=['Auto']
                ),
            ], className='bin-auto', style={'color':'white'}), 
            dcc.Graph(id='demand-histogram'),
        ], 
        className='col s12 m10 l10',
        style={'display':'inline-block', 'position':'relative', 'width':'90%', 'float':'center', 'padding':'3%'},
    ),    
    
    ],

    style={'display':'inline-block', "backgroundColor": "#18252E", 'width':'100%'} ,
)



# automatically change dropdown options for device_id based on selected device_type
@app.callback(
    dash.dependencies.Output('device-id', 'options'),
    [dash.dependencies.Input('device-type', 'value')])
def set_device_options(selected_device_type):
    return [{'label': i, 'value': i} for i in np.unique(df_dev_class[df_dev_class['device_type']==selected_device_type]['device_id'])]

@app.callback(
    dash.dependencies.Output('device-id', 'value'),
    [dash.dependencies.Input('device-id', 'options')])
def set_device_value(available_options):
    return available_options[0]['value']

# automatically change dropdown options for date based on selected device_type and device_id
@app.callback(
    dash.dependencies.Output('date', 'options'),
    [dash.dependencies.Input('device-type', 'value'),
    dash.dependencies.Input('device-id', 'value')])
def set_date_options(device_type, device_id):
    return [{'label': i, 'value': i} for i in np.unique(df_dev_class[(df_dev_class['device_type']==device_type) & (df_dev_class['device_id']==device_id)]['date_only'])]

@app.callback(
    dash.dependencies.Output('date', 'value'),
    [dash.dependencies.Input('date', 'options')])
def set_date_value(available_options):
    return available_options[0]['value']





@app.callback(
    dash.dependencies.Output('data','children'),
    [dash.dependencies.Input('device-type', 'value'),
    dash.dependencies.Input('device-id', 'value'),
    dash.dependencies.Input('date', 'value'),
    dash.dependencies.Input('resolution', 'value')],
    )
def get_data(device_type, device_id, date, resolution):
    con = lite.connect('load_profiles.db')
    with con:
        cur = con.cursor()
        cur.execute('SELECT * FROM data WHERE device_type=? AND device_id=? AND date_only=? LIMIT 100000', (device_type, device_id, date))
        p = np.array(cur.fetchall())
        df_data = pd.DataFrame(p, columns=['date_time', 'power_avg', 'power_inst', 'device_type', 'device_id', 'date_only'])
        df_data[['power_avg', 'power_inst', ]] = df_data[['power_avg', 'power_inst', ]].astype(float)
        df_data['power_avg'] = my_round(df_data['power_avg'], prec=2, base=resolution)
        df_data['power_inst'] = my_round(df_data['power_inst'], prec=2, base=resolution)
        df_selected = df_data[(df_data['power_avg'] > 0)]
        df_selected = df_selected.reset_index()

        start = df_selected.loc[0, 'date_time']
        end = df_selected.loc[len(df_selected.index)-1, 'date_time']

        df_data = df_data[(df_data['date_time'] >= start) & (df_data['date_time'] <= end)]

        df_data = df_data.reset_index()
        df_data['day_of_week'] = [x.weekday() for x in pd.to_datetime(df_data['date_time'])]  # day of the week
        df_data['second_of_day'] = [(x.hour * 3600) + (x.minute * 60) + (x.second) for x in pd.to_datetime(df_data['date_time'])]
        df_data['hour_of_day'] = [(x.hour) + (x.minute / 60) + (x.second / 3600) for x in pd.to_datetime(df_data['date_time'])]
        df_data['season'] = [get_season(x) for x in pd.to_datetime(df_data['date_time'])]

        # df_csv = pd.DataFrame([])
        # sec0 = df_data.loc[0, 'second_of_day'].values
        # sec1 = df_data.loc[df_data.index[-1], 'second_of_day'].values
        # df_csv['second_of_day'] = [x for x in range(sec0, sec1)]

        print(df_data[['day_of_week', 'second_of_day', 'hour_of_day', 'season']])

        print(df_data[['second_of_day', 'power_inst']].interpolate())
        df_data[['day_of_week', 'second_of_day', 'hour_of_day', 'season', 'power_inst']].to_csv(str(device_type)+'_'+str(device_id)+'_'+str(date)+'.csv')

    return df_data.to_json(orient='split')



@app.callback(
    dash.dependencies.Output('graphs','children'),
    [dash.dependencies.Input('data', 'children'),
    dash.dependencies.Input('resolution', 'value')],
    )
def update_graph(json_data, resolution):
    graphs = []
    df_data = pd.read_json(json_data, orient='split')
    
    # graph
    trace1 = go.Scatter(
        x = df_data['date_time'],
        y = np.round(df_data['power_inst'],int(-np.log10(int(resolution)))),
        name = 'Instantaneous Power',
        mode = 'lines',
        fill = "tozeroy",
        )

    trace2 = go.Scatter(
        x = df_data['date_time'],
        y = np.round(df_data['power_avg'],int(-np.log10(int(resolution)))),
        name = 'Average Power (8sec)',
        mode = 'lines',
        fill = "tozeroy",
        )

    data_agg = [trace1, trace2]


    graphs.append(html.Div(dcc.Graph(
                id='aggregation',
                animate=False,
                figure={'data': data_agg,
                        'layout' : go.Layout(
                                xaxis= dict(autorange=True, showgrid=False), 
                                yaxis=dict(autorange=True, showgrid=True, title='Power (W)'),
                                margin={'l':50,'r':50,'t':45,'b':50},
                                title= 'Power Demand Curve: ' + df_data.loc[0,'device_type'],

                                )
                        }
                ), 
                className='col s12 m12 l8',
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


    return graphs


@app.callback(dash.dependencies.Output('demand-histogram', 'figure'),
              # [dash.dependencies.Input('power-demand-update', 'n_intervals')],
            [dash.dependencies.Input('data', 'children'),
            dash.dependencies.Input('resolution', 'value'),
            dash.dependencies.Input('bin-slider', 'value'),],
            [dash.dependencies.State('bin-auto', 'values')]
            )
def power_demand_histogram(json_data, resolution, sliderValue, auto_state):

    power_val = []
    df_data = pd.read_json(json_data, orient='split')
    power_val = df_data['power_inst'].round(int(-np.log10(int(resolution))))

    if 'Auto' in auto_state:
        bin_val = np.histogram(power_val, bins=range(int(round(min(power_val))),
                               int(round(max(power_val)))))
    else:
        bin_val = np.histogram(power_val, bins=sliderValue)

    avg_val = float(sum(power_val.values))/len(power_val.index)
    median_val = np.median(power_val)

    pdf_fitted = rayleigh.pdf(bin_val[1], loc=(avg_val)*0.55,
                              scale=(bin_val[1][-1] - bin_val[1][0])/3)

    y_val = pdf_fitted * max(bin_val[0]) * 20,
    y_val_max = max(y_val[0])
    bin_val_max = max(bin_val[0])

    trace = Bar(
        x=bin_val[1],
        y=bin_val[0],
        marker=Marker(
            color='gray'
        ),
        showlegend=False,
        hoverinfo='x+y'
    )
    trace1 = Scatter(
        x=[bin_val[int(len(bin_val)/2)]],
        y=[0],
        mode='lines',
        line=Line(
            dash='dash',
            color='blue'
        ),
        marker=Marker(
            opacity=1,
        ),
        visible=True,
        name='Average'
    )
    trace2 = Scatter(
        x=[bin_val[int(len(bin_val)/2)]],
        y=[0],
        line=Line(
            dash='dot',
            color='black'
        ),
        mode='lines',
        marker=Marker(
            opacity=1,
        ),
        visible=True,
        name='Median'
    )
    trace3 = Scatter(
        mode='lines',
        line=Line(
            color='magenta'
        ),
        y=y_val[0],
        x=bin_val[1][:len(bin_val[1])],
        name='Rayleigh Fit'
    )
    layout = Layout(
        xaxis=dict(
            title='Power Demand (W)',
            showgrid=False,
            showline=False,
            fixedrange=True
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            title='Number of Samples',
            fixedrange=True
        ),
        margin=Margin(
            t=50,
            b=20,
            r=50
        ),
        autosize=True,
        bargap=0.01,
        bargroupgap=0,
        hovermode='closest',
        legend=Legend(
            x=0.175,
            y=-0.2,
            orientation='h'
        ),
        shapes=[
            dict(
                xref='x',
                yref='y',
                y1=int(max(bin_val_max, y_val_max))+0.5,
                y0=0,
                x0=avg_val,
                x1=avg_val,
                type='line',
                line=Line(
                    dash='dash',
                    color='blue',
                    width=5
                )
            ),
            dict(
                xref='x',
                yref='y',
                y1=int(max(bin_val_max, y_val_max))+0.5,
                y0=0,
                x0=median_val,
                x1=median_val,
                type='line',
                line=Line(
                    dash='dot',
                    color='black',
                    width=5
                )
            )
        ]
    )
    return Figure(data=[trace, trace1, trace2], layout=layout)


@app.callback(dash.dependencies.Output('bin-auto', 'values'), 
            [dash.dependencies.Input('bin-slider', 'value'),
            dash.dependencies.Input('data', 'children')],
            [dash.dependencies.State('bin-slider', 'value')],
            [dash.dependencies.Event('bin-slider', 'change')])
def deselect_auto(sliderValue, json_data, sliderState):
    df_data = pd.read_json(json_data, orient='split')
    power_val = df_data['power_inst']
    if (power_val is not None and
       len(power_val.index) > 5):
        return ['']
    else:
        return ['Auto']

@app.callback(dash.dependencies.Output('bin-size', 'children'),
    [dash.dependencies.Input('bin-auto', 'values')],
    [dash.dependencies.State('bin-slider', 'value')],)
def deselect_auto(autoValue, sliderValue):
    if 'Auto' in autoValue:
        return '# of Bins: Auto'
    else:
        return '# of Bins: ' + str(int(sliderValue))






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
    app.run_server(debug=True, host='0.0.0.0', port=13000)