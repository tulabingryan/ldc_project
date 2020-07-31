import RPi.GPIO as GPIO
import time

def setup_gpio(inputs=[], outputs=[15]):
    # setup the raspi gpio
    try:
        GPIO.setmode(GPIO.BOARD)     # set up BOARD GPIO numbering  

        for x in inputs:
            GPIO.setup(int(x), GPIO.IN)

        for y in outputs:
            GPIO.setup(int(y), GPIO.OUT)

        print("Input channels:", inputs)
        print("Output channels:", outputs)

    except:
        pass

    return


def gpio_out(pin=15, state=0):
    # Output signal to gpio
    try:
        GPIO.output(pin, state)
    except:
        pass
    return 


if __name__=="__main__":

	while True:
		try:

			test_mode = input("Test mode [0: relay,    1: 4pins,   2: 1pin]:")
			test_mode = int(test_mode)

			if test_mode==0:
				setup_gpio(inputs=[], outputs=[15])
				state = input("State [0,1]: ")

				try:
					if int(state) in [0, 1]:
						hold = input("Hold for (seconds): ")
						hold = float(hold)
						gpio_out(pin=15, state=int(state))
						time.sleep(hold)
						gpio_out(pin=15, state=0)
					else:
						print("Invalid state")
						raise Exception
				except Exception as e:
					print("Error:", e)

			elif test_mode==1:
				setup_gpio(inputs=[], outputs=[32, 36, 38, 40])
				state = input("Input state (0,1) for [32, 36, 38, 40], separate by ',': ")
				states = state.split(',')
				
				try:
					state_list = [int(s) for s in states]

					if len(state_list)==4:
						hold = input("Hold for (seconds): ")
						hold = float(hold)
						GPIO.output([32,36,38,40], state_list)  # first LOW, second HIGH
						time.sleep(hold)
						GPIO.output([32,36,38,40], GPIO.LOW) # all LOW
					else:
						print("Invalid state")
						raise Exception
				except Exception as e:
					print("Error:", e)


			elif test_mode==2:
				pin = input("Choose pin [32,36,38,40]: ")
				pin = int(pin)
				setup_gpio(inputs=[], outputs=list(pin))
				state = input("State [0,1]: ")
				try:
					if int(state) in [0, 1]:
						hold = input("Hold for (seconds): ")
						hold = float(hold)
						gpio_out(pin=pin, state=state)
						time.sleep(hold)
						gpio_out(pin=pin, state=0)

					else:
						print("Invalid state")
						raise Exception
				except Exception as e:
					print("Error:", e)


			else:
				print("Invalid mode. Please enter 0 for 'relay',  1 for '4pins', 2 for '1pin'.")
		except Exception as e:
			print("Error main:", e)

		finally:
			GPIO.cleanup() # clean up the GPIO to reset mode
        
