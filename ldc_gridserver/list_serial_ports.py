import sys
import glob
import serial
import serial.tools.list_ports

# def serial_ports():
#     """ Lists serial port names

#         :raises EnvironmentError:
#             On unsupported or unknown platforms
#         :returns:
#             A list of the serial ports available on the system
#     """
#     if sys.platform.startswith('win'):
#         ports = ['COM%s' % (i + 1) for i in range(256)]
#     elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
#         # this excludes your current terminal "/dev/tty"
#         ports = glob.glob('/dev/tty[A-Za-z]*')
#     elif sys.platform.startswith('darwin'):
#         ports = glob.glob('/dev/tty.*')
#     else:
#         raise EnvironmentError('Unsupported platform')

#     result = []
#     for port in ports:
#         try:
#             s = serial.Serial(port)
#             s.close()
#             result.append(port)
#         except (OSError, serial.SerialException):
#             pass
#     return result


def get_ports(report=False):

    ports = serial.tools.list_ports.comports()
    dict_ports = {}
    for port, desc, hwid in sorted(ports):
            # print("{}:_{}_{}".format(port, desc, hwid))
            try:
                hardware_id = hwid.split(':')[1]
                dict_ports[port] = hardware_id
            except:
                pass
    if report: print(dict_ports)

    return dict_ports



if __name__ == '__main__':
    # print(serial_ports())
    get_ports()

