import spidev
import time



def reverse_bits(byte):
    '''Change order of LSB to MSB'''
    byte = ((byte & 0xF0) >> 4) | ((byte & 0xF0) << 4)
    byte = ((byte & 0xCC) >> 2) | ((byte & 0x33) << 2)
    byte = ((byte & 0xAA) >> 1) | ((byte & 0x55) << 1)
    return byte




def read_spi():
    try:
        '''Initialize spi settings'''
        spi = spidev.SpiDev()
        bus = 0
        device = 0
        spi.open(bus, device)
        spi.bits_per_word = 8
        spi.max_speed_hz = 500000
        spi.mode = 3
        # read spi
        r = spi.readbytes(n_bytes)
        return r[0]
    except Exception as e:
        print("Error read_spi:", e)
        return None




if __name__=='__main__':
    while True:
        try:
        
            r = read_spi()
            #val = reverse_bits(r[0])
            print('pyLDC:',r[0])
            time.sleep(0)
        except KeyboardInterrupt:
            spi.close()
            break

