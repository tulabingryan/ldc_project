'''SPI interface: PSOC and Raspi zero'''

import RPi.GPIO as GPIO
import time
import sys

GPIO.setmode(GPIO.BOARD)  # use the board numbering of pins
CLK = 23
MISO = 21
MOSI = 19
CS = 24

def setup_SPI_pins(clkPin, misoPin, mosiPin, csPin):
	'''Set all pins as an output except MISO'''
	GPIO.setup(clkPin, GPIO.OUT)
	GPIO.setup(misoPin, GPIO.IN)
	GPIO.setup(mosiPin, GPIO.OUT)
	GPIO.setup(csPin, GPIO.OUT)

def read_SPI(channel, clkPin, misoPin, mosiPin, csPin):
	if (channel < 0) or (channel > 7):
		print("Invalid channel, must be between [0,7]")
		return -1

	# Enable csPin
	GPIO.output(csPin, GPIO.HIGH)

	# Start reading
	GPIO.output(csPin, GPIO.LOW)
	GPIO.output(clkPin, GPIO.HIGH)

	# read command is
	# start bit = 1
	# single-ended comparison = 1
	# channel number bit 2
	# channel number bit 1
	# channel number bit 0 (LSB)
	read_command = 0x18
	read_command |= channel

	send_bits(read_command, 5, clkPin, mosiPin)

	value = receive_bits(8, clkPin, misoPin)

	# set cs HIGH to end reading
	GPIO.output(csPin, GPIO.HIGH)

	return value


def send_bits(data, numBits, clkPin, mosiPin):
	''' Send 1 byte or less of data'''
	data <<= (8 - numBits)

	for bit in range(numBits):
		# Set RPi's output bit high or low depending on highest bit of data field
		if data & 0x80:
			GPIO.output(mosiPin, GPIO.HIGH)
		else:
			GPIO.output(mosiPin, GPIO.LOW)

		# Advance data to the next bit
		data <<= 1

		# Pulse the clock pin HIGH then LOW
		GPIO.output(clkPin, GPIO.HIGH)
		GPIO.output(clkPin, GPIO.LOW)

def receive_bits(numBits, clkPin, misoPin):
	''' Receive bits'''
	retVal = 0
	counter = 0
	null_bits = 0
	for bit in range(numBits):
		counter += 1
		# Pulse clock Pin
		GPIO.output(clkPin, GPIO.HIGH)
		GPIO.output(clkPin, GPIO.LOW)
		if counter > null_bits:
			# Read 1 data bit
			if GPIO.input(misoPin):
				retVal |= 0x1

			# Advance input to next bit
			retVal <<= 1
		else:
			pass
	# Divide by two to drop the NULL bit
	return (retVal)

def reverse_bits(byte):
	''' Reverse bits for LSB and MSB'''
	byte = ((byte & 0xF0) >> 4) | ((byte & 0x0F) << 4)
	byte = ((byte & 0xCC) >> 2) | ((byte & 0x33) << 2)
	byte = ((byte & 0xAA) >> 1) | ((byte & 0x55) << 1)
	return byte

if __name__=='__main__':
	try:
		setup_SPI_pins(CLK, MISO, MOSI, CS)

		while True:
			val = read_SPI(0, CLK, MISO, MOSI, CS)
			rval = reverse_bits(val)
			print("Result:", str(val), str(rval))
			time.sleep(1)

	except KeyboardInterrupt:
		GPIO.cleanup()
		sys.exit(0)



