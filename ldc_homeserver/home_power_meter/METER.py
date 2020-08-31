# ./METER.py
# James Ashworth
# University of Auckland
# 26/11/2018



'''Note: install package using 'pip install <package>', e.g., 'pip install numpy'
'''

### ANCILLARY FUNCTIONS TO READ DATA FROM THE POWER METER

# MODBUS-RTU implementation from the energy meters has the following comms parameters:
# 9600baud, 8 data bits, no parity bits, 1 stop bit.


#Set up the comms port and open it.
def comms_init(self):
    energyMeter_serial = serial.Serial(
        port='/dev/ttyUSB0',
        baudrate = 9600,
        bytesize = serial.EIGHTBITS,
        parity = serial.PARITY_NONE,
        stopbits = serial.STOPBITS_ONE,
        timeout = 1
        )
    
    return energyMeter_serial

def crc(data):
    #Calculates the CRC which is appended to the string of hex bytes sent to the energy meter.
    #calculated according to CRC16/MODBUS.
    
    crc = 0xFFFF  #starting CRC value
    crclookup = [0x0000,0xC0C1,0xC181,0x0140,0xC301,0x03C0,0x0280,0xC241,0xC601,0x06C0,0x0780,0xC741,0x0500,0xC5C1,0xC481,0x0440,0xCC01,0x0CC0,0x0D80,0xCD41,0x0F00,0xCFC1,0xCE81,0x0E40,0x0A00,0xCAC1,0xCB81,0x0B40,0xC901,0x09C0,0x0880,0xC841,0xD801,0x18C0,0x1980,0xD941,0x1B00,0xDBC1,0xDA81,0x1A40,0x1E00,0xDEC1,0xDF81,0x1F40,0xDD01,0x1DC0,0x1C80,0xDC41,0x1400,0xD4C1,0xD581,0x1540,0xD701,0x17C0,0x1680,0xD641,0xD201,0x12C0,0x1380,0xD341,0x1100,0xD1C1,0xD081,0x1040,0xF001,0x30C0,0x3180,0xF141,0x3300,0xF3C1,0xF281,0x3240,0x3600,0xF6C1,0xF781,0x3740,0xF501,0x35C0,0x3480,0xF441,0x3C00,0xFCC1,0xFD81,0x3D40,0xFF01,0x3FC0,0x3E80,0xFE41,0xFA01,0x3AC0,0x3B80,0xFB41,0x3900,0xF9C1,0xF881,0x3840,0x2800,0xE8C1,0xE981,0x2940,0xEB01,0x2BC0,0x2A80,0xEA41,0xEE01,0x2EC0,0x2F80,0xEF41,0x2D00,0xEDC1,0xEC81,0x2C40,0xE401,0x24C0,0x2580,0xE541,0x2700,0xE7C1,0xE681,0x2640,0x2200,0xE2C1,0xE381,0x2340,0xE101,0x21C0,0x2080,0xE041,0xA001,0x60C0,0x6180,0xA141,0x6300,0xA3C1,0xA281,0x6240,0x6600,0xA6C1,0xA781,0x6740,0xA501,0x65C0,0x6480,0xA441,0x6C00,0xACC1,0xAD81,0x6D40,0xAF01,0x6FC0,0x6E80,0xAE41,0xAA01,0x6AC0,0x6B80,0xAB41,0x6900,0xA9C1,0xA881,0x6840,0x7800,0xB8C1,0xB981,0x7940,0xBB01,0x7BC0,0x7A80,0xBA41,0xBE01,0x7EC0,0x7F80,0xBF41,0x7D00,0xBDC1,0xBC81,0x7C40,0xB401,0x74C0,0x7580,0xB541,0x7700,0xB7C1,0xB681,0x7640,0x7200,0xB2C1,0xB381,0x7340,0xB101,0x71C0,0x7080,0xB041,0x5000,0x90C1,0x9181,0x5140,0x9301,0x53C0,0x5280,0x9241,0x9601,0x56C0,0x5780,0x9741,0x5500,0x95C1,0x9481,0x5440,0x9C01,0x5CC0,0x5D80,0x9D41,0x5F00,0x9FC1,0x9E81,0x5E40,0x5A00,0x9AC1,0x9B81,0x5B40,0x9901,0x59C0,0x5880,0x9841,0x8801,0x48C0,0x4980,0x8941,0x4B00,0x8BC1,0x8A81,0x4A40,0x4E00,0x8EC1,0x8F81,0x4F40,0x8D01,0x4DC0,0x4C80,0x8C41,0x4400,0x84C1,0x8581,0x4540,0x8701,0x47C0,0x4680,0x8641,0x8201,0x42C0,0x4380,0x8341,0x4100,0x81C1,0x8081,0x4040] 
    
    for a in data:
        lookup_index = (crc ^ a) & 0xFF
        crc = (((crc >> 8) & 0xFF) ^ (crclookup[lookup_index]))
            
    return crc 

def read_frequency(ID):
    request_string = modbus_string_builder(ID, 40305, 1)
    write(request_string)
    
    #surely there's a better way than specifying a number of bytes.
    response = read(7)
    
    #it would probably be good practice at this point to compare the checksums but for the sake of getting this working I'm going to ignore that
    
    #the structure of the return is as follows
    #1. address
    #2. function
    #3. number of bytes to follow
    #4 to #n-2: data
    #n-1, n: checksum
    
    returned_data = response[3:(len(response)-2)]
    rawfreq = int.from_bytes(returned_data, 'big')
    
    freq = rawfreq * 0.01
    
    return freq
    
def read_voltage(ID):
    request_string = build_modbus_string(ID, 40306, 1)
    write(request_string)
    
    response = read(7)
    
    returned_data = response[3:(len(response)-2)]
    rawvolt = int.from_bytes(returned_data, 'big')
    
    voltage = rawvolt * 0.01
    
    return voltage
    
def read_current(ID):
    request_string = build_modbus_string(ID, 40314, 2)
    write(request_string)
    
    response = read(9)
    returned_data = response[3:(len(response)-2)]
    rawcurr = int.from_bytes(returned_data, 'big')
    
    current = rawcurr * 0.001
    
    return current
    
def read_active_power(ID):
    request_string = build_modbus_string(ID, 40321, 2)
    write(request_string)
    
    response = read(9)
    returned_data = response[3:(len(response)-2)]
    rawap = int.from_bytes(returned_data, 'big')
    
    activeppower = rawap * 0.001
    
    return activepower
    
def read_reactive_power(ID):
    request_string = build_modbus_string(ID, 40329, 2)
    write(request_string)
    
    response = read(9)
    returned_data = response
    
    
    return rp
    
def read_apparent_power(ID):
    request_string = build_modbus_string(ID, 40337, 2)

    return power_apparent
    
def read_power_factor(ID):
    request_string = build_modbus_string(ID, 40345, 2)

    return pf
    
def read_active_energy(ID):

    return energy_active
    
def read_reactive_energy(ID):

    return energy_reactive
    
def build_modbus_string(ID, register, bytes_to_read):
    modbus_string = array.array('B')
    
    modbus_string.append(ID)
    modbus_string.append(0x03)
    
    modbus_register = register - 40001
    modbus_string.append(((register >> 8) & 0xFF))
    modbus_string.append((register & 0xFF))
    
    modbus_string.append(((bytes_to_read >> 8) & 0xFF))
    modbus_string.append((bytes_to_read) & 0xFF)
    
    checksum = crc(modbus_string)
    modbus_string.append((checksum) & 0xFF)
    modbus_string.append(((checksum >> 8) & 0xFF))
    
    return modbus_string
    
