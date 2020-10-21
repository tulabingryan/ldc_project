##./home_server.py
# -*- coding: utf-8 -*-

from PACKAGES import *


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
global local_ip, subnet, house_name, mcast_ip, mcast_port, df_data, dict_data, date_list
global timezone


try:
    subnet = 5
    dict_data = {}
    date_list = []
    hist_files = glob.glob(f'/home/pi/studies/ardmore/data/H{subnet}*.pkl*')
    list_files = [x.split('/')[-1] for x in hist_files]
    dates = ['-'.join(x.split('.')[0].split('_')[1:]) for x in list_files]    
    dates.sort()
    date_list.extend(dates)
    date_list.extend(['Last 1 Hour'])
    date_list.reverse()
    dict_cmd = read_json(f'/home/pi/ldc_project/ldc_simulator/dict_cmd.txt')
    cmd_algorithm = dict_cmd['algorithm']
    ldc_signal = float(dict_cmd['frequency'])
    history_range = dict_cmd['history']
    gain = dict_cmd['gain']
    timezone = 'Pacific/Auckland'
except Exception as e:
    print(f'Error initialize:{e}')

    
    
    ### set timezone
    # timezone = 'Pacific/Auckland' #get_timezone(latitude, longitude, timestamp=time.time())
    # os.environ['TZ'] = timezone
    # time.tzset()
    # print("Timezone:", timezone)


tabs_styles = {'height': '40px'}
tab_style = {
        'borderTop': '1px solid #18252E',
        'borderBottom': '1px solid #18252E',
        'backgroundColor': '#18252E',
        'color':'white',
        'padding': '10px',
        'hover':{'color':'red'},
        # 'fontWeight': 'bold',
        'text-align':'center',
        # 'float':'center',
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
def get_data(day=None, unixstart=None, unixend=None):
    """ Fetch data from the local database"""
    try:
        if day:
            df_data = pd.read_pickle(f'/home/pi/studies/ardmore/data/H{subnet}_{day}.pkl.xz', compression='infer')    
        else:
            if unixstart: 
                daystart = pd.to_datetime(unixstart, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%Y_%m_%d')
                df_data = pd.read_pickle(f'/home/pi/studies/ardmore/data/H{subnet}_{daystart}.pkl.xz', compression='infer')    
            if unixend:
                dayend = pd.to_datetime(unixstart, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').strftime('%Y_%m_%d')

            if daystart!=dayend:
                df = pd.read_pickle(f'/home/pi/studies/ardmore/data/H{subnet}_{dayend}.pkl.xz', compression='infer')     
                df_data = pd.concat([df_data, df], axis=0)

        float_cols = [x for x in df_data.columns if  not x.startswith('timezone')]
        df_data = df_data[float_cols].astype(float)
        df_data.index = pd.to_datetime(df_data['unixtime'].values, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
        df_data = df_data.resample(f'1S').mean().interpolate()
        return df_data
 
    except Exception as e:
        print(f"Error get_data:{e}")
        
        
    









@app.callback(
    Output('dropdown-history', 'option'),
    [Input('periodic-target-update', 'n_intervals')],
    [])
def update_history_option(n_intervals):
    # change the frequency signal 
    global date_list
    hist_files = glob.glob("/home/pi/studies/ardmore/homeserver/*.pkl*")
    list_files = [x.split('/')[1] for x in hist_files]
    dates = [x.split('.')[0] for x in list_files]
    dates.sort()
    date_list = dates
    date_list.extend(['Last 1 Hour'])
    date_list.reverse()
    return [{'label': x, 'value': x} for x in date_list]  


@app.callback(
    Output('data-update', 'interval'),
    [Input('dropdown-history', 'value')],
    [])
def update_refresh_rate(history_range):
    # set history to put to graph
    if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
        refresh_rate = 10*1000  #[ms]
    else:
        refresh_rate = 600*1000 
    print("Range: {}   Refresh: {}".format(history_range, refresh_rate))
    return refresh_rate


@app.callback(
    Output('hidden-data','data'),
    [Input('data-update','n_intervals'),
    Input('dropdown-history', 'value')],
    [State('hidden-data', 'data')],
    )
def update_data(n_intervals, history_range, json_data):
    ### update the graph
    global cmd_algorithm, cmd_loading, ldc_signal, latest_demand

    if history_range in ['Last 15 Minutes', 'Last 30 Minutes', 'Last 1 Hour', 'Last 2 Hours', 'Last 6 Hours', 'Last 12 Hours', 'Last 24 Hours']:
        hr = history_range.split()
        n_points =  float(hr[1])*60 if hr[-1]=='Minutes' else float(hr[1])*3600
        day = datetime.datetime.now().strftime('%Y_%m_%d')
        unixend = int(time.time())
        unixstart =  int(unixend - n_points)
        
    else:
        n_points = 10000
        day = '_'.join(history_range.split('-'))
        dt_start = pd.to_datetime(history_range).tz_localize('Pacific/Auckland')
        dt_end = dt_start + datetime.timedelta(days=1)
        unixstart =  dt_start.timestamp()
        unixend = dt_end.timestamp()

    # if json_data:
    #     df_data = pd.read_json(json_data, orient='split').astype(float)
    #     ### get upperbound data
    #     if unixend > df_data['unixtime'].max():
    #         s = df_data['unixtime'].max()
    #         e = unixend # np.min([unixend, s+900])
    #         day = datetime.datetime.fromtimestamp(s).strftime('%Y_%m_%d')
    #         new_data = get_data(unixstart=unixstart, unixend=unixend)
    #         if new_data.size:
    #             df_data = pd.concat([df_data, new_data.reset_index()], axis=0, sort='unixtime').reset_index(drop=True)

    #     ### get lowerbound data
    #     if unixstart < df_data['unixtime'].min():
    #         e = df_data['unixtime'].min()
    #         s = unixstart # np.max([unixstart, e-900])
    #         day = datetime.datetime.fromtimestamp(s).strftime('%Y_%m_%d')
    #         new_data = get_data(unixstart=unixstart, unixend=unixend)
    #         if new_data.size:
    #             df_data = pd.concat([new_data.reset_index(), df_data], axis=0, sort='unixtime').reset_index(drop=True)
            
    # else:
    df_data = get_data(unixstart=unixstart, unixend=unixend)
    
    if not df_data.empty:
        df_data = df_data.groupby('unixtime').mean()
        df_data.reset_index(drop=False, inplace=True)
        # df_data = df_data[(df_data['unixtime']>=unixstart) & (df_data['unixtime']<=unixend)]
        
        ### check if meter data is valid
        if ('power_active_0' in df_data.columns):
            df_data['power_active_0'] = df_data['power_active_0'].fillna(0)
            if df_data['power_active_0'].mean() > 0.1:
                with_meter_data = True
            else:
                with_meter_data = False
        else:
            with_meter_data = False

        if with_meter_data:
            df_data['power_kw'] = df_data['power_active_0'] 
            ### clean validate waterheater demand based on meter data
            list_params = [a for a in df_data.columns if a.lower().endswith('demand')]
            list_grainy = [a for a in df_data.columns if (a.lower().endswith('demand') and not (a.lower().startswith('waterheater')) and not (a.lower().startswith('heatpump')))]  # loads emulated in the grainy load bank
            df_data['waterheater_actual_demand'] = np.roll(df_data['waterheater_actual_demand'].values, shift=0) * ((((df_data['power_kw']*1e3) - df_data[list_grainy].sum(axis=1)>1900))*1) + np.random.normal(0, 1, df_data.index.size)
            ### clean heatpump demand using meter data and clean waterheater demand
            list_minus_hp = [a for a in df_data.columns if (a.lower().endswith('demand') and not (a.lower().startswith('heatpump')))]
            df_data['heatpump_actual_demand'] = np.clip(((df_data['power_kw'] * 1000) - np.roll(df_data[list_minus_hp].sum(axis=1), shift=0))-200, a_min=0, a_max=2000)  # assume unaccounted load is 200W, i.e., computer, chroma, etc.
            
        else:
            df_data['power_kw'] = df_data[[x for x in df_data.columns if x.endswith('actual_demand')]].sum(axis=1) * 1e-3
            df_data['power_active_0'] = df_data['power_kw']
            df_data['powerfactor_0'] = np.random.normal(0.9,0.01, df_data.index.size)
            df_data['voltage_0'] = np.random.normal(230,0.1, df_data.index.size)
        
        return  df_data.to_json(orient='split') # limit number of points to 1000 max



@app.callback(
    Output('graphs','children'),
    [Input('hidden-data', 'data')],
    [])
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

        if not df_data.empty:
            df_data = df_data.groupby('unixtime').mean().reset_index(drop=False)
            n_points = df_data['unixtime'].values[-1] - df_data['unixtime'].values[0]
            sample = max([1,int(n_points/5000)])
            # print(df_data[[x for x in df_data.columns if x.startswith('waterheater')]])
            # convert timezone from UTC to local timezone before graph
            df_data.index = pd.to_datetime(df_data['unixtime'].values, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland') #[pd.to_datetime(a, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland').isoformat() for a in df_data['unixtime']]
            df_data.index = df_data.index.tz_localize(None)
            ### resample data to have uniform interval
            df_data = df_data.resample(f'{sample}S').mean() #.bfill() 
            list_zerona = [x for x in df_data.columns if x.endswith('demand')]
            list_zerona.extend(['power_kw', 'power_active_0'])
            list_zerona.extend([x for x in df_data.columns if x.endswith('status')])
            list_avgna = [x for x in df_data.columns if x not in list_zerona]
            df_data[list_zerona] = df_data[list_zerona].fillna(0)
            # df_data[list_avgna] = df_data[list_avgna].interpolate()
                
            

            ### plot total house demand
            trace = go.Scattergl(
                            x = df_data.index,
                            y = df_data['power_kw'].values,
                            name = 'power_kw',
                            mode = 'lines',
                            fill = "tozeroy",
                            connectgaps=False,
                            opacity=0.8,
                            )

            trace_rolling_avg_60s = go.Scattergl(
                            x = df_data.index, 
                            y = df_data["power_kw"].rolling(60).mean(),
                            name = 'rolling_avg_60s',
                            line= {'color':'rgb(255,0,255)'},
                            connectgaps=False,
                            # opacity = 0.8,
                            # fill = "tozeroy",
                            )

            graphs.append(html.Div(dcc.Graph(
                            id='total-house-demand',
                            animate=False,
                            figure={'data': [trace],
                                    'layout' : go.Layout(
                                        xaxis=dict(autorange=True),
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
                                        )
                                    }
                            ), className='row'))

            list_priority = [a for a in df_data.columns if a.lower().endswith('priority')]
            list_priority.extend(['ldc_signal'])
            # print(df_data[list_priority])

            ### plot individual device demand
            list_minus_wh = [a for a in df_data.columns if (a.lower().endswith('demand') and not (a.lower().startswith('waterheater')) and not (a.lower().startswith('heatpump')))] 
            # df_data['waterheater_actual_demand'] = np.roll(df_data['waterheater_actual_demand'].values, shift=0) * (((df_data['power_kw']>1.7)&(df_data[list_minus_wh].sum(axis=1)<1500))*1)
            list_params = [a for a in df_data.columns if a.lower().endswith('demand')]
            list_minus_hp = [a for a in df_data.columns if (a.lower().endswith('demand') and not (a.lower().startswith('heatpump')))]
            # df_data['heatpump_actual_demand'] = np.clip(((df_data['power_kw'] * 1000) - np.roll(df_data[list_minus_hp].sum(axis=1), shift=0))-200, a_min=0, a_max=1500)
            
            
            for param in list_params:
                    traces_demand.extend([
                            go.Scattergl(
                                x = df_data.index,
                                y = df_data[param].values,
                                name = param.split('_')[0],
                                mode = 'lines',
                                fill = "tozeroy",
                                connectgaps=False,
                                opacity=0.8,
                                )
                            ])
            graphs.append(html.Div(dcc.Graph(
                            id='house-demand',
                            animate=False,
                            figure={'data': traces_demand,
                                    'layout' : go.Layout(
                                        xaxis= dict(autorange=True),
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
                                        )
                                    }
                            ), className='row'))

            ### plot temperatures
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
            list_params = [a for a in df_data.columns 
                                if ((a.lower().endswith('status')) 
                                    and not (a.lower().startswith('window')) 
                                    and not (a.lower().startswith('door')))]

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
                                        tickvals=[x for x in range(20)], 
                                        ticktext=['0' if x%2==0 else '1' for x in range(20)]),
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
                df_data['ambient_temp'] = df_data['heatpump_temp_out']
                list_params.extend(['ambient_temp'])
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


# app.clientside_callback(
#     ClientsideFunction(
#         namespace='clientside',
#         function_name='update_graph'
#     ),
#     Output('graphs','children'),
#     [Input('hidden-data', 'data')]
# )


def serve_layout():
    return html.Div([
        # header
        html.Div([
            dcc.Location(id='url', refresh=False),
            get_logo(),
            html.H2("Localized Demand Control", 
                style={
                    'marginTop':'0', 
                    'marginLeft':'20', 
                    'display':'inline-block', 
                    'text-align':'left',
                    'float':'center', 
                    'color':'white', 
                    "backgroundColor": "#18252E"
                    }),
            ],
        ),

        html.Div([
            html.H1(f"Home Status", 
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
        ),
        
        # tabs
        html.Div([
            dcc.Tabs(id="tabs", 
                children=[
                    dcc.Tab(
                        label="House 1", 
                        value="house_1", 
                        style=tab_style,
                        selected_style=tab_selected_style,
                        className='custom-tab',
                        ),
                    dcc.Tab(
                        label="House 2", 
                        value="house_2", 
                        style=tab_style,
                        selected_style=tab_selected_style,
                        className='custom-tab',
                        ),
                    dcc.Tab(
                        label="House 3", 
                        value="house_3", 
                        style=tab_style,
                        selected_style=tab_selected_style,
                        className='custom-tab',
                        ),
                    dcc.Tab(
                        label="House 4", 
                        value="house_4", 
                        style=tab_style,
                        selected_style=tab_selected_style,
                        className='custom-tab',
                        ),
                    dcc.Tab(
                        label="House 5", 
                        value="house_5", 
                        style=tab_style,
                        selected_style=tab_selected_style,
                        className='custom-tab',
                        ),
                    ],
                value="house_1",
                className="col s12 m7 l5",
                style=tabs_styles,
                )                   
            ], 
            className='col s12 m3 l2',
            style={
                'display': 'inline-block', 
                'padding':'5', 
                'float':'left'}
        ),
                        

        ### Tab content
        html.Div(
            id="tab_content", 
            className="row", 
            style={"margin": "1%"}),
        ],
        className="row",
        style={
            "margin": "0%", 
            "backgroundColor": "#18252E"
            },
    )



def create_priorities_div(dict_items):
    list_div = []
    for k,v in dict_items.items():
        list_div.extend([
            html.Label(f'{v["name"]}:', 
                className='column', 
                style={
                    'color':'white', 
                    'text-align':'left', 
                    'display':'inline-block', 
                    "position": "relative"
                    }
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
    Output('device-states','children'),
    [Input('hidden-data', 'data')],
    [])
def create_states_div(json_data):
    
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

    if json_data:
        df_data = pd.read_json(json_data, orient='split')
        d = df_data.tail(1).round(3)

        if not d.empty:
        
            list_div.extend([
                html.Label(f"Total Power: {np.round(d['power_active_0'].values[0], 3)} kW", 
                    className='column', 
                    style={
                        'color':'white', 
                        'text-align':'left', 
                        'display':'inline-block', 
                        "position": "relative"
                        }
                    ),
                html.Label(f"Power Factor: {np.round(d['powerfactor_0'].values[0], 3)} ", 
                    className='column', 
                    style={'color':'white', 
                        'text-align':'left', 
                        'display':'inline-block', 
                        "position": "relative"
                        }
                    ),
                html.Label(f"Voltage: {np.round(d['voltage_0'].values[0], 2)} V", 
                    className='column', 
                    style={'color':'white', 
                        'text-align':'left', 
                        'display':'inline-block', 
                        "position": "relative"
                        }
                    ),
                html.Div('  ',
                    className='column',
                    style={
                        'color':'white', 
                        'marginTop':10, 
                        'display':'inline-block', 
                        "position": "relative"
                        }
                    ),
                ])
            
            for k in dict_all_devices.keys():
                params = [x for x in d.columns if x.startswith(k)]
                
                if len(params)>0:
                    list_div.extend([
                        html.Label(f"{dict_all_devices[k]['name']}", 
                            className='column', 
                            style={
                                'color':'white', 
                                'text-align':'left', 
                                'display':'inline-block', 
                                "position": "relative"
                                }
                            ),
                        ]
                    )

                    for p in params:
                        list_div.extend([
                            html.Label(f"{' '.join([x.capitalize() for x in p.split('_')[1:]])}: {d[p].values[0]}", 
                                className='column', 
                                style={
                                    'color':'white', 
                                    'marginLeft':10, 
                                    'text-align':'left', 
                                    'display':'inline-block', 
                                    "position": "relative"
                                    }
                                ),
                            ]
                        )
                list_div.extend([
                        html.Div('  ',
                            className='column',
                            style={
                                'color':'white', 
                                'marginTop':10, 
                                'display':'inline-block', 
                                "position": "relative"
                                }
                            ),
                        ])
    return list_div

def render_status(house_num=1):
    # render content for status tab
    global cmd_algorithm, cmd_loading, ldc_signal, date_list, dict_cmd, subnet
    subnet=house_num
    date_list = []
    hist_files = glob.glob(f'/home/pi/studies/ardmore/data/H{subnet}*.pkl.xz')
    list_files = [x.split('/')[-1] for x in hist_files]
    dates = ['-'.join(x.split('.')[0].split('_')[1:]) for x in list_files]
    dates.sort()
    date_list.extend(dates)
    date_list.extend([
        # 'Last 2 Hours', 
        # 'Last 1 Hour', 
        # 'Last 30 Minutes',
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

    
    day = '_'.join(dates[-1].split('-'))
    df_data = get_data(day=day)


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

        # html.Div([
        #     html.H1(f"Home Status", 
        #         style={
        #             'marginTop':'5', 
        #             'text-align':'center',
        #             'float':'center', 
        #             'color':'white'
        #             }
        #         ),
        #     ], 
        #     className='banner', 
        #     style={
        #         'width':'100%', 
        #         'display':'inline-block',
        #         "backgroundColor": "#18252E",
        #         }
        # ),

        html.Div([
            html.Div([
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
                ],className='row', 
            ),

            html.Div('  ',
                className='column',
                style={
                    'color':'white', 
                    'marginTop':20, 
                    'display':'inline-block', 
                    "position": "relative"
                    }
            ),

            html.Div([
                html.Label('Priorities', 
                    className='column', 
                    style={
                        'color':'white', 
                        'font-size':'large', 
                        'text-align':'center', 
                        'display':'inline-block', 
                        "position": "relative"
                        }
                    ),
                html.Div(children=priority_div, 
                    className='column'
                    ),
                ]),
            
            html.Div([
                    html.Label('Device State', 
                        className='column', 
                        style={
                            'color':'white', 
                            'font-size':'large', 
                            'text-align':'center', 
                            'display':'inline-block', 
                            "position": "relative"
                            }
                        ),
                    html.Div('  ',
                        className='column',
                        style={
                            'color':'white', 
                            'marginTop':10, 
                            'display':'inline-block', 
                            "position": "relative"
                            }
                    ),
                    html.Div(
                        children=html.Div(
                            id='device-states'), 
                        className='row'
                        ),
                ],
                className='column',
                style={
                    'color':'white', 
                    'marginTop':20, 
                    'display':'inline-block', 
                    "position": "relative"
                    }
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
            # html.Div(children=html.Div(id='hidden-data'), className='row', style={'opacity':'1.0', 'display':'none'}),
            dcc.Store(id='hidden-data'),
            dcc.Interval(id='data-update', interval=3*1000),
            ], className='row', style={'display':'none',},
        ),
      
                    
        ],
        style={
            'display':'inline-block', 
            "backgroundColor": "#18252E", 
            "width":"100%"} 
            
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
                html.H1("Settings", 
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
            ),
            
            html.Div([    
                ], 
                className='col s12 m2 l1',
                style={
                    'display': 'inline-block', 
                    'padding': '3', 
                    'float': 'left'
                    }
            ),
            
            # hidden div: holder of data
            html.Div([       
                ], 
                className='row', 
                style={
                    'display':'none',
                    },
            ),
            

            html.Div([
                ], 
                className='col s12 m12 l7',
                style={
                    'width':'80%', 
                    'display':'inline-block', 
                    'padding':'3px'
                    },
            ),
                
            ],

            style={
                'display':'inline-block', 
                "backgroundColor": "#18252E", 
                'width':'100%'
                } 
                    
            )


def render_history():
    # render content for history tab
    return html.Div(children=[
        html.Div([
            html.H1("History", 
                style={
                    'marginTop':'5', 
                    'text-align':'center',
                    'float':'center', 
                    'color':'white'}),
            ], 
            className='banner', 
            style={
                'width':'100%',
                'display':'inline-block',
                "backgroundColor": "#18252E",
                }
        ),
        
        html.Div([
            ], 
            className='col s12 m2 l1',
            style={
                'display': 'inline-block', 
                'padding':'3', 
                'float':'left'
                }
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
            style={
                'width':'80%', 
                'display':'inline-block', 
                'padding':'3px'
                },
        ),
    
    ],
    style={
        'display':'inline-block', 
        "backgroundColor": "#18252E", 
        'width':'100%'
        } 
    )



app.layout = serve_layout()




@app.callback(Output("tab_content", "children"), [Input("tabs", "value")])
def render_content(tab):
    if tab in [f"house_{x}" for x in range(1,6)]:
        return render_status(house_num=int(tab.split('_')[-1]))
    elif tab == "settings_tab":
        return render_settings()
    elif tab == "history_tab":
        return render_history()
    else:
        return render_status(house_num=int(tab.split('_')[-1]))


if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0', port=21003)