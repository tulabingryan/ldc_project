import serial
import time
import numpy as np


#B4800 | CS8 | CLOCAL | CREAD | PARENB | PARODD

def read_rs232():
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
    

def write_rs232(msg):
    # send data to serial port
    try:
        ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate = 4800,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
            )
        
        s_msg = list(msg)
        for s in s_msg:
            ser.write(s.encode('ascii'))
            # time.sleep(0.001)

        ser.write(b'\r')

    except Exception as e:
        raise e


if __name__ == '__main__':
    while  True:
        try:
            # t1 = time.perf_counter()
            read_rs232()
            # print("elapsed:", time.perf_counter()-t1)
        except Exception as e:
            # print("Error:", e)
            time.sleep(0.5)
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