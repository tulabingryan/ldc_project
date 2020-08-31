import numpy as np
import pandas as pd
import socket
import MULTICAST



def get_data(dict_msg, db_name='./ldc_all.db', mcast_ip="224.0.2.3", mcast_port=16003, report=False):
    # define timeout
    if dict_msg[list(dict_msg)[0]]["unixstart"]==0:
        tm = 1
    else:
        tm = 10
    # get data from database
    dict_data = MULTICAST.send(dict_msg, ip=mcast_ip, port=mcast_port, timeout=tm)
    df_data = pd.DataFrame.from_dict(dict_data, orient='index').reset_index(drop=True)
    # try:
    #     df_data = pd.melt(df_data, id_vars=["unixtime", "id"], var_name="parameter", value_name="value")
    #     df_data = df_data.dropna()
    # except:
    #     pass
    if report: print(df_data)
    return df_data



def read_csv(filename, failed=True):
    # Continually try reading csv until successful
    while True:
        try:
            df = pd.read_csv(filename)
            break
        except Exception as e:
            print("Error read_csv:", e)
    return df


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
    return local_ip


#############################################################
# local_ip = get_local_ip()
# subnet = int(local_ip.split('.')[2])
# df_housespecs = read_csv('./houseSpecs.csv')
# house_name = df_housespecs.loc[subnet-1, 'name']
# mcast_ip = df_housespecs.loc[subnet-1, 'ip_local']
# mcast_port = df_housespecs.loc[subnet-1, 'port_local']


# dict_cmd = {'LXX001':{'status':1, 'priority':0, 'schedule':{}, 'can_shed':0, 'can_ramp':0, 'unixstart':0, 'unixend':0}}

# df_data = get_data(dict_msg=dict_cmd, 
#     db_name='./ldc_all.db', mcast_ip=mcast_ip, mcast_port=int(mcast_port), report=False)

# print(df_data['id'])
# print(list(df_data))
############################################################

