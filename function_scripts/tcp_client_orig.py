import socket
import sys
import time
import multiprocessing
import threading, queue


def tcp_client(ip='localhost', port=10000, msg='urgent message'):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = (ip, port)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)
    
    tref = time.perf_counter()
    try:
        for i in range(10):
            # Send data
            message = msg.encode()
            print('sending {!r}'.format(message))
            sock.sendall(message)

            # Look for the response
            amount_received = 0
            amount_expected = len(message)

            while amount_received < amount_expected:
                data = sock.recv(16)
                amount_received += len(data)
                print('server response: {!r}'.format(data))
            tref_new = time.perf_counter()
            print(tref_new - tref)
            tref = tref_new
    except Exception as e:
        print("Error:", e)

    finally:
        print('closing socket')
        sock.close()


#######################################################
# separate functions for connect and send
def connect(ip='localhost', port=10000):
    while True:
        try:
            # Create a TCP/IP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect the socket to the port where the server is listening
            server_address = (ip, port)
            print('connecting to {} port {}'.format(*server_address))
            sock.connect(server_address)
            break
        except:
            pass
        finally:
            break
   
    return sock


def send_msg(sock, msg='urgent message'):
    tref = time.perf_counter()
    try:
        for i in range(10):
            # Send data
            message = msg.encode()
            print('sending {!r}'.format(message))
            sock.sendall(message)

            # Look for the response
            amount_received = 0
            amount_expected = len(message)

            while amount_received < amount_expected:
                data = sock.recv(16)
                amount_received += len(data)
                print('server response: {!r}'.format(data))
            tref_new = time.perf_counter()
            print(tref_new - tref)
            tref = tref_new
    except Exception as e:
        print("Error:", e)

    finally:
        print('closing socket')
        sock.close()

#####################################################################
# class tcp client
class TcpClient(multiprocessing.Process):
    id = 0
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        
        TcpClient.id += 1
        self.id = str(TcpClient.id)

        print("Client ", self.id, " created.")
        # make connection        
        self.ip = 'localhost'
        self.port = 10000
        
        # run separate threads
        thread = threading.Thread(target=self.step, args=())
        thread.daemon = True                         # Daemonize thread
        thread.start() 

        
    def connect(self):
        return connect(self.ip, self.port)

    def send_msg(self, sock, msg):
        send_msg(sock, msg)
        return
    
    def step(self):
        sock = self.connect()
        self.send_msg(sock, msg=str(self.id) + ": URGENT")
    
    def __del(self):
        print(self.id, " deleted")

#####################################################################

# main call
if __name__=="__main__":
    for i in range(5):
        try:
            c = TcpClient() 
            #sock = connect()
            #send_msg(sock)
            #tcp_client()
        except Exception as e:
            print("Error main:", e)
        finally:
            del c
