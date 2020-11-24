import numpy as np
import pandas as pd
import datetime, time
import serial



def create_states(power_list=[75,150,300,600,1200,2400,4800,4800], report=False):
    # create a 256 combination of power levels in the power_list

    try:
        ### read csv
        df_relay = pd.read_csv('./relay_states.csv')
        df_states = pd.read_csv('./power_states.csv')
        
    except Exception as e:    
        state_list = [np.array(list('{0:08b}'.format(x))).astype(int) for x in np.arange(256)]
        df_relay = pd.DataFrame(state_list)
        array_states = np.array(state_list) * np.array(power_list).T
        df_states = pd.DataFrame(array_states)
        df_states['value'] = df_states.sum(axis=1)
        ### save to csv 
        # df_states['orig_idx'] = df_states.index
        # df_states = df_states.sort_values('value').reset_index(drop=True)
        # df_relay.to_csv('./relay_states.csv', index=False)
        # df_states.to_csv('./power_states.csv', index=False)

    if report:
        print(df_relay)
        print(df_states)
        print(sorted(df_states['value']))
    return df_relay, df_states
# test #
# create_states(report=True)
# end test


def calc_distance(a, b):
    return np.linalg.norm(a-b)

# test
# d = calc_distance(43, 24)
# print(d)
# end test


def find_nearest(value, value_list, report=False, border='lower'):
    # map value to the nearest value in the value_list
    try:
        ds = [calc_distance(value, x) for x in value_list]
        idx = np.argsort(ds)
        closest_value = value_list[idx[0]]
        

        if value_list[idx[0]] <  value_list[idx[1]]:
            lower_idx = idx[0]
            lower_value = value_list[idx[0]]
            upper_idx = idx[1]
            upper_value = value_list[idx[1]]
        else:
            lower_idx = idx[1]
            lower_value = value_list[idx[1]]
            upper_idx = idx[0]
            upper_value = value_list[idx[0]]
        
        

        if report: 
            print("Value:{}  closest:{}  lower:{}  upper:{}  ".format(value, closest_value, lower_value, upper_value))

        if border=='lower':
            return lower_idx, lower_value
        elif border=='upper':
            return upper_idx, upper_value
        elif border=='closest':
            return idx[0], closest_value

        
    except Exception as e:
        print("Error find_nearest:", e)
        df_relay, df_states = create_states()
        value_list = df_states['value']
        ds = [calc_distance(value, x) for x in value_list]
        idx = np.argmin(ds)
        if report: print(idx)
        return idx, value_list[idx]



def relay_pinouts(value, df_relay, df_states, report=False):
    # drive the raspi pinouts
    try:
        idx, nearest_power = find_nearest(value, df_states['value'], border='lower', report=False)
        residual = value - nearest_power
        if report: print('Nearest:{}, Residual:{}, Pins:{}'.format(nearest_power, residual, df_relay.loc[idx].values))
        return df_relay.loc[idx].values, nearest_power, residual 
    except Exception as e:
        #print("Error relay_pinouts:",e)
        df_relay, df_states = create_states()
        idx, nearest_power = find_nearest(value, df_states['value'], border='lower')
        residual = value - nearest_power
        if report: print('Nearest:{}, Residual:{}, Pins:{}'.format(nearest_power, residual, df_relay.loc[idx].values))
        return df_relay.loc[idx].values, nearest_power, residual


def pinouts(value, df_states, report=False):
    df_states['idx'] = df_states.index
    # df_states = df_states.sort_values(['value'])
    # df_states = df_states[df_states['value']<=value]
    residual = value % 75
    nearest_power = value - residual
    new_pins = df_states[[0,1,2,3,4,5,6,7]][df_states['value']==nearest_power].values[0].flatten()
    new_pins = (new_pins>0)*1
    if report: print('Nearest:{}  Residual:{}  Pins:{}'.format(nearest_power, residual, new_pins))

    return new_pins, nearest_power, residual



class Grainy():
    def __init__(self):
        while True:
            try:
                ### setup raspi
                import serial
                import pifacedigitalio
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BOARD)
                GPIO.setwarnings(False)
                self.pins = [0,0,0,0,0,0,0,0]
                self.pf = pifacedigitalio.PiFaceDigital()
                self.df_relay, self.df_states = create_states(report=False)  # create power levels based on resistor bank
                print('piface setup successfull...')
                
                ### declare variables 
                self.dict_history = {}
                dict_agg = {}

                break
            except Exception as e:
                print(f"Error AGGREGATOR.drive_grainy.setup:{e}")
                time.sleep(30)
            except KeyboardInterrupt:
                break


    def drive_grainy(self, demand):
        # initialization to drive the pifacedigital
        try:
            total = min([demand, 10e3]) #limit to 10kW

            ### convert total load value into 8-bit binary to drive 8 pinouts of piface
            newpins, grainy, chroma = relay_pinouts(total, self.df_relay, self.df_states, report=False)
            
            ### execute piface command
            for i in range(len(self.pins)):
                if self.pins[i]==0 and newpins[i]==1:
                    self.pf.output_pins[i].turn_on()
                elif self.pins[i]==1 and newpins[i]==0:
                    self.pf.output_pins[i].turn_off()
            self.pins = newpins  # store updated pin states

            ### execute chroma emulation, send through rs232
            rs232 = serial.Serial(
                port='/dev/ttyUSB0',
                baudrate = 57600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1)
            if chroma<=0:
                rs232.write(b'LOAD OFF\r\n')
            else:    
                rs232.write(b'CURR:PEAK:MAX 28\r\n')
                rs232.write(b'MODE POW\r\n')
                cmd = 'POW '+ str(chroma) +'\r\n'
                rs232.write(cmd.encode())
                rs232.write(b'LOAD ON\r\n')

        except KeyboardInterrupt:
            print("Terminating grainy load driver...")
            for i in range(len(self.pins)):
                self.pf.output_pins[i].turn_off()
        except Exception as e:
            print("Error drive_grainy:", e)
            


if __name__ == '__main__':
    grainy = Grainy()
    while True:
        try:
            demand = input('Target Watt:')
            grainy.drive_grainy(float(demand))
        except Exception as e:
            print(e)
        except KeyboardInterrupt:
            break