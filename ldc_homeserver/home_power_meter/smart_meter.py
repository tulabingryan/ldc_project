# ./smart_meter.py
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

# local packages
import METER


# Set up a class which holds parameters of each energy meter.
class EnergyMeter(multiprocessing.Process):
    ''' Generic Class for an energy meter'''    
    def __init__(self, ID):

        multiprocessing.Process.__init__(self)
        self.daemon = True
    

        self.id = ID
        self.voltage = 0
        self.current = 0
        self.powerfactor = 0
        self.frequency = 0
        self.power_active = 0
        self.power_reactive = 0
        self.power_apparent = 0
        self.energy_active = 0
        self.energy_reactive = 0

        # multicasting ip and port
        self.mcast_ip = '224.0.2.0'
        self.mcast_port = 17000

        # initialize dictionary for data
        self.dict_data = {
            "unixtime":time.time(),
            "localtime":datetime.datetime.now().isoformat(),
            "id":self.id,
            "voltage":self.voltage,
            "current":self.current,
            "powerfactor":self.powerfactor,
            "frequency":self.frequency,
            "power_active":self.power_active,
            "power_reactive":self.power_reactive,
            "power_apparent":self.power_apparent,
            "energy_active":self.energy_active,
            "energy_reactive":self.energy_reactive,
        }  

        self.q_data = queue.Queue(maxsize=3)  # data can only be passed in different threads using queue

        # run separate threads
        thread = threading.Thread(target=self.respond_to_query, args=())
        thread.daemon = True                         # Daemonize thread
        thread.start() 

        self.step()  # run step function to read meter data and store in queue


    
    def get_meter_data(self):
        # read power meter, update dict_data, and put into q_data
        # use the functions in METER.py here
        try:
            # read data from meter
            self.voltage = METER.read_voltage(self.id)
            self.current = METER.read_current(self.id)
            self.powerfactor = METER.read_powerfactor(self.id)
            self.frequency = METER.read_frequency(self.id)
            self.power_active = METER.read_power_active(self.id)
            self.power_reactive = METER.read_power_reactive(self.id)
            self.power_apparent = METER.read_power_apparent(self.id)
            self.energy_active = METER.read_energy_active(self.id)
            self.energy_reactive = METER.read_energy_reactive(self.id)
        except:
            pass

        # update dictionary
        self.dict_data.update({
            "unixtime":time.time(),
            "localtime":datetime.datetime.now().isoformat(),
            "id":self.id,
            "voltage":self.voltage,
            "current":self.current,
            "powerfactor":self.powerfactor,
            "frequency":self.frequency,
            "power_active":self.power_active,
            "power_reactive":self.power_reactive,
            "power_apparent":self.power_apparent,
            "energy_active":self.energy_active,
            "energy_reactive":self.energy_reactive,            
            })

        print(self.dict_data)
        # put on the queue
        while self.q_data.empty() is False:
            self.q_data.get() # empty all of past data
            self.q_data.task_done()  # release lock
        self.q_data.put(self.dict_data) # put data on queue

        return self.dict_data



    def respond_to_query(self):
        # Receive query and send dict_data as a response (running as a separate thread)
        multicast_ip = self.mcast_ip
        port = self.mcast_port

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
        
        dict_toSend = {}
        
        # Receive/respond loop
        while True:
            # receive and decode message
            data, address = sock.recvfrom(1024)
            received_msg = data.decode("utf-8")
            dict_msg = ast.literal_eval(received_msg)
            # prepare data to send, fetch latest data from the queue
            try:
                if list(dict_msg)[0] in ['power']:
                    if self.id== dict_msg['power']:  # only respond if ID is same as self.id
                        # fetch latest data on queue        
                        while self.q_data.empty() is False:
                            dict_onQueue = self.q_data.get()
                            self.q_data.task_done()
                        self.q_data.put(dict_onQueue)  # return latest data on queue to avoid empty queue
                        
                        dict_toSend.update(dict_onQueue)
                        message_toSend = str(dict_toSend).encode('utf-8')
                        # send message
                        sock.sendto(message_toSend, address)
                        

                    else:
                        pass
                else:
                    pass
                
            except Exception as e:
                print("Error respond_to_query:", e)
                
        return


    def step(self):
        # continually read meter data and store into queue
        while True:
            try:
                self.get_meter_data()
                time.sleep(1)
            except Exception as e:
                print("Error in ", self.id, " step:", e)

    def __del__(self):
        # run the following upon destroying this object
        print("Destroying ", self.id)


if __name__ == '__main__':
    while True:
        try:
            # create class instance
            ID = '001'
            EM1 = EnergyMeter(ID)
        except Exception as e:
            print("Error main:",e)
        except KeyboardInterrupt:
            break
    