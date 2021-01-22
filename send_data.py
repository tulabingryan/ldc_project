import os
import sys
import glob
import socket
import numpy as np
import pandas as pd
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


def compress_pickle(path):
    '''
    Convert feather file to pkl.xz to reduce size 
    '''
    try:
        df_all = pd.read_pickle(f'{path}', compression='infer')
        df_all.to_pickle(f'{path}.xz', compression='infer')
    except Exception as e:
        print("Error compress_pickle:", e)
        


# def join_pickle():
#     '''
#     Convert feather file to pkl.xz to reduce size 
#     '''
#     try:
#         paths_all = glob.glob(f'/home/pi/ldc_project/history/*.pkl')
#         if paths_all:
#             days = np.unique([f"{'_'.join(x.split('_')[:-1])}" for x in paths_all])
#             for day in days:
#                 paths = [x for x in paths_all if x.startswith(day)]
#                 if paths:
#                     df_new = pd.concat([pd.read_pickle(p, compression='infer') for p in paths], axis=0, sort='unixtime')
#                     file = f"{'_'.join(paths[0].split('_')[:-1])}"
#                     df_old = pd.read_pickle(f'{file}.pkl.xz', compression='infer')
#                     df_all = pd.concat([df_old, df_new], axis=0, sort='unixtime')
#                     df_all['unixtime'] = df_all['unixtime'].astype(int)
#                     df_all = df_all.groupby('unixtime').mean().reset_index(drop=False)
#                     df_all.to_pickle(f'{file}.pkl.xz', compression='infer')
#                     [os.remove(p) for p in paths]
                
#     except Exception as e:
#         print("Error compress_pickle:", e)
        

def sync_files(from_path, to_path, remove_source=False, options='-auzhe'):
    '''
    -v, –verbose                             Verbose output
    -q, –quiet                                  suppress message output
    -a, –archive                              archive files and directory while synchronizing ( -a equal to following options -rlptgoD)
    -r, –recursive                           sync files and directories recursively
    -b, –backup                              take the backup during synchronization
    -u, –update                              don’t copy the files from source to destination if destination files are newer
    -l, –links                                   copy symlinks as symlinks during the sync
    -n, –dry-run                             perform a trial run without synchronization
    -e, –rsh=COMMAND            mention the remote shell to use in rsync
    -z, –compress                          compress file data during the transfer
    -h, –human-readable            display the output numbers in a human-readable format
    –progress                                 show the sync progress during transfer
    '''

    try:
        if remove_source:
            os.system(f'sshpass -p "ldc" rsync {options} ssh -T /home/pi --quiet --remove-source-files {from_path} {to_path}') 
        else:
            os.system(f'sshpass -p "ldc" rsync {options} ssh -T /home/pi --quiet --exclude-from ".send_data-exluded" {from_path} {to_path}')
    except Exception as e:
        print("Error:", e, from_path, to_path)

        

def get_local_ip(report=False):
    # get local ip address
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            break
        except Exception as e:
            if report: print(f"{datetime.datetime.now().isoformat()} Error get_local_ip:{e}")
            time.sleep(1)

    if report: 
        print("Local IP:{}".format(local_ip))
    return local_ip

def send_data():
    parser = OptionParser(version=' ')
    parser.add_option('-n', '--now', dest='n', default=0, help='now')
    options, args = parser.parse_args(sys.argv[1:])

    interval = 0.1
    print(f"Sending data logs to server...")
    if not options.n:
        rsync_options = '-avuhe'
    else:
        rsync_options = '-q'

    

    while True:
        try:
            t = time.perf_counter()

            ### send data logs
            files_to_send = glob.glob(f'/home/pi/ldc_project/history/*.pkl.xz')
            files_to_send.sort(key=os.path.getmtime)
            files_to_send = files_to_send[::-1]
            for f in files_to_send[1:]:
                from_path = f
                to_path = f'pi@192.168.1.81:/home/pi/studies/ardmore/temp/{f.split("/")[-1]}'
                sync_files(from_path=from_path, to_path=to_path, 
                    remove_source=True, options=rsync_options)
            
            ### send error logs
            files_to_send = glob.glob(f'/home/pi/ldc_project/logs/*')
            files_to_send.sort(key=os.path.getmtime)
            files_to_send = files_to_send[::-1]
            for f in files_to_send:
                from_path = f
                to_path = f'pi@192.168.1.81:/home/pi/studies/ardmore/logs/{f.split("/")[-1]}'
                sync_files(from_path=from_path, to_path=to_path, 
                    remove_source=True, options=rsync_options)
            

            # local_ip = get_local_ip()  # ensures network connection
            # now = datetime.datetime.now()
            # dt = now.timetuple()
            # today = now.strftime('%Y_%m_%d')
            
            # ### convert 
            # if options.n:
            #     print("sending files now...")
            #     sync_files(dict_paths={
            #         '/home/pi/ldc_project/history/':'pi@192.168.1.81:/home/pi/studies/ardmore/data/',
            #         '/home/pi/ldc_project/logs/':'pi@192.168.1.81:/home/pi/studies/ardmore/logs/',
            #         '/home/pi/ldc_project/ldc_homeserver/history/':'pi@192.168.1.81:/home/pi/studies/ardmore/homeserver/',
            #         }, options='-avuhe', remove_source=False)
            # elif ((dt.tm_hour==23) and (dt.tm_min>=55)):
            #     delete_old('/home/pi/ldc_project/logs/*', n_retain=0)
            #     delete_old('/home/pi/ldc_project/history/*', n_retain=5)
            #     delete_old('/home/pi/ldc_project/ldc_homeserver/history/*', n_retain=5)
            # else:
            #     for p in glob.glob(f'/home/pi/ldc_project/history/*{today}.pkl'):
            #         if last_edit < os.stat(p).st_mtime:
            #             last_edit = os.stat(p).st_mtime
            #             compress_pickle(p)

            #             sync_files(
            #                 dict_paths={
            #                     '/home/pi/ldc_project/history/': 'pi@192.168.1.81:/home/pi/studies/ardmore/data/',
            #                     'pi@192.168.1.81:/home/pi/ldc_project/ldc_gridserver/dict_cmd.txt': '/home/pi/ldc_project/ldc_simulator/dict_cmd.txt',
            #                     },
            #                 remove_source=False)
                        
            #     if now.second%60<1:  # only send every minute
            #         for p in glob.glob(f'/home/pi/ldc_project/logs/*'):
            #             if os.stat(p).st_mtime > (time.time()-60):  ### sync only if updated recently
            #                 sync_files(
            #                     dict_paths={'/home/pi/ldc_project/logs/': 'pi@192.168.1.81:/home/pi/studies/ardmore/logs/'},
            #                     remove_source=False)
            
            #                 if os.stat(p).st_size >= 1e6: # 1MB limit
            #                     os.system(f'sudo rm {p}')
            #                     os.system('sudo reboot')  # reboot the system
                        

                
            # print(time.perf_counter() - t)
            time.sleep(interval)
        except Exception as e:
            print(f"Error send_data: {e}")
            pass
        except KeyboardInterrupt:
            break



if __name__ == '__main__':
    send_data()

