import json
import numpy as np
import pandas as pd
# import multiprocessing
import time, datetime
# from multiprocessing import shared_memory  # error, only available for python 3.8
def main():
	df = pd.DataFrame([])
	df['a'] = np.random.normal(1,0.1,10)
	df['b'] = df['a'] * 100
	df2 = pd.DataFrame.from_dict({'a':np.random.randint(1,10,3)})
	print(df)
	print(df2)
	df.update(df2)
	print(df)
	return
if __name__ == '__main__':
	main()