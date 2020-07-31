import socket
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BOARD)     # set up BOARD GPIO numbering  

def setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40]):
    # setup the raspi gpio
    try:
        

        for x in inputs:
            GPIO.setup(int(x), GPIO.IN)

        for y in outputs:
            GPIO.setup(int(y), GPIO.OUT)

        # print("Input channels:", inputs)
        # print("Output channels:", outputs)

    except:
        pass

    return


def gpio_out(pins=[15, 32, 36, 38, 40], states=[0,0,0,0,0]):
    # Output signal to gpio
    try:
        GPIO.output(pins, states)
    except:
        pass
    return 


def get_local_ip(report=False):
    # get local ip address
    count = 0
    local_ip = '127.0.0.1'
    while True and count < 5:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            break
        except Exception as e:
            print("Error in FUNCTIONS get_local_ip: ", e)
            count += 1
    if report: print("Local IP:{}".format(local_ip))
    return local_ip

def execute_state(newstate, device_id, report=False):
    setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40])
    if newstate not in [0,1]:
        print("Invalid input...")
    else:
        if device_id in [123, 124, 125]: 
            s = (not newstate)*1  # logic for doors is reversed
        else:
            s = newstate
            
        if s==GPIO.input(32): 
            if report: print('Unit already in that state')
            pass
        else:
            GPIO.output([15, 32, 36, 38, 40], [1, s, s, s, s])
            if report: print('Changing state, please wait...')
            time.sleep(30)
            if report: print('State changed to:{}'.format(dict_state[newstate]))
    
    GPIO.output([15, 32, 36, 38, 40], [0, s, s, s, s])


if __name__=="__main__":
    local_ip = get_local_ip()
    device_id = int(local_ip.split('.')[3])
    dict_state = {0:'CLOSED', 1:'OPEN'}
    execute_state(0, device_id)  # initially put it to closed status

    try:
        while True:
            try:

                newstate = int(input(f"Change state[0: {dict_state[0]},    1: {dict_state[1]}]:"))
                execute_state(newstate, device_id, report=True)
                                    
            except Exception as e:
                print("Error main:", e)

            except KeyboardInterrupt:
                break
    finally:
        GPIO.cleanup() # clean up the GPIO to reset mode
        
