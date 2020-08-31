import numpy as np
import multiprocessing
import time

class Sample():
	count = 0 

	def __init__(self):
		Sample.count += 1
		self.id = Sample.count
		c = 0
		while True and c < 10:
			print("Alive:", self.id)
			time.sleep(1)
			c += 1

		raise Exception

	def __del__(self):
		print("Dead:", self.id)


def main():
	while True:
		try:
			a = Sample()
		except Exception as e:
			print("Error:", e)
			time.sleep(1)


if __name__ == '__main__':
	main()
