
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

    def _get(self, path, ** params):
        params['apiKey'] = self._api_key
        response = requests.get(_SERVER + path, params = params)
        response.raise_for_status()
        return response.json()

    def _patch(self, path, data, ** params):
        params['apiKey'] = self._api_key
        response = requests.patch(_SERVER + path, params = params, data = data)
        response.raise_for_status()
        return response.json()

    def devices(self):
        result = self._get("/users/me/pods", fields="id,room")
        return {x['room']['name']: x['id'] for x in result['result']}

    def pod_measurement(self, podUid):
        result = self._get("/pods/%s/measurements" % podUid)
        return result['result']

    def pod_history(self, podUid):
        result = self._get("/pods/%s/historicalMeasurements" % podUid)
        return result['result']

    def pod_ac_state(self, podUid):
        result = self._get("/pods/%s/acStates" % podUid, limit = 1, fields="status,reason,acState")
        return result['result'][0]['acState']

    def pod_change_ac_state(self, podUid, currentAcState, propertyToChange, newValue):
        self._patch("/pods/%s/acStates/%s" % (podUid, propertyToChange),
                json.dumps({'currentAcState': currentAcState, 'newValue': newValue}))




def get_history(report=False, csv=False):
    # get history records of sensibo device
    # if not os.path.exists('./sensibo/'): os.makedirs('sensibo')

    client = SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
    devices = client.devices()

    for device in devices:
        ### get history
        uid = devices[device]
        history = client.pod_history(uid)
        ### convert of pandas dataframe
        df_temperature = pd.DataFrame.from_dict(history['temperature'], orient='columns')
        df_humidity = pd.DataFrame.from_dict(history['humidity'], orient='columns')

        df_temperature.columns = ['date_time', 'temperature']
        df_humidity.columns = ['date_time', 'humidity']

        df_temperature.index = pd.to_datetime(df_temperature['date_time'], utc=True)
        df_humidity.index = pd.to_datetime(df_humidity['date_time'], utc=True)

        df_temperature.index = df_temperature.index.tz_convert('Pacific/Auckland')
        df_humidity.index = df_humidity.index.tz_convert('Pacific/Auckland')

        df_history = pd.concat([df_temperature['temperature'], df_humidity['humidity']], axis=1)

        df_history['device'] = device
        
        if report: print(df_history)

        if csv:
            dt = df_history.index[0]
            filename = '{}_temperature_humidity_{}_{}_{}.csv'.format(device, dt.year, dt.month, dt.day)
            df_history.to_csv(filename, index=True)
            print(f'{filename} saved...')


if __name__ == "__main__":
    # client = SensiboClientAPI('srBysNj0K9o6De9acaSz8wrvS2Qpju')
    # devices = client.devices() 
    # uid = devices['ldc_heatpump_h2'] 
    ### query status of uid
    # ac_state = client.pod_ac_state(uid)
    ### query history
    # history = client.pod_history(uid) #['temperature'][-1]['value']
    # print("History:", history)

    # ### set to cooling
    # print('Set to cooling mode...')
    # client.pod_change_ac_state(uid, ac_state, "mode", 'cool') 
    # ac_state = client.pod_ac_state(uid)  # get states
    # print("Confirmed states:", ac_state)
    
    # ### set to heating
    # print('Set to heating mode...')
    # client.pod_change_ac_state(uid, ac_state, "mode", 'heat') 
    # ac_state = client.pod_ac_state(uid)  # get states
    # print("Confirmed states:", ac_state)
    

    # ### change setpoint
    # print('Change target temperature...')
    # client.pod_change_ac_state(uid, ac_state, "targetTemperature", int(22.0)) 
    # ac_state = client.pod_ac_state(uid)  # get states
    # print("Confirmed states:", ac_state)

    # ### change status to ON
    # print('Change status to ON...')
    # client.pod_change_ac_state(uid, ac_state, "on", True) 
    # ac_state = client.pod_ac_state(uid)  # get states
    # print("Confirmed states:", ac_state)

    
    get_history(report=False, csv=True)

###########
