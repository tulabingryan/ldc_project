import os
import sys
import glob
import socket
import numpy as np
import time
import json

# Note: this code requires sshpass
# to install in linux machine: 'sudo apt-get install sshpass'

def get_local_ip(report=False):
    # get local ip address
    count = 0
    local_ip = '127.0.0.1'
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            break
        except Exception as e:
          time.sleep(1)

    if report: print("Local IP:{}".format(local_ip))
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


def sync_folders(from_path='/home/pi/ldc_project/', to_host='pi@192.168.11.120', to_path='/home/pi/ldc_project/', ssh_password="ldc"):
  try:
      cmd = 'sshpass -p "{}" rsync -auhe ssh --progress --exclude-from ".rsync-exluded" --force --delete {} {}:{}'.format(ssh_password, from_path, to_host, to_path) 
      # cmd = 'sshpass -p "{}" rsync -auhe ssh --exclude-from ".rsync-exluded" --delete {} {}:{}'.format(ssh_password, from_path, to_host, to_path) 
      os.system(cmd)      
  except Exception as e:
    print("Error:", e)

def main():
  # dict_config = read_json('/home/pi/ldc_project/config_self.json')
  local_ip = get_local_ip()
  print("local ip:{}".format(local_ip))
  groups = [int(local_ip.split('.')[2])]

  target_hosts = []
  if groups[0] == 11:
    target_hosts = []
    target_hosts.extend(['192.168.{}.{}'.format(x,y) for y in range(100, 128) for x in groups])
  elif groups[0]==1:
    target_hosts.extend(['192.168.1.3'])
  elif groups[0]==10:
    target_hosts.extend(['10.10.10.168'])
  elif groups[0] in [12,13,14,15]:
    target_hosts = []
    groups.extend([14,15])
    groups = np.unique(groups)
    target_hosts.extend(['192.168.{}.{}'.format(x,y) for y in range(100, 114) for x in groups])
  else:
    target_hosts.extend(['192.168.{}.{}'.format(x,y) for y in range(100, 114) for x in groups])
  
  target_hosts.sort()
  
  while True:
    try:
      for h in target_hosts:
        print(f'\n\n{h} sync start...')
        sync_folders(from_path='/home/pi/ldc_project/', to_host='pi@'+h, to_path='/home/pi/ldc_project/', ssh_password="ldc")
        
      break
    except Exception as e:
      print("Error:", e)
    except KeyboardInterrupt:
      break

if __name__ == '__main__':
  main()


