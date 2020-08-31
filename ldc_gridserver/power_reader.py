import serial
import time
import numpy as np



def read_rs232():
    # read data from rs232
    ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate = 38400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
            )
    try:
        while True:
            try:
                r = ser.read(1).decode()
                if r=='p':  
                    response = np.array(ser.read(16).decode().split())
                    power, csum, k = response
                    print("power:",power, " csum:", csum, " k:", k)
                    ser.close()
                    break
                else:
                    pass
            except Exception as e:
                ser.close()
                raise e

        
        return float(power)

    except Exception as e:
        raise e
    

def write_rs232(msg):
    # send data to serial port
    try:
        ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate = 38400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
            )
        
        s_msg = list(msg)
        for s in s_msg:
            print(s)
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