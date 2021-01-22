# MULTICAST.py
# Ryan Tulabing
# University of Auckland, 2017-2020


import os
import datetime, time
import threading, queue, multiprocessing
import numpy as np
import pandas as pd
import sqlite3 as lite

# for multicast
import socket
import struct
import sys
import json
import ast




def send(dict_msg={'sample':'test'}, ip='224.0.2.0', port=17000, timeout=0.5, data_bytes=8192, hops=1):
    # send multicast query to listening devices
    address_port=(ip, port)
    # Create the datagram socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Set a timeout so the socket does not block
    # indefinitely when trying to receive data.
    sock.settimeout(timeout)

    # Set the time-to-live for messages to 1 so they do not
    # go past the local network segment.
    ttl = struct.pack('b', hops)  # number of hops
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    dict_received = {}
    x = time.perf_counter()

    try:
        # Send data to the multicast group 
        message = str(dict_msg).encode()
        sent = sock.sendto(message, address_port)
        # Look for responses from all recipients
        while True:
            try:
                data, address = sock.recvfrom(data_bytes)
                m = data.decode("utf-8")
                msg_received = ast.literal_eval(m)
                dict_received.update({address[0]:msg_received})
                
            except socket.timeout:
                break
            except Exception as e:
                print(f'Error MULTICAST send response loop:{e}')
                
            
    except Exception as e:
        print("Error in MULTICAST send", e)
        pass
    finally:
        sock.close()

    return dict_received

            # if self.timestamp >= int(self.df_weather['unixtime'].tail(1)):
                        #     self.df_weather = self.get_weatherHistory(unixtime=int(self.timestamp) + (60*60*2), report=False)
            

### test ###
# d = send(dict_msg={"all":"id"}, ip='224.0.2.0', port=10000, timeout=10, hops=64)
# print(d)
### end test ###


def receive(ip='224.0.2.0', port=17000):
    # Receive multicast message from the group
    multicast_group = (ip, port)  # (ip_address, port)


    # Create the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to the server address
    sock.bind(multicast_group)

    # Tell the operating system to add the socket to
    # the multicast group on all interfaces.
    group = socket.inet_aton(ip)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_ADD_MEMBERSHIP,
        mreq)
    
    # Receive/respond loop
    while True:
        try:
            print('\nwaiting to receive message')
            data, address = sock.recvfrom(1024)          

            print('sending acknowledgement to', address)
            sock.sendto(data, address)            

            message = data.decode("utf-8")
            dict_msg = ast.literal_eval(message)
            print(dict_msg)
            
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'Error:{e}')
        
        

class Listener():
    """docstring for Listener"""
    def __init__(self, ip, port, q_to_send, house):
        super(Listener, self).__init__()
        
        self.q_to_send = q_to_send  # input queue to monitor, source of response
        self.dict_data = {}
        self.house = house
        self.dict_to_send = {}
        self.dict_on_queue = {}
        
        self.setup()
        self.listen()

    def setup(self):
        ### create connection
        while  True:
            try:
                self.multicast_group = (self.ip, self.port)  # (ip_address, port)
                # Create the socket
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Bind to the server address
                self.sock.bind(self.multicast_group)

                # Tell the operating system to add the socket to
                # the multicast group on all interfaces.
                self.group = socket.inet_aton(self.ip)
                self.mreq = struct.pack('4sL', self.group, socket.INADDR_ANY)
                self.sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    mreq)
                break
            except Exception as e:
                print("Error in MULTICAST Listener binding socket:",e)
        

    def listen(self):
        # Receive/respond loop
        while True:
            # receive and decode message
            data, address = self.sock.recvfrom(1024)
            received_msg = data.decode("utf-8")
            dict_msg = ast.literal_eval(received_msg)
            
            # prepare data to send, fetch latest data from the queue
            try:
                # Note: house name is used as the key, 'all' is a query from the aggregator  
                key = list(dict_msg)[0]
                
                if key in [self.house, "all"]:          
                    if dict_msg[key] in ["a"]: # response to RESISTORBANK
                        if self.q_to_send.empty():
                            pass
                        else:
                            self.dict_on_queue = self.q_to_send.get()
                            self.q_to_send.task_done()
                            self.dict_to_send.update(self.dict_on_queue)
                            message_to_send = str(self.dict_to_send).encode()
                            sock.sendto(message_to_send, address)
                            # print("Responded to :", address)

                    else:
                        pass

                    
            except Exception as e:
                print("Error in MULTICAST Listener listen:", e)
                pass                      
        return


        

#--- Test ---
# dict_msg = {"hello":{"hi":1.0, "yo":2.0}}
# send(dict_msg)
