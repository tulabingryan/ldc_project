"""
./MODELS.py 
Module for LDC System Models
Author: Ryan Tulabing
Project: Local Demand Control
Institution: University of Auckland
Year: 2017 - 2020
Thesis: Localized Demand Control for Local Grids with Limited Resources
Generic model:

                             _________________Se_________________ 
                            |                                    |
     __________   A1   ___|/____   A2   __________        _____|_________
    |  Dongle  |----->| Device |----->|  End-use |  Se  |  Environment |
    |__________|<-----|________|<-----|__________|<-----|______________|
         /|        S1     |  /|      S2    |    /|                |
        |A0           S4|   |A4        S3|/____|A3              |
     ___|_______       _|/__|____      | Person |               |
    |  LDC     |  S5  |  Local  |      |________|               |
    | Injector |<-----|  Grid   |<------------------------------|
     ----------        ---------     Se

Definitions:
LDC Injector = LDC signal injector
    A0 = LDC signal (750-850Hz)
Dongle = LDC ldc_dongles to control the loads
    A1 = Action, approval of proposed demand
    S1 = State of the device, e.g., priority, mode, etc.
Device = Load appliance, e.g., heatpump, waterheater, etc.
    A2 = Action of the device, e.g., provide heat, cool freezer, etc.
    S2 = State of the end-use, e.g., room temp, freezer temp, job status, soc, etc.
End-use = End-usage application, room to heat, dishes to wash, laundry to dry
    A3 = Action of users, e.g., schedules, water usage, other settings, etc.
    S3 = State of the end-usage, e.g., temperature, soc, 
Person = person that creates schedules and settings for end-uses
Local Grid = local power grid
    A4 = Action of the grid, e.g., voltage, frequency
    S4 = State of the device, e.g., power demand, 
    S5 = state of the grid, e.g., aggregated demand, voltage, frequency, 
Environment = Weather environment, e.g, outside temperature, humidity, solar, wind
    Se = state of the environment, e.g., outside temp, solar, windspeed, humidity


"The worthwhile problems are the ones you can really solve or help solve, 
        the ones you can really contribute something to. 
        No problem is too small or too trivial 
        if we can really do something about it."
-Richard P. Feynman, Nobel Prize, Physics
"""


from PACKAGES import * 



######## helper functions #################
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
            time.sleep(3)
            # print("Error in get_local_ip: ", e)
            pass
        except KeyboardInterrupt:
            break
    return local_ip

def save_json(json_data, filename):
    # save json_data in filename
    with open(filename, 'w') as outfile:  
        json.dump(json_data, outfile)
        print("{}: {} saved...".format(datetime.datetime.now().isoformat(), filename))
    return filename

def read_json(filename):
    # read file as json
    with open(filename) as json_file:  
        data = json.load(json_file)
    return data

def read_temp_sensor():
    # read the temperature sensor
    try:
        readings = os.popen('/usr/local/bin/pcsensor').read()
        
        return readings
    except Exception as e:
        print(f'Error MODELS.read_temp_sensor:{e}')
    

def add_demands(baseload=0, heatpump=0, heater=0, waterheater=0, fridge=0, freezer=0, 
    clotheswasher=0, clothesdryer=0, dishwasher=0, solar=0, wind=0):
    return np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(baseload, 
        heatpump), heater), waterheater), fridge), freezer), clotheswasher), clothesdryer), 
        dishwasher), solar), wind)

def countem(node, target):
    'Count occurence of target in node'
    if node==target:
        return 1
    if isinstance(node, list):
        return sum(countem(subnode, target) for subnode in node)
    if isinstance(node, dict):
        return sum(countem(subnode, target) for subnode in node.values())
    return 0

def path_to(target, node):
    'Get path to target in node'
    if target==node:
        return f'-> {target!r}'
    elif isinstance(node, list):
        for i, subnode in enumerate(node):
            path = path_to(target, subnode)
            if path:
                return f'[{i}]{path}'
    elif isinstance(node, dict):
        for key, subnode in node.items():
            if target==key:
                return f'-> {target!r}'
            else:
                path = path_to(target, subnode)
                if path:
                    return f'[{key!r}]{path}'
    return ''


def setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40]):
    # setup the raspi gpio
    try:
        for x in inputs: GPIO.setup(int(x), GPIO.IN)
        for y in outputs: GPIO.setup(int(y), GPIO.OUT)
    except:
        pass

def execute_state(newstate, device_id, report=False):
    dict_state = {0:'CLOSED', 1:'OPEN'}
    try:
        if newstate not in [0,1]:
            print("Error MODELS.execute_state: invalid newstate")
        else:
            s = newstate
            if device_id in [123, 124, 125]: 
                s = (not newstate)*1  # logic for doors is reversed
            
            if s==GPIO.input(32): 
                # if report: print('Unit already in that state')
                pass
            else:
                if device_id in [118, 119, 120, 121, 122, 123, 124, 125]:
                    GPIO.output([15, 32, 36, 38, 40], [1, s, s, s, s])
                    
                    if report: print('Changing state, please wait...')
                    
                    ### turn off relay after 30s for windows and doors
                    time.sleep(30)
                    GPIO.output([15, 32, 36, 38, 40], [0, s, s, s, s])

                    
                    if report: print('{} state changed to:{}'.format(device_id, dict_state[newstate]))
                else:
                        GPIO.output([15, 32, 36, 38, 40], [s, s, s, s, s])
    except Exception as e:
        print("Error MODELS.execute_state:", e)





def prepare_data(states, common):
    try:
        if states['load_type'][0] in ['heatpump', 'heater']:
            return {np.round(common['unixtime'], 1):{
            'temp_out': ','.join(np.char.zfill(states['temp_out'].round(3).astype(str), 7)),
            'humidity_out': ','.join(np.char.zfill(states['humidity'].round(3).astype(str), 7)),
            'windspeed': ','.join(np.char.zfill(states['windspeed'].round(3).astype(str), 7)),
            'temp_in': ','.join(np.char.zfill(states['temp_in'].round(3).astype(str), 7)),
            'temp_target': ','.join(np.char.zfill(states['temp_target'].round(3).astype(str), 7)),
            'humidity_in': ','.join(np.char.zfill(states['humidity_in'].round(3).astype(str), 7)),
            'flexibility': ','.join(np.char.zfill(states['flexibility'].round(5).astype(str), 7)),
            'priority': ','.join(np.char.zfill(states['priority'].round(3).astype(str), 7)),
            'actual_demand': ','.join(np.char.zfill(states['actual_demand'].round(1).astype(str), 7)),
            'ldc_signal': ','.join(np.char.zfill(states['ldc_signal'].round(3).astype(str), 7)),
            'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
            'connected': ','.join(states['connected'].astype(int).astype(str)),
            'mode': ','.join(states['mode'].astype(int).astype(str)),
            }}
        elif states['load_type'][0] in ['fridge', 'freezer', 'waterheater']:
            return {np.round(common['unixtime'], 1):{
            'temp_in': ','.join(np.char.zfill(states['temp_in'].round(3).astype(str), 7)),
            'temp_target': ','.join(np.char.zfill(states['temp_target'].round(3).astype(str), 7)),
            'flexibility': ','.join(np.char.zfill(states['flexibility'].round(5).astype(str), 7)),
            'priority': ','.join(np.char.zfill(states['priority'].round(3).astype(str), 7)),
            'actual_demand': ','.join(np.char.zfill(states['actual_demand'].round(1).astype(str), 7)),
            'ldc_signal': ','.join(np.char.zfill(states['ldc_signal'].round(3).astype(str), 7)),
            'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
            'connected': ','.join(states['connected'].astype(int).astype(str)),
            }}
        elif states['load_type'][0] in ['clotheswasher', 'clothesdryer', 'dishwasher']:
            return {np.round(common['unixtime'], 1):{
            'progress': ','.join(np.char.zfill(states['progress'].round(5).astype(str), 7)),
            'flexibility': ','.join(np.char.zfill(states['flexibility'].round(5).astype(str), 7)),
            'priority': ','.join(np.char.zfill(states['priority'].round(3).astype(str), 7)),
            'actual_demand': ','.join(np.char.zfill(states['actual_demand'].round(1).astype(str), 7)),
            'ldc_signal': ','.join(np.char.zfill(states['ldc_signal'].round(3).astype(str), 7)),
            'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
            'connected': ','.join(states['connected'].astype(int).astype(str)),
            'mode': ','.join(states['mode'].astype(int).astype(str)),
            }}
        elif states['load_type'][0] in ['ev', 'storage']:
            return {np.round(common['unixtime'], 1):{
            'soc': ','.join(np.char.zfill(states['soc'].round(5).astype(str), 7)),
            'target_soc': ','.join(np.char.zfill(states['target_soc'].round(5).astype(str), 7)),
            'flexibility': ','.join(np.char.zfill(states['flexibility'].round(5).astype(str), 7)),
            'priority': ','.join(np.char.zfill(states['priority'].round(3).astype(str), 7)),
            'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
            'mode': ','.join(states['mode'].astype(int).astype(str)),
            'connected': ','.join(states['connected'].astype(int).astype(str)),
            'actual_demand': ','.join(np.char.zfill(states['actual_demand'].round(1).astype(str), 7)),
            'ldc_signal': ','.join(np.char.zfill(states['ldc_signal'].round(3).astype(str), 7)),
            }}
        elif states['load_type'][0] in ['solar', 'wind']:
            return {np.round(common['unixtime'], 1):{
            'priority': ','.join(np.char.zfill(states['priority'].round(3).astype(str), 7)),
            'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
            'mode': ','.join(states['mode'].astype(int).astype(str)),
            'connected': ','.join(states['connected'].astype(int).astype(str)),
            'actual_demand': ','.join(np.char.zfill(states['actual_demand'].round(1).astype(str), 7)),
            'ldc_signal': ','.join(np.char.zfill(states['ldc_signal'].round(3).astype(str), 7)),
            }}
        else:
            return {np.round(common['unixtime'], 1):{
            'actual_demand': ','.join(np.char.zfill(states['actual_demand'].round(1).astype(str), 7)),
            }}
    except Exception as e:
        print(f'Error MODELS.prepare_data:{e}')
        print(states['temp_target'])


def prepare_summary(states, common):
    try:
        if states['load_type'][0] in ['heatpump', 'heater']:
            return {common['unixtime']:{
            'mean_temp_out': states['temp_out'].mean().round(3),
            'mean_humidity_out': states['humidity'].mean().round(3),
            'mean_windspeed_out': states['windspeed'].mean().round(3),
            'mean_temp_in': states['temp_in'].mean().round(3),
            'min_temp_in': states['temp_in'].min().round(3),
            'max_temp_in': states['temp_in'].max().round(3),
            'std_temp_in': states['temp_in'].std().round(3),
            'temp_in': ','.join(np.char.zfill(states['temp_in'].round(3).astype(str), 7)),
            'temp_target': states['temp_target'].mean().round(3),
            'mean_humidity_in': states['humidity_in'].mean().round(3),
            'min_humidity_in': states['humidity_in'].min().round(3),
            'max_humidity_in': states['humidity_in'].max().round(3),
            'std_humidity_in': states['humidity_in'].std().round(3),
            'mean_flexibility': states['flexibility'].mean().round(5),
            'min_flexibility': states['flexibility'].min().round(5),
            'max_flexibility': states['flexibility'].max().round(5),
            'std_flexibility': states['flexibility'].std().round(5),
            'mean_priority': states['priority'].mean().round(3),
            'min_priority': states['priority'].min().round(3),
            'max_priority': states['priority'].max().round(3),
            'std_priority': states['priority'].std().round(3),
            'sum_actual_demand': states['actual_demand'].sum().round(1),
            'mean_ldc_signal': states['ldc_signal'].mean().round(3),
            'sum_actual_status': states['actual_status'].sum(),
            'sum_connected': states['connected'].sum(),
            }}
        elif states['load_type'][0] in ['fridge', 'freezer', 'waterheater']:
            return {common['unixtime']:{
            'mean_temp_in': states['temp_in'].mean().round(3),
            'min_temp_in': states['temp_in'].min().round(3),
            'max_temp_in': states['temp_in'].max().round(3),
            'std_temp_in': states['temp_in'].std().round(5),
            'temp_in': ','.join(np.char.zfill(states['temp_in'].round(3).astype(str), 7)),
            'mean_temp_target': states['temp_target'].mean().round(3),
            'mean_flexibility': states['flexibility'].mean().round(5),
            'min_flexibility': states['flexibility'].min().round(5),
            'max_flexibility': states['flexibility'].max().round(5),
            'std_flexibility': states['flexibility'].std().round(5),
            'mean_priority': states['priority'].mean().round(3),
            'min_priority': states['priority'].min().round(3),
            'max_priority': states['priority'].max().round(3),
            'std_priority': states['priority'].std().round(3),
            'sum_actual_demand': states['actual_demand'].sum().round(1),
            'mean_ldc_signal': states['ldc_signal'].mean().round(3),
            'sum_actual_status': states['actual_status'].sum(),
            'sum_connected': states['connected'].sum(),
            }}
        elif states['load_type'][0] in ['clotheswasher', 'clothesdryer', 'dishwasher']:
            return {common['unixtime']:{
            'mean_progress': states['progress'].astype(float).mean().round(5),
            'min_progress': states['progress'].astype(float).min().round(5),
            'max_progress': states['progress'].astype(float).max().round(5),
            'std_progress': states['progress'].astype(float).std().round(5),
            'progress': ','.join(np.char.zfill(states['progress'].round(5).astype(str), 7)),
            'mean_flexibility': states['flexibility'].astype(float).mean().round(5),
            'min_flexibility': states['flexibility'].astype(float).min().round(5),
            'max_flexibility': states['flexibility'].astype(float).max().round(5),
            'std_flexibility': states['flexibility'].astype(float).std().round(5),
            'mean_priority': states['priority'].astype(float).mean().round(5),
            'min_priority': states['priority'].astype(float).min().round(5),
            'max_priority': states['priority'].astype(float).max().round(5),
            'std_priority': states['priority'].astype(float).std().round(5),
            'sum_actual_demand': states['actual_demand'].astype(float).sum().round(5),
            'mean_ldc_signal': states['ldc_signal'].astype(float).mean().round(5),
            'sum_actual_status': states['actual_status'].astype(float).sum(),
            'sum_connected': states['connected'].astype(float).sum(),
            }}
        elif states['load_type'][0] in ['ev', 'storage']:
            return {common['unixtime']:{
            'mean_soc': states['soc'].mean().round(5),
            'min_soc': states['soc'].min().round(5),
            'max_soc': states['soc'].max().round(5),
            'std_soc': states['soc'].std().round(5),
            'soc': ','.join(np.char.zfill(states['soc'].round(5).astype(str), 7)),
            'mean_target_soc': states['target_soc'].mean().round(5),
            'min_target_soc': states['target_soc'].min().round(5),
            'max_target_soc': states['target_soc'].max().round(5),
            'std_target_soc': states['target_soc'].std().round(5),
            'mean_flexibility': states['flexibility'].mean().round(5),
            'min_flexibility': states['flexibility'].min().round(5),
            'max_flexibility': states['flexibility'].max().round(5),
            'std_flexibility': states['flexibility'].std().round(5),
            'mean_priority': states['priority'].mean().round(3),
            'min_priority': states['priority'].min().round(3),
            'max_priority': states['priority'].max().round(3),
            'std_priority': states['priority'].std().round(3),
            'sum_actual_status': states['actual_status'].sum(),
            'sum_connected': states['connected'].sum(),
            'sum_actual_demand': states['actual_demand'].sum().round(1),
            'mean_ldc_signal': states['ldc_signal'].mean().round(3),
            }}
        elif states['load_type'][0] in ['solar', 'wind']:
            return {common['unixtime']:{
            'mean_priority': states['priority'].mean().round(3),
            'min_priority': states['priority'].min().round(3),
            'max_priority': states['priority'].max().round(3),
            'std_priority': states['priority'].std().round(3),
            'sum_actual_status': states['actual_status'].sum(),
            'sum_connected': states['connected'].sum(),
            'sum_actual_demand': states['actual_demand'].sum().round(1),
            'mean_ldc_signal': states['ldc_signal'].mean().round(3),
            }}
        else:
            return {common['unixtime']:{
            'sum_actual_demand': states['actual_demand'].sum().round(1),
            }}
    except Exception as e:
        print(f'Error MODELS.prepare_data:{e}')
        print(states['temp_target'])


def save_data(dict_save, folder, filename, case, sample='1S', summary=False):
    try:
        df = pd.DataFrame.from_dict(dict_save, orient='index')
        df.index = pd.to_datetime(df.index, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
        path = f'/home/pi/studies/results/{folder}/{case}'
        os.makedirs(path, exist_ok=True)  # create folder if none existent
        df.to_hdf(f'{path}/{filename}', 
                    key=f'records', mode='a', append=True, 
                    complib='blosc', complevel=9, format='table')
        return {}  # empty dict_save if saving is successful
    except Exception as e:
        print(f"Error MODELS.save_data:{e}")
        print(folder, filename)
        print(df.dtypes)
        print(df)
        # print(df.describe())
        return dict_save

# def save_data(dict_save, folder, filename, case, sample='1S', summary=False):
#   try:
#     df = pd.DataFrame.from_dict(dict_save, orient='index')
#     df.index = pd.to_datetime(df.index, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
#     df.to_hdf(f'/home/pi/studies/results/{folder}/{filename}', 
#           key=f'{case}', mode='a', append=True, 
#           complib='blosc', complevel=9, format='table')
#     return {}  # empty dict_save if saving is successful
#   except Exception as e:
#     print(f"Error MODELS.save_data:{e}")
#     print(folder, filename)
#     print(df.dtypes)
#     print(df)
#     # print(df.describe())
#     return dict_save


# save_params = ['temp_out','humidity','windspeed','temp_in','temp_target', 'humidity_in', 
#               'flexibility', 'priority', 'actual_demand', 'actual_status', 'connected', 'mode'
#               'progress', 'soc','target_soc',
#               'unbalance_percent', 'loading_percent', 'p_a_mw', 'p_b_mw', 'p_c_mw', 'q_a_mvar', 'q_b_mvar', 'q_c_mvar',
#               'sn_mva', 'pf_a', 'pf_b', 'pf_c', 'ldc_signal', 'nogrid_percent', 'loss_percent', 'factor', 'target_percent', 'offset',
#               'p_a_hv_mw', 'p_b_hv_mw', 'p_c_hv_mw', 'q_a_hv_mvar', 'q_b_hv_mvar', 'q_c_hv_mvar']

# def prepare_data(states, common):
#   try:
#     keys = states.keys()
#     dict_out = {}
#     for p in save_params:
#       if p in keys:
#         dict_out.update({p:states[p]})
#     return {int(common['unixtime']):dict_out}
#   except Exception as e:
#     print(f'Error MODELS.prepare_data:{e}')
#     print(states['temp_target'])
#     return {}

# def save_data(dict_save, folder, filename, case, sample='1S'):
#   try:
#     df = pd.DataFrame.from_dict(dict_save, orient='index')
#     df.index = pd.to_datetime(df.index, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
#     for c in save_params:
#       if c in df.columns:
#         df[c].apply(pd.Series).to_hdf(f'/home/pi/studies/results/{folder}/{filename}', 
#           key=f'/{case}/{c}', mode='a', append=True, 
#           complib='blosc', complevel=9, format='table')
#     return {}  # empty dict_save if saving is successful
#   except Exception as e:
#     print(f"Error MODELS.save_data:{e}")
#     print(df['load_type'], folder, filename)
#     return dict_save

def save_feather(dict_data, path='history/sample.feather'):
        try:
            df_all = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True)
            try:
                on_disk = pd.read_feather(path).reset_index(drop=True)
                df_all = pd.concat([on_disk, df_all], axis=0).reset_index(drop=True)
            except Exception as e:
                # print(e)
                pass
            df_all.to_feather(path)
            return {}
        except Exception as e:
            print("Error data_logger.save_data:", e)
            return dict_data 

def save_hdf(dict_data, path=f'/home/pi/ldc_project/history/dongle.h5'):
    try:
        df = pd.DataFrame.from_dict(dict_data, orient='index')
        df.to_hdf(path, key=f'injector', mode='a', append=True, 
                complib='blosc', complevel=9, format='table')
        return {}
    except Exception as e:
        print("Error tcp_server.save_hdf:", e)
        return dict_data

# def fetch_baseload(unixtime, n_seconds=3600):
#   yearsecond = int(unixtime-1800)%31536000                 
#   with pd.HDFStore('./profiles/baseload.h5', 'r') as store:
#     df = store.select('records', where='index>={} and index<{}'.format(int(yearsecond), 
#       int(yearsecond+(3*n_seconds))))
#     df.reset_index(drop=True, inplace=True)
#     df.index = np.add(df.index.values, int(unixtime-1800))
#   return df, {'start': df.index.values[0], 'end':df.index.values[-int(n_seconds/2)]}

def fetch_baseload(season):
    with pd.HDFStore('./profiles/baseload.h5', 'r') as store:
        df = store.select(season)
    return df, {'start': df.index.values[0], 'end':df.index.values[-1], 'season':season}


######## model for environment #################


dict_season = {1:'summer', 2:'summer', 12:'summer',
    3:'autumn', 4:'autumn', 5:'autumn',
    6:'winter', 7:'winter', 8:'winter',
    9:'spring', 10:'spring', 11:'spring'}

def clock(unixtime, realtime=True, step_size=1):
    # return next timestamp and stepsize
    if realtime:
        timestamp = time.time()
        step_size = np.subtract(timestamp, unixtime)
    else:
        step_size = step_size #np.random.uniform(0.1, step_size)
        timestamp = np.mean(np.add(unixtime, step_size))
    dt = pd.to_datetime(timestamp, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
    return {
        'unixtime': timestamp,
        'step_size': step_size,
        'year': dt.year,
        'month': dt.month,
        'day': dt.day,
        'week': dt.week,
        'weekday': dt.dayofweek,
        'hour': dt.hour,
        'minute': dt.minute,
        'second': dt.second,
        'microsecond': dt.microsecond,
        'weekminute': (dt.dayofweek*24*60) + (dt.hour*60) + dt.minute,
        'season':dict_season[dt.month],
        'isotime': dt.isoformat(),
        'today': dt.strftime('%Y_%m_%d')
    }

    # (timestamp, step_size, dt.year, dt.month, dt.day,  dt.week, dt.weekday, 
    #   dt.hour, dt.minute, dt.second, dt.microsecond, dt.isoformat())

# def weather(unixtime):
#   try:

#   except:
#     con = lite.connect('./profiles/weather.db', isolation_level=None)
#     con.execute('pragma journal_mode=wal;')
#     with con:
#         cur = con.cursor()
#         cur.execute("SELECT humidity, temperature, windspeed, pressure FROM data WHERE yearhour BETWEEN {} AND {} ORDER BY yearhour ASC".format(start, end))
#         data = np.array(cur.fetchall())
#         df_weather = pd.DataFrame(data, columns=['humidity', 'temperature', 'windspeed', 'pressure'])
#         df_weather['unixtime'] = dt_range.astype(int) * 1e-9
                
#     # Save (commit) the changes
#     con.commit()
#     con.close()
#   return  

######## model for grid #################





################ models for end-uses ###################################################
def enduse_tcl(heat_all,temp_in, temp_out, temp_fill, Ua, Ca, Cp, mass_flow, step_size):
        '''
        dTz/dt = Q + mCp(Tf-Tz) + U(To-Tz)
        '''
        try:
                R = np.divide(1,Ua)
                tt = np.add(np.multiply(mass_flow, np.multiply(Cp, R)), 1)
                tau = np.divide(np.multiply(Ca, R), tt)
                a = np.exp(-np.divide(step_size, tau))
                temp_in = np.add(np.multiply(a,temp_in), 
                                np.multiply(np.subtract(1, a), np.divide(np.add(temp_out, np.add(np.multiply(R,heat_all), 
                                np.multiply(np.multiply(mass_flow, Cp),np.multiply(R, temp_fill)))), tt) )) 
                return {'temp_in':np.add(temp_in, np.random.normal(0.0,1e-3))}

        except Exception as e:
                print(e)



# def enduse_tcl(heat_all, air_part, temp_in, temp_mat, temp_out, Um, Ua, Cp, Ca, Cm, 
#   mass_flow, step_size, unixtime, connected):
#   # update temp_in and temp_mat, and temp_in_active, i.e., for connected tcls
#   '''
#   CdT/dt = Ua(Ta-T)  
#   '''
#   count = 0
#   increment = 0.2
#   while count < step_size:
#     # for air temp
#     old_temp = temp_in
#     Q_h =  np.multiply(heat_all, air_part)
#     Q_mat =  np.multiply(np.subtract(temp_mat, temp_in), Um)
#     Q_ambient = np.multiply(np.subtract(temp_out, temp_in), Ua)
#     Q_mass = np.multiply(np.subtract(temp_out, temp_in), np.multiply(mass_flow, Cp))
#     dtemp = np.divide(np.add(Q_h, np.add(Q_mat, np.add(Q_ambient, Q_mass))), Ca)
#     temp_in = np.add(temp_in, np.multiply(dtemp, increment))
#     # print(old_temp[0], Q_h[0], Q_mat[0], Q_ambient[0], Q_mass[0], dtemp[0])
#     # for material temp
#     temp_mat = np.add(temp_mat, np.multiply(np.divide(np.subtract(np.multiply(heat_all, 
#       np.subtract(1, air_part)), np.multiply(np.subtract(temp_mat, temp_in), Um)), Cm), increment))
#     count = np.add(count, increment)  
#   temp_in_active = temp_in[np.where(connected>0)]
#   return {
#     'temp_in':temp_in, 
#     'temp_mat':temp_mat,
#     'temp_in_active': temp_in_active
#     }


# def enduse_tcl(heat_all, air_part, temp_in, temp_mat, temp_out, Um, Ua, Cp, Ca, Cm, 
#   mass_flow, step_size, unixtime, connected):
#   '''Model for a thermal zone
#   Tin(t+1) = Tin(t) + (dt/2 * (Tin(t) + dTin))
#   where, 
#     dTin = (Q_device + Q_in + (air_part)Q_solar + Q_ambient + Q_refill) ; Q_device = heat from heatpump, Q_in=heat from inner sources, Q_solar=heat from solar, Q_ambient=heat from outside, Q_refill=heat from mass flow
#     dTin =  (Q_device + Q_in + (air_part)*Q_solar + Ua(Ta_Tin) + (mass_flow*Cp*(T_refill-Tin)))

#   '''
#   try:
#     temp_refill = temp_out
#     air_part = 1 # comment out if needed
#     count = 0
#     dt = step_size
#     while count < step_size:
#       # for air temp
#       Q_ambient = np.multiply(Ua, np.subtract(temp_out, temp_in))
#       Q_refill = np.multiply(np.multiply(mass_flow, Cp), np.subtract(temp_refill, temp_in))
#       Q_mat = np.multiply(Um, np.subtract(temp_mat, temp_in))
#       dtemp_in = np.divide((np.add(np.multiply(heat_all, air_part), np.add(Q_ambient, np.add(Q_refill, Q_mat)))), Ca)
#       temp_in = np.add(temp_in, np.multiply(np.add(temp_in, dtemp_in), dt/2))
            
#       # for material temp
#       Q_in = np.multiply(Um, np.subtract(temp_in, temp_mat))
#       dtemp_mat = np.divide((np.add(np.multiply(heat_all, 1-air_part), Q_in)), Cm)
#       temp_mat = np.add(temp_mat, np.multiply(np.add(temp_mat, dtemp_mat), dt/2))
            
#       count = np.add(count, dt)  
#     # temp_in_active = temp_in[np.where(connected>0)]
#   except Exception as e:
#     print("Error MODELS.enduse_tcl:", e)

#   return {
#     'temp_in':temp_in, 
#     'temp_mat':temp_mat,
#     # 'temp_in_active': temp_in_active
#     }




# ### test enduse_tcl
# enduse_tcl(heat_all=np.random.normal(2345, 100, 10), 
#   air_part=np.random.normal(0.5,0.0001,10), 
#   temp_in=np.random.normal(20,0.1,10), 
#   temp_mat=np.random.normal(20,0.1,10), 
#   temp_out=np.random.normal(10,0.1,10), 
#   Um=np.random.normal(75,0.1,10), 
#   Ua=np.random.normal(80,0.1,10),
#   Cp=np.ones(10)*1006, 
#   Ca=np.random.normal(30,0.1,10)*1.25*1006, 
#   Cm=np.random.normal(3,0.001,10)*1.25*4186, 
#   mass_flow=np.random.normal(0.05, 1e-6,10), 
#   step_size=1, 
#   unixtime=time.time(), 
#   connected=np.ones(10))






# def enduse_storage(soc, power, capacity, step_size):
#   # update soc
#   return np.divide(np.add(np.multiply(power, step_size), 
#     np.multiply(soc, capacity)), capacity)  # soc

def enduse_ev(soc, target_soc, actual_demand, capacity, connected, unixtime, step_size):
    # update soc
    soc = np.divide(np.add(np.multiply(actual_demand, step_size), 
        np.multiply(soc, capacity)), capacity)  # new soc [ratio] 
    progress = np.divide(soc, target_soc)
    unfinished = np.multiply(progress, (progress<1) * 1)  # unfinished tasks
    finished = (progress>=1) * 1  # finished tasks
    progress = np.abs(np.multiply(np.add(unfinished, finished), connected))
    return {
        'unfinished': unfinished,
        'finished': finished,
        'progress': progress,
        'soc': soc}

def enduse_storage(soc, target_soc, actual_demand, capacity, connected, unixtime, step_size):
    # update soc
    soc = np.divide(np.add(np.multiply(actual_demand, step_size), 
        np.multiply(soc, capacity)), capacity)  # new soc [ratio] 
    progress = np.divide(soc, target_soc)
    unfinished = np.multiply(progress, (progress<1) * 1)  # unfinished tasks
    finished = (progress>=1) * 1  # finished tasks
    progress = np.abs(np.multiply(np.add(unfinished, finished), connected))
    return {
        'unfinished': unfinished,
        'finished': finished,
        'progress': progress,
        'soc': soc}

def enduse_ntcl(len_profile, progress, step_size, actual_status, unixtime, connected):
    # update job status
    try:
        progress = np.add(progress, np.multiply(np.divide(step_size, len_profile), actual_status))
        unfinished = np.multiply(progress, (progress<1) * 1)  # unfinished tasks
        finished = (progress>=1) * 1  # finished tasks
        progress = np.multiply(progress, connected)

        return {
            'unfinished': unfinished,
            'finished': finished,
            'progress': progress}
    except Exception as e:
        print(f"Error MODELS.enduse_ntcl:{e}")

############# models for devices #######################################################
def device_cooling_compression(mode, temp_in, temp_min, temp_max, temp_target,
    tolerance, cooling_power, cop, standby_power, ventilation_power, 
    proposed_status, actual_status, tcl_control):
    # device model for vapor compresion cycle, e.g., freezer, fridge, air condition
    ''' 
    Generic model of Battery-based loads
    Inputs:
        mode = cooling mode
        temp_in = inside temperature
        temp_min = minimum temperature allowed
        temp_max = maximum temperature allowed
        temp_target = target temperature for cooling
        tolerance = setpoint tolerance
        cooling_power = compressor power
        cop = coefficient of performance
        standby_power = power during standby mode
        ventilation_power = power for fans
        proposed_status = proposed status of the device before demand control
        actual_status = status decided by the dongle, 1=job is start, 0=delayed 
        tcl_control = control of TCLs, direct vs setpoint change
    Outputs:
        proposed_status = proposed status for the next timestep
        flexibility = capability of the device to be delayed in starting
        proposed_demand = proposed demand for the next timestep
        actual_demand = actual demand based on the previous proposed_demand and previous actual_status
        cooling_power_thermal = actual thermal power taken from the thermal zone
    '''
    try:
        ### calculate actual demand and actual thermal output
        # NOTE: All cooling are compressor-based  
        if tcl_control=='direct': ### if compressor can be controlled
            actual_demand = np.multiply(np.add(np.add(np.multiply(cooling_power, actual_status), standby_power), 
                ventilation_power), ((mode==0)*1))  
            cooling_power_thermal = np.multiply(np.multiply(np.multiply(cooling_power, 
                actual_status), cop), ((mode==0)*1)) * -1
        else: ### if compressor can't be controlled
            actual_demand = np.multiply(np.add(np.add(np.multiply(cooling_power, proposed_status), standby_power), 
                ventilation_power), ((mode==0)*1))  
            cooling_power_thermal = np.multiply(np.multiply(np.multiply(cooling_power, 
                proposed_status), cop), ((mode==0)*1)) * -1
        
        ### update proposed status and proposed demand
        proposed_status = ((((temp_in>=np.subtract(temp_target, tolerance)) & (proposed_status==1)) 
            | ((temp_in>=np.add(temp_target, tolerance))&(proposed_status==0)))&(mode==0)) * 1
        proposed_demand = np.multiply(np.add(np.add(np.multiply(proposed_status, cooling_power), 
            standby_power), ventilation_power), ((mode==0)*1))
        ### update flexibility
        flexible_horizon = np.subtract(temp_max, temp_in)
        operation_horizon = np.subtract(temp_max, temp_min)
        flexibility = np.divide(flexible_horizon, operation_horizon)
        return {
            'proposed_status': proposed_status,
            'proposed_demand': proposed_demand, 
            'flexibility': np.multiply(flexibility, ((mode==0)*1)),
            'cooling_power_thermal': cooling_power_thermal, 
            'actual_demand': np.abs(np.add(actual_demand, np.random.normal(0, 0.01)))}
    except Exception as e:
        print("Error MODELS.device_cooling_compression:{}".format(e))
        return {}

def device_heating_compression(mode, temp_in, temp_min, temp_max, temp_target, 
    tolerance, heating_power, cop, standby_power, ventilation_power, 
    proposed_status, actual_status, tcl_control):
    # device model for vapor compression cycle for heating, e.g., heatpump
    '''
    Inputs:
        mode = cooling mode
        temp_in = inside temperature
        temp_min = minimum temperature allowed
        temp_max = maximum temperature allowed
        temp_target = target temperature for heating
        tolerance = setpoint tolerance
        heating_power = compressor power
        cop = coefficient of performance
        standby_power = power during standby mode
        ventilation_power = power for fans
        proposed_status = status without demand control
        actual_status = status decided by the dongle, 1=job is start, 0=delayed 
        tcl_control = control of TCLs, direct vs setpoint change   
    Outputs:
        proposed_status = proposed status for the next timestep
        flexibility = capability of the device to be delayed in starting
        proposed_demand = proposed demand for the next timestep
        actual_demand = actual demand based on the previous proposed_demand and previous actual_status
        cooling_power_thermal = actual thermal power taken from the thermal zone
    '''

    try:
        ### update actual demand using actual_status, approved from previous step
        if tcl_control=='direct': ## if compressor can be controlled
            actual_demand = np.add(np.add(np.multiply(heating_power, actual_status), standby_power), 
                ventilation_power)*((mode==1)*1) 
            heating_power_thermal = np.multiply(np.multiply(np.multiply(heating_power, 
                actual_status), cop), ((mode==1)*1))
        else: ## if compressor can not be controlled
            actual_demand = np.add(np.add(np.multiply(heating_power, proposed_status), standby_power), 
                ventilation_power)*((mode==1)*1) 
            heating_power_thermal = np.multiply(np.multiply(np.multiply(heating_power, 
                proposed_status), cop), ((mode==1)*1))

        ### update proposed status and proposed_demand
        proposed_status = ((((temp_in<=np.add(temp_target, tolerance))&(proposed_status==1)) 
            |  ((temp_in<=np.subtract(temp_target, tolerance))&(proposed_status==0)))&(mode==1)) * 1
        proposed_demand = np.multiply(np.multiply(proposed_status, heating_power), ((mode==1)*1))
        ### update flexibility
        flexible_horizon = np.subtract(temp_in, temp_min)
        operation_horizon = np.subtract(temp_max, temp_min)
        flexibility = np.divide(flexible_horizon, operation_horizon)
        
        
        return {
            'proposed_status': proposed_status,
            'proposed_demand': proposed_demand,
            'flexibility': np.multiply(flexibility, (mode==1)*1),
            'heating_power_thermal': heating_power_thermal, 
            'actual_demand': np.add(actual_demand, np.random.normal(1, 0.01, len(actual_demand)))}
    except Exception as e:
        print("Error MODELS.device_heating_compression:{}".format(e))
        return {}




def device_heatpump(mode, temp_in, temp_out, temp_min, temp_max, temp_target,
    cooling_setpoint, heating_setpoint, tolerance, cooling_power, heating_power, cop, 
    standby_power, ventilation_power, proposed_status, actual_status, tcl_control):
    try:
        ### determine mode
        mode = ((np.subtract(temp_max, temp_in) > 0)&(heating_setpoint>temp_out)) * 1
        ### set proposed demand
        c = device_cooling_compression(mode=mode, temp_in=temp_in, temp_min=temp_min, 
            temp_max=temp_max, temp_target=temp_target, tolerance=tolerance, 
            cooling_power=cooling_power, cop=cop, standby_power=standby_power, 
            ventilation_power=ventilation_power, proposed_status=proposed_status, 
            actual_status=actual_status, tcl_control=tcl_control)

        h = device_heating_compression(mode=mode, temp_in=temp_in, temp_min=temp_min, 
            temp_max=temp_max, temp_target=temp_target, tolerance=tolerance, 
            heating_power=heating_power, cop=cop, standby_power=standby_power, 
            ventilation_power=ventilation_power, proposed_status=proposed_status, 
            actual_status=actual_status, tcl_control=tcl_control)
        return {
            'mode': mode, 
            'proposed_status': np.add(c['proposed_status'], h['proposed_status']),
            'proposed_demand': np.add(c['proposed_demand'], h['proposed_demand']),
            'flexibility': np.add(c['flexibility'], h['flexibility']),
            'cooling_power_thermal': c['cooling_power_thermal'],
            'heating_power_thermal': h['heating_power_thermal'],
            'actual_demand': np.add(c['actual_demand'], h['actual_demand'])}
    except Exception as e:
        print("Error MODELS.device_tcl:{}".format(e))
        return {}

def device_heating_resistance(mode, temp_in, temp_min, temp_max, heating_setpoint, 
    tolerance, heating_power, cop, standby_power, ventilation_power, 
    proposed_status, actual_status, tcl_control):
    # device model for resistance-based heating, e.g., heatpump
    '''
    Inputs:
        mode = cooling mode
        temp_in = inside temperature
        temp_min = minimum temperature allowed
        temp_max = maximum temperature allowed
        heating_setpoint = target temperature for heating
        tolerance = setpoint tolerance
        heating_power = power of heating element
        cop = coefficient of performance
        standby_power = power during standby mode
        ventilation_power = power for fans
        proposed_status = status proposed in previous timestep
        actual_status = status decided by the dongle, 1=job is start, 0=delayed 
        tcl_control = control of TCLs, direct vs setpoint change
    Outputs:
        proposed_status = proposed status for the next timestep
        flexibility = capability of the device to be delayed in starting
        proposed_demand = proposed demand for the next timestep
        actual_demand = actual demand based on the previous proposed_demand and previous actual_status
        cooling_power_thermal = actual thermal power taken from the thermal zone
    '''
    try:
        if tcl_control=='direct': ### get actual_demand
            actual_demand = np.add(np.add(np.multiply(actual_status, heating_power), standby_power), ventilation_power)*((mode==1)*1) 
            heating_power_thermal = np.multiply(np.multiply(cop, np.multiply(heating_power, actual_status)), ((mode==1)*1))
        elif tcl_control.startswith('setpoint'): ## change in demand is based on setpoint adjustment, 'setpoint'=use ON/OFF state, 'setpoint2'=use ldc signal, uniform adjustment to all
            actual_demand = np.add(np.add(np.multiply(heating_power, proposed_status), standby_power), ventilation_power)*((mode==1)*1) 
            heating_power_thermal = np.multiply(np.multiply(np.multiply(heating_power, proposed_status), cop), ((mode==1)*1))
        else:
            actual_demand = np.add(np.add(np.multiply(actual_status, heating_power), standby_power), ventilation_power)*((mode==1)*1) 
            heating_power_thermal = np.multiply(np.multiply(cop, np.multiply(heating_power, actual_status)), ((mode==1)*1))

        ### update proposed_status and proposed_demand
        proposed_status = ((((temp_in<=np.add(heating_setpoint, tolerance))&(proposed_status==1)) 
            |  ((temp_in<=np.subtract(heating_setpoint, tolerance))&(proposed_status==0)))&(mode==1)) * 1
        proposed_demand = np.multiply(np.multiply(proposed_status, heating_power), ((mode==1)*1))
        ### update flexibility
        flexible_horizon = np.subtract(temp_in, temp_min)
        operation_horizon = np.subtract(temp_max, temp_min)
        flexibility = np.divide(flexible_horizon, operation_horizon)
        
        return {
            'proposed_status': proposed_status,
            'proposed_demand': proposed_demand,
            'flexibility': flexibility,
            'heating_power_thermal': heating_power_thermal, 
            'actual_demand': np.add(actual_demand, np.random.normal(1, 0.01, len(actual_demand)))}
    except Exception as e:
        print("Error MODELS.device_heating_resistance:{}".format(e))
        return {}


        

def device_battery(unixtime, unixstart, unixend, soc, charging_power, target_soc, capacity,
    connected, progress, actual_status, proposed_demand):
    ''' 
    Generic model of Battery-based loads
    Inputs:
        unixtime = current timestamp
        unixstart = earliest timestamp to start the device
        unixend = latest timestamp to finish the job
        connected = signifies if the device is connected, i.e., unixstart <= unixtime < unixend
        progress = status of the job, i.e., range 0..1, 
        actual_status = approved status, 1=job is start, 0=delayed
        proposed_demand = proposed demand for the next time step
    Outputs:
        proposed_status = proposed status for the next timestep
        flexibility = capability of the device to be delayed in starting
        priority = priority of the device based on its flexibility, 
                            used as decision variable for the ldc_dongles
        proposed_demand = proposed demand for the next timestep
        actual_demand = actual demand based on the previous proposed_demand and previous actual_status
    '''
    ### calculate actual_demand based on approved status and proposed demand from previous step
    actual_demand = np.multiply(np.multiply(actual_status, proposed_demand), (progress<1)*1)
    ### update proposed_status and proposed_demand for next step
    proposed_status = ((progress<1)&(connected>0))*1
    proposed_demand = np.divide(charging_power, np.e**(np.multiply((soc>=0.9)*1, 
        np.subtract(np.multiply(soc, 100), 90))))  # mathematical model
    ### predict finish and calculate flexibility based on newly proposed demand
    predicted_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
        soc), capacity), proposed_demand))

    flexible_horizon = np.multiply(np.subtract(unixend, predicted_finish), connected)
    operation_horizon = np.abs(np.subtract(unixend, unixstart))
    flexibility = np.divide(flexible_horizon, operation_horizon)
    
    return {
        'proposed_status': proposed_status.flatten(), 
        'flexibility': flexibility.flatten(), 
        'predicted_finish': predicted_finish.flatten(), 
        'proposed_demand': proposed_demand.flatten(), 
        'actual_demand': actual_demand.flatten()}
        



def device_charger_ev(unixtime, unixstart, unixend, soc, charging_power, target_soc, capacity,
    connected, progress, actual_status, proposed_demand):
    '''
    Input states:
        Model for EV charger
        unixtime = current timestamp
        unixstart = timestamp for earliest start
        unixend = timestamp for latest end
        soc = state of charge [ratio]
        charging_power = charger power rating [w]
        target_soc = user-defined target soc [ratio]
        capacity = storage capacity [J or watt*s]
        connected = charger is connected to socket
        progress = charging progress
        actual_status = approved status by the dongle
        proposed_demand = proposed demand from previous step
    Output actions:
        proposed_status = proposed status
        flexibility = ldc flexibility
        priority = ldc priority
        predicted_finish = predicted time of finish
        proposed_demand = proposed demand
        actual_demand = actual demand

    Charging time for 100 km of BEV range   Power supply    power   Voltage     Max. current
    6–8 hours                               Single phase    3.3 kW  230 V AC        16 A
    3–4 hours                               Single phase    7.4 kW  230 V AC        32 A
    2–3 hours                               Three phase     11 kW   400 V AC        16 A
    1–2 hours                               Three phase     22 kW   400 V AC        32 A
    20–30 minutes                           Three phase     43 kW   400 V AC        63 A
    20–30 minutes                           Direct current  50 kW   400–500 V DC    100–125 A
    10 minutes                              Direct current  120 kW  300–500 V DC    300–350 A
    '''
    ### calculate actual_demand based on approved status and proposed demand from previous step
    actual_demand = np.multiply(np.multiply(actual_status, proposed_demand), (progress<1)*1)
    ### update proposed_status and proposed_demand for next step
    proposed_status = ((unixstart<=unixtime) & (unixend>=unixtime)) * 1
    ### get proposed_demand
    # proposed_demand = np.divide(charging_power, np.e**(np.multiply((soc>=0.9)*1, 
    #   np.subtract(np.multiply(soc, 100), 90))))  # mathematical model
    proposed_demand = proposed_demand  # model based on actual data from pecan street
    ### predict finish and calculate flexibility based on newly proposed demand
    predicted_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
        soc), capacity), proposed_demand))
    flexible_horizon = np.multiply(np.subtract(unixend, predicted_finish), connected)
    operation_horizon = np.abs(np.subtract(unixend, unixstart))
    flexibility = np.divide(flexible_horizon, operation_horizon)
    
    return {'proposed_status': proposed_status.flatten(), 
        'flexibility': flexibility.flatten(), 
        'predicted_finish': predicted_finish.flatten(), 
        'proposed_demand': proposed_demand.flatten(), 
        'actual_demand': actual_demand.flatten()}


def device_charger_storage(unixtime, unixstart, unixend, soc, charging_power, target_soc, capacity,
    connected, progress, actual_status, proposed_demand):
    '''
    Input states:
        Model for battery charger
        unixtime = current timestamp
        unixstart = timestamp for earliest start
        unixend = timestamp for latest end
        soc = state of charge [ratio]
        charging_power = charger power rating [w]
        target_soc = user-defined target soc [ratio]
        capacity = storage capacity [J or watt*s]
        connected = charger is connected to socket
        progress = charging progress
        actual_status = approved status by the dongle
        proposed_demand = proposed demand from previous step
    Output actions:
        proposed_status = proposed status
        flexibility = ldc flexibility
        priority = ldc priority
        predicted_finish = predicted time of finish
        proposed_demand = proposed demand
        actual_demand = actual demand
    '''
    ### calculate actual_demand based on approved status and proposed demand from previous step
    actual_demand = np.multiply(np.multiply(actual_status, proposed_demand), (progress<1)*1)
    
    ### update proposed_status and proposed_demand for next step
    proposed_status = ((progress<1)&(connected>0))*1
    proposed_demand = np.divide(charging_power, np.e**(np.multiply((soc>=0.9)*1, 
        np.subtract(np.multiply(soc, 100), 90))))  # mathematical model
    ### predict finish
    predicted_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
        soc), capacity), proposed_demand))
    ### predict finish and calculate flexibility based on newly proposed demand
    predicted_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
        soc), capacity), proposed_demand))
    flexible_horizon = np.multiply(np.subtract(unixend, predicted_finish), connected)
    operation_horizon = np.abs(np.subtract(unixend, unixstart))
    flexibility = np.divide(flexible_horizon, operation_horizon)
    
    return {'proposed_status': proposed_status.flatten(), 
        'flexibility': flexibility.flatten(), 
        'predicted_finish': predicted_finish.flatten(), 
        'proposed_demand': proposed_demand.flatten(), 
        'actual_demand': actual_demand.flatten()}
    
    


def device_ntcl(len_profile, unixtime, unixstart, unixend, connected, progress, 
    actual_status, proposed_demand):
    ''' 
    Generic model of Non-TCL loads that are based on a power profile
    Inputs:
        len_profile = length of the load profile in seconds
        unixtime = current timestamp
        unixstart = earliest timestamp to start the device
        unixend = latest timestamp to finish the job
        connected = signifies if the device is connected, i.e., unixstart <= unixtime < unixend
        progress = status of the job, i.e., range 0..1, 
        actual_status = approved status, 1=job is start, 0=delayed
        proposed_demand = proposed demand based on current progress and profile
    Outputs:
        proposed_status = proposed status for the next timestep
        flexibility = capability of the device to be delayed in starting
        priority = priority of the device based on its flexibility, used as decision variable for the ldc_dongles
        proposed_demand = proposed demand for the next timestep
        actual_demand = actual demand based on the previous proposed_demand and previous actual_status
    '''
    try:
        ### update proposed status and proposed_demand
        proposed_status = ((progress<1)&(connected>0))*1
        ### update flexibility 
        predicted_finish = np.add(np.multiply(np.subtract(np.ones(progress.shape), progress), len_profile), unixtime)
        flexible_horizon = np.multiply(np.subtract(unixend, predicted_finish), connected)
        operation_horizon = np.abs(np.subtract(unixend, unixstart))
        flexibility = np.divide(flexible_horizon, operation_horizon)
        ### get actual demand
        actual_demand = np.multiply(np.multiply(actual_status, proposed_demand), (progress<1)*1)
        
        
        return {
            'proposed_status': proposed_status, 
            'flexibility': flexibility, 
            'proposed_demand': proposed_demand, 
            'actual_demand': actual_demand}
            # proposed_status, flexibility, priority, proposed_demand, actual_demand 
            #(NOTE: actual_demand uses the proposed_demand and actual_status of the previous timestep)
    except Exception as e:
        print("Error MODELS.device_ntcl:",e)
        return {}



def device_wind(windspeed, capacity, speed_cut_in, speed_cut_off, ldc_case, priority):
    
    return 



def ziegler_nichols(
    K: float, # system gain
    T: float, # system time constant
    L: float, # system lag time, or dead time
    control_type: str, # type of controller: P, PI, or PID
    ) -> tuple:  # returns (Kp, Ki, Kd)
    """ Calculate the PID coefficients based on Ziegler-Nichols method.
    This function assumes that the plant being controlled can be modeled
    as a first-order system with time lag and delay
    G(s) = K e^(-Ls) / (Ts + 1)
    """
    if control_type=='P':
        Kp = T/L
        Ki = 0
        Kd = 0
    elif control_type=='PI':
        Kp = 0.9*(T/L)
        Ki = Kp * 0.3/L
        Kd = 0
    else: # PID
        Kp = 1.2*(T/L)
        Ki = Kp * 1/(2*L)
        Kd = Kp * 0.5*L
    return Kp, Ki, Kd


def abb_itae(
    K: float, # system gain
    T: float, # system time constant
    L: float, # system lag time, or dead time
    control_type: str, # type of controller: P, PI, or PID
    ) -> tuple:  # returns (Kp, Ki, Kd)
    """ Calculate the PID coefficients based on ABB Integral of Time-weighted Absolute Error (ITAE).
    This function assumes that the plant being controlled can be modeled
    as a first-order system with time lag and delay
    G(s) = K e^(-Ls) / (Ts + 1);
    where   K = system gain
            L = dead time
            T = time constant
    """
    if control_type=='P':
        Kp = 2.04*K*(L/T)**1.084
        Ki = 0
        Kd = 0
    elif control_type=='PI':
        Kp = 1.164*K*(L/T)**0.977
        Ki = Kp * (T*60/40.44)*(L/T)**0.68
        Kd = 0
    else: # PID
        Kp = 0.7369*K*(L/T)**0.947
        Ki = Kp * (T*60/51.02) * (L/T)**0.738
        Kd = Kp * (T*60/157.5) * (L/T)**0.995
    return Kp, Ki, Kd


dict_pid = {
    0.1: [0.23, 0.43, 0.12],
    0.2: [0.30, 0.59, 0.17],
    0.5: [0.49, 1.07, 0.26],
    2.0: [1.04, 3.49, 0.49],
    5.0: [1.42, 8.32, 0.92],
    10.0:[1.65, 16.35, 1.59]
    }


def median_filter(
    error: float,  # current error
    previous_error: float, # error in previous step
    step_size: float, # time step
    max_d: float, # maximum derivative, running value
    min_d: float, # minimum derivative, running value
    ) -> tuple:  # return tuple of (derivative, max_d, min_d)
    ### derivative should always be between max_d and min_d, 
    derivative = np.divide(np.subtract(error, previous_error), step_size)
    if derivative > max_d:
        return max_d, derivative, min_d
    elif derivative < min_d:
        return min_d, max_d, derivative
    else:
        return derivative, max_d, min_d
        

####### models for ldc #################
def ldc_injector(ldc_signal, latest, target, step_size, algorithm, hour=0, minute=0, 
    previous_error=0, previous_i_term=0, 
    derivative=0,
    max_d=0,
    min_d=0,
    K=5):
    '''
    Model for LDC signal injector
    Inputs:
        ldc_signal = the last injected signal, range 0...100
        latest_loading = latest power loading (percent of total capacity)
        target_loading = target power loading (percent of total capacity) for the the local grid
        step_size = time elapsed since the last signal was sent
        algorithm = algorithm used for the simulation
        hour = current hour
        minute = current minute
        previous_error = error from previous time step
        previous_i_term = integral term from previous time_step
    Outputs:
        ldc_signal = updated signal value
    '''

    ### basic ldc
    if algorithm=='no_ldc':
        return {'ldc_signal': np.power(ldc_signal,0)*100}
    elif algorithm in ['basic_ldc', 'advanced_ldc']:
        # use PID control

        G = K  # 
        T = 1.34e6 / G
        # Kp, Ti, Td = dict_pid[K]
        # Ki = Kp/Ti
        # Kd = Kp*Td
        
        Kp, Ki, Kd = abb_itae(1, K, 1, 'PID')

        error = np.subtract(target, latest) #np.divide(np.subtract(target_loading, latest_loading), target_loading)
        derivative, max_d, min_d  = median_filter(error, previous_error, step_size, max_d, min_d)

        p_term = np.multiply(Kp, error)
        i_term = np.clip(np.add(previous_i_term, np.multiply(error, step_size)), a_min=0, a_max=100/Ki) #np.add(signal, np.multiply(Ki, np.multiply(error, step_size)))
        d_term = derivative
        new_signal = np.add(p_term, np.add(np.multiply(Ki, i_term), np.multiply(Kd, d_term))) 
        return {
                'ldc_signal': np.clip(new_signal, a_min=0, a_max=100),
                'previous_error': error,
                'previous_i_term': i_term,
                'derivative': derivative,
                'max_d': max_d,
                'min_d': min_d,
            }
    elif algorithm=='ripple_control':
        return {'ldc_signal':np.power(ldc_signal,0)*ripple_signal(algorithm, hour, minute)}


# def ldc_injector(ldc_signal, latest_loading, target_loading, step_size, algorithm, hour=0, minute=0, 
#   previous_error=0, previous_i_term=0):
#   '''
#   Model for LDC signal injector
#   Inputs:
#     ldc_signal = the last injected signal, range 0...100
#     latest_loading = latest power loading (percent of total capacity)
#     target_loading = target power loading (percent of total capacity) for the the local grid
#     step_size = time elapsed since the last signal was sent
#     algorithm = algorithm used for the simulation
#     hour = current hour
#     minute = current minute
#     previous_error = error from previous time step
#     previous_i_term = integral term from previous time_step
#   Outputs:
#     ldc_signal = updated signal value
#   '''

#   ### basic ldc
#   if algorithm=='no_ldc':
#     return {'ldc_signal': np.power(ldc_signal,0)*100}
#   elif algorithm in ['basic_ldc', 'advanced_ldc']:
#     # use PID control
#     delta_p = np.subtract(target_loading, latest_loading)
#     G = 2**12  # 
#     T = 1.34e6 / G
#     k = 50 # controllable_percent
#     n_samples = 256 # number of filter samples 
#     f_nominal = 800 # nominal operating frequency [750-850]
#     T1 = n_samples/f_nominal
#     damping_ratio = 0.5*np.sqrt(T/(k*T1))
        
        
#     control_p = np.multiply(ldc_signal, (np.e**-1 *(np.e - 1)*k)) 
#     cmd_p = np.subtract(delta_p, control_p)
#     i_term = np.clip(np.multiply(cmd_p, step_size), a_min=0, a_max=100)
#     # print(damping_ratio, control_p, cmd_p)
#     return {'ldc_signal': np.clip(i_term, a_min=0, a_max=100), 'previous_i_term':i_term}
#   elif algorithm=='ripple_control':
#     return {'ldc_signal':np.power(signal,0)*ripple_signal(algorithm, hour, minute)}
        

# # ### test ldc_injector
# target_loading = 10
# latest_loading = 0
# signal = 0
# step_size = 1
# algorithm = 'basic_ldc'
# dict_test = {'ldc_signal':0, 'latest_loading':0, 'previous_error':0}
# for i in range(300):
#   print(i,dict_test)
#   dict_test.update(ldc_injector(ldc_signal=dict_test['ldc_signal'], 
#       latest_loading=dict_test['latest_loading'], 
#       target_loading=target_loading, 
#       step_size=step_size, 
#       algorithm=algorithm,
#       previous_error=dict_test['previous_error']))
#   dict_test.update({'latest_loading':dict_test['ldc_signal']+0.1*dict_test['latest_loading']-750})
#   # if dict_test['latest_loading'] - target_loading < 1e-16: break

def ripple_signal(algorithm, hour, minute):
    if algorithm=='ripple_control':
        if hour>=21:
            minute_block = ((hour-21)*60) + minute
            signal = 20 + (int(minute_block/10)*5)
        elif (hour>=4):
            minute_block = ((hour-4)*60) + minute
            signal = 100 - (int(minute_block/10)*5)
        elif (hour<4):
            signal = 100
        else:
            signal = 0.0
    else:
        if hour in [19,20,6,7]:  # peaks
            signal = 0.0
        else:
            signal = 100
    return np.clip(signal, a_min=0, a_max=100)    


def read_signal(old_signal, new_signal, n_units, resolution=1, delay=0.0, step_size=1, simulation=0):
    '''Randomly update ldc_signal'''
    try:
        delta_signal = np.subtract(new_signal, old_signal)
        delay = np.random.normal(delay, 10e-3, n_units)
        delayed_signal = np.clip(np.subtract(new_signal, np.multiply(delay, np.divide(delta_signal, step_size))), a_min=0, a_max=100)
        # print(new_signal, old_signal, delayed_signal[0])
        # idx = np.flatnonzero(ldc_signal!=new_signal)
        # w_new = np.clip(np.random.normal(0.99, 0.001, len(idx)), a_min=0.9, a_max=1.0)  # update the signal based on weights to avoid transient noise
        # w_old = np.subtract(1, w_new)
        # ldc_signal[idx] = np.add(np.multiply(ldc_signal[idx], w_old), np.multiply(w_new, np.round(new_signal, resolution)))
        return {'ldc_signal':np.round(delayed_signal, resolution), 'old_signal':new_signal}  
    except Exception as e:
        print(f"Error MODELS.read_signal:{e}")
        return {}
    


# def get_actual_status(flexibility, priority, algorithm, signal, proposed_status, with_dr, unixtime, ranking, hour=12):
#   if algorithm=='no_ldc':
#     return {
#       'actual_status': np.multiply(proposed_status, ((priority<=signal)|np.invert(with_dr))*1).flatten(),
#       'priority':priority * 0
#     }
#   elif algorithm=='basic_ldc':
#     if (ranking=='dynamic')&(int(unixtime)%60==0): 
#       priority = np.random.uniform(20,80,len(priority)) # change every 60 seconds

#     return {
#       'actual_status': np.multiply(proposed_status, ((priority<=signal)|np.invert(with_dr))*1).flatten(),
#       'priority':priority
#     }

#   elif algorithm=='advanced_ldc':
#     priority = normalize(flexibility * 100)
#     return {
#       'actual_status': np.multiply(proposed_status, ((priority<=signal)|np.invert(with_dr))*1).flatten(),
#       'priority':priority
#     }
#   elif algorithm=='ripple_control':
#     if hour<=7:
#       channels = np.subtract(100, priority)  # order is reversed
#     else:
#       channels = priority
        
#     return {
#       'actual_status': np.multiply(proposed_status, ((channels<=signal)|np.invert(with_dr))*1).flatten(),
#       'priority':priority
#     }
#     # NOTE: priorities are equivalent to channels, i.e., 20-80 : 11A10-11A25
#     # signals are sent in steps of 5, i.e, 20, 25, 30, 35
#     # each channel is turned ON for 7.5 hours between 9PM to 7AM
    

def normalize(value, a_min=20, a_max=80, x_max=100, x_min=0):
    x_max = max([x_max, np.max(value)])
    x_min = min([x_min, np.min(value)])
    return np.add(a_min, np.multiply(np.divide((value - x_min), (x_max - x_min)), 
                 np.subtract(a_max, a_min)))

def spread(priority):
    for i in range(20, 90, 5):
        idx = np.flatnonzero((priority>=i)&(priority<i+5))
        if idx.size:
            priority[idx] = normalize(value=priority[idx], a_min=20, a_max=80, x_min=i, x_max=i+5)
            
    return priority

def sigmoid(x):
  return 1 / (1 + np.exp(-x))

def swap_priority(priority):
    return np.subtract(100, priority)

def ldc_dongle(states, common):
    '''
    MOdel for the LDC dongle controllers
    Inputs:
        states = a dictionary containing all states of the device
        common = a dictionary containing variables for global states, e.g., clock, weather, etc.
    Outputs:
        dict of priority and actual_status
    '''   
    try:
        dict_signal = read_signal(old_signal=states['old_signal'], 
                    new_signal=common['ldc_signal'],
                    resolution=common['resolution'], 
                    n_units=len(states['load_type']),
                    delay=common['delay'], 
                    step_size=common['step_size'],
                    simulation=common['simulation'])

        ldc_signal = dict_signal['ldc_signal']  ## delayed_signal

        actions = {}
        proposed_status = states['proposed_status']
        cdiv = 1
        ### update priority and actual_status
        if common['algorithm']=='no_ldc':
            priority = states['priority'] * 0
            actual_status = np.multiply(states['proposed_status'], ((states['priority']<=ldc_signal)|np.invert(states['with_dr']))*1)
        elif common['algorithm'] in ['basic_ldc', 'advanced_ldc']:
            ### change proposed_status to avoid thermostat lock out
            if (states['load_type'][0] in ['heater', 'waterheater']): ### change the proposed status to avoid thermostat lock up
                ### virtual thermostat, has lockout based on deadband and f_reduce
                # if states['load_type'][0]=='waterheater':
                #     f_reduce = 1
                # else:
                #     f_reduce = 1
                # revised_cooling = ((((states['temp_in']>=np.subtract(states['temp_target'], np.multiply(states['tolerance'], 0.8))) & (states['actual_status']==1)) 
                #                             | ((states['temp_in']>=np.add(states['temp_target'], np.multiply(states['tolerance'], f_reduce)))&(states['actual_status']==0)))&(states['mode']==0)) * 1
                # revised_heating = ((((states['temp_in']<=np.add(states['temp_target'], np.multiply(states['tolerance'], 0.8)))&(states['actual_status']==1)) 
                #                             |  ((states['temp_in']<=np.subtract(states['temp_target'], np.multiply(states['tolerance'], f_reduce)))&(states['actual_status']==0)))&(states['mode']==1)) * 1
                
                ### virtual relay, no lockout
                revised_cooling = ((((states['temp_in']>=np.subtract(states['temp_target'], np.multiply(states['tolerance'], 0.9))) & (states['proposed_status']==1)))&(states['mode']==0)) * 1
                revised_heating = ((((states['temp_in']<=np.add(states['temp_target'], np.multiply(states['tolerance'], 0.9)))&(states['proposed_status']==1)))&(states['mode']==1)) * 1
                
                revised_status = np.add(revised_cooling, revised_heating)
                proposed_status = np.multiply(states['proposed_status'], revised_status)

            if common['algorithm']=='basic_ldc':
                ### change priority
                if (common['ranking']=='dynamic')&(common['unixtime']%60<1): 
                    priority = np.random.uniform(20,80,len(states['priority'])) # change every 60 seconds
                elif (common['ranking']=='evolve')&(common['unixtime']%60<1):
                    priority = np.add(np.remainder(np.add(states['priority'], 1), 60), 20)
                else:
                    priority = states['priority']
            elif common['algorithm']=='advanced_ldc':
                # priority is based on the flexibility and random number from normal distribution of mean 0 and std 1.0
                # normalized_flexibility = normalize(states['flexibility'], a_min=0, a_max=1, x_max=1.0, x_min=0.0)
                flex_priority = normalize(states['flexibility']*100, a_min=1, a_max=99, x_max=100, x_min=0)
                uniform_priority = np.random.uniform(1, 99, len(states['priority']))
                new_priority = np.add(np.multiply(flex_priority, common['flex']), np.multiply((1-common['flex']), uniform_priority))
                w = np.exp(-np.divide(common['step_size'], 3600))
                priority = ((w)*states['priority']) + ((1-w)*new_priority)  # alpha=1-w in exponentially weight moving average
                
                # priority = np.array([np.random.choice([100, x], p=[f, 1-f]) for x, f in zip(priority, normalized_flexibility)])
                # if (common['unixtime']%60 < 1):
                #     priority = swap_priority(states['priority'])
                # else:
                #     priority = states['priority']
                # cdiv = 59
                # priority = spread(states['flexibility']*100)
            ### change actual_status
            if states['load_type'][0] in ['clothesdryer', 'clotheswasher', 'dishwasher']:
                partial_status = np.multiply(proposed_status, ((priority<=ldc_signal)|np.invert(states['with_dr'])|(states['flexibility']<=0))*1)
                actual_status = (((states['actual_status']==1)&(states['finished']==0)) | ((partial_status==1)&(states['actual_status']==0)))*1
            elif states['load_type'][0] in ['heatpump', 'fridge', 'freezer']:
                if common['tcl_control'] in ['setpoint', 'mixed']:
                    actual_status = np.multiply(1, ((priority<=ldc_signal)|np.invert(states['with_dr']))*1)
                    idx = np.flatnonzero(states['with_dr'])
                    states['temp_target'][idx] = adjust_setpoint(actual_status=actual_status[idx],
                                                    mode=states['mode'][idx], 
                                                    cooling_setpoint=states['cooling_setpoint'][idx], 
                                                    heating_setpoint=states['heating_setpoint'][idx], 
                                                    temp_target=states['temp_target'][idx],
                                                    upper_limit=np.subtract(states['temp_max'][idx], states['tolerance'][idx]), 
                                                    lower_limit=np.add(states['temp_min'][idx], states['tolerance'][idx]),
                                                    algorithm=common['algorithm'],
                                                    step_size=common['step_size'])
                
                elif common['tcl_control'] in ['setpoint2', 'mixed2']:  # temp_target is coupled with the ldc_signal
                    actions.update({'temp_target': np.add(states['temp_min'], np.multiply(np.subtract(states['temp_max'], states['temp_min']), np.divide(states['ldc_signal'], 100))) })
                else:
                    actual_status = np.multiply(proposed_status, ((priority<=ldc_signal)|np.invert(states['with_dr'])|(states['flexibility']<=0))*1)

            elif states['load_type'][0] in ['heater', 'waterheater']:
                actual_status = np.multiply(proposed_status, ((priority<=ldc_signal)|np.invert(states['with_dr'])|(states['flexibility']<=0))*1)
            else:
                actual_status = np.multiply(proposed_status, ((priority<=ldc_signal)|np.invert(states['with_dr'])|(states['flexibility']<=0))*1)
            
            # if common['algorithm']=='advanced_ldc':
            #   actual_status = np.multiply(actual_status, [np.random.choice([0, 1], p=[f, 1-f]) for f in normalized_flexibility])

        elif common['algorithm']=='ripple_control':
            if common['hour']<=7:
                channels = np.subtract(100, states['priority'])  # order is reversed
            else:
                channels = states['priority']
            priority = states['priority']
            actual_status = np.multiply(proposed_status, ((channels<=ldc_signal)|np.invert(states['with_dr']))*1).flatten()

            # NOTE: priorities are equivalent to channels, i.e., 20-80 : 11A10-11A25
            # signals are sent in steps of 5, i.e, 20, 25, 30, 35
            # each channel is turned ON for 7.5 hours between 9PM to 7AM

        count_offset = np.subtract(states['counter'], states['min_cycletime'])
        ready_to_change = np.flatnonzero((count_offset>0)&(count_offset%cdiv<1))  # index of counters > min_cycletime
        changed = np.flatnonzero(np.add(states['actual_status'][ready_to_change], actual_status[ready_to_change])==1)  # index of those that actually changed, a changed status will add to 1, i.e., 0 to 1 = 0 + 1 = 1
        # if states['load_type'][0]=='heater': print(states['min_cycletime'][0], states['counter'][0], states['actual_status'][0], actual_status[0])
        # if states['load_type'][0] in ['waterheater', 'heater']: print(states['load_type'][0], np.round(np.min(states['counter']), 3), len(states['load_type']), len(ready_to_change), len(changed))
        states['actual_status'][ready_to_change] = actual_status[ready_to_change]
        states['counter'] = np.add(states['counter'], common['step_size'])  
        # for units that changed in status, reset counter to zero
        states['counter'][ready_to_change[changed]] = count_offset[ready_to_change[changed]] # + np.random.uniform(-3.0, 0.0, len(changed))  # 15:3bins per second
        actions.update({
            'priority': priority, 
            'actual_status':states['actual_status'], 
            'ldc_signal':ldc_signal, 
            'old_signal':dict_signal['old_signal'], 
            'counter':states['counter']
            })
        
        return actions
    except Exception as e:
        print(f"Error MODELS.ldc_dongle:{e}")
        return {}


    
# def ldc_dongle(flexibility, priority, algorithm, signal, proposed_status, with_dr, unixtime, ranking, hour=12):
#   '''
#   MOdel for the LDC dongle controllers
#   Inputs:
#     flexibility = flexibilit of the devices
#     priority = priority of the devices
#     algorithm = algorithm used
#     signal = ldc signal from the injector
#     proposed_status = proposed status of the devices
#     with_dr
#   Outputs:
#     actual_status = approved status of the devices
#     priority = priority of the devices
#   '''   

#   '''
#   TODO: 
#   - no ldc
#   - ripple control
#   - basic ldc
#   - advanced ldc
#   - smart ldc
#   '''
#   if algorithm=='no_ldc':
#     return {
#       'actual_status': np.multiply(proposed_status, ((priority<=signal)|np.invert(with_dr))*1).flatten(),
#       'priority':priority * 0
#     }
#   elif algorithm=='basic_ldc':
#     if (ranking=='dynamic')&(int(unixtime)%60==0): 
#       priority = np.random.uniform(20,80,len(priority)) # change every 60 seconds

#     return {
#       'actual_status': np.multiply(proposed_status, ((priority<=signal)|np.invert(with_dr))*1).flatten(),
#       'priority':priority
#     }

#   elif algorithm=='advanced_ldc':
#     priority = normalize(flexibility * 100)
#     return {
#       'actual_status': np.multiply(proposed_status, ((priority<=signal)|np.invert(with_dr))*1).flatten(),
#       'priority':priority
#     }
#   elif algorithm=='ripple_control':
#     if hour<=7:
#       channels = np.subtract(100, priority)  # order is reversed
#     else:
#       channels = priority
        
#     return {
#       'actual_status': np.multiply(proposed_status, ((channels<=signal)|np.invert(with_dr))*1).flatten(),
#       'priority':priority
#     }
#     # NOTE: priorities are equivalent to channels, i.e., 20-80 : 11A10-11A25
#     # signals are sent in steps of 5, i.e, 20, 25, 30, 35
#     # each channel is turned ON for 7.5 hours between 9PM to 7AM
    
    

def adjust_setpoint(actual_status, mode, cooling_setpoint, heating_setpoint, temp_target, upper_limit, lower_limit, algorithm, step_size):
    '''Adjust the setpoint
    Inputs:
        actual_status = approved status from the function ldc_dongle
        mode = 0 for cooling, 1 for heating
        cooling_setpoint = current setpoint
        heating_setpoint = current setpoint
        upper_limit = max allowable setpoint
        lower_limit = min allowable setpoint
        algorithm = algorithm used
        step_size = time elapsed
    Outputs:
        new_setpoint
    '''
    try:
        if algorithm in ['no_ldc', 'ripple_control', 'scheduled_ripple', 'peak_ripple', 'emergency_ripple']:
            temp_target = np.add(np.multiply((cooling_setpoint), (mode==0)*1), 
                np.multiply((heating_setpoint), (mode==1)*1))

            return temp_target
        else:
            ### decrease heating temp
            heating_decreased = np.multiply(np.subtract(temp_target, 0.1), np.multiply(((mode==1)*1), ((actual_status==0)*1)))
            heating_increased = np.multiply(np.add(temp_target, 0.1), np.multiply(((mode==1)*1), ((actual_status==1)*1)))
            ### increase cooling temp
            cooling_increased = np.multiply(np.add(temp_target, 0.1), np.multiply(((mode==0)*1), ((actual_status==0)*1)))
            cooling_decreased = np.multiply(np.subtract(temp_target, 0.1), np.multiply(((mode==0)*1), ((actual_status==1)*1)))

            new_cooling = np.clip(np.add(cooling_decreased, cooling_increased), a_min=(lower_limit+upper_limit)*0.5, a_max=upper_limit)
            new_heating =  np.clip(np.add(heating_decreased, heating_increased), a_min=lower_limit, a_max=(lower_limit+upper_limit)*0.5)
            temp_target = np.add(np.multiply(new_cooling, (mode==0)*1), np.multiply(new_heating, (mode==1)*1))

            return np.round(temp_target, 1)

    except Exception as e:
        print(f"Error MODELS.adjust_setpoint{e}")
        return temp_target
        

######## model for person #################
# from numba import jit
# @jit(nopython=True)
def make_schedule(unixtime, current_task, load_type_id, unixstart, unixend, schedule_skew):
    '''
    Make task schedules for different loads
    Inputs:
        unixtime = current timestamp
        current_task = scheduled task for current unixtime: 
                                    integer part denotes the type of load 
                                    while the decimal denotes the duration in seconds
        load_type = integer code denoting the type of load
    Outputs:
        unixstart = timestamp of earliest start of the load
        unixend = timestatmp of the latest end of the load
    '''
    try:
        tasks = np.floor(current_task)
        duration = np.multiply(np.subtract(current_task, tasks), 1e5) # retain decimal part and multiply by 1e5

        new_unixstart = np.multiply(((tasks==load_type_id))*1, np.add(unixtime, np.abs(schedule_skew)))
        new_unixend = np.add(new_unixstart, duration)
        update = (np.subtract(new_unixstart, unixstart)>0)*1
        retain = (np.subtract(new_unixstart, unixstart)<=0)*1

        unixstart = np.add(np.multiply(retain, unixstart), np.multiply(update, new_unixstart))
        unixend = np.add(np.multiply(retain, unixend), np.multiply(update, new_unixend))
        return {
            'unixstart': unixstart, 
            'unixend': unixend}
    except Exception as e:
        print(f"Error MODELS.make_schedule:{e}")
    

def is_connected(unixtime, unixstart, unixend):
    return {
        'connected': np.array((unixstart<=unixtime)&(unixend>unixtime))*1
        }


def get_solar(unixtime, humidity, latitude, longitude, elevation,
    roof_tilt, azimuth, albedo, isotime, 
    roof_area, wall_area, window_area, skylight_area):
    try:
        roof = solar.get_irradiance(
                            unixtime=unixtime,
                            humidity=humidity,
                            latitude=latitude,
                            longitude=longitude,
                            elevation=elevation,
                            tilt=roof_tilt,
                            azimuth=azimuth,
                            albedo=albedo,
                            isotime=isotime)
        dict_wall = {}
        for i in range(4):
            dict_wall.update({f'wall{i+1}': solar.get_irradiance(
                                                            unixtime=unixtime,
                                                            humidity=humidity,
                                                            latitude=latitude,
                                                            longitude=longitude,
                                                            elevation=elevation,
                                                            tilt=np.power(roof_tilt,0)*90,
                                                            azimuth=np.add(azimuth,i*90),
                                                            albedo=albedo,
                                                            isotime=isotime)})


        wall_area = wall_area / 4
        window_area = window_area / 4
        roof_area = roof_area / 2
        skylight_area = skylight_area / 2


        roof_heat = (np.multiply(roof, roof_area)*0.001) + (np.multiply(roof, skylight_area)*0.01)
        wall_heat = (np.multiply(wall_area, dict_wall['wall1'])*0.01)  \
            + (np.multiply(wall_area, dict_wall['wall2'])*0.01) \
            + (np.multiply(wall_area, dict_wall['wall3'])*0.001) \
            + (np.multiply(wall_area, dict_wall['wall4'])*0.001) \

        window_heat = (np.multiply(window_area, dict_wall['wall1'])*0.01)  \
            + (np.multiply(window_area, dict_wall['wall2'])*0.01) \
            + (np.multiply(window_area, dict_wall['wall3'])*0.001) \
            + (np.multiply(window_area, dict_wall['wall4'])*0.001) \

        return {'solar_heat':np.add(roof_heat, np.add(wall_heat, window_heat))}
    except Exception as e:
        print("Error MODELS.solar_heat:",e)
        return {}

def sum_heat_sources(solar_heat, heating_power_thermal, cooling_power_thermal):
    return {
        'heat_all':np.add(solar_heat, np.add(heating_power_thermal, cooling_power_thermal))
    }



def initialize_load(load_type, dict_devices, dict_house, idx, distribution, realtime=True):
    n_house = dict_devices['house']['n_units']
    n_units = dict_devices[load_type]['n_units']
    n_ldc = dict_devices[load_type]['n_ldc']
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
        df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
        if 'with_dr' in df.columns:
            idxs = df.index
            if distribution=='per_device':
                df['with_dr'] = False
                selection = np.random.choice(idxs, n_ldc, replace=False)
                df.loc[selection, 'with_dr'] = True
            else:
                df.loc[idxs[0:n_ldc], 'with_dr'] = True
                df.loc[idxs[n_ldc:], 'with_dr'] = False
        
        dict_out = df.to_dict(orient='list')
        del df

    for k, v in dict_out.items():
        dict_out[k] = np.array(v)
    
    if load_type in ['heatpump', 'heater']:
        dict_out['latitude'] = dict_house['latitude'][np.arange(n_units)%n_house]
        dict_out['longitude'] = dict_house['longitude'][np.arange(n_units)%n_house]
        dict_out['elevation'] = dict_house['elevation'][np.arange(n_units)%n_house]
        dict_out['roof_tilt'] = dict_house['roof_tilt'][np.arange(n_units)%n_house]
        dict_out['azimuth'] = dict_house['azimuth'][np.arange(n_units)%n_house]
        dict_out['albedo'] = dict_house['albedo'][np.arange(n_units)%n_house]
        dict_out['roof_area'] = dict_house['roof_area'][np.arange(n_units)%n_house]
        dict_out['wall_area'] = dict_house['wall_area'][np.arange(n_units)%n_house]
        dict_out['window_area'] = dict_house['window_area'][np.arange(n_units)%n_house]
        dict_out['skylight_area'] = dict_house['skylight_area'][np.arange(n_units)%n_house]
        dict_out['mass_flow'] = np.zeros(n_units)   
        dict_out['temp_target'] = dict_out['heating_setpoint'] 
        dict_out['solar_heat'] = np.zeros(n_units)

    if load_type in ['fridge', 'freezer']:
        dict_out['mass_flow'] = np.zeros(n_units)
        dict_out['mode'] = np.zeros(n_units)
        dict_out['temp_target'] = dict_out['cooling_setpoint']
        # air density is 1.225kg/m^3 at 15degC sea level
        # air density is 1.2041 kg/m^3 at 20 degC sea level
        # water density is 999.1 kg/m^3 at 15degC sea level
    if load_type in ['heater', 'waterheater']:
        dict_out['mode'] = np.ones(n_units)
        dict_out['temp_target'] = dict_out['heating_setpoint']
        dict_out['min_cycletime'] = np.random.uniform(1, 1.1, n_units)
        # dict_out['counter'] = np.random.uniform(2, 3, n_units)
        # dict_out['temp_in'] = np.random.normal(np.mean(dict_out['temp_in']), np.std(dict_out['temp_in']), n_units)

    if load_type in ['ev', 'storage']:
        dict_out['progress'] = np.divide(dict_out['soc'], dict_out['target_soc'])
        dict_out['mode'] = np.zeros(n_units)
        # dict_out['schedule_skew'] = np.random.uniform(-900, 900, n_units)
    if load_type in ['dishwasher', 'clothesdryer', 'clotheswasher']:
        dict_out['finished'] = np.zeros(n_units)
        dict_out['unfinished'] = np.ones(n_units) * 0.3
    if load_type in ['solar', 'wind']:
        dict_out['mode'] = np.ones(n_units)  # generation modes are 1
        dict_out['priority'] = np.zeros(n_units)
    
    dict_out['house'] = dict_house['name'][np.arange(n_units)%n_house]
    dict_out['schedule'] = dict_house['schedule'][np.arange(n_units)%n_house] 
    dict_out['unixstart'] = np.zeros(len(dict_out['schedule']))
    dict_out['unixend'] = np.ones(len(dict_out['schedule']))  
    dict_out['old_signal'] = np.zeros(n_units)
    dict_out['ldc_signal'] = np.zeros(n_units)
    # dict_out['counter'] = np.random.uniform(0, 30, n_units)
    # dict_out['min_cycletime'] = np.random.uniform(5, 30, n_units)
    # print(dict_out['load_type'][0], 'counter', dict_out['counter'])
    # print(dict_out['load_type'][0], 'min_cycletime', dict_out['min_cycletime'])

    if realtime==False:
        if load_type in ['baseload']:
            dict_out['priority'] = np.zeros(n_units)
        else:
            p_min = 20
            p_max = 80
            p_span = p_max - p_min
            # dict_out['priority'] = np.arange(p_min, p_max, p_span/n_units )
            # dict_out['priority'] = np.random.uniform(p_min, p_max, n_units )
    else:
        pass
            
    return dict_out


def initialize_device(n_parent, n_device, device_type, schedule):
    '''Initialize the variables for windows, valves, and doors
    inputs:
        n_parent = number of parent units, e.g., heatpump, heater, house, etc.
        n_device = number of windows, valves, or doors
        device_type = window, valve, or door
        schedule = schedule profile to be inherited from house
    output:
        dict_self = dictionary containing the variables
    '''
    dict_self = {}
    for i in range(n_device): # 5 windows
        dict_self.update({f'{device_type}{i}':{
            'unixstart': np.zeros(n_parent),
            'unixend': np.ones(n_parent),
            'connected': np.zeros(n_parent),
            'actual_status': np.zeros(n_parent)
        }})
    dict_self.update({'schedule':schedule})
    return dict_self

def update_device(n_device, device_type, dict_startcode, dict_self, dict_parent, dict_common):
    '''Update the variables for windows, valves, or doors
    inputs:
        n_device = number of windows, valves, or doors
        device_type = type of device, i.e., window, valve, or door
        dict_startcode = dictionary holding codes for device_type
        dict_self = dictionary holding data for windows, valves, or doors
        dict_parent = dictionary holding data for parent unit, e.g., waterheater, heatpump, etc.
        dict_common = dictionary holding common data, e.g., unixtime, weather, etc.
    output:
        dict_self = dictinary with updated values
    '''
    for i in range(n_device):
        ### update unixstart, unixend
        dict_self[f'{device_type}{i}'].update(make_schedule(unixtime=dict_common['unixtime'],
                current_task=dict_common['current_task'][dict_parent['schedule']].values,  # float, code.duration
                load_type_id= dict_startcode[device_type]+i, # 13 is the code for hot water {device_type}, 14 is for the cold {device_type}
                unixstart=dict_self[f'{device_type}{i}']['unixstart'],
                unixend=dict_self[f'{device_type}{i}']['unixend'],
                schedule_skew=dict_parent['schedule_skew']))
        ### update connected
        dict_self[f'{device_type}{i}'].update(is_connected(unixtime=dict_common['unixtime'],
                unixstart=dict_self[f'{device_type}{i}']['unixstart'],
                unixend=dict_self[f'{device_type}{i}']['unixend']))
        ### update actual_status
        dict_self[f'{device_type}{i}'].update({'actual_status':dict_self[f'{device_type}{i}']['connected']})
    
    return dict_self
                        
