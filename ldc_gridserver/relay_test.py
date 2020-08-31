import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)

relay_pin = 15

GPIO.setup(relay_pin, GPIO.OUT)

def relay(status):
	if status==1 or status==0:
		GPIO.output(relay_pin, status)
	else:
		print("Invalid status... choose in [0,1], 0=OFF, 1=ON")

def main():
	while True:
		status = input("Status:")
		try:
			relay(int(status))
		except Exception as e:
			GPIO.output(relay_pin, 0)
			GPIO.cleanup() 
			print("Error:", e)
		except KeyboardInterrupt:
			GPIO.output(relay_pin, 0)
			GPIO.cleanup() 
			break

if __name__ == '__main__':
	try:
		main()
	except Exception as e:
		print("Error:", e)
		GPIO.output(relay_pin, 0)
		GPIO.cleanup()
	except KeyboardInterrupt:
		GPIO.output(relay_pin, 0)
		GPIO.cleanup()

