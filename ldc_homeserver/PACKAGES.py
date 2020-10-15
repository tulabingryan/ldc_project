import base64
import random
import time, datetime
import pandas as pd
import numpy as np
import sqlite3 as lite
import os, glob
import uuid
import re

import socket
import struct
import sys
import time
import json
import ast
import socket

import flask
import math
import dash
import dash_daq as daq
from dash.dependencies import ClientsideFunction, Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
# import dash_auth
# from flask_caching import Cache
# from pandas_datareader.data import DataReader

import MULTICAST

import plotly.express as px
# color_set = px.colors.qualitative.Set1
# color_set = px.colors.qualitative.Plotly
color_set = px.colors.qualitative.D3  # default for Dash
# color_set = px.colors.qualitative.G10
# color_set = px.colors.qualitative.T10
# color_set = px.colors.qualitative.Alphabet

### other color sets
# Dark24, Light24, Pastel1, Dark2, Set2, Pastel2, Set3,
# Antique, Bold, Pastel, Prism, Safe, Vivid


def save_json(json_data, filename):
    # save json_data in filename
    with open(filename, 'w') as outfile:  
        json.dump(json_data, outfile)

    return filename

def read_json(filename):
    # read file as json
    with open(filename) as json_file:  
        data = json.load(json_file)
    
    return data

def get_timezone(latitude,longitude,timestamp,report=False):
    """ Determines the timezone based on 
    location specified by the latitude and longitude """
    global timezone

    url = 'https://maps.googleapis.com/maps/api/timezone/json?location='\
            + str(latitude) + ',' + str(longitude) + '&timestamp='\
            + str(timestamp) + '&key=' + 'AIzaSyDHLF0LGjAd9mm0vLmqQfrQuuIjVVHla2k'
    req = Request(url)

    success = False
    attempts = 0
    while not(success) and (attempts<=10):
        try:
            response = urlopen(req)
            respData = response.read()
            response.close()

            respData = respData.decode("utf-8")
            data = json.loads(respData)

            if data['timeZoneId']:
                timezone = data['timeZoneId']  # get timezone
                
                if report:
                    print("latitude: "+ latitude)
                    print("longitude: "+ longitude)
                    print ("timezone: "+ timezone)

                # adjust timezone setting used for runtime
                os.environ['TZ'] = timezone
                time.tzset()
                success = True
                return timezone
            else:
                print("No results... retrying...")
                return None
                
        except HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
        except URLError as e:
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        else:
            print("Unknown Error")  # everything is fine



def get_local_ip():
    # get local ip address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip

    except Exception as e:
        print("Error in get_local_ip: ", e)



def get_logo():
    image = "./UOA.png"
    encoded_image = base64.b64encode(open(image, "rb").read())
    logo = html.Div(
                html.Img( src="data:image/png;base64,{}".format(encoded_image.decode()), 
                    height="57"
                    ),
                style={"marginTop": "0", "float":"left", "backgroundColor": "#18252E"},
                # className="sept columns",
            )
    return logo

