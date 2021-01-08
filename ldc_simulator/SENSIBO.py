
import requests
import json
import pandas as pd
import numpy as np
import datetime



_SERVER = 'https://home.sensibo.com/api/v2'

class SensiboClientAPI(object):
    def __init__(self, api_key='srBysNj0K9o6De9acaSz8wrvS2Qpju'):
        self._api_key = api_key
        self.properties = {'on':True,
                'fanLevel':'auto', 
                'temperatureUnit':'C',
                'targetTemperature':22, 
                'mode':'cool',
                'swing':'horizontal',
                }

    def _get(self, path, **params):
        params['apiKey'] = self._api_key
        response = requests.get(_SERVER + path, params = params)
        response.raise_for_status()
        return response.json()

    def _patch(self, path, data, **params):
        params['apiKey'] = self._api_key
        response = requests.patch(_SERVER + path, params = params, data = data)
        response.raise_for_status()
        return response.json()

    def devices(self):
        result = self._get(path="/users/me/pods", fields='id,room')
        return {x['room']['name']: x['id'] for x in result['result']}

    def pod_measurement(self, podUid):
        result = self._get(f"/pods/{podUid}?fields=measurements&apiKey={self._api_key}")
        return result['result']

    def pod_history(self, podUid):
        result = self._get(f"/pods/{podUid}/historicalMeasurements")
        return result['result']

    # def pod_ac_state(self, podUid):
    #     result = self._get("/pods/%s/acStates" % podUid, limit = 1, fields="status,reason,acState")
    #     return result['result'][0]['acState']
    
    def pod_ac_state(self, podUid):
        response = requests.get(f'https://home.sensibo.com/api/v2/pods/{podUid}?fields=acState&apiKey={self._api_key}')
        response.raise_for_status()
        return response.json()['result']['acState']

    def pod_change_ac_state(self, podUid, currentAcState, propertyToChange, newValue):
        self._patch("/pods/%s/acStates/%s" % (podUid, propertyToChange),
                json.dumps({'currentAcState': currentAcState, 'newValue': newValue}))

    def pod_all_info(self, podUid):
        # response = requests.get(f'https://home.sensibo.com/api/v2/users/me/pods?fields=*&apiKey={self._api_key}')
        response = requests.get(f'https://home.sensibo.com/api/v2/pods/{podUid}?fields=acState&apiKey={self._api_key}')
        response.raise_for_status()
        return response.json()


def get_measurements(report=False, csv=False):
    client = SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
    devices = client.devices()
    print(devices)
    for d in devices:
        print(client.pod_measurement(devices[d]))

def get_history(report=False, csv=False):
    # get history records of sensibo device
    # if not os.path.exists('./sensibo/'): os.makedirs('sensibo')
    client = SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
    devices = client.devices()
    print(devices)
    for device in devices:
        ### get history
        uid = devices[device]
        history = client.pod_history(uid)
        print(history)
    #     ### convert of pandas dataframe
    #     df_temperature = pd.DataFrame.from_dict(history['temperature'], orient='columns')
    #     df_humidity = pd.DataFrame.from_dict(history['humidity'], orient='columns')

    #     df_temperature.columns = ['date_time', 'temperature']
    #     df_humidity.columns = ['date_time', 'humidity']

    #     df_temperature.index = pd.to_datetime(df_temperature['date_time'], utc=True)
    #     df_humidity.index = pd.to_datetime(df_humidity['date_time'], utc=True)

    #     df_temperature.index = df_temperature.index.tz_convert('Pacific/Auckland')
    #     df_humidity.index = df_humidity.index.tz_convert('Pacific/Auckland')

    #     df_history = pd.concat([df_temperature['temperature'], df_humidity['humidity']], axis=1)

    #     df_history['device'] = device
        
    # if report: print(df_history)

    # if csv:
    #     dt = df_history.index[0]
    #     filename = '{}_temperature_humidity_{}_{}_{}.csv'.format(device, dt.year, dt.month, dt.day)
    #     df_history.to_csv(filename, index=True)
    #     print(f'{filename} saved...')


if __name__ == "__main__":
    client = SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
    devices = client.devices() 
    uid = devices['ldc_heatpump_h4'] 
    ## query status of uid
    ac_state = client.pod_ac_state(uid)
    ### get measurements
    print(client.pod_measurement(uid))

    ## query history
    history = client.pod_history(uid) #['temperature'][-1]['value']
    print("History:", history)

    ### set to cooling
    print('Set to cooling mode...')
    client.pod_change_ac_state(uid, ac_state, "mode", 'cool') 
    ac_state = client.pod_ac_state(uid)  # get states
    print("Confirmed states:", ac_state)
    
    ### set to heating
    print('Set to heating mode...')
    client.pod_change_ac_state(uid, ac_state, "mode", 'heat') 
    ac_state = client.pod_ac_state(uid)  # get states
    print("Confirmed states:", ac_state)
    

    ### change setpoint
    print('Change target temperature...')
    client.pod_change_ac_state(uid, ac_state, "targetTemperature", int(22.0)) 
    ac_state = client.pod_ac_state(uid)  # get states
    print("Confirmed states:", ac_state)

    ### change status to ON
    print('Change status to ON...')
    client.pod_change_ac_state(uid, ac_state, "on", True) 
    ac_state = client.pod_ac_state(uid)  # get states
    print("Confirmed states:", ac_state)




    ###
    # HOUSE_NUM = 5
    # API_KEY = 'srBysNj0K9o6De9acaSz8wrvS2Qpju' 
    # sensibo_api = SENSIBO.SensiboClientAPI(API_KEY)
    # sensibo_devices = sensibo_api.devices()
    # uid = sensibo_devices[f'ldc_heatpump_h{int(HOUSE_NUM)}']
    # print(uid)
    
    # # sensibo_measurement = sensibo_api.pod_measurement(uid)
    # # print(sensibo_measurement)
    # # sensibo_api.pod_all_info(uid)
    # sensibo_state = sensibo_api.pod_ac_state(uid)
    # print(sensibo_state)
    

###########
'''
The following shows all available information from sensibo
{
    'configGroup': 'stable', 
    'macAddress': '84:0d:8e:87:ba:70', 
    'isGeofenceOnExitEnabled': False, 
    'currentlyAvailableFirmwareVersion': 'SKY30044', 
    'cleanFiltersNotificationEnabled': False, 
    'connectionStatus': {
        'isAlive': True, 
        'lastSeen': {
            'secondsAgo': 3, 
            'time': '2020-10-19T03:02:50.030936Z'
            }
        }, 
    'filtersCleaning': None, 
    'acState': {
        'on': True, 
        'fanLevel': 'auto', 
        'temperatureUnit': 'C', 
        'targetTemperature': 21, 
        'mode': 'heat', 
        'swing': 'stopped'
        }, 
    'isOwner': True, 
    'mainMeasurementsSensor': None, 
    'motionSensors': [], 
    'id': 'xRnLh26Z', 
    'qrId': 'HUEUYVMSXG', 
    'roomIsOccupied': None, 
    'firmwareType': 'esp8266ex', 
    'motionConfig': None, 
    'measurements': {
        'batteryVoltage': None, 
        'temperature': 22.1, 
        'humidity': 61.2, 
        'time': {
            'secondsAgo': 3, 
            'time': '2020-10-19T03:02:50.030936Z'
            }, 
        'rssi': -46, 
        'piezo': [None, None]
        }, 
    'isClimateReactGeofenceOnEnterEnabledForThisUser': False, 
    'smartMode': None, 
    'shouldShowFilterCleaningNotification': False, 
    'firmwareVersion': 'SKY30044', 
    'sensorsCalibration': {
        'temperature': 0.0, 
        'humidity': 0.0
        }, 
    'location': {
        'latLon': [-37.035321, 174.9852232], 
        'updateTime': None, 
        'features': ['softShowPlus'], 
        'country': 'New Zealand', 
        'occupancy': 'n/a', 
        'createTime': {
            'secondsAgo': 34808947, 
            'time': '2019-09-12T05:53:47Z'
            }, 
        'address': ['129 Mullins Rd', 'Ardmore', 'Papakura 2582'], 
        'geofenceTriggerRadius': 200, 
        'subscription': None, 
        'id': 'FJoiv8WFTR', 
        'name': 'House 1: Livability studies.'
        }, 
    'tags': [], 
    'productModel': 'skyv2', 
    'isMotionGeofenceOnEnterEnabled': False, 
    'schedules': [], 
    'isClimateReactGeofenceOnExitEnabled': False, 
    'remoteCapabilities': {
        'modes': {
            'dry': {
                'swing': ['stopped', 'rangeFull', 'horizontal', 'both'], 
                'temperatures': {
                    'C': {
                        'isNative': True, 
                        'values': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
                        }, 
                    'F': {
                        'isNative': False, 
                        'values': [61, 63, 64, 66, 68, 70, 72, 73, 75, 77, 79, 81, 82, 84, 86]
                        }
                    }, 
                'fanLevels': ['quiet', 'low', 'medium', 'high', 'auto', 'strong']
                }, 
            'auto': {
                'swing': ['stopped', 'rangeFull', 'horizontal', 'both'], 
                'temperatures': {
                    'C': {
                        'isNative': True, 
                        'values': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
                        }, 
                    'F': {
                        'isNative': False, 
                        'values': [61, 63, 64, 66, 68, 70, 72, 73, 75, 77, 79, 81, 82, 84, 86]
                        }
                    }, 
                'fanLevels': ['quiet', 'low', 'medium', 'high', 'auto', 'strong']
                }, 
            'heat': {
                'swing': ['stopped', 'rangeFull', 'horizontal', 'both'], 
                'temperatures': {
                    'C': {
                        'isNative': True, 
                        'values': [10, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
                        }, 
                    'F': {
                        'isNative': False, 
                        'values': [50, 61, 63, 64, 66, 68, 70, 72, 73, 75, 77, 79, 81, 82, 84, 86]
                        }
                    }, 
                'fanLevels': ['quiet', 'low', 'medium', 'high', 'auto', 'strong']
                }, 
            'fan': {
                'swing': ['stopped', 'rangeFull', 'horizontal', 'both'], 
                'temperatures': {}, 
                'fanLevels': ['quiet', 'low', 'medium', 'high', 'auto', 'strong']
                }, 
            'cool': {
                'swing': ['stopped', 'rangeFull', 'horizontal', 'both'], 
                'temperatures': {
                    'C': {
                        'isNative': True, 
                        'values': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
                        }, 
                    'F': {
                        'isNative': False, 
                        'values': [61, 63, 64, 66, 68, 70, 72, 73, 75, 77, 79, 81, 82, 84, 86]
                        }
                    }, 
                'fanLevels': ['quiet', 'low', 'medium', 'high', 'auto', 'strong']
                }
            }
        }, 
    'serial': '091901919', 
    'accessPoint': {
        'password': None, 
        'ssid': 'SENSIBO-I-60633'
        }, 
    'remote': {
        'window': False, 
        'toggle': False
        }, 
    'room': {
        'name': 'ldc_heatpump_h1', 
        'icon': 'Office'
        }, 
    'isGeofenceOnEnterEnabledForThisUser': False, 
    'temperatureUnit': 'C', 
    'timer': None, 
    'remoteFlavor': 'Singing Wombat', 
    'isMotionGeofenceOnExitEnabled': False, 
    'remoteAlternatives': ['_fujitsu1_selector1', '_fujitsu1_different_swing', '_fujitsu1c', '_fujitsu1b', '_fujitsu1b_for_pod', '_fujitsu1_power_toggle', '_fujitsu1_airclean']
    }

'''