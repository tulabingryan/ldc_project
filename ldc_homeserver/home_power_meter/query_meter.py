# ./query_meter.py
# James Ashworth, Ryan Tulabing
# University of Auckland
# 26/11/2018

import socket
import struct
import sys
import time
import json
import ast
import pandas as pd
import serial
import multiprocessing
import threading, queue

# local packages
import METER




def send_query(dict_msg, ip='224.0.2.0', port=17000, timeout=0.1, hops=1):
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

    dict_local = {}
    x = time.perf_counter()

    try:
        # Send data to the multicast group 
        message = str(dict_msg).replace("'", "\"").encode()
        counter = time.perf_counter()
        sent = sock.sendto(message, multicast_group)

        # Look for responses from all recipients
        while True:
            try:
                data, server = sock.recvfrom(int(2**16))
                received_msg = data.decode("utf-8")
                dict_msg = ast.literal_eval(received_msg)
                dict_local.update(dict_msg)

            except socket.timeout:
                break
            else:
                pass
    except Exception as e:
        print("Error in MULTICAST send:", e)
        sock.close()
    finally:
        sock.close()

    return dict_local





if __name__ == '__main__':
    while True:
        try:
            ID = input("Meter ID: ")
            dict_msg = {"power":ID}
            dict_data = send_query(dict_msg=dict_msg)
            print(dict_data)
        except Exception as e:
            print("Error main:", e)
        except KeyboardInterrupt:
            break
