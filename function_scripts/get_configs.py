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


def send_cmd(dict_msg, ip='224.0.2.0', port=17001, timeout=5, hops=3):
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



def save_json(json_data, filename):
    # save json_data in filename
    with open(filename, 'w') as outfile:  
        json.dump(json_data, outfile)
    print("{}: {} saved...".format(datetime.datetime.now().isoformat(), filename))
    return filename

def read_json(filename):
    # read file as json
    with open(filename) as json_file:  
        data = json.load(json_file)
    return data




if __name__ == '__main__':
    dict_data = {}
    while True:
        try:
            dict_msg = {"config":"all"}
            dict_data = read_json('/home/pi/ldc_project/config_all.json')
            dict_data.update(send_cmd(dict_msg=dict_msg))
            save_json(dict_data, '/home/pi/ldc_project/config_all.json')
            for k in dict_data:
                print(dict_data[k])
            time.sleep(1)
            break
        except Exception as e:
            print("Error main:", e)
        except KeyboardInterrupt:
            break
