# ./METER.py
# Original: 26-11-2018: James Ashworth
# Edited: 25-02-2018: Ryan Tulabing
# University of Auckland

# ./METER.py
# James Ashworth, Ryan Tulabing
# University of Auckland
# 26/11/2018


import socket
import struct
import sys
import time, datetime
import json
import ast
import pandas as pd
import serial
import multiprocessing
import threading, queue
import array
import numpy as np
import serial.tools.list_ports
import os
import glob
# local packages
# import tcp_client
import MULTICAST




# Set up a class which holds parameters of each energy meter.
class EnergyMeter():
    ''' Generic Class for an energy meter'''    
    def __init__(self, house, IDs=[1,2,3], autorun=False):
        dict_serialports = self.get_ports()
        port_meters = dict_serialports['PID=0403']        

        self.powermeter_ids = IDs
        self.port = port_meters
        self.name = 'METER_{}'.format(house)
        self.load_type = 'meter'
        self.house = house

        # multicasting ip and port
        self.mcast_ip = '224.0.2.0'
        self.mcast_port = 17000
        # tcp_client.tcpClient.__init__(self, '192.168.1.81', 10081)
        self.dict_history = {}
        self.df_data = pd.DataFrame([])
        # initialize dictionary for data
        self.dict_data = {'unixtime': int(time.time())}
        self.dict_states_self = {str(self.name):self.dict_data}
        self.minute = 0
        self.dict_registers = {
            'voltage': [40306, 1], 
            'frequency':[40305, 1], 
            'current':[40314, 2], 
            'powerfactor':[40345, 1],
            'power_active':[40321, 2], 
            'power_reactive':[40329, 2], 
            'power_apparent':[40337, 2], 
            'energy_active':[((440961 - 400001) + 40001), 2], 
            'energy_reactive':[((440991 - 400001) + 40001), 2],
            }

        self.dfactor = {
            'frequency': 0.01,
            'voltage': 0.01,
            'energy_active': 0.01,
            'energy_reactive': 0.01,
            'current': 0.001,
            'powerfactor': 0.001,
            'power_active': 0.001,
            'power_reactive': 0.001,
            'power_apparent': 0.001,
        }
   
        ### modbus lookup table
        self.crclookup = [0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241, 0xC601, 0x06C0, 0x0780, 0xC741, 
                    0x0500, 0xC5C1, 0xC481, 0x0440, 0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40, 
                    0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841, 0xD801, 0x18C0, 0x1980, 0xD941,
                    0x1B00, 0xDBC1, 0xDA81, 0x1A40, 0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
                    0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641, 0xD201, 0x12C0, 0x1380, 0xD341,
                    0x1100, 0xD1C1, 0xD081, 0x1040, 0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
                    0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441, 0x3C00, 0xFCC1, 0xFD81, 0x3D40,
                    0xFF01, 0x3FC0, 0x3E80, 0xFE41, 0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840, 
                    0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41, 0xEE01, 0x2EC0, 0x2F80, 0xEF41,
                    0x2D00, 0xEDC1, 0xEC81, 0x2C40, 0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
                    0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041, 0xA001, 0x60C0, 0x6180, 0xA141, 
                    0x6300, 0xA3C1, 0xA281, 0x6240, 0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441, 
                    0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41, 0xAA01, 0x6AC0, 0x6B80, 0xAB41,
                    0x6900, 0xA9C1, 0xA881, 0x6840, 0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
                    0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40, 0xB401, 0x74C0, 0x7580, 0xB541,
                    0x7700, 0xB7C1, 0xB681, 0x7640, 0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
                    0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241, 0x9601, 0x56C0, 0x5780, 0x9741,
                    0x5500, 0x95C1, 0x9481, 0x5440, 0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
                    0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841, 0x8801, 0x48C0, 0x4980, 0x8941,
                    0x4B00, 0x8BC1, 0x8A81, 0x4A40, 0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
                    0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641, 0x8201, 0x42C0, 0x4380, 0x8341,
                    0x4100, 0x81C1, 0x8081, 0x4040]

        self.dict_modbus = self.create_query_dictionary()
        self.ser = self.connect_serial()

        
        print("Running...", self.name)


    @staticmethod
    def get_ports(report=False):
        # get list of serial ports and the id of the connected device
        ports = serial.tools.list_ports.comports()
        dict_ports = {}
        for port, desc, hwid in sorted(ports):
                try:
                    hardware_id = hwid.split(':')[1]
                    dict_ports[hardware_id] = port
                except:
                    pass
        if report: print(dict_ports)

        return dict_ports


    def connect_serial(self):
        try:
            port=self.port
            ser = serial.Serial(
                port=port,
                baudrate = 9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout = 0.1
                )

            return ser
        except Exception as e:
            print("Error connect_serial:", e)
    

    def get_meter_data(self, 
        report=False, 
        params=[
            'voltage', 
            'current', 
            'powerfactor', 
            'frequency', 
            'power_active', 
            ]):

        '''read power meter and save'''
        try:
            now = datetime.datetime.now()
            
            ### read meter data            
            for param in params:
                self.dict_data.update(self.read_meter(param))

            ### query states of other devices, and consolidate in dict_data
            # peer_states = MULTICAST.send(dict_msg={'states':'all'}, ip='224.0.2.0', port=17000, timeout=0.3, data_bytes=65536, hops=1)
            # for address, state in peer_states.items():
            #     self.dict_data.update(state)

            ### convert to dict_data to pandas dataframe
            # self.df_data = pd.DataFrame.from_dict(self.dict_data, orient='index').T

            ### save data to disk
            # df_agg = pd.melt(self.df_data.astype(str), id_vars=["unixtime"], var_name="parameter", value_name="value")
            # self.dict_data.update({"unixtime": int(now.timestamp()) })
            # self.dict_history.update({int(now.timestamp()): self.dict_data})            
            # self.dict_history = self.save_pickle(dict_data=self.dict_history, path=f'/home/pi/ldc_project/history/{self.house}_{now.strftime("%Y_%m_%d")}.pkl')

            # self.dict_history = self.save_feather(dict_data=self.dict_history, path=f'/home/pi/ldc_project/history/{self.house}_{now.strftime("%Y_%m_%d")}.feather')
            # self.save_csv(df_agg)
            if report: print(self.dict_data)

            return self.dict_data
        except Exception as e:
            print(f"Error METER.get_meter_data:{e}")
            return {}


    def read_meter(self, param='power_active'):
        # self.ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            response = [] #[1,1,1,1,1]
            count = 0
            while (not self.is_valid(response)) and (count<3):
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(self.dict_modbus['{}_{}'.format(param, _id)])
                response = self.ser.read(7 + (2*(self.dict_registers[param][1]-1)))
                count += 1

            dict_data.update({f'{param}_{_id}': int.from_bytes(response[3:-2], 'big') * self.dfactor[param]})
        
        return dict_data


    def save_csv(self, df_demand):
        try:
            # create history folder if not existing
            #if not os.path.exists('./history/'): os.makedirs('history')
            dt = datetime.datetime.fromtimestamp(float(df_demand.head(1)['unixtime'].values[0]))
            filename = dt.strftime('/home/pi/ldc_project/history/{}_%Y_%m_%d.csv'.format(self.house))
            with open(filename, 'a') as f:
                df_demand.to_csv(f, mode='a', header=f.tell()==0, index=False)

        except Exception as e:
            print("Error in METER.save_csv:", e)


    @staticmethod
    def save_pickle(dict_data, path='history/data.pkl.xz'):
        'Save data as pickle file.'
        try:
            df_all = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True).astype(float)
            try:
                on_disk = pd.read_pickle(path, compression='infer').reset_index(drop=True)
                df_all = pd.concat([on_disk, df_all], axis=0, sort=False).reset_index(drop=True)
                df_all['unixtime'] = df_all['unixtime'].astype(int)
                df_all = df_all.groupby('unixtime').mean().reset_index(drop=False)
                df_all.to_pickle(path, compression='infer')
            except Exception as e:
                df_all.to_pickle(path, compression='infer')
            
            return {}
        except Exception as e:
            print("Error METER.save_pickle:", e)
            return dict_data 

    @staticmethod
    def save_feather(dict_data, path='history/sample.feather'):
        try:
            df_all = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True).astype(float)
            try:
                on_disk = pd.read_feather(path).reset_index(drop=True)
                df_all = pd.concat([on_disk, df_all], axis=0).groupby('unixtime').mean().reset_index(drop=False)
            except Exception as e:
                pass
            df_all.to_feather(path)
            return {}
        except Exception as e:
            print("Error METER.save_feather:", e)
            return dict_data

         

    def is_valid(self, response):
        #check that the response received from the energy meter is valid - all read_() functions call this: 
        valid = 0
        
        if len(response)==5:
            #it generated an exception code, so not a response we want
            valid = 0

        else:
            checksum = self.crc(response[0:-2])
            checksum_string = array.array('B')
            checksum_string.append((checksum & 0xFF))
            checksum_string.append(((checksum >> 8) & 0xFF))
            calculated_checksum_val = int.from_bytes(checksum_string, 'big')
            sent_checksum_val = int.from_bytes(response[-2:], 'big')
            
            if (sent_checksum_val == calculated_checksum_val):
                valid = 1
            else:
                valid = 0
        
        return valid
        
        
    def create_modbus_query(self, register, bytes_to_read, _id=1):
        modbus_string = array.array('B')
    
        modbus_string.append(_id)
        modbus_string.append(0x03)
        
        modbus_register = register - 40001
        modbus_string.append(((modbus_register >> 8) & 0xFF))

        modbus_string.append((modbus_register & 0xFF))
    
        modbus_string.append(((bytes_to_read >> 8) & 0xFF))
        modbus_string.append((bytes_to_read) & 0xFF)
    
        checksum = self.crc(modbus_string)
        modbus_string.append((checksum) & 0xFF)
        modbus_string.append(((checksum >> 8) & 0xFF))
    
        return modbus_string


    def create_query_dictionary(self, params=['voltage', 'current', 'powerfactor', 'frequency',
        'power_active', 'power_reactive', 'power_apparent', 'energy_active', 'energy_reactive']):
        '''Create a dictionary of query string'''
        dict_modbus = {}
        for param in params:
            reg, btr = self.dict_registers[param]
        
            for _id in self.powermeter_ids:
                    dict_modbus['{}_{}'.format(param, _id)] = self.create_modbus_query(register=reg , bytes_to_read=btr, _id=_id)
        
        return dict_modbus


                
    def crc(self, data):
        #Calculates the CRC which is appended to the string of hex bytes sent to the energy meter.
        #calculated according to CRC16/MODBUS.
        crc = 0xFFFF  #starting CRC value

        for a in data:
            lookup_index = (crc ^ a) & 0xFF
            crc = (((crc >> 8) & 0xFF) ^ (self.crclookup[lookup_index]))

        return crc

    def autorun(self):
        # continually read meter data and store into queue
        while True:
            try:
                self.get_meter_data(params=['power_active', 'voltage', 'power_reactive'], report=True)
                time.sleep(0.5)
                
            except Exception as e:
                print("Error in autorun:", e)
                self.__del__()
    
        
    def __del__(self):
        # run the following upon destroying this object
        print("Destroying ", self.powermeter_ids)










 



if __name__ == '__main__':
    EM1 = EnergyMeter(house='H2', IDs=[0])
    while True:
        try:
            EM1.get_meter_data(report=True)                    
            pass
        except Exception as e:
            print("Error main:",e)
        except KeyboardInterrupt:
            break
    


""" NOTES 
    #the structure of the return is as follows
            #1. address
            #2. function
            #3. number of bytes to follow
            #4 to #n-2: data
            #n-1, n: checksum
        
            #unless for whatever reason a modbus exception code is generated, which I would need to handle in some way.
            #the exception messages always contain 5 bytes, and are formatted:
                #1. address
                #2. function with the most significant bit switched to 1 (for function 0x03, returns 0x83)
                #3. exception code
                #4, 5. CRC
            #this code has been written in such a way that an exception code should never be generated.
            
    #theoretically nothing should cause the energy meter to send something with an incorrect checksum - however, if noise is introduced it could corrupt the data packets (actually have observed this, but strangely enough only in the read_active_power() function.






def crc(data):
    #Calculates the CRC which is appended to the string of hex bytes sent to the energy meter.
    #calculated according to CRC16/MODBUS.
    crc = 0xFFFF  #starting CRC value
    crclookup = [0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241, 0xC601, 0x06C0, 0x0780, 0xC741, 
                0x0500, 0xC5C1, 0xC481, 0x0440, 0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40, 
                0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841, 0xD801, 0x18C0, 0x1980, 0xD941,
                0x1B00, 0xDBC1, 0xDA81, 0x1A40, 0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
                0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641, 0xD201, 0x12C0, 0x1380, 0xD341,
                0x1100, 0xD1C1, 0xD081, 0x1040, 0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
                0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441, 0x3C00, 0xFCC1, 0xFD81, 0x3D40,
                0xFF01, 0x3FC0, 0x3E80, 0xFE41, 0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840, 
                0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41, 0xEE01, 0x2EC0, 0x2F80, 0xEF41,
                0x2D00, 0xEDC1, 0xEC81, 0x2C40, 0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
                0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041, 0xA001, 0x60C0, 0x6180, 0xA141, 
                0x6300, 0xA3C1, 0xA281, 0x6240, 0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441, 
                0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41, 0xAA01, 0x6AC0, 0x6B80, 0xAB41,
                0x6900, 0xA9C1, 0xA881, 0x6840, 0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
                0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40, 0xB401, 0x74C0, 0x7580, 0xB541,
                0x7700, 0xB7C1, 0xB681, 0x7640, 0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
                0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241, 0x9601, 0x56C0, 0x5780, 0x9741,
                0x5500, 0x95C1, 0x9481, 0x5440, 0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
                0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841, 0x8801, 0x48C0, 0x4980, 0x8941,
                0x4B00, 0x8BC1, 0x8A81, 0x4A40, 0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
                0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641, 0x8201, 0x42C0, 0x4380, 0x8341,
                0x4100, 0x81C1, 0x8081, 0x4040] 

    for a in data:
        lookup_index = (crc ^ a) & 0xFF
        crc = (((crc >> 8) & 0xFF) ^ (crclookup[lookup_index]))

    return crc



def crc16(data):
    regCRC = 0xFFFF
    data = list(data)
    for i in range(0, int(len(data) / 2)):
        buff = int(data[2 * i], 16) << 4
        buff |= int(data[2 * i + 1], 16)
        regCRC = regCRC ^ buff
        for j in range(0, 8):
            if regCRC & 0x01:
                regCRC = (regCRC >> 1) ^ 0xA001
            else:
                regCRC = regCRC >> 1

    return ((regCRC & 0xFF00) >> 8) | ((regCRC & 0x0FF) << 8)

if __name__ == '__main__':  # Test
    print(hex(crc16("000600641c96")))
    print(hex(crc(b"000600641c96")))



"""
