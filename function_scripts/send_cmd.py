import socket
import os
import time


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




if __name__ == '__main__':
    while True:
        try:
            print("\n---------------------------------------------------------------")
            print("Send command to peer device via ssh.")
            local_ip = get_local_ip(report=True)
            target = input("\nTarget IP: ")
            cmd = input("Command: ")
            
            if target:
                peers = target.split(',') 
            else:
                subnet = '.'.join(local_ip.split('.')[:-1])
                if subnet.endswith('.11'):
                    limit = 130
                else:
                    limit = 114
                peers = [f'{subnet}.{x}' for x in range(100, limit)]

            for p in peers:
                print(f'\n{p}')
                os.system(f'sshpass -p "ldc" ssh pi@{p} {cmd}')

        except Exception as e:
            print("Error main:", e)
        except KeyboardInterrupt:
            break
