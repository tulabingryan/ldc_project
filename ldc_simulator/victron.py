#usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 14 14:37:31 2019
@author: pi
"""

import time
import serial



ser = serial.Serial(
    port='/dev/ttyS0',
    baudrate = 19200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
    )



cs = {
    0: 'Not charging',
    2: 'Fault',
    3: 'Bulk',
    4: 'Absorption',
    5: 'Float'
    }



err = {
    0: 'No error',
    2: 'Battery voltage too high',
    3: 'Remote temperature sensor failure',
    4: 'Remote temperature sensor failure',
    5: 'Remote temperature sensor failure (connection lost)',
    6: 'Remote battery voltage sense failure',
    7: 'Remote battery voltage sense failure',
    8: 'Remote battery voltage sense failure (connection lost)',
    17: 'Charger temperature too high',
    18: 'Charger over current',
    19: 'Charger current reversed',
    20: 'Bulk time limit exceeded',
    21: 'Current sensor issue (sensor bias/sensor broken)',
    26: 'Terminals overheated',
    28: 'Power stage issue',
    33: 'Input voltage too high (solar panel)',
    34: 'Input current too high (solar panel)',
    38: 'Input shutdown (due to excessive battery voltage)',
    39: 'Input shutdown',
    65: '[Info] Communication warning',
    66: '[Info] Incompatible device',
    67: 'BMS Connection lost',
    114: 'CPU temperature too high',
    116: 'Factory calibration data lost',
    117: 'Invalid/incompatible firmware',
    119: 'User settings invalid'
    }



mppt = {
    0: 'Off',
    1: 'Voltage or current limited',
    2: 'MPP Tracker active'
    }



def converter(packet,conv):
    try:
        if conv == "cs":
            return cs[int(packet)]

        if conv == "err":
            return err[int(packet)]

        if conv == "mppt":
            return mppt[int(packet)]

    except:
        print("[!] Unrecognised value type of",conv,":",packet)
        return packet



def ve_parser(parse_line, item):
    try:
        parse_str = parse_line.decode("utf-8")
        parse_failed = False
    except:
        print("[!] Cannot decode this:",parse_line,"\n Skipping to next line...")
        parse_failed = True

    if parse_failed:
        print("Parse failed!")
        temp=1

    #= Asynchronous message =#
    elif ":A" in parse_str:
        print("Asynchronous message")

    #= Product ID =#
    elif "PID" in parse_str and item == "PID":
        parse_str = parse_str.split("\t")
        packet = parse_str[1]
        #print("PID: {0}".format(packet))
        return packet

    #= Firmware Version =#
    elif "FW" in parse_str and item == "FW":
        parse_str = parse_str.split("\t")
        packet = parse_str[1]
        print("FW: {0}".format(packet))
        return packet

    #= Serial number =#
    elif "SER" in parse_str and item == "SER":
        parse_str = parse_str.split("\t")
        packet = parse_str[1]
        print("Serial number: {0}".format(packet))
        return packet

    #= Battery voltage =#
    elif "V" in parse_str and "P" not in parse_str and item == "V": #For VPV and PPV cases
        parse_str = parse_str.split("\t")
        packet = round(float(parse_str[1]) * 0.001,2)
        print("Battery voltage: {0}V".format(packet))
        print("Battery voltage: %.1fV" % packet)
        print("Battery voltage: {0:.2f}V".format(packet))
        return packet

    #= Current =#
    elif "I" in parse_str and "P" not in parse_str and item == "I": #For PID cases
        parse_str = parse_str.split("\t")
        packet = round(float(parse_str[1]) * 0.001,2)
        print("Battery charge current: {0}A".format(packet))
        return packet

    #= PV Voltage =#
    elif "VPV" in parse_str and item == "VPV":
        parse_str = parse_str.split("\t")
        packet = round(float(parse_str[1]) * 0.001,2)
        print("Panel voltage: {0}V".format(packet))
        return packet

    #= PV Power =#
    elif "PPV" in parse_str and item == "PPV":
        parse_str = parse_str.split("\t")
        packet = int(parse_str[1])
        print("Panel power: {0}W".format(packet))
        return packet

    #= State of operation =#
    elif "CS" in parse_str and item == "CS":
        parse_str = parse_str.split("\t")
        packet = converter(int(parse_str[1]),"cs")
        print("Charge State: {0}".format(packet))
        return packet

    #= Tracker operation mode =#
    elif "MPPT" in parse_str and item == "MPPT":
        parse_str = parse_str.split("\t")
        packet = converter(int(parse_str[1]),"mppt")
        print("MPPT: {0}".format(packet))
        return packet

    #= Error code =#
    elif "ERR" in parse_str and item == "ERR":
        parse_str = parse_str.split("\t")
        packet = converter(int(parse_str[1]),"err")
        packet = int(parse_str[1])
        print("Error: {0}".format(packet))
        return packet

    #= Load otput state (ON/OFF) =#
    elif "LOAD" in parse_str and item == "LOAD":
        parse_str = parse_str.split("\t")
        packet = (parse_str[1])
        print("LOAD: {0}".format(packet))
        return packet

    #= Yield total =#
    elif "H19" in parse_str and item == "H19":
        parse_str = parse_str.split("\t")
        packet = round(float(parse_str[1]) * 0.01,2)
        print("Yield total: {0}".format(packet))
        return packet

    #= Yield today =#
    elif "H20" in parse_str and item == "H20":
        parse_str = parse_str.split("\t")
        packet = round(float(parse_str[1]) * 0.01,2)
        print("Yield today: {0}".format(packet))
        return packet

    #= Maximum power today =#
    elif "H21" in parse_str and item == "H21":
        parse_str = parse_str.split("\t")
        packet = round(float(parse_str[1]),2)
        print("Maximum power today: {0}".format(packet))
        return packet

    #= Yield yesterday =#
    elif "H22" in parse_str and item == "H22":
        parse_str = parse_str.split("\t")
        packet = round(float(parse_str[1]) * 0.01,2)
        print("Yield yesterady: {0}".format(packet))
        return packet

    #= Maximum power yesterday =#
    elif "H23" in parse_str and item == "H23":
        parse_str = parse_str.split("\t")
        packet = round(float(parse_str[1]),2)
        print("Maximum power yesterday: {0}".format(packet))
        return packet

    #= Day sequence number (0..364) =#
    elif "HSDS" in parse_str and item == "HSDS":
        parse_str = parse_str.split("\t")
        packet = int(parse_str[1])
        print("Day sequence number: {0}".format(packet))
        return packet

    #= Checksum =#
    elif "Checksum" in parse_str:
        print("Checksum identified.")
        time.sleep(1)



    #= Maximum power yesterday =#
    elif "Relay" in parse_str and item == "REL":
        parse_str = parse_str.split("\t")
        packet = parse_str[1]
        print("Relay status: {0}".format(packet))
        return packet

    #= NULL =#
    else:
        print("[!] Unrecognised data:",parse_line)
        return None



battery_voltage = None
charge_current = None
panel_power = None
yield_total = None
error_code = None

try:
    while True: #remove this if you want only once to read
        read_data = ser.readline()
        print(read_data) #This one prints line as sent from mppt
        if battery_voltage is None:
            battery_voltage = ve_parser(read_data,"V")

        if not battery_voltage is None:
            print(battery_voltage)

        if charge_current is None:
            charge_current = ve_parser(read_data,"I")

        if not charge_current is None:
            print(charge_current)

        if panel_power is None:
            panel_power = ve_parser(read_data,"PPV")
        if not panel_power is None:
            print(panel_power)

        if yield_total is None:
            yield_total = ve_parser(read_data,"H19")
        if not yield_total is None:
            print(yield_total)

        if error_code is None:
            error_code = ve_parser(read_data,"ERR")
        if not error_code is None:
            print("Error: ",error_code)

except KeyboardInterrupt:
    print ("Program stopped by keyboard interrupt [CTRL_C] by user. ")
