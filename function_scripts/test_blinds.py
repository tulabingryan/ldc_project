import serial
import time
import numpy as np


def read():
    # read data from rs232
    ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate = 4800,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
            )
    try:
        while True:
            try:
                r = ser.readline(1).decode()
            except Exception as e:
                ser.close()
                raise e

        
        return r

    except Exception as e:
        raise e
    

def write(serial_msg):
    # send data to serial port
    try:
        ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate = 4800,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
            )
        
        ser.write(bytes.fromhex(serial_msg))

    except Exception as e:
        raise e

def control_position(id, ):
    return

def crc(data, checksum=0):
    for i in range(len(data)):
        checksum = checksum + data[i];
    a = '{:02x}'.format((checksum>>8)&0xFF)
    b = '{:02x}'.format(checksum&0xFF)
    crc_string = f"{a} {b}"
    return crc_string
  
  # checksumString[0] = (checksum >> 8) & 0xFF;
  # checksumString[1] = checksum & 0xFF;

if __name__ == '__main__':
    while  True:
        dict_channels = {'1':'FE', '2':'FD', 
            '3':'FC', '4':'FB',
            '5':'FA', '6':'F9',
            '7':'F8', '8':'F7',
            '9':'F6', '10':'F5',
            '11':'F4', '12':'F3',
            '13':'F2', '14':'F1',
            '15':'F0', '16':'EF',
            }
        dict_command = {'0':'FD', '1':'FE', '3':'FC'}
        try:
            msg = '7F F2 FA FF 00 00 E0 34 FA' 
            channel = dict_channels[input('channel:')]
            command = dict_command[input('command:')]
            msg = f"{msg} {channel} {command}"
            checksum = crc(bytes.fromhex(msg))
            cmd = f"{msg} {checksum}"
            write(serial_msg=cmd)
            # print("changing position...")
            time.sleep(1)
            
        except Exception as e:
            print("Error:", e)
            time.sleep(1)
        except KeyboardInterrupt:
            break



# t1 = time.perf_counter()
# response = np.array(ser.read(64).decode().split())
# idx = np.where(response=='p')
# print(idx, response)
# # power = reponse[idx+1]
# # power, csum, k = response
# # print("power:",power, " csum:", csum, " k:", k)
# # ser.close()

# print("Time elapsed:", time.perf_counter()-t1)

# except Exception as e:
# ser.close()
# raise e