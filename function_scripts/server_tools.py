# Ryan Tulabing
# University of Auckland, 2017-2020

import socket
import struct
import sys
import time
import json
import ast
import pandas as pd


def send(dict_msg, ip, port, timeout=0.05, hops=1):
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

    dict_data = {}
    x = time.perf_counter()

    try:
        # Send data to the multicast group 
        message = str(dict_msg).encode()
        counter = time.perf_counter()
        sent = sock.sendto(message, multicast_group)
        # Look for responses from all recipients
        while True:
            try:
                data, server = sock.recvfrom(int(2**16))
                message = data.decode("utf-8")
                dict_msg = ast.literal_eval(message)
                dict_data.update(dict_msg)
            except socket.timeout:
                break
            else:
                pass
    except Exception as e:
        print("Error in MULTICAST send", e, dict_msg, ip, port, message)
        sock.close()
    finally:
        sock.close()
    df_data = pd.DataFrame.from_dict(dict_data, orient='index')
    return df_data



### test ###
if __name__=='__main__':
    d = send(dict_msg={"all":"id"}, ip='224.0.2.0', port=10000, timeout=10, hops=64)
    print(d)
### end test ###

