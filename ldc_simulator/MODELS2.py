"""
./MODELS.py 
Module for LDC System Models
Author: Ryan Tulabing
Project: Local Demand Control
Institution: University of Auckland
Year: 2017 - 2020

Generic model:

               _________________Se_________________ 
              |                                    |
   __________   A1   ___|/____   A2   __________        _____|_________
  |  Dongle  |----->| Device |----->|  End-use |  Se  |  Environment |
  |__________|<-----|________|<-----|__________|<-----|______________|
     /|        S1     |  /|      S2    |    /|                |
    |A0           S4|   |A4        S3|/____|A3              |
   ___|_______       _|/__|____      | Person |               |
  |  LDC     |  S5  |  Local  |      |________|               |
  | Injector |<-----|  Grid   |<------------------------------|
   ----------        ---------     Se

Definitions:
LDC Injector = LDC signal injector
  A0 = LDC signal (750-850Hz)
Dongle = LDC ldc_dongles to control the loads
  A1 = Action, approval of proposed demand
  S1 = State of the device, e.g., priority, mode, etc.
Device = Load appliance, e.g., heatpump, waterheater, etc.
  A2 = Action of the device, e.g., provide heat, cool freezer, etc.
  S2 = State of the end-use, e.g., room temp, freezer temp, job status, soc, etc.
End-use = End-usage application, room to heat, dishes to wash, laundry to dry
  A3 = Action of users, e.g., schedules, water usage, other settings, etc.
  S3 = State of the end-usage, e.g., temperature, soc, 
Person = person that creates schedules and settings for end-uses
Local Grid = local power grid
  A4 = Action of the grid, e.g., voltage, frequency
  S4 = State of the device, e.g., power demand, 
  S5 = state of the grid, e.g., aggregated demand, voltage, frequency, 
Environment = Weather environment, e.g, outside temperature, humidity, solar, wind
  Se = state of the environment, e.g., outside temp, solar, windspeed, humidity


"The worthwhile problems are the ones you can really solve or help solve, 
    the ones you can really contribute something to. 
    No problem is too small or too trivial 
    if we can really do something about it."
-Richard P. Feynman, Nobel Prize, Physics
"""


from PACKAGES import * 


######## helper functions #################
def save_json(json_data, filename):
  # save json_data in filename
  with open(filename, 'w') as outfile:  
    json.dump(json_data, outfile)
    print("{}: {} saved...".format(datetime.datetime.now().isoformat(), filename))
  return filename

def read_json(filename):
  # read file as json
  with open(filename) as json_file:  
    data = json.load(json_file)
  return data
  

def add_demands(baseload=0, heatpump=0, heater=0, waterheater=0, fridge=0, freezer=0, 
  clotheswasher=0, clothesdryer=0, dishwasher=0, solar=0, wind=0):
  return np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(np.add(baseload, 
    heatpump), heater), waterheater), fridge), freezer), clotheswasher), clothesdryer), 
    dishwasher), solar), wind)

def setup_gpio(inputs=[], outputs=[15, 32, 36, 38, 40]):
  # setup the raspi gpio
  try:
    for x in inputs: GPIO.setup(int(x), GPIO.IN)
    for y in outputs: GPIO.setup(int(y), GPIO.OUT)
  except:
    pass

def execute_state(newstate, device_id, report=False):
  dict_state = {0:'CLOSED', 1:'OPEN'}
  if newstate not in [0,1]:
    print("Invalid input...")
  else:
    if device_id in [123, 124, 125]: 
      s = (not newstate)*1  # logic for doors is reversed
    else:
      s = newstate

    if s==GPIO.input(32): 
      # if report: print('Unit already in that state')
      pass
    else:
      if device_id in [118, 119, 120, 121, 122, 123, 124, 125]:
        GPIO.output([15, 32, 36, 38, 40], [1, s, s, s, s])
        
        if report: print('Changing state, please wait...')
        
        ### turn off relay after 30s for windows and doors
        time.sleep(30)
        GPIO.output([15, 32, 36, 38, 40], [0, s, s, s, s])

        
        if report: print('{} state changed to:{}'.format(device_id, dict_state[newstate]))
      else:
          GPIO.output([15, 32, 36, 38, 40], [s, s, s, s, s])
      

def normalize(value, a_min=40, a_max=80, expected_max=100):
  return np.add(a_min, np.multiply(np.divide(value, expected_max), np.subtract(a_max, a_min)))

######## model for environment #################


def clock(unixtime, realtime=True, step_size=1):
  # return next timestamp and stepsize
  if realtime:
    timestamp = time.time()
    step_size = np.subtract(timestamp, unixtime)
  else:
    timestamp = np.mean(np.add(unixtime, step_size))
  dt = pd.to_datetime(timestamp, unit='s').tz_localize('UTC').tz_convert('Pacific/Auckland')
  return (timestamp, step_size, dt.year, dt.month, dt.day,  dt.week, dt.dayofweek, 
    dt.hour, dt.minute, dt.second, dt.microsecond, dt.isoformat())

def weather(unixtime):
  return  

######## model for grid #################





################ models for end-uses ###################################################
def enduse_tcl(heat_all, air_part, temp_in, temp_mat, temp_out, Um, Ua, Cp, Ca, Cm, 
  mass_flow, step_size, unixtime, connected):
  # update temp_in and temp_mat, and temp_in_active, i.e., for connected tcls
  count = np.zeros(len(step_size))
  increment = np.clip(step_size, a_min=1e-1, a_max=0.5)
  while np.mean(count) < np.mean(step_size):
    # for air temp
    temp_in = np.add(temp_in, 
      np.multiply(np.divide(np.subtract(np.subtract(np.subtract(np.multiply(heat_all, air_part), 
      np.multiply(np.subtract(temp_in, temp_mat), Um)), 
      np.multiply(np.subtract(temp_in, temp_out), Ua)), 
      np.multiply(np.subtract(temp_in, temp_out), np.multiply(mass_flow, Cp))), Ca), increment ))
    # for material temp
    temp_mat = np.add(temp_mat, np.multiply(np.divide(np.subtract(np.multiply(heat_all, 
      np.subtract(1, air_part)), np.multiply(np.subtract(temp_mat, temp_in), Um)), Cm), increment))
    count = np.add(count, increment)
  temp_in_active = np.divide(temp_in, connected)
  return temp_in, temp_mat, temp_in_active, np.add(unixtime, count)

# def enduse_storage(soc, power, capacity, step_size):
#   # update soc
#   return np.divide(np.add(np.multiply(power, step_size), 
#     np.multiply(soc, capacity)), capacity)  # soc

def enduse_ev(soc, target_soc, a_demand, capacity, connected, unixtime, step_size):
  # update soc
  soc = np.divide(np.add(np.multiply(a_demand, step_size), 
    np.multiply(soc, capacity)), capacity)  # new soc [ratio] 
  progress = np.divide(soc, target_soc)
  unfinished = np.multiply(progress, (progress<1) * 1)  # unfinished tasks
  finished = (progress>=1) * 1  # finished tasks
  progress = np.abs(np.multiply(np.add(unfinished, finished), connected))
  return (unfinished, finished, progress, soc, unixtime+step_size)  # progress, unixtime

def enduse_storage(soc, target_soc, a_demand, capacity, connected, unixtime, step_size):
  # update soc
  soc = np.divide(np.add(np.multiply(a_demand, step_size), 
    np.multiply(soc, capacity)), capacity)  # new soc [ratio] 
  progress = np.divide(soc, target_soc)
  unfinished = np.multiply(progress, (progress<1) * 1)  # unfinished tasks
  finished = (progress>=1) * 1  # finished tasks
  progress = np.abs(np.multiply(np.add(unfinished, finished), connected))
  return (unfinished, finished, progress, soc, unixtime+step_size)  # progress, unixtime


def enduse_ntcl(len_profile, progress, step_size, a_status, unixtime, connected):
  # update job status
  progress = np.multiply(np.add(progress, np.divide(step_size, len_profile)), a_status)
  unfinished = np.multiply(progress, (progress<1) * 1)  # unfinished tasks
  finished = (progress>=1) * 1  # finished tasks
  progress = np.abs(np.multiply(np.add(unfinished, finished), connected))
  return unfinished, finished, progress, np.add(unixtime,step_size)  # progress, unixtime


############# models for devices #######################################################
def device_cooling(mode, temp_in, temp_min, temp_max, a_status, a_demand, cooling_setpoint, 
  tolerance, cooling_power, cop, standby_power, ventilation_power):
  # device model for freezer, fridge, air condition
  try:
    p_status = ((((temp_in>=np.subtract(cooling_setpoint, tolerance)) & (a_status==1)) 
      | ((temp_in>=np.add(cooling_setpoint, tolerance))&(a_status==0)))&(mode==0)) * 1
    p_demand =  np.multiply(np.multiply(p_status, cooling_power), ((mode==0)*1))
    flexible_horizon = np.subtract(temp_max, temp_in)
    operation_horizon = np.subtract(temp_max, temp_min)
    priority = np.multiply(np.multiply(np.divide(flexible_horizon, operation_horizon), 100), ((mode==0)*1)) 
    cooling_power_thermal = np.multiply(np.multiply(np.multiply(cop, cooling_power), a_status), 
      ((mode==0)*1)) * -1
    a_demand = np.multiply(np.add(np.add(np.multiply(a_status, cooling_power), standby_power), 
      ventilation_power), ((mode==0)*1))
    return (p_status, p_demand, normalize(priority), cooling_power_thermal, 
      np.add(a_demand, np.random.normal(1, 0.01, len(a_demand))))
  except Exception as e:
    print("Error MODELS.device_cooling:{}".format(e))
    return

def device_heating(mode, temp_in, temp_min, temp_max, a_status, a_demand, heating_setpoint, 
  tolerance, heating_power, cop, standby_power, ventilation_power):
  # device model for water heaters, electric heaters, etc.
  try:
    p_status = ((((temp_in<=np.add(heating_setpoint, tolerance))&(a_status==1)) 
      |  ((temp_in<=np.subtract(heating_setpoint, tolerance))&(a_status==0)))&(mode==1)) * 1
    p_demand = np.multiply(np.multiply(p_status, heating_power), ((mode==1)*1))
    flexible_horizon = np.subtract(temp_in, temp_min)
    operation_horizon = np.subtract(temp_max, temp_min)
    priority = np.multiply(np.multiply(np.divide(flexible_horizon, operation_horizon), 100), ((mode==1)*1))
    heating_power_thermal = np.multiply(np.multiply(cop, heating_power), a_status)*((mode==1)*1)
    a_demand = np.add(np.add(np.multiply(a_status, heating_power), standby_power), 
      ventilation_power)*((mode==1)*1) 
    return (p_status, p_demand, normalize(priority), heating_power_thermal, 
        np.add(a_demand, np.random.normal(1, 0.01, len(a_demand))))
  except Exception as e:
    print("Error MODELS.device_heating:{}".format(e))
    return

def device_tcl(mode, temp_in, temp_out, temp_min, temp_max, priority, a_status, a_demand, p_status, 
  p_demand, cooling_setpoint, heating_setpoint, tolerance, cooling_power, heating_power, cop, 
  standby_power, ventilation_power, cooling_power_thermal, heating_power_thermal):
  try:
    ### determine mode
    lowerbound_cooling = np.subtract(cooling_setpoint, tolerance)
    mode = ((np.subtract(temp_max, temp_in) > 0)&(heating_setpoint>temp_out)) * 1

    ### set proposed demand
    c = device_cooling(mode=mode, temp_in=temp_in, temp_min=temp_min, temp_max=temp_max, 
      a_status=a_status, a_demand=a_demand, cooling_setpoint=cooling_setpoint, 
      tolerance=tolerance, cooling_power=cooling_power, cop=cop,
      standby_power=standby_power, ventilation_power=ventilation_power)

    h = device_heating(mode=mode, temp_in=temp_in, temp_min=temp_min, temp_max=temp_max, 
      a_status=a_status, a_demand=a_demand, heating_setpoint=heating_setpoint, 
      tolerance=tolerance, heating_power=heating_power, cop=cop, 
      standby_power=standby_power, ventilation_power=ventilation_power)

    p_status = np.add(c[0], h[0]) 
    p_demand = np.add(c[1], h[1]) 
    priority = np.add(c[2], h[2])
    heating_power_thermal = h[3]
    cooling_power_thermal = c[3]
    a_demand = np.add(c[4], h[4])

    return (mode, p_status, p_demand, priority, cooling_power_thermal, 
      heating_power_thermal, a_demand)
  except Exception as e:
    print("Error MODELS.device_tcl:{}".format(e))
    return


def device_battery(unixtime, unixstart, unixend, soc, charging_power, target_soc, capacity,
  connected, progress, a_status, a_demand):
  ''' 
  Generic model of Battery-based loads
  Inputs:
    unixtime = current timestamp
    unixstart = earliest timestamp to start the device
    unixend = latest timestamp to finish the job
    connected = signifies if the device is connected, i.e., unixstart <= unixtime < unixend
    progress = status of the job, i.e., range 0..1, 
    a_status = approved status, 1=job is start, 0=delayed
    p_demand = proposed demand for the next time step
    a_demand = proposed demand in the previous timestep
  Outputs:
    p_status = proposed status for the next timestep
    flexibility = capability of the device to be delayed in starting
    priority = priority of the device based on its flexibility, 
              used as decision variable for the ldc_dongles
    p_demand = proposed demand for the next timestep
    a_demand = actual demand based on the previous p_demand and previous a_status
  '''
  p_status = ((progress<1)&(connected>0))*1
  p_demand = np.divide(charging_power, np.e**(np.multiply((soc>=0.9)*1, 
    np.subtract(np.multiply(soc, 100), 90))))  # mathematical model
  p_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
    soc), capacity), p_demand))
  flexibility = np.divide(np.subtract(unixend, p_finish), np.subtract(unixend, unixstart))
  priority = normalize(flexibility * 100)
  a_demand = np.multiply(np.multiply(a_status, a_demand), (progress<1)*1)
  return p_status, flexibility, priority, p_finish, p_demand, a_demand 
    # p_status, flexibility, priority, p_demand, a_demand (NOTE: a_demand uses the p_demand and a_status of the previous timestep)



def device_charger_ev(unixtime, unixstart, unixend, soc, charging_power, target_soc, capacity,
  connected, progress, a_status, p_demand, a_demand):
  '''
  Input states:
    Model for EV charger
    unixtime = current timestamp
    unixstart = timestamp for earliest start
    unixend = timestamp for latest end
    soc = state of charge [ratio]
    charging_power = charger power rating [w]
    target_soc = user-defined target soc [ratio]
    capacity = storage capacity [J or watt*s]
  Output actions:
    p_status = proposed status
    flexibility = ldc flexibility
    priority = ldc priority
    p_finish = predicted time of finish
    p_demand = proposed demand
    a_demand = actual demand

  Charging time for 100 km of BEV range   Power supply    power   Voltage     Max. current
  6–8 hours                               Single phase    3.3 kW  230 V AC        16 A
  3–4 hours                               Single phase    7.4 kW  230 V AC        32 A
  2–3 hours                               Three phase     11 kW   400 V AC        16 A
  1–2 hours                               Three phase     22 kW   400 V AC        32 A
  20–30 minutes                           Three phase     43 kW   400 V AC        63 A
  20–30 minutes                           Direct current  50 kW   400–500 V DC    100–125 A
  10 minutes                              Direct current  120 kW  300–500 V DC    300–350 A
  '''
  ### get p_status
  p_status = ((unixstart<=unixtime) & (unixend>=unixtime)) * 1
  ### get p_demand
  # p_demand = np.divide(charging_power, np.e**(np.multiply((soc>=0.9)*1, 
  #   np.subtract(np.multiply(soc, 100), 90))))  # mathematical model
  p_demand = p_demand  # model based on numpy.linalg.interp1d 
  ### predict finish
  p_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
    soc), capacity), p_demand))
  ### get flexibility
  flexibility = np.clip((np.divide(np.subtract(unixend, p_finish), 
      np.subtract(unixend, unixstart))-0.1), a_min=0.0, a_max=1.0)
  ### get priority
  priority = normalize(flexibility * 100 )
  ### actual demand based on previous p_demand and a_status
  a_demand = np.multiply(np.multiply(a_status, a_demand), (progress<1)*1)
  return p_status, flexibility, priority, p_finish, p_demand, a_demand

def device_charger_storage(unixtime, unixstart, unixend, soc, charging_power, target_soc, capacity,
  connected, progress, a_status, p_demand, a_demand):
  '''
  Input states:
    Model for battery charger
    unixtime = current timestamp
    unixstart = timestamp for earliest start
    unixend = timestamp for latest end
    soc = state of charge [ratio]
    charging_power = charger power rating [w]
    target_soc = user-defined target soc [ratio]
    capacity = storage capacity [J or watt*s]
  Output actions:
    p_status = proposed status
    flexibility = ldc flexibility
    priority = ldc priority
    p_finish = predicted time of finish
    p_demand = proposed demand
    a_demand = actual demand
  '''
  ### get p_status
  p_status = ((unixstart<=unixtime) & (unixend>=unixtime))*1
  ### get p_demand
  p_demand = np.divide(charging_power, np.power(np.e, (np.multiply((soc>=0.9)*1, np.subtract(np.multiply(soc, 100), 90)))))  # mathematical model
  ### predict finish
  p_finish = np.add(unixtime, np.divide(np.multiply(np.subtract(target_soc, 
    soc), capacity), p_demand))
  ### get flexibility
  flexibility = np.clip((np.divide(np.subtract(unixend, p_finish), 
      np.subtract(unixend, unixstart))-0.1), a_min=0.0, a_max=1.0)
  ### get priority
  priority = normalize(flexibility * 100)
  ### actual demand based on previous p_demand and a_status
  a_demand = np.multiply(np.multiply(a_status, a_demand), (progress<1)*1)
  return p_status, flexibility, priority, p_finish, p_demand.flatten(), a_demand.flatten()


def device_ntcl(len_profile, unixtime, unixstart, unixend, connected, progress, 
  a_status, p_demand, a_demand):
  ''' 
  Generic model of Non-TCL loads that are based on a power profile
  Inputs:
    len_profile = length of the load profile in seconds
    unixtime = current timestamp
    unixstart = earliest timestamp to start the device
    unixend = latest timestamp to finish the job
    connected = signifies if the device is connected, i.e., unixstart <= unixtime < unixend
    progress = status of the job, i.e., range 0..1, 
    a_status = approved status, 1=job is start, 0=delayed
    p_demand = proposed demand for the next time step
    a_demand = proposed demand in the previous timestep
  Outputs:
    p_status = proposed status for the next timestep
    flexibility = capability of the device to be delayed in starting
    priority = priority of the device based on its flexibility, used as decision variable for the ldc_dongles
    p_demand = proposed demand for the next timestep
    a_demand = actual demand based on the previous p_demand and previous a_status
  '''
  p_status = ((progress<1)&(connected>0))*1 
  p_finish = np.add(np.multiply(np.subtract(np.ones(progress.shape), progress), 
    len_profile), unixtime)
  flexibility = np.clip((np.divide(np.subtract(unixend, p_finish), 
      (np.subtract(unixend, unixstart)))), a_min=0, a_max=1.0)
  priority = normalize(np.multiply(flexibility, 100))
  a_demand = np.multiply(np.multiply(a_status, a_demand), (progress<1)*1)
  return (p_status, flexibility, priority, p_demand, a_demand )
    # p_status, flexibility, priority, p_demand, a_demand (NOTE: a_demand uses the p_demand and a_status of the previous timestep)

def device_wind(windspeed, capacity, speed_cut_in, speed_cut_off):
  
  return 

######## models for ldc #################
def ldc_injector(signal, latest_power, target_power, step_size):
  '''
  Model for LDC signal injector
  Inputs:
    signal = the last injected signal, range 0...100
    latest_power = latest power reading
    target_power = target power demand for the the local grid
    step_size = time elapsed since the last signal was sent
  Outputs:
    signal = updated signal value
  '''
  offset = np.divide(np.subtract(target_power, latest_power), target_power)
  signal = np.clip(np.add(signal, np.multiply(offset, np.multiply(step_size, 1e0))),a_min=0.01, a_max=100.0)
  return signal


def ldc_dongle(priority, signal, p_status, with_dr):
  '''
  MOdel for the LDC dongle controllers
  Inputs:
    priority = priority number of the devices
    signal = ldc signal from the injector
    p_status = proposed status of the devices
    with_dr
  Outputs:
    a_status = approved status of the devices
  '''   
  return np.multiply(p_status, ((priority<=signal)|np.invert(with_dr))*1).flatten()  # a_status

def adjust_setpoint(a_status, mode, old_setpoint, upper_limit, lower_limit):
  '''Adjust the setpoint
  Inputs:
    a_status = approved status from the function ldc_dongle
    mode = 0 for cooling, 1 for heating
    old_setpoint = current setpoint
    upper_limit = max allowable setpoint
    lower_limit = min allowable setpoint
  Outputs:
    new_setpoint
  '''
  ### decrease heating temp
  heating_decrease = np.multiply(np.subtract(old_setpoint, 0.5), np.multiply(((mode==1)*1), ((a_status==0)*1)))
  heating_normal = np.multiply(old_setpoint, np.multiply(((mode==1)*1), ((a_status==1)*1)))
  ### increase cooling temp
  cooling_increased = np.multiply(np.add(old_setpoint, 0.5), np.multiply(((mode==0)*1), ((a_status==0)*1)))
  cooling_normal = np.multiply(old_setpoint, np.multiply(((mode==0)*1), ((a_status==1)*1)))

  return np.clip(np.add(cooling_normal, np.add(cooling_increased, 
                np.add(heating_decrease, heating_normal))), 
                a_min=lower_limit, a_max=upper_limit)

######## model for person #################
# from numba import jit
# @jit(nopython=True)
def make_schedule(unixtime, current_task, load_type_id, unixstart, unixend):
  '''
  Make task schedules for different loads
  Inputs:
    unixtime = current timestamp
    current_task = array of floats where the integer part denotes the type of load while the decimal denots the duration in seconds
    load_type = integer code denoting the type of load
  Outputs:
    unixstart = timestamp of earliest start of the load
    unixend = timestatmp of the latest end of the load
  '''
  try:
    tasks = np.floor(current_task)
    duration = np.multiply(np.subtract(current_task, tasks), 1e5)

    new_unixstart = np.multiply(((tasks==load_type_id))*1, unixtime)
    new_unixend = np.add(new_unixstart, duration)
    update = (np.subtract(new_unixstart, unixstart)>0)*1
    retain = (np.subtract(new_unixstart, unixstart)<=0)*1

    unixstart = np.add(np.multiply(retain, unixstart), np.multiply(update, new_unixstart))
    unixend = np.add(np.multiply(retain, unixend), np.multiply(update, new_unixend))
  except Exception as e:
    print(e)
  return unixstart, unixend

def is_connected(unixtime, unixstart, unixend):
  return ((unixstart<=unixtime)&(unixend>unixtime))*1











