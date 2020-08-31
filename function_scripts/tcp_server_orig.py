import socket
import sys
import time, datetime
import numpy as np
import pandas as pd
import ast
import sqlite3 as lite

class tcp_server():
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        sock = self.connect()
        self.receive_message(sock)
               

    def connect(self):
        while True:
            try:
                # Create a TCP/IP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # Bind the socket to the port
                server_address = (self.ip, self.port)
                print('starting up on {} port {}'.format(*server_address))
                sock.bind(server_address)

                # Listen for incoming connections
                sock.listen(500)
                break
            except:
                pass
            finally:
                break
       
        return sock


    def receive_message(self, sock):
        while True:
            # Wait for a connection
            print('waiting for a connection')
            connection, client_address = sock.accept()
            try:
                print('connection from', client_address)

                # Receive the data in small chunks and retransmit it
                while True:
                    data = connection.recv(2**16)
                    print('received {!r}'.format(data))
                    if data:
                        connection.sendall(data)
                        
                    else:
                        print('no data from', client_address)
                        break
            except Exception as e:
                print("Error in tcp_server receive_msg:", e)

            finally:
                # Clean up the connection
                connection.close()



if __name__=="__main__":
    while True:
        try:
            S = tcp_server('localhost', 10000)
        except Exception as e:
            pass
        except KeyboardInterrupt:
            break
        
