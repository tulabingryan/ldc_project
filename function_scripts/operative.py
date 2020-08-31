import os
import sys
import glob
import socket
import numpy as np
import multiprocessing
import threading, queue
import struct
import ast
import time


def execute(cmd):
    try:
        x = os.system(cmd)
        return x
    except Exception as e:
        print("Error:", e)
        return None


class Operative(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.daemon = True

        self.mcast_ip_local = '224.0.2.0'
        self.mcast_port_local = 17001
        self.receive_mcast()



    def receive_mcast(self):
        # Receive multicast message from the group
        while True:
            try:
                multicast_ip = self.mcast_ip_local
                port = self.mcast_port_local

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
                print(f'Error operative.py mcast setup {e}')
                print('Retrying in 10 seconds')
                time.sleep(10)
            except KeyboardInterrupt:
                break

        # Receive/respond loop
        while True:
            print("Waiting for command to execute...")
            # receive and decode message
            data, address = sock.recvfrom(1024)
            received_msg = data.decode("utf-8")
            dict_msg = ast.literal_eval(received_msg)
            # prepare data to send, fetch latest data from the queue
            try:
                # Note: house name is used as the key, 'all' is a query from the aggregator  
                if list(dict_msg)[0] in ["cmd"]:          
                    cmd = dict_msg['cmd']
                    result = execute(cmd)
                    sock.sendto(str({"issues":result}).encode(), address)
                else:
                    pass

            except Exception as e:
                print("Error in ", self.name, " receive_mcast:", e)
                pass                      
        return






if __name__ == '__main__':
    while True:
        try:
            op = Operative()
        except Exception as e:
            print("Error:", e)
        except KeyboardInterrupt:
            break
