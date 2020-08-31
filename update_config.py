#./update_config.py
import os
import sys
import glob
import socket
import numpy as np
import json
import time, datetime
import multiprocessing
import threading, queue
import struct
import ast


def get_local_ip():
    # get local ip address
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            break
        except Exception as e:
            time.sleep(3)
            # print("Error in get_local_ip: ", e)
            pass
        except KeyboardInterrupt:
          break
    return local_ip

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





def main():
    while True:
        try:
            multicast_ip = '224.0.2.0'
            port = 17001

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

    while True:
        try:
            ### read existing config on file
            dict_config_self = read_json('config_self.json')
            #dict_config_all = read_json('config_all.json')

            ### determine local ip address
            local_ip = get_local_ip()
            
            try:
                ### update config
                if dict_config_self["local_ip"] != local_ip: 
                    dict_config_self.update({"local_ip":local_ip})
                    save_json(dict_config_self, 'config_self.json')

                #if dict_config_all[dict_config_self["id"]]["local_ip"] != local_ip:
                #    dict_config_all.update({dict_config_self["id"]:dict_config_self})
                #    save_json(dict_config_all, 'config_all.json')
            except:
                dict_config_self.update({"local_ip":local_ip})
                save_json(dict_config_self, 'config_self.json')
                #dict_config_all.update({dict_config_self["id"]:dict_config_self})
                #save_json(dict_config_all, 'config_all.json')


            # receive query and decode message
            data, address = sock.recvfrom(1024)
            received_msg = data.decode("utf-8")
            dict_msg = ast.literal_eval(received_msg)
            # prepare data to send, fetch latest data from the queue
            try:
                if list(dict_msg)[0] in ["config"]:
                    if dict_msg["config"] in ["all", local_ip]:
                        sock.sendto(str({dict_config_self["id"]:dict_config_self}).encode(), address)

            except Exception as e:
                print("Error in receive_mcast:", e)
                pass                      
        except Exception as e:
            print("Error MAIN.main:{}".format(e))
        except KeyboardInterrupt:
            break
        

if __name__ == '__main__':
    main()
