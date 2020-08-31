'''
./WATERUSAGE.py
Simulation of hot water usage
Author: Ryan Tulabing
University of Aukcland
2017-2020
'''


import numpy as np
import pandas as pd
import time, datetime
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)

global relay_pin, status
relay_pin = 15

GPIO.setup(relay_pin, GPIO.OUT)

def relay(status, relay_pin=15):
    try:
        if status==1 or status==0:
            GPIO.output(relay_pin, status)
        else:
            print("Invalid status... choose in [0,1], 0=OFF, 1=ON")
    except Exception as e:
        print("Error relay:", e)



def get_dayhour():
    try:
        now = datetime.datetime.now()
        dayhour = now.hour + (now.minute/60) + (now.second / 3600)
        return dayhour
    except Exception as e:
        print("Error get_dayhour:", e)
        return 0




def drain_valve(duration=5):
    ## drain valve for a duration [seconds]
    relay(1)
    time.sleep(duration)  # keep valve open for 3 seconds
    relay(0)
        
    def mcast_listener(self):
        # Receive multicast message from the group
        counter = 0
        while  True:
            try:
                multicast_ip = '238.173.254.147'
                port=12604
                multicast_group = (multicast_ip, port)  # (ip_address, port)
                # Create the socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Bind to the server address
                sock.bind(multicast_group)

                # Tell the operating system to add the socket to
                # the multicast group on all interfaces.
                group = socket.inet_aton(multicast_ip)
                mreq = struct.pack('4sL', group, socket.INADDR_ANY)
                sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    mreq)
                break
            except Exception as e:
                print("Error in ", self.name, " mcast_listener binding socket:",e)
        
        dict_toSend_self = {}
        dict_toSend_all = {}
        dict_toSend_house = {}
        # Receive/respond loop
        while True:
            # receive and decode message
            data, address = sock.recvfrom(1024)
            received_msg = data.decode("utf-8")
            dict_msg = ast.literal_eval(received_msg)
            
            # prepare data to send, fetch latest data from the queue
            try:
                # Note: house name is used as the key, 'all' is a query from the aggregator  
                key = list(dict_msg)[0]
                
                
                if key in [self.house, "all"]:          
                    if dict_msg[key] in ["h"]:  # response to home_server
                        if self.q_states_self.empty():
                            # print('q_states_self is empty ')
                            time.sleep(0.1)
                        else:
                            dict_onQueue = self.q_states_self.get(block=False)  # remove one item on queue
                            self.q_states_self.task_done()  # release block
                            dict_toSend_self.update(dict_onQueue)
                            message_toSend_self = str(dict_toSend_self).encode()
                            sock.sendto(message_toSend_self, address)
                            # print("Responded to home_server at:", address)
                        
                    if dict_msg[key] in ["a"]: # response to RESISTORBANK
                        if self.q_house_agg.empty():
                            # print('q_house_agg is empty')
                            time.sleep(0.1)
                        else:
                            dict_onQueue_house = self.q_house_agg.get(block=False)
                            self.q_house_agg.task_done()
                            dict_toSend_house.update(dict_onQueue_house)
                            message_toSend_house = str(dict_toSend_house).encode()
                            sock.sendto(message_toSend_house, address)
                            # print("Responded to RESISTORBANK at:", address)

                    else:
                        pass

                # elif key==self.App.name[0]:
                #     while  self.q_states_all.empty() is False:
                #         dict_onQueue = self.q_states_all.get(block=False)
                #         self.q_states_all.task_done()
                #     self.q_states_all.put(dict_onQueue)
                #     dict_toSend_all.update(dict_onQueue)
                #     message_toSend = str(dict_toSend_all).encode()
                #     sock.sendto(message_toSend, address)

                #     # update user command
                #     while self.q_user_cmd.empty() is False:
                #         self.dict_user_cmd = self.q_user_cmd.get()
                #         self.q_user_cmd.task_done()
                #     self.dict_user_cmd.update(dict_msg[self.name])
                #     self.q_user_cmd.put(self.dict_user_cmd)
                else:
                    pass

                    
            except Exception as e:
                print("Error in DONGLE mcast_listener:", e)
                pass                      
        return



class Waterheater(object):
    """docstring for Waterheater"""
    def __init__(self):
        super(Waterheater, self).__init__()
        
        


if __name__ == '__main__':
    while True:
        try:
            drain_valve()
        except Exception as e:
            print("Error main:", e)
            GPIO.output(relay_pin, 0)
            GPIO.cleanup() 
        except KeyboardInterrupt:
            GPIO.output(relay_pin, 0)
            GPIO.cleanup() 
            break


# result = subprocess.run(['ls', '-l', stdout=subprocess.PIPE])
# result.stdout