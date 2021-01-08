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

import collections


try:
    from inspect import isfunction
    from numba import vectorize, njit, guvectorize
    has_numba = True
except ImportError:
    has_numba = False
    


######## helper functions #################
def update_dict(old_dict, new_dict):
    '''
    Update old dictionary using new dictionary.
    Parameters:
        old_dict: old dictionary
        new_dict: new dictionary
    Returns:
        old_dict, updated dictionary
    '''
    for k, v in new_dict.items():
        if isinstance(old_dict, collections.Mapping):
            if isinstance(v, collections.Mapping):
                r = update(old_dict.get(k, {}), v)
                old_dict[k] = r
            else:
                old_dict[k] = u[k]
        else:
            old_dict = {k: u[k]}
    return old_dict


def get_local_ip(report=False):
    # get local ip address
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            break
        except Exception as e:
            # if report: 
            print(f"{datetime.datetime.now().isoformat()} Error get_local_ip:{e}")
            time.sleep(10)
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




# def prepare_data(states, common):
#     try:
#         if states['load_type'][0] in ['heatpump', 'heater']:
#             return {np.round(common['unixtime'], 1):{
#             'temp_out': ','.join(np.char.zfill(np.round(states['temp_out'], 3).astype(str), 7)),
#             'humidity_out': ','.join(np.char.zfill(np.round(states['humidity'], 3).astype(str), 7)),
#             'windspeed': ','.join(np.char.zfill(np.round(states['windspeed'], 3).astype(str), 7)),
#             'temp_in': ','.join(np.char.zfill(np.round(states['temp_in'], 3).astype(str), 7)),
#             'temp_target': ','.join(np.char.zfill(np.round(states['temp_target'], 3).astype(str), 7)),
#             'humidity_in': ','.join(np.char.zfill(np.round(states['humidity_in'], 3).astype(str), 7)),
#             'flexibility': ','.join(np.char.zfill(np.round(states['flexibility'], 5).astype(str), 7)),
#             'priority': ','.join(np.char.zfill(np.round(states['priority'], 3).astype(str), 7)),
#             'actual_demand': ','.join(np.char.zfill(np.round(states['actual_demand'], 1).astype(str), 7)),
#             'ldc_signal': ','.join(np.char.zfill(np.round(states['ldc_signal'], 3).astype(str), 7)),
#             'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
#             'connected': ','.join(states['connected'].astype(int).astype(str)),
#             'mode': ','.join(states['mode'].astype(int).astype(str)),
#             }}
#         elif states['load_type'][0] in ['fridge', 'freezer', 'waterheater']:
#             return {np.round(common['unixtime'], 1):{
#             'temp_in': ','.join(np.char.zfill(np.round(states['temp_in'], 3).astype(str), 7)),
#             'temp_target': ','.join(np.char.zfill(np.round(states['temp_target'], 3).astype(str), 7)),
#             'flexibility': ','.join(np.char.zfill(np.round(states['flexibility'], 5).astype(str), 7)),
#             'priority': ','.join(np.char.zfill(np.round(states['priority'], 3).astype(str), 7)),
#             'actual_demand': ','.join(np.char.zfill(np.round(states['actual_demand'], 1).astype(str), 7)),
#             'ldc_signal': ','.join(np.char.zfill(np.round(states['ldc_signal'], 3).astype(str), 7)),
#             'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
#             'connected': ','.join(states['connected'].astype(int).astype(str)),
#             }}
#         elif states['load_type'][0] in ['clotheswasher', 'clothesdryer', 'dishwasher']:
#             return {np.round(common['unixtime'], 1):{
#             'progress': ','.join(np.char.zfill(np.round(states['progress'], 5).astype(str), 7)),
#             'flexibility': ','.join(np.char.zfill(np.round(states['flexibility'], 5).astype(str), 7)),
#             'priority': ','.join(np.char.zfill(np.round(states['priority'], 3).astype(str), 7)),
#             'actual_demand': ','.join(np.char.zfill(np.round(states['actual_demand'], 1).astype(str), 7)),
#             'ldc_signal': ','.join(np.char.zfill(np.round(states['ldc_signal'], 3).astype(str), 7)),
#             'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
#             'connected': ','.join(states['connected'].astype(int).astype(str)),
#             'mode': ','.join(states['mode'].astype(int).astype(str)),
#             }}
#         elif states['load_type'][0] in ['ev', 'storage']:
#             return {np.round(common['unixtime'], 1):{
#             'soc': ','.join(np.char.zfill(np.round(states['soc'], 5).astype(str), 7)),
#             'target_soc': ','.join(np.char.zfill(np.round(states['target_soc'], 5).astype(str), 7)),
#             'flexibility': ','.join(np.char.zfill(np.round(states['flexibility'], 5).astype(str), 7)),
#             'priority': ','.join(np.char.zfill(np.round(states['priority'], 3).astype(str), 7)),
#             'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
#             'mode': ','.join(states['mode'].astype(int).astype(str)),
#             'connected': ','.join(states['connected'].astype(int).astype(str)),
#             'actual_demand': ','.join(np.char.zfill(np.round(states['actual_demand'], 1).astype(str), 7)),
#             'ldc_signal': ','.join(np.char.zfill(np.round(states['ldc_signal'], 3).astype(str), 7)),
#             }}
#         elif states['load_type'][0] in ['solar', 'wind']:
#             return {np.round(common['unixtime'], 1):{
#             'priority': ','.join(np.char.zfill(np.round(states['priority'], 3).astype(str), 7)),
#             'actual_status': ','.join(states['actual_status'].astype(int).astype(str)),
#             'mode': ','.join(states['mode'].astype(int).astype(str)),
#             'connected': ','.join(states['connected'].astype(int).astype(str)),
#             'actual_demand': ','.join(np.char.zfill(np.round(states['actual_demand'], 1).astype(str), 7)),
#             'ldc_signal': ','.join(np.char.zfill(np.round(states['ldc_signal'], 3).astype(str), 7)),
#             }}
#         else:
#             return {np.round(common['unixtime'], 1):{
#             'actual_demand': ','.join(np.char.zfill(np.round(states['actual_demand'], 1).astype(str), 7)),
#             }}
#     except Exception as e:
#         print(f'Error MODELS.prepare_data:{e}')
#         print(states['temp_target'])

dict_params = {
    'temp_in': ['mean', 'min', 'max', 'std'], 
    'temp_target': ['mean', 'min', 'max', 'std'], 
    'temp_out': ['mean', 'min', 'max', 'std'], 
    'soc': ['mean', 'min', 'max', 'std'],  
    'target_soc': ['mean', 'min', 'max', 'std'], 
    'humidity_in': ['mean', 'min', 'max', 'std'], 
    'humidity_out': ['mean', 'min', 'max', 'std'], 
    'windspeed_out': ['mean', 'min', 'max', 'std'], 
    'flexibility': ['mean', 'min', 'max', 'std'],  
    'priority': ['mean', 'min', 'max', 'std'], 
    'actual_demand': ['sum'], 
    'actual_status': ['sum'],
    'proposed_status': ['sum'], 
    'mode': ['sum'],
    'connected': ['sum'],
    'ldc_signal': ['mean'],
    }

monitored_params = dict_params.keys()

def prepare_data(states, common):
    try:
        payload = {}
        states_params = states.keys()

        for k in monitored_params:
            if k in states_params:
                if np.isscalar(states[k]):
                    payload.update({k:[states[k]]})
                else:
                    payload.update({k:states[k].tolist()})

        return {common['unixtime']: payload} #{k:v for k, v in states.items() if k in params}}
    except Exception as e:
        print(f"Error prepare_data:{e}")
    



def prepare_summary(states, common):
    try:
        payload = {}
        states_params = states.keys()

        for k in monitored_params:
            if k in states_params:
                for m in dict_params[k]:
                    payload.update({f'{m}_{k}': eval(f'np.{m}(states["{k}"]).round(5)')})
        return {common['unixtime']: payload}
        
    except Exception as e:
        print(f"Error prepare_summary:{e}")

# def prepare_summary(states, common):
#     try:
#         if states['load_type'][0] in ['heatpump', 'heater']:
#             return {common['unixtime']:{
#             'mean_temp_out': states['temp_out'].mean().round(3),
#             'mean_humidity_out': states['humidity'].mean().round(3),
#             'mean_windspeed_out': states['windspeed'].mean().round(3),
#             'mean_temp_in': states['temp_in'].mean().round(3),
#             'min_temp_in': states['temp_in'].min().round(3),
#             'max_temp_in': states['temp_in'].max().round(3),
#             'std_temp_in': states['temp_in'].std().round(3),
#             'temp_in': ','.join(np.char.zfill(states['temp_in'].round(3).astype(str), 7)),
#             'temp_target': states['temp_target'].mean().round(3),
#             'mean_humidity_in': states['humidity_in'].mean().round(3),
#             'min_humidity_in': states['humidity_in'].min().round(3),
#             'max_humidity_in': states['humidity_in'].max().round(3),
#             'std_humidity_in': states['humidity_in'].std().round(3),
#             'mean_flexibility': states['flexibility'].mean().round(5),
#             'min_flexibility': states['flexibility'].min().round(5),
#             'max_flexibility': states['flexibility'].max().round(5),
#             'std_flexibility': states['flexibility'].std().round(5),
#             'mean_priority': states['priority'].mean().round(3),
#             'min_priority': states['priority'].min().round(3),
#             'max_priority': states['priority'].max().round(3),
#             'std_priority': states['priority'].std().round(3),
#             'sum_actual_demand': states['actual_demand'].sum().round(1),
#             'mean_ldc_signal': states['ldc_signal'].mean().round(3),
#             'sum_actual_status': states['actual_status'].sum(),
#             'sum_connected': states['connected'].sum(),
#             }}
#         elif states['load_type'][0] in ['fridge', 'freezer', 'waterheater']:
#             return {common['unixtime']:{
#             'mean_temp_in': states['temp_in'].mean().round(3),
#             'min_temp_in': states['temp_in'].min().round(3),
#             'max_temp_in': states['temp_in'].max().round(3),
#             'std_temp_in': states['temp_in'].std().round(5),
#             'temp_in': ','.join(np.char.zfill(states['temp_in'].round(3).astype(str), 7)),
#             'mean_temp_target': states['temp_target'].mean().round(3),
#             'mean_flexibility': states['flexibility'].mean().round(5),
#             'min_flexibility': states['flexibility'].min().round(5),
#             'max_flexibility': states['flexibility'].max().round(5),
#             'std_flexibility': states['flexibility'].std().round(5),
#             'mean_priority': states['priority'].mean().round(3),
#             'min_priority': states['priority'].min().round(3),
#             'max_priority': states['priority'].max().round(3),
#             'std_priority': states['priority'].std().round(3),
#             'sum_actual_demand': states['actual_demand'].sum().round(1),
#             'mean_ldc_signal': states['ldc_signal'].mean().round(3),
#             'sum_actual_status': states['actual_status'].sum(),
#             'sum_connected': states['connected'].sum(),
#             }}
#         elif states['load_type'][0] in ['clotheswasher', 'clothesdryer', 'dishwasher']:
#             return {common['unixtime']:{
#             'mean_progress': states['progress'].astype(float).mean().round(5),
#             'min_progress': states['progress'].astype(float).min().round(5),
#             'max_progress': states['progress'].astype(float).max().round(5),
#             'std_progress': states['progress'].astype(float).std().round(5),
#             'progress': ','.join(np.char.zfill(states['progress'].round(5).astype(str), 7)),
#             'mean_flexibility': states['flexibility'].astype(float).mean().round(5),
#             'min_flexibility': states['flexibility'].astype(float).min().round(5),
#             'max_flexibility': states['flexibility'].astype(float).max().round(5),
#             'std_flexibility': states['flexibility'].astype(float).std().round(5),
#             'mean_priority': states['priority'].astype(float).mean().round(5),
#             'min_priority': states['priority'].astype(float).min().round(5),
#             'max_priority': states['priority'].astype(float).max().round(5),
#             'std_priority': states['priority'].astype(float).std().round(5),
#             'sum_actual_demand': states['actual_demand'].astype(float).sum().round(5),
#             'mean_ldc_signal': states['ldc_signal'].astype(float).mean().round(5),
#             'sum_actual_status': states['actual_status'].astype(float).sum(),
#             'sum_connected': states['connected'].astype(float).sum(),
#             }}
#         elif states['load_type'][0] in ['ev', 'storage']:
#             return {common['unixtime']:{
#             'mean_soc': states['soc'].astype(float).mean().round(5),
#             'min_soc': states['soc'].astype(float).min().round(5),
#             'max_soc': states['soc'].astype(float).max().round(5),
#             'std_soc': states['soc'].astype(float).std().round(5),
#             'soc': ','.join(np.char.zfill(states['soc'].round(5).astype(str), 7)), 
#             'mean_target_soc': states['target_soc'].astype(float).mean().round(5),
#             'min_target_soc': states['target_soc'].astype(float).min().round(5),
#             'max_target_soc': states['target_soc'].astype(float).max().round(5),
#             'std_target_soc': states['target_soc'].astype(float).std().round(5),
#             'mean_flexibility': states['flexibility'].astype(float).mean().round(5),
#             'min_flexibility': states['flexibility'].astype(float).min().round(5),
#             'max_flexibility': states['flexibility'].astype(float).max().round(5),
#             'std_flexibility': states['flexibility'].astype(float).std().round(5),
#             'mean_priority': states['priority'].astype(float).mean().round(3),
#             'min_priority': states['priority'].astype(float).min().round(3),
#             'max_priority': states['priority'].astype(float).max().round(3),
#             'std_priority': states['priority'].astype(float).std().round(3),
#             'sum_actual_status': states['actual_status'].astype(float).sum(),
#             'sum_connected': states['connected'].astype(float).sum(),
#             'sum_actual_demand': states['actual_demand'].astype(float).sum().round(1),
#             'mean_ldc_signal': states['ldc_signal'].astype(float).mean().round(3),
#             }}
#         elif states['load_type'][0] in ['solar', 'wind']:
#             return {common['unixtime']:{
#             'mean_priority': states['priority'].mean().round(3),
#             'min_priority': states['priority'].min().round(3),
#             'max_priority': states['priority'].max().round(3),
#             'std_priority': states['priority'].std().round(3),
#             'sum_actual_status': states['actual_status'].sum(),
#             'sum_connected': states['connected'].sum(),
#             'sum_actual_demand': states['actual_demand'].sum().round(1),
#             'mean_ldc_signal': states['ldc_signal'].mean().round(3),
#             }}
#         else:
#             return {common['unixtime']:{
#             'sum_actual_demand': states['actual_demand'].sum().round(1),
#             }}
#     except Exception as e:
#         print(f'Error MODELS.prepare_summary:{e}')
#         print(states['temp_target'])


# def save_data(dict_save, folder, filename, case, sample='1S', summary=False):
#     try:
#         df = pd.DataFrame.from_dict(dict_save, orient='index')
#         df.index = pd.to_datetime(df.index, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
#         path = f'/home/pi/studies/results/{folder}/{case}'
#         os.makedirs(path, exist_ok=True)  # create folder if none existent
#         df.to_hdf(f'{path}/{filename}', 
#                     key=f'records', mode='a', append=True, 
#                     complib='blosc', complevel=9, format='table')
#         return {}  # empty dict_save if saving is successful
#     except Exception as e:
#         print(f"Error MODELS.save_data:{e}")
#         print(folder, filename)
#         print(df.dtypes)
#         for k, v in dict_save.items():
#             for x, y in v.items():
#                 print(x, y)
#         # print(df.describe())
#         return dict_save

def save_data(dict_save, folder, filename, case, sample='1S', summary=False):
    try:
        path = f'/home/pi/studies/results/{folder}/{case}'
        os.makedirs(path, exist_ok=True)  # create folder if none existent
        dict_save = save_pickle(dict_save, path=f'{path}/{filename.split(".")[0]}.pkl')
        return dict_save  # empty dict_save if saving is successful
    except Exception as e:
        print(f"Error MODELS.save_data:{e}")
        print(folder, filename)
        for k, v in dict_save.items():
            for x, y in v.items():
                print(x, y)
        # print(df.describe())
        return dict_save
        

def save_pickle(dict_data, path='history/data.pkl.xz'):
    'Save data as pickle file.'
    try:
        df_all = pd.DataFrame.from_dict(dict_data, orient='index')
        try:
            on_disk = pd.read_pickle(path, compression='infer')
            df_all = pd.concat([on_disk, df_all], axis=0, sort=False)
            df_all.to_pickle(path, compression='infer')
        except Exception as e:
            df_all.to_pickle(path, compression='infer')
        
        return {}
    except Exception as e:
        print("Error save_pickle:", e)
        return dict_data 

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
        # step_size = np.random.uniform(0.1, step_size*2)
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
### TCL ###
def compute_temp_in(temp_in, temp_out, temp_fill, heat_all, Ua, Ca, Cp, mass_flow, step_size):
    """
    Compute the temperature inside the thermal zone based on the model:
    Two-state RC model defined by dynamic equation:
    dTz/dt = Q + mCp(Tf-Tz) + U(To-Tz)

    Solution is:
    Tz = (QR + mCpRTf + To) / (mCpR+1) + ((e^(-tRC/(mCpR+1))) * (K mCpR + K -(QR+mCpR Tf + To))/(mCpR+1))
    
    Args:
        temp_in : temperature inside the thermal zone [°C]
        temp_out: temperature outside the thermal zone [°C]
        temp_fill: temperature of the refill medium (e.g., air, water) [°C]
        heat_all: net heat introduced to the zone [J]
        Ua: thermal conductance of the zone []
        Ca: thermal capacitance of the zone
        Cp: heat capacity of the medium
        mass_flow: flow rate of mass
        step_size: time step size
        
    Returns:
        temp_in: updated temperature inside the thermal zone [°C]

    Reference:

    """
    R = 1 / Ua
    tt = np.multiply(mass_flow, np.multiply(Cp, R)) + 1
    tau = np.multiply(Ca, R) / tt
    a = np.exp(-np.divide(step_size, tau))
    return ((a*temp_in) + ((1-a) * ((temp_out + ((R*heat_all) + ((mass_flow*Cp)*(R*temp_fill)))) / tt) ))


def enduse_tcl(states):
    '''
    Wrapper for enduse model of thermostat-controlled loads.
    
    Args:
        states: state parameters of the device
    
    Returns:
        states: updated state parameters
    '''
    states['temp_fill'] = np.asarray(states['temp_out']).reshape(-1)

    states['heat_all'] = np.add(
        states['solar_heat'], 
        states['power_thermal']
        ).reshape(-1)

    states['temp_in'] = np.asarray(compute_temp_in(
        states['temp_in'], 
        states['temp_out'], 
        states['temp_fill'], 
        states['heat_all'], 
        states['Ua'], 
        states['Ca'], 
        states['Cp'], 
        states['mass_flow'], 
        states['step_size'],
        )).reshape(-1)
    
    return states

### battery ###
def compute_soc(soc, actual_demand, capacity, step_size, charging_efficiency):
    '''
    Calculate the state of charge based on a math model.
    
    Args:
        soc: state of charge of the battery
        actual_demand: power demand to charge the battery
        capacity: battery rated capacity
        step_size: time step,
        charging_efficiency: efficiency of charger

    Returns:
        soc: updated state of charge

    References:

    '''
    return ((actual_demand*step_size*charging_efficiency) + (soc*capacity)) / capacity


def compute_battery_demand(driving, driving_power, actual_demand):
    '''
    Calculate the state of charge based on a math model.
    
    Args:
        driving: boolean if currently driving
        driving_power: power extracted from battery to EV motors
        
    Returns:
        driving_power: power extracted from the battery

    References:

    '''
    if driving==1:
        return driving_power
    else:
        return actual_demand


def compute_progress_battery(soc, target_soc, connected):
    '''
    Calculate charging progress.

    Args:
        soc: state of charge of the battery [0..1]
        target_soc: target state of charge [0..1]
        connected: state of device if plugged in or not [0,1]

    Returns:
        progress: progress of charging with respect to desired soc

    References:

    '''
    return (soc/target_soc)*connected

def enduse_battery(states):
    '''
    Wrapper for model of battery-based loads.
    
    Args:
        states: state parameters of the device
    
    Returns:
        states: updated state parameters
        
    '''
    if 'ev' in states['load_type']:
        states['soc'] = np.asarray(compute_soc(
            states['soc'],
            compute_battery_demand(
                states['driving'], 
                states['driving_power'],
                states['actual_demand'],
                ),
            states['capacity'], 
            states['step_size'],
            states['charging_efficiency'],
            )).reshape(-1)

    else:
        states['soc'] = np.asarray(compute_soc(
            states['soc'], 
            states['actual_demand'], 
            states['capacity'], 
            states['step_size'],
            states['charging_efficiency']
            )).reshape(-1)

    states['progress'] = np.asarray(compute_progress_battery(
        states['soc'], 
        states['target_soc'], 
        states['connected'],
        )).reshape(-1)

    return states
    


### NTCL ###
def compute_progress_ntcl(progress, len_profile, step_size, actual_status, connected):
    '''
    Model for usage of non-urgent non-thermostat controlled load.

    Args:
        progress: job progress [0..1]
        profile_duration: duration of the entire job profile [s]
        step_size: time step [s]
        actual_status: ON or OFF status of the device [0,1]
        connected: status if the device is plugged-in [0,1]

    Returns:
        progress: updated progress of the device job

    '''
    return (progress + ((step_size/len_profile)*actual_status)) * connected
    
    
def enduse_ntcl(states):
    '''
    Wrapper for enduse model of non-urgent non-TCL.

    Args:
        states: state parameters of the device
    
    Returns:
        states: updated state parameters
    '''
    states['progress'] = np.asarray(compute_progress_ntcl(
        states['progress'], 
        states['len_profile'], 
        states['step_size'], 
        states['actual_status'], 
        states['connected'],
        )).reshape(-1)
    
    states['soc'] = states['progress']

    return states


############# models for devices #######################################################
### TCL ###
def compute_proposed_status_tcl(mode, proposed_status, temp_in, temp_target, tolerance):
    '''
    Determine the status of the TCL 

    Args:
        mode: mode of operation [0=cooling, 1=heating]
        proposed_status: previous proposed_status
        temp_in: inside temperature
        temp_target: target temperature
        tolerance: setpoint tolerance
    '''
    if mode==0 and proposed_status==1 and temp_in>=(temp_target-tolerance):
        return 1
    elif mode==0 and proposed_status==0 and temp_in>=(temp_target+tolerance):
        return 1
    elif mode==1 and proposed_status==1 and temp_in<=(temp_target+tolerance):
        return 1
    elif mode==1 and proposed_status==0 and temp_in<=(temp_target-tolerance):
        return 1
    
    return 0


def compute_proposed_demand_tcl(mode, cooling_power, heating_power, standby_power, ventilation_power, proposed_status):
    '''
    Calculate proposed power demand.

    Args:
        mode: operation mode [0=cooling, 1=heating]
        cooling_power: cooling input electrical power demand
        heating_power: heating input electrical power demand
        standby_power: standby power demand
        ventilation_power: ventilation power demand 
        proposed_status: proposed status

    Returns:
        proposed_demand: proposed electrical demand [W]
    '''
    if mode==0:
        return (proposed_status*cooling_power) + standby_power + ventilation_power
    elif mode==1:
        return (proposed_status*heating_power) + standby_power + ventilation_power
    
    return 0

def compute_actual_demand_tcl(proposed_demand, standby_power, ventilation_power, actual_status):
    '''
    Calculate the actual power demand.

    Args:
        mode: operation mode [0=cooling, 1=heating]
        proposed_demand: proposed electrical demand [W]
        standby_power: standby power demand
        ventilation_power: ventilation power demand
        actual_status: actual approved power demand

    Returns:
        actual power demand
    
    References:

    '''
    return (actual_status*proposed_demand) + standby_power + ventilation_power
    

def compute_power_thermal(mode, actual_demand, cop):
    '''
    Calculate the equivalent thermal power injected to or removed from the thermal zone

    Args:
        mode: operation mode [0=cooling, 1=heating]
        actual_demand: actual electrical power demand
        cop: coefficient of performance
        actual_status: actual approved status

    Returns:
        power_thermal: equivalent thermal power
    '''
    if mode==0:
        return actual_demand * cop * -1
    elif mode==1:
        return actual_demand * cop
    
    return 0


def compute_flexibility_tcl(mode, temp_in, temp_min, temp_max):
    '''
    Calculate the flexibility of thermostat controlled device.

    Args:
        mode: operation mode [0=cooling, 1=heating]
        temp_in: temperature inside the thermal zone
        temp_min: minimum allowable temperature
        temp_max: maximum allowable temperature

    Returns:
        flexibility: flexibility of the device
    '''
    if mode==0:
        return (temp_max-temp_in) / (temp_max-temp_min)
    elif mode==1:
        return (temp_in-temp_min) / (temp_max-temp_min)
    
    return 0


def device_tcl(states, common, inverter=False):
    # device model for vapor compresion cycle, e.g., freezer, fridge, air condition
    ''' 
    Generic model for thermostat-controlled loads
    
    Args:
        states: dictionary containing state parameters of the device
        common: dictionary containing common data and settings

    Returns:
        updated states

    '''
    try:
        ### calculate actual demand and actual thermal output
        states['actual_demand'] = np.asarray(compute_actual_demand_tcl(
            states['proposed_demand'], 
            states['standby_power'], 
            states['ventilation_power'], 
            states['actual_status'],
            )).reshape(-1)

        ### calculate actual thermal power injected or removed from the thermal zone
        states['power_thermal'] = np.asarray(compute_power_thermal(
                states['mode'], 
                states['actual_demand'], 
                states['cop'], 
                )).reshape(-1)

        ### update proposed status and proposed demand
        states['proposed_status'] = np.asarray(compute_proposed_status_tcl(
            states['mode'], 
            states['proposed_status'], 
            states['temp_in'], 
            states['temp_target'], 
            states['tolerance'],
            )).reshape(-1)

        states['proposed_demand'] = np.asarray(compute_proposed_demand_tcl(
            states['mode'], 
            states['cooling_power'], 
            states['heating_power'], 
            states['standby_power'], 
            states['ventilation_power'], 
            states['proposed_status'],
            )).reshape(-1)

        ### update flexibility
        states['flexibility'] = np.asarray(compute_flexibility_tcl(
            states['mode'], 
            states['temp_in'], 
            states['temp_min'], 
            states['temp_max'],
            )).reshape(-1)

        # for k, v in states.items():
        #     print(k, v)

        return 
    except Exception as e:
        print("Error MODELS.device_tcl:{}".format(e))
        return {}


### Battery-based ###
def compute_finish_battery(unixtime, target_soc, soc, capacity, proposed_demand):
    '''
    Predict finish time of charging.

    Args:
        unixtime: current timestamp
        target_soc: target state of charge
        soc: current state of charge
        capacity: battery capacity [W*s]
        proposed_demand: proposed power demand [W]

    Returns:
        predicted_finish: timestamp of forecasted finish
    
    References:

    '''
    return unixtime + (((target_soc-soc)*capacity)/proposed_demand)


def compute_flexible_horizon(unixend, predicted_finish, connected):
    '''
    Calculate flexible horizon.

    Args:
        unixend: desired timestamp when SOC should reach the target level [timestamp]
        predicted_finish: forecasted timestamp when target SOC is reached [timestamp]
        connected: status of the device [0=unplugged, 1=connected]

    Returns:
        flexible_horizon: flexible time horizon [s]

    References:

    '''
    return (unixend-predicted_finish)*connected


def compute_operation_horizon(unixstart, unixend):
    '''
    Calculate operation time horizon

    Args:
        unixstart: start of charging or process [timestamp]
        unixend: target end of charging or process [timestamp]

    Returns:
        operation_horizon

    References:

    '''
    return unixend-unixstart





# def compute_flexibility_battery(flexible_horizon, operation_horizon, connected):
#     '''
#     Calculate the device flexibility.

#     Args:
#         flexible_horizon: flexible part of operation horizon
#         operation_horizon: total operation horizon
#         connected: boolean if device is plugged in
        
#     Returns:
#         flexibility: flexibility of the device

#     References:

#     '''
#     if connected>0:
#         return flexible_horizon/operation_horizon
#     else:
#         return 0


def compute_adjusted_min_soc(min_soc, target_soc, unixtime, unixstart, unixend):
    '''
    Adjust minimum state of charge to consider charging schedule.

    Args:
        min_soc: minimum allowable state of charge
        target_soc: target state of charge
        unixtime: current timestamp
        unixstart: earliest start timestamp
        unixend: latest finish timestamp

    Returns:
        min_soc: adjusted min_soc
    '''
    # if unixstart==0 or unixend==1:
    #     adjusted_min_soc = min_soc
    # else:

    return target_soc * (1-np.exp(-(unixend-unixstart)/((unixend-unixstart)*0.7)))  #(1 - np.(unixtime-unixstart) / (unixend-unixstart))
    
    # if adjusted_min_soc>=target_soc:
    #     return target_soc-0.1
    # elif min_soc>=adjusted_min_soc:
    #     return min_soc
    # else:
    #     return adjusted_min_soc


def compute_flexibility_battery(soc, target_soc, min_soc, connected):
    '''
    Calculate device flexibility.
    
    Args:
        soc: state of charge
        target_soc: target state of charge
        min_soc: minimum state of charge

    Returns:
        flexibility: flexibility of the device

    '''
    if connected>0:
        return (soc-min_soc) / (target_soc-min_soc)
    else:
        return 0
    

def compute_proposed_demand_battery(charging_power, soc):
    '''
    Mathematical model of battery charger.
    (charging_power / np.e**(((soc>=0.9)*1 *((soc*100)-90))))  # mathematical model

    Args:
        charging_power: rated charging power
        soc: state of charge

    Returns:
        power_demand: power demand as a function of soc [W]

    References:

    '''
    if soc>=0.9:
        return charging_power * np.e**-((soc-0.9)*100)
    else:
        return charging_power


def compute_proposed_status_battery(progress, connected):
    '''
    Determine the charger status.

    Args:
        progress: charging progress
        connected: status of charger [0=unplugged, 1=plugged]

    Returns:
        status: status of charger [0,1]
    
    References:

    '''
    if progress<1 and connected>0:
        return 1
    else:
        return 0
    

def compute_actual_demand_battery(proposed_demand, charging_power, priority, priority_offset, b2g, with_dr, connected):
    '''
    Calculate actual or approved power demand.

    Args:
        proposed_demand: proposed charging power [W]
        charging_power: rating of the charger / inverter
        priority: priority value of the device
        priority_offset: offset of priority from ldc_signal
        b2g: battery to grid capability [0,1]
        with_dr: response capability [0,1]
        connected: boolean if plugged in [0,1]
        
    Returns:
        actual_demand: actual or approved power demand [W]
    References:

    '''
    if (connected==0) or (with_dr==1 and b2g==0 and priority_offset<0):
        return 0
    elif (with_dr==1 and b2g==1 and priority_offset<0 and priority>20):
        return -1 * charging_power * compute_normalize(abs(priority_offset), 0.0, 90.0, 0.0, 1.0)
    elif (with_dr==1):
        new_demand = proposed_demand * (compute_normalize(priority_offset, 0.0, 90-priority, 0.0, 1.0))
        if new_demand>proposed_demand:
            return proposed_demand
        else:
            return new_demand

    else:
        return proposed_demand
        

def device_battery(states):
    ''' 
    Generic model of Battery-based loads.

    Args:
        states: dictionary containing the state of the device
        
    Returns:
        updated dictionary
    
    References:
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
    states['actual_demand'] = np.asarray(compute_actual_demand_battery(
        states['proposed_demand'], 
        states['charging_power'],
        states['priority'],
        states['priority_offset'], 
        states['b2g'],
        states['with_dr'],
        states['connected'],
        )).reshape(-1)
    

    ### update proposed_status and proposed_demand for next step
    states['proposed_status'] = np.asarray(compute_proposed_status_battery(
        states['progress'], 
        states['connected'])).reshape(-1)

    ### mathematical model
    states['proposed_demand'] = np.asarray(compute_proposed_demand_battery(
        states['charging_power'], 
        states['soc'])).reshape(-1)

    ### predict finish and calculate flexibility based on newly proposed demand
    # states['predicted_finish'] = compute_finish_battery(
    #     states['unixtime'], 
    #     states['target_soc'], 
    #     states['soc'], 
    #     states['capacity'], 
    #     states['proposed_demand'],
    #     )
    # states['flexible_horizon'] = compute_flexible_horizon(
    #     states['unixend'], 
    #     states['predicted_finish'], 
    #     states['connected'],
    #     )
    # states['operation_horizon'] = compute_operation_horizon(
    #     states['unixstart'], 
    #     states['unixend'],
    #     )
    # states['flexibility'] = compute_flexibility_battery(
    #     states['flexible_horizon'],
    #     states['operation_horizon'],
    #     )

    if 'ev' in states['load_type']:
        states['flexibility'] = np.asarray(compute_flexibility_battery(
            states['soc'], 
            states['target_soc'], 
            compute_adjusted_min_soc(
                states['min_soc'],
                states['target_soc'],
                states['unixtime'],
                states['unixstart'],
                states['unixend'],
                ),
            states['connected'],
            )).reshape(-1)
            
    else:
        states['flexibility'] = np.asarray(compute_flexibility_battery(
            states['soc'], 
            states['target_soc'], 
            states['min_soc'],
            states['connected'],
            )).reshape(-1)
    

    return states
        



# def device_charger_ev(unixtime, unixstart, unixend, soc, charging_power, target_soc, capacity,
#     connected, progress, actual_status, proposed_demand):
#     '''
#     Input states:
#         Model for EV charger
#         unixtime = current timestamp
#         unixstart = timestamp for earliest start
#         unixend = timestamp for latest end
#         soc = state of charge [ratio]
#         charging_power = charger power rating [w]
#         target_soc = user-defined target soc [ratio]
#         capacity = storage capacity [J or watt*s]
#         connected = charger is connected to socket
#         progress = charging progress
#         actual_status = approved status by the dongle
#         proposed_demand = proposed demand from previous step
#     Output actions:
#         proposed_status = proposed status
#         flexibility = ldc flexibility
#         priority = ldc priority
#         predicted_finish = predicted time of finish
#         proposed_demand = proposed demand
#         actual_demand = actual demand


#     '''
#     ### calculate actual_demand based on approved status and proposed demand from previous step
#     actual_demand = np.multiply(np.multiply(actual_status, proposed_demand), (progress<1)*1)
#     ### update proposed_status and proposed_demand for next step
#     proposed_status = ((unixstart<=unixtime) & (unixend>=unixtime)) * 1
#     ### get proposed_demand
#     # proposed_demand = np.divide(charging_power, np.e**(np.multiply((soc>=0.9)*1, 
#     #   np.subtract(np.multiply(soc, 100), 90))))  # mathematical model
#     proposed_demand = proposed_demand  # model based on actual data from pecan street
#     ### predict finish and calculate flexibility based on newly proposed demand
#     predicted_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
#         soc), capacity), proposed_demand))
#     flexible_horizon = np.multiply(np.subtract(unixend, predicted_finish), connected)
#     operation_horizon = np.abs(np.subtract(unixend, unixstart))
#     flexibility = np.divide(flexible_horizon, operation_horizon)
    
#     return {'proposed_status': proposed_status.flatten(), 
#         'flexibility': flexibility.flatten(), 
#         'predicted_finish': predicted_finish.flatten(), 
#         'proposed_demand': proposed_demand.flatten(), 
#         'actual_demand': actual_demand.flatten()}


# def device_charger_storage(unixtime, unixstart, unixend, soc, charging_power, target_soc, capacity,
#     connected, progress, actual_status, proposed_demand):
#     '''
#     Input states:
#         Model for battery charger
#         unixtime = current timestamp
#         unixstart = timestamp for earliest start
#         unixend = timestamp for latest end
#         soc = state of charge [ratio]
#         charging_power = charger power rating [w]
#         target_soc = user-defined target soc [ratio]
#         capacity = storage capacity [J or watt*s]
#         connected = charger is connected to socket
#         progress = charging progress
#         actual_status = approved status by the dongle
#         proposed_demand = proposed demand from previous step
#     Output actions:
#         proposed_status = proposed status
#         flexibility = ldc flexibility
#         priority = ldc priority
#         predicted_finish = predicted time of finish
#         proposed_demand = proposed demand
#         actual_demand = actual demand
#     '''
#     ### calculate actual_demand based on approved status and proposed demand from previous step
#     actual_demand = np.multiply(np.multiply(actual_status, proposed_demand), (progress<1)*1)
    
#     ### update proposed_status and proposed_demand for next step
#     proposed_status = ((progress<1)&(connected>0))*1
#     proposed_demand = np.divide(charging_power, np.e**(np.multiply((soc>=0.9)*1, 
#         np.subtract(np.multiply(soc, 100), 90))))  # mathematical model
#     ### predict finish
#     predicted_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
#         soc), capacity), proposed_demand))
#     ### predict finish and calculate flexibility based on newly proposed demand
#     predicted_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
#         soc), capacity), proposed_demand))
#     flexible_horizon = np.multiply(np.subtract(unixend, predicted_finish), connected)
#     operation_horizon = np.abs(np.subtract(unixend, unixstart))
#     flexibility = np.divide(flexible_horizon, operation_horizon)
    
#     return {'proposed_status': proposed_status.flatten(), 
#         'flexibility': flexibility.flatten(), 
#         'predicted_finish': predicted_finish.flatten(), 
#         'proposed_demand': proposed_demand.flatten(), 
#         'actual_demand': actual_demand.flatten()}
    
    

### NTCL ###
def compute_actual_demand_ntcl(proposed_demand, actual_status):
    '''
    Calculate actual demand of NTCL.

    Args:
        proposed_demand: proposed power demand
        actual_status: actual or approved status
    
    Returns:
        actual_demand: approved demand
    '''
    return proposed_demand * actual_status


def compute_proposed_status_ntcl(progress, connected):
    '''
    Determine the status of the non-urgent non-TCL device.

    Args:
        progress: job progress
        connected: status if device is plugged in or job is pending.

    Returns:
        proposed_status: proposed status for the next timestep
    '''
    if connected==1 and progress<1.0:
        return 1
    return 0
    

def compute_finish_ntcl(unixtime, progress, len_profile):
    '''
    Predict the expected finish time.

    Args:
        unixtime: current timestamp
        progress: progress of the NTCL job
        len_profile: duration of the profile of the NTCL

    Returns:
        predicted_finish
    '''
    return unixtime + ((1-progress)*len_profile)
    

def compute_flexibility_ntcl(unixstart, unixend, predicted_finish, len_profile):
    '''
    Calculate the flexibility of the non-urgent non-thermostat-controlled loads.

    Args:
        unixstart: earliest start
        unixend: latest finish
        predicted_finish: predicted finish time
        len_profile: duration of the profile

    Returns:
        flexibility: flexibility of the device
    '''
    return (unixend-predicted_finish) / (unixend-(unixstart+len_profile))


def device_ntcl(states, dict_data):
    ''' 
    Generic model of Enduse of non-urgent non-thermostat controlled loads.
    
    Args:
        states: dictionary containing the state of the device
        dict_data: dictionary containing the representative profiles for the device

    Returns:
        updated dictionary
    '''
    ### calculate actual_demand based on approved status and proposed demand from previous step
    states['actual_demand'] = np.asarray(compute_actual_demand_ntcl(
        states['proposed_demand'], 
        states['actual_status'], 
        )).reshape(-1)

    ### update proposed_status and proposed_demand for next step
    states['proposed_status'] = np.asarray(compute_proposed_status_ntcl(
        states['progress'], 
        states['connected'],
        )).reshape(-1)

    ### mathematical model
    # states['proposed_demand'] = compute_proposed_demand_ntcl(
    #     states['charging_power'], 
    #     states['soc'])

    # states['proposed_demand'] = np.array([np.interp(x*y, np.arange(y), dict_data[k]) for k, x, y in zip(states['profile'], states['len_profile'], states['progress'])]).flatten()
    states['proposed_demand'] = np.asarray([dict_data[k][int((x*y)%x)] for k, x, y in zip(
        states['profile'], 
        states['len_profile'], 
        states['progress'])]).reshape(-1)

    ### predict finish and calculate flexibility based on newly proposed demand
    states['predicted_finish'] = np.asarray(compute_finish_ntcl(
        states['unixtime'], 
        states['progress'], 
        states['len_profile'],
        )).reshape(-1)

    ### get flexibility
    states['flexibility'] = np.asarray(compute_flexibility_ntcl(
        states['unixstart'],
        states['unixend'],
        states['predicted_finish'],
        states['len_profile'],
        )).reshape(-1)
    
    return states


# def device_ntcl(states):
#     ''' 
#     Generic model of Non-TCL loads that are based on a power profile
#     Args:
#         states: device state parameters

#     Returns:
#         states: updated states
#     '''
#     try:
#         ### update proposed status and proposed_demand
#         states['proposed_status'] = (states['(progress']<1)&(states['connected']>0))*1
#         ### update flexibility 
#         states['predicted_finish'] = np.add(np.multiply(np.subtract(np.ones(states['progress'].shape), progress), len_profile), unixtime)
#         flexible_horizon = np.multiply(np.subtract(unixend, predicted_finish), connected)
#         operation_horizon = np.abs(np.subtract(unixend, unixstart))
#         flexibility = np.divide(flexible_horizon, operation_horizon)
#         ### get actual demand
#         actual_demand = np.multiply(np.multiply(actual_status, proposed_demand), (progress<1)*1)
        
        
#         return {
#             'proposed_status': proposed_status, 
#             'flexibility': flexibility, 
#             'proposed_demand': proposed_demand, 
#             'actual_demand': actual_demand}
#             # proposed_status, flexibility, priority, proposed_demand, actual_demand 
#             #(NOTE: actual_demand uses the proposed_demand and actual_status of the previous timestep)
#     except Exception as e:
#         print("Error MODELS.device_ntcl:",e)
#         return {}



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
        return {'ldc_signal': np.power(ldc_signal,0)*90}
    elif algorithm in ['basic_ldc', 'advanced_ldc']:
        # use PID control

        G = K  # 
        T = 1.34e6 / G
        # Kp, Ti, Td = dict_pid[K]
        # Ki = Kp/Ti
        # Kd = Kp*Td
        min_load = 0.001
        

        error = np.subtract(target, latest) #np.divide(np.subtract(target_loading, latest_loading), target_loading)
        derivative, max_d, min_d  = median_filter(error, previous_error, step_size, max_d, min_d)

        # K = K + abs(derivative)
        Kp, Ki, Kd = abb_itae(1, K, 1, 'PID')

        # Kp = 0
        # Ki = 512.0 *1000 / 1.34e6
        # Kd = 0

        p_term = np.multiply(Kp, error)
        i_term = np.clip(np.add(previous_i_term, np.multiply(error, step_size)), a_min=0, a_max=90/Ki) #np.add(signal, np.multiply(Ki, np.multiply(error, step_size)))
        d_term = derivative
        new_signal = np.add(p_term, np.add(np.multiply(Ki, i_term), np.multiply(Kd, d_term))) 
        if latest<=min_load:
            new_signal = np.add(new_signal, (10*(min_load-latest)/min_load))
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


def read_signal(old_signal, new_signal, resolution, delay, step_size, simulation):
    '''
    Emulate ldc_signal recovery including latency.

    Args:
        old_signal: ldc_signal in the previous step
        new_signal: ldc_signal sent from the signal injector
        resolution: number of decimal places for rounding the ldc_signal
        delay: emulated latency delay [s]
        step_size: time step of the simulation [s]
        simulation: status of the program run [0=real, 1=simulation]

    Returns:
        ldc_signal: updated ldc_signal

    References:

    '''
    if simulation==1:
        return new_signal - (delay*((new_signal-old_signal)/step_size))
    else:
        return new_signal

    # try:
    #     delta_signal = np.subtract(new_signal, old_signal)
    #     delay = np.random.normal(delay, 10e-3, n_units)
    #     delayed_signal = np.clip(np.subtract(new_signal, np.multiply(delay, np.divide(delta_signal, step_size))), a_min=0, a_max=100)
    #     # print(new_signal, old_signal, delayed_signal[0])
    #     # idx = np.flatnonzero(ldc_signal!=new_signal)
    #     # w_new = np.clip(np.random.normal(0.99, 0.001, len(idx)), a_min=0.9, a_max=1.0)  # update the signal based on weights to avoid transient noise
    #     # w_old = np.subtract(1, w_new)
    #     # ldc_signal[idx] = np.add(np.multiply(ldc_signal[idx], w_old), np.multiply(w_new, np.round(new_signal, resolution)))
    #     return {'ldc_signal': np.round(delayed_signal, resolution), 'old_signal':new_signal}  
    # except Exception as e:
    #     print(f"Error MODELS.read_signal:{e}")
    #     return {}
    


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
    return np.add(a_min, np.multiply(np.divide((value - x_min), (x_max - x_min)), np.subtract(a_max, a_min)))

def compute_normalize(value, in_min, in_max, out_min, out_max):
    '''
    Normalize value within the range [out_min, out_max].

    Args:
        value: the value to be normalized
        in_min: expected minimum input
        in_max: expected maximum input
        out_min: output minimum
        out_max: output maximum
    
    Returns:
        normalized_value
    '''
    if value>=in_max:
        in_max = value
    if value<=in_min:
        in_min = value

    return out_min + (((value - in_min) / (in_max - in_min))*(out_max-out_min))


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

def compute_min_cycletime(priority, ldc_signal):
    # return abs(ldc_signal-priority)
    # if min_cycletime<10:
    #     return min_cycletime * 10
    return 1

    
    
    
def compute_counter_offset(counter, min_cycletime):
    return counter-min_cycletime

def compute_revised_status(mode, proposed_status, temp_in, temp_target, tolerance, actual_status, flexibility):
    '''
    Revise the proposed status to avoid reaching the thermostat boundaries which causes the control lock-out.

    Args:
        mode: operation mode [0,1]
        proposed_status: proposed status of the device [0, 1]
        temp_in: inside temperature
        temp_target: target setpoint of the inside temperature
        tolerance: tolerance deviation from the target setpoint
        actual_status: current status of the device
        flexibility: flexibility of the device
    
    Returns:
        revised_status: revised form of the proposed status

    References:

    '''
    if (mode==0 and proposed_status==1 and temp_in<=(temp_target-(tolerance*0.9)) and actual_status==1) \
        or (mode==0 and proposed_status==1 and temp_in<=(temp_target-(tolerance*flexibility)) and actual_status==0) \
        or (mode==1 and proposed_status==1 and temp_in>=(temp_target+(tolerance*0.9)) and actual_status==1) \
        or (mode==1 and proposed_status==1 and temp_in>=(temp_target+(tolerance*flexibility)) and actual_status==0):
        return 0  # turn off to avoid reaching the thermostat boundary and cause lockout
    else:
        return proposed_status



def compute_priority_offset(priority, ldc_signal):
    '''
    Calculate the norm distance of the priority from the ldc_signal

    Args:
        priority: device priority value
        ldc_signal: command signal from the LDC injector

    Returns:
        priority_offset: difference between the ldc_signal and the priority value

    '''
    return ldc_signal - priority

def compute_actual_status(with_dr, proposed_status, priority_offset, flexibility, min_cycletime, counter):
    '''
    Decide if proposed status should be approved.

    Args:
        with_dr: boolean if device is LDC enabled [0,1]
        proposed_status: proposed device status for the next time step
        priority_offset: difference between ldc_signal and priority value
        flexibility: flexibility of the device
        min_cycletime: threshold of the counter before the device status can be interrupted
        counter: internal operation counter

    Returns:
        actual_status: actual or approved status

    References:

    '''
    if with_dr==0 or counter<min_cycletime\
        or priority_offset>=0 \
        or flexibility<=0:
        return proposed_status
    else:
        return 0

def compute_changed_status(old_status, new_status, counter, min_cycletime):
    '''
    Implement actual status if counter is beyond minimum_cycletime.

    Args:
        old_status: status in previous time step
        new_status: status in the nex time step
        counter: internal device counter
        min_cycletime: minimum time before  status change is allowed
    
    Returns:
        actual_status: actual or approved status for implementation
    '''
    if counter>=min_cycletime:
        return new_status
    else:
        return old_status
    

def compute_counter(old_status, new_status, counter, step_size):
    '''
    Update counter.

    Args:
        old_status: device status in the previous time step
        new_status: device status for the next time step
        counter: current count value
        step_size: time step increment

    Returns:
        counter: updated value of the counter
    
    References:

    '''
    if old_status!=new_status:
        return 0
    else:
        return counter + step_size


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
        ldc_signal = read_signal(
                        states['old_signal'], 
                        np.ones(states['ldc_signal'].size)*common['ldc_signal'],
                        np.ones(states['ldc_signal'].size)*common['resolution'],
                        np.ones(states['ldc_signal'].size)*common['delay'], 
                        np.ones(states['ldc_signal'].size)*common['step_size'],
                        np.ones(states['ldc_signal'].size)*common['simulation'],
                        )
        
        states['old_signal'] = np.ones(states['ldc_signal'].size)*common['ldc_signal']
        states['ldc_signal'] = ldc_signal
        states['step_size'] = np.ones(states['ldc_signal'].size)*common['step_size']
        states['alpha'] = np.exp(states['step_size']/60)
        old_status = states['actual_status']
        
        ### update priority and actual_status
        if common['algorithm']=='no_ldc':
            states['priority'] = states['priority'] * 0
            states['actual_status'] = states['proposed_status']
            
        elif common['algorithm'] in ['basic_ldc', 'advanced_ldc']:
            ### change priority
            if common['algorithm']=='basic_ldc':
                if (common['ranking']=='dynamic')&(common['unixtime']%60<1): 
                    states['priority'] = np.random.uniform(0,100,len(states['priority'])) # change every 60 seconds
                elif (common['ranking']=='evolve')&(common['unixtime']%60<1):
                    states['priority'] = np.add(np.remainder(np.add(states['priority'], 1), 60), 20)
                else:
                    states['priority'] = states['priority']

            elif common['algorithm']=='advanced_ldc':
                # priority is based on the flexibility and random number from normal distribution of mean 0 and std 1.0
                # flex_priority = normalize(states['flexibility'], a_min=1.0, a_max=99.0, x_max=1.0, x_min=-0.2)
                states['priority'] = normalize(states['flexibility'], a_min=1.0, a_max=90.0, x_min=0.0, x_max=1.0)
                # states['priority'] = compute_normalize(
                #     states['flexibility'], 
                #     np.zeros(states['flexibility'].size), 
                #     np.ones(states['flexibility'].size), 
                #     np.ones(states['flexibility'].size)*1, 
                #     np.ones(states['flexibility'].size)*100,
                #     )

                # uniform_priority = np.random.uniform(1, 100, len(states['priority']))
                # new_priority = np.add(np.multiply(flex_priority, common['flex']), np.multiply((1-common['flex']), uniform_priority))
                # w = np.exp(-np.divide(common['step_size'], 3600))
                # states['priority'] = ((w)*states['priority']) + ((1-w)*new_priority)  # alpha=1-w in exponentially weight moving average
                
                # priority = np.array([np.random.choice([100, x], p=[f, 1-f]) for x, f in zip(priority, normalized_flexibility)])
                # if (common['unixtime']%60 < 1):
                #     priority = swap_priority(states['priority'])
                # else:
                #     priority = states['priority']
                
                # priority = spread(states['flexibility']*100)

            ### get offset of priority from the ldc_signal
            states['priority_offset'] = compute_priority_offset(states['priority'], states['ldc_signal']) 
            
            ### change actual_status
            if states['load_type'][0] in ['clothesdryer', 'clotheswasher', 'dishwasher']:
                partial_status = compute_actual_status(
                    states['with_dr'],
                    states['proposed_status'],
                    states['priority_offset'],
                    states['flexibility'],
                    states['min_cycletime'],
                    states['counter'],
                    )
                
                ### avoid interruption if already in operation
                states['actual_status'] = (((states['actual_status']==1)&(states['finished']==0)) | ((partial_status==1)&(states['actual_status']==0)))*1
                
            elif states['load_type'][0] in ['heatpump', 'fridge', 'freezer']:
                if common['tcl_control'] in ['setpoint', 'mixed']:
                    states['actual_status'] = states['proposed_status']

                    states['temp_target'] = adjust_setpoint(
                        states['with_dr'], 
                        states['heating_setpoint'], 
                        states['cooling_setpoint'], 
                        states['temp_min'], 
                        states['temp_max'], 
                        states['temp_target'], 
                        states['mode'], 
                        states['priority_offset'],
                        )
                    
                else:
                    states['actual_status'] = compute_actual_status(
                        states['with_dr'],
                        states['proposed_status'],
                        states['priority_offset'],
                        states['flexibility'],
                        states['min_cycletime'],
                        states['counter'],
                        )
                                        
            elif states['load_type'][0] in ['heater', 'waterheater']:
                ### define minimum cycle time to avoid jitter in ON/OFF of relay
                states['min_cycletime'] = compute_min_cycletime(states['priority'], states['ldc_signal'])
                ### change proposed_status to avoid thermostat lock out
                states['actual_status'] = compute_actual_status(
                    states['with_dr'],
                    compute_revised_status(
                        states['mode'], 
                        states['proposed_status'], 
                        states['temp_in'], 
                        states['temp_target'], 
                        states['tolerance'],
                        states['actual_status'],
                        states['flexibility'],
                        ),  # revise proposed status to avoid thermostat lockout
                    states['priority_offset'],
                    states['flexibility'],
                    states['min_cycletime'],
                    states['counter'],
                    )
                
                # states['actual_status'] = compute_changed_status(old_status, states['actual_status'], states['counter'], states['min_cycletime'])
            elif states['load_type'][0] in ['solar', 'wind']:
                states['priority'] = np.ones(states['priority'].size) * 90

            else:
                states['actual_status'] = compute_actual_status(
                    states['with_dr'],
                    states['proposed_status'],
                    states['priority_offset'],
                    states['flexibility'],
                    states['min_cycletime'],
                    states['counter'],
                    )
                                            
        elif common['algorithm']=='ripple_control':
            if common['hour']<=7:
                channels = np.subtract(100, states['priority'])  # order is reversed
            else:
                channels = states['priority']
            
            if 'waterheater' in states['load_type']:
                states['priority_offset'] = compute_priority_offset(['priority'], states['ldc_signal'])
                states['actual_status'] = compute_actual_status(
                                    states['with_dr'],
                                    states['proposed_status'],
                                    states['priority_offset'],
                                    np.ones(states['flexibility'].size),
                                    states['min_cycletime'],
                                    states['counter'],
                                    )
            else:
                states['actual_status'] = states['proposed_status']

            # NOTE: priorities are equivalent to channels, i.e., 20-80 : 11A10-11A25
            # signals are sent in steps of 5, i.e, 20, 25, 30, 35
            # each channel is turned ON for 7.5 hours between 9PM to 7AM

        states['counter'] = compute_counter(old_status, states['actual_status'], states['counter'], states['step_size'])

        # if 'storage' in states['load_type']:
        # # #     idx_max = 42 #np.argsort(states['priority_offset']) #np.argmax(states['priority_offset'])
        #     n = 10
        #     print(common['isotime'])
        #     for i in range(n):
        #         print(
        #             states['actual_demand'][i],
        #             # states['charging_power'][i],
        #             states['priority'][i],
        #             # states['soc'][i], 
        #             # states['min_soc'][i],
        #             # states['target_soc'][i], 
        #             # states['flexibility'][i], 
        #             states['ldc_signal'][i],
        #             )
            # print(
            #     # common['ldc_signal'].round(1),
            #     # states['min_cycletime'][idx_max].mean().round(1),
            #     states['ldc_signal'][idx_max].mean().round(1),
            #     states['counter'][idx_max].mean().round(1), 
            #     states['min_cycletime'][idx_max].mean().round(1), 
            #     states['priority_offset'][idx_max].mean().round(1), 
            #     states['actual_status'][idx_max].mean(), 
            #     # states['ldc_signal'][idx_max].mean().round(1), 
            #     # states['priority'][idx_max].mean().round(1), 
            #     states['actual_demand'][idx_max].mean().round(1),
            #     # states['soc'][idx_max].mean(), 
            #     states['flexibility'][idx_max].mean().round(1),
            #     states['temp_in'][idx_max].mean().round(1)
            # )


        return states
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
    
    

def adjust_setpoint(with_dr, heating_setpoint, cooling_setpoint, temp_min, temp_max, temp_target, mode, priority_offset):
    '''
    Adjust the setpoint
    
    Args:
        with_dr: boolean if device is LDC enabled [0,1]
        heating_setpoint: temperature setpoint for heating mode
        cooling_setpoint: temperature setpoint for cooling mode
        temp_min: lowest allowable setpoint
        temp_max: highest allowable setpoint
        temp_target: target temperature from previous time step
        mode: operation mode [0=cooling, 1=heating]
        priority_offset: difference between ldc_signal and priority value
        
    Returns:
        temp_target: adjusted setpoint target

    References:

    '''
    if with_dr==1 and temp_target<=temp_min:
        return temp_min
    elif with_dr==1 and temp_target>=temp_max:
        return temp_max
    elif with_dr==1 and mode==0:
        return cooling_setpoint + (priority_offset*0.01*(temp_max-temp_min))
    elif with_dr==1 and mode==1:
        return heating_setpoint + (priority_offset*0.01*(temp_max-temp_min))
    else:
        return temp_target
    
    # elif with_dr==1 and ((mode==0 and actual_status==1) or (mode==1 and actual_status==0)):
    #     return temp_target - 0.1
    # elif with_dr==1 and ((mode==0 and actual_status==0) or (mode==1 and actual_status==1)):
    #     return temp_target + 0.1
    # else:
    #     return temp_target


    # try:
    #     if algorithm in ['no_ldc', 'ripple_control', 'scheduled_ripple', 'peak_ripple', 'emergency_ripple']:
    #         temp_target = np.add(np.multiply((cooling_setpoint), (mode==0)*1), 
    #             np.multiply((heating_setpoint), (mode==1)*1))

    #         return temp_target
    #     else:
            
    #         ### decrease heating temp
    #         heating_decreased = np.multiply(np.subtract(temp_target, 0.1), np.multiply(((mode==1)*1), ((actual_status==0)*1)))
    #         heating_increased = np.multiply(np.add(temp_target, 0.1), np.multiply(((mode==1)*1), ((actual_status==1)*1)))
    #         ### increase cooling temp
    #         cooling_increased = np.multiply(np.add(temp_target, 0.1), np.multiply(((mode==0)*1), ((actual_status==0)*1)))
    #         cooling_decreased = np.multiply(np.subtract(temp_target, 0.1), np.multiply(((mode==0)*1), ((actual_status==1)*1)))

    #         new_cooling = np.clip(np.add(cooling_decreased, cooling_increased), a_min=(lower_limit+upper_limit)*0.5, a_max=upper_limit)
    #         new_heating =  np.clip(np.add(heating_decreased, heating_increased), a_min=lower_limit, a_max=(lower_limit+upper_limit)*0.5)
    #         temp_target = np.add(np.multiply(new_cooling, (mode==0)*1), np.multiply(new_heating, (mode==1)*1))

    #         return np.round(temp_target, 1)

    # except Exception as e:
    #     print(f"Error MODELS.adjust_setpoint{e}")
    #     return temp_target
        
def update_from_common(states, common):
    '''
    Update global data from common dictionary.

    Args:
        states: state parameters of the device
        common: global parameters
    
    Returns:
        states: updated states
    '''
    states['unixtime'] = np.ones(states['load_type'].size) * common['unixtime']
    states['step_size'] = np.ones(states['load_type'].size) * common['step_size']
    return states



######## model for person #################
# from numba import jit
# @jit(nopython=True)

def compute_is_connected(unixtime, unixstart, unixend):
    '''
    Determine if the device is plugged in or in use.

    Args:
        unixtime: current timestamp
        unixstart: timestamp for earliest usage start
        unixend: timestamp for latest usage finish
    
    Returns:
        connected: boolean status if connected [0,1]
    '''
    if unixtime>=unixstart and unixtime<=unixend:
        return 1
    else:
        return 0

def compute_is_driving(unixtime, unixstart, unixend, trip_time):
    if (unixtime>unixend and unixtime<(unixend+(trip_time*3600))) \
        or (unixtime>unixstart and unixtime<(unixstart+(trip_time*3600))):
        return 1
    else:
        return 0

def compute_adjusted_connected(connected, driving):
    if driving==1:
        return 0
    else:
        return connected

    

def update_schedules(states, common):
    '''
    Update the usage schedules i.e., unixstart and unixend of the devices.

    Args:
        states: state variables of the devices
        common: common global variables, including schedules
    
    Returns:
        states: updated states
    '''
    new_tasks = common['current_task'][states['schedule']].values
    tasks_id = np.floor(new_tasks)
    durations = np.multiply(np.subtract(new_tasks, tasks_id), 1e5)

    idx_updated = np.flatnonzero(tasks_id==states['load_type_id'][0])

    states['unixstart'][idx_updated] = states['unixtime'][idx_updated] + np.abs(states['schedule_skew'][idx_updated])
    states['unixend'][idx_updated] = states['unixstart'][idx_updated] + durations[idx_updated]

    if states['load_type'][0] in ['storage', 'baseload', 'house']:
        states['connected'] = np.ones(states['connected'].size)
    
    else:
        states['connected'] = compute_is_connected(
            states['unixtime'], 
            states['unixstart'], 
            states['unixend'],
            )

    if 'ev' in states['load_type']:
        states['driving'] = compute_is_driving(
            states['unixtime'],
            states['unixstart'], 
            states['unixend'],
            states['trip_time'],
            )
        
        states['connected'] = compute_adjusted_connected(
            states['connected'],
            states['driving'],
            )

        
    if states['load_type'][0] in ['dishwasher', 'clotheswasher', 'clothesdryer']:
        states['progress'][idx_updated] = np.zeros(idx_updated.size)

    return states


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
            'unixend': unixend,
            }
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

dict_ev = {
    'tesla_s85_90kwh': {'capacity': 90.0, 'charging_power': 7.4},  # [kwh] [kW]
    'tesla_s60_60kwh': {'capacity': 60.0, 'charging_power': 7.4},
    'tesla_3_75kwh': {'capacity': 75.0, 'charging_power': 7.4},
    'nissan_leaf_30kwh': {'capacity': 30.0, 'charging_power': 3.3},
    'ford_focus_23kwh': {'capacity': 23.0, 'charging_power': 3.3},
    'ford_focus_33kwh': {'capacity': 33.0, 'charging_power': 3.3},
    'mitsubishi_imiev_16kwh': {'capacity': 16.0, 'charging_power': 3.3},
    'chevy_volt_16kwh': {'capacity': 16.0, 'charging_power': 3.3},
    'tesla_powerwall_13kwh': {'capacity': 13.0, 'charging_power': 7.4},
    }

def initialize_load(load_type, dict_devices, dict_house, idx, distribution, common, realtime=True):
    dict_load_type_id = {
            'heater':3,
            'dishwasher':4,
            'clothesdryer':5,
            'clotheswasher':6,
            'storage':7,
            'ev':8,
            'fridge':9,  # always ON
            'freezer':10,  # always ON
            'heatpump':11,
            'waterheater':12,  # always ON
            'valve':13,
            'humidifier':16,
            'window':18,
            'door':23,
            'human':27,
            'solar':28,
        }

    n_house = dict_devices['house']['n_units']
    n_units = dict_devices[load_type]['n_units']
    n_ldc = dict_devices[load_type]['n_ldc']
    n_b2g = dict_devices[load_type]['n_b2g']
    
    with pd.HDFStore('./specs/device_specs.h5', 'r') as store:
        df = store.select(load_type, where='index>={} and index<{}'.format(idx, idx+n_units))
        if 'with_dr' in df.columns:
            idxs = df.index
            if distribution=='per_device':
                df['with_dr'] = 0
                selection = np.random.choice(idxs, n_ldc, replace=False)
                df.loc[selection, 'with_dr'] = 1
            else:
                df.loc[idxs[0:n_ldc], 'with_dr'] = 1
                df.loc[idxs[n_ldc:], 'with_dr'] = 0
        
        ### assign b2g
        df['b2g'] = 0
        idxs = df.index
        if distribution=='per_device':
            df['b2g'] = 0
            selection = np.random.choice(idxs, n_b2g, replace=False)
            df.loc[selection, 'b2g'] = 1
        else:
            df.loc[idxs[0:n_b2g], 'b2g'] = 1
            df.loc[idxs[n_b2g:], 'b2g'] = 0

        dict_out = df.to_dict(orient='list')
        del df

    for k, v in dict_out.items():
        dict_out[k] = np.array(v)

    
    dict_out['unixstart'] = np.random.normal(common['unixtime'] - (common['hour']*3600), 0.1, n_units)
    dict_out['unixend'] = np.random.normal(common['unixtime'] - (common['hour']*3600) + (3600*24), 0.1, n_units)
    dict_out['alpha'] = np.exp(np.ones(n_units)/60)
    dict_out['actual_demand'] = np.zeros(n_units)
        
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
        # dict_out['temp_in'] = dict_out['temp_target'] - np.abs((np.random.normal(0.0,0.1,n_units)*dict_out['tolerance']))
        dict_out['solar_heat'] = np.zeros(n_units)
        dict_out['power_thermal'] = np.zeros(n_units)
        dict_out['heat_all'] = np.zeros(n_units)
        dict_out['temp_out'] = np.random.normal(common['temp_out'], 0.01, n_units)
        dict_out['humidity'] = np.random.normal(common['humidity'], 0.01, n_units)
        dict_out['humidity_in'] = dict_out['humidity'] - np.random.normal(0.1, 0.001, n_units)
        dict_out['windspeed'] = np.random.normal(common['windspeed'], 0.01, n_units)
        

    if load_type in ['fridge', 'freezer']:
        dict_out['mass_flow'] = np.zeros(n_units)
        dict_out['mode'] = np.zeros(n_units)
        dict_out['temp_target'] = dict_out['cooling_setpoint']
        dict_out['solar_heat'] = np.zeros(n_units)
        dict_out['power_thermal'] = np.zeros(n_units)
        dict_out['heat_all'] = np.zeros(n_units)
        # dict_out['temp_in'] = dict_out['temp_target'] + (np.random.normal(0.0,0.1,n_units)*dict_out['tolerance'])
        # air density is 1.225kg/m^3 at 15degC sea level
        # air density is 1.2041 kg/m^3 at 20 degC sea level
        # water density is 999.1 kg/m^3 at 15degC sea level
    if load_type in ['heater', 'waterheater']:
        dict_out['mode'] = np.ones(n_units)
        dict_out['temp_target'] = dict_out['heating_setpoint']
        dict_out['temp_max'] = dict_out['temp_target'] + (dict_out['tolerance']*0.9)
        # dict_out['temp_in'] = dict_out['temp_target'] - np.abs((np.random.normal(0.0,0.3,n_units)*dict_out['tolerance']))
        dict_out['min_cycletime'] = np.random.uniform(1, 1.1, n_units)
        dict_out['solar_heat'] = np.zeros(n_units)
        dict_out['power_thermal'] = np.zeros(n_units)
        dict_out['heat_all'] = np.zeros(n_units)
        # dict_out['counter'] = np.random.uniform(2, 3, n_units)
        # dict_out['temp_in'] = np.random.normal(np.mean(dict_out['temp_in']), np.std(dict_out['temp_in']), n_units)

    if load_type in ['storage']:
        dict_out['soc'] = np.clip(np.random.normal(0.5, 0.3, n_units), a_min=0.2, a_max=0.8)
        dict_out['progress'] = np.divide(dict_out['soc'], dict_out['target_soc'])
        dict_out['mode'] = np.zeros(n_units)
        dict_out['min_soc'] = np.random.uniform(0.2, 0.3, n_units)
        dict_out['target_soc'] = np.random.uniform(0.9, 0.95, n_units)
        dict_out['connected'] = np.ones(n_units)
        dict_out['charging_power'] = np.ones(n_units) * 7400
        dict_out['capacity'] = np.ones(n_units) * 13.0 * 1000 * 3600
        dict_out['b2g'] = np.ones(n_units)
        # dict_out['capacity'] = np.array([dict_ev[x]['capacity'] for x in dict_out['profile']]) * 1000 * 3600
        # dict_out['charging_power'] = np.array([dict_ev[x]['charging_power'] for x in dict_out['profile']]) 
        # print(dict_out['capacity']/1e3/3.6e3)
        # print(dict_out['charging_power']/1e3)
        # dict_out['schedule_skew'] = np.random.uniform(-900, 900, n_units)
    
    if load_type=='ev':
        dict_out['soc'] = np.random.uniform(0.7, 0.8, n_units)
        dict_out['progress'] = np.divide(dict_out['soc'], dict_out['target_soc'])
        dict_out['min_soc'] = np.random.uniform(0.3, 0.4, n_units)
        dict_out['target_soc'] = np.random.uniform(0.9, 0.95, n_units)
        dict_out['connected'] = np.ones(n_units)
        dict_out['capacity'] = np.array([dict_ev[x]['capacity'] for x in dict_out['profile']]) * 1000 * 3600
        dict_out['charging_power'] = np.array([dict_ev[x]['charging_power'] for x in dict_out['profile']]) * 1000 
        
        dict_out['daily_energy'] = np.multiply(np.clip(np.random.normal(0.6, 0.05, n_units), a_min=0.55, a_max=0.65), dict_out['capacity']) #[Ws]
        dict_out['km_per_kwh'] = np.clip(np.random.normal(6.0, 0.1, n_units), a_min=4.225, a_max=6.76) #[km/kWh] 1kWh per 6.5 km avg 
        dict_out['trip_distance'] = np.multiply(dict_out['km_per_kwh'], dict_out['daily_energy']/1e3/3.6e3) # [km] avg daily trip
        dict_out['avg_speed'] = np.clip(np.random.normal(85, 10, n_units), a_min=50, a_max=100)  # [km/h]
        dict_out['trip_time'] = np.divide(dict_out['trip_distance']*0.5, dict_out['avg_speed']) #[hours] avg daily trip
        dict_out['driving_power'] = ((dict_out['trip_distance']*0.5/dict_out['trip_time']) / dict_out['km_per_kwh']) * 1000 * -1 #[W]
        dict_out['unixstart'] = np.random.normal(common['unixtime'] - (common['hour']*3600) - (6*3600), 1800, n_units)
        dict_out['unixend'] = np.random.normal(common['unixtime'] - (common['hour']*3600) + (6*3600), 1800, n_units)
        
        # print(dict_out['daily_energy']/1e3/3.6e3)
        # print(dict_out['km_per_kwh'])
        # print(dict_out['trip_distance'])
        # print(dict_out['avg_speed'])
        # print(dict_out['trip_time'])
        # print(dict_out['driving_power'])
        
    if load_type in ['dishwasher', 'clothesdryer', 'clotheswasher']:
        dict_out['finished'] = np.ones(n_units)
        dict_out['unfinished'] = np.zeros(n_units) 
        dict_out['unixstart'] = np.random.normal(common['unixtime'] - (common['hour']*3600)- (3600*24) + (3600*18), 900, n_units)
        dict_out['unixend'] = np.random.normal(common['unixtime'] - (common['hour']*3600) - (3600*24) + (3600*21) , 900, n_units)
      
    if load_type in ['solar', 'wind']:
        dict_out['mode'] = np.ones(n_units)  # generation modes are 1
        dict_out['priority'] = np.ones(n_units) * 90.0
        dict_out['connected'] = np.ones(n_units)
        dict_out['flexibility'] = np.ones(n_units) * 0.9
        dict_out['capacity'] = np.clip(np.round(np.random.normal(270*18, 270, n_units), -1), a_min=270*10, a_max=270*56)

        #   'mean_priority': states['priority'].mean().round(3),
        #     'min_priority': states['priority'].min().round(3),
        #     'max_priority': states['priority'].max().round(3),
        #     'std_priority': states['priority'].std().round(3),
        #     'sum_actual_status': states['actual_status'].sum(),
        #     'sum_connected': states['connected'].sum(),
        #     'sum_actual_demand': states['actual_demand'].sum().round(1
    
    dict_out['house'] = dict_house['name'][np.arange(n_units)%n_house]
    dict_out['schedule'] = dict_house['schedule'][np.arange(n_units)%n_house] 
    dict_out['load_type_id'] = np.ones(n_units) * dict_load_type_id[load_type]
    dict_out['old_signal'] = np.zeros(n_units)
    dict_out['ldc_signal'] = np.zeros(n_units)
    dict_out['priority_offset'] = np.subtract(dict_out['ldc_signal'], dict_out['priority'])
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

    # if not has_numba:
    #     for k, v in dict_out.items():
    #         dict_out[k] = np.asarray(v)[0]
            
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
                        



if has_numba:
    # Vectorise all 'core' functions. 
    # Utility function are excluded as they are just wrappers.
    numba_funcs = []
    for func in list(globals().items()):
        if isfunction(func[1]) and func[0].startswith(('compute', 'read_signal', 'adjust_setpoint')):
            globals()[func[0]] = vectorize(func[1])
            numba_funcs.append(func)
        # elif isfunction(func[1]) and func[0].startswith(('read_signal')):
        #     globals()[func[0]] = guvectorize(func[1])
        #     numba_funcs.append(func)






