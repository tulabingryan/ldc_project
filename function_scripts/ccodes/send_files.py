import os
import sys
import glob
import socket
import numpy as np

# Note: this code requires sshpass
# to install in linux machine: 'sudo apt-get install sshpass'

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
            print("Error in get_local_ip: ", e)
            pass
        except KeyboardInterrupt:
          break
    return local_ip


def get_file_list():
  return glob.glob('*.*')
  
def get_ip_list():
  local_ip = get_local_ip()
  subnet = local_ip.split('.')[2]
  ip_list = []
  for i in range(100,113):
    ip_list.append('192.168.'+str(subnet)+'.' + str(i))

  return ip_list

def get_directory():
  cwd = os.getcwd().split('/')
  for i in range(len(cwd)):
    if cwd[i]=='ldc_project':
      dir_list = cwd[i:]
    else:
      pass
  directory = '/home/pi/'
  for d in dir_list:
    directory = directory + str(d) + '/'

  return directory



def send_files(file_list, ip_list, directory):
  try:
    file_string = ''
    for f in file_list:
      file_string = file_string + str(f) + ' '

    for address in ip_list:
      cmd = 'sshpass -p "raspberry" scp ' + file_string + ' pi@'+address + ":" + directory
      try:
          os.system(cmd) 
          print("files sent to ", address)
      except Exception as e:
          raise e

  except Exception as e:
    print("Error:", e)



def main():
  try:
    list_files = get_file_list()
    list_ip = get_ip_list()
    directory = get_directory()
    print(list_files, list_ip, directory)
    send_files(file_list=list_files, ip_list=list_ip, directory=directory)
  except Exception as e:
    print("Error:", e)





if __name__ == '__main__':
  main()
