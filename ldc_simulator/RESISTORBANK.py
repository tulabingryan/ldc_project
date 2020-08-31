'''
./GRAINY.py 
Module for Load Emulator
Author: Ryan Tulabing
Project: Local Demand Control
Institution: University of Auckland
Year: 2017
'''

        
#---import python packages---
import os
import datetime, time
import threading, queue
import numpy as np
import multiprocessing
import pandas as pd
import sqlite3 as lite

# for multicast
import socket
import struct
import sys
import json
import ast

try:
    # for interacting with raspi
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)     # set up BOARD GPIO numbering 
    # for reading spi
    import spidev
except Exception as e:
    print("Error importing GPIO, spidev",e)

try:
    # for driving chroma
    import serial
    
except Exception as e:
    print("Error importing serial",e)
    

try:
    # for controlling pifacedigital
    import pifacedigitalio
except Exception as e:
    print("Error importing pifacedigitalio",e)

#---import local packages---
import MULTICAST
import FUNCTIONS



#multiprocessing.Process
class GrainyLoad(multiprocessing.Process):
    'Common base class for grainy load driver'
    
    def __init__(self, name):
        
        multiprocessing.Process.__init__(self)
        self.daemon = True

        
        self.name = name
        self.house = name
        self.dict_states_all = {}
        
        # initialize variables
        self.p_watt = 0
        self.q_var = 0
        self.s_va = 0
        self.power_factor = 1
        self.grainy_load = 0
        self.chroma_load = 0

        # initialize spi reader
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)  # (bus, device)
            self.spi.bits_per_word = 8
            self.spi.max_speed_hz = 500000
            self.spi.mode = 3
        except:
            pass
        
        # initialization to drive the pifacedigital
        self.pins = [0,0,0,0,0,0,0,0]
        self.df_relay, self.df_states = FUNCTIONS.create_states()

        try:
            self.pf = pifacedigitalio.PiFaceDigital()

        except Exception as e:
            print("Error piface instance:", e)

        self.step()
       
    def step(self):
        ### main routine
        while True:
            try:
                self.query()  # aggregate data
                self.emulate_model()  # emulate models using resistor bank and chroma
                
                # print(self.grainy_load, self.chroma_load, self.power_factor)
                
            except Exception as e:
                print("Error in ", self.name, " step:", e)
                # time.sleep(1)


    def query(self):
        # Ask peers about their demand and flexibility
        try:
            dict_msg = {self.house:'a'}  # prepare mcast command
            self.dict_states_all.update(MULTICAST.send(dict_msg, ip='238.173.254.147', port=12604, timeout=0.1))  # update data
                
            # process dict to data frame
            valid_stamp = int(time.time()) - 10
            self.df_states_all = pd.DataFrame.from_dict(self.dict_states_all, orient='index')
            self.df_states_all = self.df_states_all.loc[(self.df_states_all['house']==self.house)]
            self.df_states_all = self.df_states_all.loc[(self.df_states_all['unixtime']>=valid_stamp)]
            # self.df_states_all[['a_demand']] = self.df_states_all[['a_demand']].astype(float)
            self.df_states_all[['p_mw', 'q_mvar']] = self.df_states_all[['p_mw', 'q_mvar']].astype(float)

            
            return self.df_states_all
        except Exception as e:
            print("Error in RESISTORBANK query:", e)
            return pd.DataFrame(columns=['house','load_type','a_demand','flexibility','priority'])



    def emulate_model(self):
        # loads to be emulated in chroma
        try:
            # waterheater_load = self.df_states_all[self.df_states_all['load_type']=='waterheater']['a_demand'].values
            # self.grainy_load = self.df_states_all['a_demand'].sum(axis=0).values - waterheater_load

            self.p_watt = self.df_states_all['p_mw'].sum(axis=0) * 1e6
            self.q_var = self.df_states_all['q_mvar'].sum(axis=0) * 1e6

            self.grainy_load = self.p_watt
            self.chroma_load = self.drive_piface()   # this will return the residual power that can't be emulated in the grainy load

            self.s_va = np.clip(((self.chroma_load)**2 + (self.q_var)**2)**0.5, a_min=1, a_max=30e3)
            self.power_factor = self.chroma_load / self.s_va
            self.drive_chroma()
        except Exception as e:
            print("Error RESISTORBANK emulate_model:",e)


    def drive_chroma(self):
        # Send data to Chroma variable load simulator
        # through serial interface (rs232)
        try:
            rs232 = serial.Serial(
                port='/dev/ttyUSB0',
                baudrate = 57600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
                )
            
            # print("Chroma:", self.chroma_load)
            if self.chroma_load<=0:
                rs232.write(b'LOAD OFF\r\n')  # turn OFF if load is zero
            else:    
                rs232.write(b'CURR:PEAK:MAX 28\r\n')  # set current limit

                # set power factor
                pfac_cmd = 'PFAC ' + str(self.power_factor) + '\r\n'
                rs232.write(pfac_cmd.encode())  # set current limit

                print(self.chroma_load, self.chroma_load/self.power_factor)
                # set power, watt
                # rs232.write(b'MODE POW\r\n')  # set 
                cmd = 'POW '+ str(self.chroma_load) +'\r\n'
                rs232.write(cmd.encode())

                rs232.write(b'LOAD ON\r\n')

        except Exception as e:
            print("Error drive_chroma:", e)
            pass
        

    def drive_piface(self):
        try:
            # convert baseload value into 8-bit binary to drive 8 pinouts of piface
            newpins, residual = FUNCTIONS.relay_pinouts(self.grainy_load, self.df_relay, self.df_states, report=False)
            # print("Grainy:", self.grainy_load)
            for i in range(len(self.pins)):
                if self.pins[i]==0 and newpins[i]==1:
                    self.pf.output_pins[i].turn_on()
                elif self.pins[i]==1 and newpins[i]==0:
                    self.pf.output_pins[i].turn_off()
                else:
                    pass
            self.pins = newpins
            return residual
        except Exception as e:
            print("Error drive_piface:", e)
            return self.grainy_load



    def __del__(self):
        try:
            print(self.name, " deleted...")
            GPIO.cleanup()         # clean up the GPIO to reset mode
            for i in range(len(self.pins)):
                self.pf.output_pins[i].turn_off()
        except:
            pass



##################################################

    # def save_data(self):
    #     try:
    #         # create history folder if not existing
    #         if not os.path.exists('./history/'): os.makedirs('history')

    #         if len(self.df_history.index) > 0:
    #             pass
    #         else:
    #             # check latest record
    #             self.df_history = pd.read_csv('./history/' + sorted(os.listdir('history'))[-1])

    #         start_dt = datetime.datetime.fromtimestamp(float(self.df_history.head(1)['unixtime'].values))
    #         end_dt = datetime.datetime.fromtimestamp(float(self.df_states_all['unixtime'].values[0]))

    #         if start_dt.day == end_dt.day:
    #             df_data_new = pd.melt(self.df_states_all, id_vars=["unixtime", "localtime", "house", "id", "type"], 
    #                       var_name="parameter", value_name="value")
    #             df_data_new = df_data_new.dropna()
    #             # add new data
    #             self.df_history = pd.concat([self.df_history,df_data_new], sort=False).reset_index(drop=True)
    #             # save the data
    #             self.df_history.to_csv(start_dt.strftime('./history/%Y-%m-%d.csv'), index=False)

    #         else:
    #             # save the old data
    #             self.df_history.to_csv(start_dt.strftime('./history/%Y-%m-%d.csv'), index=False)
    #             df_data_new = pd.melt(self.df_states_all, id_vars=["unixtime", "localtime", "house", "id", "type"], 
    #                       var_name="parameter", value_name="value")
    #             df_data_new = df_data_new.dropna()
    #             self.df_history = df_data_new
    #             # save the new data
    #             self.df_history.to_csv(end_dt.strftime('./history/%Y-%m-%d.csv'), index=False)


    #     except Exception as e:
    #         print("Error in save_data:", e)


        


    


def main():
    try:
        local_ip = FUNCTIONS.get_local_ip(report=True)
        idx = int(local_ip.split('.')[2])-1
        df_houseSpecs = pd.read_csv('./specs/houseSpecs.csv')
        G = GrainyLoad(name=df_houseSpecs.loc[idx, 'name'])
        
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()