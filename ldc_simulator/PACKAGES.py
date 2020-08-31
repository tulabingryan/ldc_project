#---import python packages---
from optparse import OptionParser
import sys, os
from scipy.interpolate import interp1d
import json
import math
import numpy as np
import pandas as pd
import datetime, time
import threading, queue, multiprocessing
import itertools
# for multicast
import socket, struct, sys, json, ast
import MULTICAST

# #---import local modules---
import FUNCTIONS
from WEATHER import Weather
from CLOCK import Clock
import solar


raspi0 = False
raspi3 = False
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    ### for reading ldc signal
    import spidev
    raspi0 = True
except:
    pass

try:
    ### for piface driver, in grainy load raspi3
    import pifacedigitalio
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    raspi3 = True
except:
    pass
