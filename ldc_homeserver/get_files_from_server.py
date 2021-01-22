import os, sys, glob
import numpy as np
import pandas as pd
import time, datetime



def get_files(from_path='pi@192.168.1.81:/home/pi/studies/ardmore/data', to_path='/home/pi/studies/ardmore/data'):
    os.system(f'sshpass -p "ldc" rsync -avuhe ssh -T /home/pi {from_path} {to_path}')
    return
    

if __name__=='__main__':
    while True:
        try:
            get_files()
            time.sleep(0.5)
        except Exception as e:
            print(f"Error:{e}")
        except KeyboardInterrupt:
            break