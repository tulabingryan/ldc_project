# ./smart_meter.py
# James Ashworth, Ryan Tulabing
# University of Auckland
# 26/11/2018


import socket
import struct
import sys
import time, datetime
import json
import ast
import pandas as pd
import serial
import multiprocessing
import threading, queue
import array
import numpy as np

def __generate_crc16_table():
    """ Generates a crc16 lookup table

    .. note:: This will only be generated once
    """
    result = []
    for byte in range(256):
        crc = 0x0000
        for _ in range(8):
            if (byte ^ crc) & 0x0001:
                crc = (crc >> 1) ^ 0xa001
            else: crc >>= 1
            byte >>= 1
        result.append(crc)
    return result



# Set up a class which holds parameters of each energy meter.
class EnergyMeter(multiprocessing.Process):
    ''' Generic Class for an energy meter'''    
    def __init__(self, IDs=[1,2,3], port='/dev/ttyUSB1'):

        multiprocessing.Process.__init__(self)
        self.daemon = True
    

        self.powermeter_ids = IDs
        self.port = port


        # multicasting ip and port
        self.mcast_ip = '224.0.2.0'
        self.mcast_port = 17000

        # initialize dictionary for data
        self.dict_data = {}
        self.dict_registers = {
            'voltage': [40306, 1], 'frequency':[40305, 1], 'current':[40314, 2], 'powerfactor':[40345, 1],
            'power_active':[40321, 2], 'power_reactive':[40329, 2], 'power_apparent':[40337, 2], 
            'energy_active':[((440961 - 400001) + 40001), 2], 'energy_reactive':[((440991 - 400001) + 40001), 2],
            }
   
        self.dict_modbus = self.create_query_dictionary()

        self.q_data = queue.Queue(maxsize=3)  # data can only be passed in different threads using queue
        
        # run separate threads
        thread = threading.Thread(target=self.respond_to_query, args=())
        thread.daemon = True                         # Daemonize thread
        thread.start() 

        self.step()  # run step function to read meter data and store in queue

    def connect_serial(self):
        port='/dev/ttyUSB1'
        ser = serial.Serial(
            port=port,
            baudrate = 9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout = 0.2
            )
            
        return ser

    
    def get_meter_data(self, params=['voltage', 'current', 'powerfactor', 'frequency',
        'power_active', 'power_reactive', 'power_apparent', 'energy_active', 'energy_reactive']):
        # read power meter, update dict_data, and put into q_data

        self.dict_data.update({
                "unixtime":time.time(),
                # "localtime":datetime.datetime.now().isoformat(),                
            })


        for param in params:
            dict_reading = self.read_meter(param) #self.read_voltage()
            for _id in self.powermeter_ids:
                self.dict_data['{}_{}'.format(param, _id)] = dict_reading[_id] 

            if param=='power_active':
                self.dict_data['power_sum'] = 0
                for _id in self.powermeter_ids:
                    self.dict_data['power_sum'] += self.dict_data['{}_{}'.format(param, _id)]
            else:
                pass


        print(self.dict_data)
        # put on the queue
        while self.q_data.empty() is False:
            self.q_data.get() # empty all of past data
            self.q_data.task_done()  # release lock
        self.q_data.put(self.dict_data) # put data on queue

        return self.dict_data



    def respond_to_query(self):
        # Receive query and send dict_data as a response (running as a separate thread)
        multicast_ip = self.mcast_ip
        port = self.mcast_port

        multicast_group = (multicast_ip, port)  # (ip_address, port)

        # Create the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind to the server address
        sock.bind(multicast_group)

        # Tell the operating system to add the socket to
        # the multicast group on all interfaces.
        group = socket.inet_aton(multicast_ip)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            mreq)
        
        dict_toSend = {}
        
        # Receive/respond loop
        while True:
            # receive and decode message
            data, address = sock.recvfrom(1024)
            received_msg = data.decode("utf-8")
            dict_msg = ast.literal_eval(received_msg)
            # prepare data to send, fetch latest data from the queue
            try:
                if list(dict_msg)[0] in ['power']:
                    # fetch latest data on queue        
                    while self.q_data.empty() is False:
                        dict_onQueue = self.q_data.get()
                        self.q_data.task_done()
                    self.q_data.put(dict_onQueue)  # return latest data on queue to avoid empty queue
                    
                    dict_toSend.update(dict_onQueue)
                    message_toSend = str(dict_toSend).encode('utf-8')
                    # send message
                    sock.sendto(message_toSend, address)

                else:
                    pass
                
            except Exception as e:
                print("Error respond_to_query:", e)
                
        return


    def step(self):
        # continually read meter data and store into queue
        while True:
            try:
                self.get_meter_data(params=['voltage', 'energy_active'])
                # time.sleep(0.5)
                
            except Exception as e:
                print("Error in step:", e)
                self.__del__()
                                
### CODE MODIFICATIONS HERE, updating the energyMeter class with the functions I already have written - James
#2/12/18    

#the structure of the return is as follows
        #1. address
        #2. function
        #3. number of bytes to follow
        #4 to #n-2: data
        #n-1, n: checksum
    
        #unless for whatever reason a modbus exception code is generated, which I would need to handle in some way.
        #the exception messages always contain 5 bytes, and are formatted:
            #1. address
            #2. function with the most significant bit switched to 1 (for function 0x03, returns 0x83)
            #3. exception code
            #4, 5. CRC
        #this code has been written in such a way that an exception code should never be generated.
        
#theoretically nothing should cause the energy meter to send something with an incorrect checksum - however, if noise is introduced it could corrupt the data packets (actually have observed this, but strangely enough only in the read_active_power() function.
    
    def read_meter(self, param='power_active'):
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            attempt = 0
            response = []
            while len(response) < 1 and attempt < 20:
                ser.write(self.dict_modbus['{}_{}'.format(param, _id)])
                response = ser.read(7 + (2*(self.dict_registers[param][1]-1)))
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
            
            if param in ['frequency', 'voltage', 'energy_active', 'energy_reactive']:
                factor = 0.01
            else:
                factor = 0.001

            if self.check_valid_response(response):
                data = response[3:-2]
                value = int.from_bytes(data, 'big') * factor
                dict_data[_id] = value
                
            else:
                print("invalid frequency:", _id, attempt, response)
                pass

        return dict_data


    def read_frequency(self):
        # read frequency
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            request_string = self.create_modbus_query(40305, 1, _id)
            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                # ser.reset_input_buffer()
                response = ser.read(7)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
                
            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                rawfreq = int.from_bytes(returned_data, 'big')
                freq = rawfreq * 0.01
                dict_data[_id] = freq
                
            else:
                print("invalid frequency:", _id, attempt, response)
                pass

        return dict_data

                
    def read_voltage(self):
        #read voltage (V)
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            request_string = self.create_modbus_query(40306, 1, _id)

            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                response = ser.read(7)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
            
            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                rawvolt = int.from_bytes(returned_data, 'big')
                dict_data[_id] = rawvolt * 0.01
                
            else:
                print("invalid voltage:", _id)
                pass
        return dict_data  
            
        
    def read_current(self):
        #read current (A)
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            request_string = self.create_modbus_query(40314, 2, _id)
            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                # ser.reset_input_buffer()
                response = ser.read(9)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
            
            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                rawcurr = int.from_bytes(returned_data, 'big')
                dict_data[_id] = rawcurr * 0.001
                
            else:
                print("invalid current:", _id)
                pass
        return dict_data
                
                
    def read_powerfactor(self):
        #read powerfactor (const.)
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            request_string = self.create_modbus_query(40345, 1, _id)
            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                # ser.reset_input_buffer()
                response = ser.read(7)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
            
            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                raw_pf = int.from_bytes(returned_data, 'big')
                dict_data[_id] = raw_pf * 0.001
                
            else:
                print("invalid powerfactor:", _id)
                pass
        return dict_data
    

        
    def read_power_active(self):
        #read active power (kW)
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            request_string = self.create_modbus_query(40321, 2, _id)
            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                # ser.reset_input_buffer()
                response = ser.read(9)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
            
            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                rawap = int.from_bytes(returned_data, 'big')
                dict_data[_id] = rawap * 0.001
                
            else:
                print("invalid power_active:", _id)
                pass

        return dict_data
                
                
    
    def read_power_reactive(self):
        #read reactive power (kVAr)
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            request_string = self.create_modbus_query(40329, 2, _id)
            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                # ser.reset_input_buffer()
                response = ser.read(9)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
            
            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                rawrp = int.from_bytes(returned_data, 'big')
                dict_data[_id] = rawrp * 0.001
                
            else:
                print("invalid power_reactive:", _id)
                pass
        return dict_data
            


    def read_power_apparent(self):
        #read apparent power (kVA)
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            request_string = self.create_modbus_query(40337, 2, _id)
            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                # ser.reset_input_buffer()
                response = ser.read(9)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
            
            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                raw_power_apparent = int.from_bytes(returned_data, 'big')
                dict_data[_id] = raw_power_apparent * 0.001
                
            else:
                print("invalid power_apparent:", _id)
                pass

        return dict_data
                    

    def read_energy_active(self):
        #read active energy (kWhr)
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            reg, btr = self.dict_registers['energy_active']
            request_string = self.create_modbus_query(reg, btr, _id)
            
            
            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                # ser.reset_input_buffer()
                response = ser.read(9)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()
            
            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                raw_ea = int.from_bytes(returned_data, 'big')
                dict_data[_id] = raw_ea * 0.01 
                
            else:
                print("invalid energy_active:", _id)
                pass
        return dict_data
                
            
    def read_energy_reactive(self):
        #read reactive energy (kVArhr)
        ser = self.connect_serial()
        dict_data = {}
        for _id in self.powermeter_ids:
            request_string = self.create_modbus_query(((440991 - 400001) + 40001), 2, _id)
            attempt = 0
            # ser.reset_output_buffer()
            response = []
            while len(response)<1 and attempt < 10:
                ser.write(request_string)
                # ser.reset_input_buffer()
                response = ser.read(9)
                attempt += 1

                ser.flushInput()
                ser.flushOutput()

            if self.check_valid_response(response):
                returned_data = response[3:(len(response)-2)]
                raw_er = int.from_bytes(returned_data, 'big')
                dict_data[_id] = raw_er * 0.01
                
            else:
                print("invalid energy_reactive:", _id)
                pass
        
        return dict_data


    
         

    def check_valid_response(self, response):
        #check that the response received from the energy meter is valid - all read_() functions call this: 
        valid = 0
        
        if(len(response) == 5):
            #it generated an exception code, so not a response we want
            valid = 0
            # print("MODBUS exception code generated: ", response[2])
            # for i in range(0,len(response)):
            #    print(response[i])
        else:
            checksum = self.crc(response[0:-2])
            checksum_string = array.array('B')
            checksum_string.append((checksum & 0xFF))
            checksum_string.append(((checksum >> 8) & 0xFF))
            calculated_checksum_val = int.from_bytes(checksum_string, 'big')
        
            sent_checksum_val = int.from_bytes(response[-2:], 'big')
            
            if (sent_checksum_val == calculated_checksum_val):
                valid = 1
            else:
                valid = 0
                # print("Invalid data...:", response, sent_checksum_val, calculated_checksum_val)
        
        return valid
        
        
    def create_modbus_query(self, register, bytes_to_read, _id=1):
        modbus_string = array.array('B')
	
        modbus_string.append(_id)
        modbus_string.append(0x03)
        
        modbus_register = register - 40001
        modbus_string.append(((modbus_register >> 8) & 0xFF))

        modbus_string.append((modbus_register & 0xFF))
	
        modbus_string.append(((bytes_to_read >> 8) & 0xFF))
        modbus_string.append((bytes_to_read) & 0xFF)
	
        checksum = self.crc(modbus_string)
        modbus_string.append((checksum) & 0xFF)
        modbus_string.append(((checksum >> 8) & 0xFF))
	
        return modbus_string


    def create_query_dictionary(self, params=['voltage', 'current', 'powerfactor', 'frequency',
        'power_active', 'power_reactive', 'power_apparent', 'energy_active', 'energy_reactive']):
        dict_modbus = {}
        for param in params:
            reg, btr = self.dict_registers[param]
            for _id in self.powermeter_ids:
                    dict_modbus['{}_{}'.format(param, _id)] = self.create_modbus_query(register=reg , bytes_to_read=btr, _id=_id)
    
        return dict_modbus


            
    
    def crc(self, data):
        #Calculates the CRC which is appended to the string of hex bytes sent to the energy meter.
        #calculated according to CRC16/MODBUS.
        crc = 0xFFFF  #starting CRC value
        crclookup = [0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 
                    0x0280, 0xC241, 0xC601, 0x06C0, 0x0780, 0xC741, 
                    0x0500, 0xC5C1, 0xC481, 0x0440, 0xCC01, 0x0CC0,
                    0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40, 
                    0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 
                    0x0880, 0xC841, 0xD801, 0x18C0, 0x1980, 0xD941,
                    0x1B00, 0xDBC1, 0xDA81, 0x1A40, 0x1E00, 0xDEC1,
                    0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
                    0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 
                    0x1680, 0xD641, 0xD201, 0x12C0, 0x1380, 0xD341,
                    0x1100, 0xD1C1, 0xD081, 0x1040, 0xF001, 0x30C0,
                    0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
                    0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0,
                    0x3480, 0xF441, 0x3C00, 0xFCC1, 0xFD81, 0x3D40,
                    0xFF01, 0x3FC0, 0x3E80, 0xFE41, 0xFA01, 0x3AC0,
                    0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840, 
                    0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0,
                    0x2A80, 0xEA41, 0xEE01, 0x2EC0, 0x2F80, 0xEF41,
                    0x2D00, 0xEDC1, 0xEC81, 0x2C40, 0xE401, 0x24C0,
                    0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
                    0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0,
                    0x2080, 0xE041, 0xA001, 0x60C0, 0x6180, 0xA141, 
                    0x6300, 0xA3C1, 0xA281, 0x6240, 0x6600, 0xA6C1, 
                    0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441, 
                    0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0,
                    0x6E80, 0xAE41, 0xAA01, 0x6AC0, 0x6B80, 0xAB41,
                    0x6900, 0xA9C1, 0xA881, 0x6840, 0x7800, 0xB8C1,
                    0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
                    0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1,
                    0xBC81, 0x7C40, 0xB401, 0x74C0, 0x7580, 0xB541,
                    0x7700, 0xB7C1, 0xB681, 0x7640, 0x7200, 0xB2C1,
                    0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
                    0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0,
                    0x5280, 0x9241, 0x9601, 0x56C0, 0x5780, 0x9741,
                    0x5500, 0x95C1, 0x9481, 0x5440, 0x9C01, 0x5CC0,
                    0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
                    0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0,
                    0x5880, 0x9841, 0x8801, 0x48C0, 0x4980, 0x8941,
                    0x4B00, 0x8BC1, 0x8A81, 0x4A40, 0x4E00, 0x8EC1,
                    0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
                    0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0,
                    0x4680, 0x8641, 0x8201, 0x42C0, 0x4380, 0x8341,
                    0x4100,0x81C1,0x8081,0x4040] 
    
        for a in data:
            lookup_index = (crc ^ a) & 0xFF
            crc = (((crc >> 8) & 0xFF) ^ (crclookup[lookup_index]))

        return crc

   

        
    def __del__(self):
        # run the following upon destroying this object
        print("Destroying ", self.powermeter_ids)


if __name__ == '__main__':
    while True:
        try:
            # create class instance
            __crc16_table = __generate_crc16_table()

        
            EM1 = EnergyMeter(IDs=[1,2,3], port='/dev/ttyUSB1')
            # EM2 = EnergyMeter(IDs=[2], port='/dev/ttyUSB1')
            # EM3 = EnergyMeter(IDs=[3], port='/dev/ttyUSB1')

            
        except Exception as e:
            print("Error main:",e)
        except KeyboardInterrupt:
            break
    
