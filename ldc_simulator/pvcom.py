#!/usr/bin/python3           
# This is client.py file

import socket
import struct
import time
import numpy as np
import pandas as pd
import datetime
import os, sys, glob
import multiprocessing


class SolarMonitor(multiprocessing.Process):
    def __init__(self, house_id='H4'):
        multiprocessing.Process.__init__(self)
        self.daemon = True
    
        # Create a TCP/IP socket
        self.pv_address = {
            'H4': '192.168.1.72',
            'H5': '192.168.1.73',
            'H1': '192.168.1.71',
        }
        
        self.house_id = house_id 
        self.TCP_IP = self.pv_address[self.house_id]
        self.TCP_PORT = 502
        self.BUFFER_SIZE = 64
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.TCP_IP, self.TCP_PORT))



        self.dict_params = {
            817: {'name': 'house_p_w', 'factor': 1.0, 'type':'uint16', 'unit_id': 100},
            820: {'name': 'grid_p_w', 'factor': 1.0, 'type':'int16', 'unit_id': 100},
            840: {'name': 'storage_v_v', 'factor': 10.0, 'type':'uint16', 'unit_id': 100},
            841: {'name': 'storage_i_a', 'factor': 10.0, 'type':'int16', 'unit_id': 100},
            842: {'name': 'storage_p_w', 'factor': 1.0, 'type':'int16', 'unit_id': 100},
            843: {'name': 'storage_soc', 'factor': 1.0, 'type':'uint16', 'unit_id': 100},
            844: {'name': 'storage_state', 'factor': 1.0, 'type':'uint16', 'unit_id': 100},
            846: {'name': 'draintime_s', 'factor': 0.01, 'type': 'uint16', 'unit_id': 100},
            850: {'name': 'solar_p_w', 'factor': 1.0, 'type':'uint16', 'unit_id': 100},
            851: {'name': 'solar_i_a', 'factor': 10.0, 'type':'int16', 'unit_id': 100},
            ### settings
            2703: {'name': 'grid_target_p_w', 'factor': 0.01, 'type':'int16', 'unit_id': 100},
            2704: {'name': 'inverter_max_p_w', 'factor': 0.1, 'type':'uint16', 'unit_id': 100},
            2706: {'name': 'feedin_max_p_w', 'factor': 0.01, 'type':'int16', 'unit_id': 100},
            2901: {'name': 'storage_min_soc', 'factor': 10, 'type':'uint16', 'unit_id': 100},
        }

    def read_modbus(self, unit_id=100, function_code=3, coil_id=1, start_register=817, n_registers=9):
        '''
        Read data from registers using modbus.
        '''
        ### prepare request
        regbytes = struct.pack('<H', start_register)
        nregisters_bytes = struct.pack('<H', n_registers)
        req = struct.pack('12B', 
                    0x00, # transaction identifier
                    0x07, # transaction identifier
                    0x00, # protocol identifier
                    0x00, # protocol identifier
                    0x00, # length (upper byte, if message is > 256 bytes)
                    0x06,  # legth (lower byte, i.e., number of bytes that will follow)
                    int(unit_id),  # uniID 
                    int(function_code),  # functionCode
                    int(regbytes[1]),  # register address (upper byte), e.g., 0A in 0xA28
                    int(regbytes[0]),  # register address (lower byte), e.g., 28 in 0xA28
                    int(nregisters_bytes[1]),  # number of registers (upper byte)
                    int(nregisters_bytes[0]), # number of registers  (lower byte)
                    )

        ### send request
        self.sock.send(req) 
        # print(req)

        ### receive response  
        response = self.sock.recv(self.BUFFER_SIZE)
        # print(response)
        response_nbytes = int.from_bytes(response[8:9], 'big')
        dict_response = {}
        for i in range(1, response_nbytes, 2):
            value = int.from_bytes(response[8+i: 8+i+2], 'big')
            dict_response.update({start_register+i-1 : value})
        
        return dict_response


    def write_modbus(self, unit_id=100, function_code=6, register=2901, data=80, scale_factor=10):
        '''
        Write value to registers using modbus.
        '''
        ### prepare request
        reg_bytes = struct.pack('<H', register)
        data_bytes = struct.pack('<H', int(data*scale_factor))

        req = struct.pack('12B', 
                    0x00, # transaction identifier
                    0x02, # transaction identifier
                    0x00, # protocol identifier
                    0x00, # protocol identifier
                    0x00, # length (upper byte, if message is > 256 bytes)
                    0x06,  # legth (lower byte, i.e., number of bytes that will follow)
                    int(unit_id),  # uniID 
                    int(function_code),  # functionCode
                    int(reg_bytes[1]),  # register address (upper byte), e.g., 0A in 0xA28
                    int(reg_bytes[0]),  # register address (lower byte), e.g., 28 in 0xA28
                    int(data_bytes[1]),  # data upper byte
                    int(data_bytes[0])  # data lower byte
                    )
        
        ### send request
        self.sock.send(req)  
        ### receive response  
        response = self.sock.recv(self.BUFFER_SIZE)

        return {int.from_bytes(response[-4: -2], 'big'): int.from_bytes(response[-2:], 'big') }



    def save_data(self, dict_save, folder, filename, case, sample='1S', summary=False, report=False):
        try:
            path = f'/home/pi/studies/{folder}/{case}'
            os.makedirs(path, exist_ok=True)  # create folder if none existent
            dict_save = save_pickle(dict_save, path=f'{path}/{filename.split(".")[0]}.pkl.xz', report=report)
            return dict_save  # empty dict_save if saving is successful
        except Exception as e:
            print(f"Error save_data:{e}")
            return dict_save
            

    def save_pickle(self, dict_data, path='history/data.pkl.xz', report=False):
        'Save data as pickle file.'
        try:
            df_all = pd.DataFrame.from_dict(dict_data, orient='index')
            try:
                on_disk = pd.read_pickle(path, compression='infer')
                df_all = pd.concat([on_disk, df_all], axis=0, sort=False)
                df_all['unixtime'] = df_all['unixtime'].astype(int)
                df_all = df_all.groupby('unixtime').mean()
                df_all.reset_index(drop=False, inplace=True)
                df_all.to_pickle(path, compression='infer')
            except Exception as e:
                df_all.to_pickle(path, compression='infer')
            
            if report: print(df_all.tail(10))
            return {}
        except Exception as e:
            print("Error save_pickle:", e)
            return dict_data 

    def get_meter_data(self, 
        dict_params={
            817: {'name': 'house_p_w', 'factor': 1.0, 'type':'uint16', 'unit_id': 100},
            820: {'name': 'grid_p_w', 'factor': 1.0, 'type':'int16', 'unit_id': 100},
            840: {'name': 'storage_v_v', 'factor': 10.0, 'type':'uint16', 'unit_id': 100},
            841: {'name': 'storage_i_a', 'factor': 10.0, 'type':'int16', 'unit_id': 100},
            842: {'name': 'storage_p_w', 'factor': 1.0, 'type':'int16', 'unit_id': 100},
            843: {'name': 'storage_soc', 'factor': 1.0, 'type':'uint16', 'unit_id': 100},
            844: {'name': 'storage_state', 'factor': 1.0, 'type':'uint16', 'unit_id': 100},
            846: {'name': 'draintime_s', 'factor': 0.01, 'type': 'uint16', 'unit_id': 100},
            850: {'name': 'solar_p_w', 'factor': 1.0, 'type':'uint16', 'unit_id': 100},
            851: {'name': 'solar_i_a', 'factor': 10.0, 'type':'int16', 'unit_id': 100},
            ### settings
            2703: {'name': 'grid_target_p_w', 'factor': 0.01, 'type':'int16', 'unit_id': 100},
            2704: {'name': 'inverter_max_p_w', 'factor': 0.1, 'type':'uint16', 'unit_id': 100},
            2706: {'name': 'feedin_max_p_w', 'factor': 0.01, 'type':'int16', 'unit_id': 100},
            2901: {'name': 'storage_min_soc', 'factor': 10, 'type':'uint16', 'unit_id': 100},
        },
        report=False):

        dict_tosave = {}
        for r, s in dict_params.items():
            dict_response = self.read_modbus(unit_id=100, 
                function_code=3, coil_id=1, start_register=r, n_registers=1)

            for k, v in dict_response.items():
                dict_tosave.update({dict_params[k]['name']: eval(f'np.{dict_params[k]["type"]}({v})')/dict_params[k]['factor']})
        
        return dict_tosave

    def change_settings(self, dict_params):
        dict_response = {}
        for k, v in dict_params.items():
            dict_response.update(write_modbus(unit_id=v['unit_id'], function_code=6, 
                register=v['reg_address'], data=v['data'], scale_factor=v['factor']))
        
        return dict_response
        

    def autorun(self, save=False, report=False, diagnostics=False):
        dict_history = {}
        last_day = datetime.datetime.now().strftime('%Y_%m_%d')
        while True:
            try:
                now = datetime.datetime.now()
                today = now.strftime('%Y_%m_%d')

                dict_tosave = self.get_meter_data(dict_params=self.dict_params)

                if report:
                    print(dict_tosave)

                if save:
                    ### prepare history for saving
                    dict_tosave.update({'unixtime': time.time()})
                    dict_history.update({time.time(): dict_tosave})

                    if now.second%60<1:
                        if last_day!=today:
                            dict_history = self.save_data(dict_save=dict_history, folder='ardmore',
                                filename=f'H4_PV_{last_day}.pkl.xz', 
                                case='data', report=True) 
                        else:
                            dict_history = self.save_data(dict_save=dict_history, folder='ardmore',
                                filename=f'H4_PV_{today}.pkl.xz', 
                                case='data', report=True)
                            
                last_day = today
                time.sleep(0.1)
            except Exception as e:
                if diagnostics: 
                    print(f'Error modbus_com:{e}')
                self.sock.close()
                break
            except KeyboardInterrupt:
                self.sock.close()
                break

            

if __name__=='__main__':
    pv = SolarMonitor(house_id='H4')
    pv.autorun(report=True, diagnostics=True)