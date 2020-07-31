#./update_config.py
import os
import sys
import glob
import socket
import numpy as np
import json
import time, datetime

def get_local_ip():
  # get local ip address
  while True:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.connect(("8.8.8.8", 80))
      local_ip = s.getsockname()[0]
      s.close()
      print("Connection established. local ip:{}".format(local_ip))
      break
    except Exception as e:
      time.sleep(3)
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
  try:
    ### determine local ip address
    local_ip = get_local_ip()
    group = 'h{}'.format(int(local_ip.split('.')[2])%10)
    dev_id = '{}_{}'.format(group, int(local_ip.split('.')[3]))

    if int(local_ip.split('.')[3])==100:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi3", "local_ip": local_ip, 
      "role": "aggregator"}
    elif int(local_ip.split('.')[3])==101:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "meter"}
    elif int(local_ip.split('.')[3])==102:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": ""}
    elif int(local_ip.split('.')[3])==103:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": ""}
    elif int(local_ip.split('.')[3])==104:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "dishwasher"}
    elif int(local_ip.split('.')[3])==105:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "clothesdryer"}
    elif int(local_ip.split('.')[3])==106:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "clotheswasher"}
    elif int(local_ip.split('.')[3])==107:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "batterycharger"}
    elif int(local_ip.split('.')[3])==108:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "evcharger"}
    elif int(local_ip.split('.')[3])==109:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "fridge"}
    elif int(local_ip.split('.')[3])==110:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "freezer"}
    elif int(local_ip.split('.')[3])==111:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "heatpump"}
    elif int(local_ip.split('.')[3])==112:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "waterheater"}
    elif int(local_ip.split('.')[3])==113:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "hotvalve"}
    elif int(local_ip.split('.')[3])==114:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "coldvalve"}
    elif int(local_ip.split('.')[3])==115:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "dumpvalve"}
    elif int(local_ip.split('.')[3])==116:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "humidifier_kitchen_1"}
    elif int(local_ip.split('.')[3])==117:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "humidifier_kitchen_2"}
    elif int(local_ip.split('.')[3])==118:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "window_lounge"}
    elif int(local_ip.split('.')[3])==119:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "window_kitchen"}
    elif int(local_ip.split('.')[3])==120:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "window_bathroom"}
    elif int(local_ip.split('.')[3])==121:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "window_bedroom_master"}
    elif int(local_ip.split('.')[3])==122:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "window_bedroom_1"}
    elif int(local_ip.split('.')[3])==123:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "door_lounge"}
    elif int(local_ip.split('.')[3])==124:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "door_bathroom"}
    elif int(local_ip.split('.')[3])==125:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "door_bedroom_1"}
    elif int(local_ip.split('.')[3])==126:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi3", "local_ip": local_ip, 
      "role": "blinds"}
    elif int(local_ip.split('.')[3])==127:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "humidifier_lounge"}
    elif int(local_ip.split('.')[3])==128:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": "humidifier_bedroom_1"}
    elif int(local_ip.split('.')[3])==3:
      dict_self = {"id":"t1_3", "group":"t1", "hardware":"raspi3", "local_ip":local_ip,
      "role":"signal_injector"}
    elif int(local_ip.split('.')[3])==81:
      dict_self = {"id":"t1_81", "group":"t1", "hardware":"pc", "local_ip":local_ip,
      "role":"gridserver"}
    else:
      dict_self = {"id": dev_id, "group": group, "hardware": "raspi0", "local_ip": local_ip, 
      "role": ""}

    print(dict_self)
    save_json(dict_self, 'config_self.json')

  except Exception as e:
    print("Error MAIN.main:{}".format(e))
      

if __name__ == '__main__':
    main()
