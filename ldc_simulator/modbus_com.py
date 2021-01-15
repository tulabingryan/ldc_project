#!/usr/bin/python3           
# This is client.py file

import socket
import struct
import time

# Create a TCP/IP socket
TCP_IP = '192.168.1.72'
TCP_PORT = 502
BUFFER_SIZE = 39
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((TCP_IP, TCP_PORT))

while True:
    try:

        unitId = 16
        functionCode = 5
        # print("\n,Switching plug on")
        coilId = 1
        # req = struct.pack('12B', 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, int(unitId), int(functionCode), 0x00, int(coilId),
        #                 0xff,
        #                 0x00)

        req = struct.pack('12B', 
                    0x00, 0x07, 0x00, 0x00, 
                    0x00, 0x06, 0x64, 0x03, 
                    0x03, 0x28, 0x00, 0x0F
                    )
        for x in req[:]:
            print(int(x))
        sock.send(req)
        # print("TX: (%s)" % req)
        response = sock.recv(39)
        
        # for i in range(len(response)):
        #     print(int.from_bytes(response[i:i+1], 'big'))

        print('------------------------')
        time.sleep(2)
    except KeyboardInterrupt:
        break

    # finally:
    #     print('\nCLOSING SOCKET')
    #     sock.close()

    