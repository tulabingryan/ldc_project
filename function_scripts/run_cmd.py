import os
import time
import json
import socket


def execute(cmd):
    try:
        x = os.system(cmd)
        return x
    except Exception as e:
        print("Error:", e)
        return None

def get_local_ip(report=False):
    # get local ip address
    count = 0
    local_ip = '127.0.0.1'
    while local_ip=='127.0.0.1':
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception as e:
            # print("Error in FUNCTIONS get_local_ip: ", e)
            pass
    if report: print("Local IP:{}".format(local_ip))
    return local_ip


if __name__ == '__main__':
    ### continuously check for a command to be executed
    ### command is saved in cmd.json
    local_ip = get_local_ip()
    print("LocalIp:", local_ip)
    cmd_path = './cmd.json'
    local_cmd = {"cmd":"None", "requested":"2020-01-31T13:33:0", "confirmed":"pending"}
    while True:
        try:
            if os.path.exists(cmd_path): 
                # read file
                with open(cmd_path, 'r') as f:
                    data=f.read()

                # parse file
                json_cmd = json.loads(data)

                # process global command
                online_cmd = json_cmd["all"]
                # if online_cmd["cmd"]!="None"

                # if online_cmd!="Pending":
                #     continue
                # else:
                #     local_cmd.update(online_cmd)
                #     result = execute(json_cmd['cmd'])
                #     with open(cmd_path, 'w') as f:
                #         json.dump(json_cmd, f)
            
                time.sleep(1)
                
            else:
                time.sleep(1)
        except Exception as e:
            print(e)
            pass
        except KeyboardInterrupt:
            break


