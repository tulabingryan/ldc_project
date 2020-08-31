# MULTICAST.py
# Ryan Tulabing
# University of Auckland, 2017-2020

import socket
import struct
import sys
import time
import json
import ast
import pandas as pd
import serial




def send(dict_msg, ip, port, timeout=1, hops=1):
    # send multicast query to listening devices
    multicast_group=(ip, port)
    # Create the datagram socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Set a timeout so the socket does not block
    # indefinitely when trying to receive data.
    sock.settimeout(timeout)
    

    # Set the time-to-live for messages to 1 so they do not
    # go past the local network segment.
    ttl = struct.pack('b', hops)  # number of hops
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    dict_demand = {}
    x = time.perf_counter()

    try:
        # Send data to the multicast group 
        message = str(dict_msg).replace("'", "\"").encode()
        # counter = time.perf_counter()
    
        sent = sock.sendto(message, multicast_group)

        # Look for responses from all recipients
        while True:
            try:
                data, server = sock.recvfrom(int(2**16))
                received_msg = data.decode("utf-8")
                dict_msg = ast.literal_eval(received_msg)
                dict_demand.update(dict_msg)
            except Exception as e:
                # print("Error inner:", e)
                break                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    

            # except socket.timeout:
            #     break
            # else:
            #     pass
    except Exception as e:
        # print("Error in MULTICAST send:", e)
        sock.close()
    finally:
        sock.close()

    return dict_demand

           
# ## test ###
# for i in range(10):
#     d = send(dict_msg={"power":"all"}, ip='224.0.2.0', port=17000, timeout=0.5, hops=64)
#     # print(pd.DataFrame.from_dict(d, orient='index'))
#     print(d)
# ## end test ###


def receive(ip='224.0.2.0', port=10000):
    # Receive multicast message from the group
    multicast_group = (ip, port)  # (ip_address, port)


    # Create the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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
    
    dict_demand = {}
    # a = time.perf_counter()
    # Receive/respond loop
    while True:
        # print('\nwaiting to receive message')
        data, address = sock.recvfrom(1024)


        #print('received {} bytes from {}'.format(
        #    len(data), address))
        #print(data)
            

        #print('sending acknowledgement to', address)
        #sock.sendto(data, address)
        

        message = data.decode("utf-8")
        dict_msg = ast.literal_eval(message)
        dict_demand.update(dict_msg)
        df_demand = pd.DataFrame.from_dict(dict_demand, orient='index')
        df_demand = df_demand.sort_values('flexibility',ascending=True, axis=0)
        
        try:        
            # print(df_demand[['flexibility','priority','demand','Ta','HWC_Ta','HWC_mode']])
            print("Demand updated")
            
        except Exception as e:
            # print(df_demand)
            pass

        print(time.perf_counter() - a)
        a = time.perf_counter()

        return df_demand

   



#--- Test ---
# dict_msg = {"hello":{"hi":1.0, "yo":2.0}}
# send(dict_msg)



# def read_rs232(self):
#     # read data from rs232
#     try:
#         s = serial.Serial(
#             port='/dev/ttyUSB0',
#             baudrate = 38400,
#             parity=serial.PARITY_NONE,
#             stopbits=serial.STOPBITS_ONE,
#             bytesize=serial.EIGHTBITS,
#             timeout=1
#             )
#     except:
#         s = serial.Serial(
#             port='/dev/ttyAMA0',
#             baudrate = 38400,
#             parity=serial.PARITY_NONE,
#             stopbits=serial.STOPBITS_ONE,
#             bytesize=serial.EIGHTBITS,
#             timeout=1
#             )

#     try:
#         response = s.read(1).decode()
        
#         if response[0] == 'p':
#             response = s.read(16).decode().split()
#             power, csum, k = response
#             # print("power:", power, " csum:", csum, " k:", k)
#             self.agg_demand = float(power)
#             self.dict_agg['grid'] = self.agg_demand
#             return self.agg_demand
#         else:
#             pass
#     except Exception as e:
#         # print("Error in read_rs232.", e)
#         pass