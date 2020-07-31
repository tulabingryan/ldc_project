import os
import sys
import glob
import socket
import numpy as np
import time, datetime
from optparse import OptionParser
# Note: this code requires sshpass
# to install in linux machine: 'sudo apt-get install sshpass'



def get_file_list(path='*.*'):
  return glob.glob(path)

  
def delete_old(path='*.*', n_retain=1):
  files = get_file_list(path)
  files.sort(key=os.path.getmtime)
  files = files[::-1]
  
  old_files = files[n_retain:]
  for f in old_files:
    cmd = 'sudo rm {}'.format(f)
    os.system(cmd)


def sync_files(dict_paths={
  '/home/pi/ldc_project/history/':'pi@192.168.1.81:/home/pi/studies/ardmore/data/',
  '/home/pi/ldc_project/logs/':'pi@192.168.1.81:/home/pi/studies/ardmore/logs/',
  }, remove_source=False):
  
  try:
    for from_path in dict_paths:
      to_path = dict_paths[from_path]
      if remove_source:
        cmd = 'sshpass -p "ldc" rsync -avuzhe ssh --remove-source-files {} {}'.format(from_path, to_path) 
        os.system(cmd) 
      else:
        cmd = 'sshpass -p "ldc" rsync -avuzhe ssh {} {}'.format(from_path, to_path) 
        os.system(cmd) 
  except Exception as e:
    print("Error:", e)
    raise e
      

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

def main():
  parser = OptionParser(version=' ')
  parser.add_option('-n', '--n', dest='n', default=0, help='now')
  options, args = parser.parse_args(sys.argv[1:])
  while True:
    try:
      local_ip = get_local_ip()  # ensures network connection
      dt = datetime.datetime.now().timetuple()
      if options.n:
        print("sending files now...")
        sync_files(dict_paths={
          '/home/pi/ldc_project/history/':'pi@192.168.1.81:/home/pi/studies/ardmore/data/',
          '/home/pi/ldc_project/logs/':'pi@192.168.1.81:/home/pi/studies/ardmore/logs/',
          '/home/pi/ldc_project/ldc_homeserver/history/':'/home/pi/studies/ardmore/homeserver/',
          },remove_source=False)
      elif ((dt.tm_hour==23) and (dt.tm_min>=55)):
        delete_old('/home/pi/ldc_project/logs/*', n_retain=0)
        delete_old('/home/pi/ldc_project/history/*', n_retain=5)
      else:
        sync_files(remove_source=False)
        sync_files(dict_paths={
          'pi@192.168.1.81:/home/pi/ldc_project/ldc_gridserver/dict_cmd.txt':'/home/pi/ldc_project/ldc_simulator/dict_cmd.txt',
          }, remove_source=False)
        sync_files(dict_paths={
          'pi@192.168.1.81:/home/pi/ldc_project/ldc_simulator/':'/home/pi/ldc_project/ldc_simulator/',
          }, remove_source=False)
        # sync_files(dict_paths={
        #   '/home/pi/ldc_project/ldc_homeserver/history/':'pi@192.168.1.81:/home/pi/studies/ardmore/homeserver/',
        #   }, remove_source=False)

      time.sleep(300)
    except Exception as e:
      print("Error:", e)
      break
    except KeyboardInterrupt:
      break



if __name__ == '__main__':
  main()

