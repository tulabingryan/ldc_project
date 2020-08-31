import socket
import sys
import time


def contact_server(dict_msg, ip, port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = (ip, port)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)
    
    try:
        # Send data
        message = str(dict_msg).encode()
        print('sending {!r}'.format(message))
        sock.sendall(message)

        # Look for the response
        data = sock.recv(2**16)
        print('received {!r}'.format(data))
        
    finally:
        print('closing socket')
        sock.close()


if __name__=='__main__':
    while  True:
        try:
            algo = input("Algorithm: ")
            loading = input("Loading: ")
            dict_msg = {str(algo): float(loading)}
            contact_server(dict_msg, ip='0.0.0.0', 10000)
        except Exception as e:
            print("Error:", e)
