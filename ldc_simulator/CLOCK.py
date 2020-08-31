import multiprocessing
import pandas as pd
import time

class Clock():
  # global clock
  n = 0
  def __init__(self, dict_data, unixstart, unixend=None, 
    timestep_s=1.0, realtime=True, timezone='Pacific/Auckland'):
    multiprocessing.Process.__init__(self)
    self.daemon = True
    self.name = 'Clock_{}'.format(self.n + 1)
    self.dict_data = dict_data
    self.unixstart = unixstart
    self.unixend = unixend
    self.unixtime = unixstart
    self.timestep_s = timestep_s
    self.realtime = realtime
    self.timezone = timezone
    self.dt = pd.to_datetime(self.unixtime, unit='s').tz_localize('UTC').tz_convert(timezone)
    self.isotime = self.dt.isoformat()
    self.pause = 1e-6
    
    # # run separate threads
    # thread = threading.Thread(target=self.autorun, args=())
    # thread.daemon = True                         # Daemonize thread
    # thread.start()
    

  def step(self):
    # Avance the clock time 
    try:
      if (self.unixend==None) and (self.realtime==True):
        self.unixtime = time.time()
      elif (self.unixend==None) and (self.realtime==False):
        self.unixtime += self.timestep_s
      elif self.unixtime >= self.unixend:
        print("Clock time ended...")
        raise Exception
      else:  # simulated
        self.unixtime += self.timestep_s

      # convert to datetime format
      self.dt = pd.to_datetime(self.unixtime, 
        unit='s').tz_localize('UTC').tz_convert(self.timezone)
      self.isotime = self.dt.isoformat()
      self.dict_data = {**self.dict_data, **dict(zip(["unixtime", 
          "timestep_s", "year", "month", "day", "week", 
          "dayofweek", "hour", "minute", 
          "second", "microsecond", "isotime"], 
          [self.unixtime, self.timestep_s, self.dt.year, 
            self.dt.month, self.dt.day, self.dt.week, 
            self.dt.dayofweek, self.dt.hour, self.dt.minute, 
            self.dt.second, self.dt.microsecond, 
            self.isotime
          ]
          ))}
      
      return (self.unixtime, self.timestep_s, self.dt.year, 
          self.dt.month, self.dt.day, self.dt.week, 
          self.dt.dayofweek, self.dt.hour, self.dt.minute, 
          self.dt.second, self.dt.microsecond, 
          self.isotime)

    except Exception as e:
      print("Error in ", self.name, " step:", e)
        
  def reset(self):
      self.unixtime = self.unixstart

  def report(self):
    print("isoformat:", self.dt.isoformat())
    print("year:", self.dt.year)
    print("month:", self.dt.month)
    print("day:", self.dt.day)
    print("hour:", self.dt.hour)
    print("minute:", self.dt.minute)
    print("second:", self.dt.second)
    print("microsecond:", self.dt.microsecond)
    print("weekday:", self.dt.dayofweek)

  def autorun(self):
    while True:
      try:
        self.step()
        time.sleep(self.pause)
      except KeyboardInterrupt:
        break
      except Exception as e:
        print("Error CLOCK.autorun:{}".format(e))

  def __del__(self):
    print(self.name, "deleted...")


### --- test Clock ---
if __name__ == '__main__':
  import time
  import datetime
  import numpy as np
  import pandas as pd
  # import multiprocessing
  import MULTICAST
  import threading
  C1 = Clock(dict_data={}, unixstart=time.time(), 
            unixend=None, timestep_s=1.0, realtime=True, timezone='Pacific/Auckland')
  while True:
    try:
      unixtime,timestep_s, year, month, day, week, dayofweek, hour, minute, second, microsecond, isotime = C1.step()
      print(unixtime, isotime)
      time.sleep(1)
          
    except KeyboardInterrupt:
      del C1
      break
    except Exception as e:
      print("Error CLOCK.main:{}".format(e))


### end test
